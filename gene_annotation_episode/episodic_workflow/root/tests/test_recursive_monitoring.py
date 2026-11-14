"""Selected recursive monitoring with actual storage and ordinary Episodes.

Choices/controllers are scripted; the live targets are tiny fixture processes.
These checks make no configured-model, production credit-unit or scientific
completion claim.
"""
import asyncio
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from method_loop import ChildEpisodeUnit, Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from method_loop.durable import DurableExecutionStore, content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.progress_records import job_status
from gene_annotation_episode.runtime import Record, TypedReportContract, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_durable_episode import commission_spec, await_event, event_condition, release_gate, returned
from test_runtime import FixtureController, ScriptedProvider


def assignment(handle, *, known=(), permitted=(), fields=FIELDS):
    return {"version": "monitor_assignment_v1", "target_handle": handle,
        "requested_fields": list(fields), "known_progress_refs": list(known),
        "permitted_committed_record_types": list(permitted)}


def bound(scope, value, *, episode_id="monitor-fixture", parent_path=()):
    return BindingContext("durable-fixture-run", episode_id, "monitor",
        (*parent_path, ("monitor", episode_id)), scope, value, {})


def durable_target(tmp_path, store, executions, *, key="target", parent=None, arguments=None, run_id=None):
    spec = commission_spec(tmp_path, key=key, parent=parent, arguments=arguments)
    if run_id is not None:
        spec["run_id"] = run_id
        for party in ("parent", "child"):
            spec[party]["episode_id"] = EpisodeRef(run_id, spec[party]["path"]).episode_id
    spec["runtime_binding"]["arguments"]["execution_directory"] = str(executions.root_directory)
    spec["runtime_binding"]["settings_sha256"] = content_digest(spec["runtime_binding"]["arguments"])
    spec["child"]["scope"] = store.validate_scope({"subject_refs": store.problem()["subject_refs"]})
    executions.commission(spec)
    return spec


class Services:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider
        self.outcomes = defaultdict(list)
        self.credit_calls = []
        self.tools = ToolRegistry(store)

    def observe_progress(self, handle, fields, scope, **kwargs):
        return self.provider.observe(handle, fields, plain(scope), **kwargs)

    def dependencies(self, handle, scope):
        return self.provider.direct_dependencies(handle, plain(scope))

    def read_progress(self, reference, scope):
        return self.provider.read_progress(reference, plain(scope))

    def received_progress_refs(self, episode_id):
        return self.provider.received_progress_refs(episode_id)

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        rows = self.outcomes[episode_id]
        rows = rows if tools is None else [row for row in rows if row["selected_tool"] in tools]
        return {"records": deepcopy(rows[offset:offset + limit]), "offset": offset, "limit": limit,
                "next_offset": offset + limit if offset + limit < len(rows) else None}

    def read_record(self, ref):
        return self.store.get(ref)

    def reference_in_scope(self, ref, scope, namespace):
        if self.provider.resolve(ref, plain(scope), namespace):
            return True
        if not self.store.reference_subset([ref], plain(scope)):
            return False
        return namespace is None or self.store.get(ref)["record_type"] == namespace

    def bound_role_credit(self, context, selection):
        # Explicit test-only projection. It deliberately identifies received
        # observations across projection views, rather than counting polls.
        self.credit_calls.append((context, selection))
        refs = [ref for row in self.outcomes[context.episode_id] for ref in row.get("progress_refs", ())]
        refs.extend(self.provider.received_progress_refs(context.episode_id, plain(context.scope)))
        baseline = set(context.assignment.get("known_progress_refs", ()))
        identities = {self.provider.observation_identity(ref) for ref in refs}
        identities.difference_update(self.provider.observation_identity(ref) for ref in baseline)
        return {"credit": len(identities)}

    async def execute_tool(self, name, arguments, *, scope, operation_key):
        return await self.tools.execute_async(name, arguments, scope=plain(scope), operation_key=operation_key)

    def remember(self, episode_id, index, selected_tool, result):
        self.outcomes[episode_id].append({"decision_index": index, "selected_tool": selected_tool,
            "status": result["status"], "record_refs": result.get("record_refs", []),
            "changed_record_refs": result.get("changed_record_refs", []),
            "progress_refs": result.get("progress_refs", []), "result_ref": result.get("operation_ref")})


def test_exact_exposed_observations_survive_reopen_and_projection_views_share_identity(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        executions = DurableExecutionStore(tmp_path / "executions")
        target = durable_target(tmp_path, store, executions)
        scope = target["child"]["scope"]
        provider = ProgressProvider(store, executions, run_id=target["run_id"])
        source = store._caller_source({"stage": "fixture_committed"}, "fixture")
        exposure = provider.expose(target["handle"], operation_key="actual-completed",
            committed_record_refs=[source["id"]], provenance_refs=[source["id"]])
        assert provider.expose(target["handle"], operation_key="actual-completed",
            committed_record_refs=[source["id"]], provenance_refs=[source["id"]]) == exposure
        with pytest.raises(ContractError, match="operation_identity_conflict"):
            provider.expose(target["handle"], operation_key="actual-completed")
        hidden = provider.observe(target["handle"], list(FIELDS), scope)
        visible = provider.observe(target["handle"], list(FIELDS), scope,
            permitted_committed_record_types=["source"])
        assert hidden["committed_record_refs"] == [] and visible["committed_record_refs"] == [source["id"]]
        assert hidden["progress_ref"] != visible["progress_ref"]
        assert provider.observation_identity(hidden["progress_ref"]) == provider.observation_identity(visible["progress_ref"])
        assert provider.observe(target["handle"], list(FIELDS), scope) == hidden
        assert provider.read_progress(hidden["progress_ref"], scope) == hidden
        assert provider.resolve(hidden["progress_ref"], scope, "episode_progress")
        assert provider.resolve(target["handle"], scope, "execution_handle")
        assert provider.resolve(content_digest(target), scope, "progress_provenance")
        assert exposure["publication_ref"].startswith("progress_publication_")
        assert provider.resolve(exposure["publication_ref"], scope, "progress_provenance")
        assert provider.resolve(exposure["publication_ref"], scope)
        assert not provider.resolve(exposure["publication_ref"], scope, "episode_progress")
        assert not provider.resolve(exposure["publication_ref"], {
            "subject_refs": scope["subject_refs"], "segments": [{
                "target_ref": scope["subject_refs"][0], "start": 0, "end": 1, "unit": "aa"}]})
        assert hidden["execution_status"]["liveness"] == "unknown"
        assert hidden["measurements"] == hidden["log_windows"] == []
        assert not store.list("observation") and not store.list("assessment")
        with pytest.raises(ContractError, match="unknown_reference"):
            store.get(hidden["progress_ref"])
        saved = deepcopy(hidden)
    with Store(tmp_path / "state") as reopened:
        provider = ProgressProvider(reopened, executions, run_id=target["run_id"])
        assert provider.observe(target["handle"], list(FIELDS), scope) == saved
        # Another connection participates in the same authoritative transaction.
        with pytest.raises(RuntimeError):
            with reopened.transaction():
                provider.expose(target["handle"], operation_key="rolled-back", provenance_refs=[source["id"]])
                raise RuntimeError("fixture interruption")
        assert reopened.db.execute("SELECT count(*) FROM runtime_progress_exposures").fetchone()[0] == 1


def test_exposure_notifications_require_commit_and_recover_after_publication_before_ack(tmp_path, monkeypatch):
    executions = DurableExecutionStore(tmp_path / "executions")
    calls = []
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        target = durable_target(tmp_path, store, executions)
        scope = target["child"]["scope"]
        provider = ProgressProvider(store, executions, run_id=target["run_id"])
        original = executions.record_progress

        def publish_then_interrupt(handle, reference, operation_key):
            assert not store.db.in_transaction
            # A separate connection sees the saved exposure before C2 does.
            with Store(tmp_path / "state") as reader:
                saved = reader.db.execute("SELECT payload FROM runtime_progress_exposures "
                    "WHERE target_handle=? AND operation_key=?", (handle, operation_key)).fetchone()
                assert json.loads(saved[0])["publication_ref"] == reference
            event = original(handle, reference, operation_key)
            calls.append(event)
            raise RuntimeError("fixture crash after C2 publication before local acknowledgment")

        monkeypatch.setattr(executions, "record_progress", publish_then_interrupt)
        with pytest.raises(RuntimeError, match="rollback"):
            with store.transaction():
                provider.expose(target["handle"], operation_key="rolled-back")
                with pytest.raises(ContractError, match="require_committed_transaction"):
                    provider.flush_notifications()
                raise RuntimeError("rollback")
        assert provider.flush_notifications() == {"published": 0, "pending": 0}
        empty = asyncio.run(executions.wait_events(event_condition(target["handle"], "progress_committed",
            reconsider_at=datetime.now(timezone.utc).isoformat())))
        assert empty["events"] == [] and not calls
        with store.transaction():
            exposure = provider.expose(target["handle"], operation_key="committed")
            with pytest.raises(ContractError, match="require_committed_transaction"):
                provider.flush_notifications()
        assert not calls
        with pytest.raises(RuntimeError, match="before local acknowledgment"):
            provider.flush_notifications()
        event, = calls
        assert event["record_ref"] == exposure["publication_ref"]
        assert provider.resolve(event["record_ref"], scope, "progress_provenance")
        assert not provider.resolve(event["record_ref"], scope, "episode_progress")
    monkeypatch.setattr(executions, "record_progress", original)
    with Store(tmp_path / "state") as reopened:
        provider = ProgressProvider(reopened, executions, run_id=target["run_id"])
        assert provider.expose(target["handle"], operation_key="committed") == exposure
        assert provider.flush_notifications() == {"published": 1, "pending": 0}
        assert provider.expose(target["handle"], operation_key="committed") == exposure
        assert provider.flush_notifications() == {"published": 0, "pending": 0}
        assert await_event(executions, target["handle"], "progress_committed")["events"] == [event]
        after = asyncio.run(executions.wait_events(event_condition(target["handle"], "progress_committed",
            after_cursor=event["cursor"], reconsider_at=datetime.now(timezone.utc).isoformat())))
        assert after["events"] == []
        assert not reopened.db.execute("SELECT count(*) FROM runtime_progress_observations").fetchone()[0]
        assert not reopened.db.execute("SELECT count(*) FROM runtime_progress_receipts").fetchone()[0]


def test_selected_direct_relationships_reject_grandchild_fanout_and_foreign_scope(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        executions = DurableExecutionStore(tmp_path / "executions")
        target = durable_target(tmp_path, store, executions)
        child = durable_target(tmp_path, store, executions, key="child", parent=target)
        grandchild = durable_target(tmp_path, store, executions, key="grandchild", parent=child)
        unrelated = durable_target(tmp_path, store, executions, key="other")
        provider = ProgressProvider(store, executions, run_id=target["run_id"])
        scope = target["child"]["scope"]
        def dependency(spec):
            return {"handle": spec["handle"], "kind": "episode", "relation_ref": content_digest(spec),
                "observed_at": "2026-10-21T00:00:00+00:00", "state": "pending"}
        provider.expose(target["handle"], operation_key="selected-child", dependencies=[dependency(child)])
        provider.expose(child["handle"], operation_key="selected-grandchild", dependencies=[dependency(grandchild)])
        assert provider.direct_dependencies(target["handle"], scope) == [dependency(child)]
        binding = MonitorEpisodes(Services(store, provider))
        context = bound(scope, assignment(target["handle"]))
        assert binding.allowed_children(context, ()) == ("monitor",)
        assert binding.prepare_assignment(context, "monitor", assignment(child["handle"]), scope, "selected")["target_handle"] == child["handle"]
        for spec in (grandchild, unrelated):
            with pytest.raises(ContractError, match="not_exposed_direct_dependency"):
                binding.prepare_assignment(context, "monitor", assignment(spec["handle"]), scope, "invalid")
        with pytest.raises(ContractError, match="relationship_mismatch"):
            provider.expose(target["handle"], operation_key="not-direct", dependencies=[dependency(grandchild)])
        with pytest.raises(ContractError, match="outside_scope"):
            provider.observe(target["handle"], list(FIELDS), {"subject_refs": scope["subject_refs"],
                "segments": [{"target_ref": scope["subject_refs"][0], "start": 0, "end": 1, "unit": "aa"}]})
        assert EpisodeBindingRegistry((binding,)).entry_roles == ("monitor",)
        assert binding.credit_kind("monitor") == "monitoring"


def test_form_delivery_is_explicit_typed_idempotent_and_transactional(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        executions = DurableExecutionStore(tmp_path / "executions")
        target = durable_target(tmp_path, store, executions)
        scope = target["child"]["scope"]
        provider = ProgressProvider(store, executions, run_id=target["run_id"])
        observed = provider.observe(target["handle"], list(FIELDS), scope)
        schema = obj({"selected": {"type": "array", "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "episode_progress"}}, "flag": {"type": "string", "enum": ["unresolved"]}})
        form = {"selected": [observed["progress_ref"]], "flag": "unresolved"}
        assert provider.receive_form("science", form, schema, scope, "return-1") == form["selected"]
        assert provider.receive_form("science", form, schema, scope, "return-1") == form["selected"]
        provider.receive_form("science", form, schema, scope, "repeat-return")
        assert provider.received_progress_refs("science", scope) == form["selected"]
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            provider.receive_form("science", {"selected": [], "flag": "unresolved"}, schema, scope, "return-1")
        with pytest.raises(RuntimeError):
            with store.transaction():
                provider.receive_form("rolled-back", form, schema, scope, "return")
                raise RuntimeError
        assert provider.received_progress_refs("rolled-back") == []
        # Generic strings and references with other namespaces confer no
        # progress observation receipt.
        wrong = deepcopy(schema)
        wrong["properties"]["selected"]["items"]["x-reference-namespace"] = "artifact"
        assert provider.receive_form("unrequested", form, wrong, scope, "wrong-namespace") == []


class LiveJob:
    """Actual tiny process; progress comes from its retained stdout bytes."""
    handle = "job:actual-fixture"

    def __init__(self, tmp_path, store, scope):
        self.store, self.target_scope = store, scope
        self.log = tmp_path / "job.stdout"
        self.gate = tmp_path / "job.gate"
        os.mkfifo(self.gate)
        self.stream = self.log.open("wb")
        self.process = subprocess.Popen([sys.executable, "-u", "-c",
            "import sys; print('batch 1 complete', flush=True); open(sys.argv[1],'rb').read(1)", str(self.gate)],
            stdout=self.stream, stderr=subprocess.STDOUT)
        # Readiness bounds this engineering fixture, not a work timeout.
        import time
        deadline = time.monotonic() + 5
        while not self.log.read_bytes():
            assert time.monotonic() < deadline
            time.sleep(0.005)
        data = self.log.read_bytes()
        artifact = store.artifact(data, "text/plain")
        self.source = store.put("source", {"provider": "actual_subprocess_stdout", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="tool")
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.calls = []

    def scope(self, handle):
        if handle != self.handle:
            raise KeyError(handle)
        return self.target_scope

    def direct_dependencies(self, handle, scope):
        self.scope(handle)
        return []

    def observe(self, handle, requested_fields, scope, *, operation_key=None):
        self.scope(handle)
        self.calls.append(handle)
        assert self.process.poll() is None
        data = self.store.get_artifact(self.source["artifact_ref"])
        status = job_status(handle, {"job_ref": handle, "registry_ref": "fixture-registry",
            "state": "running", "outcome": "pending", "elapsed_seconds": None,
            "duration_measure": "systemd_service_wall_seconds", "native_returncode": None,
            "failure_code": None, "resource": None,
            "progress_kind": "native_execution_state_and_output_bytes_not_search_fraction",
            "outputs": [{"role": "native_text", "available": True, "bytes": len(data),
                "writer_closed": False}]}, observed_at=self.timestamp)
        return {"version": "progress_snapshot_v1", "progress_ref": "job_observation_fixture",
            "target_handle": handle, "observed_at": self.timestamp, "provenance_refs": [self.source["id"]],
            "execution_status": status, "measurements": [{"name": "completed_batches", "value": 1,
                "unit": "count", "measured_at": self.timestamp, "provenance_ref": self.source["id"]}],
            "log_windows": [{"source_ref": self.source["id"], "artifact_ref": self.source["artifact_ref"],
                "start_byte": 0, "end_byte": len(data), "observed_at": self.timestamp,
                "content_sha256": hashlib.sha256(data).hexdigest()}], "committed_record_refs": [],
            "dependencies": [], "result_available": True}

    def close(self):
        release_gate(self.gate)
        self.process.wait(timeout=5)
        self.stream.close()


def test_job_exposure_has_committed_identity_without_an_unbound_c2_notification(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        scope = store.validate_scope({"subject_refs": store.problem()["subject_refs"]})
        executions = DurableExecutionStore(tmp_path / "executions")
        job = LiveJob(tmp_path, store, scope)
        try:
            provider = ProgressProvider(store, executions, run_id="job-fixture", job_provider=job)
            def unbound(*_):
                raise AssertionError("job-provider handles have no C2 event binding")
            monkeypatch.setattr(executions, "record_progress", unbound)
            exposure = provider.expose(job.handle, operation_key="actual-log-retained",
                provenance_refs=[job.source["id"]])
            assert provider.expose(job.handle, operation_key="actual-log-retained",
                provenance_refs=[job.source["id"]]) == exposure
            assert provider.resolve(exposure["publication_ref"], scope, "progress_provenance")
            assert not provider.resolve(exposure["publication_ref"], scope, "episode_progress")
            assert provider.flush_notifications() == {"published": 0, "pending": 0}
            assert provider.observe(job.handle, list(FIELDS), scope)["log_windows"][0]["source_ref"] == job.source["id"]
        finally:
            job.close()


class RecursiveConsumer:
    """Actual ordinary Episode consumer; every recursive edge has its own form."""
    def __init__(self, services, binding, scope, selected):
        self.services, self.binding, self.scope, self.selected = services, binding, scope, selected
        self.sources, self.controllers, self.forms, self.decisions = {}, {}, [], []
        def controller(path):
            # Test continuation differs by assignment, not a production quota.
            count = 2 if path[-1] == ("science", "root") or path[-1][1] in {"outer", "middle"} else 3
            value = FixtureController(str(path), 0, count)
            self.controllers[path] = value
            return value
        science = Grain("science", "Assign useful monitoring", "Received progress", controller)
        monitor = Grain("monitor", "Investigate selected exposed progress", "Received progress", controller)
        self.grains = {"science": science, "monitor": monitor}
        self.context = Context(tree=EpisodeTree(science, {science: (monitor,), monitor: (monitor,)},
            self_nesting=("monitor",)), run_id="durable-fixture-run")
        self.form_schema = obj({"progress": binding.fact_sources("monitor")["monitoring_progress_refs"]["report_schema"],
            "state": binding.fact_sources("monitor")["monitoring_execution_state"]["report_schema"],
            "available": binding.fact_sources("monitor")["monitoring_result_available"]["report_schema"],
            "assessment": {"type": "string", "enum": ["work_observed", "unresolved"]}})

    def build(self, role, key, value, *, parent=None, parent_path=(), contract=None):
        path = (*parent_path, (role, key))
        goal = (EpisodeGoal.root(objective="Investigate a selected progress question", result_contract={}) if parent is None
            else EpisodeGoal.child(parent, objective="Resolve requested dependent progress", result_contract=contract.schema))
        identity = Episode.identity(self.context, self.grains[role], key, parent_path=parent_path)
        request = EpisodeRequest(goal, Record({"scope": self.scope, "assignment": value}), contract)
        context = BindingContext("durable-fixture-run", identity.episode_id, role, path, self.scope, value, request.as_record())
        consumer = self
        class Source:
            last = None
            binding_context = context
            def credit(self):
                return Record({"credit": consumer.services.bound_role_credit(context, {})["credit"]})
            def next(self, view):
                inputs = view.model_inputs({"last": self.last, **(consumer.binding.decision_context(context, view)
                    if role == "monitor" else {})}, reports=view.child_reports)
                consumer.decisions.append((key, view.units_consumed, inputs))
                selected = consumer.selected(key, view.units_consumed, inputs)
                index = view.units_consumed
                operation = f"{context.episode_id}:{index}"
                if selected["kind"] == "child":
                    target = selected["assignment"]
                    if role == "monitor":
                        target = consumer.binding.prepare_assignment(context, "monitor", target, consumer.scope, operation)
                    child_contract = TypedReportContract("Return requested measured progress with a constrained interpretation",
                        consumer.form_schema, lambda ref, namespace: consumer.services.reference_in_scope(ref, consumer.scope, namespace))
                    child = consumer.build("monitor", selected["key"], target,
                        parent=goal, parent_path=path, contract=child_contract)
                    def receive(result, *_):
                        form = result.as_record()["form"]
                        child_context = child.source.binding_context
                        consumer.binding.validate_report(child_context, form, child_contract.schema)
                        refs = consumer.services.provider.receive_form(context.episode_id, form,
                            child_contract.schema, consumer.scope, operation)
                        consumer.forms.append((key, selected["key"], form))
                        self.last = {"status": "completed", "progress_refs": refs}
                        consumer.services.remember(context.episode_id, index, None, self.last)
                        return self.credit()
                    return ChildEpisodeUnit(child, receive, lambda result, *_: result.as_record()["form"])
                async def perform(_):
                    if role == "science":
                        # The scientific parent uses its requested closed form
                        # while the monitored target is still executing.
                        form, = inputs["child_reports"]
                        assert form["available"] is False and form["state"] == "executing"
                        self.last = {"status": "completed", "record_refs": []}
                    else:
                        self.last = await consumer.binding.execute(context, selected["tool"], selected["arguments"], operation)
                        assert self.last["status"] == "completed", self.last
                    consumer.services.remember(context.episode_id, index, selected.get("tool"), self.last)
                    return self.credit()
                return Leaf(None, perform, lambda _, result: result, label=selected["kind"])
            def finish(self, record):
                if contract is None:
                    return self.credit()
                facts = consumer.binding.facts(context, {"completion": {"ended_by": record.ended_by,
                    "end_reason": record.end_reason, "units_consumed": record.units_consumed}})
                return Record({"form": form_with_facts({"assessment": "work_observed"}, contract.schema, facts)})
        source = Source()
        self.sources[path] = source
        return Episode(self.grains[role], key, source, request, source.finish)


def test_recursive_monitors_return_their_original_forms_while_actual_targets_remain_active(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        executions = DurableExecutionStore(tmp_path / "executions")
        gate = tmp_path / "target.gate"
        os.mkfifo(gate)
        target = durable_target(tmp_path, store, executions, arguments={"gate": str(gate)})
        middle = durable_target(tmp_path, store, executions, key="middle", parent=target)
        unselected = durable_target(tmp_path, store, executions, key="not-selected", parent=target)
        scope = target["child"]["scope"]
        executions.start(target["handle"])
        await_event(executions, target["handle"], "progress_committed")
        job = LiveJob(tmp_path, store, scope)
        try:
            provider = ProgressProvider(store, executions, run_id=target["run_id"], job_provider=job)
            def dep(spec):
                return {"handle": spec["handle"], "kind": "episode", "relation_ref": content_digest(spec),
                    "observed_at": job.timestamp, "state": "pending"}
            provider.expose(target["handle"], operation_key="actual-direct-commissions",
                dependencies=[dep(middle), dep(unselected)])
            provider.expose(middle["handle"], operation_key="actual-job-submission", dependencies=[{
                "handle": job.handle, "kind": "job", "relation_ref": job.source["id"],
                "observed_at": job.timestamp, "state": "executing"}])
            services = Services(store, provider)
            binding = MonitorEpisodes(services, outcome_page_size=1)
            original_job_observations = []
            def choose(key, index, inputs):
                if key == "root":
                    if index == 0:
                        return {"kind": "child", "key": "outer", "assignment": assignment(target["handle"])}
                    assert len(inputs["child_reports"]) == 1
                    return {"kind": "integrate"}
                if key in {"outer", "middle"} and index == 0:
                    deps = inputs["monitor_direct_dependencies"]
                    selected = middle["handle"] if key == "outer" else job.handle
                    assert selected in [row["handle"] for row in deps]
                    return {"kind": "child", "key": "middle" if key == "outer" else "job",
                        "assignment": assignment(selected)}
                if key == "job" and index == 1:
                    snapshot = inputs["last"]["result"]
                    assert snapshot["measurements"][0]["value"] == 1
                    original_job_observations.append(deepcopy(snapshot))
                    return {"kind": "tool", "tool": "progress.log", "arguments": {
                        "progress_ref": snapshot["progress_ref"], "log_index": 0}}
                if key == "job" and index == 2:
                    assert inputs["last"]["result"]["text"] == "batch 1 complete\n"
                    job.timestamp = datetime.now(timezone.utc).isoformat()
                if key in {"outer", "middle"}:
                    assert inputs["child_reports"][0]["assessment"] == "work_observed"
                return {"kind": "tool", "tool": "progress.observe", "arguments": {"requested_fields": list(FIELDS)}}
            consumer = RecursiveConsumer(services, binding, scope, choose)
            root = consumer.build("science", "root", {})
            result = asyncio.run(root.run_async(consumer.context))
            assert result.units_consumed == 2
            assert len(consumer.forms) == 3
            assert len(consumer.sources) == 4
            assert [row[1] for row in consumer.forms] == ["job", "middle", "outer"]
            assert all(set(form) == {"progress", "state", "available", "assessment"} for _, _, form in consumer.forms)
            assert executions.status(target["handle"])["liveness"] == "live"
            assert job.process.poll() is None
            assert executions.status(unselected["handle"])["lifecycle_state"] == "pending"
            assert not provider._exposures(unselected["handle"])
            assert job.calls == [job.handle, job.handle]
            assert sum(len(controller.scores) for controller in consumer.controllers.values()) == 9
            # The repeated job snapshot contributes once. Child turns do not
            # become three scientific-parent observations.
            leaf_controller = next(controller for path, controller in consumer.controllers.items() if path[-1][1] == "job")
            assert leaf_controller.scores == [1, 0, 0]
            original, = original_job_observations
            assert provider.observe(job.handle, list(FIELDS), scope) == original
            root_form = consumer.forms[-1][2]
            assert root_form["state"] == "executing" and root_form["available"] is False
            assert len(root_form["progress"]) == 3
            assert not store.list("observation") and not store.list("assessment")
        finally:
            job.close()
            release_gate(gate)
            assert returned(executions, target)["outcome"] == "closed"
        closed = provider.observe(target["handle"], list(FIELDS), scope)
        assert closed["execution_status"]["lifecycle_state"] == "returned" and closed["result_available"]
        assert root_form["state"] == "executing" and root_form["available"] is False


def test_run_workflow_consumes_selected_recursive_forms_and_actual_retained_job_progress(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        scope = store.validate_scope({"subject_refs": store.problem()["subject_refs"]})
        directory = tmp_path / "run"
        executions = DurableExecutionStore(directory / "episode-execution")
        gate = tmp_path / "target.gate"
        os.mkfifo(gate)
        job = LiveJob(tmp_path, store, scope)
        targets, retained, controllers, selections, delivered = {}, {}, {}, [], []
        binding = MonitorEpisodes(None, outcome_page_size=1)
        definitions = binding.fact_sources("monitor")
        schema = obj({
            "progress": definitions["monitoring_progress_refs"]["report_schema"],
            "state": definitions["monitoring_execution_state"]["report_schema"],
            "available": definitions["monitoring_result_available"]["report_schema"],
            "assessment": {"type": "string", "enum": ["work_observed", "unresolved"]}})

        def provider_for(run_id):
            if run_id not in retained:
                retained[run_id] = ProgressProvider(store, executions, run_id=run_id, job_provider=job)
            return retained[run_id]

        def project(context, selection):
            # Explicit fixture units supplied through the supported caller port.
            # Projection consumes actual C7 receipt/outcome selection, without
            # deriving a second scientific score or counting read timestamps.
            selections.append((context, deepcopy(selection)))
            progress = provider_for(context.run_id)
            known = {progress.observation_identity(ref, scope) for ref in selection["known_progress_refs"]}
            baseline = {progress.observation_identity(ref, scope) for ref in selection["initial_progress_refs"]}
            return {"credit": len(known - baseline)}

        def controller(path, initial):
            value = FixtureController(str(path), initial, 3 if len(path) == 4 else 2)
            controllers[path] = value
            return value

        def child(handle):
            return {"selection": {"kind": "episode_child", "role": "monitor",
                "assignment": assignment(handle), "goal": "Investigate the selected exposed progress",
                "scope": scope, "purpose": "Return original observations and constrained progress interpretation",
                "schema_json": json.dumps(schema), "initial_report_json": '{"assessment":"unresolved"}'},
                "report_update": {}}

        def observe(context):
            if context["child_reports"]:
                form, = context["child_reports"]
                assert form["assessment"] == "work_observed"
                assert form["available"] is (form["state"] == "executing"
                    and context["monitor_assignment"]["target_handle"] == targets["middle"]["handle"])
                delivered.append(form)
            return {"selection": {"kind": "tool", "tool": "progress.observe",
                "arguments": {"requested_fields": list(FIELDS)}}, "report_update": {"assessment": "work_observed"}}

        def select_dependency(context, handle):
            assert handle in {row["handle"] for row in context["monitor_direct_dependencies"]}
            return child(handle)

        def read_job_log(context):
            snapshot = context["last_local_outcome"]["result"]
            assert snapshot["measurements"][0]["value"] == 1
            return {"selection": {"kind": "tool", "tool": "progress.log", "arguments": {
                "progress_ref": snapshot["progress_ref"], "log_index": 0}}, "report_update": {"assessment": "work_observed"}}

        def repeat_job_observation(context):
            assert context["last_local_outcome"]["result"]["text"] == "batch 1 complete\n"
            job.timestamp = datetime.now(timezone.utc).isoformat()
            return observe(context)

        def science_uses_form(context):
            form, = context["child_reports"]
            assert set(form) == {"progress", "state", "available", "assessment"}
            assert form["state"] == "executing" and form["available"] is False
            assert len(form["progress"]) == 3
            assert executions.status(targets["target"]["handle"])["liveness"] == "live"
            assert job.process.poll() is None
            delivered.append(form)
            return {"selection": {"kind": "tool", "tool": "episode.history",
                "arguments": {"view": "records", "decision_indices": [0]}}, "report_update": {}}

        class ApplicationProvider(ScriptedProvider):
            async def complete(self, *args, **kwargs):
                if not targets:
                    run_id = json.loads((directory / "run.json").read_text())["run_id"]
                    targets["target"] = durable_target(tmp_path, store, executions,
                        run_id=run_id, arguments={"gate": str(gate)})
                    for key in ("middle", "unselected"):
                        targets[key] = durable_target(tmp_path, store, executions, key=key,
                            parent=targets["target"], run_id=run_id)
                    executions.start(targets["target"]["handle"])
                    await asyncio.wait_for(executions.wait_events(event_condition(
                        targets["target"]["handle"], "progress_committed")), 10)
                    progress = provider_for(run_id)
                    progress.expose(targets["target"]["handle"], operation_key="selected-direct-commissions",
                        dependencies=[{"handle": targets[key]["handle"], "kind": "episode",
                            "relation_ref": content_digest(targets[key]), "observed_at": job.timestamp,
                            "state": "pending"} for key in ("middle", "unselected")])
                    progress.expose(targets["middle"]["handle"], operation_key="selected-job-submission",
                        dependencies=[{"handle": job.handle, "kind": "job", "relation_ref": job.source["id"],
                            "observed_at": job.timestamp, "state": "executing"}])
                    assert progress.flush_notifications() == {"published": 2, "pending": 0}
                return await super().complete(*args, **kwargs)

        scripted = ApplicationProvider([
            lambda context: child(targets["target"]["handle"]),
            lambda context: select_dependency(context, targets["middle"]["handle"]),
            lambda context: select_dependency(context, job.handle),
            observe, read_job_log, repeat_job_observation, observe, observe, science_uses_form])
        try:
            summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=scripted,
                run_dir=directory, controller_factory=controller, project_credit=lambda store, scope: 0,
                episode_binding_descriptors=[binding.as_record()],
                role_credit_bindings={"monitor": {"definition": {"kind": "fixture_unique_observation",
                    "units": "fixture_information"}, "project": project}}, job_progress_provider=job))
            progress = provider_for(summary["run_id"])
            assert summary["completed_actions"] == 2 and summary["episode_count"] == 4
            assert len(scripted.contexts) == 9 and len(delivered) == 3
            assert [len(value.scores) for path, value in sorted(controllers.items(), key=lambda item: len(item[0]))] == [2, 2, 2, 3]
            leaf = next(value for path, value in controllers.items() if len(path) == 4)
            assert leaf.scores == [1, 0, 0]
            assert all(not selection["known_record_refs"] for _, selection in selections)
            assert job.calls == [job.handle, job.handle]
            root_id = EpisodeRef(summary["run_id"], (("annotation", "root"),)).episode_id
            assert progress.received_progress_refs(root_id, scope) == delivered[-1]["progress"]
            assert executions.status(targets["unselected"]["handle"])["lifecycle_state"] == "pending"
            assert not progress._exposures(targets["unselected"]["handle"])
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE run_id=?",
                (summary["run_id"],)).fetchone()[0] == 9
            assert not store.list("assessment") and not store.list("observation")
        finally:
            job.close()
            if "target" in targets:
                release_gate(gate)
                assert returned(executions, targets["target"])["outcome"] == "closed"


def test_monitor_rejects_undelivered_refs_unrestricted_forms_and_modified_recorded_facts(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        executions = DurableExecutionStore(tmp_path / "executions")
        target = durable_target(tmp_path, store, executions)
        scope = target["child"]["scope"]
        provider = ProgressProvider(store, executions, run_id=target["run_id"])
        services = Services(store, provider)
        binding = MonitorEpisodes(services)
        observed = provider.observe(target["handle"], list(FIELDS), scope)
        context = bound(scope, assignment(target["handle"]))
        failed = asyncio.run(binding.execute(context, "progress.read", {"progress_ref": observed["progress_ref"]}, "unreceived"))
        assert failed["feedback"]["code"] == "monitor_progress_not_received"
        with pytest.raises(ReportBoundaryError, match="unavailable"):
            binding.validate_report(context, {"progress": [observed["progress_ref"]]}, obj({"progress": {
                "type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "episode_progress"}}}))
        with pytest.raises(ReportBoundaryError, match="semantic type"):
            binding.validate_report(context, {"findings": "unrestricted"}, obj({"findings": {"type": "string"}}))
        schema = obj({"state": binding.fact_sources("monitor")["monitoring_execution_state"]["report_schema"]})
        with pytest.raises(ContractError, match="recorded_fact_mismatch"):
            binding.validate_report(context, {"state": "executing"}, schema)
        assert binding.facts(context, {})["monitoring_execution_state"] is None
        assert binding.credit_view(context, {}) == {"credit": 0}
        assert len(services.credit_calls) == 1
        assert "reason" not in binding.permitted_common_actions(context)
