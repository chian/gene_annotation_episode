"""Finite selected preparation using the actual pinned native libraries.

No acquisition, installation, gates, summaries, scheduling or scoring occurs
here. Raw input records remain intact; each output keeps its primary identity.
"""

from __future__ import annotations

from copy import copy, deepcopy
import importlib
import math

from . import fluorescence_event_contracts as core
from .fluorescence_fcs_reader import FORMAT_PROFILE, decode_selected_fcs
from .fluorescence_preparation_contracts import (
    BACKENDS, COMPENSATE_METHOD, POLICY, SCALE_METHOD, _parent_request,
    preparation_problem, scaling_units_compatible, validate_matrix_read_result, validate_preparation_outcome,
)
from .fluorescence_preparation_readers import _load_flowutils, _metadata_tokens, _native_problem


def _initial(parent, request, method):
    _parent_request(request, parent)
    core._need(request["recipe"]["method"] == method, "invalid_parameters")
    mapping = [dict(input_channel_key=old["key"], input_ordinal=old["ordinal"],
                    output_channel_key=new["key"], output_ordinal=new["ordinal"])
               for old, new in zip(parent["channels"], request["output"]["channels"])]
    parameters = dict(version="fluorescence_resolved_preparation_v1",
                      request_sha256=core.digest(request), input_domain_key=parent["domain"]["key"],
                      output_domain_key=request["output"]["key"], method=method,
                      backend=deepcopy(BACKENDS[method]), channel_map=mapping,
                      scaling=None, compensation=None, transformation=None,
                      status="complete", problems=[], diagnostics=[])
    return dict(version="fluorescence_preparation_outcome_v1", status="complete",
                data=None, parameters=parameters, issues=[])


_ISSUE_FOR_PROBLEM = {
    "input_unavailable": "measurement_domain_unavailable",
    "parameter_unavailable": "source_unavailable",
    "parameter_identity_mismatch": "retained_artifact_mismatch",
    "parameter_invalid": "native_format_mismatch",
    "channel_mapping_incompatible": "measurement_domain_mismatch",
    "domain_incompatible": "measurement_domain_mismatch",
    "already_prepared": "measurement_domain_mismatch",
    "preparation_state_unknown": "measurement_domain_unavailable",
    "backend_unavailable": "decoder_unavailable",
    "matrix_singular": "measurement_domain_unavailable",
    "native_preparation_failed": "measurement_domain_unavailable",
    "derived_nonfinite": "derived_numeric_overflow",
    "incomplete_native_array": "incomplete_population",
}


def _add_problem(outcome, request, code, *, channel=None, ordinal=None, error=None):
    problem = preparation_problem(code, request["output"]["key"],
                                  channel_key=channel, event_ordinal=ordinal)
    if problem not in outcome["parameters"]["problems"]:
        outcome["parameters"]["problems"].append(problem)
    issue = core.issue(_ISSUE_FOR_PROBLEM[code], "domain",
                       source_key=request["output"]["source_key"],
                       sample_key=request["output"]["sample_key"],
                       domain_key=request["output"]["key"], channel_key=channel,
                       event_ordinal=ordinal)
    if issue not in outcome["issues"]:
        outcome["issues"].append(issue)
    if error is not None:
        diagnostic = dict(problem_code=code,
                          exception_class=type(error).__module__ + "." + type(error).__qualname__)
        if diagnostic not in outcome["parameters"]["diagnostics"]:
            outcome["parameters"]["diagnostics"].append(diagnostic)


def _finish(outcome, parent, request, status=None):
    if status is None:
        status = "partial" if outcome["parameters"]["problems"] else "complete"
    outcome["status"] = outcome["parameters"]["status"] = status
    return validate_preparation_outcome(outcome, request=request, parent=parent)


def _failed(outcome, parent, request, status, code, *, error=None):
    _add_problem(outcome, request, code, error=error)
    return _finish(outcome, parent, request, status)


def _state_problem(parent, *, scaling):
    domain = parent["domain"]
    if domain["state"] != "available" or parent["source"]["extent"] == "unavailable":
        return "unavailable", "input_unavailable"
    if not scaling:
        for field in ("compensation", "transformation"):
            state = domain[field]["state"]
            if state == "applied":
                return "incompatible", "already_prepared"
            if state in {"unknown", "failed"}:
                return "incompatible", "preparation_state_unknown"
    if scaling:
        if (domain["scale_kind"] != "encoded" or domain["parent_domain_key"] is not None
                or parent["source"]["format_profile"] != FORMAT_PROFILE):
            return "incompatible", "domain_incompatible"
        if domain.get("scaling", {}).get("state") == "applied":
            return "incompatible", "already_prepared"
        if domain.get("scaling", {}).get("state") in {"unknown", "failed"}:
            return "incompatible", "preparation_state_unknown"
    return None


def _data(parent, request):
    output = request["output"]
    events = []
    for index, old in enumerate(parent["events"]):
        events.append(dict(sample_key=output["sample_key"], domain_key=output["key"],
            event_ordinal=old["event_ordinal"], source_ordinal=index,
            location=dict(record_ordinal=index, line_start=None, line_end=None,
                          byte_start=None, byte_end=None),
            values=[dict(channel_key=channel["key"], measurement=deepcopy(cell["measurement"]))
                    for channel, cell in zip(output["channels"], old["values"])]))
    return dict(version="fluorescence_prepared_event_data_v1",
                request_sha256=core.digest(request), input_parse_sha256=core.digest(parent),
                sample_key=output["sample_key"], parent_domain_key=parent["domain"]["key"],
                domain_key=output["key"], channels=[dict(row, domain_key=output["key"])
                                                 for row in deepcopy(output["channels"])],
                correspondence=[dict(source_ordinal=index, event_ordinal=row["event_ordinal"])
                                for index, row in enumerate(parent["events"])], events=events)


def _derived(data, row, column, number, outcome, request):
    cell = data["events"][row]["values"][column]
    ordinal = data["events"][row]["event_ordinal"]
    value = float(number)
    if math.isfinite(value):
        cell["measurement"] = dict(value=value, state="derived", raw=None)
    else:
        cell["measurement"] = dict(value=None, state="invalid", raw=None)
        _add_problem(outcome, request, "derived_nonfinite", channel=cell["channel_key"], ordinal=ordinal)


def _unavailable_values(data, row, columns, outcome, request, problem):
    for column in columns:
        cell = data["events"][row]["values"][column]
        cell["measurement"] = dict(value=None, state="unavailable", raw=None)
        _add_problem(outcome, request, problem, channel=cell["channel_key"],
                     ordinal=data["events"][row]["event_ordinal"])


def _scaling_resolution(native, parent, request, outcome):
    names = [f"p{index}{suffix}" for index in range(1, len(parent["channels"]) + 1)
             for suffix in ("n", "s", "e", "g", "r")]
    names.extend(["datatype", "timestep"])
    tokens, invalid = _metadata_tokens(native, names)
    rows = []
    time_channels = [row for row in parent["channels"]
                     if row["native_name"] is not None and row["native_name"].lower() == "time"]
    if len(time_channels) > 1:
        _add_problem(outcome, request, "channel_mapping_incompatible")
    time_key = time_channels[0]["key"] if len(time_channels) == 1 else None
    for position, channel in enumerate(parent["channels"], 1):
        raw = {suffix: tokens.get(f"p{position}{suffix}") for suffix in ("e", "g", "r")}
        row = dict(input_channel_key=channel["key"], native_parameter_number=position,
                   pne_raw=raw["e"], png_raw=raw["g"], pnr_raw=raw["r"],
                   decades=None, log_zero=None, range=None, gain=None,
                   gain_applied=False, log_linearization_applied=False)
        output_key = request["output"]["channels"][position - 1]["key"]
        bad = any(f"p{position}{suffix}" in invalid for suffix in ("n", "s", "e", "g", "r"))
        if tokens.get(f"p{position}n") != channel["native_name"]:
            _add_problem(outcome, request, "channel_mapping_incompatible", channel=output_key)
        try:
            if raw["e"] is None or raw["r"] is None:
                raise ValueError("required metadata absent")
            decades, log_zero = [float(token) for token in raw["e"].split(",")]
            native_range = float(raw["r"])
            gain = None if raw["g"] is None else float(raw["g"])
            if (not all(math.isfinite(number) for number in (decades, log_zero, native_range))
                    or decades < 0 or log_zero < 0 or native_range <= 0
                    or (decades > 0 and log_zero <= 0)
                    or (gain is not None and (not math.isfinite(gain) or gain <= 0))):
                raise ValueError("invalid required metadata")
            # FlowIO explicitly suppresses Time-channel gain. Raw supplied gain
            # stays in png_raw, while gain records its effective library value.
            effective_gain = 1.0 if channel["key"] == time_key and gain is not None else gain
            row.update(decades=decades, log_zero=log_zero, range=native_range,
                       gain=effective_gain, gain_applied=effective_gain not in (None, 1.0),
                       log_linearization_applied=decades > 0)
        except (ValueError, OverflowError, TypeError):
            bad = True
        if bad:
            _add_problem(outcome, request, "parameter_invalid", channel=output_key)
        rows.append(row)
    timestep_raw = tokens.get("timestep")
    timestep = None
    bad_time = "timestep" in invalid
    if timestep_raw is not None:
        try:
            timestep = float(timestep_raw)
            if not math.isfinite(timestep) or timestep <= 0:
                raise ValueError("invalid timestep")
        except (ValueError, OverflowError):
            timestep, bad_time = None, True
    if bad_time or "datatype" in invalid:
        _add_problem(outcome, request, "parameter_invalid")
    return dict(source_file=deepcopy(parent["source"]["file"]),
                dataset_position=parent["source"]["dataset_position"], metadata_policy=POLICY,
                channels=rows, time=dict(channel_key=time_key, timestep_raw=timestep_raw,
                                        timestep=timestep, applied=time_key is not None and timestep is not None))


def prepare_fcs_scaling(raw: bytes, *, parent: dict, request: dict) -> dict:
    """Apply only FlowIO1.4.0 gain/log/time preprocessing after strict preflight."""
    outcome = _initial(parent, request, SCALE_METHOD)
    problem = _state_problem(parent, scaling=True)
    if problem is not None:
        return _failed(outcome, parent, request, *problem)
    decoded = decode_selected_fcs(raw, source=parent["source"])
    native = decoded["native"]
    if native is not None and hasattr(native, "text"):
        outcome["parameters"]["scaling"] = _scaling_resolution(native, parent, request, outcome)
        if outcome["parameters"]["problems"]:
            return _finish(outcome, parent, request, "incompatible")
    if decoded["error"] is not None:
        return _failed(outcome, parent, request, *_native_problem(decoded["error"]))
    if not scaling_units_compatible(parent, request, outcome["parameters"]["scaling"]):
        return _failed(outcome, parent, request, "incompatible", "domain_incompatible")
    count = decoded["count"]
    if count != len(parent["channels"]) or native.events is None:
        return _failed(outcome, parent, request, "incompatible", "channel_mapping_incompatible")
    represented = (len(native.events) + count - 1) // count
    if represented != len(parent["events"]):
        return _failed(outcome, parent, request, "incompatible", "parameter_identity_mismatch")
    for row in parent["events"]:
        start = row["source_ordinal"] * count
        for column, cell in enumerate(row["values"]):
            number = cell["measurement"]["value"]
            if number is not None and (start + column >= len(native.events)
                                      or native.events[start + column] != number):
                return _failed(outcome, parent, request, "incompatible", "parameter_identity_mismatch")
    resolution = outcome["parameters"]["scaling"]
    affected = {index for index, channel in enumerate(resolution["channels"])
                if channel["gain_applied"] or channel["log_linearization_applied"]
                or (resolution["time"]["applied"] and channel["input_channel_key"] == resolution["time"]["channel_key"])}
    complete_rows = len(native.events) // count
    working = native
    if len(native.events) % count:
        # A view of the genuine complete prefix is sufficient for as_array.
        # The incomplete represented row remains below with unavailable changed
        # cells; no value or row is padded to make the library reshape succeed.
        working = copy(native)
        working.events = native.events[:complete_rows * count]
    try:
        prepared = working.as_array(preprocess=True)
    except (ValueError, TypeError, OverflowError, FloatingPointError) as error:
        return _failed(outcome, parent, request, "failed", "native_preparation_failed", error=error)
    if prepared.shape != (complete_rows, count):
        return _failed(outcome, parent, request, "failed", "incomplete_native_array")
    data = _data(parent, request)
    for row_index, row in enumerate(parent["events"]):
        for column in affected:
            if row_index >= complete_rows or row["values"][column]["measurement"]["value"] is None:
                _unavailable_values(data, row_index, [column], outcome, request, "input_unavailable")
            else:
                _derived(data, row_index, column, prepared[row_index, column], outcome, request)
    if parent["source"]["extent"] == "partial" or len(native.events) % count:
        _add_problem(outcome, request, "incomplete_native_array")
    outcome["data"] = data
    return _finish(outcome, parent, request)


def prepare_spill_compensation(parent: dict, *, matrix: dict, request: dict) -> dict:
    """Solve only the selected conventional matrix with exact ordered axes."""
    outcome = _initial(parent, request, COMPENSATE_METHOD)
    matrix = validate_matrix_read_result(matrix)
    parameters = request["recipe"]["parameters"]
    if any(matrix[field] != parameters[name] for field, name in (
            ("file", "matrix_file"), ("dataset_position", "dataset_position"), ("keyword", "keyword"))):
        return _failed(outcome, parent, request, "incompatible", "parameter_identity_mismatch")
    outcome["parameters"]["compensation"] = matrix
    problem = _state_problem(parent, scaling=False)
    if problem is not None:
        return _failed(outcome, parent, request, *problem)
    if parent["domain"]["comparison_basis"] != parameters["input_domain_basis"]:
        return _failed(outcome, parent, request, "incompatible", "domain_incompatible")
    if matrix["state"] != "available":
        for problem in matrix["problems"]:
            _add_problem(outcome, request, problem["code"])
        return _finish(outcome, parent, request, matrix["state"])
    axes = parameters["axes"]
    names = [row["native_name"] for row in parent["channels"]]
    if matrix["axis_tokens"] != [axis["native_label"] for axis in axes]:
        return _failed(outcome, parent, request, "incompatible", "channel_mapping_incompatible")
    for axis in axes:
        index = axis["input_ordinal"]
        if (index >= len(parent["channels"]) or parent["channels"][index]["key"] != axis["input_channel_key"]
                or names[index] != axis["native_label"] or names.count(axis["native_label"]) != 1):
            return _failed(outcome, parent, request, "incompatible", "channel_mapping_incompatible")
    backend = _load_flowutils()
    if backend is None:
        return _failed(outcome, parent, request, "unavailable", "backend_unavailable")
    try:
        np = importlib.import_module("numpy")
    except (ImportError, OSError):
        return _failed(outcome, parent, request, "unavailable", "backend_unavailable")
    data = _data(parent, request)
    # Project only participating columns in original column order. The explicit
    # library index map then addresses those columns in matrix-axis order. No
    # missing untouched value needs a numeric placeholder in the native array.
    columns = sorted(axis["input_ordinal"] for axis in axes)
    native_indices = [columns.index(axis["input_ordinal"]) for axis in axes]
    complete_rows, numerical_rows = [], []
    for index, row in enumerate(parent["events"]):
        values = [row["values"][column]["measurement"]["value"] for column in columns]
        if any(value is None for value in values):
            _unavailable_values(data, index, columns, outcome, request, "input_unavailable")
            continue
        try:
            converted = [float(value) for value in values]
        except (OverflowError, ValueError) as error:
            _unavailable_values(data, index, columns, outcome, request, "derived_nonfinite")
            _add_problem(outcome, request, "derived_nonfinite", ordinal=row["event_ordinal"], error=error)
            continue
        if not all(math.isfinite(value) for value in converted):
            _unavailable_values(data, index, columns, outcome, request, "derived_nonfinite")
            continue
        complete_rows.append(index)
        numerical_rows.append(converted)
    try:
        # Reparse the retained keyword with the actual library, never accepting
        # replacement coefficients supplied independently from its raw token.
        native_matrix, native_axes = backend.get_spill(matrix["raw_token"])
        if native_axes != matrix["axis_tokens"] or native_matrix.tolist() != matrix["values"]:
            return _failed(outcome, parent, request, "incompatible", "parameter_identity_mismatch")
        array = np.asarray(numerical_rows, dtype=np.float64).reshape((len(complete_rows), len(columns)))
        prepared = backend.compensate(array, native_matrix, fluoro_indices=native_indices)
    except np.linalg.LinAlgError as error:
        return _failed(outcome, parent, request, "failed", "matrix_singular", error=error)
    except (ValueError, TypeError, IndexError, OverflowError, FloatingPointError) as error:
        return _failed(outcome, parent, request, "failed", "native_preparation_failed", error=error)
    if prepared.shape != (len(complete_rows), len(columns)):
        return _failed(outcome, parent, request, "failed", "incomplete_native_array")
    for native_row, original_row in enumerate(complete_rows):
        for native_column, original_column in enumerate(columns):
            _derived(data, original_row, original_column, prepared[native_row, native_column], outcome, request)
    if parent["source"]["extent"] == "partial":
        _add_problem(outcome, request, "incomplete_native_array")
    outcome["data"] = data
    return _finish(outcome, parent, request)
