"""Actual shared Workflow communication over synthetic protein structure bytes.

Run only through the packet410 bounded runner. Scripted choices and scientific
test horizons are inputs; native measurements, receipts and operational
continuation are produced by the unchanged runtime.
"""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_operands import authenticate_structure_sequence_reference

F = import_module("verification.tool_graders_protein_structure_workflow_2026-10-27_410.fixture_helpers")


def values(projection):
    row, = projection["delivery"]["rows"]
    return {cell["field"]: cell["value"]["value"] for cell in row["values"]}


def deny(*args, **kwargs):
    raise AssertionError("saved recalculation attempted original acquisition, native analysis or network")


@pytest.fixture(scope="module")
def connected_case(tmp_path_factory):
    directory = tmp_path_factory.mktemp("protein-workflow410")
    saved = {}
    patch = pytest.MonkeyPatch()
    alignment_events = []
    actual_authenticate = WorkflowServices.authenticate_structure_alignment_operands
    actual_align = ToolRegistry._prepare_alignment_async

    def authenticated(self, context, arguments):
        descriptors = actual_authenticate(self, context, arguments)
        assert descriptors["query"] is not None and descriptors["reference"] is not None
        alignment_events.append({"event": "both_operands_authenticated", "episode_id": context.episode_id,
            "arguments": deepcopy(arguments), "descriptors": deepcopy(descriptors)})
        return descriptors

    async def aligned(self, arguments, scope, directory):
        assert alignment_events[-1]["event"] == "both_operands_authenticated"
        assert alignment_events[-1]["arguments"] == arguments
        alignment_events.append({"event": "native_alignment_preparation", "arguments": deepcopy(arguments)})
        return await actual_align(self, arguments, scope, directory)

    patch.setattr(WorkflowServices, "authenticate_structure_alignment_operands", authenticated)
    patch.setattr(ToolRegistry, "_prepare_alignment_async", aligned)

    def before_saved(case):
        descriptor = case.descriptor
        saved["descriptor"] = deepcopy(descriptor)
        saved["sheet"] = case.store.get_artifact(descriptor["sheet_file"]["artifact_ref"])
        saved["baseline"] = case.store.get_artifact(descriptor["original_components_file"]["artifact_ref"])
        saved["authority"] = case.owner.native_protein_structure_results.read_result_authority(
            descriptor["custody"], scope=case.store.validate_scope())
        saved["observations"] = [dict(row) for row in case.store.db.execute(
            "SELECT * FROM runtime_observations ORDER BY episode_id,unit_index")]
        saved["native_plans"] = {str(path): path.read_bytes() for path in case.workspace.rglob("protein-structure-plan.json")}
        saved["dispatches"] = []
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def selected_worker(command, **kwargs):
            assert command[1:4] == ["-B", "-m", "gene_annotation_episode.protein_structure_result_worker"]
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan["mode"] == "saved_sheet_recalculation"
            assert kwargs["policy"].to_dict() == F.POLICY
            saved["dispatches"].append({"command": list(command), "plan": deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, "prepare_job", selected_worker)
        patch.setattr("gene_annotation_episode.native_protein_structure_results.capture_local_protein_structure_bundle", deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), "observe_target", deny)
        patch.setattr("socket.create_connection", deny)

    try:
        case = F.workflow_case(directory, before_saved=before_saved)
        case.saved_evidence = saved
        case.alignment_events = alignment_events
        (directory / "SAVED_CHECK.json").write_text(json.dumps({
            "dispatches": saved["dispatches"], "original_descriptor": saved["descriptor"],
            "alignment_events": alignment_events,
            "native_plan_paths": list(saved["native_plans"]),
            "scope": "Original acquisition and network entry points denied in parent; exact existing saved worker command delegated unchanged."
        }, indent=2) + "\n")
        yield case
        case.store.close()
    finally:
        patch.undo()


def test_full_workflow_retains_native_alignment_and_exact_requested_comparison(connected_case):
    case = connected_case
    assert [len(case.by_role[role]) for role in ("annotation", "scientific_process", "launch", "launch_local", "results")] == [1, 3, 3, 3, 4]
    fixed, moving = case.provider.descriptors
    assert fixed == case.returned[0]["sequences"][0]
    assert moving == case.returned[1]["sequences"][0]
    maps = [json.loads(case.store.get_artifact(descriptor["residue_map_file"]["artifact_ref"]))
            for descriptor in (fixed, moving)]
    assert [[row["position_key"]["residue_number"] for row in value["residues"]] for value in maps] == [[10, 10, 11, 15], [101, 102, 103, 104]]
    assert maps[0]["residues"][1]["position_key"]["insertion_code"] == "A"
    for descriptor in (fixed, moving):
        assert case.store.get_artifact(descriptor["sequence_file"]["artifact_ref"]) == b"AGST"
        assert descriptor["sequence_length"] == 4
        assert descriptor["allowed_uses"] == ["sequence_align", "structure_correspondence"]
        context = case.science_contexts[-1]
        assert authenticate_structure_sequence_reference(case.store, context, descriptor["reference_ref"],
            returns=case.owner.native_protein_structure_returns) == descriptor
    native = json.loads(case.store.get_artifact(case.provider.alignment["native_file"]["artifact_ref"]))
    grading = json.loads(case.store.get_artifact(case.provider.alignment["grading_file"]["artifact_ref"]))
    assert grading["native_artifact_ref"] == case.provider.alignment["native_file"]["artifact_ref"]
    assert [row["event"] for row in case.alignment_events] == ["both_operands_authenticated", "native_alignment_preparation"]
    assert case.alignment_events[0]["descriptors"] == {"query": fixed, "reference": moving}
    assert grading["grading"]["scores"]["paired_positions"] == 4 and native["native_score"] == 19
    assert native["native_format"] == "biopython_pairwise_native_v2" and "paired_positions" not in native
    descriptor, = case.returned[2]["saved"]
    sheet = json.loads(case.store.get_artifact(descriptor["sheet_file"]["artifact_ref"]))
    baseline = json.loads(case.store.get_artifact(descriptor["original_components_file"]["artifact_ref"]))
    assert sheet["native_baseline"] == baseline
    assert sheet["correspondence"]["alignment_native"]["descriptor"] == case.provider.alignment
    assert [(row["fixed_position_key"]["residue_number"], row["moving_position_key"]["residue_number"])
            for row in sheet["correspondence"]["rows"]] == [(10, 101), (10, 102), (11, 103), (15, 104)]
    assert baseline["fit"]["used_correspondence_ids"] == ["column_0", "column_1", "column_2"]
    assert baseline["evaluation"]["used_correspondence_ids"] == ["column_3"]
    first, second = [row["summary"][0] for row in case.returned[2:]]
    assert list(values(first)) == F.SUMMARY_FIELDS
    assert values(first)["alignment_score"] == native["native_score"]
    assert values(first)["mapped_pair_count"] == 4
    assert values(first)["fit_used_count"] == 3
    assert values(first)["evaluation_used_count"] == 1
    assert values(first)["evaluation_sse"] == pytest.approx(4, abs=1e-10)
    assert values(first)["evaluation_rmsd"] == pytest.approx(2, abs=1e-10)
    rmsd = next(row for row in first["delivery"]["rows"][0]["values"] if row["field"] == "evaluation_rmsd")
    assert rmsd["population"]["denominator"] == 1
    assert rmsd["value"]["unit"] == "angstrom"
    assert case.forwarded == [{"credit": 0}, {"summary": [first, second]}, {"summary": [first, second]}]
    assert case.flow.journal.row("runtime_forms", case.root_context.episode_id) is None
    received = case.owner.native_protein_structure_returns.received_context(case.root_context)
    assert next(group["facts"] for group in received if group["fact_source"] == F.SOURCES["summary"]) == [first, second]
    for index, outcome in enumerate(case.outcomes):
        receipt = outcome["result"]
        body, publication = receipt["body"], receipt["publication"]
        context = case.result_contexts[index]
        assert body["intent"]["operation_key"] == f"{F.RUN_ID}:{context.episode_id}:0"
        assert body["intent"]["original_request_sha256"] == digest(plain(context.request))
        assert body["native_success"] and body["capture_complete"] and publication["delivery_complete"]
        assert body["worker"]["execution"]["returncode"] == 0
        if index < 3:
            assert body["bundle"]["requested_job"] == case.provider.plans[index]["requested_job"]
            native_file = body["qualified_files"]["native_file"]
            retained = json.loads(case.store.get_artifact(native_file["artifact_ref"]))
            assert retained["request"] == case.provider.plans[index]["requested_job"]["native_protein_structure"]["request"]
            assert body["worker"]["plan"]["mode"] == "original_native_result"
        for name in ("sheet_file", "original_components_file"):
            identity = body["qualified_files"][name]
            if identity is not None:
                assert case.store.get_artifact(identity["artifact_ref"])
        assert case.owner.native_protein_structure_results.own_fact_groups(context, verify_artifacts=True) == publication["facts"]
        assert case.owner.native_protein_structure_results.read_result_authority(publication["custody"], scope=case.scope)["custody"] == publication["custody"]
        assert case.owner.native_protein_structure_results.owns_reference(publication["source_record"]["id"])


def test_saved_received_sheet_recalculates_only_the_explicit_new_population(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    descriptor = saved["descriptor"]
    assert case.returned[3]["saved"] == [descriptor]
    assert case.store.get_artifact(descriptor["sheet_file"]["artifact_ref"]) == saved["sheet"]
    assert case.store.get_artifact(descriptor["original_components_file"]["artifact_ref"]) == saved["baseline"]
    assert case.owner.native_protein_structure_results.read_result_authority(descriptor["custody"], scope=case.scope) == saved["authority"]
    assert {str(path): path.read_bytes() for path in case.workspace.rglob("protein-structure-plan.json")} == saved["native_plans"]
    # Each producer retains its original plan and an identical attempt copy.
    assert len(saved["native_plans"]) == 6 and len(case.provider.plans) == 3
    dispatch, = saved["dispatches"]
    assert set(dispatch["plan"]) == {"version", "mode", "directory", "parameters", "sheet", "original_components"}
    assert dispatch["plan"]["parameters"]["evaluation_selection"] == {"kind": "all_mapped_pairs"}
    assert dispatch["plan"]["parameters"]["distance_threshold_A"] == 1.5
    first, second = [row["summary"][0] for row in case.returned[2:]]
    assert values(second) == pytest.approx({**values(first), "evaluation_used_count": 4, "evaluation_rmsd": 1}, abs=1e-10)
    assert first["calculation"] != second["calculation"]
    original = case.outcomes[2]["result"]["body"]
    recalculated = case.outcomes[3]["result"]["body"]
    assert recalculated["observation_origin"] == "original_saved_observation"
    assert recalculated["qualified_files"]["sheet_file"] == original["qualified_files"]["sheet_file"]
    assert recalculated["qualified_files"]["original_components_file"] == original["qualified_files"]["original_components_file"]
    rows = {(row["episode_id"], row["unit_index"]): dict(row) for row in case.store.db.execute("SELECT * FROM runtime_observations")}
    assert all(rows[(old["episode_id"], old["unit_index"])] == old for old in saved["observations"])
    assert case.store.db.execute("SELECT count(*) FROM tool_operations WHERE name='sequence.align'").fetchone()[0] == 1


def test_practical_completion_retains_final_credit_and_one_durable_observation(connected_case):
    case = connected_case
    for row in case.records:
        context = case.contexts[row["episode_id"]]
        actions = list(case.store.db.execute("SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (context.episode_id,)))
        observations = list(case.store.db.execute("SELECT * FROM runtime_observations WHERE episode_id=? ORDER BY unit_index", (context.episode_id,)))
        assert len(actions) == len(observations) == row["units_consumed"]
        assert case.provider.turns[context.episode_id] == len(actions)
        if context.role in {"launch", "launch_local", "results"}:
            assert len(actions) == 1
            assert row["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
            proof = case.owner.completion_for_action(context, f"{F.RUN_ID}:{context.episode_id}:0")
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role["launch_local"]] == [[7], [7], [7]]
    assert [F.history(row) for row in case.by_role["launch"]] == [[3], [3], [3]]
    assert [F.history(row) for row in case.by_role["results"]] == [[2], [2], [2], [0]]
    assert F.history(case.by_role["annotation"][0]) == [0, 0]
    assert case.store.count("annotation") == 0


def test_later_actual_receipts_do_not_authorize_an_earlier_sibling(connected_case):
    case = connected_case
    early, coordinator, aligner = case.science_contexts
    for descriptor in case.provider.descriptors:
        assert case.owner.native_protein_structure_returns.authenticate_received_sequence(
            aligner, descriptor, required_use="sequence_align")["custody"] == descriptor["custody"]
        with pytest.raises(ProteinStructureOperandError, match="sequence_not_received"):
            case.owner.native_protein_structure_returns.authenticate_received_sequence(early, descriptor, required_use="sequence_align")
        resolver = case.flow.resolver(early.scope, grain=early.role, context=early)
        assert not resolver(descriptor["reference_ref"], "reference")
    descriptor, = case.returned[2]["saved"]
    assert case.owner.native_protein_structure_returns.authenticate_received_saved_sheet(
        aligner, descriptor, required_use="recalculate")["custody"] == descriptor["custody"]
    for context in (early, coordinator, case.root_context):
        with pytest.raises(ProteinStructureOperandError, match="saved_sheet_not_received"):
            case.owner.native_protein_structure_returns.authenticate_received_saved_sheet(context, descriptor, required_use="recalculate")
    assert F.history(case.by_role["scientific_process"][0]) == [0]
