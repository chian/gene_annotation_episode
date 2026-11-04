"""Pure retained-CD contracts; synthetic handles establish no producer authority.

All components come from the existing calculator. The retained TSV comparison
reads the original208 control bytes and never imports or reruns Biomni.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator, validators

from gene_annotation_episode import circular_dichroism_contracts as contracts
from gene_annotation_episode import circular_dichroism_measurements as core
from test_circular_dichroism_measurements import supplied


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SOURCE = "source_" + "a" * 24
OTHER_SOURCE = "source_" + "b" * 24


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _measurements(case="protein"):
    value = supplied()
    if case == "nucleic":
        value["sample_type"] = "nucleic_acid"
        value["spectrum"].update(wavelength_data=[270., 280., 290., 295., 300.], cd_signal_data=[1., 1., 0., 1., 0.])
    elif case == "invalid_spectrum":
        value["spectrum"]["cd_signal_data"].pop()
    elif case == "constant_thermal":
        value["thermal"].update(temperature_data=[20., 30., 40.], thermal_cd_data=[2., 2., 2.])
    elif case == "negative_width":
        value["thermal"].update(temperature_data=[40., 30., 20., 10.], thermal_cd_data=[0., 1., 3., 4.])
    elif case == "unknown_units":
        value["spectrum"]["signal_unit"] = value["thermal"]["signal_unit"] = "unknown"
        value["thermal"]["measurement_wavelength_nm"] = None
    elif case == "absent_thermal":
        value["thermal"] = None
    elif case == "unknown_sample":
        value["sample_type"] = "unrecognized supplied type"
    elif case == "temperature_overflow":
        value["thermal"].update(temperature_data=[-1e308, 0., 1e308], thermal_cd_data=[0., 5., 10.])
    elif case == "missing_spectrum":
        value["spectrum"] = None
    else:
        assert case == "protein"
    return value


def _native(case="protein", *, measurements=None):
    value = _measurements(case) if measurements is None else measurements
    raw = json.dumps(value, allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    sheet = core.populate_circular_dichroism_sheet(measurements=value)
    return dict(version=contracts.RESULT_VERSION,
        request=dict(version=contracts.REQUEST_VERSION, input_file=dict(
            artifact_ref="artifact_" + digest, sha256=digest, size_bytes=len(raw), format="json")),
        sheet=sheet, components=core.calculate_circular_dichroism_components(sheet))


def _forbidden(*args, **kwargs):
    raise AssertionError("literal CD validation or projection attempted calculation, acquisition or native work")


def _no_math(monkeypatch):
    for name in ("_spectrum", "_thermal", "calculate_circular_dichroism_components"):
        monkeypatch.setattr(core, name, _forbidden)


@pytest.mark.parametrize("case", ["protein", "nucleic", "invalid_spectrum", "constant_thermal", "negative_width",
    "unknown_units", "absent_thermal", "unknown_sample", "temperature_overflow", "missing_spectrum"])
def test_core_generated_summaries_copy_full_source_cells_without_calculating(monkeypatch, case):
    native = _native(case)
    before = _canonical(native)
    _no_math(monkeypatch)
    admitted = contracts.validate_circular_dichroism_tool_result(native)
    assert _canonical(admitted) == before
    assert contracts.validate_circular_dichroism_components_shape(native["components"], sheet=native["sheet"]) == native["components"]
    result = contracts.project_circular_dichroism_return(native, source_ref=SOURCE)
    assert result["source_ref"] == SOURCE and result["qualifications"] == native["components"]["qualifications"]
    assert result["sample_type"] == native["components"]["sample_type"]
    assert result["thermal"]["summary"] == native["components"]["thermal"]["summary"]
    assert result["spectrum"]["features"] == [{key: deepcopy(row[key]) for key in (
        "name", "window_nm", "sign", "count", "population_count", "count_denominator")}
        for row in native["components"]["spectrum"]["features"]]
    assert native["sheet"]["source_method"]["native_execution"] is False
    assert _canonical(native) == before
    if case == "unknown_sample":
        assert result["sample_type"] is None and result["spectrum"]["state"] == "incompatible"
        assert result["thermal"]["state"] == "present"
    elif case == "negative_width":
        width = next(cell for cell in result["thermal"]["summary"] if cell["name"] == "source_transition_width")
        assert width["value"] < 0
    elif case == "absent_thermal":
        assert result["thermal"]["state"] == "not_supplied" and result["thermal"]["summary"] == []
    monkeypatch.setattr(core, "validate_circular_dichroism_sheet", _forbidden)
    monkeypatch.setattr(core, "populate_circular_dichroism_sheet", _forbidden)
    assert contracts.validate_circular_dichroism_return(json.loads(_canonical(result))) == result


@pytest.mark.parametrize("fault", ["extra_field", "version", "request_field", "request_format", "request_digest",
    "request_bool_size", "native_claim", "sample_identity", "qualifications", "formula", "unit", "count_float",
    "count_bool", "count_population", "count_denominator_false", "selected_outside", "selected_duplicate",
    "coordinate_count", "summary_order", "midpoint_float", "midpoint_outside", "midpoint_temperature",
    "relative_ordinal_float", "relative_denominator", "relative_value_outside", "nonfinite", "unsupported_label", "window_identity"])
def test_native_shape_and_retained_relationship_forgery_is_rejected(fault):
    native = _native(); components = native["components"]
    feature = components["spectrum"]["features"][0]
    summary = {cell["name"]: cell for cell in components["thermal"]["summary"]}
    if fault == "extra_field": native["findings"] = "not an allowed field"
    elif fault == "version": native["version"] = "other"
    elif fault == "request_field": native["request"]["path"] = "/tmp/unselected"
    elif fault == "request_format": native["request"]["input_file"]["format"] = "csv"
    elif fault == "request_digest": native["request"]["input_file"]["sha256"] = "0" * 64
    elif fault == "request_bool_size": native["request"]["input_file"]["size_bytes"] = True
    elif fault == "native_claim": native["sheet"]["source_method"]["native_execution"] = True
    elif fault == "sample_identity": components["sample_key"] = "a different sample"
    elif fault == "qualifications": components["qualifications"] = []
    elif fault == "formula": feature["count"]["formula_id"] = "structure_fraction"
    elif fault == "unit": feature["count"]["unit"] = "fraction"
    elif fault == "count_float": feature["count"]["value"] = float(feature["count"]["value"])
    elif fault == "count_bool": feature["count"]["value"] = True
    elif fault == "count_population": feature["population_count"] += 1
    elif fault == "count_denominator_false": feature["count"]["denominator"] = False
    elif fault == "selected_outside": feature["selected_indices"][-1] = 900
    elif fault == "selected_duplicate": feature["selected_indices"][1] = feature["selected_indices"][0]
    elif fault == "coordinate_count": native["sheet"]["measurements"]["spectrum"]["coordinate_count"] += 1
    elif fault == "summary_order": components["thermal"]["summary"].reverse()
    elif fault == "midpoint_float": summary["sampled_midpoint_index"]["value"] = 2.0
    elif fault == "midpoint_outside": summary["sampled_midpoint_index"]["value"] = 900
    elif fault == "midpoint_temperature": summary["sampled_midpoint_temperature"]["value"] = 41.
    elif fault == "relative_ordinal_float": components["thermal"]["relative_signal"][0]["index"] = 0.0
    elif fault == "relative_denominator": components["thermal"]["relative_signal"][0]["relative_signal"]["denominator"] = 11.
    elif fault == "relative_value_outside": components["thermal"]["relative_signal"][0]["relative_signal"]["value"] = 2.
    elif fault == "nonfinite": components["thermal"]["relative_signal"][0]["relative_signal"]["value"] = float("nan")
    elif fault == "window_identity": feature["window_nm"] = [1, 2]
    else: components["spectrum"]["source_structure_label"] = "calibrated helix percentage"
    with pytest.raises(ValueError): contracts.validate_circular_dichroism_tool_result(native)


@pytest.mark.parametrize("mode,namespace", [("calculate", "source"), ("calculate", "artifact"), ("read_stored", None), ("calculate_saved", None)])
def test_closed_tool_arguments_keep_original_identity_and_unbounded_explicit_selection(mode, namespace):
    view = dict(spectrum_ordinals=[2, 0, 2], thermal_ordinals=[2**200, 0], issue_ordinals=[])
    args = (dict(mode=mode, input=dict(namespace=namespace, reference=SOURCE if namespace == "source" else "artifact_" + "1" * 64), view=view)
        if mode == "calculate" else dict(mode=mode, result_ref=SOURCE, view=view))
    assert contracts.validate_circular_dichroism_tool_arguments(args) == args
    assert Draft202012Validator(contracts.circular_dichroism_tool_argument_schema()).is_valid(args)
    args["view"] = None
    assert contracts.validate_circular_dichroism_tool_arguments(args) == args


@pytest.mark.parametrize("fault", ["mode", "extra_path", "raw_measurements", "namespace", "reference", "bool_index",
    "float_index", "negative_index", "missing_view_key", "tuple_view", "saved_input", "missing_view"])
def test_tool_arguments_do_not_accept_paths_raw_data_or_ambiguous_ordinals(fault):
    args = dict(mode="calculate", input=dict(namespace="source", reference=SOURCE),
        view=dict(spectrum_ordinals=[], thermal_ordinals=[], issue_ordinals=[]))
    if fault == "mode": args["mode"] = "fit"
    elif fault == "extra_path": args["output_dir"] = "./"
    elif fault == "raw_measurements": args["measurements"] = supplied()
    elif fault == "namespace": args["input"]["namespace"] = "material"
    elif fault == "reference": args["input"]["reference"] = "artifact_" + "1" * 64
    elif fault == "bool_index": args["view"]["spectrum_ordinals"] = [True]
    elif fault == "float_index": args["view"]["spectrum_ordinals"] = [1.0]
    elif fault == "negative_index": args["view"]["spectrum_ordinals"] = [-1]
    elif fault == "missing_view_key": del args["view"]["issue_ordinals"]
    elif fault == "tuple_view": args["view"]["spectrum_ordinals"] = (1, 2)
    elif fault == "saved_input": args.update(mode="read_stored", result_ref=SOURCE)
    else: del args["view"]
    with pytest.raises(ValueError): contracts.validate_circular_dichroism_tool_arguments(args)


def test_view_preserves_order_duplicates_original_populations_and_unknown_rows(monkeypatch):
    native = _native(); before = _canonical(native)
    _no_math(monkeypatch)
    summary = contracts.project_circular_dichroism_return(native, source_ref=SOURCE)
    selection = dict(spectrum_ordinals=[2, 0, 2, 99], thermal_ordinals=[4, 2, 2, 99], issue_ordinals=[0, 0, 99])
    view = contracts.project_circular_dichroism_view(native, source_ref=SOURCE, view=selection)
    assert view["selection"] == selection and view["summary"] == summary
    assert [row["ordinal"] for row in view["spectrum_rows"]] == selection["spectrum_ordinals"]
    assert [row["signal"]["value"] for row in view["spectrum_rows"][:-1]] == [supplied()["spectrum"]["cd_signal_data"][index] for index in [2, 0, 2]]
    assert view["spectrum_rows"][-1]["availability"] == "out_of_range"
    assert [row["relative_signal"] for row in view["thermal_rows"][:-1]] == [native["components"]["thermal"]["relative_signal"][index]["relative_signal"] for index in [4, 2, 2]]
    assert view["thermal_rows"][-1]["relative_signal"] is None
    assert all(row["availability"] == "out_of_range" for row in view["issues"])
    empty = contracts.project_circular_dichroism_view(native, source_ref=SOURCE, view=None)
    assert empty["summary"] == summary and empty["spectrum_rows"] == empty["thermal_rows"] == empty["issues"] == []
    assert _canonical(native) == before


def test_view_distinguishes_explicit_null_missing_invalid_and_observed_zero(monkeypatch):
    value = supplied()
    value["spectrum"].update(wavelength_data=[0., 195.], cd_signal_data=[None, 0., 3.])
    native = _native(measurements=value)
    _no_math(monkeypatch)
    view = contracts.project_circular_dichroism_view(native, source_ref=SOURCE,
        view=dict(spectrum_ordinals=[0, 1, 2, 3], thermal_ordinals=[], issue_ordinals=[0, 0, 999]))
    rows = view["spectrum_rows"]
    assert rows[0]["wavelength"]["state"] == "invalid_input" and rows[0]["wavelength"]["value"] == 0.
    assert rows[0]["signal"]["input_kind"] == "null" and rows[0]["signal"]["state"] == "invalid_input"
    assert rows[1]["signal"]["state"] == "present" and rows[1]["signal"]["value"] == 0.
    assert rows[2]["wavelength"]["state"] == "missing" and rows[2]["signal"]["value"] == 3.
    assert rows[3]["availability"] == "out_of_range"
    assert view["issues"][0] == view["issues"][1]
    assert view["issues"][-1]["issue"] is None
    assert view["summary"]["spectrum"]["state"] == "invalid_input" and view["summary"]["thermal"]["state"] == "present"


def test_constant_thermal_and_invalid_wavelength_do_not_invent_derived_values(monkeypatch):
    constant = _native("constant_thermal")
    value = supplied(); value["thermal"]["measurement_wavelength_nm"] = 0.
    invalid = _native(measurements=value)
    _no_math(monkeypatch)
    selection = dict(spectrum_ordinals=[], thermal_ordinals=[0, 1, 2], issue_ordinals=[])
    view = contracts.project_circular_dichroism_view(constant, source_ref=SOURCE, view=selection)
    assert all(row["availability"] == "present" and row["relative_signal"] is None
        and row["in_source_transition_window"] is None for row in view["thermal_rows"])
    summary = contracts.project_circular_dichroism_return(invalid, source_ref=SOURCE)
    assert summary["thermal"]["measurement_wavelength"] == dict(state="invalid_input", value=0., unit="nm", reason="nonpositive_measurement_wavelength")
    assert summary["thermal"]["summary"] == [] and summary["spectrum"]["state"] == "present"


@pytest.mark.parametrize("fault", ["source", "ordinal_float", "reorder", "boolean_value", "wrong_unit", "wrong_kind",
    "relative_denominator", "findings", "null_selection", "changed_length", "spectrum_signal_unit", "thermal_signal_unit", "signal_none"])
def test_selected_view_relationships_are_validated(fault):
    view = contracts.project_circular_dichroism_view(_native(), source_ref=SOURCE,
        view=dict(spectrum_ordinals=[0, 1], thermal_ordinals=[2], issue_ordinals=[]))
    if fault == "source": view["source_ref"] = OTHER_SOURCE
    elif fault == "ordinal_float": view["spectrum_rows"][0]["ordinal"] = 0.0
    elif fault == "reorder": view["spectrum_rows"].reverse()
    elif fault == "boolean_value": view["spectrum_rows"][0]["signal"]["value"] = True
    elif fault == "wrong_unit": view["spectrum_rows"][0]["wavelength"]["unit"] = "mdeg"
    elif fault == "wrong_kind": view["spectrum_rows"][0]["signal"]["input_kind"] = "integer"
    elif fault == "relative_denominator": view["thermal_rows"][0]["relative_signal"]["denominator"] = 11.
    elif fault == "findings": view["findings"] = "not allowed"
    elif fault == "null_selection": view["selection"] = None
    elif fault == "spectrum_signal_unit": view["spectrum_rows"][0]["signal"]["unit"] = "delta_epsilon"
    elif fault == "thermal_signal_unit": view["thermal_rows"][0]["signal"]["unit"] = "unknown"
    elif fault == "signal_none": view["spectrum_rows"][0]["signal"]["unit"] = None
    else: view["thermal_rows"].append(deepcopy(view["thermal_rows"][0]))
    with pytest.raises(ValueError): contracts.validate_circular_dichroism_view(view)


def test_no_silent_view_limit_and_projection_is_detached():
    native = _native()
    view = contracts.project_circular_dichroism_view(native, source_ref=SOURCE,
        view=dict(spectrum_ordinals=[0] * 300, thermal_ordinals=[], issue_ordinals=[]))
    assert len(view["spectrum_rows"]) == 300 and all(row["ordinal"] == 0 for row in view["spectrum_rows"])
    view["spectrum_rows"][0]["signal"]["value"] = 999.
    assert view["spectrum_rows"][1]["signal"]["value"] == supplied()["spectrum"]["cd_signal_data"][0]
    view["summary"]["thermal"]["summary"].clear()
    assert native["components"]["thermal"]["summary"]


@pytest.mark.parametrize("where", ["key", "value"])
def test_non_utf8_nested_input_metadata_is_rejected(where):
    value = supplied()
    value["external_metadata"] = {"\ud800": 1} if where == "key" else {"literal": "\ud800"}
    native = _native(measurements=value)
    with pytest.raises(ValueError, match="finite_json_required"):
        contracts.validate_circular_dichroism_tool_result(native)


def test_frozen_window_descriptor_uses_the_core_definition_without_math(monkeypatch):
    result = contracts.project_circular_dichroism_return(_native(), source_ref=SOURCE)
    result["spectrum"]["features"][0]["window_nm"] = [1, 2]
    _no_math(monkeypatch)
    monkeypatch.setattr(core, "populate_circular_dichroism_sheet", _forbidden)
    monkeypatch.setattr(core, "validate_circular_dichroism_sheet", _forbidden)
    assert not Draft202012Validator(contracts.circular_dichroism_return_schema()).is_valid(result)
    with pytest.raises(ValueError): contracts.validate_circular_dichroism_return(result)


def test_frozen_summary_schema_is_closed_strict_and_grants_only_its_source(monkeypatch):
    result = contracts.project_circular_dichroism_return(_native(), source_ref=SOURCE)
    _no_math(monkeypatch)
    monkeypatch.setattr(core, "populate_circular_dichroism_sheet", _forbidden)
    monkeypatch.setattr(core, "validate_circular_dichroism_sheet", _forbidden)
    for owner, name in [(builtins, "open"), (Path, "open"), (socket, "socket"), (subprocess, "Popen"), (subprocess, "run")]:
        monkeypatch.setattr(owner, name, _forbidden)
    descriptor = contracts.circular_dichroism_fact_sources()[contracts.FACT_SOURCE]
    schema = descriptor["report_schema"]
    strict = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda _checker, item: type(item) is int))
    assert strict(schema).is_valid([result])
    assert contracts.validate_circular_dichroism_return(result) == result
    references = []
    def visit(node, path=()):
        if type(node) is dict:
            if node.get("format") == "reference": references.append((path, node["x-reference-namespace"]))
            for key, child in node.items(): visit(child, (*path, key))
        elif type(node) is list:
            for index, child in enumerate(node): visit(child, (*path, index))
    visit(schema)
    assert references == [(("items", "properties", "source_ref"), "source")]
    altered = deepcopy(result); altered["spectrum"]["features"][0]["count"]["value"] = 3.0
    assert not strict(schema).is_valid([altered])
    with pytest.raises(ValueError): contracts.validate_circular_dichroism_return(altered)


def test_retained_original_control_tables_match_without_rerunning_biomni():
    root = Path(__file__).parent / "fixtures/circular_dichroism_native_control"
    names = (("supplied_numeric_control_cd_spectrum_analysis.txt", "cc9890bdf6af58a1439c2c8990774ace8d50df64fd08a833c67aa8ba7bd8c193"),
        ("supplied_numeric_control_thermal_denaturation.txt", "5f1ac12c2a48a4231b77ab7ca3c446f951b62b0446b9f79e02786853754993ee"))
    captured = []
    for name, digest in names:
        raw = (root / name).read_bytes(); assert hashlib.sha256(raw).hexdigest() == digest
        captured.append(raw.decode().splitlines())
    value = supplied(); native = _native(measurements=value)
    assert captured[0][0] == "Wavelength (nm)\tCD Signal"
    assert [[float(item) for item in line.split("\t")] for line in captured[0][1:]] == [
        [x, y] for x, y in zip(value["spectrum"]["wavelength_data"], value["spectrum"]["cd_signal_data"], strict=True)]
    assert captured[1][0] == "Temperature (°C)\tCD Signal\tUnfolded Fraction"  # Original header, not a measurement claim.
    assert [[float(item) for item in line.split("\t")] for line in captured[1][1:]] == [
        [x, y, row["relative_signal"]["value"]] for x, y, row in zip(value["thermal"]["temperature_data"],
            value["thermal"]["thermal_cd_data"], native["components"]["thermal"]["relative_signal"], strict=True)]
    assert native["sheet"]["source_method"]["native_execution"] is False
