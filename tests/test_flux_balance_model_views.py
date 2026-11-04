"""Source-free saved views of six byte-exact captures from check348.

Origin: runs/check348_fba_model_edit/tmp/fba-model-selected0. That earlier
selected-runtime control inspected/edited tiny caller-authored models without
optimizing. Only the six required data files below are retained here. Setup
uses the existing capture parsers; these tests never load Cobra models, call
the model worker, optimize, or establish Source/publication custody.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import flux_balance_model_tools as tools
from gene_annotation_episode import flux_balance_readers as readers
from test_flux_balance_model_tools import addition, file_for, request, selector


FIXTURES = Path(__file__).parent / "fixtures" / "flux_balance_model_views"
CAPTURE_PINS = {
    "inspect/original-model.json": (696, "c82d1a09f98331f517e6d997fe2008f6682f562e0cf42901071645c6a4114aeb"),
    "inspect/model-capture.json": (19630, "8a9674b1c807470018ac696dccc77e122f1b97fbb94e330baf7abf832d6e7d5e"),
    "inspect/problem-capture.json": (39917, "c7973ccde3b146b0068f4920ba08eafb5919e9cc6e53fa9abeb39c4008a85a1a"),
    "edit/model-capture.json": (22208, "7ad60a696734c21590eeaf1cfff66c3d0066afbe342939af1a091d7437fd0c9a"),
    "edit/problem-capture.json": (46319, "2c087035c118be9a6d4a4f3c8893b7136079c5e4de7c0bb224866507c98aba97"),
    "edit/edited-model.json": (926, "161d861f709335c55ff7355164c2b40cf310d1bb0f7c4c560d473f94634ef536"),
}
COLLECTIONS = ("model", "compartments", "metabolites", "reactions", "genes", "groups", "stoichiometry", "objective")


@pytest.fixture(scope="module")
def retained_results():
    payloads = {name: (FIXTURES / name).read_bytes() for name in CAPTURE_PINS}
    assert set(p.relative_to(FIXTURES).as_posix() for p in FIXTURES.rglob("*") if p.is_file()) == set(CAPTURE_PINS)
    for name, raw in payloads.items():
        assert (len(raw), hashlib.sha256(raw).hexdigest()) == CAPTURE_PINS[name]
    original = payloads["inspect/original-model.json"]
    results = {}
    for mode in ("inspect", "edit"):
        mf = file_for(payloads[mode + "/model-capture.json"], "cobra_model_capture_v1")
        pf = file_for(payloads[mode + "/problem-capture.json"], "cobra_glpk_problem_capture_v1")
        models = readers.parse_cobra_glpk_model_capture(payloads[mode + "/model-capture.json"],
            source=mf, original_model=file_for(original))
        problems = readers.parse_cobra_glpk_problem_capture(payloads[mode + "/problem-capture.json"], source=pf, models=models)
        edited = None if mode == "inspect" else {"role": "edited_model", "relative_path": "edited-model.json",
            "file": file_for(payloads["edit/edited-model.json"])}
        records = [] if mode == "inspect" else tools._edit_rows(addition())
        for row in records:
            row["state"] = "applied"
        files = [{"role": "original_model", "relative_path": "original-model.json", "file": file_for(original)}]
        if edited is not None:
            files.append(edited)
        files.extend([{"role": "effective_model", "relative_path": "model-capture.json", "file": mf},
            {"role": "effective_problem", "relative_path": "problem-capture.json", "file": pf}])
        results[mode] = tools.validate_flux_balance_model_result({"version": tools.RESULT_VERSION,
            "request": request(original, edit=addition() if mode == "edit" else None), "models": models,
            "problems": problems, "edit_results": records, "edit_state": "exact" if mode == "edit" else "not_requested",
            "edited_model": edited, "files": files, "model_optimize_call_count": 0, "issues": []})
    return results


@pytest.fixture
def saved_only(retained_results, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("saved view attempted payload I/O, parsing or model execution")
    for name in ("open", "read_bytes", "read_text", "write_bytes", "write_text"):
        monkeypatch.setattr(Path, name, forbidden)
    for module in (tools, readers):
        for name in ("parse_cobra_glpk_model_capture", "parse_cobra_glpk_problem_capture"):
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(tools, "read_bytes", forbidden)
    monkeypatch.setattr(tools, "run_flux_balance_model_request", forbidden)
    return deepcopy(retained_results)


@pytest.mark.parametrize("collection", COLLECTIONS)
@pytest.mark.parametrize("phase", ["loaded_original", "effective"])
def test_retained_collections_have_closed_detached_saved_views(saved_only, collection, phase):
    stored = saved_only["edit"]
    before = canonical(stored)
    value = tools.project_flux_balance_model_result(stored, selector=selector(collection, phase))
    frozen = canonical(value)
    assert canonical(tools.validate_flux_balance_model_view(json.loads(frozen))) == frozen
    assert canonical(stored) == before
    assert value["population"]["snapshot_available"] is True
    assert value["page"]["returned_row_count"] == len(value["rows"])
    assert all(row["availability"] == "present" for row in value["rows"])
    for private in ("native_cobra_json", "native_capture_evidence", "detail_file", "artifact_ref", "annotation_pointer",
            "notes_pointer", "gpr_source_pointer", "boundary_source", "native_expression_pointer"):
        assert private not in frozen
    value["selector"]["row_window"]["limit"] = 1
    assert canonical(stored) == before


def test_retained_counts_zero_bounds_charge_and_distinct_original_population(saved_only):
    original = tools.project_flux_balance_model_result(saved_only["edit"], selector=selector("reactions"))
    effective = tools.project_flux_balance_model_result(saved_only["edit"], selector=selector("reactions", "effective"))
    metabolites = tools.project_flux_balance_model_result(saved_only["edit"], selector=selector("metabolites", "effective"))
    assert original["population"]["expected_count"] == original["population"]["retained_count"] == 3
    assert effective["population"]["expected_count"] == effective["population"]["retained_count"] == 4
    assert [row["values"]["id"] for row in effective["rows"]] == ["IN", "AB", "OUT", "BC"]
    ab = effective["rows"][1]["values"]
    assert ab["lower"]["kind"] == ab["upper"]["kind"] == "finite"
    assert ab["lower"]["value"] == ab["upper"]["value"] == 0
    charge = metabolites["rows"][2]["values"]["charge"]
    assert charge["state"] == "present" and charge["value"] == 0 and charge["missing_reason"] is None
    assert metabolites["population"]["retained_count"] == 3


def test_explicit_selection_keeps_duplicate_order_and_counts_full_native_population(saved_only):
    selected = selector("reactions", "effective", ordinals=[3, 1, 3, 0], offset=1, limit=2)
    view = tools.project_flux_balance_model_result(saved_only["edit"], selector=selected)
    assert view["population"] == {"basis": "captured_loaded_native_collection", "expected_count": 4,
        "retained_count": 4, "snapshot_available": True}
    assert view["page"] == {"selected_row_count": 4, "offset": 1, "returned_row_count": 2, "has_more": True}
    assert [row["ordinal"] for row in view["rows"]] == [1, 3]
    duplicate = tools.project_flux_balance_model_result(saved_only["edit"],
        selector=selector("reactions", "effective", ordinals=[3, 3]))
    assert duplicate["rows"][0] == duplicate["rows"][1]
    assert duplicate["page"]["selected_row_count"] == 2 and duplicate["population"]["retained_count"] == 4


@pytest.mark.parametrize("offset", [0, 2, 20])
def test_entire_explicit_selection_is_bounds_checked_even_outside_returned_window(saved_only, offset):
    with pytest.raises(ValueError, match="view_position_out_of_range"):
        tools.project_flux_balance_model_result(saved_only["edit"],
            selector=selector("reactions", "effective", ordinals=[0, 4], offset=offset, limit=1))
    view = tools.project_flux_balance_model_result(saved_only["edit"],
        selector=selector("reactions", "effective", ordinals=[0, 1], offset=offset, limit=1))
    view["selector"]["ordinals"][1] = 4
    if offset == 0:
        with pytest.raises(ValueError, match="view_population_conflict"):
            tools.validate_flux_balance_model_view(view)
    else:
        with pytest.raises(ValueError):
            tools.validate_flux_balance_model_view(view)


def _partial(stored):
    value = deepcopy(stored)
    issue = tools._issue("partial_population", "parse", "/partial")
    for phase in ("loaded_original", "effective"):
        model = value["models"][phase]
        model["reactions"] = model["reactions"][1:]
        model["metabolites"] = model["metabolites"][1:]
        model["stoichiometry"] = model["stoichiometry"][1::2]
        model["population"].update(reactions=None, metabolites=None, completeness="partial")
        value["problems"][phase]["representation"] = "partial"
    value["models"]["issues"].append(issue)
    value["problems"]["issues"].append(issue)
    return value


@pytest.mark.parametrize("collection,ordinals", [("reactions", [1, 2]), ("metabolites", [1]), ("stoichiometry", [1, 3])])
def test_partial_implicit_native_ordinals_may_have_gaps_without_unknown_becoming_zero(saved_only, collection, ordinals):
    # Engineered missing saved rows exercise DTO relationships, not a new capture.
    value = tools.project_flux_balance_model_result(_partial(saved_only["inspect"]), selector=selector(collection))
    assert value["population"]["expected_count"] is None
    assert value["population"]["retained_count"] == len(ordinals)
    assert [row["ordinal"] for row in value["rows"]] == ordinals
    assert all(row["availability"] == "present" for row in value["rows"])
    assert canonical(tools.validate_flux_balance_model_view(value)) == canonical(value)


def test_unknown_snapshot_explicit_missing_row_differs_from_observed_empty(saved_only):
    value = deepcopy(saved_only["inspect"])
    issue = tools._issue("schema_invalid", "parse", "/capture")
    value["models"].update(loaded_original=None, effective=None, source=None, input_profile="unknown", loader=None,
        source_to_loaded_ids=[], source_feature_audit=[], source_audit=None, issues=[issue])
    value["problems"].update(loaded_original=None, effective=None, source=None, configuration_before_solve=None, issues=[issue])
    missing = tools.project_flux_balance_model_result(value, selector=selector("groups", ordinals=[6, 6]))
    empty = tools.project_flux_balance_model_result(saved_only["inspect"], selector=selector("groups"))
    assert missing["population"] == {"basis": "captured_loaded_native_collection", "expected_count": None,
        "retained_count": 0, "snapshot_available": False}
    assert missing["rows"] == [{"ordinal": 6, "availability": "unavailable", "values": None}] * 2
    assert missing["issues"] == [tools._public(issue)]
    assert empty["population"]["expected_count"] == empty["population"]["retained_count"] == 0
    assert empty["population"]["snapshot_available"] is True and empty["rows"] == []


def test_partial_explicit_absence_keeps_selected_count_separate_from_retained_count(saved_only):
    view = tools.project_flux_balance_model_result(_partial(saved_only["inspect"]),
        selector=selector("reactions", ordinals=[0, 2, 0, 99]))
    assert view["page"]["selected_row_count"] == 4 and view["population"]["retained_count"] == 2
    assert [row["availability"] for row in view["rows"]] == ["unavailable", "present", "unavailable", "unavailable"]
    assert all(row["values"] is None for row in view["rows"] if row["availability"] == "unavailable")


@pytest.mark.parametrize("collection", ["model", "objective"])
def test_metadata_and_objective_are_native_singletons_with_unbounded_view_limit(saved_only, collection):
    view = tools.project_flux_balance_model_result(saved_only["edit"],
        selector=selector(collection, "effective", ordinals=[0, 0], limit=10**12))
    assert view["population"]["expected_count"] == view["population"]["retained_count"] == 1
    assert view["page"]["selected_row_count"] == view["page"]["returned_row_count"] == 2
    assert view["rows"][0] == view["rows"][1]
    if collection == "model":
        assert set(view["rows"][0]["values"]) == {"model_id", "model_name", "population", "medium_state", "medium_basis"}
    else:
        assert view["rows"][0]["values"]["direction"] == "max"
        assert [row["variable_position"] for row in view["rows"][0]["values"]["terms"]] == [6, 7]


@pytest.mark.parametrize("fault", ["extra", "version", "selector_extra", "selector_ordinal_bool", "selector_ordinal_float",
    "row_ordinal_bool", "row_ordinal_float", "expected_bool", "retained_float", "page_bool", "page_count", "offset",
    "returned_count", "has_more", "wrong_order", "position_join", "private_source", "private_pointer", "private_file",
    "bound_null", "bound_token", "bound_hex", "bound_nonfinite", "bound_order", "unit_basis", "unit_text",
    "unavailable_values", "present_null", "implicit_missing", "unavailable_snapshot", "retained_less_than_present"])
def test_closed_view_rejects_shape_scalar_private_and_page_conflicts_without_reads(saved_only, fault):
    view = tools.project_flux_balance_model_result(saved_only["edit"], selector=selector("reactions", "effective"))
    first = view["rows"][0]
    if fault == "extra": view["operation_key"] = "private"
    elif fault == "version": view["version"] = "other"
    elif fault == "selector_extra": view["selector"]["resource_id"] = "private"
    elif fault == "selector_ordinal_bool": view["selector"]["ordinals"] = [True]
    elif fault == "selector_ordinal_float": view["selector"]["ordinals"] = [0.0]
    elif fault == "row_ordinal_bool": first["ordinal"] = False
    elif fault == "row_ordinal_float": first["ordinal"] = 0.0
    elif fault == "expected_bool": view["population"]["expected_count"] = True
    elif fault == "retained_float": view["population"]["retained_count"] = 4.0
    elif fault == "page_bool": view["page"]["returned_row_count"] = True
    elif fault == "page_count": view["page"]["selected_row_count"] += 1
    elif fault == "offset": view["page"]["offset"] += 1
    elif fault == "returned_count": view["page"]["returned_row_count"] -= 1
    elif fault == "has_more": view["page"]["has_more"] = True
    elif fault == "wrong_order": view["rows"].reverse()
    elif fault == "position_join": first["values"]["position"] = 1
    elif fault == "private_source": first["values"]["lower"]["source"] = {"file": {}, "pointer": "/private"}
    elif fault == "private_pointer": first["values"]["annotation_pointer"] = "/private"
    elif fault == "private_file": view["issues"] = [{**tools._public(tools._issue("schema_invalid", "return", "/view")), "detail_file": {}}]
    elif fault == "bound_null": first["values"]["lower"]["value"] = None
    elif fault == "bound_token": first["values"]["lower"]["native_token"] = "not-a-number"
    elif fault == "bound_hex": first["values"]["lower"]["float_hex"] = "0x1p+1"
    elif fault == "bound_nonfinite": first["values"]["lower"]["value"] = float("inf")
    elif fault == "bound_order":
        first["values"]["lower"].update(value=1000, native_token=None, float_hex=None)
    elif fault == "unit_basis": first["values"]["flux_unit"]["basis"] = "guessed"
    elif fault == "unit_text": first["values"]["flux_unit"].update(basis="native_model", native_text=None)
    elif fault == "unavailable_values": first["availability"] = "unavailable"
    elif fault == "present_null": first["values"] = None
    elif fault == "implicit_missing": first.update(availability="unavailable", values=None)
    elif fault == "unavailable_snapshot": view["population"]["snapshot_available"] = False
    else: view["population"]["retained_count"] = 1; view["selector"]["ordinals"] = [0, 1, 2, 3]
    with pytest.raises(ValueError):
        tools.validate_flux_balance_model_view(view)


@pytest.mark.parametrize("fault", ["duplicate_values", "singleton_missing", "metadata_count", "objective_terms", "number_missing",
    "objective_private_source", "objective_private_flux_expression_pointer", "feature_extra", "feature_kind", "issue_code"])
def test_collection_specific_scalar_population_and_public_qualifications(saved_only, fault):
    collection = "objective" if fault.startswith("objective_") or fault == "number_missing" else "model"
    view = tools.project_flux_balance_model_result(saved_only["edit"],
        selector=selector(collection, "effective", ordinals=[0, 0] if fault == "duplicate_values" else [0]))
    first = view["rows"][0]
    if fault == "duplicate_values": first["values"]["model_name"] = "different repeated cell"
    elif fault == "singleton_missing":
        for row in view["rows"]: row.update(availability="unavailable", values=None)
    elif fault == "metadata_count": first["values"]["population"]["reactions"] = None
    elif fault == "objective_terms": first["values"]["terms"].append(deepcopy(first["values"]["terms"][0]))
    elif fault == "number_missing": first["values"]["native_constant"]["missing_reason"] = "not_returned"
    elif fault == "objective_private_source": first["values"]["source"] = {"file": {}, "pointer": "/private"}
    elif fault == "objective_private_flux_expression_pointer": first["values"]["flux_expression_pointer"] = "/private/expression"
    elif fault.startswith("feature"):
        view["source_features"] = [{"kind": "default_bound", "disposition": "transformed"}]
        if fault == "feature_extra": view["source_features"][0]["source"] = {}
        else: view["source_features"][0]["kind"] = "arbitrary_native_warning"
    else:
        view["issues"] = [tools._public(tools._issue("schema_invalid", "return", "/view"))]
        view["issues"][0]["code"] = "arbitrary_native_warning"
    with pytest.raises(ValueError):
        tools.validate_flux_balance_model_view(view)


def test_qualified_public_issues_features_and_schema_are_detached_without_payloads(saved_only):
    view = tools.project_flux_balance_model_result(saved_only["inspect"], selector=selector("model"))
    view["source_features"] = [{"kind": "default_bound", "disposition": "transformed"}]
    view["issues"] = [tools._public(tools._issue("loader_default_applied", "load", "/model"))]
    expected = canonical(view)
    validated = tools.validate_flux_balance_model_view(view)
    assert canonical(validated) == expected
    validated["source_features"][0]["disposition"] = "unknown"
    assert canonical(view) == expected
    schema = tools.flux_balance_model_schema("View")
    assert len(schema["oneOf"]) == 8
    assert [item["properties"]["selector"]["properties"]["collection"]["const"] for item in schema["oneOf"]] == list(COLLECTIONS)
    assert all(item["additionalProperties"] is False for item in schema["oneOf"])
    schema["oneOf"].clear()
    assert len(tools.flux_balance_model_schema("View")["oneOf"]) == 8
