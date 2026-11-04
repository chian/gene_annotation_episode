"""Deterministic, supplied-byte MetaCATS readers for declared native layouts.

No reader acquires data, executes R/Perl, makes a statistical decision, or binds
native labels to biological groups. Original bytes remain the caller's retained
artifact; every read numerical token has its own original byte/line range.
"""
from __future__ import annotations

from bisect import bisect_right
from copy import deepcopy
import hashlib
import re
from typing import Literal

from .bvbrc_alignment_values import diagnostic, document_id, native_number
from .phylogeny_format_contracts import _artifact
from .bvbrc_metacats_format_contracts import (
    CHISQ_HEADERS, PAIR_HEADER, RAW_LAYOUT, RAW_WRAPPERS, _count_specs, _position,
    _raw_groups, validate_metacats_chisq_table, validate_metacats_pair_table,
    validate_metacats_raw_r_table, validate_metacats_metadata, validate_metacats_adjusted_matrix,
)


DIAGNOSTIC_CODES = frozenset({
    "artifact_digest_conflict", "encoding_invalid", "empty_input", "native_header_conflict",
    "ragged_native_row", "malformed_native_number", "native_number_incompatible",
    "native_numeric_underflow", "native_numeric_overflow", "native_number_missing",
    "native_group_cell_unparsed", "native_group_heading_unresolved", "native_position_invalid",
    "legacy_method_unresolved", "legacy_star_unresolved", "native_fewer_5_unresolved",
    "raw_wrapper_invalid", "raw_wrapper_truncated", "raw_wrapper_trailing_data",
    "raw_site_token_invalid", "raw_group_positions_conflict", "raw_pair_order_conflict",
    "matrix_token_unresolved", "matrix_row_invalid", "ragged_matrix", "ragged_metadata",
    "duplicate_native_symbol",
})


def _parameter(condition):
    if not condition:
        raise ValueError("bvbrc_metacats_reader_parameter_invalid")


def _diag(code, artifact, path="", severity="qualification"):
    assert code in DIAGNOSTIC_CODES
    return diagnostic("bvbrc_metacats_" + code, phase="native_decode", path=path,
                      severity=severity, evidence_refs=(artifact["raw_artifact_ref"],))


def _invalid(code, artifact):
    return {"status": "invalid", "value": None, "diagnostics": [_diag(code, artifact, severity="error")]}


class _Source:
    def __init__(self, data, artifact, encoding):
        self.text = data.decode(encoding)
        self.artifact, self.encoding = deepcopy(artifact), encoding
        self.offsets = [0]
        for character in self.text:
            self.offsets.append(self.offsets[-1] + len(character.encode(encoding)))
        self.line_starts = [0] + [m.end() for m in re.finditer(r"\r\n|\r|\n", self.text)]
        self.diagnostics = []
        self.completeness = "complete"

    def loc(self, start, end):
        return {"artifact": deepcopy(self.artifact), "byte_start_0based": self.offsets[start],
                "byte_end_0based_exclusive": self.offsets[end],
                "line_start_1based": bisect_right(self.line_starts, start),
                "line_end_1based_inclusive": bisect_right(self.line_starts, max(start, end - 1)),
                "xml_path": None}

    def issue(self, code, path="", *, structural=False, truncated=False):
        self.diagnostics.append(_diag(code, self.artifact, path, "error" if structural else "qualification"))
        if truncated:
            self.completeness = "truncated"
        elif structural and self.completeness != "truncated":
            self.completeness = "partial"

    def number(self, token, start, *, integer=False, minimum=None, maximum=None, path=""):
        value = native_number(token, source_location=self.loc(start, start + len(token)),
                              integer=integer, minimum=minimum, maximum=maximum)
        state = value["state"]
        if state == "failed":
            code = {"underflow": "native_numeric_underflow", "overflow": "native_numeric_overflow"}.get(
                value["token_kind"], "malformed_native_number")
            self.issue(code, path)
        elif state == "incompatible":
            self.issue("native_number_incompatible", path)
        elif state == "missing":
            self.issue("native_number_missing", path)
        return value

    def lines(self, start=0, end=None):
        end = len(self.text) if end is None else end
        for match in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", self.text[start:end]):
            if match.start() == end - start:
                break
            yield match.group().rstrip("\r\n"), start + match.start(), start + match.end()

    def document(self, document_kind, parameters, rows, *, identity="table_id", **fields):
        return {identity: document_id(document_kind, artifact=self.artifact, parameters=parameters),
                "artifact": deepcopy(self.artifact), "encoding": self.encoding,
                "completeness": self.completeness, **fields, **rows}

    def result(self, value, validator):
        return {"status": "partial" if self.diagnostics else "ok",
                "value": validator(value), "diagnostics": deepcopy(self.diagnostics)}


def _source(data, artifact, encoding):
    _parameter(type(data) is bytes and encoding in ("ascii", "utf-8"))
    _artifact(artifact)
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        return None, _invalid("artifact_digest_conflict", artifact)
    try:
        return _Source(data, artifact, encoding), None
    except UnicodeError:
        return None, _invalid("encoding_invalid", artifact)


def _fields(line, start):
    """Preserve leading/trailing empty TSV cells and their exact positions."""
    result, cursor = [], start
    for token in line.split("\t"):
        result.append((token, cursor))
        cursor += len(token) + 1
    return result


def _counts(source, token, start, path, *, raw_r=False):
    specs, valid = _count_specs(token, raw_r)
    if not valid:
        source.issue("native_group_cell_unparsed", path)
    if len({spec[0] for spec in specs}) != len(specs):
        source.issue("duplicate_native_symbol", path)
    return [{"symbol": symbol, "count": source.number(number, start + a, integer=True, minimum=0,
                                                       path=path + "/" + str(index) + "/count")}
            for index, (symbol, number, a, _) in enumerate(specs)]


def parse_metacats_chisq_table(data: bytes, *, artifact: dict,
        layout: Literal['current_filtered_tsv', 'legacy_example_tsv'], category_id: str,
        encoding: Literal['ascii', 'utf-8']) -> dict:
    """Read omnibus native observations; heading order never establishes identity."""
    _parameter(type(layout) is str and layout in CHISQ_HEADERS and type(category_id) is str and bool(category_id))
    source, failure = _source(data, artifact, encoding)
    if failure:
        return failure
    lines = list(source.lines())
    if not lines:
        return _invalid("empty_input", artifact)
    header = lines[0][0].split("\t")
    fixed = CHISQ_HEADERS[layout]
    if header[:len(fixed)] != fixed:
        return _invalid("native_header_conflict", artifact)
    groups = header[len(fixed):]
    if layout == "legacy_example_tsv":
        source.issue("legacy_method_unresolved", "/layout")
    if any(not h for h in groups) or not groups or len(set(groups)) != len(groups):
        source.issue("native_group_heading_unresolved", "/group_heading_tokens")
    rows = []
    for row_index, (line, start, end) in enumerate(lines[1:]):
        fields = _fields(line, start)
        path = "/rows/" + str(row_index)
        if len(fields) != len(header):
            source.issue("ragged_native_row", path, structural=True)
            continue
        position, qualification = _position(fields[0][0], layout)
        if qualification == "invalid":
            source.issue("native_position_invalid", path + "/position_token")
        elif qualification == "legacy_star":
            source.issue("legacy_star_unresolved", path + "/position_token")
        fewer = fields[4][0] if layout == "current_filtered_tsv" else None
        if fewer is not None and fewer not in ("Y", "N"):
            source.issue("native_fewer_5_unresolved", path + "/fewer_5_token")
        rows.append({"row_index": row_index, "source_location": source.loc(start, end),
            "position_token": fields[0][0], "position_1based": position, "position_qualification": qualification,
            "chi_square": source.number(*fields[1], minimum=0, path=path + "/chi_square"),
            "p_value": source.number(*fields[2], minimum=0, maximum=1, path=path + "/p_value"),
            "df": source.number(*fields[3], integer=True, minimum=0, path=path + "/df"),
            "fewer_5_token": fewer,
            "group_cells": [{"heading_index": i, "raw_token": token,
                "symbol_counts": _counts(source, token, position, path + "/group_cells/" + str(i))}
                for i, (token, position) in enumerate(fields[len(fixed):])]})
    value = source.document("metacats_chisq_table", {"layout": layout, "category_id": category_id, "encoding": encoding},
                            {"rows": rows}, layout=layout, category_id=category_id,
                            header_tokens=header, group_heading_tokens=groups)
    return source.result(value, validate_metacats_chisq_table)


def parse_metacats_pair_table(data: bytes, *, artifact: dict,
        layout: Literal['current_filtered_tsv'], category_id: str,
        encoding: Literal['ascii', 'utf-8']) -> dict:
    """Read native unadjusted pair p-values without splitting group labels."""
    _parameter(layout == "current_filtered_tsv" and type(category_id) is str and bool(category_id))
    source, failure = _source(data, artifact, encoding)
    if failure:
        return failure
    lines = list(source.lines())
    if not lines:
        return _invalid("empty_input", artifact)
    header = lines[0][0].split("\t")
    if header != PAIR_HEADER:
        return _invalid("native_header_conflict", artifact)
    rows = []
    for row_index, (line, start, end) in enumerate(lines[1:]):
        fields, path = _fields(line, start), "/rows/" + str(row_index)
        if len(fields) != 3:
            source.issue("ragged_native_row", path, structural=True)
            continue
        rows.append({"row_index": row_index, "source_location": source.loc(start, end),
                     "position": source.number(*fields[0], integer=True, minimum=1, path=path + "/position"),
                     "p_value": source.number(*fields[1], minimum=0, maximum=1, path=path + "/p_value"),
                     "raw_groups_token": fields[2][0]})
    value = source.document("metacats_pair_table", {"layout": layout, "category_id": category_id, "encoding": encoding},
                            {"rows": rows}, layout=layout, category_id=category_id, header_tokens=header)
    return source.result(value, validate_metacats_pair_table)


def _quoted_end(text, start):
    """Lex the write.table quoted field as inert data, including literal newlines.

    write.table's default qmethod escapes quotes with a backslash. No escape is
    evaluated and no expression is executed. Other backslashes stay literal.
    """
    if start >= len(text) or text[start] != '"':
        return None
    cursor = start + 1
    while cursor < len(text):
        if text[cursor] == "\\" and cursor + 1 < len(text) and text[cursor + 1] == '"':
            cursor += 2
        elif text[cursor] == '"':
            return cursor + 1
        else:
            cursor += 1
    return None


def _raw_wrapper(source, kind):
    text = source.text
    column, heading = RAW_WRAPPERS[kind]
    prefix = re.match(re.escape(column) + r"(?:\r\n|\r|\n)(\"1\")[ \t]+\"", text)
    if prefix is None:
        return None
    payload_start = prefix.end()
    close = _quoted_end(text, payload_start - 1)
    if close is None:
        payload_end = len(text)
        source.issue("raw_wrapper_truncated", structural=True, truncated=True)
    else:
        payload_end = close - 1
        if text[close:].strip():
            source.issue("raw_wrapper_trailing_data", structural=True)
    lines = list(source.lines(payload_start, payload_end))
    if not lines or lines[0][0] != heading:
        return None
    return column, prefix[1], heading, lines[1:]


def _raw_position(source, field, path):
    token, start = field
    match = re.fullmatch(r"\s*Site(.*?)\s*", token)
    if match is None:
        source.issue("raw_site_token_invalid", path)
        return source.number(token, start, integer=True, minimum=1, path=path)
    return source.number(match[1], start + match.start(1), integer=True, minimum=1, path=path)


def parse_metacats_raw_r_table(data: bytes, *, artifact: dict,
        kind: Literal['omnibus', 'pairwise'], layout: Literal['r_write_table_single_result_string'],
        category_id: str, encoding: Literal['ascii', 'utf-8']) -> dict:
    """Read a retained unfiltered single-result write.table wrapper as data."""
    _parameter(layout == RAW_LAYOUT and type(kind) is str and kind in RAW_WRAPPERS
               and type(category_id) is str and bool(category_id))
    source, failure = _source(data, artifact, encoding)
    if failure:
        return failure
    wrapped = _raw_wrapper(source, kind)
    if wrapped is None:
        return _invalid("raw_wrapper_invalid", artifact)
    column, wrapper_row, heading, lines = wrapped
    rows = []
    for row_index, (line, start, end) in enumerate(lines):
        fields, path = _fields(line, start), "/" + ("omnibus_rows" if kind == "omnibus" else "pair_rows") + "/" + str(row_index)
        if len(fields) != (6 if kind == "omnibus" else 4):
            source.issue("ragged_native_row", path, structural=True)
            continue
        row = {"row_index": row_index, "source_location": source.loc(start, end), "site_token": fields[0][0],
               "position": _raw_position(source, fields[0], path + "/position")}
        if kind == "omnibus":
            row.update(chi_square=source.number(*fields[1], minimum=0, path=path + "/chi_square"),
                p_value=source.number(*fields[2], minimum=0, maximum=1, path=path + "/p_value"),
                df=source.number(*fields[3], integer=True, minimum=0, path=path + "/df"),
                fewer_5_token=fields[4][0], residue_diversity_token=fields[5][0], positional_groups=[])
            if fields[4][0].strip() not in ("Y", "N"):
                source.issue("native_fewer_5_unresolved", path + "/fewer_5_token")
            specs, valid = _raw_groups(fields[5][0])
            if not valid:
                source.issue("native_group_cell_unparsed", path + "/residue_diversity_token")
            positions = [spec[0] for spec in specs]
            if positions != list(range(1, len(positions) + 1)):
                source.issue("raw_group_positions_conflict", path + "/positional_groups")
            for i, (position, token, counts, offset) in enumerate(specs):
                row["positional_groups"].append({"position_1based": position, "raw_token": token,
                    "symbol_counts": _counts(source, counts, fields[5][1] + offset,
                                             path + "/positional_groups/" + str(i), raw_r=True)})
        else:
            row.update(p_value=source.number(*fields[1], minimum=0, maximum=1, path=path + "/p_value"),
                column_a_1based=source.number(*fields[2], integer=True, minimum=1, path=path + "/column_a_1based"),
                column_b_1based=source.number(*fields[3], integer=True, minimum=1, path=path + "/column_b_1based"))
            a, b = row["column_a_1based"], row["column_b_1based"]
            if a["state"] == b["state"] == "available" and a["value"] >= b["value"]:
                source.issue("raw_pair_order_conflict", path)
        rows.append(row)
    parameters = {"layout": layout, "kind": kind, "category_id": category_id, "encoding": encoding}
    collections = {"omnibus_rows": rows if kind == "omnibus" else None,
                   "pair_rows": rows if kind == "pairwise" else None}
    value = source.document("metacats_raw_r_table", parameters, collections, layout=layout, kind=kind,
        category_id=category_id, wrapper_column_token=column, wrapper_row_token=wrapper_row,
        section_heading_token=heading)
    return source.result(value, validate_metacats_raw_r_table)


def parse_metacats_metadata(data: bytes, *, artifact: dict, delimiter: Literal['tab'],
        header: Literal['present', 'absent'], encoding: Literal['ascii', 'utf-8']) -> dict:
    """Preserve all ordered metadata cells, including empty/duplicate/extra rows."""
    _parameter(delimiter == "tab" and header in ("present", "absent"))
    source, failure = _source(data, artifact, encoding)
    if failure:
        return failure
    lines = list(source.lines())
    if header == "present" and not lines:
        return _invalid("empty_input", artifact)
    header_tokens = lines[0][0].split("\t") if header == "present" else None
    lines = lines[1:] if header == "present" else lines
    rows = [{"row_index": i, "source_location": source.loc(start, end), "cells": line.split("\t")}
            for i, (line, start, end) in enumerate(lines)]
    widths = [len(row["cells"]) for row in rows] + ([len(header_tokens)] if header_tokens is not None else [])
    if len(set(widths)) > 1:
        source.issue("ragged_metadata", "/rows", structural=True)
    value = source.document("metacats_metadata", {"delimiter": delimiter, "header": header, "encoding": encoding},
        {"rows": rows}, identity="document_id", delimiter=delimiter, header=header, header_tokens=header_tokens)
    return source.result(value, validate_metacats_metadata)


def parse_metacats_adjusted_matrix(data: bytes, *, artifact: dict, category_id: str,
        encoding: Literal['ascii', 'utf-8']) -> dict:
    """Read native tab-separated ID/group followed by space-separated symbols.

    Original group strings and all sequence tokens, including '#' and internal
    '-', remain distinct. This is not the FASTA format and does not use its
    alphabet restrictions. Unsupported multiple-character symbols are retained
    with a qualification; they are not silently split or translated.
    """
    _parameter(type(category_id) is str and bool(category_id))
    source, failure = _source(data, artifact, encoding)
    if failure:
        return failure
    rows = []
    for row_index, (line, start, end) in enumerate(source.lines()):
        fields = line.split("\t")
        path = "/rows/" + str(row_index)
        if len(fields) != 3:
            source.issue("matrix_row_invalid", path, structural=True)
            continue
        symbols = fields[2].split()
        if not fields[0].strip() or not fields[1].strip() or any(len(s) != 1 for s in symbols):
            source.issue("matrix_token_unresolved", path, structural=True)
        rows.append({"row_index": row_index, "source_location": source.loc(start, end),
                     "native_member_token": fields[0], "native_group_token": fields[1], "symbols": symbols})
    if len({len(row["symbols"]) for row in rows}) > 1:
        source.issue("ragged_matrix", "/rows", structural=True)
    if not rows and source.diagnostics:
        return {"status": "invalid", "value": None, "diagnostics": source.diagnostics}
    value = source.document("metacats_adjusted_matrix", {"category_id": category_id, "encoding": encoding},
                            {"rows": rows}, identity="document_id", category_id=category_id)
    return source.result(value, validate_metacats_adjusted_matrix)


__all__ = ["parse_metacats_chisq_table", "parse_metacats_pair_table", "parse_metacats_raw_r_table",
           "parse_metacats_metadata", "parse_metacats_adjusted_matrix"]
