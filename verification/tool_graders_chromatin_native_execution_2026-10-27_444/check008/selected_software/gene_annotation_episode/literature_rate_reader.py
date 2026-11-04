"""Read already acquired, explicitly mapped A105 rate-summary tables.

This finite CSV/TSV route does not read arbitrary paper prose or figures. A
source acquisition or a separately retained extraction supplies the table and
its identity. Literal source rows remain available beside the parsed operands.
No evidence score, replication assumption or target correspondence is inferred.
"""
from __future__ import annotations

import csv
import io
import math
import re

from .literature_experimental_contracts import (
    ExperimentalContractError, HEADERS, RATE_UNIT_ALIASES, REPRESENTATIONS,
    VERSION, validate_rate_extraction,
)


_DECIMAL = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_VALUE = re.compile(r"\s*(?P<approx>~)?\s*(?P<bound><=|>=|<|>)?\s*(?P<number>" + _DECIMAL + r")\s*")
_PLAIN_NUMBER = re.compile(r"\s*(" + _DECIMAL + r")\s*")
_BOUNDS = {None: "none", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}


def _error(code, field):
    raise ExperimentalContractError(code, field)


def _required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        _error("nonempty_source_token_required", field)


def _number(token, field):
    """Parse a finite printed decimal, with neither limits nor uncertainty."""
    match = _PLAIN_NUMBER.fullmatch(token)
    if match is None:
        _error("invalid_numeric_token", field)
    value = float(match.group(1))
    if not math.isfinite(value):
        _error("finite_number_required", field)
    return value


def _measurement(token, field):
    if not token.strip():
        return None, "unavailable", "none", False
    match = _VALUE.fullmatch(token)
    if match is None:
        _error("invalid_numeric_token", field)
    value = _number(match.group("number"), field)
    bound = _BOUNDS[match.group("bound")]
    return value, "observed" if bound == "none" else "censored", bound, bool(match.group("approx"))


def read_rate_table(table, *, expected_subject, expected_experiment):
    """Extract literal rate operands from an explicitly supplied table.

    The complete table must concern the requested subject and experiment. This
    function does not silently filter a mixed table, map a similar name, average
    repeated arms, infer independence or turn a censored threshold into a point.
    Header/row source strings exclude line terminators; row numbers are physical
    one-based line numbers. Multiline CSV records are explicitly unsupported.
    """
    keys = {"source_ref", "artifact_ref", "text", "representation", "delimiter"}
    if not isinstance(table, dict) or set(table) != keys:
        _error("closed_fields_required", "table")
    for field in ("source_ref", "artifact_ref", "text"):
        _required_text(table[field], "table." + field)
    for name, value in (("expected_subject", expected_subject),
                        ("expected_experiment", expected_experiment)):
        _required_text(value, name)
    if table["representation"] not in REPRESENTATIONS:
        _error("unknown_source_representation", "table.representation")
    if table["delimiter"] not in (",", "\t"):
        _error("explicit_csv_or_tsv_delimiter_required", "table.delimiter")

    # Match csv.reader physical line accounting for LF, CRLF and CR sources.
    raw_lines = re.split(r"\r\n|\r|\n", table["text"])
    reader = csv.reader(io.StringIO(table["text"], newline=""),
                        delimiter=table["delimiter"], strict=True)
    try:
        headers = next(reader)
    except (StopIteration, csv.Error) as error:
        raise ExperimentalContractError("invalid_table_header", "table.text") from error
    if reader.line_num != 1:
        _error("multiline_csv_record_unsupported", "table.header")
    if len(headers) != len(set(headers)) or set(headers) != set(HEADERS):
        _error("exact_unique_headers_required", "table.header")
    header = raw_lines[0]
    rows = []
    while True:
        previous_line = reader.line_num
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error as error:
            raise ExperimentalContractError("invalid_csv_record", f"table.line[{previous_line + 1}]") from error
        row_number = reader.line_num
        path = f"table.line[{row_number}]"
        if row_number != previous_line + 1:
            _error("multiline_csv_record_unsupported", path)
        if len(values) != len(headers):
            _error("table_column_count_mismatch", path)
        fields = dict(zip(headers, values))
        if fields["subject"] != expected_subject:
            _error("source_subject_mismatch", path + ".subject")
        if fields["experiment"] != expected_experiment:
            _error("source_experiment_mismatch", path + ".experiment")
        value, status, bound, approximate = _measurement(fields["value"], path + ".value")
        magnitude = (_number(fields["uncertainty_magnitude"], path + ".uncertainty_magnitude")
                     if fields["uncertainty_magnitude"].strip() else None)
        kind = fields["uncertainty_kind"]
        # A blank source reports no uncertainty statistic. Retain an untyped
        # magnitude as unspecified, rather than guessing SD or SEM.
        if not kind:
            kind = "unreported" if magnitude is None else "unspecified"
        count_token = fields["count"].strip()
        if count_token:
            if re.fullmatch(r"[0-9]+", count_token) is None:
                _error("positive_integer_count_required", path + ".count")
            try:
                count = int(count_token)
            except ValueError as error:
                raise ExperimentalContractError("integer_token_unrepresentable", path + ".count") from error
        else:
            count = None
        try:
            unit = RATE_UNIT_ALIASES[fields["unit"]]
        except KeyError as error:
            raise ExperimentalContractError("unsupported_rate_unit", path + ".unit") from error
        rows.append({
            **{field: fields[field] for field in ("arm", "condition", "endpoint", "normalization")},
            "value": value, "unit": unit, "status": status, "bound": bound,
            "approximate": approximate,
            "uncertainty": {"kind": kind, "magnitude": magnitude, "count": count,
                            "sampling_basis": fields["sampling_basis"] or "unspecified"},
            "origin": fields["origin"],
            "source": {"source_ref": table["source_ref"], "artifact_ref": table["artifact_ref"],
                       "representation": table["representation"], "row_number": row_number,
                       "header": header, "raw_row": raw_lines[row_number - 1]},
        })
    return validate_rate_extraction({"version": VERSION, "subject": expected_subject,
                                     "experiment": expected_experiment, "rows": rows})


__all__ = ["read_rate_table"]
