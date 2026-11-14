"""Configured masking information with the existing local commission route."""
from __future__ import annotations

from copy import deepcopy

from .native_blast_masking_contracts import (
    MODES, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA, SOFTWARE_SCHEMA,
    _error, _path, _schema, finite_json_copy, native_blast_masking_job_schema,
)
from .sequence_masking_contracts import sequence_masking_operation_schema


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
        elif row["mode"] == "convert_mask":
            allowed = {fmt: {"interval"} for fmt in sequence_masking_operation_schema(
                program=row["program"], mode=row["mode"])["properties"]["output_format"]["enum"]}
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
        elif mode == "convert_mask":
            description = "Convert supplied lowercase nucleotide or protein masks and retain the selected native coordinate output."
            format_meaning = "Configured output formats: " + ", ".join(row["output_formats"]) + ". "
            if set(row["output_formats"]) & {"maskinfo_xml", "maskinfo_asn1_text"}:
                format_meaning += "Configured XML or ASN.1 text output retains complete mask metadata and identifiers. "
            if "maskinfo_asn1_bin" in row["output_formats"]:
                format_meaning += ("ASN.1 binary bytes can be acquired but their reader is explicitly unavailable, "
                    "so mask quantities remain unavailable. ")
            if "interval" in row["output_formats"]:
                format_meaning += ("Interval output has no headers or record boundaries: only an explicit single-input binding "
                    "can associate it. Multi-input interval output remains unassigned. ")
            meaning = ("Supply one uncompressed, ungapped FASTA with its original letter case and explicitly declare dna or protein. "
                "Select convert_mask with lowercase_input basis. Lowercase input positions are the supplied mask; "
                "convert2blastmask converts those positions without running DUST, SEG, WindowMasker or another detector. "
                "Declare masking_algorithm and masking_options exactly; both are required and non-null, and the options text "
                "may be empty. These declarations do not authenticate an upstream detector run. They remain separate from "
                "the native normalized algorithm program name/code and options retained in structured output. "
                + format_meaning + "Native coordinates are zero-based inclusive; the shared sheet "
                "retains them and uses half-open intervals for calculations. Preserve every original input occurrence, including "
                "duplicate headers and uppercase records. The converter omits unmasked inputs; only authenticated successful "
                "complete conversion with validated source/output relationships establishes a zero-mask omission. "
                "A known-zero omission has no native interval count or invented output record. ")
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
        parameters = ("Select only the configured output formats and supply both exact conversion parameters; no native default is inserted. "
            if mode == "convert_mask" else
            "Select only the configured output formats and explicitly nullable native parameters; null omits that option. ")
        result_scope = ("Request the conversion artifacts, per-record quantities, saved common sheet or qualified failures needed by the parent. "
            "Results acquisition reads sealed retained originals through the conversion parser and the shared sequence-masking "
            "sheet and deterministic calculator, keeping input occurrences distinct even when headers repeat. "
            "Failed, partial, unsupported or unassociated output remains qualified; absent output alone never proves zero masks. "
            "These preparation quantities are not gene-function confidence. This binding accepts plain FASTA with supplied "
            "lowercase masks only. Header-plus-interval input and API/HPC execution need their own actual bindings. "
            "Unverified multi-root/list or continuation framing remains qualified as incomplete."
            if mode == "convert_mask" else
            "Request the preparation artifacts, per-record quantities, native statistics or qualified failures needed by the parent. "
            "Results acquisition reads sealed retained originals through the shared sequence-masking parser and deterministic "
            "calculator, keeping input occurrences distinct even when headers repeat. Failed and partial output remains qualified; "
            "a missing record is not a zero-mask record. These preparation quantities are not gene-function confidence. "
            "This binding supports supplied plain FASTA and ASCII statistics only; other native formats and API/HPC execution "
            "need their own actual bindings.")
        instructions = (meaning + parameters +
            "Commission the requested job through launch and its configured launch_local child, which selects practical.job.start "
            "under the caller's allocation. The producer runs one selected command and retains original input bytes, selected "
            "output, stdout and stderr. Invalid or empty input is retained with failure and is not silently repaired. "
            "Monitoring can read original native status and selected log windows; liveness alone does not establish productive work. "
            + result_scope)
        result.append({"name": "native." + program + "." + mode, "description": description,
            "resources": "local", "instructions": instructions, "input_schema": schema,
            "invocation_route": {"kind": "commission", "routes": [{"entry_role": "launch",
                "resource_id": resource_id, "resource_role": "launch_local"}]}})
    return result
