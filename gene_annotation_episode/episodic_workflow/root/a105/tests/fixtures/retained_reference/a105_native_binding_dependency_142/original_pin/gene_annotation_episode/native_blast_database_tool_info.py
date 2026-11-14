"""Four-field tool information with the explicitly configured HPC commission port.

Returning a descriptor does not install software, verify deployment or attach
the separate E result path. Scientific construction keeps evidence_axis,
thought_pattern and the selected child_tool_info set under their existing owners.
"""
from __future__ import annotations

from copy import deepcopy

from . import native_blast_database_contracts as contracts

_DESCRIPTIONS = {
    "psiblast": "Search a prepared protein sequence database using a supplied protein sequence, CLUSTAL alignment or PSSM, retaining the selected iterative native search.",
    "deltablast": "Search a prepared protein sequence database using supplied protein queries and a separately selected DELTA domain database.",
    "rpsblast": "Search a prepared RPS profile database with supplied protein sequences, retaining native model-position alignments.",
    "rpstblastn": "Search a prepared RPS profile database with translated supplied nucleotide queries, retaining nucleotide and model coordinates.",
    "blastn_vdb": "Search explicitly selected prepared local VDB datasets with supplied nucleotide sequences under their retained offline configuration.",
    "tblastn_vdb": "Search translated prepared local VDB datasets with supplied protein sequences or a protein PSSM containing its actual query Seq-entry.",
}
_MEANINGS = {
    "psiblast": "A selected iteration count of zero preserves native until-convergence behavior. A checkpoint filename does not establish biological round, inclusion membership or convergence. Preserve optional ASN and ASCII checkpoint families in full. An omitted MSA master stays unknown; explicit master ordinals are zero-based in the request and converted to one-based native indices.",
    "deltablast": "The target sequence database and domain database are distinct operands. Domain reporting and sequence reporting must be qualified by actual source relationships; report array position does not identify a stage. Preserve selected domain and sequence inclusion thresholds independently and all actual checkpoint-family files.",
    "rpsblast": "Reference coordinates denote model positions. A displayed model master is not a biological reference sequence and does not establish a taxonomy population. Automatic native thread selection zero remains zero; resource allocation compatibility belongs to the configured resource binding.",
    "rpstblastn": "Original query coordinates are nucleotides; alignment columns and model coordinates are amino acids. Preserve the selected strand, query genetic code and native frames. A profile representative is not an independently supplied biological reference sequence. Automatic native thread selection zero remains zero.",
    "blastn_vdb": "Preserve the ordered dataset identities, selected sra_mode and include_filtered_reads selection. A selected SRA mode does not classify each hit as a read or reference. Actual run/sample/feature joins and population denominators need explicitly supplied, source-qualified metadata.",
    "tblastn_vdb": "Query units are amino acids and translated target coordinates retain their original native units. Preserve the selected database genetic code and dataset/filter scope. Native program identity may be tblastn or, for a supplied PSSM, psitblastn. Never invent a PSSM master from scores or lengths; effective biological binding remains a separate parser and metadata extractor responsibility.",
}


def _bindings(bindings):
    rows = contracts._copy(bindings)
    contracts._schema(rows, contracts._array(contracts._object({
        "program": {"enum": list(contracts.PROGRAMS)}, "mode": {"const": "database"},
        "software": contracts.SOFTWARE_SCHEMA, "database_manifests": contracts._array(contracts.FILE_IDENTITY_SCHEMA, minItems=1)})))
    seen = set()
    for row in rows:
        key = row["program"], row["mode"]
        if key in seen:
            contracts._fail("duplicate_program_mode_binding")
        seen.add(key)
        contracts._absolute(row["software"]["executable"])
        paths = set()
        for manifest in row["database_manifests"]:
            contracts._file_identity(manifest)
            if manifest["path"] in paths:
                contracts._fail("duplicate_database_manifest_binding")
            paths.add(manifest["path"])
    return rows


def native_blast_database_tool_contracts(bindings, *, resource_kind, resource_id):
    """Describe only explicit HPC bindings; grant no direct scientific execution."""
    if resource_kind != "hpc" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        contracts._fail("explicit_hpc_resource_required")
    result = []
    for binding in _bindings(bindings):
        program = binding["program"]
        schema = deepcopy(contracts.NATIVE_BLAST_DATABASE_REQUESTED_JOB_SCHEMA)
        job = schema["properties"]["native_blast_database"]
        job["properties"]["program"] = {"const": program}
        job["properties"]["software"] = {"const": binding["software"]}
        job["properties"]["databases"]["items"]["properties"]["manifest_file"] = {"enum": deepcopy(binding["database_manifests"])}
        instructions = (
            "Supply the selected native_blast_database_job_v1 with actual query bytes, exact file identities, explicit software, "
            "prepared database manifests, native paths, selected options and required outputs. Start from the supplied sequence, "
            "CLUSTAL alignment or accepted scoremat ASN text; a candidate annotation or public query name is not required. "
            + _MEANINGS[program] + " "
            "Select one JSON15 report or a tabular6/tabular7 report with exact ordered native fields and delimiter. "
            "Unrequested traceback, counts and database-population metadata remain unavailable. Metadata input descriptors "
            "declare intended consumer and schema; the producer retains complete bytes without interpreting that schema. "
            "The separate result consumer must qualify supported metadata schemas, native records and scientific relationships. "
            "Commission the exact requested_job through launch and this configured launch_hpc child. The resource child selects "
            "practical.job.start with its original allocation, queue, account and endpoint. The producer executes one selected native "
            "command after verifying the actual package/interpreter, executable, inputs, manifests and prepared database bytes. "
            "Software deployment, prepared databases, runtime dependencies and authenticated HPC access must already be established "
            "through their explicit preparation work; this operation neither installs nor fetches them. VDB requires retained actual "
            "offline configuration and complete prepared datasets. No retry, resource substitution, format fallback or hidden preparation "
            "command is part of this producer. Aurora storage remains under /lus/flare/projects/BioReason-Aurora-Test and new jobs "
            "charge EpiCalib. "
            "Monitoring uses existing resource status and selected complete-offset log observations. Native elapsed seconds measure "
            "only the native subprocess, separately from wrapper duration, queue wait and turnaround; liveness is not scientific progress. "
            "Results acquisition must authenticate the original attempt and sealed native_blast_database_bundle_v1, then verify and retain "
            "complete declared artifact bytes before separate native parsers and metadata extractors populate numerical sheets. Sequence-database, profile, "
            "iteration/PSSM and VDB results retain their distinct numerical meanings and calculators. Producer success is neither a "
            "function assignment nor a confidence score. Missing reports, unsuccessful native exits, partial captures and successful "
            "zero-hit reports remain distinct. Request only the typed facts needed by the receiving episode. Full native artifacts "
            "and sheets remain retained separately from small typed returns.")
        result.append({"name": "native." + program, "description": _DESCRIPTIONS[program], "resources": "hpc",
            "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": resource_id,
                "resource_role": "launch_hpc"}]}})
    return result


__all__ = ["native_blast_database_tool_contracts"]
