"""Closed data ports for explicitly selected fluorescence preparation.

The common fluorescence sheet remains the only numerical scoring authority.
These validators check identities and lineage, never rerun a native operation.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from . import fluorescence_event_contracts as core

SCALE_METHOD = "fcs_scale_flowio_1_4_0"
COMPENSATE_METHOD = "spill_compensate_flowutils_1_2_2"
METHODS = {SCALE_METHOD, COMPENSATE_METHOD}
POLICY = "strict_present_fcs_metadata_v1"
STATUSES = {"complete", "partial", "unavailable", "failed", "incompatible"}
PROBLEM_CODES = set("""input_unavailable parameter_unavailable parameter_identity_mismatch
parameter_invalid channel_mapping_incompatible domain_incompatible already_prepared
preparation_state_unknown backend_unavailable matrix_singular native_preparation_failed
derived_nonfinite incomplete_native_array""".split())
BACKENDS = {
    SCALE_METHOD: dict(distribution="FlowIO", version="1.4.0", callable="flowio.FlowData.as_array"),
    COMPENSATE_METHOD: dict(distribution="FlowUtils", version="1.2.2", callable="flowutils.compensate.compensate"),
}
_CODE = "invalid_parameters"


def _need(condition):
    core._need(condition, _CODE)


def _keys(value, names):
    core._keys(value, names, _CODE)


def _list(value):
    core._list(value, _CODE)


def _number(value, *, nullable=False):
    _need((nullable and value is None) or core.finite(value))


def _sha(value):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def _output_channels(value):
    _list(value)
    for channel in value:
        _keys(channel, "key ordinal native_name label unit analyte")
        core._channel(dict(channel, measurement_origin="observed"), binding=True)
    core._unique([channel["key"] for channel in value], _CODE)
    _need([channel["ordinal"] for channel in value] == list(range(len(value))))
    _need(bool(value))


def _request(value):
    _keys(value, "key input output recipe_file recipe")
    core._key(value["key"], _CODE)
    _keys(value["input"], "kind index")
    core._enum(value["input"]["kind"], {"event_input", "preparation"}, _CODE)
    core._integer(value["input"]["index"], _CODE)
    output = value["output"]
    _keys(output, "key source_key sample_key channels comparison_basis")
    for name in ("key", "source_key", "sample_key"):
        core._key(output[name], _CODE)
    _output_channels(output["channels"])
    core._basis(output["comparison_basis"], _CODE, nullable=True)
    core._file(value["recipe_file"], _CODE)
    recipe = value["recipe"]
    _keys(recipe, "version method parameters")
    _need(recipe["version"] == "fluorescence_preparation_recipe_v1")
    core._enum(recipe["method"], METHODS, _CODE)
    params = recipe["parameters"]
    if recipe["method"] == SCALE_METHOD:
        _keys(params, "metadata_policy")
        _need(params["metadata_policy"] == POLICY)
    else:
        _keys(params, "matrix_file dataset_position keyword input_domain_basis axes")
        core._file(params["matrix_file"], _CODE)
        core._integer(params["dataset_position"], _CODE)
        core._enum(params["keyword"], {"spill", "spillover"}, _CODE)
        core._basis(params["input_domain_basis"], _CODE)
        _list(params["axes"])
        _need(bool(params["axes"]))
        for axis in params["axes"]:
            _keys(axis, "native_label input_channel_key input_ordinal")
            core._key(axis["native_label"], _CODE)
            core._key(axis["input_channel_key"], _CODE)
            core._integer(axis["input_ordinal"], _CODE)
        for name in ("native_label", "input_channel_key", "input_ordinal"):
            core._unique([axis[name] for axis in params["axes"]], _CODE)
    return value


def validate_preparation_request(value: dict, *, input_domains: list[dict]) -> dict:
    """Resolve index in the ordered list for the request's selected input kind.

    The producer supplies DomainIdentity records {key, source_key, sample_key}
    projected from original domains or earlier requested outputs. It validates
    that category/topology; this port never invents a future executed Domain.
    """
    _request(value)
    _list(input_domains)
    for domain in input_domains:
        _keys(domain, "key source_key sample_key")
        for name in domain:
            core._key(domain[name], _CODE)
    core._unique([domain["key"] for domain in input_domains], _CODE)
    index = value["input"]["index"]
    _need(index < len(input_domains))
    parent = input_domains[index]
    output = value["output"]
    _need(output["sample_key"] == parent["sample_key"])
    _need(output["key"] not in {domain["key"] for domain in input_domains})
    _need(output["source_key"] not in {domain["source_key"] for domain in input_domains})
    return deepcopy(value)


def _parent_request(request, parent):
    _request(request)
    core.validate_event_parse_result(parent)
    output = request["output"]
    _need(output["sample_key"] == parent["sample"]["key"])
    _need(output["key"] not in {parent["domain"]["key"], parent["sample"]["primary_domain_key"]})
    _need(output["source_key"] != parent["source"]["key"])
    _need(len(output["channels"]) == len(parent["channels"]))
    old_keys = {channel["key"] for channel in parent["channels"]}
    for old, new in zip(parent["channels"], output["channels"]):
        _need(new["key"] not in old_keys)
        for name in ("ordinal", "native_name", "label", "analyte"):
            _need(new[name] == old[name])
        prospective_time = (request["recipe"]["method"] == SCALE_METHOD
                            and old["native_name"] is not None
                            and old["native_name"].lower() == "time")
        if not prospective_time:
            _need(new["unit"] == old["unit"])


def scaling_units_compatible(parent, request, resolution):
    """Check selected units against actual resolved native Time preprocessing."""
    time = resolution["time"]
    for index, (old, new) in enumerate(zip(parent["channels"], request["output"]["channels"])):
        if not time["applied"] or old["key"] != time["channel_key"]:
            if new["unit"] != old["unit"]:
                return False
        else:
            if old["native_name"] is None or old["native_name"].lower() != "time":
                return False
            decades = resolution["channels"][index]["decades"]
            if decades == 0:
                if new["unit"] not in {None, "seconds"}:
                    return False
            elif new["unit"] is not None:
                return False
    return True


def _successful_scaling_metadata(resolution, parent):
    """Validate recorded native parameter meaning, without applying a transform."""
    time = resolution["time"]
    time_keys = [row["key"] for row in parent["channels"]
                 if row["native_name"] is not None and row["native_name"].lower() == "time"]
    _need(len(time_keys) <= 1)
    _need(time["channel_key"] == (time_keys[0] if time_keys else None))
    try:
        timestep = None if time["timestep_raw"] is None else float(time["timestep_raw"])
        _need(timestep is None or (core.finite(timestep) and timestep > 0))
        _need(time["timestep"] == timestep)
        _need(time["applied"] == (time["channel_key"] is not None and timestep is not None))
        for channel in resolution["channels"]:
            _need(channel["pne_raw"] is not None and channel["pnr_raw"] is not None)
            decades, log_zero = [float(token) for token in channel["pne_raw"].split(",")]
            native_range = float(channel["pnr_raw"])
            gain = None if channel["png_raw"] is None else float(channel["png_raw"])
            _need(all(core.finite(number) for number in (decades, log_zero, native_range)))
            _need(decades >= 0 and log_zero >= 0 and native_range > 0
                  and (decades == 0 or log_zero > 0))
            _need(gain is None or (core.finite(gain) and gain > 0))
            effective_gain = 1.0 if channel["input_channel_key"] == time["channel_key"] and gain is not None else gain
            _need((channel["decades"], channel["log_zero"], channel["range"], channel["gain"])
                  == (decades, log_zero, native_range, effective_gain))
            _need(channel["gain_applied"] == (effective_gain not in (None, 1.0)))
            _need(channel["log_linearization_applied"] == (decades > 0))
    except (ValueError, TypeError, OverflowError) as error:
        if isinstance(error, core.FluorescenceContractError):
            raise
        raise core.FluorescenceContractError(_CODE) from error


def preparation_problem(code, domain_key, *, channel_key=None, event_ordinal=None):
    value = dict(code=code, domain_key=domain_key, channel_key=channel_key,
                 event_ordinal=event_ordinal)
    _problem(value)
    return value


def _problem(value):
    _keys(value, "code domain_key channel_key event_ordinal")
    core._enum(value["code"], PROBLEM_CODES, _CODE)
    core._key(value["domain_key"], _CODE)
    core._key(value["channel_key"], _CODE, nullable=True)
    core._integer(value["event_ordinal"], _CODE, nullable=True)


def _problems(values):
    _list(values)
    for value in values:
        _problem(value)
    core._unique([core.canonical(value) for value in values], _CODE)


def validate_matrix_read_result(value: dict) -> dict:
    """Validate native matrix data and exact lexical tokens; no matrix solve."""
    _keys(value, "version file dataset_position keyword raw_token axis_tokens values state problems")
    _need(value["version"] == "fluorescence_spill_matrix_v1")
    core._file(value["file"], _CODE)
    core._integer(value["dataset_position"], _CODE)
    core._enum(value["keyword"], {"spill", "spillover"}, _CODE)
    core._text(value["raw_token"], _CODE)
    core._enum(value["state"], {"available", "unavailable", "incompatible"}, _CODE)
    _list(value["axis_tokens"])
    for token in value["axis_tokens"]:
        core._text(token, _CODE, nullable=False)
    _list(value["values"])
    for row in value["values"]:
        _list(row)
        for number in row:
            _number(number)
    _problems(value["problems"])
    if value["state"] == "available":
        _need(not value["problems"] and value["raw_token"] is not None)
        axes = value["axis_tokens"]
        _need(bool(axes) and all(axes))
        core._unique(axes, _CODE)
        size = len(axes)
        _need(len(value["values"]) == size and all(len(row) == size for row in value["values"]))
        tokens = value["raw_token"].split(",")
        try:
            count = int(tokens[0])
            parsed = [float(token) for token in tokens[1 + size:]]
        except (ValueError, OverflowError) as error:
            raise core.FluorescenceContractError(_CODE) from error
        _need(count == size and tokens[1:1 + size] == axes)
        _need(all(core.finite(number) for number in parsed))
        _need(parsed == [number for row in value["values"] for number in row])
    else:
        _need(bool(value["problems"]) and not value["values"])
    return deepcopy(value)


def _scaling(value):
    _keys(value, "source_file dataset_position metadata_policy channels time")
    core._file(value["source_file"], _CODE)
    core._integer(value["dataset_position"], _CODE)
    _need(value["metadata_policy"] == POLICY)
    _list(value["channels"])
    for channel in value["channels"]:
        _keys(channel, "input_channel_key native_parameter_number pne_raw png_raw pnr_raw decades log_zero range gain gain_applied log_linearization_applied")
        core._key(channel["input_channel_key"], _CODE)
        core._integer(channel["native_parameter_number"], _CODE, minimum=1)
        for name in ("pne_raw", "png_raw", "pnr_raw"):
            core._text(channel[name], _CODE)
        for name in ("decades", "log_zero", "range", "gain"):
            _number(channel[name], nullable=True)
        for name in ("gain_applied", "log_linearization_applied"):
            _need(type(channel[name]) is bool)
    core._unique([row["input_channel_key"] for row in value["channels"]], _CODE)
    _need([row["native_parameter_number"] for row in value["channels"]]
          == list(range(1, len(value["channels"]) + 1)))
    time = value["time"]
    _keys(time, "channel_key timestep_raw timestep applied")
    core._key(time["channel_key"], _CODE, nullable=True)
    core._text(time["timestep_raw"], _CODE)
    _number(time["timestep"], nullable=True)
    _need(type(time["applied"]) is bool)
    if time["channel_key"] is not None:
        _need(time["channel_key"] in {row["input_channel_key"] for row in value["channels"]})
    if time["applied"]:
        _need(time["channel_key"] is not None and time["timestep_raw"] is not None
              and time["timestep"] is not None and time["timestep"] > 0)


def validate_resolved_preparation(value: dict, *, request: dict) -> dict:
    _request(request)
    _keys(value, "version request_sha256 input_domain_key output_domain_key method backend channel_map scaling compensation transformation status problems diagnostics")
    _need(value["version"] == "fluorescence_resolved_preparation_v1")
    _sha(value["request_sha256"])
    _need(value["request_sha256"] == core.digest(request))
    core._key(value["input_domain_key"], _CODE)
    _need(value["output_domain_key"] == request["output"]["key"])
    method = request["recipe"]["method"]
    _need(value["method"] == method)
    _keys(value["backend"], "distribution version callable")
    _need(value["backend"] == BACKENDS[method])
    _list(value["channel_map"])
    _need(len(value["channel_map"]) == len(request["output"]["channels"]))
    for index, (mapping, output) in enumerate(zip(value["channel_map"], request["output"]["channels"])):
        _keys(mapping, "input_channel_key input_ordinal output_channel_key output_ordinal")
        core._key(mapping["input_channel_key"], _CODE)
        core._integer(mapping["input_ordinal"], _CODE)
        core._integer(mapping["output_ordinal"], _CODE)
        _need(mapping["input_ordinal"] == mapping["output_ordinal"] == index)
        _need(mapping["output_channel_key"] == output["key"])
    core._unique([row["input_channel_key"] for row in value["channel_map"]], _CODE)
    core._enum(value["status"], STATUSES, _CODE)
    _problems(value["problems"])
    for problem in value["problems"]:
        _need(problem["domain_key"] == value["output_domain_key"])
        _need(problem["channel_key"] is None or problem["channel_key"] in
              {row["output_channel_key"] for row in value["channel_map"]})
    if value["status"] == "complete":
        _need(not value["problems"])
    elif value["status"] in {"unavailable", "failed", "incompatible"}:
        _need(bool(value["problems"]))
    _list(value["diagnostics"])
    for diagnostic in value["diagnostics"]:
        _keys(diagnostic, "problem_code exception_class")
        _need(diagnostic["problem_code"] in {row["code"] for row in value["problems"]})
        _need(type(diagnostic["exception_class"]) is str and re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", diagnostic["exception_class"]) is not None)
    _need(value["transformation"] is None)
    if method == SCALE_METHOD:
        _need(value["compensation"] is None)
        if value["scaling"] is not None:
            _scaling(value["scaling"])
            _need([row["input_channel_key"] for row in value["scaling"]["channels"]]
                  == [row["input_channel_key"] for row in value["channel_map"]])
        if value["status"] in {"complete", "partial"}:
            _need(value["scaling"] is not None)
    else:
        _need(value["scaling"] is None)
        if value["compensation"] is not None:
            matrix = validate_matrix_read_result(value["compensation"])
            params = request["recipe"]["parameters"]
            _need(matrix["file"] == params["matrix_file"]
                  and matrix["dataset_position"] == params["dataset_position"]
                  and matrix["keyword"] == params["keyword"])
        if value["status"] in {"complete", "partial"}:
            _need(value["compensation"] is not None and value["compensation"]["state"] == "available")
    return deepcopy(value)


def validate_prepared_event_data(value: dict, *, request: dict, parent: dict) -> dict:
    _parent_request(request, parent)
    _keys(value, "version request_sha256 input_parse_sha256 sample_key parent_domain_key domain_key channels correspondence events")
    _need(value["version"] == "fluorescence_prepared_event_data_v1")
    _need(value["request_sha256"] == core.digest(request)
          and value["input_parse_sha256"] == core.digest(parent))
    _need(value["sample_key"] == parent["sample"]["key"]
          and value["parent_domain_key"] == parent["domain"]["key"]
          and value["domain_key"] == request["output"]["key"])
    channels = [dict(row, domain_key=value["domain_key"]) for row in request["output"]["channels"]]
    _list(value["channels"])
    for channel in value["channels"]:
        core._channel(channel)
    _need(value["channels"] == channels)
    expected_mapping = [dict(source_ordinal=index, event_ordinal=row["event_ordinal"])
                        for index, row in enumerate(parent["events"])]
    _list(value["correspondence"])
    for mapping in value["correspondence"]:
        _keys(mapping, "source_ordinal event_ordinal")
        core._integer(mapping["source_ordinal"], _CODE)
        core._integer(mapping["event_ordinal"], _CODE)
    _need(value["correspondence"] == expected_mapping)
    _list(value["events"])
    _need(len(value["events"]) == len(parent["events"]))
    method = request["recipe"]["method"]
    affected = ({axis["input_ordinal"] for axis in request["recipe"]["parameters"]["axes"]}
                if method == COMPENSATE_METHOD else set(range(len(channels))))
    for index, (old, event) in enumerate(zip(parent["events"], value["events"])):
        _keys(event, "sample_key domain_key event_ordinal source_ordinal location values")
        _need(event["sample_key"] == value["sample_key"] and event["domain_key"] == value["domain_key"])
        _need(event["source_ordinal"] == index and type(event["source_ordinal"]) is int)
        _need(event["event_ordinal"] == old["event_ordinal"] and type(event["event_ordinal"]) is int)
        core._location(event["location"], _CODE)
        _need(event["location"] == dict(record_ordinal=index, line_start=None, line_end=None,
                                        byte_start=None, byte_end=None))
        _list(event["values"])
        _need(len(event["values"]) == len(channels))
        for ordinal, (cell, previous, channel) in enumerate(zip(event["values"], old["values"], channels)):
            _keys(cell, "channel_key measurement")
            _need(cell["channel_key"] == channel["key"])
            measurement = cell["measurement"]
            core._measurement(measurement, _CODE)
            if ordinal not in affected:
                _need(measurement == previous["measurement"])
            elif measurement != previous["measurement"]:
                _need(measurement["state"] in {"derived", "invalid", "unavailable"}
                      and measurement["raw"] is None)
    return deepcopy(value)


def validate_preparation_outcome(value: dict, *, request: dict, parent: dict) -> dict:
    _parent_request(request, parent)
    _keys(value, "version status data parameters issues")
    _need(value["version"] == "fluorescence_preparation_outcome_v1")
    parameters = validate_resolved_preparation(value["parameters"], request=request)
    _need(value["status"] == parameters["status"])
    _need(parameters["input_domain_key"] == parent["domain"]["key"])
    _need([row["input_channel_key"] for row in parameters["channel_map"]]
          == [row["key"] for row in parent["channels"]])
    scaling = parameters["scaling"]
    if scaling is not None:
        _need(scaling["source_file"] == parent["source"]["file"]
              and scaling["dataset_position"] == parent["source"]["dataset_position"])
    represented = {event["event_ordinal"] for event in parent["events"]}
    for problem in parameters["problems"]:
        _need(problem["event_ordinal"] is None or problem["event_ordinal"] in represented)
    if value["data"] is not None:
        _need(value["status"] in {"complete", "partial"})
        validate_prepared_event_data(value["data"], request=request, parent=parent)
        _need(parent["domain"]["state"] == "available"
              and parent["source"]["extent"] != "unavailable")
        if request["recipe"]["method"] == COMPENSATE_METHOD:
            _need(all(parent["domain"][field]["state"] == "not_applied"
                      for field in ("compensation", "transformation")))
            params = request["recipe"]["parameters"]
            _need(params["input_domain_basis"] == parent["domain"]["comparison_basis"])
            _need(parameters["compensation"]["axis_tokens"] == [axis["native_label"] for axis in params["axes"]])
            affected = {axis["input_ordinal"] for axis in params["axes"]}
            for axis in params["axes"]:
                _need(axis["input_ordinal"] < len(parent["channels"]))
                channel = parent["channels"][axis["input_ordinal"]]
                _need(channel["key"] == axis["input_channel_key"] and channel["native_name"] == axis["native_label"])
        else:
            _need(parent["domain"]["scale_kind"] == "encoded"
                  and parent["domain"]["parent_domain_key"] is None
                  and parent["source"]["format_profile"] == "fcs_flowio_1_4_0_encoded"
                  and parent["domain"].get("scaling", {}).get("state") in {None, "not_applied"})
            _successful_scaling_metadata(scaling, parent)
            _need(scaling_units_compatible(parent, request, scaling))
            affected = set()
            for index, row in enumerate(scaling["channels"]):
                _need(row["pne_raw"] is not None and row["pnr_raw"] is not None)
                _need(row["decades"] is not None and row["decades"] >= 0
                      and row["log_zero"] is not None and row["log_zero"] >= 0
                      and row["range"] is not None and row["range"] > 0)
                _need(row["decades"] == 0 or row["log_zero"] > 0)
                _need(row["gain"] is None or row["gain"] > 0)
                _need(row["log_linearization_applied"] == (row["decades"] > 0))
                _need(row["gain_applied"] == (row["gain"] not in (None, 1.0)))
                if (row["gain_applied"] or row["log_linearization_applied"]
                        or (scaling["time"]["applied"] and row["input_channel_key"] == scaling["time"]["channel_key"])):
                    affected.add(index)
        for previous, event in zip(parent["events"], value["data"]["events"]):
            missing_axis = any(previous["values"][index]["measurement"]["value"] is None for index in affected)
            for index, (old, new) in enumerate(zip(previous["values"], event["values"])):
                if index not in affected:
                    _need(new["measurement"] == old["measurement"])
                else:
                    measurement = new["measurement"]
                    _need(measurement["state"] in {"derived", "unavailable", "invalid"}
                          and measurement["raw"] is None)
                    if (old["measurement"]["value"] is None
                            or (request["recipe"]["method"] == COMPENSATE_METHOD and missing_axis)):
                        _need(measurement["state"] == "unavailable")
                    if measurement["state"] != "derived":
                        _need(any(problem["channel_key"] == new["channel_key"]
                                  and problem["event_ordinal"] == event["event_ordinal"]
                                  for problem in parameters["problems"]))
        if value["status"] == "complete":
            _need(parent["source"]["extent"] == "complete")
    else:
        _need(value["status"] in {"unavailable", "failed", "incompatible"})
    indexes = dict(source_key={request["output"]["source_key"]},
                   sample_key={parent["sample"]["key"]}, domain_key={request["output"]["key"]},
                   channel_key={row["key"] for row in request["output"]["channels"]})
    core._issues(value["issues"], _CODE, indexes=indexes)
    for issue in value["issues"]:
        _need(issue["event_ordinal"] is None or issue["event_ordinal"] in represented)
    if value["status"] != "complete":
        _need(bool(value["issues"]))
    return deepcopy(value)


def _artifact_matches(identity, value):
    core._file(identity, _CODE)
    raw = core.canonical(value) + b"\n"
    _need(identity["size_bytes"] == len(raw) and identity["sha256"] == hashlib.sha256(raw).hexdigest())


def assemble_prepared_parse(outcome: dict, *, request: dict, parent: dict,
                            data_file: dict | None, parameters_file: dict) -> dict:
    """Assemble only after the caller has retained the two independent artifacts."""
    validate_preparation_outcome(outcome, request=request, parent=parent)
    _artifact_matches(parameters_file, outcome["parameters"])
    data = outcome["data"]
    if data is None:
        _need(data_file is None)
    else:
        _need(data_file is not None)
        _artifact_matches(data_file, data)
    domain = deepcopy(parent["domain"])
    output = request["output"]
    domain.update(key=output["key"], source_key=output["source_key"],
                  parent_domain_key=parent["domain"]["key"],
                  comparison_basis=deepcopy(output["comparison_basis"]),
                  correspondence=[] if data is None else deepcopy(data["correspondence"]),
                  state="available" if data is not None else
                        "failed" if outcome["status"] == "failed" else "unavailable")
    # Undocumented inherited scaling remains explicitly unknown in a new domain.
    domain.setdefault("scaling", dict(state="unknown", method=None, parameters_file=None))
    field = "scaling" if request["recipe"]["method"] == SCALE_METHOD else "compensation"
    domain[field] = dict(state="applied" if data is not None else "failed",
                         method=request["recipe"]["method"], parameters_file=deepcopy(parameters_file))
    if field == "scaling" and data is not None:
        domain["scale_kind"] = "scaled"
    source = dict(key=output["source_key"], file=deepcopy(data_file), dataset_position=0,
                  format_profile="fluorescence_prepared_event_data_v1",
                  extent=parent["source"]["extent"] if data is not None else "unavailable",
                  native_event_count=None, metadata=[])
    result = dict(schema=core.PARSE_SCHEMA, source=source, sample=deepcopy(parent["sample"]),
                  channels=[dict(row, domain_key=output["key"]) for row in deepcopy(output["channels"])],
                  domain=domain, events=[] if data is None else deepcopy(data["events"]),
                  issues=deepcopy(outcome["issues"]))
    return core.validate_event_parse_result(result)
