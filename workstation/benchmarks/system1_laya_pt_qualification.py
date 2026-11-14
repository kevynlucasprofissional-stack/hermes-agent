"""Benchmark real Laya multilíngue para a escolha de elementos do Browser, sem acesso à UI."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import time

from laya import Router

# Casos sintéticos de leitura, sem páginas do usuário nem segredos.
CASES = [
    ("relatorios", "Relatórios", ["Relatórios", "Configurações", "Ajuda"], "@e1"),
    ("configuracoes", "Configurações", ["Relatórios", "Configurações", "Ajuda"], "@e2"),
    ("painel", "Painel", ["Ajuda", "Painel", "Configurações"], "@e2"),
    ("editorial", "Calendário editorial", ["Calendário editorial", "Clientes", "Financeiro"], "@e1"),
    ("clientes", "Clientes", ["Ajuda", "Contatos", "Clientes"], "@e3"),
    ("relatorios_parcial", "Relatórios", ["Abrir relatórios", "Configurações", "Ajuda"], "@e1"),
    ("relatorios_ausente", "Relatórios", ["Clientes", "Configurações", "Ajuda"], None),
    ("duplicado", "Relatórios", ["Relatórios", "Relatórios", "Ajuda"], None),
    ("acao_inexistente", "Editar", ["Excluir", "Publicar", "Cancelar"], None),
]
NEUTRAL = {"NO_MATCH", "ABSTAIN"}
THRESHOLD = 0.54  # perfis locais: 0,60 * 0,90 read_only


def run(output: Path) -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    router = Router(device="cpu", default="multilingual", max_loaded=1, auto_task_detection=False)
    records = []
    for name, target, labels, expected in CASES:
        controls = [{"ref": f"@e{i + 1}", "role": "button", "label": label} for i, label in enumerate(labels)]
        criteria = {row["ref"]: f'button: {row["label"]}' for row in controls}
        criteria["NO_MATCH"] = "Nenhum elemento corresponde ao alvo"
        criteria["ABSTAIN"] = "Ambiguidade ou incerteza; abster-se"
        state = {"objective": target, "kind": "button", "controls": controls}
        questions = {"preferred_candidate": {
            "type": "choice",
            "instructions": "Which observed UI element exactly matches the requested read-only target? "
                            "Choose ABSTAIN or NO_MATCH if uncertain.",
            "criteria": criteria,
        }}
        started = time.perf_counter()
        response = router.predict(state=state, questions=questions, model="multilingual", lang="pt")
        elapsed_ms = (time.perf_counter() - started) * 1000
        answer = response.get("answers", {}).get("preferred_candidate", {})
        choice = answer.get("choice")
        confidence = float(answer.get("answer_confidence", 0.0))
        effective = choice if confidence >= THRESHOLD and choice not in NEUTRAL else None
        # The production selector also insists that the target occurs in the observed label.
        if effective is not None:
            label = next((row["label"] for row in controls if row["ref"] == effective), "")
            exact = [row for row in controls if row["label"].casefold() == target.casefold()]
            plausible = [row for row in controls if target.casefold() in row["label"].casefold()]
            if (target.casefold() not in label.casefold() or len(exact) > 1
                    or (not exact and len(plausible) > 1)):
                effective = None
        success = effective == expected
        record = {"case": name, "target": target, "expected": expected, "raw_choice": choice,
                  "confidence": round(confidence, 4), "decision_after_hermes_guard": effective,
                  "duration_ms": round(elapsed_ms, 2), "ok": success,
                  "abstained": effective is None}
        records.append(record)
        print("QUAL_CASE=" + json.dumps(record, ensure_ascii=False), flush=True)
    timings = [row["duration_ms"] for row in records]
    warm = timings[1:]
    report = {"model": "multilingual", "language": "pt", "inference_backend": "cpu",
              "offline": True, "n": len(records), "correct": sum(r["ok"] for r in records),
              "false_accept": sum(r["expected"] is None and r["decision_after_hermes_guard"] is not None for r in records),
              "fallback": sum(r["abstained"] for r in records), "cold_ms": timings[0],
              "warm_p50_ms": round(statistics.median(warm), 2),
              "warm_max_ms": round(max(warm), 2), "threshold": THRESHOLD, "cases": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("QUAL_SUMMARY=" + json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    run(ap.parse_args().output)
