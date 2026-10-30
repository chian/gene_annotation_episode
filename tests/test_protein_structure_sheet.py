"""Input-sheet integrity, original native baselines, and pure recalculation."""
from copy import deepcopy
from importlib import import_module
import pytest
from gene_annotation_episode.protein_structure_sheet import build_protein_structure_sheet
from gene_annotation_episode.protein_structure_sheet import parse_native_protein_comparison
from gene_annotation_episode.protein_structure_calculations import (
    calculate_protein_structure_components, validate_recorded_protein_structure_components,
)

f = import_module("verification.tool_graders_protein_structure_calculations_2026-10-27_389.fixture_helpers")


def test_builder_preserves_detached_native_coordinates_and_metadata():
    sheet = f.make_sheet()
    original = deepcopy(sheet)
    sheet["coordinate_pairs"][0]["fixed_xyz_A"]["value"][0] = 99
    assert sheet["structures"]["fixed"]["atoms"][0]["xyz_A"][0]["value"] == 0
    assert original["native_uncertainty"]["fixed"]["atom_uncertainty"][0]["b_factor_native"]["value"] == 20


def test_forged_same_length_map_is_not_a_valid_sheet():
    fixed, moving = f.a.fixture_pdb(), f.a.fixture_pdb(role="moving", chain="B")
    _, file, corr = f.a.explicit_map(fixed[2], moving[2])
    forged = deepcopy(fixed[2])
    forged["residues"][0]["ca"]["selected_atom_row_key"] = forged["residues"][1]["ca"]["selected_atom_row_key"]
    with pytest.raises(ValueError):
        build_protein_structure_sheet(fixed=fixed[1], moving=moving[1], fixed_sequence=forged, moving_sequence=moving[2],
            correspondence=corr, correspondence_input={"kind": "explicit_map", "map_file": file},
            fixed_metadata=fixed[3], moving_metadata=moving[3], native_request=f.a.fit_parameters(), native_baseline=None)


def test_native_parser_preserves_original_baseline_without_refitting(monkeypatch):
    import numpy as np
    native = f.synthetic_native(f.make_sheet())
    original = deepcopy(native)
    def forbidden(*args, **kwargs):
        raise AssertionError("native parsing must not refit")
    monkeypatch.setattr(np.linalg, "svd", forbidden)
    result = parse_native_protein_comparison(native, expected_request=native["request"])
    assert result == original["sheet"] and native == original
    result["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] = 99
    assert native == original


@pytest.mark.parametrize("location", ["fit_rmsd", "spectrum", "evaluation", "count", "hash"])
def test_native_parser_rejects_inconsistent_saved_numbers(location):
    native = f.synthetic_native(f.make_sheet())
    baseline = native["sheet"]["native_baseline"]
    if location == "fit_rmsd":
        baseline["fit"]["fit_rmsd"]["value"] = 9
    elif location == "spectrum":
        baseline["fit"]["singular_values"]["value"][0] = 9
    elif location == "evaluation":
        baseline["site_measurements"][0]["distance"]["value"] = 9
    elif location == "count":
        baseline["counts"]["available_pair_count"]["value"] = 1
    else:
        baseline["input_numerical_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        parse_native_protein_comparison(native, expected_request=native["request"])


def test_native_parser_exact_request_and_null_sheet_failure():
    native = f.synthetic_native(f.make_sheet())
    changed = deepcopy(native["request"])
    changed["parameters"]["distance_threshold_A"] = 2
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        parse_native_protein_comparison(native, expected_request=changed)
    from gene_annotation_episode.protein_structure_contracts import issue
    native.update(sheet=None, state="unavailable", issues=[issue("native_process_failed", stage="native", field="returncode")])
    assert parse_native_protein_comparison(native, expected_request=native["request"]) is None
    native["issues"] = []
    with pytest.raises(ValueError):
        parse_native_protein_comparison(native, expected_request=native["request"])


def test_saved_sheet_recalculation_is_pure_and_never_changes_original(monkeypatch):
    import builtins
    import pathlib
    import socket
    import subprocess
    from gene_annotation_episode import sequence_ops
    native = f.synthetic_native(f.make_sheet())
    saved = parse_native_protein_comparison(native, expected_request=native["request"])
    original = deepcopy(saved)
    parameters = deepcopy(saved["native_request"])
    parameters["distance_threshold_A"] = 1.5
    def forbidden(*args, **kwargs):
        raise AssertionError("saved-sheet calculation attempted I/O or native analysis")
    for module, name in ((builtins, "open"), (pathlib.Path, "open"), (socket, "socket"), (subprocess, "Popen"), (sequence_ops, "align_pair")):
        monkeypatch.setattr(module, name, forbidden)
    changed = calculate_protein_structure_components(saved, parameters=parameters)
    assert saved == original
    assert changed["calculation_id"] != saved["native_baseline"]["calculation_id"]
    assert changed["input_numerical_sha256"] == saved["native_baseline"]["input_numerical_sha256"]
    assert changed["fit"] == saved["native_baseline"]["fit"]


def test_unknown_traceback_population_never_becomes_no_alignment():
    sheet = f.make_sheet(retained=True)
    corr = deepcopy(sheet["correspondence"])
    from gene_annotation_episode.protein_structure_contracts import issue
    corr.update(state="invalid", population_available=False, alignment_native=None, rows=[], unmapped_fixed=[], unmapped_moving=[],
        issues=[issue("invalid_traceback", stage="correspondence", field="traceback")])
    invalid = f.rebuild_sheet(sheet, correspondence=corr)
    result = calculate_protein_structure_components(invalid, parameters=invalid["native_request"])
    assert result["counts"]["mapped_pair_count"]["value"] is None
    assert result["counts"]["mapped_pair_count"]["reason"] == "invalid_traceback"
    assert result["counts"]["fit_requested_count"]["value"] is None
    assert result["counts"]["fit_used_count"]["value"] == 0
    assert result["counts"]["fit_excluded_count"]["value"] is None
    params = deepcopy(invalid["native_request"])
    params["evaluation_selection"] = {"kind": "explicit", "members": [{"kind": "sequence_position", "structure_role": "fixed", "position_0based": 0}]}
    result = calculate_protein_structure_components(invalid, parameters=params)
    assert result["counts"]["evaluation_requested_count"]["value"] == 1
    assert result["counts"]["evaluation_resolved_pair_count"]["value"] is None
    assert result["counts"]["evaluation_excluded_count"]["value"] == 1


def test_genuine_native_no_alignment_has_zero_pair_population_and_native_missing_score():
    from gene_annotation_episode.biopython_pairwise_grader import build_biopython_pairwise_sheet
    from gene_annotation_episode.protein_structure_correspondence import correspondence_from_pairwise_sheet
    from gene_annotation_episode.execution_contracts import canonical
    sheet = f.make_sheet(retained=True)
    source = deepcopy(sheet["input_identities"]["correspondence"])
    native = {"aligned": False, "query_length": 4, "reference_length": 4, "mode": "global", "matrix": "BLOSUM62", "biopython_version": "synthetic"}
    pairwise = build_biopython_pairwise_sheet(native, molecule="protein")
    source["alignment"]["native_file"] = f.a.identity(canonical(native).encode(), "biopython_pairwise_json")
    source["alignment"]["grading_file"] = f.a.identity(canonical(pairwise).encode(), "tool_grading_artifact_v1")
    corr = correspondence_from_pairwise_sheet(pairwise, native=native, alignment=source["alignment"],
        fixed=sheet["sequences"]["fixed"], moving=sheet["sequences"]["moving"],
        fixed_descriptor=source["fixed_sequence_descriptor"], moving_descriptor=source["moving_sequence_descriptor"],
        orientation=source["orientation"])
    sheet = f.rebuild_sheet(sheet, correspondence=corr, correspondence_input=source)
    result = calculate_protein_structure_components(sheet, parameters=sheet["native_request"])
    assert result["counts"]["mapped_pair_count"] == {"value": 0, "state": "present", "reason": None, "unit": "pair", "origin": "derived"}
    assert result["alignment"]["alignment_column_count"]["value"] == 0
    assert result["alignment"]["alignment_score"]["value"] is None
    assert result["alignment"]["alignment_score"]["reason"] == "no_alignment"


def test_native_confidence_is_unchanged_and_never_weights_the_fit(tmp_path):
    symbols, bvalues = "AGSTV", [1, 10, 30, 90, 99]
    xyz = f.TETRAHEDRON + [[1, 1, 1]]
    moving_xyz = f.TETRAHEDRON + [[1, 1, 3]]
    def raw(points, role, chain):
        return f.from_pdb("".join(f.a.atom_line(serial=i + 1, component=f.a.COMPONENTS[s], chain=chain, number=i + 1,
            xyz=point, b=str(b)) for i, (s, point, b) in enumerate(zip(symbols, points, bvalues))).encode(), role)
    fixed, moving = raw(xyz, "fixed", "A"), raw(moving_xyz, "moving", "B")
    plain = f.make_sheet(fixed, moving)
    documented = f.make_sheet(f.with_semantics(fixed, "declared_plddt"), f.with_semantics(moving, "declared_plddt"))
    before = deepcopy(documented["native_uncertainty"])
    first = calculate_protein_structure_components(plain, parameters=plain["native_request"])
    second = calculate_protein_structure_components(documented, parameters=documented["native_request"])
    assert first["fit"] == second["fit"]
    assert second["fit"]["fixed_centroid"]["value"] == pytest.approx([0.4, 0.4, 0.4])
    assert second["fit"]["moving_centroid"]["value"] == pytest.approx([0.4, 0.4, 0.8])
    assert [row["plddt"]["value"] for row in documented["native_uncertainty"]["fixed"]["atom_uncertainty"]] == bvalues
    assert all(row["physical_b_A2"]["state"] == "not_applicable" for row in before["fixed"]["atom_uncertainty"])
    assert documented["native_uncertainty"] == before
    assert "uncertainty_not_used_as_weight" in second["qualifications"]
    physical = f.with_semantics(f.a.fixture_pdb(b="20.00"), "native_atomic_displacement")
    assert physical[3]["atom_uncertainty"][0]["physical_b_A2"]["value"] == 20
    assert physical[3]["atom_uncertainty"][0]["plddt"]["value"] is None
    from gene_annotation_episode.execution_contracts import canonical
    (tmp_path / "native_confidence_preserved.json").write_text(canonical({"sheet": documented, "components": second}))


@pytest.mark.parametrize("case", ["minimum", "missing", "empty", "supplied", "overflow"])
def test_native_parser_preserves_partial_zero_and_supplied_cases(case):
    if case == "minimum":
        sheet = f.make_sheet(f.a.fixture_pdb("A", coordinates=[[0, 0, 0]]), f.a.fixture_pdb("A", role="moving", chain="B", coordinates=[[0, 0, 0]]))
    elif case == "missing":
        sheet = f.make_sheet(f.cif_case(f.TETRAHEDRON, missing=(0,)), f.cif_case(f.TETRAHEDRON, role="moving"))
    elif case == "empty":
        sheet = f.make_sheet(pairs=[])
    elif case == "overflow":
        coordinates = [[1e308, 0, 0], [-1e308, 0, 0], [0, 1e308, 0], [0, 0, 1e308]]
        sheet = f.make_sheet(f.cif_case(coordinates), f.cif_case(coordinates, role="moving"))
    else:
        original = f.make_sheet()
        sheet = f.rebuild_sheet(original, native_request=f.declared_parameters(original))
    native = f.synthetic_native(sheet)
    parsed = parse_native_protein_comparison(native, expected_request=native["request"])
    assert parsed == native["sheet"]


def test_builder_validates_original_baseline_and_uses_unicode_canonical_identity():
    from gene_annotation_episode.execution_contracts import digest
    native = f.synthetic_native(f.make_sheet(fixed=f.cif_case(f.TETRAHEDRON, extra="_note.description 'β input'\n")))
    rebuilt = f.rebuild_sheet(native["sheet"])
    assert rebuilt == native["sheet"]
    expected = digest({k: v for k, v in rebuilt.items() if k != "native_baseline"})
    assert rebuilt["native_baseline"]["input_numerical_sha256"] == expected
    tampered = deepcopy(rebuilt)
    tampered["native_baseline"]["fit"]["fit_rmsd"]["value"] = 5
    with pytest.raises(ValueError, match="numeric_inconsistency"):
        f.rebuild_sheet(tampered)


def test_recorded_later_components_validate_without_refit_calculator_or_io(monkeypatch):
    import builtins
    import numpy as np
    from gene_annotation_episode import protein_structure_calculations as calculations
    native = f.synthetic_native(f.make_sheet())
    saved = native["sheet"]
    parameters = deepcopy(saved["native_request"])
    parameters["distance_threshold_A"] = 1.5
    later = calculate_protein_structure_components(saved, parameters=parameters)
    originals = deepcopy((saved, later))
    def forbidden(*args, **kwargs):
        raise AssertionError("recorded component validation attempted a calculation or I/O")
    monkeypatch.setattr(np.linalg, "svd", forbidden)
    monkeypatch.setattr(calculations, "calculate_protein_structure_components", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    checked = validate_recorded_protein_structure_components(saved, components=later)
    assert checked == later and checked is not later and (saved, later) == originals
    checked["evaluation"]["evaluation_sse"]["value"] = 999
    assert later == originals[1]
    for field in ("evaluation", "input"):
        bad = deepcopy(later)
        if field == "evaluation":
            bad["evaluation"]["evaluation_rmsd"]["value"] = 7
        else:
            bad["input_numerical_sha256"] = "0" * 64
        with pytest.raises(ValueError):
            validate_recorded_protein_structure_components(saved, components=bad)


def test_invalid_traceback_does_not_relax_original_extraction_associations():
    from gene_annotation_episode.protein_structure_contracts import issue
    sheet = f.make_sheet(retained=True)
    corr = deepcopy(sheet["correspondence"])
    corr.update(state="invalid", population_available=False, alignment_native=None, rows=[], unmapped_fixed=[], unmapped_moving=[],
        issues=[issue("invalid_traceback", stage="correspondence", field="traceback")])
    source = deepcopy(sheet["input_identities"]["correspondence"])
    source["fixed_sequence_descriptor"]["selection"]["zero_occupancy_policy"] = "include"
    with pytest.raises(ValueError, match="sequence_artifact_mismatch"):
        f.rebuild_sheet(sheet, correspondence=corr, correspondence_input=source)


def test_recorded_component_qualifications_and_units_cannot_be_rewritten():
    native = f.synthetic_native(f.make_sheet())
    for path in ("qualifications", "unit"):
        altered = deepcopy(native)
        if path == "qualifications":
            altered["sheet"]["native_baseline"]["qualifications"] = []
        else:
            altered["sheet"]["native_baseline"]["site_measurements"][0]["distance"]["unit"] = "score_0_100"
        with pytest.raises(ValueError, match="numeric_inconsistency"):
            parse_native_protein_comparison(altered, expected_request=altered["request"])


def test_retained_filled_saved_sheet_and_later_calculations_are_consistent():
    import json
    from pathlib import Path
    directory = Path(f.__file__).parent / "examples"
    sheet = json.loads((directory / "held_out_saved_sheet.json").read_text())
    calculations = json.loads((directory / "held_out_components.json").read_text())
    original = deepcopy(sheet)
    for components in calculations.values():
        checked = validate_recorded_protein_structure_components(sheet, components=components)
        assert checked == components
    assert sheet == original and sheet["native_baseline"] == calculations["one"]
