# -*- coding: utf-8 -*-
"""Inventário auditável dos históricos Claude Code e seus relatórios.
Uso: python atualizar_controle_sessoes_ia.py
Apenas lê transcrições e relatórios; altera exclusivamente arquivos CONTROLE_SESSOES_IA.*.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter
import csv,hashlib,json,re,os

ROOT=Path(__file__).resolve().parent
RAW=ROOT/"Sessões Claude - BRUTO"
REPORTS=ROOT/"Relatório de sessões de IA"
LIVE=Path.home()/".claude"/"projects"
J=ROOT/"CONTROLE_SESSOES_IA.json"
C=ROOT/"CONTROLE_SESSOES_IA.csv"
UUID=re.compile(r"^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$",re.I)
TICK=chr(96)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4*1024*1024),b""):h.update(x)
    return h.hexdigest()
def read_prev():
    if J.exists():
        return json.loads(J.read_text(encoding="utf-8"))
    return {"sessoes":[]}
def short_path(title):
    return re.sub(r'[<>:"/\\|?*]','-',str(title)).strip(" .")[:78]
def sync():
    prev=read_prev()
    old={v["id_sessao"]:v for v in prev["sessoes"]}
    lines=[];report_lookup={}
    # IDs exatos no cabeçalho são vinculados com evidência forte.
    for report in REPORTS.rglob("Relatório Técnico - *.md"):
        m=re.search(r"\[([0-9a-f]{8})\]\.md$",report.name,re.I)
        if not m:continue
        prefix=m.group(1).lower()
        # Candidate by ID prefix. Exact full UUID is checked before linking.
        report_lookup.setdefault(prefix,[]).append(report)
    root_files=list(RAW.glob("*/*/*.jsonl"))
    for f in sorted(root_files):
        sid=f.stem
        if not UUID.fullmatch(sid):continue
        original=old.get(sid,{})
        rep=Path(original["caminho_relatorio"]) if original.get("caminho_relatorio") else None
        if rep is not None and not rep.is_file():
            matches=list(REPORTS.rglob(rep.name))
            if len(matches)==1: rep=matches[0]
        if rep is None:
            for candidate in report_lookup.get(sid[:8].lower(),[]):
                if sid in candidate.read_text(encoding="utf-8",errors="replace"):
                    rep=candidate
                    break
        status="SEM_RELATORIO"
        method=original.get("vinculo","")
        note=""
        raw_hash=sha(f)
        report_basis=original.get("sha256_jsonl_no_ultimo_relatorio") or original.get("sha256_jsonl") or raw_hash
        if rep is not None and rep.is_file():
            actual=sha(rep)
            prior=original.get("sha256_relatorio")
            if prior and prior!=actual:
                status="RELATORIO_MODIFICADO_REVISAR"
                note="Hash do relatório mudou desde a última execução; verificar vínculo e conteúdo"
            elif report_basis!=raw_hash:
                status="RELATORIO_POSSIVELMENTE_DESATUALIZADO"
                note="O histórico bruto mudou desde a base do relatório; avaliar novos turnos"
            else:
                status="COM_RELATORIO"
            if not original:
                method="ID_EXATO"
        elif rep is not None:
            status="RELATORIO_DESAPARECIDO"
            note="O relatório vinculado não está mais no caminho esperado"
        source=LIVE/f.parent.parent.name/(sid+".jsonl")
        src_state="ORIGEM_LOCAL_AUSENTE"
        src_hash=""
        if source.is_file():
            if f.stat().st_size!=source.stat().st_size:
                src_state="BACKUP_DESATUALIZADO"
            else:
                src_hash=sha(source)
                src_state="BACKUP_SINCRONIZADO" if raw_hash==src_hash else "BACKUP_DESATUALIZADO"
        row=dict(original)
        row.update({
            "id_sessao":sid,"titulo":row.get("titulo",""),
            "projeto":f.parent.parent.name,"situacao":status,"vinculo":method,
            "relatorio":rep.name if rep else "",
            "sha256_jsonl":raw_hash,"bytes_jsonl":f.stat().st_size,
            "sha256_jsonl_no_ultimo_relatorio":report_basis,
            "sha256_relatorio":(original.get("sha256_relatorio") if status=="RELATORIO_MODIFICADO_REVISAR" else sha(rep)) if rep is not None and rep.is_file() else "",
            "bytes_relatorio":rep.stat().st_size if rep is not None and rep.is_file() else 0,
            "caminho_arquivo_bruto":str(f),
            "caminho_relatorio":str(rep) if rep is not None else "",
            "origem_sincronizacao":src_state,
            "observacao_controle":note
        })
        lines.append(row)
    archived_ids={v["id_sessao"] for v in lines}
    for original in LIVE.glob("*/*.jsonl"):
        sid=original.stem
        if UUID.fullmatch(sid) and sid not in archived_ids:
            lines.append({"id_sessao":sid,"titulo":"","projeto":original.parent.name,
                "situacao":"NOVO_SEM_BACKUP_E_RELATORIO","vinculo":"",
                "relatorio":"","sha256_jsonl":"","bytes_jsonl":0,"sha256_relatorio":"","bytes_relatorio":0,
                "caminho_arquivo_bruto":"","caminho_relatorio":"","origem_sincronizacao":"ORIGEM_NAO_ARQUIVADA",
                "observacao_controle":str(original)})
    counts=dict(Counter(x["situacao"] for x in lines))
    sources=dict(Counter(x["origem_sincronizacao"] for x in lines))
    ctrl={"schema_version":3,
          "atualizado_em":datetime.now(timezone(timedelta(hours=-3))).isoformat(),
          "total_sessoes":len(lines),"contagem_situacao":counts,"sincronizacao":sources,
          "metodo":"ID exato em novos relatórios; vínculo histórico preservado para relatórios antigos, confirmado por hash do arquivo.",
          "sessoes":lines}
    temp=J.with_suffix(".json.tmp")
    temp.write_text(json.dumps(ctrl,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(temp,J)
    columns=["id_sessao","titulo","projeto","situacao","origem_sincronizacao","vinculo","relatorio",
             "avaliacao_conteudo","verificacao_de_codigo",
             "bytes_jsonl","sha256_jsonl","sha256_jsonl_no_ultimo_relatorio","bytes_relatorio","sha256_relatorio",
             "caminho_arquivo_bruto","caminho_relatorio","observacao_controle"]
    with C.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");w.writeheader();w.writerows(lines)
    print(json.dumps({"total":len(lines),"situacao":counts,"backup":sources,
                      "controle_json":str(J),"controle_csv":str(C)},ensure_ascii=False,indent=2))
if __name__=="__main__":
    sync()
