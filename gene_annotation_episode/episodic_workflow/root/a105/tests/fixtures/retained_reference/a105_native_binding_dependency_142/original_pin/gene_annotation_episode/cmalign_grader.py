"""Deterministic numerical components from saved cmalign_sheet_v1 data.

This module never parses retained native text. Counts/bounds are extracted by
cmalign_inputs; this calculator validates their relationships, selects explicit
populations and computes ratios. Native avg pp, scientific components and timing
remain separate. No annotation or combined confidence score is defined.
"""
from __future__ import annotations

from copy import deepcopy

from .hmmalign_inputs import require_finite_json

_COUNTS = ("retained_nucleotides", "model_match_nucleotides", "model_gap_positions",
    "missing_model_positions", "nonresidue_model_positions", "retained_insert_nucleotides",
    "retained_local_end_nucleotides", "deleted_model_positions", "local_end_skipped_model_positions",
    "total_insert_nucleotides", "total_local_end_nucleotides", "omitted_nucleotides")


def _count(x, nullable=False):
    return x is None and nullable or type(x) is int and x >= 0


def _ratio(n, d):
    return n/d if n is not None and d is not None and d > 0 else None


def _validate_row(row):
    try:
        if (type(row) is not dict or type(row["record_key"]) is not str or
                row["origin"] not in {"newly_aligned", "inherited", "unknown"} or
                any(not _count(row["measurements"][k], True) for k in _COUNTS) or
                not _count(row["mapping"]["original_length"], True) or not _count(row["model_length"], True)):
            raise ValueError("cmalign_sequence_sheet_invalid")
        counts, pp = row["measurements"], row["posterior"]
        if any(type(row["availability"][k]) is not bool for k in ("alignment_geometry", "model_mapping", "original_mapping", "pp", "true_deletions")):
            raise ValueError("cmalign_sequence_availability_invalid")
        native = row["native_scores"]
        if native is not None:
            if type(native) is not dict:
                raise ValueError("cmalign_native_scores_invalid")
            for name in ("bit_score", "avg_pp", "band_seconds", "alignment_seconds", "total_seconds", "matrix_mb"):
                v = native.get(name)
                if v is not None and (type(v) not in (int, float) or name != "bit_score" and v < 0 or name == "avg_pp" and v > 1):
                    raise ValueError("cmalign_native_scores_invalid")
        if counts["model_match_nucleotides"] is not None:
            for k in ("retained_insert_nucleotides", "retained_local_end_nucleotides", "model_gap_positions",
                      "missing_model_positions", "nonresidue_model_positions"):
                if counts[k] is None:
                    raise ValueError("cmalign_sequence_count_relationship_invalid")
            if sum(counts[k] for k in ("model_match_nucleotides", "retained_insert_nucleotides", "retained_local_end_nucleotides")) != counts["retained_nucleotides"]:
                raise ValueError("cmalign_sequence_count_relationship_invalid")
            if row["model_length"] is not None and sum(counts[k] for k in
                    ("model_match_nucleotides", "model_gap_positions", "missing_model_positions", "nonresidue_model_positions")) != row["model_length"]:
                raise ValueError("cmalign_model_count_relationship_invalid")
        if counts["deleted_model_positions"] is not None and counts["deleted_model_positions"] != counts["model_gap_positions"]:
            raise ValueError("cmalign_deletion_count_relationship_invalid")
        for field in ("retained_nucleotide_population", "available_count", "unavailable_count", "lower_sum_hundredths", "upper_sum_hundredths"):
            if not _count(pp[field]):
                raise ValueError("cmalign_posterior_sheet_invalid")
        bins = pp["bin_counts"]
        if (type(bins) is not dict or any(k not in "0123456789*" or len(k) != 1 or not _count(v) for k,v in bins.items())
                or sum(bins.values()) != pp["available_count"]
                or pp["available_count"]+pp["unavailable_count"] != pp["retained_nucleotide_population"]):
            raise ValueError("cmalign_posterior_sheet_invalid")
        lower = sum((95 if k == "*" else max(0, 10*int(k)-5))*v for k,v in bins.items())
        upper = sum((100 if k == "*" else 10*int(k)+5)*v for k,v in bins.items())
        if (lower != pp["lower_sum_hundredths"] or upper != pp["upper_sum_hundredths"] or
                pp["upper_inclusive"] is not (bool(pp["available_count"]) and set(bins) == {"*"}) or
                counts["retained_nucleotides"] is not None and pp["retained_nucleotide_population"] != counts["retained_nucleotides"]):
            raise ValueError("cmalign_posterior_sheet_invalid")
        if row["availability"]["original_mapping"]:
            positions, omitted = row["mapping"]["positions"], row["mapping"]["omitted_original_positions"]
            length = row["mapping"]["original_length"]
            if (type(positions) is not list or type(omitted) is not list or length is None or
                    positions != sorted(set(positions)) or omitted != sorted(set(omitted)) or
                    any(not _count(x) or x == 0 for x in positions+omitted) or
                    set(positions) & set(omitted) or sorted(positions+omitted) != list(range(1, length+1)) or
                    len(positions) != counts["retained_nucleotides"] or len(omitted) != counts["omitted_nucleotides"]):
                raise ValueError("cmalign_original_mapping_relationship_invalid")
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("cmalign_sequence_sheet_invalid") from exc


def _score_row(row):
    _validate_row(row)
    result = {k: deepcopy(row[k]) for k in ("record_key", "alignment_key", "name", "occurrence", "origin",
        "locator", "availability", "mapping", "inherited_join", "issues")}
    result["native_name"] = row.get("native_name", row["name"])
    result["name_mapping"] = deepcopy(row.get("name_mapping"))
    counts, pp, score = row["measurements"], row["posterior"], row["native_scores"] or {}
    result.update(deepcopy(counts))
    result.update(original_length=row["mapping"]["original_length"], model_length=row["model_length"],
        native_bit_score=score.get("bit_score"), native_avg_pp=score.get("avg_pp"),
        native_index=score.get("native_index"), cm_from=score.get("cm_from"), cm_to=score.get("cm_to"),
        truncation=score.get("truncation"), timing={k: score.get(k) for k in
            ("band_seconds", "alignment_seconds", "total_seconds", "matrix_mb")},
        posterior_available_count=pp["available_count"], posterior_unavailable_count=pp["unavailable_count"],
        posterior_bin_counts=deepcopy(pp["bin_counts"]), posterior_population=pp["population"],
        posterior_lower_mean=_ratio(pp["lower_sum_hundredths"], 100*pp["available_count"]),
        posterior_upper_mean=_ratio(pp["upper_sum_hundredths"], 100*pp["available_count"]),
        posterior_lower_inclusive=True if pp["available_count"] else None,
        posterior_upper_inclusive=pp["upper_inclusive"] if pp["available_count"] else None)
    n = counts["model_match_nucleotides"] if row["availability"]["model_mapping"] else None
    coverage_n = n if row["availability"]["original_mapping"] else None
    result["model_occupancy"] = _ratio(n, row["model_length"])
    result["sequence_matched_coverage"] = _ratio(coverage_n, row["mapping"]["original_length"])
    result["numerators"] = {"model_occupancy": n, "sequence_matched_coverage": coverage_n,
        "posterior_lower_mean": pp["lower_sum_hundredths"]/100,
        "posterior_upper_mean": pp["upper_sum_hundredths"]/100}
    result["denominators"] = {"model_occupancy": row["model_length"],
        "sequence_matched_coverage": row["mapping"]["original_length"],
        "posterior_lower_mean": pp["available_count"], "posterior_upper_mean": pp["available_count"]}
    result["unavailable"] = {k: "required_native_data_or_validated_geometry_unavailable"
                             for k in (*_COUNTS, "native_bit_score", "native_avg_pp", "original_length", "model_length",
                                 "model_occupancy", "sequence_matched_coverage", "posterior_lower_mean", "posterior_upper_mean")
                             if result[k] is None}
    if result["deleted_model_positions"] is None:
        result["unavailable"]["deleted_model_positions"] = "rendered_gaps_do_not_distinguish_deleted_from_unvisited_model_positions"
    if result["local_end_skipped_model_positions"] is None:
        result["unavailable"]["local_end_skipped_model_positions"] = "native_ifile_elfile_report_emissions_not_skipped_model_state_traceback"
    result["status"] = "partial" if row["issues"] or not row["availability"]["alignment_geometry"] else "available"
    return result


def _validate_population(group, allowed):
    if (type(group) is not dict or not _count(group.get("row_count")) or
            type(group.get("record_keys")) is not list or any(type(k) is not str for k in group["record_keys"]) or
            len(set(group["record_keys"])) != group["row_count"] or
            len(group["record_keys"]) != group["row_count"] or type(group.get("counts")) is not dict or
            any(k not in allowed or not _count(v) for k,v in group["counts"].items()) or
            sum(group["counts"].values()) != group["row_count"]):
        raise ValueError("cmalign_population_sheet_invalid")


def _score_population(row, population, *, pair=False):
    allowed = {"canonical", "noncanonical", "ambiguous", "gap", "missing", "nonresidue", "unavailable"} if pair else {
        "residue", "gap", "missing", "nonresidue", "unavailable"}
    result = deepcopy(row)
    if type(row.get("populations")) is not dict or set(row["populations"]) != {"all", "newly_aligned", "inherited", "unknown"}:
        raise ValueError("cmalign_population_sheet_invalid")
    for group in result["populations"].values():
        _validate_population(group, allowed)
        c = group["counts"]
        if pair:
            group.update(observed_two_nucleotide_pairs=c.get("canonical", 0)+c.get("noncanonical", 0)+c.get("ambiguous", 0),
                canonical_pairs=c.get("canonical", 0), noncanonical_pairs=c.get("noncanonical", 0),
                unambiguous_pair_denominator=c.get("canonical", 0)+c.get("noncanonical", 0),
                excluded={k: c.get(k, 0) for k in ("gap", "missing", "ambiguous", "nonresidue", "unavailable")})
            group["canonical_pair_fraction"] = _ratio(group["canonical_pairs"], group["unambiguous_pair_denominator"])
        else:
            group.update(occupancy_numerator=c.get("residue", 0), occupancy_denominator=c.get("residue", 0)+c.get("gap", 0),
                missing_rows=c.get("missing", 0), nonresidue_rows=c.get("nonresidue", 0), unavailable_rows=c.get("unavailable", 0))
            group["occupancy"] = _ratio(group["occupancy_numerator"], group["occupancy_denominator"])
    all_keys = set(result["populations"]["all"]["record_keys"])
    group_keys = [k for name in ("newly_aligned", "inherited", "unknown") for k in result["populations"][name]["record_keys"]]
    if len(group_keys) != len(set(group_keys)) or set(group_keys) != all_keys:
        raise ValueError("cmalign_population_membership_invalid")
    for category in allowed:
        if result["populations"]["all"]["counts"].get(category, 0) != sum(result["populations"][name]["counts"].get(category, 0)
                for name in ("newly_aligned", "inherited", "unknown")):
            raise ValueError("cmalign_population_count_relationship_invalid")
    result["population"] = population
    result.update(deepcopy(result["populations"][population]))
    return result


def _definitions():
    definitions = {}
    def add(key, inputs, formula, units, population, denominator=None, uncertainty=None,
            missing="null_when_required_data_or_validated_geometry_is_unavailable", kind="derived"):
        definitions[key] = {"inputs": inputs, "formula_or_native_source": formula, "units": units,
            "population": population, "denominator": denominator,
            "coordinate_convention": "alignment_columns_zero_based; sequence_and_model_positions_one_based",
            "uncertainty": uncertainty, "missing_behavior": missing, "kind": kind}
    descriptions = {
        "retained_nucleotides": "count RNA nucleotide or ambiguity letters in native aligned row",
        "model_match_nucleotides": "count nucleotide letters at RF consensus positions",
        "model_gap_positions": "count - . _ at RF consensus positions; includes unvisited positions, not automatically D states",
        "missing_model_positions": "count native sequence ~ at RF consensus positions; does not include RF ~ EL columns",
        "nonresidue_model_positions": "count native sequence * at RF consensus positions; not an observed nucleotide",
        "retained_insert_nucleotides": "count nucleotide letters at RF . - _ IL/IR columns",
        "retained_local_end_nucleotides": "count nucleotide letters at RF ~ EL columns",
        "deleted_model_positions": "model_gap_positions only with explicit global and notrunc, no submodel truncation, no native contradiction, and validated model geometry",
        "local_end_skipped_model_positions": "zero in explicit global nontruncated mode; local mode unavailable without traceback",
        "total_insert_nucleotides": "full output: retained insert count; matchonly: sum validated --ifile emission counts",
        "total_local_end_nucleotides": "full output: retained EL count; matchonly: sum validated --elfile emission counts; global zero",
        "omitted_nucleotides": "count validated disjoint original positions removed by match-only rendering",
    }
    for field, formula in descriptions.items():
        add(field, ["sequences[].measurements."+field, "sequences[].correspondence", "operation.settings"],
            formula, "positions" if "positions" in field else "nucleotides", "one_native_alignment_row", kind="extracted_native_geometry_count")
    add("original_length", ["mapping.original_length", "supplied_sequences", "native sidecar length"],
        "agreement of supplied actual sequence length, declared length and associated native lengths", "nucleotides", "entire_original_input_sequence", kind="validated_metadata")
    add("model_length", ["model.consensus_length", "alignments.rf_model_positions"],
        "supplied model CLEN or unambiguous sidecar model header, checked against all RF consensus columns", "positions", "entire_CM_consensus", kind="validated_metadata")
    add("model_occupancy", ["model_match_nucleotides", "model_length", "availability.model_mapping"],
        "model_match_nucleotides/model_length", "fraction", "all_CM_consensus_positions_including_missing", "model_length", missing="null_without_valid_model_map_or_positive_denominator")
    add("sequence_matched_coverage", ["model_match_nucleotides", "original_length", "availability.original_mapping"],
        "model_match_nucleotides/original_length", "fraction", "entire_original_sequence", "original_length", missing="null_without_exact_original_and_model_map_or_positive_denominator")
    add("native_bit_score", ["native_scores.bit_score"], "native --sfile bit sc", "bits", "one_native_sequence_alignment",
        uncertainty="printed to two decimal places; model score, not function correctness", kind="native_model_score")
    add("native_avg_pp", ["native_scores.avg_pp"], "native --sfile avg pp", "probability", "all_original_aligned_nucleotides_including_matchonly_omissions",
        "native sequence length", uncertainty="rounded to three decimals; conditional on banding/truncation mode", kind="native_model_posterior_statistic")
    for side in ("lower", "upper"):
        add("posterior_"+side+"_mean", ["posterior."+side+"_sum_hundredths", "posterior.available_count"],
            f"{side}_sum_hundredths/(100*available_count)", "probability_bound", "retained_nucleotides_with_available_PP", "posterior.available_count",
            uncertainty="native quantization interval, conditional on banding/truncation; not exact posterior or annotation correctness", missing="null_when_no_available_bins")
    add("posterior_counts_and_bins", ["posterior.bin_counts", "posterior.available_count", "posterior.unavailable_count"],
        "0:[0,.05); d=1..9:[(10d-5)/100,(10d+5)/100); *:[.95,1]; unavailable is excluded, never zero",
        "nucleotides_and_probability_bounds", "retained_nucleotides", "available_count_for_means", uncertainty="upper mean endpoint closed only when every bin is *", kind="native_quantization_counts")
    add("column_occupancy", ["columns[].populations.*.counts"], "residue/(residue+gap)", "fraction", "selected_population_in_one_alignment_column",
        "residue+gap rows", missing="null_for_zero_denominator; missing/nonresidue/unavailable rows excluded and separately counted")
    add("native_pp_cons_bounds", ["columns[].native_pp_cons_bounds"], "same native PP quantization bins; native population not inferred",
        "probability_bounds", "native_consensus_annotation_population_unspecified", uncertainty="quantization interval", kind="native_annotation")
    add("canonical_pair_fraction", ["pairs[].populations.*.counts"], "canonical/(canonical+noncanonical); canonical=AU/UA/GC/CG/GU/UG",
        "fraction", "observed_unambiguous_two_nucleotide_pairs_after_uppercase_T_to_U", "canonical+noncanonical rows",
        uncertainty="consistency with supplied model alignment only, not experimental structure or function", missing="null_for_zero_denominator; gaps/missing/ambiguous/nonresidue/unavailable excluded separately")
    add("pair_counts", ["pairs[].populations.*.counts"],
        "observed_two_nucleotide_pairs=canonical+noncanonical+ambiguous; disjoint exclusions use missing then gap then nonresidue then unavailable then ambiguous precedence",
        "row_pairs", "selected_population_at_each_supplied_SS_cons_pair", kind="extracted_native_geometry_count")
    add("timing", ["native_scores.band_seconds", "native_scores.alignment_seconds", "native_scores.total_seconds", "native_scores.matrix_mb"],
        "native --sfile band calc/alignment/total seconds and mem (Mb); no inference about queue wait or biological confidence",
        "seconds_and_native_MB", "one_native_sequence_execution", uncertainty="native printed precision .01; matrix MB is native dynamic-programming matrix allocation estimate", kind="native_execution_information")
    add("native_coordinates_and_index", ["native_scores.native_index", "native_scores.cm_from", "native_scores.cm_to"],
        "native input-file sequence index and model alignment boundaries; -1 sentinel retained when no occupied position", "indices", "one_native_sequence_alignment", kind="native_metadata")
    add("summary_counts", ["sequences", "alignments", "columns", "pairs", "parameters.population"],
        "count records or sum explicit pair/column counts in selected population; does not assert independence", "records_or_row_pairs", "supplied_artifacts_selected_population", kind="derived_counts")
    return definitions


def calculate_cmalign_scores(sheet: dict, *, parameters: dict | None = None) -> dict:
    """Recalculate from extracted numeric data, without reparsing any artifact."""
    require_finite_json([sheet, parameters], "cmalign_scores_finite_json_required")
    if parameters is not None and type(parameters) is not dict:
        raise ValueError("cmalign_parameters_object_required")
    options = {"population": "all", **(parameters or {})}
    if set(options) != {"population"}:
        raise ValueError("cmalign_unknown_parameters:"+",".join(sorted(set(options)-{"population"})))
    if type(options["population"]) is not str or options["population"] not in {"all", "newly_aligned", "inherited"}:
        raise ValueError("cmalign_population_invalid")
    if (type(sheet) is not dict or sheet.get("schema") != "cmalign_sheet_v1" or
            type(sheet.get("operation")) is not dict or sheet["operation"].get("program") != "cmalign" or
            sheet.get("status") not in ("available", "partial", "missing", "invalid") or
            any(type(sheet.get(k)) is not list for k in ("sequences", "columns", "pairs", "alignments", "issues"))):
        raise ValueError("cmalign_sheet_contract_invalid")
    rows, issues = [], deepcopy(sheet["issues"])
    for row in sheet["sequences"]:
        try:
            rows.append(_score_row(row))
        except ValueError as exc:
            issue = {"code": str(exc), "record_key": row.get("record_key") if type(row) is dict else None}
            issues.append(issue)
            invalid = {k: None for k in (*_COUNTS, "original_length", "model_length", "native_bit_score",
                "native_avg_pp", "native_index", "cm_from", "cm_to", "truncation", "model_occupancy",
                "sequence_matched_coverage", "posterior_lower_mean", "posterior_upper_mean",
                "posterior_available_count", "posterior_unavailable_count")}
            invalid.update({k: deepcopy(row.get(k)) if type(row) is dict else None
                            for k in ("record_key", "name", "origin", "locator", "alignment_key", "occurrence")})
            invalid.update(status="invalid", issues=[issue])
            rows.append(invalid)
    columns = [_score_population(c, options["population"]) for c in sheet["columns"]]
    pairs = [_score_population(p, options["population"], pair=True) for p in sheet["pairs"]]
    membership = {r["record_key"]: r for r in sheet["sequences"] if type(r) is dict and type(r.get("record_key")) is str}
    if len(membership) != len(sheet["sequences"]):
        raise ValueError("cmalign_duplicate_or_missing_sequence_key")
    for component in columns+pairs:
        for population, group in component["populations"].items():
            for key in group["record_keys"]:
                if (key not in membership or membership[key]["alignment_key"] != component["alignment_key"] or
                        population != "all" and membership[key]["origin"] != population):
                    raise ValueError("cmalign_population_reference_invalid")
    chosen = [r for r in rows if r["status"] != "invalid" and (options["population"] == "all" or r["origin"] == options["population"])]
    pair_totals = {k: sum(p[k] for p in pairs) for k in
        ("observed_two_nucleotide_pairs", "canonical_pairs", "noncanonical_pairs", "unambiguous_pair_denominator")}
    pair_totals["canonical_pair_fraction"] = _ratio(pair_totals["canonical_pairs"], pair_totals["unambiguous_pair_denominator"])
    pair_totals["excluded"] = {k: sum(p["excluded"][k] for p in pairs) for k in ("gap", "missing", "ambiguous", "nonresidue", "unavailable")}
    result = {"schema": "cmalign_scores_v1", "operation": deepcopy(sheet["operation"]),
        "alignment_kind": sheet.get("alignment_kind"), "parameters": options,
        "sequences": rows, "columns": columns, "pairs": pairs,
        "summary": {"population": options["population"], "sequence_count": len(rows), "selected_sequence_count": len(chosen),
            "alignment_count": len(sheet["alignments"]), "column_count": len(columns), "pair_count": len(pairs),
            "pair_map_unavailable_alignment_count": sum(not a["pair_map_available"] for a in sheet["alignments"]),
            "pair_totals": pair_totals, "record_keys": [r["record_key"] for r in chosen],
            "duplicate_artifact_groups": deepcopy(sheet.get("duplicate_artifact_groups", [])),
            "meaning": "alignment_geometry_and_native_model_measurements; no_gene_function_confidence_or_independence_claim"},
        "status": "invalid" if any(r["status"] == "invalid" for r in rows) else sheet["status"],
        "issues": issues, "definitions": _definitions()}
    require_finite_json(result, "cmalign_scores_finite_json_required")
    return result


__all__ = ["calculate_cmalign_scores"]
