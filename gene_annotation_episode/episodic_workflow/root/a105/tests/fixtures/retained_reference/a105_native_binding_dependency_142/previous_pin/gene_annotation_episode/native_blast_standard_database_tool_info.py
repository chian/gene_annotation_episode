"""Real invocation information for explicitly declared standard database bindings.

The returned commission contract describes a selected HPC operation. It does
not install that operation, authenticate access, or claim a results deployment.
"""
from __future__ import annotations

from copy import deepcopy

from . import native_blast_standard_database_contracts as contracts

_DESCRIPTIONS = {
    "blastn": "Search a selected prepared nucleotide sequence database with supplied nucleotide FASTA queries.",
    "blastp": "Search a selected prepared protein sequence database with supplied protein FASTA queries.",
    "blastx": "Search a selected prepared protein sequence database with translated supplied nucleotide FASTA queries.",
    "tblastn": "Search a selected prepared nucleotide sequence database with supplied protein FASTA queries or one supplied protein PSSM.",
    "tblastx": "Search a selected prepared nucleotide sequence database with translated supplied nucleotide FASTA queries, retaining both translated coordinate axes.",
}
_MEANINGS = {
    "blastn": "Query coordinates, reference coordinates and alignment columns are nucleotides. Preserve selected task, strand, range, scores and masking.",
    "blastp": "Query coordinates, reference coordinates and alignment columns are amino acids. Preserve substitutions and gaps separately from paired residues.",
    "blastx": "Query coordinates and full or selected query lengths are original nucleotides; reference coordinates and alignment columns are amino acids. Preserve query genetic code and native frame; each paired translated query residue occupies three original nucleotides.",
    "tblastn": "Query coordinates and alignment columns are amino acids; reference coordinates and full reference lengths are original nucleotides. Preserve database genetic code and native reference frame. Each paired translated reference residue occupies three original nucleotides. A selected text ASN PSSM compiles to -in_pssm and may report the native program alias psitblastn. Its actual master and column map require a separate supplied-byte reader; never derive a consensus or substitute the number of model positions for proven biological identity.",
    "tblastx": "Both query and reference coordinates and full lengths are original nucleotides; alignment columns are amino acids. Preserve both genetic codes, native frames and directions. Each paired residue occupies three nucleotides on both original axes. Alternative frames and repeated accessions do not establish independent references. This native program has no task, gap-open/extend, ungapped, mt_mode or composition-statistics option.",
}


def _bindings(bindings):
    rows = contracts._copy(bindings)
    contracts._schema(rows, contracts._array(contracts._object({
        "program": {"enum": list(contracts.PROGRAMS)}, "mode": {"const": "database"},
        "software": contracts.SOFTWARE_SCHEMA,
        "database_manifests": contracts._array(contracts.FILE_IDENTITY_SCHEMA, minItems=1)})))
    seen = set()
    for row in rows:
        if row["program"] in seen:
            contracts._fail("duplicate_program_mode_binding")
        seen.add(row["program"])
        contracts._absolute(row["software"]["executable"])
        paths = set()
        for manifest in row["database_manifests"]:
            contracts._file_identity(manifest)
            if manifest["path"] in paths:
                contracts._fail("duplicate_database_manifest_binding")
            paths.add(manifest["path"])
    return rows


def standard_blast_database_tool_contracts(bindings: list[dict], *, resource_kind: str,
                                          resource_id: str) -> list[dict]:
    """Describe each caller-bound commission; no discovery, execution or grading."""
    if resource_kind != "hpc" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        contracts._fail("explicit_hpc_resource_required")
    result = []
    for binding in _bindings(bindings):
        program = binding["program"]
        spec = contracts.standard_blast_database_program_spec(program)
        schema = deepcopy(contracts.NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA)
        job = schema["properties"]["native_blast_standard_database"]
        job["properties"]["program"] = {"const": program}
        job["properties"]["software"] = {"const": binding["software"]}
        job["properties"]["query"]["properties"]["kind"] = {"enum": spec["query_kinds"]}
        db = job["properties"]["databases"]["items"]["properties"]
        db["kind"] = {"const": spec["database_kind"]}
        db["manifest_file"] = {"enum": deepcopy(binding["database_manifests"])}
        instructions = (
            "Search the supplied query input against the explicitly selected prepared sequence database. "
            "Supply native_blast_standard_database_job_v1 with actual input paths and byte identities, selected software, "
            "the complete prepared database manifest and inventory, exact options and three required output selections. "
            "A candidate annotation or publicly searchable query name is not required. Preserve every FASTA record and its "
            "original ordinal, including repeated identifiers. " + _MEANINGS[program] + " "
            "Select one single-file JSON15 report or tabular6/tabular7 with explicit ordered fields and delimiter; null "
            "delimiter means the native tab. Tables require qseqid and sseqid. Complete geometry additionally needs "
            "qlen, slen, qstart, qend, sstart, send, qseq, sseq, length, nident, positive, gaps, score, bitscore, evalue "
            "and the relevant qframe/sframe or frames fields. Those fields are never injected into your selection; "
            "unreported quantities remain unavailable. qcovus is available only for blastn. A BTOP string alone does "
            "not establish missing aligned symbols. Native multi-valued accession, title and taxon lists do not establish "
            "one-to-one biological associations. Preserve full input length, selected interval width and reported length separately. "
            "Select only options admitted by validate_standard_blast_database_options; arbitrary argv, subject/remote mode, "
            "untracked files, database restriction/filtering and index options are unsupported in this version. "
            "Commission the exact requested_job through launch and the configured launch_hpc child. Its existing resource "
            "episode selects practical.job.start under the original caller allocation, queue, account and endpoint. "
            "The bound producer entry is run_standard_blast_database_plan in "
            "gene_annotation_episode.native_blast_standard_database_driver; compile_standard_blast_database_argv "
            "defines its selected native command. The producer checks actual package/interpreter/runtime bytes, executable, "
            "inputs, manifests, all selected database files and metadata sidecars before that one command. "
            "A declared binding or matching inventory hash does not establish installed software, usable databases, "
            "authenticated access or a deployed results path. Preparation and access remain separately established work. "
            "No download, database selection, index creation, format fallback, retry or resource substitution is part of this operation. "
            "Aurora files remain under /lus/flare/projects/BioReason-Aurora-Test and new PBS jobs charge EpiCalib. "
            "Monitoring uses existing resource status and selected complete-offset stdout/stderr observations. Native "
            "subprocess elapsed seconds remain separate from queue wait, wrapper duration and turnaround; liveness "
            "alone is not productive scientific progress. "
            "Results acquisition authenticates the original attempt and native_blast_standard_database_bundle_v1, "
            "retains all original artifacts, then uses separate native readers and metadata extractors to populate the "
            "standard sequence-database numerical fields. Separate calculators consume the saved sheets and explicit "
            "parameters without executing or reacquiring the search. Explicit function assignments, full-sequence "
            "duplicate proofs, source-qualified taxonomic/quality measurements and an actual matching population census "
            "are separate inputs; titles, best hits, hit limits and native dbsize do not supply them. "
            "The existing conditional reference kernel uses maximum group bit scores, explicit function allocation, "
            "selected priors and temperature, and a qualified census for representation adjustment. Taxonomy, target "
            "taxonomy, assembly quality, evidence categories, coverage, identity and study dependence are retained but "
            "are not coefficients in that kernel. Conditional reference weights are not calibrated annotation probabilities. "
            "Retain nonzero native exits, missing or partial artifacts and successful closed zero-hit outputs as different "
            "states. Producer success supplies execution facts and artifacts, not annotation credit or function confidence. "
            "Return only the receiving episode's requested typed facts; retain complete native bytes and numerical "
            "sheets separately. This descriptor does not grant direct execution to root or a scientific episode.")
        result.append({"name": "native." + program + ".database", "description": _DESCRIPTIONS[program],
            "resources": "hpc", "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": resource_id,
                "resource_role": "launch_hpc"}]}})
    return result


__all__ = ["standard_blast_database_tool_contracts"]
