"""Deterministic numerical components for populated hmmalign sheets.

No function-confidence score is defined. RF columns represent model positions;
insert-column occupancy describes rendering only, never residue homology. PP
means are bounds over the explicitly counted available-PP residue population.
The calculator consumes extracted numerical data, never reparses native text.
"""
from __future__ import annotations

from copy import deepcopy

from .hmmalign_inputs import SHEET_SCHEMA, require_finite_json


_COUNTS = ("retained_residues", "match_state_residues", "deleted_model_positions", "insert_state_residues",
           "terminal_unaligned_residues", "missing_model_positions", "nonresidue_model_positions")
_SCALARS = ("original_length", "model_length", *_COUNTS, "trimmed_residues",
            "model_occupancy", "sequence_match_coverage", "posterior_lower_mean", "posterior_upper_mean")


def _count(value, *, nullable=False):
    return value is None and nullable or type(value) is int and value >= 0


def _fraction(numerator, denominator):
    return numerator/denominator if numerator is not None and denominator is not None and denominator > 0 else None


def _validate_sequence(row):
    code = "hmmalign_sequence_sheet_invalid"
    try:
        if (type(row) is not dict or type(row["record_key"]) is not str or type(row["locator"]) is not dict
                or type(row["name"]) is not str or not _count(row["occurrence"]) or not _count(row["alignment_index"])
                or row["origin"] not in {"newly_aligned", "inherited", "unknown"}
                or row["fragment"] not in {"native_missing_data", "declared", "not_declared"}
                or type(row["measurements"]) is not dict or type(row["mapping"]) is not dict
                or type(row["native"]) is not dict or type(row["native"]["aligned_sequence"]) is not str
                or type(row["availability"]) is not dict or type(row["availability"]["geometry"]) is not bool
                or type(row["issues"]) is not list or "native_rf" not in row or "inherited_join" not in row):
            raise ValueError(code)
        counts, mapping, posterior = row["measurements"], row["mapping"], row["posterior"]
        if any(not _count(counts[field], nullable=True) for field in _COUNTS):
            raise ValueError(code)
        if not _count(row["model_length"], nullable=True) or row["model_length"] == 0:
            raise ValueError(code)
        if any(not _count(mapping[field], nullable=True) for field in ("original_length", "trimmed_residues")):
            raise ValueError(code)
        if counts["match_state_residues"] is not None:
            if any(counts[field] is None for field in _COUNTS):
                raise ValueError(code)
            if counts["match_state_residues"] + counts["insert_state_residues"] + counts["terminal_unaligned_residues"] != counts["retained_residues"]:
                raise ValueError(code)
            if sum(counts[k] for k in ("match_state_residues", "deleted_model_positions", "missing_model_positions", "nonresidue_model_positions")) != row["rf_model_positions"]:
                raise ValueError(code)
            if row["model_length"] is not None and row["model_length"] != row["rf_model_positions"]:
                raise ValueError(code)
        if mapping["trimmed_residues"] is not None and mapping["original_length"] is not None:
            if counts["retained_residues"] is not None and mapping["trimmed_residues"] != mapping["original_length"]-counts["retained_residues"]:
                raise ValueError(code)
        for field in ("residue_population", "bounded_residue_count", "unavailable_residue_count",
                      "lower_sum_hundredths", "upper_sum_hundredths"):
            if not _count(posterior[field]):
                raise ValueError(code)
        n = posterior["bounded_residue_count"]
        if (n + posterior["unavailable_residue_count"] != posterior["residue_population"] or
                not 0 <= posterior["lower_sum_hundredths"] <= posterior["upper_sum_hundredths"] <= 100*n or
                type(posterior["bin_counts"]) is not dict or
                any(k not in "0123456789*" or len(k) != 1 or not _count(v) for k, v in posterior["bin_counts"].items()) or
                sum(posterior["bin_counts"].values()) != n):
            raise ValueError(code)
        lower = sum((95 if k == "*" else max(0, int(k)*10-5))*v for k, v in posterior["bin_counts"].items())
        upper = sum((100 if k == "*" else int(k)*10+5)*v for k, v in posterior["bin_counts"].items())
        if (posterior["lower_sum_hundredths"] != lower or posterior["upper_sum_hundredths"] != upper or
                posterior["mean_upper_inclusive"] is not all(k == "*" for k in posterior["bin_counts"]) or
                type(posterior["population"]) is not str or "native_pp" not in posterior):
            raise ValueError(code)
        if counts["retained_residues"] is not None and posterior["residue_population"] != counts["retained_residues"]:
            raise ValueError(code)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError(code) from error


def _definitions():
    definitions = {}
    descriptions = {
        "original_length": ("mapping.original_length", "supplied_original_sequence_residues", "supplied length validated against supplied sequence, or its actual symbol length"),
        "model_length": ("model_length", "profile_match_states", "supplied profile.length checked against RF model-column count; otherwise RF count"),
        "retained_residues": ("measurements.retained_residues", "retained_output_residues", "count ASCII letters in the native aligned row; gaps, ~ and nonresidue * excluded"),
        "match_state_residues": ("measurements.match_state_residues", "RF_model_columns", "count residue symbols at RF model positions"),
        "deleted_model_positions": ("measurements.deleted_model_positions", "RF_model_columns", "count - . _ gaps at RF model positions; ~ is missing, not deletion"),
        "missing_model_positions": ("measurements.missing_model_positions", "RF_model_columns", "count native ~ at RF model positions"),
        "nonresidue_model_positions": ("measurements.nonresidue_model_positions", "RF_model_columns", "count native * nonresidue symbols at RF model positions"),
        "insert_state_residues": ("measurements.insert_state_residues", "internal_nonmodel_columns", "count residues between first and last RF model columns at nonmodel positions"),
        "terminal_unaligned_residues": ("measurements.terminal_unaligned_residues", "retained_output_terminal_nonmodel_columns", "count retained residues before first or after last RF model column; excludes residues removed by --trim"),
        "trimmed_residues": ("mapping.trimmed_residues", "supplied_original_sequence_residues", "original_length - retained_residues when trim is true and lengths/sequence compatible; zero when trim is false and join compatible"),
    }
    for field, (source, population, formula) in descriptions.items():
        definitions[field] = {"inputs": [source], "formula": formula, "units": "positions" if field.endswith("positions") or field == "model_length" else "residues",
            "population": population, "denominator": None, "coordinate_convention": "model_positions_1_based; alignment_and_sequence_positions_0_based",
            "kind": "extracted_count_or_validated_metadata", "uncertainty": None,
            "missing": "null_when_required_geometry_RF_or_validated_metadata_is_unavailable"}
    for field, numerator, denominator, population in (
            ("model_occupancy", "match_state_residues", "model_length", "all_profile_match_states_including_missing_fragment_positions"),
            ("sequence_match_coverage", "match_state_residues", "original_length", "entire_supplied_original_sequence")):
        definitions[field] = {"inputs": [numerator, denominator], "formula": f"{numerator} / {denominator}",
            "units": "fraction", "population": population, "denominator": denominator,
            "coordinate_convention": None, "kind": "derived_ratio", "uncertainty": None,
            "missing": "null_for_missing_numerator_or_missing_invalid_or_zero_denominator"}
    for side in ("lower", "upper"):
        definitions[f"posterior_{side}_mean"] = {"inputs": [f"posterior.{side}_sum_hundredths", "posterior.bounded_residue_count"],
            "formula": f"posterior.{side}_sum_hundredths / (100 * posterior.bounded_residue_count)",
            "units": "probability_bound", "population": "retained_residues_with_available_native_PP",
            "denominator": "posterior.bounded_residue_count", "coordinate_convention": None,
            "kind": "bound_derived_from_native_ordinal_bins", "uncertainty": "quantization_interval; not exact posterior or annotation correctness",
            "missing": "null_when_no_retained_residue_has_usable_PP; missing PP never contributes zero"}
    definitions["posterior_bins"] = {"inputs": ["native per-sequence PP", "native PP_cons"],
        "formula": "0:[0,.05), 1:[.05,.15), ..., 9:[.85,.95), *:[.95,1]; . unavailable",
        "units": "probability_bounds", "population": "corresponding native PP residue or PP_cons model-column population",
        "denominator": None, "coordinate_convention": "alignment_columns_0_based", "kind": "native_quantization_bounds",
        "uncertainty": "interval endpoints retained, upper endpoint open unless all bins are *", "missing": "null_for_gap_missing_or_invalid_symbol"}
    definitions["column_occupancy"] = {"inputs": ["columns.populations.*.occupancy_numerator", "columns.populations.*.occupancy_denominator"],
        "formula": "residue rows / rows with usable column geometry and symbol other than ~",
        "units": "fraction", "population": "separately all/newly_aligned/inherited/unknown/fragment/nonfragment rows",
        "denominator": "corresponding occupancy_denominator; ~ excluded and explicitly counted",
        "coordinate_convention": "alignment_columns_0_based; model_positions_1_based",
        "kind": "derived_ratio", "uncertainty": None, "missing": "null_for_zero_denominator",
        "interpretation": "insert-column occupancy is rendering occupancy and does not imply homologous correspondence"}
    definitions["pp_cons"] = {"inputs": ["native PP_cons", "column native_pp_cons_bounds"],
        "formula": "native bin of the mean posterior over newly aligned match-state residues with PP; inherited traces excluded",
        "units": "probability_bounds", "population": "newly_aligned_match_state_residues_with_native_PP",
        "denominator": "native total unknown unless complete membership/PP supplied; observed denominator separately retained",
        "coordinate_convention": "alignment_columns_0_based", "kind": "native_quantization_bounds", "uncertainty": "bin interval",
        "missing": "null_for_missing_invalid_or_insert_column_PP_cons"}
    definitions["summary"] = {"inputs": ["sequences", "columns", "alignments", "status"],
        "formula": "counts of supplied records and explicit populations; no score aggregation or independence claim",
        "units": "records", "population": "supplied native artifact", "denominator": None,
        "coordinate_convention": None, "kind": "record_counts", "uncertainty": "completeness separately reported",
        "missing": "missing output differs from a terminated empty Stockholm record"}
    return definitions


def _score_sequence(row):
    _validate_sequence(row)
    counts, mapping, pp = row["measurements"], row["mapping"], row["posterior"]
    denominator = pp["bounded_residue_count"]
    numerators = {"model_occupancy": counts["match_state_residues"],
        "sequence_match_coverage": counts["match_state_residues"],
        "posterior_lower_mean": pp["lower_sum_hundredths"]/100 if denominator else None,
        "posterior_upper_mean": pp["upper_sum_hundredths"]/100 if denominator else None}
    denominators = {"model_occupancy": row["model_length"], "sequence_match_coverage": mapping["original_length"],
                    "posterior_lower_mean": denominator, "posterior_upper_mean": denominator}
    result = {"record_key": row["record_key"], "locator": deepcopy(row["locator"]),
        "name": row["name"], "occurrence": row["occurrence"], "alignment_index": row["alignment_index"],
        "origin": row["origin"], "fragment": row["fragment"], "status": "available" if row["availability"]["geometry"] else "partial",
        "availability": deepcopy(row["availability"]), "original_length": mapping["original_length"],
        "model_length": row["model_length"], **deepcopy(counts), "trimmed_residues": mapping["trimmed_residues"],
        **{k: _fraction(numerators[k], denominators[k]) for k in numerators},
        "numerators": numerators, "denominators": denominators,
        "posterior_bounded_residue_count": denominator, "posterior_unavailable_residue_count": pp["unavailable_residue_count"],
        "posterior_mean_lower_inclusive": True if denominator else None,
        "posterior_mean_upper_inclusive": pp["mean_upper_inclusive"] if denominator else None,
        "posterior_population": pp["population"], "posterior_bin_counts": deepcopy(pp["bin_counts"]),
        "mapping": deepcopy(mapping), "inherited_join": deepcopy(row["inherited_join"]),
        "native": {"aligned_sequence": row["native"]["aligned_sequence"], "rf": row["native_rf"], "pp": pp["native_pp"]},
        "issues": deepcopy(row["issues"])}
    result["unavailable"] = {key: ("no_usable_native_PP_residues" if key.startswith("posterior_") else
        "RF_or_common_column_geometry_unavailable" if key in _COUNTS and key != "retained_residues" else
        "required_numerator_or_positive_denominator_unavailable" if key.endswith("coverage") or key == "model_occupancy" else
        "validated_original_length_or_declared_trim_missing" if key in {"original_length", "trimmed_residues"} else
        "validated_profile_length_unavailable" if key == "model_length" else "native_symbols_invalid")
        for key in _SCALARS if result[key] is None}
    result["derived"] = {key: result[key] for key in _SCALARS}
    return result


def _score_column(column):
    try:
        if type(column) is not dict or type(column["record_key"]) is not str or type(column["populations"]) is not dict:
            raise ValueError("hmmalign_column_sheet_invalid")
        result = deepcopy(column)
        for group in result["populations"].values():
            if (any(not _count(group[k]) for k in ("occupancy_numerator", "occupancy_denominator", "missing_rows", "row_count")) or
                    group["occupancy_numerator"] > group["occupancy_denominator"] or
                    group["occupancy_denominator"]+group["missing_rows"] != group["row_count"] or
                    len(group["record_keys"]) != group["row_count"]):
                raise ValueError("hmmalign_column_sheet_invalid")
            group["occupancy"] = _fraction(group["occupancy_numerator"], group["occupancy_denominator"])
            group["unavailable_reason"] = None if group["occupancy_denominator"] else "no_observable_rows_in_declared_population"
        result.update({key: result["populations"]["all"][key] for key in
                       ("occupancy", "occupancy_numerator", "occupancy_denominator")})
        bounds = result["native_pp_cons_bounds"]
        result["posterior_cons_lower"] = bounds["lower_hundredths"]/100 if bounds is not None else None
        result["posterior_cons_upper"] = bounds["upper_hundredths"]/100 if bounds is not None else None
        return result
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("hmmalign_column_sheet_invalid") from error


def calculate_hmmalign_scores(sheet, *, parameters=None):
    """Calculate ordinary fixed native components; unsupported knobs are errors."""
    require_finite_json(sheet, "hmmalign_sheet_finite_json_required")
    require_finite_json(parameters, "hmmalign_parameters_finite_json_required")
    if parameters is not None and type(parameters) is not dict:
        raise ValueError("hmmalign_parameters_object_required")
    if parameters:
        raise ValueError("hmmalign_unsupported_parameters:"+",".join(sorted(parameters)))
    if (type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA or type(sheet.get("operation")) is not dict
            or sheet["operation"].get("program") != "hmmalign" or type(sheet.get("sequences")) is not list
            or type(sheet.get("columns")) is not list or type(sheet.get("alignments")) is not list
            or type(sheet.get("issues")) is not list):
        raise ValueError("hmmalign_sheet_schema_invalid")
    issues, sequences, columns = deepcopy(sheet["issues"]), [], []
    for index, row in enumerate(sheet["sequences"]):
        try:
            sequences.append(_score_sequence(row))
        except ValueError as error:
            issue = {"code": str(error), "sequence_index": index,
                     "record_key": row.get("record_key") if type(row) is dict else None}
            sequences.append({"record_key": issue["record_key"], "locator": deepcopy(row.get("locator")) if type(row) is dict else None,
                              "status": "invalid", **dict.fromkeys(_SCALARS), "issues": [issue]})
            issues.append(issue)
    for index, column in enumerate(sheet["columns"]):
        try:
            columns.append(_score_column(column))
        except ValueError as error:
            issue = {"code": str(error), "column_index": index,
                     "record_key": column.get("record_key") if type(column) is dict else None}
            columns.append({"record_key": issue["record_key"], "status": "invalid", "issues": [issue]})
            issues.append(issue)
    summary = {"native_status": sheet.get("status"), "alignment_count": len(sheet["alignments"]),
        "terminated_alignment_count": sum(a.get("complete") is True for a in sheet["alignments"] if type(a) is dict),
        "sequence_count": len(sheet["sequences"]), "column_count": len(sheet["columns"]),
        "invalid_sequence_count": sum(r["status"] == "invalid" for r in sequences),
        "sequence_counts_by_origin": {origin: sum(r.get("origin") == origin for r in sequences)
                                      for origin in ("newly_aligned", "inherited", "unknown")},
        "fragment_sequence_count": sum(r.get("fragment") in {"native_missing_data", "declared"} for r in sequences),
        "acquisition": deepcopy(sheet.get("acquisition")),
        "meaning": "supplied_alignment_measurements; inherited_rows_are_not_new_support; no_function_confidence_or_independence_claim"}
    result = {"schema": "hmmalign_scores_v1", "operation": deepcopy(sheet["operation"]), "parameters": {},
        "sequences": sequences, "columns": columns, "summary": summary, "definitions": _definitions(), "issues": issues}
    require_finite_json(result, "hmmalign_scores_finite_json_required")
    return result


__all__ = ["calculate_hmmalign_scores"]
