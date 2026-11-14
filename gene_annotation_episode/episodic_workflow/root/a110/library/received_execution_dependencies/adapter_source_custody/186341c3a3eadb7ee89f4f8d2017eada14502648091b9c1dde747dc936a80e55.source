"""Read the inspected GenomeComparison legacy JSON or TSV from supplied bytes.

This is a native projection reader, not a complete scientific capability. The
producer keeps only first-HSP/best-subject summaries. ``percent_identity`` is a
rounded first-HSP alignment-column fraction; ``seq_coverage`` is the rounded
legacy abs(subject_end-subject_start)/subject_length fraction, omitting the
inclusive endpoint. Neither is reconstructed, corrected, or treated as a
probability. Coordinates remain the writer's native values, including artificial
layout coordinates. All full-HSP, inventory, join, custody and aggregate work
belongs to separate consumers.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math

from .bvbrc_proteome_native_contracts import (
    COMPARISON_FIELD, COMPARISON_FIELDS, COMPARISON_KEY, COUNT_FIELDS,
    DECIMAL_PATTERN, FORMATS, FRACTION_FIELDS, NUMBER_FIELDS, REFERENCE_FIELDS,
    NativeValidationError, _pointer, _table_blocks, _validate_shape,
    native_schema, validate_native_projection,
)


_MISSING = object()
_SCOPE_FIELDS = (
    "track_key", "reference_row_ordinal", "association_key", "protein_key",
    "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal",
)


@dataclass(frozen=True)
class _NumberToken:
    lexeme: str


@dataclass(frozen=True)
class _ObjectPairs:
    pairs: list


class _DuplicateMember(ValueError):
    def __init__(self, path):
        self.path = path


def _check_unique_members(node, path=""):
    """Check the complete pairs tree before constructing any JSON dictionaries."""
    if isinstance(node, _ObjectPairs):
        seen = set()
        for key, child in node.pairs:
            pointer = _pointer(path, key)
            if key in seen:
                raise _DuplicateMember(pointer)
            seen.add(key)
            _check_unique_members(child, pointer)
    elif type(node) is list:
        for ordinal, child in enumerate(node):
            _check_unique_members(child, _pointer(path, ordinal))


def _materialize(node):
    if isinstance(node, _ObjectPairs):
        return {key: _materialize(child) for key, child in node.pairs}
    if type(node) is list:
        return [_materialize(child) for child in node]
    return node


def _invalid_constant(token):
    raise ValueError("nonstandard_json_number")


def _scope(**values):
    return {name: values.get(name) for name in _SCOPE_FIELDS}


def _field(binding, pointer, row_ordinal=None, field_name=None):
    return {
        "source_ref": binding["source_ref"], "sha256": binding["sha256"],
        "pointer": pointer, "row_ordinal": row_ordinal, "field_name": field_name or None,
    }


def _diagnostic(code, path="", *, severity="error", scope=None, fields=()):
    return {
        "code": code, "severity": severity, "path": path,
        "scope": _scope() if scope is None else deepcopy(scope),
        "source_fields": deepcopy(list(fields)),
    }


def _requirement(code, required_input, *, scope=None, fields=()):
    return {
        "code": code, "scope": _scope() if scope is None else deepcopy(scope),
        "required_input": required_input, "source_fields": deepcopy(list(fields)),
    }


def _invalid(code, path="", *, binding=None, required_input="complete_artifact_bytes"):
    fields = [_field(binding, "")] if binding is not None else []
    return {
        "status": "invalid", "value": None,
        "requirements": [_requirement(code, required_input, fields=fields)],
        "diagnostics": [_diagnostic(code, path, fields=fields)],
    }


def _string(raw, source_field):
    if raw is _MISSING:
        presence, value = "omitted", None
    elif raw is None:
        presence, value = "explicit_null", None
    elif type(raw) is str:
        presence, value = ("blank" if raw == "" else "value"), raw
    else:
        presence, value = "invalid", None
    return {"value": value, "presence": presence, "source_field": source_field}


def _number(raw, source_field, name):
    cell = {"value": None, "presence": "invalid", "lexeme": None, "source_field": source_field}
    if raw is _MISSING:
        cell["presence"] = "omitted"
        return cell, None
    if raw is None:
        cell["presence"] = "explicit_null"
        return cell, None
    if isinstance(raw, _NumberToken):
        lexeme = raw.lexeme
    elif type(raw) is str:
        lexeme = raw
        if raw == "":
            cell.update(presence="blank", lexeme="")
            return cell, None
    elif type(raw) is bool:
        cell["lexeme"] = "true" if raw else "false"
        return cell, "native_number_invalid"
    else:
        return cell, "native_number_invalid"
    cell["lexeme"] = lexeme
    if DECIMAL_PATTERN.fullmatch(lexeme) is None:
        return cell, "native_number_invalid"
    try:
        decimal = Decimal(lexeme)
        if not decimal.is_finite():
            return cell, "native_number_invalid"
        if name in FRACTION_FIELDS and not Decimal(0) <= decimal <= Decimal(1):
            return cell, "native_fraction_out_of_range"
        if name in COUNT_FIELDS and (decimal < 0 or decimal != decimal.to_integral_value()):
            return cell, "native_number_invalid"
        # JSON-compatible finite numerical storage; lexeme retains exact spelling.
        # Avoid replacing a nonzero underflow with a measured zero.
        number = float(decimal)
        if not math.isfinite(number) or (number == 0 and decimal != 0):
            return cell, "native_number_invalid"
        if decimal == decimal.to_integral_value():
            number = int(decimal)
        cell.update(value=number, presence="value")
    except (InvalidOperation, OverflowError, ValueError):
        return cell, "native_number_invalid"
    return cell, None


class _ProjectionBuilder:
    def __init__(self, source, declared_format, source_contract):
        self.source = deepcopy(source)
        self.binding = self.source["content"]
        self.format = declared_format
        self.contract = deepcopy(source_contract)
        self.diagnostics = []
        self.requirements = []
        self.tracks = {}
        self.rows = []
        self.associations = []
        self.unsupported = []
        self.table_fields = []

    def qualify(self, code, *, scope=None, fields=(), required_input=None, path=""):
        self.diagnostics.append(_diagnostic(code, path, severity="qualification", scope=scope, fields=fields))
        if required_input is not None:
            self.requirements.append(_requirement(code, required_input, scope=scope, fields=fields))

    def unsupported_field(self, pointer, *, row=None, scope=None, source_field=None):
        if pointer not in self.unsupported:
            self.unsupported.append(pointer)
        diagnostic = _diagnostic("native_schema_incompatible", pointer, scope=scope,
                                 fields=[source_field or _field(self.binding, pointer)])
        if row is None:
            self.diagnostics.append(diagnostic)
        else:
            row["diagnostics"].append(diagnostic)
            row["valid"] = False

    def add_track(self, key, *, display_name=None, materialization="unknown", fields=()):
        if key not in self.tracks:
            self.tracks[key] = {
                "track_key": key,
                "comparison_ordinal": None if key == "ref_genome" else int(COMPARISON_KEY.fullmatch(key).group(1)),
                "display_name": display_name, "materialization": materialization,
                "source_fields": deepcopy(list(fields)),
            }
        else:
            track = self.tracks[key]
            if materialization != "unknown":
                track["materialization"] = materialization
            for field in fields:
                if field not in track["source_fields"]:
                    track["source_fields"].append(deepcopy(field))

    def record(self, *, raw, row_ordinal, pointer, physical_row, prefix, columns=None, malformed=None):
        reference = prefix == "ref_genome"
        names = REFERENCE_FIELDS if reference else COMPARISON_FIELDS
        if reference:
            record = {"row_ordinal": row_ordinal, "reference_row_key": f"ref_genome/row/{row_ordinal}"}
            scope = _scope(track_key=prefix, reference_row_ordinal=row_ordinal)
        else:
            association_key = f"{prefix}/row/{row_ordinal}"
            record = {
                "association_key": association_key, "reference_row_ordinal": row_ordinal,
                "track_key": prefix, "comparison_ordinal": self.tracks[prefix]["comparison_ordinal"],
            }
            scope = _scope(track_key=prefix, reference_row_ordinal=row_ordinal, association_key=association_key)
        record.update(native_pointer=pointer, valid=True, diagnostics=[])
        if malformed is not None:
            record["diagnostics"].append(_diagnostic(malformed, pointer, scope=scope,
                                                     fields=[_field(self.binding, pointer, physical_row)]))
        for name in names:
            field_name = prefix + "_" + name
            field_pointer = _pointer(pointer, field_name) if columns is None else pointer + "/" + str(columns[field_name])
            source_field = _field(self.binding, field_pointer, physical_row, field_name)
            scalar = raw.get(field_name, _MISSING)
            if name in NUMBER_FIELDS:
                cell, code = _number(scalar, source_field, name)
            else:
                cell = _string(scalar, source_field)
                code = "native_row_invalid" if cell["presence"] == "invalid" else None
            record[name] = cell
            if code is not None:
                record["diagnostics"].append(_diagnostic(code, field_pointer, scope=scope, fields=[source_field]))
        if record["patric_id"]["presence"] != "value":
            source_field = record["patric_id"]["source_field"]
            record["diagnostics"].append(_diagnostic("native_row_invalid", source_field["pointer"],
                                                     scope=scope, fields=[source_field]))
        if not reference and record["hit"]["presence"] == "value" and record["hit"]["value"] not in {"bi (<->)", "uni (->)"}:
            source_field = record["hit"]["source_field"]
            record["diagnostics"].append(_diagnostic("native_hit_category_invalid", source_field["pointer"],
                                                     scope=scope, fields=[source_field]))
        record["valid"] = not any(item["severity"] == "error" for item in record["diagnostics"])
        return record

    def finish(self):
        ids = {}
        for row in self.rows:
            if row["patric_id"]["presence"] == "value":
                ids.setdefault(row["patric_id"]["value"], []).append(row)
        for repeated in ids.values():
            if len(repeated) < 2:
                continue
            fields = [row["patric_id"]["source_field"] for row in repeated]
            for row in repeated:
                row["diagnostics"].append(_diagnostic(
                    "native_duplicate_reference_id", row["patric_id"]["source_field"]["pointer"],
                    severity="qualification",
                    scope=_scope(track_key="ref_genome", reference_row_ordinal=row["row_ordinal"]), fields=fields,
                ))
            self.requirements.append(_requirement("native_duplicate_reference_id", "identifier_mapping", fields=fields))

        for row in self.rows + self.associations:
            self.diagnostics.extend(deepcopy(row["diagnostics"]))
        root_field = _field(self.binding, "")
        complete = self.source["body_complete"] and self.source["object_complete"] == "yes"
        if not self.source["body_complete"]:
            self.qualify("source_bytes_incomplete", fields=[root_field], required_input="complete_artifact_bytes")
        if self.source["object_complete"] != "yes":
            self.qualify("source_object_incomplete", fields=[root_field], required_input="complete_artifact_bytes")
        if self.contract["deployment_match"] == "unobserved":
            self.qualify("native_source_version_unverified", required_input="native_producer_version", path="/source_contract")
        self.qualify("legacy_hsp_data_not_retained", fields=[root_field], required_input="directional_blast_report")
        for track in self.tracks.values():
            if track["materialization"] == "unknown":
                self.qualify("track_materialization_unknown", scope=_scope(track_key=track["track_key"]),
                             fields=track["source_fields"], required_input="producer_manifest")
        has_errors = any(item["severity"] == "error" for item in self.diagnostics)
        if has_errors:
            self.requirements.append(_requirement("projection_incomplete", "complete_artifact_bytes", fields=[root_field]))
        completeness = ("complete_document" if complete else
                        "partial_or_unknown_artifact" if self.format == "genome_comparison_json_v1" else
                        "complete_prefix_only")
        value = {
            "version": "bvbrc_proteome_native_projection_v1", "scientific_mode": "proteome_comparison",
            "format": self.format, "source": self.source, "source_contract": self.contract,
            "tracks": list(self.tracks.values()), "reference_rows": self.rows, "associations": self.associations,
            "physical_record_count": len(self.rows), "table_field_order": self.table_fields,
            "projection_completeness": completeness, "unsupported_field_paths": self.unsupported,
        }
        value = validate_native_projection(value)
        result = {
            "status": "partial" if has_errors or not complete else "ok", "value": value,
            "requirements": self.requirements, "diagnostics": self.diagnostics,
        }
        _validate_shape("NativeProjectionResult", result)
        return deepcopy(result)


def _parse_json(text, builder):
    try:
        pairs = json.loads(text, object_pairs_hook=_ObjectPairs, parse_int=_NumberToken,
                           parse_float=_NumberToken, parse_constant=_invalid_constant)
        _check_unique_members(pairs)
        document = _materialize(pairs)
    except _DuplicateMember as error:
        return _invalid("duplicate_json_member", error.path, binding=builder.binding)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return _invalid("native_json_invalid", binding=builder.binding)
    if (type(document) is not dict or type(document.get("genome_names")) is not dict or
            type(document.get("feature_matches")) is not list):
        return _invalid("native_schema_incompatible", binding=builder.binding)
    names = document["genome_names"]
    if "ref_genome" not in names or type(names["ref_genome"]) is not str:
        return _invalid("native_schema_incompatible", "/genome_names/ref_genome", binding=builder.binding)
    for key in document:
        if key not in {"genome_names", "feature_matches"}:
            builder.unsupported_field(_pointer("", key))
    for key, display in names.items():
        pointer = _pointer("/genome_names", key)
        if key != "ref_genome" and COMPARISON_KEY.fullmatch(key) is None:
            builder.unsupported_field(pointer)
            continue
        if key != "ref_genome":
            try:
                int(COMPARISON_KEY.fullmatch(key).group(1))
            except ValueError:
                return _invalid("native_schema_incompatible", pointer, binding=builder.binding)
        field = _field(builder.binding, pointer, field_name=key)
        if type(display) is not str:
            builder.unsupported_field(pointer, source_field=field)
            display = None
        builder.add_track(key, display_name=display,
                          materialization="reference_rows" if key == "ref_genome" else "unknown", fields=[field])
    for ordinal, original in enumerate(document["feature_matches"]):
        pointer = f"/feature_matches/{ordinal}"
        raw = original if type(original) is dict else {}
        row = builder.record(raw=raw, row_ordinal=ordinal, pointer=pointer, physical_row=ordinal,
                             prefix="ref_genome", malformed="native_row_invalid" if type(original) is not dict else None)
        comparisons = {}
        for field_name in raw:
            match = COMPARISON_FIELD.fullmatch(field_name)
            if field_name in {"ref_genome_" + name for name in REFERENCE_FIELDS}:
                continue
            if match is not None and match.group(3) in COMPARISON_FIELDS:
                key = match.group(1)
                try:
                    int(match.group(2))
                except ValueError:
                    builder.unsupported_field(_pointer(pointer, field_name), row=row,
                        scope=_scope(track_key="ref_genome", reference_row_ordinal=ordinal),
                        source_field=_field(builder.binding, _pointer(pointer, field_name), ordinal, field_name))
                    continue
                field = _field(builder.binding, _pointer(pointer, field_name), ordinal, field_name)
                comparisons.setdefault(key, []).append(field)
            else:
                builder.unsupported_field(_pointer(pointer, field_name), row=row,
                    scope=_scope(track_key="ref_genome", reference_row_ordinal=ordinal),
                    source_field=_field(builder.binding, _pointer(pointer, field_name), ordinal, field_name))
        builder.rows.append(row)
        for key, source_fields in comparisons.items():
            if key not in builder.tracks:
                builder.qualify("native_comparison_track_missing", scope=_scope(track_key=key, reference_row_ordinal=ordinal),
                                fields=source_fields, required_input="complete_artifact_bytes", path=pointer)
            builder.add_track(key, materialization="published_association", fields=source_fields)
            builder.associations.append(builder.record(raw=raw, row_ordinal=ordinal, pointer=pointer,
                                                        physical_row=ordinal, prefix=key))
    return builder.finish()


def _parse_tsv(text, builder):
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    # Literal tabs only: the producer has no quoting or escape convention.
    rows = [line.removesuffix("\r").split("\t") for line in lines]
    headers = [(ordinal, row, _table_blocks(row)) for ordinal, row in enumerate(rows) if _table_blocks(row) is not None]
    if len(headers) != 1:
        return _invalid("native_table_header_invalid", "/rows", binding=builder.binding)
    field_line, fields, blocks = headers[0]
    starts = {0} | {offset for _, _, offset in blocks}
    displays = [(ordinal, row) for ordinal, row in enumerate(rows) if ordinal != field_line and
                len(row) == len(fields) and all(cell == "" for index, cell in enumerate(row) if index not in starts)]
    if len(displays) != 1:
        return _invalid("native_table_header_invalid", "/rows", binding=builder.binding)
    display_line, display = displays[0]
    builder.table_fields = fields
    columns = {field: column for column, field in enumerate(fields)}
    all_blocks = [("ref_genome", None, 0)] + blocks
    for key, _, offset in all_blocks:
        width = 12 if key == "ref_genome" else 10
        source_fields = [_field(builder.binding, f"/rows/{display_line}/{offset}", display_line, fields[offset])]
        source_fields.extend(_field(builder.binding, f"/rows/{field_line}/{column}", field_line, fields[column])
                             for column in range(offset, offset + width))
        builder.add_track(key, display_name=display[offset],
                          materialization="reference_rows" if key == "ref_genome" else "table_field_block", fields=source_fields)
    for physical, cells in enumerate(rows):
        if physical in {field_line, display_line}:
            continue
        ordinal = len(builder.rows)
        pointer = f"/rows/{physical}"
        raw = dict(zip(fields, cells))
        malformed = "native_table_width_invalid" if len(cells) != len(fields) else None
        row = builder.record(raw=raw, row_ordinal=ordinal, pointer=pointer, physical_row=physical,
                             prefix="ref_genome", columns=columns, malformed=malformed)
        for column in range(len(fields), len(cells)):
            builder.unsupported_field(f"{pointer}/{column}", row=row,
                scope=_scope(track_key="ref_genome", reference_row_ordinal=ordinal),
                source_field=_field(builder.binding, f"{pointer}/{column}", physical))
        builder.rows.append(row)
        for key, _, offset in blocks:
            if not any(cell != "" for cell in cells[offset:offset + 10]):
                continue
            builder.associations.append(builder.record(raw=raw, row_ordinal=ordinal, pointer=pointer,
                physical_row=physical, prefix=key, columns=columns, malformed=malformed))
    return builder.finish()


def parse_genome_comparison(content: bytes, *, source: dict, declared_format: str,
                            source_contract: dict) -> dict:
    """Return a closed NativeProjectionResult for supplied custom JSON/TSV bytes.

    Source content identity is checked before decoding. ``object_complete`` is
    yes/no/unknown; no custody, task or producer identity is inferred. Invalid
    documents return null with fixed diagnostics. Malformed local records remain
    in source order alongside usable neighbors. Returned objects are detached.
    """
    try:
        _validate_shape("NativeSource", source)
    except (NativeValidationError, RecursionError):
        return _invalid("artifact_binding_unqualified", "/source")
    binding = source["content"]
    if type(content) is not bytes:
        return _invalid("artifact_binding_unqualified", "/content", binding=binding)
    if binding["sha256"] != hashlib.sha256(content).hexdigest() or binding["byte_count"] != len(content):
        return _invalid("artifact_digest_mismatch", "/source/content", binding=binding)
    if type(declared_format) is not str or declared_format not in FORMATS:
        return _invalid("native_schema_incompatible", "/declared_format", binding=binding)
    try:
        _validate_shape("SourceContract", source_contract)
    except (NativeValidationError, RecursionError) as error:
        return _invalid("native_schema_incompatible", "/source_contract" + getattr(error, "path", ""),
                        binding=binding, required_input="native_producer_version")
    if source_contract["deployment_match"] == "different":
        return _invalid("native_schema_incompatible", "/source_contract/deployment_match",
                        binding=binding, required_input="native_producer_version")
    decode_content = content
    complete = source["body_complete"] and source["object_complete"] == "yes"
    if declared_format == "genome_comparison_tsv_v1" and not complete:
        # Do not promote an unterminated final transfer fragment to a row.
        decode_content = content[:content.rfind(b"\n") + 1]
    try:
        text = decode_content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _invalid("native_encoding_invalid", binding=binding)
    builder = _ProjectionBuilder(source, declared_format, source_contract)
    return _parse_json(text, builder) if declared_format == "genome_comparison_json_v1" else _parse_tsv(text, builder)


__all__ = ["parse_genome_comparison", "native_schema", "validate_native_projection"]
