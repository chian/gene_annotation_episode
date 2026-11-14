"""Pure readers for the six explicitly selected ComparativeSystems formats.

Native reports are retained, including source defects. No records, identities,
producer versions or biological absence are reconstructed from a filename.
"""
from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import io
import json
import math
import re

from .bvbrc_comparative_systems_handoff_contracts import validate_shape

__all__ = ("parse_comparative_systems_document",)

_COMMIT = "670b3b6dd09509ebc62fb6f1b1caf3e38c33bd33"
_SOURCE_SHA = "052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f"
_PREFIX = "comparative_systems_"
_PROFILES = {
    _PREFIX + "pathways_json_v1": (("pathway", "manual_tabs_unquoted"),
                                   ("ecnumber", "manual_tabs_unquoted"), ("genes", "pandas_tsv")),
    _PREFIX + "subsystems_json_v1": (("subsystems", "pandas_tsv"), ("genes", "pandas_tsv")),
    _PREFIX + "families_json_v1": (("plfam", "manual_tabs_unquoted"), ("pgfam", "manual_tabs_unquoted")),
    _PREFIX + "pathways_tsv_v1": (("pathways_tsv", "pandas_tsv"),),
    _PREFIX + "subsystems_tsv_v1": (("subsystems_tsv", "pandas_tsv"),),
    _PREFIX + "variant_matrix_source670b_v1": (("variant_matrix", "pinned_variant_matrix"),),
}
_HEADERS = {
    "plfam": "family_id feature_count genome_count product aa_length_min aa_length_max aa_length_mean aa_length_std genomes".split(),
    "pgfam": "family_id feature_count genome_count product aa_length_min aa_length_max aa_length_mean aa_length_std genomes".split(),
    "pathway": "annotation pathway_id pathway_name pathway_class genome_count ec_count gene_count genome_ec ec_conservation gene_conservation".split(),
    "ecnumber": "annotation pathway_id pathway_name pathway_class ec_description ec_number genome_count ec_count gene_count genome_ec".split(),
    "subsystems": "superclass class subclass subsystem_name subsystem_id role_counts gene_counts genome_count gene_conservation role_conservation prop_active".split(),
}
_UNITS = {"feature_count": "occurrence", "genome_count": "genome",
          "ec_count": "ec_token", "gene_count": "feature_token", "genome_ec": "genome_ec_pair",
          "ec_conservation": "percent", "role_counts": "role_token", "gene_counts": "feature_token",
          "role_conservation": "percent", "prop_active": "fraction", "aa_length_min": "amino_acid",
          "aa_length_max": "amino_acid", "aa_length_mean": "amino_acid", "aa_length_std": "amino_acid"}
_INTEGER_FIELDS = {"feature_count", "genome_count", "ec_count", "gene_count", "genome_ec",
                   "role_counts", "gene_counts", "aa_length_min", "aa_length_max",
                   "subsystem_name_counts", "active", "likely", "inactive", "missing_genomes"}


def _pointer(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def _location(document, table=None, row=None, column=None, field=None, pointer=""):
    return {"source_ref": document["source_ref"], "raw_artifact_ref": document["raw_artifact_ref"],
            "document_id": document["document_id"], "json_pointer": pointer, "table": table,
            "row_ordinal": row, "column_ordinal": column, "native_field": field}


def _cell(value, unit, *, state="available", method="native_field", refs=(), codes=(),
          origin="program_reported_derived", population_id=None):
    return {"state": state, "value": value if state == "available" else None, "unit": unit,
            "origin": origin, "population_id": population_id, "method_id": method,
            "input_refs": list(refs), "uncertainty": None, "qualification_codes": list(dict.fromkeys(codes))}


def _diagnostic(document, code, *, phase="decode", row=None, locations=()):
    return {"code": code, "phase": phase, "document_id": document["document_id"],
            "row_ordinal": row, "field": document["role"], "source_refs": [document["source_ref"]],
            "locations": list(locations), "affected_field_ids": [], "required_input_role": None}


def _known_producer(document, producer_evidence):
    evidence_id = document["producer_evidence_id"]
    ids = [item["evidence_id"] for item in producer_evidence]
    if len(ids) != len(set(ids)):
        raise ValueError("comparative_systems_duplicate_producer_id")
    if evidence_id is None:
        return False
    matches = [item for item in producer_evidence if item["evidence_id"] == evidence_id]
    if len(matches) != 1:
        raise ValueError("comparative_systems_producer_reference_missing")
    item = matches[0]
    witnessed = ((item["identity_kind"] == "source_executed" and
                  document["basis"] == "source_executed_synthetic") or
                 (item["identity_kind"] == "deployed_attested" and document["basis"] == "service_artifact"))
    return witnessed and item["commit"] == _COMMIT and item["source_sha256"] in (None, _SOURCE_SHA)


def _number(token, field, location, unit, *, forced_state=None, codes=()):
    refs = [{"kind": "native", "owner_id": location["document_id"], "pointer": location["json_pointer"]}]
    qualifiers = list(codes)
    state, value = "available", None
    if token is None or token.strip() == "":
        state = "missing"
    else:
        try:
            if field in _INTEGER_FIELDS:
                if re.fullmatch(r"[+-]?[0-9]+", token) is None:
                    raise ValueError
                value = int(token)
            else:
                if re.fullmatch(r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|(?i:nan|inf(?:inity)?))", token) is None:
                    raise ValueError
                value = float(token)
            if isinstance(value, float) and not math.isfinite(value):
                state = "invalid"
                qualifiers.append("nonfinite_number")
            elif value < 0 or (unit == "percent" and value > 100) or (unit == "fraction" and value > 1):
                state = "invalid"
                qualifiers.append("numeric_token_invalid")
        except (ValueError, OverflowError):
            state = "invalid"
            qualifiers.append("numeric_token_invalid")
    if forced_state is not None:
        state = forced_state
    return {"native_field": field, "raw_lexeme": token, "location": location,
            "cell": _cell(value, unit, state=state, refs=refs, codes=qualifiers)}


def _row_numbers(document, table, row, header, pointer, *, known):
    tokens = row["tokens"]
    nums = []
    if table == "variant_matrix":
        fields = [(4, "active", "occurrence"), (5, "likely", "occurrence"),
                  (6, "inactive", "occurrence"), (7, "missing_genomes", "genome")]
    elif table in _HEADERS:
        fields = [(idx, field, _UNITS.get(field, "feature_per_role_genome" if table == "subsystems"
                                         else "feature_per_ec_genome"))
                  for idx, field in enumerate(header)
                  if field in _UNITS or field == "gene_conservation"]
    else:
        return nums
    for column, field, unit in fields:
        codes = []
        forced = "invalid" if row["status"] == "invalid" else None
        if table == "variant_matrix":
            if not known:
                forced = "incompatible"
                codes.append("producer_version_unverified")
            if column in (6, 7):
                codes.append("native_category_imputed")
        token = tokens[column] if column < len(tokens) else None
        nums.append(_number(token, field, _location(document, table, row["row_ordinal"], column,
                                                   field, pointer), unit, forced_state=forced, codes=codes))
    if table in ("plfam", "pgfam"):
        by_name = {n["native_field"]: n for n in nums}
        limits = [by_name.get(name) for name in ("aa_length_min", "aa_length_mean", "aa_length_max")]
        if all(n and n["cell"]["state"] == "available" for n in limits):
            values = [n["cell"]["value"] for n in limits]
            if not values[0] <= values[1] <= values[2]:
                for number in limits:
                    number["cell"].update(state="invalid", value=None)
                    number["cell"]["qualification_codes"].append("numeric_token_invalid")
    return nums


def _parse_table(text, table, dialect, document, pointer, diagnostics, *, known):
    result = {"table": table, "json_pointer": pointer, "raw_text": text,
              "dialect": dialect, "headers": [], "rows": []}
    records, malformed = [], None
    if dialect == "pandas_tsv":
        stream = io.StringIO(text, newline="")
        reader = csv.reader(stream, delimiter="\t", quotechar='"', doublequote=True, strict=True)
        previous = 0
        try:
            for tokens in reader:
                records.append(tokens)
                previous = reader.line_num
        except csv.Error:
            malformed = ["".join(text.splitlines(keepends=True)[previous:])]
    else:
        # splitlines() would also split vertical tabs inside an unquoted field.
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        records = [line.removesuffix("\r").split("\t") for line in lines]
    header_count = 2 if dialect == "pinned_variant_matrix" else 1
    result["headers"] = records[:header_count]
    records = records[header_count:]
    if not text or not result["headers"] or len(result["headers"]) != header_count:
        diagnostics.append(_diagnostic(document, "tsv_header_mismatch", locations=[_location(document, table, pointer=pointer)]))
    header = result["headers"][-1] if result["headers"] else []
    bad_header = len(header) != len(set(header))
    if table in _HEADERS and header != _HEADERS[table]:
        bad_header = True
    if table == "variant_matrix":
        bad_header = (len(header) < 7 or header[:7] != ["Superclass", "Class", "Subclass", "SS", "active", "likely", "inactive"]
                      or len(result["headers"]) != 2 or len(result["headers"][0]) != len(header))
        if len(result["headers"]) == 2:
            names = result["headers"][0][7:]
            if len(names) != len(set(names)):
                diagnostics.append(_diagnostic(document, "genome_name_collision"))
    if bad_header:
        diagnostics.append(_diagnostic(document, "tsv_header_mismatch", locations=[_location(document, table, pointer=pointer)]))
    if malformed is not None:
        records.append(malformed)
    for ordinal, tokens in enumerate(records):
        codes = []
        expected = len(header) + (1 if table == "variant_matrix" else 0)
        invalid = bad_header or len(tokens) != expected or (malformed is not None and ordinal == len(records) - 1)
        if invalid:
            codes.append("tsv_header_mismatch" if bad_header else "tsv_row_width_mismatch")
        if table == "variant_matrix" and len(tokens) == len(header) + 1:
            codes.append("variant_matrix_extra_column")
        row = {"row_ordinal": ordinal, "tokens": tokens, "status": "invalid" if invalid else "ok",
               "numeric_fields": [], "qualification_codes": codes}
        row["numeric_fields"] = _row_numbers(document, table, row, header, pointer, known=known)
        for number in row["numeric_fields"]:
            codes.extend(number["cell"]["qualification_codes"])
        row["qualification_codes"] = list(dict.fromkeys(codes))
        if row["status"] != "invalid" and any(n["cell"]["state"] != "available" for n in row["numeric_fields"]):
            row["status"] = "partial"
        result["rows"].append(row)
        for code in row["qualification_codes"]:
            diagnostics.append(_diagnostic(document, code, row=ordinal,
                                           locations=[_location(document, table, ordinal, pointer=pointer)]))
    if not result["rows"]:
        diagnostics.append(_diagnostic(document, "no_native_rows", locations=[_location(document, table, pointer=pointer)]))
    return result


def _family_hex(table, metadata, document, diagnostics):
    """Decode only a complete, consistent two-digit-per-genome encoding."""
    genome_ids = metadata.get("genome_ids")
    lists = metadata.get(table["table"] + "_genomes")
    valid_ids = (type(genome_ids) is list and all(type(g) is str and g.strip() and g == g.strip() for g in genome_ids))
    valid_order = valid_ids and len(set(genome_ids)) == len(genome_ids)
    if not valid_order:
        diagnostics.append(_diagnostic(document, "identity_conflict", phase="association"))
    if not valid_ids:
        return
    for row in table["rows"]:
        header = table["headers"][0] if table["headers"] else []
        values = dict(zip(header, row["tokens"])) if row["status"] != "invalid" else {}
        column = header.index("genomes") if header.count("genomes") == 1 else None
        # Preserve an actual token even in an invalid-width row. An absent
        # column has no lexeme; it is distinct from a present empty token.
        raw = row["tokens"][column] if column is not None and column < len(row["tokens"]) else None
        positives = lists.get(values.get("family_id")) if type(lists) is dict else None
        valid_list = type(positives) is list and all(type(g) is str and g.strip() for g in positives)
        nums = {n["native_field"]: n["cell"] for n in row["numeric_fields"]}
        codes = ["native_query_completeness_unknown"]
        width = isinstance(raw, str) and len(raw) == 2 * len(genome_ids) and re.fullmatch(r"[0-9a-fA-F]*", raw) is not None
        counts = [int(raw[i:i + 2], 16) for i in range(0, len(raw), 2)] if width else []
        coherent = (valid_order and width and valid_list and set(positives) <= set(genome_ids)
                    and nums.get("feature_count", {}).get("state") == "available"
                    and nums.get("genome_count", {}).get("state") == "available"
                    and sum(counts) == nums["feature_count"]["value"]
                    and len(set(positives)) == nums["genome_count"]["value"]
                    and {g for g, count in zip(genome_ids, counts) if count > 0} == set(positives))
        if not width:
            codes.append("hex_count_width_ambiguous")
        elif not coherent:
            codes.append("identity_conflict")
        if valid_list and len(positives) != len(set(positives)):
            codes.append("duplicate_identical_representation")
        for ordinal, _genome in enumerate(genome_ids):
            location = _location(document, table["table"], row["row_ordinal"],
                                 column, "genomes", table["json_pointer"])
            cell = _cell(counts[ordinal] if coherent else None, "occurrence",
                         state="available" if coherent else "incompatible", method="native_hex_exact_width", codes=codes,
                         refs=[{"kind": "native", "owner_id": document["document_id"], "pointer": table["json_pointer"]},
                               {"kind": "native", "owner_id": document["document_id"], "pointer": f"/genome_ids/{ordinal}"}])
            row["numeric_fields"].append({"native_field": "genomes", "raw_lexeme": raw,
                                           "location": location, "cell": cell})
        for code in codes[1:]:
            if code not in row["qualification_codes"]:
                row["qualification_codes"].append(code)
            diagnostics.append(_diagnostic(document, code, row=row["row_ordinal"], phase="association"))
        if not coherent and row["status"] == "ok":
            row["status"] = "partial"


class _JSONNumber:
    def __init__(self, token):
        self.token = token


def _json_decode(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def constant(_token):
        raise ValueError("nonfinite_number")

    native = json.loads(text, object_pairs_hook=pairs, parse_int=_JSONNumber,
                        parse_float=_JSONNumber, parse_constant=constant)
    lexemes = {}

    def plain(item, pointer):
        if isinstance(item, _JSONNumber):
            value = json.loads(item.token)
            if type(value) is float and not math.isfinite(value):
                raise ValueError("nonfinite_number")
            lexemes[pointer] = item.token
            return value
        if type(item) is dict:
            for key in item:
                key.encode("utf-8")
            return {key: plain(value, pointer + "/" + _pointer(key)) for key, value in item.items()}
        if type(item) is list:
            return [plain(value, pointer + "/" + str(i)) for i, value in enumerate(item)]
        if type(item) is str:
            item.encode("utf-8")
        return item

    return plain(native, ""), lexemes


def _overview_numbers(value, document, lexemes, diagnostics):
    numbers = []

    def visit(node, path, depth):
        if type(node) is not dict:
            diagnostics.append(_diagnostic(document, "format_incompatible", locations=[_location(document, "overview", pointer=path)]))
            return
        if depth:
            for field, unit in (("subsystem_name_counts", "subsystem_name"), ("gene_counts", "feature_token")):
                pointer = path + "/" + field
                item = node.get(field)
                token = lexemes.get(pointer) if type(item) in (int, float) else (str(item) if item is not None else None)
                number = _number(token, field, _location(document, "overview", field=field, pointer=pointer), unit)
                numbers.append(number)
                for code in number["cell"]["qualification_codes"]:
                    diagnostics.append(_diagnostic(document, code, locations=[number["location"]]))
        if depth < 3:
            for name, child in node.items():
                if name not in ("subsystem_name_counts", "gene_counts"):
                    visit(child, path + "/" + _pointer(name), depth + 1)

    visit(value, "/overview", 0)
    return numbers


def parse_comparative_systems_document(content: bytes, *, document: dict,
                                      format_profile: str, producer_evidence: tuple[dict, ...]) -> dict:
    """Read supplied bytes only, preserving malformed and valid sibling rows.

    Invalid call contracts raise ValueError; invalid artifact contents return a
    typed result with its original byte identity and bounded diagnostics.
    """
    document = validate_shape("SourceDocumentV1", document)
    evidence = [validate_shape("ProducerEvidenceV1", item) for item in producer_evidence]
    if type(content) is not bytes:
        raise ValueError("comparative_systems_bytes_required")
    if format_profile != document["format_profile"] or format_profile not in _PROFILES:
        raise ValueError("comparative_systems_format_profile_mismatch")
    known = _known_producer(document, evidence)
    result = {"version": "bvbrc_comparative_systems_native_v1", "status": "ok", "document": document,
              "tables": [], "metadata": [], "reported_numbers": [], "diagnostics": []}
    diagnostics = result["diagnostics"]
    if len(content) != document["byte_count"] or hashlib.sha256(content).hexdigest() != document["sha256"]:
        diagnostics.append(_diagnostic(document, "byte_identity_mismatch"))
        result["status"] = "invalid"
        return validate_shape("NativeDocumentResultV1", result)
    if not known:
        diagnostics.append(_diagnostic(document, "producer_version_unverified"))
    producing = next((item for item in evidence if item["evidence_id"] == document["producer_evidence_id"]), None)
    if producing is None or producing["reference_release"] is None:
        diagnostics.append(_diagnostic(document, "reference_release_unknown", phase="population"))
    if document["object_complete"] != "complete" or document["transfer_body_complete"] != "complete":
        diagnostics.append(_diagnostic(document, "artifact_truncated"))
    diagnostics.append(_diagnostic(document, "native_query_completeness_unknown", phase="population"))
    if known and ("pathways" in format_profile or "subsystems" in format_profile):
        diagnostics.append(_diagnostic(document, "native_first_object_discard", phase="population"))
    is_json = "_json_" in format_profile
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        diagnostics.append(_diagnostic(document, "outer_json_invalid" if is_json else "format_incompatible"))
        result["status"] = "invalid"
        return validate_shape("NativeDocumentResultV1", result)
    metadata = {}
    if is_json:
        try:
            metadata, lexemes = _json_decode(text)
        except (ValueError, RecursionError) as error:
            code = str(error) if str(error) in ("duplicate_json_key", "nonfinite_number") else "outer_json_invalid"
            diagnostics.append(_diagnostic(document, code))
            result["status"] = "invalid"
            return validate_shape("NativeDocumentResultV1", result)
        if type(metadata) is not dict:
            diagnostics.append(_diagnostic(document, "format_incompatible"))
            result["status"] = "invalid"
            return validate_shape("NativeDocumentResultV1", result)
        table_names = {name for name, _ in _PROFILES[format_profile]}
        for key, value in metadata.items():
            if key not in table_names or type(value) is not str:
                result["metadata"].append({"location": _location(document, pointer="/" + _pointer(key)), "value": value})
        for table, dialect in _PROFILES[format_profile]:
            value = metadata.get(table)
            if type(value) is not str:
                diagnostics.append(_diagnostic(document, "missing_required_field" if table not in metadata else "format_incompatible",
                                               locations=[_location(document, table, pointer="/" + table)]))
                continue
            parsed = _parse_table(value, table, dialect, document, "/" + table, diagnostics, known=known)
            if table in ("plfam", "pgfam"):
                _family_hex(parsed, metadata, document, diagnostics)
            result["tables"].append(parsed)
        if "subsystems" in format_profile:
            if "overview" in metadata:
                result["reported_numbers"].extend(_overview_numbers(metadata["overview"], document, lexemes, diagnostics))
            else:
                diagnostics.append(_diagnostic(document, "missing_required_field"))
        ids, names = metadata.get("genome_ids"), metadata.get("genome_names")
        if type(ids) is not list or any(type(g) is not str or not g.strip() for g in ids):
            diagnostics.append(_diagnostic(document, "identity_conflict", phase="association"))
        elif len(ids) != len(set(ids)):
            diagnostics.append(_diagnostic(document, "identity_conflict", phase="association"))
        if names is not None:
            if type(names) is not list or type(ids) is not list or len(names) != len(ids) or any(type(n) is not str for n in names):
                diagnostics.append(_diagnostic(document, "identity_conflict", phase="association"))
            elif len(names) != len(set(names)):
                diagnostics.append(_diagnostic(document, "genome_name_collision", phase="association"))
        if type(metadata.get("genome_data")) is dict and type(ids) is list:
            if any(type(v) is not list or len(v) != len(ids) for v in metadata["genome_data"].values()):
                diagnostics.append(_diagnostic(document, "identity_conflict", phase="association"))
    else:
        table, dialect = _PROFILES[format_profile][0]
        result["tables"].append(_parse_table(text, table, dialect, document, "", diagnostics, known=known))
    for table in result["tables"]:
        for row in table["rows"]:
            result["reported_numbers"].extend(deepcopy(row["numeric_fields"]))
    if not result["tables"]:
        result["status"] = "invalid"
    elif any(d["code"] not in {"producer_version_unverified", "native_query_completeness_unknown", "no_native_rows", "reference_release_unknown"}
             for d in diagnostics):
        result["status"] = "partial"
    return validate_shape("NativeDocumentResultV1", result)
