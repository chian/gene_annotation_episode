"""Selected coordinates reuse complete received identity without new alignment.

The expression check uses the same reusable sequence and declared table as the
autonomous region case. Its unit publication is not an HPC execution claim.
"""
import json
from pathlib import Path

import pytest

from gene_annotation_episode.a107_expression_components import calculate
from gene_annotation_episode.a107_qualification import _expression
from gene_annotation_episode.component_axis_native_hpc import publish, RESULT_PROVIDER
from gene_annotation_episode.component_sequence_attribution import protein_correspondence, protein_sequence
from gene_annotation_episode.state import Store


FIXTURES = Path(__file__).parent / "fixtures/a107_evaluation"


@pytest.fixture
def real_sequence(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(FIXTURES / "anonymous-case-01.faa", molecule="protein")["subject_refs"]
        yield store, target, protein_sequence(store, target)


def reference(store, sequence):
    artifact = store.artifact(sequence)
    source = store.put("source", {"provider": "sequence_identity_unit_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    return store.put("reference", {"reference_type": "protein", "source_ref": source,
        "accession": "reference-sequence", "label": "Received reference sequence",
        "sequence_ref": artifact, "molecule": "protein", "length": len(sequence),
        "term_refs": [], "context_refs": []}, origin="caller")["id"]


def region(store, subject, segments):
    return store.put("feature", {"subject_ref": subject, "kind": "sequence_region",
        "segments": [{"start": start, "end": end} for start, end in segments],
        "strand": "+", "context_refs": []}, origin="caller")["id"]


@pytest.mark.parametrize("separate_reference", [False, True])
def test_selected_identity_keeps_original_residue_indices(real_sequence, separate_reference):
    store, target, sequence = real_sequence
    component = reference(store, sequence) if separate_reference else target
    selected = list(range(20, 40))
    link, refs = protein_correspondence(store, target, component, {target, component}, positions=selected)
    assert link["state"] == "evaluated" and not link["missing"]
    assert [(row[0], row[1]) for row in link["pairs"]] == [(p, p) for p in selected]
    assert all(row[2] == sequence[row[0]] == row[3] for row in link["pairs"])
    assert link["identity_distance"] == 0
    assert link["mapped_pair_count"] == link["requested_actual_position_count"] == 20
    assert link["reference_position_count"] == len(sequence)
    assert link["coverage"] == pytest.approx(20 / len(sequence))
    assert refs == {target, component}
    assert link["functional_property"] == "unestablished_by_sequence_correspondence_alone"


def test_matching_local_letters_do_not_invent_an_unreceived_complete_map(real_sequence):
    store, target, sequence = real_sequence
    other = ("A" if sequence[0] != "A" else "M") + sequence[1:]
    component = reference(store, other)
    assert sequence[20:40] == other[20:40] and sequence != other
    link, _ = protein_correspondence(store, target, component, {target, component}, positions=list(range(20, 40)))
    assert link["state"] == "unresolved" and link["missing"]
    assert link["mapped_pair_count"] == 0


def test_discontinuous_feature_lifts_through_its_received_complete_identity(real_sequence):
    store, target, _sequence = real_sequence
    feature = region(store, target, [(20, 30), (40, 50)])
    link, refs = protein_correspondence(store, feature, target, {feature, target}, positions=[0, 1, 10, 19])
    assert link["state"] == "evaluated" and not link["missing"]
    assert [(row[0], row[1]) for row in link["pairs"]] == [(0, 20), (1, 21), (10, 40), (19, 49)]
    assert link["coordinate_frames"]["actual"]["feature_path"][0]["feature_ref"] == feature
    assert {target, feature} <= refs


def test_missing_parent_frame_is_not_reopened_for_a_different_reference(real_sequence):
    store, target, sequence = real_sequence
    feature = region(store, target, [(20, 40)])
    component = reference(store, sequence)
    link, refs = protein_correspondence(store, feature, component, {feature, component}, positions=[0, 1])
    assert link["state"] == "unresolved"
    assert link["required_record_refs"] == [target]
    assert target not in refs and not link["pairs"]


def test_identity_within_one_received_feature_needs_no_private_parent_frame(real_sequence):
    store, target, _sequence = real_sequence
    feature = region(store, target, [(20, 40)])
    link, refs = protein_correspondence(store, feature, feature, {feature}, positions=[3, 4])
    assert link["state"] == "evaluated" and not link["missing"]
    assert [(row[0], row[1]) for row in link["pairs"]] == [(3, 3), (4, 4)]
    assert refs == {feature}


def test_coordinate_identity_keeps_unresolved_amino_acids_explicit(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MXAA", molecule="protein")["subject_refs"]
        link, _ = protein_correspondence(store, target, target, {target}, positions=[0, 1])
        assert link["unresolved_actual_symbols"] == [{"position": 1, "symbol": "X"}]
        assert link["unresolved_reference_symbols"] == [{"position": 1, "symbol": "X"}]
        assert "resolved_amino_acid_identity_in_requested_scope" in link["missing"]


@pytest.mark.parametrize("require_criterion", [False, True])
def test_real_region_expression_keeps_whole_feature_quantities(real_sequence, require_criterion):
    store, target, _sequence = real_sequence
    document = json.loads((FIXTURES / "declared-expression-panel.json").read_text())
    native = calculate(document, {"condition_key": "c1", "left_feature_id": "left",
        "right_feature_id": "right", "sample_ids": ["s1", "s2", "s3", "s4"]})
    expression = publish(store, RESULT_PROVIDER, {"axis": "A107",
        "scientific_profile": "a107_expression_components_v2", "scope": store.validate_scope(),
        "operation": "partner.request_expression_hpc", "native_components": native})
    result, _ = _expression(store, {"target_ref": target, "actual_ref": target,
        "component_ref": target, "expression_ref": expression, "feature_side": "left",
        "encoded_product_ref": None, "positions": list(range(20, 40)), "alignment_ref": None,
        "require_detection_criterion": require_criterion}, {target, expression})
    assert result["measured_feature_identity"] == "declared_measured_feature_sequence_equals_received_actual_sequence"
    assert result["component_correspondence"]["mapped_pair_count"] == 20
    assert not result["correspondence_missing"]
    assert result["native_components"] == native["components"]
    assert result["dependence"] == native["dependence"]
    assert result["biological_scope"] == "whole_measured_feature_quantity; requested_local_map_is_not_site_specific_expression"
    if require_criterion:
        assert "assay_criterion_for_selected_measured_samples" in result["expression_criterion_missing"]


def test_correct_self_coordinates_do_not_override_a_different_measured_sequence(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(FIXTURES / "anonymous-case-02.faa", molecule="protein")["subject_refs"]
        document = json.loads((FIXTURES / "declared-expression-panel.json").read_text())
        native = calculate(document, {"condition_key": "c1", "left_feature_id": "left",
            "right_feature_id": "right", "sample_ids": ["s1", "s2", "s3", "s4"]})
        expression = publish(store, RESULT_PROVIDER, {"axis": "A107",
            "scientific_profile": "a107_expression_components_v2", "scope": store.validate_scope(),
            "operation": "partner.request_expression_hpc", "native_components": native})
        result, _ = _expression(store, {"target_ref": target, "actual_ref": target,
            "component_ref": target, "expression_ref": expression, "feature_side": "left",
            "encoded_product_ref": None, "positions": list(range(20, 40)), "alignment_ref": None,
            "require_detection_criterion": False}, {target, expression})
        assert result["component_correspondence"]["mapped_pair_count"] == 20
        assert result["state"] == "expression_correspondence_unresolved"
        assert "measured_sequence_hash_differs; molecular_correspondence_unresolved" in result["missing"]
        assert result["native_components"] == native["components"]
