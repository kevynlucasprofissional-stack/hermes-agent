"""Typed Creative operations for safe agent/human co-editing on HyperFrames compositions.

Provides AST/DOM level inspect, add, update, and style operations on native HTML/CSS/JS
HyperFrames projects with ETag concurrency, input sanitization, and owner journaling.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_3d import (
    ThreeJsSceneConfig,
    generate_threejs_canvas_dom,
    inspect_glb_bytes,
)
from workstation.creative_nle import (
    Clip,
    Timeline,
    Track,
    add_nle_clip,
    add_nle_track,
    add_nle_transition,
    delete_nle_clip,
    reorder_nle_clips,
    sanitize_svg_markup,
    sanitize_typography,
    set_clip_audio,
    split_nle_clip,
    trim_nle_clip,
)
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext
from workstation.creative_project_store import (
    CreativeConflictError,
    CreativeProjectRevision,
    load_creative_revision,
    save_creative_revision,
)
from workstation.journal import ExecutionJournal
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine

logger = logging.getLogger(__name__)

CreativeOperationKind = Literal[
    "inspect_project",
    "list_elements",
    "inspect_element",
    "add_element",
    "update_element",
    "set_style",
    "add_3d_canvas",
    "import_3d_asset",
    "update_3d_transform",
    "add_nle_track",
    "add_nle_clip",
    "trim_nle_clip",
    "split_nle_clip",
    "delete_nle_clip",
    "reorder_nle_clips",
    "add_nle_transition",
    "set_nle_audio",
    "add_svg_element",
]

_FORBIDDEN_TAGS = {"script", "iframe", "object", "embed", "frame", "frameset", "applet"}
_FORBIDDEN_ATTR_PATTERNS = [re.compile(r"^on[a-z]+", re.IGNORECASE)]
_FORBIDDEN_URL_SCHEMES = [re.compile(r"^\s*javascript:", re.IGNORECASE), re.compile(r"^\s*data:\s*text/html", re.IGNORECASE)]


@dataclass
class DOMElement:
    """Lightweight DOM tree node for HTML composition AST operations."""
    tag: str
    attrs: Dict[str, str]
    text: str = ""
    tail: str = ""
    children: List[DOMElement] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    @property
    def hf_id(self) -> Optional[str]:
        return self.attrs.get("data-hf-id") or self.attrs.get("id")


class _HTMLTreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = DOMElement("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k: v or "" for k, v in attrs}
        node = DOMElement(tag=tag.lower(), attrs=attr_dict)
        self.stack[-1].children.append(node)
        # Handle void/self-closing elements
        if tag.lower() not in {"meta", "link", "img", "br", "hr", "input", "source"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str):
        if len(self.stack) > 1 and self.stack[-1].tag == tag.lower():
            self.stack.pop()

    def handle_data(self, data: str):
        if self.stack[-1].children:
            self.stack[-1].children[-1].tail += data
        else:
            self.stack[-1].text += data


def parse_html_tree(html_content: str) -> DOMElement:
    """Parse HTML string into DOMElement tree."""
    parser = _HTMLTreeBuilder()
    parser.feed(html_content)
    return parser.root


def render_html_tree(node: DOMElement) -> str:
    """Serialize DOMElement tree back to HTML string."""
    if node.tag == "root":
        return "".join(render_html_tree(child) for child in node.children)

    attrs_str = ""
    if node.attrs:
        attrs_str = " " + " ".join(f'{k}="{v}"' if v else k for k, v in sorted(node.attrs.items()))

    # Void/self-closing tags
    if node.tag in {"meta", "link", "img", "br", "hr", "input", "source"}:
        return f"<{node.tag}{attrs_str}>{node.tail}"

    children_str = "".join(render_html_tree(child) for child in node.children)
    return f"<{node.tag}{attrs_str}>{node.text}{children_str}</{node.tag}>{node.tail}"


def find_element_by_id(root: DOMElement, element_id: str) -> Optional[DOMElement]:
    """Find a DOM element matching data-hf-id or id."""
    for child in root.children:
        if child.hf_id == element_id:
            return child
        found = find_element_by_id(child, element_id)
        if found is not None:
            return found
    return None


def remove_element_by_id(root: DOMElement, element_id: str) -> bool:
    """Remove a DOM element matching data-hf-id or id from the tree."""
    for i, child in enumerate(root.children):
        if child.hf_id == element_id:
            root.children.pop(i)
            return True
        if remove_element_by_id(child, element_id):
            return True
    return False


def _find_parent_element(root: DOMElement, target: DOMElement) -> Optional[DOMElement]:
    """Find the parent node containing the target DOMElement."""
    for child in root.children:
        if child is target:
            return root
        found = _find_parent_element(child, target)
        if found is not None:
            return found
    return None


def _build_clip_dom_node(clip: Clip) -> DOMElement:
    """Construct a DOMElement representation of an NLE clip."""
    attrs: Dict[str, str] = {
        "id": clip.clip_id,
        "data-hf-id": clip.clip_id,
        "data-hf-clip": clip.clip_id,
        "data-hf-track": clip.track_id,
        "data-start": str(round(clip.start_time, 3)),
        "data-end": str(round(clip.end_time, 3)),
    }
    if clip.source_path:
        attrs["data-hf-source"] = clip.source_path

    if clip.vector_svg:
        clean_svg = sanitize_svg_markup(clip.vector_svg)
        parsed_svg = parse_html_tree(clean_svg)
        svg_root = next((c for c in parsed_svg.children if c.tag == "svg"), None)
        if svg_root is not None:
            svg_root.attrs.update(attrs)
            cls_name = f"{svg_root.attrs.get('class', '')} hf-clip hf-clip-vector".strip()
            svg_root.attrs["class"] = cls_name
            return svg_root

    tag = "div"
    classes = ["hf-clip"]
    style_parts = []

    if clip.text_content is not None:
        classes.append("hf-clip-text")
        if clip.typography:
            for k, v in clip.typography.items():
                css_prop = k.replace("_", "-")
                style_parts.append(f"{css_prop}: {v}")

    if clip.volume != 1.0 or clip.muted:
        attrs["data-volume"] = str(clip.volume)
        attrs["data-muted"] = str(clip.muted).lower()

    if style_parts:
        attrs["style"] = "; ".join(style_parts)

    attrs["class"] = " ".join(classes)
    return DOMElement(tag=tag, attrs=attrs, text=clip.text_content or "")


def sanitize_attributes(attrs: Dict[str, str]) -> Dict[str, str]:
    """Ensure attributes contain no event handlers or javascript: URLs."""
    sanitized: Dict[str, str] = {}
    for k, v in attrs.items():
        key = k.strip().lower()
        for forbidden in _FORBIDDEN_ATTR_PATTERNS:
            if forbidden.match(key):
                raise ValueError(f"Executable attribute '{key}' is forbidden in Creative compositions")
        val = str(v)
        for scheme in _FORBIDDEN_URL_SCHEMES:
            if scheme.match(val):
                raise ValueError(f"Dangerous URL scheme in attribute '{key}' is forbidden")
        sanitized[k] = val
    return sanitized


def sanitize_styles(styles: Dict[str, str]) -> Dict[str, str]:
    """Validate CSS property names and values, rejecting expressions and URLs with javascript."""
    clean: Dict[str, str] = {}
    for prop, val in styles.items():
        if not re.fullmatch(r"[a-zA-Z\-]+", prop.strip()):
            raise ValueError(f"Invalid CSS property name: {prop}")
        val_str = str(val).strip()
        if "javascript:" in val_str.lower() or "expression(" in val_str.lower():
            raise ValueError(f"Dangerous expression in CSS style value for property {prop}")
        clean[prop.strip()] = val_str
    return clean


def parse_inline_styles(style_str: str) -> Dict[str, str]:
    """Parse inline CSS style attribute into dictionary."""
    styles: Dict[str, str] = {}
    for item in style_str.split(";"):
        if ":" in item:
            prop, val = item.split(":", 1)
            styles[prop.strip()] = val.strip()
    return styles


def format_inline_styles(styles: Dict[str, str]) -> str:
    """Format dictionary into inline CSS style attribute string."""
    return "; ".join(f"{k}: {v}" for k, v in sorted(styles.items()))


@dataclass(frozen=True)
class CreativeOperation:
    """Typed creative edit operation."""
    kind: CreativeOperationKind
    project_id: str
    parent_revision_id: str
    params: Dict[str, Any]
    operation_id: Optional[str] = None
    if_match: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "project_id": self.project_id,
            "parent_revision_id": self.parent_revision_id,
            "params": self.params,
            "operation_id": self.operation_id,
            "if_match": self.if_match,
        }


def inspect_project(revision: CreativeProjectRevision) -> Dict[str, Any]:
    """Read project metadata and element overview."""
    project_dir = revision.manifest_path.parent
    html_path = project_dir / "index.html"
    json_path = project_dir / "hyperframes.json"

    meta: Dict[str, Any] = {}
    if json_path.is_file():
        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    elements: List[Dict[str, Any]] = []
    if html_path.is_file():
        root = parse_html_tree(html_path.read_text(encoding="utf-8"))
        elements = _extract_element_list(root)

    return {
        "project_id": revision.project_id,
        "revision_id": revision.revision_id,
        "engine": revision.engine,
        "etag": revision.etag,
        "metadata": meta,
        "element_count": len(elements),
        "elements": elements,
    }


def _extract_element_list(node: DOMElement) -> List[Dict[str, Any]]:
    result = []
    if node.tag not in {"root", "html", "head", "meta", "title", "link", "style"}:
        result.append({
            "id": node.hf_id,
            "tag": node.tag,
            "text": node.text.strip(),
            "classes": node.attrs.get("class", "").split(),
            "style": node.attrs.get("style", ""),
        })
    for child in node.children:
        result.extend(_extract_element_list(child))
    return result


def apply_creative_operation(
    config: WorkstationConfig,
    context: CreativeRunContext,
    operation: CreativeOperation,
) -> Tuple[CreativeProjectRevision, Dict[str, Any]]:
    """Execute a typed CreativeOperation atomically with ETag validation and journaling."""
    workspace = context.validate(config)
    op_id = operation.operation_id or uuid4().hex

    policy = ScopedPolicyEngine().evaluate(ActionScope(
        task_id=context.task_id,
        session_id=context.session_id,
        capability="creative_edit",
        action_name=operation.kind,
        target=operation.project_id,
        workspace_root=str(workspace),
    ))
    if policy.decision is not PolicyDecision.ALLOW:
        raise PermissionError(f"Creative operation denied by policy: {policy.decision.value}")

    parent_rev = load_creative_revision(operation.project_id, operation.parent_revision_id)
    if parent_rev.engine != "hyperframes":
        raise ValueError(f"Operation requires HyperFrames project engine, got {parent_rev.engine}")

    # Check ETag optimistic concurrency
    if operation.if_match is not None and operation.if_match != parent_rev.etag:
        raise CreativeConflictError(f"409 Conflict: ETag mismatch. Expected {parent_rev.etag}, got {operation.if_match}")

    project_dir = parent_rev.manifest_path.parent
    html_file = project_dir / "index.html"
    json_file = project_dir / "hyperframes.json"

    if not html_file.is_file() or not json_file.is_file():
        raise ValueError("Corrupt HyperFrames project: missing index.html or hyperframes.json")

    html_text = html_file.read_text(encoding="utf-8")
    json_meta = json.loads(json_file.read_text(encoding="utf-8"))

    root = parse_html_tree(html_text)
    op_result_details: Dict[str, Any] = {}

    if operation.kind == "add_element":
        tag = operation.params.get("tag", "div").lower().strip()
        if tag in _FORBIDDEN_TAGS:
            raise ValueError(f"Tag <{tag}> is forbidden in Creative compositions")
        element_id = operation.params.get("element_id") or f"hf-{uuid4().hex[:8]}"
        text = str(operation.params.get("text") or "")
        attrs = sanitize_attributes(dict(operation.params.get("attributes") or {}))
        attrs["data-hf-id"] = element_id

        styles = sanitize_styles(dict(operation.params.get("styles") or {}))
        if styles:
            existing_styles = parse_inline_styles(attrs.get("style", ""))
            existing_styles.update(styles)
            attrs["style"] = format_inline_styles(existing_styles)

        new_node = DOMElement(tag=tag, attrs=attrs, text=text)
        parent_id = operation.params.get("parent_id")
        target_parent = find_element_by_id(root, parent_id) if parent_id else None
        if target_parent is None:
            # Fall back to <body> if present, or root
            body = next((c for c in root.children if c.tag == "html"), root)
            body = next((c for c in body.children if c.tag == "body"), body)
            target_parent = body

        target_parent.children.append(new_node)
        op_result_details = {"added_element_id": element_id, "tag": tag}

    elif operation.kind == "update_element":
        element_id = str(operation.params.get("element_id") or "")
        target = find_element_by_id(root, element_id)
        if target is None:
            raise ValueError(f"Element '{element_id}' not found in composition")

        if "text" in operation.params:
            target.text = str(operation.params["text"])

        if "attributes" in operation.params:
            clean_attrs = sanitize_attributes(dict(operation.params["attributes"]))
            target.attrs.update(clean_attrs)

        op_result_details = {"updated_element_id": element_id}

    elif operation.kind == "set_style":
        element_id = str(operation.params.get("element_id") or "")
        target = find_element_by_id(root, element_id)
        if target is None:
            raise ValueError(f"Element '{element_id}' not found in composition")

        new_styles = sanitize_styles(dict(operation.params.get("styles") or {}))
        existing = parse_inline_styles(target.attrs.get("style", ""))
        existing.update(new_styles)
        target.attrs["style"] = format_inline_styles(existing)

        op_result_details = {"styled_element_id": element_id, "applied_styles": new_styles}

    elif operation.kind == "add_3d_canvas":
        canvas_id = str(operation.params.get("canvas_id") or f"hf-3d-{uuid4().hex[:8]}")
        width = int(operation.params.get("width", 1280))
        height = int(operation.params.get("height", 720))
        bg_color = str(operation.params.get("background_color", "#0f172a"))
        model_asset = operation.params.get("model_asset")
        active_anim = operation.params.get("active_animation")

        camera_params = operation.params.get("camera") or {}
        lights_params = operation.params.get("lights") or {}
        transform_params = operation.params.get("transform") or {}

        cfg = ThreeJsSceneConfig(
            canvas_id=canvas_id,
            width=width,
            height=height,
            background_color=bg_color,
            camera_fov=float(camera_params.get("fov", 60.0)),
            camera_near=float(camera_params.get("near", 0.1)),
            camera_far=float(camera_params.get("far", 1000.0)),
            camera_position=tuple(camera_params.get("position", [0.0, 1.5, 3.0])),
            camera_target=tuple(camera_params.get("target", [0.0, 0.0, 0.0])),
            ambient_light_color=str(lights_params.get("ambient_color", "#ffffff")),
            ambient_light_intensity=float(lights_params.get("ambient_intensity", 0.7)),
            directional_light_color=str(lights_params.get("directional_color", "#ffffff")),
            directional_light_intensity=float(lights_params.get("directional_intensity", 1.0)),
            directional_light_position=tuple(lights_params.get("directional_position", [5.0, 10.0, 7.5])),
            model_asset=model_asset,
            active_animation=active_anim,
            model_position=tuple(transform_params.get("position", [0.0, 0.0, 0.0])),
            model_rotation=tuple(transform_params.get("rotation", [0.0, 0.0, 0.0])),
            model_scale=tuple(transform_params.get("scale", [1.0, 1.0, 1.0])),
        )

        canvas_node = generate_threejs_canvas_dom(cfg)
        parent_id = operation.params.get("parent_id")
        target_parent = find_element_by_id(root, parent_id) if parent_id else None
        if target_parent is None:
            body = next((c for c in root.children if c.tag == "html"), root)
            body = next((c for c in body.children if c.tag == "body"), body)
            target_parent = body

        target_parent.children.append(canvas_node)

        scenes_meta = json_meta.setdefault("scenes_3d", {})
        scenes_meta[canvas_id] = cfg.to_dict()

        op_result_details = {"added_canvas_id": canvas_id, "scene": cfg.to_dict()}

    elif operation.kind == "import_3d_asset":
        asset_name = str(operation.params.get("asset_name") or "model.glb").strip()
        data_bytes = operation.params.get("data_bytes")
        if data_bytes is None and "data_base64" in operation.params:
            try:
                data_bytes = base64.b64decode(operation.params["data_base64"])
            except Exception as exc:
                raise ValueError(f"Invalid base64 payload for 3D asset: {exc}") from exc

        if not isinstance(data_bytes, (bytes, bytearray)):
            raise ValueError("3D asset import requires valid data_bytes or data_base64")

        meta_receipt = inspect_glb_bytes(data_bytes, asset_name=asset_name)

        clean_filename = Path(asset_name).name
        if not clean_filename.endswith(".glb") and not clean_filename.endswith(".gltf"):
            clean_filename = f"{clean_filename}.glb"
        rel_asset_path = f"assets/{clean_filename}"

        assets_3d = json_meta.setdefault("assets_3d", {})
        assets_3d[rel_asset_path] = meta_receipt.to_dict()

        target_canvas_id = operation.params.get("canvas_id")
        if target_canvas_id:
            canvas_elem = find_element_by_id(root, target_canvas_id)
            if canvas_elem is not None:
                canvas_elem.attrs["data-hf-model"] = rel_asset_path
            if target_canvas_id in json_meta.get("scenes_3d", {}):
                json_meta["scenes_3d"][target_canvas_id]["model_asset"] = rel_asset_path

        new_native_asset_files = {rel_asset_path: bytes(data_bytes)}
        op_result_details = {
            "imported_asset": rel_asset_path,
            "metadata": meta_receipt.to_dict(),
            "bound_to_canvas": target_canvas_id,
        }

    elif operation.kind == "update_3d_transform":
        canvas_id = str(operation.params.get("canvas_id") or "")
        scenes = json_meta.get("scenes_3d", {})
        if canvas_id not in scenes:
            raise ValueError(f"3D Scene for canvas '{canvas_id}' not found in metadata")

        scene_cfg = scenes[canvas_id]
        transform = scene_cfg.setdefault("transform", {})

        if "position" in operation.params:
            transform["position"] = list(operation.params["position"])
        if "rotation" in operation.params:
            transform["rotation"] = list(operation.params["rotation"])
        if "scale" in operation.params:
            transform["scale"] = list(operation.params["scale"])

        if "active_animation" in operation.params:
            new_anim = str(operation.params["active_animation"])
            scene_cfg["active_animation"] = new_anim
            canvas_elem = find_element_by_id(root, canvas_id)
            if canvas_elem is not None:
                canvas_elem.attrs["data-hf-anim"] = new_anim

        op_result_details = {
            "updated_canvas_id": canvas_id,
            "transform": transform,
            "active_animation": scene_cfg.get("active_animation"),
        }

    elif operation.kind == "add_nle_track":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline(
            duration=float(json_meta.get("duration", 10.0)),
            fps=int(json_meta.get("fps", 30)),
            width=int(json_meta.get("width", 1920)),
            height=int(json_meta.get("height", 1080)),
        )
        track_id = str(operation.params.get("track_id") or f"track_{uuid4().hex[:6]}")
        track_type = operation.params.get("track_type", "video")
        name = str(operation.params.get("name") or track_id)
        track = add_nle_track(timeline, track_id=track_id, track_type=track_type, name=name)

        body = next((c for c in root.children if c.tag == "html"), root)
        body = next((c for c in body.children if c.tag == "body"), body)
        track_node = DOMElement(
            tag="div",
            attrs={
                "id": track_id,
                "data-hf-id": track_id,
                "data-hf-track": track_id,
                "class": f"hf-track hf-track-{track_type}",
            },
        )
        body.children.append(track_node)
        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {"added_track": track.to_dict()}

    elif operation.kind == "add_nle_clip":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline(
            duration=float(json_meta.get("duration", 10.0)),
            fps=int(json_meta.get("fps", 30)),
            width=int(json_meta.get("width", 1920)),
            height=int(json_meta.get("height", 1080)),
        )
        track_id = str(operation.params.get("track_id") or "")
        clip_id = str(operation.params.get("clip_id") or f"clip_{uuid4().hex[:8]}")
        start_time = float(operation.params.get("start_time", 0.0))
        end_time = float(operation.params.get("end_time", start_time + 5.0))
        source_path = operation.params.get("source_path")
        in_point = float(operation.params.get("in_point", 0.0))
        out_point = float(operation.params.get("out_point", end_time - start_time))
        volume = float(operation.params.get("volume", 1.0))
        muted = bool(operation.params.get("muted", False))
        text_content = operation.params.get("text_content")
        typography = sanitize_typography(operation.params.get("typography") or {}) if operation.params.get("typography") else None
        vector_svg = sanitize_svg_markup(operation.params["vector_svg"]) if operation.params.get("vector_svg") else None
        transform = operation.params.get("transform")
        keyframes = operation.params.get("keyframes")

        clip = Clip(
            clip_id=clip_id,
            track_id=track_id,
            start_time=start_time,
            end_time=end_time,
            source_path=source_path,
            in_point=in_point,
            out_point=out_point,
            volume=volume,
            muted=muted,
            text_content=text_content,
            typography=typography,
            vector_svg=vector_svg,
            transform=transform,
            keyframes=keyframes,
        )
        add_nle_clip(timeline, track_id, clip)

        clip_node = _build_clip_dom_node(clip)
        track_node = find_element_by_id(root, track_id)
        if track_node is not None:
            track_node.children.append(clip_node)
        else:
            body = next((c for c in root.children if c.tag == "html"), root)
            body = next((c for c in body.children if c.tag == "body"), body)
            body.children.append(clip_node)

        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {"added_clip": clip.to_dict()}

    elif operation.kind == "trim_nle_clip":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        clip_id = str(operation.params.get("clip_id") or "")
        start_time = float(operation.params.get("start_time", 0.0))
        end_time = float(operation.params.get("end_time", 0.0))
        ripple = bool(operation.params.get("ripple", False))

        trimmed_clip = trim_nle_clip(timeline, clip_id, start_time, end_time, ripple=ripple)

        clip_node = find_element_by_id(root, clip_id)
        if clip_node is not None:
            clip_node.attrs["data-start"] = str(round(trimmed_clip.start_time, 3))
            clip_node.attrs["data-end"] = str(round(trimmed_clip.end_time, 3))

        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "trimmed_clip": trimmed_clip.to_dict(),
            "timeline_duration": timeline.duration,
        }

    elif operation.kind == "split_nle_clip":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        clip_id = str(operation.params.get("clip_id") or "")
        split_time = float(operation.params.get("split_time", 0.0))

        clip_a, clip_b = split_nle_clip(timeline, clip_id, split_time)

        node_a = find_element_by_id(root, clip_id)
        if node_a is not None:
            node_a.attrs["data-end"] = str(round(clip_a.end_time, 3))
            node_b = _build_clip_dom_node(clip_b)
            parent = _find_parent_element(root, node_a)
            if parent is not None:
                idx = parent.children.index(node_a)
                parent.children.insert(idx + 1, node_b)

        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "clip_a": clip_a.to_dict(),
            "clip_b": clip_b.to_dict(),
        }

    elif operation.kind == "delete_nle_clip":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        clip_id = str(operation.params.get("clip_id") or "")
        ripple = bool(operation.params.get("ripple", False))

        delete_nle_clip(timeline, clip_id, ripple=ripple)
        remove_element_by_id(root, clip_id)

        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "deleted_clip_id": clip_id,
            "timeline_duration": timeline.duration,
        }

    elif operation.kind == "reorder_nle_clips":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        track_id = str(operation.params.get("track_id") or "")
        clip_ids = list(operation.params.get("clip_ids") or [])

        reordered = reorder_nle_clips(timeline, track_id, clip_ids)
        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "track_id": track_id,
            "reordered_clips": [c.to_dict() for c in reordered],
        }

    elif operation.kind == "add_nle_transition":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        clip_a_id = str(operation.params.get("clip_a_id") or "")
        clip_b_id = str(operation.params.get("clip_b_id") or "")
        trans_type = str(operation.params.get("transition_type") or "crossfade")
        dur = float(operation.params.get("duration", 0.5))

        clip_a, clip_b = add_nle_transition(timeline, clip_a_id, clip_b_id, trans_type, dur)
        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "clip_a_transition_out": clip_a.transition_out,
            "clip_b_transition_in": clip_b.transition_in,
        }

    elif operation.kind == "set_nle_audio":
        timeline_dict = json_meta.get("timeline")
        timeline = Timeline.from_dict(timeline_dict) if isinstance(timeline_dict, dict) else Timeline()
        clip_id = str(operation.params.get("clip_id") or "")
        vol = float(operation.params.get("volume", 1.0))
        muted = bool(operation.params.get("muted", False))

        clip = set_clip_audio(timeline, clip_id, vol, muted)
        clip_node = find_element_by_id(root, clip_id)
        if clip_node is not None:
            clip_node.attrs["data-volume"] = str(clip.volume)
            clip_node.attrs["data-muted"] = str(clip.muted).lower()

        json_meta["timeline"] = timeline.to_dict()
        op_result_details = {
            "clip_id": clip_id,
            "volume": clip.volume,
            "muted": clip.muted,
        }

    elif operation.kind == "add_svg_element":
        svg_markup = str(operation.params.get("svg_markup") or "")
        clean_svg = sanitize_svg_markup(svg_markup)
        elem_id = str(operation.params.get("element_id") or f"hf-svg-{uuid4().hex[:8]}")

        parsed = parse_html_tree(clean_svg)
        svg_node = next((c for c in parsed.children if c.tag == "svg"), None)
        if svg_node is None:
            raise ValueError("Invalid SVG markup: missing <svg> element")

        svg_node.attrs["data-hf-id"] = elem_id
        if "id" not in svg_node.attrs:
            svg_node.attrs["id"] = elem_id

        parent_id = operation.params.get("parent_id")
        target_parent = find_element_by_id(root, parent_id) if parent_id else None
        if target_parent is None:
            body = next((c for c in root.children if c.tag == "html"), root)
            body = next((c for c in body.children if c.tag == "body"), body)
            target_parent = body

        target_parent.children.append(svg_node)
        op_result_details = {"added_svg_id": elem_id}

    else:
        raise ValueError(f"Unsupported modification operation: {operation.kind}")

    updated_html = render_html_tree(root)
    updated_native_files = {
        "index.html": updated_html.encode("utf-8"),
        "hyperframes.json": json.dumps(json_meta, indent=2).encode("utf-8"),
    }
    # Preserve other existing native files if present (including nested paths)
    for item in parent_rev.manifest_path.parent.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(parent_rev.manifest_path.parent).as_posix()
            if rel_path not in {"manifest.json", "source.creative.json", "index.html", "hyperframes.json"}:
                updated_native_files[rel_path] = item.read_bytes()

    if "new_native_asset_files" in locals():
        updated_native_files.update(new_native_asset_files)

    try:
        new_rev = save_creative_revision(
            json_meta,
            project_id=parent_rev.project_id,
            parent_revision=parent_rev.revision_id,
            operation_id=op_id,
            engine="hyperframes",
            native_files=updated_native_files,
            if_match=parent_rev.etag,
        )
    except Exception as error:
        raise CreativeEffectUncertain(op_id) from error

    journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
    journal.record(
        ExecutionEventKind.ACTION,
        f"Creative operation applied: {operation.kind}",
        metadata={
            "operation_id": op_id,
            "project_id": new_rev.project_id,
            "parent_revision_id": parent_rev.revision_id,
            "new_revision_id": new_rev.revision_id,
            "new_etag": new_rev.etag,
            "details": op_result_details,
        },
    )

    return new_rev, op_result_details
