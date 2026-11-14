"""Quality summaries and explicit Phred-model predictions from saved data."""
from __future__ import annotations

from copy import deepcopy
import math

from .bvbrc_fastqutils_contracts import validate_contract, validate_sheet, json_sha256, FastqUtilsContractError
from .bvbrc_fastqutils_identity import component_ref
from .bvbrc_fastqutils_metric_specs import component_spec


def calculate_quality(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    validate_sheet(sheet)
    job = validate_contract("CalculationBinding",job)
    if job["method"] != "quality_phred_v1":
        raise FastqUtilsContractError("binding_conflict", "/method")
    populations = {r["id"]:r for r in sheet["populations"]}
    cells = {r["id"]:r for r in sheet["measurements"]}
    selected_pops = [populations[r] for r in job["population_refs"] if r in populations]
    selected = [cells[r] for r in job["operand_measurement_refs"] if r in cells]
    codes = list(job["diagnostic_codes"])
    state = None
    basis = None
    histogram = {}
    if job["state"]!="ready": state="incompatible" if job["state"]=="incompatible" else "missing"
    if state is None and (len(selected_pops)!=len(job["population_refs"]) or len(selected)!=len(job["operand_measurement_refs"])):
        state="missing"; codes.append("missing_requested_value")
    if state is None and len(selected_pops)!=1:
        state="incompatible"; codes.append("incompatible_population")
    population = selected_pops[0] if len(selected_pops)==1 else None
    if population:
        basis = deepcopy(population["encoding_basis"])
        documents = [d for d in sheet["documents"] if d["document_id"] in population["document_ids"]]
        stream_partial = any(d["parse_scope"] != "complete" or d["artifact"]["transfer_scope"] == "partial" for d in documents)
        if stream_partial:
            state=state or "truncated"; codes.append("partial_transfer")
        elif population["scope"]=="unknown" or any(d["artifact"]["transfer_scope"]=="unknown" for d in documents):
            state=state or "missing"; codes.append("partial_transfer")
        elif population["scope"]!="complete":
            state=state or "not_measured"; codes.append("missing_requested_value")
        encoding = basis["encoding"]
        if basis["basis"]=="unknown" or encoding=="unknown":
            state=state or "missing"; codes.append("unknown_quality_encoding")
        if basis["basis"]=="explicit_source_bound_declaration":
            codes.append("explicit_encoding_assumption")
        declarations = {item["value"]["encoding"] for item in sheet["supplied_metadata"]
                        if item["kind"]=="encoding_declaration"
                        and item["value"]["document_id"] in population["document_ids"]}
        if len(declarations)>1:
            state="incompatible"; codes.append("encoding_declaration_conflict")
        numeric = basis["basis"] in ("native_bam_phred","native_sam_phred")
        expected_metric = "phred_histogram_count" if numeric else "quality_character_count"
        for row in selected:
            if row["population_ref"]!=population["id"] or row["metric"]!=expected_metric:
                state="incompatible"; codes.append("incompatible_population"); continue
            if row["state"]!="available":
                state=state or ("truncated" if row["state"]=="partial" else row["state"])
                if row["state"]!="partial": continue
            q = row["axis"]["lower"]
            expected_axis = "quality_score" if numeric else "quality_ascii"
            if row["axis"]["kind"]!=expected_axis or q!=row["axis"]["upper"] or type(q) is not int:
                state="incompatible"; codes.append("invalid_quality_score"); continue
            if not numeric:
                if encoding not in ("phred33","phred64"): continue
                q -= 33 if encoding=="phred33" else 64
            if not 0<=q<=93 or q in histogram:
                state="incompatible"; codes.append("invalid_quality_score"); continue
            histogram[q] = row["value"]
        # Check complete membership and the missing mask, without re-parsing.
        records = {r["id"]:r for d in sheet["documents"] for r in
                   d["alignment_records"]+d["sequence_records"]}
        members = [records[r] for r in population["member_record_refs"] if r in records]
        if len(members)!=len(population["member_record_refs"]):
            state=state or "missing"; codes.append("missing_requested_value")
        expected_count = 0
        for record in members:
            values = record["phred_values"] if numeric else record["quality_symbols"]
            sequence = record["sequence"]
            if sequence is None or values is None or len(values)!=len(sequence) or (numeric and any(q is None for q in values)):
                state=state or "not_measured"; codes.append("missing_requested_value")
            else: expected_count += len(values)
        member_refs={r["id"] for r in members}
        if any(d["code"]=="invalid_quality_score" and member_refs.intersection(d["affected_refs"])
               for document in documents for d in document["diagnostics"]):
            state="incompatible"; codes.append("invalid_quality_score")
        if state is None and sum(histogram.values())!=expected_count:
            state="incompatible"; codes.append("count_inconsistent")
    denominator = (sum(histogram.values()) if population and basis["encoding"] != "unknown"
                   and (selected or not population["member_record_refs"]) else None)
    weighted = sum(q*n for q,n in histogram.items()) if denominator is not None else None
    errors = math.fsum(n*10**(-q/10) for q,n in histogram.items()) if denominator is not None else None
    jobs = [("mean_phred",None,weighted,denominator)]
    jobs += [("q_ge_threshold_fraction",threshold,sum(n for q,n in histogram.items() if q>=threshold) if denominator is not None else None,denominator)
             for threshold in sorted(job["quality_thresholds"])]
    jobs += [("phred_implied_expected_errors",None,errors,None),
             ("phred_implied_error_fraction",None,errors,denominator)]
    output=[]
    sheet_hash=json_sha256(sheet)
    for metric,threshold,numerator,denom in jobs:
        spec=component_spec(metric)
        own_state=state
        own_codes=list(codes)
        if own_state is None and denom==0:
            own_state="undefined"; own_codes.append("zero_denominator")
        value = None if own_state else numerator if metric=="phred_implied_expected_errors" else numerator/denom
        row=dict(id=component_ref(sheet["analysis_id"],sheet_hash,parameters_sha256,job["calculation_id"],metric,threshold),
            metric=metric,state=own_state or "available",value=value,unit=spec["units"][0],method=job["method"],
            population_refs=[p["id"] for p in selected_pops],operand_measurement_refs=[r["id"] for r in selected],
            numerator=numerator,denominator=denom,threshold=threshold,meaning=spec["meaning"],uncertainty=spec["uncertainty"],
            parameter_sha256=parameters_sha256,diagnostic_codes=list(dict.fromkeys(own_codes)),
            calculation_id=job["calculation_id"],encoding_basis=basis,lineage_basis=None)
        output.append(validate_contract("Component",row))
    return output


__all__=["calculate_quality"]
