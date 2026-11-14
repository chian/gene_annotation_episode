"""Descriptive composition components from explicitly selected saved counts."""
from __future__ import annotations

from .bvbrc_fastqutils_contracts import validate_contract, validate_sheet, json_sha256, FastqUtilsContractError
from .bvbrc_fastqutils_identity import component_ref
from .bvbrc_fastqutils_metric_specs import component_spec


def calculate_composition(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    validate_sheet(sheet)
    job = validate_contract("CalculationBinding", job)
    if job["method"] != "composition_v1":
        raise FastqUtilsContractError("binding_conflict", "/method")
    populations = {r["id"]:r for r in sheet["populations"]}
    cells = {r["id"]:r for r in sheet["measurements"]}
    selected = [cells[ref] for ref in job["operand_measurement_refs"] if ref in cells]
    selected_pops = [populations[ref] for ref in job["population_refs"] if ref in populations]
    base_codes = list(job["diagnostic_codes"])
    base_state = None
    if job["state"] != "ready":
        base_state = "incompatible" if job["state"] == "incompatible" else "missing"
    elif len(selected)!=len(job["operand_measurement_refs"]) or len(selected_pops)!=len(job["population_refs"]):
        base_state = "missing"; base_codes.append("missing_requested_value")
    elif any(p["scope"]!="complete" for p in selected_pops):
        base_state = "truncated" if any(p["scope"]=="partial" for p in selected_pops) else "missing"
        base_codes.append("partial_transfer")
    elif any(r["population_ref"] not in job["population_refs"] for r in selected):
        base_state = "incompatible"; base_codes.append("incompatible_population")

    def one(metric, symbol=None):
        matches = [r for r in selected if r["metric"]==metric and
                   (symbol is None or r["axis"]["kind"]=="symbol" and r["axis"]["label"]==symbol)]
        if len(matches)!=1: return None,matches,"missing" if not matches else "incompatible"
        row = matches[0]
        if row["state"]!="available" or row["value"] is None:
            return None,matches,"truncated" if row["state"]=="partial" else row["state"]
        return row["value"],matches,None

    symbols = {s:one("fastq_symbol_count",s) for s in ("A","C","G","T","N","other_iupac","invalid")}
    bases = one("fastq_base_count")
    reads = one("fastq_read_count")
    configurations = [
        ("gc_acgt_fraction",[symbols[s] for s in ("G","C")],[symbols[s] for s in ("A","C","G","T")]),
        ("n_fraction",[symbols["N"]],[bases]),
        ("ambiguous_fraction",[symbols["N"],symbols["other_iupac"]],[bases]),
        ("mean_read_length",[bases],[reads]),
    ]
    results = []
    sheet_hash = json_sha256(sheet)
    for metric,numerators,denominators in configurations:
        spec = component_spec(metric)
        operands = numerators+denominators+([symbols["invalid"]] if metric!="mean_read_length" else [])
        refs = list(dict.fromkeys(r["id"] for _,rows,_ in operands for r in rows))
        codes = list(base_codes)
        state = base_state
        if state is None:
            state = next((s for _,_,s in operands if s is not None),None)
            if state: codes.append("missing_requested_value" if state=="missing" else "incompatible_population")
        # All descriptive operands must refer to the same exact artifact-local
        # read membership; equal count values do not establish correspondence.
        rows = [r for _,items,_ in operands for r in items]
        used_pops = [populations[r["population_ref"]] for r in rows if r["population_ref"] in populations]
        if used_pops and any((p["member_artifact_refs"],p["member_record_refs"]) !=
                            (used_pops[0]["member_artifact_refs"],used_pops[0]["member_record_refs"]) for p in used_pops):
            state="incompatible"; codes.append("incompatible_population")
        numerator = sum(v for v,_,_ in numerators) if all(v is not None for v,_,_ in numerators) else None
        denominator = sum(v for v,_,_ in denominators) if all(v is not None for v,_,_ in denominators) else None
        if metric!="mean_read_length" and symbols["invalid"][0] not in (None,0):
            state="incompatible"; codes.append("invalid_sequence_symbol")
        if metric in ("n_fraction","ambiguous_fraction") and all(symbols[s][0] is not None for s in symbols) and bases[0] is not None:
            if sum(v[0] for v in symbols.values())!=bases[0]: state="incompatible"; codes.append("count_inconsistent")
        if state is None and denominator == 0:
            state="undefined"; codes.append("zero_denominator")
        value = numerator/denominator if state is None else None
        result = dict(id=component_ref(sheet["analysis_id"],sheet_hash,parameters_sha256,job["calculation_id"],metric,None),
            metric=metric,state=state or "available",value=value,unit=spec["units"][0],method=job["method"],
            population_refs=[p["id"] for p in selected_pops],operand_measurement_refs=refs,
            numerator=numerator,denominator=denominator,threshold=None,meaning=spec["meaning"],
            uncertainty=spec["uncertainty"],parameter_sha256=parameters_sha256,
            diagnostic_codes=list(dict.fromkeys(codes)),calculation_id=job["calculation_id"],
            encoding_basis=None,lineage_basis=None)
        results.append(validate_contract("Component",result))
    return results


__all__ = ["calculate_composition"]
