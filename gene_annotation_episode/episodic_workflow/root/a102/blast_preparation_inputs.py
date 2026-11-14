"""Pure, located readers for supplied BLAST preparation text.

These documents retain native observations, not preparation success, inferred
membership, effective defaults, or scientific scores. The caller retains the
exact bytes and joins literal references to selected inputs and captured files.
No reader opens paths, invokes a program, or resolves a database.
"""
from __future__ import annotations

import math
import re

from .blast_database_extraction import _check, _check_bytes, _failure
from .blast_database_inspection import _field
from .blast_preparation_contracts import validate_blast_preparation_document
from .blast_utility_contracts import validate_blast_utility_record
from .domain import ContractError


_GRAMMARS = frozenset({"blast_database_lines", "profile_whitespace_tokens"})
_LIST_KEYS = frozenset({"DBLIST", "VDBLIST", "GILIST", "SEQIDLIST", "TAXIDLIST"})
_INTEGER = re.compile(r"[0-9]+\Z")
_SIGNED_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_NATIVE_ERROR = re.compile(r"(?:Error:|ERROR:|BLAST Database error:|NCBI C\+\+ Exception:)")


def _integer(value, *, signed=False):
    if value is None or not (_SIGNED_INTEGER if signed else _INTEGER).fullmatch(value):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _number(value):
    if value is None or not _NUMBER.fullmatch(value):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _problem(document, code, line=None, *, stage="parse"):
    row = _failure(stage, code, document["occurrence_id"], line_number=line)
    if row not in document["failures"]:
        document["failures"].append(row)


def _context(contents, occurrence, kind):
    occurrence = validate_blast_utility_record("ArtifactOccurrence", occurrence)
    check = _check_bytes(contents, occurrence)
    document = {"version": "blast_preparation_document_v1", "kind": kind,
                "occurrence_id": occurrence["occurrence_id"], "native_fields": [],
                "rows": [], "checks": [check], "failures": []}
    if kind == "profile_aux":
        document["parameter_observations"] = []
    if occurrence["completeness"] != "complete":
        _problem(document, "output_completeness_unestablished", stage="capture")
    # Split only native line delimiters. Unicode separators are literal UTF-8
    # text, not Python's additional str.splitlines delimiters.
    lines, start = [], 0
    for number, match in enumerate(re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", contents), 1):
        raw = match.group()
        if not raw:
            continue
        body = raw.rstrip(b"\r\n")
        try:
            text = body.decode("utf-8")
            if any(ord(c) < 32 and c != "\t" for c in text) or "\x7f" in text:
                raise ValueError("unsupported_native_control")
        except (UnicodeDecodeError, ValueError):
            text = None
            _problem(document, "native_row_invalid", number)
        lines.append((number, start, text))
        start += len(raw)
    return document, lines


def _finish(document):
    parsed = [row for row in document["failures"] if row["stage"] == "parse"]
    invalid = [row for row in parsed if row["code"] != "native_diagnostic_unrecognized"]
    status = "fail" if invalid else "unknown" if parsed else "pass"
    oid = document["occurrence_id"]
    document["checks"].append(_check("syntax", status, [oid], "native_format_parser", [oid],
        invalid[0]["code"] if invalid else parsed[0]["code"] if parsed else None))
    return validate_blast_preparation_document(document)


def _add_field(document, name, value, unit, line, lexeme):
    document["native_fields"].append(_field(name, value, unit, document["occurrence_id"],
        lexeme=lexeme, line=line, basis="native_reported",
        missing="native_field_invalid" if value is None else None))
    if value is None:
        _problem(document, "native_document_invalid", line)


def _duplicate_fields(document):
    groups = {}
    for field in document["native_fields"]:
        previous = groups.setdefault(field["field_name"], [])
        if previous:
            conflict = any((old["value"], old["unit"]) != (field["value"], field["unit"])
                           for old in previous)
            _problem(document, "database_metadata_conflict" if conflict else
                     "duplicate_native_identity", field["line_number"], stage="validation")
        previous.append(field)


def _parameter(document, parameter, value, line, lexeme, *, effect="effective", missing=None):
    return {"parameter": parameter, "scope_key": document["occurrence_id"],
            "value": value, "effect": effect, "occurrence_id": document["occurrence_id"],
            "line_number": line, "native_lexeme": lexeme, "missing_reason": missing}


def parse_blast_preparation_list(contents: bytes, *, grammar: str, occurrence: dict) -> dict:
    """Locate literal entries without quoting, normalizing, or deduplicating them.

    Database lists contain one trimmed name per nonempty line; profile lists
    split on native ASCII spaces/tabs and line endings. Comments are not a
    feature of either native grammar: a '#' token remains a literal entry.
    """
    if type(grammar) is not str or grammar not in _GRAMMARS:
        raise ContractError("blast_utility_preparation_list_grammar")
    document, lines = _context(contents, occurrence, "list")
    for number, start, line in lines:
        if line is None:
            continue
        if grammar == "blast_database_lines":
            value = line.strip(" \t")
            spans = [(len(line) - len(line.lstrip(" \t")), value)] if value else []
        else:
            spans = [(match.start(), match.group()) for match in re.finditer(r"[^ \t]+", line)]
        for token_ordinal, (position, value) in enumerate(spans):
            begin = start + len(line[:position].encode("utf-8"))
            document["rows"].append({"ordinal": len(document["rows"]),
                "line_number": number, "token_ordinal": token_ordinal,
                "original_token": value, "start_byte": begin,
                "end_byte": begin + len(value.encode("utf-8"))})
    if not document["rows"]:
        _problem(document, "native_document_invalid")
    return _finish(document)


def _alias_tokens(value):
    """Double quotes delimit native alias names; no shell escape expansion."""
    tokens, position = [], 0
    while position < len(value):
        while position < len(value) and value[position] in " \t":
            position += 1
        if position == len(value):
            break
        start = position
        if value[position] == '"':
            end = value.find('"', position + 1)
            if end < 0:
                return None
            token, position = value[position + 1:end], end + 1
            if position < len(value) and value[position] not in " \t":
                return None
        else:
            while position < len(value) and value[position] not in " \t":
                if value[position] == '"':
                    return None
                position += 1
            token = value[start:position]
        if not token:
            return None
        tokens.append({"ordinal": len(tokens), "value": token,
                       "native_lexeme": value[start:position]})
    return tokens


def parse_blast_alias_document(contents: bytes, *, occurrence: dict) -> dict:
    """Retain ordered native alias fields, including unknown keys and duplicates."""
    document, lines = _context(contents, occurrence, "alias")
    seen = set()
    for number, _, line in lines:
        if line is None or not line.strip(" \t") or line.lstrip(" \t").startswith("#"):
            continue
        match = re.fullmatch(r"[ \t]*([^ \t]+)(?:[ \t]+(.*))?", line)
        key, value = match[1], match[2] if match[2] is not None else ""
        tokens = _alias_tokens(value) if key in _LIST_KEYS else []
        if tokens is None or key in _LIST_KEYS and not tokens:
            _problem(document, "native_row_invalid", number)
            tokens = []
        document["rows"].append({"row_ordinal": len(document["rows"]),
            "line_number": number, "native_key": key, "value_lexeme": value, "tokens": tokens})
        if key in seen and key in _LIST_KEYS:
            _problem(document, "duplicate_native_identity", number, stage="validation")
        seen.add(key)
        if key == "TITLE":
            _add_field(document, "database_title", value, "text", number, value)
        elif key in {"NSEQ", "LENGTH"}:
            _add_field(document, "database_sequence_count" if key == "NSEQ" else
                "database_residue_count", _integer(value.strip(" \t")),
                "sequences" if key == "NSEQ" else "symbols", number, value)
    if not document["rows"]:
        _problem(document, "native_document_invalid")
    _duplicate_fields(document)
    return _finish(document)


def parse_blast_seqid_list_info(contents: bytes, *, occurrence: dict) -> dict:
    """Read stored-list metadata without inferring a submitted ID population."""
    document, lines = _context(contents, occurrence, "seqid_info")
    specs = {
        "Num of Ids: ": ("identifier_list_count", "identifiers", _integer),
        "Title: ": ("identifier_list_title", "text", str),
        "Create Date: ": ("identifier_list_created_at_native", "text", str),
        "\tTotal Vol Length: ": ("identifier_list_database_length", "symbols", _integer),
        "\tDB Create Date: ": ("identifier_list_database_created_at_native", "text", str),
    }
    index = 0
    while index < len(lines):
        number, _, line = lines[index]
        index += 1
        if line is None or not line.strip(" \t") or line == "DB Info: ":
            continue
        if line in {"\tDB Vols: ", "\tDB Vols:"}:
            names, lexemes = [], [line]
            while index < len(lines) and lines[index][2] is not None and lines[index][2].startswith("\t\t"):
                vol_number, _, volume = lines[index]
                index += 1
                lexemes.append(volume)
                if volume[2:]:
                    names.append(volume[2:])
                else:
                    _problem(document, "native_row_invalid", vol_number)
            _add_field(document, "identifier_list_database_volumes", names if names else None,
                       "paths", number, "\n".join(lexemes))
            continue
        for prefix, (name, unit, convert) in specs.items():
            if line.startswith(prefix):
                lexeme = line[len(prefix):]
                value = convert(lexeme)
                if name.endswith("created_at_native") and not value:
                    value = None
                _add_field(document, name, value, unit, number, lexeme)
                break
        else:
            _problem(document, "native_format_unsupported" if line ==
                "Seqidlist file is not in blast db version 5 format" else
                "native_diagnostic_unrecognized", number)
    required = {"identifier_list_count", "identifier_list_title", "identifier_list_created_at_native"}
    if not required <= {row["field_name"] for row in document["native_fields"]}:
        _problem(document, "native_document_invalid")
    _duplicate_fields(document)
    return _finish(document)


def parse_blast_aliastool_diagnostics(contents: bytes, *, occurrence: dict) -> dict:
    """Read explicit converted/created counts; never decode binary membership."""
    document, lines = _context(contents, occurrence, "aliastool_diagnostics")
    for number, _, line in lines:
        if line is None or not line.strip(" \t"):
            continue
        category, count = "unknown", None
        converted = re.fullmatch(r"Converted ([0-9]+) GIs (?:into binary GI file|from .+ to binary format in .+)", line)
        created = re.fullmatch(r"Created (?:nucleotide|protein) BLAST \(alias\) database .+ with ([0-9]+) sequences", line)
        if converted or created:
            count = _integer((converted or created)[1])
            if count is not None:
                category = "converted_gi_count" if converted else "created_alias_sequence_count"
                _add_field(document, "identifier_list_converted_count" if converted else
                    "database_sequence_count", count, "identifier_occurrences" if converted else
                    "sequences", number, (converted or created)[1])
            else:
                _problem(document, "native_row_invalid", number)
        elif _NATIVE_ERROR.match(line):
            category = "native_error"
            _problem(document, "preparation_not_successful", number, stage="native")
        else:
            _problem(document, "native_diagnostic_unrecognized", number)
        document["rows"].append({"line_number": number, "category": category,
                                 "native_lexeme": line, "native_count": count})
    _duplicate_fields(document)
    return _finish(document)


def parse_makembindex_diagnostics(contents: bytes, *, occurrence: dict) -> dict:
    """Read native parameter warnings and literal created/removed member names."""
    document, lines = _context(contents, occurrence, "index_diagnostics")
    ignored = {"Warning: -stride has no effect upon legacy index creation": "stride",
        "Warning: -ws_hint has no effect upon legacy index creation": "ws_hint",
        "Warning: option 'output' is ignored for new style indices": "output_prefix"}
    for number, _, line in lines:
        if line is None or not line.strip(" \t"):
            continue
        category, observation, reference = "unknown", None, None
        adjusted = re.fullmatch(r"Warning: -ws_hint requested is too low\. Setting to the minimum value of ([0-9]+)", line)
        member = re.fullmatch(r"creating (.+)\.\.\.(done|removed \(empty\))", line)
        if line in ignored:
            category = "parameter_ignored"
            observation = _parameter(document, ignored[line], None, number, line, effect="ignored")
        elif adjusted and _integer(adjusted[1]) is not None and _integer(adjusted[1]) > 0:
            category = "parameter_adjusted"
            observation = _parameter(document, "ws_hint", _integer(adjusted[1]), number, line)
        elif member:
            category = "member_created" if member[2] == "done" else "empty_member_removed"
            reference = member[1]
        elif _NATIVE_ERROR.match(line):
            category = "native_error"
            _problem(document, "preparation_not_successful", number, stage="native")
        else:
            _problem(document, "native_diagnostic_unrecognized", number)
        document["rows"].append({"line_number": number, "category": category,
            "native_lexeme": line, "parameter_observation": observation,
            "native_output_reference": reference})
    return _finish(document)


def parse_makeprofiledb_aux(contents: bytes, *, occurrence: dict) -> dict:
    """Read the eight-line header and native length/K pairs in original order.

    Header lines 4–7 are writer placeholders. They are checked as syntax but
    produce no numerical metadata. Effective parameters retain this document's
    occurrence scope until an explicit population join associates a volume.
    """
    document, lines = _context(contents, occurrence, "profile_aux")
    values = [line for _, _, line in lines]
    specs = [("matrix", 0, str), ("gap_open", 1, lambda x: _integer(x, signed=True)),
             ("gap_extend", 2, lambda x: _integer(x, signed=True)), ("scale", 7, _number)]
    for parameter, index, convert in specs:
        lexeme = values[index] if index < len(values) else None
        value = convert(lexeme) if lexeme is not None else None
        if parameter == "matrix" and (not value or any(c.isspace() for c in value)):
            value = None
        if value is None:
            _problem(document, "native_document_invalid", index + 1 if index < len(values) else None)
        document["parameter_observations"].append(_parameter(document, parameter, value,
            index + 1 if index < len(values) else None, lexeme,
            effect="effective" if value is not None else "unknown",
            missing=None if value is not None else "native_field_invalid" if index < len(values)
            else "native_field_absent"))
    for index in range(3, 7):
        lexeme = values[index] if index < len(values) else None
        value = _number(lexeme) if index < 5 else _integer(lexeme)
        if value != 0:
            _problem(document, "native_document_invalid", index + 1 if index < len(values) else None)
    for index in range(8, len(values), 2):
        length = _integer(values[index])
        k = _number(values[index + 1]) if index + 1 < len(values) else None
        if length is None or k is None:
            _problem(document, "native_row_invalid", index + 1 if length is None or
                     index + 1 == len(values) else index + 2)
            continue
        document["rows"].append({"native_profile_ordinal": (index - 8) // 2,
            "sequence_length": length, "karlin_k": k,
            "length_line_number": index + 1, "k_line_number": index + 2})
    if len(values) < 8:
        _problem(document, "native_document_invalid")
    return _finish(document)


_PROFILE_SUFFIXES = (
    (" was excluded: due to too few independent observations", "excluded_low_observations"),
    (" was excluded: it conatins an invalid CD", "excluded_invalid"),
    (" contains no frequency ratios.", "missing_frequency_ratios"),
    (" contains no weighted residue frequencies for building delta database", "missing_weighted_frequencies"),
    (" contains no observations information for building delta database", "missing_independent_observations"),
    (" contains no core block to build cobalt database", "missing_core_blocks"),
    (" 's num of columns does not match size of sequence", "profile_size_conflict"),
    (" has invalid alphabet size", "profile_size_conflict"),
    (" contains no bioseq data", "native_error"),
    (" contains no info on num of columns or num of rows", "native_error"),
    (" contains no pssm or residue frequencies", "native_error"),
    (" contains no scoremat", "native_error"),
    (" contains invalid scoremat", "native_error"),
    (" does not exists", "native_error"),
)
_PROFILE_CONFLICTS = frozenset({"Gap extend penalties do not match", "Gap open penalties do not match",
                              "Score matrix does not match", "Scaling factors do not match"})
_PROFILE_SIZES = frozenset({"PSSM too large for this sequence", "PSSM was truncated early",
                          "Number of frequency and observations columns do not match"})


def parse_makeprofiledb_diagnostics(contents: bytes, *, occurrence: dict) -> dict:
    """Retain located native dispositions without inventing per-input joins."""
    document, lines = _context(contents, occurrence, "profile_diagnostics")
    for number, _, line in lines:
        if line is None or not line.strip(" \t"):
            continue
        category, reference = "unknown", None
        message = re.sub(r"^(?:Warning: |Error: (?:INPUT ERROR: |ERROR: |Error: )?)", "", line)
        for suffix, matched_category in _PROFILE_SUFFIXES:
            if message.endswith(suffix) and message[:-len(suffix)]:
                category, reference = matched_category, message[:-len(suffix)]
                break
        if category == "unknown":
            if message in _PROFILE_CONFLICTS:
                category = "parameter_conflict"
            elif message in _PROFILE_SIZES:
                category = "profile_size_conflict"
            elif message.startswith("Number of frequencies and observations columns do not match in "):
                category = "profile_size_conflict"
                reference = message[len("Number of frequencies and observations columns do not match in "):] or None
            elif _NATIVE_ERROR.match(line):
                category = "native_error"
        if category == "unknown":
            _problem(document, "native_diagnostic_unrecognized", number)
        elif category not in {"excluded_low_observations", "excluded_invalid"}:
            _problem(document, "preparation_not_successful", number, stage="native")
        document["rows"].append({"line_number": number, "category": category,
                                "native_reference": reference, "native_lexeme": line})
    return _finish(document)


__all__ = ["parse_blast_preparation_list", "parse_blast_alias_document",
           "parse_blast_seqid_list_info", "parse_blast_aliastool_diagnostics",
           "parse_makembindex_diagnostics", "parse_makeprofiledb_aux",
           "parse_makeprofiledb_diagnostics"]
