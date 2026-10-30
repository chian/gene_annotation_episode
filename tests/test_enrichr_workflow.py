"""Actual Workflow custody with scripted choices and engineering HTTP bodies.

The full-loop cases exercise registered services and production episode
construction. They use no live model or Enrichr service and establish no gene
function. The separate partial case exercises report/admission components with
explicit selected-row fixtures; it does not claim a completed resource loop.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from method_loop.archive import iter_json
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.enrichr_contracts import TABLE_SOURCE, ROW_SOURCE, enrichr_fact_sources
from gene_annotation_episode.enrichr_returns import OWN_WITNESSES
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_enrichr_returns import Harness, source_only_schema


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
RESOURCES = {"enrichr": {"kind": "api", "service": "enrichr",
    "protocol_profile": "standard_enrichr_v1", "base_url": "https://enrichr.invalid/Enrichr",
    "timeout": 2, "response_byte_limit": 65536}}
SELECTED_TOOLS = [{"name": name, "resources": "api"}
    for name in ("api.enrichr.query", "api.enrichr.result")]
QUESTION = ("Which terms does the explicitly selected library associate with this supplied gene list, "
    "and what native statistical values, overlaps and response-coverage limits were returned?")


def _request():
    return {"version": "enrichr_request_v1", "protocol_profile": "standard_enrichr_v1",
        "library": "Literal library", "genes": ["GENE_A", "gene_a", "GENE_A"],
        "identifier_policy": "literal_no_mapping", "species_context": None,
        "description": "engineering fixture; no biological submission",
        "background": {"policy": "service_native", "genes": None},
        "native_statistic_profile": "documented_odds_v1"}


def _result_form(rich):
    value = source_only_schema()
    if rich:
        for name, source in (("tables", TABLE_SOURCE), ("rows", ROW_SOURCE)):
            value["properties"][name] = deepcopy(enrichr_fact_sources()[source]["report_schema"])
            value["required"].append(name)
    return value


def _handoff_form():
    value = source_only_schema()
    value["properties"]["sources"]["x-source"] = "execution_handoff_refs"
    value["properties"]["sources"]["items"]["x-reference-namespace"] = "execution_handoff"
    return value


def _parent_form(rich):
    if rich:
        return {"type": "object", "properties": {
            "tables": deepcopy(enrichr_fact_sources()[TABLE_SOURCE]["report_schema"]),
            "rows": deepcopy(enrichr_fact_sources()[ROW_SOURCE]["report_schema"])},
            "required": ["tables", "rows"], "additionalProperties": False}
    # This is ordinary scalar Source forwarding, not another RESULT producer.
    return {"type": "object", "properties": {"source": {
        "type": ["string", "null"], "format": "reference", "x-reference-namespace": "source"}},
        "required": ["source"], "additionalProperties": False}


def _child(role, assignment, scope, schema):
    return {"selection": {"kind": "episode_child", "role": role, "goal": QUESTION,
        "scope": deepcopy(scope), "purpose": "Return only the requested original Enrichr data",
        "assignment": deepcopy(assignment), "schema_json": json.dumps(schema), "initial_report_json": "{}"},
        "report_update": {}}


def _selected(name):
    return {"selection": {"kind": "tool", "tool": name, "arguments": {}}, "report_update": {}}


def _wait(update=None):
    return {"selection": {"kind": "wait", "condition": {"version": "event_condition_v1",
        "events": [], "reconsider_at": datetime.now(timezone.utc).isoformat()}},
        "report_update": {} if update is None else deepcopy(update)}


def _forbidden(*args, **kwargs):
    raise AssertionError("Closed replay or a custody check attempted new work")


class EngineeringHTTP:
    """Replace urllib I/O only; retain the real bounded HTTP/protocol path."""
    def __init__(self, monkeypatch):
        self.calls = []
        self.body = canonical({"Literal library": [
            [1, "engineering first term", 0, 2.5, 8, ["GENE_A", "GENE_A"], .25, 0, 0],
            [2, "engineering second term", .1, 1.5, 3, ["gene_a"], .5, .1, .5]]}).encode()
        outer = self

        class Response(io.BytesIO):
            status = 200
            def __init__(self, body, url):
                super().__init__(body)
                self.url = url
                self.headers = Message()
                self.headers["Content-Type"] = "application/json"
            def geturl(self):
                return self.url

        def open_response(opener, request, *, timeout):
            ordinal = len(outer.calls)
            assert ordinal < 2, "A local result window must not issue another HTTP request"
            address = urlsplit(request.full_url)
            assert (address.scheme, address.netloc) == ("https", "enrichr.invalid")
            assert timeout == RESOURCES["enrichr"]["timeout"]
            if ordinal == 0:
                assert address.path == "/Enrichr/addList" and request.get_method() == "POST"
                assert b"GENE_A\ngene_a\nGENE_A" in request.data
                body = b'{"userListId":731,"shortId":"engineering"}'
            else:
                assert address.path == "/Enrichr/enrich" and request.get_method() == "GET"
                assert request.data is None
                assert parse_qs(address.query) == {"userListId": ["731"], "backgroundType": ["Literal library"]}
                body = outer.body
            outer.calls.append({"url": request.full_url, "method": request.get_method(),
                "body_sha256": None if request.data is None else hashlib.sha256(request.data).hexdigest(),
                "timeout": timeout})
            return Response(body, request.full_url)

        monkeypatch.setattr("urllib.request.OpenerDirector.open", open_response)
        monkeypatch.setattr("socket.create_connection", _forbidden)


class EnrichrWorkflowRun:
    """The existing scientific/launch/API/results machinery, with fixture choices."""
    def __init__(self, store, directory, *, rich, scope=None):
        self.store, self.directory, self.rich = store, Path(directory), rich
        self.run_id = "enrichr-workflow-" + ("rich" if rich else "source-only")
        self.scope = deepcopy(scope) if scope is not None else {"subject_refs":
            store.create_problem(raw_sequence="MACDEFGHIK", molecule="protein")["subject_refs"]}
        self.request, self.selections = _request(), [
            {"version": "enrichr_selector_v1", "offset": offset, "limit": 1} for offset in (0, 1)]
        self.api_assignment = {"version": "api_service_assignment_v1", "resource_id": "enrichr",
            "service": "enrichr", "request": self.request, "endpoint": "usable_handoff",
            "constraints": {"allowed_resource_ids": ["enrichr"], "allowed_kinds": ["api"]}}
        self.launch_assignment = {"version": "execution_launch_assignment_v1",
            "requests": {"enrichr": self.api_assignment}, "immutable_input_versions": [],
            "constraints": {"allowed_resource_ids": ["enrichr"], "allowed_kinds": ["api"]}}
        self.calls, self.contexts, self.result_forms, self.result_contexts = {}, [], [], []
        self.handoff = self.scientific_after_result = self.root_after_result = None
        tools = ToolRegistry(store)
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=self.run_id, directory=self.directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        self.library = ScientificProcessLibrary(self.directory / "scientific-process-library")

        def controller(path, initial):
            def engineering_continuation(history, parameters, contexts):
                count = 2 if path[-1][0] == "annotation" else 4
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {"fixture": "scripted_scientific_continuation_only"})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=engineering_continuation
                if path[-1][0] in {"annotation", "scientific_process"} else None)

        self.workflow = Workflow(store, tools, self, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=(self.descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=("scientific_process",),
            episode_record_receipts=True, initial_known_record_refs=[])
        self.episode = self.workflow.build("annotation", "root", QUESTION, self.scope)

    def commission(self):
        # These existing options provide the engineering investigation context;
        # neither set membership nor a service term establishes coexpression.
        assignment = {"selection": {"version": "scientific_process_selection_v3",
            "evidence_axis": self.library.reference("A107"), "thought_pattern": self.library.reference("P13"),
            "child_tool_info": deepcopy(SELECTED_TOOLS)}, "evidence_refs": self.scope["subject_refs"],
            "constraints": {"preserve_literal_gene_list": True},
            "context": {"question": QUESTION, "selected_enrichment_request": deepcopy(self.request),
                "engineering_inputs": True, "biological_function_established": False}}
        selected = _child("scientific_process", assignment, self.scope, _parent_form(self.rich))
        if not self.rich:
            selected["selection"]["initial_report_json"] = '{"source":null}'
        return selected

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        count = self.calls[episode_id]
        self.contexts.append((episode_id, deepcopy(current)))
        assert current.get("feedback") is None, current.get("feedback")
        execution = current.get("execution_assignment", {})
        version = execution.get("version")
        if version == "execution_launch_assignment_v1":
            assert count == 1 and execution == self.launch_assignment
            return _child("launch_api", self.api_assignment, self.scope, _handoff_form())
        if version == "api_service_assignment_v1":
            assert count == 1 and execution == self.api_assignment
            return _selected("api.enrichr.query")
        if version == "execution_results_assignment_v1":
            assert count == 1 and execution["selector"] in self.selections
            self.result_contexts.append(deepcopy(current))
            return _selected("api.enrichr.result")
        if "scientific_process" in current:
            assert current["goal"]["objective"] == QUESTION
            if count == 1:
                response = _child("launch", self.launch_assignment, self.scope, _handoff_form())
                if not self.rich:
                    response["report_update"] = {"source": None}
                return response
            if count == 2:
                handoff = current["child_reports"][-1]
                assert handoff["completed"] is True
                self.handoff, = handoff["sources"]
            else:
                assert count in (3, 4)
                form = deepcopy(current["child_reports"][-1])
                assert form["completed"] is True
                self.result_forms.append(form)
                # The Results Source was admitted while its scientific parent
                # has not yet delivered any report to the annotation episode.
                assert not self.store.db.execute("SELECT 1 FROM runtime_report_attempts "
                    "WHERE run_id=? AND child_episode_id=?", (self.run_id, episode_id)).fetchall()
                assert form["sources"][0] in self.workflow.receipts.known(episode_id)
            if count in (2, 3):
                response = _child("results", {"version": "execution_results_assignment_v1",
                    "handoff_ref": self.handoff, "selector": self.selections[count - 2]},
                    self.scope, _result_form(self.rich))
                if not self.rich:
                    response["report_update"] = {"source": None}
                return response
            self.scientific_after_result = deepcopy(current)
            return _wait(None if self.rich else {"source": self.result_forms[0]["sources"][0]})
        if count == 1:
            return self.commission()
        assert count == 2
        self.root_after_result = deepcopy(current)
        return _wait()

    async def release(self, episode_id):
        pass

    def run(self):
        async def execute():
            record = await self.episode.run_async(self.workflow.context)
            await self.episode.build_result(record)
            return record
        record = asyncio.run(execute())
        self.archive = json.loads("".join(iter_json(record.as_record())))
        return self.archive

    @property
    def api(self):
        return self.workflow.episode_bindings.for_role("results").api_execution

    def context(self, episode_id):
        saved = self.workflow.journal.row("runtime_episodes", episode_id)
        request, path = json.loads(saved["request"]), tuple(map(tuple, json.loads(saved["path"])))
        assert EpisodeRef(self.run_id, path).episode_id == episode_id
        return BindingContext(self.run_id, episode_id, path[-1][0], path,
            request["message"]["scope"], request["message"].get("episode_assignment", {}), request)

    def rows(self, table, episode_id):
        return [dict(row) for row in self.store.db.execute("SELECT * FROM " + table +
            " WHERE run_id=? AND episode_id=?", (self.run_id, episode_id))]


def _sql_rows(store):
    tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {table: sorted(canonical(list(row)) for row in store.db.execute(
        'SELECT * FROM "' + table.replace('"', '""') + '"')) for table in tables}


def _file_pins(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()}


def _no_api_root(store, directory, run_id, scope, initial_refs):
    class NoProvider:
        async def complete(self, *args, **kwargs):
            _forbidden()
    workflow = Workflow(store, ToolRegistry(store), NoProvider(), directory, run_id,
        controller_factory=lambda path, initial: YieldController(str(path), initial, 0, YieldParameters(100, 50)),
        project_credit=lambda *_: 0, episode_record_receipts=True, initial_known_record_refs=initial_refs)
    assert "results" not in workflow.episode_bindings.roles
    episode = workflow.build("annotation", "root", "Read only explicitly supplied retained evidence", scope)
    return workflow, episode


@pytest.mark.parametrize("rich", [False, True], ids=["source-only", "rich"])
def test_registered_enrichr_workflow_windows_custody_and_withdrawn_payload_reconstruction(tmp_path, monkeypatch, rich):
    http = EngineeringHTTP(monkeypatch)
    state, directory = tmp_path / "state", tmp_path / "run"
    with Store(state) as store:
        run = EnrichrWorkflowRun(store, directory, rich=rich)
        run.run()
        scientific = run.archive["units"][0]["child"]
        launch = scientific["units"][0]["child"]
        api = launch["units"][0]["child"]
        results = [scientific["units"][index]["child"] for index in (1, 2)]
        assert len(http.calls) == 2 and len(run.result_forms) == 2
        references = [form["sources"][0] for form in run.result_forms]
        assert references[0] != references[1]
        assert run.api.result_identity(references[0], run.scope) == run.api.result_identity(references[1], run.scope)
        witnesses = []
        for index, result in enumerate(results):
            context = run.context(result["episode_id"])
            facts = json.loads(run.workflow.journal.row("runtime_forms", result["episode_id"])["facts"])
            assert facts["execution_completed"] is True
            witnesses.extend(facts[OWN_WITNESSES]["publications"])
            assert result["units_consumed"] == 1
            assert result["units"][0]["controller_step"]["marginal_credit"] == (2 if index == 0 else 0)
            assert result["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert len(run.rows(table, context.episode_id)) == 1
            if rich:
                assert [row["ordinal"] for row in run.result_forms[index]["rows"]] == [index]
                window = run.result_forms[index]["tables"][0]["window"]
                assert (window["offset"], window["limit"], window["selected_row_count"]) == (index, 1, 1)
                assert window["selected_ordinals"] == [index] and window["state"] == "known"
            else:
                assert set(run.result_forms[index]) == {"sources", "completed"}
                assert not any(source in facts for source in (TABLE_SOURCE, ROW_SOURCE))
        assert {witness["native_artifact_ref"] for witness in witnesses} == {
            "artifact_" + hashlib.sha256(http.body).hexdigest()}
        onward = run.root_after_result["child_reports"][-1]
        if rich:
            assert onward == {name: [row for form in run.result_forms for row in form[name]] for name in ("tables", "rows")}
        else:
            assert onward == {"source": references[0]}
        assert run.workflow.resolver(run.scope, context=run.context(run.archive["episode_id"]))(references[0], "source") is True

        # New Workflow instances without an Enrichr resource must also block
        # private controls before the generic global Store artifact fallback.
        native_ref = witnesses[0]["native_artifact_ref"]
        private_refs = {witness[name] for witness in witnesses
            for name in ("request_artifact_ref", "grading_artifact_ref")}
        private_refs.update(item["artifact_ref"] for witness in witnesses for item in witness["protocol_artifacts"]
            if item["artifact_ref"] != native_ref)
        source_only, source_root = _no_api_root(store, tmp_path / "no-api-source", "no-api-source", run.scope, [references[0]])
        resolve = source_only.resolver(run.scope, source=source_root.source)
        assert resolve(references[0], "source") is True and resolve(native_ref, "artifact") is False
        assert all(resolve(reference, "artifact") is False for reference in private_refs)
        assert store.reference_subset([witnesses[0]["request_artifact_ref"]], run.scope) == [witnesses[0]["request_artifact_ref"]]
        explicit, file_root = _no_api_root(store, tmp_path / "no-api-file", "no-api-file", run.scope, [native_ref])
        explicit_resolve = explicit.resolver(run.scope, source=file_root.source)
        assert native_ref in explicit.receipts.known(file_root.source.episode_id)
        assert explicit_resolve(native_ref, "artifact") is True
        assert all(explicit_resolve(reference, "artifact") is False for reference in private_refs)

        withdrawn = private_refs | {native_ref}
        for reference in withdrawn:
            sha = reference.removeprefix("artifact_")
            path = store.path / "artifacts" / sha[:2] / sha
            assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
            path.unlink()
        before, files = _sql_rows(store), _file_pins(directory)
        scope, archived = deepcopy(run.scope), deepcopy(run.archive)
        original_forms = deepcopy(run.result_forms)
        source_records = [deepcopy(store.get(reference)) for reference in references]
    with Store(state) as store:
        original_reader = store.get_artifact
        def no_withdrawn_bytes(reference):
            assert reference not in withdrawn, "Replay reopened withdrawn native/control payload bytes"
            return original_reader(reference)
        monkeypatch.setattr(store, "get_artifact", no_withdrawn_bytes)
        monkeypatch.setattr("urllib.request.OpenerDirector.open", _forbidden)
        for module, names in (("gene_annotation_episode.enrichr_contracts", (
                "parse_enrichr_response", "calculate_enrichr_components", "project_enrichr_return")),
                ("gene_annotation_episode.enrichr_returns", ("project_enrichr_return", "validate_enrichr_sheet"))):
            for name in names:
                monkeypatch.setattr(module + "." + name, _forbidden)
        replay = EnrichrWorkflowRun(store, directory, rich=rich, scope=scope)
        monkeypatch.setattr(replay, "complete", _forbidden)
        assert replay.run() == archived
        assert replay.calls == {} and len(http.calls) == 2
        assert _sql_rows(store) == before and _file_pins(directory) == files
        assert [store.get(reference) for reference in references] == source_records
        for result, expected in zip(results, original_forms):
            form = json.loads(replay.workflow.journal.row("runtime_forms", result["episode_id"])["form"])
            assert form == expected
        (tmp_path / "ENRICHR_WORKFLOW.json").write_text(json.dumps({
            "qualification": "scripted provider and engineering HTTP responses; no live model/service or functional claim",
            "question": QUESTION, "rich_return": rich, "http_calls": http.calls,
            "native_sha256": hashlib.sha256(http.body).hexdigest(), "result_forms": original_forms,
            "onward_form": onward, "same_capture_result_identity": True,
            "result_marginal_credits": [2, 0], "withdrawn_payload_count": len(withdrawn),
            "closed_replay_new_provider_calls": 0, "closed_replay_rows_and_files_unchanged": True}, indent=2) + "\n")


def test_partial_source_only_result_is_admitted_by_actual_workflow_components_without_endpoint_completion(tmp_path):
    """Selected-row fixture plus real Workflow validators; no partial loop run."""
    with Store(tmp_path / "state") as store:
        case = Harness(store, tmp_path / "run")
        schema = source_only_schema()
        child = case.child(case.root, schema=schema)
        outcome = case.action(child)
        assert outcome["status"] == "partial"
        tools = ToolRegistry(store, clients=case.client)
        factory = ExecutionServiceFactory(deepcopy(case.api.configuration), {},
            case.api.handoff_unit, case.api.acquired_record_unit, .5)
        workflow = Workflow(store, tools, object(), tmp_path / "run", case.run_id,
            controller_factory=lambda path, initial: YieldController(str(path), initial, 0, YieldParameters(100, 50)),
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs="actual_tool_registry_v1",
            episode_record_receipts=True, initial_known_record_refs=[])
        assert workflow.episode_bindings.for_role("results").api_execution.configuration == case.api.configuration
        facts = case.api.facts(child, {})
        assert facts["execution_completed"] is False and OWN_WITNESSES in facts
        form = form_with_facts({}, schema, facts)
        case.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        workflow.validate_report(form, case.scope, grain="results", schema=schema, context=child)
        case.journal.save("runtime_report_attempts", {"parent_episode_id": case.root.episode_id, "decision_index": 0,
            "delivery_ref": "delivery_partial_fixture", "child_episode_id": child.episode_id,
            "contract": canonical(plain(child.request)["report_contract"]), "form": canonical(form), "failure": None})
        reference = outcome["result"]["source_ref"]
        assert reference not in case.receipts.known(case.root.episode_id)
        admitted = workflow.episode_bindings.received_form_references(case.root, form, schema,
            f"{case.run_id}:{case.root.episode_id}:0:typed_form")
        assert admitted == [reference]
        workflow.receipts.receive(case.root.episode_id, admitted, kind="child_form", source_index=0)
        assert reference in workflow.receipts.known(case.root.episode_id)
        assert not case.store.db.execute("SELECT 1 FROM runtime_observations").fetchall()
        assert len(case.client.calls) == 2 and form == {"sources": [reference], "completed": False}
