"""Four-field scientific information and separate configured host contracts.

Bindings are explicit rows {program, mode, software}; the caller supplies the
local or HPC resource separately. There is no executable discovery.
The caller installs the existing launch/resource/results route separately.
"""
from __future__ import annotations

import re

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_hmmer_contracts import PROGRAMS, finite_json_copy, _absolute




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


