"""Four-field scientific information and separate configured host contracts.

Bindings are explicit rows {program, mode, software}; the caller supplies the
local or HPC resource separately. There is no executable discovery.
The caller installs the existing launch/resource/results route separately.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .native_hmmer_contracts import (
    NATIVE_HMMER_JOB_SCHEMA, NATIVE_HMMER_REQUESTED_JOB_SCHEMA, PROGRAMS,
    finite_json_copy, operand_contract, output_contract, _absolute,
)


_DESCRIPTIONS = {
    "hmmscan": "Search supplied protein sequences against an explicitly supplied pressed profile database.",
    "hmmsearch": "Search supplied protein profiles against an explicitly supplied sequence database.",
    "jackhmmer": "Iteratively search supplied protein queries against an explicitly supplied sequence database.",
    "nhmmer": "Search nucleotide sequences using an explicitly selected sequence, profile or alignment query.",
    "nhmmscan": "Search supplied nucleotide sequences against an explicitly supplied pressed nucleotide profile database.",
    "hmmalign": "Align supplied sequences to exactly one supplied profile, optionally including its original alignment.",
}
_MEANINGS = {
    "hmmscan": "The model axis is the hit profile; the sequence axis is the query. Preserve full-sequence and domain bit scores, E-values, bias, coordinates, reporting/inclusion state and native posterior bins. Profile-consensus matches are distinct from actual sequence identities.",
    "hmmsearch": "The model axis is the query profile; the sequence axis is the database target. Preserve full-sequence and domain bit scores, E-values, bias, coordinates, reporting/inclusion state and native posterior bins.",
    "jackhmmer": "Preserve every native stdout iteration. Tables and -A are final-round outputs; model checkpoints are used at round start and alignment checkpoints describe included rows at round end. Checkpoint files can contain multiple queries. Native convergence does not control episode continuation.",
    "nhmmer": "Preserve query-construction mode, strand, local locus bit scores, E-values, bias, model coordinates and sequence coordinates. The table length is target sequence length. -Z is millions of nucleotides with native strand scaling. Separate sequence, profile and alignment query modes.",
    "nhmmscan": "Preserve strand, local locus bit scores, E-values, bias and model/sequence coordinates. The table length is target model length; sequence coverage needs the actual query length. Descending reverse-strand coordinates retain their direction.",
    "hmmalign": "Retain all Stockholm rows, RF, PP and original annotations. Model occupancy is match-state residues divided by profile length; sequence match coverage uses original sequence length. PP characters provide probability intervals. Inserts do not establish homologous residue correspondence. --trim removes terminal residues; --mapali identifies inherited rows and requires the profile's original map/checksum-compatible alignment.",
}


def validate_native_hmmer_bindings(value):
    rows = finite_json_copy(value)
    if type(rows) is not list:
        raise ValueError("native_hmmer_explicit_binding_rows_required")
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {"program", "mode", "software"}
                or row["program"] not in PROGRAMS):
            raise ValueError("native_hmmer_invalid_configured_binding")
        modes = (["sequence", "profile", "alignment"] if row["program"] == "nhmmer"
                 else ["align"] if row["program"] == "hmmalign" else ["search"])
        if row["mode"] not in modes:
            raise ValueError("native_hmmer_invalid_configured_mode")
        software = row["software"]
        if (type(software) is not dict or set(software) != {"executable", "sha256", "engine_version"}
                or type(software["executable"]) is not str or not software["executable"].startswith("/")
                or type(software["sha256"]) is not str or not re.fullmatch(r"[0-9a-fA-F]{64}", software["sha256"])
                or software["engine_version"] is not None and (type(software["engine_version"]) is not str
                    or not software["engine_version"] or "\0" in software["engine_version"])):
            raise ValueError("native_hmmer_invalid_configured_software")
        _absolute(software["executable"])
        key = row["program"], row["mode"]
        if key in seen:
            raise ValueError("native_hmmer_duplicate_program_mode_binding")
        seen.add(key)
    return rows


def native_hmmer_tool_contracts(bindings, *, resource_kind, resource_id):
    """Commissioning contracts only; no direct scientific invocation grant."""
    if (type(resource_kind) is not str or resource_kind not in {"local", "hpc"}
            or type(resource_id) is not str or not resource_id or "\0" in resource_id):
        raise ValueError("native_hmmer_explicit_resource_required")
    grouped = {}
    for binding in validate_native_hmmer_bindings(bindings):
        grouped.setdefault(binding["program"], []).append(binding)
    entries = []
    for program, rows in grouped.items():
        modes = [row["mode"] for row in rows]
        mode_details = []
        for mode in modes:
            required, optional = operand_contract(program, mode)
            required_outputs, optional_outputs = output_contract(program, mode)
            mode_details.append("Mode " + mode + ": supply " + ", ".join(required)
                + ("; optional operands " + ", ".join(optional) if optional else "")
                + ". Retain " + ", ".join(required_outputs)
                + ("; selected optional outputs " + ", ".join(optional_outputs) if optional_outputs else "") + ".")
        instructions = " ".join(mode_details) + " " + _MEANINGS[program] + (
            " Supply exact input identities, declared formats, native options and explicit query/target metadata;"
            " unavailable lengths, cutoffs or database-population measurements remain unavailable."
            " Commission the selected job through the existing launch episode and its configured local-compute or HPC child."
            " That child prepares the selected resource and uses practical.job.start; monitoring reads the original"
            " execution through its existing status operation, and results acquisition obtains the sealed bundle"
            " and complete original artifacts. No index is built implicitly."
            " The deterministic HMMER parser, numerical sheet and calculator retain separate responsibilities."
            " Request the numerical quantities and subject/reference relationships needed by the receiving episode."
            " Native scores and posterior quantities are not probabilities of gene-function correctness."
            " Missing, failed, partial and complete zero-result searches remain distinct."
            " This information does not permit direct native execution inside a scientific episode.")
        schema = deepcopy(NATIVE_HMMER_REQUESTED_JOB_SCHEMA)
        schema["properties"]["native_hmmer"]["allOf"].append({"oneOf": [
            {"properties": {"program": {"const": row["program"]}, "mode": {"const": row["mode"]},
                            "software": {"const": row["software"]}}} for row in rows]})
        entries.append({"name": "native." + program, "description": _DESCRIPTIONS[program],
                        "resources": resource_kind, "instructions": instructions, "input_schema": schema,
                        "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch",
                            "resource_id": resource_id, "resource_role": "launch_" + resource_kind}]}})
    return entries


def native_hmmer_tool_information(bindings, *, resource_kind, resource_id):
    """Public child_tool_info contains exactly these four fields."""
    return [{key: row[key] for key in ("name", "description", "resources", "instructions")}
            for row in native_hmmer_tool_contracts(bindings, resource_kind=resource_kind, resource_id=resource_id)]
