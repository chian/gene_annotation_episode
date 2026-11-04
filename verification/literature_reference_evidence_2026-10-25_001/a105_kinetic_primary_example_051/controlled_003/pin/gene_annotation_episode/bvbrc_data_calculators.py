"""Inspectable deterministic numerical components for saved BV-BRC sheets.

Page/count/facet quantities describe acquired documents, not annotation
confidence. Sequence counts describe only explicitly supplied join pages.
No network, subprocess, source lookup, expression statistic or W05 aggregation
is performed here. Recalculation neither reacquires data nor changes history.
"""
from __future__ import annotations

import math

from .bvbrc_data_readers import validate_data_sheet
from .bvbrc_data_schema import schema, validate

__all__ = (
    "PAGE_COMPONENTS_SCHEMA", "FACET_COMPONENTS_SCHEMA", "calculate_page_counts",
    "calculate_facet_fractions", "calculate_feature_sequence_counts",
)

PAGE_COMPONENTS_SCHEMA = schema("PageComponents")
FACET_COMPONENTS_SCHEMA = schema("FacetComponents")
_DENOMINATOR_POLICY = "same_response_exact_document_count"


def calculate_page_counts(sheet: dict) -> dict:
    """Count all native occurrences, keeping the native population separate.

    Partial and invalid rows each contribute one to invalid_row_count. The
    population count is the native report, even when qualification makes its
    use as an exact denominator unavailable. No length(docs) substitution.
    """
    sheet = validate_data_sheet(sheet)
    count, population = sheet["count"], sheet["population"]
    if (count["reported_value"] != population["reported_total"]
            or count["exactness"] != population["exactness"]
            or sheet["page"]["reported_total"] != population["reported_total"]
            or sheet["page"]["count_exactness"] != population["exactness"]):
        raise ValueError("bvbrc_inconsistent_population_fields")
    valid = sum(row["status"] == "valid" for row in sheet["rows"])
    return validate("PageComponents", {
        "version": "bvbrc_data_page_components_v1", "native_row_count": len(sheet["rows"]),
        "valid_row_count": valid, "invalid_row_count": len(sheet["rows"]) - valid,
        "reported_population_count": population["reported_total"],
        "population_exactness": population["exactness"],
    })


def _denominator_reason(sheet, facet):
    count, population, page, qualification = (
        sheet["count"], sheet["population"], sheet["page"], sheet["qualification"])
    if (facet["population_key"] != population["population_key"]
            or count["population_key"] != population["population_key"]
            or count["reported_value"] != population["reported_total"]
            or page["reported_total"] != population["reported_total"]
            or count["exactness"] != population["exactness"]
            or page["count_exactness"] != population["exactness"]
            or count["native_location"] != population["native_location"]
            or any(issue["code"] == "bvbrc_population_metadata_conflict"
                   for issue in sheet["issues"] + facet["issues"])):
        return "population_conflict"
    if not qualification["population_metadata_valid"]:
        return count["reason"] or "population_conflict"
    if not qualification["service_matches"] or not qualification["request_matches"]:
        return "incompatible_input"
    if not qualification["transport_complete"] or not sheet["transport"]["body_complete"]:
        return "transport_incomplete"
    if qualification["native_partial_results"]:
        return "native_partial_results"
    if not qualification["http_success"] or not qualification["format_valid"]:
        return "native_value_invalid"
    if count["availability"] != "available":
        return count["reason"] or "unknown_denominator"
    if count["reported_value"] is None:
        return "unknown_denominator"
    if (count["exactness"] != "exact" or population["native_num_found_exact"] is not True
            or population["native_location"] != "/response/numFound"
            or sheet["custody"]["native_profile"] != "solr_json_envelope_v1"):
        return "inexact_population"
    if count["reported_value"] == 0:
        return "empty_population"
    return None


def calculate_facet_fractions(sheet: dict, *, denominator_policy: str) -> dict:
    """Return bucket documents / same-response exact matching documents.

    Numerators and denominators remain inspectable even when the fraction is
    unavailable. Multivalued buckets may overlap; their counts are never summed
    to construct a denominator. Zero population is unavailable, not zero.
    """
    if denominator_policy != _DENOMINATOR_POLICY:
        raise ValueError("bvbrc_unsupported_denominator_policy")
    sheet = validate_data_sheet(sheet)
    if sheet["mode"] != "facet":
        raise ValueError("bvbrc_incompatible_input")
    fractions = []
    for facet in sheet["facets"]:
        reason = _denominator_reason(sheet, facet)
        denominator = sheet["population"]["reported_total"]
        for bucket in facet["buckets"]:
            numerator = bucket["count"]
            unavailable = reason
            fraction = None
            if bucket["status"] != "valid" or numerator is None or bucket["term"] is None:
                unavailable = "native_value_invalid"
            if unavailable is None and numerator > denominator:
                unavailable = "population_conflict"
            if unavailable is None:
                try:
                    fraction = numerator / denominator
                    if not math.isfinite(fraction) or fraction == 0 and numerator != 0:
                        unavailable, fraction = "unrepresentable_numeric_value", None
                except OverflowError:
                    unavailable = "unrepresentable_numeric_value"
            fractions.append({"bucket_key": bucket["bucket_key"], "numerator": numerator,
                              "denominator": denominator, "fraction": fraction, "reason": unavailable})
    return validate("FacetComponents", {
        "version": "bvbrc_data_facet_components_v1", "denominator_policy": denominator_policy,
        "population_key": sheet["population"]["population_key"], "fractions": fractions,
    })


def calculate_feature_sequence_counts(join_sheet: dict) -> dict:
    """Count selected occurrences/relations, never independent evidence.

    Distinct joined sequences use (kind, exact native MD5) for joined or
    repeated-identical edges only. Retained feature rows count distinct selected
    occurrences across AA/NA edges. Native sequence rows count every supplied
    sequence-page occurrence, including unused rows. Missing-key and
    missing-record counts count those exact edge statuses; conflicts include
    incompatible native sequence kinds. Other missing states remain explicit
    on the saved edges and are not silently reclassified.
    """
    sheet = validate("FeatureSequenceSheet", join_sheet)
    pages = {}
    for page in sheet["input_page_counts"]:
        key = (page["native_sha256"], page["collection"])
        if key in pages or page["valid_row_count"] > page["retained_row_count"]:
            raise ValueError("bvbrc_invalid_input_page_counts")
        if page["collection"] not in ("genome_feature", "feature_sequence"):
            raise ValueError("bvbrc_incompatible_input")
        pages[key] = page
    if set(sheet["input_native_sha256s"]) != {key[0] for key in pages}:
        raise ValueError("bvbrc_invalid_input_page_counts")
    selected = sheet["selection"]
    allowed_kinds = {"AA", "NA"} if selected["sequence_kind"] == "both" else {selected["sequence_kind"]}
    feature_rows, edge_keys, occurrences, represented, joined = set(), set(), set(), set(), []
    for edge in sheet["edges"]:
        if (edge["edge_key"] in edge_keys or edge["feature_id"] not in selected["feature_ids"]
                or edge["sequence_kind"] not in allowed_kinds
                or len(edge["feature_rows"]) != (0 if edge["join_status"] == "missing_feature" else 1)):
            raise ValueError("bvbrc_invalid_feature_sequence_edge")
        edge_keys.add(edge["edge_key"])
        occurrence = (edge["feature_id"], edge["sequence_kind"],
                      tuple((row["native_sha256"], row["row_key"]) for row in edge["feature_rows"]))
        if occurrence in occurrences:
            raise ValueError("bvbrc_duplicate_feature_sequence_relation")
        occurrences.add(occurrence)
        represented.add((edge["feature_id"], edge["sequence_kind"]))
        for locations, collection in ((edge["feature_rows"], "genome_feature"),
                                      (edge["sequence_rows"], "feature_sequence")):
            for row in locations:
                page = pages.get((row["native_sha256"], collection))
                prefix = row["native_sha256"] + "/row/"
                ordinal = row["row_key"].removeprefix(prefix)
                if (row["collection"] != collection or page is None
                        or not row["row_key"].startswith(prefix) or not ordinal.isascii()
                        or not ordinal.isdigit() or str(int(ordinal)) != ordinal
                        or int(ordinal) >= page["retained_row_count"]):
                    raise ValueError("bvbrc_invalid_feature_sequence_location")
        feature_rows.update((row["native_sha256"], row["row_key"]) for row in edge["feature_rows"])
        if edge["join_status"] in ("joined", "repeated_identical"):
            if (edge["native_md5"] is None or not edge["sequence_rows"] or edge["sequence_length"] is None
                    or edge["raw_md5_match"] is not True or edge["reason"] is not None):
                raise ValueError("bvbrc_invalid_feature_sequence_edge")
            joined.append(edge)
        if edge["length_match"] is not None:
            if (edge["sequence_length"] is None or edge["feature_length"] is None
                    or edge["length_match"] != (edge["sequence_length"] == edge["feature_length"])):
                raise ValueError("bvbrc_invalid_length_agreement")
    if represented != {(feature, kind) for feature in selected["feature_ids"] for kind in allowed_kinds}:
        raise ValueError("bvbrc_missing_selected_feature_relation")
    return validate("FeatureSequenceComponents", {
        "version": "bvbrc_feature_sequence_components_v1",
        "selected_feature_count": len(selected["feature_ids"]),
        "retained_feature_row_count": len(feature_rows),
        "native_sequence_record_count": sum(page["retained_row_count"] for key, page in pages.items()
                                            if key[1] == "feature_sequence"),
        "distinct_joined_aa_sequence_count": len({edge["native_md5"] for edge in joined if edge["sequence_kind"] == "AA"}),
        "distinct_joined_na_sequence_count": len({edge["native_md5"] for edge in joined if edge["sequence_kind"] == "NA"}),
        "relation_count": len(joined),
        "missing_key_count": sum(edge["join_status"] == "missing_key" for edge in sheet["edges"]),
        "missing_record_count": sum(edge["join_status"] == "missing_record" for edge in sheet["edges"]),
        "conflicting_relation_count": sum(edge["join_status"] in ("conflict", "type_mismatch") for edge in sheet["edges"]),
        "length_agreement_count": sum(edge["length_match"] is True for edge in joined),
    })
