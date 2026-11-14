"""Pure joins of supplied BV-BRC molecular measurements and their metadata.

The input sheets record native observations. This extractor checks their local
identifiers and references; it cannot establish receipt, source custody or the
truth of an asserted digest. The host separately qualifies those facts. It does
not fetch missing records, infer a replicate design, normalize measurements or
calculate expression statistics. Every selected result occurrence is retained.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math
import re

from .bvbrc_data_fields import (
    FIELD_REGISTRY,
    MOLECULAR_MEASUREMENT_FIELDS,
    SUPPLIED_METADATA_FIELDS,
)
from .bvbrc_data_schema import schema, validate

__all__ = (
    "MOLECULAR_SHEET_SCHEMA", "SUPPLIED_METADATA_SCHEMA",
    "extract_molecular_experiment_rows",
)

MOLECULAR_SHEET_SCHEMA = schema("MolecularSheet")
SUPPLIED_METADATA_SCHEMA = schema("SuppliedMetadata")
_JSON_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def _pointer(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError("bvbrc_molecular_incompatible_input:" + detail)


def _cell_map(row: dict) -> dict:
    return {cell["field"]: cell for cell in row["cells"]}


def _string(row: dict, field: str) -> str | None:
    cell = _cell_map(row).get(field)
    if (cell is not None and cell["presence"] == "present"
            and cell["status"] == "valid" and cell["native_shape"] == "scalar"
            and len(cell["atoms"]) == 1 and cell["atoms"][0]["kind"] == "string"):
        return cell["atoms"][0]["string_value"]
    return None


def _atom_check(atom: dict, cell: dict) -> None:
    kind = atom["kind"]
    populated = {"string": "string_value", "number": "number_value",
                 "boolean": "boolean_value"}.get(kind)
    for field in ("string_value", "number_value", "boolean_value"):
        if field != populated:
            _require(atom[field] is None, "atom_value_kind")
    if kind != "number":
        _require(atom["number_lexeme"] is None, "non_number_lexeme")
        if populated is not None:
            _require(atom[populated] is not None, "missing_atom_value")
        return
    token = atom["number_lexeme"]
    _require(type(token) is str and _JSON_NUMBER.fullmatch(token) is not None,
             "invalid_number_lexeme")
    try:
        exact = Decimal(token)
        projected = float(token)
    except (ValueError, InvalidOperation, OverflowError) as error:
        raise ValueError("bvbrc_molecular_incompatible_input:invalid_number_lexeme") from error
    value = atom["number_value"]
    if value is None:
        _require((not math.isfinite(projected) or (projected == 0 and exact != 0))
                 and "bvbrc_unrepresentable_numeric_value" in cell["issue_codes"],
                 "unrepresentable_atom")
    elif type(value) is int:
        _require(exact == value, "number_lexeme_value")
    else:
        _require(math.isfinite(projected) and projected == value
                 and not (value == 0 and exact != 0), "number_lexeme_value")


def _raw_cell_check(cell: dict, definition: dict) -> None:
    for atom in cell["atoms"]:
        _atom_check(atom, cell)
    presence = cell["presence"]
    shape = cell["native_shape"]
    if presence in ("absent", "null", "unselected"):
        _require(not cell["atoms"], "unavailable_cell_atoms")
        _require(shape == ("null" if presence == "null" else "absent"),
                 "unavailable_cell_shape")
    elif shape == "scalar":
        _require(len(cell["atoms"]) == 1, "scalar_cardinality")
    elif shape == "object":
        _require(cell["status"] == "invalid" and not cell["atoms"],
                 "invalid_object_cell")
    else:
        _require(shape == "array", "present_cell_shape")
    if cell["status"] != "valid":
        return
    _require(presence == "present", "valid_cell_presence")
    _require(shape == ("array" if definition["multi_valued"] else "scalar"),
             "valid_field_cardinality")
    native_type = definition["solr_type"]
    expected = ("number" if native_type in ("float", "int", "long") else
                "boolean" if native_type == "boolean" else "string")
    _require(all(atom["kind"] == expected for atom in cell["atoms"]),
             "valid_field_type")
    if native_type in ("int", "long"):
        _require(all(type(atom["number_value"]) is int for atom in cell["atoms"]),
                 "native_integer_type")


def _numeric_check(numeric: dict, raw: dict, definition: dict) -> None:
    _require(numeric["cell_key"] == raw["cell_key"]
             and numeric["native_path"] == raw["native_path"], "numeric_reference")
    _require(numeric["quantity_kind"] == definition["quantity_kind"], "quantity_kind")
    available = numeric["status"] in ("reported", "parsed_numeric_text")
    if not available:
        _require(numeric["value"] is None and numeric["reason"] is not None
                 and numeric["origin"] == "unavailable", "unavailable_number")
        _require(not (raw["status"] == "valid" and raw["presence"] == "present"
                      and definition["numeric_text_grammar"] is None),
                 "available_native_number_discarded")
        expected = {"absent": ("missing", "native_field_absent"),
                    "null": ("missing", "native_null"),
                    "unselected": ("unselected", "not_selected")}.get(raw["presence"])
        if expected:
            _require((numeric["status"], numeric["reason"]) == expected,
                     "numeric_missingness")
        return
    _require(numeric["value"] is not None and numeric["reason"] is None
             and raw["status"] == "valid" and raw["presence"] == "present"
             and raw["native_shape"] == "scalar" and len(raw["atoms"]) == 1,
             "reported_number_source")
    atom = raw["atoms"][0]
    if numeric["status"] == "reported":
        _require(atom["kind"] == "number" and atom["number_value"] == numeric["value"]
                 and numeric["origin"] == "native_reported", "reported_number_value")
    else:
        _require(definition["numeric_text_grammar"] == "nonnegative_decimal_integer"
                 and atom["kind"] == "string"
                 and re.fullmatch(r"[0-9]+", atom["string_value"]) is not None
                 and int(atom["string_value"]) == numeric["value"]
                 and numeric["origin"] == "derived_from_native_text", "numeric_text")


def _pages(values: list[dict], collection: str) -> list[dict]:
    _require(type(values) is list, "page_list")
    pages = []
    for value in values:
        page = validate("DataSheet", value)
        _require(page["collection"] == collection, "collection")
        _require(page["mode"] == "page" and page["page"]["mode"] == "page", "page_mode")
        _require(page["qualification"]["service_matches"]
                 and page["qualification"]["request_matches"], "known_source_mismatch")
        registry = FIELD_REGISTRY[collection]
        fields = page["selected_fields"]
        _require(all(field in registry["fields"] for field in fields), "collection_field")
        _require(page["page"]["returned_row_count"] == len(page["rows"]), "row_count")
        _require(page["page"]["valid_row_count"] == sum(
            row["status"] == "valid" for row in page["rows"]), "valid_row_count")
        _require(page["page"]["invalid_row_count"] == sum(
            row["status"] != "valid" for row in page["rows"]), "invalid_row_count")
        for index, row in enumerate(page["rows"]):
            _require(row["row_index"] == index, "row_ordinal")
            _require(row["row_key"] == page["custody"]["native_sha256"] + "/row/" + str(index),
                     "row_key")
            _require(row["native_path"] in ("/" + str(index), "/response/docs/" + str(index)),
                     "row_path")
            _require([cell["field"] for cell in row["cells"]] == fields, "selected_cells")
            cells = _cell_map(row)
            for field, cell in cells.items():
                _require(cell["cell_key"] == row["row_key"] + "/field/" + _pointer(field)
                         and cell["native_path"] == row["native_path"] + "/" + _pointer(field),
                         "cell_reference")
                _raw_cell_check(cell, registry["fields"][field])
            key = registry["unique_key"]
            _require(_string(row, key) == row["native_id"], "native_identity")
            expected_numerical = [field for field in fields
                                  if registry["fields"][field]["numeric_projection"]]
            _require([cell["field"] for cell in row["numerical_cells"]] == expected_numerical,
                     "numerical_cells")
            for numeric in row["numerical_cells"]:
                _numeric_check(numeric, cells[numeric["field"]], registry["fields"][numeric["field"]])
                if collection == "bioset_result":
                    _require(numeric["unit_code"] is None and numeric["unit_basis"] == "unknown"
                             and not numeric["unit_cell_keys"], "native_molecular_units")
                    _require(numeric["denominator_value"] is None and numeric["denominator_basis"] == "unknown"
                             and not numeric["uncertainty_cell_keys"], "unsupported_molecular_context")
        pages.append(page)
    return pages


def _location(page: dict, row: dict) -> dict:
    return {"native_sha256": page["custody"]["native_sha256"],
            "collection": page["collection"], "row_key": row["row_key"]}


def _cell_location(page: dict, row: dict, cell: dict, level: str) -> dict:
    return {**_location(page, row), "cell_key": cell["cell_key"],
            "field": cell["field"], "source_level": level}


def _index(pages: list[dict]) -> dict:
    result = {}
    for page in pages:
        for row in page["rows"]:
            if row["native_id"] is not None:
                result.setdefault(row["native_id"], []).append((page, row))
    return result


def _cell_value(cell: dict):
    """Comparable source value; a scalar is never coerced to an array."""
    return {"shape": cell["native_shape"], "atoms": [
        {key: value for key, value in atom.items() if key != "number_lexeme"}
        for atom in cell["atoms"]]}


def _disagree(candidates: list[tuple[dict, dict]]) -> bool:
    # Omitted/unselected values from different projections are not contradictions.
    seen = {}
    for _, row in candidates:
        for cell in row["cells"]:
            if cell["presence"] == "present" and cell["status"] == "valid":
                value = _cell_value(cell)
                if cell["field"] in seen and seen[cell["field"]] != value:
                    return True
                seen[cell["field"]] = value
    return False


def _link(expected: str | None, pages: list[dict], index: dict,
          collection: str) -> tuple[dict, list]:
    candidates = index.get(expected, []) if expected is not None else []
    if expected is None:
        status, reason = "missing_key", "missing_join_key"
    elif not pages:
        status, reason = "missing_input", "missing_input_page"
    elif not candidates:
        status = "missing_record"
        reason = "missing_feature_record" if collection == "genome_feature" else "requested_row_absent"
    elif _disagree(candidates):
        status, reason = "conflict", "conflicting_metadata"
    else:
        status, reason = "matched", None
    return {"expected_id": expected, "rows": [_location(page, row) for page, row in candidates],
            "status": status, "reason": reason}, candidates


def _issue(row: dict, field: str | None = None, code: str = "bvbrc_join_conflict") -> dict:
    return {"code": code, "phase": "join", "row_index": row["row_index"],
            "field": field, "native_path": row["native_path"] + ("/" + _pointer(field) if field else ""),
            "http_status": None}


def _unavailable_number(row: dict, field: str) -> dict:
    return {"cell_key": row["row_key"] + "/field/" + _pointer(field), "field": field,
            "native_path": row["native_path"] + "/" + _pointer(field),
            "value": None, "status": "unselected", "reason": "not_selected",
            "quantity_kind": "bioset_result." + field, "unit_code": None,
            "unit_basis": "unknown", "unit_cell_keys": [], "denominator_value": None,
            "denominator_basis": "unknown", "origin": "unavailable",
            "uncertainty_cell_keys": [], "issue_codes": []}


def _metadata(candidates: list, collection: str, level: str, link: dict | None = None) -> list:
    records = []
    # Include identifiers and parent-level numeric metadata such as samples,
    # biosets and entity_count; none is reinterpreted as replication.
    fields = [field for field in FIELD_REGISTRY[collection]["selectable_fields"]
              if collection != "bioset_result" or field not in MOLECULAR_MEASUREMENT_FIELDS]
    for field in fields:
        cells, values, missing = [], [], []
        for page, row in candidates:
            cell = _cell_map(row).get(field)
            if cell is None or cell["presence"] == "unselected":
                missing.append("not_selected")
            elif cell["presence"] == "absent":
                missing.append("native_field_absent")
            elif cell["presence"] == "null":
                missing.append("native_null")
            else:
                cells.append(_cell_location(page, row, cell, level))
                if cell["status"] == "valid":
                    values.append(_canonical(_cell_value(cell)))
                else:
                    missing.append("native_value_invalid")
        conflict = len(set(values)) > 1 or (link is not None and link["status"] == "conflict")
        if conflict:
            status, reason = "conflict", "conflicting_metadata"
        elif values:
            status, reason = "reported", None
        else:
            status = "missing"
            reason = missing[0] if missing else (link["reason"] if link else "not_selected")
        records.append({"field": field, "source_level": level, "cells": cells,
                        "status": status, "reason": reason})
    return records


def _add_requirement(requirements: list, collection: str, field: str,
                     value: str, reason: str) -> None:
    for requirement in requirements:
        if (requirement["collection"], requirement["field"], requirement["reason"]) == (collection, field, reason):
            if value not in requirement["values"]:
                requirement["values"].append(value)
            return
    requirements.append({"collection": collection, "field": field, "values": [value],
                         "sequence_kind": None, "reason": reason})


def _supplied(records: list[dict]) -> list[dict]:
    _require(type(records) is list, "supplied_metadata_list")
    result = [validate("SuppliedMetadata", record) for record in records]
    locations = {}
    for record in result:
        path = record["provenance"]["record_path"]
        _require(path == "" or path.startswith("/"), "metadata_json_pointer")
        _require(re.search(r"~(?![01])", path) is None, "metadata_json_pointer_escape")
        _require(bool(record["provenance"]["source_ref"]), "metadata_source_ref")
        content = {key: value for key, value in record.items() if key != "provenance"}
        # Include containers as well as leaves so a repeated source/path cannot
        # assert different array cardinality or different null/empty states.
        for suffix, value in _located_values(content):
            location = (record["provenance"]["source_ref"], path + suffix)
            previous = locations.get(location)
            encoded = _canonical(value)
            _require(previous is None or previous == encoded, "conflicting_source_path")
            locations[location] = encoded
    return result


def _located_values(value, path: str = ""):
    yield path, value
    if type(value) is dict:
        for key, child in value.items():
            yield from _located_values(child, path + "/" + _pointer(key))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _located_values(child, path + "/" + str(index))


def _supplied_location(record: dict, field: str, suffix: str) -> dict:
    source_ref = record["provenance"]["source_ref"]
    path = record["provenance"]["record_path"] + "/" + _pointer(field) + suffix
    return {"cell_key": "supplied/" + _pointer(source_ref) + path,
            "field": field, "source_level": "supplied", "source_ref": source_ref,
            "record_path": path}


def _supplied_rows(records: list, result_id: str, bioset_id: str | None) -> tuple[list, bool, dict]:
    relevant = [record for record in records if record["result_id"] == result_id or
                (record["result_id"] is None and bioset_id is not None and record["bioset_id"] == bioset_id)]
    metadata, unit_cells = [], {field: [] for field in MOLECULAR_MEASUREMENT_FIELDS}
    conflict = False
    for field in SUPPLIED_METADATA_FIELDS:
        cells, known_values = [], []
        binding_conflict = any(record["bioset_id"] != bioset_id for record in relevant)
        for record in relevant:
            value = record[field]
            if value is None:
                cells.append(_supplied_location(record, field, ""))
                continue
            known_values.append(_canonical(value))
            for suffix, atom in _located_values(value):
                if type(atom) not in (list, dict) or not atom:
                    cells.append(_supplied_location(record, field, suffix))
            if field == "measurement_units" and record["bioset_id"] == bioset_id:
                for index, unit in enumerate(value):
                    unit_cells[unit["field"]].append(
                        (_supplied_location(record, field, "/" + str(index) + "/unit"), unit["unit"]))
        differing = len(set(known_values)) > 1
        # Two fields' distinct units are complementary. Only different strings
        # for the same measured field are contradictory unit assertions.
        if field == "measurement_units":
            differing = any(len({unit for _, unit in candidates}) > 1
                            for candidates in unit_cells.values())
        if binding_conflict or differing:
            status, reason = "conflict", "conflicting_metadata"
            conflict = True
        elif not relevant:
            status, reason = "missing", "missing_input_page"
        elif field == "measurement_units" and not any(unit_cells.values()):
            status, reason = "missing", "unknown_units"
        elif not known_values:
            status, reason = "missing", "native_null"
        else:
            status, reason = "supplied", None
        metadata.append({"field": field, "source_level": "supplied", "cells": cells,
                         "status": status, "reason": reason})
    return metadata, conflict, unit_cells


def extract_molecular_experiment_rows(result_pages: list[dict], *,
        bioset_pages: list[dict], experiment_pages: list[dict],
        feature_pages: list[dict], result_ids: list[str],
        supplied_metadata: list[dict]) -> dict:
    """Return all selected occurrences and exact parent links, without I/O.

    Invalid contracts or internally inconsistent cell references raise
    ``ValueError``. Source-reported malformed cells and missing/contradictory
    biological parents remain typed partial results with valid numbers intact.
    The caller must have qualified actual input custody before this call.
    """
    _require(type(result_ids) is list and bool(result_ids)
             and all(type(value) is str for value in result_ids)
             and len(set(result_ids)) == len(result_ids), "result_ids")
    pages = {
        "bioset_result": _pages(result_pages, "bioset_result"),
        "bioset": _pages(bioset_pages, "bioset"),
        "experiment": _pages(experiment_pages, "experiment"),
        "genome_feature": _pages(feature_pages, "genome_feature"),
    }
    supplied = _supplied(supplied_metadata)
    indices = {collection: _index(items) for collection, items in pages.items()}
    selected = set(result_ids)
    result = {"version": "bvbrc_molecular_sheet_v1", "selected_result_ids": result_ids[:],
              "input_native_sha256s": list(dict.fromkeys(
                  page["custody"]["native_sha256"] for items in pages.values() for page in items)),
              "supplied_metadata": supplied, "rows": [], "missing_result_ids": [],
              "requirements": [], "issues": [deepcopy(issue)
                  for items in pages.values() for page in items for issue in page["issues"]]}
    for page in pages["bioset_result"]:
        for native in page["rows"]:
            result_id = native["native_id"]
            if result_id not in selected:
                continue
            exp_id, bioset_id, feature_id, entity_id = (
                _string(native, field) for field in ("exp_id", "bioset_id", "feature_id", "entity_id"))
            experiment, experiment_rows = _link(exp_id, pages["experiment"], indices["experiment"], "experiment")
            bioset, bioset_rows = _link(bioset_id, pages["bioset"], indices["bioset"], "bioset")
            feature, feature_rows = _link(feature_id, pages["genome_feature"], indices["genome_feature"], "genome_feature")
            issues = deepcopy(native["issues"])
            for _, parent in bioset_rows:
                parent_exp = _string(parent, "exp_id")
                if parent_exp is not None and exp_id is not None and parent_exp != exp_id:
                    bioset.update(status="conflict", reason="conflicting_metadata")
                    issues.append(_issue(parent, "exp_id"))
                elif parent_exp is None or exp_id is None:
                    if bioset["status"] != "conflict":
                        bioset.update(status="missing_key", reason="missing_join_key")
            # A same-feature native patric_id or protein_id can corroborate an
            # explicit alias. An entity_id has no declared namespace, so it is
            # retained but never guessed to be a PATRIC identifier.
            for _, parent in feature_rows:
                for field in ("patric_id", "protein_id"):
                    left, right = _string(native, field), _string(parent, field)
                    if left is not None and right is not None and left != right:
                        feature.update(status="conflict", reason="conflicting_metadata")
                        issues.append(_issue(native, field))
            duplicate_conflict = _disagree(indices["bioset_result"][result_id])
            if duplicate_conflict:
                issues.append(_issue(native, "id"))
            numerical = {cell["field"]: cell for cell in native["numerical_cells"]}
            measurements = [deepcopy(numerical[field]) if field in numerical
                            else _unavailable_number(native, field)
                            for field in MOLECULAR_MEASUREMENT_FIELDS]
            metadata = (_metadata([(page, native)], "bioset_result", "result")
                        + _metadata(bioset_rows, "bioset", "bioset", bioset)
                        + _metadata(experiment_rows, "experiment", "experiment", experiment))
            supplied_rows, supplied_conflict, unit_cells = _supplied_rows(supplied, result_id, bioset_id)
            metadata.extend(supplied_rows)
            for measurement in measurements:
                units = unit_cells[measurement["field"]]
                if units:
                    measurement["unit_basis"] = "supplied"
                    measurement["unit_cell_keys"] = list(dict.fromkeys(cell["cell_key"] for cell, _ in units))
                    if len({unit for _, unit in units}) > 1:
                        measurement["issue_codes"].append("bvbrc_join_conflict")
            if supplied_conflict:
                issues.append(_issue(native))
            for field, link in (("exp_id", experiment), ("bioset_id", bioset), ("feature_id", feature)):
                if link["status"] == "conflict":
                    diagnostic = _issue(native, field)
                    if diagnostic not in issues:
                        issues.append(diagnostic)
            statuses = [link["status"] for link in (experiment, bioset, feature)]
            relationship = ("conflict" if duplicate_conflict or supplied_conflict or "conflict" in statuses
                            else "matched" if all(status == "matched" for status in statuses) else "partial")
            molecular_row = {"row_key": native["row_key"], "result_id": result_id,
                             "result_rows": [_location(page, native)], "exp_id": exp_id,
                             "bioset_id": bioset_id, "feature_id": feature_id, "entity_id": entity_id,
                             "experiment": experiment, "bioset": bioset, "feature": feature,
                             "measurements": measurements, "metadata": metadata,
                             "relationship_status": relationship, "issues": issues}
            result["rows"].append(molecular_row)
            for collection, field, link in (("experiment", "exp_id", experiment),
                                             ("bioset", "bioset_id", bioset),
                                             ("genome_feature", "feature_id", feature)):
                if link["expected_id"] is not None and link["status"] in ("missing_input", "missing_record"):
                    _add_requirement(result["requirements"], collection, field, link["expected_id"], link["reason"])
                elif link["status"] == "missing_key":
                    # The absent identifier itself is unknown. Request the
                    # identified native record that should contain that key.
                    if collection == "bioset" and bioset_rows and exp_id is not None:
                        _add_requirement(result["requirements"], "bioset", "bioset_id", bioset_id, "missing_join_key")
                    else:
                        _add_requirement(result["requirements"], "bioset_result", "id", result_id, "missing_join_key")
            result["issues"].extend(issues)
    for result_id in result_ids:
        if result_id not in indices["bioset_result"]:
            result["missing_result_ids"].append(result_id)
            reason = "missing_input_page" if not pages["bioset_result"] else "requested_row_absent"
            _add_requirement(result["requirements"], "bioset_result", "id", result_id, reason)
    return validate("MolecularSheet", result)
