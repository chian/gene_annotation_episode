"""Actual composed Rfam Workflow with controlled, explicitly qualified transport.

Only model choices, root/scientific continuation estimates and HTTP responses
are fixtures. Construction, selected actions, custody, publication, native
parsers, numerical sheets/calculators, typed admissions, operational credit and
practical terminal-zero continuation are production code. No live request,
configured model, scientific program or HPC job runs in this verification.
"""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS
from gene_annotation_episode.rfam_batch_grader import calculate_rfam_batch_components
from gene_annotation_episode.rfam_batch_returns import rfam_fact_sources
from gene_annotation_episode.rfam_batch_table_grader import calculate_rfam_batch_table_components
from gene_annotation_episode.rfam_discovery import BASE_URL, result_url
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
EVIDENCE = ROOT / "verification/tool_graders_rfam_workflow_2026-10-26_241"
RUNS = Path(os.environ.get("RFAM_WORKFLOW_RUNS", str(EVIDENCE / "runs")))
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
NATIVE_FILE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/003-fetch-json/response.body"
RESOURCES = {"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 12.5}}
SELECTED_TOOLS = [{"name": name, "resources": "api"}
    for name in ("api.rfam.submit", "api.rfam.fetch")]
METRICS = ["native_score_bits", "native_evalue", "native_gc_fraction", "query_span_nt",
    "query_span_fraction", "model_coverage_fraction"]
GOAL = "Measure Rfam family-model matches and query coverage for the supplied nucleotide input occurrences"
HISTORY_TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations",
    "runtime_model_calls", "runtime_report_attempts", "runtime_forms")


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _child(role, assignment, scope, schema):
    return {"selection": {"kind": "episode_child", "role": role, "goal": GOAL,
        "scope": scope, "purpose": "Return only the requested native score, E-value, GC and query interval measurements, explicit unavailable model coverage, and reported population sizes; preserve each original input occurrence",
        "assignment": deepcopy(assignment), "schema_json": json.dumps(schema),
        "initial_report_json": "{}"}, "report_update": {}}


def _facts_form():
    sources = rfam_fact_sources()
    properties = {"measurements": sources["rfam_result_rows"]["report_schema"],
        "populations": sources["rfam_result_populations"]["report_schema"]}
    return {"type": "object", "additionalProperties": False,
        "properties": properties, "required": list(properties)}


def _history(store, run_id):
    return {table: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + table + " WHERE run_id=? ORDER BY rowid", (run_id,))]
        for table in HISTORY_TABLES}


class ControlledRfam:
    """Fresh SourceSnapshots with a retained native body or synthetic body.

    The native body's bytes and historical job ID stay unchanged. The new
    submission snapshot is a controlled response for that identity, not a claim
    that this test performed or rediscovered the historical remote submission.
    """
    timeout = 12.5

    def __init__(self, case, directory):
        self.case, self.directory, self.calls = case, directory, []
        native = json.loads(NATIVE_FILE.read_bytes())
        self.sequence = native["searchSequence"]
        self.job = native["jobId"] if case == "retained_single" else "infernal_cmscan-CONTROLLED_" + case
        self.body = NATIVE_FILE.read_bytes() if case == "retained_single" else canonical({
            "jobId": self.job, "searchSequence": self.sequence, "numHits": 0, "hits": {}}).encode()
        self.submitted_file = None

    def _snapshot(self, action, request, content, *, representation=None):
        url = (BASE_URL + "/submit-job" if action == "submit" else result_url(self.job)
            + ("" if representation == "json" else "/" + representation))
        self.calls.append({"action": action, "url": url, "request": deepcopy(request),
            "response_sha256": hashlib.sha256(content).hexdigest(), "response_bytes": len(content)})
        prefix = self.directory / ("controlled-http-" + str(len(self.calls)))
        prefix.with_suffix(".body").write_bytes(content)
        _write(prefix.with_suffix(".json"), self.calls[-1])
        return SourceSnapshot("rfam_batch", url, {"action": action, **request},
            f"2026-10-26T12:00:{len(self.calls):02d}+00:00", content,
            "text/plain" if representation == "tblout" else "application/json",
            {"status": 200, "body_complete": True, "evidence_kind": "synthetic_fixture",
             "fixture_origin": "retained_native_body" if self.case == "retained_single" and action == "fetch"
                else "synthetic_response"})

    def submit(self, sequence):
        assert self.case != "selected_batch" and sequence == self.sequence
        self.submitted_file = (sequence + "\n").encode("ascii")
        return self._snapshot("submit", {"sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
            "sequence_length": len(sequence), **self._file_request("sequence.seq")},
            canonical({"jobId": self.job, "resultURL": result_url(self.job)}).encode())

    def _file_request(self, filename):
        return {"filename": filename, "file_sha256": hashlib.sha256(self.submitted_file).hexdigest(),
            "file_bytes": len(self.submitted_file),
            "file_base64": base64.b64encode(self.submitted_file).decode("ascii")}

    def submit_file(self, content, *, filename):
        assert self.case == "selected_batch" and filename == "sequences.fa"
        self.submitted_file = content
        names = [line[1:] for line in content.decode("ascii").splitlines() if line.startswith(">")]
        assert names == [f"rfam_query_{index:08d}" for index in range(4)]
        # Synthetic format-1 cmscan rows deliberately differ in order from the
        # four submitted occurrences. Occurrence 3 has zero reported matches.
        rows = [f"5S_rRNA RF00001 {names[index]} - cm 1 120 1 {span} + no 1 0.49 0.0 {score} 1e-8 ! synthetic family match"
            for index, span, score in ((2, 70, 30), (0, 80, 40), (1, 90, 50))]
        self.body = ("#target name accession query name accession mdl mdl from mdl to seq from seq to strand trunc pass gc bias score E-value inc description of target\n"
            + "\n".join(rows) + "\n#\n# Program: cmscan\n# Version: 1.1.5 (Sep 2023)\n"
            + "# Pipeline mode: SCAN\n# Query file: " + self.job + ".sequence\n"
            + "# Target file: synthetic-models.cm\n# Option settings: cmscan --tblout synthetic.tblout synthetic-models.cm "
            + self.job + ".sequence\n# [ok]\n").encode("ascii")
        return self._snapshot("submit", self._file_request(filename),
            canonical({"jobId": self.job, "resultURL": result_url(self.job)}).encode())

    def result(self, job_id, *, representation):
        assert job_id == self.job
        assert representation == ("tblout" if self.case == "selected_batch" else "json")
        return self._snapshot("fetch", {"job_id": job_id, "representation": representation},
            self.body, representation=representation)


@pytest.fixture(scope="module", params=("retained_single", "complete_empty", "selected_batch"))
def composed_rfam_run(request):
    RUNS.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=request.param + "-", dir=RUNS))
    provenance = {"case": request.param, "status": "started", "live_api": False,
        "configured_model": False, "native_program_executed": False, "hpc": False,
        "fixture_overrides": ["scripted model choices", "root/scientific continuation only", "controlled Rfam HTTP responses"],
        "production_overrides": [], "retained_native_sha256": hashlib.sha256(NATIVE_FILE.read_bytes()).hexdigest(),
        "native_fixture": str(NATIVE_FILE.relative_to(ROOT)),
        "qualification": "The retained single body is byte-exact; new request/submission custody is controlled. Empty and generated-header batch bodies are synthetic. No remote call occurs."}
    _write(directory / "PROVENANCE.json", provenance)
    native = ControlledRfam(request.param, directory)
    with pytest.MonkeyPatch.context() as patch, Store(directory / "state") as store:
        def forbidden(*args, **kwargs):
            raise AssertionError("Composed Rfam verification attempted live transport, subprocess or hidden wait")
        for name in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
                     "urllib.request.OpenerDirector.open", "subprocess.run", "subprocess.Popen", "time.sleep"):
            patch.setattr(name, forbidden)
        tools = ToolRegistry(store, clients=native)
        if request.param == "selected_batch":
            supplied = directory / "public-occurrences.fastq"
            supplied.write_text("".join(f"@original-{label}\n{native.sequence}\n+\n{'I' * len(native.sequence)}\n"
                for label in ("first", "second")))
            store.create_problem(supplied, molecule="dna")
            library_target, = store.targets()
            members = tools.execute("library.members", {"library_ref": library_target["id"]})
            assert members["status"] == "completed", members
            a, b = members["result"]["members"]
            selected_inputs = tools.execute("library.select", {"library_ref": library_target["id"],
                "member_refs": [b["member_ref"], a["member_ref"]]})
            assert selected_inputs["status"] == "completed", selected_inputs
            scope = selected_inputs["result"]["scope"]
            scientific_inputs = [b["id"], a["id"]]
            service_request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
                "subject_refs": [b["id"], a["id"], b["id"], a["id"]]}
            _write(directory / "caller-selected-inputs.json", {"inventory": members,
                "selection": selected_inputs, "request": service_request})
        else:
            target, = store.create_problem(raw_sequence=native.sequence, molecule="dna")["subject_refs"]
            scope, scientific_inputs = {"subject_refs": [target]}, [target]
            service_request = {"version": "rfam_batch_request_v1", "mode": "single_sequence", "subject_ref": target}
        selector = {"version": "rfam_batch_result_selector_v2" if request.param == "selected_batch"
            else "rfam_batch_result_selector_v1", "representation": "tblout" if request.param == "selected_batch"
            else "json", "model_metadata_ref": None, "projection": {"family": "hit",
            "rows": {"offset": 0, "limit": 2}, "metrics": METRICS}}
        assignment = {"version": "api_service_assignment_v1", "resource_id": "rfam", "service": "rfam_batch",
            "request": service_request, "endpoint": "usable_handoff", "constraints": {}}
        launch = launch_assignment({"rfam": assignment})
        handoff_form, parent_form, result_form = form("execution_handoff_refs"), _facts_form(), _facts_form()
        result_form["properties"]["completed"] = {"type": "boolean", "x-source": "execution_completed"}
        result_form["required"].append("completed")
        run_id, run_directory = "rfam-composed-" + request.param, directory / "run"
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=run_id, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / "scientific-process-library")

        def controllers(path, initial):
            def estimate(history, parameters, contexts):
                count = {"annotation": 1, "scientific_process": 2}[path[-1][0]]
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {"fixture": "root_and_scientific_continuation_only"})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process"} else None)

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
                    assert count == 1 and execution["selector"] == selector
                    return selected("api.rfam.fetch", {})
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
                    "child_tool_info": deepcopy(SELECTED_TOOLS)}, "evidence_refs": scientific_inputs,
                    "constraints": {"preserve_original_input_occurrences": True},
                    "context": {"supplied_sequence": native.sequence, "molecule": "dna", "complete": True,
                        "label_is_public_identity": False}}
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
                ("native-calls", native.calls), ("history", _history(store, run_id))):
                _write(directory / (name + ".json"), value)
            (directory / "native-result.body").write_bytes(native.body)
            (directory / "submitted-file.body").write_bytes(native.submitted_file)
            for index, call in enumerate(choices.calls):
                if "scientific_process" in call["current"]:
                    (directory / f"scientific-presentation-{index}.txt").write_text(
                        render_scientific_process_prompt(call["current"], call["instructions"]))
            provenance.update(status="workflow_closed", response_sha256=hashlib.sha256(native.body).hexdigest(),
                own_actions={row["scope_level"]: row["units_consumed"]
                    for row in (archive, scientific, launch_record, api_record, results)})
            _write(directory / "PROVENANCE.json", provenance)
            yield SimpleNamespace(store=store, workflow=workflow, api=api, choices=choices, native=native,
                archive=archive, scientific=scientific, launch=launch_record, api_record=api_record, results=results,
                returned=returned, forwarded=forwarded, final_ref=final_ref, body=body, manifest=manifest,
                parsed=parsed, sheet=sheet, calculation=calculation, scope=scope, directory=directory,
                run_directory=run_directory, case=request.param, selector=selector, service_request=service_request,
                episode=episode, library=library, parent_form=parent_form, result_form=result_form,
                construct=construct, execute=execute)
        except BaseException as error:
            provenance.update(status="failed", error_type=type(error).__name__, error=str(error))
            _write(directory / "PROVENANCE.json", provenance)
            _write(directory / "failed-history.json", _history(store, run_id))
            raise


def test_three_slots_selected_tools_and_actual_child_owners(composed_rfam_run):
    run = composed_rfam_run
    binding = run.workflow.scientific_process_binding
    context = run.api.rfam_returns.context(run.scientific["episode_id"])
    binding.validate_context(context)
    information = binding.tool_library.resolve_tool_info(SELECTED_TOOLS,
        run.workflow.services.tool_information_catalog(run.scope))
    assert plain(context.assignment)["selection"]["child_tool_info"] == information
    assert plain(context.assignment)["selection"]["evidence_axis"] == run.library.reference("A101")
    assert plain(context.assignment)["selection"]["thought_pattern"] == run.library.reference("P01")
    assert run.workflow.catalog(run.scope, source=run.episode.source) == []
    assert not any(row["name"].startswith(("api.rfam.", "public.rfam.")) for row in binding.catalog(context))
    execution = run.workflow.episode_bindings.for_role("results")
    numerical_sources = {"rfam_result_rows", "rfam_result_populations"}
    assert numerical_sources <= execution.fact_sources("results").keys()
    for role in ("launch", "launch_api"):
        assert not numerical_sources.intersection(execution.fact_sources(role))
    for role in ("scientific_process", "annotation"):
        assert numerical_sources <= execution.received_report_sources(role).keys()
    contracts = binding.tool_library.resolve_invocations(SELECTED_TOOLS,
        run.workflow.services.tool_information_catalog(run.scope))
    for row in contracts:
        owner = "launch_api" if row["name"] == "api.rfam.submit" else "results"
        assert row["invocation_route"] == {"kind": "commission", "routes": [{
            "entry_role": "launch" if owner == "launch_api" else owner,
            "resource_id": "rfam", "resource_role": owner}]}
    for call in run.choices.calls:
        if "scientific_process" not in call["current"]:
            continue
        prompt = render_scientific_process_prompt(call["current"], call["instructions"])
        task, steering = prompt.split("\n\nSTEERING", 1)
        assert task.startswith("TASK\n")
        for row in information:
            assert row["instructions"] in task and row["instructions"] not in steering
        assert call["current"]["scientific_process"]["evidence_axis"]["investigation_instructions"] in task
        assert "rfam_batch_sheet_v1" not in prompt and "infernal_search_sheet_v1" not in prompt
    for option in ("A101", "P01"):
        assert (run.run_directory / "scientific-process-library/entries" / (option + ".json")).read_bytes() == (
            PUBLICATION / "entries" / (option + ".json")).read_bytes()


def test_requested_rows_population_and_original_bytes_cross_both_boundaries(composed_rfam_run):
    run = composed_rfam_run
    assert run.returned["completed"] is True
    assert run.forwarded == {key: run.returned[key] for key in ("measurements", "populations")}
    assert set(run.returned) == {"measurements", "populations", "completed"}
    assert set(run.forwarded) == {"measurements", "populations"}
    projection = run.body["projection"]
    assert run.forwarded["measurements"] == [{"source_ref": run.final_ref, **row,
        "population_complete": projection["population_complete"]} for row in projection["rows"]]
    for row in run.forwarded["measurements"]:
        assert set(row) == {"source_ref", "record_key", "query_occurrence_key", "family_accession",
            "strand", "measured", "unavailable", "population_complete"}
        assert {cell["name"] for cell in row["measured"] + row["unavailable"]} == set(METRICS)
        assert row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
    for child, parent, expected in ((run.results, run.scientific, run.returned),
            (run.scientific, run.archive, run.forwarded)):
        admission = run.store.db.execute("SELECT parent_episode_id,form,failure FROM runtime_report_attempts "
            "WHERE run_id=? AND child_episode_id=?", (run.workflow.run_id, child["episode_id"])).fetchone()
        assert admission["parent_episode_id"] == parent["episode_id"] and admission["failure"] is None
        assert json.loads(admission["form"]) == expected
        context = run.api.rfam_returns.context(parent["episode_id"])
        facts = run.api.rfam_returns.received_facts(context, run.parent_form)
        assert facts == {"rfam_result_rows": expected["measurements"], "rfam_result_populations": expected["populations"]}
    saved = run.body["publication_result"]
    assert run.store.get_artifact(saved["artifact_ref"]) == run.native.body
    assert run.body["service_request"] == run.service_request
    assert run.body["assignment"]["selector"] == run.selector
    assert run.manifest["selector"] == run.selector and run.manifest["request"] == run.service_request
    assert run.body["target"]["origin_episode_id"] == run.api_record["episode_id"]
    assert run.body["target"]["execution_id"] == run.native.job
    grading = run.store.get(saved["grading_source_ref"])
    assert grading["parent_source_refs"] == [saved["submission_source_ref"], run.final_ref]
    assert run.store.db.execute("SELECT count(*) FROM provider_jobs").fetchone()[0] == 0
    assert run.store.count("annotation") == run.store.count("observation") == 0


def test_numerical_answers_and_original_occurrence_associations(composed_rfam_run):
    run = composed_rfam_run
    rows = run.returned["measurements"]
    population, = run.returned["populations"]
    assert population["source_ref"] == run.final_ref and population["population_complete"] is True
    if run.case == "retained_single":
        assert run.native.body == NATIVE_FILE.read_bytes()
        row, = rows
        assert {cell["name"]: cell["value"] for cell in row["measured"]} == {
            "native_score_bits": 104.6, "native_evalue": 1.4e-24, "native_gc_fraction": .49,
            "query_span_nt": 119, "query_span_fraction": 1.0}
        assert row["query_occurrence_key"] == run.sheet["input"]["query_occurrence_key"]
        assert run.sheet["input"]["subject_ref"] == run.service_request["subject_ref"]
        hit, = run.calculation["hits"]
        assert hit["represented_model_positions"] == 120
        assert hit["model_consensus_compared_count"] == 118 and hit["model_consensus_equal_count"] == 75
        assert hit["model_coverage_fraction"] is None
        assert population["available_row_count"] == population["selected_row_count"] == 1
    elif run.case == "complete_empty":
        assert rows == [] and run.sheet["hits"] == run.calculation["hits"] == []
        assert population["available_row_count"] == population["selected_row_count"] == 0
        assert run.sheet["population"]["reported_set_complete"] is True
        assert len(run.calculation["query_strands"]) == 2
        assert all(row["query_strand_union_span_nt"] == row["query_strand_union_fraction"] == 0
            and row["population_complete"] for row in run.calculation["query_strands"])
    else:
        queries = run.parsed["input_identity"]["queries"]
        assert len(queries) == 4 and len({row["query_occurrence_key"] for row in queries}) == 4
        assert [row["subject_ref"] for row in queries] == run.service_request["subject_refs"]
        assert [row["selected_occurrence_ordinal"] for row in queries] == [0, 1, 2, 3]
        assert [row["original_record_ordinal"] for row in queries] == [
            run.store.get(ref)["source_ordinal"] for ref in run.service_request["subject_refs"]]
        assert queries[0]["original_input_ref"] == queries[2]["original_input_ref"]
        assert queries[1]["original_input_ref"] == queries[3]["original_input_ref"]
        assert len({row["submitted_sequence_sha256"] for row in queries}) == 1
        assert [row["query_occurrence_key"] for row in run.calculation["hits"]] == [
            queries[index]["query_occurrence_key"] for index in (2, 0, 1)]
        assert [row["query_occurrence_key"] for row in rows] == [
            queries[index]["query_occurrence_key"] for index in (2, 0)]
        assert [next(cell["value"] for cell in row["measured"] if cell["name"] == "native_score_bits")
            for row in rows] == [30, 40]
        assert [next(cell["value"] for cell in row["measured"] if cell["name"] == "query_span_fraction")
            for row in rows] == [70 / 119, 80 / 119]
        assert population["available_row_count"] == 3 and population["selected_row_count"] == 2
        assert population["more_rows"] is True
        assert len(run.sheet["hits"]) == 3 and len(run.calculation["native_calculation"]["hits"]) == 3
        missing = [row for row in run.calculation["query_strands"]
            if row["query_occurrence_key"] == queries[3]["query_occurrence_key"]]
        assert len(missing) == 2 and all(row["selected_row_count"] == row["query_strand_union_span_nt"] == 0
            and row["population_complete"] for row in missing)
        assert run.parsed["query_population"][3]["reported_row_count"] == 0


def test_exact_action_observations_and_production_practical_terminal_zero(composed_rfam_run):
    run = composed_rfam_run
    expected = [(run.archive, ["episode_child:scientific_process"]),
        (run.scientific, ["episode_child:launch", "episode_child:results"]),
        (run.launch, ["episode_child:launch_api"]), (run.api_record, ["api.rfam.submit"]),
        (run.results, ["api.rfam.fetch"])]
    for closed, names in expected:
        assert closed["units_consumed"] == len(names) == run.choices.counts[closed["episode_id"]]
        for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
            assert run.store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (run.workflow.run_id, closed["episode_id"])).fetchone()[0] == len(names)
        actions = [json.loads(row[0]) for row in run.store.db.execute(
            "SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",
            (run.workflow.run_id, closed["episode_id"]))]
        assert [a["tool"] if a["kind"] == "tool" else a["kind"] + ":" + a["role"] for a in actions] == names
    for closed, expected_gain in ((run.launch, 3), (run.api_record, 3), (run.results, 2)):
        assert closed["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        assert closed["units"][-1]["controller_step"]["marginal_credit"] == expected_gain
        context = run.api.rfam_returns.context(closed["episode_id"])
        family = run.workflow.episode_bindings.for_role(context.role)
        key = f"{context.run_id}:{context.episode_id}:0"
        proof = family.completion_for_action(context, key)
        assert proof and family.verify_completion(context, proof)
    for closed in (run.archive, run.scientific):
        assert all(unit["controller_step"]["marginal_credit"] == 0 for unit in closed["units"])
    assert len(run.choices.calls) == 6 and [row["action"] for row in run.native.calls] == ["submit", "fetch"]
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations WHERE run_id=?",
        (run.workflow.run_id,)).fetchone()[0] == 6
    pairs = run.store.db.execute("SELECT a.action,m.response,m.purpose FROM runtime_actions a "
        "JOIN runtime_model_calls m ON m.run_id=a.run_id AND m.episode_id=a.episode_id "
        "AND m.call_index=a.decision_index WHERE a.run_id=?", (run.workflow.run_id,)).fetchall()
    assert len(pairs) == 6 and all(row["purpose"] == "decision"
        and json.loads(row["action"]) == json.loads(row["response"])["selection"] for row in pairs)


def test_saved_recalculation_and_reopened_workflow_preserve_completed_history(composed_rfam_run, monkeypatch):
    run = composed_rfam_run
    history, calls = _history(run.store, run.workflow.run_id), deepcopy(run.native.calls)
    if run.case == "selected_batch":
        recalculated = calculate_rfam_batch_table_components(deepcopy(run.parsed), parameters={"hit_scope": "reported"})
    else:
        recalculated = calculate_rfam_batch_components(deepcopy(run.sheet), parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
    assert recalculated == run.calculation
    _write(run.directory / "recalculated.json", recalculated)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved replay must not acquire, parse, calculate or call a model")
    for name in ("submit", "submit_file", "result"):
        monkeypatch.setattr(run.native, name, forbidden)
    for path in ("gene_annotation_episode.rfam_batch_publication.populate_rfam_batch_json_sheet",
        "gene_annotation_episode.rfam_batch_publication.calculate_rfam_batch_components",
        "gene_annotation_episode.rfam_batch_publication.parse_rfam_alignment_display",
        "gene_annotation_episode.rfam_batch_table.populate_rfam_batch_tblout_sheet",
        "gene_annotation_episode.rfam_batch_table_grader.calculate_rfam_batch_table_components"):
        monkeypatch.setattr(path, forbidden)
    class NoModel:
        async def complete(self, *args, **kwargs):
            forbidden()
        async def release(self, episode_id):
            pass
    with Store(run.directory / "state") as reopened_store:
        reopened_tools = ToolRegistry(reopened_store, clients=run.native)
        reopened = run.construct(NoModel(), storage=reopened_store, registry=reopened_tools)
        root = reopened.build("annotation", "root", GOAL, run.scope)
        archive = asyncio.run(run.execute(root, reopened))
        assert archive == run.archive
        assert _history(reopened_store, run.workflow.run_id) == history and run.native.calls == calls
        restored_api = reopened.episode_bindings.for_role("results").api_execution
        assert restored_api.rfam_returns.read(run.final_ref, run.scope) == run.body
        for closed, name in ((run.api_record, "api.rfam.submit"), (run.results, "api.rfam.fetch")):
            context = restored_api.rfam_returns.context(closed["episode_id"])
            key = f"{context.run_id}:{context.episode_id}:0"
            # API replay returns its original outcome; runtime separately appends
            # pending_work_after_action. The complete enriched runtime history was
            # compared above and remains unchanged below.
            saved = json.loads((restored_api._episode_directory(context.episode_id)
                / "actions" / digest(key) / "outcome.json").read_text())
            assert asyncio.run(restored_api.execute(context, name, {}, key)) == saved
    assert _history(run.store, run.workflow.run_id) == history and run.native.calls == calls
    _write(run.directory / "reopened-archive.json", archive)
    _write(run.directory / "replay-verification.json", {"new_native_calls": 0, "new_model_calls": 0,
        "completed_history_unchanged": True, "archive_unchanged": True,
        "saved_sheet_recalculation_equal": True})
