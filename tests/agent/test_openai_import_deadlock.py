"""Regression: cold concurrent SDK imports deadlock on Python 3.14.

The operational entrypoints call prewarm_openai_sdk() before creating threads.
This uses fresh Python subprocesses to avoid pytest/import-cache false passes.
"""

import os
import subprocess
import sys
import textwrap

import pytest

_SCRIPT = textwrap.dedent("""
    import importlib
    import threading
    import sys

    from agent.process_bootstrap import prewarm_openai_sdk
    prewarm_openai_sdk()
    assert "openai.types.chat" in sys.modules

    barrier = threading.Barrier(10, timeout=10)
    errors = []

    def worker(i):
        try:
            barrier.wait()
            if i % 4 == 0:
                from openai import OpenAI
                client = OpenAI(api_key="unit-test", base_url="https://example.invalid/v1")
                client.close()
            elif i % 4 == 1:
                importlib.import_module("openai.types.chat")
            elif i % 4 == 2:
                importlib.import_module("openai.resources.chat.completions")
            else:
                from agent.auxiliary_client import _load_openai_cls
                cls = _load_openai_cls()
                client = cls(api_key="unit-test", base_url="https://example.invalid/v1")
                client.close()
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert not any(thread.is_alive() for thread in threads), "hung import worker"
    assert not errors, errors
""")


@pytest.mark.parametrize("trial", range(3))
def test_openai_sdk_prewarm_before_concurrent_client_build(trial, tmp_path):
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path / "hermes")
    env.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        check=False,
        capture_output=True,
        text=True,
        timeout=35,
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
