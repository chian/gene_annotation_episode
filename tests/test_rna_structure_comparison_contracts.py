"""Closed selection and saved representation checks; calculators are separate."""
from copy import deepcopy
import builtins
import json
from importlib import import_module
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import gene_annotation_episode.rna_structure_comparison_contracts as contracts
from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet
_fixtures = import_module("verification.tool_graders_rna_comparison_inputs_2026-10-26_366.fixture_helpers")
comparison, empty_components, energy_request, feature, member, pair_inputs, parameters, scan_request, selector, site, supplied = (
    getattr(_fixtures, name) for name in ("comparison", "empty_components", "energy_request", "feature", "member",
        "pair_inputs", "parameters", "scan_request", "selector", "site", "supplied"))


def test_all_exported_schemas_are_json_schemas_and_objects_are_closed():
    names = ("RNA_COMPARISON_SELECTOR_SCHEMA", "RNA_COMPARISON_PARAMETERS_SCHEMA",
        "RNA_COMPARISON_SHEET_SCHEMA", "RNA_COMPARISON_COMPONENTS_SCHEMA",
        "RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA")
    def inspect(schema):
        if type(schema) is dict:
            if schema.get("type") == "object":
                assert schema["additionalProperties"] is False
                assert set(schema["required"]) == set(schema["properties"])
            for child in schema.values():
                inspect(child)
        elif type(schema) is list:
            for child in schema:
                inspect(child)
    for name in names:
        schema = getattr(contracts, name)
        Draft202012Validator.check_schema(schema)
        inspect(schema)


def test_finite_sets_include_addendum_without_arbitrary_metric_formulas():
    assert contracts.UNCERTAINTY_REASON in contracts.COMPARISON_REASONS
    assert {"minimum_selected_energy", "baseline_energy_above_minimum", "lowest_energy_tie_count"} <= set(contracts.SCAN_ENERGY_METRICS)
    assert set(contracts.METRIC_SPECS) == set(contracts.COMPARISON_FORMULAS)
    assert all(value["metric"] in contracts.COMPARISON_METRICS for value in contracts.METRIC_SPECS.values())
    assert set(contracts.COMPATIBILITY_FIELDS) >= {"baseline.structure_association", "variant.structure_association", "other_observed_settings.alias"}
    assert len(contracts.COMPATIBILITY_FIELDS) == len(set(contracts.COMPATIBILITY_FIELDS))
    assert contracts.SCAN_MEMBER_RANK_METRICS == ("member_rank_start", "member_rank_end")
    assert not set(contracts.SCAN_MEMBER_RANK_METRICS) & set(contracts.SCAN_ENERGY_METRICS)
    assert set(contracts.SCAN_MEMBER_RANK_METRICS) <= contracts.COMPARISON_METRICS


@pytest.mark.parametrize("metric", ["member_rank_start", "member_rank_end"])
def test_member_ranks_require_explicit_scan_members_projection(metric):
    aggregate = {"projection_id": "rank", "family": "scan_energy", "scan_id": "scan",
        "metrics": [metric], "include_rank_class": False}
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_projection_request(aggregate)
    member_projection = {"projection_id": "member", "family": "scan_members", "scan_id": "scan",
        "members": {"kind": "explicit", "member_ids": ["WT"]}, "fields": [metric.removeprefix("member_")],
        "order": "declared", "limit": None}
    assert contracts.validate_rna_comparison_projection_request(member_projection) == member_projection


@pytest.mark.parametrize("field,value", [("schema", "future"), ("tie_rule", "epsilon"),
    ("arithmetic", "formula language"), ("site_denominator", "all_sites"),
    ("native_uncertainty_policy", "make_probability"), ("extra", 1)])
def test_parameters_are_closed_fixed_values(field, value):
    requested = parameters()
    requested[field] = value
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_parameters(requested)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'\xff', b'{'])
def test_supplied_json_rejects_duplicate_keys_nonfinite_and_malformed(raw):
    with pytest.raises(ValueError):
        contracts.parse_rna_comparison_json(raw)


def test_strict_json_valid_roundtrip():
    selected, _ = pair_inputs()
    assert contracts.parse_rna_comparison_json(json.dumps(selected)) == selected


@pytest.mark.parametrize("invalid", [True, 1.0, -1, "1", float("nan"), float("inf")])
def test_positions_require_actual_nonnegative_integer(invalid):
    selected, _ = pair_inputs(selections=[site(positions=[invalid])])
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(selected)


@pytest.mark.parametrize("bad_id", ["", "line\nbreak", "line\rbreak", "nul\0byte", True])
def test_new_ids_are_restricted(bad_id):
    selected, _ = pair_inputs()
    selected["projections"][0]["projection_id"] = bad_id
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(selected)


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(extra=True), lambda s: s.pop("projections"),
    lambda s: s.update(projections=[]), lambda s: s["projections"].append(deepcopy(s["projections"][0])),
    lambda s: s["projections"][0].update(fields=["pairs", "pairs"]),
    lambda s: s["projections"][0].update(fields=["all"]),
    lambda s: s["question"].update(baseline_member_id="absent"),
    lambda s: s["question"]["comparisons"][0].update(variant_member_id="absent"),
    lambda s: s["question"]["comparisons"].append(deepcopy(s["question"]["comparisons"][0])),
    lambda s: s["question"]["comparisons"][0].update(extra="comment"),
])
def test_selectors_reject_implicit_full_return_and_dangling_or_duplicate_fields(mutation):
    selected, _ = pair_inputs()
    mutation(selected)
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(selected)


def test_every_parent_projection_family_can_be_selected_exactly():
    energy = energy_request(0.1)
    a, b = feature(), feature("V", "GGGAAAUCC")
    selected = selector([member(a), member(b)], [comparison(correspondence={"kind": "supplied_partial_correspondence",
        "authority": {"kind": "parent_assignment", "source_ref": None}, "matches": []},
        selections=[site(positions=[0])], pairs=True, energy=energy)], scan=scan_request(energy, ["selected"]))
    projections = [
        {"projection_id": "energy", "family": "energy_comparison", "comparison_ids": ["compare-V"], "metrics": ["energy_delta"], "include_order": True, "include_tolerance_band": False},
        {"projection_id": "structures", "family": "structures", "member_ids": ["WT", "V"], "fields": ["dot_bracket"]},
        {"projection_id": "sites", "family": "position_changes", "comparison_id": "compare-V", "selection_id": "selected", "transitions": ["unresolved_partner"]},
        {"projection_id": "pairs", "family": "pair_changes", "comparison_ids": ["compare-V"], "relations": ["preserved", "lost"]},
        {"projection_id": "counts", "family": "comparison_counts", "comparison_ids": ["compare-V"], "selection_ids": ["selected"], "metrics": ["changed_site_count", "preserved_pair_count"], "include_pairing_change_state": True},
        {"projection_id": "rank", "family": "scan_energy", "scan_id": "scan", "metrics": ["baseline_rank_start", "baseline_energy_above_minimum"], "include_rank_class": True},
        {"projection_id": "scan-sites", "family": "scan_sites", "scan_id": "scan", "selection_ids": ["selected"], "metrics": ["changed_variant_fraction"]},
        {"projection_id": "members", "family": "scan_members", "scan_id": "scan", "members": {"kind": "exceptions", "predicates": ["lower_than_baseline", "received_failure"]}, "fields": ["energy", "rank_start", "eligibility"], "order": "declared", "limit": 2},
    ]
    selected["projections"] = projections
    assert contracts.validate_rna_comparison_selector(selected)["projections"] == projections
    for projection in projections:
        selected["projections"] = [projection]
        assert contracts.validate_rna_comparison_selector(selected)["projections"] == [projection]


@pytest.mark.parametrize("projection", [
    {"projection_id": "x", "family": "energy_comparison", "comparison_ids": ["missing"], "metrics": ["energy_delta"], "include_order": True, "include_tolerance_band": False},
    {"projection_id": "x", "family": "position_changes", "comparison_id": "compare-V", "selection_id": "missing", "transitions": ["lost_pairing"]},
    {"projection_id": "x", "family": "comparison_counts", "comparison_ids": ["compare-V"], "selection_ids": [], "metrics": ["changed_site_count"], "include_pairing_change_state": False},
    {"projection_id": "x", "family": "structures", "member_ids": ["missing"], "fields": ["dot_bracket"]},
    {"projection_id": "x", "family": "scan_energy", "scan_id": "scan", "metrics": ["baseline_rank_start"], "include_rank_class": True},
    {"projection_id": "x", "family": "pair_changes", "comparison_ids": ["compare-V"], "relations": ["preserved"]},
])
def test_projection_dependencies_must_be_explicit(projection):
    selected, _ = pair_inputs()
    selected["projections"] = [projection]
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(selected)


def test_scan_energy_and_shared_baseline_selection_must_match_every_member():
    a, b, c = feature(), feature("A", "GGGAAAUCC"), feature("B", "GGGUAACCC")
    energy = energy_request()
    selected = selector([member(a), member(b), member(c)], [comparison(k, energy=energy, selections=[site(positions=[0])]) for k in ("A", "B")], scan=scan_request(energy, ["selected"]))
    contracts.validate_rna_comparison_selector(selected)
    wrong = deepcopy(selected)
    wrong["question"]["comparisons"][1]["energy"]["normalization"] = "per_nt"
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(wrong)
    wrong = deepcopy(selected)
    wrong["question"]["comparisons"][1]["site_selections"][0]["positions"] = [1]
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_selector(wrong)


def test_structural_paths_resolve_actual_closed_instance_and_null_leaf():
    selected, operands = pair_inputs()
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    assert contracts.resolve_comparison_input_path(sheet, "/operands/0/original_sheet/topology/pairs/0/i") == 0
    assert contracts.resolve_comparison_input_path(sheet, "/operands/0/original_bundle_software") is None
    for pointer in ("/operands/WT/original_sheet", "/operands/99", "/operands/00", "/operands/0/narrative",
            "/operands/0/original_bundle_software/engine", "/operands/0/~2", "raw prose"):
        with pytest.raises(ValueError):
            contracts.resolve_comparison_input_path(sheet, pointer)


def test_issue_relationships_cannot_name_unknown_selection_member_or_path():
    selected, operands = pair_inputs(selections=[site()])
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    valid = contracts.comparison_issue("invalid_site_selection", stage="selection", member_id="WT",
        comparison_id="compare-V", selection_id="selected", field="/comparisons/0/resolved_selections/0/indices")
    contracts.validate_rna_comparison_issue(valid, sheet=sheet)
    for key, value in (("member_id", "missing"), ("selection_id", "missing"), ("comparison_id", None),
            ("field", "/operands/2"), ("code", "my prose")):
        wrong = {**valid, key: value}
        with pytest.raises(ValueError):
            contracts.validate_rna_comparison_issue(wrong, sheet=sheet)


def test_components_bind_original_sheet_digest_and_exact_input_copies():
    selected, operands = pair_inputs()
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    result = empty_components(sheet)
    assert contracts.validate_rna_comparison_components(result, sheet=sheet) == result
    for mutation in (lambda v: v.update(input_sheet_sha256="0" * 64),
            lambda v: v["comparisons"][0].update(variant_member_id="WT"),
            lambda v: v["comparisons"][0]["correspondence"]["baseline_to_variant"][0].update(column=1),
            lambda v: v.update(unused_input_paths=["/operands/99"]),
            lambda v: v.update(used_input_paths=["/parameters"], unused_input_paths=["/parameters"]),
            lambda v: v["comparisons"][0].update(energy={})):
        wrong = deepcopy(result)
        mutation(wrong)
        with pytest.raises(ValueError):
            contracts.validate_rna_comparison_components(wrong, sheet=sheet)


def cell(metric, prefix, *, state="present", value=0, reason=None, selection=None, numerator=0, denominator=None):
    spec = contracts.METRIC_SPECS[prefix + "." + metric]
    return {"metric": metric, "value": value, "unit": spec["units"][0], "state": state, "reason": reason,
        "numerator": numerator, "denominator": denominator, "origin": spec["origins"][0],
        "formula_id": prefix + "." + metric, "input_paths": ["/operands"], "population_id": "compare-V",
        "selection_id": selection, "uncertainty": {"state": "not_produced", "value": None, "reason": contracts.UNCERTAINTY_REASON}}


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(value=True), lambda c: c.update(value=float("nan")),
    lambda c: c.update(value=float("inf")), lambda c: c.update(value=1.0),
    lambda c: c.update(unit="variants"), lambda c: c.update(formula_id="rna_scan_site_v1.changed_variant_count"),
    lambda c: c.update(reason="not_tested"), lambda c: c.update(state="unknown"),
    lambda c: c.update(denominator=4), lambda c: c.update(numerator=2),
    lambda c: c.update(origin="retained_native_prediction"),
    lambda c: c.update(input_paths=["/operands/98"]), lambda c: c.update(extra="text"),
])
def test_numeric_cells_strict_types_finite_values_formula_and_input_paths(mutation):
    selected, operands = pair_inputs()
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    value = cell("changed_site_count", "rna_site_compare_v1", selection="selected")
    mutation(value)
    with pytest.raises(ValueError):
        value = contracts.checked(value, contracts.NUMERIC_CELL_SCHEMA)
        contracts._cell_relationship(value, sheet, prefix="rna_site_compare_v1", selection_id="selected")


def all_unpaired_component_case(selection):
    a, b = feature("WT", "ACG", "..."), feature("V", "ACG", "...")
    selected, operands = pair_inputs(a=a, b=b, request={"kind": "identical_sequence"}, selections=[selection])
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    result = empty_components(sheet)
    row = result["comparisons"][0]
    partner = {"state": "unpaired", "local_index": None, "column": None, "counterpart_index": None}
    row["all_site_rows"] = [{"column": i, "baseline_index": i, "variant_index": i,
        "baseline_symbol": symbol, "variant_symbol": symbol, "baseline_partner": deepcopy(partner),
        "variant_partner": deepcopy(partner), "transition": "unchanged_unpaired",
        "change_indicator": cell("change_indicator", "rna_site_compare_v1"), "issues": []} for i, symbol in enumerate("ACG")]
    return sheet, result


def test_invalid_selection_cannot_turn_into_present_zero_component():
    sheet, result = all_unpaired_component_case(site(positions=[99]))
    rows = [cell(metric, "rna_site_compare_v1", state="invalid_input", value=None,
        reason="invalid_site_selection", numerator=None, selection="selected") for metric in contracts.SITE_METRICS]
    result["comparisons"][0]["components"] = rows
    contracts.validate_rna_comparison_components(result, sheet=sheet)
    rows[0].update(state="present", value=0, reason=None, numerator=0)
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_components(result, sheet=sheet)


def test_valid_empty_site_set_has_zero_count_but_zero_denominator_is_unavailable():
    sheet, result = all_unpaired_component_case(site())
    rows = []
    for metric in contracts.SITE_METRICS:
        if metric.endswith("fraction"):
            rows.append(cell(metric, "rna_site_compare_v1", state="missing_input", value=None,
                reason="zero_denominator", selection="selected", denominator=0))
        else:
            rows.append(cell(metric, "rna_site_compare_v1", selection="selected"))
    result["comparisons"][0]["components"] = rows
    contracts.validate_rna_comparison_components(result, sheet=sheet)
    fraction = next(c for c in rows if c["metric"] == "changed_site_fraction")
    fraction.update(state="present", reason=None, value=0)
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_components(result, sheet=sheet)


def test_component_validation_is_representation_only_and_does_not_import_calculators(monkeypatch):
    selected, operands = pair_inputs()
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    result = empty_components(sheet)
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name not in ("RNA", "rna_structure_comparison_calculations", "rna_structure_scan_calculations")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("unexpected file access"))
    contracts.validate_rna_comparison_components(result, sheet=sheet)


def test_all_original_pair_keys_are_retained_once_in_valid_partial_map():
    a, b = feature(), feature("V", "GGGAAAUCC")
    request = {"kind": "supplied_partial_correspondence", "authority": {"kind": "parent_assignment", "source_ref": None},
        "matches": [{"baseline_index": 0, "variant_index": 0}]}
    selected, operands = pair_inputs(a=a, b=b, request=request, pairs=True)
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    inputs = sheet["comparisons"][0]
    rows = []
    for side in ("baseline", "variant"):
        for i, j in ((0, 8), (1, 7), (2, 6)):
            rows.append({"relation": "unresolved_" + side, "columns": None,
                "baseline_pair": [i, j] if side == "baseline" else None,
                "variant_pair": [i, j] if side == "variant" else None,
                "baseline_pair_key": f"pair:{i}:{j}" if side == "baseline" else None,
                "variant_pair_key": f"pair:{i}:{j}" if side == "variant" else None,
                "gap_endpoint": False, "issues": []})
    contracts._validate_pair_rows(rows, inputs, a, b)
    with pytest.raises(ValueError):
        contracts._validate_pair_rows(rows[:-1], inputs, a, b)
    with pytest.raises(ValueError):
        contracts._validate_pair_rows(rows + [deepcopy(rows[0])], inputs, a, b)
    wrong = deepcopy(rows)
    wrong[0]["baseline_pair"] = [0, 7]
    with pytest.raises(ValueError):
        contracts._validate_pair_rows(wrong, inputs, a, b)


def test_missing_map_preserves_coverage_but_disallows_biological_zero():
    a, b = feature("WT", "ACG", "..."), feature("V", "ACG", "...")
    selected = selector([member(a), member(b)], [comparison(selections=[site(positions=[0])])])
    sheet = populate_rna_comparison_sheet(selected, operands={"WT": supplied(a), "V": supplied(b)})
    result = empty_components(sheet)
    rows = []
    partner = {"state": "unpaired", "local_index": None, "column": None, "counterpart_index": None}
    unavailable = {**partner, "state": "unavailable"}
    for side in ("baseline", "variant"):
        for i, symbol in enumerate("ACG"):
            rows.append({"column": None, "baseline_index": i if side == "baseline" else None,
                "variant_index": i if side == "variant" else None,
                "baseline_symbol": symbol if side == "baseline" else None,
                "variant_symbol": symbol if side == "variant" else None,
                "baseline_partner": deepcopy(partner if side == "baseline" else unavailable),
                "variant_partner": deepcopy(partner if side == "variant" else unavailable),
                "transition": "unmapped_site", "change_indicator": cell("change_indicator", "rna_site_compare_v1",
                    state="missing_input", value=None, reason="correspondence_not_supplied", numerator=None), "issues": []})
    result["comparisons"][0]["all_site_rows"] = rows
    values = []
    for metric in contracts.SITE_METRICS:
        if metric in ("requested_site_count", "decidable_site_count", "unmapped_site_count"):
            amount = 0 if metric == "decidable_site_count" else 1
            values.append(cell(metric, "rna_site_compare_v1", value=amount, numerator=amount, selection="selected"))
        elif metric == "decidable_site_fraction":
            values.append(cell(metric, "rna_site_compare_v1", value=0, numerator=0, denominator=1, selection="selected"))
        else:
            values.append(cell(metric, "rna_site_compare_v1", state="missing_input", value=None,
                reason="correspondence_not_supplied", numerator=None, selection="selected"))
    result["comparisons"][0]["components"] = values
    contracts.validate_rna_comparison_components(result, sheet=sheet)
    changed = next(v for v in values if v["metric"] == "changed_site_count")
    changed.update(value=0, numerator=0, state="present", reason=None)
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_components(result, sheet=sheet)


def test_nullable_original_energy_is_absence_never_synthetic_native_record():
    a, b = feature(energy=-3.0), feature("V", "GGGAAAUCC", energy=-2.0)
    selected, operands = pair_inputs(a=a, b=b, energy=energy_request())
    selected["question"]["membership"][0] = {"member_id": "WT", "kind": "declared_absent", "state": "not_supplied"}
    selected["question"]["comparisons"][0]["correspondence"] = None
    operands["WT"] = supplied(None)
    sheet = populate_rna_comparison_sheet(selected, operands=operands)
    result = empty_components(sheet)
    energy = {"request": energy_request(), "baseline_native": None,
        "variant_native": deepcopy(b["native_evaluation"]),
        "compatibility": {"profile": contracts.PROFILE, "state": "unknown",
            "checks": [{"field": "baseline.structure_association", "outcome": "missing"}], "issues": []},
        "components": [], "order": "unavailable", "baseline_tolerance_band": "not_requested"}
    for metric in contracts.ENERGY_METRICS:
        if metric.startswith("variant_"):
            value = cell(metric, "rna_energy_compare_v1", value=-2.0, numerator=None)
        elif metric == "baseline_tolerance":
            value = cell(metric, "rna_energy_compare_v1", state="not_requested", value=None, reason="not_requested", numerator=None)
        else:
            value = cell(metric, "rna_energy_compare_v1", state="missing_input", value=None, reason="baseline_unavailable", numerator=None)
        if value["origin"].startswith("retained_native_"):
            value["origin"] = "retained_native_evaluation"
        energy["components"].append(value)
    result["comparisons"][0]["energy"] = energy
    contracts.validate_rna_comparison_components(result, sheet=sheet)
    energy["baseline_native"] = deepcopy(a["native_evaluation"])
    with pytest.raises(ValueError):
        contracts.validate_rna_comparison_components(result, sheet=sheet)


def test_production_modules_have_no_io_or_native_or_later_lane_imports():
    import ast
    root = Path(__file__).parents[1] / "gene_annotation_episode"
    forbidden = {"os", "subprocess", "socket", "requests", "urllib", "RNA", "pathlib",
        "rna_structure_comparison_calculations", "rna_structure_scan_calculations", "rna_structure_comparison_views"}
    for name in ("rna_structure_comparison_contracts.py", "rna_structure_comparison_inputs.py"):
        tree = ast.parse((root / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] not in forbidden for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "exec", "eval", "compile"}
