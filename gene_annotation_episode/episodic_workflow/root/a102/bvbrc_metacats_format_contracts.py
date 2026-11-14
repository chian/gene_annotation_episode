"""Closed, detached validators for supplied MetaCATS native documents.

These checks validate stored syntax, numerical semantics, locations and internal
identities. They neither authenticate artifact custody nor infer group identity.
They perform no I/O and do not calculate significance or annotation credit.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re

from .bvbrc_alignment_values import document_id, native_number, validate_native_number
from .phylogeny_format_contracts import _artifact, _contained, _location


CHISQ_HEADERS = {
    "current_filtered_tsv": ["Position", "Chi-square_value", "P-value", "Degrees_of_freedom", "Fewer_5"],
    "legacy_example_tsv": ["Position", "Chi-square Value", "P-value", "Degree Freedom"],
}
PAIR_HEADER = ["Position", "Multiple_comparison_p-value", "Groups"]
RAW_LAYOUT = "r_write_table_single_result_string"
RAW_WRAPPERS = {"omnibus": ('"resultCST"', "Chi-square Analysis Result:"),
                "pairwise": ('"resultMC"', "MGC Multiple Comparison Result:")}
_COMMON = {"artifact", "encoding", "completeness"}
_COMPLETENESS = ("complete", "partial", "truncated", "unknown")


def _require(condition, code):
    if not condition:
        raise ValueError("bvbrc_metacats_" + code)


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "document_shape_invalid")


def _text(value, nonempty=False):
    return type(value) is str and (not nonempty or bool(value))


def _texts(value):
    return type(value) is list and all(_text(x) for x in value)


def _int(value, minimum=0):
    return type(value) is int and value >= minimum


def _base(value, keys, kind, parameters, identity="table_id"):
    _shape(value, _COMMON | set(keys) | {identity})
    _artifact(value["artifact"])
    _require(value["encoding"] in ("ascii", "utf-8"), "encoding_invalid")
    _require(value["completeness"] in _COMPLETENESS, "completeness_invalid")
    _require(value[identity] == document_id(kind, artifact=value["artifact"], parameters=parameters),
             "document_identity_conflict")


def _strings_encoding(value, encoding):
    if type(value) is str:
        try:
            value.encode(encoding)
        except UnicodeError:
            _require(False, "encoding_conflict")
    elif type(value) is list:
        for item in value:
            _strings_encoding(item, encoding)
    elif type(value) is dict:
        for key, item in value.items():
            if key not in ("artifact", "source_location", "table_id", "document_id", "category_id"):
                _strings_encoding(item, encoding)


def _rows(rows, artifact, keys):
    _require(type(rows) is list, "rows_invalid")
    previous_index, previous_end = -1, 0
    for row in rows:
        _shape(row, set(keys) | {"row_index", "source_location"})
        _require(_int(row["row_index"]) and row["row_index"] > previous_index, "row_index_invalid")
        previous_index = row["row_index"]
        _location(row["source_location"], artifact=artifact)
        loc = row["source_location"]
        _require(loc["xml_path"] is None and loc["byte_start_0based"] is not None
                 and loc["line_start_1based"] is not None, "source_location_invalid")
        _require(loc["byte_start_0based"] >= previous_end, "row_source_order_conflict")
        previous_end = loc["byte_end_0based_exclusive"]


def _number(value, row, *, integer=False, minimum=None, maximum=None):
    validate_native_number(value)
    _location(value["source_location"], artifact=row["source_location"]["artifact"])
    _contained(value["source_location"], row["source_location"])
    expected = native_number(value["raw_token"], source_location=value["source_location"],
                             integer=integer, minimum=minimum, maximum=maximum)
    _require(value == expected and type(value["value"]) is type(expected["value"]), "native_number_semantics_conflict")


def _column_offsets(row, tokens, encoding):
    _require(all(_text(t) and "\r" not in t and "\n" not in t and "\t" not in t for t in tokens),
             "native_cell_token_invalid")
    loc = row["source_location"]
    _require(loc["line_start_1based"] == loc["line_end_1based_inclusive"], "row_line_range_conflict")
    offsets, cursor = [], loc["byte_start_0based"]
    for token in tokens:
        offsets.append(cursor)
        cursor += len(token.encode(encoding)) + 1
    length = cursor - 1 - loc["byte_start_0based"]
    _require(loc["byte_end_0based_exclusive"] - loc["byte_start_0based"] - length in (0, 1, 2),
             "row_byte_range_conflict")
    return offsets


def _number_offset(number, start, row, encoding):
    loc = number["source_location"]
    _require(loc["byte_start_0based"] == start
             and loc["byte_end_0based_exclusive"] == start + len(number["raw_token"].encode(encoding))
             and loc["line_start_1based"] == loc["line_end_1based_inclusive"] == row["source_location"]["line_start_1based"]
             and loc["xml_path"] is None, "number_source_range_conflict")


def _position(token, layout):
    """Read a native coordinate token, preserving the legacy star separately."""
    pattern = r"([0-9]+)(\*)?" if layout == "legacy_example_tsv" else r"([0-9]+)"
    match = re.fullmatch(pattern, token.strip())
    if match is None:
        return None, "invalid"
    try:
        position = int(match[1])
    except ValueError:
        return None, "invalid"
    if position < 1:
        return None, "invalid"
    return position, "legacy_star" if layout == "legacy_example_tsv" and match[2] else "plain"


def _count_specs(raw_token, raw_r=False):
    """Return recognized (symbol, count token, start, end), plus syntax validity.

    Unrecognized text stays in its enclosing raw_token; it is never interpreted
    as an absent residue or a zero count. Duplicate symbols remain separate.
    """
    if not raw_token.strip():
        return [], True
    delimiter = ",_" if raw_r else ","
    specs, valid, cursor = [], True, 0
    for part in raw_token.split(delimiter):
        pattern = r"\s*([^\s_]+)_([^\s])\s*" if raw_r else r"\s*([^\s]+)[ \t]+([^\s])\s*"
        match = re.fullmatch(pattern, part)
        if match:
            specs.append((match[2], match[1], cursor + match.start(1), cursor + match.end(1)))
        else:
            valid = False
        cursor += len(part) + len(delimiter)
    return specs, valid


def _counts(counts, raw_token, row, *, raw_r=False, start=None, encoding="utf-8"):
    _require(type(counts) is list, "symbol_counts_invalid")
    specs, _ = _count_specs(raw_token, raw_r)
    _require(len(counts) == len(specs), "symbol_count_token_conflict")
    for item, (symbol, token, offset, _) in zip(counts, specs):
        _shape(item, {"symbol", "count"})
        _number(item["count"], row, integer=True, minimum=0)
        _require(item["symbol"] == symbol and item["count"]["raw_token"] == token,
                 "symbol_count_token_conflict")
        if start is not None:
            _number_offset(item["count"], start + len(raw_token[:offset].encode(encoding)), row, encoding)


def _validate_chisq(value):
    _shape(value, _COMMON | {"table_id", "layout", "category_id", "header_tokens", "group_heading_tokens", "rows"})
    layout = value["layout"]
    _require(_text(layout) and layout in CHISQ_HEADERS and _text(value["category_id"], True), "reader_parameter_invalid")
    _base(value, {"layout", "category_id", "header_tokens", "group_heading_tokens", "rows"},
          "metacats_chisq_table", {k: value[k] for k in ("layout", "category_id", "encoding")})
    header, fixed = value["header_tokens"], CHISQ_HEADERS[layout]
    _require(_texts(header) and header[:len(fixed)] == fixed, "native_header_conflict")
    _require(value["group_heading_tokens"] == header[len(fixed):], "group_heading_conflict")
    _rows(value["rows"], value["artifact"], {"position_token", "position_1based", "position_qualification",
          "chi_square", "p_value", "df", "fewer_5_token", "group_cells"})
    for row in value["rows"]:
        _require(_text(row["position_token"]), "position_token_invalid")
        expected = _position(row["position_token"], layout)
        _require((row["position_1based"], row["position_qualification"]) == expected
                 and (row["position_1based"] is None or _int(row["position_1based"], 1)), "position_token_conflict")
        _number(row["chi_square"], row, minimum=0)
        _number(row["p_value"], row, minimum=0, maximum=1)
        _number(row["df"], row, integer=True, minimum=0)
        _require(row["fewer_5_token"] is None if layout == "legacy_example_tsv" else _text(row["fewer_5_token"]),
                 "fewer_5_token_invalid")
        cells = row["group_cells"]
        _require(type(cells) is list and len(cells) == len(value["group_heading_tokens"]), "group_cells_invalid")
        for cell in cells:
            _shape(cell, {"heading_index", "raw_token", "symbol_counts"})
        tokens = [row["position_token"], row["chi_square"]["raw_token"], row["p_value"]["raw_token"], row["df"]["raw_token"]]
        if layout == "current_filtered_tsv":
            tokens.append(row["fewer_5_token"])
        tokens.extend(cell["raw_token"] for cell in cells)
        offsets = _column_offsets(row, tokens, value["encoding"])
        for key, index in (("chi_square", 1), ("p_value", 2), ("df", 3)):
            _number_offset(row[key], offsets[index], row, value["encoding"])
        for index, cell in enumerate(cells):
            _shape(cell, {"heading_index", "raw_token", "symbol_counts"})
            _require(type(cell["heading_index"]) is int and cell["heading_index"] == index
                     and _text(cell["raw_token"]), "group_cell_invalid")
            _counts(cell["symbol_counts"], cell["raw_token"], row,
                    start=offsets[len(fixed) + index], encoding=value["encoding"])


def validate_metacats_chisq_table(value: dict) -> dict:
    _validate_chisq(value)
    _strings_encoding(value, value["encoding"])
    return deepcopy(value)


def validate_metacats_pair_table(value: dict) -> dict:
    _shape(value, _COMMON | {"table_id", "layout", "category_id", "header_tokens", "rows"})
    _require(value["layout"] == "current_filtered_tsv" and _text(value["category_id"], True), "reader_parameter_invalid")
    _base(value, {"layout", "category_id", "header_tokens", "rows"}, "metacats_pair_table",
          {k: value[k] for k in ("layout", "category_id", "encoding")})
    _require(value["header_tokens"] == PAIR_HEADER, "native_header_conflict")
    _rows(value["rows"], value["artifact"], {"position", "p_value", "raw_groups_token"})
    for row in value["rows"]:
        _number(row["position"], row, integer=True, minimum=1)
        _number(row["p_value"], row, minimum=0, maximum=1)
        _require(_text(row["raw_groups_token"]), "group_token_invalid")
        offsets = _column_offsets(row, [row["position"]["raw_token"], row["p_value"]["raw_token"], row["raw_groups_token"]], value["encoding"])
        _number_offset(row["position"], offsets[0], row, value["encoding"])
        _number_offset(row["p_value"], offsets[1], row, value["encoding"])
    _strings_encoding(value, value["encoding"])
    return deepcopy(value)


def _raw_groups(token):
    if token.strip() == "NA":
        return [], True
    groups, valid, cursor = [], True, 0
    for part in token.split("|"):
        match = re.fullmatch(r"\s*group([0-9]+)\((.*)\)\s*", part)
        if match is None:
            valid = False
        else:
            try:
                position = int(match[1])
            except ValueError:
                position = 0
            if position < 1:
                valid = False
            else:
                groups.append((position, part, match[2], cursor + match.start(2)))
        cursor += len(part) + 1
    return groups, valid


def validate_metacats_raw_r_table(value: dict) -> dict:
    keys = {"table_id", "layout", "kind", "category_id", "wrapper_column_token", "wrapper_row_token",
            "section_heading_token", "omnibus_rows", "pair_rows"}
    _shape(value, _COMMON | keys)
    _require(value["layout"] == RAW_LAYOUT and _text(value["kind"]) and value["kind"] in RAW_WRAPPERS
             and _text(value["category_id"], True), "reader_parameter_invalid")
    _base(value, keys - {"table_id"}, "metacats_raw_r_table",
          {k: value[k] for k in ("layout", "kind", "category_id", "encoding")})
    column, heading = RAW_WRAPPERS[value["kind"]]
    _require(value["wrapper_column_token"] == column and value["wrapper_row_token"] == '"1"'
             and value["section_heading_token"] == heading, "raw_wrapper_conflict")
    omnibus = value["kind"] == "omnibus"
    active, inactive = ("omnibus_rows", "pair_rows") if omnibus else ("pair_rows", "omnibus_rows")
    _require(value[inactive] is None, "raw_row_kind_conflict")
    fields = ({"chi_square", "df", "fewer_5_token", "residue_diversity_token", "positional_groups"}
              if omnibus else {"column_a_1based", "column_b_1based"})
    _rows(value[active], value["artifact"], fields | {"site_token", "position", "p_value"})
    for row in value[active]:
        _require(_text(row["site_token"]), "site_token_invalid")
        _number(row["position"], row, integer=True, minimum=1)
        site = re.fullmatch(r"\s*Site(.*?)\s*", row["site_token"])
        expected = site[1] if site else row["site_token"]
        _require(row["position"]["raw_token"] == expected, "site_position_token_conflict")
        _number(row["p_value"], row, minimum=0, maximum=1)
        if omnibus:
            _number(row["chi_square"], row, minimum=0)
            _number(row["df"], row, integer=True, minimum=0)
            _require(_text(row["fewer_5_token"]) and _text(row["residue_diversity_token"]), "raw_token_invalid")
            tokens = [row["site_token"], row["chi_square"]["raw_token"], row["p_value"]["raw_token"],
                      row["df"]["raw_token"], row["fewer_5_token"], row["residue_diversity_token"]]
            offsets = _column_offsets(row, tokens, value["encoding"])
            for key, index in (("chi_square", 1), ("p_value", 2), ("df", 3)):
                _number_offset(row[key], offsets[index], row, value["encoding"])
            specs, _ = _raw_groups(row["residue_diversity_token"])
            _require(type(row["positional_groups"]) is list and len(row["positional_groups"]) == len(specs),
                     "raw_group_token_conflict")
            for group, (position, token, counts, offset) in zip(row["positional_groups"], specs):
                _shape(group, {"position_1based", "raw_token", "symbol_counts"})
                _require(type(group["position_1based"]) is int and group["position_1based"] == position
                         and group["raw_token"] == token, "raw_group_token_conflict")
                _counts(group["symbol_counts"], counts, row, raw_r=True,
                        start=offsets[5] + len(row["residue_diversity_token"][:offset].encode(value["encoding"])), encoding=value["encoding"])
        else:
            for name in ("column_a_1based", "column_b_1based"):
                _number(row[name], row, integer=True, minimum=1)
            offsets = _column_offsets(row, [row["site_token"], row["p_value"]["raw_token"],
                row["column_a_1based"]["raw_token"], row["column_b_1based"]["raw_token"]], value["encoding"])
            for key, index in (("p_value", 1), ("column_a_1based", 2), ("column_b_1based", 3)):
                _number_offset(row[key], offsets[index], row, value["encoding"])
        start = offsets[0] + (len(row["site_token"][:site.start(1)].encode(value["encoding"])) if site else 0)
        _number_offset(row["position"], start, row, value["encoding"])
    _strings_encoding(value, value["encoding"])
    return deepcopy(value)


def validate_metacats_metadata(value: dict) -> dict:
    keys = {"delimiter", "header", "header_tokens", "rows"}
    _shape(value, _COMMON | keys | {"document_id"})
    _require(value["delimiter"] == "tab" and value["header"] in ("present", "absent"), "reader_parameter_invalid")
    _base(value, keys, "metacats_metadata", {k: value[k] for k in ("delimiter", "header", "encoding")}, "document_id")
    _require(_texts(value["header_tokens"]) and bool(value["header_tokens"]) if value["header"] == "present"
             else value["header_tokens"] is None, "metadata_header_invalid")
    _rows(value["rows"], value["artifact"], {"cells"})
    for row in value["rows"]:
        _require(_texts(row["cells"]) and bool(row["cells"]), "metadata_cells_invalid")
        _column_offsets(row, row["cells"], value["encoding"])
    widths = [len(row["cells"]) for row in value["rows"]]
    if value["header_tokens"] is not None:
        widths.append(len(value["header_tokens"]))
    _require(value["completeness"] != "complete" or len(set(widths)) <= 1, "complete_ragged_metadata")
    _strings_encoding(value, value["encoding"])
    return deepcopy(value)


def validate_metacats_adjusted_matrix(value: dict) -> dict:
    _shape(value, _COMMON | {"document_id", "category_id", "rows"})
    _require(_text(value["category_id"], True), "reader_parameter_invalid")
    _base(value, {"category_id", "rows"}, "metacats_adjusted_matrix",
          {k: value[k] for k in ("category_id", "encoding")}, "document_id")
    _rows(value["rows"], value["artifact"], {"native_member_token", "native_group_token", "symbols"})
    for row in value["rows"]:
        _require(_text(row["native_member_token"]) and _text(row["native_group_token"])
                 and _texts(row["symbols"]), "matrix_row_invalid")
        if value["completeness"] == "complete":
            _require(bool(row["native_member_token"].strip()) and bool(row["native_group_token"].strip())
                     and all(len(s) == 1 and not s.isspace() for s in row["symbols"]), "matrix_token_invalid")
    widths = [len(row["symbols"]) for row in value["rows"]]
    _require(value["completeness"] != "complete" or len(set(widths)) <= 1, "complete_ragged_matrix")
    _strings_encoding(value, value["encoding"])
    return deepcopy(value)


__all__ = ["validate_metacats_chisq_table", "validate_metacats_pair_table",
           "validate_metacats_raw_r_table", "validate_metacats_metadata", "validate_metacats_adjusted_matrix"]


def _closed_validator(function):
    """All malformed saved-object shapes report a finite ValueError."""
    @wraps(function)
    def checked(value):
        try:
            return function(value)
        except (KeyError, TypeError, IndexError, OverflowError, UnicodeError) as error:
            raise ValueError("bvbrc_metacats_document_shape_invalid") from error
    return checked


for _name in __all__:
    globals()[_name] = _closed_validator(globals()[_name])
