"""Unit tests for CW-047 creative_web_service lifecycle, reuse, and loopback verification."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tools.process_registry import ProcessRegistry
from workstation.creative_web_app_spec import APPS
from workstation.creative_web_service import (
    CreativeWebAppError,
    allocate_creative_port,
    clear_active_instances,
    discover_web_app_dist,
    get_or_launch_creative_web_app,
    open_and_verify_creative_web_app,
    probe_creative_web_app_health,
    start_creative_web_app_server,
    stop_creative_web_app_server,
)


class CreativeWebServiceTests(unittest.TestCase):
    def setUp(self):
        clear_active_instances()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name).resolve()
        (self.root / "index.html").write_text("<title>PhotoCraft Test</title>", encoding="utf-8")
        (self.root / "fixture.wasm").write_bytes(b"\x00asm")

    def tearDown(self):
        clear_active_instances()

    def test_discover_web_app_dist_unknown(self):
        self.assertIsNone(discover_web_app_dist("unknown_engine"))

    def test_discover_web_app_dist_env_override(self):
        with patch.dict("os.environ", {"HERMES_PHOTOCRAFT_WEB_DIST": str(self.root)}):
            found = discover_web_app_dist("photocraft")
            self.assertEqual(found, self.root)

    def test_discover_web_app_dist_missing_index(self):
        empty_dir = self.root / "empty_dist"
        empty_dir.mkdir()
        with patch("workstation.creative_web_service.get_hermes_home", return_value=self.root / "fake_home"):
            with patch.dict("os.environ", {"HERMES_PHOTOCRAFT_WEB_DIST": str(empty_dir)}):
                self.assertIsNone(discover_web_app_dist("photocraft"))

    def test_allocate_creative_port_strict_loopback(self):
        with self.assertRaises(ValueError):
            allocate_creative_port(host="0.0.0.0")
        port = allocate_creative_port(start_port=9100, max_port=9150)
        self.assertTrue(9100 <= port <= 9150)

    def test_start_probe_and_stop_server(self):
        registry = ProcessRegistry()
        instance = start_creative_web_app_server(
            "photocraft",
            dist_root=self.root,
            registry=registry,
            timeout=5.0,
        )
        try:
            self.assertEqual(instance.engine, "photocraft")
            self.assertTrue(instance.url.startswith("http://127.0.0.1:"))
            self.assertTrue(probe_creative_web_app_health(instance, registry=registry))
            session = registry.get(instance.process_id)
            self.assertTrue(getattr(session, "persist_on_release", False))
        finally:
            registry.kill_process(instance.process_id)

    def test_start_filmcraft_server(self):
        registry = ProcessRegistry()
        instance = start_creative_web_app_server(
            "filmcraft",
            dist_root=self.root,
            registry=registry,
            timeout=5.0,
        )
        try:
            self.assertEqual(instance.engine, "filmcraft")
            self.assertTrue(instance.url.startswith("http://127.0.0.1:"))
            self.assertTrue(probe_creative_web_app_health(instance, registry=registry))
        finally:
            registry.kill_process(instance.process_id)

    def test_reuse_healthy_instance(self):
        registry = ProcessRegistry()
        inst1, reused1 = get_or_launch_creative_web_app(
            "photocraft",
            dist_root=self.root,
            registry=registry,
            timeout=5.0,
        )
        try:
            self.assertFalse(reused1)
            inst2, reused2 = get_or_launch_creative_web_app(
                "photocraft",
                dist_root=self.root,
                registry=registry,
                timeout=5.0,
            )
            self.assertTrue(reused2)
            self.assertEqual(inst1.process_id, inst2.process_id)
            self.assertEqual(inst1.port, inst2.port)
        finally:
            registry.kill_process(inst1.process_id)

    def test_restart_after_killed(self):
        registry = ProcessRegistry()
        inst1, _ = get_or_launch_creative_web_app(
            "photocraft",
            dist_root=self.root,
            registry=registry,
            timeout=5.0,
        )
        try:
            # Kill the first server
            registry.kill_process(inst1.process_id)
            # Next call must detect unhealthy and launch a fresh server
            inst2, reused = get_or_launch_creative_web_app(
                "photocraft",
                dist_root=self.root,
                registry=registry,
                timeout=5.0,
            )
            self.assertFalse(reused)
            self.assertNotEqual(inst1.process_id, inst2.process_id)
        finally:
            stop_creative_web_app_server("photocraft", registry=registry)

    def test_open_and_verify_success(self):
        registry = ProcessRegistry()
        try:
            app = APPS["photocraft"]
            dispatched_calls = []

            def mock_dispatch(name, args):
                dispatched_calls.append((name, args))
                if name == "browser_navigate":
                    return {"success": True, "url": args["url"]}
                if name == "browser_snapshot":
                    # Controller-owned snapshot metadata
                    target_url = next(c[1]["url"] for c in dispatched_calls if c[0] == "browser_navigate")
                    return {
                        "text": f'{{"tab_id": 1, "url": "{target_url}"}}\n"snapshot": "<html></html>"'
                    }
                return {}

            receipt = open_and_verify_creative_web_app(
                app,
                mock_dispatch,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt.status, "verified")
            self.assertEqual(receipt.engine, "photocraft")
            self.assertTrue(receipt.observed_url.startswith("http://127.0.0.1:"))
        finally:
            stop_creative_web_app_server("photocraft", registry=registry)

    def test_open_and_verify_reuse_preserves_without_reload(self):
        registry = ProcessRegistry()
        try:
            app = APPS["filmcraft"]
            dispatched_calls = []

            # 1. Initial launch
            def mock_dispatch_first(name, args):
                dispatched_calls.append((name, args))
                if name == "browser_navigate":
                    return {"success": True, "url": args["url"]}
                if name == "browser_snapshot":
                    target_url = next(c[1]["url"] for c in dispatched_calls if c[0] == "browser_navigate")
                    return {
                        "text": f'{{"tab_id": 1, "url": "{target_url}"}}\n"snapshot": "<html></html>"'
                    }
                return {}

            receipt1 = open_and_verify_creative_web_app(
                app,
                mock_dispatch_first,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt1.status, "verified")
            self.assertFalse(receipt1.reused)
            self.assertTrue(receipt1.dispatch_attempted)

            # 2. Second launch: editor already active in browser
            navigated_again = False

            def mock_dispatch_second(name, args):
                nonlocal navigated_again
                if name == "browser_navigate":
                    navigated_again = True
                    return {"success": True, "url": args["url"]}
                if name == "browser_snapshot":
                    # Browser is still on the active filmcraft loopback URL
                    return {
                        "text": f'{{"tab_id": 1, "url": "{receipt1.url}"}}\n"snapshot": "<html>active project</html>"'
                    }
                return {}

            receipt2 = open_and_verify_creative_web_app(
                app,
                mock_dispatch_second,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt2.status, "verified")
            self.assertTrue(receipt2.reused)
            self.assertFalse(receipt2.dispatch_attempted)
            self.assertFalse(navigated_again, "browser_navigate must not be called when editor is already active")
            self.assertEqual(receipt2.reason, "creative_filmcraft_already_active_preserved")
        finally:
            stop_creative_web_app_server("filmcraft", registry=registry)

    def test_open_and_verify_reuse_human_lease(self):
        registry = ProcessRegistry()
        try:
            app = APPS["photocraft"]
            # Pre-launch server
            _inst, _ = get_or_launch_creative_web_app(app.key, dist_root=self.root, registry=registry)

            # Reusing when human control is active on the browser
            def mock_dispatch(name, args):
                if name == "browser_snapshot":
                    return {"status": "error", "reason": "409 USER_CONTROL_ACTIVE"}
                return {}

            receipt = open_and_verify_creative_web_app(
                app,
                mock_dispatch,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt.status, "user_control_active")
            self.assertFalse(receipt.dispatch_attempted)
        finally:
            stop_creative_web_app_server("photocraft", registry=registry)

    def test_open_and_verify_human_lease(self):
        registry = ProcessRegistry()
        try:
            app = APPS["photocraft"]

            def mock_dispatch(name, args):
                if name == "browser_navigate":
                    return {"status": "error", "reason": "409 USER_CONTROL_ACTIVE"}
                return {}

            receipt = open_and_verify_creative_web_app(
                app,
                mock_dispatch,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt.status, "user_control_active")
            self.assertEqual(receipt.reason, "user_control_active")
        finally:
            stop_creative_web_app_server("photocraft", registry=registry)

    def test_open_and_verify_url_mismatch(self):
        registry = ProcessRegistry()
        try:
            app = APPS["photocraft"]

            def mock_dispatch(name, args):
                if name == "browser_navigate":
                    return {"success": True}
                if name == "browser_snapshot":
                    # Simulated malicious or mismatched redirect
                    return {
                        "text": '{"tab_id": 1, "url": "https://attacker.example/malicious"}\n"snapshot": ""'
                    }
                return {}

            receipt = open_and_verify_creative_web_app(
                app,
                mock_dispatch,
                dist_root=self.root,
                registry=registry,
            )
            self.assertEqual(receipt.status, "uncertain")
        finally:
            stop_creative_web_app_server("photocraft", registry=registry)

    def test_open_and_verify_missing_dist(self):
        app = APPS["photocraft"]
        # With no env var and an empty search directory, missing_dist is returned cleanly
        with patch("workstation.creative_web_service.discover_web_app_dist", return_value=None):
            receipt = open_and_verify_creative_web_app(app, lambda *a: {})
            self.assertEqual(receipt.status, "missing_dist")


if __name__ == "__main__":
    unittest.main()
