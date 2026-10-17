"""Owner readback contracts using synthetic single-card BrowserTask observations."""

from copy import deepcopy
import json
from types import SimpleNamespace
import unittest

from workstation.integrations.hermes import run_local_adoption as module


class CardReadbackTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.saved = {}
        self.args = {
            "mode": "inspect",
            "selector": 'article[data-card-id="card-a"]',
            "limit": 1,
            "attributes": ["data-card-id", "data-list"],
        }
        self.raw = {
            "success": True,
            "cached": False,
            "runtime": "electron-chromium",
            "task_id": "task-A",
            "tab_id": "tab-A",
            "url": "https://example.test/cards",
            "count": 1,
            "items": [{"tag": "ARTICLE", "text": "Title ADescription A",
                       "attributes": {"data-card-id": "card-a", "data-list": "Todo"}}],
        }
        self.source = {
            "task_id": "task-A", "run_id": "run-A", "operation_id": "op-A",
            "raw_result_ref": "artifact://raw-A", "transition_ref": "artifact://sample-A",
            "browser_task_id": "task-A",
        }

        def store(task_id, name, content, *, schema):
            ref = f"artifact://receipt-{len(self.saved)}"
            self.saved[ref] = {"schema": schema, "content": deepcopy(content)}
            return SimpleNamespace(ref=ref)

        self.artifacts = SimpleNamespace(store=store, resolve_structured=self.saved.__getitem__)

    def dispatch(self, primitive, args):
        self.calls.append((primitive, deepcopy(args)))
        result = deepcopy(self.raw)
        if args["selector"].endswith(" > h2"):
            result["items"] = [{"tag": "H2", "text": "Title A", "attributes": {}}]
        elif args["selector"].endswith(" > p"):
            result["items"] = [{"tag": "P", "text": "Description A", "attributes": {}}]
        return json.dumps(result)

    def reader(self, dispatch=None, source=None):
        return module._readback_browser_extract_items(
            dispatch or self.dispatch, self.artifacts, "task-A", "run-A",
            source_for_readback=source or (lambda args, raw: deepcopy(self.source)),
        )

    def test_fresh_card_fields_get_resolved_owner_receipt(self):
        result = self.reader()("browser_extract_items", self.args, self.raw)
        self.assertTrue(result["ok"])
        body = self.saved[result["evidence_ref"]]["content"]
        self.assertEqual(body["operation_id"], "op-A")
        self.assertEqual(body["raw_result_ref"], "artifact://raw-A")
        self.assertEqual(body["transition_ref"], "artifact://sample-A")
        self.assertEqual(body["projection"]["result_count"], 1)
        self.assertEqual(body["observation_consistency"], "non_atomic_parent_bracket")
        self.assertEqual([call[0] for call in self.calls], ["browser_extract_items"] * 4)
        self.assertEqual(self.calls[0][1]["selector"], ':is(article[data-card-id="card-a"])')
        self.assertEqual(self.calls[-1][1]["selector"], ':where(article[data-card-id="card-a"])')

    def test_cached_or_cross_tab_observation_never_gets_receipt(self):
        for change in ({"cached": True}, {"tab_id": "other-tab"}, {"task_id": "other-task"}):
            with self.subTest(change=change):
                self.saved.clear()
                def altered(primitive, args):
                    result = json.loads(self.dispatch(primitive, args))
                    result.update(change)
                    return result
                self.assertFalse(self.reader(altered)("browser_extract_items", self.args, self.raw)["ok"])
                self.assertFalse(self.saved)

    def test_changed_parent_or_child_field_never_gets_receipt(self):
        for changed_part in ("parent", "title"):
            with self.subTest(changed_part=changed_part):
                self.saved.clear()
                def altered(primitive, args):
                    result = json.loads(self.dispatch(primitive, args))
                    if ((changed_part == "parent" and args["selector"].startswith(":where("))
                            or (changed_part == "title" and args["selector"].endswith(" > h2"))):
                        result["items"][0]["text"] = "Changed"
                    return result
                self.assertFalse(self.reader(altered)("browser_extract_items", self.args, self.raw)["ok"])
                self.assertFalse(self.saved)

    def test_missing_canonical_source_or_ambiguous_card_fails_closed(self):
        result = self.reader(source=lambda args, raw: None)("browser_extract_items", self.args, self.raw)
        self.assertFalse(result["ok"])
        self.assertFalse(self.calls)
        self.raw["count"] = 2
        result = self.reader()("browser_extract_items", self.args, self.raw)
        self.assertFalse(result["ok"])
        self.assertFalse(self.saved)

    def test_ack_and_wrong_run_source_cannot_certify_card(self):
        self.assertFalse(self.reader()("browser_extract_items", self.args, {"ok": True})["ok"])
        self.source["run_id"] = "other-run"
        self.assertFalse(self.reader()("browser_extract_items", self.args, self.raw)["ok"])
        self.assertFalse(self.saved)

    def test_card_readback_does_not_grant_mutation_effects(self):
        from workstation.run_adoption import effects_for_step
        self.assertEqual(effects_for_step("browser_extract_items", self.args, {}), [])

    def test_receipt_must_resolve_with_its_original_binding(self):
        def tampered(ref):
            resolved = deepcopy(self.saved[ref])
            resolved["content"]["operation_id"] = "other-op"
            return resolved
        self.artifacts.resolve_structured = tampered
        self.assertFalse(self.reader()("browser_extract_items", self.args, self.raw)["ok"])

    def test_projection_rejects_extra_text(self):
        from workstation.experience_compiler.read_output_contract import (
            UnverifiedRead, prepare_read_shape,
        )
        rows = [{"id": "card-a", "list": "Todo", "title": "Title A", "description": "Description A"}]
        for text in ("Unrelated Title ADescription A", "Title AUnexpected Description A",
                     "Title ADescription A Unrelated"):
            with self.subTest(text=text):
                self.raw["items"][0]["text"] = text
                with self.assertRaises(UnverifiedRead):
                    prepare_read_shape(self.raw, rows)

