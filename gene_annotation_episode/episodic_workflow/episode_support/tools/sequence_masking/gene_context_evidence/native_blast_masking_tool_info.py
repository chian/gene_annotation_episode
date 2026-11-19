"""Configured masking information with the existing local commission route."""
from __future__ import annotations


from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.gene_context_evidence.native_blast_masking_contracts import MODES, SOFTWARE_SCHEMA, _error, _path, _schema, finite_json_copy
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.gene_context_evidence.sequence_masking_contracts import sequence_masking_operation_schema


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


