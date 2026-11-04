"""Additive context/geometry ports: no search or acquisition is executed."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_database_grader import build_database_sheet, calculate_database_probabilities
from test_blast_database_grader import result, metadata, profile
from test_blast_explicit_associations import synthetic_inputs, sequence_binding


def context(**identity_changes):
    identity = dict(namespace="native_blast_database", value="synthetic_db", version="1",
        release="release1", scope="bacteria_only", preparation_type="sequence_database",
        source={"source_ref": "synthetic-manifest", "pointer": "/database"})
    identity.update(identity_changes)
    return dict(reporting=dict(native_hit_array_present=True, native_hit_count=2,
        requested_hit_limit=2, requested_hsp_limit=3, native_returncode=0, producer_complete=True),
        database_identity=identity)


@pytest.mark.parametrize("program", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("override", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
def test_every_ordinary_override_requires_exact_program(program, override):
    native = result()
    native["search"]["program"] = program
    if override == program:
        assert build_database_sheet(native, geometry_program=override) == build_database_sheet(native)
    else:
        with pytest.raises(ValueError, match="^blast_database_geometry_program_conflict$"):
            build_database_sheet(native, geometry_program=override)


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
def test_extended_geometry_preserves_execution_identity_and_digest_groups(program):
    inputs = synthetic_inputs()
    inputs["result"]["search"]["program"] = program
    inputs["sequence_identity_bindings"] = [sequence_binding(4), sequence_binding(9)]
    original = deepcopy(inputs)
    out = build_database_sheet(**inputs, geometry_program="blastp")
    assert inputs == original
    assert out["normalized_result"]["search"]["program"] == program
    assert len(out["sequence_groups"]) == 1
    assert out["hits"][0]["measurements"]["query_paired_coverage"] == .5
    old = build_database_sheet(**inputs)
    assert old["hits"][0]["measurements"]["query_paired_coverage"] is None
    assert len(old["sequence_groups"]) == 2
    for wrong in ("blastn", "blastx", "tblastn", "tblastx"):
        with pytest.raises(ValueError, match="^blast_database_geometry_program_conflict$"):
            build_database_sheet(**inputs, geometry_program=wrong)


@pytest.mark.parametrize("program,geometry", [("rpsblast", "blastp"), ("rpstblastn", "blastx"),
    ("blastn_vdb", "blastn"), ("tblastn_vdb", "tblastn")])
def test_profile_and_vdb_cannot_enter_sequence_population_geometry(program, geometry):
    native = result()
    native["search"]["program"] = program
    with pytest.raises(ValueError, match="^blast_database_geometry_program_conflict$"):
        build_database_sheet(native, geometry_program=geometry)


def test_context_uses_real_limits_and_population_without_inventing_request_fields():
    native, supplied = result(), context()
    before = deepcopy((native, supplied))
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G")],
        calculation_context=supplied, database_profile=profile(release="release1", scope="bacteria_only"))
    assert (native, supplied) == before
    assert sheet["normalized_result"]["search"]["request"] == {}
    assert sheet["calculation_context"] == supplied
    assert sheet["search_limits"]["requested_hit_limit"] == 2
    assert sheet["search_limits"]["requested_hsp_limit"] == 3
    assert sheet["search_limits"]["limit_reached"] is True
    assert sheet["database_representation"]["available_for_adjustment"] is True
    score = calculate_database_probabilities(sheet)
    assert score["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    assert score["representation_adjusted_probabilities"] == pytest.approx({"F": 1/3, "G": 2/3})


@pytest.mark.parametrize("identity,request_values,reason", [
    ({"release": None}, {}, "database_context_release_unavailable"),
    ({"scope": None}, {}, "database_context_scope_unavailable"),
    ({"value": "wrong"}, {}, "database_context_value_conflict"),
    ({}, {"database_release": "other"}, "database_context_release_conflict"),
    ({}, {"database_scope": "other"}, "database_context_scope_conflict"),
    ({"preparation_type": "rps"}, {}, "database_context_sequence_population_unqualified"),
])
def test_population_conflicts_disable_only_correction(identity, request_values, reason):
    native = result(**request_values)
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G")],
        calculation_context=context(**identity), database_profile=profile(release="release1", scope="bacteria_only"))
    scores = calculate_database_probabilities(sheet)
    assert reason in scores["representation_adjustment_unavailable_reasons"]
    assert scores["representation_adjusted_probabilities"] is None
    assert scores["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    assert sheet["normalized_result"] == native


def test_null_ports_exactly_preserve_saved_legacy_sheets_and_models():
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "verification/tool_graders_blast_explicit_associations_2026-10-24/legacy_prechange.json").read_text())["cases"]
    for case in cases:
        actual = build_database_sheet(**case["arguments"], geometry_program=None, calculation_context=None)
        assert actual == case["sheet"]
        assert "calculation_context" not in actual
        assert calculate_database_probabilities(actual) == case["calculations"][0]


@pytest.mark.parametrize("value", [True, "blastp", {}, {"reporting": {}},
    {"reporting": None, "database_identity": None}])
def test_invalid_context_contract_is_rejected(value):
    with pytest.raises(ValueError, match="blast_database_calculation_"):
        build_database_sheet(result(), calculation_context=value)


def test_context_contradiction_is_visible_even_without_population_profile():
    out = build_database_sheet(result(), calculation_context=context(value="wrong"))
    assert "database_context_value_conflict" in {issue["code"] for issue in out["issues"]}
    assert out["database_representation"]["available_for_adjustment"] is False
