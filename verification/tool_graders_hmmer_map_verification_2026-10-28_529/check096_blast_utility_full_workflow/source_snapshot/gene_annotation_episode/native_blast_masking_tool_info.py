"""Configured masking information with the existing local commission route."""
from __future__ import annotations

from copy import deepcopy

from .native_blast_masking_contracts import (
    MODES, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA, SOFTWARE_SCHEMA,
    _error, _path, _schema, finite_json_copy, native_blast_masking_job_schema,
)


def validate_native_blast_masking_bindings(rows):
    rows = finite_json_copy(rows)
    if type(rows) is not list:
        _error("binding_rows_required")
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {"program", "mode", "software", "output_formats", "masking_styles"}
                or type(row["program"]) is not str or type(row["mode"]) is not str
                or (row["program"], row["mode"]) not in MODES):
            _error("configured_binding_invalid")
        key = row["program"], row["mode"]
        if key in seen:
            _error("duplicate_program_mode_binding")
        seen.add(key)
        _schema(row["software"], SOFTWARE_SCHEMA)
        _path(row["software"]["executable"], absolute=True)
        for field in ("output_formats", "masking_styles"):
            if type(row[field]) is not list or not row[field] or any(type(v) is not str for v in row[field]) or len(set(row[field])) != len(row[field]):
                _error("configured_formats_invalid")
        formats, styles = set(row["output_formats"]), set(row["masking_styles"])
        allowed = {"interval": {"interval"}, "fasta": {"soft", "hard"} if row["program"] == "dustmasker" else {"soft"}}
        if row["mode"] == "create_counts":
            allowed = {"ascii_statistics": {"not_applicable"}}
        if not formats <= allowed.keys() or not styles <= set().union(*(allowed[f] for f in formats)) or any(not allowed[f] & styles for f in formats):
            _error("configured_format_style_conflict")
    return rows


def native_blast_masking_tool_contracts(bindings, *, resource_kind, resource_id):
    if resource_kind != "local" or type(resource_id) is not str or not resource_id or "\0" in resource_id:
        _error("configured_local_resource_required")
    result = []
    for row in validate_native_blast_masking_bindings(bindings):
        program, mode = row["program"], row["mode"]
        schema = deepcopy(NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA)
        job_schema = native_blast_masking_job_schema(program=program, mode=mode)
        job_schema["properties"]["software"] = {"const": row["software"]}
        job_schema["properties"]["operation"]["allOf"] = [{"properties": {
            "output_format": {"enum": row["output_formats"]}, "masking_style": {"enum": row["masking_styles"]}}}]
        schema["properties"]["native_blast_masking"] = job_schema
        if mode == "create_counts":
            description = "Create retained ASCII WindowMasker statistics from one supplied nucleotide reference FASTA."
            meaning = ("Supply the reference FASTA whose unit counts are required. Select create_counts explicitly and ASCII output. "
                "Retain all native code/count rows, metadata, percentile rows and reported thresholds. Counts may be clipped; "
                "absent units are not measured zeros. Requested count clipping thresholds and reported percentile-derived "
                "thresholds have distinct meanings. Request the generated statistics artifact and its actual reference association "
                "for any later separately selected masking command. Counts creation does not mask a target sequence. ")
        else:
            molecule = "protein" if program == "segmasker" else "nucleotide"
            description = "Prepare " + molecule + " sequences with " + program + " and retain the selected mask output."
            meaning = ("Supply one uncompressed, ungapped " + molecule + " FASTA. Select interval output or an explicitly supported "
                "FASTA masking style. Interval endpoints are native zero-based inclusive; the shared sheet retains them and "
                "uses half-open intervals for calculations. Lowercase output indicates soft masks; existing input lowercase "
                "is not an inherited mask. Exact masked fractions describe prepared positions over the same input record length. ")
            if program == "dustmasker":
                meaning += ("DUST hard FASTA changes selected positions to N; pre-existing N makes total masking ambiguous. "
                    "Changed symbols and masked positions remain separate quantities. ")
            if program == "windowmasker":
                meaning += ("Supply the selected ASCII statistics file and its known or unknown reference provenance. "
                    "The background reference may differ from the target. No counts file is created automatically. "
                    "Retain requested parameters, native statistics and warnings separately; omitted options remain unspecified. ")
        instructions = (meaning +
            "Select only the configured output formats and explicitly nullable native parameters; null omits that option. "
            "Commission the requested job through launch and its configured launch_local child, which selects practical.job.start "
            "under the caller's allocation. The producer runs one selected command and retains original input bytes, selected "
            "output, stdout and stderr. Invalid or empty input is retained with failure and is not silently repaired. "
            "Monitoring can read original native status and selected log windows; liveness alone does not establish productive work. "
            "Request the preparation artifacts, per-record quantities, native statistics or qualified failures needed by the parent. "
            "Results acquisition reads sealed retained originals through the shared sequence-masking parser and deterministic "
            "calculator, keeping input occurrences distinct even when headers repeat. Failed and partial output remains qualified; "
            "a missing record is not a zero-mask record. These preparation quantities are not gene-function confidence. "
            "This binding supports supplied plain FASTA and ASCII statistics only; other native formats and API/HPC execution "
            "need their own actual bindings.")
        result.append({"name": "native." + program + "." + mode, "description": description,
            "resources": "local", "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch",
                "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return result
