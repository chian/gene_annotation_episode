"""Pure selected BV-BRC facts and receiver values.

``QualifiedResult`` is a host-established precondition, not an authentication
token: this module cannot establish custody by inspecting JSON flags. It checks
the supplied records' relationships and projects only the frozen selection.
Fact ``collection`` accompanies the publication's source binding. Materialized
cells instead identify their actual input source and collection; these can
differ when the publication joins several collections.
There is no Store, transport, calculator, model, action, credit or prompt here.
Model-facing rendering is deliberately a separate, unfinished boundary.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from .bvbrc_data_fields import (
    FIELD_REGISTRY, METADATA_FIELDS, NUMERICAL_FIELDS, SELECTABLE_FIELDS,
    MOLECULAR_MEASUREMENT_FIELDS, SUPPLIED_METADATA_FIELDS,
)
from .bvbrc_data_query import validate_data_query
from .bvbrc_data_readers import validate_data_sheet
from .bvbrc_data_schema import fact_schemas, schema, validate, json_digest
from .communication import ReportBoundaryError, validate_closed_schema
from .execution_contracts import digest as host_digest

RESULT_SELECTOR_SCHEMA = schema("ResultSelector")
PUBLISHED_GRADING_SCHEMA = schema("PublishedGrading")
QUALIFIED_RESULT_SCHEMA = schema("QualifiedResult")
PUBLICATION_INPUTS_SCHEMA = schema("PublicationInputs")
RECEIVER_MATERIALIZATION_SCHEMA = schema("ReceiverMaterialization")
FACT_SCHEMAS = fact_schemas()
FACT_SOURCES = tuple(FACT_SCHEMAS)
IDENTIFIER_NAMESPACES = (
    "bvbrc_data_row", "bvbrc_data_cell", "bvbrc_data_identifier",
    "bvbrc_data_population", "bvbrc_data_bucket",
)
__all__ = (
    "RESULT_SELECTOR_SCHEMA", "PUBLISHED_GRADING_SCHEMA", "QUALIFIED_RESULT_SCHEMA",
    "PUBLICATION_INPUTS_SCHEMA", "FACT_SCHEMAS", "RECEIVER_MATERIALIZATION_SCHEMA",
    "FACT_SOURCES", "IDENTIFIER_NAMESPACES", "bvbrc_data_fact_sources",
    "validate_data_result_selector", "project_bvbrc_data_facts",
    "resolve_bvbrc_data_identifier", "validate_bvbrc_data_return",
    "materialize_bvbrc_received_values",
)

_MEANINGS = (
    "Selected retained response and page coverage; document counts are acquisition metadata.",
    "Native matching-document counts with their exact population and availability.",
    "Native field buckets and saved fractions of the same response's exact document population.",
    "Explicitly selected native rows, numerical measurements and source metadata cells.",
    "Selected feature occurrences and their recorded AA/NA sequence associations.",
    "Selected molecular measurements with recorded result, bioset, experiment and feature relationships.",
)
_LEVEL_COLLECTION = {"result": "bioset_result", "bioset": "bioset", "experiment": "experiment"}
_Validator = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine_many({
        "integer": lambda _, v: type(v) is int,
        "number": lambda _, v: type(v) in (int, float),
        "boolean": lambda _, v: type(v) is bool,
    }))


def _require(condition, detail):
    if not condition:
        raise ValueError("bvbrc_data_projection_invalid:" + detail)


def _json(value):
    """Reject non-JSON inputs, including bool-as-number via later validation."""
    active = set()

    def copy(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float:
            _require(math.isfinite(item), "nonfinite_number")
            return item
        _require(kind in (dict, list) and id(item) not in active, "finite_json_required")
        active.add(id(item))
        try:
            if kind is list:
                return [copy(v) for v in item]
            _require(all(type(k) is str for k in item), "json_keys")
            return {k: copy(v) for k, v in item.items()}
        finally:
            active.remove(id(item))
    return copy(value)


def _same(a, b):
    # Python equality would silently equate True, 1 and 1.0.
    return json.dumps(a, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) == json.dumps(
        b, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _escape(value):
    return value.replace("~", "~0").replace("/", "~1")


def _ref(source, key):
    return source + "#" + key


def _unique(values):
    return list(dict.fromkeys(values))


def _pointer(path):
    _require(type(path) is str and (not path or path.startswith("/"))
             and re.search(r"~(?![01])", path) is None, "metadata_pointer")


def _locations(value, path=""):
    yield path, value
    if type(value) is dict:
        for name, child in value.items():
            yield from _locations(child, path + "/" + _escape(name))
    elif type(value) is list:
        for i, child in enumerate(value):
            yield from _locations(child, path + "/" + str(i))


def _supplied_records(records):
    occupied = {}
    for record in records:
        source, path = record["provenance"]["source_ref"], record["provenance"]["record_path"]
        _require(bool(source), "metadata_source")
        _pointer(path)
        for suffix, value in _locations({k: v for k, v in record.items() if k != "provenance"}):
            key = (source, path + suffix)
            _require(key not in occupied or _same(occupied[key], value), "conflicting_metadata_location")
            occupied[key] = value


def bvbrc_data_fact_sources() -> dict:
    """Detached source descriptors accepted by the existing closed form guard."""
    return {name: {"type": "array", "meaning": meaning, "report_schema": definition}
            for (name, definition), meaning in zip(fact_schemas().items(), _MEANINGS)}


def validate_data_result_selector(selector: dict, *, request: dict) -> dict:
    """Validate local selection semantics without resolving its input sources."""
    request = validate_data_query(request)
    result = validate("ResultSelector", selector)
    projection, collection = result["projection"], request["collection"]
    family = projection["family"]
    if request["mode"] != "page":
        _require(family == "query_metadata" and result["page"] is None, "mode_projection")
    inputs = result["inputs"]
    _require(all(item["source_ref"] for item in inputs), "input_source")
    _require(len({item["source_ref"] for item in inputs}) == len(inputs), "duplicate_input_source")
    if family in ("query_metadata", "collection_rows"):
        _require(not inputs and not result["supplied_metadata"], "unexpected_inputs")
    if family == "collection_rows":
        _require(set(projection["numeric_fields"]) <= set(NUMERICAL_FIELDS[collection]), "numeric_field")
        _require(set(projection["metadata_fields"]) <= set(METADATA_FIELDS[collection]), "metadata_field")
    if family == "feature_sequence":
        allowed = {"genome_feature", "feature_sequence"}
        _require(collection in allowed and all(item["collection"] in allowed for item in inputs), "join_collection")
        _require(not result["supplied_metadata"], "unexpected_metadata")
        _require(all(projection["feature_ids"]), "feature_id")
        _require(set(projection["feature_metadata_fields"]) <= set(SELECTABLE_FIELDS["genome_feature"]), "feature_metadata_field")
    if family == "molecular_experiment":
        allowed = {"bioset_result", "bioset", "experiment", "genome_feature"}
        _require(collection in allowed and all(item["collection"] in allowed for item in inputs), "join_collection")
        _require(all(projection["result_ids"]), "result_id")
        for item in projection["metadata_fields"]:
            level, field = item["source_level"], item["field"]
            fields = SUPPLIED_METADATA_FIELDS if level == "supplied" else SELECTABLE_FIELDS[_LEVEL_COLLECTION[level]]
            _require(field in fields and not (level == "result" and field in MOLECULAR_MEASUREMENT_FIELDS), "metadata_field_level")
        _supplied_records(result["supplied_metadata"])
    return result


def _cell_reason(cell):
    if cell is None or cell["presence"] == "unselected":
        return "not_selected"
    if cell["presence"] == "absent":
        return "native_field_absent"
    if cell["presence"] == "null":
        return "native_null"
    if cell["status"] == "unrepresentable":
        return "unrepresentable_numeric_value"
    if cell["status"] != "valid":
        return "native_value_invalid"
    return None


def _string(row, field):
    cell = next((c for c in row["cells"] if c["field"] == field), None)
    if (cell is not None and _cell_reason(cell) is None and cell["native_shape"] == "scalar"
            and cell["atoms"][0]["kind"] == "string"):
        return cell["atoms"][0]["string_value"]
    return None


def _atom(value):
    kind = "null" if value is None else "boolean" if type(value) is bool else (
        "number" if type(value) in (int, float) else "string")
    return {"kind": kind, "string_value": value if kind == "string" else None,
            "number_value": value if kind == "number" else None,
            "boolean_value": value if kind == "boolean" else None,
            "number_lexeme": json.dumps(value, allow_nan=False) if kind == "number" else None}


def _fact_shape(source, value):
    errors = list(_Validator(FACT_SCHEMAS[source]).iter_errors(value))
    _require(not errors, "fact_shape:" + source)


class _View:
    """One detached, internally checked host-qualified publication."""

    def __init__(self, value):
        self.q = validate("QualifiedResult", value)
        self.g = self.q["grading"]
        self.binding = self.q["binding"]
        self.source = self.binding["source_ref"]
        self.prepared = self.g["prepared"]
        self.selector = validate_data_result_selector(self.g["selector"], request=self.prepared["original_request"])
        self.projection = self.selector["projection"]
        self.sheet = self.g["parse_result"]["sheet"]
        _require(bool(self.source), "source")
        _require(self.binding["selector_sha256"] == host_digest(self.selector), "selector_binding")
        _require(self.binding["collection"] == self.prepared["original_request"]["collection"], "request_collection")
        _require(all(_same(self.prepared["original_request"][key], self.prepared["effective_request"][key])
                     for key in ("collection", "mode", "filters")), "effective_request")
        _require(self.prepared["page_selector"] == self.selector["page"], "page_selection")
        _require(self.g["parse_result"]["retained_native_sha256"] == self.binding["native_sha256"], "raw_binding")
        _require(_same(self.g["input_bindings"], [r["binding"] for r in self.q["input_results"]]), "input_bindings")
        _require(_same(self.selector["inputs"], [{"collection": r["binding"]["collection"],
            "source_ref": r["binding"]["source_ref"]} for r in self.q["input_results"]]), "selected_input_bindings")
        _require(self.source not in [r["source_ref"] for r in self.selector["inputs"]], "self_input")
        self.entries = []
        if self.sheet is not None:
            _require(self.g["parse_result"]["status"] == self.sheet["qualification"]["status"], "parse_sheet_status")
            _require(self.sheet["custody"]["prepared_sha256"] == json_digest(self.prepared), "prepared_binding")
            _require(self.sheet["population"]["population_key"] == self.prepared["query_population"]["population_key"], "population_binding")
            _require(self.sheet["mode"] == self.prepared["effective_request"]["mode"]
                     and self.sheet["selected_fields"] == self.prepared["effective_request"]["fields"], "effective_selection")
            _require(self.sheet["custody"]["native_profile"] == "solr_json_envelope_v1", "native_profile")
            self._add_page(self.binding, self.sheet)
        else:
            _require(self.g["parse_result"]["status"] == "failed" and bool(self.g["parse_result"]["failures"]), "failed_sheet_status")
        for item in self.q["input_results"]:
            self._add_page(item["binding"], item["sheet"])
        self.supplied = self.selector["supplied_metadata"]
        expected_bindings = _unique((r["provenance"]["source_ref"], r["provenance"]["record_path"],
            json_digest({k: v for k, v in r.items() if k != "provenance"})) for r in self.supplied)
        actual_bindings = [(b["source_ref"], b["record_path"], b["metadata_sha256"]) for b in self.g["metadata_bindings"]]
        _require(actual_bindings == expected_bindings, "metadata_bindings")
        self.cells = {}
        self.registry = {key: set() for key in (*IDENTIFIER_NAMESPACES, "execution_result", "source")}

    def _add_page(self, binding, sheet):
        sheet = validate_data_sheet(sheet)
        _require(sheet["collection"] == binding["collection"] and sheet["custody"]["native_sha256"] == binding["native_sha256"], "input_sheet_binding")
        _require(sheet["qualification"]["service_matches"] and sheet["qualification"]["request_matches"], "sheet_request")
        count, population, page = sheet["count"], sheet["population"], sheet["page"]
        _require(count["population_key"] == population["population_key"]
                 and count["reported_value"] == population["reported_total"] == page["reported_total"]
                 and count["exactness"] == population["exactness"] == page["count_exactness"], "count_population_relationship")
        _require((count["availability"] == "available") == (count["reason"] is None)
                 and (count["availability"] != "available" or count["reported_value"] is not None), "count_availability")
        self.entries.append((binding, sheet))

    def locations(self, location, *, collection=None):
        _require(collection is None or location["collection"] == collection, "location_collection")
        matches = [(binding, sheet, row) for binding, sheet in self.entries
            if sheet["collection"] == location["collection"] and sheet["custody"]["native_sha256"] == location["native_sha256"]
            for row in sheet["rows"] if row["row_key"] == location["row_key"]]
        _require(bool(matches), "row_location")
        return matches

    def row_refs(self, locations, collection, native_id=None):
        refs = []
        for location in locations:
            for binding, _, row in self.locations(location, collection=collection):
                _require(native_id is None or row["native_id"] == native_id, "row_native_identity")
                refs.append(_ref(binding["source_ref"], row["row_key"]))
        return _unique(refs)

    def native_cells(self, location, *, rows=None, level=None):
        _require(level is None or location["source_level"] == level, "cell_level")
        if rows is not None:
            _require({k: location[k] for k in ("native_sha256", "collection", "row_key")} in rows, "cell_row_relationship")
        refs = []
        for binding, sheet, row in self.locations(location):
            found = [c for c in row["cells"] if c["cell_key"] == location["cell_key"] and c["field"] == location["field"]]
            _require(len(found) == 1, "cell_location")
            refs.append(self.add_cell(binding, sheet, row, found[0], location["source_level"]))
        return refs

    def add_cell(self, binding, sheet, row, cell, level):
        ref = _ref(binding["source_ref"], cell["cell_key"])
        value = {"source_ref": binding["source_ref"], "row_ref": _ref(binding["source_ref"], row["row_key"]),
            "cell_ref": ref, "collection": sheet["collection"], "native_id": row["native_id"],
            "field": cell["field"], "source_level": level,
            **{key: deepcopy(cell[key]) for key in ("presence", "native_shape", "atoms", "status", "issue_codes")}}
        # The same selected cell can be shown under distinct source levels in
        # different fact families. Level is part of the materialization lookup.
        key = (ref, level)
        _require(key not in self.cells or _same(self.cells[key], value), "conflicting_cell_value")
        self.cells[key] = value
        return ref

    def supplied_cell(self, location, *, result_id, bioset_id, field):
        _require(location["source_level"] == "supplied" and location["field"] == field, "supplied_field")
        matches = []
        for record in self.supplied:
            relevant = record["result_id"] == result_id or (record["result_id"] is None and record["bioset_id"] == bioset_id)
            if not relevant or record["provenance"]["source_ref"] != location["source_ref"]:
                continue
            base = record["provenance"]["record_path"] + "/" + _escape(field)
            for suffix, atom in _locations(record[field]):
                if type(atom) in (list, dict) and atom:
                    continue
                if base + suffix == location["record_path"]:
                    matches.append(atom)
        _require(bool(matches) and all(_same(matches[0], value) for value in matches), "supplied_location")
        key = "supplied/" + _escape(location["source_ref"]) + location["record_path"]
        _require(location["cell_key"] == key, "supplied_key")
        atom = matches[0]
        value = {"source_ref": location["source_ref"], "row_ref": None,
            "cell_ref": _ref(location["source_ref"], key), "collection": None, "native_id": None,
            "field": field, "source_level": "supplied", "presence": "null" if atom is None else "present",
            "native_shape": "null" if atom is None else "array" if type(atom) is list else "object" if type(atom) is dict else "scalar",
            "atoms": [] if atom is None or type(atom) in (list, dict) else [_atom(atom)],
            "status": "missing" if atom is None else "valid", "issue_codes": []}
        self.cells[(value["cell_ref"], "supplied")] = value
        return value["cell_ref"]

    def common(self, status):
        return {"source_ref": self.source, "collection": self.binding["collection"],
            "input_source_refs": [b["source_ref"] for b in self.g["input_bindings"]],
            "metadata_source_refs": _unique(b["source_ref"] for b in self.g["metadata_bindings"]), "status": status}

    def absent_reason(self):
        if self.sheet is not None:
            return "requested_row_absent"
        return self.parse_reason()

    def parse_reason(self):
        codes = {failure["code"] for failure in self.g["parse_result"]["failures"]}
        if "bvbrc_response_body_incomplete" in codes:
            return "transport_incomplete"
        if "bvbrc_native_partial_results" in codes:
            return "native_partial_results"
        if codes.intersection({"bvbrc_response_service_mismatch", "bvbrc_response_request_mismatch", "bvbrc_provider_http_error"}):
            return "incompatible_input"
        if codes.intersection({"bvbrc_unsupported_media_type", "bvbrc_expected_native_row_array", "bvbrc_expected_solr_response"}):
            return "native_format_unverified"
        if "bvbrc_population_metadata_conflict" in codes:
            return "population_conflict"
        return "native_value_invalid"

    def metadata(self, row, entries, fields, level):
        selected, missing = [], []
        for field in fields:
            reasons = []
            for binding, sheet, native in entries:
                cell = next((c for c in native["cells"] if c["field"] == field), None)
                reason = _cell_reason(cell)
                if cell is not None and cell["presence"] in ("present", "null"):
                    selected.append({"field": field, "value_ref": self.add_cell(binding, sheet, native, cell, level), "source_level": level})
                if reason is not None:
                    reasons.append(reason)
            if not entries:
                reasons.append(self.absent_reason())
            for reason in _unique(reasons):
                missing.append({"field": field, "source_level": level, "reason": reason})
        row["metadata_cells"], row["metadata_unavailable"] = selected, missing

    def measurements(self, row, entries, fields, *, level, recorded=None, unit_refs=None):
        row["measurements"], row["unavailable"] = [], []
        for field in fields:
            if not entries:
                row["unavailable"].append({"field": field, "reason": self.absent_reason()})
                continue
            binding, sheet, native = entries[0]
            native_number = next((c for c in native["numerical_cells"] if c["field"] == field), None)
            number = next((c for c in recorded if c["field"] == field), None) if recorded is not None else native_number
            if number is None:
                row["unavailable"].append({"field": field, "reason": "not_selected"})
                continue
            if native_number is None:
                _require(number["status"] == "unselected" and number["value"] is None and number["reason"] == "not_selected", "unacquired_number")
            else:
                omit = {"unit_basis", "unit_cell_keys", "issue_codes"} if recorded is not None else set()
                _require(_same({k: v for k, v in number.items() if k not in omit},
                               {k: v for k, v in native_number.items() if k not in omit}), "number_row_relationship")
            if number["status"] not in ("reported", "parsed_numeric_text"):
                _require(number["value"] is None and number["reason"] is not None, "unavailable_number")
                row["unavailable"].append({"field": field, "reason": number["reason"]})
                continue
            raw = next(c for c in native["cells"] if c["field"] == field)
            refs = [] if unit_refs is None else unit_refs.get(field, [])
            _require(len(refs) == len(number["unit_cell_keys"]), "number_unit_relationship")
            uncertainty = []
            for key in number["uncertainty_cell_keys"]:
                cells = [c for c in native["cells"] if c["cell_key"] == key]
                _require(len(cells) == 1, "number_uncertainty_relationship")
                uncertainty.append(self.add_cell(binding, sheet, native, cells[0], level))
            row["measurements"].append({"field": field, "cell_ref": self.add_cell(binding, sheet, native, raw, level),
                "value": number["value"], "unit_code": number["unit_code"], "unit_basis": number["unit_basis"],
                "unit_value_refs": refs, "denominator_value": number["denominator_value"],
                "denominator_basis": number["denominator_basis"], "uncertainty_cell_refs": uncertainty,
                "origin": number["origin"]})

    def query_facts(self, source):
        if self.sheet is None:
            common = {**self.common("unavailable"), "population_ref": _ref(self.source,
                self.prepared["query_population"]["population_key"])}
            effective = self.prepared["effective_request"]
            if source == FACT_SOURCES[0]:
                return [{**common, "mode": effective["mode"],
                    "requested_offset": effective["offset"] if effective["mode"] == "page" else None,
                    "requested_limit": effective["limit"] if effective["mode"] == "page" else None,
                    "returned_row_count": None, "valid_row_count": None, "invalid_row_count": None,
                    "reported_total": None, "count_exactness": "unknown", "response_complete": False,
                    "population_coverage": "unknown", "next_offset": None, "unavailable_reason": self.parse_reason()}]
            if source == FACT_SOURCES[1]:
                # The query population is known from the original assignment;
                # its measured size is unknown when no sheet could be read.
                return [{**common, "reported_value": None,
                    "exactness": "unknown", "availability": "unavailable", "reason": self.absent_reason()}]
            if source == FACT_SOURCES[2] and effective["mode"] == "facet":
                request = effective["facet"]
                return [{**common, "field": request["field"], "bucket_ref": None,
                    "is_missing_bucket": None, "term_ref": None, "count": None, "denominator": None,
                    "fraction": None, "fraction_unavailable_reason": self.parse_reason(),
                    "requested_offset": request["offset"], "requested_limit": request["limit"],
                    "requested_min_count": request["min_count"], "bucket_window_status": "invalid"}]
            return []
        sheet, page, count = self.sheet, self.sheet["page"], self.sheet["count"]
        common = self.common("complete" if self.g["parse_result"]["status"] == "complete" else "partial")
        population = _ref(self.source, sheet["population"]["population_key"])
        if source == FACT_SOURCES[0]:
            return [{**common, **{key: page[key] for key in (
                "mode", "requested_offset", "requested_limit", "returned_row_count", "valid_row_count",
                "invalid_row_count", "reported_total", "count_exactness", "response_complete", "population_coverage", "next_offset")},
                "population_ref": population, "unavailable_reason": None if common["status"] == "complete" else self.parse_reason()}]
        if source == FACT_SOURCES[1]:
            return [{**common, "population_ref": population,
                **{key: count[key] for key in ("reported_value", "exactness", "availability", "reason")}}]
        if sheet["mode"] != "facet":
            return []
        components = self.g["facet_components"]
        _require(components is not None and components["population_key"] == sheet["population"]["population_key"], "facet_components")
        buckets = [b for f in sheet["facets"] for b in f["buckets"]]
        _require([f["bucket_key"] for f in components["fractions"]] == [b["bucket_key"] for b in buckets], "facet_component_membership")
        values = {f["bucket_key"]: f for f in components["fractions"]}
        result = []
        for facet in sheet["facets"]:
            _require(facet["population_key"] == components["population_key"]
                     and facet["request"] == self.prepared["effective_request"]["facet"], "facet_request")
            if not facet["buckets"] and facet["issues"]:
                request = facet["request"]
                result.append({**common, "status": "unavailable", "population_ref": population,
                    "field": request["field"], "bucket_ref": None, "is_missing_bucket": None,
                    "term_ref": None, "count": None, "denominator": None, "fraction": None,
                    "fraction_unavailable_reason": self.parse_reason(), "requested_offset": request["offset"],
                    "requested_limit": request["limit"], "requested_min_count": request["min_count"],
                    "bucket_window_status": "invalid"})
            for bucket in facet["buckets"]:
                fraction = values[bucket["bucket_key"]]
                _require(fraction["numerator"] == bucket["count"]
                         and fraction["denominator"] == sheet["population"]["reported_total"], "facet_number_relationship")
                if fraction["reason"] is None:
                    _require(count["availability"] == "available" and count["exactness"] == "exact"
                             and sheet["population"]["native_num_found_exact"] is True
                             and fraction["denominator"] is not None and fraction["denominator"] > 0
                             and bucket["status"] == "valid" and fraction["numerator"] is not None
                             and fraction["fraction"] == fraction["numerator"] / fraction["denominator"], "facet_fraction_relationship")
                else:
                    _require(fraction["fraction"] is None, "unavailable_fraction")
                term_ref = None
                if bucket["term"] is not None:
                    term_ref = _ref(self.source, bucket["term_cell_key"])
                    null = bucket["term"]["kind"] == "null"
                    self.cells[(term_ref, "facet")] = {"source_ref": self.source, "row_ref": None,
                        "cell_ref": term_ref, "collection": sheet["collection"], "native_id": None,
                        "field": facet["request"]["field"], "source_level": "facet", "presence": "null" if null else "present",
                        "native_shape": "null" if null else "scalar", "atoms": [] if null else [deepcopy(bucket["term"])],
                        "status": "missing" if null else "valid", "issue_codes": []}
                result.append({**common, "population_ref": population, "field": facet["request"]["field"],
                    "bucket_ref": _ref(self.source, bucket["bucket_key"]), "is_missing_bucket": bucket["is_missing_bucket"],
                    "term_ref": term_ref, "count": bucket["count"], "denominator": fraction["denominator"],
                    "fraction": fraction["fraction"], "fraction_unavailable_reason": fraction["reason"],
                    "requested_offset": facet["request"]["offset"], "requested_limit": facet["request"]["limit"],
                    "requested_min_count": facet["request"]["min_count"], "bucket_window_status": facet["bucket_window_status"]})
        return result

    def numeric_facts(self):
        result = []
        for index in self.projection["row_indices"]:
            entries = [(b, s, row) for b, s in self.entries if b["source_ref"] == self.source
                       for row in s["rows"] if row["row_index"] == index]
            native = entries[0][2] if entries else None
            row = {**self.common("unavailable" if native is None else "complete"),
                "row_ref": None if native is None else _ref(self.source, native["row_key"]),
                "requested_row_index": index, "native_id": None if native is None else native["native_id"]}
            self.measurements(row, entries, self.projection["numeric_fields"], level="row")
            self.metadata(row, entries, self.projection["metadata_fields"], "row")
            if native is not None and (not self.sheet["transport"]["body_complete"]
                                      or row["unavailable"] or row["metadata_unavailable"]):
                row["status"] = "partial"
            result.append(row)
        return result

    def feature_facts(self):
        sheet = self.g["feature_sequence_sheet"]
        _require(sheet is not None, "feature_sheet_unavailable")
        selection = {k: self.projection[k] for k in ("feature_ids", "sequence_kind")}
        _require(_same(sheet["selection"], selection), "feature_selection")
        _require(set(sheet["input_native_sha256s"]) == {s["custody"]["native_sha256"] for _, s in self.entries}, "feature_input_membership")
        kinds = ("AA", "NA") if selection["sequence_kind"] == "both" else (selection["sequence_kind"],)
        expected = {(row["row_key"], kind, row["native_id"]) for _, page in self.entries if page["collection"] == "genome_feature"
                    for row in page["rows"] if row["native_id"] in selection["feature_ids"] for kind in kinds}
        seen, missing, result = set(), set(), []
        for edge in sheet["edges"]:
            _require(edge["feature_id"] in selection["feature_ids"] and edge["sequence_kind"] in kinds, "feature_edge_selection")
            feature_refs = self.row_refs(edge["feature_rows"], "genome_feature", edge["feature_id"])
            sequence_refs = self.row_refs(edge["sequence_rows"], "feature_sequence", edge["native_md5"])
            _require(len(edge["feature_rows"]) == (0 if edge["join_status"] == "missing_feature" else 1), "feature_occurrence")
            entries = [v for loc in edge["feature_rows"] for v in self.locations(loc)]
            if entries:
                key = (entries[0][2]["row_key"], edge["sequence_kind"], edge["feature_id"])
                _require(key not in seen, "duplicate_feature_edge")
                seen.add(key)
                _require(_string(entries[0][2], edge["sequence_kind"].lower() + "_sequence_md5") == edge["native_md5"], "feature_hash_relationship")
            else:
                key = (edge["feature_id"], edge["sequence_kind"])
                _require(key not in missing, "duplicate_missing_feature")
                missing.add(key)
            expected_sequence_rows, expected_sequence_cells = [], []
            for _, page in self.entries:
                if page["collection"] != "feature_sequence" or edge["native_md5"] is None:
                    continue
                for native in page["rows"]:
                    if native["native_id"] != edge["native_md5"]:
                        continue
                    location = {"native_sha256": page["custody"]["native_sha256"],
                        "collection": "feature_sequence", "row_key": native["row_key"]}
                    if location not in expected_sequence_rows:
                        expected_sequence_rows.append(location)
                    for cell in native["cells"]:
                        if cell["field"] == "sequence":
                            cell_location = {**location, "cell_key": cell["cell_key"], "field": "sequence", "source_level": "sequence"}
                            if cell_location not in expected_sequence_cells:
                                expected_sequence_cells.append(cell_location)
            _require(_same(edge["sequence_rows"], expected_sequence_rows)
                     and _same(edge["sequence_cells"], expected_sequence_cells), "sequence_member_relationship")
            row = {**self.common("unavailable" if not entries else "complete" if edge["join_status"] in ("joined", "repeated_identical") else "partial"),
                "feature_id": edge["feature_id"], "feature_row_refs": feature_refs, "sequence_kind": edge["sequence_kind"],
                "native_md5": edge["native_md5"], "sequence_row_refs": sequence_refs, "sequence_value_refs": [],
                **{k: edge[k] for k in ("sequence_length", "feature_length", "raw_md5_match", "length_match", "join_status")},
                "unavailable_reason": edge["reason"]}
            for location in edge["feature_metadata_cells"]:
                self.native_cells(location, rows=edge["feature_rows"], level="feature")
            for location in edge["sequence_cells"]:
                _require(location["field"] == "sequence", "sequence_field")
                refs = self.native_cells(location, rows=edge["sequence_rows"], level="sequence")
                if self.projection["include_sequence_values"]:
                    row["sequence_value_refs"].extend(refs)
            row["sequence_value_refs"] = _unique(row["sequence_value_refs"])
            self.metadata(row, entries, self.projection["feature_metadata_fields"], "feature")
            if row["metadata_unavailable"] and row["status"] == "complete":
                row["status"] = "partial"
            result.append(row)
        _require(seen == expected, "feature_occurrence_membership")
        expected_missing = {(identifier, kind) for identifier in selection["feature_ids"] for kind in kinds
                            if not any(key[2] == identifier for key in expected)}
        _require(missing == expected_missing, "missing_feature_membership")
        return result

    def molecular_facts(self):
        sheet = self.g["molecular_sheet"]
        _require(sheet is not None, "molecular_sheet_unavailable")
        selected = self.projection["result_ids"]
        _require(sheet["selected_result_ids"] == selected and _same(sheet["supplied_metadata"], self.supplied), "molecular_selection")
        _require(set(sheet["input_native_sha256s"]) == {s["custody"]["native_sha256"] for _, s in self.entries}, "molecular_input_membership")
        occurrences = [(binding, page, row) for binding, page in self.entries if page["collection"] == "bioset_result"
                       for row in page["rows"] if row["native_id"] in selected]
        expected = Counter(row["row_key"] for _, _, row in occurrences)
        seen, result = Counter(), []
        _require(len(sheet["rows"]) == len(occurrences), "result_occurrence_membership")
        for molecular, occurrence in zip(sheet["rows"], occurrences):
            _require(molecular["result_id"] in selected and len(molecular["result_rows"]) == 1, "result_selection")
            candidates = self.locations(molecular["result_rows"][0], collection="bioset_result")
            _require(occurrence in candidates, "result_occurrence_order")
            entries = [occurrence]
            native = entries[0][2]
            _require(native["native_id"] == molecular["result_id"] and native["row_key"] == molecular["row_key"], "result_identity")
            seen[molecular["row_key"]] += 1
            for field in ("exp_id", "bioset_id", "feature_id", "entity_id"):
                _require(_string(native, field) == molecular[field], "molecular_identifier_relationship")
            row = {**self.common("complete" if molecular["relationship_status"] == "matched" else "partial"),
                "row_ref": _ref(entries[0][0]["source_ref"], native["row_key"]), "requested_row_index": None,
                "native_id": native["native_id"], "result_id": molecular["result_id"],
                **{k: molecular[k] for k in ("exp_id", "bioset_id", "feature_id", "entity_id", "relationship_status")}}
            metadata_entries = {"result": entries}
            for kind, collection, identity in (("experiment", "experiment", "exp_id"),
                    ("bioset", "bioset", "bioset_id"), ("feature", "genome_feature", "feature_id")):
                link = molecular[kind]
                _require(link["expected_id"] == molecular[identity], "parent_link_identity")
                matches = [(b, s, r) for b, s in self.entries if s["collection"] == collection
                           for r in s["rows"] if molecular[identity] is not None and r["native_id"] == molecular[identity]]
                _require(link["rows"] == [{"native_sha256": s["custody"]["native_sha256"],
                    "collection": collection, "row_key": r["row_key"]} for _, s, r in matches], "parent_link_membership")
                metadata_entries[kind] = matches
                row[kind + "_row_refs"] = self.row_refs(link["rows"], collection, molecular[identity])
                if link["status"] == "matched":
                    _require(bool(link["rows"]) and link["reason"] is None, "matched_parent")
                for location in link["rows"]:
                    for _, _, parent in self.locations(location):
                        if kind == "bioset" and _string(parent, "exp_id") != molecular["exp_id"]:
                            _require(link["status"] != "matched" and molecular["relationship_status"] != "matched", "bioset_experiment_relationship")
            metadata = {}
            for item in molecular["metadata"]:
                key = (item["source_level"], item["field"])
                _require(key not in metadata, "duplicate_metadata_field")
                metadata[key] = item
                level, field = key
                _require(field in (SUPPLIED_METADATA_FIELDS if level == "supplied" else SELECTABLE_FIELDS[_LEVEL_COLLECTION[level]])
                         and not (level == "result" and field in MOLECULAR_MEASUREMENT_FIELDS), "metadata_registered_field")
                expected_locations = []
                if level == "supplied":
                    for record in self.supplied:
                        relevant = record["result_id"] == molecular["result_id"] or (
                            record["result_id"] is None and record["bioset_id"] == molecular["bioset_id"])
                        if not relevant:
                            continue
                        for suffix, atom in _locations(record[field]):
                            if type(atom) in (list, dict) and atom:
                                continue
                            path = record["provenance"]["record_path"] + "/" + _escape(field) + suffix
                            source = record["provenance"]["source_ref"]
                            expected_locations.append({"cell_key": "supplied/" + _escape(source) + path,
                                "field": field, "source_level": level, "source_ref": source, "record_path": path})
                else:
                    for _, page, source_row in metadata_entries[level]:
                        for cell in source_row["cells"]:
                            if cell["field"] == field and cell["presence"] == "present":
                                expected_locations.append({"native_sha256": page["custody"]["native_sha256"],
                                    "collection": page["collection"], "row_key": source_row["row_key"],
                                    "cell_key": cell["cell_key"], "field": field, "source_level": level})
                _require(_same(item["cells"], expected_locations), "metadata_cell_membership")
                for location in item["cells"]:
                    _require(location["field"] == field and location["source_level"] == level, "metadata_location_relationship")
                    if level == "supplied":
                        self.supplied_cell(location, result_id=molecular["result_id"], bioset_id=molecular["bioset_id"], field=field)
                    else:
                        _require(location["collection"] == _LEVEL_COLLECTION[level], "metadata_collection")
                        locations = molecular["result_rows"] if level == "result" else molecular[level]["rows"]
                        self.native_cells(location, rows=locations, level=level)
            unit_refs = {}
            _require([n["field"] for n in molecular["measurements"]] == list(MOLECULAR_MEASUREMENT_FIELDS), "measurement_slots")
            for number in molecular["measurements"]:
                expected_keys, refs = [], []
                for record in self.supplied:
                    if record["bioset_id"] != molecular["bioset_id"] or record["result_id"] not in (None, molecular["result_id"]):
                        continue
                    for i, unit in enumerate(record["measurement_units"]):
                        if unit["field"] != number["field"]:
                            continue
                        source = record["provenance"]["source_ref"]
                        path = record["provenance"]["record_path"] + "/measurement_units/" + str(i) + "/unit"
                        key = "supplied/" + _escape(source) + path
                        expected_keys.append(key)
                        refs.append(self.supplied_cell({"source_ref": source, "record_path": path,
                            "cell_key": key, "source_level": "supplied", "field": "measurement_units"},
                            result_id=molecular["result_id"], bioset_id=molecular["bioset_id"], field="measurement_units"))
                _require(number["unit_cell_keys"] == _unique(expected_keys)
                         and number["unit_basis"] == ("supplied" if expected_keys else "unknown"), "measurement_units")
                unit_refs[number["field"]] = _unique(refs)
            self.measurements(row, entries, self.projection["measurement_fields"], level="result",
                              recorded=molecular["measurements"], unit_refs=unit_refs)
            row["metadata_cells"], row["metadata_unavailable"] = [], []
            for selection in self.projection["metadata_fields"]:
                level, field = selection["source_level"], selection["field"]
                item = metadata.get((level, field))
                _require(item is not None, "missing_metadata_slot")
                for location in item["cells"]:
                    refs = [self.supplied_cell(location, result_id=molecular["result_id"], bioset_id=molecular["bioset_id"], field=field)] if level == "supplied" else self.native_cells(location, level=level)
                    row["metadata_cells"].extend({"field": field, "value_ref": ref, "source_level": level} for ref in refs)
                if item["reason"] is not None:
                    row["metadata_unavailable"].append({"field": field, "source_level": level, "reason": item["reason"]})
            if row["unavailable"] or row["metadata_unavailable"]:
                row["status"] = "partial"
            result.append(row)
        _require(seen == expected, "result_occurrence_membership")
        missing = [identifier for identifier in selected if not any(row["result_id"] == identifier for row in sheet["rows"])]
        _require(sheet["missing_result_ids"] == missing, "missing_result_membership")
        for identifier in missing:
            row = {**self.common("unavailable"), "row_ref": None, "requested_row_index": None,
                "native_id": None, "result_id": identifier, "exp_id": None, "bioset_id": None,
                "feature_id": None, "entity_id": None, "experiment_row_refs": [], "bioset_row_refs": [],
                "feature_row_refs": [], "relationship_status": "partial", "metadata_cells": [],
                "metadata_unavailable": [{**item, "reason": "requested_row_absent"} for item in self.projection["metadata_fields"]]}
            self.measurements(row, [], self.projection["measurement_fields"], level="result")
            result.append(row)
        return result

    def facts(self, sources):
        values = {}
        family = self.projection["family"]
        for source in sources:
            if source in FACT_SOURCES[:3]:
                rows = self.query_facts(source)
            elif source == FACT_SOURCES[3] and family == "collection_rows":
                rows = self.numeric_facts()
            elif source == FACT_SOURCES[4] and family == "feature_sequence":
                rows = self.feature_facts()
            elif source == FACT_SOURCES[5] and family == "molecular_experiment":
                rows = self.molecular_facts()
            else:
                rows = []
            _fact_shape(source, rows)
            values[source] = rows
        return values


def _views(qualified_results):
    _require(type(qualified_results) is list, "qualified_result_list")
    views = [_View(value) for value in qualified_results]
    _require(len({view.source for view in views}) == len(views), "duplicate_qualified_source")
    if views:
        key = lambda view: tuple(view.q["host_qualification"][k] for k in ("run_id", "receiver_episode_id", "scope_sha256"))
        _require(all(key(view) == key(views[0]) for view in views), "receiver_context")
    return views


def _sources(requested_sources):
    _require(type(requested_sources) is tuple and all(type(s) is str and s in FACT_SOURCES for s in requested_sources)
             and len(set(requested_sources)) == len(requested_sources), "fact_sources")
    return requested_sources


def project_bvbrc_data_facts(qualified_results: list[dict], *, selector: dict, requested_sources: tuple[str, ...]) -> dict:
    """Project exactly the requested sources from unchanged original selections."""
    sources = _sources(requested_sources)
    selector = validate("ResultSelector", selector)
    result = {source: [] for source in sources}
    for view in _views(qualified_results):
        _require(_same(selector, view.selector), "selector_changed")
        for source, rows in view.facts(sources).items():
            result[source].extend(rows)
    return deepcopy(result)


def _reference_values(value, node):
    if value is None:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _reference_values(child, node["properties"][key])
    elif isinstance(value, list):
        for child in value:
            yield from _reference_values(child, node["items"])
    elif isinstance(value, str) and "x-reference-namespace" in node:
        yield node["x-reference-namespace"], value


def resolve_bvbrc_data_identifier(qualified_results: list[dict], *, reference: str, namespace: str) -> bool:
    """Exact selected membership; never prefix/provider or global lookup."""
    if type(reference) is not str or namespace not in (*IDENTIFIER_NAMESPACES, "execution_result", "source"):
        return False
    try:
        for view in _views(qualified_results):
            facts = view.facts(FACT_SOURCES)
            for source, rows in facts.items():
                if (namespace, reference) in _reference_values(rows, FACT_SCHEMAS[source]):
                    return True
                if namespace == "bvbrc_data_identifier":
                    for row in rows:
                        for key in _requested_cells(row, source):
                            cell = view.cells[key]
                            field = cell["field"]
                            if (cell["status"] == "valid" and cell["source_level"] != "supplied"
                                    and (field.endswith(("_id", "_ids", "_accession", "_md5"))
                                         or field in ("id", "md5", "accession", "ec_number", "go"))):
                                if any(atom["kind"] == "string" and atom["string_value"] == reference for atom in cell["atoms"]):
                                    return True
        return False
    except (ValueError, KeyError):
        return False


def validate_bvbrc_data_return(form: dict, *, original_schema: dict, recorded_facts: dict) -> None:
    """Check the original closed form and equality of whole BV-BRC fact arrays.

    The existing host validates other namespaces/interpretation fields. This
    function validates the full schema shape and every requested BV-BRC field.
    """
    original_schema = validate_closed_schema(original_schema)
    form, recorded_facts = _json(form), _json(recorded_facts)
    errors = list(_Validator(original_schema).iter_errors(form))
    if errors:
        raise ReportBoundaryError(errors[0].message, code="bvbrc_invalid_form")
    for name, declared in original_schema["properties"].items():
        source = declared.get("x-source")
        if source not in FACT_SOURCES:
            continue
        if source not in recorded_facts:
            raise ReportBoundaryError("Recorded BV-BRC source is unavailable", code="unknown_fact", field=name)
        _fact_shape(source, recorded_facts[source])
        if not _same(form[name], recorded_facts[source]):
            raise ReportBoundaryError("BV-BRC values disagree with their recorded relationships", code="bvbrc_recorded_facts_mismatch", field=name)


def _requested_cells(row, source):
    for metadata in row.get("metadata_cells", []):
        yield metadata["value_ref"], metadata["source_level"]
    level = "result" if source == FACT_SOURCES[5] else "row"
    for measurement in row.get("measurements", []):
        yield measurement["cell_ref"], level
        for reference in measurement["unit_value_refs"]:
            yield reference, "supplied"
        for reference in measurement["uncertainty_cell_refs"]:
            yield reference, level
    for reference in row.get("sequence_value_refs", []):
        yield reference, "sequence"
    if row.get("term_ref") is not None:
        yield row["term_ref"], "facet"


def materialize_bvbrc_received_values(qualified_results: list[dict], *, admitted_form: dict, original_schema: dict) -> list[dict]:
    """Deliver requested actual source values, preserving units and missingness."""
    views = _views(qualified_results)
    original_schema = validate_closed_schema(original_schema)
    fields = [(name, declared["x-source"]) for name, declared in original_schema["properties"].items()
              if declared.get("x-source") in FACT_SOURCES]
    sources = tuple(_unique(source for _, source in fields))
    recorded = {source: [] for source in sources}
    cells = {}
    for view in views:
        for source, rows in view.facts(sources).items():
            recorded[source].extend(rows)
        for key, value in view.cells.items():
            _require(key not in cells or _same(cells[key], value), "conflicting_selected_cell")
            cells[key] = value
    validate_bvbrc_data_return(admitted_form, original_schema=original_schema, recorded_facts=recorded)
    result = []
    for name, source in fields:
        rows = recorded[source]
        selected_cells, unavailable, seen = [], [], set()
        for row in rows:
            for key in _requested_cells(row, source):
                _require(key in cells, "materialization_cell_unavailable")
                if key not in seen:
                    selected_cells.append(cells[key])
                    seen.add(key)
            level = "result" if source == FACT_SOURCES[5] else "row"
            for item in row.get("unavailable", []):
                unavailable.append({"collection": "bioset_result" if level == "result" else row["collection"], "native_id": row.get("native_id"),
                    "field": item["field"], "source_level": level, "reason": item["reason"]})
            for item in row.get("metadata_unavailable", []):
                level = item["source_level"]
                collection = {**_LEVEL_COLLECTION, "feature": "genome_feature", "sequence": "feature_sequence",
                              "supplied": "bioset_result"}.get(level, row["collection"])
                identity = {"bioset": "bioset_id", "experiment": "exp_id", "feature": "feature_id"}.get(level, "native_id")
                unavailable.append({"collection": collection, "native_id": row.get(identity), **item})
        context = views[0].q["host_qualification"] if views else {"run_id": None, "receiver_episode_id": None}
        key = json_digest({"run_id": context["run_id"], "receiver_episode_id": context["receiver_episode_id"],
            "original_schema": original_schema, "form_field": name, "fact_source": source, "facts": rows})
        result.append(validate("ReceiverMaterialization", {"version": "bvbrc_received_values_v1",
            "admission_key": key, "form_field": name, "fact_source": source,
            "facts": rows, "cells": selected_cells, "unavailable": unavailable}))
    return result
