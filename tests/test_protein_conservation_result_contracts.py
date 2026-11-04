"""Supplied engineering JSON tests, without a native producer or calculation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import protein_conservation_result_contracts as contracts
from gene_annotation_episode import phylogeny_calculators, phylogeny_formats
from gene_annotation_episode import phylogeny_calculation_contracts as numerical_contracts


FIXTURE = Path(__file__).parent / "fixtures/protein_conservation/supplied_alignment.json"
FIXTURE_SHA256 = "09fca54ed15e79114e7f8d167ada2b6dad584d30b9aa67554b9c6ab1454b12be"
SOURCE = "source_" + "a" * 24  # Lexical DTO operand only; no Source is created.


@pytest.fixture
def supplied():
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    value = json.loads(raw)
    assert value["provenance"]["kind"] == "supplied_engineering_json"
    assert value["provenance"]["actual_native_execution"] is False
    assert value["provenance"]["producer_authenticated"] is False
    return value


def build(supplied, **changed):
    keys = ("alignment", "population_request", "population", "components", "input_record",
            "native_execution", "associations", "selection", "issues")
    arguments = {key: deepcopy(supplied[key]) for key in keys}
    arguments.update(changed)
    return contracts.conservation_public_value(**arguments)


def forbid_science(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("contract projection attempted parsing or calculation")
    for module, names in ((phylogeny_formats, ("parse_aligned_fasta",)),
            (phylogeny_calculators, ("literal_site_conservation", "alignment_components")),
            (numerical_contracts, ("ratio", "quantity"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)


@pytest.mark.parametrize("kind", ["Value", "Return", "Selection", "PopulationRequest", "Arguments"])
def test_exported_schemas_are_valid_detached_json_schema(kind):
    schema = contracts.conservation_result_schema(kind)
    Draft202012Validator.check_schema(schema)
    schema["$defs"].clear()
    assert contracts.conservation_result_schema(kind)["$defs"]


def test_literal_native_and_components_views_need_no_parser_or_calculator(supplied, monkeypatch):
    before = deepcopy(supplied)
    forbid_science(monkeypatch)
    value = build(supplied)
    assert value["native_rows"] == supplied["alignment"]["rows"]
    assert value["sites"] == supplied["components"]["sites"]
    assert value["context"]["input"]["source_ref"] is None
    assert value["native_rows"][2]["sequence"] == "cA"
    assert value["context"]["population"]["row_indices"] == [2, 0, 1]
    assert value["context"]["ordered_source_row_indices"] == [0, 1, 2]
    returned = contracts.project_conservation_return(value, source_ref=SOURCE)
    assert contracts.validate_conservation_return(returned) == returned
    assert supplied == before
    returned["native_rows"][0]["sequence"] = "changed detached return"
    assert value["native_rows"][0]["sequence"] == "C-"


def test_independent_ordered_row_and_site_pages_do_not_change_scientific_population(supplied):
    selection = deepcopy(supplied["selection"])
    selection["native_rows"] = dict(row_indices=[2, 0, 1], offset=1, limit=1)
    selection["sites"] = dict(columns_0based=[0, 1], offset=1, limit=1)
    value = build(supplied, selection=selection)
    assert [row["row_index"] for row in value["native_rows"]] == [0]
    assert [row["column_0based"] for row in value["sites"]] == [1]
    assert value["accounting"] == {
        "native_rows": dict(retained_record_count=3, selected_record_count=3,
            returned_record_count=1, omitted_record_count=2),
        "sites": dict(retained_record_count=2, selected_record_count=2,
            returned_record_count=1, omitted_record_count=1)}
    assert value["context"]["population"] == supplied["population"]
    assert value["context"]["member_count"] == supplied["components"]["member_count"]


def test_empty_views_keep_context_definitions_population_and_qualifications(supplied):
    selection = deepcopy(supplied["selection"])
    selection["native_rows"]["row_indices"] = []
    selection["sites"]["columns_0based"] = []
    value = build(supplied, selection=selection)
    assert value["native_rows"] == value["sites"] == []
    assert value["context"]["member_count"]["value"] == 3
    assert value["context"]["site_count"]["value"] == 2
    assert value["context"]["threshold"] == supplied["components"]["threshold"]
    assert value["context"]["native_execution"]["state"] == "unknown"
    assert value["context"]["row_associations"] == supplied["associations"]
    assert value["accounting"]["native_rows"]["selected_record_count"] == 0
    assert value["accounting"]["sites"]["retained_record_count"] == 2


def test_population_helper_binds_semantic_label_without_caller_host_identifiers(supplied):
    request = dict(kind="all_output_rows_and_columns", label="all retained native rows", completeness="complete")
    bound = contracts.bind_conservation_population(request, alignment=supplied["alignment"],
        evidence=supplied["population"]["evidence"])
    assert bound["resolution"] == dict(state="resolved", reason_codes=[])
    assert bound["population"] == dict(population_id=request["label"],
        alignment_id=supplied["alignment"]["alignment_id"], row_indices=[0, 1, 2],
        columns_0based=[0, 1], completeness="complete", evidence=supplied["population"]["evidence"])
    assert set(request) == {"kind", "label", "completeness"}
    assert supplied["population"]["row_indices"] == [2, 0, 1]


def test_known_native_rows_survive_unresolved_full_column_dimension(supplied):
    alignment = deepcopy(supplied["alignment"])
    alignment["rows"][2]["sequence"] = "c"
    alignment.update(completeness="partial", observed_column_count=None)
    request = dict(kind="all_output_rows_and_columns", label="unknown full columns", completeness="partial")
    execution = deepcopy(supplied["native_execution"])
    execution["parser_status"] = "partial"
    selection = deepcopy(supplied["selection"])
    selection["native_rows"]["row_indices"] = [2, 0]
    value = build(supplied, alignment=alignment, population_request=request, population=None,
        components=None, native_execution=execution, selection=selection)
    assert [row["sequence"] for row in value["native_rows"]] == ["c", "C-"]
    assert value["context"]["population"] is None
    assert value["context"]["population_resolution"] == dict(state="unresolved",
        reason_codes=["output_column_dimension_unresolved"])
    assert value["context"]["member_count"] is value["context"]["site_count"] is None
    assert value["sites"] == []
    assert value["accounting"]["native_rows"]["retained_record_count"] == 3
    assert value["accounting"]["sites"]["retained_record_count"] is None


def test_absent_alignment_is_not_a_zero_population_even_with_requested_indices(supplied):
    execution = deepcopy(supplied["native_execution"])
    execution.update(state="failed", returncode=1, parser_status="not_parsed",
        output_capture=dict(state="missing", retained_size_bytes=None, original_size_bytes=None))
    associations = dict(state="unavailable", rows=[], unmatched_input_record_ordinals=None)
    selection = deepcopy(supplied["selection"])
    selection["native_rows"]["row_indices"] = [2]
    selection["sites"]["columns_0based"] = [0]
    value = build(supplied, alignment=None, population=None, components=None,
        native_execution=execution, associations=associations, selection=selection)
    assert value["context"]["population_resolution"]["reason_codes"] == ["alignment_unavailable"]
    assert value["context"]["population"] is value["context"]["member_count"] is None
    assert value["native_rows"] == value["sites"] == []
    for count in value["accounting"].values():
        assert count == dict(retained_record_count=None, selected_record_count=None,
            returned_record_count=0, omitted_record_count=None)


def test_complete_retained_output_can_coexist_with_failed_native_process(supplied):
    execution = deepcopy(supplied["native_execution"])
    execution.update(state="failed", returncode=7)
    execution["output_capture"] = dict(state="complete",
        retained_size_bytes=len(supplied["raw_output_utf8"].encode()),
        original_size_bytes=len(supplied["raw_output_utf8"].encode()))
    value = build(supplied, native_execution=execution)
    assert value["context"]["native_execution"]["returncode"] == 7
    assert value["context"]["alignment"]["completeness"] == "complete"
    assert value["context"]["population"]["completeness"] == "complete"
    assert value["sites"] == supplied["components"]["sites"]


def test_partial_supplied_quantities_remain_unknown_while_record_counts_are_known(supplied):
    alignment = deepcopy(supplied["alignment"])
    alignment["rows"][2]["sequence"] = "c"
    alignment.update(completeness="partial", observed_column_count=None)
    request = deepcopy(supplied["population_request"])
    request["completeness"] = "partial"
    population = deepcopy(supplied["population"])
    population["completeness"] = "partial"
    components = deepcopy(supplied["components"])
    components["sites"][0]["symbol_counts"] = [dict(symbol="-", count=2)]
    quantities = [components["member_count"], components["site_count"]]
    for row in components["sites"]:
        row.update(modal_symbol=None, modal_first_source_row_index=None, strict_gt_0_8=None)
        quantities.extend(row[name] for name in ("modal_count", "majority_fraction", "displayed_2dp_fraction"))
    for quantity in quantities:
        quantity.update(value=None, state="missing", numerator=None, denominator=None)
    execution = deepcopy(supplied["native_execution"])
    execution["parser_status"] = "partial"
    value = build(supplied, alignment=alignment, population_request=request, population=population,
        components=components, native_execution=execution)
    assert value["context"]["site_count"]["value"] is None
    assert value["sites"][0]["majority_fraction"]["state"] == "missing"
    assert value["accounting"]["sites"]["retained_record_count"] == 2
    assert value["accounting"]["native_rows"]["retained_record_count"] == 3


def test_explicit_known_empty_population_is_distinct_from_unknown_and_empty_views(supplied, monkeypatch):
    forbid_science(monkeypatch)
    request = deepcopy(supplied["population_request"])
    request["row_indices"] = []
    population = deepcopy(supplied["population"])
    population["row_indices"] = []
    components = deepcopy(supplied["components"])
    components["ordered_source_row_indices"] = []
    components["member_count"]["value"] = 0
    for row in components["sites"]:
        row.update(symbol_counts=[], modal_symbol=None, modal_first_source_row_index=None, strict_gt_0_8=None)
        for name in ("modal_count", "majority_fraction", "displayed_2dp_fraction"):
            row[name].update(value=None, state="not_measured", numerator=None,
                denominator=0 if name != "modal_count" else None)
    value = build(supplied, population_request=request, population=population, components=components)
    assert value["context"]["member_count"]["value"] == 0
    assert value["context"]["site_count"]["value"] == 2
    assert value["accounting"]["native_rows"]["retained_record_count"] == 3
    assert value["sites"][0]["majority_fraction"]["value"] is None
    assert value["sites"][0]["majority_fraction"]["state"] == "not_measured"


def test_malformed_native_symbols_are_literal_retained_data_not_cleaned(supplied):
    alignment = deepcopy(supplied["alignment"])
    alignment["rows"][2]["sequence"] = "c1"
    alignment.update(completeness="partial", observed_column_count=None)
    request = dict(kind="all_output_rows_and_columns", label="malformed native scope", completeness="partial")
    execution = deepcopy(supplied["native_execution"])
    execution["parser_status"] = "partial"
    issue = dict(code="phylogeny_alignment_symbol_invalid", phase="native_decode", path="/rows/2/sequence",
        severity="error", evidence_refs=[alignment["artifact"]["raw_artifact_ref"]])
    value = build(supplied, alignment=alignment, population_request=request, population=None,
        components=None, native_execution=execution, issues=[issue])
    assert value["native_rows"][2]["sequence"] == "c1"
    assert value["context"]["issues"] == [issue]


@pytest.mark.parametrize("mode", ["run_native", "calculate_saved", "read_stored"])
def test_closed_ordinary_arguments_preserve_selected_input_and_semantic_population(supplied, mode):
    args = dict(mode=mode, selection=supplied["selection"])
    if mode == "run_native":
        args["input"] = supplied["input_record"]["selection"]
    else:
        args["result_ref"] = SOURCE
    if mode != "read_stored":
        args["population_request"] = supplied["population_request"]
    assert contracts.validate_conservation_arguments(args) == args


def test_literal_read_cannot_change_the_scientific_population(supplied):
    arguments = dict(mode="read_stored", result_ref=SOURCE, selection=supplied["selection"],
        population_request=supplied["population_request"])
    with pytest.raises(ValueError):
        contracts.validate_conservation_arguments(arguments)


@pytest.mark.parametrize("section,key,value", [
    ("native_rows", "row_indices", [True]), ("native_rows", "row_indices", [1.0]),
    ("native_rows", "row_indices", [1, 1]), ("native_rows", "row_indices", [-1]),
    ("native_rows", "offset", True), ("native_rows", "limit", -1),
    ("sites", "columns_0based", [0, 0]), ("sites", "columns_0based", [False]),
    ("sites", "limit", 2.0), ("sites", "offset", -1),
])
def test_selection_rejects_ambiguous_or_nonliteral_scalar_types(supplied, section, key, value):
    selected = deepcopy(supplied["selection"])
    selected[section][key] = value
    with pytest.raises(ValueError):
        contracts.validate_conservation_selection(selected)


@pytest.mark.parametrize("name,key", [("native_rows", "row_indices"), ("sites", "columns_0based")])
def test_known_out_of_scope_view_indices_are_not_silently_dropped(supplied, name, key):
    selected = deepcopy(supplied["selection"])
    selected[name][key] = [99]
    with pytest.raises(ValueError, match="selection_outside_retained_values"):
        build(supplied, selection=selected)


@pytest.mark.parametrize("kind", ["label", "rows", "columns", "completeness", "alignment", "evidence"])
def test_bound_population_cannot_substitute_other_scope_or_provenance(supplied, kind):
    population = deepcopy(supplied["population"])
    if kind == "label":
        population["population_id"] = "other label"
    elif kind == "rows":
        population["row_indices"] = [0]
    elif kind == "columns":
        population["columns_0based"] = [0]
    elif kind == "completeness":
        population["completeness"] = "unknown"
    elif kind == "alignment":
        population["alignment_id"] = "other alignment"
    else:
        population["evidence"][0]["pointer"] = "not-a-pointer"
    with pytest.raises(ValueError):
        build(supplied, population=population)


def test_header_associations_use_full_literal_headers_and_preserve_duplicates(supplied):
    value = build(supplied)
    assert value["context"]["row_associations"]["rows"][0]["input_record_ordinals"] == [0, 1]
    assert value["context"]["row_associations"]["rows"][1]["state"] == "ambiguous_label_match"
    alignment = deepcopy(supplied["alignment"])
    alignment["rows"][2]["raw_header"] = "dup different full title"
    alignment["rows"][2]["member_label"] = "dup"
    associations = deepcopy(supplied["associations"])
    associations["rows"][2] = dict(output_row_index=2, input_record_ordinals=[], state="unmatched_output_label")
    associations["unmatched_input_record_ordinals"] = [2]
    value = build(supplied, alignment=alignment, associations=associations)
    assert value["native_rows"][2]["member_label"] == "dup"
    assert value["context"]["row_associations"]["rows"][2]["input_record_ordinals"] == []


def test_incompatible_input_occurrences_remain_qualified_without_positive_header_matches(supplied):
    input_record = deepcopy(supplied["input_record"])
    input_record["records_state"] = "partial"
    input_record["records"][0].update(header="", status="incompatible", issues=["input_not_utf8"])
    associations = deepcopy(supplied["associations"])
    associations.update(state="partial", unmatched_input_record_ordinals=None)
    for row in associations["rows"][:2]:
        row.update(input_record_ordinals=[1], state="ambiguous_label_match")
    associations["rows"][2]["state"] = "ambiguous_label_match"
    value = build(supplied, input_record=input_record, associations=associations)
    assert value["context"]["input"]["records"][0]["header"] == ""
    assert all(0 not in row["input_record_ordinals"] for row in value["context"]["row_associations"]["rows"])
    assert value["context"]["row_associations"]["unmatched_input_record_ordinals"] is None
    with pytest.raises(ValueError):
        build(supplied, input_record=input_record)


def test_all_incompatible_headers_leave_membership_unknown(supplied):
    input_record = deepcopy(supplied["input_record"])
    input_record["records_state"] = "partial"
    for row in input_record["records"]:
        row.update(status="incompatible", issues=["unrepresentable_sequence_symbol"])
    associations = dict(state="unavailable", rows=[dict(output_row_index=i,
        input_record_ordinals=[], state="unavailable_input_records") for i in range(3)],
        unmatched_input_record_ordinals=None)
    value = build(supplied, input_record=input_record, associations=associations)
    assert value["context"]["row_associations"] == associations


def test_selected_source_input_uses_actual_source_role_while_file_only_has_none(supplied):
    input_record = deepcopy(supplied["input_record"])
    input_record["source_ref"] = SOURCE
    with pytest.raises(ValueError, match="input_source_role_conflict"):
        build(supplied, input_record=input_record)
    input_record["selection"].update(namespace="source", reference=SOURCE)
    value = build(supplied, input_record=input_record)
    assert value["context"]["input"]["source_ref"] == SOURCE
    assert build(supplied)["context"]["input"]["source_ref"] is None


@pytest.mark.parametrize("kind", ["collapse", "zip", "case", "unmatched", "row_ordinal"])
def test_false_label_associations_fail_before_projection(supplied, kind):
    associations = deepcopy(supplied["associations"])
    if kind == "collapse":
        associations["rows"][0]["input_record_ordinals"] = [0]
    elif kind == "zip":
        associations["rows"][1].update(input_record_ordinals=[1], state="unique_label_match")
    elif kind == "case":
        associations["rows"][2]["input_record_ordinals"] = [0]
    elif kind == "unmatched":
        associations["unmatched_input_record_ordinals"] = [2]
    else:
        associations["rows"][0]["output_row_index"] = 1
    with pytest.raises(ValueError):
        build(supplied, associations=associations)


@pytest.mark.parametrize("kind", ["native_index", "native_header", "native_location", "native_columns",
    "site_unit", "site_scope", "site_order", "modal_row", "modal_symbol", "record_count", "member_quantity"])
def test_public_values_check_native_calculated_and_accounting_joins(supplied, kind):
    value = build(supplied)
    if kind == "native_index":
        value["native_rows"][0]["row_index"] = 1
    elif kind == "native_header":
        value["native_rows"][0]["member_label"] = "invented"
    elif kind == "native_location":
        value["native_rows"][0]["source_location"]["artifact"]["sha256"] = "0" * 64
    elif kind == "native_columns":
        value["native_rows"][0]["sequence"] = "C"
    elif kind == "site_unit":
        value["sites"][0]["majority_fraction"]["unit"] = "confidence"
    elif kind == "site_scope":
        value["sites"][0]["majority_fraction"]["population_ref"] = "other"
    elif kind == "site_order":
        value["sites"].reverse()
    elif kind == "modal_row":
        value["sites"][0]["modal_first_source_row_index"] = 99
    elif kind == "modal_symbol":
        value["sites"][0]["modal_symbol"] = "X"
    elif kind == "record_count":
        value["accounting"]["sites"]["returned_record_count"] = 0
    else:
        value["context"]["member_count"]["unit"] = "original input sequences"
    with pytest.raises(ValueError):
        contracts.validate_conservation_public_value(value)


@pytest.mark.parametrize("kind", ["file_sha", "source_alias", "record_extent", "capture_extent",
    "native_state", "alphabet", "parser_state", "nonfinite", "extra_control"])
def test_context_does_not_invent_input_native_or_qualified_values(supplied, kind):
    value = build(supplied)
    context = value["context"]
    if kind == "file_sha":
        context["input"]["file"]["sha256"] = "0" * 64
    elif kind == "source_alias":
        context["input"]["selection"].update(namespace="source", reference=SOURCE)
    elif kind == "record_extent":
        context["input"]["records"][0]["byte_end"] = 9999
    elif kind == "capture_extent":
        context["input"]["capture"]["original_size_bytes"] = 1
    elif kind == "native_state":
        context["native_execution"].update(state="completed", returncode=1)
    elif kind == "alphabet":
        context["native_execution"]["alphabet"]["value"] = "protein"
    elif kind == "parser_state":
        context["native_execution"]["parser_status"] = "not_parsed"
    elif kind == "nonfinite":
        context["member_count"]["value"] = float("nan")
    else:
        context["native_execution"]["private_driver_path"] = "/private/driver"
    with pytest.raises(ValueError):
        contracts.validate_conservation_public_value(value)


def test_source_only_declarative_contract_and_opaque_provenance(supplied, monkeypatch):
    forbid_science(monkeypatch)
    value = build(supplied)
    returned = contracts.project_conservation_return(value, source_ref=SOURCE)
    schema = contracts.conservation_result_schema("Return")
    assert Draft202012Validator(schema).is_valid(returned)
    fact = contracts.conservation_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    Draft202012Validator.check_schema(fact)
    assert Draft202012Validator(fact).is_valid([returned])
    annotations = []
    def visit(node, path=()):
        if isinstance(node, dict):
            if node.get("format") == "reference" or "x-reference-namespace" in node:
                annotations.append(path)
            for key, item in node.items():
                visit(item, path + (key,))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, path + (index,))
    visit(schema)
    assert annotations == [("$defs", "Return", "properties", "source_ref")]
    assert returned["native_rows"][0]["source_location"]["artifact"]["source_ref"] == \
        "engineering_capture_source_not_authenticated"
    for bad in ("artifact_" + "b" * 64, "arbitrary-text", SOURCE + "\n", None):
        with pytest.raises(ValueError):
            contracts.project_conservation_return(value, source_ref=bad)
