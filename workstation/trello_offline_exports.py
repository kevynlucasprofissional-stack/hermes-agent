"""Incorpora exports Trello locais como snapshots de leitura, sem alterar o Trello.

Os cards previamente importados pelo conector prevalecem: nunca sobrescrever.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from workstation import acirv_datasets

BOARDS = {
    "Edq32SNp": "Calendário Editorial",
    "ZWzfEDkM": "LEADS DE ASSOCIADOS",
    "GDM8ZE3r": "ACIRV + VCOM: SCRUM",
}
COMPLETE_LIST = re.compile(r"(?:^|[\s_-])(finalizad[oa]s?|conclu[ií]d[oa]s?|feitos?|done|completed)(?:[\s_-]|$)",re.I)
TRELLO_ID = re.compile(r"^[a-f0-9]{24}$")


def _hash(path: Path) -> str:
    d=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            d.update(chunk)
    return d.hexdigest()


def import_exports(paths: list[Path], home: Path | None = None) -> dict:
    """Adiciona somente os cartões abertos ausentes à trello.sqlite interna."""
    snapshots=[]
    for path in map(Path,paths):
        raw=json.loads(path.read_text(encoding="utf-8-sig"))
        if raw.get("shortLink") not in BOARDS or raw.get("name")!=BOARDS[raw["shortLink"]]:
            raise ValueError(f"Export Trello inesperado: {path.name}")
        if not isinstance(raw.get("cards"),list) or not isinstance(raw.get("lists"),list):
            raise ValueError("Export sem cartões/listas")
        lists={l["id"]:l.get("name","") for l in raw["lists"]}
        labels={l["id"]:l for l in raw.get("labels",[])}
        members={m["id"]:m for m in raw.get("members",[])}
        checks=defaultdict(list)
        for x in raw.get("checklists",[]): checks[x.get("idCard")].append(x)
        actions=defaultdict(list)
        for x in raw.get("actions",[]):
            card=((x.get("data") or {}).get("card") or {}).get("id")
            if card: actions[card].append(x)
        digest=_hash(path)
        valid=[]
        for c in raw["cards"]:
            if c.get("closed") is True or c.get("dueComplete") is True:
                continue
            list_name=lists.get(c.get("idList"))
            if list_name is None:
                raise ValueError("Cartão sem lista válida")
            if COMPLETE_LIST.search(list_name):
                continue
            if not TRELLO_ID.fullmatch(str(c.get("id",""))) or c.get("idBoard")!=raw["id"]:
                raise ValueError("Cartão com id inválido/outro quadro")
            valid.append((c,list_name,actions[c["id"]],checks[c["id"]]))
        snapshots.append((path,raw,digest,valid,labels,members))
    target=acirv_datasets.directory(home)/"trello.sqlite"
    if not target.is_file():
        raise ValueError("Importe o dataset Trello antes dos exports")
    source_hash=_hash(target)
    fd,temp_name=tempfile.mkstemp(prefix="trello-export-",suffix=".sqlite",dir=target.parent)
    os.close(fd)
    temp=Path(temp_name)
    try:
        with closing(sqlite3.connect(target.as_uri()+"?mode=ro",uri=True)) as src:
            with closing(sqlite3.connect(temp)) as dst:src.backup(dst)
        totals={}
        with closing(sqlite3.connect(temp)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""CREATE TABLE IF NOT EXISTS trello_export_evidence(
                card_id TEXT PRIMARY KEY REFERENCES cards(id),
                board_id TEXT NOT NULL, card_json TEXT NOT NULL,
                actions_json TEXT NOT NULL, checklists_json TEXT NOT NULL,
                source_sha256 TEXT NOT NULL
            )""")
            for path,raw,digest,items,labels,members in snapshots:
                count=0
                for c, list_name,action_rows,check_rows in items:
                    if conn.execute("SELECT 1 FROM cards WHERE id=?",(c["id"],)).fetchone():
                        continue
                    conn.execute("""INSERT INTO cards
                        (id,name,description,url,board_name,board_id,list_name,list_id,
                         due,last_activity_at,status,labels_json,members_json,
                         checklists_json,comments_json,checklists_truncated,comments_truncated)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                        c["id"],c["name"],c.get("desc") or "",c.get("shortUrl") or c["url"],
                        raw["name"],raw["id"],list_name,c["idList"],
                        c.get("due"),c.get("dateLastActivity"),"em_aberto",
                        json.dumps([labels[k] for k in c.get("idLabels",[]) if k in labels],ensure_ascii=False),
                        json.dumps([members[k] for k in c.get("idMembers",[]) if k in members],ensure_ascii=False),
                        json.dumps(check_rows,ensure_ascii=False),
                        json.dumps([a for a in action_rows if a.get("type")=="commentCard"],ensure_ascii=False),
                        0,int(len(raw.get("actions",[]))>=1000),
                    ))
                    conn.execute("""INSERT INTO trello_export_evidence
                        (card_id,board_id,card_json,actions_json,checklists_json,source_sha256)
                        VALUES (?,?,?,?,?,?)""",(
                        c["id"],raw["id"],json.dumps(c,ensure_ascii=False),
                        json.dumps(action_rows,ensure_ascii=False),
                        json.dumps(check_rows,ensure_ascii=False),digest,
                    ))
                    count+=1
                totals[raw["name"]]=count
            if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Snapshot Trello inválido")
            conn.commit()
            total=conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        if not any(totals.values()):
            return {"status":"unchanged","new_by_board":totals,"cards":total}
        if _hash(target)!=source_hash:
            raise ValueError("Dataset Trello alterado simultaneamente; nenhum dado substituído")
        backup=target.with_suffix(".before-export-merge.sqlite")
        if backup.exists():
            raise ValueError("Já existe backup desta fusão; inspecionar antes de sobrescrever")
        with closing(sqlite3.connect(target.as_uri()+"?mode=ro",uri=True)) as src:
            with closing(sqlite3.connect(backup)) as dst:src.backup(dst)
        os.replace(temp,target)
        return {"status":"imported","new_by_board":totals,"cards":total,"backup":str(backup)}
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports",nargs="+",type=Path)
    args=parser.parse_args()
    print(json.dumps(import_exports(args.exports),ensure_ascii=False))


if __name__=="__main__":
    main()
