"""New supplied-File request through real native, saved and typed episode paths."""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.genomic_overlap_return_views import PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.native_genomic_overlap_contracts import genomic_overlap_output_files
from gene_annotation_episode.native_genomic_overlap_local import local_genomic_overlap_plan
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def test_file_only_native_saved_and_full_saved_results_builder(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_OVERLAP_FILE_WORKFLOW") != "1":
        pytest.skip("explicit tiny native File-only workflow selection required")
    fixture_root = Path(__file__).parent / "retained_workflow_fixtures"
    monkeypatch.syspath_prepend(str(fixture_root))
    f = import_module("verification.tool_graders_genomic_overlap_workflow_2026-10-27_437.fixture_helpers")
    directory = tmp_path / "file-only-workflow"
    directory.mkdir()
    role = dict(model="presentation-engineering-control", reasoning_effort="low")
    session = _SessionConnection({"connection": {"command": ["unselected-model-command"]},
        "FAST": role, "REASONING": role, "routing": {}}, directory / "presentation", directory)
    question = ("For these supplied BED and coordinate-row Files, what are the unstranded overlap "
        "count, covered-base intersection and union, and Jaccard ratio? Recalculate the saved "
        "sheet with minimum_overlap_bp=6 and retain the original geometry and unknown reference.")
    proof = dict(version="genomic_overlap_file_workflow_verification_v1", passed=False,
        historical_science_reexecuted=False, new_request_native_pairs=1,
        input_acquisition_sources_created=0, saved_full_builder_verified=False)
    calls, saved_input_bytes = [], {}
    with Store(directory / "state") as store:
        store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
        scope = store.validate_scope()
        specs, inputs, initial = [], [], []
        before_sources = store.count("source")
        for key, raw, format in (
                ("A", b"chr1\t0\t10\n", "bed_outer_span_v1"),
                ("B", b'[["chr1",5,15]]', "coordinate_rows_v1")):
            artifact = store.artifact(raw)
            file = f.identity(store, artifact, format)
            specs.append(dict(set_key=key, display_label=None, source=dict(
                kind="bed_artifact" if key == "A" else "coordinate_rows_artifact", file=file),
                reference=None, format=format))
            inputs.append(dict(set_key=key, path=str(f.artifact_path(store, file))))
            initial.append(artifact)
        assert store.count("source") == before_sources
        request = dict(version="genomic_overlap_request_v1", operation="analyze_genomic_region_overlap",
            mode="unstranded_outer_span", region_sets=specs, comparisons=[dict(comparison_key="AB",
                ordinal=0, a_set_key="A", b_set_key="B")], output_prefix="overlap")
        workspace = directory / "workspace"
        workspace.mkdir()
        software = f.NATIVE.software()
        job = dict(version="native_genomic_overlap_job_v1", program="bedtools_intersect_all_pairs",
            request=request, software=software, inputs=inputs, outputs=genomic_overlap_output_files(request),
            environment={"LC_ALL": "C"})
        launch = f.launch_assignment(job, workspace)
        factory = ExecutionServiceFactory({"here": dict(kind="local", workspace=str(workspace),
            policy=deepcopy(f.POLICY), native_genomic_overlap=[dict(operation=request["operation"],
                mode=request["mode"], software=deepcopy(software))])}, {}, 3, 2, 1, log_window_bytes=128)
        preliminary = ToolRegistry(store, job_limits=deepcopy(f.POLICY))
        application = factory(store, run_id=f.RUN_ID, directory=directory / "run", tool_registry=preliminary)
        binding = prepare_scientific_binding(run_directory=directory / "run",
            source_directory=Path(__file__).parents[1] / "research/slotted_process_library/publications/2026-10-24-001",
            tool_catalog=preliminary.catalog(), child_roles=("scientific_process", "launch", "results"),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / "run/scientific-process-library")
        science = dict(selection=dict(version="scientific_process_selection_v3",
            evidence_axis=library.reference("A101"), thought_pattern=library.reference("P01"),
            child_tool_info=[dict(name="analyze_genomic_region_overlap", resources="local")]),
            evidence_refs=scope["subject_refs"], constraints=dict(no_external_acquisition=True,
                allocation=deepcopy(f.POLICY)), context=dict(supplied_sequence="ACGTACGT", molecule="dna",
                    supplied_genomic_overlap_request=deepcopy(request), candidate_annotation_required=False))
        configuration = dict(factory=factory.as_record(), scientific_binding=binding, goal=question,
            scope=scope, initial_refs=initial, saved=True, failure=None)
        f.write(directory / "fixture-configuration.json", configuration)
        full_form, parent_form = f.result_form("overlap", "saved", "failures", completed=True), f.result_form("overlap")

        def selector(saved=None):
            selected = f.selector(saved=saved, minimum=1 if saved is None else 6)
            selected["comparison_keys"] = ["AB"]
            selected["projection"]["limit"] = 1
            return selected

        class Choices:
            def __init__(self):
                self.turns, self.handoff, self.plan = {}, None, None

            async def complete(self, episode_id, role, instructions, current, schema):
                assert not current.get("feedback"), current.get("feedback")
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                wire, rendered_instructions = session._presentation(episode_id, role, instructions, current)
                calls.append(dict(episode_id=episode_id, context=deepcopy(current), wire=wire))
                f.write(directory / ("decision-" + str(len(calls) - 1) + ".json"), calls[-1])
                if "practical_assignment" in current:
                    assert turn == 1
                    answer = f.action("practical.job.start")
                elif current.get("execution_assignment", {}).get("version") == "execution_launch_assignment_v1":
                    answer = f.commission("launch_local", current["execution_assignment"]["requests"]["here"],
                        scope, f.HANDOFF_FORM, objective="Execute the selected supplied-File interval comparison.")
                elif current.get("execution_assignment", {}).get("version") == RESULTS_VERSION:
                    assert turn == 1, "unexpected incomplete result; preserve the original failure without repeating collection"
                    selected = current["execution_assignment"]["selector"]
                    task = current["selected_execution_task"]
                    assert task["scientific_question"] == question and task["selector"] == selected
                    assert wire.startswith("TASK") and "STEERING" in wire and question in wire
                    assert instructions in wire and rendered_instructions == instructions
                    for info in task["selected_tool_info"]:
                        assert info["name"] in wire and info["description"] in wire and info["instructions"] in wire
                    if selected["mode"] == "saved_sheet_recalculation":
                        assert selected == selector(saved=selected["saved_sheet_file"])
                        assert selected["parameters"]["minimum_overlap_bp"] == 6
                        assert "saved_sheet_recalculation" in wire and "minimum_overlap_bp" in wire
                        proof["saved_full_builder_verified"] = True
                    answer = f.action("execution.results.collect")
                elif "scientific_process" not in current:
                    answer = f.commission("scientific_process", science, scope, parent_form, objective=question)
                elif turn == 1:
                    answer = f.commission("launch", launch, scope, f.HANDOFF_FORM, objective="Execute the frozen File-only request.")
                elif turn == 2:
                    reader = PracticalReceiptInformation(store, f.RUN_ID)
                    self.handoff, = [ref for ref in current["child_reports"][-1]["references"]
                        if reader.read(ref, scope)["receipt"]["tool_name"] == "practical.job.start"]
                    target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                    outcome = await asyncio.to_thread(f.native_lifecycle.wait_job,
                        f.native_lifecycle.NativeJobHandle(Path(target["execution_id"])))
                    assert outcome.returncode == 0
                    self.plan = local_genomic_overlap_plan(target["assignment"], target["execution_id"])
                    answer = f.commission("results", dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                        selector=selector()), scope, full_form, objective="Return the requested overlap measurements and saved sheet.")
                else:
                    assert turn == 3
                    original = current["child_reports"][-1]
                    assert original["completed"] and not original["failures"]
                    saved, = original["saved"]
                    saved_input_bytes[saved["artifact_ref"]] = store.get_artifact(saved["artifact_ref"])
                    answer = f.commission("results", dict(version=RESULTS_VERSION, handoff_ref=self.handoff,
                        selector=selector(saved=saved)), scope, full_form,
                        objective="Recalculate the received sheet with minimum_overlap_bp=6.")
                answer = f.provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        choices = Choices()
        flow, _ = f.assemble(store, directory, choices, configuration)
        owner = flow.episode_bindings.for_role("results")
        try:
            root, record, archive = asyncio.run(f.run_root(flow, configuration))
            contexts = [owner.native_genomic_overlap_returns.context(row["episode_id"]) for row in f.walk(archive)]
            result_contexts = [ctx for ctx in contexts if ctx.role == "results"]
            forms = [json.loads(flow.journal.row("runtime_forms", ctx.episode_id)["form"]) for ctx in result_contexts]
            assert len(forms) == 2 and all(form["completed"] and not form["failures"] for form in forms)
            projections = [form["overlap"][0] for form in forms]
            metrics = [projection["pair_rows"][0]["measurements"] for projection in projections]
            for projection, values in zip(projections, metrics):
                assert projection["pair_rows"][0]["reference_relation"] == "unknown"
                assert values["unfiltered.native_pair_count"] == 1
                assert values["unfiltered.intersection_union_bp"] == 5
                assert values["unfiltered.combined_union_bp"] == 15
                assert values["unfiltered.jaccard_bp"] == dict(numerator=5, denominator=15,
                    value=1/3, missing_reason=None)
            assert [values["selected.selected_pair_count"] for values in metrics] == [1, 0]
            assert [values["selected.selected_pairwise_bp_sum"] for values in metrics] == [5, 0]
            assert forms[0]["saved"] == forms[1]["saved"]
            for ref, raw in saved_input_bytes.items():
                assert store.get_artifact(ref) == raw
                sheet = json.loads(raw)
                assert sheet["request"] == request
                assert all("source_ref" not in spec["source"] for spec in sheet["request"]["region_sets"])
            runs = f.worker_runs(directory)
            assert sorted(run["plan"]["mode"] for run in runs) == ["native_result", "saved_sheet_recalculation"]
            assert len(list(workspace.rglob("native.json"))) == 1
            parent = owner.native_genomic_overlap_returns.context(record.episode_id)
            assert owner.native_genomic_overlap_returns.received_facts(parent, parent_form) == {PROJECTION_SOURCE: projections}
            saved = forms[0]["saved"][0]
            assert not owner.native_genomic_overlap_returns.resolve_received(parent, saved["artifact_ref"], "artifact")
            assert proof["saved_full_builder_verified"]
            proof.update(passed=True, native_plan=choices.plan, input_file_refs=initial, requested_question=question,
                forms=forms, original_saved_sheet_sha256=hashlib.sha256(next(iter(saved_input_bytes.values()))).hexdigest(),
                typed_parent_values=projections, calls=calls, calculation_workers=2,
                retained_input_source_refs=[spec["source"].get("source_ref") for spec in request["region_sets"]])
        except BaseException as error:
            proof["failure"] = dict(type=type(error).__name__, message=str(error))
            proof["calls"] = calls
            raise
        finally:
            (directory / "FILE_ONLY_WORKFLOW.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
