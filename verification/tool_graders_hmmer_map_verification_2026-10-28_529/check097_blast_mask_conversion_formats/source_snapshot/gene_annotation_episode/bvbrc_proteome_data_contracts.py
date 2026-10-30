"""Pure validation of saved proteome input data and their relationships.

Schema assets define closed data shapes, not calculation instructions. Source
custody belongs to the execution host. No acquisition, scientific parser or
calculator is invoked by these validation functions.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator, validators


class ProteomeDataError(ValueError):
    def __init__(self, code: str, path: str = ""):
        self.code = code
        self.path = path
        super().__init__(code)


def _require(condition, code, path=""):
    if not condition:
        raise ProteomeDataError("proteome_data_" + code, path)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _plain(value, path="", ancestors=None):
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ProteomeDataError("proteome_data_invalid_unicode", path) from error
        return
    if value is None or type(value) in (int, bool):
        return
    if type(value) is float:
        _require(math.isfinite(value), "nonfinite_number", path)
        return
    _require(type(value) in (dict, list), "plain_json_required", path)
    ancestors = set() if ancestors is None else ancestors
    _require(id(value) not in ancestors, "recursive_json", path)
    ancestors.add(id(value))
    for key, child in (value.items() if type(value) is dict else enumerate(value)):
        _require(type(value) is list or type(key) is str, "string_key_required", path)
        _plain(child, _pointer(path, key), ancestors)
    ancestors.remove(id(value))


_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
})
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPES)
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


@lru_cache(maxsize=1)
def _document():
    # This package asset is loaded once. It is not caller-supplied executable
    # scoring rules, nor a remote schema reference.
    return json.loads(Path(__file__).with_name("bvbrc_proteome_data_schemas.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _schema(name):
    definitions = _document()["$defs"]
    _require(type(name) is str and name in definitions, "unknown_contract")
    reachable = set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                target = node["$ref"]
                if not target.startswith("#/$defs/") or target[8:] not in definitions:
                    raise RuntimeError("invalid_packaged_proteome_data_reference")
                key = target[8:]
                if key not in reachable:
                    reachable.add(key)
                    visit(definitions[key])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    schema = {"$schema": _document()["$schema"], "$ref": "#/$defs/" + name}
    visit(schema)
    schema["$defs"] = {key: definitions[key] for key in definitions if key in reachable}
    return schema


def proteome_data_schema(name: str) -> dict:
    """Return an isolated closed schema for one installed data contract."""
    _require(type(name) is str, "unknown_contract")
    return deepcopy(_schema(name))


@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))


def _native_cell(value, path):
    presence = value["presence"]
    number = "lexeme" in value
    if number:
        lexeme = value["lexeme"]
        if presence == "value":
            _require(type(lexeme) is str and _DECIMAL.fullmatch(lexeme) is not None,
                     "numeric_lexeme_invalid", path)
            try:
                decimal = Decimal(lexeme)
                numeric = value["value"]
                equal = (decimal == Decimal(numeric) if type(numeric) is int else
                         float(decimal) == numeric and (numeric != 0 or decimal == 0))
            except (InvalidOperation, OverflowError, ValueError):
                equal = False
            _require(equal, "numeric_lexeme_conflict", path)
        elif presence == "blank":
            _require(lexeme == "", "numeric_presence_conflict", path)
        elif presence in {"explicit_null", "omitted"}:
            _require(lexeme is None, "numeric_presence_conflict", path)
    else:
        actual = value["value"]
        _require((presence == "value" and type(actual) is str and actual != "") or
                 (presence == "blank" and actual == "") or
                 (presence in {"explicit_null", "omitted", "invalid"} and actual is None),
                 "string_presence_conflict", path)


def _common(value, path=""):
    if type(value) is dict:
        if set(value) == {"source_ref", "sha256", "pointer", "row_ordinal", "field_name"}:
            _require(re.search(r"~(?![01])", value["pointer"]) is None,
                     "source_pointer_invalid", path)
        if (set(value) == {"value", "presence", "lexeme", "source_field"} or
                set(value) == {"value", "presence", "source_field"} and
                type(value["value"]) not in (int, float)):
            _native_cell(value, path)
        for key, child in value.items():
            _common(child, _pointer(path, key))
    elif type(value) is list:
        for index, child in enumerate(value):
            _common(child, _pointer(path, index))


def validate_proteome_data(name: str, value: dict) -> dict:
    """Validate installed shape and saved relationships; return a detached copy."""
    try:
        return _validate_proteome_data(name, value)
    except RecursionError as error:
        raise ProteomeDataError("proteome_data_excessive_nesting") from error


def _validate_proteome_data(name, value):
    _require(type(name) is str, "unknown_contract")
    _plain(value)
    error = next(_validator(name).iter_errors(value), None)
    if error is not None:
        path = ""
        for token in error.absolute_path:
            path = _pointer(path, token)
        raise ProteomeDataError("proteome_data_schema_invalid", path)
    _common(value)
    _relationships(name, value)
    return deepcopy(value)


def _relationships(name, value):
    if name.endswith("Result"):
        if value["value"] is not None:
            _relationships(name.removesuffix("Result"), value["value"])
            if value["status"] == "ok":
                data = value["value"]
                _require(not _error_diagnostics(value) and not _error_diagnostics(data),
                         "successful_result_errors_conflict")
                if "records" in data:
                    records = data["records"]
                    if name == "ProteinInventoryResult":
                        valid = all(row["record_complete"] and row["identifier"] is not None and
                                    row["valid_sequence"] for row in records)
                    else:
                        valid = all(row["valid"] for row in records)
                    _require(valid, "successful_result_invalid_records")
        return
    if name == "ProteinInventory":
        _inventory(value)
    elif name == "FastaRecord":
        _fasta_record(value, "")
    elif name in {"FeatureSnapshot", "GenomeSnapshot", "FeatureSequenceSnapshot"}:
        _snapshot(name, value)
    elif name in {"FeatureRecord", "GenomeRecord", "FeatureSequenceRecord"}:
        _metadata_record(name, value, "", "unknown")
    elif name == "PopulationDescriptor":
        _population(value, "")
    elif name == "CoordinateConvention":
        _coordinate_convention(value, "")
    elif name == "InputIndex":
        _input_index(value)
    elif name == "SequenceGroup":
        refs = [(r["inventory_key"], r["record_ordinal"]) for r in value["members"]]
        _require(bool(refs) and len(refs) == len(set(refs)), "sequence_group_members_invalid")
    elif name == "DuplicateIdentifierGroup":
        ordinals = value["record_ordinals"]
        _require(len(ordinals) >= 2 and ordinals == sorted(set(ordinals)),
                 "duplicate_identifier_members_invalid")
    elif name == "RunParameterSnapshot":
        _parameter_snapshot(value, "")


_ASCII_SPACE = " \t\n\r\v\f"
_HEADER_SPACE = " \t\r\v\f"
_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO*")
_HEX_MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")


def _normalize(text):
    return "".join(ch for ch in text if ch not in _ASCII_SPACE).translate(_UPPER)


def _usable(cell):
    return cell["presence"] == "value" and bool(cell["value"].strip())


def _error_diagnostics(value):
    return any(item["severity"] == "error" for item in value["diagnostics"])


def _source_field(field, binding, path, *, pointer=None, ordinal=None, field_name=None):
    _require(field["source_ref"] == binding["source_ref"] and field["sha256"] == binding["sha256"],
             "source_binding_conflict", path)
    if pointer is not None:
        _require(field["pointer"] == pointer, "source_location_conflict", path)
    if ordinal is not None:
        _require(field["row_ordinal"] == ordinal, "source_ordinal_conflict", path)
    if field_name is not None:
        _require(field["field_name"] == field_name, "source_field_name_conflict", path)


def _header_parts(header):
    if header is None:
        return None, None
    start = 0
    while start < len(header) and header[start] in _HEADER_SPACE:
        start += 1
    end = start
    while end < len(header) and header[end] not in _HEADER_SPACE:
        end += 1
    return (header[start:end], header[end:]) if start != end else (None, None)


def _fasta_record(row, path):
    _require(row["byte_end_exclusive"] > row["byte_start"], "record_byte_interval_invalid", path)
    header = row["header"]
    _require(header is None or "\n" not in header, "header_line_conflict", path)
    identifier, description = _header_parts(header)
    _require((row["identifier"], row["description"]) == (identifier, description),
             "header_identity_conflict", path)
    sequence_fields = ("sequence", "sequence_symbol_count", "sequence_sha256", "sequence_md5")
    if not row["record_complete"]:
        _require(all(row[key] is None for key in sequence_fields) and not row["valid_sequence"],
                 "incomplete_sequence_conflict", path)
        return
    sequence = row["sequence"]
    _require(type(sequence) is str and sequence == _normalize(sequence),
             "normalized_sequence_required", path)
    raw = sequence.encode("utf-8")
    _require(row["sequence_symbol_count"] == len(sequence), "sequence_count_conflict", path)
    _require(row["sequence_sha256"] == hashlib.sha256(raw).hexdigest() and
             row["sequence_md5"] == hashlib.md5(raw).hexdigest(), "sequence_digest_conflict", path)
    _require(row["valid_sequence"] == (bool(sequence) and set(sequence) <= _ALPHABET),
             "sequence_validity_conflict", path)


def _inventory(value):
    records = value["records"]
    source = value["source"]
    binding = source["content"]
    valid = []
    identifiers = {}
    sequences = {}
    previous_end = None
    for ordinal, row in enumerate(records):
        path = f"/records/{ordinal}"
        _fasta_record(row, path)
        _require(row["record_ordinal"] == ordinal, "record_ordinal_conflict", path)
        _require(row["byte_end_exclusive"] <= binding["byte_count"], "record_outside_source", path)
        if previous_end is not None:
            _require(row["byte_start"] == previous_end, "record_byte_order_conflict", path)
        previous_end = row["byte_end_exclusive"]
        _source_field(row["source_field"], binding, path, pointer=f"/records/{ordinal}", ordinal=ordinal)
        if row["identifier"] is not None:
            identifiers.setdefault(row["identifier"], []).append(ordinal)
        if row["record_complete"] and row["identifier"] is not None and row["valid_sequence"]:
            valid.append(ordinal)
            sequences.setdefault(row["sequence"], []).append(ordinal)
        if row["record_complete"] and ordinal == len(records) - 1:
            _require(source["body_complete"] and source["object_complete"] == "yes",
                     "final_record_completeness_conflict", path)
    if records:
        _require(previous_end == binding["byte_count"], "final_record_byte_end_conflict", "/records")
    _require(value["observed_header_count"] == len(records) and
             value["complete_record_count"] == sum(r["record_complete"] for r in records) and
             value["valid_complete_record_count"] == len(valid), "inventory_counts_conflict")
    duplicates = {key: members for key, members in identifiers.items() if len(members) > 1}
    claimed_duplicates = {}
    for group in value["duplicate_identifier_groups"]:
        _require(group["identifier"] not in claimed_duplicates, "duplicate_identifier_group_repeated")
        claimed_duplicates[group["identifier"]] = group["record_ordinals"]
    _require(claimed_duplicates == duplicates, "duplicate_identifier_groups_conflict")
    groups = {}
    for group in value["sequence_groups"]:
        members = group["members"]
        _require(bool(members), "sequence_group_empty")
        ordinals = [item["record_ordinal"] for item in members]
        _require(ordinals == sorted(set(ordinals)) and all(i in valid for i in ordinals),
                 "sequence_group_member_conflict")
        _require(all(item["inventory_key"] == value["inventory_key"] for item in members),
                 "sequence_group_inventory_conflict")
        text = records[ordinals[0]]["sequence"]
        _require(all(records[i]["sequence"] == text for i in ordinals), "sequence_group_text_conflict")
        _require(group["sequence_sha256"] == records[ordinals[0]]["sequence_sha256"] and
                 group["sequence_symbol_count"] == len(text), "sequence_group_value_conflict")
        _require(text not in groups, "sequence_group_repeated")
        groups[text] = ordinals
    _require(groups == sequences, "sequence_groups_incomplete")


def _numeric_domain(cell, minimum=None):
    if cell["presence"] != "value":
        return cell["presence"] != "invalid"
    number = cell["value"]
    return number == int(number) and (minimum is None or number >= minimum)


def _hex_cell(cell):
    return (cell["presence"] != "invalid" if cell["presence"] != "value" else
            _HEX_MD5.fullmatch(cell["value"]) is not None)


def _metadata_record(name, row, path, convention):
    cells = {key: cell for key, cell in row.items()
             if type(cell) is dict and "presence" in cell and "source_field" in cell}
    valid = not _error_diagnostics(row) and all(c["presence"] != "invalid" for c in cells.values())
    if name == "FeatureRecord":
        valid = valid and (_usable(row["feature_id"]) or _usable(row["patric_id"]))
        valid = valid and _numeric_domain(row["aa_length"], 0) and _hex_cell(row["aa_sequence_md5"])
        minimum = {"one_based_closed": 1, "zero_based_half_open": 0, "unknown": None}[convention]
        valid = valid and all(_numeric_domain(row[field], minimum) for field in ("start", "end"))
        if convention == "zero_based_half_open" and all(row[k]["presence"] == "value" for k in ("start", "end")):
            valid = valid and row["end"]["value"] >= row["start"]["value"]
    elif name == "GenomeRecord":
        valid = valid and _usable(row["genome_id"]) and _numeric_domain(row["taxon_id"], 1)
    else:
        sequence = row["sequence"]
        present = sequence["presence"] in {"value", "blank"}
        text = _normalize(sequence["value"]) if present else None
        if present:
            raw = text.encode("utf-8")
            _require(row["sequence_symbol_count"] == len(text) and
                     row["computed_md5"] == hashlib.md5(raw).hexdigest() and
                     row["computed_sha256"] == hashlib.sha256(raw).hexdigest(),
                     "metadata_sequence_integrity_conflict", path)
        else:
            _require(all(row[k] is None for k in ("sequence_symbol_count", "computed_md5", "computed_sha256")),
                     "metadata_sequence_absence_conflict", path)
        valid = valid and present and bool(text) and set(text) <= _ALPHABET
        valid = valid and _usable(row["md5"]) and _hex_cell(row["md5"])
        valid = valid and row["md5"]["value"].lower() == row["computed_md5"]
    _require(row["valid"] == bool(valid), "metadata_validity_conflict", path)


def _population(value, path):
    _require(len(value["selected_fields"]) == len(set(value["selected_fields"])),
             "selected_fields_repeated", path)
    total = value["reported_total_count"]
    _require(total is None or _numeric_domain(total, 0), "population_count_invalid", path)


def _coordinate_convention(value, path):
    _require(value["value"] == "unknown" or bool(value["source_fields"]),
             "coordinate_evidence_missing", path)


def _snapshot(name, value):
    _population(value["population"], "/population")
    convention = "unknown"
    if name == "FeatureSnapshot":
        _coordinate_convention(value["coordinate_convention"], "/coordinate_convention")
        convention = value["coordinate_convention"]["value"]
    binding = value["source"]["content"]
    record_type = {"FeatureSnapshot": "FeatureRecord", "GenomeSnapshot": "GenomeRecord",
                   "FeatureSequenceSnapshot": "FeatureSequenceRecord"}[name]
    for ordinal, row in enumerate(value["records"]):
        path = f"/records/{ordinal}"
        _require(row["row_ordinal"] == ordinal, "metadata_ordinal_conflict", path)
        _source_field(row["source_field"], binding, path, pointer=f"/{ordinal}", ordinal=ordinal)
        for key, cell in row.items():
            if type(cell) is dict and "presence" in cell and "source_field" in cell:
                _source_field(cell["source_field"], binding, _pointer(path, key),
                              pointer=f"/{ordinal}/{key}", ordinal=ordinal, field_name=key)
        _metadata_record(record_type, row, path, convention)
    fields = value["unsupported_field_paths"]
    _require(len(fields) == len(set(fields)) and all(re.search(r"~(?![01])", f) is None for f in fields),
             "unsupported_field_paths_invalid", "/unsupported_field_paths")


def _parameter_snapshot(value, path):
    source = value["source_field"]
    for name in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
        _source_field(value[name]["source_field"], source, _pointer(path, name),
                      pointer=_pointer(source["pointer"], name), field_name=name)


def _input_index(value):
    entries = value["inputs"]
    _require(bool(entries), "original_inputs_missing")
    n = len(entries)
    ordinals = [item["original_index"] for item in entries]
    _require(set(ordinals) == set(range(1, n + 1)) and len(set(ordinals)) == n,
             "original_input_ordinals_conflict")
    reference = value["reference_original_index"]
    _require(reference <= n, "reference_index_outside_inputs")
    order = [reference] + [i for i in range(1, n + 1) if i != reference]
    tracks = {index: "ref_genome" if position == 0 else f"comp_genome_{position}"
              for position, index in enumerate(order)}
    keys = set()
    grouped = {"genome_id": [], "user_genome": [], "user_feature_group": []}
    groups = {"genome_id": "genome_ids", "user_genome": "user_genomes", "user_feature_group": "user_feature_groups"}
    source = value["parameter_source"]["source_field"]
    for item in entries:
        path = "/inputs"
        key = item["input_key"]
        _require(key == item["parameter_pointer"] and key not in keys, "input_key_conflict", path)
        keys.add(key)
        match = re.fullmatch("/" + groups[item["kind"]] + r"/(0|[1-9][0-9]*)", key)
        _require(match is not None, "input_pointer_conflict", path)
        grouped[item["kind"]].append((int(match.group(1)), item["original_index"]))
        _require(item["expected_track_key"] == tracks[item["original_index"]], "input_track_conflict", path)
        _source_field(item["source_field"], source, path, pointer=source["pointer"] + key)
    cursor = 1
    for kind in groups:
        rows = sorted(grouped[kind])
        _require(rows == [(index, cursor + index) for index in range(len(rows))],
                 "input_original_order_conflict", "/inputs")
        cursor += len(rows)
    kinds = set()
    for snapshot in value["run_parameter_snapshots"]:
        _require(snapshot["kind"] not in kinds, "parameter_snapshot_repeated")
        kinds.add(snapshot["kind"])
        _parameter_snapshot(snapshot, "/run_parameter_snapshots")
        if snapshot["kind"] == value["parameter_source"]["kind"]:
            _require(snapshot["source_field"] == source, "selected_parameter_source_conflict")
    _require(value["parameter_source"]["kind"] in kinds, "selected_parameter_snapshot_missing")
    _require(value["source_contract"]["deployment_match"] != "different", "source_version_incompatible")


__all__ = ["proteome_data_schema", "validate_proteome_data", "ProteomeDataError"]
