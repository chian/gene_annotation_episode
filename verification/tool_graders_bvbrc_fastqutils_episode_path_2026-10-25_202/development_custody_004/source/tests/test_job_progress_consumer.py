"""Typed physical-job observations through C8 and ordinary monitor consumers.

Native status and controller choices here are fixtures. These tests exercise
real Store transactions, source custody, C8 publication and method_loop returns;
they make no native-execution or configured-model scientific claim.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import sqlite3

import pytest

from method_loop.durable import DurableExecutionStore, canonical, content_digest
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider, read_progress
from gene_annotation_episode.progress_records import JOB_STATUS_VERSION, job_status
from gene_annotation_episode.state import Store
from test_recursive_monitoring import (RecursiveConsumer, Services, assignment, bound,
                                      durable_target)


class ContractJob:
    """Job-provider port with independently committed, selected raw captures."""

    handle = "homology_job_fixture"

    def __init__(self, store, scope):
        self.store, self.target_scope = store, scope
        self.timestamp = "2026-10-21T01:00:00+00:00"
        self.native_reads = 0
        self.calls = []
        self.native = {"job_ref": self.handle, "registry_ref": "execution_registry_fixture",
            "state": "running", "outcome": "pending", "elapsed_seconds": None,
            "duration_measure": "systemd_service_wall_seconds", "native_returncode": None,
            "failure_code": None, "resource": None,
            "progress_kind": "native_execution_state_and_output_bytes_not_search_fraction",
            "outputs": [{"role": "native_text", "available": True, "bytes": 13,
                         "writer_closed": False}]}
        self.data = b"batch 1 done\n"
        artifact = store.artifact(self.data, "text/plain")
        self.source = store.put("source", {"provider": "fixture_retained_job_stdout",
            "accession": None, "uri": None, "artifact_ref": artifact, "text_ref": artifact,
            "request_ref": None, "version": None, "retrieved_at": self.timestamp}, origin="tool")
        with store.transaction():
            store.db.execute("CREATE TABLE IF NOT EXISTS fixture_job_captures "
                "(operation_key TEXT PRIMARY KEY, signature TEXT NOT NULL, snapshot TEXT NOT NULL)")

    def scope(self, handle):
        if handle != self.handle:
            raise KeyError(handle)
        return self.target_scope

    def direct_dependencies(self, handle, scope):
        self.scope(handle)
        assert scope == self.target_scope
        return []

    def observe(self, handle, requested_fields, scope, *, operation_key=None):
        self.calls.append(operation_key)
        signature = content_digest({"handle": handle, "fields": requested_fields, "scope": scope})
        with self.store.transaction():
            if operation_key is not None:
                old = self.store.db.execute("SELECT signature,snapshot FROM fixture_job_captures "
                    "WHERE operation_key=?", (operation_key,)).fetchone()
                if old:
                    assert old["signature"] == signature
                    return json.loads(old["snapshot"])
            self.scope(handle)
            self.native_reads += 1
            status = job_status(handle, deepcopy(self.native), observed_at=self.timestamp)
            snapshot = {"version": "progress_snapshot_v1", "progress_ref": "fixture_raw_capture",
                "target_handle": handle, "observed_at": self.timestamp,
                "provenance_refs": [self.source["id"]], "execution_status": status,
                "measurements": [{"name": "service_wall_elapsed", "value": self.native["elapsed_seconds"],
                    "unit": "seconds", "measured_at": self.timestamp,
                    "provenance_ref": self.source["id"]}] if "measurements" in requested_fields else [],
                "log_windows": [{"source_ref": self.source["id"], "artifact_ref": self.source["artifact_ref"],
                    "start_byte": 0, "end_byte": len(self.data), "observed_at": self.timestamp,
                    "content_sha256": hashlib.sha256(self.data).hexdigest()}]
                    if "log_windows" in requested_fields else [],
                "committed_record_refs": [], "dependencies": [],
                "result_available": status["result_available"]}
            if operation_key is not None:
                self.store.db.execute("INSERT INTO fixture_job_captures VALUES(?,?,?)",
                    (operation_key, signature, canonical(snapshot)))
        return snapshot


def setup_provider(tmp_path, store):
    store.create_problem(raw_sequence="MKWAA", molecule="protein")
    scope = store.validate_scope({"subject_refs": store.problem()["subject_refs"]})
    job = ContractJob(store, scope)
    executions = DurableExecutionStore(tmp_path / "executions")
    return scope, job, ProgressProvider(store, executions,
        run_id="durable-fixture-run", job_provider=job)


@pytest.mark.parametrize("native_state,lifecycle,available", [
    ("not_submitted", "pending", False), ("prepared", "pending", False),
    ("starting", "executing", True), ("running", "executing", True),
    ("returned", "returned", True), ("submission_unconfirmed", None, True),
    ("execution_unknown", None, True)])
def test_native_status_keeps_its_exact_detail_and_actual_output_availability(
        tmp_path, native_state, lifecycle, available):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        job.native["state"] = native_state
        job.native["outcome"] = "succeeded" if native_state == "returned" else "unknown"
        output = job.native["outputs"][0]
        output.update(available=available, bytes=len(job.data) if available else None,
            writer_closed=native_state == "returned")
        snapshot = provider.observe(job.handle, list(FIELDS), scope)
        status = snapshot["execution_status"]
        assert status == job_status(job.handle, job.native, observed_at=job.timestamp)
        assert status["version"] == JOB_STATUS_VERSION and status["lifecycle_state"] == lifecycle
        assert snapshot["result_available"] is available
        assert set(status) == {"version", "handle", "observed_at", "lifecycle_state", "result_available", "native"}
        assert provider.read_progress(snapshot["progress_ref"], scope) == snapshot
        context = bound(scope, assignment(job.handle, known=[snapshot["progress_ref"]]))
        facts = MonitorEpisodes(Services(store, provider)).facts(context, {})
        assert facts["monitoring_execution_state"] == lifecycle
        assert facts["monitoring_result_available"] is available
        assert not store.list("assessment") and not store.list("observation")


def test_selected_job_observation_replays_before_target_reads_and_conflicts_on_selection(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        original = provider.observe(job.handle, list(FIELDS), scope, operation_key="selected")
        assert job.calls == ["selected"] and job.native_reads == 1
        job.timestamp = "2026-10-21T02:00:00+00:00"
        job.native.update(state="returned", outcome="succeeded", elapsed_seconds=7)
        job.native["outputs"][0]["writer_closed"] = True
        with monkeypatch.context() as patch:
            def forbidden(*args, **kwargs):
                raise AssertionError("replay must precede any target access")
            patch.setattr(provider, "_target", forbidden)
            assert provider.observe(job.handle, list(FIELDS), scope, operation_key="selected") == original
            variants = [("another_job", list(FIELDS), scope, ()),
                (job.handle, ["execution_status"], scope, ()),
                (job.handle, list(FIELDS), {**scope, "segments": []}, ()),
                (job.handle, list(FIELDS), scope, ["source"])]
            for handle, fields, selected_scope, permitted in variants:
                with pytest.raises(ContractError, match="progress_operation_identity_conflict"):
                    provider.observe(handle, fields, selected_scope, operation_key="selected",
                        permitted_committed_record_types=permitted)
        assert job.calls == ["selected"]
        current = provider.observe(job.handle, list(FIELDS), scope)
        assert current["result_available"] and current["execution_status"]["lifecycle_state"] == "returned"
        assert current["progress_ref"] != original["progress_ref"]
        assert provider.observe(job.handle, list(FIELDS), scope, operation_key="later") == current
        assert job.calls == ["selected", None, "later"]
    with Store(tmp_path / "state") as store:
        executions = DurableExecutionStore(tmp_path / "executions")
        provider = ProgressProvider(store, executions, run_id="durable-fixture-run")
        assert provider.observe(job.handle, list(FIELDS), scope, operation_key="selected") == original


@pytest.mark.parametrize("failure", ["validation", "publication"])
def test_valid_native_capture_survives_outer_c8_interruption_and_publication_is_atomic(tmp_path, monkeypatch, failure):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        if failure == "validation":
            with monkeypatch.context() as patch:
                def fail(*args):
                    raise RuntimeError("interrupted validation")
                patch.setattr(provider, "_validate_exposed", fail)
                with pytest.raises(RuntimeError, match="interrupted validation"):
                    provider.observe(job.handle, list(FIELDS), scope, operation_key="selected")
        else:
            store.db.execute("CREATE TEMP TRIGGER interrupt_publication BEFORE INSERT ON runtime_progress_selections "
                "BEGIN SELECT RAISE(ABORT, 'interrupted publication'); END")
            with pytest.raises(sqlite3.IntegrityError, match="interrupted publication"):
                provider.observe(job.handle, list(FIELDS), scope, operation_key="selected")
            store.db.execute("DROP TRIGGER interrupt_publication")
        assert store.db.execute("SELECT count(*) FROM runtime_progress_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_progress_selections").fetchone()[0] == 0
        saved = json.loads(store.db.execute("SELECT snapshot FROM fixture_job_captures").fetchone()[0])
        job.timestamp = "2026-10-21T02:00:00+00:00"
        job.native.update(state="returned", outcome="succeeded", elapsed_seconds=7)
        job.native["outputs"][0]["writer_closed"] = True
        replay = provider.observe(job.handle, list(FIELDS), scope, operation_key="selected")
        assert job.native_reads == 1 and job.calls == ["selected", "selected"]
        assert replay["execution_status"] == saved["execution_status"]
        assert replay["observed_at"] == saved["observed_at"]
        assert replay["log_windows"] == saved["log_windows"]
        assert store.get_artifact(replay["log_windows"][0]["artifact_ref"]) == job.data
        assert store.db.execute("SELECT progress_ref FROM runtime_progress_selections").fetchone()[0] == replay["progress_ref"]


def test_unchanged_native_capture_retains_original_custody_time_and_identity(tmp_path):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        first = provider.observe(job.handle, list(FIELDS), scope, operation_key="one")
        job.timestamp = "2026-10-21T02:00:00+00:00"
        second = provider.observe(job.handle, list(FIELDS), scope, operation_key="two")
        assert second == first
        assert job.native_reads == 2
        assert store.get(first["log_windows"][0]["source_ref"])["retrieved_at"] == first["observed_at"]
        assert store.db.execute("SELECT count(*) FROM runtime_progress_observations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_progress_selections").fetchone()[0] == 2


def test_episode_status_retains_c2_relationships_and_selected_replay(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        target = durable_target(tmp_path, store, provider.durable_store)
        status = provider.durable_store.status(target["handle"])
        monkeypatch.setattr(provider.durable_store, "status", lambda *_: status)
        original = provider.observe(target["handle"], list(FIELDS), scope, operation_key="episode")
        assert original["execution_status"] == status
        assert original["execution_status"]["version"] == "execution_status_v1"
        with monkeypatch.context() as patch:
            patch.setattr(provider.durable_store, "load_commission", lambda *_: pytest.fail("C2 replay read target"))
            assert provider.observe(target["handle"], list(FIELDS), scope, operation_key="episode") == original
        invalid = deepcopy(original["execution_status"])
        invalid.update(return_available=True, return_id="unreturned-form")
        monkeypatch.setattr(provider.durable_store, "status", lambda *_: invalid)
        with pytest.raises(ContractError, match="progress_status_relationship_mismatch"):
            provider.observe(target["handle"], list(FIELDS), scope)
        monkeypatch.setattr(provider.durable_store, "status", lambda *_: job_status(job.handle,
            job.native, observed_at=job.timestamp))
        with pytest.raises(ContractError):
            provider.observe(target["handle"], list(FIELDS), scope)


def test_physical_job_rejects_c2_status_and_inconsistent_raw_result_availability(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        target = durable_target(tmp_path, store, provider.durable_store)
        raw = job.observe(job.handle, list(FIELDS), scope)
        bad = deepcopy(raw)
        bad["execution_status"] = provider.durable_store.status(target["handle"])
        bad["execution_status"]["handle"] = job.handle
        monkeypatch.setattr(job, "observe", lambda *args, **kwargs: bad)
        with pytest.raises(ContractError):
            provider.observe(job.handle, list(FIELDS), scope)
        bad = {**raw, "result_available": False}
        with pytest.raises(ContractError, match="progress_job_result_relationship_mismatch"):
            provider.observe(job.handle, list(FIELDS), scope)


def test_monitor_selected_observation_uses_same_key_and_returns_original_typed_facts(tmp_path):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        job.native["state"] = "execution_unknown"
        services = Services(store, provider)
        binding = MonitorEpisodes(services)
        context = bound(scope, assignment(job.handle))
        observed = asyncio.run(binding.execute(context, "progress.observe", {"requested_fields": list(FIELDS)}, "selected"))
        assert observed["status"] == "completed" and job.calls == ["selected"]
        assert binding.facts(context, {})["monitoring_execution_state"] is None
        assert binding.facts(context, {})["monitoring_result_available"] is None
        services.remember(context.episode_id, 0, "progress.observe", observed)
        schema = obj({"state": binding.fact_sources("monitor")["monitoring_execution_state"]["report_schema"],
            "available": binding.fact_sources("monitor")["monitoring_result_available"]["report_schema"],
            "progress": binding.fact_sources("monitor")["monitoring_progress_refs"]["report_schema"],
            "assessment": {"type": "string", "enum": ["unresolved"]}})
        form = form_with_facts({"assessment": "unresolved"}, schema, binding.facts(context, {}))
        binding.validate_report(context, form, schema)
        assert form["state"] is None and form["available"] is True
        assert provider.receive_form("science", form, schema, scope, "original-return") == form["progress"]
        assert provider.received_progress_refs("science", scope) == form["progress"]
        job.native["state"] = "returned"
        replay = asyncio.run(binding.execute(context, "progress.observe", {"requested_fields": list(FIELDS)}, "selected"))
        assert replay == observed and job.calls == ["selected"]
        log = asyncio.run(binding.execute(context, "progress.log", {"progress_ref": form["progress"][0], "log_index": 0}, "read-log"))
        assert log["result"]["text"] == job.data.decode()
        assert not store.list("assessment") and not store.list("observation")


def test_shared_episode_controller_stops_before_observing_another_job_progress_return(tmp_path):
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        services = Services(store, provider)
        binding = MonitorEpisodes(services)
        def choose(key, index, inputs):
            if key == "root":
                return {"kind": "child", "key": f"job-{index}", "assignment": assignment(job.handle)}
            return {"kind": "tool", "tool": "progress.observe", "arguments": {"requested_fields": list(FIELDS)}}
        consumer = RecursiveConsumer(services, binding, scope, choose)
        # This fixture's scientific controller allows two completed child
        # returns. Each selected monitor has three actions, including unchanged
        # observations. The configured controller alone ends those loops.
        root = consumer.build("science", "root", {})
        result = asyncio.run(root.run_async(consumer.context))
        assert result.units_consumed == 2 and result.ended_by == "yield_stop"
        assert len(consumer.forms) == 2
        assert len(job.calls) == 6 and job.native_reads == 6
        assert len(provider.received_progress_refs(root.source.binding_context.episode_id, scope)) == 1
        assert services.bound_role_credit(root.source.binding_context, {})["credit"] == 1
        assert not store.list("assessment") and not store.list("observation")


def test_shared_reader_uses_only_original_saved_run_scope_and_creates_no_state(tmp_path):
    with Store(tmp_path / "empty") as store:
        before = list(store.db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        with pytest.raises(ContractError, match="progress_reference_unavailable"):
            read_progress(store, "durable-fixture-run", "missing")
        assert list(store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")) == before
    with Store(tmp_path / "state") as store:
        scope, job, provider = setup_provider(tmp_path, store)
        saved = provider.observe(job.handle, list(FIELDS), scope, operation_key="selected")
        table_counts = {row[0]: store.db.execute(f'SELECT count(*) FROM "{row[0]}"').fetchone()[0]
            for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert read_progress(store, provider.run_id, saved["progress_ref"], scope) == saved
        with pytest.raises(ContractError, match="progress_reference_unavailable"):
            read_progress(store, "another-run", saved["progress_ref"], scope)
        narrow = {"subject_refs": scope["subject_refs"], "segments": [{
            "target_ref": scope["subject_refs"][0], "start": 0, "end": 1, "unit": "aa"}]}
        with pytest.raises(ContractError, match="progress_reference_outside_scope"):
            read_progress(store, provider.run_id, saved["progress_ref"], narrow)
        assert job.calls == ["selected"] and job.native_reads == 1
        assert all(store.db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] == count
            for name, count in table_counts.items())
