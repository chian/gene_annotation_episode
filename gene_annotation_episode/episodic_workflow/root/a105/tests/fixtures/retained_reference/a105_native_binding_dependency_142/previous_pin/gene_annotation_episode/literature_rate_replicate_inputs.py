"""Literal, explicitly mapped raw rate tables, separate from summary tables.

Sampling-unit and observation IDs are supplied experimental meanings, not
independence inferred from row position. The entire input is retained so a
detached record can be checked without reacquiring its source.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from decimal import Decimal
import io
import json
import re

from .literature_experimental_contracts import (
    ExperimentalContractError, ORIGINS, RATE_UNIT_ALIASES, REPRESENTATIONS,
    SAMPLING_BASES,
)
from .literature_rate_reader import _measurement


VERSION = "a105_rate_replicates_v1"
HEADERS = ("subject", "experiment", "arm", "condition", "endpoint",
           "normalization", "sampling_unit", "sampling_basis", "observation_id",
           "value", "unit", "origin")
GROUP_FIELDS = ("arm", "condition", "endpoint", "normalization")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def read_rate_replicate_table(table, *, expected_subject, expected_experiment):
    """Parse points, limits, blanks and literal ND without choosing a model.

    One observation ID identifies one physical measurement within this
    experiment, even if represented in multiple rows. A sampling-unit ID groups
    repeated readings of that unit; it does not certify biological replication.
    Unit IDs can be shared across arms, preserving possible pairing. Multiline
    CSV fields are explicitly unsupported, as in the existing summary reader.
    """
    if not isinstance(table, dict) or set(table) != {
            "source_ref", "artifact_ref", "text", "representation", "delimiter"}:
        _fail("closed_fields_required", "table")
    for name in ("source_ref", "artifact_ref", "text"):
        _text(table[name], "table." + name)
    _text(expected_subject, "expected_subject")
    _text(expected_experiment, "expected_experiment")
    if table["representation"] not in REPRESENTATIONS:
        _fail("unknown_source_representation", "table.representation")
    if table["delimiter"] not in (",", "\t"):
        _fail("explicit_csv_or_tsv_delimiter_required", "table.delimiter")
    lines = re.split(r"\r\n|\r|\n", table["text"])
    reader = csv.reader(io.StringIO(table["text"], newline=""),
                        delimiter=table["delimiter"], strict=True)
    try:
        headers = next(reader)
    except (StopIteration, csv.Error) as error:
        raise ExperimentalContractError("invalid_table_header", "table.text") from error
    if reader.line_num != 1:
        _fail("multiline_csv_record_unsupported", "table.header")
    if len(headers) != len(set(headers)) or set(headers) != set(HEADERS):
        _fail("exact_unique_headers_required", "table.header")
    rows = []
    while True:
        previous = reader.line_num
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error as error:
            raise ExperimentalContractError("invalid_csv_record", f"table.line[{previous + 1}]") from error
        line = reader.line_num
        path = f"table.line[{line}]"
        if line != previous + 1:
            _fail("multiline_csv_record_unsupported", path)
        if len(values) != len(headers):
            _fail("table_column_count_mismatch", path)
        fields = dict(zip(headers, values))
        if fields["subject"] != expected_subject:
            _fail("source_subject_mismatch", path + ".subject")
        if fields["experiment"] != expected_experiment:
            _fail("source_experiment_mismatch", path + ".experiment")
        for name in (*GROUP_FIELDS, "sampling_unit", "observation_id"):
            _text(fields[name], path + "." + name)
        basis = fields["sampling_basis"] or "unspecified"
        if basis not in SAMPLING_BASES:
            _fail("unknown_sampling_basis", path + ".sampling_basis")
        if fields["unit"] not in RATE_UNIT_ALIASES:
            _fail("unsupported_rate_unit", path + ".unit")
        if fields["origin"] not in ORIGINS:
            _fail("unknown_value_origin", path + ".origin")
        if table["representation"] == "synthetic_fixture" and fields["origin"] != "synthetic":
            _fail("synthetic_origin_required", path + ".origin")
        token = fields["value"]
        if token.strip().casefold() in ("nd", "not detected"):
            value, status, bound, approximate = None, "not_detected", "none", False
        else:
            value, status, bound, approximate = _measurement(token, path + ".value")
            # Do not silently turn a nonzero source decimal into floating zero.
            if value == 0 and Decimal(token.strip().lstrip("~<=> ")) != 0:
                _fail("numerical_model_range", path + ".value")
        rows.append({**{name: fields[name] for name in GROUP_FIELDS},
            "sampling_unit": fields["sampling_unit"], "sampling_basis": basis,
            "observation_id": fields["observation_id"], "value": value,
            "raw_value": token, "unit": RATE_UNIT_ALIASES[fields["unit"]],
            "status": status, "bound": bound, "approximate": approximate,
            "origin": fields["origin"],
            "source": {"source_ref": table["source_ref"], "artifact_ref": table["artifact_ref"],
                       "representation": table["representation"], "row_number": line,
                       "header": lines[0], "raw_row": lines[line - 1]}})
    return {"version": VERSION, "subject": expected_subject,
            "experiment": expected_experiment, "table": deepcopy(table), "rows": rows}


def validate_rate_replicate_extraction(extraction):
    """Check all detached operands against the retained literal table."""
    if not isinstance(extraction, dict) or set(extraction) != {
            "version", "subject", "experiment", "table", "rows"}:
        _fail("closed_fields_required", "extraction")
    if extraction["version"] != VERSION:
        _fail("unsupported_extraction_version", "version")
    expected = read_rate_replicate_table(extraction["table"],
        expected_subject=extraction["subject"], expected_experiment=extraction["experiment"])
    try:
        actual_json = json.dumps(extraction, sort_keys=True, allow_nan=False, ensure_ascii=False)
        expected_json = json.dumps(expected, sort_keys=True, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ExperimentalContractError("invalid_detached_json_record", "extraction") from error
    if actual_json != expected_json:
        _fail("detached_source_operand_mismatch", "extraction")
    return expected


__all__ = ["VERSION", "HEADERS", "GROUP_FIELDS", "read_rate_replicate_table",
           "validate_rate_replicate_extraction"]
