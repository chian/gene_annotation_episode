"""Saved Infernal search v2 cells and their non-calculating validation boundary.

Parsers retain source facts; the common calculator alone publishes numerical
components. Validation checks custody and relationships without parsing source
text or calling a calculator. Legacy sheets require an explicit pure upgrade.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Literal, NotRequired, TypedDict

SHEET_SCHEMA = "infernal_search_sheet_v2"
SCORE_SCHEMA = "infernal_search_scores_v2"
SOURCE_PROFILES = ("infernal_tblout", "rfam_single_json", "rfam_batch_tblout", "rfam_batch_report")
CORRESPONDENCE_COUNT_FIELDS = (
    "model_consensus_compared_count", "model_consensus_equal_count", "query_insert_count",
    "model_delete_count", "truncated_model_count_5p", "truncated_model_count_3p",
    "local_end_model_omitted_count", "local_end_query_count")
HIT_COMPONENT_FIELDS = (
    "bitscore", "evalue", "bias_bits", "gc_fraction", "model_from", "model_to",
    "sequence_from", "sequence_to", "consensus_length", "sequence_length",
    "native_rank", "native_alignment_accuracy", "model_span_length", "sequence_span_length",
    "model_span_fraction", "sequence_span_fraction", "display_model_from", "display_model_to",
    "display_query_from", "display_query_to", "represented_model_positions",
    "represented_query_positions", "represented_model_fraction", *CORRESPONDENCE_COUNT_FIELDS,
    "model_consensus_equal_fraction")


class LengthCell(TypedDict):
    native: int | None
    supplied: int | None
    value: int | None
    status: str
    provenance: dict


class SourceDescriptor(TypedDict):
    profile: str
    source_ref: str | None
    artifact_ref: str | None
    source_sha256: str | None
    source_byte_length: int | None
    byte_hash_verified: bool


class TableSourceLocator(TypedDict):
    kind: NotRequired[Literal["tblout"]]
    artifact_id: str
    artifact_index: int
    line: int


class JsonSourceLocator(TypedDict):
    kind: Literal["json"]
    artifact_id: str
    artifact_index: int
    json_pointer: str


class ReportSourceLocator(TypedDict):
    kind: Literal["report"]
    artifact_id: str
    artifact_index: int
    line: int


SourceLocator = TableSourceLocator | JsonSourceLocator | ReportSourceLocator


class Correspondence(TypedDict):
    status: Literal["complete", "partial", "invalid", "unsupported"]
    display_model_from: int | None
    display_model_to: int | None
    display_query_from: int | None
    display_query_to: int | None
    segments: list[dict]
    paired_positions: list[dict]
    aligned_model_intervals: list[list[int]]
    aligned_query_intervals: list[list[int]]
    posterior_segments: list[dict]
    model_consensus_compared_count: int | None
    model_consensus_equal_count: int | None
    query_insert_count: int | None
    model_delete_count: int | None
    truncated_model_count_5p: int | None
    truncated_model_count_3p: int | None
    local_end_model_omitted_count: int | None
    local_end_query_count: int | None
    blocks: list[dict]
    issues: list[dict]
    source_refs: NotRequired[list[dict]]


class SequencePopulation(TypedDict):
    sequence_identity: dict
    query_occurrence_key: str | None
    native_name: str | None
    length: LengthCell
    declared_strands: list[Literal["+", "-"]]
    reported_set_complete: bool
    reported_row_count: int | None
    source_locators: list[SourceLocator]
    membership_basis: Literal["frozen_complete_input", "native_report", "both", "native_query_list"]
    issues: list[dict]


SOURCE_CONTEXT_FIELDS = {
    "infernal_tblout": {"profile"},
    "rfam_single_json": {"profile", "capture", "input_identity", "job", "format_metadata", "population", "supplied_model_metadata"},
    "rfam_batch_tblout": {"profile", "capture", "input_identity", "supplied_model_metadata", "occurrence_bindings", "query_population", "report_membership"},
    "rfam_batch_report": {"profile", "capture", "input_identity", "membership", "population_complete"},
}
SOURCE_DETAILS_FIELDS = {
    "infernal_tblout": {"profile", "missing", "issues", "source_locators"},
    "rfam_single_json": {"profile", "missing", "issues", "native_json_pointer", "document_ordinal", "family_list_ordinal",
        "family_name", "identity_valid", "query_coordinates_valid", "alignment_identity", "raw_row", "raw_row_digest",
        "model_metadata_ref", "source_locators"},
    "rfam_batch_report": {"profile", "missing", "issues", "native_query_name", "query_header_line", "score_line",
        "alignment_header_line", "alignment_summary_line", "raw_cells", "source_lines", "source_locators"},
    "rfam_batch_tblout": {"profile", "missing", "issues", "source_locators"},
}


def finite_copy(value):
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("infernal_finite_json_required") from error
    return deepcopy(value)


def sheet_digest(value):
    """Canonical saved-cell digest; does not read files or source text."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _require(condition, code="infernal_search_sheet_invalid"):
    if not condition:
        raise ValueError(code)


def _int(value, minimum=0):
    return type(value) is int and value >= minimum


def _text(value):
    return isinstance(value, str) and bool(value)


def _closed(value, required, optional=()):
    _require(isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional))


def _identity(identity, metadata):
    _require(isinstance(identity, dict))
    if identity.get("kind") == "supplied_sequence_metadata":
        _closed(identity, ("kind", "metadata_index"))
        _require(_int(identity["metadata_index"]) and identity["metadata_index"] < len(metadata or []))
    else:
        _closed(identity, ("kind", "artifact_index", "list_index"))
        _require(identity["kind"] == "native_query_list" and _int(identity["artifact_index"]) and _int(identity["list_index"]))


def _locator(locator, artifacts, *, legacy=False):
    _require(isinstance(locator, dict))
    kind = locator.get("kind", "tblout" if legacy else None)
    _require(kind in ("tblout", "json", "report"))
    field = "json_pointer" if kind == "json" else "line"
    _closed(locator, ("artifact_id", "artifact_index", field), ("kind",))
    index = locator["artifact_index"]
    _require(_int(index) and index < len(artifacts) and locator["artifact_id"] == artifacts[index].get("artifact_id"))
    _require(_text(locator[field]) and locator[field].startswith("/") if kind == "json" else _int(locator[field], 1))


def _length_cell(value):
    _closed(value, LengthCell.__annotations__)
    _require(isinstance(value["status"], str) and isinstance(value["provenance"], dict))
    for key in ("native", "supplied", "value"):
        _require(value[key] is None or _int(value[key], 1))
    if value["status"] == "validated":
        _require(_int(value["value"], 1) and all(value[k] in (None, value["value"]) for k in ("native", "supplied")))
    else:
        _require(value["value"] is None)


def _interval(value):
    _require(type(value) is list and len(value) == 2 and _int(value[0]) and _int(value[1], value[0] + 1))


def _correspondence(value):
    fields = {"status", "display_model_from", "display_model_to", "display_query_from", "display_query_to",
              "segments", "paired_positions", "aligned_model_intervals", "aligned_query_intervals", "posterior_segments",
              "blocks", "issues", *CORRESPONDENCE_COUNT_FIELDS}
    _closed(value, fields, ("source_refs",))
    _require(value["status"] in ("complete", "partial", "invalid", "unsupported"))
    for field in CORRESPONDENCE_COUNT_FIELDS:
        _require(value[field] is None or _int(value[field]))
    for field in ("display_model_from", "display_model_to", "display_query_from", "display_query_to"):
        _require(value[field] is None or _int(value[field], 1))
    for field in ("segments", "paired_positions", "posterior_segments", "blocks", "issues"):
        _require(isinstance(value[field], list) and all(isinstance(row, dict) for row in value[field]))
    for field in ("aligned_model_intervals", "aligned_query_intervals"):
        _require(isinstance(value[field], list))
        for interval in value[field]:
            _interval(interval)
    compared, equal = (value[k] for k in CORRESPONDENCE_COUNT_FIELDS[:2])
    _require(equal is None or compared is not None and equal <= compared)
    if value["status"] in ("invalid", "unsupported"):
        _require(all(value[k] is None for k in CORRESPONDENCE_COUNT_FIELDS))
        return
    # These are relationship checks of native traversal cells, not another
    # published calculation. Explicit pairs cannot be replaced by omission text.
    pairs = value["paired_positions"]
    for pair in pairs:
        _closed(pair, ("model_position", "query_position", "consensus_symbol", "query_symbol"))
        _require(_int(pair["model_position"]) and _int(pair["query_position"]))
        _require(all(type(pair[k]) is str and len(pair[k]) == 1 for k in ("consensus_symbol", "query_symbol")))
        for axis in ("model", "query"):
            _require(any(a <= pair[axis + "_position"] < b for a, b in value["aligned_" + axis + "_intervals"]))
    canonical = [(p["consensus_symbol"].upper().replace("T", "U"), p["query_symbol"].upper().replace("T", "U")) for p in pairs]
    determinate = [(a, b) for a, b in canonical if a in "ACGU" and b in "ACGU"]
    _require(compared is None or compared == len(determinate))
    _require(equal is None or equal == sum(a == b for a, b in determinate))
    for segment in value["segments"]:
        _closed(segment, ("kind", "model_interval", "query_interval", "model_text", "query_text",
                          "model_count", "query_count", "correspondence_represented"))
        _require(segment["kind"] in ("match", "query_insertion", "model_deletion", "truncated_model", "local_end"))
        _require(segment["correspondence_represented"] is (segment["kind"] in ("match", "query_insertion", "model_deletion")))
        for axis in ("model", "query"):
            interval = segment[axis + "_interval"]
            _require(_int(segment[axis + "_count"]) and isinstance(segment[axis + "_text"], str))
            if interval is not None:
                _interval(interval)
            _require(segment[axis + "_count"] == (interval[1] - interval[0] if interval is not None else 0))


def _saved_input_links(sheet):
    """Check source-validated occurrence facts without interpreting source grammar."""
    context = sheet["source_context"] or {}
    identity = context.get("input_identity")
    metadata = sheet["sequence_metadata"] or []
    if identity is not None:
        _require(isinstance(identity, dict))
        queries = identity.get("queries") if context["profile"] != "rfam_single_json" else [identity]
        _require(isinstance(queries, list) and len(queries) == len(metadata))
        for query, row in zip(queries, metadata):
            _require(isinstance(query, dict) and isinstance(row, dict))
            _require(row.get("query_occurrence_key") == query.get("query_occurrence_key"))
            _require(row.get("length") == query.get("submitted_length_nt") and row.get("sequence") == query.get("submitted_sequence"))
            _require(row.get("name") == query.get("native_query_name"))
    populations = {sheet_digest(p["sequence_identity"]): p for p in sheet["sequence_populations"]}
    for hit in sheet["hits"]:
        linked = hit["sequence"].get("identity")
        if linked is None:
            _require(hit["attribution"]["sequence"] != "valid")
            continue
        if linked["kind"] == "supplied_sequence_metadata":
            row = metadata[linked["metadata_index"]]
            _require(hit["sequence"]["metadata_join"].get("metadata_index") == linked["metadata_index"])
            _require(hit["sequence"].get("name") == row.get("name"))
            if hit["sequence"].get("accession") is not None and row.get("accession") is not None:
                _require(hit["sequence"]["accession"] == row["accession"])
            if hit["query_occurrence_key"] is not None:
                _require(hit["query_occurrence_key"] == row.get("query_occurrence_key"))
            cell = hit["lengths"]["sequence"]
            if cell["status"] == "validated" and cell["supplied"] is not None:
                _require(cell["supplied"] == row.get("length"))
        if populations:
            population = populations.get(sheet_digest(linked))
            _require(population is not None and hit["query_occurrence_key"] == population["query_occurrence_key"])
        if hit["source_details"]["profile"].startswith("rfam_"):
            # The supported Rfam sources do not bind full searched-model input
            # lengths. An accession-only catalogue row is never that binding.
            _require(hit["model"]["metadata_join"].get("status") != "matched")
            _require(hit["lengths"]["model"]["value"] is None)
    for population in sheet["sequence_populations"]:
        linked = population["sequence_identity"]
        if linked["kind"] == "supplied_sequence_metadata":
            row = metadata[linked["metadata_index"]]
            _require(population["query_occurrence_key"] == row.get("query_occurrence_key"))
            _require(population["native_name"] == row.get("name"))
            cell = population["length"]
            if cell["status"] == "validated" and cell["supplied"] is not None:
                _require(cell["supplied"] == row.get("length"))
        if population["reported_set_complete"]:
            members = [h for h in sheet["hits"] if h["sequence"].get("identity") == linked]
            _require(population["reported_row_count"] == len(members))


def validate_infernal_search_sheet(sheet: dict) -> dict:
    """Validate saved v2 relationships; never upgrade, parse or calculate."""
    finite_copy(sheet)
    if not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("infernal_search_sheet_required")
    _closed(sheet, ("schema", "operation", "artifacts", "hits", "sequence_metadata", "model_metadata",
        "metadata_validation", "issues", "status", "statistical_limitations", "no_hit_meaning",
        "sequence_populations", "source_context", "lineage"), ("publication_inputs",))
    _require(isinstance(sheet["operation"], dict) and isinstance(sheet["operation"].get("settings", {}), dict))
    _require(sheet["operation"].get("program") in (None, "cmsearch", "cmscan"))
    _require(sheet["operation"].get("native_version") is None or isinstance(sheet["operation"]["native_version"], str))
    for key in ("artifacts", "hits", "sequence_populations", "issues", "statistical_limitations"):
        _require(isinstance(sheet[key], list))
    for key in ("sequence_metadata", "model_metadata"):
        _require(sheet[key] is None or isinstance(sheet[key], list))
    context = sheet["source_context"]
    if context is not None:
        _require(isinstance(context, dict) and context.get("profile") in SOURCE_CONTEXT_FIELDS)
        _closed(context, ("profile",), SOURCE_CONTEXT_FIELDS[context["profile"]] - {"profile"})
    lineage = sheet["lineage"]
    if lineage is not None:
        _closed(lineage, ("source_sheet_schema", "source_sheet_digest"))
        _require(_text(lineage["source_sheet_schema"]) and re.fullmatch(r"[0-9a-f]{64}", lineage["source_sheet_digest"]) is not None)
    artifacts = sheet["artifacts"]
    for artifact in artifacts:
        _require(isinstance(artifact, dict))
        descriptor = artifact.get("source_descriptor")
        _closed(descriptor, SourceDescriptor.__annotations__)
        _require(descriptor["profile"] in SOURCE_PROFILES and type(descriptor["byte_hash_verified"]) is bool)
        for field in ("source_ref", "artifact_ref"):
            _require(descriptor[field] is None or _text(descriptor[field]))
        _require(descriptor["source_sha256"] is None or isinstance(descriptor["source_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", descriptor["source_sha256"]) is not None)
        _require(descriptor["source_byte_length"] is None or _int(descriptor["source_byte_length"]))
        if descriptor["byte_hash_verified"]:
            _require(descriptor["source_sha256"] is not None and descriptor["source_byte_length"] is not None)
            content = artifact.get("content")
            _require(isinstance(content, str))
            try:
                original = content.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ValueError("infernal_source_bytes_unavailable") from error
            _require(hashlib.sha256(original).hexdigest() == descriptor["source_sha256"]
                     and len(original) == descriptor["source_byte_length"])
    ids = [hit.get("hit_id") for hit in sheet["hits"] if isinstance(hit, dict)]
    _require(len(ids) == len(sheet["hits"]) and all(_text(i) for i in ids) and len(set(ids)) == len(ids))
    for hit in sheet["hits"]:
        _locator(hit["locator"], artifacts, legacy=True)
        details = hit["source_details"]
        _require(isinstance(details, dict) and details.get("profile") in SOURCE_DETAILS_FIELDS)
        _closed(details, ("profile",), SOURCE_DETAILS_FIELDS[details["profile"]] - {"profile"})
        locator = hit["locator"]
        kind = locator.get("kind", "tblout")
        expected_id = (locator["artifact_id"] + locator["json_pointer"] if kind == "json" else
                       locator["artifact_id"] + "/lines/" + str(locator["line"]) if kind == "report" else
                       json.dumps([locator["artifact_id"], locator["artifact_index"], locator["line"]], separators=(",", ":")))
        _require(hit["hit_id"] == expected_id)
        for field, allowed in (("algorithm", (None, "cm", "hmm")), ("strand", (None, "+", "-")), ("inclusion", (None, "!", "?"))):
            _require(hit.get(field) in allowed)
        attribution = hit["attribution"]
        _closed(attribution, ("sequence", "model", "source_locators"))
        _require(all(attribution[k] in ("valid", "unresolved", "conflict") for k in ("sequence", "model")))
        for locator in attribution["source_locators"]:
            _locator(locator, artifacts, legacy=True)
        for kind in ("sequence", "model"):
            _require(isinstance(hit[kind], dict) and (hit[kind].get("name") is None or _text(hit[kind]["name"])))
            _length_cell(hit["lengths"][kind])
            if hit.get(kind + "_interval") is not None:
                _interval(hit[kind + "_interval"])
                start, end = hit.get(kind + "_from"), hit.get(kind + "_to")
                _require(_int(start, 1) and _int(end, 1))
                _require(hit[kind + "_interval"] == [min(start, end) - 1, max(start, end)])
                if kind == "model":
                    _require(start <= end)
                else:
                    _require(hit["strand"] in ("+", "-") and (start <= end if hit["strand"] == "+" else start >= end))
        identity = hit["sequence"].get("identity")
        if identity is not None:
            _identity(identity, sheet["sequence_metadata"])
        _require(hit["query_occurrence_key"] is None or _text(hit["query_occurrence_key"]))
        _require(type(hit["population_complete"]) is bool)
        duplicate = hit["duplicate_of"]
        if duplicate is not None:
            _require(duplicate in ids and duplicate != hit["hit_id"])
            other = sheet["hits"][ids.index(duplicate)]
            _require(other["locator"]["artifact_index"] == hit["locator"]["artifact_index"])
        if hit["correspondence"] is not None:
            _correspondence(hit["correspondence"])
    seen, occurrence_keys = set(), set()
    for population in sheet["sequence_populations"]:
        _closed(population, SequencePopulation.__annotations__)
        _identity(population["sequence_identity"], sheet["sequence_metadata"])
        key = sheet_digest(population["sequence_identity"])
        _require(key not in seen)
        seen.add(key)
        occurrence = population["query_occurrence_key"]
        _require(occurrence is None or _text(occurrence) and occurrence not in occurrence_keys)
        if occurrence is not None:
            occurrence_keys.add(occurrence)
        _length_cell(population["length"])
        strands = population["declared_strands"]
        _require(isinstance(strands, list) and len(set(strands)) == len(strands) and all(s in ("+", "-") for s in strands))
        _require(type(population["reported_set_complete"]) is bool and (population["reported_row_count"] is None or _int(population["reported_row_count"])))
        _require(population["membership_basis"] in ("frozen_complete_input", "native_report", "both", "native_query_list"))
        for locator in population["source_locators"]:
            _locator(locator, artifacts, legacy=True)
    _saved_input_links(sheet)
    return sheet


def validate_infernal_search_scores(scores: dict, *, sheet: dict) -> dict:
    """Authenticate saved components and links without running arithmetic."""
    validate_infernal_search_sheet(sheet)
    finite_copy(scores)
    code = "infernal_search_scores_invalid"
    _require(isinstance(scores, dict) and scores.get("schema") == SCORE_SCHEMA, code)
    _closed(scores, ("schema", "sheet_digest", "operation", "source_context", "parameters", "hits",
        "sequence_strand_aggregates", "sequence_populations", "unresolved_aggregate_hit_ids", "definitions",
        "statistical_limitations", "search_space", "retained_but_not_combined", "issues", "status"))
    _require(scores.get("sheet_digest") == sheet_digest(sheet), code)
    _require(scores.get("operation") == sheet["operation"] and scores.get("source_context") == sheet["source_context"], code)
    _require(scores.get("parameters") in ({"hit_scope": "reported"}, {"hit_scope": "included"}), code)
    _require(isinstance(scores.get("hits"), list) and len(scores["hits"]) == len(sheet["hits"]), code)
    for row, hit in zip(scores["hits"], sheet["hits"]):
        _closed(row, ("hit_id", "locator", "sequence", "model", "query_occurrence_key", "attribution",
            "algorithm", "strand", "inclusion", "selected_for_aggregate", "components", "attributed_components",
            "population_complete", "duplicate_of", "denominators", "model_interval", "sequence_interval",
            "unavailable_components", "status", "issues"))
        for key in ("hit_id", "locator", "sequence", "model", "algorithm", "strand", "inclusion", "query_occurrence_key", "attribution"):
            _require(row.get(key) == hit.get(key), code)
        for key in ("components", "attributed_components"):
            _require(isinstance(row.get(key), dict) and set(row[key]) == set(HIT_COMPONENT_FIELDS), code)
            _require(all(v is None or type(v) in (int, float) and math.isfinite(v) for v in row[key].values()), code)
        valid = all(hit["attribution"][k] == "valid" for k in ("sequence", "model"))
        _require(row["attributed_components"] == (row["components"] if valid else dict.fromkeys(HIT_COMPONENT_FIELDS)), code)
        unavailable = row.get("unavailable_components")
        # JSON object order may change during canonical artifact persistence.
        # Missing component membership is exact; dictionary insertion order
        # is not part of the numerical or saved-return contract.
        _require(isinstance(unavailable, list) and all(type(k) is str for k in unavailable)
            and len(unavailable) == len(set(unavailable))
            and set(unavailable) == {k for k, v in row["components"].items() if v is None}, code)
        components = row["components"]
        for field in ("bitscore", "evalue", "bias_bits", "gc_fraction", "native_alignment_accuracy"):
            value = hit.get(field)
            usable = type(value) in (int, float) and math.isfinite(value)
            usable = usable and (field not in ("evalue", "gc_fraction", "native_alignment_accuracy") or value >= 0)
            usable = usable and (field not in ("gc_fraction", "native_alignment_accuracy") or value <= 1)
            _require(components[field] == (value if usable else None), code)
        for field in ("native_rank", "model_from", "model_to", "sequence_from", "sequence_to"):
            value = hit.get(field)
            _require(components[field] == (value if _int(value, 1) else None), code)
        for kind, denominator_name in (("model", "consensus_length"), ("sequence", "sequence_length")):
            cell = hit["lengths"][kind]
            expected_length = cell["value"] if cell["status"] == "validated" else None
            _require(components[denominator_name] == row["denominators"][denominator_name] == expected_length, code)
            interval = row[kind + "_interval"]
            _require(interval == hit.get(kind + "_interval"), code)
            length, fraction = components[kind + "_span_length"], components[kind + "_span_fraction"]
            if interval is None:
                _require(length is None and fraction is None, code)
            else:
                _require(length == interval[1] - interval[0], code)
                if expected_length is None:
                    _require(fraction is None, code)
                else:
                    _require(fraction is not None and math.isclose(fraction * expected_length, length, rel_tol=1e-12), code)
        correspondence = hit["correspondence"]
        if correspondence is not None and correspondence["status"] in ("complete", "partial"):
            for field in (*CORRESPONDENCE_COUNT_FIELDS, "display_model_from", "display_model_to", "display_query_from", "display_query_to"):
                _require(components[field] == correspondence[field], code)
            compared, equal = (components[k] for k in CORRESPONDENCE_COUNT_FIELDS[:2])
            ratio = components["model_consensus_equal_fraction"]
            if compared in (None, 0) or equal is None:
                _require(ratio is None, code)
            else:
                _require(ratio is not None and math.isclose(ratio * compared, equal, rel_tol=1e-12), code)
        selection = (True if scores["parameters"]["hit_scope"] == "reported" else
                     hit["inclusion"] == "!" if hit["inclusion"] in ("!", "?") else None)
        _require(row["selected_for_aggregate"] is selection, code)
    ids = {h["hit_id"] for h in sheet["hits"]}
    declarations = {sheet_digest(p["sequence_identity"]): p for p in sheet["sequence_populations"]}
    linked = {sheet_digest(p["sequence_identity"]): p["sequence_identity"] for p in sheet["sequence_populations"]}
    for hit in sheet["hits"]:
        identity = hit["sequence"].get("identity")
        if identity is not None:
            linked.setdefault(sheet_digest(identity), identity)
    expected_strands = []
    for key, identity in linked.items():
        declaration = declarations.get(key)
        strands = list(declaration["declared_strands"]) if declaration else []
        for hit in sheet["hits"]:
            if hit["sequence"].get("identity") == identity and hit["strand"] in ("+", "-") and hit["strand"] not in strands:
                strands.append(hit["strand"])
        expected_strands.extend((identity, strand) for strand in strands)
    _require([(r.get("sequence_identity"), r.get("strand")) for r in scores["sequence_strand_aggregates"]] == expected_strands, code)
    _require([r.get("sequence_identity") for r in scores["sequence_populations"]] == list(linked.values()), code)
    for collection in ("sequence_strand_aggregates", "sequence_populations"):
        _require(isinstance(scores.get(collection), list), code)
        for row in scores[collection]:
            _identity(row["sequence_identity"], sheet["sequence_metadata"])
            _require(row["hit_scope"] == scores["parameters"]["hit_scope"] and set(row["hit_ids"]) <= ids, code)
            expected_id = json.dumps([row["sequence_identity"], row["strand"], row["hit_scope"]], sort_keys=True, separators=(",", ":"))
            _require(row["aggregate_id"] == expected_id, code)
            declaration = declarations.get(sheet_digest(row["sequence_identity"]))
            if declaration:
                _require(row["query_occurrence_key"] == declaration["query_occurrence_key"], code)
            members = [r for r in scores["hits"] if r["sequence"].get("identity") == row["sequence_identity"]
                       and (collection == "sequence_populations" or r["strand"] == row["strand"])]
            selected = [r for r in members if r["selected_for_aggregate"] is True]
            _require(row["hit_ids"] == [r["hit_id"] for r in selected], code)
            denominator_cells = {r["denominators"]["sequence_length"] for r in (selected or members)}
            if declaration is not None:
                declared_length = declaration["length"]
                denominator_cells.add(declared_length["value"] if declared_length["status"] == "validated" else None)
            expected_denominator = next(iter(denominator_cells)) if len(denominator_cells) == 1 and None not in denominator_cells else None
            _require(row["union_denominator"] == expected_denominator, code)
            if row["hit_count"] is not None:
                _require(row["hit_count"] == len(selected), code)
            if row["valid_geometry_count"] is not None:
                valid = [r for r in selected if r["sequence_interval"] is not None and all(
                    r["attribution"][kind] == "valid" for kind in ("sequence", "model"))]
                _require(row["valid_geometry_count"] == len(valid), code)
                _require(row["invalid_geometry_count"] == len(selected) - len(valid), code)
            if declaration and collection == "sequence_populations":
                _require(row["reported_row_count"] == declaration["reported_row_count"], code)
            if row["union_numerator"] is None:
                _require(row["span_sum"] is None and row["overlap_excess"] is None, code)
            else:
                _require(row["span_sum"] >= row["union_numerator"] and row["overlap_excess"] == row["span_sum"] - row["union_numerator"], code)
            if not row["complete_for_selected_population"]:
                _require(row["union_span_fraction"] is None, code)
    return scores


__all__ = ["SHEET_SCHEMA", "SCORE_SCHEMA", "CORRESPONDENCE_COUNT_FIELDS", "HIT_COMPONENT_FIELDS",
           "SequencePopulation", "SourceDescriptor", "SourceLocator", "Correspondence", "LengthCell", "finite_copy", "sheet_digest",
           "validate_infernal_search_sheet", "validate_infernal_search_scores"]
