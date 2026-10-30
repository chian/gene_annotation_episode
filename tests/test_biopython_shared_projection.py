"""R1 shared projection: synthetic conflicts and real tiny native compatibility.

The worker seam is explicitly supplied in the conflicting-result cases. Real
native publication and child-return modes remain covered by the existing tests.
"""
import ast
import asyncio
from copy import deepcopy
from importlib import import_module
import inspect
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode import biopython_pairwise_grader as grader
from gene_annotation_episode import sequence_ops
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import SequenceWork, ToolRegistry
from test_biopython_pairwise_grader import synthetic_gapped_result
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, select
from test_tool_grading_child_returns import RETURN_FORM, fixed_completion_estimate, zero_fixture_credit
from test_tool_grading_publication import numerical, only_grading


ALIASES = {"paired_positions": "paired_positions", "identical_positions": "identical_positions",
    "identity_fraction": "paired_identity", "query_coverage": "query_aligned_coverage",
    "reference_coverage": "reference_aligned_coverage"}


def native_v2():
    native = synthetic_gapped_result()
    for field in ALIASES:
        del native[field]
    native["native_format"] = "biopython_pairwise_native_v2"
    return native


def supplied_worker(monkeypatch, native, registry=ToolRegistry):
    calls = []
    async def run(self, operation, arguments, *, directory):
        calls.append((operation, deepcopy(arguments)))
        path = directory / "supplied-native.json"
        path.write_text(canonical(native))
        return SequenceWork(path, {"fixture": "synthetic_shared_projection_conflict"})
    monkeypatch.setattr(registry, "_sequence_worker_async", run)
    return calls


def operands(store, tmp_path, operation):
    if operation == "sequence.align":
        path = tmp_path / "pair.faa"
        path.write_text(">query\nNACDEFGNNN\n>reference\nNNNACTVEGNNN\n")
        query, reference = store.create_problem(path, molecule="protein")["subject_refs"]
        return {"query_ref": query, "reference_ref": reference, "molecule": "protein", "mode": "local"}, [query, reference], query
    path = tmp_path / "reads.fastq"
    path.write_text("@query\nNACGTACNNN\n+\nIIIIIIIIII\n@reference\nNNNACTGTCNNN\n+\nIIIIIIIIIIII\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "entries": [{"path": path.name,
        "molecule": "dna", "quality_encoding": "phred33"}]}))
    target, = store.create_problem(manifest_path=manifest)["subject_refs"]
    result = ToolRegistry(store).execute("library.members", {"library_ref": target}, operation_key="members")
    query, reference = [row["id"] for row in result["result"]["members"]]
    return {"subject_refs": [query], "reference_ref": reference, "molecule": "dna", "mode": "local"}, [target, query, reference], target


def assert_projection(store, result, operation):
    preview = result["result"] if operation == "sequence.align" else result["result"]["records"][0]
    grading = only_grading(store, preview["source_ref"])
    observation = store.get(preview["observation_ref"])
    scores, values = grading["scores"], numerical(observation)
    for alias, component in ALIASES.items():
        assert preview[alias] == scores[component]
        observation_name = "target_coverage" if alias == "reference_coverage" else alias
        if scores[component] is None:
            assert observation_name not in values
        else:
            assert values[observation_name] == scores[component]
    return preview, grading, observation


@pytest.mark.parametrize("operation", ["sequence.align", "reads.align"])
def test_conflicting_legacy_aliases_follow_sheet_through_requested_child_return_and_replay(tmp_path, monkeypatch, operation):
    native = synthetic_gapped_result()
    native.update(paired_positions=20, identical_positions=21, identity_fraction=.2,
        query_coverage=.1, reference_coverage=.2)
    if operation == "reads.align":
        native.update(aligned_query="ACG-TAC", aligned_reference="ACTGT-C", matrix="match_2_mismatch_minus_1")
    calls = supplied_worker(monkeypatch, native)
    actual_grade, grades = grader.grade_biopython_pairwise, []
    def counted(*args, **kwargs):
        result = actual_grade(*args, **kwargs)
        grades.append(deepcopy(result))
        return result
    monkeypatch.setattr(grader, "grade_biopython_pairwise", counted)
    with Store(tmp_path / "state") as store:
        args, supplied, target = operands(store, tmp_path, operation)
        scope = store.validate_scope({"subject_refs": supplied if operation == "sequence.align" else [target]})
        tools = ToolRegistry(store)
        directory = tmp_path / "run"
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process",))
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Measure the supplied sequence material with the assigned native operation.",
            "scope": scope, "purpose": "Return the recorded native numerical evidence, with function unresolved.",
            "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
            "assignment": {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": operation, "resources": "local"}]},
                "evidence_refs": supplied, "constraints": {"no_external_acquisition": True},
                "context": {"molecule": args["molecule"]}}}
        decisions = ScriptedDecisions([select(commission), select({"kind": "tool", "tool": operation, "arguments": args})])
        workflow = Workflow(store, tools, decisions, directory, "shared-biopython-" + operation,
            fixed_completion_estimate, zero_fixture_credit, episode_binding_descriptors=[descriptor],
            episode_record_receipts=True, initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
        root = workflow.build("annotation", "root", "Investigate the supplied unnamed sequence", scope)
        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record
        record = asyncio.run(run())
        assert record.units_consumed == 1
        child_id = decisions.calls[1]["episode_id"]
        returned = json.loads(workflow.journal.row("runtime_forms", child_id)["form"])
        row = store.db.execute("SELECT * FROM tool_operations WHERE name=?", (operation,)).fetchone()
        result = json.loads(row["result"])
        assert result["status"] == "completed"
        assert returned == {"records": result["record_refs"]}
        preview, grading, observation = assert_projection(store, result, operation)
        assert len(calls) == len(grades) == 1
        assert grading == {key: value for key, value in grades[0].items() if key != "correspondence"}
        source = store.get(preview["source_ref"])
        retained = [json.loads(store.get_artifact(ref)) for ref in source["auxiliary_artifact_refs"]
            if store.get(ref).get("media_type") == "application/vnd.gene-annotation.tool-grading+json"]
        assert len(retained) == 1 and retained[0]["schema"] == "tool_grading_artifact_v2"
        assert retained[0]["correspondence"] == grades[0]["correspondence"]
        assert set(retained[0]["grading"]) == {"sheet", "scores"}
        assert grading["sheet"]["native_result"] == native
        assert grading["sheet"]["reported_measurements"]["identical_positions"] == 21
        assert {issue["code"] for issue in grading["sheet"]["issues"]} >= {
            "reported_count_traceback_conflict", "reported_fraction_traceback_conflict"}
        assert preview["paired_positions"] == 5 and preview["identical_positions"] == 4
        assert preview["identity_fraction"] == .8 and preview["query_coverage"] == .6 and preview["reference_coverage"] == .5
        assert grading["scores"]["alignment_identity"] == 4 / 7
        assert grading["scores"]["query_paired_coverage"] == .5 and grading["scores"]["reference_paired_coverage"] == 5 / 12
        assert observation["id"] in workflow.receipts.known(root.source.episode_id)
        received, = workflow.working_state(root.source)["observations"]
        assert numerical(received) == numerical(observation)
        before = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
        raw = store.get_artifact(store.get(preview["source_ref"])["artifact_ref"])
        assert raw == canonical(native).encode()
        assert tools.execute(operation, args, scope=scope, operation_key=row["operation_key"]) == result
        root_action = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?", (root.source.episode_id,)).fetchone()[0]
        workflow.receive_form(root.source, returned, RETURN_FORM, root_action, redelivery=True)
        assert before == [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
        assert len(calls) == len(grades) == 1
        saved = json.loads(json.dumps(grading))
        monkeypatch.setattr(sequence_ops, "align_pair", lambda *a, **k: pytest.fail("saved calculator reran alignment"))
        assert grader.calculate_biopython_pairwise_scores(saved["sheet"]) == saved["scores"]
        if os.environ.get("BIOPYTHON504_ATTEMPT"):
            report = {"operation": operation, "synthetic_native": native, "grading": saved,
                "preview": preview, "published_values": numerical(observation), "returned": returned,
                "closed_observations_unchanged": True, "grade_calls": len(grades), "worker_calls": len(calls)}
            (Path(os.environ["BIOPYTHON504_ATTEMPT"]) / (operation + ".numerical_report.json")).write_text(json.dumps(report, indent=2) + "\n")


@pytest.mark.parametrize("changes", [
    {"coordinates": None}, {"coordinates": [[1, 7], [3, 9]]}, {"query_interval": None},
    {"aligned_query": None, "aligned_reference": None}, {"query_length": None},
])
def test_unavailable_calculated_cells_never_fall_back_to_reported_aliases(tmp_path, monkeypatch, changes):
    native = synthetic_gapped_result()
    native.update(changes)
    supplied_worker(monkeypatch, native)
    with Store(tmp_path / "state") as store:
        args, _, _ = operands(store, tmp_path, "sequence.align")
        result = ToolRegistry(store).execute("sequence.align", args, operation_key="partial-geometry")
        assert result["status"] == "completed", result
        _, grading, observation = assert_projection(store, result, "sequence.align")
        assert grading["sheet"]["native_result"] == native
        assert grading["scores"]["query_aligned_coverage"] is None
        if "query_length" not in changes:
            assert observation.get("operand_intervals") is None
            assert "query_start" not in numerical(observation)


@pytest.mark.parametrize("new_format", [False, True])
@pytest.mark.parametrize("rejected", [False, True])
def test_failed_or_absent_grading_does_not_restore_native_convenience_numbers(tmp_path, monkeypatch, new_format, rejected):
    native = native_v2() if new_format else synthetic_gapped_result()
    supplied_worker(monkeypatch, native)
    def reject(*args, **kwargs):
        if rejected:
            raise ValueError("synthetic_grading_rejected")
        return {"sheet": None, "scores": None}
    monkeypatch.setattr(grader, "grade_biopython_pairwise", reject)
    with Store(tmp_path / "state") as store:
        args, _, _ = operands(store, tmp_path, "sequence.align")
        result = ToolRegistry(store).execute("sequence.align", args, operation_key="no-grading")
        assert result["status"] == ("partial" if rejected else "completed")
        preview = result["result"]
        assert all(preview[key] is None for key in ALIASES)
        values = numerical(store.get(preview["observation_ref"]))
        assert not (set(ALIASES) | {"target_coverage"}) & set(values)
        assert values["alignment_score"] == 17.5 and values["query_length"] == 10
        assert only_grading(store, preview["source_ref"])["scores"] is None


def test_new_format_is_explicit_and_legacy_missing_measurements_stay_missing():
    native = native_v2()
    result = grader.grade_biopython_pairwise(native, molecule="protein")
    assert result["sheet"]["schema"] == "biopython_pairwise_sheet_v1" and result["sheet"]["issues"] == []
    assert set(result["sheet"]["reported_measurements"].values()) == {None}
    legacy = deepcopy(native)
    del legacy["native_format"]
    old = grader.grade_biopython_pairwise(legacy, molecule="protein")
    assert {issue["field"] for issue in old["sheet"]["issues"] if issue["code"] == "measurement_missing"} == set(ALIASES)
    assert old["scores"]["paired_identity"] == result["scores"]["paired_identity"]
    native["native_format"] = "unknown"
    with pytest.raises(ValueError, match="biopython_pairwise_native_format_unknown"):
        grader.grade_biopython_pairwise(native, molecule="protein")


def test_raw_native_producer_has_no_convenience_count_or_ratio_implementation():
    tree = ast.parse(inspect.getsource(sequence_ops.align_pair))
    assert not any(isinstance(node, ast.Constant) and node.value in ALIASES
        for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str))
    assert not any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) for node in ast.walk(tree))


@pytest.mark.parametrize("no_alignment", [False, True])
def test_structure_correspondence_accepts_new_native_and_preserves_legacy_shape(no_alignment):
    f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
    from gene_annotation_episode.protein_structure_contracts import _validate
    from gene_annotation_episode.protein_structure_correspondence import correspondence_from_pairwise_sheet
    fixed = f.fixture_pdb("AAAA" if no_alignment else "AGST")[2]
    moving = f.fixture_pdb("WWWW" if no_alignment else "AGST", role="moving", chain="B")[2]
    sheet, kwargs, result = f.retained_alignment(fixed, moving, mode="local" if no_alignment else "global")
    native = kwargs["native"]
    assert native["native_format"] == "biopython_pairwise_native_v2" and not set(ALIASES) & set(native)
    assert result["population_available"] and len(result["rows"]) == (0 if no_alignment else 4)
    legacy = deepcopy(native)
    del legacy["native_format"]
    if no_alignment:
        for field in ("native_score", "gap_open", "gap_extend", "limitations"):
            del legacy[field]
    else:
        scores = grader.calculate_biopython_pairwise_scores(sheet)
        legacy.update({alias: scores[component] for alias, component in ALIASES.items()})
    assert _validate("BiopythonPairwiseNative", legacy) == legacy
    kwargs["native"] = legacy
    legacy_sheet = grader.build_biopython_pairwise_sheet(legacy, molecule="protein")
    legacy_result = correspondence_from_pairwise_sheet(legacy_sheet, **kwargs)
    assert legacy_result["rows"] == result["rows"]
