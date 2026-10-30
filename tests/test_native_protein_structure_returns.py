"""397: persisted authority-port fixtures, separate from root host integration."""
from copy import deepcopy
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_protein_structure_returns import (
    NativeProteinStructureReturns, requested_sources, FACT_SOURCES, SEQUENCE_SOURCE,
    SAVED_SOURCE, PROJECTION_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_contracts import issue
from gene_annotation_episode.state import Store

F = import_module("verification.tool_graders_protein_structure_returns_2026-10-27_397.fixture_helpers")


@pytest.fixture
def f(tmp_path):
    with Store(tmp_path / "store") as store:
        yield F.Fixture(store)


def original(f, **kwargs):
    child = f.child(**kwargs)
    view = f.publish(child, comparison=kwargs.get("saved", False))
    form = f.returned(f.root, child)
    return child, view, form


def descriptor(view):
    return view["facts"][SEQUENCE_SOURCE][0]


def rejected(code):
    return pytest.raises(ProteinStructureOperandError, match="^" + code + "$")


def no_science(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Authority inspection executed science or acquisition")
    for module, names in (
        ("protein_structure_calculations", ["calculate_protein_structure_components", "fit_ca_transform"]),
        ("protein_structure_formats", ["parse_pdb_structure", "parse_mmcif_structure"]),
        ("protein_structure_sequences", ["extract_structure_sequence"]),
        ("sequence_ops", ["align_pair"]),
        ("native_protein_structure_acquisition", ["capture_local_protein_structure_bundle"]),
    ):
        target = import_module("gene_annotation_episode." + module)
        for name in names:
            if hasattr(target, name):
                monkeypatch.setattr(target, name, forbid)
    monkeypatch.setattr("numpy.linalg.svd", forbid)
    monkeypatch.setattr("socket.create_connection", forbid)


def test_exact_seven_operands_and_requested_sources_read_only_reopen(f, monkeypatch):
    child, view, form = original(f)
    selected = descriptor(view)
    before = list(f.store.db.iterdump())
    no_science(monkeypatch)
    for _ in range(2):
        returns = NativeProteinStructureReturns(f.owner)
        actual = returns.authenticate_received_sequence(f.root, selected, required_use="sequence_align")
        assert actual == view
        assert returns.received_sequence_descriptors(f.root, selected["reference_ref"]) == [selected]
        actual["facts"][SEQUENCE_SOURCE].clear()
        assert returns.received_facts(f.root, F.schema_for(SEQUENCE_SOURCE))[SEQUENCE_SOURCE] == [selected]
    refs = f.returns.record_admission(f.root, form, child.request["report_contract"]["measurements"]["schema"],
        f"{f.run_id}:{f.root.episode_id}:0:typed_form")
    assert refs == [selected["reference_ref"], *(selected[key]["artifact_ref"] for key in
        ("sequence_file", "residue_map_file", "structure_file")), *(selected["custody"][key]
        for key in ("handoff_ref", "source_ref", "bundle_artifact_ref"))]
    assert len(refs) == 7
    for ref in refs:
        assert f.returns.resolve_received(f.root, ref, None) is True
    assert f.returns.resolve_received(f.root, view["native_file"]["artifact_ref"], "artifact") is False
    assert f.returns.resolve_received(f.root, selected["reference_ref"], "artifact") is False
    assert f.returns.resolve_received(f.root, f.scope["subject_refs"][0], "subject") is None
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize("delivery", ["values", "artifact", "unselected"])
def test_descriptor_cell_is_received_only_when_explicitly_delivered_as_values(f, delivery):
    fields = ["descriptor"] if delivery != "unselected" else ["sequence_length"]
    child, view, _ = original(f, sources=(PROJECTION_SOURCE,),
        projections=[F.selection("extracted_sequence", fields, artifact=delivery == "artifact")])
    desc = descriptor(view)
    if delivery == "values":
        assert f.returns.authenticate_received_sequence(f.root, desc, required_use="structure_correspondence") == view
    else:
        with rejected("sequence_not_received"):
            f.returns.authenticate_received_sequence(f.root, desc, required_use="sequence_align")
        assert f.returns.resolve_received(f.root, desc["reference_ref"], "subject") is False
    if delivery == "artifact":
        projection = view["facts"][PROJECTION_SOURCE][0]
        assert f.returns.resolve_received(f.root, projection["delivery"]["table_file"]["artifact_ref"], "artifact") is True
        assert f.returns.resolve_received(f.root, projection["custody"]["bundle_artifact_ref"], "artifact") is False


def test_wrong_sequence_use_never_unions_grants(f):
    _, view, _ = original(f, sequence_uses=("structure_correspondence",))
    desc = descriptor(view)
    with rejected("sequence_not_received"):
        f.returns.authenticate_received_sequence(f.root, desc, required_use="sequence_align")
    assert f.returns.authenticate_received_sequence(f.root, desc, required_use="structure_correspondence") == view
    altered = deepcopy(desc)
    altered["allowed_uses"] = ["sequence_align", "structure_correspondence"]
    with rejected("sequence_not_received"):
        f.returns.authenticate_received_sequence(f.root, altered, required_use="sequence_align")


@pytest.mark.parametrize("case", ["direct_sibling", "later_report", "delayed_earlier_report", "historical_null_prefix"])
def test_frozen_delivery_prefix_prevents_store_visibility_grants(f, case):
    producer = f.child(index=0)
    if case == "later_report":
        f.returned(f.root, producer, facts={source: [] for source in FACT_SOURCES})
    consumer = f.child(index=1, role="scientific_process")
    view = f.publish(producer)
    if case != "direct_sibling":
        # For the later_report case this overwrites the successful form: the
        # earlier frozen digest must reject the new form with the same index.
        f.returned(f.root, producer)
    if case == "historical_null_prefix":
        manifest = plain(consumer.request["message"]["knowledge_inheritance"])
        manifest.pop("received_report_prefix")
        request = plain(consumer.request)
        request["message"]["knowledge_inheritance"] = manifest
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=NULL WHERE run_id=? AND episode_id=?",
            (f.run_id, consumer.episode_id))
        f.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), f.run_id, consumer.episode_id))
        consumer = f.returns.context(consumer.episode_id)
    # Simulate old recursive reference expansion. It must supply no descriptor.
    f.receipts.receive(consumer.episode_id, f.store._refs(descriptor(view)), kind="initial")
    with rejected("original_commission_mismatch" if case == "historical_null_prefix" else "sequence_not_received"):
        f.returns.authenticate_received_sequence(consumer, descriptor(view), required_use="sequence_align")


def test_multiple_ancestor_boundaries_forward_exact_facts(f):
    scientific = f.child(index=0, role="scientific_process")
    producer = f.child(parent=scientific, index=0)
    view = f.publish(producer)
    f.returned(scientific, producer)
    consumer = f.child(parent=scientific, index=1, role="scientific_process")
    grandchild = f.child(parent=consumer, index=0, role="launch_local")
    assert f.returns.authenticate_received_sequence(grandchild, descriptor(view), required_use="sequence_align") == view
    f.returned(f.root, scientific)
    assert f.returns.received_sequence_descriptors(f.root, descriptor(view)["reference_ref"]) == [descriptor(view)]
    later = f.child(index=1, role="scientific_process")
    assert f.returns.authenticate_received_sequence(later, descriptor(view), required_use="structure_correspondence") == view


@pytest.mark.parametrize("case", ["commission_purpose", "commission_scope", "commission_schema", "commission_assignment",
                                    "frozen_form", "frozen_facts", "manifest_parent", "manifest_request", "missing_action"])
def test_original_commission_form_and_manifest_tampering_rejected(f, case):
    child, view, _ = original(f)
    if case.startswith("commission_"):
        row = f.journal.row("runtime_actions", f.root.episode_id, 0)
        action = json.loads(row["action"])
        key = case.removeprefix("commission_")
        if key == "schema":
            action["schema_json"] = canonical(F.schema_for(FAILURE_SOURCE))
        else:
            action[key] = {"altered": True} if key != "purpose" else "Altered purpose"
        f.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(action), f.run_id, f.root.episode_id))
    elif case in {"frozen_form", "frozen_facts"}:
        column = case.removeprefix("frozen_")
        row = f.journal.row("runtime_forms", child.episode_id)
        value = json.loads(row[column])
        value[SEQUENCE_SOURCE if column == "facts" else next(iter(value))] = []
        f.store.db.execute(f"UPDATE runtime_forms SET {column}=? WHERE run_id=? AND episode_id=?",
            (canonical(value), f.run_id, child.episode_id))
    elif case == "manifest_parent":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE run_id=? AND episode_id=?",
            (child.episode_id, f.run_id, child.episode_id))
    elif case == "manifest_request":
        request = plain(child.request)
        request["message"]["knowledge_inheritance"]["through_receipt_index"] = -1
        f.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), f.run_id, child.episode_id))
    else:
        f.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0",
            (f.run_id, child.episode_id))
    with rejected("original_commission_mismatch"):
        f.returns.received_sequence_descriptors(f.root, descriptor(view)["reference_ref"])


def test_valid_unsaved_construction_grants_no_own_execution(f):
    _, view, _ = original(f)
    child = f.child(index=1, role="launch_local", save=False)
    assert f.returns.authenticate(child, allow_unsaved=True) is child
    assert f.returns.authenticate_received_sequence(child, descriptor(view), required_use="sequence_align") == view
    f.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
        "action": canonical({"kind": "tool", "tool": "anything", "arguments": {}}), "result": None, "credit": None})
    with rejected("original_commission_mismatch"):
        f.returns.authenticate(child, allow_unsaved=True)


@pytest.mark.parametrize("use", ["recalculate", "select_projection", "use_transform"])
def test_saved_descriptor_exact_uses_and_no_components_locator_grant(f, use, monkeypatch):
    _, view, _ = original(f, sources=(SAVED_SOURCE,), saved=True)
    desc = view["facts"][SAVED_SOURCE][0]
    no_science(monkeypatch)
    assert f.returns.authenticate_received_saved_sheet(f.root, desc, required_use=use) == view
    assert desc["allowed_uses"] == ["recalculate", "select_projection", "use_transform"]
    assert f.returns.resolve_received(f.root, desc["original_components_file"]["artifact_ref"], "artifact") is True
    altered = deepcopy(desc)
    altered["allowed_uses"] = [use]
    with rejected("saved_sheet_not_received"):
        f.returns.authenticate_received_saved_sheet(f.root, altered, required_use=use)


def test_saved_receipt_survives_lost_bytes_and_source_only_does_not_grant(f):
    _, view, _ = original(f, sources=(SAVED_SOURCE,), saved=True)
    desc = view["facts"][SAVED_SOURCE][0]
    path = f.store.path / "artifacts" / desc["sheet_file"]["sha256"][:2] / desc["sheet_file"]["sha256"]
    path.unlink()
    assert f.returns.authenticate_received_saved_sheet(f.root, desc, required_use="recalculate") == view
    assert f.returns.received_facts(f.root, F.schema_for(PROJECTION_SOURCE)) == {PROJECTION_SOURCE: []}


@pytest.mark.parametrize("case", ["values", "artifact", "only_saved", "rotation_only", "split"])
def test_received_transform_requires_one_actual_matching_complete_projection(f, case, monkeypatch):
    projections = [] if case == "only_saved" else [F.selection("transform", ["rotation"] if case == "rotation_only" else ["rotation", "translation"], artifact=case == "artifact")]
    if case == "split":
        projections = [F.selection("transform", ["rotation"]), F.selection("transform", ["translation"])]
        projections[1]["projection_id"] = "second"
    _, view, _ = original(f, sources=(SAVED_SOURCE, PROJECTION_SOURCE), saved=True, projections=projections)
    components = json.loads(f.store.get_artifact(view["components_file"]["artifact_ref"]))
    transform = {"version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": components["transform"]["rotation"]["value"], "translation_A": components["transform"]["translation"]["value"],
        "fixed_selection": view["request"]["fixed_selection"], "moving_selection": view["request"]["moving_selection"],
        "origin": "received_fitted", "received_from": {"saved_sheet": view["facts"][SAVED_SOURCE][0],
            "components_file": view["components_file"], "calculation_id": components["calculation_id"], "calculation_custody": view["custody"]}}
    no_science(monkeypatch)
    result = f.returns.received_transform_projections(f.root, transform)
    assert len(result) == (1 if case in {"values", "artifact"} else 0)
    changed = deepcopy(transform)
    changed["received_from"]["calculation_id"] = "different-calculation"
    assert f.returns.received_transform_projections(f.root, changed) == []
    if case == "values":
        assert f.returns.resolve_received(f.root, view["components_file"]["artifact_ref"], "artifact") is True  # explicit saved-sheet operand
        output = os.environ.get("PROTEIN_RETURNS_EXAMPLES")
        if output:
            Path(output).mkdir(exist_ok=True)
            (Path(output) / "typed_transform.json").write_text(canonical({"transform": transform, "projection": result[0]}) + "\n")


@pytest.mark.parametrize("case", ["extra_field", "count_float", "count_bool", "nonfinite", "wrong_schema", "wrong_source"])
def test_closed_numerical_sources_reject_mutated_forms(f, case):
    child, view, form = original(f, sources=(PROJECTION_SOURCE,),
        projections=[F.selection("extracted_sequence", ["sequence_length"])])
    schema = plain(child.request["report_contract"]["measurements"]["schema"])
    form = deepcopy(form)
    row = form["answer_0"][0]
    if case == "extra_field":
        row["unrequested"] = 3
    elif case.startswith("count_"):
        row["requested_count"] = 1.0 if case == "count_float" else True
    elif case == "nonfinite":
        row["delivery"]["rows"][0]["values"][0]["value"]["value"] = float("inf")
    elif case == "wrong_schema":
        schema["properties"]["answer_0"]["$id"] += ":changed"
    else:
        schema["properties"]["answer_0"]["x-source"] = SEQUENCE_SOURCE
    with rejected("invalid_schema"):
        f.returns.validate_received_report(child, form, schema)


def test_source_only_and_old_expanded_receipts_never_grant_auxiliaries(f):
    child = f.child(schema=F.reference_schema("execution_result_refs", "execution_result"))
    view = f.publish(child)
    f.returned(f.root, child, facts={"execution_result_refs": [view["custody"]["source_ref"]]})
    desc = descriptor(view)
    f.receipts.receive(f.root.episode_id, f.store._refs(desc), kind="initial")
    for target in (desc["reference_ref"], desc["sequence_file"]["artifact_ref"], view["native_file"]["artifact_ref"]):
        assert f.returns.resolve_received(f.root, target, None) is False
        assert f.returns.retained_reference_access(child, target, None) is False
    assert f.returns.resolve_received(f.root, view["custody"]["source_ref"], "source") is True
    assert f.returns.retained_reference_access(child, view["custody"]["source_ref"], "execution_result") is True
    with rejected("sequence_not_received"):
        f.returns.authenticate_received_sequence(f.root, desc, required_use="sequence_align")


def test_independently_explicit_shared_artifact_delivery_is_preserved(f):
    _, view, _ = original(f)
    ref = view["native_file"]["artifact_ref"]
    other = f.child(index=1, role="scientific_process", schema=F.reference_schema("committed_record_refs", "artifact"))
    outcome = {"status": "completed", "record_refs": [ref]}
    f.journal.save("runtime_actions", {"episode_id": other.episode_id, "decision_index": 0,
        "action": canonical({"kind": "tool", "tool": "fixture.independently_supplied", "arguments": {}}), "result": canonical(outcome), "credit": 0})
    f.receipts.receive(other.episode_id, [ref], kind="own_action", source_index=0)
    f.returned(f.root, other, facts={"committed_record_refs": [ref]})
    assert f.returns.resolve_received(f.root, ref, "artifact") is True


def test_null_custody_failure_crosses_exact_original_and_forwarded_forms(f):
    middle = f.child(role="scientific_process", sources=(FAILURE_SOURCE,))
    child = f.child(parent=middle, sources=(FAILURE_SOURCE,))
    view = f.publish(child)
    failure = {"version": "protein_structure_failure_return_v1", "custody": None, "projection_id": None,
               "issue": issue("capture_incomplete", stage="capture", field="manifest")}
    view["facts"][FAILURE_SOURCE] = [failure]
    f.persist(child, view)
    f.returned(middle, child)
    f.returned(f.root, middle)
    assert f.returns.received_facts(f.root, F.schema_for(FAILURE_SOURCE)) == {FAILURE_SOURCE: [failure]}


@pytest.fixture
def aligned(f):
    first, left, _ = original(f)
    second, right, _ = original(f, index=1)
    scientist = f.child(index=2, role="scientific_process", schema=F.reference_schema())
    alignment = f.alignment(scientist, descriptor(left)["reference_ref"], descriptor(right)["reference_ref"])
    return scientist, alignment


def test_real_alignment_own_action_then_explicit_child_return_then_frozen_ancestor(f, aligned, monkeypatch):
    scientist, alignment = aligned
    no_science(monkeypatch)
    assert f.returns.authenticate_received_alignment(scientist, alignment) is None
    child = f.child(parent=scientist, index=1, role="launch_local")
    assert f.returns.authenticate_received_alignment(child, alignment) is None
    with rejected("alignment_not_received"):
        f.returns.authenticate_received_alignment(f.root, alignment)
    f.returned(f.root, scientist, facts={"committed_record_refs": [alignment["observation_ref"]]})
    assert f.returns.authenticate_received_alignment(f.root, alignment) is None
    later = f.child(index=3, role="launch_local")
    assert f.returns.authenticate_received_alignment(later, alignment) is None


@pytest.mark.parametrize("case", ["source_only", "untyped_body", "delayed_return", "after_own_cutoff"])
def test_alignment_receipt_cannot_be_replaced_by_source_or_store_visibility(f, aligned, case):
    scientist, alignment = aligned
    if case == "after_own_cutoff":
        early = f.child(parent=scientist, index=0, role="launch_local")
        # The fixture deliberately replaces the original action by a child
        # commission at the same ordinal: that cannot prove an earlier align.
    else:
        early = f.child(index=3, role="launch_local")
    refs = [alignment["source_ref"]] if case == "source_only" else [alignment["observation_ref"]]
    if case == "untyped_body":
        refs = []
    if case != "after_own_cutoff":
        f.returned(f.root, scientist, facts={"committed_record_refs": refs})
    f.receipts.receive(early.episode_id, [alignment["source_ref"], alignment["observation_ref"]], kind="initial")
    with rejected("alignment_not_received"):
        f.returns.authenticate_received_alignment(early, alignment)


@pytest.mark.parametrize("case", ["reads_align", "missing_tool_row", "incomplete", "changed_outcome", "operation_ref", "arguments", "bad_pending"])
def test_alignment_matches_exact_original_runtime_and_tool_registry_records(f, aligned, case):
    scientist, alignment = aligned
    row = f.journal.row("runtime_actions", scientist.episode_id, 0)
    if case == "missing_tool_row":
        f.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (alignment["original_operation_key"],))
    elif case == "incomplete":
        f.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0", (f.run_id, scientist.episode_id))
    else:
        action, outcome = json.loads(row["action"]), json.loads(row["result"])
        if case == "reads_align":
            action["tool"] = "reads.align"
        elif case == "arguments":
            action["arguments"]["mode"] = "local"
        elif case == "operation_ref":
            outcome["operation_ref"] = "operation_" + "a" * 24
        elif case == "bad_pending":
            outcome["pending_work_after_action"] = {"items": "bad"}
        else:
            outcome["result"]["paired_positions"] = 999
        f.store.db.execute("UPDATE runtime_actions SET action=?,result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(action), canonical(outcome), f.run_id, scientist.episode_id))
    with rejected("alignment_not_received" if case == "incomplete" else "original_commission_mismatch"):
        f.returns.authenticate_received_alignment(scientist, alignment)


def test_alignment_validated_pending_wrapper_and_no_positive_authority_cache(f, aligned):
    scientist, alignment = aligned
    row = f.journal.row("runtime_actions", scientist.episode_id, 0)
    outcome = json.loads(row["result"])
    outcome["pending_work_after_action"] = {"version": "pending_work_v1", "captured_at": "2026-10-27T00:00:01+00:00", "items": []}
    f.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0", (canonical(outcome), f.run_id, scientist.episode_id))
    assert f.returns.authenticate_received_alignment(scientist, alignment) is None
    f.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (alignment["original_operation_key"],))
    with rejected("original_commission_mismatch"):
        f.returns.authenticate_received_alignment(scientist, alignment)


def test_requested_source_order_empty_arrays_and_independent_field_names(f):
    schema = F.schema_for(FAILURE_SOURCE, SEQUENCE_SOURCE, names={SEQUENCE_SOURCE: "chosen_chain"})
    assert requested_sources(schema) == (SEQUENCE_SOURCE, FAILURE_SOURCE)
    assert f.returns.received_facts(f.root, schema) == {SEQUENCE_SOURCE: [], FAILURE_SOURCE: []}
    assert f.returns.received_context(f.root) == []


def test_actual_compact_fact_expansion_and_original_declaration(f, monkeypatch):
    child = f.compact_commission(f.child())
    view = f.publish(child)
    f.returned(f.root, child)
    no_science(monkeypatch)
    assert f.returns.authenticate_received_sequence(f.root, descriptor(view), required_use="sequence_align") == view
    request = plain(child.request)
    request["message"]["report_contract_declaration"]["fact_references"][0]["schema_sha256"] = "0" * 64
    f.replace_request(child, request)
    with rejected("original_commission_mismatch"):
        f.returns.received_sequence_descriptors(f.root, descriptor(view)["reference_ref"])


@pytest.mark.parametrize("alter", [None, "frozen_digest", "schema_text", "purpose", "origin", "form"])
def test_compact_redelivery_uses_its_actual_frozen_prefix_and_facts(f, alter):
    child = f.compact_commission(f.child(sources=(FAILURE_SOURCE,)))
    view = f.publish(child)
    f.returned(f.root, child)
    early = f.child(index=1, role="launch_local")
    f.redeliver(child, index=2)
    late = f.child(index=3, role="launch_local")
    with rejected("sequence_not_received"):
        f.returns.authenticate_received_sequence(early, descriptor(view), required_use="sequence_align")
    assert f.returns.authenticate_received_sequence(late, descriptor(view), required_use="sequence_align") == view
    if alter is None:
        assert f.returns.received_facts(f.root, F.schema_for(SEQUENCE_SOURCE))[SEQUENCE_SOURCE] == [descriptor(view)]
        return
    if alter in {"frozen_digest", "schema_text", "purpose"}:
        row = f.journal.row("runtime_model_calls", f.root.episode_id, 2)
        request, response = json.loads(row["request"]), json.loads(row["response"])
        if alter == "frozen_digest":
            request["contract_information"]["fact_sources_sha256"] = "0" * 64
        elif alter == "schema_text":
            response["selection"]["schema_json"] = canonical(F.schema_for(FAILURE_SOURCE))
        else:
            response["selection"]["purpose"] += " altered"
        f.store.db.execute("UPDATE runtime_model_calls SET request=?,response=? WHERE run_id=? AND episode_id=? AND call_index=2",
            (canonical(request), canonical(response), f.run_id, f.root.episode_id))
    elif alter == "origin":
        f.store.db.execute("UPDATE runtime_report_attempts SET delivery_ref=? WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
            ("unrelated-delivery", f.run_id, f.root.episode_id))
    else:
        f.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
            (canonical({source: [] for source in FACT_SOURCES}), f.run_id, child.episode_id))
    with rejected("original_commission_mismatch"):
        f.returns.received_sequence_descriptors(f.root, descriptor(view)["reference_ref"])


@pytest.mark.parametrize("alter", [None, "selector", "other_assignment", "assignment_hash", "invocation_hash", "invocation_ref", "goal", "initial_report"])
def test_materialized_scientific_assignment_requires_original_selectors_and_hashes(f, alter):
    from gene_annotation_episode.scientific_process_records import scientific_digest, scientific_invocation_ref, selector_selection
    from gene_annotation_episode.tool_information import make_tool_info
    from gene_annotation_episode.tools import ToolRegistry
    _, view, _ = original(f)
    child = f.child(index=1, role="scientific_process")
    tool = make_tool_info({"name": "sequence.align", **ToolRegistry(f.store).catalog(f.scope)["sequence.align"]}, "local")
    option = lambda slot, name: {"version": "scientific_process_option_ref_v1", "library_id": "a" * 64,
                                "slot": slot, "option_id": name, "entry_sha256": "b" * 64}
    selected = {"version": "scientific_process_selection_v3", "evidence_axis": option("evidence_axis", "A1"),
        "thought_pattern": option("thought_pattern", "P1"), "child_tool_info": [tool]}
    assignment = {"selection": selected, "evidence_refs": [], "constraints": {}, "context": {}}
    request = plain(child.request)
    request["message"]["episode_assignment"] = assignment
    contract = request["report_contract"]
    invocation = {"objective": request["goal"]["objective"], "scope": plain(child.scope),
        "purpose": contract["decision"], "report_schema": contract["measurements"]["schema"], "initial_report": {}}
    request["message"]["scientific_process"] = {"version": "filled_scientific_process_v1", "selection": selected,
        "assignment_sha256": scientific_digest(assignment), "invocation_sha256": scientific_digest(invocation),
        "mechanics_binding": {"version": "synthetic_recorded_mechanics_binding"}}
    request["message"]["scientific_invocation_ref"] = scientific_invocation_ref(f.run_id, child.path)
    action = json.loads(f.journal.row("runtime_actions", f.root.episode_id, 1)["action"])
    action["assignment"] = {**assignment, "selection": selector_selection(selected)}
    if alter == "selector":
        action["assignment"]["selection"]["child_tool_info"][0]["resources"] = "hpc"
    elif alter == "other_assignment":
        action["assignment"]["evidence_refs"] = list(f.scope["subject_refs"])
    elif alter in {"assignment_hash", "invocation_hash"}:
        request["message"]["scientific_process"][alter.removesuffix("_hash") + "_sha256"] = "0" * 64
    elif alter == "invocation_ref":
        request["message"]["scientific_invocation_ref"] = scientific_invocation_ref(f.run_id, f.root.path)
    elif alter == "goal":
        action["goal"] += " altered"
    elif alter == "initial_report":
        action["initial_report_json"] = '{"extra":true}'
    f.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=1",
        (canonical(action), f.run_id, f.root.episode_id))
    child = f.replace_request(child, request)
    if alter is None:
        assert f.returns.authenticate_received_sequence(child, descriptor(view), required_use="sequence_align") == view
    else:
        with rejected("original_commission_mismatch"):
            f.returns.authenticate_received_sequence(child, descriptor(view), required_use="sequence_align")


def test_all_four_exact_resources_forward_partial_facts_with_arbitrary_field_names(f, monkeypatch):
    names = {PROJECTION_SOURCE: "selected_numbers", SAVED_SOURCE: "retained_pair",
             SEQUENCE_SOURCE: "chosen_sequences", FAILURE_SOURCE: "qualified_issues"}
    middle = f.child(role="scientific_process", schema=F.schema_for(*FACT_SOURCES, names=names))
    extraction = f.child(parent=middle, index=0, sources=(PROJECTION_SOURCE, SEQUENCE_SOURCE, FAILURE_SOURCE),
        projections=[F.selection("extracted_sequence", ["sequence_length"])])
    extracted = f.publish(extraction)
    failure = {"version": "protein_structure_failure_return_v1", "custody": extracted["custody"], "projection_id": None,
               "issue": issue("selected_field_unavailable", stage="projection", field="projection_fields")}
    extracted["facts"][FAILURE_SOURCE] = [failure]
    f.persist(extraction, extracted)
    f.returned(middle, extraction)
    comparison = f.child(parent=middle, index=1, sources=(PROJECTION_SOURCE, SAVED_SOURCE), saved=True,
        projections=[F.selection("transform", ["rotation", "translation"])])
    compared = f.publish(comparison, comparison=True)
    f.returned(middle, comparison)
    no_science(monkeypatch)
    form = f.returned(f.root, middle)
    assert list(form) == list(names.values())
    assert [len(form[name]) for name in names.values()] == [2, 1, 1, 1]
    groups = f.returns.received_facts(f.root, F.schema_for(*FACT_SOURCES))
    assert groups[SEQUENCE_SOURCE] == [descriptor(extracted)]
    assert groups[SAVED_SOURCE] == compared["facts"][SAVED_SOURCE]
    assert groups[FAILURE_SOURCE] == [failure]
    assert f.returns.resolve_received(f.root, extracted["native_file"]["artifact_ref"], "artifact") is False
    output = os.environ.get("PROTEIN_RETURNS_EXAMPLES")
    if output:
        Path(output).mkdir(exist_ok=True)
        (Path(output) / "four_source_form.json").write_text(canonical(form) + "\n")


def test_grant_namespaces_do_not_convert_sequence_or_artifact_to_result(f):
    _, view, _ = original(f)
    selected = descriptor(view)
    assert f.returns.resolve_received(f.root, selected["reference_ref"], "subject") is True
    assert f.returns.resolve_received(f.root, selected["sequence_file"]["artifact_ref"], "subject") is False
    assert f.returns.resolve_received(f.root, selected["reference_ref"], "execution_result") is False
    assert f.returns.resolve_received(f.root, selected["custody"]["source_ref"], "execution_result") is True
    assert f.returns.resolve_received(f.root, selected["custody"]["source_ref"], "execution_handoff") is False
    assert f.returns.resolve_received(f.root, selected["custody"]["result_receipt_key"], None) is False


@pytest.mark.parametrize("alter", [None, "new_field", "changed_contract", "changed_value"])
def test_redelivery_nonfact_fields_match_only_original_frozen_interpretations(f, alter):
    schema = F.schema_for(FAILURE_SOURCE)
    schema["properties"]["choice"] = {"type": "string", "enum": ["first", "second"]}
    schema["required"].append("choice")
    child = f.child(schema=schema)
    view = f.publish(child)
    facts = {**view["facts"], "interpretations": {"choice": "first"}}
    f.returned(f.root, child, facts=facts)
    f.redeliver(child, index=1)
    row = f.journal.row("runtime_model_calls", f.root.episode_id, 1)
    response = json.loads(row["response"])
    selected = json.loads(response["selection"]["schema_json"])
    name = "new_choice" if alter == "new_field" else "choice"
    node = {"type": "string", "enum": ["first"]} if alter == "changed_contract" else schema["properties"]["choice"]
    selected["properties"][name] = node
    selected["required"].append(name)
    response["selection"]["schema_json"] = canonical(selected)
    attempt = f.store.db.execute("SELECT contract,form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
        (f.run_id, f.root.episode_id)).fetchone()
    contract, form = json.loads(attempt["contract"]), json.loads(attempt["form"])
    contract["measurements"]["schema"]["properties"][name] = node
    contract["measurements"]["schema"]["required"].append(name)
    form[name] = "second" if alter == "changed_value" else "first"
    f.store.db.execute("UPDATE runtime_model_calls SET response=? WHERE run_id=? AND episode_id=? AND call_index=1",
        (canonical(response), f.run_id, f.root.episode_id))
    f.store.db.execute("UPDATE runtime_report_attempts SET contract=?,form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1",
        (canonical(contract), canonical(form), f.run_id, f.root.episode_id))
    if alter is None:
        assert f.returns.authenticate_received_sequence(f.root, descriptor(view), required_use="sequence_align") == view
    else:
        with rejected("original_commission_mismatch"):
            f.returns.received_sequence_descriptors(f.root, descriptor(view)["reference_ref"])
