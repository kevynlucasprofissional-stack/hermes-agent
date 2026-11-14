"""P03 Cron integration: real Hermes cron store, local durable output, zero external delivery."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from workstation.trello_action_journal import append_batch, install_schema
from workstation.trello_daily_brief_cron import (
    main, prepare_paused_cron_job, register_dry_run,
)


def fixture_db(tmp_path):
    file = tmp_path / "canonical-fixture.sqlite"
    with sqlite3.connect(file) as conn:
        install_schema(conn)
        append_batch(conn, "boardABC", [
            {"id": "ab123", "type": "updateCard",
             "date": "2026-10-26T16:00:00Z",
             "data": {"card": {"id": "card222"}}}
        ])
    return file


def test_cli_offline_fixture_generates_traceable_text_without_network(tmp_path, capsys):
    file = fixture_db(tmp_path)
    code = main(["--board", "boardABC", "--day", "2026-10-26", "--tz", "UTC",
                 "--fixture-db", str(file), "--dry-run", "--format", "text"])
    printed = capsys.readouterr().out
    assert code == 0
    assert "[ab123]" in printed
    assert "boardABC" in printed
    assert "SECRET" not in printed


def test_cli_prompt_mode_yields_untrusted_metadata_not_raw_comments(tmp_path, capsys):
    file = fixture_db(tmp_path)
    code = main(["--board", "boardABC", "--day", "2026-10-26", "--tz", "UTC",
                 "--fixture-db", str(file), "--dry-run", "--format", "prompt"])
    printed = capsys.readouterr().out
    assert code == 0
    assert "dados não confiáveis" in printed and "ab123" in printed
    assert "desc" not in printed


def test_cli_rejects_fixture_database_without_dry_run(tmp_path):
    file = fixture_db(tmp_path)
    with pytest.raises(ValueError, match="fixture"):
        main(["--board", "boardABC", "--fixture-db", str(file)])


def test_paused_bot_routine_in_existing_cron_store_inherits_model_without_provider_pin(tmp_path):
    from cron import jobs
    home = tmp_path / "bot-home"
    (home / "scripts").mkdir(parents=True)
    (home / "config.yaml").write_text("cron:\n  model: fixture-model\n  model_provider: fixture-provider\n", encoding="utf-8")
    with jobs.use_cron_store(home):
        job = prepare_paused_cron_job(
            profile_home=home, board_id="boardABC", schedule="0 8 * * 1-5",
            timezone_name="America/Sao_Paulo", bot_name="trello-relator",
        )
        persisted = jobs.get_job(job["id"])
        assert persisted["enabled"] is False
        assert persisted["deliver"] == "local"
        assert persisted["model"] is None and persisted["provider"] is None
        assert persisted["no_agent"] is False
        assert persisted["script"] == "trello_daily_brief.py"
        assert "[bot:trello-relator]" in persisted["name"]
        assert persisted["next_run_at"] is None
        assert (home / "scripts" / "trello_daily_brief.py").is_file()


def test_dry_run_persists_output_with_id_in_existing_cron_store(tmp_path):
    from cron import jobs
    file = fixture_db(tmp_path)
    home = tmp_path / "isolated-home"
    (home / "scripts").mkdir(parents=True)
    with jobs.use_cron_store(home):
        job = prepare_paused_cron_job(profile_home=home, board_id="boardABC", bot_name="trello-relator")
        result = register_dry_run(job_id=job["id"], board_id="boardABC", day="2026-10-26",
                                  timezone_name="UTC", fixture_db=file)
        outputs = list((home / "cron" / "output" / job["id"]).glob("*.md"))
        assert outputs and str(result["output_path"]) == str(outputs[0])
        assert "[ab123]" in outputs[0].read_text("utf-8")
        assert result["job_id"] == job["id"]
        assert result["evidence_sha256"]
        assert jobs.get_job(job["id"])["enabled"] is False


def test_cron_uses_existing_model_precedence_not_job_override(tmp_path, monkeypatch):
    from cron import jobs, scheduler
    home = tmp_path / "scoped-bot-home"
    (home / "scripts").mkdir(parents=True)
    (home / "config.yaml").write_text(
        "cron:\n  model: sample-daily-model\n  model_provider: sample-provider\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HERMES_MODEL", raising=False)
    with jobs.use_cron_store(home):
        job = prepare_paused_cron_job(profile_home=home, board_id="boardABC", bot_name="trello-relator")
        resolved = scheduler._load_cron_job_config(job, job["id"], job["name"])
        assert resolved.model == "sample-daily-model"
        assert resolved.cron_default_provider == "sample-provider"


def test_existing_cron_run_job_executes_script_and_keeps_delivery_local(tmp_path, monkeypatch):
    from cron import jobs, scheduler
    file = fixture_db(tmp_path)
    home = tmp_path / "scoped-script-home"
    (home / "scripts").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    with jobs.use_cron_store(home):
        job = prepare_paused_cron_job(profile_home=home, board_id="boardABC", bot_name="trello-relator")
        # Only this test fixture directs a script at the temporary SQLite database.
        repo_root = str(Path(__file__).resolve().parents[2])
        wrapper = (
            "import sys\n"
            f"sys.path.insert(0, {repo_root!r})\n"
            "from workstation.trello_daily_brief_cron import main\n"
            "if __name__ == '__main__':\n"
            f"    raise SystemExit(main({['--board','boardABC','--day','2026-10-26','--tz','UTC','--format','text','--fixture-db',str(file),'--dry-run']!r}))\n"
        )
        (home / "scripts" / "trello_daily_brief.py").write_text(wrapper, encoding="utf-8")
        simulated = {**job, "no_agent": True}  # test-only: no model calls or delivery
        ok, audit_doc, content, error = scheduler.run_job(simulated)
        assert ok is True, (error, audit_doc)
        assert "[ab123]" in content and error is None
        assert "[ab123]" in audit_doc
        saved = jobs.save_job_output(job["id"], audit_doc)
        assert saved.exists() and "[ab123]" in saved.read_text("utf-8")
        assert jobs.get_job(job["id"])["enabled"] is False
        assert jobs.get_job(job["id"])["deliver"] == "local"


def test_register_paused_job_is_idempotent_in_behavior_and_refuses_duplicate(tmp_path):
    from cron import jobs
    home = tmp_path / "fresh-profile"
    (home / "scripts").mkdir(parents=True)
    with jobs.use_cron_store(home):
        first = prepare_paused_cron_job(profile_home=home, board_id="boardABC")
        with pytest.raises(ValueError, match="already exists"):
            prepare_paused_cron_job(profile_home=home, board_id="boardABC")
        matches = [job for job in jobs.load_jobs() if job["name"] == first["name"]]
        assert len(matches) == 1


def test_cron_registration_failure_removes_only_script_created_by_attempt(tmp_path, monkeypatch):
    from cron import jobs
    home = tmp_path / "fail-profile"
    (home / "scripts").mkdir(parents=True)
    with jobs.use_cron_store(home):
        monkeypatch.setattr(jobs, "create_job", lambda **kwargs: (_ for _ in ()).throw(ValueError("registration denied")))
        with pytest.raises(ValueError, match="registration denied"):
            prepare_paused_cron_job(profile_home=home, board_id="boardABC")
        assert not (home / "scripts" / "trello_daily_brief.py").exists()
