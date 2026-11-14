"""Finite, exact directional facts; independent of providers and calculation.

The accepted numerical schema is read as data only. This layer never imports a
native reader, numerical validator/calculator, provider, projection or binder.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

from . import bvbrc_proteome_fact_contracts as legacy

obj, arr, enum, nullable = legacy.obj, legacy.arr, legacy.enum, legacy.nullable
N, P = legacy.UINT, {"type": "integer", "minimum": 1}
TEXT = legacy.TEXT
_DEFS = json.loads(Path(__file__).with_name(
    "bvbrc_proteome_directional_numerical_schemas.json").read_text(encoding="utf-8"))["$defs"]


def _expanded(value):
    if type(value) is dict:
        if "$ref" in value:
            return _expanded(_DEFS[value["$ref"].removeprefix("#/$defs/")])
        return {k: _expanded(v) for k, v in value.items()}
    if type(value) is list:
        return [_expanded(v) for v in value]
    return value


TRACE_COUNTS = tuple(_DEFS["TraceCounts"]["properties"])
TRACE_FRACTIONS = tuple(_DEFS["TraceFractions"]["properties"])
COVERAGES = tuple(_DEFS["CoverageComponents"]["properties"])
EXTREMA = ("maximum_reported_hsp_bit_score", "maximum_reported_hsp_raw_score",
           "minimum_reported_hsp_expectation")
COMPATIBLE_COUNTS = tuple(_DEFS["CompatiblePairCounts"]["properties"])
SUBJECT_FRACTIONS = ("compatible_unique_pair_symbol_identity", "compatible_unique_pair_resolved_identity",
    "compatible_unique_pair_resolved_fraction", "nonoverlapping_hsp_reported_identity_over_columns")
REPORTED_FRACTIONS = ("reported_identity_fraction", "reported_positive_fraction", "reported_gap_fraction",
    "reported_identity_among_paired_fraction")
NUMERICAL_ISSUES = tuple(_DEFS["IssueCode"]["enum"])
READER_ISSUES = tuple(_DEFS["ReaderIssue"]["properties"]["code"]["enum"])
COUNT_UNITS = tuple(_DEFS["CountCell"]["properties"]["unit"]["enum"])
STATISTIC_KINDS = tuple(_DEFS["ReaderStatistic"]["properties"]["kind"]["enum"])
EXPECTATION_STATES = ("positive_reported_decimal", "printed_zero_precision_unknown", "missing", "invalid")
BINDING_CODES = tuple("proteome_directional_" + code for code in (
    "document_missing", "document_ambiguous", "duplicate_document_selection", "artifact_binding_conflict",
    "artifact_digest_mismatch", "format_incompatible", "nonzero_range_unsupported", "declared_version_conflict",
    "reader_contract_invalid", "sheet_construction_failed", "calculation_failed", "requested_target_missing",
    "requested_value_unavailable", "saved_identity_conflict", "saved_numerical_relationship_conflict"))
HOST_INPUT_KINDS = ("output_bytes", "parser_binding", "byte_version_evidence", "scientific_metadata")
FAMILIES = dict(zip(("directional_count", "directional_fraction", "directional_coverage",
    "directional_native_integer", "directional_native_decimal", "directional_state", "directional_extremum",
    "directional_intervals", "directional_columns", "directional_edges", "directional_conflicts",
    "directional_support", "directional_issues", "directional_requirements"),
    ("directional_counts", "directional_fractions", "directional_coverages", "directional_native_integers",
     "directional_native_decimals", "directional_states", "directional_extrema", "directional_intervals",
     "directional_columns", "directional_edges", "directional_conflicts", "directional_support",
     "directional_issues", "directional_requirements")))
ORDINALS = ("report_ordinal", "query_ordinal", "subject_ordinal", "hsp_ordinal", "block_ordinal",
            "description_ordinal", "database_header_ordinal", "statistic_ordinal")
KEYS = {"report": (), "query": ("query_ordinal",),
    "subject": ("query_ordinal", "subject_ordinal"),
    "hsp": ("query_ordinal", "subject_ordinal", "hsp_ordinal"),
    "block": ("query_ordinal", "subject_ordinal", "hsp_ordinal", "block_ordinal"),
    "description": ("query_ordinal", "description_ordinal"),
    "database_header": ("query_ordinal", "database_header_ordinal"),
    "statistic": ("query_ordinal", "statistic_ordinal")}
KEYS["correspondence"] = KEYS["compatible_pairs"] = KEYS["subject"]
COUNT_METRICS = {
    "report": ("displayed_query_count", "displayed_description_count", "displayed_subject_count",
               "displayed_hsp_count", "displayed_block_count"),
    "query": ("displayed_description_count", "displayed_subject_count", "displayed_hsp_count", "displayed_block_count"),
    "subject": ("displayed_hsp_count", "displayed_block_count", "nonoverlapping_hsp_reported_identity_count",
                "nonoverlapping_hsp_reported_alignment_columns"),
    "hsp": TRACE_COUNTS + ("reported_paired_column_count", "reported_nonidentical_paired_count"),
    "block": TRACE_COUNTS, "correspondence": ("distinct_pair_count", "repeated_pair_occurrence_count"),
    "compatible_pairs": COMPATIBLE_COUNTS}
FRACTION_METRICS = {"hsp": TRACE_FRACTIONS + REPORTED_FRACTIONS, "block": TRACE_FRACTIONS,
                    "subject": SUBJECT_FRACTIONS}
COVERAGE_METRICS = {"query": ("any_displayed_subject_query_paired_union",),
                    **{scope: COVERAGES for scope in ("subject", "hsp", "block")}}
INTEGER_METRICS = {"query": ("length",), "subject": ("length",),
    "hsp": ("identity_count", "identity_denominator", "positive_count", "positive_denominator",
            "gap_count", "gap_denominator", "raw_score", "expect_group_count"),
    "database_header": ("sequence_count", "letter_count"), "statistic": ("integer_value",)}
DECIMAL_METRICS = {"hsp": ("bit_score", "expect", "identity_printed_percent", "positive_printed_percent", "gap_printed_percent"),
    "description": ("bit_score", "evalue"), "statistic": ("decimal_value", "threshold", "bits", "lambda", "k", "h")}
STATE_METRICS = {"report": {"parse_state": ("ok", "partial", "failure"), "body_complete": (),
    "object_complete": ("yes", "no", "unknown"), "operand_binding": ("unbound",)},
    "query": {"display_state": tuple(_DEFS["QueryComponents"]["properties"]["display_state"]["enum"]),
              "boundary": tuple(_DEFS["ReaderQuery"]["properties"]["boundary"]["enum"])},
    "hsp": {"contiguous_blocks": ("yes", "no", "unknown"),
        "native_denominator_extent": tuple(_DEFS["HspComponents"]["properties"]["native_denominator_extent"]["enum"]),
        "expectation_display": EXPECTATION_STATES},
    "subject": {"mapping_state": ("compatible_displayed_partial_map", "observed_conflict", "incomplete_geometry")}}


def _selector(kind, scope, *, metrics=None, page=False, **extra):
    return obj(kind={"const": kind}, scope={"const": scope},
        **({"document_id": TEXT, **{key: N for key in KEYS[scope]}} if scope != "all" else {}),
        **({"metric": enum(*metrics)} if metrics is not None else {}),
        **({"offset": N, "limit": P} if page else {}), **extra)


SELECTORS = {}
for _kind, _scopes in (("directional_count", COUNT_METRICS), ("directional_fraction", FRACTION_METRICS),
    ("directional_coverage", COVERAGE_METRICS), ("directional_intervals", COVERAGE_METRICS),
    ("directional_native_integer", INTEGER_METRICS), ("directional_native_decimal", DECIMAL_METRICS),
    ("directional_state", STATE_METRICS), ("directional_extremum", {"subject": EXTREMA})):
    SELECTORS[_kind] = {"oneOf": [_selector(_kind, scope, metrics=metrics, page=_kind == "directional_intervals")
                                  for scope, metrics in _scopes.items()]}
for _kind, _scope in (("directional_columns", "block"), ("directional_edges", "subject"),
                     ("directional_conflicts", "subject")):
    SELECTORS[_kind] = _selector(_kind, _scope, page=True)
_support = []
for _scope, _collections in (("hsp", ("strings_support", "pair_geometry_support")),
                           ("subject", ("pair_geometry_support",)), *COVERAGE_METRICS.items()):
    _support.append(_selector("directional_support", _scope, page=True, collection=enum(*_collections),
        member=enum("included_blocks", "excluded_blocks", "hsps_without_traceback")))
_support.append(_selector("directional_support", "subject", page=True, collection=enum(*EXTREMA),
                         member=enum("tied_hsps", "excluded_hsps")))
SELECTORS["directional_support"] = {"oneOf": _support}
SELECTORS["directional_issues"] = {"oneOf": [_selector("directional_issues", scope, page=True,
    layer=enum("reader", "numerical")) for scope in ("report", "query", "subject", "hsp", "block")]}
SELECTORS["directional_requirements"] = _selector("directional_requirements", "all")


def validate_directional_selector(value: dict) -> dict:
    legacy._validate({"oneOf": list(SELECTORS.values())}, value, "directional_selector_invalid")
    legacy.require(all(type(v) is not str or bool(v.strip()) for v in value.values()), "directional_selector_invalid")
    return deepcopy(value)


def _reference(kind):
    if kind == "document":
        return TEXT
    if kind == "source":
        return TEXT
    return legacy.reference_schema(kind)


EXACT_DECIMAL = obj(sign={"type": "integer", "minimum": 0, "maximum": 1},
    digits={"type": "array", "minItems": 1, "items": {"type": "integer", "minimum": 0, "maximum": 9}},
    exponent={"type": "integer"})
EXACT_RATIO = obj(numerator=N, denominator=P, rendered_decimal=EXACT_DECIMAL)
INTERVAL = obj(start=N, end=P)


def directional_fact_schemas() -> dict:
    target = obj(document_id=_reference("document"), **{k: nullable(N) for k in ORDINALS})
    support = obj(basis=enum("strings", "pair_geometry", "reported_interval", "trace_occupied", "trace_paired"),
        support_ref=_reference("population"), included_block_count=N, excluded_block_count=N,
        hsps_without_traceback_count=N, complete_for_displayed_blocks={"type": "boolean"})
    context = obj(target=target, native_source_ref=nullable(_reference("source")),
        value_ref=nullable(_reference("field")), parameter_ref=nullable(_reference("parameter")),
        operand_refs=arr(_reference("source_field")), report_parse_state=nullable(enum("ok", "partial", "failure")),
        body_complete=nullable({"type": "boolean"}), object_complete=nullable(enum("yes", "no", "unknown")),
        declaration_state=nullable(enum("unconstrained_version", "matching_version", "conflicting_version")),
        operand_binding={"const": "unbound"}, supports=arr(support),
        mapping_state=nullable(enum(*STATE_METRICS["subject"]["mapping_state"])),
        qualification_refs=arr(_reference("qualification")), requirement_refs=arr(_reference("requirement")))
    state = nullable(enum("value", "missing", "invalid", "conflict", "undefined"))
    count = obj(state=state, value=nullable(N), unit=enum(*COUNT_UNITS),
        reason_codes=arr(enum(*NUMERICAL_ISSUES)), uncertainty={"type": "null"})
    ratio = obj(state=state, value=nullable(EXACT_RATIO), unit={"const": "fraction"},
        reason_codes=arr(enum(*NUMERICAL_ISSUES)), uncertainty={"type": "null"})
    ni = obj(state=nullable(enum("present", "missing", "invalid")), value=nullable(N))
    nd = obj(state=nullable(enum("present", "missing", "invalid")), value=nullable(EXACT_DECIMAL))
    population = obj(**{k: nullable(N) for k in ("total_pairs", "resolved_pairs", "unresolved_pairs", "stop_containing_pairs")})
    native_units = enum("aa", "alignment_column", "bits", "native_raw_score", "expected_count", "percent",
        "native_expect_group_count", "sequence_occurrence", "native_reported_integer", "native_reported_decimal")
    def numeric(metrics, **props):
        return obj(availability=legacy.AVAILABILITY, quantity=enum(*dict.fromkeys(metrics)), context=context, **props)
    out = {
        "directional_count": numeric(sum(COUNT_METRICS.values(), ()), cell=count),
        "directional_fraction": numeric(sum(FRACTION_METRICS.values(), ()), cell=ratio, pair_population=nullable(population)),
        "directional_coverage": numeric(sum(COVERAGE_METRICS.values(), ()), count=count, reported_length=ni,
            denominator_ref=nullable(_reference("source_field")), coverage=ratio, interval_count=N,
            intervals_ref=nullable(_reference("population"))),
        "directional_native_integer": numeric(sum(INTEGER_METRICS.values(), ()), cell=ni, unit=native_units,
            statistic_kind=nullable(enum(*STATISTIC_KINDS))),
        "directional_native_decimal": numeric(sum(DECIMAL_METRICS.values(), ()), cell=nd, unit=native_units,
            statistic_kind=nullable(enum(*STATISTIC_KINDS)), expectation_display=nullable(enum(*EXPECTATION_STATES)),
            expect_group_count=nullable(ni)),
        "directional_state": numeric(tuple(m for v in STATE_METRICS.values() for m in v),
            value_code=nullable(enum(*dict.fromkeys(code for v in STATE_METRICS.values() for codes in v.values() for code in codes))),
            value_boolean=nullable({"type": "boolean"})),
        "directional_extremum": numeric(EXTREMA, state=nullable(enum("value", "missing", "invalid")),
            native_integer=nullable(ni), native_decimal=nullable(nd), selected_operand_ref=nullable(_reference("source_field")),
            tied_hsp_count=N, excluded_hsp_count=N, tied_hsps_ref=nullable(_reference("population")),
            excluded_hsps_ref=nullable(_reference("population")), reason_codes=arr(enum(*NUMERICAL_ISSUES)),
            expectation_display=nullable(enum(*EXPECTATION_STATES)), expect_group_count=nullable(ni))}
    column = _expanded(_DEFS["Column"])
    for key in ("query_symbol", "subject_symbol"):
        column["properties"][key] = {"type": "string", "format": "alignment_symbol"}
    conflict = _expanded(_DEFS["MappingConflict"])
    for key in ("query_intervals", "subject_intervals"):
        conflict["properties"][key] = arr(INTERVAL)
    items = {"directional_intervals": INTERVAL, "directional_columns": column,
        "directional_edges": _expanded(_DEFS["PairEdge"]), "directional_conflicts": conflict,
        "directional_support": obj(block_key=nullable(_expanded(_DEFS["BlockKey"])),
            hsp_key=nullable(_expanded(_DEFS["HspKey"]))),
        "directional_issues": obj(layer=enum("reader", "numerical"), code=enum(*dict.fromkeys((*READER_ISSUES, *NUMERICAL_ISSUES))),
            issue_ref=_reference("qualification"), operand_refs=arr(_reference("source_field")),
            column_keys=arr(_expanded(_DEFS["ColumnKey"])), hsp_keys=arr(_expanded(_DEFS["HspKey"])))}
    collections = {"directional_intervals": tuple(dict.fromkeys(sum(COVERAGE_METRICS.values(), ()))),
        "directional_columns": ("columns",), "directional_edges": ("edges",), "directional_conflicts": ("conflicts",),
        "directional_support": ("strings_support", "pair_geometry_support", *dict.fromkeys(sum(COVERAGE_METRICS.values(), ())), *EXTREMA),
        "directional_issues": ("reader", "numerical")}
    for kind, item in items.items():
        out[kind] = obj(availability=legacy.AVAILABILITY, context=context, collection=enum(*collections[kind]),
            offset=N, limit=P, total_count=N, returned_count=N, next_offset=nullable(N), items=arr(item))
    out["directional_requirements"] = obj(availability={"const": "available"}, requirements=arr(obj(
        requirement_ref=_reference("requirement"), code=enum(*BINDING_CODES), required_input=enum(*HOST_INPUT_KINDS),
        document_id=nullable(_reference("document")), field_ref=nullable(_reference("field")),
        native_source_refs=arr(_reference("source")))))
    return deepcopy(out)


def requested_form_schema_v2(selections: dict) -> dict:
    legacy.require(type(selections) is dict and all(type(n) is str and bool(n.strip()) for n in selections), "form_invalid")
    checked = {name: (validate_directional_selector(value) if type(value) is dict and value.get("kind") in SELECTORS
                     else legacy.validate_selector(value)) for name, value in selections.items()}
    for value in checked.values():
        if value["kind"] == "request_status":
            legacy.require(value["field"] in checked and checked[value["field"]]["kind"] != "request_status", "status_target_invalid")
    schemas = {**legacy.fact_schemas(), **directional_fact_schemas()}
    return obj(**{name: {**schemas[value["kind"]], "x-bvbrc-proteome": value} for name, value in checked.items()})


def validate_requested_form_v2(value: dict) -> dict:
    legacy.require(type(value) is dict and set(value) == {"type", "properties", "required", "additionalProperties"}, "form_invalid")
    props, required = value["properties"], value["required"]
    legacy.require(type(props) is dict and type(required) is list and all(type(n) is str for n in required), "form_invalid")
    legacy.require(len(required) == len(set(required)) and set(required) == set(props), "form_required_conflict")
    legacy.require(all(type(v) is dict and "x-bvbrc-proteome" in v for v in props.values()), "form_invalid")
    expected = requested_form_schema_v2({name: node["x-bvbrc-proteome"] for name, node in props.items()})
    expected["required"] = list(required)
    legacy._plain_json(value)
    legacy.require(legacy.canonical(value) == legacy.canonical(expected), "form_noncanonical")
    return deepcopy(value)


def exact_decimal(value: str) -> dict:
    """Convert an already normalized decimal lexeme, without Decimal or float."""
    legacy.require(type(value) is str, "directional_decimal_invalid")
    match = re.fullmatch(r"([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?", value)
    legacy.require(match is not None, "directional_decimal_invalid")
    sign, whole, fraction, leading_fraction, exponent = match.groups()
    fraction = leading_fraction if whole is None else (fraction or "")
    coefficient = ((whole or "") + fraction).lstrip("0")
    power = int(exponent or "0") - len(fraction)
    if not coefficient:
        return {"sign": 0, "digits": [0], "exponent": 0}
    trailing = len(coefficient) - len(coefficient.rstrip("0"))
    coefficient = coefficient.rstrip("0")
    return {"sign": int(sign == "-"), "digits": [int(d) for d in coefficient], "exponent": power + trailing}


def validate_directional_fact(kind: str, value: dict, *, selector: dict | None = None) -> dict:
    """Enforce relationships lost when translated to the existing parent grammar.

    Exact equality to the authenticated saved projection remains the additional
    mandatory origin check in the return binder.
    """
    schemas = directional_fact_schemas()
    legacy.require(kind in schemas, "directional_fact_invalid")
    legacy._validate(schemas[kind], value, "directional_fact_invalid")
    def check(node):
        if type(node) is list:
            for item in node: check(item)
        elif type(node) is dict:
            if set(node) == {"sign", "digits", "exponent"}:
                digits = node["digits"]
                legacy.require((digits == [0] and node["sign"] == 0 and node["exponent"] == 0)
                    or (digits[0] != 0 and digits[-1] != 0), "directional_decimal_noncanonical")
            if "state" in node and "value" in node:
                legacy.require((node["state"] in {"value", "present", "position"}) == (node["value"] is not None), "directional_cell_conflict")
                if node["state"] is None and "reason_codes" in node:
                    legacy.require(not node["reason_codes"], "directional_cell_conflict")
            if set(node) == {"start", "end"}:
                legacy.require(node["end"] > node["start"], "directional_interval_invalid")
            if set(node) == {"block_key", "hsp_key"}:
                legacy.require((node["block_key"] is None) != (node["hsp_key"] is None), "directional_support_invalid")
            if set(node) == {"numerator", "denominator", "rendered_decimal"}:
                legacy.require(node["numerator"] <= node["denominator"] and node["rendered_decimal"]["sign"] == 0,
                               "directional_ratio_conflict")
            for key, item in node.items():
                if type(item) is str and item.startswith("bvbrc_proteome_") and ":" in item:
                    legacy.decode_reference(item)
                if key in {"query_symbol", "subject_symbol"}:
                    legacy.require(re.fullmatch(r"[A-Za-z*\-]", item) is not None, "directional_symbol_invalid")
                check(item)
    check(value)
    if "items" in value:
        returned = min(value["limit"], max(0, value["total_count"] - value["offset"]))
        legacy.require(value["returned_count"] == len(value["items"]) == returned, "directional_page_conflict")
        expected = value["offset"] + returned if value["offset"] + returned < value["total_count"] else None
        legacy.require(value["next_offset"] == expected, "directional_page_conflict")
    if kind == "directional_state":
        metric = value["quantity"]
        if metric == "body_complete":
            legacy.require(value["value_code"] is None, "directional_state_conflict")
        else:
            codes = next(metrics[metric] for metrics in STATE_METRICS.values() if metric in metrics)
            legacy.require(value["value_boolean"] is None and (value["value_code"] is None or value["value_code"] in codes), "directional_state_conflict")
    if "context" in value:
        context, quantity = value["context"], value.get("quantity")
        target = context["target"]
        legacy.require(bool(target["document_id"].strip()), "directional_target_conflict")
        if kind in {"directional_count", "directional_fraction", "directional_native_integer", "directional_native_decimal", "directional_coverage"}:
            cell = value["coverage"] if kind == "directional_coverage" else value["cell"]
            legacy.require((cell['state'] is None) == (context['value_ref'] is None), 'directional_cell_reference_conflict')
            if cell['state'] is not None:
                legacy.require(context['native_source_ref'] is not None and target['report_ordinal'] is not None,
                               'directional_cell_reference_conflict')
            expected = {"value": "available", "present": "available", "invalid": "invalid", "conflict": "incompatible"}.get(cell["state"], "unavailable")
            if kind == "directional_count":
                if quantity in TRACE_COUNTS and target["hsp_ordinal"] is not None:
                    unit = ("gap_run" if quantity.endswith("gap_runs") else "displayed_position" if quantity.endswith("non_gap_symbols")
                            else "alignment_column" if quantity in {"alignment_columns", "query_gap_columns", "subject_gap_columns"} else "paired_column")
                elif quantity.startswith("displayed_"): unit = quantity[len("displayed_"):-len("_count")] + "_occurrence"
                elif quantity in {"reported_paired_column_count", "reported_nonidentical_paired_count", "nonoverlapping_hsp_reported_identity_count"}: unit = "paired_column"
                elif quantity == "nonoverlapping_hsp_reported_alignment_columns": unit = "alignment_column"
                elif quantity == "repeated_pair_occurrence_count": unit = "pair_representation"
                else: unit = "coordinate_pair"
                legacy.require(cell["unit"] == unit, "directional_unit_conflict")
            if kind == "directional_fraction":
                pop = value["pair_population"]
                has_population = quantity in TRACE_FRACTIONS or quantity.startswith("compatible_unique_pair_")
                legacy.require((pop is not None) == has_population, "directional_population_conflict")
                if pop is not None and all(number is not None for number in pop.values()):
                    legacy.require(pop["total_pairs"] == pop["resolved_pairs"] + pop["unresolved_pairs"] + pop["stop_containing_pairs"], "directional_population_conflict")
            if kind == "directional_coverage" and cell["state"] == "value":
                legacy.require(value["count"]["state"] == "value" and value["reported_length"]["state"] == "present"
                    and cell["value"]["numerator"] == value["count"]["value"]
                    and cell["value"]["denominator"] == value["reported_length"]["value"], "directional_ratio_conflict")
            if kind in {"directional_native_integer", "directional_native_decimal"}:
                units = {"length": "aa", "letter_count": "aa", "sequence_count": "sequence_occurrence",
                    "bit_score": "bits", "bits": "bits", "expect": "expected_count", "evalue": "expected_count",
                    "raw_score": "native_raw_score", "expect_group_count": "native_expect_group_count"}
                unit = units.get(quantity, "percent" if quantity.endswith("printed_percent") else
                    "native_reported_integer" if quantity == "integer_value" else "native_reported_decimal"
                    if target["statistic_ordinal"] is not None else "alignment_column")
                legacy.require(value["unit"] == unit, "directional_unit_conflict")
                legacy.require((value["statistic_kind"] is not None) == (target["statistic_ordinal"] is not None and context["value_ref"] is not None),
                               "directional_statistic_conflict")
                if kind == "directional_native_decimal":
                    expectation = quantity in {"expect", "evalue"}
                    if expectation and cell["state"] is not None:
                        display = cell["state"] if cell["state"] != "present" else "invalid" if cell["value"]["sign"] else (
                            "printed_zero_precision_unknown" if cell["value"]["digits"] == [0] else "positive_reported_decimal")
                    else: display = None
                    legacy.require(value["expectation_display"] == display, "directional_expectation_conflict")
                    legacy.require((value["expect_group_count"] is not None) == (quantity == "expect" and target["hsp_ordinal"] is not None),
                                   "directional_expectation_conflict")
        elif kind == "directional_state":
            expected = "available" if value["value_boolean"] is not None or value["value_code"] is not None else "unavailable"
        elif kind == "directional_extremum":
            expected = {"value": "available", "invalid": "invalid"}.get(value["state"], "unavailable")
            raw = quantity == "maximum_reported_hsp_raw_score"
            if value["state"] == "value":
                selected_cell = value["native_integer"] if raw else value["native_decimal"]
                legacy.require(selected_cell is not None and selected_cell["state"] == "present"
                    and value["selected_operand_ref"] is not None and value["tied_hsp_count"] > 0, "directional_extremum_conflict")
            legacy.require((value["native_decimal"] is None if raw else value["native_integer"] is None), "directional_extremum_conflict")
        else:
            expected = "unavailable" if context["value_ref"] is None else "available"
        if context["declaration_state"] == "conflicting_version": expected = "incompatible"
        legacy.require(value["availability"] == expected, "directional_availability_conflict")
    if selector is not None:
        selected = validate_directional_selector(selector)
        legacy.require(selected["kind"] == kind, "directional_selector_conflict")
        if "metric" in selected and "quantity" in value:
            legacy.require(value["quantity"] == selected["metric"], "directional_selector_conflict")
        if "context" in value:
            target = value["context"]["target"]
            legacy.require(target["document_id"] == selected["document_id"] and all(
                target[k] == selected.get(k) for k in ORDINALS if k != "report_ordinal"), "directional_target_conflict")
    if kind == 'directional_requirements':
        refs = [row['requirement_ref'] for row in value['requirements']]
        legacy.require(len(refs) == len(set(refs)), 'directional_requirement_conflict')
    return deepcopy(value)


__all__ = ["requested_form_schema_v2", "validate_requested_form_v2", "validate_directional_selector",
           "directional_fact_schemas", "validate_directional_fact", "exact_decimal"]
