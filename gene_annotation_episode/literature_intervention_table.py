"""Bind A106 table numbers to their printed row, column headers and unit.

The existing scalar reader owns numerical semantics and physical identity.
This adapter only replaces adjacency with the existing XML geometry checks;
it does not calculate predictions or establish their scientific applicability.
"""
from copy import deepcopy

from .domain import ContractError
from .literature_assay_inputs import _witness_schema
from .literature_measurement_validation_inputs import _associate, _table_cells, _visible_span


def table_number_schema(literal):
    schema = deepcopy(literal)
    schema["properties"].update(kind={"const": "source_table_number"},
        row_label=_witness_schema(), column_labels={"type": "array", "minItems": 1,
            "items": _witness_schema()})
    schema["required"] = list(schema["properties"])
    schema["description"] = (
        "Read a printed number from an HTML/JATS table using its exact row label, column "
        "headers and unit witness. Include grouped quantity and model headers when needed "
        "to identify one column. number_start and number_end are zero-based character offsets "
        "within number.witness.quote; witness start/end are absolute UTF-8 byte offsets in the source. "
        "Values are read from retained bytes. Reading a published "
        "model prediction does not establish its independence or biological applicability.")
    return schema


def associate_table_unit(selection, number, unit, sources):
    selector = number["selector"]
    anchor = selector["witness"]
    start = anchor["start"] + len(anchor["quote"][:selector["number_start"]].encode())
    end = anchor["start"] + len(anchor["quote"][:selector["number_end"]].encode())
    numeric = {**anchor, "start": start, "end": end}
    _visible_span(sources, anchor, start, end, "number")
    table, cells = _table_cells(sources, numeric)

    def cell_for(witness):
        return next((cell for cell in cells
            if cell["start"] <= witness["start"] < witness["end"] <= cell["end"]), None)

    selected = cell_for(numeric)
    if table is None or selected is None or selected["header"]:
        raise ContractError("intervention_table_data_cell_required")
    row = sources.witness(selection["row_label"], "row_label")
    columns = [sources.witness(witness, "column_labels") for witness in selection["column_labels"]]
    for witness in (row, *columns, unit):
        if any(witness[key] != anchor[key] for key in ("artifact_ref", "representation")):
            raise ContractError("intervention_table_witness_from_different_source")
        _visible_span(sources, witness, witness["start"], witness["end"], "table_label")
    row_cell = cell_for(row)
    if (row_cell is None or row_cell["row"] != selected["row"]
            or max(row_cell["columns"]) >= min(selected["columns"])):
        raise ContractError("intervention_table_row_mismatch")

    bound = {**number, "number_start_bytes": start, "number_end_bytes": end}
    possible_columns = None
    for witness in (*columns, unit):
        _associate(bound, witness, sources, "table_column")
        cell = cell_for(witness)
        if witness is not unit and (not cell["header"] or cell["row"] >= selected["row"]):
            raise ContractError("intervention_table_column_header_required")
        possible_columns = (set(cell["columns"]) if possible_columns is None
            else possible_columns.intersection(cell["columns"]))
    if len(possible_columns) != 1 or possible_columns != set(selected["columns"]):
        raise ContractError("intervention_table_column_ambiguous")
