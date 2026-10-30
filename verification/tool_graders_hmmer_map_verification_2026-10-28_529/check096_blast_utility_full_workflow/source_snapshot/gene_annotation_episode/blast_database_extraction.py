"""Pure, occurrence-preserving readers for selected ``blastdbcmd`` sequences.

The fixed native format is ``%o\t%i\t%a\t%l\t%s``. The existing sequence
parser owns alphabet interpretation. This supporting reader adds no scientific
score, acquisition, file access or native invocation.
"""
from __future__ import annotations

import hashlib
import re

from .blast_utility_contracts import validate_blast_utility_record
from .domain import ContractError, parse_sequences


def _failure(stage, code, occurrence_id=None, record_key=None, line_number=None,
             native_returncode=None):
    return {"stage": stage, "code": code, "occurrence_id": occurrence_id,
            "record_key": record_key, "line_number": line_number,
            "native_returncode": native_returncode}


def _check(name, status, subjects, method, evidence, reason=None):
    return {"name": name, "status": status, "subject_refs": list(dict.fromkeys(subjects)),
            "method": method, "reason": reason,
            "evidence_occurrence_ids": list(dict.fromkeys(evidence))}


def _reader_context(occurrence, operation, database_binding, outcome, *, program, modes):
    occurrence = validate_blast_utility_record("ArtifactOccurrence", occurrence)
    operation = validate_blast_utility_record("Operation", operation)
    database_binding = validate_blast_utility_record("DatabaseBinding", database_binding)
    outcome = validate_blast_utility_record("NativeOutcome", outcome)
    if operation["program"] != program or operation["mode"] not in modes:
        raise ContractError("blast_utility_reader_operation")
    if occurrence["direction"] != "output":
        raise ContractError("blast_utility_reader_output_occurrence")
    if operation["database_key"] != database_binding["database_key"]:
        raise ContractError("blast_utility_database_key_mismatch")
    if database_binding["kind"] == "vdb":
        raise ContractError("blast_utility_incompatible_database_format")
    if operation["molecule"] != database_binding["molecule"]:
        raise ContractError("blast_utility_database_kind_conflict")
    if occurrence["occurrence_id"] in set(operation["input_occurrence_ids"]) | set(database_binding["occurrence_ids"]):
        raise ContractError("blast_utility_duplicate_occurrence_identity")
    return occurrence, operation, database_binding, outcome


def _check_bytes(content, occurrence):
    if type(content) is not bytes:
        raise ContractError("blast_utility_bytes_required")
    if len(content) != occurrence["size_bytes"] or hashlib.sha256(content).hexdigest() != occurrence["sha256"]:
        raise ContractError("blast_utility_input_identity_mismatch")
    return _check("custody", "pass", [occurrence["occurrence_id"]], "identity_digest",
                  [occurrence["occurrence_id"]])


def _complete_capture(occurrence, outcome):
    return (occurrence["completeness"] == "complete" and outcome["writer_closed"]
            and outcome["inventory_complete"])


def _outcome_observations(outcome, occurrences, database_key):
    ids = [o["occurrence_id"] for o in occurrences]
    checks, failures = [], []
    if outcome["state"] == "succeeded":
        status, reason = "pass", None
    elif outcome["state"] == "failed":
        status = "fail"
        reason = "native_nonzero_exit" if outcome["started"] else "native_start_failed"
    else:
        status, reason = "unknown", "output_inventory_incomplete"
    checks.append(_check("native_execution", status, [database_key],
                         "native_execution_outcome", ids, reason))
    if reason:
        failures.append(_failure("native" if outcome["state"] == "failed" else "capture",
                                 reason, ids[0], native_returncode=outcome["returncode"]))
    if not all(_complete_capture(o, outcome) for o in occurrences):
        if not any(f["code"] == "output_inventory_incomplete" for f in failures):
            failures.append(_failure("capture", "output_inventory_incomplete", ids[0]))
    return checks, failures


def _bindings(value, selectors):
    if value is None:
        return {}
    if type(value) is not list:
        raise ContractError("blast_utility_record_bindings")
    result = {}
    for row in value:
        if type(row) is not dict or set(row) != {"native_row_ordinal", "selector_ordinals"}:
            raise ContractError("blast_utility_record_bindings")
        ordinal, selected = row["native_row_ordinal"], row["selector_ordinals"]
        if (type(ordinal) is not int or ordinal < 0 or ordinal in result or
                type(selected) is not list or not selected or
                any(type(s) is not int or s not in selectors for s in selected) or
                len(set(selected)) != len(selected)):
            raise ContractError("blast_utility_record_bindings")
        result[ordinal] = list(selected)
    return result


def _nonnegative_int(text):
    if not re.fullmatch(r"[0-9]+", text):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _sequence_symbols(original, molecule):
    """Use the established alphabet parser, retaining invalid source symbols."""
    normalized = original.upper()
    # Whitespace is not sequence data in this five-column one-line native format.
    if not original or any(c.isspace() for c in original):
        return normalized, None
    try:
        parsed = parse_sequences(original, format="raw", molecule=molecule)[0]
    except ContractError:
        return normalized, None
    if "unexpected_symbol_for_declared_molecule" in parsed.issues:
        return normalized, None
    return parsed.sequence, len(parsed.sequence)


def parse_blastdbcmd_sequences(content: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict, record_bindings: list[dict] | None = None) -> dict:
    """Read original native rows, preserving missing requests and partial work.

    ``%l`` is the full stored sequence length, including for ranged output. Native
    range clipping is represented only when its reported full length and actual
    returned symbols agree. Exact identifier/accession equality joins all matching
    selector occurrences; other aliases require explicit caller bindings.
    """
    occurrence, operation, database_binding, outcome = _reader_context(
        occurrence, operation, database_binding, outcome,
        program="blastdbcmd", modes={"extract_sequences"})
    if occurrence["role"] not in {"extracted_sequences", "stdout"} or occurrence["native_format"] != "blastdbcmd_tabular_v1":
        raise ContractError("blast_utility_reader_output_occurrence")
    oid = occurrence["occurrence_id"]
    checks = [_check_bytes(content, occurrence)]
    native_checks, failures = _outcome_observations(outcome, [occurrence], database_binding["database_key"])
    checks.extend(native_checks)
    params = operation["parameters"]
    selectors = {s["ordinal"]: s["value"] for s in params["selectors"]}
    bindings = _bindings(record_bindings, selectors)
    records, malformed, unexpected = [], [], []
    lines = content.splitlines(keepends=True)
    for ordinal, raw in enumerate(lines):
        line_number, key = ordinal + 1, oid + "#/records/" + str(ordinal)
        line = raw.rstrip(b"\r\n")
        try:
            parts = line.decode("utf-8").split("\t")
        except UnicodeDecodeError:
            parts = []
        if len(parts) != 5 or not parts[1] or any(c.isspace() or ord(c) < 32 for c in parts[1]):
            malformed.append(ordinal)
            failures.append(_failure("parse", "native_row_invalid", oid, key, line_number))
            continue
        oid_text, identifier, accession, length_text, original = parts
        native_oid, native_length = _nonnegative_int(oid_text), _nonnegative_int(length_text)
        accession = accession or None
        rf, rc = [], []

        def fail(stage, code):
            rf.append(_failure(stage, code, oid, key, line_number))

        if native_oid is None or native_length is None or (accession is not None and
                any(c.isspace() or ord(c) < 32 for c in accession)):
            fail("parse", "native_row_invalid")
        exact = [s for s, value in selectors.items() if value == identifier or value == accession]
        if ordinal in bindings:
            matched = bindings[ordinal]
            if not set(exact) <= set(matched):
                raise ContractError("blast_utility_supplied_binding_conflict")
            association = "explicit"
        elif exact:
            matched, association = exact, "exact"
        else:
            matched, association = [], "unresolved"
            unexpected.append(key)
            fail("association", "record_association_unresolved")
        rc.append(_check("identity", "unknown" if association == "unresolved" else "pass", [key],
                         "explicit_reference_join" if association == "explicit" else "selected_record_match",
                         [oid], "record_association_unresolved" if association == "unresolved" else None))
        normalized, symbol_count = _sequence_symbols(original, operation["molecule"])
        symbols_valid = symbol_count is not None
        if not symbols_valid:
            fail("validation", "sequence_symbol_invalid")
        rc.append(_check("sequence_symbols", "pass" if symbols_valid else "fail", [key],
                         "native_format_parser", [oid], None if symbols_valid else "sequence_symbol_invalid"))
        effective = None
        if native_length is not None and symbols_valid:
            requested = params["range"]
            start = requested["start_1based"] - 1 if requested else 0
            end = min(requested["end_1based"], native_length) if requested else native_length
            if start > end or symbol_count != end - start:
                fail("validation", "sequence_length_conflict")
                symbol_count = None
            else:
                effective = {"start_0based": start, "end_exclusive": end, "strand": params["strand"]}
        elif native_length is None:
            symbol_count = None
        length_ok = symbol_count is not None and effective is not None
        rc.append(_check("sequence_length", "pass" if length_ok else "unknown", [key],
                         "sequence_length_agreement", [oid], None if length_ok else
                         "native_row_invalid" if native_length is None else
                         "sequence_length_conflict" if symbols_valid else "sequence_symbol_invalid"))
        row_closed = raw.endswith((b"\n", b"\r")) or _complete_capture(occurrence, outcome)
        if not row_closed:
            fail("capture", "output_inventory_incomplete")
            effective = None
        complete = row_closed and not rf
        record = {"record_key": key, "native_row_ordinal": ordinal, "line_number": line_number,
                  "matched_selector_ordinals": matched, "association": association,
                  "native_oid": native_oid, "native_identifier": identifier,
                  "native_accession": accession, "native_reported_length": native_length,
                  "native_length_basis": "full_sequence", "original_sequence": original,
                  "normalized_sequence": normalized, "returned_symbol_count": symbol_count,
                  "molecule": operation["molecule"], "requested_range": params["range"],
                  "effective_range": effective, "completeness": "complete" if complete else "partial",
                  "checks": rc, "failures": rf}
        records.append(record)
    by_oid = {}
    for record in records:
        if record["native_oid"] is not None:
            by_oid.setdefault(record["native_oid"], []).append(record)
    for group in by_oid.values():
        # Repeated selectors and several native deflines are legitimate. An OID
        # cannot supply conflicting sequence bytes/length under this same range.
        if len({(r["normalized_sequence"], r["native_reported_length"]) for r in group}) > 1:
            for r in group:
                r["failures"].append(_failure("validation", "duplicate_native_identity", oid,
                                             r["record_key"], r["line_number"]))
                r["checks"].append(_check("identity", "fail", [r["record_key"]],
                                           "native_format_parser", [oid], "duplicate_native_identity"))
                r["completeness"] = "partial"
    for ordinal in bindings:
        if ordinal >= len(lines) or ordinal in malformed:
            failures.append(_failure("association", "supplied_binding_conflict", oid,
                                     line_number=ordinal + 1))
    for r in records:
        checks.extend(r["checks"])
        failures.extend(r["failures"])
    if not content:
        failures.append(_failure("capture", "output_missing", oid))
    present = {s for r in records for s in r["matched_selector_ordinals"]}
    missing = [s for s in selectors if s not in present]
    if missing:
        failures.append(_failure("association", "selection_incomplete", oid))
    complete = (not failures and outcome["state"] == "succeeded" and _complete_capture(occurrence, outcome)
                and not missing and not unexpected and bool(records))
    invalid_syntax = any(f["code"] == "native_row_invalid" for f in failures)
    checks.append(_check("syntax", "fail" if invalid_syntax else "pass" if records else "unknown", [oid],
                         "native_format_parser", [oid], "native_row_invalid" if invalid_syntax else
                         None if records else "output_missing"))
    checks.append(_check("selection", "pass" if complete else "unknown", [database_binding["database_key"]],
                         "selected_record_match", [oid], None if complete else "selection_incomplete"))
    return validate_sequence_extraction({
        "version": "blast_sequence_extraction_v1", "operation": operation,
        "database_binding": database_binding, "output_occurrence": occurrence,
        "original_outcome": outcome, "records": records, "missing_selector_ordinals": missing,
        "unexpected_record_keys": unexpected,
        "population_completeness": "complete_selection" if complete else "partial_selection" if records else "unknown",
        "checks": checks, "failures": failures})


def validate_sequence_extraction(result: dict) -> dict:
    """Validate the saved common record and its deterministic relationships."""
    return validate_blast_utility_record("SequenceExtraction", result)


__all__ = ["parse_blastdbcmd_sequences", "validate_sequence_extraction"]
