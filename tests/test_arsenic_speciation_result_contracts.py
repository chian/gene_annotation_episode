"""Pure ordinary contracts over supplied numerical fixtures, not HPLC runs."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from gene_annotation_episode import arsenic_speciation_result_contracts as contracts
from gene_annotation_episode import calibrated_signal_calculations as calculations
from gene_annotation_episode import calibrated_signal_contracts as scientific
from gene_annotation_episode import calibrated_signal_sheet as reader
from gene_annotation_episode import molecular_sequence_result_contracts as private
from gene_annotation_episode.domain import validate_schema
from test_calibrated_signal_measurements import supplied_inputs, selection, threshold, uncertainty


SOURCE = "source_" + "a" * 24
INPUT = "artifact_" + "1" * 64
_ROLE_STATES = dict(samples="present", species="present", calibrations="present", association="present")
_CALCULATION = dict(state="completed", call_count=1, native_invocation="not_requested")
_FILE_STATES = dict(sheet="retained_undeclared", components="retained")


def _arguments(mode="calculate", *, selected=None):
    if mode == "read_stored":
        return dict(mode=mode, result_ref=SOURCE)
    return dict(mode=mode, **({"input": dict(namespace="artifact", reference=INPUT)}
        if mode == "calculate" else {"result_ref": SOURCE}),
        selection=selection() if selected is None else deepcopy(selected))


def _documents(data=None, selected=None):
    sheet = reader.populate_calibrated_signal_sheet(**(supplied_inputs() if data is None else data))
    components = calculations.calculate_calibrated_signal_components(sheet,
        selection=selection() if selected is None else selected)
    return sheet, components


def _packet(data=None, selected=None, *, mode="calculate"):
    sheet, components = _documents(data, selected)
    states = {name: "empty" if type(sheet[name]) is list and not sheet[name] else "present"
        for name in contracts.INPUT_ROLES}
    return contracts.ordinary_arsenic_packet(arguments=_arguments(mode, selected=components["selection"]),
        input_state="complete", role_states=states, components=components,
        calculation=_CALCULATION, file_states=_FILE_STATES, failures=[])


def _return_schema():
    return contracts.ordinary_arsenic_fact_sources()[contracts.FACT_SOURCE]["report_schema"]["items"]


@pytest.mark.parametrize("mode", ["calculate", "calculate_saved", "read_stored"])
def test_arguments_are_closed_detached_and_preserve_the_selected_mode(mode):
    original = _arguments(mode)
    before = deepcopy(original)
    actual = contracts.validate_ordinary_arsenic_arguments(original)
    validate_schema(actual, contracts.ARGUMENT_SCHEMA)
    assert actual == before and actual is not original
    actual["mode"] = "changed detached copy"
    assert original == before


@pytest.mark.parametrize("change", ["native", "both_inputs", "saved_input", "read_selection", "read_input",
    "source_namespace", "artifact_namespace", "extra_calibration", "missing_selection", "duplicate_identity"])
def test_arguments_reject_new_native_work_ambiguous_inputs_and_read_overrides(change):
    value = _arguments()
    if change == "native": value["mode"] = "run_native"
    elif change == "both_inputs": value["result_ref"] = SOURCE
    elif change == "saved_input": value["mode"] = "calculate_saved"
    elif change == "read_selection": value = {**_arguments("read_stored"), "selection": selection()}
    elif change == "read_input": value = dict(mode="read_stored", input=value["input"])
    elif change == "source_namespace": value["input"] = dict(namespace="source", reference=INPUT)
    elif change == "artifact_namespace": value["input"] = dict(namespace="artifact", reference=SOURCE)
    elif change == "extra_calibration": value["calibration_factor"] = 1
    elif change == "missing_selection": del value["selection"]
    else: value["selection"]["sample_ids"] *= 2
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_arguments(value)


def test_public_values_copy_the_existing_components_without_embedded_input_sheet():
    sheet, components = _documents()
    before = deepcopy(components)
    packet = contracts.ordinary_arsenic_packet(arguments=_arguments(), input_state="complete",
        role_states=_ROLE_STATES, components=components, calculation=_CALCULATION,
        file_states=_FILE_STATES, failures=[])
    value = packet["values"]
    assert set(value) == {"schema", "components_version", "population", "rows", "uncertainty_assessments",
        "unassigned_measurements", "qualifications"}
    assert value["schema"] == contracts.VALUES_VERSION and value["components_version"] == scientific.COMPONENTS_VERSION
    for name in ("population", "rows", "uncertainty_assessments", "unassigned_measurements", "qualifications"):
        assert value[name] == components[name]
    assert "sheet" not in value and "selection" not in value
    row = value["rows"][0]
    assert row["linear_estimate"]["value"] == row["aliquot_concentration"]["value"] == 10
    assert row["original_sample_concentration"]["value"] == 20
    assert row["aliquot_concentration"]["unit"] == "supplied_mass_per_volume_unit"
    assert row["aliquot_concentration"]["quantity_basis"] == dict(kind="mass_of_element", identity="As")
    value["rows"][0]["linear_estimate"]["value"] = 999
    assert components == before and components["sheet"] == sheet


def _two_by_two():
    data = supplied_inputs()
    point = deepcopy(data["samples"][0]["measurements"][0])
    point.update(measurement_id="point-2", retention_time=20)
    point["signal"]["value"] = 43
    data["samples"][0]["measurements"].append(point)
    sample = deepcopy(data["samples"][0]); sample["sample_id"] = "sample-B"
    data["samples"].append(sample)
    species = deepcopy(data["species"][0]); species.update(species_id="species-B", reference_retention_time=20)
    data["species"].append(species)
    calibration = deepcopy(data["calibrations"][0]); calibration.update(calibration_id="cal-B", species_id="species-B")
    data["calibrations"].append(calibration)
    data["association"]["analysis_species_ids"].append("species-B")
    selected = selection(samples=("sample-B", "sample-A"), species=("species-B", "species-A"), calibrations=("cal-B", "cal-A"))
    return data, selected


def test_selection_order_is_literal_while_rows_keep_original_sample_species_ordinals():
    data, selected = _two_by_two()
    packet = _packet(data, selected)
    assert packet["selection"] == selected
    rows = packet["values"]["rows"]
    assert [(row["sample_id"], row["species_id"]) for row in rows] == [
        ("sample-A", "species-A"), ("sample-A", "species-B"),
        ("sample-B", "species-A"), ("sample-B", "species-B")]
    assert [(row["sample_ordinal"], row["species_ordinal"]) for row in rows] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert [row["aliquot_concentration"]["value"] for row in rows] == [10, 20, 10, 20]
    assert packet["values"]["population"] == dict(supplied_sample_count=2, supplied_species_count=2,
        selected_sample_count=2, selected_species_count=2, returned_row_count=4,
        association_species_ids=["species-A", "species-B"], association_competitor_basis="declared_analysis_population",
        replicate_pooling=False)
    validate_schema(contracts.project_ordinary_arsenic_return(packet, SOURCE), _return_schema())


@pytest.mark.parametrize("change", ["sheet_sample", "sheet_ordinal", "candidate_identity", "calibration_identity", "selection", "population"])
def test_packet_builder_rejects_components_detached_from_their_actual_sheet_and_selection(change):
    _sheet, components = _documents()
    if change == "sheet_sample": components["sheet"]["samples"][0]["sample_id"] = "other-sample"
    elif change == "sheet_ordinal": components["rows"][0]["sample_ordinal"] = 1
    elif change == "candidate_identity": components["rows"][0]["association"]["candidates"][0]["measurement_id"] = "other-point"
    elif change == "calibration_identity": components["rows"][0]["selected_calibration_ids"] = []
    elif change == "selection": components["selection"]["sample_ids"] = []
    else: components["population"]["supplied_sample_count"] = 2
    with pytest.raises(ValueError):
        contracts.ordinary_arsenic_packet(arguments=_arguments(), input_state="complete", role_states=_ROLE_STATES,
            components=components, calculation=_CALCULATION, file_states=_FILE_STATES, failures=[])


@pytest.mark.parametrize("change", ["count_float", "count_bool", "selected_count", "row_count", "ordinal_bool",
    "duplicate_pair", "row_order", "assigned_identity", "unknown_competitor", "calibration_choice", "unassigned_order"])
def test_public_validator_rejects_inconsistent_count_and_ordered_identity_claims(change):
    data, selected = _two_by_two()
    packet = _packet(data, selected); value = packet["values"]
    if change == "count_float": value["population"]["supplied_sample_count"] = 2.0
    elif change == "count_bool": value["population"]["selected_sample_count"] = True
    elif change == "selected_count": value["population"]["selected_species_count"] = 1
    elif change == "row_count": value["population"]["returned_row_count"] = 3
    elif change == "ordinal_bool": value["rows"][0]["sample_ordinal"] = False
    elif change == "duplicate_pair": value["rows"][1] = deepcopy(value["rows"][0])
    elif change == "row_order": value["rows"].reverse()
    elif change == "assigned_identity": value["rows"][0]["association"]["measurement_id"] = "point-2"
    elif change == "unknown_competitor": value["rows"][0]["association"]["competing_species_ids"] = ["outside-population"]
    elif change == "calibration_choice": value["rows"][0]["calibration_id"] = "cal-B"
    else: value["unassigned_measurements"].reverse()
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_packet(packet)


@pytest.mark.parametrize("samples,species", [((), ("species-A",)), (("sample-A",), ()), ((), ())])
def test_valid_empty_selections_keep_real_populations_and_global_qualifications(samples, species):
    selected = selection(samples=samples, species=species)
    packet = _packet(selected=selected)
    assert packet["values"] is not None and packet["values"]["rows"] == []
    assert packet["values"]["population"]["supplied_sample_count"] == 1
    assert packet["values"]["population"]["supplied_species_count"] == 1
    assert packet["values"]["population"]["selected_sample_count"] == len(samples)
    assert packet["values"]["population"]["selected_species_count"] == len(species)
    assert packet["values"]["population"]["returned_row_count"] == 0
    assert packet["context"]["qualifications"] == scientific.QUALIFICATIONS
    assert packet["values"]["population"]["association_species_ids"] == ["species-A"]
    validate_schema(contracts.project_ordinary_arsenic_return(packet, SOURCE), _return_schema())


def test_partial_input_or_missing_components_never_becomes_an_empty_measured_population():
    roles = {**_ROLE_STATES, "calibrations": "invalid"}
    packet = contracts.ordinary_arsenic_packet(arguments=_arguments(), input_state="partial", role_states=roles,
        components=None, calculation=dict(state="input_unavailable", call_count=0, native_invocation="not_requested"),
        file_states=dict(sheet="retained", components="producer_absent"),
        failures=[private.supplied_failure("input_invalid", "load", role="sheet", source_pointer="/calibrations")])
    assert packet["values"] is None and packet["context"]["role_states"] == roles
    assert packet["context"]["qualifications"] == scientific.QUALIFICATIONS
    assert packet["failures"][0]["source_location"] == "calibrations"
    assert "source_pointer" not in packet["failures"][0]
    assert "population" not in packet["context"]
    validate_schema(contracts.project_ordinary_arsenic_return(packet, SOURCE), _return_schema())
    packet["context"]["input_state"] = "complete"
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_packet(packet)


def test_completed_call_can_preserve_missing_retained_components_and_unknown_worker_count():
    packet = contracts.ordinary_arsenic_packet(arguments=_arguments(), input_state="complete", role_states=_ROLE_STATES,
        components=None, calculation=_CALCULATION,
        file_states=dict(sheet="retained", components="retention_failed"),
        failures=[private.supplied_failure("retention_failed", "capture", role="components")])
    assert packet["values"] is None and packet["context"]["calculation"]["call_count"] == 1
    packet["context"]["calculation"].update(state="worker_uncertain", call_count=None)
    assert contracts.validate_ordinary_arsenic_packet(packet) == packet
    packet["context"]["calculation"]["call_count"] = 0
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_packet(packet)


@pytest.mark.parametrize("change,expected,reason", [("zero_estimate", 0, None),
    ("negative_estimate", -1.5, None), ("zero_factor", None, "nonpositive_calibration_factor"),
    ("unknown_applicability", None, "calibration_applicability_unknown")])
def test_zero_negative_estimates_and_unavailable_calibration_stay_distinct(change, expected, reason):
    data = supplied_inputs()
    if change == "zero_estimate": data["samples"][0]["measurements"][0]["signal"]["value"] = 3
    elif change == "negative_estimate": data["samples"][0]["measurements"][0]["signal"]["value"] = 0
    elif change == "zero_factor": data["calibrations"][0]["concentration_per_signal"]["value"] = 0
    else: data["calibrations"][0]["applicability"] = "unknown"
    packet = _packet(data)
    cell = packet["values"]["rows"][0]["aliquot_concentration"]
    assert cell["value"] == expected and cell["reason"] == reason
    assert cell["state"] == ("unavailable" if expected is None else "qualified" if expected < 0 else "present")
    assert packet["context"]["calculation"]["state"] == "completed"
    validate_schema(contracts.project_ordinary_arsenic_return(packet, SOURCE), _return_schema())


def test_censoring_and_uncertainty_keep_supplied_meanings_without_new_error_bars_or_probability():
    data = supplied_inputs()
    data["calibrations"][0]["thresholds"] = [threshold(11), threshold(21, kind="LOQ", basis="original_sample")]
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"] = uncertainty()
    data["samples"][0]["measurements"][0]["signal"]["uncertainty"]["magnitude"] = -.2
    packet = _packet(data)
    row = packet["values"]["rows"][0]
    assert [item["kind"] for item in row["censoring"]] == ["LOD", "LOQ"]
    assert [item["estimate"]["value"] for item in row["censoring"]] == [10, 20]
    assert all(item["state"] == "below" and item["reported_bound"]["lower"] is None for item in row["censoring"])
    assert row["aliquot_concentration"]["uncertainty"] == dict(state="not_propagated", reason="no_selected_joint_uncertainty_model")
    assessment = packet["values"]["uncertainty_assessments"][0]
    assert assessment["statistical_validity"] == "not_assessed" and "negative_uncertainty_magnitude" in assessment["issues"]
    assert row["aliquot_concentration"]["value"] == 10
    assert not {"confidence", "function_probability", "total_arsenic", "speciation_completeness"} & packet["values"].keys()
    validate_schema(contracts.project_ordinary_arsenic_return(packet, SOURCE), _return_schema())


@pytest.mark.parametrize("change", ["present_null", "unavailable_zero", "censor_estimate", "bound_relation", "bound_basis"])
def test_quantity_availability_and_censoring_operand_links_cannot_contradict_retained_cells(change):
    data = supplied_inputs()
    data["calibrations"][0]["thresholds"] = [threshold(11)]
    packet = _packet(data); row = packet["values"]["rows"][0]
    if change == "present_null": row["linear_estimate"]["value"] = None
    elif change == "unavailable_zero": row["linear_estimate"].update(value=0, state="unavailable")
    elif change == "censor_estimate": row["censoring"][0]["estimate"]["value"] = 999
    elif change == "bound_relation": row["censoring"][0]["reported_bound"]["upper_relation"] = "less_or_equal"
    else: row["censoring"][0]["reported_bound"]["quantity_basis"]["identity"] = "other-analyte"
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_packet(packet)


def test_rational_numeric_denominator_is_not_an_experimental_population():
    data = supplied_inputs()
    data["samples"][0]["measurements"][0]["signal"]["value"] = 4
    data["calibrations"][0]["concentration_per_signal"]["value"] = .1
    packet = _packet(data)
    cell = packet["values"]["rows"][0]["aliquot_concentration"]
    exact = Fraction(.1)
    assert cell["exact_value"] == dict(numerator=str(exact.numerator), denominator=str(exact.denominator))
    assert cell["value"] == .1 and packet["values"]["population"]["returned_row_count"] == 1
    assert exact.denominator != packet["values"]["population"]["returned_row_count"]


def test_construction_validation_and_literal_return_need_no_calculator_original_input_or_network(monkeypatch):
    import socket
    _sheet, components = _documents()
    packet = _packet(); public = contracts.project_ordinary_arsenic_return(packet, SOURCE)
    def forbidden(*args, **kwargs): raise AssertionError("ordinary contract performed scientific work or a File read")
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", forbidden)
    monkeypatch.setattr(calculations, "validate_calibrated_signal_components", forbidden)
    monkeypatch.setattr(reader, "read_calibrated_signal_inputs", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert contracts.ordinary_arsenic_packet(arguments=_arguments(), input_state="complete", role_states=_ROLE_STATES,
        components=components, calculation=_CALCULATION, file_states=_FILE_STATES, failures=[]) == packet
    assert contracts.validate_ordinary_arsenic_packet(packet) == packet
    assert contracts.validate_ordinary_arsenic_return(public) == public
    assert contracts.project_ordinary_arsenic_return(packet, SOURCE) == public
    validate_schema(public, _return_schema())
    with pytest.raises(ValueError):
        contracts.ordinary_arsenic_packet(arguments=_arguments("read_stored"), input_state="complete", role_states=_ROLE_STATES,
            components=components, calculation=_CALCULATION, file_states=_FILE_STATES, failures=[])


@pytest.mark.parametrize("source", [INPUT, "source_wrong", "source_" + "A" * 24, "", None])
def test_only_an_actual_source_namespace_can_be_added_to_the_source_free_packet(source):
    packet = _packet()
    assert "source_ref" not in packet
    with pytest.raises(ValueError): contracts.project_ordinary_arsenic_return(packet, source)


def test_fact_schema_grants_only_top_source_and_keeps_nested_failure_provenance_opaque():
    from jsonschema import Draft202012Validator
    packet = _packet()
    nested = private.supplied_failure("schema_invalid", "load", role="components", source_ref=INPUT, source_pointer="/sheet")
    packet["failures"] = [private.supplied_failure_view(nested)]
    public = contracts.project_ordinary_arsenic_return(packet, SOURCE)
    assert public["failures"][0]["source_ref"] == INPUT and public["failures"][0]["source_location"] == "embedded_sheet"
    declared = contracts.ordinary_arsenic_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    assert declared["x-source"] == contracts.FACT_SOURCE
    Draft202012Validator.check_schema(declared)
    schema = declared["items"]; annotations = []
    def visit(node, path=()):
        if type(node) is dict:
            if "x-reference-namespace" in node: annotations.append((path, node["x-reference-namespace"]))
            for key, value in node.items(): visit(value, (*path, key))
        elif type(node) is list:
            for index, value in enumerate(node): visit(value, (*path, index))
    visit(schema)
    assert annotations == [(("properties", "source_ref"), "source")]
    validate_schema(public, schema)
    schema["properties"]["source_ref"]["pattern"] = "changed detached schema"
    assert _return_schema()["properties"]["source_ref"]["pattern"] == "^source_[0-9a-f]{24,64}$"
    assert json.loads(json.dumps(public)) == public


@pytest.mark.parametrize("change", ["global_qualifications", "native_claim", "count_bool", "count_zero", "unretained_values", "new_field"])
def test_context_and_closed_public_schema_do_not_admit_invented_meaning(change):
    packet = _packet()
    if change == "global_qualifications": packet["context"]["qualifications"] = []
    elif change == "native_claim": packet["context"]["calculation"]["native_invocation"] = "completed"
    elif change == "count_bool": packet["context"]["calculation"]["call_count"] = True
    elif change == "count_zero": packet["context"]["calculation"].update(state="worker_failed", call_count=0)
    elif change == "unretained_values": packet["file_states"]["components"] = "producer_absent"
    else: packet["values"]["score"] = .9
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_packet(packet)
