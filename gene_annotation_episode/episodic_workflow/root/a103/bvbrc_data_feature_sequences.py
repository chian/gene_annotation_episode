"""Pure feature-to-sequence associations from explicitly supplied BV-BRC sheets.

This extractor does not fetch, inspect files, execute work, or calculate the
separate acquisition components. Source strings stay in the supplied DataSheets;
the returned frozen sheet links their exact cells. Every feature occurrence has
its own edge, including when distinct annotations share a sequence hash.

``sequence_length`` is the character count of the exact supplied string, only
when every candidate supplies the same length. ``feature_length`` is the native
nonnegative integer aa_length/na_length. No genomic-span or translation estimate
fills either value. MD5 checks use exact ASCII bytes, including case/whitespace.
The nullable MD5 flag is consensus over *all* candidates. Length agreement
requires an unambiguous sequence length and a reported feature length;
unavailable or disagreeing lengths cannot be represented by a chosen first row.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from .bvbrc_data_fields import FIELD_REGISTRY
from .bvbrc_data_schema import schema, validate

__all__ = (
    "extract_feature_sequence_join",
    "FEATURE_SEQUENCE_SHEET_SCHEMA",
    "FEATURE_SEQUENCE_COMPONENTS_SCHEMA",
)

FEATURE_SEQUENCE_SHEET_SCHEMA = schema("FeatureSequenceSheet")
FEATURE_SEQUENCE_COMPONENTS_SCHEMA = schema("FeatureSequenceComponents")
_MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def _invalid(detail: str) -> None:
    raise ValueError("bvbrc_feature_sequence_input_invalid:" + detail)


def _pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _unique(items: list[dict]) -> list[dict]:
    result, seen = [], set()
    for item in items:
        key = json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _check_atom(atom: dict, cell: dict) -> None:
    kind = atom["kind"]
    expected = {"string": "string_value", "number": "number_value",
                "boolean": "boolean_value", "null": None}[kind]
    for key in ("string_value", "number_value", "boolean_value"):
        if key != expected and atom[key] is not None:
            _invalid("atom_kind_value")
    if kind in ("string", "boolean") and atom[expected] is None:
        _invalid("atom_missing_value")
    if kind != "number":
        if atom["number_lexeme"] is not None:
            _invalid("atom_number_lexeme")
        return
    lexeme = atom["number_lexeme"]
    if lexeme is None or not _NUMBER.fullmatch(lexeme):
        _invalid("atom_number_lexeme")
    try:
        exact = Decimal(lexeme)
    except InvalidOperation:
        _invalid("atom_number_lexeme")
    if not exact.is_finite():
        _invalid("atom_number_lexeme")
    value = atom["number_value"]
    if value is None:
        if "bvbrc_unrepresentable_numeric_value" not in cell["issue_codes"]:
            _invalid("unqualified_unrepresentable_atom")
    elif type(value) is int:
        if exact != value:
            _invalid("atom_number_value")
    elif float(exact) != value or (exact != 0 and value == 0):
        _invalid("atom_number_value")


def _check_cell(cell: dict, row: dict, fields: dict) -> None:
    field = cell["field"]
    if cell["cell_key"] != row["row_key"] + "/field/" + _pointer(field):
        _invalid("cell_key")
    if cell["native_path"] != row["native_path"] + "/" + _pointer(field):
        _invalid("cell_native_path")
    presence, shape, atoms = cell["presence"], cell["native_shape"], cell["atoms"]
    if presence != "present":
        expected_shape = "null" if presence == "null" else "absent"
        expected_status = "unselected" if presence == "unselected" else "missing"
        if atoms or shape != expected_shape or cell["status"] != expected_status:
            _invalid("absent_cell_shape")
    elif shape == "scalar":
        if len(atoms) != 1:
            _invalid("scalar_cell_cardinality")
    elif shape == "object":
        if atoms or cell["status"] != "invalid":
            _invalid("object_cell_shape")
    elif shape != "array":
        _invalid("present_cell_shape")
    if presence == "present" and cell["status"] in ("missing", "unselected"):
        _invalid("present_cell_status")
    for atom in atoms:
        _check_atom(atom, cell)
    # Invalid native values may be retained, but cannot claim a valid typed cell.
    if presence == "present" and cell["status"] == "valid":
        specification = fields[field]
        expected_shape = "array" if specification["multi_valued"] else "scalar"
        if shape != expected_shape:
            _invalid("valid_cell_cardinality")
        native_type = specification["solr_type"]
        for atom in atoms:
            if native_type in ("int", "long"):
                correct = atom["kind"] == "number" and type(atom["number_value"]) is int
            elif native_type == "float":
                correct = atom["kind"] == "number" and atom["number_value"] is not None
            elif native_type == "boolean":
                correct = atom["kind"] == "boolean"
            else:
                correct = atom["kind"] == "string"
            if not correct:
                _invalid("valid_cell_native_type")


def _scalar(row: dict, field: str, kind: str) -> tuple[object | None, str | None]:
    cell = next((cell for cell in row["cells"] if cell["field"] == field), None)
    if cell is None or cell["presence"] == "unselected":
        return None, "not_selected"
    if cell["presence"] == "absent":
        return None, "native_field_absent"
    if cell["presence"] == "null":
        return None, "native_null"
    if cell["status"] == "unrepresentable":
        return None, "unrepresentable_numeric_value"
    if (cell["status"] != "valid" or cell["native_shape"] != "scalar"
            or cell["atoms"][0]["kind"] != kind):
        return None, "native_value_invalid"
    return cell["atoms"][0][kind + "_value"], None


def _check_page(value: dict, collection: str) -> dict:
    page = validate("DataSheet", value)
    if page["collection"] != collection or page["mode"] != "page" or page["page"]["mode"] != "page":
        _invalid("incompatible_collection_or_mode")
    fields = FIELD_REGISTRY[collection]["fields"]
    if any(field not in fields or not fields[field]["stored"] for field in page["selected_fields"]):
        _invalid("collection_field")
    rows, counts = page["rows"], page["page"]
    valid_count = sum(row["status"] == "valid" for row in rows)
    if (counts["returned_row_count"] != len(rows) or counts["valid_row_count"] != valid_count
            or counts["invalid_row_count"] != len(rows) - valid_count):
        _invalid("page_row_counts")
    digest = page["custody"]["native_sha256"]
    prefix = "/response/docs/" if page["custody"]["native_profile"] == "solr_json_envelope_v1" else "/"
    identity_field = FIELD_REGISTRY[collection]["unique_key"]
    for index, row in enumerate(rows):
        if (row["row_index"] != index or row["row_key"] != digest + "/row/" + str(index)
                or row["native_path"] != prefix + str(index)):
            _invalid("row_locator")
        if [cell["field"] for cell in row["cells"]] != page["selected_fields"]:
            _invalid("selected_cell_order_or_membership")
        cells = {cell["field"]: cell for cell in row["cells"]}
        for cell in row["cells"]:
            _check_cell(cell, row, fields)
        identity, _ = _scalar(row, identity_field, "string")
        # D2 retains a native empty string cell but does not confer an identity
        # on it. Do not coerce whitespace or any other nonempty identifier.
        identity = identity or None
        if row["native_id"] != identity:
            _invalid("native_identity")
        if row["status"] == "valid" and (identity is None or any(
                cell["status"] in ("invalid", "unrepresentable") for cell in row["cells"])):
            _invalid("valid_row_status")
        if [cell["field"] for cell in row["numerical_cells"]] != [
                field for field in page["selected_fields"] if fields[field]["numeric_projection"]]:
            _invalid("selected_numerical_cell_order_or_membership")
        numeric_fields = set()
        for numeric in row["numerical_cells"]:
            field = numeric["field"]
            if field not in cells or field in numeric_fields or not fields[field]["numeric_projection"]:
                _invalid("numerical_cell_membership")
            numeric_fields.add(field)
            if (numeric["cell_key"] != cells[field]["cell_key"]
                    or numeric["native_path"] != cells[field]["native_path"]):
                _invalid("numerical_cell_locator")
            if numeric["status"] == "reported":
                native_value, reason = _scalar(row, field, "number")
                if reason is not None or native_value != numeric["value"]:
                    _invalid("numerical_cell_value")
            elif numeric["status"] != "parsed_numeric_text" and numeric["value"] is not None:
                _invalid("unavailable_numerical_cell_value")
    return page


def _pages(values: list[dict], collection: str) -> list[dict]:
    if type(values) is not list:
        _invalid("pages_must_be_list")
    pages: dict[str, dict] = {}
    for value in values:
        page = _check_page(value, collection)
        digest = page["custody"]["native_sha256"]
        if digest not in pages:
            pages[digest] = page
            continue
        previous = pages[digest]
        if len(previous["rows"]) != len(page["rows"]):
            _invalid("conflicting_repeated_page")
        # Reprojection of the same bytes can select different fields. Merge
        # compatible projections by exact locator; no representation gains a row.
        selected = list(dict.fromkeys(previous["selected_fields"] + page["selected_fields"]))
        for old, new in zip(previous["rows"], page["rows"]):
            if any(old[key] != new[key] for key in ("row_key", "row_index", "native_path", "native_id")):
                _invalid("conflicting_repeated_page")
            for key in ("cells", "numerical_cells"):
                by_field = {cell["field"]: cell for cell in old[key]}
                for cell in new[key]:
                    if cell["field"] in by_field and cell != by_field[cell["field"]]:
                        _invalid("conflicting_repeated_cell")
                    by_field[cell["field"]] = cell
                old[key] = [by_field[field] for field in selected if field in by_field]
            old["issues"] = _unique(old["issues"] + new["issues"])
            if new["status"] != "valid":
                old["status"] = "invalid" if "invalid" in (old["status"], new["status"]) else "partial"
        previous["selected_fields"] = selected
        previous["issues"] = _unique(previous["issues"] + page["issues"])
    return list(pages.values())


def _row_location(page: dict, row: dict) -> dict:
    return {"native_sha256": page["custody"]["native_sha256"],
            "collection": page["collection"], "row_key": row["row_key"]}


def _cell_location(page: dict, row: dict, cell: dict, level: str) -> dict:
    return {**_row_location(page, row), "cell_key": cell["cell_key"],
            "field": cell["field"], "source_level": level}


def _issue(code: str, row: dict | None = None, field: str | None = None) -> dict:
    return {"code": code, "phase": "join", "row_index": None if row is None else row["row_index"],
            "field": field, "native_path": None if row is None else row["native_path"]
            + ("/" + _pointer(field) if field is not None else ""), "http_status": None}


def _requirement(collection: str, field: str, value: str, kind: str | None, reason: str) -> dict:
    return {"collection": collection, "field": field, "values": [value],
            "sequence_kind": kind, "reason": reason}


def _consensus(values: list) -> object | None:
    if not values or any(value is None for value in values):
        return None
    return values[0] if all(value == values[0] for value in values) else None


def _base_edge(feature_id: str, kind: str, key: str) -> dict:
    return {"edge_key": key, "feature_id": feature_id, "feature_rows": [],
            "sequence_kind": kind, "native_md5": None, "sequence_rows": [],
            "sequence_cells": [], "feature_metadata_cells": [], "sequence_length": None,
            "feature_length": None, "raw_md5_match": None, "length_match": None,
            "join_status": "missing_feature", "reason": "missing_feature_record", "issues": []}


def _feature_conflicts(occurrences: list[tuple[dict, dict]], kind: str) -> set[str]:
    # Unknown cells are not contradictions. AA and NA remain independent modes.
    opposite = "na" if kind == "AA" else "aa"
    excluded = {opposite + "_length", opposite + "_sequence_md5"}
    observed: dict[str, set[str]] = {}
    for _, row in occurrences:
        for cell in row["cells"]:
            if cell["presence"] == "present" and cell["field"] not in excluded:
                signature = json.dumps([cell["native_shape"], cell["atoms"]], sort_keys=True)
                observed.setdefault(cell["field"], set()).add(signature)
    return {field for field, values in observed.items() if len(values) > 1}


def _edge(page: dict, row: dict, feature_id: str, kind: str,
          candidates_by_md5: dict, have_sequence_pages: bool,
          conflicts: set[str]) -> tuple[dict, list[dict]]:
    hash_field, length_field = kind.lower() + "_sequence_md5", kind.lower() + "_length"
    result = _base_edge(feature_id, kind, row["row_key"] + "/" + kind)
    result["feature_rows"] = [_row_location(page, row)]
    # All explicitly selected source cells remain available to a later, smaller
    # caller-owned projection; this does not put those values into a prompt.
    result["feature_metadata_cells"] = [
        _cell_location(page, row, cell, "feature") for cell in row["cells"]
        if cell["presence"] in ("present", "null")
    ]
    result["issues"] = deepcopy(row["issues"])
    native_md5, hash_reason = _scalar(row, hash_field, "string")
    result["native_md5"] = native_md5
    length, length_reason = _scalar(row, length_field, "number")
    invalid_length = length_reason in ("native_value_invalid", "unrepresentable_numeric_value")
    if length_reason is None and (type(length) is not int or length < 0):
        invalid_length, length_reason, length = True, "native_value_invalid", None
    result["feature_length"] = length
    requirements = []
    if length_reason is not None:
        result["issues"].append(_issue("bvbrc_invalid_native_field" if invalid_length
                                      else "bvbrc_input_unavailable", row, length_field))
        requirements.append(_requirement("genome_feature", "feature_id", feature_id, kind, length_reason))
    if hash_reason is not None:
        invalid_hash = hash_reason in ("native_value_invalid", "unrepresentable_numeric_value")
        result.update(join_status="conflict" if invalid_hash else "missing_key", reason=hash_reason)
        result["issues"].append(_issue("bvbrc_invalid_native_field" if invalid_hash
                                      else "bvbrc_input_unavailable", row, hash_field))
        requirements.append(_requirement("genome_feature", "feature_id", feature_id, kind, hash_reason))
    else:
        invalid_hash = _MD5.fullmatch(native_md5) is None
        candidates = candidates_by_md5.get(native_md5, [])
        result["sequence_rows"] = [_row_location(p, r) for p, r in candidates]
        result["sequence_cells"] = [_cell_location(p, r, cell, "sequence")
                                    for p, r in candidates for cell in r["cells"]
                                    if cell["field"] == "sequence"]
        strings, types, lengths, hash_matches, unavailable = [], [], [], [], []
        for _, candidate in candidates:
            result["issues"].extend(deepcopy(candidate["issues"]))
            text, text_reason = _scalar(candidate, "sequence", "string")
            native_kind, type_reason = _scalar(candidate, "sequence_type", "string")
            strings.append(text)
            types.append(native_kind)
            lengths.append(None if text is None else len(text))
            matches = None
            if text is not None:
                try:
                    matches = hashlib.md5(text.encode("ascii")).hexdigest() == native_md5
                except UnicodeEncodeError:
                    text_reason = "native_value_invalid"
                if matches is False:
                    result["issues"].append(_issue("bvbrc_native_md5_mismatch", candidate, "sequence"))
            hash_matches.append(matches)
            if text_reason is not None:
                unavailable.append(text_reason)
                result["issues"].append(_issue("bvbrc_input_unavailable" if text is None
                                              else "bvbrc_invalid_native_field", candidate, "sequence"))
            if type_reason is not None:
                unavailable.append(type_reason)
                result["issues"].append(_issue("bvbrc_input_unavailable", candidate, "sequence_type"))
            elif native_kind != kind:
                result["issues"].append(_issue("bvbrc_join_conflict", candidate, "sequence_type"))
            if text is not None and length is not None and len(text) != length:
                result["issues"].append(_issue("bvbrc_native_length_mismatch", row, length_field))
        result["sequence_length"] = _consensus(lengths)
        result["raw_md5_match"] = _consensus(hash_matches)
        if length is not None:
            if result["sequence_length"] is not None:
                result["length_match"] = result["sequence_length"] == length
            if any(size is not None and size != length for size in lengths):
                requirements.append(_requirement("genome_feature", "feature_id", feature_id, kind,
                                                 "conflicting_metadata"))
        if invalid_hash:
            result.update(join_status="conflict", reason="native_value_invalid")
            result["issues"].append(_issue("bvbrc_invalid_native_field", row, hash_field))
            requirements.append(_requirement("genome_feature", "feature_id", feature_id, kind,
                                             "native_value_invalid"))
        elif not candidates:
            reason = "missing_sequence_record" if have_sequence_pages else "missing_input_page"
            result.update(join_status="missing_record", reason=reason)
            result["issues"].append(_issue("bvbrc_input_unavailable", row, hash_field))
            requirements.append(_requirement("feature_sequence", "md5", native_md5, kind, reason))
        elif len(set(strings)) > 1 or len(set(types)) > 1:
            result.update(join_status="conflict", reason="ambiguous_join")
            result["issues"].append(_issue("bvbrc_join_conflict", row, hash_field))
        elif all(text is None for text in strings):
            result.update(join_status="missing_sequence", reason="sequence_text_unavailable")
        elif unavailable:
            # A common unavailable reason is precise; different unavailable
            # causes remain in their requirements without first-row precedence.
            result.update(join_status="conflict", reason=_consensus(unavailable) or "ambiguous_join")
        elif types[0] != kind:
            result.update(join_status="type_mismatch", reason="sequence_type_mismatch")
            result["issues"].append(_issue("bvbrc_join_conflict", row, hash_field))
        elif result["raw_md5_match"] is not True or result["length_match"] is False or invalid_length:
            result.update(join_status="conflict", reason="native_value_invalid" if invalid_length
                          or result["raw_md5_match"] is not True else "conflicting_metadata")
        else:
            result.update(join_status="repeated_identical" if len(candidates) > 1 else "joined", reason=None)
        sequence_problem = candidates and (len(set(strings)) > 1 or len(set(types)) > 1
            or unavailable or types[0] != kind or result["raw_md5_match"] is not True)
        if sequence_problem and not invalid_hash:
            reasons = list(dict.fromkeys(unavailable)) or [result["reason"]]
            requirements.extend(_requirement("feature_sequence", "md5", native_md5, kind, reason)
                                for reason in reasons)
    if conflicts:
        result.update(join_status="conflict", reason="conflicting_metadata")
        result["issues"].extend(_issue("bvbrc_join_conflict", row, field) for field in sorted(conflicts))
        requirements.append(_requirement("genome_feature", "feature_id", feature_id, kind, "conflicting_metadata"))
    result["issues"] = _unique(result["issues"])
    return result, requirements


def extract_feature_sequence_join(feature_pages: list[dict], sequence_pages: list[dict], *,
                                  feature_ids: list[str], sequence_kind: str) -> dict:
    """Return the frozen FeatureSequenceSheet for exactly these supplied inputs.

    Malformed/contradictory sheet structures raise ValueError. Meaningful native
    missingness and conflicting candidates remain typed results with acquisition
    requirements, never automatic queries. Identical delivery and compatible
    reprojection of one (native_sha256, collection) count once. Distinct retained
    native rows, including identical sequence rows, keep separate source locators.
    """
    result = validate("FeatureSequenceSheet", {
        "version": "bvbrc_feature_sequence_sheet_v1",
        "selection": {"feature_ids": feature_ids, "sequence_kind": sequence_kind},
        "input_native_sha256s": [], "input_page_counts": [], "edges": [], "requirements": [], "issues": [],
    })
    feature_pages = _pages(feature_pages, "genome_feature")
    sequence_pages = _pages(sequence_pages, "feature_sequence")
    all_pages = feature_pages + sequence_pages
    result["input_native_sha256s"] = list(dict.fromkeys(page["custody"]["native_sha256"] for page in all_pages))
    result["input_page_counts"] = [
        {"native_sha256": page["custody"]["native_sha256"], "collection": page["collection"],
         "retained_row_count": len(page["rows"]),
         "valid_row_count": sum(row["status"] == "valid" for row in page["rows"])}
        for page in all_pages
    ]
    result["issues"] = [deepcopy(issue) for page in all_pages for issue in _unique(
        page["issues"] + [i for row in page["rows"] for i in row["issues"]])]
    features, sequences = {}, {}
    for pages, index, field in ((feature_pages, features, "feature_id"), (sequence_pages, sequences, "md5")):
        for page in pages:
            for row in page["rows"]:
                value, reason = _scalar(row, field, "string")
                if reason is None and row["native_id"] is not None:
                    index.setdefault(value, []).append((page, row))
    kinds = ("AA", "NA") if sequence_kind == "both" else (sequence_kind,)
    for index, feature_id in enumerate(result["selection"]["feature_ids"]):
        occurrences = features.get(feature_id, [])
        conflicts = {kind: _feature_conflicts(occurrences, kind) for kind in kinds}
        if not occurrences:
            reason = "missing_feature_record" if feature_pages else "missing_input_page"
            for kind in kinds:
                edge = _base_edge(feature_id, kind, "selection/" + str(index) + "/" + kind)
                edge["reason"] = reason
                edge["issues"] = [_issue("bvbrc_input_unavailable", field="feature_id")]
                result["edges"].append(edge)
            result["requirements"].append(_requirement("genome_feature", "feature_id", feature_id, None, reason))
        for page, row in occurrences:
            for kind in kinds:
                edge, requirements = _edge(page, row, feature_id, kind, sequences,
                                           bool(sequence_pages), conflicts[kind])
                result["edges"].append(edge)
                result["requirements"].extend(requirements)
    result["requirements"] = _unique(result["requirements"])
    return validate("FeatureSequenceSheet", result)
