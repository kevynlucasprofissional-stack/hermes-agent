"""D-049 B1.1 — Benchmark comparativo: browser_snapshot legacy vs views compactas.

Mede bytes entregues ao modelo, contagem de elementos e latência em cenários
representativos. Usa o runtime Electron via workstation _dispatch quando
disponível; caso contrário, gera payloads sintéticos baseados no formato real
do formatInventory para validar a projeção Python.

Execução: python workstation/scripts/benchmark_snapshot_views.py
"""
from __future__ import annotations

import json
import statistics
import time
from typing import Any

from tools.browser_workstation import project_model_browser_payload


def _make_legacy_payload(element_count: int, text_chars: int) -> dict[str, Any]:
    """Gera payload legado compatível com formatInventory para benchmark."""
    lines = ["Interactive elements:\n"]
    elements = []
    for i in range(1, element_count + 1):
        ref = f"@e{i}"
        role = "button" if i % 3 == 0 else ("textbox" if i % 3 == 1 else "link")
        label = f"Element {i}"
        tag = role.upper()
        disabled = i % 7 == 0
        lines.append(f'- [{ref}] {role} "{label}"' + (" disabled" if disabled else ""))
        elements.append({
            "ref": ref, "role": role, "label": label, "tag": tag,
            "disabled": disabled, "value": "", "testid": None, "name": None,
        })
    lines.append("\nPage text:\n")
    body = "Lorem ipsum dolor sit amet. " * (text_chars // 28 + 1)
    lines.append(body[:text_chars])
    return {
        "success": True,
        "snapshot": "\n".join(lines),
        "element_count": element_count,
        "elements": elements,
        "url": "https://app.example.com/dashboard",
        "title": "Dashboard",
        "revision": 1,
        "truncated": False,
        "total_text_chars": text_chars,
    }


def _make_view_payload(view: str, element_count: int, text_chars: int) -> dict[str, Any]:
    """Gera payload compacto equivalente ao retornado pelo Electron com view ativa."""
    if view == "summary":
        text = (
            f"Host: app.example.com\nTitle: Dashboard\n"
            f"Elements: {element_count}\nText chars: {text_chars}"
        )
    elif view == "action_map":
        lines = []
        for i in range(1, element_count + 1):
            ref = f"@e{i}"
            role = "button" if i % 3 == 0 else ("textbox" if i % 3 == 1 else "link")
            label = f"Element {i}"
            disabled = " disabled" if i % 7 == 0 else ""
            lines.append(f'{ref} {role} "{label}"{disabled}')
        text = "\n".join(lines)
    elif view == "focus":
        # Foco em @e5 com 3 vizinhos
        start = max(1, 5 - 3)
        end = min(element_count, 5 + 3)
        lines = []
        for i in range(start, end + 1):
            marker = "→" if i == 5 else " "
            ref = f"@e{i}"
            role = "button" if i % 3 == 0 else ("textbox" if i % 3 == 1 else "link")
            label = f"Element {i}"
            lines.append(f'{marker} [{ref}] {role} "{label}"')
        text = "\n".join(lines)
    elif view == "content":
        text = "Lorem ipsum dolor sit amet. " * (text_chars // 28 + 1)
        text = text[:text_chars]
    else:
        raise ValueError(f"Unknown view: {view}")

    return {
        "success": True,
        "view": view,
        "snapshot": text,
        "snapshot_view": view,
        "truncated": False,
        "url": "https://app.example.com/dashboard",
        "title": "Dashboard",
        "revision": 1,
        "total_text_chars": text_chars,
    }


def _measure(payload: dict[str, Any], cycles: int) -> dict[str, float]:
    """Mede bytes e latência de projeção sobre N ciclos."""
    sizes: list[int] = []
    latencies: list[float] = []
    for _ in range(cycles):
        t0 = time.perf_counter()
        projected = project_model_browser_payload(payload)
        dt = (time.perf_counter() - t0) * 1000
        raw = json.dumps(projected, ensure_ascii=False).encode("utf-8")
        sizes.append(len(raw))
        latencies.append(dt)
    return {
        "bytes_p50": statistics.median(sizes),
        "bytes_p95": sorted(sizes)[int(len(sizes) * 0.95)] if len(sizes) >= 2 else sizes[0],
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 2 else latencies[0],
        "cycles": cycles,
    }


SCENARIOS = [
    {"name": "simple_nav", "elements": 12, "text_chars": 800},
    {"name": "spa_dashboard", "elements": 85, "text_chars": 6000},
    {"name": "form_heavy", "elements": 45, "text_chars": 3000},
    {"name": "extraction_large", "elements": 150, "text_chars": 12000},
    {"name": "human_override", "elements": 30, "text_chars": 2000},
]

VIEWS = ["summary", "action_map", "focus", "content"]
CYCLES = 20


def main() -> None:
    print("=" * 90)
    print("D-049 B1.1 — Benchmark: browser_snapshot legacy vs views compactas")
    print(f"Ciclos por cenário: {CYCLES}")
    print("=" * 90)

    results: list[dict[str, Any]] = []

    for scenario in SCENARIOS:
        name = scenario["name"]
        el = scenario["elements"]
        tc = scenario["text_chars"]
        print(f"\n--- {name} ({el} elements, {tc} text chars) ---")

        legacy = _make_legacy_payload(el, tc)
        legacy_m = _measure(legacy, CYCLES)
        print(f"  LEGACY      p50={legacy_m['bytes_p50']:>7,.0f}B  p95={legacy_m['bytes_p95']:>7,.0f}B  "
              f"lat_p50={legacy_m['latency_p50_ms']:.3f}ms")

        for view in VIEWS:
            vp = _make_view_payload(view, el, tc)
            vm = _measure(vp, CYCLES)
            saving = (1 - vm["bytes_p50"] / legacy_m["bytes_p50"]) * 100 if legacy_m["bytes_p50"] > 0 else 0
            print(f"  {view:<12} p50={vm['bytes_p50']:>7,.0f}B  p95={vm['bytes_p95']:>7,.0f}B  "
                  f"lat_p50={vm['latency_p50_ms']:.3f}ms  saving={saving:+.1f}%")
            results.append({
                "scenario": name, "mode": view,
                "bytes_p50": vm["bytes_p50"], "bytes_p95": vm["bytes_p95"],
                "saving_pct": round(saving, 1),
            })

        results.append({
            "scenario": name, "mode": "legacy",
            "bytes_p50": legacy_m["bytes_p50"], "bytes_p95": legacy_m["bytes_p95"],
            "saving_pct": 0.0,
        })

    print("\n" + "=" * 90)
    print("RESUMO — Economia média por view (todos os cenários)")
    print("=" * 90)
    for view in VIEWS:
        savings = [r["saving_pct"] for r in results if r["mode"] == view]
        avg = statistics.mean(savings) if savings else 0
        mn = min(savings) if savings else 0
        mx = max(savings) if savings else 0
        print(f"  {view:<12} avg={avg:+.1f}%  min={mn:+.1f}%  max={mx:+.1f}%")

    # Salvar resultados estruturados
    out_path = "workstation/context/benchmark_snapshot_views_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResultados salvos em: {out_path}")


if __name__ == "__main__":
    main()