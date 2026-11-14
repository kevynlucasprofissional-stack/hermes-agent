"""The local missed-run policy preserves grace and manual triggers."""
from datetime import timedelta

import pytest

from cron import jobs


@pytest.mark.parametrize("catch_up", [True, False])
def test_missed_policy_preserves_grace_and_manual(tmp_path, monkeypatch, catch_up):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(f"cron:\n  catch_up_missed: {str(catch_up).lower()}\n", encoding="utf-8")
    with jobs.use_cron_store(tmp_path / "cron"):
        now = jobs._hermes_now()
        for name, lag in [("stale", 14400), ("grace", 30), ("manual", 14400)]:
            job = jobs.create_job(prompt=name, schedule="every 1h", model="fixture", deliver="local")
            stored = jobs.load_jobs()
            row = next(row for row in stored if row["id"] == job["id"])
            row["next_run_at"] = (now - timedelta(seconds=lag)).isoformat()
            if name == "manual":
                row["manual_run_at"] = row["next_run_at"]
            jobs.save_jobs(stored)
        due = {job["prompt"] for job in jobs.get_due_jobs()}
        assert due == ({"stale", "grace", "manual"} if catch_up else {"grace", "manual"})
        stale = next(row for row in jobs.load_jobs() if row["prompt"] == "stale")
        assert jobs._ensure_aware(jobs.datetime.fromisoformat(stale["next_run_at"])) > now


@pytest.mark.parametrize("uncomputable", [False, True])
def test_default_and_uncomputable_still_catch_up(tmp_path, monkeypatch, uncomputable):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    if uncomputable:
        (tmp_path / "config.yaml").write_text("cron:\n  catch_up_missed: false\n", encoding="utf-8")
    with jobs.use_cron_store(tmp_path / "cron"):
        job = jobs.create_job(prompt="default", schedule="every 1h", model="fixture", deliver="local")
        stored = jobs.load_jobs()
        stored[0]["next_run_at"] = (jobs._hermes_now() - timedelta(hours=4)).isoformat()
        jobs.save_jobs(stored)
        if uncomputable:
            monkeypatch.setattr(jobs, "compute_next_run", lambda *args: None)
        assert [row["id"] for row in jobs.get_due_jobs()] == [job["id"]]


def test_daily_outage_catchup_claims_once_and_reanchors_next_day(tmp_path, monkeypatch):
    """Real jobs store: a missed daily slot is due ASAP, claimed once, then next day."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        "timezone: America/Sao_Paulo\ncron:\n  catch_up_missed: true\n", encoding="utf-8"
    )
    now = datetime(2026, 11, 7, 17, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    monkeypatch.setattr(jobs, "_hermes_now", lambda: now)

    with jobs.use_cron_store(tmp_path / "cron"):
        job = jobs.create_job(
            prompt="Missed daily sync", schedule="0 9 * * *", model="fixture", deliver="local"
        )
        records = jobs.load_jobs()
        records[0]["next_run_at"] = datetime(
            2026, 11, 6, 9, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
        ).isoformat()
        jobs.save_jobs(records)

        due = jobs.get_due_jobs()
        assert [item["id"] for item in due] == [job["id"]]
        assert due[0]["last_dispatch"]["kind"] == "catch_up"
        assert due[0]["last_dispatch"]["scheduled_at"].startswith("2026-11-06T09:00:00")

        assert jobs.claim_job_for_fire(job["id"]) is True
        assert jobs.claim_job_for_fire(job["id"]) is False
        assert jobs.get_due_jobs() == []
        next_run = jobs.load_jobs()[0]["next_run_at"]
        assert next_run.startswith("2026-11-08T09:00:00")

    # File-backed state persists across scheduler/store reconstruction.
    with jobs.use_cron_store(tmp_path / "cron"):
        assert jobs.get_due_jobs() == []
        assert jobs.load_jobs()[0]["next_run_at"] == next_run
