"""Case- and occurrence-preserving readers for supplied masking artifacts.

All I/O is outside these functions. Hash checks bind the supplied bytes to their
descriptor; authentication of the producer is the host's responsibility.
"""
from __future__ import annotations

import hashlib
import re

from .domain import ContractError, parse_sequences
from .sequence_masking_contracts import ALPHABETS, _mask_runs, sequence_masking_molecule, validate_sequence_masking_record


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
    return {"version": "sequence_masking_preflight_v1", "valid": bool(records) and not failures,
            "record_count": len(records), "failures": failures}


def parse_masking_input_fasta(content: bytes, *, occurrence: dict, molecule: str) -> dict:
    """Read captured FASTA with exact case, original ordinal and byte positions.

    Shared preflight/parse logic uses the existing normalized-sequence reader for
    valid nonempty records, and retains invalid/empty records without repair.
    """
    occurrence = validate_sequence_masking_record("Occurrence", occurrence)
    if occurrence["direction"] != "input" or occurrence["role"] not in ("sequences", "reference_sequences"):
        raise ContractError("sequence_masking_input_occurrence")
    _bytes(content, occurrence)
    observations, file_failures = _input_observations(content, molecule, occurrence["completeness"])
    oid, records, checks = occurrence["occurrence_id"], [], []
    failures = [_failure("input", r["code"], oid, line_number=r["line_number"]) for r in file_failures]
    for observed in observations:
        key = oid + "#/records/" + str(observed["record_ordinal"])
        length = observed["length"]
        rf = [_failure("input", r["code"], oid, key, r["line_number"]) for r in observed["failures"]]
        invalid = [r for r in observed["failures"] if r["code"] != "empty_sequence"]
        rc = [_check("input_substrate", "fail" if invalid else "pass", key,
                     invalid[0]["code"] if invalid else None)]
        if length == 0:
            rc.append(_check("native_nonempty_input", "fail", key, "empty_sequence"))
        else:
            rc.append(_check("native_nonempty_input", "unknown" if length is None else "pass", key,
                             "input_length_unavailable" if length is None else None))
        record = {**observed, "record_key": key, "occurrence": occurrence, "checks": rc, "failures": rf}
        records.append(record); checks.extend(rc); failures.extend(rf)
    checks.append(_check("input_fasta_syntax", "fail" if file_failures else "pass",
                         reason="malformed_or_empty_input" if file_failures else None))
    return validate_sequence_masking_record("InputParse", {
        "version": "sequence_masking_input_v1", "occurrence": occurrence, "records": records,
        "checks": checks, "failures": failures})


def parse_sequence_masking_output(content: bytes, *, format: str, occurrence: dict,
        input_records: list[dict], operation: dict, custody: dict) -> dict:
    """Populate native interval/FASTA observations without numerical aggregation."""
    operation = validate_sequence_masking_record("Operation", operation)
    occurrence = validate_sequence_masking_record("Occurrence", occurrence)
    custody = validate_sequence_masking_record("Custody", custody)
    if type(input_records) is not list:
        raise ContractError("sequence_masking_list_required")
    input_records = [validate_sequence_masking_record("InputRecord", r) for r in input_records]
    inputs = {r["record_key"]: r for r in input_records}
    if len(inputs) != len(input_records) or set(inputs) != set(custody["sequence_order"]):
        raise ContractError("sequence_masking_input_population")
    if format not in ("interval", "fasta") or operation["mode"] != "mask" or operation["output_format"] != format:
        raise ContractError("sequence_masking_output_format")
    if occurrence["role"] != "mask":
        raise ContractError("sequence_masking_output_occurrence")
    _bytes(content, occurrence)
    blocks, orphan = _blocks(content)
    records, unassigned, checks, failures = [], [], [], []
    oid = occurrence["occurrence_id"]
    for line, _ in orphan:
        failures.append(_failure("parse", "data_before_output_header", oid, line_number=line))
    if not blocks:
        failures.append(_failure("parse", "mask_output_absent", oid))
    closed_output = custody["output_complete"] and occurrence["completeness"] == "complete" and custody["native_returncode"] in (0, None)
    native_order = (closed_output and custody["native_returncode"] == 0 and
        custody["producer_kind"] == "authenticated_native" and custody["order_basis"] == "native_fasta_iteration" and
        len(blocks) == len(inputs) and bool(inputs) and not orphan and
        all(r["length"] is not None and r["length"] > 0 for r in inputs.values()))
    bindings = {b["output_record_ordinal"]: b for b in custody["record_bindings"]}
    # Explicit declarations also preserve supplied artifacts and proved partial rows.
    for ordinal in bindings:
        if ordinal >= len(blocks):
            failures.append(_failure("association", "bound_output_record_absent", oid,
                                     bindings[ordinal]["input_record_key"]))
    for ordinal, block in enumerate(blocks):
        key, association = None, "unresolved"
        if ordinal in bindings:
            binding = bindings[ordinal]
            key = binding["input_record_key"]
            association = "authenticated_native_order" if binding["basis"] == "native_fasta_iteration" else "caller_declared"
        elif native_order:
            key = custody["sequence_order"][ordinal]
            association = "authenticated_native_order"
        rf = []
        def fail(code, line=None, stage="parse"):
            rf.append(_failure(stage, code, oid, key, line))
        if key is None:
            fail("output_record_unassociated", block["start"], "association")
        complete = bool(block["closed_by_header"] or closed_output)
        if not complete:
            fail("output_record_incomplete", block["start"])
        if not block["header"].strip():
            fail("empty_output_header", block["start"])
        if _unreadable(block["header"]):
            fail("output_not_utf8", block["start"])
        source = inputs.get(key)
        expected_molecule = sequence_masking_molecule(operation)
        if source is not None and source["molecule"] != expected_molecule:
            fail("incompatible_input_molecule", stage="input")
        if source is not None and source["length"] is None:
            fail("input_substrate_unavailable", stage="input")
        native_intervals, intervals, sequence = [], [], None
        measurement = "unavailable"
        if format == "interval":
            for number, line in block["lines"]:
                if not line.strip():
                    continue
                match = re.fullmatch(r"\s*([0-9]+)\s*-\s*([0-9]+)\s*", line)
                if match is None:
                    fail("malformed_interval_row", number); continue
                try:
                    start, end = map(int, match.groups())
                except ValueError:
                    fail("malformed_interval_row", number); continue
                native_intervals.append({"start": start, "end_inclusive": end, "line_number": number})
                if start > end:
                    fail("reversed_interval", number)
                elif source is not None and source["length"] is not None and end >= source["length"]:
                    fail("interval_out_of_bounds", number)
                else:
                    intervals.append([start, end + 1])
            if not rf:
                measurement = "exact_mask"
        else:
            sequence = "".join("".join(line.split()) for _, line in block["lines"])
            normalized = sequence.upper()
            if operation["masking_style"] == "soft":
                intervals = _mask_runs([c.islower() for c in sequence])
            if _unreadable(sequence):
                fail("output_not_utf8", block["start"])
            if not set(normalized) <= ALPHABETS[expected_molecule]:
                fail("unsupported_output_symbol", block["start"])
            if source is not None and source["length"] is not None:
                if len(normalized) != source["length"]:
                    fail("output_sequence_length_mismatch", block["start"])
                elif operation["masking_style"] == "soft":
                    if normalized != source["normalized_sequence"]:
                        fail("output_sequence_symbol_change", block["start"])
                    if not rf:
                        measurement = "exact_mask"
                else:
                    original = source["normalized_sequence"]
                    if any(a != b and b != "N" for a, b in zip(original, normalized)):
                        fail("hard_mask_non_n_substitution", block["start"])
                    intervals = _mask_runs([a != b and b == "N" for a, b in zip(original, normalized)])
                    if not rf:
                        measurement = "hard_mask_ambiguous" if "N" in original else "exact_mask"
        row = {"output_record_ordinal": ordinal, "input_record_key": key,
            "native_header": block["header"], "output_locator": {"byte_offset": block["offset"],
                "line_start": block["start"], "line_end": block["end"]},
            "native_intervals": native_intervals, "intervals_half_open": intervals,
            "output_sequence": sequence, "association": association,
            "completeness": "complete" if complete else "partial", "measurement": measurement, "failures": rf}
        (records if key is not None else unassigned).append(row)
        failures.extend(rf)
        checks.append(_check("mask_measurement", "pass" if measurement == "exact_mask" else "unknown", key,
                             None if measurement == "exact_mask" else
                             "hard_mask_ambiguous" if measurement == "hard_mask_ambiguous" else
                             rf[0]["code"] if rf else "mask_measurement_unavailable"))
    present = {r["input_record_key"] for r in records}
    for key in custody["sequence_order"]:
        if key not in present:
            failures.append(_failure("association", "input_mask_record_absent", oid, key))
    checks.append(_check("mask_output_population", "pass" if len(blocks) == len(inputs) else "fail",
                         reason=None if len(blocks) == len(inputs) else "output_population_mismatch"))
    checks.append(_check("mask_output_custody", "pass" if closed_output else "unknown",
                         reason=None if closed_output else "output_not_successfully_closed"))
    checks.append(_check("mask_association_provenance", "pass" if native_order else "unknown",
                         reason=None if native_order else "explicit_or_unresolved_association"))
    return validate_sequence_masking_record("ParsedMaskOutput", {
        "version": "sequence_masking_parsed_output_v1", "format": format, "occurrence": occurrence,
        "custody": custody, "records": records, "unassigned_records": unassigned,
        "checks": checks, "failures": failures})


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
        "version": "sequence_masking_sheet_v1", "operation": operation, "inputs": inputs,
        "parsed_output": parsed_output, "statistics": statistics, "native_outcome": native_outcome,
        "checks": checks, "failures": failures})
