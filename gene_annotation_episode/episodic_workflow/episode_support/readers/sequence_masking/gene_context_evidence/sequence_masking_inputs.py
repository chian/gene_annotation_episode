"""Case- and occurrence-preserving readers for supplied masking artifacts.

All I/O is outside these functions. Hash checks bind the supplied bytes to their
descriptor; authentication of the producer is the host's responsibility.
"""
from __future__ import annotations

import hashlib

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, parse_sequences
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.gene_context_evidence.sequence_masking_contracts import ALPHABETS, sequence_masking_molecule, validate_sequence_masking_record


def _failure(stage, code, occurrence_id=None, record_key=None, line_number=None):
    return {"stage": stage, "code": code, "occurrence_id": occurrence_id,
            "record_key": record_key, "line_number": line_number}


def _check(name, status, record_key=None, reason=None):
    return {"name": name, "status": status, "record_key": record_key, "reason": reason}


def _bytes(content, occurrence):
    if type(content) is not bytes:
        raise ContractError("sequence_masking_bytes_required")
    if len(content) != occurrence["size_bytes"] or hashlib.sha256(content).hexdigest() != occurrence["sha256"]:
        raise ContractError("sequence_masking_content_occurrence_mismatch")


def _blocks(content):
    """Retain raw header text and line/byte positions before any normalization."""
    blocks, orphan, current, offset = [], [], None, 0
    for number, raw in enumerate(content.splitlines(keepends=True), 1):
        line = raw.decode("utf-8", errors="surrogateescape").rstrip("\r\n")
        candidate = line.lstrip()
        if candidate.startswith(">"):
            if current is not None:
                current["closed_by_header"] = True
                blocks.append(current)
            current = {"header": candidate[1:], "offset": offset, "start": number,
                       "end": number, "lines": [], "closed_by_header": False}
        elif current is not None:
            current["lines"].append((number, line))
            current["end"] = number
        elif line.strip():
            orphan.append((number, line))
        offset += len(raw)
    if current is not None:
        blocks.append(current)
    return blocks, orphan


def _unreadable(text):
    return any(0xDC80 <= ord(c) <= 0xDCFF for c in text)


def _input_observations(content, molecule, completeness):
    """One substrate reader shared by captured parsing and identity-free preflight."""
    if type(content) is not bytes:
        raise ContractError("sequence_masking_bytes_required")
    if type(molecule) is not str or molecule not in ALPHABETS:
        raise ContractError("sequence_masking_molecule")
    blocks, orphan = _blocks(content)
    records, failures = [], []
    for line, _ in orphan:
        failures.append({"code": "sequence_before_fasta_header", "record_ordinal": None, "line_number": line})
    if not blocks:
        failures.append({"code": "empty_input" if not content.strip() else "no_fasta_records",
                         "record_ordinal": None, "line_number": None})
    for ordinal, block in enumerate(blocks):
        original = "".join("".join(line.split()) for _, line in block["lines"])
        normalized = original.upper()
        invalid = []
        if not block["header"].strip():
            invalid.append(("empty_sequence_identifier", block["start"]))
        if _unreadable(block["header"]) or _unreadable(original):
            invalid.append(("input_not_utf8", block["start"]))
        if not block["closed_by_header"] and completeness != "complete":
            invalid.append(("input_record_incomplete", block["start"]))
        if set(normalized) & set("-."):
            invalid.append(("gapped_input_unsupported", block["start"]))
        if not set(normalized) <= ALPHABETS[molecule]:
            invalid.append(("unsupported_sequence_symbol", block["start"]))
        length = None if invalid else len(normalized)
        if not invalid and normalized:
            normalized = parse_sequences(original, format="raw", molecule=molecule,
                                         name=block["header"].strip().split()[0])[0].sequence
        rf = [{"code": reason, "record_ordinal": ordinal, "line_number": line} for reason, line in invalid]
        if length == 0:
            rf.append({"code": "empty_sequence", "record_ordinal": ordinal, "line_number": block["start"]})
        records.append({"record_ordinal": ordinal, "byte_offset": block["offset"], "native_header": block["header"],
            "molecule": molecule, "original_sequence": original, "normalized_sequence": normalized,
            "length": length, "failures": rf})
    return records, failures


def preflight_masking_input_fasta(content: bytes, *, molecule: str) -> dict:
    """Validate bytes before artifact capture, without invented custody identities."""
    records, failures = _input_observations(content, molecule, "complete")
    failures += [failure for record in records for failure in record["failures"]]
    return {"version": "sequence_masking_preflight", "valid": bool(records) and not failures,
            "record_count": len(records), "failures": failures}


def populate_sequence_masking_sheet(*, operation: dict, inputs: list[dict], parsed_output: dict,
        statistics: dict | None, native_outcome: dict) -> dict:
    """Combine validated supplied observations; never infer a native effective option."""
    operation = validate_sequence_masking_record("Operation", operation)
    if type(inputs) is not list:
        raise ContractError("sequence_masking_list_required")
    inputs = [validate_sequence_masking_record("InputRecord", r) for r in inputs]
    parsed_output = validate_sequence_masking_record("ParsedMaskOutput", parsed_output)
    native_outcome = validate_sequence_masking_record("NativeOutcome", native_outcome)
    if statistics is not None:
        statistics = validate_sequence_masking_record("WindowMaskerStatistics", statistics)
    checks = [r for record in inputs for r in record["checks"]] + parsed_output["checks"]
    failures = [r for record in inputs for r in record["failures"]] + parsed_output["failures"]
    if statistics is not None:
        checks += statistics["checks"]
        failures += statistics["failures"]
    elif operation["program"] == "windowmasker":
        checks.append(_check("windowmasker_statistics_available", "unknown", reason="statistics_unavailable"))
        failures.append(_failure("statistics", "statistics_unavailable"))
    if native_outcome["state"] != "succeeded":
        failures.append(_failure("native", "native_" + native_outcome["state"],
                                 parsed_output["occurrence"]["occurrence_id"]))
    checks.append(_check("native_execution", "pass" if native_outcome["state"] == "succeeded" else
                         "fail" if native_outcome["state"] == "failed" else "unknown",
                         reason=None if native_outcome["state"] == "succeeded" else "native_" + native_outcome["state"]))
    return validate_sequence_masking_record("SequenceMaskingSheet", {
        "version": "sequence_masking_sheet", "operation": operation, "inputs": inputs,
        "parsed_output": parsed_output, "statistics": statistics, "native_outcome": native_outcome,
        "checks": checks, "failures": failures})
