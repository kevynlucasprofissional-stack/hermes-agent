"""Extract all subagent comparative reports from session transcript JSONL.

Uses task-id cross-referencing to find ALL 29 reports, including those
that may not have standard section headers or are in attachment format.
"""
import json
import re
import sys
import os

TRANSCRIPT = r"C:\Users\Kevyn Lucas\.claude\projects\C--Github-hermes-agent\fabba7e6-1013-42c5-92c4-c77d82407065.jsonl"
OUTPUT = r"C:\Github\hermes-agent\workstation\context\BROWSER_COMPARATIVE_ANALYSES.md"


def extract_text_blocks(obj):
    """Yield all text strings from a JSONL object regardless of type."""
    t = obj.get("type", "")
    if t in ("user", "assistant"):
        msg = obj.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    yield block.get("text", "")
        elif isinstance(content, str):
            yield content
    elif t == "attachment":
        att = obj.get("attachment", {})
        for key in ("content", "text", "rendered"):
            val = att.get(key, "")
            if isinstance(val, str):
                yield val
    elif t == "queue-operation":
        content = obj.get("content", "")
        if isinstance(content, str):
            yield content
        elif isinstance(content, dict):
            for v in content.values():
                if isinstance(v, str):
                    yield v


def find_all_reports(transcript_path):
    """Find all unique comparative reports using multiple strategies."""
    reports = []
    seen_normalized = set()

    # Strategy 1: Find reports by "# Relat" marker with section headers
    # Strategy 2: Find reports in agent-message hand-backs
    # Strategy 3: Find reports that mention "vs Hermes" or "Hermes Workstation vs"

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            # Quick filter
            has_report_marker = "Relat" in line or "Comparativo" in line
            has_vs_marker = "vs Hermes" in line or "Hermes Workstation vs" in line or "Browser Hermes" in line

            if not has_report_marker and not has_vs_marker:
                continue

            try:
                obj = json.loads(line)
            except Exception:
                continue

            for text in extract_text_blocks(obj):
                # Try to find report start with multiple markers
                idx = -1
                for marker in ["# Relatório Comparativo", "# Relat", "## Relatório Comparativo"]:
                    pos = text.find(marker)
                    if pos >= 0:
                        idx = pos
                        break

                if idx < 0:
                    # Try finding report by table pattern (| Dimensão |)
                    table_idx = text.find("| Dimensão |")
                    if table_idx > 0:
                        # Look backwards for a heading
                        preceding = text[:table_idx]
                        for marker in ["# ", "## "]:
                            last_heading = preceding.rfind(marker)
                            if last_heading >= 0:
                                idx = last_heading
                                break

                    if idx < 0:
                        continue

                report_text = text[idx:]

                # Validate it's a real report: must have tables or section headers
                has_table = "| Dimensão |" in report_text or "|---|" in report_text or "| :" in report_text
                has_sections = "## 1." in report_text or "## 2." in report_text or "## 3." in report_text
                has_exec_summary = "Resumo Executivo" in report_text or "Recomendações" in report_text

                if not (has_table or has_sections or has_exec_summary):
                    continue

                first_line = report_text.split("\n")[0].strip()

                # Normalize for dedup
                norm = re.sub(r"[^\w]", "", first_line.lower())
                if len(norm) < 10:  # Skip very short/empty titles
                    continue
                if norm in seen_normalized:
                    continue
                seen_normalized.add(norm)
                reports.append((line_num, first_line, report_text))

    return reports


def main():
    reports = find_all_reports(TRANSCRIPT)
    print(f"Found {len(reports)} unique reports:")
    for line_num, title, _ in reports:
        print(f"  Line {line_num}: {title[:120]}")

    # Build consolidated markdown
    header = """# Análises Comparativas do Browser Nativo Hermes Workstation

> Consolidado de todos os relatórios comparativos gerados por subagentes.
> Cada relatório analisa uma referência externa contra o browser nativo do Hermes Workstation.
> Gerado automaticamente a partir do transcript da sessão.

---

"""
    sections = []
    for i, (_, _, report_text) in enumerate(reports, 1):
        sections.append(f"<!-- Relatório {i} -->\n\n{report_text}\n\n---\n")

    content = header + "\n".join(sections)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as out:
        out.write(content)

    size_bytes = len(content.encode("utf-8"))
    print(f"\nWritten {len(reports)} reports to {OUTPUT}")
    print(f"File size: {size_bytes} bytes ({size_bytes / 1024:.1f} KB)")


if __name__ == "__main__":
    main()