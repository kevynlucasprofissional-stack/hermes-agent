"""Resumable file-backed WhatsApp campaign with native per-item receipts.

The model never receives the recipient list or media path. All effects are
executed through the real Hermes BrowserTask and one canonical TaskRun.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
from typing import Any, Callable

from workstation.integrations.hermes.whatsapp_campaign_manifest import (
    CampaignManifest, CampaignManifestError, load_campaign,
)

FINAL = {"OBSERVED", "CONFIRMED", "SKIPPED_OPT_OUT"}
STOP = {"UNCERTAIN", "IN_PROGRESS", "HOLD"}


def _home() -> Path:
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"])
    return Path(os.environ["LOCALAPPDATA"]) / "hermes"


def _db() -> Path:
    return _home() / "whatsapp_send_control.sqlite"


def _job_id(manifest: CampaignManifest) -> str:
    # Stable across Hermes sessions, TaskRuns and source-file updates.
    return "wa_campaign_" + hashlib.sha256(
        str(Path(manifest.source_dir).resolve()).casefold().encode()
    ).hexdigest()[:20]


def _init(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS whatsapp_campaign_jobs(
            job_id TEXT PRIMARY KEY,
            source_digest TEXT NOT NULL,
            source_path TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS whatsapp_campaign_steps(
            job_id TEXT NOT NULL, contact_index INTEGER NOT NULL,
            step_code TEXT NOT NULL, phone_hash TEXT NOT NULL,
            body_digest TEXT NOT NULL, media_digest TEXT,
            status TEXT NOT NULL, error_code TEXT, failure_phase TEXT,
            message_data_id TEXT, ack_label TEXT,
            operation_id TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (job_id,contact_index,step_code),
            FOREIGN KEY(job_id) REFERENCES whatsapp_campaign_jobs(job_id));
        """)


def campaign_status(manifest: CampaignManifest) -> dict[str, Any]:
    job_id=_job_id(manifest)
    if not _db().is_file():
        return {"success":True,"job_id":job_id,"state":"NOT_STARTED",
                "planned_contacts":len(manifest.contacts),
                "planned_steps":sum(len(c.steps) for c in manifest.contacts),
                "observed_count":0}
    try:
        with sqlite3.connect("file:"+_db().as_posix()+"?mode=ro",uri=True) as db:
            row=db.execute(
                "SELECT source_digest,status FROM whatsapp_campaign_jobs WHERE job_id=?",
                (job_id,)
            ).fetchone()
            if not row:
                return {"success":True,"job_id":job_id,"state":"NOT_STARTED",
                        "planned_contacts":len(manifest.contacts),
                        "planned_steps":sum(len(c.steps) for c in manifest.contacts),
                        "observed_count":0}
            if row[0]!=manifest.digest:
                return {"success":False,"error_code":"CAMPAIGN_MANIFEST_CHANGED",
                        "job_id":job_id}
            steps=db.execute(
                "SELECT contact_index,step_code,status,error_code,ack_label "
                "FROM whatsapp_campaign_steps WHERE job_id=? ORDER BY contact_index,step_code",
                (job_id,)
            ).fetchall()
    except sqlite3.Error:
        return {"success":False,"error_code":"CAMPAIGN_STATUS_UNAVAILABLE"}
    counts={}
    for r in steps:
        counts[r[2]]=counts.get(r[2],0)+1
    return {
        "success":True,"job_id":job_id,"state":row[1],
        "planned_contacts":len(manifest.contacts),"planned_steps":len(steps),
        "counts":counts,
        "current_contact_index":next((r[0] for r in steps if r[2] not in FINAL),None),
        "items":[{"contact_index":r[0],"step_code":r[1],
                  "state":r[2],"error_code":r[3],"ack_label":r[4]}
                 for r in steps],
    }


def _grant(*,mode:str,task_id:str,session_id:str,run_id:str,root:Path) -> None:
    script=Path(__file__).resolve().parents[3]/"workstation"/"scripts"/"wa_campaign_scoped_upload_grant.mjs"
    subprocess.run(
        ["node",str(script),mode,task_id,session_id,str(run_id),str(root)],
        check=True,timeout=12,capture_output=True,text=True,
        cwd=script.parents[2],
    )


def execute_campaign(
    *, source_dir: str, task_id: str, run_id: str, session_id: str,
    send_text: Callable[..., dict[str, Any]],
    send_image: Callable[..., dict[str, Any]],
    opt_out_check: Callable[..., dict[str, Any]],
    max_contacts: int = 1,
) -> dict[str, Any]:
    manifest=load_campaign(source_dir)
    if (not task_id or not run_id or not session_id
            or type(max_contacts) is not int or not 1<=max_contacts<=200):
        return {"state":"FAILED","error_code":"CAMPAIGN_CONTEXT_INVALID"}
    job_id=_job_id(manifest)
    dbpath=_db()
    dbpath.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(dbpath,timeout=10) as db:
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        _init(db)
        db.execute("BEGIN IMMEDIATE")
        exists=db.execute("SELECT source_digest FROM whatsapp_campaign_jobs WHERE job_id=?",
                          (job_id,)).fetchone()
        if exists and exists[0]!=manifest.digest:
            db.rollback()
            return {"state":"HOLD","error_code":"CAMPAIGN_MANIFEST_CHANGED","job_id":job_id}
        if exists is None:
            db.execute(
                "INSERT INTO whatsapp_campaign_jobs(job_id,source_digest,source_path,status)"
                "VALUES (?,?,?,?)",
                (job_id,manifest.digest,manifest.source_dir,"QUEUED"))
            for index,person in enumerate(manifest.contacts):
                for step in person.steps:
                    db.execute(
                        "INSERT INTO whatsapp_campaign_steps("
                        "job_id,contact_index,step_code,phone_hash,body_digest,media_digest,"
                        "status) VALUES(?,?,?,?,?,?,?)",
                        (job_id,index,step.code,
                         hashlib.sha256(person.phone.encode()).hexdigest(),
                         hashlib.sha256(step.body.encode()).hexdigest(),
                         step.media_sha256,
                         "SKIPPED_OPT_OUT" if person.opted_out else "QUEUED"),
                    )
        db.commit()

    # The file grant lasts only during this TaskRun; staging has one photo.
    media_steps=[s for c in manifest.contacts for s in c.steps if s.kind=="image"]
    stage=None
    active_grant=False
    if media_steps:
        src=Path(media_steps[0].media_path)
        stage=_home()/"campaign-media"/job_id
        stage.mkdir(parents=True,exist_ok=True)
        file_copy=stage/src.name
        if not file_copy.is_file() or _sha256_copy(file_copy)!=media_steps[0].media_sha256:
            shutil.copy2(src,file_copy)
        if _sha256_copy(file_copy)!=media_steps[0].media_sha256:
            return {"state":"HOLD","error_code":"MEDIA_STAGING_HASH_MISMATCH"}
        try:
            _grant(mode="add",task_id=task_id,run_id=str(run_id),
                   session_id=session_id,root=stage.resolve())
            active_grant=True
        except Exception:
            return {"state":"HOLD","error_code":"UPLOAD_GRANT_FAILED","job_id":job_id}

    visited=0
    stop_reason=None
    try:
        for n,contact in enumerate(manifest.contacts):
            if contact.opted_out:
                continue
            with sqlite3.connect(dbpath) as db:
                statuses=db.execute(
                    "SELECT status FROM whatsapp_campaign_steps "
                    "WHERE job_id=? AND contact_index=?",
                    (job_id,n)).fetchall()
            if statuses and all(r[0] in FINAL for r in statuses):
                continue
            if visited>=max_contacts:
                break
            if any(r[0] in STOP for r in statuses):
                stop_reason="RECONCILIATION_REQUIRED"
                break
            visited+=1
            try:
                check=opt_out_check(
                    phone_digits=contact.phone,task_id=task_id,
                    session_id=session_id,run_id=str(run_id),
                    operation_id=f"{job_id}_{n}_optout")
            except Exception:
                check={"state":"HOLD","error_code":"OPT_OUT_CHECK_FAILED"}
            if not isinstance(check,dict) or check.get("state") not in {"CLEAR","OPT_OUT"}:
                stop_reason=(check or {}).get("error_code","OPT_OUT_CHECK_UNKNOWN")
                break
            if check["state"]=="OPT_OUT":
                with sqlite3.connect(dbpath) as db:
                    db.execute(
                        "UPDATE whatsapp_campaign_steps SET status='SKIPPED_OPT_OUT' "
                        "WHERE job_id=? AND contact_index=? AND status='QUEUED'",
                        (job_id,n))
                    db.commit()
                continue
            for step in contact.steps:
                with sqlite3.connect(dbpath,timeout=10) as db:
                    db.execute("BEGIN IMMEDIATE")
                    status=db.execute(
                        "SELECT status FROM whatsapp_campaign_steps "
                        "WHERE job_id=? AND contact_index=? AND step_code=?",
                        (job_id,n,step.code)
                    ).fetchone()
                    if status is None or status[0] in FINAL:
                        db.rollback()
                        continue
                    if status[0]!="QUEUED":
                        db.rollback()
                        stop_reason="RECONCILIATION_REQUIRED"
                        break
                    op=hashlib.sha256(
                        f"{job_id}|{n}|{step.code}|{manifest.digest}".encode()
                    ).hexdigest()[:20]
                    operation_id=f"wa_campaign_{op}"
                    db.execute(
                        "UPDATE whatsapp_campaign_steps SET status='IN_PROGRESS',"
                        "operation_id=?,updated_at=CURRENT_TIMESTAMP WHERE "
                        "job_id=? AND contact_index=? AND step_code=?",
                        (operation_id,job_id,n,step.code))
                    db.commit()
                try:
                    if step.kind=="image":
                        assert stage is not None
                        result=send_image(
                            phone_digits=contact.phone,caption=step.body,
                            media_path=str(stage/Path(step.media_path).name),
                            task_id=task_id,run_id=str(run_id),session_id=session_id,
                            operation_id=operation_id)
                    else:
                        result=send_text(
                            phone_digits=contact.phone,message=step.body,
                            task_id=task_id,kanban_card_id=task_id,
                            run_id=str(run_id),session_id=session_id,
                            operation_id=operation_id,
                            delivery_timeout_seconds=7.0)
                except Exception:
                    result={"state":"UNCERTAIN","error_code":"CAMPAIGN_SEND_EXCEPTION"}
                ack=result.get("ack_label") if isinstance(result,dict) else None
                msgid=result.get("message_data_id") if isinstance(result,dict) else None
                good=(isinstance(result,dict) and result.get("state") in {"OBSERVED","CONFIRMED"}
                      and result.get("header_verified") is True
                      and ack in {"sent","delivered","read"}
                      and isinstance(msgid,str) and re.fullmatch(r"sha256:[a-f0-9]{64}",msgid))
                if good:
                    state=result["state"]
                elif (isinstance(result,dict) and result.get("state")=="FAILED"
                      and result.get("failure_phase") in {
                          "PRE_SEND","RESOLVE_RECIPIENT","OPEN_CHAT","VERIFY_CHAT",
                      }):
                    # Hard evidence: no composition or send-click attempted.
                    # The failed item remains explicitly blocked, never auto-retried.
                    state="HOLD"
                else:
                    state="UNCERTAIN"
                with sqlite3.connect(dbpath) as db:
                    db.execute(
                        "UPDATE whatsapp_campaign_steps SET status=?,error_code=?,"
                        "failure_phase=?,message_data_id=?,ack_label=?,"
                        "updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND "
                        "contact_index=? AND step_code=? AND status='IN_PROGRESS'",
                        (state,result.get("error_code") if isinstance(result,dict) else "INVALID_RESULT",
                         result.get("failure_phase") if isinstance(result,dict) else "UNKNOWN",
                         msgid if good else None,ack if good else None,
                         job_id,n,step.code))
                    db.commit()
                if not good:
                    stop_reason=(result or {}).get("error_code","UNVERIFIED_SEND")
                    break
                time.sleep(.4)
            if stop_reason:
                break
    finally:
        if active_grant and stage is not None:
            try:
                _grant(mode="remove",task_id=task_id,
                       run_id=str(run_id),session_id=session_id,root=stage.resolve())
            except Exception:
                # Still expires automatically within the strict time window.
                pass
    status=campaign_status(manifest)
    if not status.get("success"):
        return status
    left=status.get("counts",{}).get("QUEUED",0)
    state=("PAUSED" if stop_reason else "COMPLETED" if left==0 else "PARTIAL")
    with sqlite3.connect(dbpath) as db:
        db.execute("UPDATE whatsapp_campaign_jobs SET status=?,updated_at=CURRENT_TIMESTAMP "
                   "WHERE job_id=?", (state,job_id))
        db.commit()
    status["state"]=state
    status["stop_reason"]=stop_reason
    status["contacts_visited_this_run"]=visited
    return status


def _sha256_copy(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda:stream.read(262144),b""):
            h.update(b)
    return h.hexdigest()
