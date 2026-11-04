"""Composed report Workflow with retained HTTP snapshots, never new HTTP.

Model decisions and root/scientific continuation are engineering fixtures.
Production construction, receipts, publication, parsers/calculators, typed
admission, operational credit and practical terminal-zero logic remain intact.
The partial case uses the ordinary estimator with explicit caller parameters.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS
from gene_annotation_episode.rfam_batch_report_contracts import REPORT_FORMAT, RFAM_REPORT_METRIC_UNITS
from gene_annotation_episode.rfam_batch_report_grader import calculate_rfam_batch_report_components
from gene_annotation_episode.rfam_batch_returns import rfam_fact_sources
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import form
from test_practical_runtime import selected


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "verification/tool_graders_rfam_report_workflow_2026-10-26_245"
RUNS = Path(os.environ.get("RFAM_REPORT_WORKFLOW_RUNS", str(EVIDENCE / "runs")))
LIVE = ROOT / "verification/tool_graders_rfam_live_workflow_2026-10-26_243/live_001"
OUT = EVIDENCE / "original_job_out_001"
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
JOB = "infernal_cmscan-R20261026-041949-0621-14761545-p2m"
RESOURCES = {"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90.0}}
SELECTED_TOOLS = [{"name": name, "resources": "api"} for name in
    ("api.rfam.submit", "api.rfam.status", "api.rfam.fetch")]
METRICS = ["native_score_bits", "native_evalue", "native_bias_bits", "query_span_nt",
    "native_model_span_positions", "represented_model_positions", "represented_query_positions",
    "model_consensus_compared_count", "model_consensus_equal_count", "query_insert_count",
    "model_delete_count", "model_coverage_fraction"]
GOAL = "Measure native Rfam model matches and sequence correspondence for the three supplied nucleotide occurrences"
HISTORY_TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations",
    "runtime_model_calls", "runtime_report_attempts", "runtime_forms")
OLD_JSON = ROOT / "verification/tool_graders_rfam_workflow_2026-10-26_241/tests_005/runs/retained_single-7n2b5y3a"
PROTECTED = [LIVE / name for name in ("history.json", "archive.json", "results-return.json",
    "scientific-return.json", "requested-forms.json", "state/state.sqlite3", "submitted-file.body")]
PROTECTED += [OLD_JSON / name for name in ("history.json", "results-return.json", "scientific-return.json")]


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _protected_hashes():
    return {str(path.relative_to(ROOT)): _sha(path.read_bytes()) for path in PROTECTED}


def _history(store, run_id):
    return {table: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + table + " WHERE run_id=? ORDER BY rowid", (run_id,))]
        for table in HISTORY_TABLES}


def _facts_form():
    sources = rfam_fact_sources()
    properties = {"measurements": sources["rfam_report_rows"]["report_schema"],
        "populations": sources["rfam_result_populations"]["report_schema"]}
    return {"type": "object", "additionalProperties": False,
        "properties": properties, "required": list(properties)}


def _child(role, assignment, scope, schema):
    return {"selection": {"kind": "episode_child", "role": role, "goal": GOAL,
        "scope": scope, "purpose": "Return the selected native model/query measurements with explicit unavailable model coverage and population qualifications; retain original query occurrences and distinguish a model name from an RF accession",
        "assignment": deepcopy(assignment), "schema_json": json.dumps(schema),
        "initial_report_json": "{}"}, "report_update": {}}


def _original_snapshot(action):
    row, = [item for item in json.loads((LIVE / "http-snapshots.json").read_text())
        if item["request"]["action"] == action]
    path, = LIVE.glob("http-" + action + "-*.body")
    content = path.read_bytes()
    assert row["content_ref"] == "artifact_" + _sha(content)
    return SourceSnapshot(**{key: row[key] for key in
        ("service", "url", "request", "retrieved_at", "media_type", "transport")}, content=content)


class RetainedReportTransport:
    """Replay exact HTTP custody; host input operands are explicitly rebound.

    Removing the old input_operand permits the production service to resolve
    current Store subjects. Request wire bytes/headers, original sequences,
    submission file and query names are never changed by that host adaptation.
    Complete-zero and truncated response bodies are separately marked synthetic.
    """
    timeout = 90.0

    def __init__(self, case, directory):
        self.case, self.directory, self.calls = case, directory, []
        self.job = JOB
        self.submission = _original_snapshot("submit")
        self.original_status = _original_snapshot("status")
        self.submitted_file = (LIVE / "submitted-file.body").read_bytes()
        metadata = json.loads((OUT / "snapshot.json").read_text())
        content = (OUT / "response.body").read_bytes()
        assert metadata["content_sha256"] == _sha(content)
        assert base64.b64decode(metadata["content_base64"]) == content
        self.original_report = SourceSnapshot(**{key: metadata[key] for key in
            ("service", "url", "request", "retrieved_at", "media_type", "transport")}, content=content)
        self.result_snapshot = self.original_report
        if case == "complete_zero":
            text = content.decode("ascii")
            header = text[:text.index("Query:")]
            queries = re.findall(r"^Query:.*$", text, re.MULTILINE)
            content = (header + "".join(query + "\nHit scores:\n"
                "   [No hits detected that satisfy reporting thresholds]\n\nHit alignments:\n"
                "   [No hits detected that satisfy reporting thresholds]\n\n"
                "Internal CM pipeline statistics summary:\nTotal CM hits reported: 0\n//\n"
                for query in queries) + "[ok]\n").encode("ascii")
            self._synthetic(content, True, "Generated zero-hit blocks for all three original names and lengths")
        elif case == "truncated_partial":
            content = content[:content.index(b"Query:       rfam_query_00000002")]
            self._synthetic(content, False, "Exact original prefix through two complete query blocks; third occurrence and final marker absent")
        self.body = self.result_snapshot.content

    def _synthetic(self, content, complete, meaning):
        self.result_snapshot = replace(self.original_report, content=content, transport={
            "status": 200, "body_complete": complete, "evidence_kind": "synthetic_fixture",
            "fixture_original_sha256": self.original_report.sha256, "fixture_transformation": meaning})

    def _return(self, snapshot):
        request = deepcopy(snapshot.request)
        old_operand = request.pop("input_operand", None)
        value = replace(snapshot, request=request)
        entry = asdict(value)
        entry.pop("content")
        entry.update(content_sha256=value.sha256, content_bytes=len(value.content),
            original_host_input_operand=old_operand,
            host_context_adaptation="Production service resolves current Store input_operand; HTTP request and response bytes remain retained")
        self.calls.append(entry)
        prefix = self.directory / ("controlled-snapshot-" + str(len(self.calls)))
        prefix.with_suffix(".body").write_bytes(value.content)
        _write(prefix.with_suffix(".json"), entry)
        return value

    def submit_file(self, content, *, filename):
        assert content == self.submitted_file and filename == self.submission.request["filename"]
        return self._return(self.submission)

    def result(self, job_id, *, representation):
        assert job_id == self.job and representation == "out"
        return self._return(self.result_snapshot)

    def status(self, job_id):
        assert self.case == "truncated_partial" and job_id == self.job
        return self._return(self.original_status)


@pytest.fixture(scope="module", params=("retained_report", "complete_zero", "truncated_partial"))
def report_workflow_run(request):
    RUNS.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=request.param + "-", dir=RUNS))
    protected = _protected_hashes()
    native = RetainedReportTransport(request.param, directory)
    provenance = {"case": request.param, "status": "started", "live_api": False,
        "configured_model": False, "native_program_executed": False, "hpc": False,
        "fixtures": ["scripted model decisions", "root/scientific continuation", "retained transport snapshots"],
        "production_overrides": [], "original_job_id": JOB,
        "original_report_sha256": native.original_report.sha256,
        "response_sha256": native.result_snapshot.sha256,
        "response_evidence": "retained_native_response" if request.param == "retained_report" else "synthetic_fixture",
        "input_adaptation": "Rebuild Store subjects from exact original supplied public-inputs.fa; service rebuilds host input_operand. Native generated query names, submitted FASTA bytes and original multipart request bytes remain unchanged.",
        "original_acquisition": str(OUT.relative_to(ROOT)),
        "qualification": "Controlled full Workflow verification uses retained submission/result custody; it does not perform a new live Workflow or remote submission.",
        "protected_historical_hashes": protected}
    _write(directory / "PROVENANCE.json", provenance)
    with pytest.MonkeyPatch.context() as patch, Store(directory / "state") as store:
        def forbidden(*args, **kwargs):
            raise AssertionError("Controlled report Workflow attempted live transport, subprocess or hidden wait")
        for name in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
                     "urllib.request.OpenerDirector.open", "subprocess.run", "subprocess.Popen", "time.sleep"):
            patch.setattr(name, forbidden)
        tools = ToolRegistry(store, clients=native)
        subjects = store.create_problem(LIVE / "public-inputs.fa", molecule="dna")["subject_refs"]
        assert len(subjects) == 2
        scope = {"subject_refs": subjects}
        service_request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
            "subject_refs": [subjects[0], subjects[0], subjects[1]]}
        metrics = METRICS if request.param == "retained_report" else (
            ["native_score_bits", "query_span_nt", "model_coverage_fraction"] if request.param == "complete_zero"
            else ["native_score_bits", "native_evalue", "query_span_nt", "represented_query_positions",
                "model_consensus_compared_count", "model_coverage_fraction"])
        selector = {"version": "rfam_batch_result_selector_v3", "representation": "out",
            "model_metadata_ref": None, "projection": {"family": "hit",
            "rows": {"offset": 1 if request.param == "retained_report" else 0,
                "limit": 2 if request.param == "retained_report" else 1}, "metrics": metrics}}
        assignment = {"version": "api_service_assignment_v1", "resource_id": "rfam", "service": "rfam_batch",
            "request": service_request, "endpoint": "usable_handoff", "constraints": {}}
        launch = launch_assignment({"rfam": assignment})
        handoff_form, parent_form, result_form = form("execution_handoff_refs"), _facts_form(), _facts_form()
        result_form["properties"]["completed"] = {"type": "boolean", "x-source": "execution_completed"}
        result_form["required"].append("completed")
        run_id, run_directory = "rfam-report-composed-" + request.param, directory / "run"
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=run_id, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / "scientific-process-library")
        _write(directory / "requested-forms.json", {"scientific": parent_form, "results": result_form,
            "handoff": handoff_form})
        _write(directory / "caller-selected-inputs.json", {"scope": scope,
            "request": service_request, "selector": selector})

        def controllers(path, initial):
            role = path[-1][0]
            def estimate(history, parameters, contexts):
                count = {"annotation": 1, "scientific_process": 2}[role]
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {"fixture": "root_and_scientific_continuation_only"})
            # Partial result closure remains the ordinary production estimator
            # and comparison. The caller selects these engineering parameters;
            # a status action follows the incomplete fetch without another fetch.
            partial = request.param == "truncated_partial" and role == "results"
            return YieldController(str(path), initial, 1e6 if partial else 0,
                YieldParameters(2, 1) if partial else YieldParameters(100, 50),
                estimate_with_context=estimate if role in {"annotation", "scientific_process"} else None)

        class Choices:
            def __init__(self):
                self.counts, self.calls = {}, []

            async def complete(self, episode_id, role, instructions, current, schema):
                self.calls.append({"episode_id": episode_id, "role": role, "instructions": instructions,
                    "current": deepcopy(current), "schema": deepcopy(schema)})
                _write(directory / "model-calls.json", self.calls)
                assert current.get("feedback") is None, current.get("feedback")
                self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                execution = current.get("execution_assignment", {})
                if execution.get("version") == "execution_launch_assignment_v1":
                    assert count == 1 and execution == launch
                    return _child("launch_api", assignment, scope, handoff_form)
                if execution.get("version") == "api_service_assignment_v1":
                    assert count == 1 and execution == assignment
                    return selected("api.rfam.submit", {})
                if execution.get("version") == "execution_results_assignment_v1":
                    assert execution["selector"] == selector
                    if count == 1:
                        return selected("api.rfam.fetch", {})
                    assert count == 2 and request.param == "truncated_partial"
                    context = api.rfam_returns.context(episode_id)
                    original, = list(api._own_outcomes(context))
                    assert original[1]["status"] == "partial"
                    assert api._completion(context) is None
                    return selected("api.rfam.status", {})
                if "scientific_process" in current:
                    assert current["scientific_process"]["selection"]["child_tool_info"] == SELECTED_TOOLS
                    if count == 1:
                        return _child("launch", launch, scope, handoff_form)
                    assert count == 2
                    received = current["child_reports"][-1]
                    assert received["completed"] is True
                    assert received["yield"]["expected_next_gain"] == NumericBand.exact(0).as_record()
                    handoff, = received["references"]
                    return _child("results", {"version": "execution_results_assignment_v1",
                        "handoff_ref": handoff, "selector": selector}, scope, result_form)
                assert count == 1 and episode_id == episode.source.episode_id
                available = workflow.scientific_process_binding.tool_library.parent_tool_info(
                    workflow.services.tool_information_catalog(scope))
                assert all(any((row["name"], row["resources"]) == (tool["name"], tool["resources"])
                    for row in available) for tool in SELECTED_TOOLS)
                scientific_assignment = {"selection": {"version": "scientific_process_selection_v3",
                    "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                    "child_tool_info": deepcopy(SELECTED_TOOLS)}, "evidence_refs": subjects,
                    "constraints": {"preserve_original_input_occurrences": True},
                    "context": {"supplied_sequence": native.submission.request["input_operand"]["queries"][0]["submitted_sequence"],
                        "molecule": "dna", "complete": True, "label_is_public_identity": False}}
                return _child("scientific_process", scientific_assignment, scope, parent_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        def construct(provider, *, storage=store, registry=tools):
            current_application = factory(storage, run_id=run_id, directory=run_directory,
                tool_registry=registry, tool_catalog=registry.catalog())
            value = Workflow(storage, registry, provider, run_directory, run_id,
                controller_factory=controllers, project_credit=lambda *_: 0,
                episode_binding_descriptors=(descriptor, *current_application.episode_binding_descriptors),
                role_credit_bindings=current_application.role_credit_bindings,
                job_progress_provider=current_application.job_progress_provider,
                annotation_child_roles=("scientific_process",), episode_record_receipts=True,
                initial_known_record_refs=[])
            value.episode_bindings.for_role("results").api_execution.services["rfam"].client = native
            return value

        workflow = construct(choices)
        api = workflow.episode_bindings.for_role("results").api_execution
        episode = workflow.build("annotation", "root", GOAL, scope)
        async def execute(root, owner):
            record = await root.run_async(owner.context)
            await root.build_result(record)
            return json.loads("".join(iter_json(record.as_record())))

        try:
            archive = asyncio.run(execute(episode, workflow))
            scientific = archive["units"][0]["child"]
            launch_record = scientific["units"][0]["child"]
            api_record = launch_record["units"][0]["child"]
            results = scientific["units"][1]["child"]
            returned = json.loads(workflow.journal.row("runtime_forms", results["episode_id"])["form"])
            forwarded = json.loads(workflow.journal.row("runtime_forms", scientific["episode_id"])["form"])
            final_ref, = {row["source_ref"] for row in returned["populations"]}
            body = api.rfam_returns.read(final_ref, scope)
            saved = body["publication_result"]
            grading = store.get(saved["grading_source_ref"])
            manifest = json.loads(store.get_artifact(grading["artifact_ref"]))
            parsed = json.loads(store.get_artifact(manifest["parse_ref"]))
            sheet = json.loads(store.get_artifact(saved["sheet_ref"]))
            calculation = json.loads(store.get_artifact(saved["calculation_ref"]))
            for name, value in (("archive", archive), ("results-return", returned),
                ("scientific-return", forwarded), ("publication", body), ("grading-manifest", manifest),
                ("parse", parsed), ("sheet", sheet), ("calculation", calculation),
                ("controlled-calls", native.calls), ("history", _history(store, run_id))):
                _write(directory / (name + ".json"), value)
            (directory / "native-result.body").write_bytes(native.body)
            (directory / "submitted-file.body").write_bytes(native.submitted_file)
            for index, call in enumerate(choices.calls):
                if "scientific_process" in call["current"]:
                    (directory / f"scientific-presentation-{index}.txt").write_text(
                        render_scientific_process_prompt(call["current"], call["instructions"]))
            provenance.update(status="workflow_closed", own_actions={row["scope_level"]: row["units_consumed"]
                for row in (archive, scientific, launch_record, api_record, results)})
            _write(directory / "PROVENANCE.json", provenance)
            yield SimpleNamespace(store=store, workflow=workflow, api=api, choices=choices, native=native,
                archive=archive, scientific=scientific, launch=launch_record, api_record=api_record, results=results,
                returned=returned, forwarded=forwarded, final_ref=final_ref, body=body, manifest=manifest,
                parsed=parsed, sheet=sheet, calculation=calculation, scope=scope, directory=directory,
                run_directory=run_directory, case=request.param, selector=selector, service_request=service_request,
                episode=episode, library=library, parent_form=parent_form, result_form=result_form,
                construct=construct, execute=execute, protected=protected)
        except BaseException as error:
            provenance.update(status="failed", error_type=type(error).__name__, error=str(error))
            _write(directory / "PROVENANCE.json", provenance)
            _write(directory / "failed-history.json", _history(store, run_id))
            raise
        finally:
            assert _protected_hashes() == protected


def test_report_three_slots_and_actual_child_owners(report_workflow_run):
    run = report_workflow_run
    binding = run.workflow.scientific_process_binding
    context = run.api.rfam_returns.context(run.scientific["episode_id"])
    binding.validate_context(context)
    information = binding.tool_library.resolve_tool_info(SELECTED_TOOLS,
        run.workflow.services.tool_information_catalog(run.scope))
    assignment = plain(context.assignment)
    assert assignment["selection"]["child_tool_info"] == information
    assert assignment["selection"]["evidence_axis"] == run.library.reference("A101")
    assert assignment["selection"]["thought_pattern"] == run.library.reference("P01")
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []
    assert not any(row["name"].startswith(("api.rfam.", "public.rfam.")) for row in binding.catalog(context))
    execution = run.workflow.episode_bindings.for_role("results")
    sources = {"rfam_report_rows", "rfam_result_populations"}
    assert sources <= execution.fact_sources("results").keys()
    for role in ("launch", "launch_api"):
        assert not sources.intersection(execution.fact_sources(role))
    for role in ("scientific_process", "annotation"):
        assert sources <= execution.received_report_sources(role).keys()
    contracts = binding.tool_library.resolve_invocations(SELECTED_TOOLS,
        run.workflow.services.tool_information_catalog(run.scope))
    submit, = [row for row in contracts if row["name"] == "api.rfam.submit"]
    fetch, = [row for row in contracts if row["name"] == "api.rfam.fetch"]
    assert submit["invocation_route"] == {"kind": "commission", "routes": [{
        "entry_role": "launch", "resource_id": "rfam", "resource_role": "launch_api"}]}
    assert fetch["invocation_route"] == {"kind": "commission", "routes": [{
        "entry_role": "results", "resource_id": "rfam", "resource_role": "results"}]}
    for call in run.choices.calls:
        if "scientific_process" not in call["current"]:
            continue
        prompt = render_scientific_process_prompt(call["current"], call["instructions"])
        task, steering = prompt.split("\n\nSTEERING", 1)
        assert task.startswith("TASK\n")
        assert call["current"]["scientific_process"]["evidence_axis"]["investigation_instructions"] in task
        for row in information:
            assert row["instructions"] in task and row["instructions"] not in steering
        for raw in ("rfam_batch_report_sheet_v1", "paired_positions", "# cmscan ::", "model_consensus_equal_fraction"):
            assert raw not in steering


def test_report_requested_facts_cross_both_scientific_boundaries(report_workflow_run):
    run = report_workflow_run
    assert set(run.returned) == {"measurements", "populations", "completed"}
    assert run.returned["completed"] is (run.case != "truncated_partial")
    assert run.forwarded == {key: run.returned[key] for key in ("measurements", "populations")}
    projection = run.body["projection"]
    assert run.forwarded["measurements"] == [{"source_ref": run.final_ref, **row,
        "population_complete": projection["population_complete"]} for row in projection["rows"]]
    for row in run.forwarded["measurements"]:
        assert set(row) == {"source_ref", "record_key", "query_occurrence_key", "family_accession",
            "model_name", "strand", "measured", "unavailable", "population_complete"}
        assert row["model_name"] == "5S_rRNA" and row["family_accession"] is None
        assert {cell["name"] for cell in row["measured"] + row["unavailable"]} == set(run.selector["projection"]["metrics"])
        assert row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
        assert all(cell["unit"] == RFAM_REPORT_METRIC_UNITS[cell["name"]] for cell in row["measured"])
    for child, parent, expected in ((run.results, run.scientific, run.returned),
            (run.scientific, run.archive, run.forwarded)):
        admission = run.store.db.execute("SELECT parent_episode_id,form,failure FROM runtime_report_attempts "
            "WHERE run_id=? AND child_episode_id=?", (run.workflow.run_id, child["episode_id"])).fetchone()
        assert admission["parent_episode_id"] == parent["episode_id"] and admission["failure"] is None
        assert json.loads(admission["form"]) == expected
        context = run.api.rfam_returns.context(parent["episode_id"])
        assert run.api.rfam_returns.received_facts(context, run.parent_form) == {
            "rfam_report_rows": expected["measurements"], "rfam_result_populations": expected["populations"]}
        assert run.api.resolve(context, "5S_rRNA", "rfam_model") is bool(expected["measurements"])
        assert run.api.resolve(context, "RF00001", "rfam_family") is False
    context = run.api.rfam_returns.context(run.results["episode_id"])
    assert run.api.resolve(context, "5S_rRNA", "rfam_model") is bool(run.returned["measurements"])
    assert run.api.resolve(context, "foreign-model", "rfam_model") is False
    assert run.store.count("annotation") == run.store.count("observation") == 0


def test_report_original_custody_and_limited_numerical_projection(report_workflow_run):
    run = report_workflow_run
    saved = run.body["publication_result"]
    assert run.store.get_artifact(saved["artifact_ref"]) == run.native.body
    assert run.body["service_request"] == run.service_request
    assert run.body["assignment"]["selector"] == run.selector
    assert run.manifest["selector"] == run.selector and run.manifest["request"] == run.service_request
    assert run.body["target"]["origin_episode_id"] == run.api_record["episode_id"]
    assert run.body["target"]["execution_id"] == JOB
    assert run.manifest["format"] == REPORT_FORMAT
    original = run.store.get(saved["submission_source_ref"])
    request = json.loads(run.store.get_artifact(original["request_ref"]))
    assert request["transport"] == run.native.submission.transport
    assert base64.b64decode(request["request"]["file_base64"]) == run.native.submitted_file
    assert request["transport"]["request"]["body_base64"] == run.native.submission.transport["request"]["body_base64"]
    assert run.sheet["input_identity"]["submitted_file_sha256"] == _sha(run.native.submitted_file)
    queries = run.sheet["input_identity"]["queries"]
    assert [row["subject_ref"] for row in queries] == run.service_request["subject_refs"]
    assert [row["selected_occurrence_ordinal"] for row in queries] == [0, 1, 2]
    assert [row["native_query_name"] for row in queries] == ["rfam_query_00000000", "rfam_query_00000001", "rfam_query_00000002"]
    assert queries[0]["subject_ref"] == queries[1]["subject_ref"] != queries[2]["subject_ref"]
    assert len({row["query_occurrence_key"] for row in queries}) == 3
    for row in run.calculation["hits"]:
        assert row["model_name"] == "5S_rRNA" and row["family_accession"] is None
        assert row["native_score_bits"] == 104.6 and row["native_evalue"] == 1.4e-24
        assert row["native_bias_bits"] == 0 and row["query_span_nt"] == 119
        assert row["native_model_span_positions"] == row["represented_model_positions"] == 120
        assert row["represented_query_positions"] == 119
        assert row["model_consensus_compared_count"] == 118 and row["model_consensus_equal_count"] == 75
        assert row["query_insert_count"] == 1 and row["model_delete_count"] == 2
        assert row["model_length_positions"] is row["model_coverage_fraction"] is None
    population, = run.returned["populations"]
    rows = run.returned["measurements"]
    if run.case == "retained_report":
        assert run.native.body == (OUT / "response.body").read_bytes()
        response = run.store.get(saved["source_ref"])
        metadata = json.loads(run.store.get_artifact(response["request_ref"]))
        assert metadata["transport"] == run.native.original_report.transport
        assert run.parsed["status"] == "complete"
        assert population["population_complete"] is True
        assert (population["available_row_count"], population["selected_row_count"], population["more_rows"]) == (3, 2, True)
        assert [row["query_occurrence_key"] for row in rows] == [queries[index]["query_occurrence_key"] for index in (1, 2)]
        assert [row["strand"] for row in rows] == ["+", "-"]
        assert run.calculation["hits"][2]["native_start_1i"] == 119
        assert run.calculation["hits"][2]["native_end_1i"] == 1
        expected = {name: run.calculation["hits"][0][name] for name in METRICS if name != "model_coverage_fraction"}
        assert all({cell["name"]: cell["value"] for cell in row["measured"]} == expected for row in rows)
    elif run.case == "complete_zero":
        assert rows == run.sheet["hits"] == run.calculation["hits"] == []
        assert (population["available_row_count"], population["selected_row_count"], population["more_rows"]) == (0, 0, False)
        assert population["population_complete"] and run.parsed["status"] == "complete"
        assert len(run.calculation["query_strands"]) == 6
        assert all(row["selected_row_count"] == row["query_strand_union_span_nt"] == row["query_strand_union_fraction"] == 0
            and row["population_complete"] for row in run.calculation["query_strands"])
    else:
        assert run.parsed["status"] == "partial" and run.body["status"] == "partial"
        assert population["population_complete"] is False
        assert (population["available_row_count"], population["selected_row_count"], population["more_rows"]) == (2, 1, True)
        assert rows[0]["query_occurrence_key"] == queries[0]["query_occurrence_key"]
        assert any(issue["code"] == "rfam_response_body_incomplete" for issue in saved["projection_errors"])
        assert any(issue["code"] == "rfam_batch_report_query_missing" for issue in run.parsed["issues"])
        assert all(row["query_strand_union_fraction"] is None for row in run.calculation["query_strands"])
        missing = [row for row in run.calculation["query_strands"] if row["query_occurrence_key"] == queries[2]["query_occurrence_key"]]
        assert len(missing) == 2 and all(row["selected_row_count"] is None and row["query_strand_union_span_nt"] is None for row in missing)
    assert run.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0


def test_report_own_action_observations_credit_and_true_practical_completion(report_workflow_run):
    run = report_workflow_run
    partial = run.case == "truncated_partial"
    expected = [(run.archive, ["episode_child:scientific_process"]),
        (run.scientific, ["episode_child:launch", "episode_child:results"]),
        (run.launch, ["episode_child:launch_api"]), (run.api_record, ["api.rfam.submit"]),
        (run.results, ["api.rfam.fetch", "api.rfam.status"] if partial else ["api.rfam.fetch"])]
    for closed, names in expected:
        assert closed["units_consumed"] == len(names) == run.choices.counts[closed["episode_id"]]
        for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
            assert run.store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (run.workflow.run_id, closed["episode_id"])).fetchone()[0] == len(names)
        actions = [json.loads(row[0]) for row in run.store.db.execute(
            "SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",
            (run.workflow.run_id, closed["episode_id"]))]
        assert [a["tool"] if a["kind"] == "tool" else a["kind"] + ":" + a["role"] for a in actions] == names
    for closed in (run.launch, run.api_record):
        assert closed["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        assert closed["units"][-1]["controller_step"]["marginal_credit"] == 3
        context = run.api.rfam_returns.context(closed["episode_id"])
        family = run.workflow.episode_bindings.for_role(context.role)
        proof = family.completion_for_action(context, f"{context.run_id}:{context.episode_id}:0")
        assert proof and family.verify_completion(context, proof)
    context = run.api.rfam_returns.context(run.results["episode_id"])
    proof = run.api.completion_for_action(context, f"{context.run_id}:{context.episode_id}:0")
    estimate = run.results["controller_state"]["estimate"]
    if partial:
        assert proof is None and run.api._completion(context) is None
        assert [unit["controller_step"]["marginal_credit"] for unit in run.results["units"]] == [2, 0]
        assert estimate["expected_next_gain"] != NumericBand.exact(0).as_record()
        assert estimate["expected_next_gain"]["status_code"] == 0
        assert estimate["expected_next_gain"]["upper"] <= 1e6
        assert estimate["diagnostics"]["fitting_scope"] == "full_history"
    else:
        assert proof and run.api.verify_completion(context, proof)
        assert estimate["expected_next_gain"] == NumericBand.exact(0).as_record()
        assert estimate["diagnostics"]["fitting_scope"] == "verified_assignment_endpoint"
        assert run.results["units"][0]["controller_step"]["marginal_credit"] == 2
    for closed in (run.archive, run.scientific):
        assert all(unit["controller_step"]["marginal_credit"] == 0 for unit in closed["units"])
    count = 7 if partial else 6
    assert len(run.choices.calls) == count
    assert [row["request"]["action"] for row in run.native.calls] == (["submit", "fetch", "status"] if partial else ["submit", "fetch"])
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations WHERE run_id=?",
        (run.workflow.run_id,)).fetchone()[0] == count
    _write(run.directory / "action-observation-verification.json", {"actions": count,
        "observations": count, "model_calls": count, "results_final_estimate": estimate,
        "results_practical_completion": proof, "results_gains": [
            unit["controller_step"]["marginal_credit"] for unit in run.results["units"]]})


def test_report_saved_recalculation_and_reopened_workflow_need_no_native_work(report_workflow_run, monkeypatch):
    run = report_workflow_run
    history, calls = _history(run.store, run.workflow.run_id), deepcopy(run.native.calls)
    recalculated = calculate_rfam_batch_report_components(deepcopy(run.sheet),
        parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
    assert recalculated == run.calculation
    _write(run.directory / "recalculated.json", recalculated)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved replay must not acquire, parse, calculate or call a model")
    for name in ("submit_file", "result", "status"):
        monkeypatch.setattr(run.native, name, forbidden)
    for path in ("gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet",
        "gene_annotation_episode.rfam_batch_report_grader.calculate_rfam_batch_report_components",
        "gene_annotation_episode.rfam_batch_report._alignment_geometry",
        "gene_annotation_episode.rfam_batch_report.parse_rfam_report_membership",
        "gene_annotation_episode.rfam_batch_table.parse_rfam_report_membership",
        "gene_annotation_episode.rfam_batch_publication.publish_rfam_batch_result",
        "gene_annotation_episode.rfam_batch_transport.RfamBatchHTTP._request"):
        monkeypatch.setattr(path, forbidden)
    class NoModel:
        async def complete(self, *args, **kwargs):
            forbidden()
        async def release(self, episode_id):
            pass
    with Store(run.directory / "state") as reopened_store:
        registry = ToolRegistry(reopened_store, clients=run.native)
        reopened = run.construct(NoModel(), storage=reopened_store, registry=registry)
        root = reopened.build("annotation", "root", GOAL, run.scope)
        archive = asyncio.run(run.execute(root, reopened))
        assert archive == run.archive
        assert _history(reopened_store, run.workflow.run_id) == history and run.native.calls == calls
        restored_api = reopened.episode_bindings.for_role("results").api_execution
        assert restored_api.rfam_returns.read(run.final_ref, run.scope) == run.body
        actions = [(run.api_record, 0, "api.rfam.submit"), (run.results, 0, "api.rfam.fetch")]
        if run.case == "truncated_partial":
            actions.append((run.results, 1, "api.rfam.status"))
        for closed, index, name in actions:
            context = restored_api.rfam_returns.context(closed["episode_id"])
            key = f"{context.run_id}:{context.episode_id}:{index}"
            saved = json.loads((restored_api._episode_directory(context.episode_id)
                / "actions" / digest(key) / "outcome.json").read_text())
            assert asyncio.run(restored_api.execute(context, name, {}, key)) == saved
    assert _history(run.store, run.workflow.run_id) == history and run.native.calls == calls
    assert _protected_hashes() == run.protected
    _write(run.directory / "reopened-archive.json", archive)
    _write(run.directory / "replay-verification.json", {"new_native_calls": 0, "new_model_calls": 0,
        "new_parser_calls": 0, "new_calculator_calls": 0, "archive_unchanged": True,
        "completed_history_and_forms_unchanged": True, "original_action_outcomes_unchanged": True,
        "saved_sheet_recalculation_equal": True, "old_history_and_forms_unchanged": True})


def test_report_does_not_widen_saved_json_or_table_forms(report_workflow_run):
    run = report_workflow_run
    sources = rfam_fact_sources()
    old = sources["rfam_result_rows"]["report_schema"]["items"]
    report = sources["rfam_report_rows"]["report_schema"]["items"]
    assert "model_name" not in old["properties"] and "model_name" not in old["required"]
    assert report["properties"]["model_name"] == {"type": ["string", "null"],
        "format": "identifier", "x-reference-namespace": "rfam_model"}
    old_metrics = old["properties"]["measured"]["items"]["properties"]["name"]["enum"]
    # Bias and native model span are also table measurements (TABLE_METRICS009).
    # The report-only geometry/accuracy/rank fields must stay out of old forms.
    assert not {"represented_query_positions", "native_alignment_accuracy", "native_rank"}.intersection(old_metrics)
    schema = {"type": "object", "additionalProperties": False, "required": ["measurements", "populations"],
        "properties": {"measurements": sources["rfam_result_rows"]["report_schema"],
            "populations": sources["rfam_result_populations"]["report_schema"]}}
    for directory in (OLD_JSON, LIVE):
        saved = json.loads((directory / "scientific-return.json").read_text())
        validate_form(saved, schema, lambda *_: True)
        assert all("model_name" not in row for row in saved["measurements"])
    assert _protected_hashes() == run.protected
