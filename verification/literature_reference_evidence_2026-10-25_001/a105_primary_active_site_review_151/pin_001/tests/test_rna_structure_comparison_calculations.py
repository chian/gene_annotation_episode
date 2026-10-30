"""Hand-checkable invented arithmetic fixtures; no native execution."""
from copy import deepcopy
from fractions import Fraction
import importlib
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_comparison_calculations import (
    calculate_rna_comparison_components, calculate_rna_energy_comparison,
    calculate_rna_pair_changes, calculate_rna_site_changes, qualify_rna_energy_comparison,
)
from gene_annotation_episode.rna_structure_comparison_contracts import (
    ARRAY_SETTING_NAMES, MODEL_SETTING_NAMES, OTHER_SCALAR_SETTING_NAMES,
    validate_rna_comparison_components,
)
from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet

f = importlib.import_module("verification.tool_graders_rna_comparison_calculations_2026-10-26_367.fixture_helpers")


def calculated(sheet):
    result = calculate_rna_comparison_components(sheet)
    assert validate_rna_comparison_components(result, sheet=sheet) == result
    return result["comparisons"][0]


def test_example_1_unchanged_pairing_independent_energy():
    sheet = f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), energy=f.energy_request())
    result = calculated(sheet)
    site = f.values(result["components"], "selected")
    pairs = f.values(result["components"])
    energy = f.values(result["energy"]["components"])
    assert site["decidable_site_count"] == site["unchanged_site_count"] == 9
    assert site["changed_site_count"] == site["changed_site_fraction"] == 0
    assert pairs["preserved_pair_count"] == 3 and pairs["pair_symmetric_difference_count"] == 0
    assert energy["energy_delta"] == 1.0 and result["energy"]["order"] == "variant_higher"
    assert result["pairing_change_state"] == "unchanged_in_complete_correspondence"
    assert result["energy"]["compatibility"]["state"] == "compatible"
    assert all(s["state"] == "unavailable" for s in sheet["operands"][0]["original_sheet"]["model"]["other_observed_settings"] if s["name"] in ARRAY_SETTING_NAMES)


def test_example_2_reassigned_partner_counts_pairs_and_sites_separately():
    sheet = f.pair(f.feature(sequence="G" * 10, structure="((....)).."),
        f.feature("V", "G" * 10, ".((....))."), selections=[f.site(positions=[0, 1, 2, 6, 7, 8])])
    result = calculated(sheet)
    rows = {r["baseline_index"]: r for r in result["all_site_rows"]}
    assert {i for i, r in rows.items() if r["transition"] == "lost_pairing"} == {0, 6}
    assert {i for i, r in rows.items() if r["transition"] == "gained_pairing"} == {2, 8}
    assert {i for i, r in rows.items() if r["transition"] == "reassigned_partner"} == {1, 7}
    assert (rows[1]["baseline_partner"]["local_index"], rows[1]["variant_partner"]["local_index"]) == (6, 8)
    assert f.values(result["components"], "selected")["changed_site_fraction"] == 1
    assert f.values(result["components"])["pair_symmetric_difference_count"] == 4


def test_example_3_inserted_unpaired_site_preserves_pairing():
    sheet = f.pair(b=f.feature("V", "UGGGAAACCC", ".(((...)))"),
        correspondence=f.complete([(None, 0)] + [(i, i + 1) for i in range(9)]))
    result = calculated(sheet)
    assert result["all_site_rows"][0]["transition"] == "inserted_site"
    assert result["all_site_rows"][1]["variant_index"] == 1
    assert result["all_site_rows"][1]["variant_partner"]["local_index"] == 9
    assert f.values(result["components"])["alignment_inserted_nt"] == 1
    assert f.values(result["components"])["preserved_pair_count"] == 3
    assert result["pairing_change_state"] == "unchanged_in_complete_correspondence"


def test_example_4_deletion_changes_only_decidable_denominator():
    columns = [(i, i if i < 3 else None if i == 3 else i - 1) for i in range(9)]
    result = calculated(f.pair(b=f.feature("V", "GGGAACCC", "(((..)))"),
        correspondence=f.complete(columns), selections=[f.site(positions=[2, 3, 6])]))
    cells = f.cells(result["components"], "selected")
    assert (cells["requested_site_count"]["value"], cells["decidable_site_count"]["value"], cells["deleted_site_count"]["value"]) == (3, 2, 1)
    assert cells["decidable_site_fraction"]["value"] == 2 / 3
    assert (cells["changed_site_fraction"]["numerator"], cells["changed_site_fraction"]["denominator"]) == (0, 2)


def test_example_6_incompatible_models_keep_raw_energy_and_topology():
    result = calculated(f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", energy=-6.0, temperature=25.0), energy=f.energy_request()))
    energy = f.cells(result["energy"]["components"])
    assert (energy["baseline_native_energy"]["value"], energy["variant_native_energy"]["value"]) == (-4, -6)
    assert energy["energy_delta"]["state"] == "incompatible"
    assert result["energy"]["compatibility"]["state"] == "incompatible"
    assert result["pairing_change_state"] == "unchanged_in_complete_correspondence"
    assert "model_setting_different" in {i["code"] for i in result["issues"]}


def test_example_7_same_local_partner_is_unknown_when_unmapped():
    result = calculated(f.pair(correspondence=f.partial([(0, 0)]), selections=[f.site(positions=[0])]))
    row = result["all_site_rows"][0]
    assert row["baseline_partner"]["local_index"] == row["variant_partner"]["local_index"] == 8
    assert row["transition"] == "unresolved_partner" and row["change_indicator"]["value"] is None
    cells = f.cells(result["components"], "selected")
    assert cells["decidable_site_count"]["value"] == 0
    assert cells["changed_site_fraction"]["reason"] == "zero_denominator"
    assert f.cells(result["components"])["pair_symmetric_difference_count"]["reason"] == "unresolved_pair_endpoints"
    assert len(result["all_site_rows"]) == 17
    assert all(r["relation"].startswith("unresolved") for r in result["all_pair_rows"])


@pytest.mark.parametrize("baseline_structure,variant_structure,transition", [
    ("(.......)", ".........", "lost_pairing"), (".........", "(.......)", "gained_pairing")])
def test_lost_or_gained_with_unmapped_partner_is_decidable(baseline_structure, variant_structure, transition):
    result = calculated(f.pair(f.feature(structure=baseline_structure), f.feature("V", "GGGAAAUCC", variant_structure),
        correspondence=f.partial([(0, 0)]), selections=[f.site(positions=[0])]))
    assert result["all_site_rows"][0]["transition"] == transition
    assert f.values(result["components"], "selected")["changed_site_fraction"] == 1


def test_pair_endpoint_explicit_gap_is_known_loss_not_unknown():
    result = calculated(f.pair(f.feature(sequence="GAAAAAAC", structure="(......)"),
        f.feature("V", "AAAAAAC", "......."), correspondence=f.complete([(0, None)] + [(i, i - 1) for i in range(1, 8)])))
    assert result["all_pair_rows"] == [{"relation": "lost", "columns": [0, 7], "baseline_pair": [0, 7],
        "variant_pair": None, "baseline_pair_key": "pair:0:7", "variant_pair_key": None, "gap_endpoint": True, "issues": []}]
    assert result["pairing_change_state"] == "changed"


def test_valid_empty_union_and_no_pairs_have_unavailable_fraction():
    result = calculated(f.pair(f.feature(structure="........."), f.feature("V", "GGGAAAUCC", "........."), selections=[f.site()]))
    site = f.cells(result["components"], "selected")
    assert site["requested_site_count"]["value"] == site["changed_site_count"]["value"] == 0
    assert site["changed_site_fraction"]["value"] is None and site["changed_site_fraction"]["denominator"] == 0
    assert f.cells(result["components"])["preserved_baseline_pair_fraction"]["reason"] == "zero_denominator"


@pytest.mark.parametrize("selection", [f.site(positions=[100]), f.site(intervals=[(4, 2)]), f.site(regions=["missing-region"])])
def test_invalid_selection_is_never_present_zero(selection):
    sheet = f.pair(selections=[selection])
    result = calculated(sheet)
    assert result["resolved_selections"][0]["indices"] == []
    assert all(c["value"] is None and c["reason"] == "invalid_site_selection" for c in result["components"] if c["selection_id"] == "selected")


def test_selected_variant_coordinates_and_overlap_union():
    result = calculated(f.pair(b=f.feature("V", "UGGGAAACCC", ".(((...)))"),
        correspondence=f.complete([(None, 0)] + [(i, i + 1) for i in range(9)]),
        selections=[f.site(member_id="V", positions=[0, 0, 1], intervals=[(0, 3), (2, 4)])]))
    cells = f.cells(result["components"], "selected")
    assert cells["requested_site_count"]["value"] == 4 and cells["inserted_site_count"]["value"] == 1
    assert cells["decidable_site_fraction"]["value"] == 3 / 4


@pytest.mark.parametrize("kind", ["invalid_topology", "missing_map", "invalid_map"])
def test_invalid_global_inputs_keep_coverage_without_biological_zeros(kind):
    a = f.feature(structure="(((......") if kind == "invalid_topology" else f.feature()
    correspondence = None if kind == "missing_map" else f.complete([(0, 0)]) if kind == "invalid_map" else "auto"
    result = calculated(f.pair(a, correspondence=correspondence))
    cells = f.cells(result["components"], "selected")
    assert cells["requested_site_count"]["value"] == 9
    assert cells["decidable_site_count"]["value"] == 0
    assert cells["changed_site_count"]["value"] is None
    assert cells["changed_site_fraction"]["value"] is None
    assert result["pairing_change_state"] == "unresolved"
    assert f.cells(result["components"])["variant_pair_count"]["value"] == 3


def test_supplied_structures_without_sequences_use_explicit_alignment():
    a, b = f.feature(sequence=None), f.feature("V", None)
    result = calculated(f.pair(a, b, correspondence=f.complete([(i, i) for i in range(9)])))
    assert all(r["baseline_symbol"] is None and r["variant_symbol"] is None for r in result["all_site_rows"])
    assert f.values(result["components"])["pair_symmetric_difference_count"] == 0
    assert "original_sequence_unavailable" in {i["code"] for i in result["issues"]}


@pytest.mark.parametrize("field", MODEL_SETTING_NAMES)
def test_every_selected_scientific_setting_checked(field):
    a, b = f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0)
    if field in ("circ", "gquad"):
        b["model"]["selected"][field] = b["model"]["effective_settings"][field] = True
        with pytest.raises(ValueError):
            qualify_rna_energy_comparison(a, b, request=f.energy_request(), baseline_software=f.software(), variant_software=f.software())
        return
    value = b["model"]["effective_settings"][field]
    new = not value if type(value) is bool else 20 if field == "max_bp_span" else value + 1
    b["model"]["selected"][field] = b["model"]["effective_settings"][field] = new
    proof = qualify_rna_energy_comparison(a, b, request=f.energy_request(), baseline_software=f.software(), variant_software=f.software())
    assert proof["state"] == "incompatible"


@pytest.mark.parametrize("field", OTHER_SCALAR_SETTING_NAMES)
def test_every_additional_scalar_difference_or_missing_is_retained(field):
    a, b = f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0)
    record = next(r for r in b["model"]["other_observed_settings"] if r["name"] == field)
    record["value"] = "changed" if isinstance(record["value"], str) else 1
    args = {"request": f.energy_request(), "baseline_software": f.software(), "variant_software": f.software()}
    assert qualify_rna_energy_comparison(a, b, **args)["state"] == "incompatible"
    record.update(value=None, state="unavailable")
    proof = qualify_rna_energy_comparison(a, b, **args)
    assert proof["state"] == "unknown"
    assert next(c for c in proof["checks"] if c["field"] == "other_observed_settings." + field)["outcome"] == "missing"


@pytest.mark.parametrize("field", ["worker_source_sha256", "rna_module_sha256", "rna_extension_sha256", "viennarna_distribution_version"])
def test_unknown_software_is_not_generation_proof(field):
    other = f.software()
    other[field] = "9" * 64 if "sha256" in field else "2.8.0"
    proof = qualify_rna_energy_comparison(f.feature(energy=-3.0), f.feature("V", energy=-2.0),
        request=f.energy_request(), baseline_software=f.software(), variant_software=other)
    assert proof["state"] == "unknown"
    assert not any(c["outcome"] == "equal_by_versioned_generation_rule" for c in proof["checks"])


def test_parameter_bytes_and_scalar_types_are_not_opaque_model_names():
    a, b = f.feature(energy=-3.0), f.feature("V", energy=-2.0)
    b["model"]["model_key"] = a["model"]["model_key"]
    b["native_evaluation"]["model_key"] = a["model"]["model_key"]
    b["model"]["parameter_artifact"]["relative_path"] = "different/path.par"
    args = {"request": f.energy_request(), "baseline_software": f.software(), "variant_software": f.software()}
    assert qualify_rna_energy_comparison(a, b, **args)["state"] == "compatible"
    b["model"]["parameter_artifact"]["sha256"] = "b" * 64
    assert qualify_rna_energy_comparison(a, b, **args)["state"] == "incompatible"
    b["model"]["parameter_artifact"]["sha256"] = a["model"]["parameter_artifact"]["sha256"]
    b["model"]["other_observed_settings"][0]["value"] = False
    assert qualify_rna_energy_comparison(a, b, **args)["state"] == "incompatible"


@pytest.mark.parametrize("mutation", ["missing", "extra", "array_scalar", "bad_load", "bad_save", "unsupported_version"])
def test_profile_recognition_never_infers_unseen_settings(mutation):
    a, b = f.feature(energy=-3.0), f.feature("V", energy=-2.0)
    for s in (a, b):
        model = s["model"]
        if mutation == "missing":
            model["other_observed_settings"].pop(0)
        elif mutation == "extra":
            model["other_observed_settings"].append({"name": "novel_model_field", "value": 0, "state": "observed"})
        elif mutation == "array_scalar":
            next(r for r in model["other_observed_settings"] if r["name"] == "alias").update(value=0, state="observed")
        elif mutation in ("bad_load", "bad_save"):
            model["parameter_" + mutation[4:] + "_return"] = 0
        else:
            model["engine_version"] = s["native_evaluation"]["engine_version"] = "2.6.0"
    proof = qualify_rna_energy_comparison(a, b, request=f.energy_request(), baseline_software=f.software(), variant_software=f.software())
    assert proof["state"] == "unknown"


def test_missing_energy_original_record_and_absent_original_are_distinct():
    a = f.feature(energy=-3.0)
    original = f.feature("V", "GGGAAAUCC")
    result = calculated(f.pair(a, original, energy=f.energy_request()))
    assert result["energy"]["variant_native"] == original["native_evaluation"]
    selected = f.selector([f.member(a), f.absent("V")], [f.comparison(energy=f.energy_request())])
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": f.supplied(a), "V": f.blank()})
    result = calculated(sheet)
    assert result["energy"]["variant_native"] is None
    assert f.cells(result["energy"]["components"])["variant_native_energy"]["reason"] == "not_tested"


def test_missing_original_model_does_not_erase_the_present_native_value():
    a, b = f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0)
    b["model"] = None
    b["status"] = "partial"
    b["issues"].append({"stage": "parse", "code": "rna_model_snapshot_missing", "record_key": "V",
        "field": "/model", "index": None, "artifact_role": None})
    result = calculated(f.pair(a, b, energy=f.energy_request()))
    assert result["energy"]["compatibility"]["state"] == "unknown"
    assert f.cells(result["energy"]["components"])["variant_native_energy"]["value"] == -2.0
    assert f.cells(result["energy"]["components"])["energy_delta"]["value"] is None


@pytest.mark.parametrize("value,expected", [(-4.0, "below"), (-3.5, "within"), (-2.5, "within"), (-2.0, "above")])
def test_explicit_tolerance_uses_closed_exact_boundaries(value, expected):
    result = calculated(f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=value), energy=f.energy_request(0.5)))
    assert result["energy"]["baseline_tolerance_band"] == expected


def test_exact_ratio_difference_once_rounded_and_tolerance_inclusive():
    a = f.feature(sequence="AAA", structure="...", energy=-1.0)
    b = f.feature("V", "AAAAAA", "......", energy=-2.0)
    result = calculated(f.pair(a, b, correspondence=None, selections=[], pairs=False, energy=f.energy_request(0.0, "per_nt")))
    energy = f.cells(result["energy"]["components"])
    assert energy["energy_delta"]["value"] == 0.0
    assert result["energy"]["order"] == "equal" and result["energy"]["baseline_tolerance_band"] == "within"
    assert energy["baseline_selected_energy"]["numerator"] == -1.0
    assert energy["variant_selected_energy"]["denominator"] == 6
    assert "different_sequence_lengths" in {i["code"] for i in result["issues"]}


def test_overflow_delta_unavailable_without_losing_signed_native_values():
    sheet = f.pair(f.feature(energy=-1e308), f.feature("V", "GGGAAAUCC", energy=1e308), energy=f.energy_request())
    result = calculated(sheet)
    cells = f.cells(result["energy"]["components"])
    assert cells["baseline_native_energy"]["value"] == -1e308
    assert cells["energy_delta"]["reason"] == "nonfinite_derived_value"
    assert result["energy"]["order"] == "unavailable"


def test_unrequested_energy_and_topology_are_not_implicitly_calculated():
    sheet = f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), pairs=False, selections=[], correspondence=None)
    assert calculate_rna_energy_comparison(sheet, comparison_id="compare-V") is None
    result = calculated(sheet)
    assert result["energy"] is None and result["all_site_rows"] == result["all_pair_rows"] == result["components"] == []
    assert result["pairing_change_state"] == "not_requested"


def test_wrong_requested_energy_kind_is_not_substituted():
    request = {**f.energy_request(), "quantity": "native_mfe"}
    result = calculated(f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), energy=request))
    assert f.cells(result["energy"]["components"])["energy_delta"]["value"] is None
    assert "energy_kind_mismatch" in {i["code"] for i in result["issues"]}


@pytest.mark.parametrize("bad", [None, {}, [], {"schema": "future"}])
def test_malformed_sheet_rejected(bad):
    for calculate in (calculate_rna_site_changes, calculate_rna_pair_changes, calculate_rna_energy_comparison):
        with pytest.raises(ValueError):
            calculate(bad, comparison_id="compare-V")


def test_saved_input_recalculation_preserves_original_and_parameter_identity(monkeypatch):
    sheet = f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), energy=f.energy_request())
    before = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("scientific execution or I/O is outside deterministic arithmetic")
    import builtins
    import socket
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    first = calculate_rna_comparison_components(sheet)
    second = calculate_rna_comparison_components(deepcopy(sheet))
    assert first == second and sheet == before
    assert first["input_sheet_sha256"] == f.comparison_digest(sheet)
    changed = deepcopy(sheet["selected_question"])
    changed["comparisons"][0]["energy"]["baseline_absolute_tolerance"] = 1.0
    recalculated = calculate_rna_comparison_components(f.rebuild(sheet, question=changed))
    assert recalculated["input_sheet_sha256"] != first["input_sheet_sha256"]
    assert sheet == before


def test_topology_only_retains_known_different_models_without_selecting_energy():
    result = calculated(f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0, temperature=25.0)))
    assert result["energy"] is None
    assert result["pairing_change_state"] == "unchanged_in_complete_correspondence"
    assert "model_setting_different" in {i["code"] for i in result["issues"]}


def _retained(name):
    """Saved 357 outputs; this helper never executes/imports ViennaRNA."""
    path = Path(__file__).parent / "fixtures/rna_structure_comparison_calculations_367/retained357" / (name + ".json")
    packet = json.loads(path.read_bytes())
    if "sheet" in packet:
        return packet["sheet"], packet["bundle"]["software"]
    # Two old packets retained a native record rather than its populated sheet.
    # Re-serialize that exact dictionary as supplied parser input; no new native
    # execution or original native-byte digest claim is made for this encoding.
    from gene_annotation_episode.rna_structure_native import parse_rna_native_record, populate_rna_feature_sheet
    original = packet["record"]
    parsed = parse_rna_native_record(json.dumps(original).encode(), format="rna_native_record_json_v1",
        expected_mode=original["mode"], record_key=original["record_key"])
    sheet = populate_rna_feature_sheet(parsed, record_key=original["record_key"],
        original_input=original["input"], model_metadata=None, subject_binding=None)
    return sheet, packet["bundle"]["software"]


@pytest.mark.parametrize("name,quantity", [("prediction", "native_mfe"), ("evaluation", "native_evaluation")])
def test_retained_native_357_inputs_support_pinned_generation_proof_without_rewriting_arrays(name, quantity):
    original, software = _retained(name)
    before = deepcopy(original)
    request = {**f.energy_request(), "quantity": quantity}
    proof = qualify_rna_energy_comparison(original, original, request=request,
        baseline_software=software, variant_software=software)
    assert proof["state"] == "compatible"
    assert sum(c["outcome"] == "equal_by_versioned_generation_rule" for c in proof["checks"]) == 3
    selected = f.selector([f.member(original, key="WT")], [], scan=f.scan_request(request))
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": {"original_sheet": original,
        "original_bundle_software": software, "received_failure": None}})
    result = calculate_rna_comparison_components(sheet)
    cells = f.cells(result["scan"]["energy_components"])
    assert cells["baseline_selected_energy"]["value"] == -1.2000000476837158
    assert cells["baseline_selected_energy"]["origin"] == ("retained_native_prediction" if name == "prediction" else "retained_native_evaluation")
    assert cells["baseline_rank_start"]["value"] == 1
    assert original == before
    assert any(path.endswith("/native_uncertainty") for path in result["unused_input_paths"])


def test_retained_native_357_different_settings_and_failure_preserve_actual_states():
    a, sa = _retained("evaluation")
    b, sb = _retained("supplied_parameters_nondefault_model")
    failed, sf = _retained("short_loop_native_failure")
    assert a["model"]["parameter_artifact"]["sha256"] == b["model"]["parameter_artifact"]["sha256"]
    proof = qualify_rna_energy_comparison(a, b, request=f.energy_request(), baseline_software=sa, variant_software=sb)
    assert proof["state"] == "incompatible"
    assert b["native_evaluation"]["value"] == -2.140000104904175
    selected = f.selector([f.member(a, key="WT"), f.member(failed, key="V")], [f.comparison(energy=f.energy_request())])
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": {"original_sheet": a,
        "original_bundle_software": sa, "received_failure": None}, "V": {"original_sheet": failed,
        "original_bundle_software": sf, "received_failure": None}})
    result = calculated(sheet)
    assert result["energy"]["variant_native"] == failed["native_evaluation"]
    assert result["energy"]["variant_native"]["state"] == "failed"
    assert result["energy"]["variant_native"]["reason"] == "rna_native_failed"
    assert f.cells(result["energy"]["components"])["energy_delta"]["state"] == "failed"


def test_filled_eight_hand_examples_are_retained(tmp_path):
    fixtures = {
        "1_same_pairing_different_energy": f.pair(f.feature(energy=-3.0), f.feature("V", "GGGAAAUCC", energy=-2.0), energy=f.energy_request()),
        "2_reassigned_partner": f.pair(f.feature(sequence="G" * 10, structure="((....)).."), f.feature("V", "G" * 10, ".((....))."), selections=[f.site(positions=[0, 1, 2, 6, 7, 8])]),
        "3_insertion": f.pair(b=f.feature("V", "UGGGAAACCC", ".(((...)))"), correspondence=f.complete([(None, 0)] + [(i, i + 1) for i in range(9)])),
        "4_deletion": f.pair(b=f.feature("V", "GGGAACCC", "(((..)))"), correspondence=f.complete([(i, i if i < 3 else None if i == 3 else i - 1) for i in range(9)]), selections=[f.site(positions=[2, 3, 6])]),
        "5_scan_failure_ties_aliases": f.scan(),
        "6_incompatible_models": f.pair(f.feature(energy=-4.0), f.feature("V", "GGGAAAUCC", energy=-6.0, temperature=25.0), energy=f.energy_request()),
        "7_unknown_partner": f.pair(correspondence=f.partial([(0, 0)]), selections=[f.site(positions=[0])]),
        "8_tolerance_exact_ranks": f.scan((0.0, 0.06, 0.12), failed=False, aliases=False, tolerance=0.1),
    }
    output = {"provenance": "Invented arithmetic fixtures, not native measurements or experiments.",
        "examples": {key: {"sheet": sheet, "components": calculate_rna_comparison_components(sheet)} for key, sheet in fixtures.items()}}
    path = tmp_path / "filled_eight_examples.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    assert len(json.loads(path.read_text())["examples"]) == 8
