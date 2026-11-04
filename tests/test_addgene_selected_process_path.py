"""Selected shared-loop Addgene metadata delivery over retained response bytes.

Provider choices and parent/scientific continuation are engineering fixtures.
Resource roles use the actual configured yield controller. No live service,
authenticated sequence bases, target relationship or scientific closure is claimed.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
import hashlib
import io
import json
from pathlib import Path

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode import addgene_sequence_facts as facts
from gene_annotation_episode import addgene_sequence_native as native
from gene_annotation_episode import addgene_sequence_returns as returns
from gene_annotation_episode import sequence_support_publication as publication
from gene_annotation_episode.addgene_sequence_facts import FACT_SOURCE, ADDGENE_SEQUENCE_FACTS_SCHEMA
from gene_annotation_episode.api_sequence_support import COLLECT
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import (NumericBand, YieldController, YieldEstimate,
    YieldParameters, estimate_score_yield)
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
FIXTURES = Path(__file__).parent / "fixtures/addgene_sequence_page"
ENTITY_SHA = "deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d"
METADATA_SHA = "ae1e05538cb541d5e1ad6a6610e690204e8d426066ba6432494c72ef62aa0e06"
QUESTION = ("For Addgene plasmid 50005, what does the retained response report for selected native "
    "sequence records 2, 0 and 99, and which records require authentication or remain unavailable?")
REQUEST = {"operation": "get_plasmid_sequence", "provider": "addgene",
    "plasmid_id": "50005", "max_bytes": 4194304}
SELECTOR = {"view": "sequences", "record_ordinals": [2, 0, 99]}
RESOURCES = {"addgene": {"kind": "api", "service": "sequence_support"}}
SELECTED_TOOLS = [{"name": name, "resources": "api"}
    for name in ("get_plasmid_sequence", COLLECT)]


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


PARENT_FORM = _object({"metadata": deepcopy(ADDGENE_SEQUENCE_FACTS_SCHEMA)})
HANDOFF_FORM = _object({"references": {"type": "array", "uniqueItems": True,
    "items": {"type": "string", "format": "reference", "x-reference-namespace": "execution_handoff"},
    "x-source": "execution_handoff_refs"}})
RESULT_FORM = _object({"metadata": deepcopy(ADDGENE_SEQUENCE_FACTS_SCHEMA),
    "completed": {"type": "boolean", "x-source": "execution_completed"},
    "references": {"type": "array", "uniqueItems": True,
        "items": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "x-source": "execution_result_refs"}, "credit": {"type": "number", "x-source": "credit"}})


def _child(role, assignment, scope, schema):
    return {"report_update": {}, "selection": {"kind": "episode_child", "role": role,
        "goal": QUESTION, "purpose": "Return the explicitly assigned retained Addgene metadata",
        "scope": deepcopy(scope), "assignment": deepcopy(assignment),
        "schema_json": json.dumps(schema), "initial_report_json": "{}"}}


def _wait():
    return {"report_update": {}, "selection": {"kind": "wait", "condition": {
        "version": "event_condition_v1", "events": [],
        "reconsider_at": datetime.now(timezone.utc).isoformat()}}}


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _keys(item)


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


def _files(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()}


class _SelectedRun:
    def __init__(self, store, directory, *, scope=None):
        self.store, self.directory, self.run_id = store, Path(directory), "addgene-selected-process-fixture"
        self.scope = (deepcopy(scope) if scope is not None else {"subject_refs":
            store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]})
        self.calls, self.contexts, self.controllers = {}, [], {}
        self.handoff = self.scientific_after = self.root_after = None
        self.api_assignment = {"version": "api_service_assignment_v1", "resource_id": "addgene",
            "service": "sequence_support", "request": deepcopy(REQUEST), "endpoint": "usable_handoff",
            "constraints": {"allowed_resource_ids": ["addgene"], "allowed_kinds": ["api"]}}
        self.launch_assignment = {"version": "execution_launch_assignment_v1",
            "requests": {"addgene": deepcopy(self.api_assignment)}, "immutable_input_versions": [],
            "constraints": {"allowed_resource_ids": ["addgene"], "allowed_kinds": ["api"]}}
        tools = ToolRegistry(store, clients=PublicClients(ncbi_email=None))
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=self.run_id, directory=self.directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        self.library = ScientificProcessLibrary(self.directory / "scientific-process-library")

        def controller(path, initial):
            role = path[-1][0]
            if role in {"annotation", "scientific_process"}:
                def engineering(history, parameters, contexts):
                    required = 2 if role == "annotation" else 3
                    return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= required else 1),
                        parameters, {"fixture": "engineering_parent_scientific_continuation_only"})
                value = YieldController(str(path), initial, 0, YieldParameters(100, 50),
                    estimate_with_context=engineering)
            else:
                # No resource estimator, cap or forced completion: the real
                # configured controller sees the actual gains and ordinary waits.
                value = YieldController(str(path), initial, 5, YieldParameters(2, 1, .5))
            self.controllers[path] = value
            return value

        self.workflow = Workflow(store, tools, self, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=(self.descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[])
        self.episode = self.workflow.build("annotation", "root", QUESTION, self.scope)

    def context(self, episode_id):
        row = self.store.db.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.run_id, episode_id)).fetchone()
        path, request = tuple(map(tuple, json.loads(row["path"]))), json.loads(row["request"])
        message = request["message"]
        return BindingContext(self.run_id, episode_id, path[-1][0], path, message["scope"],
            message.get("episode_assignment", {}), request)

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        count = self.calls[episode_id]
        self.contexts.append((episode_id, deepcopy(current)))
        assert current.get("feedback") is None, current.get("feedback")
        assert not {returns.OWN_BINDINGS, returns.CLOSURE_PREFIX}.intersection(_keys(current))
        assignment = current.get("execution_assignment", {})
        if assignment.get("version") == "execution_launch_assignment_v1":
            assert count == 1 and assignment == self.launch_assignment
            return _child("launch_api", self.api_assignment, self.scope, HANDOFF_FORM)
        if assignment.get("version") == "api_service_assignment_v1":
            assert count == 1 and assignment == self.api_assignment
            return {"report_update": {}, "selection": {"kind": "tool", "tool": "get_plasmid_sequence", "arguments": {}}}
        if assignment.get("version") == "execution_results_assignment_v1":
            assert assignment == {"version": "execution_results_assignment_v1",
                "handoff_ref": self.handoff, "selector": SELECTOR}
            if count == 1:
                return {"report_update": {}, "selection": {"kind": "tool", "tool": COLLECT, "arguments": {}}}
            return _wait()
        if "scientific_process" in current:
            if count == 1:
                return _child("launch", self.launch_assignment, self.scope, HANDOFF_FORM)
            if count == 2:
                self.handoff, = current["child_reports"][-1]["references"]
                return _child("results", {"version": "execution_results_assignment_v1",
                    "handoff_ref": self.handoff, "selector": SELECTOR}, self.scope, RESULT_FORM)
            assert count == 3
            self.scientific_after = deepcopy(current)
            return _wait()
        if count == 1:
            assignment = {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": self.library.reference("A101"), "thought_pattern": self.library.reference("P01"),
                "child_tool_info": deepcopy(SELECTED_TOOLS)}, "evidence_refs": list(self.scope["subject_refs"]),
                "constraints": {"preserve_original_request": True}, "context": {"question": QUESTION,
                    "selected_native_request": deepcopy(REQUEST), "selected_native_ordinals": [2, 0, 99]}}
            return _child("scientific_process", assignment, self.scope, PARENT_FORM)
        assert count == 2
        self.root_after = deepcopy(current)
        return _wait()

    async def release(self, episode_id):
        return None

    def run(self):
        async def execute():
            record = await self.episode.run_async(self.workflow.context)
            result = await self.episode.build_result(record)
            return record, result
        self.record, self.result = asyncio.run(execute())
        self.archive = json.loads("".join(iter_json(self.record.as_record())))
        return self.archive


def test_selected_process_retained_addgene_metadata_partial_return_and_closed_replay(tmp_path, monkeypatch):
    entity, metadata = (FIXTURES / "addgene50005.entity").read_bytes(), (FIXTURES / "addgene50005.json").read_bytes()
    assert len(entity) == 211547 and hashlib.sha256(entity).hexdigest() == ENTITY_SHA
    assert hashlib.sha256(metadata).hexdigest() == METADATA_SHA
    retained = json.loads(metadata)
    assert retained["sha256"] == ENTITY_SHA and retained["body_complete"] is True
    transport_calls = []
    installed_controllers = {}
    original_controller = Workflow.controller

    def controller(workflow, path):
        installed = original_controller(workflow, path)
        installed_controllers[id(workflow), path] = installed.controller
        return installed

    monkeypatch.setattr(Workflow, "controller", controller)

    class Response:
        status = 200

        def __init__(self):
            self.body, self.headers = io.BytesIO(entity), Message()
            self.headers["Content-Type"] = "text/html; charset=utf-8"
            self.headers["Content-Length"] = str(len(entity))

        def __enter__(self): return self
        def __exit__(self, *_): return False
        def geturl(self): return "https://www.addgene.org/50005/sequences/"
        def read(self, size=-1): return self.body.read(size)

    def open_response(request, *, timeout):
        assert not transport_calls, "selected collect or replay repeated acquisition"
        assert request.full_url == "https://www.addgene.org/50005/sequences/"
        assert request.get_method() == "GET" and request.data is None and timeout == 90
        headers = {key.lower(): value for key, value in request.header_items()}
        assert headers["accept"] == "text/html"
        transport_calls.append({"method": "GET", "url": request.full_url, "timeout": timeout})
        return Response()

    def forbidden(*args, **kwargs):
        raise AssertionError("closed Addgene Workflow attempted parser, publication, model or transport work")

    monkeypatch.setattr("urllib.request.urlopen", open_response)
    monkeypatch.setattr("socket.create_connection", forbidden)
    with Store(tmp_path / "state") as store:
        run = _SelectedRun(store, tmp_path / "run")
        run.run()
        episodes = list(store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=?", (run.run_id,)))
        contexts = {row["episode_id"]: run.context(row["episode_id"]) for row in episodes}
        by_role = {role: [context for context in contexts.values() if context.role == role]
            for role in ("annotation", "scientific_process", "launch", "launch_api", "results")}
        assert all(len(values) == 1 for values in by_role.values())
        root_context, science, launch, launch_api, result_context = [by_role[role][0]
            for role in ("annotation", "scientific_process", "launch", "launch_api", "results")]
        executor = run.workflow.episode_bindings.for_role("results")
        api = executor.api_execution
        frozen = {row["episode_id"]: {"facts": json.loads(row["facts"]), "form": json.loads(row["form"])}
            for row in store.db.execute("SELECT * FROM runtime_forms WHERE run_id=?", (run.run_id,))}
        assert root_context.episode_id not in frozen, "root has an incoming typed return, no outgoing contract"
        result_facts, result_form = frozen[result_context.episode_id]["facts"], frozen[result_context.episode_id]["form"]
        science_facts, science_form = frozen[science.episode_id]["facts"], frozen[science.episode_id]["form"]
        assert returns.OWN_BINDINGS in result_facts and returns.CLOSURE_PREFIX not in result_facts
        assert returns.CLOSURE_PREFIX in science_facts and returns.OWN_BINDINGS not in science_facts
        assert not {returns.OWN_BINDINGS, returns.CLOSURE_PREFIX}.intersection(_keys(result_form))
        assert not {returns.OWN_BINDINGS, returns.CLOSURE_PREFIX}.intersection(_keys(science_form))
        assert result_form["completed"] is result_facts["execution_completed"] is False
        assert result_form["credit"] == result_facts["credit"] == 2
        public = result_facts[FACT_SOURCE]
        assert result_form["metadata"] == science_form["metadata"] == public
        assert run.scientific_after["child_reports"][-1] == result_form
        assert run.root_after["child_reports"][-1] == science_form == {"metadata": public}
        assert executor.received_report_facts(science)[FACT_SOURCE] == public
        assert api.addgene_returns.received_context(root_context) == {FACT_SOURCE: public}
        fact, = public
        assert fact["requested_id"] == "50005" and fact["authentication_required"] is True
        assert fact["parse_status"] == "partial" and fact["response_complete"] is True
        selected = fact["selected_rows"]
        assert [row["selection_ordinal"] for row in selected] == [0, 1, 2]
        assert [row["record_ordinal"] for row in selected] == [2, 0, 99]
        assert [row["status"] for row in selected] == ["authentication_required", "authentication_required", "unavailable"]
        assert [row["native_record"]["sequence_id"] for row in selected[:2]] == ["91449", "513490"]
        assert [row["native_record"]["source_completeness"] for row in selected[:2]] == ["partial", "full"]
        assert all(row["native_record"]["source_verification"] == "addgene_verified" for row in selected[:2])
        assert all(row["sequence_file_ref"] is row["symbol_count"] is None for row in selected)
        assert all(row["native_record"]["sequence"] is None for row in selected[:2])
        assert selected[2]["native_record"] is None and selected[2]["issue_codes"] == ["selected_record_unavailable"]
        assert result_form["references"] == [fact["source_ref"]]
        source = store.get(fact["source_ref"])
        assert source["provider"] == "addgene" and source["origin"] == "external"
        assert store.get_artifact(source["artifact_ref"]) == entity
        assert len(transport_calls) == 1
        tools = plain(science.assignment)["selection"]["child_tool_info"]
        assert [{"name": row["name"], "resources": row["resources"]} for row in tools] == SELECTED_TOOLS
        assert all(set(row) == {"name", "description", "resources", "instructions"} for row in tools)
        assert plain(launch_api.assignment)["request"] == REQUEST
        assert plain(result_context.assignment)["selector"] == SELECTOR
        actions = {context.role: [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",
            (run.run_id, context.episode_id))] for context in contexts.values()}
        result_actions = [json.loads(row["action"]) for row in actions["results"]]
        assert result_actions[0] == {"kind": "tool", "tool": COLLECT, "arguments": {}}
        assert len(result_actions) >= 2 and all(row["kind"] == "wait" for row in result_actions[1:])
        collect_outcome = json.loads(actions["results"][0]["result"])
        assert collect_outcome["status"] == "partial"
        assert all(json.loads(row["result"])["record_refs"] == [] for row in actions["results"][1:])
        caller_controller = run.controllers[result_context.path]
        assert caller_controller.estimator.estimate_with_context is None
        resource_controller = installed_controllers[id(run.workflow), result_context.path]
        assert resource_controller.cost == 5 and resource_controller.settings == YieldParameters(2, 1, .5)
        practical = resource_controller.estimator.estimate_with_context
        assert type(practical) is PracticalYieldEstimator
        assert practical.base_estimate is estimate_score_yield
        assert practical.as_record()["version"] == "verified_practical_endpoint_yield_v1"
        state = resource_controller.state()
        assert state.decision.stop is True and state.current_credit == 2
        assert list(state.history) == [2] + [0] * (len(result_actions) - 1)
        assert state.estimate.diagnostics["fitting_scope"] == "full_history"
        assert all(context is None or context.get("practical_completion") is None
            for context in resource_controller.estimator.contexts)
        assert len(actions["launch"]) == len(actions["launch_api"]) == 1
        assert len(actions["scientific_process"]) == 3 and len(actions["annotation"]) == 2
        for context in contexts.values():
            n = len(actions[context.role])
            for table in ("runtime_observations", "runtime_model_calls"):
                assert store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                    (run.run_id, context.episode_id)).fetchone()[0] == n
        for _, current in run.contexts:
            assert not {returns.OWN_BINDINGS, returns.CLOSURE_PREFIX}.intersection(_keys(current))
        rows_before = _tables(store)
        for fault in ("status", "source"):
            forged = deepcopy(science_form)
            if fault == "status": forged["metadata"][0]["selected_rows"][0]["status"] = "available"
            else: forged["metadata"][0]["source_ref"] = run.handoff
            with pytest.raises(ReportBoundaryError):
                run.workflow.validate_report(forged, run.scope, grain="scientific_process",
                    schema=PARENT_FORM, context=science)
            assert _tables(store) == rows_before
        selection = run.workflow.services.record_selection(result_context)
        credit = executor.project_credit(result_context, selection)
        assert credit["credit"] == 2
        replay_credit_calls, original_credit = [], ExecutionEpisodes.project_credit
        replay_callbacks, active_validation = [], []
        phase = "explicit_credit_before_replay"
        original_initialize = ExecutionEpisodes.initialize
        original_validate = ExecutionEpisodes.validate_report
        original_own_closed = returns.AddgeneSequenceReturns._own_closed

        def closed_credit(owner, context, receiver_selection):
            replay_credit_calls.append({"phase": phase, "role": context.role})
            return original_credit(owner, context, receiver_selection)

        def initialize(owner, context):
            result = original_initialize(owner, context)
            replay_callbacks.append({"phase": phase, "callback": "initialize",
                "episode_id": context.episode_id, "role": context.role})
            return result

        def validate(owner, context, form, schema):
            entry = {"phase": phase, "callback": "validate_report",
                "episode_id": context.episode_id, "role": context.role,
                "schema_fields": sorted(plain(schema).get("properties", {})),
                "schema_mode": ("full" if plain(schema) == plain(context.request)[
                    "report_contract"]["measurements"]["schema"] else "stripped")}
            active_validation.append(entry)
            try:
                result = original_validate(owner, context, form, schema)
            finally:
                active_validation.pop()
            replay_callbacks.append(entry)
            return result

        def own_closed(owner, context, closed, rows):
            result = original_own_closed(owner, context, closed, rows)
            replay_callbacks.append({"phase": phase, "callback": "own_closed",
                "episode_id": context.episode_id, "role": context.role,
                "validation_schema_mode": (active_validation[-1]["schema_mode"]
                    if active_validation else None)})
            return result

        monkeypatch.setattr(ExecutionEpisodes, "project_credit", closed_credit)
        monkeypatch.setattr(ExecutionEpisodes, "initialize", initialize)
        monkeypatch.setattr(ExecutionEpisodes, "validate_report", validate)
        monkeypatch.setattr(returns.AddgeneSequenceReturns, "_own_closed", own_closed)
        for owner, name in ((native, "read_addgene_sequences"), (facts, "build_addgene_sequence_fact"),
                (returns, "build_addgene_sequence_fact"), (returns, "read_sequence_support_publication"),
                (publication, "read_sequence_support_publication"), (publication, "publish_sequence_support"),
                (publication, "_publish"), (PublicClients, "_http")):
            monkeypatch.setattr(owner, name, forbidden)
        monkeypatch.setattr("urllib.request.urlopen", forbidden)
        assert executor.project_credit(result_context, selection) == credit
        rows_before, run_files, artifact_files = _tables(store), _files(run.directory), _files(store.path / "artifacts")
        old_archive, changes = deepcopy(run.archive), store.db.total_changes
        phase = "fresh_root_constructor"
        replay = _SelectedRun(store, run.directory, scope=run.scope)
        monkeypatch.setattr(replay, "complete", forbidden)
        phase = "fresh_root_run"
        assert replay.run() == old_archive
        root_replay_callbacks = [row for row in replay_callbacks
            if row["phase"] in {"fresh_root_constructor", "fresh_root_run"}]
        result_reconstructed = any(row["callback"] == "initialize" and row["role"] == "results"
            for row in root_replay_callbacks)
        if result_reconstructed:
            assert any(row["callback"] == "validate_report" and row["role"] == "results"
                and row["schema_mode"] == "stripped" and row["schema_fields"] == []
                for row in root_replay_callbacks)
            assert any(row["callback"] == "own_closed" and row["role"] == "results"
                and row["validation_schema_mode"] == "stripped" for row in root_replay_callbacks)
        phase = "explicit_credit_after_replay"
        replay_executor = replay.workflow.episode_bindings.for_role("results")
        assert replay_executor.project_credit(replay.context(result_context.episode_id),
            replay.workflow.services.record_selection(replay.context(result_context.episode_id))) == credit
        assert any(row == {"phase": "explicit_credit_after_replay", "role": "results"}
            for row in replay_credit_calls)
        assert _tables(store) == rows_before
        assert _files(run.directory) == run_files and _files(store.path / "artifacts") == artifact_files
        assert len(transport_calls) == 1 and store.count("annotation") == store.count("observation") == 0
        (tmp_path / "ADDGENE_SELECTED_PROCESS.json").write_text(json.dumps(dict(
            qualification="scripted selected Workflow over retained Addgene metadata; no live service or authenticated bases",
            fixture_sha256={"entity": ENTITY_SHA, "metadata": METADATA_SHA}, question=QUESTION,
            request=REQUEST, selector=SELECTOR, source_ref=fact["source_ref"], handoff_ref=run.handoff,
            typed_result=result_form, onward_typed_return=science_form,
            own_bindings=result_facts[returns.OWN_BINDINGS], closure_prefix=science_facts[returns.CLOSURE_PREFIX],
            resource_action_count=len(result_actions), resource_controller=state.as_record(),
            resource_estimator=practical.as_record(), transport_calls=transport_calls,
            replay_credit_calls=replay_credit_calls, replay_callbacks=replay_callbacks,
            root_replay_reconstructed_results=result_reconstructed,
            replay_scope="Actual callback roles/schema modes are recorded; manual credit checks are separate",
            replay_total_changes_delta=store.db.total_changes-changes,
            closed_replay_tables_forms_observations_and_files_unchanged=True), indent=2) + "\n")
