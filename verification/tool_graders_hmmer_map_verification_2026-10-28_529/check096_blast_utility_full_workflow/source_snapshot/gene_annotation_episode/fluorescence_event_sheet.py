"""Build the one retained numerical sheet for supplied fluorescence events."""

from __future__ import annotations

from copy import deepcopy

from .fluorescence_event_contracts import (
    FluorescenceContractError,
    SHEET_SCHEMA,
    _validate_sheet,
    canonical,
    validate_event_parse_result,
)


def validate_fluorescence_sheet(sheet: dict) -> dict:
    """Validate closed shapes and declared joins, preserving the exact object."""
    return _validate_sheet(sheet)


def populate_fluorescence_sheet(parsed: list[dict], *, populations: list[dict],
                                gates: list[dict], control_pairs: list[dict],
                                native_reports: list[dict]) -> dict:
    """Join supplied operands without calculating gate or numerical results."""
    if type(parsed) is not list:
        raise FluorescenceContractError("invalid_parse_result")
    sheet = dict(schema=SHEET_SCHEMA, input_sources=[], samples=[], channels=[],
                 measurement_domains=[], events=[], population_definitions=populations,
                 gate_definitions=gates, control_pairs=control_pairs,
                 native_reports=native_reports, issues=[])
    shared = {"source": {}, "sample": {}}
    for batch in parsed:
        validate_event_parse_result(batch)
        for field, destination, code in (("source", "input_sources", "invalid_source"),
                                         ("sample", "samples", "invalid_sample")):
            item = batch[field]
            previous = shared[field].get(item["key"])
            if previous is None:
                shared[field][item["key"]] = item
                sheet[destination].append(item)
            elif canonical(previous) != canonical(item):
                raise FluorescenceContractError(code)
        sheet["channels"].extend(batch["channels"])
        sheet["measurement_domains"].append(batch["domain"])
        sheet["events"].extend(batch["events"])
        sheet["issues"].extend(batch["issues"])
    validate_fluorescence_sheet(sheet)
    return deepcopy(sheet)
