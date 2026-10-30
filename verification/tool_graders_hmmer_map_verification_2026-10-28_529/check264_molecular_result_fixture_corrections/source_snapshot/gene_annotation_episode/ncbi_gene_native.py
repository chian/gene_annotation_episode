"""Source-faithful Gene XML metadata, without candidate selection or acquisition.

Native XML trees retain source assertions. Child-index paths bind every locus,
commentary and location to that tree; they are not genomic coordinates. No
function inference, sequence extraction, DTD retrieval or numerical score occurs.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import io
import json
import math
import re
import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator


_DECIMAL = re.compile(r"[0-9]+\Z")
_ISSUE_CODES = ("xml_parse_failed", "xml_root_invalid", "response_incomplete",
    "gene_id_missing", "gene_id_ambiguous", "gene_id_invalid", "gene_id_duplicate",
    "requested_gene_missing", "unexpected_gene", "source_identity_malformed")


def _object(properties):
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


_TEXT = {"type": ["string", "null"]}
_TEXTS = {"type": "array", "items": _TEXT}
_PATH = {"type": "array", "items": {"type": "integer", "minimum": 0}}
_TREE_REF = {"$ref": "#/$defs/native_tree"}
_TREE = _object({"tag": {"type": "string"},
    "attributes": {"type": "object", "additionalProperties": {"type": "string"}},
    "text": _TEXT, "tail": _TEXT,
    "children": {"type": "array", "items": _TREE_REF}})
_COMMENTARY = _object({"commentary_ordinal": {"type": "integer", "minimum": 0},
    "path": _PATH, "parent_commentary_path": {"anyOf": [_PATH, {"type": "null"}]},
    "types": {"type": "array", "items": _object({"code": _TEXT, "label": _TEXT})},
    "accession_values": _TEXTS, "version_values": _TEXTS,
    "labels": _TEXTS, "headings": _TEXTS,
    "locations": {"type": "array", "items": _object({"tag": {"type": "string"},
        "path": _PATH, "native": _TREE_REF})}})
_RECORD = _object({"record_ordinal": {"type": "integer", "minimum": 0},
    "gene_id": {"anyOf": [{"type": "string", "pattern": "^[0-9]+$"}, {"type": "null"}]},
    "gene_id_values": _TEXTS, "taxon_ids": _TEXTS, "gene_symbols": _TEXTS,
    "loci": {"type": "array", "items": _object({"locus_ordinal": {"type": "integer", "minimum": 0},
        "path": _PATH, "commentaries": {"type": "array", "items": _COMMENTARY}})},
    "native_record": _TREE_REF})
_SCHEMA = _object({"version": {"const": "ncbi_gene_native_v1"},
    "source_ref": {"type": "string", "minLength": 1},
    "request": _object({"gene_ids": {"anyOf": [{"type": "null"},
        {"type": "array", "minItems": 1, "uniqueItems": True,
         "items": {"type": "string", "pattern": "^[0-9]+$"}}]}}),
    "response_complete": {"type": "boolean"},
    "parse_status": {"enum": ["complete", "partial", "invalid"]},
    "records": {"type": "array", "items": _RECORD},
    "issues": {"type": "array", "items": _object({"code": {"enum": list(_ISSUE_CODES)},
        "record_ordinal": {"type": ["integer", "null"], "minimum": 0},
        "path": {"anyOf": [_PATH, {"type": "null"}]}})}})
_SCHEMA["$defs"] = {"native_tree": _TREE}
NCBI_GENE_NATIVE_SCHEMA = deepcopy(_SCHEMA)
_VALIDATOR = Draft202012Validator(_SCHEMA)


def _require(condition, code):
    if not condition:
        raise ValueError("ncbi_gene_" + code)


def _copy(value):
    def check(node):
        if node is None or type(node) in (str, int, bool):
            return
        if type(node) is float and math.isfinite(node):
            return
        if type(node) is list:
            for child in node:
                check(child)
            return
        if type(node) is dict and all(type(key) is str for key in node):
            for child in node.values():
                check(child)
            return
        raise ValueError("ncbi_gene_finite_json_required")
    try:
        check(value)
        return deepcopy(value)
    except RecursionError as error:
        raise ValueError("ncbi_gene_finite_json_required") from error


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _tree(element):
    return {"tag": element.tag, "attributes": dict(element.attrib),
        "text": element.text, "tail": element.tail,
        "children": [_tree(child) for child in element]}


def _children(node, tag):
    return [(i, child) for i, child in enumerate(node["children"]) if _local(child["tag"]) == tag]


def _at(node, tags):
    selected = [node]
    for tag in tags:
        selected = [child for parent in selected for _, child in _children(parent, tag)]
    return selected


def _texts(node, tag):
    return [child["text"] for _, child in _children(node, tag)]


def _commentaries(node, path):
    result = []
    def visit(current, current_path, parent_path):
        next_parent = parent_path
        if _local(current["tag"]) == "Gene-commentary":
            result.append({"commentary_ordinal": len(result), "path": list(current_path),
                "parent_commentary_path": None if parent_path is None else list(parent_path),
                "types": [{"code": child["text"], "label": child["attributes"].get("value")}
                    for _, child in _children(current, "Gene-commentary_type")],
                "accession_values": _texts(current, "Gene-commentary_accession"),
                "version_values": _texts(current, "Gene-commentary_version"),
                "labels": _texts(current, "Gene-commentary_label"),
                "headings": _texts(current, "Gene-commentary_heading"),
                "locations": [{"tag": child["tag"], "path": [*current_path, i], "native": deepcopy(child)}
                    for i, child in enumerate(current["children"]) if _local(child["tag"]) in
                    ("Gene-commentary_genomic-coords", "Gene-commentary_seqs")]})
            next_parent = current_path
        for i, child in enumerate(current["children"]):
            visit(child, [*current_path, i], next_parent)
    visit(node, path, None)
    return result


def _record(native, ordinal):
    values = [node["text"] for node in _at(native,
        ("Entrezgene_track-info", "Gene-track", "Gene-track_geneid"))]
    gene_id = values[0] if len(values) == 1 and type(values[0]) is str and _DECIMAL.fullmatch(values[0]) else None
    taxa = []
    for tag in _at(native, ("Entrezgene_source", "BioSource", "BioSource_org", "Org-ref", "Org-ref_db", "Dbtag")):
        if _texts(tag, "Dbtag_db") == ["taxon"]:
            taxa.extend(node["text"] for object_id in _at(tag, ("Dbtag_tag", "Object-id"))
                for node in object_id["children"] if _local(node["tag"]) in ("Object-id_id", "Object-id_str"))
    loci = []
    for wrapper_index, wrapper in _children(native, "Entrezgene_locus"):
        for i, child in _children(wrapper, "Gene-commentary"):
            path = [wrapper_index, i]
            loci.append({"locus_ordinal": len(loci), "path": path,
                "commentaries": _commentaries(child, path)})
    return {"record_ordinal": ordinal, "gene_id": gene_id, "gene_id_values": values,
        "taxon_ids": taxa, "gene_symbols": [node["text"] for node in _at(native,
            ("Entrezgene_gene", "Gene-ref", "Gene-ref_locus"))],
        "loci": loci, "native_record": deepcopy(native)}


def _identity_issues(records, requested):
    issues = []
    def issue(code, ordinal=None):
        issues.append({"code": code, "record_ordinal": ordinal, "path": None})
    seen = Counter(row["gene_id"] for row in records if row["gene_id"] is not None)
    for row in records:
        values, gene = row["gene_id_values"], row["gene_id"]
        if not values:
            issue("gene_id_missing", row["record_ordinal"])
        elif len(values) > 1:
            issue("gene_id_ambiguous", row["record_ordinal"])
        elif gene is None:
            issue("gene_id_invalid", row["record_ordinal"])
        if gene is not None and seen[gene] > 1:
            issue("gene_id_duplicate", row["record_ordinal"])
        if requested is not None and gene is not None and gene not in requested:
            issue("unexpected_gene", row["record_ordinal"])
    if requested is not None:
        for gene in requested:
            if gene not in seen:
                issue("requested_gene_missing")
    return issues


def _status(records, issues):
    if any(row["code"] == "xml_root_invalid" for row in issues):
        return "invalid"
    if any(row["code"] == "xml_parse_failed" for row in issues) and not records:
        return "invalid"
    return "partial" if issues else "complete"


def validate_ncbi_gene_native(value):
    """Check closed types and every projection against its retained native tree."""
    saved = _copy(value)
    _require(_VALIDATOR.is_valid(saved), "native_schema_invalid")
    requested = saved["request"]["gene_ids"]
    _require(requested is None or all(_DECIMAL.fullmatch(gene) for gene in requested),
        "requested_gene_ids_invalid")
    expected_issues = _identity_issues(saved["records"], saved["request"]["gene_ids"])
    for ordinal, row in enumerate(saved["records"]):
        _require(_local(row["native_record"]["tag"]) == "Entrezgene", "native_record_tag_invalid")
        _require(_same(row, _record(row["native_record"], ordinal)), "native_projection_conflict")
    structural = [row for row in saved["issues"] if row["code"] in
        ("xml_parse_failed", "xml_root_invalid", "response_incomplete", "source_identity_malformed")]
    for issue in structural:
        _require(issue["record_ordinal"] is None and issue["path"] is None, "issue_relationship_invalid")
    _require(len({row["code"] for row in structural}) == len(structural), "issue_relationship_invalid")
    _require((not saved["response_complete"]) == any(row["code"] == "response_incomplete" for row in structural),
        "response_completeness_conflict")
    _require(_same(saved["issues"], [*structural, *expected_issues]), "issue_relationship_invalid")
    _require(saved["parse_status"] == _status(saved["records"], saved["issues"]), "parse_status_conflict")
    _require(not any(row["code"] == "xml_root_invalid" for row in structural) or not saved["records"],
        "root_record_conflict")
    return saved


def read_ncbi_gene_xml(content: bytes, *, source_ref: str,
        requested_gene_ids: list[str] | None, response_complete: bool) -> dict:
    """Read complete source records, retaining partial work after XML failure."""
    _require(type(content) is bytes, "content_bytes_required")
    _require(type(source_ref) is str and bool(source_ref), "source_ref_required")
    _require(type(response_complete) is bool, "response_complete_required")
    _require(requested_gene_ids is None or type(requested_gene_ids) is list
        and bool(requested_gene_ids) and all(type(gene) is str and _DECIMAL.fullmatch(gene)
            for gene in requested_gene_ids) and len(set(requested_gene_ids)) == len(requested_gene_ids),
        "requested_gene_ids_invalid")
    closed_records, issues, stack, root_tag = [], [], [], None
    def issue(code):
        if not any(row["code"] == code for row in issues):
            issues.append({"code": code, "record_ordinal": None, "path": None})
    try:
        for event, element in ET.iterparse(io.BytesIO(content), events=("start", "end")):
            if event == "start":
                stack.append(element)
                if root_tag is None:
                    root_tag = _local(element.tag)
                    if root_tag not in ("Entrezgene-Set", "Entrezgene"):
                        issue("xml_root_invalid")
                continue
            depth = len(stack)
            if root_tag == "Entrezgene-Set" and depth == 2:
                if _local(element.tag) == "Entrezgene":
                    closed_records.append(element)
                else:
                    issue("source_identity_malformed")
            elif root_tag == "Entrezgene" and depth == 1:
                closed_records.append(element)
            stack.pop()
    except (ET.ParseError, UnicodeError, ValueError, LookupError):
        issue("xml_parse_failed")
    # A record's trailing text can arrive after its end event. Project only
    # after parsing stops, while retaining every earlier fully closed record.
    records = [_record(_tree(element), ordinal)
        for ordinal, element in enumerate(closed_records)]
    if not response_complete:
        issue("response_incomplete")
    issues.extend(_identity_issues(records, requested_gene_ids))
    result = {"version": "ncbi_gene_native_v1", "source_ref": source_ref,
        "request": {"gene_ids": deepcopy(requested_gene_ids)},
        "response_complete": response_complete, "parse_status": _status(records, issues),
        "records": records, "issues": issues}
    return validate_ncbi_gene_native(result)


__all__ = ["NCBI_GENE_NATIVE_SCHEMA", "read_ncbi_gene_xml", "validate_ncbi_gene_native"]
