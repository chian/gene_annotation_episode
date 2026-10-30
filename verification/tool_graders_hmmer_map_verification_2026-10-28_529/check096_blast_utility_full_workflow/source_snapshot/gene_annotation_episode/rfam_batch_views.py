"""Pure receiver-selected projections of saved Rfam numerical components."""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError
from .rfam_batch_contracts import (
    RFAM_METRIC_UNITS, RFAM_MISSING_REASONS, RfamCalculationResult,
    RfamSelectedProjection, closed_object, finite_json_copy, is_int, is_number,
    is_text, query_strand_record_key, rfam_digest, validate_issue,
    validate_rfam_parameters, validate_rfam_projection)
from .rfam_batch_grader import CALCULATED_HIT_METRICS, validate_rfam_sheet


def _checked_calculation(sheet, calculation):
    code = "rfam_projection_reference_conflict"
    calculation = finite_json_copy(calculation, code=code)
    closed_object(calculation, RfamCalculationResult.__annotations__, code=code)
    if (calculation["version"] != "rfam_batch_calculation_v1" or calculation["sheet_digest"] != rfam_digest(sheet)
            or type(calculation["hits"]) is not list or type(calculation["query_strands"]) is not list
            or type(calculation["issues"]) is not list):
        raise ContractError(code)
    validate_rfam_parameters(calculation["parameters"])
    population = calculation["population"]
    closed_object(population, ("query_occurrence_key", "reported_row_count", "valid_interval_row_count",
        "duplicate_row_count", "reported_set_complete", "interval_population_complete"), code=code)
    if (population["query_occurrence_key"] != sheet["input"]["query_occurrence_key"]
            or population["reported_row_count"] != len(sheet["hits"])
            or population["reported_set_complete"] != sheet["population"]["reported_set_complete"]
            or any(not is_int(population[k]) for k in ("reported_row_count", "valid_interval_row_count", "duplicate_row_count"))
            or any(type(population[k]) is not bool for k in ("reported_set_complete", "interval_population_complete"))
            or len(calculation["hits"]) != len(sheet["hits"])):
        raise ContractError(code)
    for native, row in zip(sheet["hits"], calculation["hits"]):
        closed_object(row, ("hit_key", "query_occurrence_key", "family_accession", "strand", "missing", *CALCULATED_HIT_METRICS), code=code)
        if (row["hit_key"] != native["hit_key"] or row["query_occurrence_key"] != native["query_occurrence_key"]
                or row["family_accession"] != (native["family_accession"] if native["identity_valid"] else None)
                or row["strand"] != native["native"]["strand"] or type(row["missing"]) is not dict
                or any(k not in CALCULATED_HIT_METRICS or v not in RFAM_MISSING_REASONS for k, v in row["missing"].items())):
            raise ContractError(code)
        for name in CALCULATED_HIT_METRICS:
            if row[name] is None:
                if name not in row["missing"]:
                    raise ContractError(code)
            elif not is_number(row[name]) or name in row["missing"]:
                raise ContractError(code)
    if len(calculation["query_strands"]) != 2:
        raise ContractError(code)
    for strand, row in zip(("+", "-"), calculation["query_strands"]):
        metrics = ("query_length_nt", "selected_row_count", "valid_interval_row_count", "query_strand_sum_span_nt",
            "query_strand_union_span_nt", "query_strand_union_fraction", "query_strand_overlap_excess_nt")
        closed_object(row, ("query_occurrence_key", "strand", "population_complete", *metrics), code=code)
        if (row["query_occurrence_key"] != sheet["input"]["query_occurrence_key"] or row["strand"] != strand
                or type(row["population_complete"]) is not bool or any(not is_number(row[k]) for k in metrics)):
            raise ContractError(code)
    for issue in calculation["issues"]:
        validate_issue(issue)
    return calculation


def project_rfam_batch_result(sheet, calculation, *, projection, artifact_bindings) -> RfamSelectedProjection:
    """Select typed cells; caller authenticates stored artifact custody first.

This checks supplied digests and exact original row associations. It neither
opens referenced artifacts nor recalculates the scientific components.
    """
    if isinstance(sheet, dict) and sheet.get("schema") == "infernal_search_sheet_v2":
        from .rfam_batch_infernal import project_rfam_infernal_result
        return project_rfam_infernal_result(sheet, calculation, projection=projection,
            artifact_bindings=artifact_bindings, representation="json")
    projection = validate_rfam_projection(projection)
    sheet = validate_rfam_sheet(sheet)
    calculation = _checked_calculation(sheet, calculation)
    code = "rfam_projection_reference_conflict"
    bindings = finite_json_copy(artifact_bindings, code=code)
    closed_object(bindings, ("source_ref", "sheet_ref", "calculation_ref", "sheet_digest", "calculation_digest"), code=code)
    if (any(not is_text(bindings[k]) for k in ("source_ref", "sheet_ref", "calculation_ref"))
            or bindings["source_ref"] != sheet["source"]["source_ref"]
            or bindings["sheet_digest"] != rfam_digest(sheet)
            or bindings["calculation_digest"] != rfam_digest(calculation)):
        raise ContractError(code)
    family = projection["family"]
    if family == "hit":
        rows = calculation["hits"]
        keys = [r["hit_key"] for r in rows]
    else:
        rows = calculation["query_strands"]
        keys = [query_strand_record_key(r["query_occurrence_key"], r["strand"]) for r in rows]
    if "record_keys" in projection["rows"]:
        requested = projection["rows"]["record_keys"]
        indices = {key: i for i, key in enumerate(keys)}
        if any(key not in indices for key in requested):
            raise ContractError(code)
        selected = [indices[key] for key in requested]
    else:
        offset, limit = projection["rows"]["offset"], projection["rows"]["limit"]
        selected = list(range(offset, min(offset + limit, len(rows))))
    projected = []
    for index in selected:
        row = rows[index]
        values = dict(row)
        missing = dict(row.get("missing", {}))
        measured, unavailable = [], []
        for name in projection["metrics"]:
            value = values.get(name)
            if is_number(value):
                measured.append({"name": name, "value": value, "unit": RFAM_METRIC_UNITS[name]})
            else:
                reason = missing.get(name, "not_reported")
                if reason not in RFAM_MISSING_REASONS:
                    raise ContractError(code)
                unavailable.append({"name": name, "reason": reason})
        projected.append({"record_key": keys[index], "query_occurrence_key": row["query_occurrence_key"],
            "family_accession": row.get("family_accession"), "strand": row["strand"],
            "measured": measured, "unavailable": unavailable})
    return {"version": "rfam_selected_projection_v1", "source_ref": bindings["source_ref"],
        "sheet_ref": bindings["sheet_ref"], "calculation_ref": bindings["calculation_ref"],
        "family": family, "selection": deepcopy(projection), "available_row_count": len(rows),
        "selected_row_count": len(projected), "more_rows": len(projected) < len(rows),
        "population_complete": calculation["population"]["reported_set_complete" if family == "hit" else "interval_population_complete"],
        "rows": projected}
