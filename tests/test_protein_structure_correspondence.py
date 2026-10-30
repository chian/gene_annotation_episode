"""Actual retained Biopython output, explicit maps, and rejection of wrong identities."""
from copy import deepcopy
from importlib import import_module
import pytest
from gene_annotation_episode.biopython_pairwise_grader import build_biopython_pairwise_sheet
from gene_annotation_episode.protein_structure_correspondence import correspondence_from_pairwise_sheet, validate_explicit_residue_map
from gene_annotation_episode.protein_structure_sequences import rebind_structure_sequence
f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


def pair():
    return f.fixture_pdb()[2], f.fixture_pdb(role="moving", chain="B")[2]


def test_actual_retained_alignment_does_not_intersect_residue_numbers():
    fixed, moving = pair()
    sheet, kwargs, result = f.retained_alignment(fixed, moving)
    assert result["population_available"] and len(result["rows"]) == 4
    assert [(r["fixed_position_key"]["residue_number"], r["moving_position_key"]["residue_number"]) for r in result["rows"]] == [(10, 101), (10, 102), (11, 103), (15, 104)]
    assert result["alignment_native"]["pairwise_sheet"] == sheet
    assert result["unmapped_fixed"] == result["unmapped_moving"] == []


def test_global_substitution_and_orientation_are_literal_column_relationships():
    fixed = f.fixture_pdb("AGST")[2]
    moving = f.fixture_pdb("AGTT", role="moving", chain="B")[2]
    _, _, result = f.retained_alignment(fixed, moving, orientation="fixed_is_reference")
    assert [r["relationship"] for r in result["rows"]] == ["identical", "identical", "substituted", "identical"]
    assert result["rows"][2]["fixed_symbol"] == "S" and result["rows"][2]["moving_symbol"] == "T"


def test_gap_columns_and_local_unmapped_sites_survive():
    fixed = f.fixture_pdb("AAAAWWWW", coordinates=[[float(i), 0, 0] for i in range(8)])[2]
    moving = f.fixture_pdb("WWWW", role="moving", chain="B")[2]
    _, _, local = f.retained_alignment(fixed, moving, mode="local")
    assert [r["sequence_position_0based"] for r in local["unmapped_fixed"]] == [0, 1, 2, 3]
    assert all(r["reason"] == "outside_alignment" for r in local["unmapped_fixed"])
    _, _, global_ = f.retained_alignment(fixed, moving, mode="global", orientation="fixed_is_reference")
    assert len(global_["rows"]) == 8
    assert sum(r["relationship"] == "moving_gap" for r in global_["rows"]) == 4
    assert all(r["reason"] == "gap_in_other_sequence" for r in global_["unmapped_fixed"])


def test_no_alignment_is_genuine_empty_population_not_bad_traceback():
    fixed = f.fixture_pdb("AAAA")[2]
    moving = f.fixture_pdb("WWWW", role="moving", chain="B")[2]
    sheet, kwargs, result = f.retained_alignment(fixed, moving, mode="local")
    assert not kwargs["native"]["aligned"] and result["population_available"] and result["rows"] == []
    assert all(row["reason"] == "no_alignment" for row in result["unmapped_fixed"])


def test_altered_traceback_keeps_invalid_state_without_fake_zero():
    fixed, moving = pair()
    sheet, kwargs, _ = f.retained_alignment(fixed, moving)
    kwargs["native"]["coordinates"][0][-1] = 3
    bad_sheet = build_biopython_pairwise_sheet(kwargs["native"], molecule="protein")
    result = correspondence_from_pairwise_sheet(bad_sheet, **kwargs)
    assert not result["population_available"] and result["state"] == "invalid"
    assert result["alignment_native"] is None and result["issues"][0]["code"] == "invalid_traceback"


def test_equal_lengths_wrong_reference_or_changed_map_are_rejected():
    fixed, moving = pair()
    sheet, kwargs, _ = f.retained_alignment(fixed, moving)
    wrong = deepcopy(kwargs); wrong["alignment"]["query_reference_ref"] = "reference_" + "f" * 24
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        correspondence_from_pairwise_sheet(sheet, **wrong)
    wrong = deepcopy(kwargs); wrong["fixed_descriptor"]["selection"]["zero_occupancy_policy"] = "include"
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        correspondence_from_pairwise_sheet(sheet, **wrong)
    wrong = deepcopy(kwargs); wrong["fixed_descriptor"]["residue_map_file"] = f.identity(b"changed", "protein_structure_sequence_v1")
    with pytest.raises(ValueError, match="sequence_artifact_mismatch"):
        correspondence_from_pairwise_sheet(sheet, **wrong)


def test_role_rebound_original_single_maps_match_exact_original_bytes():
    _, _, one, _ = f.fixture_pdb(role="single")
    _, _, two, _ = f.fixture_pdb(role="single", chain="B")
    fixed, moving = rebind_structure_sequence(one, structure_role="fixed"), rebind_structure_sequence(two, structure_role="moving")
    sheet, kwargs, _ = f.retained_alignment(fixed, moving)
    kwargs["fixed_descriptor"] = f.sequence_descriptor(one, reference_digit="a")
    kwargs["moving_descriptor"] = f.sequence_descriptor(two, reference_digit="b")
    result = correspondence_from_pairwise_sheet(sheet, **kwargs)
    assert len(result["rows"]) == 4
    assert one["selection"]["structure_role"] == "single"


def test_symbol_mismatch_rejects_even_when_native_counts_are_consistent():
    fixed, moving = pair()
    sheet, kwargs, _ = f.retained_alignment(fixed, moving)
    native = kwargs["native"]
    native["aligned_query"] = native["aligned_reference"] = "AAAA"
    sheet = build_biopython_pairwise_sheet(native, molecule="protein")
    with pytest.raises(ValueError, match="alignment_symbol_mismatch"):
        correspondence_from_pairwise_sheet(sheet, **kwargs)


def test_explicit_map_is_injective_collinear_and_exactly_selected():
    fixed, moving = pair()
    _, _, result = f.explicit_map(fixed, moving, [(0, 1), (2, 3)])
    assert [(r["fixed_position_0based"], r["moving_position_0based"]) for r in result["rows"]] == [(0, 1), (2, 3)]
    assert [r["sequence_position_0based"] for r in result["unmapped_fixed"]] == [1, 3]
    for pairs, code in [([(0, 0), (0, 1)], "map_not_injective"), ([(1, 0), (0, 1)], "map_not_collinear")]:
        with pytest.raises(ValueError, match=code):
            f.explicit_map(fixed, moving, pairs)
    _, _, empty = f.explicit_map(fixed, moving, [])
    assert empty["population_available"] and empty["rows"] == [] and len(empty["unmapped_fixed"]) == 4


def test_declared_no_coordinate_residue_retains_correspondence():
    fixed = f.fixture_cif()[2]
    moving = f.fixture_cif(role="moving")[2]
    _, _, result = f.explicit_map(fixed, moving)
    assert len(result["rows"]) == 3
    assert result["rows"][1]["fixed_residue"] is None
    assert result["rows"][1]["fixed_declared_residue"]["label_seq_id"] == 4
    assert result["rows"][1]["fixed_ca"]["primary_reason"] == "ca_missing"


def test_retained_filled_examples_are_hand_checkable_and_source_bound(tmp_path):
    from gene_annotation_episode.protein_structure_contracts import canonical
    fixed_bytes, fixed_parsed, fixed, fixed_meta = f.fixture_pdb()
    moving_bytes, moving_parsed, moving, moving_meta = f.fixture_pdb(role="moving", chain="B")
    sheet, kwargs, correspondence = f.retained_alignment(fixed, moving)
    cif_bytes, cif_parsed, cif_sequence, cif_metadata = f.fixture_cif()
    document, map_file, declared_pairs = f.explicit_map(cif_sequence, rebind_structure_sequence(cif_sequence, structure_role="moving"))
    example = {"purpose": "Synthetic owner-A input example; no Store authority or comparison fit was run",
        "fixed": {"parsed": fixed_parsed, "sequence": fixed, "metadata": fixed_meta, "descriptor": kwargs["fixed_descriptor"]},
        "moving": {"parsed": moving_parsed, "sequence": moving, "metadata": moving_meta, "descriptor": kwargs["moving_descriptor"]},
        "retained_native_alignment": kwargs["native"], "alignment_descriptor": kwargs["alignment"], "full_pairwise_sheet": sheet,
        "correspondence": correspondence, "declared_example": {"parsed": cif_parsed, "sequence": cif_sequence, "metadata": cif_metadata,
        "map_document": document, "map_file": map_file, "correspondence": declared_pairs}}
    (tmp_path / "fixed.pdb").write_bytes(fixed_bytes)
    (tmp_path / "moving.pdb").write_bytes(moving_bytes)
    (tmp_path / "declared_gaps.cif").write_bytes(cif_bytes)
    (tmp_path / "filled_inputs.json").write_text(canonical(example) + "\n", encoding="utf-8")
    assert [r["relationship"] for r in correspondence["rows"]] == ["identical"] * 4
    assert len(declared_pairs["rows"]) == 3 and declared_pairs["rows"][1]["fixed_ca"]["state"] == "missing"


def test_unexpected_native_or_sheet_shape_raises_instead_of_becoming_traceback_failure():
    fixed, moving = pair()
    sheet, kwargs, _ = f.retained_alignment(fixed, moving)
    bad = deepcopy(kwargs); bad["native"]["unexpected"] = 1
    with pytest.raises(ValueError, match="invalid_schema"):
        correspondence_from_pairwise_sheet(sheet, **bad)
    bad_sheet = deepcopy(sheet); bad_sheet["unexpected"] = 1
    with pytest.raises(ValueError, match="invalid_schema"):
        correspondence_from_pairwise_sheet(bad_sheet, **kwargs)


def test_partial_traceback_does_not_hide_descriptor_mode_or_operand_mismatch():
    fixed, moving = pair()
    _, kwargs, _ = f.retained_alignment(fixed, moving)
    kwargs["native"]["coordinates"][0][-1] = 3
    partial_sheet = build_biopython_pairwise_sheet(kwargs["native"], molecule="protein")
    bad = deepcopy(kwargs); bad["alignment"]["mode"] = "local"
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        correspondence_from_pairwise_sheet(partial_sheet, **bad)
    bad = deepcopy(kwargs); bad["native"]["query_length"] = 5
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        correspondence_from_pairwise_sheet(partial_sheet, **bad)
