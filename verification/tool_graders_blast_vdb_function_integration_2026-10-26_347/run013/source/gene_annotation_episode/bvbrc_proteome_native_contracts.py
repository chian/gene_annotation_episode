"""Closed, data-only contracts for the legacy GenomeComparison projection.

Validation checks supplied values and their internal relationships, not artifact
possession, API task custody, deployed producer identity, or scientific completion.
The frozen 002 schema is a package asset, loaded once; validation performs no IO.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator, validators


_DOCUMENT = json.loads(
    Path(__file__).with_name("bvbrc_proteome_native_schemas.json").read_text(encoding="utf-8")
)
_DEFINITIONS = _DOCUMENT["$defs"]

REFERENCE_FIELDS = (
    "contig", "gene", "aa_length", "patric_id", "locus_tag", "gene_name",
    "plfam_id", "pgfam_id", "function", "start", "end", "strand",
)
COMPARISON_FIELDS = (
    "hit", "contig", "gene", "aa_length", "patric_id", "locus_tag",
    "gene_name", "function", "percent_identity", "seq_coverage",
)
NUMBER_FIELDS = frozenset({"gene", "aa_length", "start", "end", "percent_identity", "seq_coverage"})
FRACTION_FIELDS = frozenset({"percent_identity", "seq_coverage"})
COUNT_FIELDS = frozenset({"gene", "aa_length"})
DECIMAL_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
COMPARISON_KEY = re.compile(r"comp_genome_([1-9][0-9]*)\Z")
COMPARISON_FIELD = re.compile(r"(comp_genome_([1-9][0-9]*))_(.+)\Z")
FORMATS = frozenset({"genome_comparison_json_v1", "genome_comparison_tsv_v1"})


class NativeValidationError(ValueError):
    """Stable validation code/path; never echoes source values into the message."""

    def __init__(self, code: str, path: str = ""):
        self.code = code
        self.path = path
        super().__init__(code)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _plain_json(value, path="", ancestors=None):
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise NativeValidationError("native_projection_nonfinite_number", path)
        return
    if type(value) not in (dict, list):
        raise NativeValidationError("native_projection_not_plain_json", path)
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise NativeValidationError("native_projection_recursive_json", path)
    ancestors.add(id(value))
    items = value.items() if type(value) is dict else enumerate(value)
    for key, child in items:
        if type(value) is dict and type(key) is not str:
            raise NativeValidationError("native_projection_nonstring_key", path)
        _plain_json(child, _pointer(path, key), ancestors)
    ancestors.remove(id(value))


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPES)


def native_schema(name: str) -> dict:
    """Return a detached entry-point schema containing its reachable definitions."""
    if type(name) is not str or name not in _DEFINITIONS:
        raise NativeValidationError("unknown_proteome_native_contract")
    reachable = set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                ref = node["$ref"]
                if not ref.startswith("#/$defs/") or ref[8:] not in _DEFINITIONS:
                    raise RuntimeError("invalid_packaged_proteome_native_reference")
                key = ref[8:]
                if key not in reachable:
                    reachable.add(key)
                    visit(_DEFINITIONS[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    root = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(root)
    root["$defs"] = {k: deepcopy(v) for k, v in _DEFINITIONS.items() if k in reachable}
    return root


_VALIDATORS = {name: _Validator(native_schema(name)) for name in _DEFINITIONS}


def _validate_shape(name, value):
    _plain_json(value)
    error = next(_VALIDATORS[name].iter_errors(value), None)
    if error is not None:
        path = ""
        for token in error.absolute_path:
            path = _pointer(path, token)
        raise NativeValidationError("native_projection_schema_invalid", path)


def _require(condition, code, path=""):
    if not condition:
        raise NativeValidationError("native_projection_" + code, path)


def _table_blocks(fields):
    """Exact column grammar; preserve native block order and skipped ordinals."""
    if fields[:12] != ["ref_genome_" + name for name in REFERENCE_FIELDS]:
        return None
    if (len(fields) - 12) % 10:
        return None
    blocks = []
    seen = set()
    for offset in range(12, len(fields), 10):
        match = COMPARISON_FIELD.fullmatch(fields[offset])
        if match is None:
            return None
        key, ordinal, _ = match.groups()
        if key in seen or fields[offset:offset + 10] != [key + "_" + name for name in COMPARISON_FIELDS]:
            return None
        seen.add(key)
        try:
            blocks.append((key, int(ordinal), offset))
        except ValueError:
            # A malformed ordinal beyond Python's integer decoding range is
            # incompatible layout, not permission to leak a decoder exception.
            return None
    return blocks


def _check_source_field(field, binding, *, pointer=None, ordinal=None, name=None):
    _require(field["source_ref"] == binding["source_ref"] and field["sha256"] == binding["sha256"],
             "source_field_binding_conflict", field["pointer"])
    _require(not re.search(r"~(?![01])", field["pointer"]), "pointer_invalid", field["pointer"])
    if pointer is not None:
        _require(field["pointer"] == pointer and field["row_ordinal"] == ordinal and
                 field["field_name"] == name, "source_field_location_conflict", pointer)


def _check_cell(cell, name, source_format, binding, *, pointer, ordinal, field_name):
    _check_source_field(cell["source_field"], binding, pointer=pointer, ordinal=ordinal, name=field_name)
    value, presence = cell["value"], cell["presence"]
    if source_format.endswith("tsv_v1"):
        _require(presence != "explicit_null", "table_null_conflict", pointer)
    if name not in NUMBER_FIELDS:
        _require((presence == "value" and type(value) is str and value != "") or
                 (presence == "blank" and value == "") or
                 (presence in {"explicit_null", "omitted", "invalid"} and value is None),
                 "string_presence_conflict", pointer)
        return
    lexeme = cell["lexeme"]
    if presence == "value":
        _require(type(lexeme) is str and DECIMAL_PATTERN.fullmatch(lexeme) is not None,
                 "number_lexeme_invalid", pointer)
        try:
            decimal = Decimal(lexeme)
            equivalent = (decimal == Decimal(value) if type(value) is int else
                          float(decimal) == value and (value != 0 or decimal == 0))
        except (InvalidOperation, OverflowError, ValueError):
            equivalent = False
        _require(equivalent, "number_lexeme_conflict", pointer)
        # Test original decimal bounds, before any floating point rounding.
        if name in FRACTION_FIELDS:
            _require(Decimal(0) <= decimal <= Decimal(1), "fraction_out_of_range", pointer)
        if name in COUNT_FIELDS:
            _require(decimal >= 0 and decimal == decimal.to_integral_value() and
                     value >= 0 and value == int(value), "count_invalid", pointer)
    elif presence == "blank":
        _require(lexeme == "", "number_presence_conflict", pointer)
    elif presence in {"omitted", "explicit_null"}:
        _require(lexeme is None, "number_presence_conflict", pointer)


def validate_native_projection(value: dict) -> dict:
    """Validate a NativeProjection and return a detached copy.

    Invalid shapes or relationships raise NativeValidationError (a ValueError)
    with a fixed code and path. This function has no bytes argument and therefore
    cannot independently authenticate the raw artifact or deployment evidence.
    The parser checks byte correspondence before constructing this projection.
    """
    _validate_shape("NativeProjection", value)
    _require(value["source_contract"]["deployment_match"] != "different",
             "source_version_incompatible", "/source_contract/deployment_match")
    binding = value["source"]["content"]
    tracks = value["tracks"]
    keys = [track["track_key"] for track in tracks]
    _require(len(keys) == len(set(keys)) and "ref_genome" in keys, "track_keys_invalid", "/tracks")
    track_map = {track["track_key"]: track for track in tracks}
    for track in tracks:
        key = track["track_key"]
        match = COMPARISON_KEY.fullmatch(key)
        _require((key == "ref_genome" and track["comparison_ordinal"] is None and
                  track["materialization"] == "reference_rows") or
                 (match is not None and track["comparison_ordinal"] == int(match.group(1)) and
                  track["materialization"] in {"table_field_block", "published_association", "unknown"}),
                 "track_identity_conflict", "/tracks")
        for field in track["source_fields"]:
            _check_source_field(field, binding)

    refs = value["reference_rows"]
    _require(value["physical_record_count"] == len(refs), "record_count_conflict", "/physical_record_count")
    _require(len({row["reference_row_key"] for row in refs}) == len(refs), "duplicate_reference_key")
    is_json = value["format"] == "genome_comparison_json_v1"
    fields = value["table_field_order"]
    if is_json:
        _require(fields == [], "json_table_fields_conflict", "/table_field_order")
    else:
        blocks = _table_blocks(fields)
        _require(blocks is not None, "table_fields_invalid", "/table_field_order")
        _require(keys == ["ref_genome"] + [item[0] for item in blocks], "table_tracks_conflict", "/tracks")
        _require(all(track_map[key]["materialization"] == "table_field_block" for key, _, _ in blocks),
                 "table_materialization_conflict", "/tracks")
    columns = {field: column for column, field in enumerate(fields)}
    header_lines = set()
    if not is_json:
        # A table projection retains both complete headers. They can occur
        # anywhere in the native sort; data locations must not overlap them.
        reference_locations = {}
        for field in track_map["ref_genome"]["source_fields"]:
            reference_locations.setdefault(field["row_ordinal"], []).append(field)
        _require(len(reference_locations) == 2, "table_header_locations_invalid", "/tracks")
        full_headers = [line for line, items in reference_locations.items() if len(items) == 12]
        display_headers = [line for line, items in reference_locations.items() if len(items) == 1]
        _require(len(full_headers) == len(display_headers) == 1 and
                 type(full_headers[0]) is int and type(display_headers[0]) is int,
                 "table_header_locations_invalid", "/tracks")
        field_line, display_line = full_headers[0], display_headers[0]
        header_lines = {field_line, display_line}
        for key, _, offset in [("ref_genome", None, 0)] + blocks:
            width = 12 if key == "ref_genome" else 10
            expected = {(f"/rows/{display_line}/{offset}", display_line, fields[offset])}
            expected.update((f"/rows/{field_line}/{column}", field_line, fields[column])
                            for column in range(offset, offset + width))
            actual = [(f["pointer"], f["row_ordinal"], f["field_name"]) for f in track_map[key]["source_fields"]]
            _require(len(actual) == len(expected) and set(actual) == expected,
                     "table_header_locations_invalid", "/tracks")
    else:
        for track in tracks:
            key = track["track_key"]
            name_pointer = _pointer("/genome_names", key)
            has_name = False
            for field in track["source_fields"]:
                if field["pointer"] == name_pointer:
                    _require(field["row_ordinal"] is None and field["field_name"] == key,
                             "track_source_location_conflict", name_pointer)
                    has_name = True
                else:
                    ordinal = field["row_ordinal"]
                    name = field["field_name"]
                    _require(type(ordinal) is int and ordinal < len(refs) and type(name) is str and
                             name.startswith(key + "_") and
                             field["pointer"] == _pointer(f"/feature_matches/{ordinal}", name),
                             "track_source_location_conflict", field["pointer"])
            _require(track["display_name"] is None or has_name, "track_name_source_missing", "/tracks")

    def check_record(row, row_ordinal, names, prefix):
        native_pointer = row["native_pointer"]
        if is_json:
            _require(native_pointer == f"/feature_matches/{row_ordinal}", "record_pointer_conflict", native_pointer)
            physical = row_ordinal
        else:
            match = re.fullmatch(r"/rows/(0|[1-9][0-9]*)", native_pointer)
            _require(match is not None, "record_pointer_conflict", native_pointer)
            physical = int(match.group(1))
        for name in names:
            field_name = prefix + "_" + name
            pointer = _pointer(native_pointer, field_name) if is_json else native_pointer + "/" + str(columns[field_name])
            _check_cell(row[name], name, value["format"], binding, pointer=pointer,
                        ordinal=physical, field_name=field_name)
            if row["valid"]:
                _require(row[name]["presence"] != "invalid", "valid_row_invalid_cell", pointer)
        errors = [d for d in row["diagnostics"] if d["severity"] == "error"]
        _require(row["valid"] == (not errors), "row_validity_conflict", native_pointer)
        if row["valid"]:
            _require(row["patric_id"]["presence"] == "value", "valid_row_identifier_missing", native_pointer)
        for diagnostic in row["diagnostics"]:
            _require(diagnostic["scope"]["reference_row_ordinal"] == row_ordinal and
                     diagnostic["scope"]["track_key"] == prefix and
                     diagnostic["scope"]["association_key"] == row.get("association_key"),
                     "diagnostic_scope_conflict", native_pointer)
            for field in diagnostic["source_fields"]:
                _check_source_field(field, binding)
        return physical

    physical_rows = []
    for ordinal, row in enumerate(refs):
        _require(row["row_ordinal"] == ordinal, "reference_ordinal_conflict", "/reference_rows")
        _require(row["reference_row_key"] == f"ref_genome/row/{ordinal}",
                 "reference_key_conflict", "/reference_rows")
        physical_rows.append(check_record(row, ordinal, REFERENCE_FIELDS, "ref_genome"))
    _require(physical_rows == sorted(set(physical_rows)), "physical_row_order_conflict", "/reference_rows")
    if not is_json:
        _require(not header_lines.intersection(physical_rows) and
                 header_lines.union(physical_rows) == set(range(len(refs) + 2)),
                 "table_physical_record_conflict", "/reference_rows")
    identifiers = {}
    for row in refs:
        if row["patric_id"]["presence"] == "value":
            identifiers.setdefault(row["patric_id"]["value"], []).append(row)
    for repeated in identifiers.values():
        if len(repeated) > 1:
            expected_pointers = {r["patric_id"]["source_field"]["pointer"] for r in repeated}
            for row in repeated:
                _require(any(d["code"] == "native_duplicate_reference_id" and
                             {f["pointer"] for f in d["source_fields"]} == expected_pointers
                             for d in row["diagnostics"]), "duplicate_reference_qualification_missing", row["native_pointer"])

    associations = value["associations"]
    _require(len({row["association_key"] for row in associations}) == len(associations), "duplicate_association_key")
    pairs = set()
    previous_ordinal = -1
    observed_tracks = set()
    for row in associations:
        ordinal, key = row["reference_row_ordinal"], row["track_key"]
        _require(row["association_key"] == f"{key}/row/{ordinal}",
                 "association_key_conflict", "/associations")
        _require(ordinal < len(refs) and ordinal >= previous_ordinal and key in track_map and key != "ref_genome",
                 "association_reference_conflict", "/associations")
        _require(row["comparison_ordinal"] == track_map[key]["comparison_ordinal"] and
                 row["native_pointer"] == refs[ordinal]["native_pointer"], "association_location_conflict", "/associations")
        _require((ordinal, key) not in pairs, "duplicate_association", "/associations")
        pairs.add((ordinal, key))
        previous_ordinal = ordinal
        observed_tracks.add(key)
        check_record(row, ordinal, COMPARISON_FIELDS, key)
        if row["valid"] and row["hit"]["presence"] == "value":
            _require(row["hit"]["value"] in {"bi (<->)", "uni (->)"}, "hit_category_invalid", row["native_pointer"])
    if is_json:
        for track in tracks:
            if track["track_key"] != "ref_genome":
                _require(track["materialization"] == ("published_association" if track["track_key"] in observed_tracks else "unknown"),
                         "json_materialization_conflict", "/tracks")

    completeness = value["projection_completeness"]
    complete = value["source"]["body_complete"] and value["source"]["object_complete"] == "yes"
    _require((complete and completeness in {"complete_document", "invalid_document"}) or
             (not complete and completeness == ("partial_or_unknown_artifact" if is_json else "complete_prefix_only")),
             "completeness_conflict", "/projection_completeness")
    paths = value["unsupported_field_paths"]
    _require(len(paths) == len(set(paths)) and all(not re.search(r"~(?![01])", path) for path in paths),
             "unsupported_paths_invalid", "/unsupported_field_paths")
    return deepcopy(value)


__all__ = ["native_schema", "validate_native_projection", "NativeValidationError"]
