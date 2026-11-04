"""Pure boundary controls over exact retained231 engineered-wrapper values.

The Source constant exercises lexical schemas only; no Source, custody or live
predictor execution is manufactured. The numerical owner is never rerun here.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import protein_disorder_measurements as core
from gene_annotation_episode import protein_disorder_result_contracts as contracts
from gene_annotation_episode.domain import canonical


SOURCE = "source_" + "a" * 24
RETAINED_SHA256 = "656d50b37936442a62d9b9608d5519812c2c2d6efd657b465a32cd80748911bc"
CASES = ("ordinary", "duplicate", "unsorted", "nonfinite", "skipped", "empty", "http_error",
    "threshold_unknown", "null_input", "threshold_outside")


@lru_cache(maxsize=1)
def retained():
    raw = (Path(__file__).parent / "fixtures/protein_disorder231/retained_values.json").read_bytes()
    assert len(raw) == 253166 and hashlib.sha256(raw).hexdigest() == RETAINED_SHA256
    value = json.loads(raw)
    assert value["schema"] == "retained_protein_disorder231_values_v1"
    assert value["provenance"]["original_report_sha256"] == "6022a690a2828e199bd906e52e3853cd7dadbe23db7055f86560fb7c5004e464"
    assert value["provenance"]["actual_scientific_service_requests"] == 0
    assert [case["case"] for case in value["cases"]] == list(CASES)
    return {case["case"]: case for case in value["cases"]}


def selection(*rows):
    return dict(version=contracts.SELECTION_VERSION, rows=list(rows))


def request(kind, fields, **identity):
    return dict(row_id=dict(kind=kind, **identity), fields=list(fields))


def prepared(*, case="ordinary", rows=None):
    original = deepcopy(retained()[case])
    sheet, components = original["sheet"], original["components"]
    selected = selection(*(rows or []))
    arguments = dict(mode="calculate_saved", result_ref=SOURCE, selection=selected)
    return arguments, sheet, components


def predict_arguments():
    args, sheet, _ = prepared()
    return dict(mode="predict", protein_sequence=sheet["inputs"]["protein_sequence"],
        threshold=sheet["inputs"]["threshold"], max_bytes=65536, selection=args["selection"])


def packet(**kwargs):
    arguments, sheet, components = prepared(**kwargs)
    return contracts.ordinary_disorder_packet(arguments=arguments, sheet=sheet, components=components)


def test_selected_native_rows_populations_operands_and_regions_keep_distinct_meanings():
    selected = [request("summary", ["disordered_percentage", "descriptive_mean_score", "unique_input_coverage"]),
        request("residue", ["score_token", "score_value", "native_threshold_comparison"], row_ordinal=3),
        request("region", ["start_1based", "end_1based", "length_residues", "member_row_ordinals"], region_ordinal=0)]
    value = packet(rows=selected)
    context, rows = value["values"]["context"], value["values"]["rows"]
    assert [row["value"] for row in rows[:3]] == [75, pytest.approx(.575), 1]
    assert [item["value"] for item in rows[0]["operands"]] == [3, 4]
    assert [item["value"] for item in rows[1]["operands"]] == [pytest.approx(2.3), 4]
    assert [item["value"] for item in rows[2]["operands"]] == [4, 4]
    assert [row["value"] for row in rows[3:]] == [".9", .9, True, 1, 2, 2, [0, 1]]
    assert context["source_equivalent"]["thresholded_row_count"] == 3
    assert context["source_equivalent"]["region_count"] == 1
    assert context["summary"]["scientific_service_execution_verified"] is False
    assert context["definitions"] == core._definitions()
    assert "not function correctness probability" in context["definitions"]["native_score"]
    assert rows[3]["unit"] is None and rows[4]["unit"] == "dimensionless_predictor_score"


def test_empty_selection_keeps_full_context_definitions_input_and_selected_data_identity():
    args, sheet, components = prepared()
    before = deepcopy((args, sheet, components))
    value = contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components)
    assert (args, sheet, components) == before
    assert value["values"]["rows"] == []
    context = value["values"]["context"]
    assert context["input"] == {key: sheet["inputs"][key] for key in ("protein_sequence", "input_ref", "input_mapping")}
    assert context["input"]["protein_sequence"] == " A-c\nD2E" and context["input"]["input_mapping"] is not None
    assert context["cleaning"]["cleaned_sequence"] == "AcDE"
    assert context["cleaning"]["original_character_indices"] == [1, 3, 5, 7]
    assert context["summary"]["original_symbol_count"] == 8
    assert context["summary"]["cleaned_symbol_count"] == 4
    assert context["source_profile"]["identity_kind"] == "declared_not_execution_receipt"
    assert context["source_profile"]["request"] == dict(url=contracts.ENDPOINT, iupred2="long", anchor2="no")
    assert context["native_log"] == components["native_log"]
    assert context["definitions"] == components["definitions"]
    assert value["values"]["data_identity"] == dict(sheet_schema=core.SHEET_SCHEMA,
        components_schema=core.COMPONENTS_SCHEMA,
        sheet_canonical_sha256=hashlib.sha256(canonical(sheet).encode()).hexdigest(),
        components_canonical_sha256=hashlib.sha256(canonical(components).encode()).hexdigest())


def test_original_order_duplicate_positions_and_repeated_requests_are_not_deduplicated():
    item = request("residue", ["score_value", "duplicate_native_position"], row_ordinal=1)
    value = packet(case="duplicate", rows=[item, item,
        request("summary", ["source_parsed_row_count", "descriptive_mean_denominator_rows",
            "unique_usable_input_position_count", "input_coverage_denominator_symbols"])])
    rows = value["values"]["rows"]
    assert [row["value"] for row in rows] == [.8, True, .8, True, 3, 3, 2, 2]
    assert rows[:2] == rows[2:4]
    assert value["selection"]["rows"][:2] == [item, item]


def test_nonfinite_native_tokens_and_out_of_domain_values_remain_separate_from_descriptive_mean():
    value = packet(case="nonfinite",
        rows=[request("residue", ["score_token", "score_kind", "score_value", "native_threshold_comparison"], row_ordinal=0),
            request("residue", ["score_value", "usable_for_descriptive_mean"], row_ordinal=3),
            request("summary", ["thresholded_row_count", "parsed_row_denominator", "descriptive_mean_score",
                "descriptive_mean_denominator_rows"])])
    rows = value["values"]["rows"]
    assert [row["value"] for row in rows] == ["NaN", "nan", None, False, 1.2, False, 3, 5, .8, 1]
    assert rows[2]["value_state"] == "stored_null"
    assert rows[0]["unit"] is None
    assert rows[2]["scientific_qualifiers"]["value"]["native_score_kind"] == "nan"
    assert rows[4]["scientific_qualifiers"]["value"]["cells"]["usable_for_descriptive_mean"] is False
    assert value["values"]["context"]["summary"]["unique_input_coverage"] == .2


@pytest.mark.parametrize("case,expected_count,expected_state", [
    ("null_input", None, "population_unknown"),
    ("empty", 0, "early_no_parsed_rows"),
    ("http_error", None, "population_unknown"),
])
def test_missing_empty_and_failed_native_views_do_not_become_zero_predictions(case, expected_count, expected_state):
    value = packet(case=case,
        rows=[request("summary", ["source_parsed_row_count", "thresholded_row_count", "disordered_percentage", "region_count"]),
            request("region", ["start_1based"], region_ordinal=0)])
    rows = value["values"]["rows"]
    assert [row["value"] for row in rows] == [expected_count, None, None, None, None]
    assert rows[-1]["value_state"] == "path_missing"
    assert value["values"]["context"]["source_equivalent"]["stage"] == expected_state
    assert value["values"]["context"]["definitions"]["uncertainty"] == core._definitions()["uncertainty"]


@pytest.mark.parametrize("case,threshold,stage,hits", [("threshold_unknown", None, "threshold_unknown", None),
    ("threshold_outside", 2, "source_equivalent_postprocessing", 0)])
def test_unknown_and_out_of_domain_thresholds_remain_literal_qualified_inputs(case, threshold, stage, hits):
    value = packet(case=case,
        rows=[request("summary", ["descriptive_mean_score", "thresholded_row_count"])])
    observed = value["values"]["context"]["parameters"]["threshold"]
    assert observed == threshold and type(observed) is type(threshold)
    assert value["values"]["context"]["source_equivalent"]["stage"] == stage
    assert [row["value"] for row in value["values"]["rows"]] == [.8, hits]


def test_retained_malformed_response_row_ordinal_is_inspectable_without_repair():
    value = packet(case="skipped",
        rows=[request("residue", ["raw_tokens", "source_parse_accepted", "score_value"], row_ordinal=0),
            request("summary", ["source_parsed_row_count", "descriptive_mean_score", "region_count"])])
    rows = value["values"]["rows"]
    assert [row["value"] for row in rows] == [["broken"], False, None, 3, .5, 0]
    assert rows[2]["value_state"] == "path_missing"
    assert value["values"]["context"]["status"] == "partial"


@pytest.mark.parametrize("mode", ["calculate_saved", "read_stored"])
def test_saved_modes_preserve_declared_mapping_opaque_references_without_semantic_grants(mode):
    args, sheet, components = prepared(
        rows=[request("residue", ["source_intervals"], row_ordinal=0)])
    mapping = deepcopy(sheet["inputs"]["input_mapping"])
    args["mode"] = mode
    value = contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components)
    assert value["values"]["context"]["input"]["input_mapping"] == mapping
    assert value["values"]["context"]["mapping"]["supplied"] == mapping
    assert value["values"]["rows"][0]["value"] == components["rows"][0]["cells"]["source_intervals"]
    returned = contracts.project_ordinary_disorder_return(value, SOURCE)
    schema = contracts.protein_disorder_result_schema("Return")
    references = []
    def walk(node, path):
        if isinstance(node, dict):
            if node.get("format") == "reference" or "x-reference-namespace" in node: references.append(path)
            for key, child in node.items(): walk(child, [*path, key])
        elif isinstance(node, list):
            for index, child in enumerate(node): walk(child, [*path, index])
    walk(schema, [])
    assert references == [["properties", "source_ref"]]
    Draft202012Validator(schema).validate(returned)


def test_inline_prediction_does_not_invent_or_accept_supplied_provenance():
    _, sheet, components = prepared()
    args = predict_arguments()
    original = deepcopy((sheet, components))
    with pytest.raises(ValueError, match="inline_input_provenance_conflict"):
        contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components)
    assert (sheet, components) == original


def test_engineered_invalid_mapping_provenance_is_opaque_qualified_data_not_an_inferred_reference_grant():
    value = packet()
    literal = ["invalid supplied mapping", {"slot": "thought_pattern", "evidence": "literal retained data",
        "option_ref": "source_" + "b" * 24, "entry": {"entries": [], "library": "opaque"}}]
    context = value["values"]["context"]
    context["input"]["input_mapping"] = deepcopy(literal)
    context["mapping"] = dict(supplied=deepcopy(literal), available=False, reason="invalid_supplied_mapping")
    before = deepcopy(value)
    # This engineered DTO shape asserts no producing Sheet or current custody.
    assert contracts.validate_ordinary_disorder_packet(value) == before
    assert value["values"]["context"]["mapping"]["supplied"] == literal


@pytest.mark.parametrize("change", [
    lambda v: v.update(output_file="unselected.csv"),
    lambda v: v.pop("threshold"),
    lambda v: v.update(max_bytes=True),
    lambda v: v.update(max_bytes=1.0),
    lambda v: v.update(threshold=True),
    lambda v: v.update(protein_sequence=None),
    lambda v: v.update(mode="run_native"),
])
def test_arguments_are_closed_and_do_not_insert_source_defaults(change):
    args = predict_arguments()
    change(args)
    before = deepcopy(args)
    with pytest.raises(ValueError): contracts.validate_ordinary_disorder_arguments(args)
    assert args == before


@pytest.mark.parametrize("bad", [
    request("residue", ["score_value"], row_ordinal=True),
    request("residue", ["score_value"], row_ordinal=1.0),
    request("residue", ["score_value", "score_value"], row_ordinal=0),
    request("residue", ["confidence"], row_ordinal=0),
    request("summary", []),
    request("unknown", ["score_value"]),
])
def test_selection_rejects_ambiguous_identity_or_unregistered_field_without_coercion(bad):
    with pytest.raises(ValueError): contracts.validate_disorder_selection(selection(bad))


@pytest.mark.parametrize("change", [
    lambda s, c: s["rows"][0]["native_values"].update(position_1based=2),
    lambda s, c: c["summary"].update(cleaned_symbol_count=999),
    lambda s, c: c["source_equivalent"].update(region_count=9),
    lambda s, c: s["source_profile"]["request"].update(url="https://example.invalid/unselected"),
    lambda s, c: c["summary"].update(scientific_service_execution_verified=True),
])
def test_constructor_rejects_supplied_sheet_component_and_identity_join_conflicts(change):
    args, sheet, components = prepared()
    change(sheet, components)
    with pytest.raises(ValueError): contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components)


@pytest.mark.parametrize("change", [
    lambda p: p["values"]["rows"][0].update(unit="function_confidence"),
    lambda p: p["values"]["rows"][0].update(source_pointer="/unselected"),
    lambda p: p["values"]["rows"][0]["operands"].reverse(),
    lambda p: p["values"]["rows"][0]["operands"].pop(),
    lambda p: p["values"]["rows"][0]["operands"][1].update(value=999),
    lambda p: p["values"]["rows"][0].update(value=999),
    lambda p: p["values"]["rows"][0].update(value_state="stored_null"),
    lambda p: p["values"]["rows"].reverse(),
    lambda p: p["values"]["data_identity"].update(sheet_canonical_sha256="wrong"),
    lambda p: p.update(version="unrecognized"),
])
def test_public_validation_rejects_path_unit_operand_order_value_state_and_selection_conflicts(change):
    value = packet(rows=[request("summary", ["descriptive_mean_score", "disordered_percentage"])])
    change(value)
    with pytest.raises(ValueError): contracts.validate_ordinary_disorder_packet(value)


@pytest.mark.parametrize("change", [
    lambda p: p["values"]["rows"][0]["scientific_qualifiers"]["value"].update(row_ordinal=3),
    lambda p: p["values"]["rows"][0]["scientific_qualifiers"]["value"].update(native_score_kind="nan"),
    lambda p: p["values"]["rows"][1]["scientific_qualifiers"]["value"]["cells"].update(usable_for_descriptive_mean=False),
])
def test_residue_qualifiers_cannot_change_identity_classified_missingness_or_conflict_between_fields(change):
    value = packet(rows=[request("residue", ["score_value", "score_token"], row_ordinal=0)])
    change(value)
    with pytest.raises(ValueError): contracts.validate_ordinary_disorder_packet(value)


@pytest.mark.parametrize("case", CASES)
def test_retained_packet_construction_validation_projection_and_fact_schema_do_no_numerical_work(case, monkeypatch):
    import builtins
    from pathlib import Path
    import socket
    import subprocess
    args, sheet, components = prepared(case=case, rows=[request("summary", ["descriptive_mean_score", "disordered_percentage"]),
        request("residue", ["score_value", "score_token"], row_ordinal=0)])
    value = contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components)
    before = deepcopy(value)
    def forbidden(*args, **kwargs): raise AssertionError("pure disorder boundary attempted external or numerical work")
    with monkeypatch.context() as guarded:
        for name in ("build_disorder_sheet", "calculate_disorder_components", "_response", "_csv"):
            guarded.setattr(core, name, forbidden)
        guarded.setattr(builtins, "open", forbidden)
        guarded.setattr(Path, "read_bytes", forbidden)
        guarded.setattr(socket, "socket", forbidden)
        guarded.setattr(subprocess, "Popen", forbidden)
        assert contracts.ordinary_disorder_packet(arguments=args, sheet=sheet, components=components) == before
        assert contracts.validate_ordinary_disorder_packet(value) == before
        returned = contracts.project_ordinary_disorder_return(value, SOURCE)
        assert contracts.validate_ordinary_disorder_return(returned) == returned
        schema = contracts.ordinary_disorder_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
        Draft202012Validator(schema).validate([returned])
    assert value == before


@pytest.mark.parametrize("source", [None, "artifact_" + "a" * 64, "source_wrong", "source_" + "G" * 24])
def test_return_requires_only_an_actual_source_reference_syntax_without_creating_one(source):
    with pytest.raises(ValueError, match="source_required"):
        contracts.project_ordinary_disorder_return(packet(), source)


def test_schemas_are_detached_closed_and_declaratively_constrain_units_and_denominator_geometry():
    value = packet(rows=[request("summary", ["descriptive_mean_score", "disordered_percentage"])])
    returned = contracts.project_ordinary_disorder_return(value, SOURCE)
    schema = contracts.protein_disorder_result_schema("Return")
    validator = Draft202012Validator(schema)
    validator.validate(returned)
    bad = deepcopy(returned); bad["values"]["rows"][0]["operands"].reverse()
    assert not validator.is_valid(bad)
    bad = deepcopy(returned); bad["values"]["rows"][0]["unit"] = "probability_of_function"
    assert not validator.is_valid(bad)
    schema["properties"]["version"]["const"] = "mutated"
    assert contracts.protein_disorder_result_schema("Return")["properties"]["version"]["const"] == contracts.PACKET_VERSION
    assert set(contracts.protein_disorder_result_schema("Arguments")["anyOf"][0]["properties"]) == {
        "mode", "protein_sequence", "threshold", "max_bytes", "selection"}


def test_every_exported_schema_conforms_to_its_declared_draft_before_validating_instances():
    for kind in ("Selection", "Arguments", "Packet", "Return"):
        Draft202012Validator.check_schema(contracts.protein_disorder_result_schema(kind))
    Draft202012Validator.check_schema(
        contracts.ordinary_disorder_fact_sources()[contracts.FACT_SOURCE]["report_schema"])


@pytest.mark.parametrize("change", [
    lambda rows: rows[0]["operands"].append(deepcopy(rows[1]["operands"][0])),
    lambda rows: rows[2]["operands"].append(deepcopy(rows[1]["operands"][0])),
    lambda rows: rows[3]["operands"].append(deepcopy(rows[1]["operands"][0])),
    lambda rows: rows[1]["operands"].pop(),
    lambda rows: rows[1]["operands"].reverse(),
    lambda rows: rows[1]["operands"].append(deepcopy(rows[1]["operands"][0])),
])
def test_declared_schema_keeps_zero_operand_rows_empty_and_ratio_operands_ordered(change, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("declarative operand control attempted scientific work")
    for name in ("build_disorder_sheet", "calculate_disorder_components", "_response", "_csv"):
        monkeypatch.setattr(core, name, forbidden)
    value = packet(rows=[request("summary", ["source_parsed_row_count", "descriptive_mean_score"]),
        request("residue", ["score_value"], row_ordinal=0),
        request("region", ["length_residues"], region_ordinal=0)])
    returned = contracts.project_ordinary_disorder_return(value, SOURCE)
    schema = contracts.protein_disorder_result_schema("Return")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(returned)
    assert [len(row["operands"]) for row in returned["values"]["rows"]] == [0, 2, 0, 0]
    changed = deepcopy(returned)
    change(changed["values"]["rows"])
    assert not validator.is_valid(changed)
    assert contracts.validate_ordinary_disorder_return(returned) == returned
