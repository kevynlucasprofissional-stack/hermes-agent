"""Campaign file manifest, durable sequential checkpoints and pause semantics.

All tests are synthetic; they never access WhatsApp, real contact files, or
the user's control SQLite/config.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from workstation.integrations.hermes import whatsapp_campaign_runner as runner
from workstation.integrations.hermes.whatsapp_campaign_manifest import (
    CampaignManifestError, load_campaign,
)


def _fixture(tmp_path: Path):
    home=tmp_path / "hermes"
    home.mkdir()
    folder=tmp_path / "source"
    folder.mkdir()
    photo=tmp_path / "photo.png"
    photo.write_bytes(b"fake-image-for-mock-only")
    (folder / "Alvos.json").write_text(json.dumps({
        "presencas": [
            {"nome":"Ana Teste", "telefone":"+5564999991111"},
            {"nome":"Beto Teste","telefone":"+5564999992222"},
        ]
    }), encoding="utf-8")
    (folder / "Mensagem.txt").write_text(
        '[Mensagem 01]\nOlá [Nome], bem-vindo!\n'
        f'[Mensagem 02]\n[Anexar foto "{photo}"]\nImagem e legenda para [Nome].\n'
        '[Mensagem 03]\nObrigado, [Nome].\n',
        encoding="utf-8",
    )
    return folder, home


def _send_ok(**kwargs):
    return {"state":"OBSERVED", "header_verified":True,
            "message_data_id":"sha256:"+"a"*64, "ack_label":"sent"}


def test_manifest_exact_content_and_sha(tmp_path):
    folder,_=_fixture(tmp_path)
    manifest=load_campaign(folder)
    assert len(manifest.contacts)==2
    assert manifest.contacts[0].steps[0].body=="Olá Ana, bem-vindo!"
    assert manifest.contacts[1].steps[1].body=="Imagem e legenda para Beto."
    assert manifest.contacts[0].steps[1].kind=="image"
    assert len(manifest.contacts[0].steps[1].media_sha256)==64
    assert manifest.skipped==0


def test_two_contact_campaign_resumes_without_duplicates(tmp_path,monkeypatch):
    folder,home=_fixture(tmp_path)
    monkeypatch.setattr(runner,"_home",lambda:home)
    grants=[]
    monkeypatch.setattr(runner,"_grant",lambda **args: grants.append(args["mode"]))
    sends=[]
    def sender(**kwargs):
        sends.append(("text",kwargs["phone_digits"],kwargs["message"]))
        return _send_ok()
    def image(**kwargs):
        sends.append(("image",kwargs["phone_digits"],kwargs["caption"]))
        return _send_ok()
    args=dict(source_dir=str(folder),task_id="task",run_id="run",session_id="sess",
              send_text=sender,send_image=image,
              opt_out_check=lambda **kwargs:{"state":"CLEAR"},max_contacts=1)
    first=runner.execute_campaign(**args)
    assert first["state"]=="PARTIAL"
    assert first["counts"]["OBSERVED"]==3
    assert len(sends)==3
    second=runner.execute_campaign(**args)
    assert second["state"]=="COMPLETED"
    assert second["counts"]["OBSERVED"]==6
    assert len(sends)==6
    assert runner.execute_campaign(**args)["counts"]["OBSERVED"]==6
    assert len(sends)==6
    assert grants==["add","remove"]*3
    assert [item[0] for item in sends]==["text","image","text"]*2


def test_campaign_pauses_when_first_send_uncertain(tmp_path,monkeypatch):
    folder,home=_fixture(tmp_path)
    monkeypatch.setattr(runner,"_home",lambda:home)
    monkeypatch.setattr(runner,"_grant",lambda **kwargs: None)
    sent=[]
    def failed(**kwargs):
        sent.append(kwargs)
        return {"state":"UNCERTAIN","error_code":"POST_SEND_UNKNOWN"}
    args=dict(source_dir=str(folder),task_id="task",run_id="run",session_id="sess",
              send_text=failed,send_image=failed,
              opt_out_check=lambda **kwargs:{"state":"CLEAR"},max_contacts=2)
    outcome=runner.execute_campaign(**args)
    assert outcome["state"]=="PAUSED"
    assert outcome["counts"]["UNCERTAIN"]==1
    assert outcome["counts"]["QUEUED"]==5
    assert len(sent)==1
    assert runner.execute_campaign(**args)["state"]=="PAUSED"
    assert len(sent)==1


def test_optout_skips_entire_contact_without_sending(tmp_path,monkeypatch):
    folder,home=_fixture(tmp_path)
    monkeypatch.setattr(runner,"_home",lambda:home)
    monkeypatch.setattr(runner,"_grant",lambda **kwargs: None)
    sent=[]
    def sender(**kwargs):
        sent.append(kwargs)
        return _send_ok()
    result=runner.execute_campaign(
        source_dir=str(folder),task_id="task",run_id="run",session_id="sess",
        send_text=sender,send_image=sender,max_contacts=2,
        opt_out_check=lambda **kwargs:{"state":"OPT_OUT"},
    )
    assert result["state"]=="COMPLETED"
    assert result["counts"]["SKIPPED_OPT_OUT"]==6
    assert not sent


def test_source_edit_after_first_execution_blocks_resume(tmp_path,monkeypatch):
    folder,home=_fixture(tmp_path)
    monkeypatch.setattr(runner,"_home",lambda:home)
    monkeypatch.setattr(runner,"_grant",lambda **kwargs:None)
    calls=[]
    def sent(**kwargs):
        calls.append(kwargs)
        return _send_ok()
    args=dict(source_dir=str(folder),task_id="task",run_id="run",session_id="sess",
              send_text=sent,send_image=sent,
              opt_out_check=lambda **kwargs:{"state":"CLEAR"},max_contacts=1)
    assert runner.execute_campaign(**args)["state"]=="PARTIAL"
    text=folder/"Mensagem.txt"
    text.write_text(text.read_text("utf8").replace("Obrigado","Agradecemos"),"utf8")
    result=runner.execute_campaign(**args)
    assert result["error_code"]=="CAMPAIGN_MANIFEST_CHANGED"
    assert len(calls)==3
