"""Pure engineering/document-example controls; these make no Enrichr requests."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import enrichr_contracts as core


SOURCE = "source_" + "a" * 24
LIBRARY = "literal library/~name"


def request(**updates):
    value = {"version": core.REQUEST_VERSION, "protocol_profile": "speedrichr_v1",
        "library": LIBRARY, "genes": ["CUL2", "INSR", "CUL2", "insr"],
        "identifier_policy": "literal_no_mapping", "species_context": "caller supplied human",
        "description": "engineering input, not a submitted biological query",
        "background": {"policy": "supplied", "genes": ["CUL2", "INSR", "OTHER"]},
        "native_statistic_profile": "documented_odds_v1"}
    return {**value, **updates}


def selector(offset=0, limit=20):
    return {"version": core.SELECTOR_VERSION, "offset": offset, "limit": limit}


def native_row(rank=1, term="literal term", p=0.01, slot3=2.5, overlaps=None):
    return [rank, term, p, slot3, 11.0, ["CUL2"] if overlaps is None else overlaps, 0.04, 0, 0]


def parse(rows, *, selected_request=None, complete=True):
    selected_request = request() if selected_request is None else selected_request
    return core.parse_enrichr_response(json.dumps({LIBRARY: rows}).encode(),
        request=selected_request, response_complete=complete, media_type="application/json")


def projected(sheet, selected=None):
    return core.project_enrichr_return(core.calculate_enrichr_components(sheet,
        selector=selector() if selected is None else selected), source_ref=SOURCE)


def test_request_preserves_literal_order_duplicates_case_background_and_context():
    original = request(background={"policy": "supplied", "genes": ["BG"]}, species_context=None,
        description="description\nkept as supplied")
    actual = core.validate_enrichr_request(original)
    assert actual == original and actual is not original
    assert actual["genes"] == ["CUL2", "INSR", "CUL2", "insr"]
    assert actual["background"] == {"policy": "supplied", "genes": ["BG"]}
    actual["genes"].append("detached")
    assert original["genes"] == ["CUL2", "INSR", "CUL2", "insr"]
    native = request(protocol_profile="standard_enrichr_v1",
        background={"policy": "service_native", "genes": None})
    assert core.validate_enrichr_request(native) == native
    assert core.validate_enrichr_request(request(genes=[" A "]))["genes"] == [" A "]


@pytest.mark.parametrize("changes", [{"genes": []}, {"background": {"policy": "supplied", "genes": []}}])
def test_empty_uploads_are_rejected_and_never_select_a_service_background(changes):
    assert not Draft202012Validator(core.ENRICHR_REQUEST_SCHEMA).is_valid(request(**changes))
    with pytest.raises(ValueError):
        core.validate_enrichr_request(request(**changes))


@pytest.mark.parametrize("changes", [
    {"version": "other"}, {"protocol_profile": "guessed"}, {"library": ""},
    {"library": "lib\nother"}, {"genes": ["A\nB"]}, {"genes": ["A\rB"]},
    {"genes": [""]}, {"genes": [None]}, {"genes": [1]}, {"genes": [1.0]}, {"genes": [True]},
    {"genes": ("A",)}, {"identifier_policy": "auto_map"}, {"species_context": 9606},
    {"description": None}, {"native_statistic_profile": "z_from_sign"}, {"extra": 1},
    {"background": {"policy": "service_native", "genes": []}},
    {"background": {"policy": "supplied", "genes": None}},
    {"protocol_profile": "standard_enrichr_v1"},
])
def test_invalid_request_never_normalizes_or_inserts_a_background(changes):
    with pytest.raises(ValueError):
        core.validate_enrichr_request(request(**changes))


@pytest.mark.parametrize("changes", [
    {"offset": True}, {"offset": 1.0}, {"offset": -1}, {"limit": False},
    {"limit": 2.0}, {"limit": -1}, {"extra": 0}, {"version": "other"},
])
def test_invalid_local_selector_rejects_type_aliases_and_unknown_fields(changes):
    with pytest.raises(ValueError, match="enrichr_selector_invalid"):
        core.validate_enrichr_selector({**selector(), **changes})


def test_documented_nine_field_example_retains_values_and_declared_meaning():
    # Official API example values; this is retained document data, not a live response.
    row = [1, "VDR 24787735 ChIP-Seq THP-1 Human", 0.000842494387359289,
        13.092592592592593, 92.6843425047622,
        ["P2RX7", "ROBO2", "CUX1", "INSR", "CRYZL1", "CUL2", "TMCC1"],
        0.5054966324155734, 0, 0]
    sheet = parse([row])
    kept = sheet["table"]["rows"][0]
    assert kept["ordinal"] == 0
    assert kept["statistics"]["rank"]["value"] == 1
    assert kept["statistics"]["rank"]["unit"] == "ordinal_1_based"
    assert kept["statistics"]["p_value"]["value"] == row[2]
    assert kept["statistics"]["adjusted_p_value"]["value"] == row[6]
    assert kept["statistics"]["statistic_3"]["value"] == row[3]
    assert kept["statistic_3_interpretation"] == {
        "profile": "documented_odds_v1", "declared_meaning": "odds_ratio", "meaning": "odds_ratio",
        "claimed_client_label": None, "basis": "documentation", "server_version_verified": False,
        "qualification_codes": ["declared_documentation_interpretation"]}
    assert kept["pointer"] == "/literal library~1~0name/0"
    assert kept["overlap"]["returned_entry_count"] == 7
    assert all(value == {"state": "unknown", "value": None} for value in sheet["population"].values())


@pytest.mark.parametrize("profile,slot,width,meaning,code", [
    ("documented_odds_v1", 2.5, 9, "odds_ratio", "declared_documentation_interpretation"),
    ("documented_odds_v1", -1.8, 9, "unknown", "profile_value_conflict"),
    ("documented_odds_v1", 2.5, 7, "unknown", "profile_width_conflict"),
    ("gget_z_label_v1", 2.5, 9, "unknown", "interface_definition_conflict"),
    ("gget_z_label_v1", -1.8, 7, "unknown", "interface_definition_conflict"),
    ("uninterpreted", 2.5, 9, "unknown", "statistic_uninterpreted"),
    ("uninterpreted", -1.8, 7, "unknown", "statistic_uninterpreted"),
])
def test_statistic_profile_is_explicit_and_never_inferred_from_sign(profile, slot, width, meaning, code):
    row = native_row(slot3=slot)[:width]
    kept = parse([row], selected_request=request(native_statistic_profile=profile))["table"]["rows"][0]
    assert kept["statistics"]["statistic_3"]["value"] == slot
    assert kept["statistics"]["p_value"]["value"] == 0.01
    assert kept["statistic_3_interpretation"]["meaning"] == meaning
    assert code in kept["statistic_3_interpretation"]["qualification_codes"]
    assert kept["statistic_3_interpretation"]["claimed_client_label"] == (
        "z_score" if profile == "gget_z_label_v1" else None)
    if width == 7:
        assert kept["statistics"]["old_p_value"]["state"] == "missing"
        assert kept["statistics"]["old_adjusted_p_value"]["value"] is None


def test_mixed_and_malformed_rows_keep_every_original_identity_and_other_valid_statistics():
    rows = [native_row(7), None, "native malformed row", True, {"unexpected": [1]}, 17,
        [False, None, 0, -3, "bad score", ["A", "A", 7, None, {"bad": True}], 0.4],
        native_row(7, term="same rank retained") + ["extra", {"nested": True}]]
    sheet = parse(rows)
    assert sheet["table"]["returned_row_count"] == 8
    kept = sheet["table"]["rows"]
    assert [row["ordinal"] for row in kept] == list(range(8))
    assert [row["native_kind"] for row in kept] == ["array", "null", "string", "boolean", "object", "number", "array", "array"]
    assert kept[2]["native_row_value"]["string_value"] == "native malformed row"
    assert kept[3]["native_row_value"]["boolean_value"] is True
    assert kept[5]["native_row_value"]["number_lexeme"] == "17"
    assert kept[6]["statistics"]["rank"]["state"] == "invalid"
    assert kept[6]["statistics"]["p_value"]["value"] == 0
    assert kept[6]["statistics"]["adjusted_p_value"]["value"] == 0.4
    assert [entry["ordinal"] for entry in kept[6]["overlap"]["entries"]] == list(range(5))
    assert [entry["state"] for entry in kept[6]["overlap"]["entries"]] == ["present", "present", "invalid", "null", "invalid"]
    assert kept[7]["native_width"] == 11
    assert kept[7]["native_cells"][10]["kind"] == "object"
    assert "extra_columns_retained" in kept[7]["qualification_codes"]
    assert [row["ordinal"] for row in projected(sheet)[core.ROW_SOURCE]] == list(range(8))


@pytest.mark.parametrize("token,state,reason", [
    ("0", "present", None), ("-0.0", "present", None),
    ("1e-400", "unrepresentable", "numeric_underflow"),
    ("1e400", "unrepresentable", "numeric_overflow"),
    ("NaN", "nonfinite", "nan"), ("Infinity", "nonfinite", "positive_infinity"),
    ("-Infinity", "nonfinite", "negative_infinity"),
    ("true", "invalid", "expected_native_number"), ("\"0.01\"", "invalid", "expected_native_number"),
    ("\"Infinity\"", "invalid", "expected_native_number"),
    ("-0.01", "invalid", "probability_out_of_range"), ("1.01", "invalid", "probability_out_of_range"),
    ("null", "null", "native_null"),
])
def test_native_numeric_tokens_are_never_coerced_clamped_or_rounded(token, state, reason):
    raw = (json.dumps(LIBRARY) + ":[[1,\"term\"," + token + ",2,9,[\"A\"],0.5,0,0]]}").encode()
    sheet = core.parse_enrichr_response(b"{" + raw, request=request(), response_complete=True)
    cell = sheet["table"]["rows"][0]["statistics"]["p_value"]
    assert (cell["state"], cell["reason"]) == (state, reason)
    assert cell["value"] == (0 if token in ("0", "-0.0") else None)
    if token not in ("true", "\"0.01\"", "\"Infinity\"", "null"):
        assert cell["number_lexeme"] == token
    if token in ("NaN", "Infinity", "-Infinity"):
        assert "nonstandard_numeric_token" in sheet["qualification_codes"]
    assert sheet["table"]["rows"][0]["statistics"]["adjusted_p_value"]["value"] == 0.5
    assert projected(sheet)[core.ROW_SOURCE][0]["statistics"]["p_value"] == cell


@pytest.mark.parametrize("native_rank", [True, 1.0, 0, -1])
def test_native_rank_requires_a_positive_json_integer_and_preserves_other_cells(native_rank):
    row = parse([native_row(rank=native_rank)])["table"]["rows"][0]
    assert row["statistics"]["rank"]["state"] == "invalid"
    assert row["statistics"]["rank"]["value"] is None
    assert row["statistics"]["p_value"]["value"] == 0.01
    assert row["statistics"]["adjusted_p_value"]["value"] == 0.04


def test_native_precision_and_observed_zero_keep_exact_lexemes():
    raw = ('{"literal library/~name":[[1,"literal Infinity and NaN",0.12345678901234567890123456789,'
        '2.00000000000000000000000000001,0,["A","A"],0,0,0]]}').encode()
    sheet = core.parse_enrichr_response(raw, request=request(), response_complete=True)
    cells = sheet["table"]["rows"][0]["native_cells"]
    assert cells[2]["number_lexeme"] == "0.12345678901234567890123456789"
    assert cells[3]["number_lexeme"] == "2.00000000000000000000000000001"
    assert cells[4]["number_value"] == 0
    assert sheet["table"]["rows"][0]["term"]["value"] == "literal Infinity and NaN"
    assert projected(sheet)[core.ROW_SOURCE][0]["overlap"]["returned_entry_count"] == 2
    assert "overlap_fraction" not in json.dumps(sheet)


@pytest.mark.parametrize("raw,state,count,response_state", [
    (b"{}", "missing", None, "decoded"),
    (b'{"literal library/~name":null}', "null", None, "decoded"),
    (b'{"literal library/~name":[]}', "empty", 0, "decoded"),
    (b'{"literal library/~name":{}}', "invalid", None, "decoded"),
    (b'{"literal library/~name":false}', "invalid", None, "decoded"),
    (b"[]", "invalid", None, "decoded"),
    (b'{"literal library/~name":[', "unavailable", None, "invalid_json"),
    (b"\xff", "unavailable", None, "invalid_utf8"),
    (b'{"literal library/~name":[],"literal library/~name":[]}', "unavailable", None, "invalid_json"),
    (b'{"literal library/~name":[[1,"\\ud800"]]}', "unavailable", None, "invalid_json"),
])
def test_response_table_missingness_and_invalid_data_do_not_become_empty(raw, state, count, response_state):
    sheet = core.parse_enrichr_response(raw, request=request(), response_complete=True)
    assert (sheet["table"]["state"], sheet["table"]["returned_row_count"]) == (state, count)
    assert sheet["response"]["state"] == response_state
    table = projected(sheet)[core.TABLE_SOURCE][0]
    assert table["captured_returned_row_count"] == count
    assert table["window"]["selected_row_count"] == (0 if count == 0 else None)


def test_incomplete_capture_qualifies_preserved_rows_and_never_claims_testing_family():
    complete = parse([native_row(), native_row(2)])
    incomplete = parse([native_row(), native_row(2)], complete=False)
    assert incomplete["table"] == complete["table"]
    assert incomplete["response"]["complete"] is False
    assert incomplete["qualification_codes"] == ["response_incomplete"]
    table = projected(incomplete, selector(0, 1))[core.TABLE_SOURCE][0]
    assert table["captured_returned_row_count"] == 2
    assert table["window"]["selected_row_count"] == 1
    assert table["window"]["all_captured_rows_selected"] is False
    assert table["population"]["testing_family_size"] == {"state": "unknown", "value": None}
    assert table["population"]["effective_universe"] == {"state": "unknown", "value": None}


@pytest.mark.parametrize("offset,limit,ordinals,next_offset,has_more", [
    (0, 2, [0, 1], 2, True), (2, 3, [2, 3], None, False),
    (0, 0, [], None, True), (20, 5, [], None, False), (0, 50, [0, 1, 2, 3], None, False),
])
def test_local_windows_preserve_native_order_and_do_not_sort_by_rank(offset, limit, ordinals, next_offset, has_more):
    sheet = parse([native_row(9), native_row(1), native_row(9), native_row(3)])
    components = core.calculate_enrichr_components(sheet, selector=selector(offset, limit))
    assert components["window"]["selected_ordinals"] == ordinals
    assert components["window"]["next_offset"] == next_offset
    assert components["window"]["has_more_captured_rows"] is has_more
    assert [row["ordinal"] for row in projected(sheet, selector(offset, limit))[core.ROW_SOURCE]] == ordinals
    assert sheet["table"]["returned_row_count"] == 4


def test_saved_selection_and_projection_are_detached_and_need_no_external_files_or_statistical_software(monkeypatch):
    sheet = parse([native_row(), native_row(2)])
    original = json.dumps(sheet, sort_keys=True)
    imported = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"scipy", "numpy", "requests", "gget", "statsmodels"}:
            raise AssertionError("saved Enrichr rows must not run statistical/API software")
        return imported(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved Enrichr rows must not read files or acquire inputs")
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "__import__", guarded_import)
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(core, "parse_enrichr_response", forbidden)
        first = core.calculate_enrichr_components(sheet, selector=selector(1, 1))
        values = core.project_enrichr_return(first, source_ref=SOURCE)
        second = core.calculate_enrichr_components(deepcopy(sheet), selector=selector(1, 1))
        assert first == second
    assert json.dumps(sheet, sort_keys=True) == original
    values[core.ROW_SOURCE][0]["statistics"]["p_value"]["value"] = 0.99
    assert sheet["table"]["rows"][1]["statistics"]["p_value"]["value"] == 0.01
    assert first["rows"][0]["statistics"]["p_value"]["value"] == 0.01


@pytest.mark.parametrize("location", ["native_value", "request", "extra", "raw_bytes", "component_cell"])
def test_tampered_internal_sheet_or_component_is_rejected(location):
    sheet = parse([native_row()])
    if location == "component_cell":
        components = core.calculate_enrichr_components(sheet, selector=selector())
        components["rows"][0]["statistics"]["p_value"]["value"] = 0.9
        with pytest.raises(ValueError, match="consistency_conflict"):
            core.project_enrichr_return(components, source_ref=SOURCE)
        return
    if location == "native_value":
        sheet["table"]["rows"][0]["statistics"]["p_value"]["value"] = 0.9
    elif location == "request":
        sheet["request"]["library"] = "other"
    elif location == "extra":
        sheet["table"]["rows"][0]["extra"] = "fabricated"
    else:
        sheet["response"]["raw_base64"] = "not base64!"
    with pytest.raises(ValueError):
        core.validate_enrichr_sheet(sheet)


def test_public_fact_schemas_are_closed_literal_values_without_private_bodies_or_grants():
    sheet = parse([native_row(overlaps=["A", None, True]), False, native_row(3)[:7]])
    values = projected(sheet)
    schemas = core.enrichr_fact_sources()
    def closed(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
            for child in node["properties"].values():
                closed(child)
        if node.get("type") == "array":
            closed(node["items"])
    for name, definition in schemas.items():
        Draft202012Validator(definition["report_schema"]).validate(values[name])
        closed(definition["report_schema"])
        assert definition["report_schema"]["x-source"] == name
    text = json.dumps(values)
    assert all(key not in text for key in ("raw_base64", "description", "request_ref", "artifact_ref", "operation_key"))
    assert set(values) == {core.TABLE_SOURCE, core.ROW_SOURCE}
    assert {row["source_ref"] for rows in values.values() for row in rows} == {SOURCE}
    altered = deepcopy(values[core.ROW_SOURCE]); altered[0]["invented"] = "summary"
    with pytest.raises(Exception):
        Draft202012Validator(schemas[core.ROW_SOURCE]["report_schema"]).validate(altered)
    with pytest.raises(ValueError, match="enrichr_return_source_invalid"):
        core.project_enrichr_return(core.calculate_enrichr_components(sheet, selector=selector()), source_ref="arbitrary")
