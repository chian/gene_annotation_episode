from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.rna_structure_comparison_operands import (
    RNAComparisonInputError, authenticate_received_rna_operand, authenticate_received_rna_failure,
    resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs,
)
from gene_annotation_episode.state import Store

SPEC = importlib.util.spec_from_file_location("rna_comparison_e_fixture", Path(__file__).parent / "fixtures/rna_comparison_results_371/helpers.py")
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


def resolve(f, context, selector):
    return resolve_rna_comparison_operands(f.store, context, selector,
        anchor_handoff_ref=f.originals[1].handoff, returns=f.native_returns)


def test_independently_received_originals_keep_nonbaseline_routing_anchor(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        selector = f.selector()
        refs = validate_rna_comparison_selected_inputs(store, f.root, selector,
            anchor_handoff_ref=f.originals[1].handoff, returns=f.native_returns)
        child = f.child(selector)
        operands = resolve(f, child, selector)
        assert operands["selected_references"] == refs
        assert list(operands["data"]) == ["WT", "V"]
        assert operands["original_receipts"] == dict(zip(("WT", "V"), f.bodies))
        assert operands["data"]["WT"]["original_sheet"]["original_input"]["sequence"] == "GGGAAACCC"
        assert operands["data"]["V"]["original_sheet"]["original_input"]["sequence"] == "GGGAAAUCC"
        assert f.descriptors[0]["handoff_ref"] != child.assignment["handoff_ref"] == f.descriptors[1]["handoff_ref"]
        assert f.native_returns.resolve_saved_rna_input(f.root, f.descriptors[0]) == f.bodies[0]
        with pytest.raises(ValueError, match="saved_assignment_conflict"):
            f.native_returns.resolve_saved_rna_input(child, f.descriptors[0])
        E.retain("independent_operands", selector=selector, operands=operands, assignment=E.plain(child.assignment))


def test_source_and_possessed_exact_refs_do_not_prove_received_descriptor(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", source_only=True)
        descriptor = f.descriptors[0]
        f.receipts.receive(f.root.episode_id, [descriptor[k] for k in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref")], kind="initial")
        with pytest.raises(ValueError, match="saved_input_not_received"):
            authenticate_received_rna_operand(f.root, descriptor, returns=f.native_returns)
        child = f.child()
        with pytest.raises(ValueError, match="saved_input_not_received"):
            f.results.retained_reference_access(child, descriptor["handoff_ref"], "execution_handoff")


@pytest.mark.parametrize("field", ["handoff_ref", "source_ref", "sheet_sha256", "record_key"])
def test_forged_saved_identity_is_rejected(tmp_path, field):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        descriptor = deepcopy(f.descriptors[0])
        descriptor[field] = f.descriptors[1][field] if field != "sheet_sha256" else "0" * 64
        with pytest.raises(ValueError):
            authenticate_received_rna_operand(f.root, descriptor, returns=f.native_returns)


@pytest.mark.parametrize("failure", [True, "null_source"])
def test_received_failure_absence_and_alias_have_distinct_operands(tmp_path, failure):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", failure=failure)
        selector = f.selector(scan=True)
        child = f.child(selector)
        operands = resolve(f, child, selector)
        assert operands["data"]["failed"] == {"original_sheet": None, "original_bundle_software": None, "received_failure": f.failure_row}
        assert operands["data"]["not-run"] == {"original_sheet": None, "original_bundle_software": None, "received_failure": None}
        assert "alias-V" not in operands["data"] and "not-run" not in operands["original_receipts"]
        assert authenticate_received_rna_failure(child, f.failure_row, returns=f.native_returns) == f.failure_body
        unselected_handoff = f.originals[-1].handoff
        assert unselected_handoff in set(f.receipts.known(child.episode_id, baseline=True))
        assert f.results.retained_reference_access(child, unselected_handoff, "execution_handoff") is False
        if f.failure_row["source_ref"] is not None:
            assert f.results.retained_reference_access(child, f.failure_row["source_ref"], "execution_handoff") is False
        forged = deepcopy(f.failure_row)
        forged["issue_ordinal"] += 1
        with pytest.raises(ValueError):
            authenticate_received_rna_failure(child, forged, returns=f.native_returns)


@pytest.mark.parametrize("kind", ["saved_sheet", "received_failure", "null_source"])
def test_later_actual_form_cannot_enter_earlier_frozen_prefix_even_with_known_refs(tmp_path, kind):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture", failure="null_source" if kind == "null_source" else kind == "received_failure")
        index = 1 if kind == "saved_sheet" else 2
        original = dict(store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (f.run_id, f.root.episode_id, index)).fetchone())
        store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
            (f.run_id, f.root.episode_id, index))
        selector = f.selector() if kind == "saved_sheet" else f.selector(scan=True)
        child = f.child(selector)
        f.journal.save("runtime_report_attempts", original)
        # Its exact Store handles were already known. Only original form receipt
        # order prevents this late arrival from crossing the child boundary.
        with pytest.raises(ValueError, match="saved_operand_not_received"):
            resolve(f, child, selector)


def test_legacy_ancestor_has_no_retrospective_comparison_return_authority(tmp_path):
    from dataclasses import replace
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        request = E.plain(child.request)
        request["message"]["knowledge_inheritance"].pop("received_report_prefix")
        store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=NULL WHERE run_id=? AND episode_id=?",
            (f.run_id, child.episode_id))
        store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), f.run_id, child.episode_id))
        child = replace(child, request=request)
        with pytest.raises(ValueError, match="operand_prefix_proof_unavailable"):
            resolve(f, child, E.plain(child.assignment)["selector"])


@pytest.mark.parametrize("problem,code", [("missing", "retained_sheet_missing"), ("changed", "retained_sheet_digest_mismatch")])
def test_genuine_lost_selected_bytes_are_custody_errors_with_original_cause(tmp_path, problem, code):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        descriptor = f.descriptors[0]
        path = store.path / "artifacts" / descriptor["sheet_sha256"][:2] / descriptor["sheet_sha256"]
        path.unlink() if problem == "missing" else path.write_bytes(b"changed retained bytes")
        with pytest.raises(RNAComparisonInputError) as caught:
            resolve(f, child, E.plain(child.assignment)["selector"])
        assert caught.value.issue == {"stage": "input", "code": code, "member_id": "WT", "comparison_id": None,
            "selection_id": None, "field": None, "index": None}
        assert caught.value.__cause__ is not None
        assert authenticate_received_rna_operand(child, descriptor, returns=f.native_returns) == f.bodies[0]


def test_changed_frozen_manifest_and_original_selected_action_rejected(tmp_path):
    with Store(tmp_path / "store") as store:
        f = E.Fixture(store, tmp_path / "fixture")
        child = f.child()
        store.db.execute("UPDATE runtime_receipt_inheritance SET through_receipt_index=0 WHERE run_id=? AND episode_id=?",
            (f.run_id, child.episode_id))
        with pytest.raises(ValueError, match="saved_prefix_conflict"):
            resolve(f, child, E.plain(child.assignment)["selector"])
        original = f.bodies[0]
        row = f.journal.row("runtime_actions", original["episode_id"], 0)
        action = json.loads(row["action"])
        action["tool"] = "execution.results.status"
        store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(action), f.run_id, original["episode_id"]))
        with pytest.raises(ValueError):
            authenticate_received_rna_operand(f.root, f.descriptors[0], returns=f.native_returns)
