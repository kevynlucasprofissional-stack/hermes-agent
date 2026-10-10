"""Unified Command Bus and typed reducers for Creative Document co-editing (CWN-02)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from fractions import Fraction
import time
from typing import Any, Callable, Literal

from workstation.creative_document import (
    Asset,
    Clip,
    Composition,
    CreativeDocument,
    CreativeDocumentError,
    Keyframe,
    Layer,
    Track,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange

ActorType = Literal["human_mouse", "hermes_agent", "headless_automation"]


@dataclass(frozen=True)
class Actor:
    actor_id: str
    actor_type: ActorType


@dataclass
class CreativeCommand:
    command_id: str
    params: dict[str, Any]
    actor: Actor
    idempotency_key: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class CommandResult:
    success: bool
    inverse_command: CreativeCommand | None = None
    error_message: str | None = None


class CommandError(ValueError):
    """Raised when command validation or execution fails."""
    pass


class CommandRegistry:
    """Registry of typed command handlers and inverse generators."""

    def __init__(self):
        self._handlers: dict[str, Callable[[CreativeDocument, CreativeCommand], CommandResult]] = {}
        self._register_default_handlers()

    def register(self, command_id: str, handler: Callable[[CreativeDocument, CreativeCommand], CommandResult]) -> None:
        self._handlers[command_id] = handler

    def execute(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        if cmd.command_id not in self._handlers:
            raise CommandError(f"Unknown command_id: '{cmd.command_id}'")
        return self._handlers[cmd.command_id](doc, cmd)

    def _register_default_handlers(self) -> None:
        self.register("track.add", self._handle_track_add)
        self.register("track.remove", self._handle_track_remove)
        self.register("clip.add", self._handle_clip_add)
        self.register("clip.remove", self._handle_clip_remove)
        self.register("layer.create", self._handle_layer_create)
        self.register("layer.remove", self._handle_layer_remove)
        self.register("layer.setProperty", self._handle_layer_set_property)
        self.register("keyframe.set", self._handle_keyframe_set)
        self.register("keyframe.remove", self._handle_keyframe_remove)
        self.register("asset.import", self._handle_asset_import)
        self.register("asset.remove", self._handle_asset_remove)
        self.register("clip.split", self._handle_clip_split)
        self.register("clip.trim", self._handle_clip_trim)
        self.register("clip.rippleDelete", self._handle_clip_ripple_delete)
        self.register("clip.slip", self._handle_clip_slip)
        self.register("clip.slide", self._handle_clip_slide)
        self.register("clip.roll", self._handle_clip_roll)
        self.register("clip.setSpeed", self._handle_clip_set_speed)
        self.register("timeline.restoreTracks", self._handle_timeline_restore_tracks)

    # --- Handlers ---

    def _find_comp(self, doc: CreativeDocument, comp_id: str | None) -> Composition:
        if not doc.compositions:
            raise CommandError("Document has no compositions")
        if comp_id is None:
            return doc.compositions[0]
        for c in doc.compositions:
            if c.composition_id == comp_id:
                return c
        raise CommandError(f"Composition not found: {comp_id}")

    def _handle_track_add(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        track_id = cmd.params["track_id"]
        if any(t.track_id == track_id for t in comp.tracks):
            raise CommandError(f"Track with ID {track_id} already exists")

        track = Track(
            track_id=track_id,
            name=cmd.params.get("name", "New Track"),
            kind=cmd.params.get("kind", "video"),
            z_index=int(cmd.params.get("z_index", len(comp.tracks))),
            locked=bool(cmd.params.get("locked", False)),
            muted=bool(cmd.params.get("muted", False)),
            solo=bool(cmd.params.get("solo", False)),
        )
        comp.tracks.append(track)

        inverse = CreativeCommand(
            command_id="track.remove",
            params={"composition_id": comp.composition_id, "track_id": track_id},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_track_remove(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        track_id = cmd.params["track_id"]
        idx = next((i for i, t in enumerate(comp.tracks) if t.track_id == track_id), None)
        if idx is None:
            raise CommandError(f"Track not found: {track_id}")

        old_track = comp.tracks.pop(idx)
        inverse = CreativeCommand(
            command_id="track.add",
            params={
                "composition_id": comp.composition_id,
                "track_id": old_track.track_id,
                "name": old_track.name,
                "kind": old_track.kind,
                "z_index": old_track.z_index,
                "locked": old_track.locked,
                "muted": old_track.muted,
                "solo": old_track.solo,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_add(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        track_id = cmd.params["track_id"]
        track = next((t for t in comp.tracks if t.track_id == track_id), None)
        if track is None:
            raise CommandError(f"Track not found for clip: {track_id}")

        clip_id = cmd.params["clip_id"]
        asset_id = cmd.params["asset_id"]

        tr = cmd.params.get("timeline_range", {"start": "0", "end": "5"})
        t_range = TimeRange(
            CanonicalTime.from_seconds(Fraction(tr["start"])),
            CanonicalTime.from_seconds(Fraction(tr["end"])),
        )
        source_in = CanonicalTime.from_seconds(Fraction(cmd.params.get("source_in", "0")))

        clip = Clip(
            clip_id=clip_id,
            track_id=track_id,
            asset_id=asset_id,
            name=cmd.params.get("name", "New Clip"),
            timeline_range=t_range,
            source_in=source_in,
            speed=float(cmd.params.get("speed", 1.0)),
            reverse=bool(cmd.params.get("reverse", False)),
            freeze=bool(cmd.params.get("freeze", False)),
            linked_clip_ids=list(cmd.params.get("linked_clip_ids", [])),
            properties=dict(cmd.params.get("properties", {})),
        )
        track.clips.append(clip)

        inverse = CreativeCommand(
            command_id="clip.remove",
            params={"composition_id": comp.composition_id, "track_id": track_id, "clip_id": clip_id},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_remove(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        track_id = cmd.params["track_id"]
        track = next((t for t in comp.tracks if t.track_id == track_id), None)
        if track is None:
            raise CommandError(f"Track not found: {track_id}")

        clip_id = cmd.params["clip_id"]
        idx = next((i for i, c in enumerate(track.clips) if c.clip_id == clip_id), None)
        if idx is None:
            raise CommandError(f"Clip not found: {clip_id}")

        old_clip = track.clips.pop(idx)
        inverse = CreativeCommand(
            command_id="clip.add",
            params={
                "composition_id": comp.composition_id,
                "track_id": track_id,
                "clip_id": old_clip.clip_id,
                "asset_id": old_clip.asset_id,
                "name": old_clip.name,
                "timeline_range": {
                    "start": str(old_clip.timeline_range.start.to_seconds()),
                    "end": str(old_clip.timeline_range.end.to_seconds()),
                },
                "source_in": str(old_clip.source_in.to_seconds()),
                "speed": old_clip.speed,
                "reverse": old_clip.reverse,
                "freeze": old_clip.freeze,
                "linked_clip_ids": old_clip.linked_clip_ids,
                "properties": old_clip.properties,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_layer_create(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        layer_id = cmd.params["layer_id"]
        if any(l.layer_id == layer_id for l in comp.layers):
            raise CommandError(f"Layer with ID {layer_id} already exists")

        layer = Layer(
            layer_id=layer_id,
            name=cmd.params.get("name", "New Layer"),
            kind=cmd.params.get("kind", "vector_svg"),
            declared_parameters=dict(cmd.params.get("declared_parameters", {})),
            opaque_code=cmd.params.get("opaque_code"),
            transform=dict(cmd.params.get("transform", {"x": 0.0, "y": 0.0, "opacity": 1.0})),
        )
        comp.layers.append(layer)

        inverse = CreativeCommand(
            command_id="layer.remove",
            params={"composition_id": comp.composition_id, "layer_id": layer_id},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_layer_remove(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        layer_id = cmd.params["layer_id"]
        idx = next((i for i, l in enumerate(comp.layers) if l.layer_id == layer_id), None)
        if idx is None:
            raise CommandError(f"Layer not found: {layer_id}")

        old_layer = comp.layers.pop(idx)
        inverse = CreativeCommand(
            command_id="layer.create",
            params={
                "composition_id": comp.composition_id,
                "layer_id": old_layer.layer_id,
                "name": old_layer.name,
                "kind": old_layer.kind,
                "declared_parameters": old_layer.declared_parameters,
                "opaque_code": old_layer.opaque_code,
                "transform": old_layer.transform,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_layer_set_property(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        layer_id = cmd.params["layer_id"]
        layer = next((l for l in comp.layers if l.layer_id == layer_id), None)
        if layer is None:
            raise CommandError(f"Layer not found: {layer_id}")

        prop_path = cmd.params["property_path"]
        new_value = cmd.params["value"]

        # Supported paths: transform.<key> or declared_parameters.<key>
        if prop_path.startswith("transform."):
            key = prop_path.split(".", 1)[1]
            old_value = layer.transform.get(key)
            layer.transform[key] = new_value
        elif prop_path.startswith("declared_parameters."):
            key = prop_path.split(".", 1)[1]
            old_value = layer.declared_parameters.get(key)
            layer.declared_parameters[key] = new_value
        else:
            raise CommandError(f"Unsupported property_path: {prop_path}")

        inverse = CreativeCommand(
            command_id="layer.setProperty",
            params={
                "composition_id": comp.composition_id,
                "layer_id": layer_id,
                "property_path": prop_path,
                "value": old_value,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_keyframe_set(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        layer_id = cmd.params["layer_id"]
        layer = next((l for l in comp.layers if l.layer_id == layer_id), None)
        if layer is None:
            raise CommandError(f"Layer not found: {layer_id}")

        kf_id = cmd.params["keyframe_id"]
        prop_path = cmd.params["property_path"]
        t = CanonicalTime.from_seconds(Fraction(cmd.params["time"]))
        val = cmd.params["value"]
        easing = cmd.params.get("easing", "linear")

        existing_kf = next((k for k in layer.keyframes if k.keyframe_id == kf_id), None)
        if existing_kf:
            old_val = existing_kf.value
            old_time = str(existing_kf.time.to_seconds())
            old_easing = existing_kf.easing
            existing_kf.value = val
            existing_kf.time = t
            existing_kf.easing = easing
            inverse = CreativeCommand(
                command_id="keyframe.set",
                params={
                    "composition_id": comp.composition_id,
                    "layer_id": layer_id,
                    "keyframe_id": kf_id,
                    "property_path": prop_path,
                    "time": old_time,
                    "value": old_val,
                    "easing": old_easing,
                },
                actor=cmd.actor,
                idempotency_key=f"inv_{cmd.idempotency_key}",
            )
        else:
            new_kf = Keyframe(
                keyframe_id=kf_id,
                property_path=prop_path,
                time=t,
                value=val,
                easing=easing,
            )
            layer.keyframes.append(new_kf)
            inverse = CreativeCommand(
                command_id="keyframe.remove",
                params={"composition_id": comp.composition_id, "layer_id": layer_id, "keyframe_id": kf_id},
                actor=cmd.actor,
                idempotency_key=f"inv_{cmd.idempotency_key}",
            )

        return CommandResult(success=True, inverse_command=inverse)

    def _handle_keyframe_remove(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        layer_id = cmd.params["layer_id"]
        layer = next((l for l in comp.layers if l.layer_id == layer_id), None)
        if layer is None:
            raise CommandError(f"Layer not found: {layer_id}")

        kf_id = cmd.params["keyframe_id"]
        idx = next((i for i, k in enumerate(layer.keyframes) if k.keyframe_id == kf_id), None)
        if idx is None:
            raise CommandError(f"Keyframe not found: {kf_id}")

        old_kf = layer.keyframes.pop(idx)
        inverse = CreativeCommand(
            command_id="keyframe.set",
            params={
                "composition_id": comp.composition_id,
                "layer_id": layer_id,
                "keyframe_id": old_kf.keyframe_id,
                "property_path": old_kf.property_path,
                "time": str(old_kf.time.to_seconds()),
                "value": old_kf.value,
                "easing": old_kf.easing,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_asset_import(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        asset_id = cmd.params["asset_id"]
        if asset_id in doc.assets:
            raise CommandError(f"Asset already exists: {asset_id}")

        asset = Asset(
            asset_id=asset_id,
            name=cmd.params.get("name", "Asset"),
            kind=cmd.params.get("kind", "video"),
            path=cmd.params.get("path", ""),
            sha256=cmd.params["sha256"],
            width=cmd.params.get("width"),
            height=cmd.params.get("height"),
        )
        doc.assets[asset_id] = asset

        inverse = CreativeCommand(
            command_id="asset.remove",
            params={"asset_id": asset_id},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_asset_remove(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        asset_id = cmd.params["asset_id"]
        if asset_id not in doc.assets:
            raise CommandError(f"Asset not found: {asset_id}")

        old_asset = doc.assets.pop(asset_id)
        inverse = CreativeCommand(
            command_id="asset.import",
            params={
                "asset_id": old_asset.asset_id,
                "name": old_asset.name,
                "kind": old_asset.kind,
                "path": old_asset.path,
                "sha256": old_asset.sha256,
                "width": old_asset.width,
                "height": old_asset.height,
            },
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _snapshot_tracks(self, comp: Composition) -> list[dict[str, Any]]:
        from workstation.creative_document import track_to_dict
        return [track_to_dict(t) for t in comp.tracks]

    def _handle_timeline_restore_tracks(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_document import track_from_dict
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        current_tracks = self._snapshot_tracks(comp)
        new_tracks = [track_from_dict(td) for td in cmd.params.get("tracks", [])]
        comp.tracks = new_tracks
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": current_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_split(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import split_clip_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        split_time = CanonicalTime.from_seconds(Fraction(cmd.params["split_time"]))
        split_clip_op(doc, comp.composition_id, cmd.params["clip_id"], split_time)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_trim(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import trim_clip_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        n_start = CanonicalTime.from_seconds(Fraction(cmd.params["new_start"])) if "new_start" in cmd.params else None
        n_end = CanonicalTime.from_seconds(Fraction(cmd.params["new_end"])) if "new_end" in cmd.params else None
        ripple = bool(cmd.params.get("ripple", False))
        trim_clip_op(doc, comp.composition_id, cmd.params["clip_id"], new_start=n_start, new_end=n_end, ripple=ripple)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_ripple_delete(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import ripple_delete_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        ripple_delete_op(doc, comp.composition_id, cmd.params["clip_id"])
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_slip(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import slip_clip_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        delta = CanonicalTime.from_seconds(Fraction(cmd.params["delta_seconds"]))
        slip_clip_op(doc, comp.composition_id, cmd.params["clip_id"], delta)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_slide(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import slide_clip_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        delta = CanonicalTime.from_seconds(Fraction(cmd.params["delta_seconds"]))
        slide_clip_op(doc, comp.composition_id, cmd.params["clip_id"], delta)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_roll(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import roll_clip_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        new_split = CanonicalTime.from_seconds(Fraction(cmd.params["new_split_time"]))
        roll_clip_op(doc, comp.composition_id, cmd.params["left_clip_id"], cmd.params["right_clip_id"], new_split)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)

    def _handle_clip_set_speed(self, doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
        from workstation.creative_timeline import set_clip_speed_op
        comp = self._find_comp(doc, cmd.params.get("composition_id"))
        old_tracks = self._snapshot_tracks(comp)
        speed = float(cmd.params["speed"])
        keep_dur = bool(cmd.params.get("keep_duration", False))
        set_clip_speed_op(doc, comp.composition_id, cmd.params["clip_id"], speed=speed, keep_duration=keep_dur)
        inverse = CreativeCommand(
            command_id="timeline.restoreTracks",
            params={"composition_id": comp.composition_id, "tracks": old_tracks},
            actor=cmd.actor,
            idempotency_key=f"inv_{cmd.idempotency_key}",
        )
        return CommandResult(success=True, inverse_command=inverse)


_GLOBAL_REGISTRY = CommandRegistry()


def execute_command(doc: CreativeDocument, cmd: CreativeCommand) -> CommandResult:
    """Execute a single typed command through the canonical CommandRegistry."""
    return _GLOBAL_REGISTRY.execute(doc, cmd)
