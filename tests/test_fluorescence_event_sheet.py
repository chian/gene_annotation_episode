"""Contract tests use declared synthetic data, never a biological measurement."""

from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.fluorescence_event_contracts import (
    COMPONENTS_SCHEMA, PARSE_SCHEMA, SHEET_SCHEMA, TABLE_SCHEMA, VIEW_SCHEMA,
    FluorescenceContractError, canonical, digest, finite, issue,
    validate_calculation_parameters, validate_components, validate_csv_request,
    validate_event_parse_result, validate_selection, validate_snapshot_request,
)
from gene_annotation_episode.fluorescence_event_sheet import (
    populate_fluorescence_sheet, validate_fluorescence_sheet,
)


def file_identity(letter="a", size=2048):
    return dict(artifact_ref="artifact_" + letter * 64, sha256=letter * 64,
                size_bytes=size, format="synthetic_fixture")


def location(ordinal=None, end=None):
    return dict(record_ordinal=ordinal, line_start=None, line_end=None,
                byte_start=None, byte_end=end)


def association(source="source", *, file=None):
    return dict(namespace="supplied", identifier="analyte", file=file or file_identity("b"),
                source_key=source, location=location())


def parsed_fixture(values=(90, 100, 100)):
    """A complete EventParseResult for consumers, explicitly synthetic values."""
    prep = dict(state="not_applied", method=None, parameters_file=None)
    source = dict(key="source", file=file_identity(), dataset_position=0,
                  format_profile="csv_v1", extent="complete", native_event_count=None,
                  metadata=[dict(name="native", value="retained")])
    sample = dict(key="sample", primary_domain_key="raw", label="duplicate label",
                  condition="condition", biological_replicate=None,
                  technical_replicate=None, associations=[association()])
    channel = dict(key="channel", domain_key="raw", ordinal=0, native_name="duplicate",
                   label="duplicate", unit="instrument", analyte=association())
    domain = dict(key="raw", sample_key="sample", source_key="source", parent_domain_key=None,
                  state="available", scale_kind="as_supplied", compensation=deepcopy(prep),
                  transformation=deepcopy(prep), correspondence=None, comparison_basis=None)
    events = []
    for ordinal, number in enumerate(values):
        events.append(dict(sample_key="sample", domain_key="raw", event_ordinal=ordinal,
                           source_ordinal=ordinal, location=location(ordinal), values=[
                               dict(channel_key="channel", measurement=dict(
                                   value=number, state="missing" if number is None else "supplied_predicted",
                                   raw=None))]))
    return dict(schema=PARSE_SCHEMA, source=source, sample=sample,
                channels=[channel], domain=domain, events=events, issues=[])


def definitions():
    population = dict(key="population", sample_key="sample", kind="all", event_ordinals=None)
    gate = dict(key="gate", sample_key="sample", parent=dict(kind="population", key="population"),
                kind="threshold", domain_key="raw", channel_key="channel",
                lower=dict(value=100, inclusive=True), upper=None)
    return population, gate


def sheet_fixture(batch=None):
    population, gate = definitions()
    return populate_fluorescence_sheet([parsed_fixture() if batch is None else batch],
                                      populations=[population], gates=[gate],
                                      control_pairs=[], native_reports=[])


def parameters_fixture():
    return dict(fraction_requests=[dict(gate_key="gate", denominator="parent")],
                intensity_requests=[], control_requests=[], native_comparison_requests=[])


def request(kind, metric, *, denominator="none", **identities):
    return dict(kind=kind, gate_key=identities.get("gate_key"),
                domain_key=identities.get("domain_key"), channel_key=identities.get("channel_key"),
                control_key=identities.get("control_key"), native_report_key=identities.get("native_report_key"),
                denominator=denominator, metric=metric)


def components_fixture(sheet):
    """Hand-specified retained bundle; deliberately independent of calculators."""
    membership = dict(gate_key="gate", sample_key="sample", parent=dict(kind="population", key="population"),
                      universe_event_ordinals=[0, 1, 2], parent_true=[0, 1, 2], parent_false=[],
                      parent_unknown=[], selected=[1, 2], rejected=[0], unknown=[],
                      parent_evaluable=[0, 1, 2], parent_nonevaluable=[], population_complete=True, issues=[])
    metrics = [
        ("retained_event_count", 3, "universe_event_ordinals"),
        ("parent_event_count", 3, "parent_true"),
        ("parent_unknown_count", 0, "parent_unknown"),
        ("evaluable_event_count", 3, "parent_evaluable"),
        ("selected_event_count", 2, "selected"),
        ("rejected_event_count", 1, "rejected"),
        ("unknown_gate_event_count", 0, "parent_nonevaluable"),
    ]
    cells = []
    for metric, number, field in metrics:
        cells.append(dict(request=request("population", metric, gate_key="gate"),
                          value=number, state="present", unit="events", population=dict(
                              sample_key="sample", gate_key="gate", domain_key=None, channel_key=None,
                              denominator="none", extent="complete"),
                          operands=["components:/memberships/0/" + field], issues=[]))
    for metric, number, unit in (("selected_fraction", 2 / 3, "dimensionless"),
                                  ("selected_percent", 100 * (2 / 3), "percent")):
        cells.append(dict(request=request("fraction", metric, gate_key="gate", denominator="parent"),
                          value=number, state="present", unit=unit, population=dict(
                              sample_key="sample", gate_key="gate", domain_key=None, channel_key=None,
                              denominator="parent", extent="complete"),
                          operands=["components:/cells/4/value", "components:/cells/1/value",
                                    "parameters:/fraction_requests/0", "sheet:/gate_definitions/0"], issues=[]))
    return dict(schema=COMPONENTS_SCHEMA, sheet_sha256=digest(sheet), parameters=parameters_fixture(),
                memberships=[membership], cells=cells, status="calculated", issues=[])


def derived_fixture(primary, *, partial=False):
    batch = deepcopy(primary)
    batch["source"]["key"] = "prepared_source"
    batch["source"]["file"] = file_identity("c")
    batch["source"]["extent"] = "partial" if partial else "complete"
    batch["domain"].update(key="prepared", source_key="prepared_source", parent_domain_key="raw",
                           correspondence=[dict(source_ordinal=0, event_ordinal=0),
                                           dict(source_ordinal=1, event_ordinal=2)])
    batch["channels"][0].update(key="prepared_channel", domain_key="prepared")
    batch["events"] = deepcopy(primary["events"][:1] if partial else primary["events"][:2])
    for event, original in zip(batch["events"], (0, 2)):
        event.update(domain_key="prepared", event_ordinal=original)
        event["values"][0]["channel_key"] = "prepared_channel"
    return batch


def assert_error(code, function, *args, **kwargs):
    with pytest.raises(FluorescenceContractError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


def test_public_identity_primitives_and_finite_numbers():
    value = {"é": [0, None], "x": "é"}
    expected = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                          allow_nan=False).encode("utf-8")
    assert canonical(value) == expected
    assert digest(value) == hashlib.sha256(expected).hexdigest()
    assert finite(0) and finite(-1.5) and finite(10**400)
    assert not any(finite(v) for v in (True, False, "2", None, float("nan"), float("inf")))
    assert TABLE_SCHEMA == "fluorescence_event_table_v1"
    assert VIEW_SCHEMA == "fluorescence_event_result_view_v1"


def test_builder_joins_once_preserves_order_and_deep_copies_every_operand():
    primary = parsed_fixture()
    prepared = derived_fixture(primary)
    population, gate = definitions()
    original = deepcopy([primary, prepared, population, gate])
    sheet = populate_fluorescence_sheet([prepared, primary], populations=[population],
                                       gates=[gate], control_pairs=[], native_reports=[])
    assert sheet["schema"] == SHEET_SCHEMA
    assert [s["key"] for s in sheet["input_sources"]] == ["prepared_source", "source"]
    assert len(sheet["samples"]) == 1
    assert sheet["events"][0]["domain_key"] == "prepared"
    assert [primary, prepared, population, gate] == original
    sheet["samples"][0]["associations"][0]["identifier"] = "changed"
    sheet["events"][0]["values"][0]["measurement"]["value"] = 999
    sheet["gate_definitions"][0]["lower"]["value"] = 999
    assert [primary, prepared, population, gate] == original


def test_shared_same_key_definitions_must_be_byte_identical():
    primary = parsed_fixture()
    prepared = derived_fixture(primary)
    prepared["sample"]["label"] = "conflict"
    assert_error("invalid_sample", populate_fluorescence_sheet, [primary, prepared],
                 populations=[], gates=[], control_pairs=[], native_reports=[])
    prepared = derived_fixture(primary)
    prepared["source"] = deepcopy(primary["source"])
    prepared["source"]["metadata"].append(dict(name="extra", value="fact"))
    prepared["domain"]["source_key"] = "source"
    assert_error("invalid_source", populate_fluorescence_sheet, [primary, prepared],
                 populations=[], gates=[], control_pairs=[], native_reports=[])


def test_partial_prepared_rows_and_original_gaps_remain_missing_not_filled():
    primary = parsed_fixture()
    prepared = derived_fixture(primary, partial=True)
    assert validate_event_parse_result(prepared) is prepared
    sheet = populate_fluorescence_sheet([primary, prepared], populations=[], gates=[],
                                       control_pairs=[], native_reports=[])
    assert len(sheet["events"]) == 4
    assert [e["event_ordinal"] for e in sheet["events"] if e["domain_key"] == "prepared"] == [0]
    prepared["source"]["extent"] = "complete"
    assert_error("invalid_domain", validate_event_parse_result, prepared)


def test_derived_parser_accepts_external_parent_but_assembled_sheet_requires_it():
    prepared = derived_fixture(parsed_fixture())
    assert validate_event_parse_result(prepared) is prepared
    assert_error("invalid_sample", populate_fluorescence_sheet, [prepared],
                 populations=[], gates=[], control_pairs=[], native_reports=[])


@pytest.mark.parametrize("change,code", [
    (lambda b: b.update(extra=1), "invalid_parse_result"),
    (lambda b: b["source"]["file"].update(sha256="A" * 64), "invalid_source"),
    (lambda b: b["source"].update(dataset_position=True), "invalid_source"),
    (lambda b: b["sample"].update(key="bad\nkey"), "invalid_sample"),
    (lambda b: b["channels"][0].update(ordinal=True), "invalid_channel"),
    (lambda b: b["events"][0].update(event_ordinal=1), "invalid_event"),
    (lambda b: b["events"][0]["location"].update(record_ordinal=2), "invalid_event"),
    (lambda b: b["events"][0]["location"].update(line_start=0), "invalid_event"),
    (lambda b: b["events"][0]["location"].update(byte_end=2049), "invalid_event"),
    (lambda b: b["events"][0]["values"][0]["measurement"].update(value=True), "invalid_event"),
    (lambda b: b["events"][0]["values"][0]["measurement"].update(value=float("inf")), "invalid_event"),
    (lambda b: b["events"][0]["values"][0]["measurement"].update(state="missing"), "invalid_event"),
    (lambda b: b.update(events=tuple(b["events"])), "invalid_event"),
])
def test_closed_parse_shapes_reject_malformed_caller_data(change, code):
    batch = parsed_fixture()
    change(batch)
    assert_error(code, validate_event_parse_result, batch)


def test_invalid_native_measurement_is_valid_retained_data_with_original_position():
    batch = parsed_fixture()
    batch["events"][1]["values"][0]["measurement"] = dict(value=None, state="invalid", raw="invalid-token")
    batch["issues"].append(issue("invalid_numeric_token", "parse", source_key="source",
                                 sample_key="sample", domain_key="raw", channel_key="channel", event_ordinal=1))
    assert validate_event_parse_result(batch) is batch
    assert [e["event_ordinal"] for e in sheet_fixture(batch)["events"]] == [0, 1, 2]


def test_duplicate_names_and_values_do_not_merge_original_channels_or_events():
    batch = parsed_fixture()
    other = deepcopy(batch["channels"][0])
    other.update(key="channel2", ordinal=1)
    batch["channels"].append(other)
    for event in batch["events"]:
        cell = deepcopy(event["values"][0])
        cell["channel_key"] = "channel2"
        event["values"].append(cell)
    assert validate_event_parse_result(batch) is batch
    assert len(sheet_fixture(batch)["events"]) == 3
    batch["events"][0]["values"].reverse()
    assert_error("invalid_event", validate_event_parse_result, batch)


def test_unavailable_complete_empty_and_partial_sources_are_distinct():
    empty = parsed_fixture(())
    assert sheet_fixture(empty)["input_sources"][0]["extent"] == "complete"
    missing = deepcopy(empty)
    missing["source"].update(file=None, extent="unavailable")
    missing["domain"]["state"] = "unavailable"
    assert_error("invalid_parse_result", validate_event_parse_result, missing)
    missing["issues"] = [issue("source_unavailable", "input", source_key="source")]
    assert sheet_fixture(missing)["events"] == []
    prefix = parsed_fixture()
    prefix["source"]["extent"] = "partial"
    prefix["issues"] = [issue("truncated_source", "parse", source_key="source", event_ordinal=99)]
    sheet = sheet_fixture(prefix)
    sheet["population_definitions"][0].update(kind="subset", event_ordinals=[2, 0])
    assert validate_fluorescence_sheet(sheet) is sheet


def test_mapping_target_source_and_parent_domain_relationships_reject_conflicts():
    primary = parsed_fixture()
    for mutate in (
        lambda p: p["domain"]["correspondence"][0].update(event_ordinal=50),
        lambda p: p["domain"].update(parent_domain_key="missing_parent"),
        lambda p: p["domain"].update(parent_domain_key="prepared"),
    ):
        prepared = derived_fixture(primary, partial=True)
        mutate(prepared)
        with pytest.raises(FluorescenceContractError):
            populate_fluorescence_sheet([primary, prepared], populations=[], gates=[],
                                       control_pairs=[], native_reports=[])
    prepared = derived_fixture(primary)
    prepared["events"][0]["event_ordinal"] = 2
    assert_error("invalid_event", validate_event_parse_result, prepared)


def test_dropped_original_record_and_unavailable_domain_rows_are_not_admitted():
    batch = parsed_fixture()
    batch["events"].pop(1)
    assert_error("invalid_event", validate_event_parse_result, batch)


def test_failed_prepared_domain_preserves_complete_original_source_and_correspondence():
    primary = parsed_fixture()
    prepared = derived_fixture(primary)
    prepared["source"] = deepcopy(primary["source"])
    prepared["domain"].update(source_key="source", state="failed")
    prepared["events"] = []
    prepared["issues"] = [issue("measurement_domain_unavailable", "domain", source_key="source",
                                 sample_key="sample", domain_key="prepared")]
    assert validate_event_parse_result(prepared) is prepared
    sheet = populate_fluorescence_sheet([primary, prepared], populations=[], gates=[],
                                       control_pairs=[], native_reports=[])
    assert len(sheet["input_sources"]) == 1
    assert sheet["input_sources"][0]["extent"] == "complete"
    assert sheet["measurement_domains"][1]["correspondence"] == prepared["domain"]["correspondence"]
    batch = parsed_fixture()
    batch["domain"]["state"] = "failed"
    assert_error("invalid_event", validate_event_parse_result, batch)


def test_gate_ancestry_is_order_independent_and_cycles_are_rejected():
    sheet = sheet_fixture()
    child = deepcopy(sheet["gate_definitions"][0])
    child.update(key="child", parent=dict(kind="gate", key="gate"), kind="pass_all",
                 domain_key=None, channel_key=None, lower=None, upper=None)
    sheet["gate_definitions"].insert(0, child)
    assert validate_fluorescence_sheet(sheet) is sheet
    sheet["gate_definitions"][1]["parent"] = dict(kind="gate", key="child")
    assert_error("invalid_gate", validate_fluorescence_sheet, sheet)


@pytest.mark.parametrize("mutate,code", [
    (lambda s: s["population_definitions"][0].update(kind="subset", event_ordinals=[3]), "invalid_population"),
    (lambda s: s["population_definitions"][0].update(kind="subset", event_ordinals=[1, 1]), "invalid_population"),
    (lambda s: s["gate_definitions"][0].update(upper=dict(value=90, inclusive=True)), "invalid_gate"),
    (lambda s: s["gate_definitions"][0].update(lower=None), "invalid_gate"),
    (lambda s: s["gate_definitions"][0].update(channel_key="missing"), "invalid_gate"),
    (lambda s: s["measurement_domains"][0]["compensation"].update(state="applied"), "invalid_domain"),
    (lambda s: s["samples"][0]["associations"][0].update(source_key="missing"), "invalid_sample"),
])
def test_saved_sheet_enforces_definition_relationships(mutate, code):
    sheet = sheet_fixture()
    mutate(sheet)
    assert_error(code, validate_fluorescence_sheet, sheet)


def test_control_comparability_is_a_supplied_input_not_a_validation_judgment():
    sheet = sheet_fixture()
    sheet["control_pairs"] = [dict(key="pair", target_gate_key="gate", control_gate_key="gate",
                                    denominator="parent", comparison_basis=dict(key="basis", evidence_file=file_identity("d")))]
    # Raw domain has no comparison basis: valid contract, unavailable comparison.
    assert validate_fluorescence_sheet(sheet) is sheet
    sheet["control_pairs"][0]["comparison_basis"] = None
    assert_error("invalid_control", validate_fluorescence_sheet, sheet)


def native_report():
    return dict(key="report", file=file_identity("e", 5), source_key="source",
                location=location(0, 5), label="reported percent", value=66.67, raw="66.67",
                unit="percent", component_request=request("fraction", "selected_percent", gate_key="gate", denominator="parent"),
                decimal_places=2)


def test_actual_report_and_association_files_remain_independent_of_event_source():
    sheet = sheet_fixture()
    report = native_report()
    sheet["native_reports"] = [report]
    assert validate_fluorescence_sheet(sheet) is sheet
    assert report["file"] != sheet["input_sources"][0]["file"]
    report["location"]["byte_end"] = 6
    assert_error("invalid_native_report", validate_fluorescence_sheet, sheet)
    report["location"]["byte_end"] = 5
    report["source_key"] = None
    sheet["samples"][0]["associations"][0]["source_key"] = None
    assert validate_fluorescence_sheet(sheet) is sheet
    sheet["samples"][0]["associations"][0]["file"]["size_bytes"] = 0
    sheet["samples"][0]["associations"][0]["location"]["byte_end"] = 1
    assert_error("invalid_sample", validate_fluorescence_sheet, sheet)


def test_native_report_may_not_link_to_itself_or_another_native_comparison():
    sheet = sheet_fixture()
    report = native_report()
    report["component_request"] = request("native_comparison", "native_value", native_report_key="report")
    sheet["native_reports"] = [report]
    assert_error("invalid_native_report", validate_fluorescence_sheet, sheet)


def test_issue_codes_stages_and_locators_are_closed_but_failed_ordinal_can_be_unretained():
    assert_error("invalid_parameters", issue, "invented", "parse")
    assert_error("invalid_parameters", issue, "invalid_event_row", "capture")
    assert_error("invalid_parameters", issue, "invalid_event_row", "parse", event_ordinal=True)
    sheet = sheet_fixture()
    sheet["issues"] = [issue("truncated_source", "parse", source_key="source", event_ordinal=20)]
    assert validate_fluorescence_sheet(sheet) is sheet
    sheet["issues"][0]["source_key"] = "unknown"
    assert_error("invalid_sheet", validate_fluorescence_sheet, sheet)


def request_context():
    parsed = parsed_fixture()
    binding = {k: v for k, v in parsed["channels"][0].items() if k != "domain_key"}
    binding["measurement_origin"] = "supplied_predicted"
    return dict(source=parsed["source"], sample=parsed["sample"], domain=parsed["domain"], channels=[binding])


def test_request_ports_require_positional_bindings_and_explicit_measurement_origin():
    context = request_context()
    original = deepcopy(context)
    assert validate_snapshot_request(**context) is None
    format_spec = dict(encoding="utf-8", delimiter=",", quotechar='"', escapechar=None,
                       doublequote=True, header=True, missing_tokens=[""])
    assert validate_csv_request(**context, format_spec=format_spec) is None
    assert context == original
    context["channels"][0].pop("measurement_origin")
    assert_error("invalid_channel", validate_snapshot_request, **context)
    context = request_context()
    context["channels"][0]["ordinal"] = 1
    assert_error("invalid_channel", validate_snapshot_request, **context)
    context = request_context()
    format_spec["header"] = 1
    assert_error("invalid_parameters", validate_csv_request, **context, format_spec=format_spec)


def test_parameter_requests_are_closed_unique_and_sample_joined():
    sheet = sheet_fixture()
    params = parameters_fixture()
    assert validate_calculation_parameters(params, sheet=sheet) is params
    params["fraction_requests"].append(deepcopy(params["fraction_requests"][0]))
    assert_error("invalid_parameters", validate_calculation_parameters, params, sheet=sheet)
    params = parameters_fixture()
    params["intensity_requests"] = [dict(gate_key="gate", domain_key="raw", channel_key="other")]
    assert_error("invalid_parameters", validate_calculation_parameters, params, sheet=sheet)
    sheet["control_pairs"] = [dict(key="pair", target_gate_key="gate", control_gate_key="gate", denominator="parent",
                                    comparison_basis=dict(key="basis", evidence_file=file_identity("d")))]
    params = parameters_fixture()
    params["control_requests"] = [dict(control_key="pair", include_legacy_clipping=False),
                                   dict(control_key="pair", include_legacy_clipping=True)]
    assert_error("invalid_parameters", validate_calculation_parameters, params, sheet=sheet)


def test_components_and_selection_return_original_objects_without_recalculation():
    sheet = sheet_fixture()
    components = components_fixture(sheet)
    original = deepcopy(components)
    assert validate_components(components, sheet=sheet) is components
    assert components == original
    # Standalone data validators cannot authenticate a scientifically forged dict.
    # A plausible changed number remains structural data, not a recalculated truth.
    components["cells"][7]["value"] = 0.5
    assert validate_components(components, sheet=sheet) is components
    selection = dict(requests=[deepcopy(components["cells"][7]["request"])], offset=0, limit=1)
    assert validate_selection(selection, components=components) is selection
    assert components["cells"][7]["value"] == 0.5


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(sheet_sha256="0" * 64),
    lambda c: c["memberships"][0]["selected"].append(0),
    lambda c: c["memberships"][0].update(parent_nonevaluable=[0]),
    lambda c: c["memberships"][0].update(population_complete=False),
    lambda c: c["cells"].append(deepcopy(c["cells"][0])),
    lambda c: c["cells"].pop(),
    lambda c: c["cells"][0].update(value=True),
    lambda c: c["cells"][0].update(value=3.0),
    lambda c: c["cells"][0].update(value=-1),
    lambda c: c["cells"][7].update(value=1.01),
    lambda c: c["cells"][8].update(value=101),
    lambda c: c["cells"][7].update(unit="percent"),
    lambda c: c["cells"][0].update(state="unavailable"),
    lambda c: c["cells"][0]["population"].update(domain_key="raw"),
    lambda c: c["cells"][0]["population"].update(sample_key="other"),
    lambda c: c.update(status="partial"),
])
def test_component_shape_membership_and_cell_identity_adversaries(mutate):
    sheet = sheet_fixture()
    components = components_fixture(sheet)
    mutate(components)
    assert_error("invalid_components", validate_components, components, sheet=sheet)


@pytest.mark.parametrize("operand", [
    "files:/events", "sheet:/events/99", "sheet:/events/01", "sheet:/events/-1",
    "sheet:/events/-", "sheet:/events/0/missing", "sheet:/~2invalid", "sheet:events/0",
    "components:/cells/0/value/0", "parameters:/not_requested",
])
def test_operand_pointers_must_resolve_exactly(operand):
    sheet = sheet_fixture()
    components = components_fixture(sheet)
    components["cells"][0]["operands"] = [operand]
    assert_error("invalid_components", validate_components, components, sheet=sheet)


def test_component_issues_missing_values_and_zero_are_preserved():
    sheet = sheet_fixture()
    components = components_fixture(sheet)
    assert components["cells"][2]["value"] == 0
    components["cells"][7].update(value=None, state="unavailable", issues=[
        issue("unknown_gate_membership", "calculation", sample_key="sample", gate_key="gate")])
    components["status"] = "partial"
    assert validate_components(components, sheet=sheet) is components
    assert components["cells"][7]["value"] is None
    assert components["cells"][2]["value"] == 0


def test_selection_does_not_synthesize_unrequested_cells_or_accept_duplicates():
    sheet = sheet_fixture()
    components = components_fixture(sheet)
    existing = deepcopy(components["cells"][0]["request"])
    selection = dict(requests=[existing, deepcopy(existing)], offset=0, limit=1)
    assert_error("invalid_selection", validate_selection, selection, components=components)
    selection["requests"] = [request("fraction", "selected_fraction", gate_key="gate", denominator="evaluable")]
    assert_error("invalid_selection", validate_selection, selection, components=components)
    selection["requests"] = [existing]
    selection["offset"] = True
    assert_error("invalid_selection", validate_selection, selection, components=components)
