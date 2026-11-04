"""Ordinary projection controls over constructed saved data; no native fit."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import molecular_sequence_result_contracts as shared
from gene_annotation_episode import protease_kinetics_measurements as scientific
from gene_annotation_episode import protease_kinetics_result_contracts as contracts
from gene_annotation_episode.domain import validate_schema
from test_protease_kinetics_measurements import supplied_fixture, replace_measurements


SOURCE = "source_" + "a" * 24
SHEET = "artifact_" + "1" * 64
INPUT = "artifact_" + "2" * 64
POPULATIONS = {
    "time_point_count": "protease_supplied_time_coordinates",
    "substrate_count": "protease_original_substrate_rows",
    "supplied_curve_count": "protease_supplied_fluorescence_curve_rows",
    "requested_initial_point_count": "protease_native_requested_initial_window",
    "actual_initial_point_count": "protease_actual_sliced_time_indices"}


def _documents(*, matrix=None, missing_curve=False, context=True):
    """Reuse the existing declared synthetic observer fixture, never a fitter."""
    measurements, capture, assay = supplied_fixture()
    capture["native_record"]["result"] = "original private report /private/native/selected_results.txt"
    if matrix is not None:
        capture["observer"]["locals"]["covariance"] = deepcopy(matrix)
    if missing_curve:
        measurements["fluorescence_data"].pop()
        capture["observer"]["locals"]["initial_velocities"][-1] = 0
        replace_measurements(capture, measurements)
    sheet = scientific.populate_protease_kinetics_sheet(native_capture=capture,
        measurements=measurements, assay_context=assay if context else None)
    components = scientific.calculate_protease_kinetics_components(sheet)
    return sheet, components


def _sources():
    result = {role: shared.empty_file_state("not_requested") for role in shared.FILE_ROLES}
    for index, role in enumerate(("sheet", "components", "capture"), 1):
        digest = str(index) * 64
        file = dict(artifact_ref="artifact_" + digest, sha256=digest, size_bytes=index, format="json")
        result[role] = dict(state="retained_undeclared", file=file, declared=None,
            observed_identity={key: file[key] for key in ("sha256", "size_bytes")}, failure=None)
    return result


def _arguments(rows, *, mode="run_native", supplied=False):
    if mode == "run_native" or supplied:
        return dict(mode=mode, input=dict(namespace="artifact", reference=INPUT), rows=deepcopy(rows))
    return dict(mode=mode, result_ref=SOURCE, rows=deepcopy(rows))


def _projection(rows, *, documents=None, mode="run_native", legacy=False, sources=None):
    sheet, components = _documents() if documents is None else documents
    sources = _sources() if sources is None else sources
    if legacy:
        selector = dict(version=shared.SELECTOR_VERSION, mode=shared.MODES[0], operation=contracts.TOOL,
            saved_sheet_ref=None, rows=deepcopy(rows), return_files=[])
    else:
        selector = contracts.ordinary_protease_kinetics_selector(_arguments(rows, mode=mode),
            saved_sheet_ref=SHEET if mode == "calculate_saved" else None)
    return shared.select_stored_molecular_sequence_values(operation=contracts.TOOL, sheet=sheet,
        components=components, selection=selector, source_files=sources,
        association=dict(state="unavailable", reason="scientific_binding_unavailable"),
        calculation=dict(kind="selected_saved_calculation" if mode == "calculate_saved" else "original_stored",
            calculator_id=contracts.CALCULATOR_ID if mode == "calculate_saved" else None))


def _packet(rows, *, documents=None, mode="run_native"):
    projection = _projection(rows, documents=documents, mode=mode)
    return contracts.ordinary_protease_kinetics_packet(projection=projection,
        arguments=_arguments(rows, mode=mode), file_states={role: projection["source_files"][role]["state"]
            for role in contracts.FILE_ROLES}, failures=[])


def _return_schema():
    return contracts.ordinary_protease_kinetics_fact_sources()[contracts.FACT_SOURCE]["report_schema"]["items"]


@pytest.mark.parametrize("mode,supplied", [("run_native", True), ("calculate_saved", True),
    ("calculate_saved", False), ("read_stored", False)])
def test_closed_arguments_preserve_selected_mode_and_detach(mode, supplied):
    arguments = _arguments([], mode=mode, supplied=supplied)
    before = deepcopy(arguments)
    actual = contracts.validate_ordinary_protease_kinetics_arguments(arguments)
    validate_schema(actual, contracts.ARGUMENT_SCHEMA)
    actual["rows"].append({})
    assert arguments == before


@pytest.mark.parametrize("change", ["both_inputs", "native_source_only", "read_file", "wrong_namespace",
    "wrong_source", "extra_override", "missing_rows", "unknown_mode"])
def test_arguments_reject_ambiguous_inputs_and_saved_overrides(change):
    value = _arguments([], mode="calculate_saved")
    if change == "both_inputs": value["input"] = dict(namespace="artifact", reference=INPUT)
    elif change == "native_source_only": value["mode"] = "run_native"
    elif change == "read_file": value = _arguments([], mode="read_stored", supplied=True)
    elif change == "wrong_namespace": value = dict(mode="run_native", input=dict(namespace="source", reference=INPUT), rows=[])
    elif change == "wrong_source": value["result_ref"] = INPUT
    elif change == "extra_override": value["assay_context"] = None
    elif change == "missing_rows": del value["rows"]
    else: value["mode"] = "fit_again"
    with pytest.raises(ValueError): contracts.validate_ordinary_protease_kinetics_arguments(value)


def test_native_input_preserves_unknown_units_and_source_owned_measurement_gates():
    measurements, _capture, _assay = supplied_fixture()
    measurements["substrate_concentrations"][0] = -1
    value = dict(schema=contracts.INPUT_VERSION, measurements=measurements, assay_context=None)
    assert contracts.validate_ordinary_protease_kinetics_input(value) == value
    validate_schema(value, contracts.INPUT_SCHEMA)
    assert value["assay_context"] is None
    # Native shape/failure handling is not replaced by new acceptance criteria.
    value["measurements"]["fluorescence_data"] = "native malformed operand"
    assert contracts.validate_ordinary_protease_kinetics_input(value) == value


@pytest.mark.parametrize("change", ["extra_measurement", "missing_measurement", "context_extra", "version", "nonfinite"])
def test_input_contract_has_no_extra_assay_or_measurement_channel(change):
    measurements, _capture, assay = supplied_fixture()
    value = dict(schema=contracts.INPUT_VERSION, measurements=measurements, assay_context=assay)
    if change == "extra_measurement": value["measurements"]["threshold"] = 1
    elif change == "missing_measurement": del value["measurements"]["time_points"]
    elif change == "context_extra": value["assay_context"]["confidence"] = 1
    elif change == "version": value["schema"] = contracts.SHEET_VERSION
    else: value["measurements"]["enzyme_concentration"] = float("nan")
    with pytest.raises(ValueError): contracts.validate_ordinary_protease_kinetics_input(value)


@pytest.mark.parametrize("rows", [
    [{"row_id": {"kind": "orf", "row_index": 0}, "fields": ["interval"]}],
    [{"row_id": {"kind": "protease_curve", "substrate_ordinal": True}, "fields": ["residual"]}],
    [{"row_id": {"kind": "protease_covariance", "parameter_i": 2, "parameter_j": 0}, "fields": ["reported_matrix_entry"]}],
    [{"row_id": {"kind": "protease_fit"}, "fields": []}],
    [{"row_id": {"kind": "protease_fit"}, "fields": ["vmax", "vmax"]}],
    [{"row_id": {"kind": "protease_fit"}, "fields": ["vmax"]}] * 2])
def test_selector_keeps_original_strict_ordinals_and_unique_rows_fields(rows):
    with pytest.raises(ValueError): contracts.ordinary_protease_kinetics_selector(_arguments(rows))


def test_five_count_populations_are_distinct_and_legacy_labels_stay_literal():
    rows = [dict(row_id={"kind": "summary"}, fields=list(POPULATIONS))]
    documents = _documents()
    current = _projection(rows, documents=documents)
    old = _projection(rows, documents=documents, legacy=True)
    assert current["schema"] == contracts.PROJECTION_VERSION
    assert current["public"]["schema"] == contracts.VALUES_VERSION
    assert [(row["field"], row["value"], row["population_id"]) for row in current["public"]["rows"]] == [
        (name, value, POPULATIONS[name]) for name, value in zip(POPULATIONS, (5, 3, 3, 5, 5))]
    assert old["schema"] == shared.PROJECTION_VERSION
    assert old["public"]["schema"] == shared.PUBLIC_VERSION and "context" not in old["public"]
    assert {row["population_id"] for row in old["public"]["rows"]} == {"protease_original_substrate_rows"}
    assert [row["value"] for row in old["public"]["rows"]] == [row["value"] for row in current["public"]["rows"]]


def test_empty_selection_keeps_global_assay_covariance_and_unknown_qualifications():
    packet = _packet([])
    value = packet["values"]
    assert value["rows"] == [] and value["original_attempt_association"] == "unavailable"
    context = value["context"]
    assert context["schema"] == contracts.CONTEXT_VERSION
    assert context["assay"]["value"]["calibration"]["source_ref"] == "constructed-calibration-fixture"
    assert context["assay"]["value"]["enzyme_basis"] == "total_enzyme_concentration"
    assert context["population"]["value"]["substrate_count"] == 3
    assert context["covariance"]["raw_matrix"]["value"] == [[4., 1.], [1., 1.]]
    assert context["covariance"]["assessment"]["value"]["statistical_covariance_validity"] == "unestablished"
    assert context["physical"]["kcat"]["reason"]["value"] == "active_site_concentration_basis_unestablished"
    assert context["physical"]["apparent_turnover"]["uncertainty"]["total_uncertainty"]["value_state"] == "stored_null"
    assert context["qualifications"]["value"] == scientific.QUALIFICATIONS
    assert context["function_probability"]["value_state"] == "stored_null"
    text = json.dumps(packet)
    assert "/private/native/selected_results.txt" not in text
    assert "source_file_sha256" not in text and "native_return" not in context
    public = contracts.project_ordinary_protease_kinetics_return(packet, SOURCE)
    validate_schema(public, _return_schema())


def test_projection_does_not_read_files_or_invoke_any_native_or_calculator(monkeypatch):
    documents = _documents()
    before = deepcopy(documents)
    from gene_annotation_episode import molecular_sequence_native as native
    from gene_annotation_episode import molecular_sequence_driver as driver
    def forbidden(*args, **kwargs): raise AssertionError("projection performed work")
    with monkeypatch.context() as guards:
        guards.setattr(scientific, "calculate_protease_kinetics_components", forbidden)
        guards.setattr(native, "execute_molecular_sequence_request", forbidden)
        guards.setattr(driver, "run_molecular_sequence_driver", forbidden)
        guards.setattr(Path, "read_bytes", forbidden)
        projection = _projection([], documents=documents)
        assert shared.validate_molecular_sequence_projection(projection) == projection
        assert contracts.validate_ordinary_protease_kinetics_packet(_packet([], documents=documents))["values"]["rows"] == []
    assert documents == before


def test_missing_curve_native_vector_zero_is_not_measured_zero():
    rows = [dict(row_id=dict(kind="protease_curve", substrate_ordinal=2),
        fields=["native_fit_vector_value", "observed_signal_slope", "residual"])]
    packet = _packet(rows, documents=_documents(missing_curve=True))
    native, measured, residual = packet["values"]["rows"]
    assert (native["value_state"], native["value"]) == ("stored_value", 0)
    assert (measured["value_state"], measured["value"]) == ("stored_null", None)
    assert residual["value_state"] == "stored_null"
    assert packet["values"]["context"]["population"]["value"]["rows"][2]["curve_state"] == "curve_missing"


@pytest.mark.parametrize("matrix", [
    [[{"type": "nonfinite", "token": "inf"}, 0], [0, 1]],
    [["malformed retained entry", 0], [0, 1]],
    {"malformed_matrix": [1, None]}])
def test_nonfinite_and_malformed_native_matrix_stays_literal(matrix):
    rows = [dict(row_id=dict(kind="protease_covariance", parameter_i=0, parameter_j=0), fields=["reported_matrix_entry"])]
    packet = _packet(rows, documents=_documents(matrix=matrix))
    context = packet["values"]["context"]
    assert context["covariance"]["raw_matrix"]["value"] == matrix
    cell = packet["values"]["rows"][0]
    if type(matrix) is list:
        assert cell["value_state"] == "stored_value" and cell["value"] == matrix[0][0]
    else:
        assert cell["value_state"] == "path_missing" and cell["value"] is None
    assert context["covariance"]["state"]["value"] == "unavailable"
    validate_schema(contracts.project_ordinary_protease_kinetics_return(packet, SOURCE), _return_schema())


def test_saved_projection_retains_sheet_fit_identity_and_original_unavailable_custody():
    documents = _documents()
    before = deepcopy(documents)
    rows = [dict(row_id={"kind": "protease_fit"}, fields=["vmax", "km", "residual_degrees_of_freedom"])]
    packet = _packet(rows, documents=documents, mode="calculate_saved")
    assert packet["values"]["source_kind"] == "selected_saved_calculation"
    assert packet["values"]["original_attempt_association"] == "unavailable"
    assert [cell["value"] for cell in packet["values"]["rows"]] == [12., 3., 1]
    assert documents == before
    projection = _projection(rows, documents=documents, mode="calculate_saved")
    read = contracts.ordinary_protease_kinetics_packet(projection=projection,
        arguments=_arguments(rows, mode="read_stored"), file_states=packet["file_states"], failures=[])
    assert read == packet  # A literal read preserves the authenticated saved-source kind.
    with pytest.raises(ValueError): contracts.ordinary_protease_kinetics_selector(_arguments([], mode="calculate_saved"))


def test_new_profile_does_not_relabel_retained_v1_components():
    sheet, components = _documents()
    components["schema"] = "protease_kinetics_components_v1"
    with pytest.raises(ValueError): _projection([], documents=(sheet, components))
    assert _projection([], documents=(sheet, components), legacy=True)["public"]["components_schema"] == components["schema"]


@pytest.mark.parametrize("change", ["context_missing", "context_pointer", "context_source", "qualification_omitted", "count_bool", "unit", "probability"])
def test_controlled_packet_rejects_changed_global_provenance_and_cell_meaning(change):
    rows = [dict(row_id={"kind": "protease_fit"}, fields=["vmax"])]
    packet = _packet(rows)
    if change == "context_missing": del packet["values"]["context"]
    elif change == "context_pointer": packet["values"]["context"]["assay"]["source_pointer"] = "/other"
    elif change == "context_source": packet["values"]["context"]["assay"]["source_ref"] = INPUT
    elif change == "qualification_omitted": packet["values"]["context"]["qualifications"]["value"] = []
    elif change == "count_bool": packet["values"]["context"]["population"]["value"]["substrate_count"] = True
    elif change == "unit": packet["values"]["rows"][0]["unit"] = "invented unit"
    else: packet["values"]["context"]["function_probability"].update(value_state="stored_value", value=.5)
    with pytest.raises(ValueError): contracts.validate_ordinary_protease_kinetics_packet(packet)


@pytest.mark.parametrize("change", ["kind", "unit", "source", "unit_source", "missing_operand"])
def test_physical_ratio_operands_keep_exact_calibration_enzyme_and_km_associations(change):
    rows = [dict(row_id=dict(kind="protease_quantity", quantity="apparent_catalytic_efficiency"), fields=["value"])]
    packet = _packet(rows)
    operands = packet["values"]["rows"][0]["denominators"]
    assert [item["kind"] for item in operands] == ["calibration_response", "enzyme_concentration", "product_per_cleavage", "denominator"]
    if change == "kind": operands[0]["kind"] = "denominator"
    elif change == "unit": operands[1]["unit"] = "s^-1"
    elif change == "source": operands[-1]["source_ref"] = "artifact_" + "f" * 64
    elif change == "unit_source": operands[0]["unit_sources"][0]["source_pointer"] = "/assay_context/units/enzyme"
    else: operands.pop()
    with pytest.raises(ValueError): contracts.validate_ordinary_protease_kinetics_packet(packet)


@pytest.mark.parametrize("source", [INPUT, "source_wrong", "source_" + "A" * 24, "", None])
def test_return_requires_actual_source_namespace_lexically_without_claiming_custody(source):
    with pytest.raises(ValueError): contracts.project_ordinary_protease_kinetics_return(_packet([]), source)


def test_source_only_schema_preserves_opaque_provenance_and_is_detached():
    schema = _return_schema()
    annotations = []
    def visit(value, path=()):
        if type(value) is dict:
            if "x-reference-namespace" in value: annotations.append((path, value["x-reference-namespace"]))
            for key, child in value.items(): visit(child, (*path, key))
        elif type(value) is list:
            for index, child in enumerate(value): visit(child, (*path, index))
    visit(schema)
    assert annotations == [(("properties", "source_ref"), "source")]
    calibration = schema["properties"]["values"]["properties"]["context"]["properties"]["assay"]["properties"]["value"]["anyOf"][0]
    assert "format" not in calibration["properties"]["calibration"]["anyOf"][0]["properties"]["source_ref"]
    schema["properties"]["source_ref"]["pattern"] = "changed"
    assert _return_schema()["properties"]["source_ref"]["pattern"] == "^source_[0-9a-f]{24,64}$"


def test_unavailable_sources_have_explicit_missing_context_and_never_zero():
    sources = {role: shared.empty_file_state("unavailable") for role in shared.FILE_ROLES}
    projection = _projection([], documents=(None, None), sources=sources)
    packet = contracts.ordinary_protease_kinetics_packet(projection=projection, arguments=_arguments([]),
        file_states={role: "unavailable" for role in contracts.FILE_ROLES}, failures=[])
    assert packet["values"]["context"]["population"]["value_state"] == "source_unavailable"
    assert packet["values"]["context"]["population"]["value"] is None
    assert packet["values"]["context"]["covariance"]["raw_matrix"]["value_state"] == "source_unavailable"


def test_unavailable_components_do_not_expose_dynamic_unit_from_unadmitted_document():
    sources = _sources()
    sources["components"] = shared.empty_file_state("unavailable")
    rows = [dict(row_id={"kind": "protease_fit"}, fields=["vmax"])]
    projection = _projection(rows, sources=sources)
    assert projection["public"]["rows"][0]["value_state"] == "source_unavailable"
    assert projection["public"]["rows"][0]["unit"] is None
    assert shared.validate_molecular_sequence_projection(projection) == projection


def test_no_ascii_ordinary_registration_or_existing_profile_version_is_changed():
    assert contracts.TOOL not in shared.ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS
    assert (shared.SELECTOR_VERSION, shared.N_SELECTOR_VERSION, shared.O_SELECTOR_VERSION) == (
        "molecular_sequence_result_selector_v1", "molecular_sequence_result_selector_v3", "molecular_sequence_result_selector_v4")
    for version, operation in ((shared.PROTEASE_SELECTOR_VERSION, shared.OPERATIONS[0]),
            (shared.N_SELECTOR_VERSION, contracts.TOOL), (shared.O_SELECTOR_VERSION, contracts.TOOL)):
        with pytest.raises(ValueError): shared.validate_molecular_sequence_result_selector(dict(version=version,
            mode=shared.MODES[0], operation=operation, saved_sheet_ref=None, rows=[], return_files=[]))


_QUANTITY_FIELDS = ("value", "variance", "standard_uncertainty")
_QUANTITY_OPERANDS = {
    "product_vmax": ("calibration_response",),
    "product_formation_per_enzyme_concentration": ("calibration_response", "enzyme_concentration"),
    "apparent_turnover": ("calibration_response", "enzyme_concentration", "product_per_cleavage"),
    "kcat": ("calibration_response", "enzyme_concentration", "product_per_cleavage"),
    "apparent_catalytic_efficiency": ("calibration_response", "enzyme_concentration", "product_per_cleavage", "denominator"),
    "catalytic_efficiency": ("calibration_response", "enzyme_concentration", "product_per_cleavage", "denominator")}
_OPERAND_POINTERS = {
    "calibration_response": "/assay_context/calibration/response_per_product_concentration",
    "enzyme_concentration": "/measurements/enzyme_concentration",
    "product_per_cleavage": "/assay_context/product_per_cleavage",
    "denominator": "/fit_components/km/value"}


def _declarative_quantity_return(quantity, *, fields=_QUANTITY_FIELDS):
    """Construct qualified positive cells from the existing observer fixture."""
    measurements, capture, assay = supplied_fixture()
    assay["enzyme_basis"] = "active_site_concentration"
    capture["observer"]["locals"]["covariance"] = [[4., 3.], [1., 1.]]
    sheet = scientific.populate_protease_kinetics_sheet(native_capture=capture,
        measurements=measurements, assay_context=assay)
    components = scientific.calculate_protease_kinetics_components(sheet)
    packet = _packet([dict(row_id=dict(kind="protease_quantity", quantity=quantity), fields=list(fields))],
        documents=(sheet, components))
    return contracts.project_ordinary_protease_kinetics_return(packet, SOURCE)


@pytest.mark.parametrize("quantity,amount", [
    ("product_vmax", 6.), ("product_formation_per_enzyme_concentration", 12.),
    ("apparent_turnover", 12.), ("kcat", 12.),
    ("apparent_catalytic_efficiency", 4.), ("catalytic_efficiency", 4.)])
def test_declarative_return_accepts_each_quantity_with_its_actual_ordered_operands(quantity, amount, monkeypatch):
    from jsonschema import Draft202012Validator
    public = _declarative_quantity_return(quantity)
    before = deepcopy(public)
    def forbidden(*args, **kwargs): raise AssertionError("schema validation performed scientific work or read a File")
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    Draft202012Validator(_return_schema()).validate(public)
    rows = public["values"]["rows"]
    assert [row["field"] for row in rows] == list(_QUANTITY_FIELDS)
    assert rows[0]["value"] == amount
    kinds = _QUANTITY_OPERANDS[quantity]
    for row in rows:
        assert row["value_state"] == "stored_value" and row["value"] > 0
        assert tuple(operand["kind"] for operand in row["denominators"]) == kinds
        assert [operand["source_pointer"] for operand in row["denominators"]] == [_OPERAND_POINTERS[kind] for kind in kinds]
        assert row["scientific_qualifiers"]["states"]["quantity_uncertainty_state"]["value"] == "qualified"
        assert row["scientific_qualifiers"]["states"]["statistical_covariance_validity"]["value"] == "unestablished"
    assert public == before


@pytest.mark.parametrize("field", _QUANTITY_FIELDS)
@pytest.mark.parametrize("change", ["missing", "extra", "reordered", "wrong_kind"])
def test_declarative_return_rejects_incorrect_quantity_operand_count_order_or_kind(field, change):
    from jsonschema import Draft202012Validator
    public = _declarative_quantity_return("apparent_catalytic_efficiency", fields=(field,))
    schema = Draft202012Validator(_return_schema())
    assert schema.is_valid(public)
    operands = public["values"]["rows"][0]["denominators"]
    if change == "missing": operands.pop()
    elif change == "extra": operands.append(deepcopy(operands[0]))
    elif change == "reordered": operands[0], operands[1] = operands[1], operands[0]
    else: operands[-1]["kind"] = "enzyme_concentration"
    assert not schema.is_valid(public)


@pytest.mark.parametrize("field", _QUANTITY_FIELDS)
@pytest.mark.parametrize("quantity,other", [
    ("product_vmax", "product_formation_per_enzyme_concentration"),
    ("product_formation_per_enzyme_concentration", "apparent_turnover"),
    ("apparent_turnover", "apparent_catalytic_efficiency"),
    ("kcat", "product_vmax"),
    ("apparent_catalytic_efficiency", "product_formation_per_enzyme_concentration"),
    ("catalytic_efficiency", "apparent_turnover")])
def test_declarative_return_rejects_quantity_discriminator_with_another_operand_population(quantity, other, field):
    from jsonschema import Draft202012Validator
    public = _declarative_quantity_return(quantity, fields=(field,))
    schema = Draft202012Validator(_return_schema())
    assert schema.is_valid(public)
    # Keep the declared selection and returned row joined; only the retained
    # operands now contradict their asserted quantity identity.
    public["selection"]["rows"][0]["row_id"]["quantity"] = other
    public["values"]["rows"][0]["row_id"]["quantity"] = other
    assert not schema.is_valid(public)
