"""Deterministic minimap2 component calculations from saved placement sheets.

No sum of native scores or identities is an annotation confidence. Query-level
calculations describe the supplied reported placements and their overlaps; they
do not identify independent evidence, unmapped biology or absent functions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json

from .minimap2_grading_inputs import (
    COUNT_FIELDS, NATIVE_TAG_TYPES, PRESETS, SHEET_SCHEMA,
    _correspondence, _path, build_minimap2_placement_sheet, require_finite_json,
)


def _fraction(numerator, denominator):
    return numerator / denominator if numerator is not None and denominator not in (None, 0) else None


def _validate_sheet(sheet):
    error = "minimap2_sheet_components_invalid"
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("minimap2_placement_sheet_required")
    require_finite_json(sheet, "finite_json_minimap2_sheet_required")
    try:
        counts, facts, availability = sheet["measured_counts"], sheet["native_facts"], sheet["availability"]
        if (sheet["preset"] not in PRESETS or type(sheet["native_valid"]) is not bool
                or sheet["status"] not in {"complete", "partial", "invalid"}
                or type(sheet["issues"]) is not list or type(sheet["native_result"]) is not dict
                or type(counts) is not dict or set(counts) != set(COUNT_FIELDS)
                or any(value is not None and (type(value) is not int or value < 0) for value in counts.values())
                or type(availability["geometry"]) is not bool
                or type(sheet["native_tag_quantities"]) is not dict
                or set(sheet["native_tag_quantities"]) != set(NATIVE_TAG_TYPES)):
            raise ValueError(error)
        for role in ("query", "reference"):
            length = facts[role+"_length"]
            metadata = sheet["metadata"][role]
            if (length is not None and (type(length) is not int or length < 0)
                    or metadata["status"] not in {"valid", "invalid", "not_supplied"}
                    or metadata["length"] is not None and metadata["length"] != length
                    or metadata["status"] == "invalid" and metadata["length"] is not None):
                raise ValueError(error)
            interval = facts[role+"_interval"]
            if interval is not None and (type(interval) is not list or len(interval) != 2
                    or any(type(v) is not int for v in interval) or length is None
                    or not 0 <= interval[0] < interval[1] <= length):
                raise ValueError(error)
        for field in ("matching_bases", "block_length", "mapping_quality"):
            value = facts[field]
            if value is not None and (type(value) is not int or value < 0 or field == "mapping_quality" and value > 255):
                raise ValueError(error)
        for tag, type_ in NATIVE_TAG_TYPES.items():
            value = sheet["native_tag_quantities"][tag]
            if value is not None and type(value) not in ((int,) if type_ == "i" else (float, int)):
                raise ValueError(error)
        if availability["geometry"]:
            if not sheet["native_valid"] or facts["strand"] not in {"+", "-"}:
                raise ValueError(error)
            cg, cs = sheet["cg_operations"], sheet["cs_operations"]
            path = _path(cg) if cg else _path(cs, cs=True)
            if _correspondence(facts, path) != sheet["correspondence"]:
                raise ValueError(error)
            if cg and cs and _path(cg) != _path(cs, cs=True):
                raise ValueError(error)
            totals = {op: sum(item["length"] for item in path if item["operation"] == op) for op in "MIDN"}
            expected = {"paired_positions": totals["M"], "inserted_bases": totals["I"],
                "deleted_bases": totals["D"], "query_gap_columns": totals["D"],
                "reference_gap_columns": totals["I"], "reference_skipped_bases": totals["N"],
                "alignment_columns": totals["M"]+totals["I"]+totals["D"],
                "cs_equal_positions": sum(p["length"] for p in cs if p["operation"] in {"=", ":"}) if cs else None,
                "cs_substituted_positions": sum(p["length"] for p in cs if p["operation"] == "*") if cs else None}
            if counts != expected:
                raise ValueError(error)
            if totals["M"]+totals["I"] != facts["query_interval"][1]-facts["query_interval"][0]:
                raise ValueError(error)
            if totals["M"]+totals["D"]+totals["N"] != facts["reference_interval"][1]-facts["reference_interval"][0]:
                raise ValueError(error)
        elif sheet["correspondence"] or any(value is not None for value in counts.values()):
            raise ValueError(error)
        original = sheet["original_symbols"]
        if original["status"] == "available":
            values = [original["equal_positions"], original["substituted_positions"]]
            if (any(type(v) is not int or v < 0 for v in values) or counts["paired_positions"] != sum(values)
                    or any(sheet["metadata"][role]["sequence_status"] != "valid" for role in ("query", "reference"))):
                raise ValueError(error)
        elif original["equal_positions"] is not None or original["substituted_positions"] is not None:
            raise ValueError(error)
    except (KeyError, TypeError, IndexError, AttributeError) as exception:
        raise ValueError(error) from exception


def _definitions():
    native = {"query_length": ("query_length", "nucleotide_positions"),
        "reference_length": ("reference_length", "nucleotide_positions"),
        "native_matching_bases": ("matching_bases", "native_nonambiguous_matching_positions"),
        "native_block_length": ("block_length", "native_nonambiguous_alignment_columns"),
        "mapping_quality": ("mapping_quality", "native_phred_mapping_quality")}
    formulas = {"query_span": "query_interval[1] - query_interval[0]",
        "reference_span": "reference_interval[1] - reference_interval[0]",
        "paired_positions": "sum(length for path M, =, X; or cs =, :, *)",
        "inserted_bases": "sum(length for path I; or cs +)",
        "deleted_bases": "sum(length for path D; or cs -)",
        "query_gap_columns": "deleted_bases", "reference_gap_columns": "inserted_bases",
        "reference_skipped_bases": "sum(length for path N; or cs ~)",
        "alignment_columns": "paired_positions + inserted_bases + deleted_bases; excludes reference N skips",
        "cs_equal_positions": "sum(length for normalized cs = and :)",
        "cs_substituted_positions": "sum(length for normalized cs *)",
        "native_ambiguity_count": "native_tag_quantities.nn; never inferred from columns - block",
        "original_symbol_equal_positions": "original_symbols.equal_positions",
        "original_symbol_substituted_positions": "original_symbols.substituted_positions"}
    ratios = {"native_alignment_identity": ("native_matching_bases", "native_block_length"),
        "query_span_coverage": ("query_span", "query_length"),
        "reference_span_coverage": ("reference_span", "reference_length"),
        "query_paired_coverage": ("paired_positions", "query_length"),
        "reference_paired_coverage": ("paired_positions", "reference_length"),
        "query_aligned_coverage": ("paired_positions + inserted_bases", "query_length"),
        "reference_aligned_coverage": ("paired_positions + deleted_bases", "reference_length")}
    definitions = {}
    for field, (source, unit) in native.items():
        definitions[field] = {"inputs": ["native_facts."+source], "formula": "native_facts."+source,
            "units": unit, "kind": "native_measurement", "denominator": None,
            "population": "supplied_native_placement", "uncertainty": None,
            "missing": "null_when_missing_or_invalid" + ("_or_MAPQ_255" if field == "mapping_quality" else ""),
            "coordinate_system": None}
    for field, formula in formulas.items():
        source = ("native_tag_quantities.nn" if field == "native_ambiguity_count" else
                  "original_symbols" if field.startswith("original_symbol") else
                  "native_facts."+field.replace("span", "interval") if field.endswith("span") else
                  "measured_counts."+field)
        definitions[field] = {"inputs": [source], "formula": formula,
            "units": "alignment_columns" if field.endswith("columns") else "nucleotide_positions",
            "kind": "native_measurement" if field == "native_ambiguity_count" else "derived_from_supplied_data",
            "denominator": None, "population": "supplied_native_placement", "uncertainty": None,
            "missing": "null_when_required_native_path_tag_or_joined_symbols_unavailable",
            "coordinate_system": "zero_based_half_open_original_operands"}
    for field, (num, den) in ratios.items():
        role = "query" if field.startswith("query") else "reference"
        definitions[field] = {"inputs": [num, den] + (["metadata."+role] if field.endswith("coverage") else []),
            "formula": num+" / "+den, "units": "fraction", "kind": "derived_ratio",
            "denominator": "denominators."+field,
            "population": "full_"+role+"_operand" if field.endswith("coverage") else "native_nonambiguous_alignment_block",
            "uncertainty": None, "missing": "null_when_numerator_or_denominator_missing_invalid_or_denominator_zero",
            "coordinate_system": "zero_based_half_open_original_operands" if field.endswith("coverage") else None}
    native_units = {"AS": "native_DP_alignment_score", "ms": "native_max_segment_DP_score",
        "NM": "native_mismatches_and_gaps_including_ambiguity", "cm": "minimizers_on_chain",
        "s1": "native_chaining_score", "s2": "native_best_secondary_chain_score", "dv": "approximate_per_base_divergence",
        "de": "gap_compressed_per_base_divergence", "rl": "query_nucleotide_positions_with_repetitive_seeds",
        "zd": "native_Z_drop_bitmask", "nn": "ambiguous_alignment_columns"}
    for tag in NATIVE_TAG_TYPES:
        definitions["native_tag_quantities."+tag] = {"inputs": ["native_tag_quantities."+tag],
            "formula": "unchanged_native_tag_value", "native_type": NATIVE_TAG_TYPES[tag], "units": native_units[tag],
            "kind": "native_measurement", "denominator": None, "population": "supplied_native_placement",
            "uncertainty": None, "missing": "null_when_tag_missing_wrong_type_or_invalid", "coordinate_system": None}
    return definitions


def calculate_minimap2_placement_scores(sheet: dict) -> dict:
    """Calculate separately inspectable placement components, with no acquisition."""
    _validate_sheet(sheet)
    facts, counts = sheet["native_facts"], sheet["measured_counts"]
    spans = {role+"_span": facts[role+"_interval"][1]-facts[role+"_interval"][0]
             if facts[role+"_interval"] is not None else None for role in ("query", "reference")}
    numerators = {"native_alignment_identity": facts["matching_bases"]}
    denominators = {"native_alignment_identity": facts["block_length"]}
    for role, gaps in (("query", "inserted_bases"), ("reference", "deleted_bases")):
        for kind in ("span", "paired", "aligned"):
            field = role+"_"+kind+"_coverage"
            numerators[field] = (spans[role+"_span"] if kind == "span" else counts["paired_positions"]
                if kind == "paired" else counts["paired_positions"]+counts[gaps]
                if counts["paired_positions"] is not None and counts[gaps] is not None else None)
            denominators[field] = sheet["metadata"][role]["length"]
    result = {"schema": "minimap2_placement_scores_v1", "status": sheet["status"],
        "preset": sheet["preset"], "native_version": sheet["native_version"],
        "query_length": facts["query_length"], "reference_length": facts["reference_length"], **spans, **counts,
        "native_matching_bases": facts["matching_bases"], "native_block_length": facts["block_length"],
        "native_ambiguity_count": sheet["native_tag_quantities"]["nn"],
        "mapping_quality": facts["mapping_quality"] if facts["mapping_quality"] != 255 else None,
        "native_alignment_identity_kind": sheet["availability"]["native_identity_kind"],
        "original_symbol_equal_positions": sheet["original_symbols"]["equal_positions"],
        "original_symbol_substituted_positions": sheet["original_symbols"]["substituted_positions"],
        **{field: _fraction(value, denominators[field]) for field, value in numerators.items()},
        "native_tag_quantities": deepcopy(sheet["native_tag_quantities"]),
        "numerators": numerators, "denominators": denominators, "definitions": _definitions(),
        "issues": deepcopy(sheet["issues"])}
    require_finite_json(result, "finite_json_minimap2_scores_required")
    return result


def grade_minimap2_placement(native: dict, *, preset: str, native_version: str | None,
        query_metadata: dict | None = None, reference_metadata: dict | None = None) -> dict:
    sheet = build_minimap2_placement_sheet(native, preset=preset, native_version=native_version,
        query_metadata=query_metadata, reference_metadata=reference_metadata)
    return {"sheet": sheet, "scores": calculate_minimap2_placement_scores(sheet)}


def _union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if start == end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return merged


def _size(intervals):
    return sum(end-start for start, end in intervals)


def _correspondence_repetition(segments):
    """Sweep affine correspondence segments without allocating one item per base.

    A correspondence key is exact reference identity, strand, and r = a*q+b.
    Equal keys repeated across rows are repeated observations. Distinct keys at
    the same original query position are alternative reported correspondences.
    """
    events = defaultdict(list)
    for key, start, end in segments:
        events[start].append((key, 1))
        events[end].append((key, -1))
    active = Counter()
    previous = None
    repeated_positions = alternative_positions = observation_count = distinct_count = 0
    for position in sorted(events):
        if previous is not None:
            width = position-previous
            observation_count += width*sum(active.values())
            distinct_count += width*len(active)
            repeated_positions += width*any(count > 1 for count in active.values())
            alternative_positions += width*(len(active) > 1)
        for key, change in events[position]:
            active[key] += change
            if active[key] == 0:
                del active[key]
        previous = position
    return {"paired_position_observation_count": observation_count,
        "distinct_correspondence_count": distinct_count,
        "repeated_correspondence_count": observation_count-distinct_count,
        "repeated_correspondence_positions": repeated_positions,
        "alternative_correspondence_positions": alternative_positions}


def calculate_minimap2_query_scores(sheets, *, query_metadata: dict, output_complete: bool | None) -> dict:
    """Summarize one exact query's supplied rows, retaining missing/invalid counts.

    Iteration is over one query only. Missing rows can be represented by None;
    malformed sheets and mismatched query identities are counted and excluded
    from joined unions. Failed/partial/unknown acquisition is declared through
    output_complete, and never establishes biological absence.
    """
    require_finite_json(query_metadata, "finite_json_minimap2_query_metadata_required")
    if (type(query_metadata) is not dict or type(query_metadata.get("name")) is not str or not query_metadata["name"]
            or type(query_metadata.get("length")) is not int or query_metadata["length"] < 0):
        raise ValueError("minimap2_query_metadata_identity_required")
    if output_complete is not None and type(output_complete) is not bool:
        raise ValueError("minimap2_output_complete_boolean_required")
    qlength = query_metadata["length"]
    issues, spans, paired, correspondence_segments = [], [], [], []
    categories, strands, references, duplicate_rows = Counter(), Counter(), {}, defaultdict(list)
    invalid = missing = geometry_missing = joined_invalid = received = valid = 0
    presets, versions = set(), set()
    for index, sheet in enumerate(sheets):
        received += 1
        if sheet is None:
            missing += 1
            issues.append({"code": "placement_sheet_missing", "row_index": index})
            continue
        try:
            _validate_sheet(sheet)
        except ValueError as error:
            invalid += 1
            issues.append({"code": str(error), "row_index": index})
            continue
        facts = sheet["native_facts"]
        if not sheet["native_valid"]:
            invalid += 1
            issues.append({"code": "placement_native_record_invalid", "row_index": index})
            continue
        if facts["query_name"] != query_metadata["name"] or facts["query_length"] != qlength:
            invalid += 1
            issues.append({"code": "query_metadata_identity_mismatch", "row_index": index,
                           "native_name": facts["query_name"], "native_length": facts["query_length"]})
            continue
        valid += 1
        presets.add(sheet["preset"])
        versions.add(sheet["native_version"])
        categories[sheet["native_alignment_type"] or "missing_or_invalid"] += 1
        strands[facts["strand"]] += 1
        reference_key = (facts["reference_name"], facts["reference_length"])
        reference = references.setdefault(reference_key, {"reference_name": reference_key[0],
            "reference_length": reference_key[1], "placement_count": 0, "span_intervals": [],
            "paired_intervals": [], "query_span_intervals": [], "query_paired_intervals": [],
            "geometry_missing_count": 0, "metadata_invalid_count": 0})
        reference["placement_count"] += 1
        # A retained PAF row is an exact duplicate independently of its locator.
        native = sheet["native_result"]
        key = native.get("native_line")
        if key is None:
            fields = ("query_name", "query_length", "query_interval", "strand", "reference_name",
                "reference_length", "reference_interval", "matching_bases", "block_length", "mapping_quality", "tags")
            key = json.dumps({field: native[field] for field in fields}, sort_keys=True, separators=(",", ":"))
        duplicate_rows[key].append(index)
        if sheet["metadata"]["query"]["status"] == "invalid":
            joined_invalid += 1
            issues.append({"code": "query_sheet_metadata_join_invalid", "row_index": index})
            continue
        spans.append(facts["query_interval"])
        reference["query_span_intervals"].append(facts["query_interval"])
        reference["span_intervals"].append(facts["reference_interval"])
        if sheet["metadata"]["reference"]["status"] == "invalid":
            reference["metadata_invalid_count"] += 1
        if not sheet["availability"]["geometry"]:
            geometry_missing += 1
            reference["geometry_missing_count"] += 1
            continue
        for part in sheet["correspondence"]:
            if part["operation"] != "M":
                continue
            qi, ri = part["query_interval"], part["reference_interval"]
            paired.append(qi)
            reference["query_paired_intervals"].append(qi)
            reference["paired_intervals"].append(ri)
            direction = part["query_step"]
            intercept = ri[0]-qi[0] if direction == 1 else ri[0]+qi[1]-1
            correspondence_segments.append(((reference_key, facts["strand"], direction, intercept), *qi))
    span_union, paired_union = _union(spans), _union(paired)
    complete_geometry = invalid == missing == geometry_missing == joined_invalid == 0
    observed_repetition = _correspondence_repetition(correspondence_segments)
    duplicates = [{"row_indices": indices, "count": len(indices)} for indices in duplicate_rows.values() if len(indices) > 1]
    reference_rows = []
    name_lengths = defaultdict(set)
    for key, row in sorted(references.items()):
        name_lengths[key[0]].add(key[1])
        for name in ("span_intervals", "paired_intervals", "query_span_intervals", "query_paired_intervals"):
            row[name] = _union(row[name])
            row[name.replace("intervals", "union_positions")] = _size(row[name])
        row["span_union_coverage"] = _fraction(row["span_union_positions"], row["reference_length"]) if not row["metadata_invalid_count"] else None
        row["paired_union_coverage"] = (_fraction(row["paired_union_positions"], row["reference_length"])
            if not row["metadata_invalid_count"] and not row["geometry_missing_count"] else None)
        row["observed_paired_union_positions"] = row["paired_union_positions"]
        if row["geometry_missing_count"]:
            row["paired_union_positions"] = None
            row["query_paired_union_positions"] = None
        reference_rows.append(row)
    for name, lengths in sorted(name_lengths.items()):
        if len(lengths) > 1:
            issues.append({"code": "reference_name_has_multiple_lengths", "reference_name": name, "lengths": sorted(lengths)})
    # Count means valid supplied placement records, even when output is partial.
    meaning = ("complete_output_has_zero_reported_placements_not_biological_absence"
               if output_complete is True and received == 0 else
               "reported_placements_from_complete_output_not_independent_evidence"
               if output_complete is True and invalid == missing == 0 else
               "reported_placements_from_partial_or_unknown_output_no_absence_inference")
    result = {"schema": "minimap2_query_scores_v1", "query_metadata": deepcopy(query_metadata),
        "query_name": query_metadata["name"], "query_length": qlength, "output_complete": output_complete,
        "result_meaning": meaning, "received_sheet_count": received, "reported_placement_count": valid,
        "invalid_sheet_count": invalid, "missing_sheet_count": missing,
        "metadata_invalid_count": joined_invalid, "geometry_missing_count": geometry_missing,
        "counts_by_native_alignment_type": dict(categories), "counts_by_strand": dict(strands),
        "counts_by_reference": [{"reference_name": row["reference_name"], "reference_length": row["reference_length"],
                                 "count": row["placement_count"]} for row in reference_rows],
        "distinct_reference_count": len(references), "selected_presets": sorted(presets),
        "native_versions": sorted(versions, key=lambda v: (v is not None, v or "")),
        "query_span_intervals": span_union, "query_span_union_positions": _size(span_union),
        "query_paired_intervals": paired_union,
        "query_paired_union_positions": _size(paired_union) if complete_geometry else None,
        "observed_query_paired_union_positions": _size(paired_union),
        "query_span_union_coverage": _fraction(_size(span_union), qlength) if not joined_invalid else None,
        "query_paired_union_coverage": _fraction(_size(paired_union), qlength) if complete_geometry else None,
        "union_population": "valid_supplied_placements_with_available_component_data",
        "paired_union_complete_for_supplied_rows": complete_geometry,
        "per_reference": reference_rows, "exact_duplicate_row_groups": duplicates,
        "exact_duplicate_row_count": sum(group["count"]-1 for group in duplicates),
        **{field: value if complete_geometry else None for field, value in observed_repetition.items()},
        "observed_geometry_subset": observed_repetition, "issues": issues,
        "definitions": {
            "reported_placement_count": "count(valid supplied rows matching exact query name and length)",
            "union_positions": "size of zero-based half-open interval union; repeated bases counted once",
            "coverage": "corresponding union positions / entire operand length; zero denominator gives null",
            "exact_duplicate_row_count": "sum(group size - 1) for exact retained PAF rows excluding row locators",
            "distinct_correspondence_count": "number of distinct (query position, exact reference identity, reference position, strand) tuples",
            "repeated_correspondence_count": "paired_position_observation_count - distinct_correspondence_count",
            "repeated_correspondence_positions": "query positions having the same exact correspondence reported more than once",
            "alternative_correspondence_positions": "query positions having more than one distinct reported correspondence",
            "uncertainty": None,
            "missing": "repetition scalars null if any supplied row lacks usable geometry; observed subset remains separately labeled",
            "population": "supplied placements for this exact query; output completeness is separately declared",
            "units": "counts_of_rows_references_or_nucleotide_positions_as_named",
            "coordinate_system": "zero_based_half_open_original_operands"}}
    require_finite_json(result, "finite_json_minimap2_query_scores_required")
    return result


__all__ = ["calculate_minimap2_placement_scores", "grade_minimap2_placement", "calculate_minimap2_query_scores"]
