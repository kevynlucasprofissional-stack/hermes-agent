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

        # Check if explicitly hidden (H-102 Red Team guard)
        raw_attrs = raw.get("attributes", {}) if isinstance(raw.get("attributes"), dict) else {}
        node_type = str(raw_attrs.get("type", raw.get("type", ""))).lower()
        is_hidden = (
            raw.get("hidden", False) is True
            or str(raw_attrs.get("aria-hidden", "")).lower() == "true"
            or raw_attrs.get("hidden") is not None
            or node_type == "hidden"
            or "display:none" in str(raw_attrs.get("style", "")).replace(" ", "").lower()
            or "visibility:hidden" in str(raw_attrs.get("style", "")).replace(" ", "").lower()
        )
        if is_hidden:
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
                attributes={k: str(v) for k, v in raw_attrs.items()},
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

        # Classify nodes by importance tiers (H-103 Smart Budgeting)
        # Tier 1 (Must preserve): Actions (buttons, submits) & Inputs (textboxes, selects, forms)
        # Tier 2: Navigation links
        # Tier 3: Static Content
        def format_node_line(node: PerceptionNode) -> str:
            indent = "  " * min(node.depth, 4)
            ref_badge = f"[#{node.ref}] " if node.ref else ""
            val_badge = f' value="{node.value}"' if node.value else ""
            name_label = f'"{node.name}"' if node.name else ""
            if node.interactive:
                return f"{indent}- {ref_badge}{node.role} {name_label}{val_badge}".strip()
            return f"{indent}- {node.role}: {name_label}".strip()

        action_roles = {"button", "tab", "menuitem", "switch"}
        input_roles = {"textbox", "searchbox", "checkbox", "radio", "combobox"}

        tier_actions: list[tuple[int, str]] = []
        tier_nav: list[tuple[int, str]] = []
        tier_content: list[tuple[int, str]] = []

        interactive_count = 0
        for idx, node in enumerate(assigned_nodes):
            if node.interactive:
                interactive_count += 1
            line = format_node_line(node)
            is_action = node.role in action_roles or node.tag in {"button", "select"}
            is_input = node.role in input_roles or node.tag in {"input", "textarea"}
            is_nav = node.role == "link" or node.tag == "a"

            if is_action or is_input:
                tier_actions.append((idx, line))
            elif is_nav:
                tier_nav.append((idx, line))
            else:
                tier_content.append((idx, line))

        # Build initial full view
        all_ordered = [(idx, line) for idx, line in sorted(tier_actions + tier_nav + tier_content, key=lambda x: x[0])]
        full_text = "\n".join(line for _, line in all_ordered)
        est_tokens = len(full_text) // 4
        truncated = False

        if est_tokens > token_budget:
            truncated = True
            char_budget = token_budget * 4

            selected_items: list[tuple[int, str]] = []
            curr_chars = 0

            action_total_chars = sum(len(line) + 1 for _, line in tier_actions)
            if action_total_chars > char_budget:
                for item in tier_actions:
                    if curr_chars + len(item[1]) + 1 <= char_budget:
                        selected_items.append(item)
                        curr_chars += len(item[1]) + 1
                    else:
                        break
            else:
                selected_items = list(tier_actions)
                curr_chars = action_total_chars
                for item in tier_nav:
                    if curr_chars + len(item[1]) + 1 <= char_budget:
                        selected_items.append(item)
                        curr_chars += len(item[1]) + 1

                for item in tier_content:
                    if curr_chars + len(item[1]) + 1 <= char_budget:
                        selected_items.append(item)
                        curr_chars += len(item[1]) + 1

            selected_items.sort(key=lambda x: x[0])
            pruned_lines = [line for _, line in selected_items]
            omitted = len(all_ordered) - len(selected_items)
            if omitted > 0:
                pruned_lines.append(f"... [truncated / smart-budget: {omitted} elements omitted; CTAs/forms prioritized]")

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
