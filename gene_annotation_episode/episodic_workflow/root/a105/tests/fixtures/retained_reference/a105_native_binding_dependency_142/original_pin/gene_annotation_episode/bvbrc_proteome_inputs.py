"""Deterministic GenomeComparison input inspection over explicitly supplied data.

The inventories describe received inputs, never executed-proteome denominators.
Source locators establish no custody or execution relationship. These readers
perform no acquisition, joins, program execution or aggregate scoring.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

from .bvbrc_appservice_contracts import ContractValidationError, validate_contract
from .bvbrc_proteome_data_contracts import (
    ProteomeDataError, proteome_data_schema, validate_proteome_data,
)


_MISSING = object()
_ASCII_SPACE = " \t\n\r\v\f"
_HEADER_TOKEN = re.compile(r"[^ \t\v\f\r]+")
_AA = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO*")
_NORMALIZATION = "ascii_whitespace_removed_uppercase_no_symbol_substitution_v1"
_TRANSLATION = str.maketrans({**{ord(c): None for c in _ASCII_SPACE},
                            **{n: n - 32 for n in range(ord("a"), ord("z") + 1)}})
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")
_SCOPE = ("track_key", "reference_row_ordinal", "association_key", "protein_key",
          "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")
_FEATURE_STRINGS = (
    "feature_id", "patric_id", "genome_id", "accession", "annotation", "feature_type",
    "aa_sequence_md5", "product", "refseq_locus_tag", "gene", "plfam_id", "pgfam_id", "strand",
)
_THRESHOLDS = ("min_ident", "min_seq_cov", "min_positives", "max_e_val")
_INPUT_ARRAYS = (("genome_ids", "genome_id"), ("user_genomes", "user_genome"),
                 ("user_feature_groups", "user_feature_group"))


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _field(binding, pointer, ordinal=None, name=None):
    return {"source_ref": binding["source_ref"], "sha256": binding["sha256"],
            "pointer": pointer, "row_ordinal": ordinal, "field_name": name or None}


def _diagnostic(code, path="", *, fields=(), severity="error"):
    return {"code": code, "severity": severity, "path": path,
            "scope": dict.fromkeys(_SCOPE), "source_fields": deepcopy(list(fields))}


def _requirement(code, required_input, *, fields=()):
    return {"code": code, "required_input": required_input,
            "scope": dict.fromkeys(_SCOPE), "source_fields": deepcopy(list(fields))}


def _result(name, value, diagnostics, requirements=(), *, partial=False):
    result = {"status": "invalid" if value is None else "partial" if partial else "ok",
              "value": value, "requirements": list(requirements), "diagnostics": diagnostics}
    # Output validation is deliberately outside expected-input exception handlers:
    # an implementation defect must not masquerade as a valid partial result.
    return validate_proteome_data(name + "Result", result)


def _invalid(name, code, path="", *, fields=(), required_input="complete_bytes"):
    return _result(name, None, [_diagnostic(code, path, fields=fields)],
                   [_requirement(code, required_input, fields=fields)])


def _source(content, source, declared_format, expected_format, key, key_name, result_name):
    try:
        source = validate_proteome_data("NativeSource", source)
    except ProteomeDataError as error:
        return None, _invalid(result_name, "supplied_contract_invalid", "/source" + error.path)
    binding = source["content"]
    fields = [_field(binding, "")]
    if type(content) is not bytes:
        return None, _invalid(result_name, "supplied_contract_invalid", "/content", fields=fields)
    if binding["sha256"] != hashlib.sha256(content).hexdigest() or binding["byte_count"] != len(content):
        return None, _invalid(result_name, "content_binding_mismatch", "/source/content", fields=fields)
    if type(declared_format) is not str or declared_format != expected_format:
        return None, _invalid(result_name, "format_incompatible", "/declared_format", fields=fields)
    if type(key) is not str or not key:
        return None, _invalid(result_name, "supplied_contract_invalid", "/" + key_name,
                              fields=fields, required_input="valid_parameters")
    return source, None


def _incompleteness(source, diagnostics, requirements):
    fields = [_field(source["content"], "")]
    for condition, code in ((not source["body_complete"], "source_bytes_incomplete"),
                            (source["object_complete"] != "yes", "source_object_incomplete")):
        if condition:
            diagnostics.append(_diagnostic(code, fields=fields, severity="qualification"))
            requirements.append(_requirement(code, "complete_bytes", fields=fields))
    return not source["body_complete"] or source["object_complete"] != "yes"


def _sequence(text):
    sequence = text.translate(_TRANSLATION)
    encoded = sequence.encode("utf-8")
    return (sequence, len(sequence), hashlib.sha256(encoded).hexdigest(),
            hashlib.md5(encoded).hexdigest(), bool(sequence) and set(sequence) <= _AA)


def read_protein_fasta(content: bytes, *, source: dict, declared_format: str,
                       inventory_key: str) -> dict:
    """Inspect every supplied FASTA occurrence, preserving exact byte intervals."""
    name = "ProteinInventory"
    source, failure = _source(content, source, declared_format, "protein_fasta_utf8_v1",
                              inventory_key, "inventory_key", name)
    if failure is not None:
        return failure
    binding = source["content"]
    complete = source["body_complete"] and source["object_complete"] == "yes"
    starts = [match.start() for match in re.finditer(br"(?m)^>", content)]
    diagnostics, requirements, records = [], [], []
    prefix = content[:starts[0]] if starts else content
    try:
        prefix.decode("utf-8", errors="strict")
        if complete:
            content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _invalid(name, "encoding_invalid", fields=[_field(binding, "")])
    if prefix.strip(_ASCII_SPACE.encode("ascii")):
        if not starts:
            return _invalid(name, "format_incompatible", fields=[_field(binding, "")])
        diagnostics.append(_diagnostic("fasta_header_invalid", fields=[_field(binding, "")]))
    # A recognizable marker is always counted. Only a complete next header can
    # close its preceding record when object completeness is not established.
    headers = []
    for start in starts:
        end = content.find(b"\n", start)
        header_complete = end >= 0 or complete
        header_bytes = content[start + 1:end if end >= 0 else len(content)]
        if end >= 0 and header_bytes.endswith(b"\r"):
            header_bytes = header_bytes[:-1]
        header = None
        if header_complete:
            try:
                header = header_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                return _invalid(name, "encoding_invalid", fields=[_field(binding, "")])
        headers.append((header, end + 1 if end >= 0 else len(content), header_complete))
    for ordinal, start in enumerate(starts):
        end = starts[ordinal + 1] if ordinal + 1 < len(starts) else len(content)
        header, sequence_start, header_complete = headers[ordinal]
        closed = headers[ordinal + 1][2] if ordinal + 1 < len(starts) else complete
        record_complete = header_complete and closed
        token = _HEADER_TOKEN.search(header) if header is not None else None
        field = _field(binding, f"/records/{ordinal}", ordinal)
        row = {"record_ordinal": ordinal, "byte_start": start, "byte_end_exclusive": end,
               "header": header, "identifier": token.group() if token else None,
               "description": header[token.end():] if token else None,
               "sequence": None, "sequence_symbol_count": None, "sequence_sha256": None,
               "sequence_md5": None, "record_complete": record_complete, "valid_sequence": False,
               "source_field": field, "diagnostics": []}
        if header_complete and token is None:
            row["diagnostics"].append(_diagnostic("fasta_header_invalid", field["pointer"], fields=[field]))
        if record_complete:
            try:
                values = _sequence(content[sequence_start:end].decode("utf-8", errors="strict"))
            except UnicodeDecodeError:
                return _invalid(name, "encoding_invalid", field["pointer"], fields=[field])
            for key, value in zip(("sequence", "sequence_symbol_count", "sequence_sha256",
                                   "sequence_md5", "valid_sequence"), values):
                row[key] = value
            if not row["valid_sequence"]:
                code = "fasta_empty_sequence" if row["sequence"] == "" else "fasta_sequence_invalid"
                row["diagnostics"].append(_diagnostic(code, field["pointer"], fields=[field]))
        else:
            row["diagnostics"].append(_diagnostic("fasta_record_incomplete", field["pointer"],
                                                   fields=[field], severity="qualification"))
            requirements.append(_requirement("fasta_record_incomplete", "complete_bytes", fields=[field]))
        records.append(row)
        diagnostics.extend(row["diagnostics"])
    identifiers, sequences = {}, {}
    for row in records:
        if row["identifier"] is not None:
            identifiers.setdefault(row["identifier"], []).append(row["record_ordinal"])
        if row["record_complete"] and row["identifier"] is not None and row["valid_sequence"]:
            # Equality of the entire normalized string is the grouping key.
            sequences.setdefault(row["sequence"], []).append(row)
    duplicate_groups = [{"identifier": identifier, "record_ordinals": ordinals}
                        for identifier, ordinals in identifiers.items() if len(ordinals) > 1]
    for group in duplicate_groups:
        fields = [records[ordinal]["source_field"] for ordinal in group["record_ordinals"]]
        diagnostics.append(_diagnostic("duplicate_identifier", fields=fields, severity="qualification"))
        requirements.append(_requirement("duplicate_identifier", "occurrence_mapping", fields=fields))
    groups = [{"molecule": "aa", "normalization": _NORMALIZATION,
               "sequence_sha256": rows[0]["sequence_sha256"],
               "sequence_symbol_count": rows[0]["sequence_symbol_count"],
               "members": [{"inventory_key": inventory_key, "record_ordinal": row["record_ordinal"]}
                           for row in rows]} for rows in sequences.values()]
    incomplete = _incompleteness(source, diagnostics, requirements)
    if not starts and not prefix.strip(_ASCII_SPACE.encode("ascii")):
        diagnostics.append(_diagnostic("input_empty", fields=[_field(binding, "")], severity="qualification"))
    value = {"version": "bvbrc_proteome_inventory_proposal_v1", "inventory_key": inventory_key,
             "format": declared_format, "source": source, "molecule": "aa", "normalization": _NORMALIZATION,
             "records": records, "observed_header_count": len(records),
             "complete_record_count": sum(row["record_complete"] for row in records),
             "valid_complete_record_count": sum(row["record_complete"] and row["identifier"] is not None
                                                 and row["valid_sequence"] for row in records),
             "duplicate_identifier_groups": duplicate_groups, "sequence_groups": groups,
             "diagnostics": diagnostics}
    return _result(name, value, diagnostics, requirements,
                   partial=incomplete or bool(duplicate_groups) or any(d["severity"] == "error" for d in diagnostics))


@dataclass(frozen=True)
class _NumberToken:
    lexeme: str


@dataclass(frozen=True)
class _Pairs:
    values: list


class _DuplicateMember(ValueError):
    def __init__(self, path):
        self.path = path


def _unique_members(node, path=""):
    if isinstance(node, _Pairs):
        seen = set()
        for key, child in node.values:
            key.encode("utf-8")
            child_path = _pointer(path, key)
            if key in seen:
                raise _DuplicateMember(child_path)
            seen.add(key)
            _unique_members(child, child_path)
    elif type(node) is list:
        for ordinal, child in enumerate(node):
            _unique_members(child, _pointer(path, ordinal))


def _materialize(node):
    if isinstance(node, _Pairs):
        return {key: _materialize(child) for key, child in node.values}
    if type(node) is list:
        return [_materialize(child) for child in node]
    return node


def _invalid_constant(_token):
    raise ValueError("nonstandard_json_number")


def _string(raw, field):
    if raw is _MISSING:
        presence, value = "omitted", None
    elif raw is None:
        presence, value = "explicit_null", None
    elif type(raw) is str:
        # JSON escapes may encode lone surrogates despite valid UTF-8 bytes.
        # Such a scalar is invalid text; its exact spelling remains in bytes.
        try:
            raw.encode("utf-8")
        except UnicodeEncodeError:
            presence, value = "invalid", None
        else:
            presence, value = ("blank" if raw == "" else "value"), raw
    else:
        presence, value = "invalid", None
    return {"value": value, "presence": presence, "source_field": field}


def _number(raw, field, *, minimum=None):
    cell = {"value": None, "presence": "invalid", "lexeme": None, "source_field": field}
    if raw is _MISSING or raw is None:
        cell["presence"] = "omitted" if raw is _MISSING else "explicit_null"
        return cell
    if isinstance(raw, _NumberToken):
        lexeme = raw.lexeme
    elif type(raw) is str:
        lexeme = raw
        try:
            raw.encode("utf-8")
        except UnicodeEncodeError:
            return cell
        if raw == "":
            cell.update(presence="blank", lexeme="")
            return cell
    elif type(raw) is bool:
        cell["lexeme"] = "true" if raw else "false"
        return cell
    else:
        return cell
    cell["lexeme"] = lexeme
    if _DECIMAL.fullmatch(lexeme) is None:
        return cell
    try:
        decimal = Decimal(lexeme)
        if not decimal.is_finite() or decimal != decimal.to_integral_value():
            return cell
        if minimum is not None and decimal < minimum:
            return cell
        numeric = float(decimal)
        if not math.isfinite(numeric) or (numeric == 0 and decimal != 0):
            return cell
        cell.update(value=int(decimal), presence="value")
    except (InvalidOperation, OverflowError, ValueError):
        pass
    return cell


def _usable_id(cell):
    return cell["presence"] == "value" and bool(cell["value"].strip())


def _row_error(row, code, field=None):
    field = row["source_field"] if field is None else field
    row["diagnostics"].append(_diagnostic(code, field["pointer"], fields=[field]))
    row["valid"] = False


def _metadata(content, *, source, declared_format, snapshot_key, population, kind,
              coordinate_convention=None):
    names = {"feature": ("FeatureSnapshot", "bvbrc_genome_feature_json_array_v1", "feature_metadata"),
             "genome": ("GenomeSnapshot", "bvbrc_genome_json_array_v1", "genome_metadata"),
             "sequence": ("FeatureSequenceSnapshot", "bvbrc_feature_sequence_json_array_v1", "feature_sequence")}
    name, expected_format, required_input = names[kind]
    source, failure = _source(content, source, declared_format, expected_format, snapshot_key, "snapshot_key", name)
    if failure is not None:
        return failure
    binding = source["content"]
    root_fields = [_field(binding, "")]
    try:
        population = validate_proteome_data("PopulationDescriptor", population)
    except ProteomeDataError as error:
        return _invalid(name, "supplied_contract_invalid", "/population" + error.path,
                        fields=root_fields, required_input="complete_membership")
    if kind == "feature":
        try:
            coordinate_convention = validate_proteome_data("CoordinateConvention", coordinate_convention)
        except ProteomeDataError as error:
            return _invalid(name, "supplied_contract_invalid", "/coordinate_convention" + error.path,
                            fields=root_fields, required_input="coordinate_convention")
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _invalid(name, "encoding_invalid", fields=root_fields)
    try:
        tree = json.loads(text, object_pairs_hook=_Pairs, parse_int=_NumberToken,
                          parse_float=_NumberToken, parse_constant=_invalid_constant)
        _unique_members(tree)
        document = _materialize(tree)
    except _DuplicateMember as error:
        return _invalid(name, "duplicate_json_member", error.path, fields=root_fields)
    except UnicodeEncodeError:
        return _invalid(name, "encoding_invalid", fields=root_fields)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return _invalid(name, "json_invalid", fields=root_fields)
    if type(document) is not list:
        return _invalid(name, "format_incompatible", fields=root_fields)
    records, diagnostics, requirements, unsupported = [], [], [], []
    strings = _FEATURE_STRINGS if kind == "feature" else ("genome_id", "genome_name") if kind == "genome" else ("md5", "sequence")
    numbers = ("start", "end", "aa_length") if kind == "feature" else ("taxon_id",) if kind == "genome" else ()
    for ordinal, original in enumerate(document):
        pointer = "/" + str(ordinal)
        row = {"row_ordinal": ordinal, "source_field": _field(binding, pointer, ordinal),
               "valid": True, "diagnostics": []}
        is_object = type(original) is dict
        raw = original if is_object else {}
        for field_name in strings + numbers:
            field = _field(binding, _pointer(pointer, field_name), ordinal, field_name)
            scalar = raw.get(field_name, _MISSING)
            if field_name in strings:
                row[field_name] = _string(scalar, field)
            else:
                minimum = 1 if field_name == "taxon_id" else 0 if field_name == "aa_length" else None
                if field_name in ("start", "end"):
                    minimum = {"unknown": None, "one_based_closed": 1, "zero_based_half_open": 0}[coordinate_convention["value"]]
                row[field_name] = _number(scalar, field, minimum=minimum)
            if not is_object:
                row[field_name].update(presence="invalid", value=None)
            if row[field_name]["presence"] == "invalid" and is_object:
                _row_error(row, "native_invalid_cell", field)
        if not is_object:
            _row_error(row, "metadata_record_invalid")
        for key in raw:
            if key not in strings + numbers:
                unknown_path = _pointer(pointer, key)
                unsupported.append(unknown_path)
                diagnostics.append(_diagnostic("unknown_metadata_fields_retained", unknown_path,
                    fields=[_field(binding, unknown_path, ordinal, key)], severity="qualification"))
        if kind == "feature":
            if not (_usable_id(row["feature_id"]) or _usable_id(row["patric_id"])):
                _row_error(row, "metadata_record_invalid")
            md5 = row["aa_sequence_md5"]
            if md5["presence"] == "value" and _MD5.fullmatch(md5["value"]) is None:
                md5.update(presence="invalid", value=None)
                _row_error(row, "native_invalid_cell", md5["source_field"])
            if coordinate_convention["value"] == "zero_based_half_open" and all(row[k]["presence"] == "value" for k in ("start", "end")) and row["end"]["value"] < row["start"]["value"]:
                # Keep both observed endpoints and isolate the invalid interval.
                _row_error(row, "metadata_record_invalid", row["end"]["source_field"])
        elif kind == "genome":
            if not _usable_id(row["genome_id"]):
                _row_error(row, "metadata_record_invalid", row["genome_id"]["source_field"])
        else:
            row.update(molecule="aa", sequence_symbol_count=None, computed_md5=None, computed_sha256=None)
            md5, sequence = row["md5"], row["sequence"]
            md5_valid = md5["presence"] == "value" and _MD5.fullmatch(md5["value"]) is not None
            if not md5_valid:
                if md5["presence"] == "value":
                    md5.update(presence="invalid", value=None)
                _row_error(row, "metadata_record_invalid", md5["source_field"])
            if sequence["presence"] in {"value", "blank"}:
                normalized, count, sha256, digest, valid_sequence = _sequence(sequence["value"])
                row.update(sequence_symbol_count=count, computed_md5=digest, computed_sha256=sha256)
                if not valid_sequence:
                    _row_error(row, "fasta_empty_sequence" if not normalized else "fasta_sequence_invalid", sequence["source_field"])
                if md5_valid and md5["value"].lower() != digest:
                    _row_error(row, "sequence_digest_conflict", md5["source_field"])
            else:
                _row_error(row, "metadata_record_invalid", sequence["source_field"])
        records.append(row)
        diagnostics.extend(row["diagnostics"])
        if not row["valid"]:
            requirements.append(_requirement("metadata_record_invalid", required_input, fields=[row["source_field"]]))
    identities = {}
    identity_fields = ("feature_id", "patric_id") if kind == "feature" else ("genome_id",) if kind == "genome" else ("md5",)
    for row in records:
        for key in identity_fields:
            cell = row[key]
            if _usable_id(cell):
                identifier = cell["value"].lower() if key == "md5" else cell["value"]
                identities.setdefault((key, identifier), []).append(cell["source_field"])
    duplicates = [fields for fields in identities.values() if len(fields) > 1]
    for fields in duplicates:
        diagnostics.append(_diagnostic("duplicate_identifier", fields=fields, severity="qualification"))
        requirements.append(_requirement("duplicate_identifier", "occurrence_mapping", fields=fields))
    incomplete = _incompleteness(source, diagnostics, requirements)
    population_state = population["population_complete"]
    if population_state != "yes":
        code = "metadata_population_incomplete" if population_state == "no" else "metadata_population_unknown"
        fields = population["completeness_evidence"] or root_fields
        diagnostics.append(_diagnostic(code, "/population", fields=fields, severity="qualification"))
        requirements.append(_requirement(code, "complete_membership", fields=fields))
    if population["origin"] == "later_database_snapshot":
        diagnostics.append(_diagnostic("later_snapshot_not_original_input", "/population", fields=root_fields, severity="qualification"))
    if kind == "feature" and coordinate_convention["value"] == "unknown":
        fields = [row[key]["source_field"] for row in records for key in ("start", "end") if row[key]["presence"] == "value"]
        if fields:
            diagnostics.append(_diagnostic("coordinate_convention_unknown", "/coordinate_convention", fields=fields, severity="qualification"))
            requirements.append(_requirement("coordinate_convention_unknown", "coordinate_convention", fields=fields))
    value = {"version": "bvbrc_proteome_metadata_proposal_v1", "snapshot_key": snapshot_key,
             "format": declared_format, "source": source, "population": population,
             "records": records, "unsupported_field_paths": unsupported, "diagnostics": diagnostics}
    if kind == "feature":
        value["coordinate_convention"] = coordinate_convention
    return _result(name, value, diagnostics, requirements,
                   partial=incomplete or population_state != "yes" or bool(duplicates) or any(not row["valid"] for row in records))


def read_feature_metadata(content: bytes, *, source: dict, declared_format: str,
                          snapshot_key: str, population: dict, coordinate_convention: dict) -> dict:
    """Read original feature cells without inferring identities or coordinates."""
    return _metadata(content, source=source, declared_format=declared_format, snapshot_key=snapshot_key,
                     population=population, coordinate_convention=coordinate_convention, kind="feature")


def read_genome_metadata(content: bytes, *, source: dict, declared_format: str,
                         snapshot_key: str, population: dict) -> dict:
    """Read genome identities, optional names and optional numerical taxon IDs."""
    return _metadata(content, source=source, declared_format=declared_format, snapshot_key=snapshot_key,
                     population=population, kind="genome")


def read_feature_sequences(content: bytes, *, source: dict, declared_format: str,
                           snapshot_key: str, population: dict) -> dict:
    """Read supplied amino-acid sequence records, retaining their MD5 identities."""
    return _metadata(content, source=source, declared_format=declared_format, snapshot_key=snapshot_key,
                     population=population, kind="sequence")


def _parameter_snapshot(parameters, source, kind):
    snapshot = {"kind": kind, "source_field": deepcopy(source)}
    for key in _THRESHOLDS:
        raw = parameters.get(key, _MISSING)
        if raw is _MISSING:
            presence, value = "omitted", None
        elif raw is None:
            presence, value = "explicit_null", None
        elif type(raw) in (int, float) and (type(raw) is int or math.isfinite(raw)):
            presence, value = "value", raw
        else:
            presence, value = "invalid", None
        snapshot[key] = {"value": value, "presence": presence,
                         "source_field": _field(source, _pointer(source["pointer"], key),
                                                source["row_ordinal"], key)}
    return snapshot


def index_original_inputs(original_task: dict, *, parameter_source: dict, source_contract: dict,
                          additional_parameter_sources: list[dict] | None = None) -> dict:
    """Index recorded selections; ordering is not evidence of executed membership."""
    name = "InputIndex"
    try:
        task = validate_contract("OriginalTask", original_task)
    except ContractValidationError as error:
        path = error.diagnostics[0]["path"]
        return _invalid(name, "supplied_contract_invalid", "/original_task" + path, required_input="original_parameters")
    for contract_name, value, path in (("ParameterSource", parameter_source, "/parameter_source"),
                                       ("SourceContract", source_contract, "/source_contract")):
        try:
            validate_proteome_data(contract_name, value)
        except ProteomeDataError as error:
            return _invalid(name, "supplied_contract_invalid", path + error.path, required_input="original_parameters")
    if task["required_application_id"] != "GenomeComparison" or task["native_application_id"] != "GenomeComparison":
        return _invalid(name, "format_incompatible", "/original_task", required_input="original_parameters")
    if source_contract["deployment_match"] == "different":
        return _invalid(name, "format_incompatible", "/source_contract", required_input="producer_execution_facts")
    source = parameter_source["source_field"]
    effective = task["effective_parameters"]
    submitted = task["submitted_parameters"]
    if additional_parameter_sources is None:
        additional_parameter_sources = []
    if type(additional_parameter_sources) is not list:
        return _invalid(name, "supplied_contract_invalid", "/additional_parameter_sources", required_input="original_parameters")
    sources = {}
    for ordinal, candidate in enumerate([parameter_source, *additional_parameter_sources]):
        path = "/parameter_source" if ordinal == 0 else f"/additional_parameter_sources/{ordinal - 1}"
        try:
            candidate = validate_proteome_data("ParameterSource", candidate)
        except ProteomeDataError as error:
            return _invalid(name, "supplied_contract_invalid", path + error.path, required_input="original_parameters")
        kind, field = candidate["kind"], candidate["source_field"]
        if kind in sources and sources[kind] != field:
            return _invalid(name, "parameter_source_conflict", path, fields=[sources[kind], field], required_input="original_parameters")
        if kind == "submitted":
            consistent = field["source_ref"] == task["submission_source_ref"]
        else:
            evidence = effective["evidence"] if effective is not None else None
            consistent = evidence is not None and (field["source_ref"] == evidence["content"]["source_ref"] and
                field["sha256"] == evidence["content"]["sha256"] and field["pointer"] == evidence["pointer"])
        if not consistent:
            return _invalid(name, "parameter_source_conflict", path, fields=[field], required_input="original_parameters")
        sources[kind] = field
    selected = submitted if parameter_source["kind"] == "submitted" else effective["value"]
    if parameter_source["kind"] == "effective":
        for key in [item[0] for item in _INPUT_ARRAYS] + ["reference_genome_index"]:
            if key in submitted and submitted[key] is not None and (key not in selected or type(submitted[key]) is not type(selected[key]) or submitted[key] != selected[key]):
                return _invalid(name, "parameter_source_conflict", _pointer("/original_task/submitted_parameters", key), fields=[source], required_input="original_parameters")
    entries = []
    for key, kind in _INPUT_ARRAYS:
        array = selected.get(key)
        if type(array) is not list or any(type(value) is not str or not value for value in array):
            return _invalid(name, "input_arrays_unavailable", _pointer("", key), fields=[source], required_input="original_parameters")
        try:
            for item in array:
                item.encode("utf-8")
        except UnicodeEncodeError:
            return _invalid(name, "input_arrays_unavailable", _pointer("", key), fields=[source], required_input="original_parameters")
        for ordinal, value in enumerate(array):
            pointer = f"/{key}/{ordinal}"
            entries.append({"input_key": pointer, "parameter_pointer": pointer,
                            "original_index": len(entries) + 1, "kind": kind, "value": value,
                            "expected_track_key": "", "source_field": _field(source, source["pointer"] + pointer, ordinal, key)})
    reference = selected.get("reference_genome_index")
    if type(reference) is not int or not 1 <= reference <= len(entries):
        return _invalid(name, "input_reference_index_invalid", "/reference_genome_index", fields=[source], required_input="original_parameters")
    entries = [entries[reference - 1]] + [entry for entry in entries if entry["original_index"] != reference]
    for ordinal, entry in enumerate(entries):
        entry["expected_track_key"] = "ref_genome" if ordinal == 0 else f"comp_genome_{ordinal}"
    snapshots = []
    if "submitted" in sources:
        snapshots.append(_parameter_snapshot(submitted, sources["submitted"], "submitted"))
    if effective is not None:
        evidence = effective["evidence"]
        effective_source = sources.get("effective", _field(evidence["content"], evidence["pointer"]))
        snapshots.append(_parameter_snapshot(effective["value"], effective_source, "effective"))
    diagnostics = [_diagnostic("input_order_is_not_execution_proof", fields=[source], severity="qualification")]
    requirements = []
    if "submitted" not in sources:
        # OriginalTask supplies no submitted-parameter content digest/pointer.
        # Retain only source-bound snapshots rather than inventing provenance.
        diagnostics.append(_diagnostic("parameter_source_conflict", "/run_parameter_snapshots", severity="qualification"))
        requirements.append(_requirement("parameter_source_conflict", "original_parameters"))
    for snapshot in snapshots:
        for key in _THRESHOLDS:
            if snapshot[key]["presence"] == "invalid":
                field = snapshot[key]["source_field"]
                diagnostics.append(_diagnostic("native_invalid_cell", field["pointer"], fields=[field]))
                requirements.append(_requirement("native_invalid_cell", "valid_parameters", fields=[field]))
    value = {"version": "bvbrc_proteome_input_index_proposal_v1", "parameter_source": parameter_source,
             "reference_original_index": reference, "inputs": entries, "source_contract": source_contract,
             "run_parameter_snapshots": snapshots, "diagnostics": diagnostics}
    return _result(name, value, diagnostics, requirements,
                   partial=bool(requirements))


__all__ = ["read_protein_fasta", "read_feature_metadata", "read_genome_metadata",
           "read_feature_sequences", "index_original_inputs"]
