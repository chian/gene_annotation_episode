"""Mapping components with complete input/read-segment correspondence.

Mapped records never serve as the denominator for an input-read fraction.
Secondary and supplementary records remain distinct from primary read segments.
"""
from __future__ import annotations

from .bvbrc_fastqutils_contracts import validate_contract, validate_sheet, json_sha256, FastqUtilsContractError
from .bvbrc_fastqutils_identity import component_ref
from .bvbrc_fastqutils_metric_specs import component_spec


def _key(title, rule):
    if title is None: return None
    if rule == "exact_title": return (title,None)
    if rule == "fastq_pair_0_3":
        # The native default splits at ASCII space only and removes the last
        # mate character, preserving its delimiter. This is a different key
        # convention from first_token_slash_mate, including for tabbed titles.
        token = title.split(" ", 1)[0]
        if not token: return None
        if len(token) >= 2 and token[-2] in "/_." and token[-1] in "12fr":
            return (token[:-1], 1 if token[-1] in "1f" else 2)
        return (token, None)
    parts=title.split()
    if not parts: return None
    token=parts[0]
    if rule=="first_token": return (token,None)
    separators="/" if rule=="first_token_slash_mate" else "/_."
    suffixes="12" if rule=="first_token_slash_mate" else "12fr"
    if len(token)>=2 and token[-2] in separators and token[-1] in suffixes:
        return (token[:-2],1 if token[-1] in "1f" else 2)
    return (token,None)


def calculate_mapping(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    validate_sheet(sheet)
    job=validate_contract("CalculationBinding",job)
    if job["method"]!="mapping_v1":
        raise FastqUtilsContractError("binding_conflict","/method")
    populations={p["id"]:p for p in sheet["populations"]}
    measurements={r["id"]:r for r in sheet["measurements"]}
    pops=[populations[r] for r in job["population_refs"] if r in populations]
    cells=[measurements[r] for r in job["operand_measurement_refs"] if r in measurements]
    records={r["id"]:r for d in sheet["documents"] for r in d["alignment_records"]+d["sequence_records"]}
    base_codes=list(job["diagnostic_codes"])
    base_state=None
    if job["state"]!="ready": base_state="incompatible" if job["state"]=="incompatible" else "missing"
    elif len(pops)!=len(job["population_refs"]) or len(cells)!=len(job["operand_measurement_refs"]):
        base_state="missing"; base_codes.append("missing_requested_value")
    if any(c["population_ref"] not in job["population_refs"] for c in cells):
        base_state="incompatible"; base_codes.append("incompatible_population")
    align_pops=[p for p in pops if p["population_key"]=="bam_records"]
    read_pops=[p for p in pops if p["population_key"]=="fastq_reads"]
    alignment=align_pops[0] if len(align_pops)==1 else None

    def operand(metric,pop=None):
        rows=[r for r in cells if r["metric"]==metric and (pop is None or r["population_ref"]==pop["id"])]
        if len(rows)!=1: return None,rows,"missing" if not rows else "incompatible"
        row=rows[0]
        return (row["value"],rows,None) if row["state"]=="available" else (None,rows,"truncated" if row["state"]=="partial" else row["state"])

    total,total_rows,total_state=operand("bam_record_count",alignment)
    primary,primary_rows,primary_state=operand("bam_primary_record_count",alignment)
    primary_state=base_state or primary_state or total_state
    primary_codes=list(base_codes)
    if alignment is None:
        primary_state="missing" if not align_pops else "incompatible"; primary_codes.append("missing_denominator")
    elif alignment["scope"]!="complete":
        primary_state="truncated" if alignment["scope"]=="partial" else "missing"
        primary_codes.append("partial_transfer")
    elif total is not None and primary is not None and primary>total:
        primary_state="incompatible"; primary_codes.append("count_inconsistent")
    if primary_state is None and total==0:
        primary_state="undefined"; primary_codes.append("zero_denominator")

    mapped_state=base_state
    mapped_codes=list(base_codes)
    denominator=None
    numerator=None
    mapped_refs=[]
    if alignment is None or not read_pops or job["read_key_rule"] is None:
        mapped_state=mapped_state or "missing"; mapped_codes.append("missing_denominator" if not read_pops else "missing_requested_value")
    elif alignment["scope"]!="complete" or any(p["scope"]!="complete" for p in read_pops):
        mapped_state=mapped_state or ("truncated" if any(p["scope"]=="partial" for p in [alignment]+read_pops) else "missing")
        mapped_codes.append("partial_transfer")
    else:
        read_rows=[]
        inputs={}
        counts=[]
        for population in read_pops:
            count,rows,state=operand("fastq_read_count",population)
            mapped_refs.extend(r["id"] for r in rows)
            if state:
                mapped_state=mapped_state or state; mapped_codes.append("missing_denominator")
            else: counts.append(count)
            members=[records[r] for r in population["member_record_refs"] if r in records]
            if len(members)!=len(population["member_record_refs"]) or any("title" not in r for r in members):
                mapped_state="incompatible"; mapped_codes.append("incompatible_population"); continue
            if count is not None and len(members)!=count:
                mapped_state="incompatible"; mapped_codes.append("count_inconsistent")
            read_rows.extend(members)
        denominator=sum(counts) if len(counts)==len(read_pops) else None
        for record in read_rows:
            key=_key(record["title"],job["read_key_rule"])
            if key is None or key in inputs:
                mapped_state="incompatible"; mapped_codes.append("ambiguous_pair_key")
            else: inputs[key]=record["id"]
        alignment_rows=[records[r] for r in alignment["member_record_refs"] if r in records]
        if len(alignment_rows)!=len(alignment["member_record_refs"]) or any("flag" not in r for r in alignment_rows):
            mapped_state="incompatible"; mapped_codes.append("incompatible_population")
        primary_keys=set()
        mapped=set()
        for record in alignment_rows:
            if "flag" not in record or record["flag"]&0x900: continue
            key=_key(record["qname"],job["read_key_rule"])
            if key is None:
                mapped_state="incompatible"; mapped_codes.append("ambiguous_pair_key"); continue
            # Mate suffixes and paired FLAG bits must agree. No assumption about
            # segment index is made when both/neither first/last bits are set.
            if record["flag"]&1:
                flag_mate=1 if record["flag"]&0xC0==0x40 else 2 if record["flag"]&0xC0==0x80 else None
                if key[1] is not None and key[1]!=flag_mate:
                    mapped_state="incompatible"; mapped_codes.append("ambiguous_pair_key"); continue
                if job["read_key_rule"] in ("first_token_slash_mate","fastq_pair_0_3"):
                    if flag_mate is None:
                        mapped_state="incompatible"; mapped_codes.append("ambiguous_pair_key"); continue
                    key=(key[0],flag_mate)
            if key in primary_keys:
                mapped_state="incompatible"; mapped_codes.append("ambiguous_pair_key")
            primary_keys.add(key)
            if key not in inputs:
                mapped_state="incompatible"; mapped_codes.append("incompatible_population")
            elif not record["flag"]&4:
                mapped.add(key)
        if mapped_state is None:
            numerator=len(mapped)
            if denominator==0:
                mapped_state="undefined"; mapped_codes.append("zero_denominator")
    rows=[]
    sheet_hash=json_sha256(sheet)
    for metric,num,den,state,codes,refs in (
        ("distinct_mapped_read_fraction",numerator,denominator,mapped_state,mapped_codes,mapped_refs+[r["id"] for r in primary_rows]),
        ("primary_record_fraction",primary,total,primary_state,primary_codes,[r["id"] for r in primary_rows+total_rows])):
        spec=component_spec(metric)
        row=dict(id=component_ref(sheet["analysis_id"],sheet_hash,parameters_sha256,job["calculation_id"],metric,None),
            metric=metric,state=state or "available",value=None if state else num/den,
            unit=spec["units"][0],method=job["method"],population_refs=[p["id"] for p in pops],
            operand_measurement_refs=list(dict.fromkeys(refs)),numerator=num,denominator=den,threshold=None,
            meaning=spec["meaning"],uncertainty=spec["uncertainty"],parameter_sha256=parameters_sha256,
            diagnostic_codes=list(dict.fromkeys(codes)),calculation_id=job["calculation_id"],encoding_basis=None,lineage_basis=None)
        rows.append(validate_contract("Component",row))
    return rows


__all__=["calculate_mapping"]
