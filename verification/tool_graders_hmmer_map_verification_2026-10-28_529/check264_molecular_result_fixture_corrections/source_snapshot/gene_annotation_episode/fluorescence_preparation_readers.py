"""Read one explicitly selected FCS spill keyword through the strict decoder.

This pure boundary acquires no data, infers no channel sets and calculates no
population statistics. The selected keyword is never replaced by its alias.
"""

from __future__ import annotations

from copy import deepcopy
import importlib

from . import fluorescence_event_contracts as core
from .fluorescence_fcs_reader import decode_selected_fcs
from .fluorescence_preparation_contracts import (
    preparation_problem, validate_matrix_read_result,
)


def _load_flowutils():
    try:
        module = importlib.import_module("flowutils")
        if getattr(module, "__version__", None) != "1.2.2":
            return None
        compensate = importlib.import_module("flowutils.compensate")
    except (ImportError, OSError, ValueError):
        return None
    if not callable(getattr(compensate, "get_spill", None)) or not callable(
            getattr(compensate, "compensate", None)):
        return None
    return compensate


def _metadata_tokens(native, names):
    """Return observed source values; reject duplicates or decoder alteration."""
    pairs = getattr(native, "preparation_text_pairs", None)
    if pairs is None:
        return {}, set(names)
    selected = {name: [] for name in names}
    invalid_keys = set()
    for key, value in pairs:
        normalized = key.lower().replace("$", "")
        if normalized in selected:
            selected[normalized].append(value)
            if key.lower() not in {normalized, "$" + normalized}:
                invalid_keys.add(normalized)
    tokens, invalid = {}, invalid_keys
    decoded = getattr(native, "text", {})
    for name, values in selected.items():
        if len(values) == 1:
            tokens[name] = values[0]
            if decoded.get(name) != values[0]:
                invalid.add(name)
        elif values:
            invalid.add(name)
    return tokens, invalid


def _native_problem(code):
    return {
        "decoder_unavailable": ("unavailable", "backend_unavailable"),
        "source_unavailable": ("unavailable", "parameter_unavailable"),
        "retained_artifact_mismatch": ("incompatible", "parameter_identity_mismatch"),
        "truncated_source": ("unavailable", "incomplete_native_array"),
    }.get(code, ("incompatible", "parameter_invalid"))


def read_fcs_spill_matrix(raw: bytes, *, source: dict, locator: dict,
                          channels: list[dict]) -> dict:
    """Read exact native tokens and coefficients, retaining failure distinctly.

    Locator is exactly {dataset_position, keyword}. Channels are the actual
    parent's ordered Channel rows, including their common domain_key. This does
    not require a separate support FCS artifact to share that channel order.
    """
    code = "invalid_parameters"
    core._source(source)
    core._keys(locator, "dataset_position keyword", code)
    core._integer(locator["dataset_position"], code)
    core._enum(locator["keyword"], {"spill", "spillover"}, code)
    core._need(locator["dataset_position"] == source["dataset_position"], code)
    core._need(source["file"] is not None and type(raw) is bytes, code)
    core._list(channels, code)
    core._need(bool(channels), code)
    for channel in channels:
        core._channel(channel)
    core._unique([row["key"] for row in channels], code)
    core._need([row["ordinal"] for row in channels] == list(range(len(channels))), code)
    core._need(len({row["domain_key"] for row in channels}) == 1, code)
    domain_key = channels[0]["domain_key"]
    result = dict(version="fluorescence_spill_matrix_v1", file=deepcopy(source["file"]),
                  dataset_position=locator["dataset_position"], keyword=locator["keyword"],
                  raw_token=None, axis_tokens=[], values=[], state="unavailable", problems=[])

    def failed(state, problem):
        result["state"] = state
        result["values"] = []
        result["problems"] = [preparation_problem(problem, domain_key)]
        return validate_matrix_read_result(result)

    decoded = decode_selected_fcs(raw, source=source, only_text=True)
    native = decoded["native"]
    tokens, invalid = _metadata_tokens(native, [locator["keyword"]])
    result["raw_token"] = tokens.get(locator["keyword"])
    if result["raw_token"] is not None:
        observed = result["raw_token"].split(",")
        try:
            count = int(observed[0])
        except (ValueError, OverflowError):
            count = 0
        if 0 < count <= len(observed) - 1:
            result["axis_tokens"] = observed[1:1 + count]
    if decoded["error"] is not None:
        # A failing native constructor can already have exposed real TEXT.
        # Keep that selected token; another metadata error is not matrix absence.
        return failed(*_native_problem(decoded["error"]))
    if invalid:
        return failed("incompatible", "parameter_invalid")
    if result["raw_token"] is None:
        return failed("unavailable", "parameter_unavailable")
    tokens = result["raw_token"].split(",")
    try:
        size = int(tokens[0])
    except (ValueError, OverflowError):
        return failed("incompatible", "parameter_invalid")
    if size <= 0 or size > len(tokens) - 1:
        return failed("incompatible", "parameter_invalid")
    axes = tokens[1:1 + size]
    result["axis_tokens"] = axes
    if (len(tokens) != 1 + size + size * size or not all(axes)
            or len(set(axes)) != size):
        return failed("incompatible", "parameter_invalid")
    try:
        lexical_values = [float(token) for token in tokens[1 + size:]]
    except (ValueError, OverflowError):
        return failed("incompatible", "parameter_invalid")
    if not all(core.finite(value) for value in lexical_values):
        return failed("incompatible", "parameter_invalid")
    # The library strips whitespace/newlines from labels. That may not create
    # an identity the source did not contain: exact tokens are required here.
    if any(axis != axis.strip().replace("\n", "") for axis in axes):
        return failed("incompatible", "channel_mapping_incompatible")
    names = [row["native_name"] for row in channels]
    if any(names.count(axis) != 1 for axis in axes):
        return failed("incompatible", "channel_mapping_incompatible")
    backend = _load_flowutils()
    if backend is None:
        return failed("unavailable", "backend_unavailable")
    try:
        matrix, native_axes = backend.get_spill(result["raw_token"])
        values = matrix.tolist()
    except (ValueError, TypeError, IndexError, OverflowError):
        return failed("incompatible", "parameter_invalid")
    if native_axes != axes or matrix.shape != (size, size):
        return failed("incompatible", "channel_mapping_incompatible")
    if any(not core.finite(value) for row in values for value in row):
        return failed("incompatible", "parameter_invalid")
    result.update(state="available", values=values)
    return validate_matrix_read_result(result)
