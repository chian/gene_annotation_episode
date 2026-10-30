"""One live Rfam job through Workflow; episode decisions are engineering scripts.

No transport, publication, admission, operational credit, or practical terminal
logic is replaced. If the first observation is not terminal, the same live
Workflow awaits an explicit operator decision through a one-request socket.
There is no polling/retry loop or new submission fallback in this harness.
"""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from method_loop.archive import iter_json
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.rfam_batch_returns import rfam_fact_sources
from gene_annotation_episode.rfam_batch_table_grader import calculate_rfam_batch_table_components
from gene_annotation_episode.rfam_batch_transport import RfamBatchHTTP
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path.cwd()
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
PUBLIC_INPUT = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/input.seq"
RESOURCES = {"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90.0}}
SELECTED_TOOLS = [{"name": name, "resources": "api"}
    for name in ("api.rfam.submit", "api.rfam.status", "api.rfam.fetch")]
METRICS = ["native_score_bits", "native_evalue", "query_length_nt", "native_start_1i",
    "native_end_1i", "query_span_nt", "query_span_fraction", "model_coverage_fraction"]
GOAL = "Measure Rfam family-model matches and query coverage for the three selected public nucleotide input occurrences"
RUN_ID = "rfam-live-composed-243"
HISTORY_TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations",
    "runtime_model_calls", "runtime_report_attempts", "runtime_forms")


def write(name, value):
    path = DIRECTORY / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def history(store):
    return {table: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + table + " WHERE run_id=? ORDER BY rowid", (RUN_ID,))]
        for table in HISTORY_TABLES}


def child(role, assignment, scope, schema):
    return {"selection": {"kind": "episode_child", "role": role, "goal": GOAL,
        "scope": scope, "purpose": "Return only the requested native score, E-value, query length, native endpoints, span and span fraction, explicit unavailable full-model coverage, and population sizes; preserve each original input occurrence",
        "assignment": deepcopy(assignment), "schema_json": json.dumps(schema),
        "initial_report_json": "{}"}, "report_update": {}}


def selected(name):
    return {"selection": {"kind": "tool", "tool": name, "arguments": {}}, "report_update": {}}


def facts_form():
    sources = rfam_fact_sources()
    properties = {"measurements": sources["rfam_result_rows"]["report_schema"],
        "populations": sources["rfam_result_populations"]["report_schema"]}
    return {"type": "object", "additionalProperties": False,
        "properties": properties, "required": list(properties)}


def handoff_form():
    return {"type": "object", "properties": {
        "completed": {"type": "boolean", "x-source": "execution_completed"},
        "references": {"type": "array", "uniqueItems": True, "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "execution_handoff"},
            "x-source": "execution_handoff_refs"},
        "yield": report_sources()["episode_yield"]["report_schema"]},
        "required": ["completed", "references", "yield"], "additionalProperties": False}


def forbidden(*args, **kwargs):
    raise AssertionError("Completed replay must not acquire, parse, calculate or call a model")


async def execute(episode, workflow):
    record = await episode.run_async(workflow.context)
    await episode.build_result(record)
    return json.loads("".join(iter_json(record.as_record())))


async def operator_choice(episode_id, current, events):
    """One explicit engineering choice, without autonomous polling or timeout."""
    request = {"episode_id": episode_id, "current": current, "actual_events": events,
        "allowed_tools": ["api.rfam.status", "api.rfam.fetch"],
        "qualification": "Operator chooses one next decision for this same live Workflow; no resubmission permitted"}
    write("pending-operator-choice.json", request)
    print(json.dumps({"needs_operator_choice": True, "episode_id": episode_id,
        "socket": str(DIRECTORY / "choice.sock")}), flush=True)
    future = asyncio.get_running_loop().create_future()
    async def receive(reader, writer):
        try:
            value = json.loads(await reader.readline())
            if value not in request["allowed_tools"]:
                raise ValueError("Only one selected status or fetch of the original handle is allowed")
            future.set_result(selected(value))
            writer.write(b"accepted\n")
            await writer.drain()
        except BaseException as error:
            if not future.done():
                future.set_exception(error)
        finally:
            writer.close()
            await writer.wait_closed()
    server = await asyncio.start_unix_server(receive, "choice.sock")
    try:
        return await future
    finally:
        server.close()
        await server.wait_closed()
        (DIRECTORY / "choice.sock").unlink(missing_ok=True)


def main():
    if (DIRECTORY / "state").exists():
        raise RuntimeError("Use the original live Workflow; this launch script never restarts or creates replacement work")
    original = PUBLIC_INPUT.read_text().strip()
    assert len(original) == 119 and set(original) <= set("ACGT")
    reverse = original.translate(str.maketrans("ACGT", "TGCA"))[::-1]
    supplied = DIRECTORY / "public-inputs.fa"
    supplied.write_text(f">public-original\n{original}\n>public-reverse-complement\n{reverse}\n")
    provenance = {"scope": "Real remote Rfam scientific execution through current Workflow with explicit scripted engineering episode decisions",
        "live_api": True, "configured_model": False, "local_scientific_program": False,
        "hpc": False, "production_overrides": [],
        "fixtures": ["episode decisions", "root/scientific continuation only", "zero root/scientific credit projector"],
        "public_input_path": str(PUBLIC_INPUT.relative_to(ROOT)),
        "public_input_sha256": hashlib.sha256(PUBLIC_INPUT.read_bytes()).hexdigest(),
        "resource_configuration": RESOURCES, "status": "started"}
    write("PROVENANCE.json", provenance)
    with Store(DIRECTORY / "state") as store:
        tools = ToolRegistry(store)
        subjects = store.create_problem(supplied, molecule="dna")["subject_refs"]
        assert len(subjects) == 2
        scope = {"subject_refs": subjects}
        request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch",
            "subject_refs": [subjects[0], subjects[0], subjects[1]]}
        selector = {"version": "rfam_batch_result_selector_v2", "representation": "tblout",
            "model_metadata_ref": None, "projection": {"family": "hit",
                "rows": {"offset": 0, "limit": 100}, "metrics": METRICS}}
        assignment = {"version": "api_service_assignment_v1", "resource_id": "rfam", "service": "rfam_batch",
            "request": request, "endpoint": "usable_handoff", "constraints": {}}
        launch_assignment = {"version": "execution_launch_assignment_v1", "requests": {"rfam": assignment},
            "immutable_input_versions": [], "constraints": {"allowed_resource_ids": ["rfam"], "allowed_kinds": ["api"]}}
        parent_form, result_form, handoff = facts_form(), facts_form(), handoff_form()
        result_form["properties"]["completed"] = {"type": "boolean", "x-source": "execution_completed"}
        result_form["required"].append("completed")
        write("caller-selected-inputs.json", {"scope": scope, "subjects": subjects, "request": request,
            "selector": selector, "sequence_transform": {subjects[0]: "unchanged", subjects[1]: "DNA reverse complement"}})
        write("requested-forms.json", {"handoff": handoff, "scientific": parent_form, "results": result_form})
        run_directory = DIRECTORY / "run"
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=RUN_ID, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = prepare_scientific_binding(run_directory=run_directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(run_directory / "scientific-process-library")

        def controllers(path, initial):
            def estimate(history_values, parameters, contexts):
                count = {"annotation": 1, "scientific_process": 2}[path[-1][0]]
                return YieldEstimate(len(history_values), NumericBand.exact(0 if len(history_values) >= count else 1),
                    parameters, {"fixture": "root_and_scientific_continuation_only"})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process"} else None)

        class Choices:
            def __init__(self):
                self.counts, self.calls = {}, []

            async def complete(self, episode_id, role, instructions, current, schema):
                self.calls.append({"episode_id": episode_id, "role": role, "instructions": instructions,
                    "current": deepcopy(current), "schema": deepcopy(schema), "decision_kind": "scripted_engineering_choice"})
                write("scripted-decisions.json", self.calls)
                self.counts[episode_id] = count = self.counts.get(episode_id, 0) + 1
                execution = current.get("execution_assignment", {})
                if current.get("feedback") is not None:
                    return await operator_choice(episode_id, current, api._events(episode_id))
                if execution.get("version") == "execution_launch_assignment_v1":
                    assert count == 1 and execution == launch_assignment
                    return child("launch_api", assignment, scope, handoff)
                if execution.get("version") == "api_service_assignment_v1":
                    assert count == 1 and execution == assignment
                    return selected("api.rfam.submit")
                if execution.get("version") == "execution_results_assignment_v1":
                    assert execution["selector"] == selector
                    events = api._events(episode_id)
                    if not events:
                        return selected("api.rfam.status")
                    last = events[-1]
                    if last["name"] == "api.rfam.status" and last["event"]["state"] == "completed":
                        return selected("api.rfam.fetch")
                    return await operator_choice(episode_id, current, events)
                if "scientific_process" in current:
                    assert current["scientific_process"]["selection"]["child_tool_info"] == SELECTED_TOOLS
                    if count == 1:
                        return child("launch", launch_assignment, scope, handoff)
                    assert count == 2
                    received = current["child_reports"][-1]
                    assert received["completed"] is True
                    reference, = received["references"]
                    target = api.read_target(reference, scope)
                    native_handle = api._native_handle(target)
                    write("original-handle.json", {"target": target, "native_handle": native_handle})
                    print(json.dumps({"submitted_original_job": native_handle}), flush=True)
                    return child("results", {"version": "execution_results_assignment_v1",
                        "handoff_ref": reference, "selector": selector}, scope, result_form)
                assert count == 1 and episode_id == episode.source.episode_id
                available = workflow.scientific_process_binding.tool_library.parent_tool_info(
                    workflow.services.tool_information_catalog(scope))
                assert all(any((row["name"], row["resources"]) == (tool["name"], tool["resources"])
                    for row in available) for tool in SELECTED_TOOLS)
                scientific_assignment = {"selection": {"version": "scientific_process_selection_v3",
                    "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                    "child_tool_info": deepcopy(SELECTED_TOOLS)}, "evidence_refs": subjects,
                    "constraints": {"preserve_original_input_occurrences": True},
                    "context": {"supplied_sequence": original, "molecule": "dna", "complete": True,
                        "label_is_public_identity": False}}
                return child("scientific_process", scientific_assignment, scope, parent_form)

            async def release(self, episode_id):
                pass

        def construct(provider, storage, registry):
            current_application = factory(storage, run_id=RUN_ID, directory=run_directory,
                tool_registry=registry, tool_catalog=registry.catalog())
            value = Workflow(storage, registry, provider, run_directory, RUN_ID,
                controller_factory=controllers, project_credit=lambda *_: 0,
                episode_binding_descriptors=(descriptor, *current_application.episode_binding_descriptors),
                role_credit_bindings=current_application.role_credit_bindings,
                job_progress_provider=current_application.job_progress_provider,
                annotation_child_roles=("scientific_process",), episode_record_receipts=True,
                initial_known_record_refs=[])
            client = value.episode_bindings.for_role("results").api_execution.services["rfam"].client
            assert type(client) is RfamBatchHTTP and client.timeout_seconds == 90
            return value

        choices = Choices()
        workflow = construct(choices, store, tools)
        api = workflow.episode_bindings.for_role("results").api_execution
        episode = workflow.build("annotation", "root", GOAL, scope)
        try:
            archive = asyncio.run(execute(episode, workflow))
            scientific = archive["units"][0]["child"]
            launch = scientific["units"][0]["child"]
            api_record = launch["units"][0]["child"]
            results = scientific["units"][1]["child"]
            returned = json.loads(workflow.journal.row("runtime_forms", results["episode_id"])["form"])
            forwarded = json.loads(workflow.journal.row("runtime_forms", scientific["episode_id"])["form"])
            assert returned["completed"] is True
            assert forwarded == {key: returned[key] for key in ("measurements", "populations")}
            assert set(returned) == {"measurements", "populations", "completed"}
            assert set(forwarded) == {"measurements", "populations"}
            final_ref, = {row["source_ref"] for row in returned["populations"]}
            body = api.rfam_returns.read(final_ref, scope)
            saved = body["publication_result"]
            grading = store.get(saved["grading_source_ref"])
            manifest = json.loads(store.get_artifact(grading["artifact_ref"]))
            parsed = json.loads(store.get_artifact(manifest["parse_ref"]))
            sheet = json.loads(store.get_artifact(saved["sheet_ref"]))
            calculation = json.loads(store.get_artifact(saved["calculation_ref"]))
            for name, value in (("archive", archive), ("results-return", returned), ("scientific-return", forwarded),
                ("publication", body), ("grading-manifest", manifest), ("parse", parsed), ("sheet", sheet),
                ("calculation", calculation), ("history", history(store))):
                write(name + ".json", value)
            snapshots = []
            for path in sorted(api.directory.glob("episodes/*/actions/*/snapshot.json")):
                metadata = json.loads(path.read_text())
                snapshot = api._load_snapshot(metadata)
                action = snapshot.request["action"]
                (DIRECTORY / ("http-" + action + "-" + path.parent.name + ".body")).write_bytes(snapshot.content)
                snapshots.append({"snapshot_path": str(path), **metadata})
                if action == "submit":
                    (DIRECTORY / "submitted-file.body").write_bytes(base64.b64decode(snapshot.request["file_base64"]))
            write("http-snapshots.json", snapshots)
            (DIRECTORY / "native-result.tblout").write_bytes(store.get_artifact(saved["artifact_ref"]))
            for index, call in enumerate(choices.calls):
                if "scientific_process" in call["current"]:
                    (DIRECTORY / f"scientific-presentation-{index}.txt").write_text(
                        render_scientific_process_prompt(call["current"], call["instructions"]))

            queries = parsed["input_identity"]["queries"]
            assert len(queries) == 3 and len({q["query_occurrence_key"] for q in queries}) == 3
            assert [q["subject_ref"] for q in queries] == request["subject_refs"]
            assert queries[0]["original_input_ref"] == queries[1]["original_input_ref"]
            assert queries[0]["submitted_sequence"] == queries[1]["submitted_sequence"] == original
            assert queries[2]["submitted_sequence"] == reverse
            assert [q["native_query_name"] for q in queries] == [f"rfam_query_{i:08d}" for i in range(3)]
            assert [q["selected_occurrence_ordinal"] for q in queries] == [0, 1, 2]
            assert len(returned["measurements"]) == len(sheet["hits"]) == 3
            compact = []
            for index, query in enumerate(queries):
                row, = [r for r in returned["measurements"] if r["query_occurrence_key"] == query["query_occurrence_key"]]
                values = {cell["name"]: cell["value"] for cell in row["measured"]}
                assert set(values) == set(METRICS) - {"model_coverage_fraction"}
                assert row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
                assert row["strand"] == ("+" if index < 2 else "-")
                assert row["family_accession"] == "RF00001"
                assert values["query_length_nt"] == values["query_span_nt"] == 119
                assert values["query_span_fraction"] == 119 / 119
                assert (values["native_start_1i"], values["native_end_1i"]) == ((1, 119) if index < 2 else (119, 1))
                compact.append({"selection_ordinal": index, "query_occurrence_key": query["query_occurrence_key"],
                    "subject_ref": query["subject_ref"], "family_accession": row["family_accession"],
                    "strand": row["strand"], **values, "unavailable": row["unavailable"]})
            population, = returned["populations"]
            assert population["population_complete"] and population["available_row_count"] == population["selected_row_count"] == 3
            assert population["more_rows"] is False
            assert all(hit["model_coverage_fraction"] is None for hit in calculation["hits"])

            for child_record, parent_record, expected in ((results, scientific, returned), (scientific, archive, forwarded)):
                admission = store.db.execute("SELECT parent_episode_id,form,failure FROM runtime_report_attempts "
                    "WHERE run_id=? AND child_episode_id=?", (RUN_ID, child_record["episode_id"])).fetchone()
                assert admission["parent_episode_id"] == parent_record["episode_id"] and admission["failure"] is None
                assert json.loads(admission["form"]) == expected
                facts = api.rfam_returns.received_facts(api.rfam_returns.context(parent_record["episode_id"]), parent_form)
                assert facts == {"rfam_result_rows": expected["measurements"], "rfam_result_populations": expected["populations"]}

            action_summary = []
            for closed in (archive, scientific, launch, api_record, results):
                episode_id = closed["episode_id"]
                actions = [json.loads(row[0]) for row in store.db.execute(
                    "SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index", (RUN_ID, episode_id))]
                observations = store.db.execute("SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?", (RUN_ID, episode_id)).fetchone()[0]
                assert closed["units_consumed"] == len(actions) == observations == choices.counts[episode_id]
                action_summary.append({"role": closed["scope_level"], "episode_id": episode_id,
                    "actions": [a["tool"] if a["kind"] == "tool" else a["kind"] + ":" + a["role"] for a in actions],
                    "observation_count": observations,
                    "actual_gains": [u["controller_step"]["marginal_credit"] for u in closed["units"]],
                    "terminal_expected_gain": closed["controller_state"]["estimate"]["expected_next_gain"]})
            for closed, gain in ((launch, 3), (api_record, 3), (results, 2)):
                assert closed["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
                assert closed["units"][-1]["controller_step"]["marginal_credit"] == gain
                context = api.rfam_returns.context(closed["episode_id"])
                family = workflow.episode_bindings.for_role(context.role)
                last_index = store.db.execute("SELECT max(decision_index) FROM runtime_actions WHERE run_id=? AND episode_id=?",
                    (RUN_ID, context.episode_id)).fetchone()[0]
                key = f"{RUN_ID}:{context.episode_id}:{last_index}"
                proof = family.completion_for_action(context, key)
                assert proof and family.verify_completion(context, proof)
            assert all(u["controller_step"]["marginal_credit"] == 0 for closed in (archive, scientific) for u in closed["units"])
            assert store.count("annotation") == store.count("observation") == 0
            assert sum(s["request"]["action"] == "submit" for s in snapshots) == 1
            assert all(s["transport"]["http_request_count"] == 1 and not s["transport"]["automatic_retries"] for s in snapshots)
            write("action-observation-verification.json", action_summary)

            with patch("socket.socket.connect", forbidden), patch("socket.create_connection", forbidden):
                recalculated = calculate_rfam_batch_table_components(deepcopy(parsed), parameters={"hit_scope": "reported"})
            assert recalculated == calculation
            write("recalculated.json", recalculated)
            original_history = history(store)
            class NoModel:
                async def complete(self, *args, **kwargs):
                    forbidden()
                async def release(self, episode_id):
                    pass
            with patch("socket.create_connection", forbidden), patch("socket.socket.connect", forbidden), \
                 patch("socket.socket.connect_ex", forbidden), patch.object(RfamBatchHTTP, "_request", forbidden), \
                 patch("gene_annotation_episode.rfam_batch_table.populate_rfam_batch_tblout_sheet", forbidden), \
                 patch("gene_annotation_episode.rfam_batch_table_grader.calculate_rfam_batch_table_components", forbidden), \
                 patch("gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet", forbidden), \
                 patch("gene_annotation_episode.infernal_search_grader.calculate_infernal_search_scores", forbidden):
                with Store(DIRECTORY / "state") as reopened_store:
                    reopened = construct(NoModel(), reopened_store, ToolRegistry(reopened_store))
                    reopened_root = reopened.build("annotation", "root", GOAL, scope)
                    reopened_archive = asyncio.run(execute(reopened_root, reopened))
                    assert reopened_archive == archive and history(reopened_store) == original_history
                    restored_api = reopened.episode_bindings.for_role("results").api_execution
                    assert restored_api.rfam_returns.read(final_ref, scope) == body
                    for closed in (api_record, results):
                        context = restored_api.rfam_returns.context(closed["episode_id"])
                        for path in restored_api._action_paths(context.episode_id):
                            intent = json.loads(path.read_text())
                            expected = json.loads((path.parent / "outcome.json").read_text())
                            assert asyncio.run(restored_api.execute(context, intent["name"], intent["arguments"], intent["operation_key"])) == expected
                    assert history(reopened_store) == original_history
            assert history(store) == original_history
            write("reopened-archive.json", reopened_archive)
            replay = {"network_calls": 0, "parser_calls": 0, "calculator_calls": 0, "model_calls": 0,
                "completed_history_unchanged": True, "archive_unchanged": True, "original_outcomes_equal": True,
                "original_typed_returns_equal": True, "saved_recalculation_equal": True}
            write("replay-verification.json", replay)
            summary = {"job": body["target"]["execution_id"], "rows": compact, "population": population,
                "actions": action_summary, "replay": replay, "http_requests": len(snapshots),
                "qualification": provenance["scope"]}
            write("SUMMARY.json", summary)
            provenance["status"] = "verified_complete_live_path"
            write("PROVENANCE.json", provenance)
            print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
        except BaseException as error:
            provenance.update(status="unfinished", error_type=type(error).__name__, error=str(error))
            write("PROVENANCE.json", provenance)
            write("unfinished-history.json", history(store))
            raise
        finally:
            loaded = {}
            for name, module in tuple(sys.modules.items()):
                raw = getattr(module, "__file__", None)
                if raw:
                    path = Path(raw).resolve()
                    if path.is_relative_to(ROOT) and path.suffix == ".py" and ".venv" not in path.parts:
                        loaded[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            write("loaded-source-hashes.json", loaded)


if __name__ == "__main__":
    main()
