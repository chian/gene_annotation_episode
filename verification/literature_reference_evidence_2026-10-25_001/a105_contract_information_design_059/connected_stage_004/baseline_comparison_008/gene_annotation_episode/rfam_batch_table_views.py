"""Pure selection of saved Rfam batch components; no score calculation."""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError
from .rfam_batch_contracts import (RFAM_METRIC_UNITS, RFAM_MISSING_REASONS,
    closed_object, finite_json_copy, is_number, is_text, query_strand_record_key,
    rfam_digest, validate_rfam_table_projection)
from .rfam_batch_table_grader import VERSION, PARAMETERS, validate_rfam_table_inputs, _index


def project_rfam_batch_table_result(parsed, calculation, *, projection, artifact_bindings):
    parsed = validate_rfam_table_inputs(parsed)
    projection = validate_rfam_table_projection(projection)
    code = "rfam_projection_reference_conflict"
    calculation = finite_json_copy(calculation, code=code)
    closed_object(calculation, ("version", "sheet_digest", "parse_digest", "parameters",
        "native_calculation", "hits", "query_strands", "population_complete"), code=code)
    bindings = finite_json_copy(artifact_bindings, code=code)
    closed_object(bindings, ("source_ref", "sheet_ref", "calculation_ref", "sheet_digest", "calculation_digest"), code=code)
    if (calculation["version"] != VERSION or calculation["parameters"] != PARAMETERS
            or calculation["sheet_digest"] != rfam_digest(parsed["sheet"])
            or calculation["parse_digest"] != rfam_digest(parsed)
            or bindings["source_ref"] != parsed["capture"]["source_ref"]
            or any(not is_text(bindings[k]) for k in ("source_ref", "sheet_ref", "calculation_ref"))
            or bindings["sheet_digest"] != calculation["sheet_digest"]
            or bindings["calculation_digest"] != rfam_digest(calculation)
            or type(calculation["population_complete"]) is not bool):
        raise ContractError(code)
    family = projection["family"]
    rows = calculation["hits" if family == "hit" else "query_strands"]
    if type(rows) is not list:
        raise ContractError(code)
    keys = ([row["hit_key"] for row in rows] if family == "hit" else
            [query_strand_record_key(row["query_occurrence_key"], row["strand"]) for row in rows])
    if len(set(keys)) != len(keys):
        raise ContractError(code)
    if family == "hit":
        native = calculation["native_calculation"]["hits"]
        if len(native) != len(rows) or keys != [r["hit_id"] for r in native]:
            raise ContractError(code)
        queries = parsed["input_identity"]["queries"]
        for row, original in zip(rows, native):
            identity = original["sequence"].get("identity")
            query_index = _index(identity, queries)
            key = None if query_index is None else queries[query_index]["query_occurrence_key"]
            if (row["query_occurrence_key"] != key or row["strand"] != original["strand"]
                    or row["family_accession"] != original["model"].get("accession")):
                raise ContractError(code)
    else:
        expected = [query_strand_record_key(q["query_occurrence_key"], strand)
                    for q in parsed["input_identity"]["queries"] for strand in ("+", "-")]
        if keys != expected:
            raise ContractError(code)
    choice = projection["rows"]
    if "record_keys" in choice:
        mapping = {key: index for index, key in enumerate(keys)}
        if any(key not in mapping for key in choice["record_keys"]):
            raise ContractError(code)
        selected = [mapping[key] for key in choice["record_keys"]]
    else:
        selected = list(range(choice["offset"], min(choice["offset"] + choice["limit"], len(rows))))
    result = []
    for index in selected:
        row = rows[index]
        measured, unavailable = [], []
        for name in projection["metrics"]:
            value = row.get(name)
            if is_number(value):
                measured.append({"name": name, "value": value, "unit": RFAM_METRIC_UNITS[name]})
            else:
                reason = row.get("missing", {}).get(name, "partial_body" if not row.get("population_complete", True) else "not_reported")
                if reason not in RFAM_MISSING_REASONS:
                    raise ContractError(code)
                unavailable.append({"name": name, "reason": reason})
        result.append({"record_key": keys[index], "query_occurrence_key": row["query_occurrence_key"],
            "family_accession": row.get("family_accession"), "strand": row["strand"],
            "measured": measured, "unavailable": unavailable})
    return {"version": "rfam_selected_projection_v1", "source_ref": bindings["source_ref"],
        "sheet_ref": bindings["sheet_ref"], "calculation_ref": bindings["calculation_ref"],
        "family": family, "selection": deepcopy(projection), "available_row_count": len(rows),
        "selected_row_count": len(result), "more_rows": len(result) < len(rows),
        "population_complete": calculation["population_complete"] if family == "hit" else
            all(row["population_complete"] for row in rows), "rows": result}


__all__ = ["project_rfam_batch_table_result"]
