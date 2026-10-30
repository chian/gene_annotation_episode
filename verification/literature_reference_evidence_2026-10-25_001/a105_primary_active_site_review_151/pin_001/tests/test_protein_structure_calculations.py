"""Independent small numerical answers for the exact protein contract."""
from copy import deepcopy
from importlib import import_module
import math
import pytest

from gene_annotation_episode.protein_structure_calculations import (
    calculate_protein_structure_components, resolve_pair_selection, fit_ca_transform, validate_declared_transform,
)

f = import_module("verification.tool_graders_protein_structure_calculations_2026-10-27_389.fixture_helpers")
a = f.a


def calculate(sheet, parameters=None):
    return calculate_protein_structure_components(sheet, parameters=parameters or sheet["native_request"])


def test_insertion_codes_disjoint_numbering_and_retained_traceback():
    sheet = f.make_sheet(retained=True)
    result = calculate(sheet)
    assert result["counts"]["mapped_pair_count"]["value"] == 4
    assert result["counts"]["available_pair_count"]["value"] == 4
    assert result["fit"]["state"] == "performed"
    assert result["fit"]["fit_rmsd"]["value"] == pytest.approx(0, abs=1e-7)
    assert result["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(0, abs=1e-14)
    for actual, expected in zip(result["transform"]["rotation"]["value"], [[1, 0, 0], [0, 1, 0], [0, 0, 1]]):
        assert actual == pytest.approx(expected, abs=1e-14)
    assert result["transform"]["translation"]["value"] == pytest.approx([0, 0, 0], abs=1e-14)
    assert sheet["sequences"]["fixed"]["residues"][0]["position_key"]["residue_number"] == 10
    assert sheet["sequences"]["fixed"]["residues"][1]["position_key"]["insertion_code"] == "A"
    assert [pair["correspondence_id"] for pair in sheet["coordinate_pairs"]] == [f"column_{i}" for i in range(4)]


def test_supplied_row_vector_orientation_and_no_fit_statistics():
    fixed = a.fixture_pdb(coordinates=[[3, -2, 5], [3, -1, 5], [2, -2, 5], [3, -2, 6]])
    sheet = f.make_sheet(fixed=fixed)
    parameters = f.declared_parameters(sheet, rotation=[[0, 1, 0], [-1, 0, 0], [0, 0, 1]], translation=[3, -2, 5])
    result = calculate(sheet, parameters)
    assert result["evaluation"]["evaluation_sse"]["value"] == 0
    assert result["evaluation"]["evaluation_rmsd"]["value"] == 0
    assert result["fit"]["fit_rmsd"] == {"value": None, "state": "not_applicable", "reason": "mode_not_applicable", "unit": "angstrom", "origin": "fitted"}
    assert result["counts"]["fit_used_count"]["state"] == "not_applicable"
    assert result["transform"]["rotation"]["value"] == parameters["declared_transform"]["rotation"]
    parameters["declared_transform"]["rotation"] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    assert calculate(sheet, parameters)["evaluation"]["evaluation_sse"]["value"] == 8


def test_held_out_fifth_site_does_not_refit_when_evaluation_changes(tmp_path):
    fixed = a.fixture_pdb("AGSTV", coordinates=f.TETRAHEDRON + [[1, 1, 1]])
    moving = a.fixture_pdb("AGSTV", role="moving", chain="B", coordinates=f.TETRAHEDRON + [[1, 1, 3]])
    parameters = a.fit_parameters()
    parameters["fit_selection"] = {"kind": "explicit", "members": [{"kind": "correspondence_id", "correspondence_id": f"map_{i}"} for i in range(4)]}
    parameters["evaluation_selection"] = {"kind": "explicit", "members": [{"kind": "sequence_position", "structure_role": "moving", "position_0based": 4}]}
    sheet = f.make_sheet(fixed, moving, parameters=parameters)
    first = calculate(sheet)
    assert first["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert first["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(2)
    assert not first["site_measurements"][0]["in_fit"]
    parameters["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    parameters["distance_threshold_A"] = 2
    second = calculate(sheet, parameters)
    assert second["fit"] == first["fit"]
    assert second["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert second["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5))
    assert second["evaluation"]["evaluation_mean_distance"]["value"] == pytest.approx(0.4)
    assert second["evaluation"]["above_threshold_count"]["value"] == 0
    parameters["distance_threshold_A"] = 1.5
    third = calculate(sheet, parameters)
    assert third["evaluation"]["above_threshold_count"]["value"] == 1
    assert third["evaluation"]["above_threshold_fraction"]["value"] == 1 / 5
    from gene_annotation_episode.execution_contracts import canonical
    (tmp_path / "held_out_original_sheet.json").write_text(canonical(sheet))
    (tmp_path / "held_out_components.json").write_text(canonical({"one": first, "all": second, "threshold_1_5": third}))


@pytest.mark.parametrize("coordinates", [[[0, 0, 0]], [[0, 0, 0], [1, 0, 0]], [[0, 0, 0], [1, 0, 0], [2, 0, 0]]])
def test_nonunique_fits_return_minimum_only(coordinates):
    sequence = "AGS"[:len(coordinates)]
    sheet = f.make_sheet(a.fixture_pdb(sequence, coordinates=coordinates),
        a.fixture_pdb(sequence, role="moving", chain="B", coordinates=coordinates))
    result = calculate(sheet)
    assert result["fit"]["state"] == "minimum_only"
    assert result["fit"]["fit_rmsd"]["value"] == pytest.approx(0)
    assert result["transform"]["rotation"]["value"] is None
    assert result["transform"]["translation"]["value"] is None
    assert result["counts"]["fit_used_count"]["value"] == len(coordinates)
    assert result["counts"]["evaluation_used_count"]["value"] == 0
    assert all(row["distance"]["value"] is None for row in result["site_measurements"])


@pytest.mark.parametrize("rotation", [[[-1, 0, 0], [0, 1, 0], [0, 0, 1]], [[2, 0, 0], [0, 1, 0], [0, 0, 1]]])
def test_supplied_reflection_and_scale_are_invalid_without_repair(rotation):
    sheet = f.make_sheet()
    parameters = f.declared_parameters(sheet, rotation=rotation)
    result = calculate(sheet, parameters)
    assert result["state"] == "invalid"
    assert result["transform"]["rotation"]["value"] is None
    assert parameters["declared_transform"]["rotation"] == rotation


def test_duplicate_alias_to_one_pair_and_nonexistent_references_reject():
    sheet = f.make_sheet()
    for members, code in [
        ([{"kind": "correspondence_id", "correspondence_id": "map_0"}, {"kind": "sequence_position", "structure_role": "moving", "position_0based": 0}], "duplicate_selection"),
        ([{"kind": "correspondence_id", "correspondence_id": "map_40"}], "map_endpoint_missing"),
        ([{"kind": "sequence_position", "structure_role": "moving", "position_0based": 40}], "map_endpoint_missing")]:
        with pytest.raises(ValueError, match=code):
            resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection={"kind": "explicit", "members": members})


def test_known_rotation_is_fitted_in_the_correct_direction():
    fixed = a.fixture_pdb(coordinates=[[3, -2, 5], [3, -1, 5], [2, -2, 5], [3, -2, 6]])
    result = calculate(f.make_sheet(fixed=fixed))
    for actual, expected in zip(result["transform"]["rotation"]["value"], [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]):
        assert actual == pytest.approx(expected, abs=1e-14)
    assert result["transform"]["translation"]["value"] == pytest.approx([3, -2, 5])
    assert result["evaluation"]["evaluation_sse"]["value"] == pytest.approx(0, abs=1e-25)


def test_missing_ca_preserves_correct_denominators_and_require_all_partition(tmp_path):
    fixed = f.cif_case(f.TETRAHEDRON + [[2, 2, 2]], missing=(0,))
    moving = f.cif_case(f.TETRAHEDRON + [[2, 2, 2], [4, 4, 4]], role="moving")
    sheet = f.make_sheet(fixed, moving, pairs=[(i, i) for i in range(4)])
    result = calculate(sheet)
    assert {name: result["counts"][name]["value"] for name in ("fixed_sequence_length", "moving_sequence_length", "mapped_pair_count", "available_pair_count")} == {
        "fixed_sequence_length": 5, "moving_sequence_length": 6, "mapped_pair_count": 4, "available_pair_count": 3}
    expected = {"fixed_correspondence_coverage": 4/5, "moving_correspondence_coverage": 4/6,
        "fixed_paired_coordinate_coverage": 3/5, "moving_paired_coordinate_coverage": 3/6,
        "mapped_pair_coordinate_coverage": 3/4, "fixed_coordinate_coverage": 4/5, "moving_coordinate_coverage": 1}
    for name, value in expected.items():
        assert result["coverage"][name]["value"] == value
    assert [result["counts"]["fit_" + n]["value"] for n in ("requested_count", "resolved_pair_count", "available_candidate_count", "used_count", "excluded_count")] == [4, 4, 3, 0, 4]
    assert [row["reason"] for row in result["fit"]["excluded"]] == ["ca_missing", "policy_requires_all", "policy_requires_all", "policy_requires_all"]
    parameters = deepcopy(sheet["native_request"])
    parameters["missing_coordinate_policy"] = "use_available"
    subset = calculate(sheet, parameters)
    assert subset["counts"]["fit_used_count"]["value"] == 3
    assert subset["fit"]["state"] == "performed"
    assert subset["site_measurements"][0]["distance"]["value"] is None
    assert subset["site_measurements"][0]["distance"]["reason"] == "ca_missing"
    assert subset["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(0, abs=1e-14)
    assert subset["coverage"]["evaluation_coverage"]["value"] == 3/4
    assert subset["state"] == "partial"
    from gene_annotation_episode.execution_contracts import canonical
    (tmp_path / "missing_ca_require_all.json").write_text(canonical(result))
    (tmp_path / "missing_ca_use_available.json").write_text(canonical(subset))


def test_reflection_tie_preserves_minimum_and_withholds_arbitrary_svd_orientation():
    h = math.sqrt(0.5)
    fixed = f.cif_case([[1, 0, 0], [-1, 0, 0], [0, h, 0], [0, -h, 0], [0, 0, h], [0, 0, -h]])
    moving = f.cif_case([[-1, 0, 0], [1, 0, 0], [0, h, 0], [0, -h, 0], [0, 0, h], [0, 0, -h]], role="moving")
    result = calculate(f.make_sheet(fixed, moving))
    assert result["fit"]["singular_values"]["value"] == pytest.approx([2, 1, 1])
    assert result["fit"]["cross_covariance_rank"]["value"] == 3
    assert result["fit"]["reflection_correction_sign"]["value"] == -1
    assert result["fit"]["fit_sse"]["value"] == pytest.approx(4)
    assert result["fit"]["fit_rmsd"]["value"] == pytest.approx(math.sqrt(2/3))
    assert result["fit"]["state"] == "minimum_only"
    assert result["transform"]["rotation"]["value"] is None
    assert all(row["primary_reason"] == "transform_unavailable" for row in result["site_measurements"])


def test_explicit_alternate_selection_not_maximum_occupancy():
    raw = (a.atom_line(serial=1, alt="A", occupancy="0.60", xyz=[0, 0, 0]) +
           a.atom_line(serial=2, alt="B", occupancy="0.40", xyz=[0, 0, 2])).encode()
    fixed = a.fixture_pdb("A", coordinates=[[0, 0, 0]])
    ambiguous = f.from_pdb(raw, "moving")
    sheet = f.make_sheet(fixed, ambiguous)
    result = calculate(sheet, f.declared_parameters(sheet))
    assert result["site_measurements"][0]["primary_reason"] == "ambiguous_ca"
    for index, distance in ((0, 0), (1, 2)):
        def select(parsed, selection):
            identity = parsed["atoms"][index]["identity"]
            selection["ca_selection"] = {"policy": "explicit_atom_rows", "choices": [{
                "position_key": identity["residue"]["position_key"], "atom_row_key": identity["atom_row_key"]}]}
            return selection
        moving = f.from_pdb(raw, "moving", select=select)
        sheet = f.make_sheet(fixed, moving)
        result = calculate(sheet, f.declared_parameters(sheet))
        assert result["site_measurements"][0]["distance"]["value"] == distance
        assert len(sheet["structures"]["moving"]["atoms"]) == 2


def test_full_precision_missing_declared_positions_and_coordinate_outputs():
    fixed = f.cif_case([[0.123456789012345, 0, 0], [0, 0, 0], [0, 1, 0]], labels=[2, 4, 7], missing=(1,))
    moving = f.cif_case([[0.123456789012345, 0, 2], [0, 0, 0], [0, 1, 0]], role="moving", labels=[2, 4, 7], missing=(1,))
    sheet = f.make_sheet(fixed, moving)
    parameters = f.declared_parameters(sheet)
    parameters["missing_coordinate_policy"] = "use_available"
    parameters["coordinate_sets"] = [{"coordinate_set_id": "selected-ca", "structure_role": "moving",
        "members": {"kind": "sequence_positions", "positions": [2, 1, 0]}, "atom_scope": "selected_ca", "frame": "original"}]
    original = deepcopy(sheet)
    result = calculate(sheet, parameters)
    assert [row["sequence_position_0based"] for row in result["coordinate_sets"][0]["rows"]] == [2, 1, 0]
    assert result["coordinate_sets"][0]["rows"][2]["xyz"]["value"][0] == 0.123456789012345
    missing = result["coordinate_sets"][0]["rows"][1]
    assert missing["xyz"]["value"] is None and missing["declared_residue_identity"]["label_seq_id"] == 4
    assert result["counts"]["fixed_sequence_length"]["value"] == 3
    assert result["site_measurements"][0]["distance"]["value"] == 2
    assert sheet == original


def test_all_atom_output_keeps_alternatives_ligands_original_order_and_selected_boundaries():
    raw = (a.atom_line(serial=1, atom=" N  ", element="N", xyz=[2, 0, 0]) +
        a.atom_line(serial=2, alt="A", occupancy="0.6", xyz=[0, 0, 0]) +
        a.atom_line(serial=3, alt="B", occupancy="0.4", xyz=[0, 0, 2]) +
        a.atom_line(serial=4, component="LIG", number=50, record="HETATM", xyz=[9, 8, 7]) +
        a.atom_line(serial=5, component="GLY", number=11, xyz=[1, 1, 1]) +
        a.atom_line(serial=6, chain="C", number=40, xyz=[8, 8, 8])).encode()
    moving = f.from_pdb(raw, "moving")
    fixed = a.fixture_pdb("AG", coordinates=[[0, 0, 0], [1, 1, 1]])
    sheet = f.make_sheet(fixed, moving)
    parameters = f.declared_parameters(sheet, translation=[3, -2, 5])
    parameters["coordinate_sets"] = [
        {"coordinate_set_id": "all-original", "structure_role": "moving", "members": {"kind": "all_selected_chain"}, "atom_scope": "selected_chain_all_atoms", "frame": "original"},
        {"coordinate_set_id": "position0-transformed", "structure_role": "moving", "members": {"kind": "sequence_positions", "positions": [0]}, "atom_scope": "selected_chain_all_atoms", "frame": "moving_in_fixed_frame"}]
    result = calculate(sheet, parameters)
    original, transformed = result["coordinate_sets"]
    assert [r["atom_row_key"] for r in original["rows"]] == [f"pdb_line_{i}" for i in range(1, 6)]
    assert original["rows"][3]["sequence_position_0based"] is None
    assert [r["xyz"]["value"] for r in transformed["rows"]] == [[5, -2, 5], [3, -2, 5], [3, -2, 7]]
    assert [r["atom_row_key"] for r in transformed["rows"]] == [f"pdb_line_{i}" for i in range(1, 4)]
    assert original["rows"][0]["xyz"]["value"] == [2, 0, 0]
    assert sheet["structures"]["moving"]["atoms"][0]["xyz_A"][0]["value"] == 2


def test_empty_explicit_map_has_measured_zero_pairs_without_invented_fit():
    result = calculate(f.make_sheet(pairs=[]))
    assert result["counts"]["mapped_pair_count"]["value"] == 0
    assert result["counts"]["available_pair_count"]["value"] == 0
    assert result["coverage"]["fixed_correspondence_coverage"]["value"] == 0
    assert result["coverage"]["mapped_pair_coordinate_coverage"]["reason"] == "zero_denominator"
    assert result["coverage"]["fit_coverage"]["reason"] == "zero_denominator"
    assert result["fit"]["fit_sse"]["value"] is None
    assert result["site_measurements"] == []


def test_empty_explicit_map_over_known_zero_length_side_has_zero_pairs():
    fixed = f.from_pdb(a.atom_line(component="LIG", record="HETATM").encode(), "fixed")
    assert fixed[2]["sequence_length"] == 0 and not fixed[2]["sequence_available"]
    sheet = f.make_sheet(fixed=fixed, pairs=[])
    result = calculate(sheet)
    assert result["counts"]["mapped_pair_count"]["value"] == 0
    assert result["counts"]["available_pair_count"]["value"] == 0
    assert result["coverage"]["fixed_correspondence_coverage"]["reason"] == "zero_denominator"
    assert result["coverage"]["moving_correspondence_coverage"]["value"] == 0
    assert result["counts"]["fixed_unmapped_count"]["value"] == 0
    assert result["counts"]["moving_unmapped_count"]["value"] == 4


def test_finite_input_overflow_is_an_explicit_invalid_calculation():
    xyz = [[1e308, 0, 0], [-1e308, 0, 0], [0, 1e308, 0], [0, 0, 1e308]]
    sheet = f.make_sheet(f.cif_case(xyz), f.cif_case(xyz, role="moving"))
    result = calculate(sheet)
    assert result["fit"]["state"] == "invalid" and result["state"] == "invalid"
    assert result["fit"]["fit_rmsd"]["value"] is None
    assert result["fit"]["issues"][0]["code"] == "numeric_inconsistency"
    from gene_annotation_episode.execution_contracts import canonical
    assert "Infinity" not in canonical(result) and "NaN" not in canonical(result)


@pytest.mark.parametrize("field,value", [("svd_relative_tolerance", float("nan")), ("rotation_orthogonality_tolerance", -1), ("geometry_absolute_tolerance_A", True)])
def test_nonfinite_negative_and_boolean_tolerances_reject(field, value):
    sheet = f.make_sheet()
    parameters = deepcopy(sheet["native_request"])
    parameters["numerical"][field] = value
    with pytest.raises(ValueError, match="invalid_schema"):
        calculate(sheet, parameters)


def test_explicit_zero_tolerance_exposes_numerical_inconsistency():
    sheet = f.make_sheet()
    parameters = deepcopy(sheet["native_request"])
    parameters["numerical"]["sse_roundoff_absolute_tolerance_A2"] = 0
    parameters["numerical"]["sse_roundoff_relative_tolerance"] = 0
    result = calculate(sheet, parameters)
    assert result["fit"]["state"] == "invalid"
    assert result["fit"]["fit_sse_roundoff_limit"]["value"] == 0
    assert result["fit"]["fit_sse_raw_formula"]["value"] is not None


def test_fitted_rotation_respects_explicit_orthogonality_tolerances():
    sheet = f.make_sheet()
    parameters = deepcopy(sheet["native_request"])
    parameters["numerical"]["rotation_orthogonality_tolerance"] = 0
    parameters["numerical"]["rotation_determinant_tolerance"] = 0
    result = calculate(sheet, parameters)
    assert result["fit"]["state"] == "invalid"
    assert result["transform"]["rotation"]["value"] is None
    assert result["fit"]["fit_sse_raw_formula"]["value"] is not None


@pytest.mark.parametrize("orientation", ["fixed_is_query", "fixed_is_reference"])
def test_retained_alignment_gap_counts_keep_structure_roles(orientation):
    fixed = a.fixture_pdb()
    moving = a.fixture_pdb("AGS", role="moving", chain="B", coordinates=f.TETRAHEDRON[:3])
    sheet = f.make_sheet(fixed, moving, retained=True, orientation=orientation)
    result = calculate(sheet)
    assert result["alignment"]["alignment_column_count"]["value"] == 4
    assert result["alignment"]["alignment_identity_count"]["value"] == 3
    assert result["alignment"]["alignment_fixed_gap_count"]["value"] == 0
    assert result["alignment"]["alignment_moving_gap_count"]["value"] == 1
    assert result["counts"]["fixed_unmapped_count"]["value"] == 1
    assert result["counts"]["moving_unmapped_count"]["value"] == 0


def test_local_unmapped_requested_site_survives_as_an_excluded_request():
    fixed = a.fixture_pdb("WAGSTW", coordinates=[[9, 9, 9]] + f.TETRAHEDRON + [[20, 20, 20]])
    sheet = f.make_sheet(fixed=fixed, retained=True, alignment_mode="local")
    parameters = deepcopy(sheet["native_request"])
    parameters["evaluation_selection"] = {"kind": "explicit", "members": [
        {"kind": "sequence_position", "structure_role": "fixed", "position_0based": 0},
        {"kind": "sequence_position", "structure_role": "moving", "position_0based": 2}]}
    parameters["missing_coordinate_policy"] = "use_available"
    result = calculate(sheet, parameters)
    assert result["coverage"]["fixed_correspondence_coverage"]["value"] == 4/6
    assert result["counts"]["fixed_unmapped_count"]["value"] == 2
    assert result["counts"]["evaluation_requested_count"]["value"] == 2
    assert result["counts"]["evaluation_resolved_pair_count"]["value"] == 1
    first = result["site_measurements"][0]
    assert first["fixed_position_0based"] == 0 and first["correspondence_id"] is None
    assert first["primary_reason"] == "unmapped_site" and first["distance"]["value"] is None


@pytest.mark.parametrize("occupancy,policy,expected", [("", "exclude", None), ("0.00", "exclude", "zero_occupancy_excluded"),
    ("0.00", "include", None), ("1.20", "include", "invalid_occupancy")])
def test_occupancy_is_an_explicit_coordinate_policy_not_a_fit_weight(occupancy, policy, expected):
    raw = a.atom_line(occupancy=occupancy).encode()
    moving = f.from_pdb(raw, "moving", select=lambda parsed, selected: {**selected, "zero_occupancy_policy": policy})
    fixed = a.fixture_pdb("A", coordinates=[[0, 0, 0]])
    sheet = f.make_sheet(fixed, moving)
    result = calculate(sheet, f.declared_parameters(sheet))
    site = result["site_measurements"][0]
    assert site["primary_reason"] == expected
    assert site["distance"]["value"] == (0 if expected is None else None)
    if occupancy == "":
        assert "occupancy_not_reported" in site["qualifications"]


def test_missing_reason_precedence_is_by_reason_then_side():
    fixed = a.fixture_pdb("A", coordinates=[[0, 0, 0]])
    moving = f.from_pdb(a.atom_line(atom=" N  ", element="N").encode(), "moving")
    sheet = f.make_sheet(fixed, moving)
    # Independently missing fixed identity takes precedence over a missing CA
    # only in explicitly supplied CoordinatePair records at the numeric port.
    pairs = deepcopy(sheet["coordinate_pairs"])
    pairs[0]["fixed_ca_state"].update(state="invalid", primary_reason="invalid_coordinate_identity")
    pairs[0]["fixed_xyz_A"].update(value=None, state="invalid", reason="invalid_coordinate_identity")
    corr = deepcopy(sheet["correspondence"])
    corr["rows"][0]["fixed_ca"] = deepcopy(pairs[0]["fixed_ca_state"])
    resolved = resolve_pair_selection(corr, pairs, selection={"kind": "all_mapped_pairs"})
    assert resolved["rows"][0]["primary_reason"] == "invalid_coordinate_identity"


def test_all_atom_mmcif_join_uses_physical_position_not_ca_token_spans():
    extra = "ATOM 9 N N . ALA X 1 1 A 100 ALA N . 9.123456789012345 0 0 1 20 5\n"
    moving = f.cif_case(f.TETRAHEDRON, role="moving", extra=extra)
    sheet = f.make_sheet(moving=moving)
    parameters = f.declared_parameters(sheet)
    parameters["coordinate_sets"] = [{"coordinate_set_id": "same-residue-atoms", "structure_role": "moving",
        "members": {"kind": "sequence_positions", "positions": [0]}, "atom_scope": "selected_chain_all_atoms", "frame": "original"}]
    result = calculate(sheet, parameters)
    rows = result["coordinate_sets"][0]["rows"]
    assert len(rows) == 2 and [row["sequence_position_0based"] for row in rows] == [0, 0]
    assert rows[1]["xyz"]["value"][0] == 9.123456789012345
    assert rows[0]["residue_identity"]["label_seq_id"]["span"] != rows[1]["residue_identity"]["label_seq_id"]["span"]


def test_supplied_transform_can_evaluate_a_single_pair_without_fitting():
    fixed = a.fixture_pdb("A", coordinates=[[0, 0, 0]])
    moving = a.fixture_pdb("A", role="moving", chain="B", coordinates=[[1, 2, 2]])
    sheet = f.make_sheet(fixed, moving)
    result = calculate(sheet, f.declared_parameters(sheet))
    assert result["evaluation"]["evaluation_rmsd"]["value"] == 3
    assert result["evaluation"]["evaluation_sse"]["value"] == 9
    assert result["fit"]["state"] == "not_applicable"


def test_public_fit_rejects_forged_selector_and_coordinate_state_relationships():
    sheet = f.make_sheet()
    selection = {"kind": "explicit", "members": [{"kind": "sequence_position", "structure_role": "fixed", "position_0based": 0}]}
    request = resolve_pair_selection(sheet["correspondence"], sheet["coordinate_pairs"], selection=selection)
    request["selection"]["members"][0]["position_0based"] = 1
    request["rows"][0]["selector"]["position_0based"] = 1
    with pytest.raises(ValueError, match="conflicting_identity"):
        fit_ca_transform(sheet["coordinate_pairs"], fit_request=request, missing_coordinate_policy="use_available", numerical_parameters=a.numerical_parameters())
    pairs = deepcopy(sheet["coordinate_pairs"])
    pairs[0]["moving_xyz_A"].update(value=None, state="unavailable", reason="ca_missing")
    with pytest.raises(ValueError, match="invalid_coordinate_identity"):
        resolve_pair_selection(sheet["correspondence"], pairs, selection={"kind": "all_mapped_pairs"})


def test_roundoff_clamp_has_an_explicit_limit_and_does_not_round_positive_values(tmp_path):
    cases = []
    for xyz in ([[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                 [[0, 0, 0], [3, 0, 0], [0, 2, 0]], f.TETRAHEDRON):
        sequence = "AGST"[:len(xyz)]
        result = calculate(f.make_sheet(a.fixture_pdb(sequence, coordinates=xyz), a.fixture_pdb(sequence, role="moving", chain="B", coordinates=xyz)))
        fit = result["fit"]
        assert fit["fit_rmsd"]["value"] == pytest.approx(0, abs=1e-7)
        raw, limit = fit["fit_sse_raw_formula"]["value"], fit["fit_sse_roundoff_limit"]["value"]
        if raw < 0:
            assert -raw <= limit and fit["fit_sse"]["value"] == 0
            assert "numerical_roundoff_clamp" in fit["qualifications"]
        else:
            assert fit["fit_sse"]["value"] == raw
        cases.append({"coordinates": xyz, "raw_sse": raw, "limit": limit, "fit_sse": fit["fit_sse"]["value"]})
    assert any(row["raw_sse"] < 0 for row in cases)
    from gene_annotation_episode.execution_contracts import canonical
    (tmp_path / "roundoff_examples.json").write_text(canonical(cases))
