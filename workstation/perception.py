from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PerceptionNode:
    ref: str
    role: str
    name: str = ""
    value: str = ""
    path: str = ""
    interactive: bool = True
    tag: str = ""
    depth: int = 0
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PerceptionView:
    snapshot_id: str
    view: str
    payload: dict[str, Any]
    estimated_tokens: int
    truncated: bool = False
    node_count: int = 0
    interactive_count: int = 0


class PerceptionEngine:
    """V2 compact, provenance-aware browser perception engine inspired by Lattice.

    Transforms raw DOM captures or accessibility node trees into token-efficient,
    hierarchical markdown summaries while preserving stable references and provenance
    paths for downstream model actions.
    """

    INTERACTIVE_ROLES = frozenset({
        "button", "link", "textbox", "searchbox", "checkbox", "radio",
        "combobox", "menuitem", "tab", "switch", "option", "treeitem"
    })

    INTERACTIVE_TAGS = frozenset({
        "button", "a", "input", "textarea", "select", "summary"
    })

    def _extract_nodes(self, raw: dict[str, Any] | list[Any], depth: int = 0, current_path: str = "") -> list[PerceptionNode]:
        nodes: list[PerceptionNode] = []

        if isinstance(raw, list):
            for i, item in enumerate(raw):
                if isinstance(item, dict):
                    nodes.extend(self._extract_nodes(item, depth, f"{current_path}/{i}"))
            return nodes

        if not isinstance(raw, dict):
            return nodes

        ref = str(raw.get("ref", raw.get("id", "")))
        role = str(raw.get("role", raw.get("tag", "generic"))).lower()
        name = str(raw.get("name", raw.get("text", raw.get("title", "")))).strip()
        value = str(raw.get("value", "")).strip()
        tag = str(raw.get("tag", "")).lower()
        path = str(raw.get("path", raw.get("selector", current_path)))

        is_interactive = (
            role in self.INTERACTIVE_ROLES
            or tag in self.INTERACTIVE_TAGS
            or raw.get("clickable", False)
            or bool(ref)
        )

        # Skip completely empty generic containers without ref or text
        has_content = bool(name or value or is_interactive)
        if has_content:
            nodes.append(PerceptionNode(
                ref=ref,
                role=role,
                name=name,
                value=value,
                path=path,
                interactive=is_interactive,
                tag=tag,
                depth=depth,
                attributes={k: str(v) for k, v in raw.get("attributes", {}).items()} if isinstance(raw.get("attributes"), dict) else {},
            ))

        # Recurse children
        children = raw.get("children", raw.get("nodes", []))
        if isinstance(children, list):
            for i, child in enumerate(children):
                if isinstance(child, dict):
                    child_path = f"{path}/{child.get('tag', 'node')}[{i}]" if path else f"/{child.get('tag', 'node')}[{i}]"
                    nodes.extend(self._extract_nodes(child, depth + 1, child_path))

        return nodes

    def summarize(self, raw_capture: dict[str, Any], token_budget: int = 1500) -> PerceptionView:
        snapshot_id = str(raw_capture.get("snapshot_id", uuid4()))
        raw_nodes = self._extract_nodes(raw_capture)

        # If nodes did not have refs assigned in raw capture, assign stable sequence numbers
        assigned_nodes: list[PerceptionNode] = []
        ref_counter = 1
        ref_map: dict[str, dict[str, Any]] = {}

        for node in raw_nodes:
            ref = node.ref
            if not ref and node.interactive:
                ref = str(ref_counter)
                ref_counter += 1
            node.ref = ref
            assigned_nodes.append(node)
            if ref:
                ref_map[ref] = {
                    "role": node.role,
                    "name": node.name,
                    "value": node.value,
                    "path": node.path,
                    "selector": node.path,
                    "tag": node.tag,
                }

        # Format compact hierarchical view
        lines: list[str] = []
        interactive_count = 0

        # Prioritize interactive and contentful nodes
        for node in assigned_nodes:
            indent = "  " * min(node.depth, 4)
            ref_badge = f"[#{node.ref}] " if node.ref else ""
            val_badge = f' value="{node.value}"' if node.value else ""
            name_label = f'"{node.name}"' if node.name else ""

            if node.interactive:
                interactive_count += 1
                lines.append(f"{indent}- {ref_badge}{node.role} {name_label}{val_badge}".strip())
            elif node.name:
                lines.append(f"{indent}- {node.role}: {name_label}".strip())

        # Check token budget (approximated as 4 chars per token)
        full_text = "\n".join(lines)
        est_tokens = len(full_text) // 4
        truncated = False

        if est_tokens > token_budget and lines:
            truncated = True
            # Binary chop or progressive prune from bottom
            target_char_count = token_budget * 4
            pruned_lines: list[str] = []
            curr_len = 0
            for line in lines:
                if curr_len + len(line) + 1 > target_char_count:
                    break
                pruned_lines.append(line)
                curr_len += len(line) + 1
            pruned_lines.append(f"... [truncated: {len(lines) - len(pruned_lines)} elements omitted to fit token budget]")
            full_text = "\n".join(pruned_lines)
            est_tokens = len(full_text) // 4

        return PerceptionView(
            snapshot_id=snapshot_id,
            view=full_text,
            payload={"refs": ref_map, "total_nodes": len(assigned_nodes)},
            estimated_tokens=est_tokens,
            truncated=truncated,
            node_count=len(assigned_nodes),
            interactive_count=interactive_count,
        )

    def diff(self, view_a: PerceptionView, view_b: PerceptionView) -> dict[str, Any]:
        """Compute structural and element diff between two perception views."""
        refs_a = view_a.payload.get("refs", {})
        refs_b = view_b.payload.get("refs", {})

        keys_a = set(refs_a.keys())
        keys_b = set(refs_b.keys())

        added_refs = keys_b - keys_a
        removed_refs = keys_a - keys_b
        common_refs = keys_a & keys_b

        changed_elements: list[dict[str, Any]] = []
        for ref in common_refs:
            item_a = refs_a[ref]
            item_b = refs_b[ref]
            if item_a != item_b:
                changed_elements.append({
                    "ref": ref,
                    "before": item_a,
                    "after": item_b,
                })

        return {
            "added_count": len(added_refs),
            "removed_count": len(removed_refs),
            "changed_count": len(changed_elements),
            "added": [refs_b[r] for r in sorted(added_refs)],
            "removed": [refs_a[r] for r in sorted(removed_refs)],
            "changed": changed_elements,
        }
