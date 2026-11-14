"""Pure readers for native BLAST database information and integrity reports.

Native measurements keep their locators and units. A parser success is never a
database integrity result; an unavailable check is never evidence of corruption.
"""
from __future__ import annotations

import json
import re

from .blast_database_extraction import (
    _check, _check_bytes, _complete_capture, _failure, _outcome_observations,
    _reader_context,
)
from .blast_utility_contracts import validate_blast_utility_record
from .domain import ContractError


def _field(name, value, unit, oid, *, lexeme=None, line=None, pointer=None,
           basis="native_reported", missing=None):
    return {"field_name": name, "value": value, "unit": unit, "value_basis": basis,
            "native_lexeme": lexeme, "occurrence_id": oid, "line_number": line,
            "json_pointer": pointer, "missing_reason": missing}


def _integer(text):
    if not re.fullmatch(r"(?:[0-9]+|[1-9][0-9]{0,2}(?:,[0-9]{3})+)", text):
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def _info_fields(text, oid, operation):
    fields, failures, units = [], [], set()
    volume_header, volumes = None, []

    def add(name, value, unit, number, lexeme, basis="native_reported"):
        fields.append(_field(name, value, unit, oid, lexeme=lexeme, line=number, basis=basis,
                             missing="native_field_invalid" if value is None else None))
        if value is None:
            failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))

    def close_volumes():
        nonlocal volume_header, volumes
        if volume_header is not None:
            fields.append(_field("database_volume_names", list(volumes), "paths", oid,
                                 line=volume_header))
            volume_header, volumes = None, []

    for number, line in enumerate(text.splitlines(), 1):
        if volume_header is not None and line.startswith("\t") and " sequences; " not in line:
            if line[1:]:
                volumes.append(line[1:])
            else:
                failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))
            continue
        if volume_header is not None and line.strip():
            close_volumes()
        if line.startswith("Database: "):
            add("database_title", line[len("Database: "):], "text", number, line[len("Database: "):])
        elif " sequences; " in line:
            match = re.fullmatch(r"\s*(.*?) sequences; (.*?) total (bases|residues)", line)
            if match is None:
                failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))
                continue
            seq, length, word = match.groups()
            unit = "nt" if word == "bases" else "aa"
            units.add(unit)
            add("database_sequence_count", _integer(seq), "sequences", number, seq)
            add("database_residue_count", _integer(length), unit, number, length,
                "native_reported_exact" if operation["parameters"]["exact_length"] else "native_reported")
        elif line.startswith("Date: "):
            value = line[len("Date: "):].split("\tLongest sequence:", 1)[0]
            add("database_created_at_native", value, "text", number, value)
        elif line.startswith("BLASTDB Version: "):
            value = line[len("BLASTDB Version: "):]
            add("database_format_version", _integer(value), "version", number, value)
        elif line == "Volumes:":
            close_volumes()
            volume_header = number
    close_volumes()
    required = {"database_title", "database_sequence_count", "database_residue_count",
                "database_created_at_native", "database_format_version", "database_volume_names"}
    if not required <= {f["field_name"] for f in fields}:
        failures.append(_failure("parse", "native_document_invalid", oid))
    return fields, failures, units


def _json_members(text):
    """Read complete top-level members even when a later native member is cut.

    Keep duplicate members and original scalar lexemes. JSON's ordinary dictionary
    conversion would erase conflicting values. No damaged member is repaired.
    """
    def invalid_constant(_):
        raise ValueError("non_json_numeric_constant")

    decoder = json.JSONDecoder(parse_constant=invalid_constant)
    members, position = [], 0

    def space(pos):
        while pos < len(text) and text[pos] in " \r\n\t":
            pos += 1
        return pos

    position = space(position)
    if position >= len(text) or text[position] != "{":
        return members, False
    position = space(position + 1)
    if position < len(text) and text[position] == "}":
        return members, space(position + 1) == len(text)
    while position < len(text):
        try:
            key, end = decoder.raw_decode(text, position)
            if type(key) is not str:
                return members, False
            position = space(end)
            if position >= len(text) or text[position] != ":":
                return members, False
            start = space(position + 1)
            value, position = decoder.raw_decode(text, start)
        except (ValueError, RecursionError):
            return members, False
        members.append((key, value, text[start:position]))
        position = space(position)
        if position < len(text) and text[position] == "}":
            return members, space(position + 1) == len(text)
        if position >= len(text) or text[position] != ",":
            return members, False
        position = space(position + 1)
    return members, False


def _metadata_fields(text, oid):
    members, complete = _json_members(text)
    failures, fields = [], []
    if not complete:
        failures.append(_failure("parse", "native_document_invalid", oid))
    keys = [key for key, _, _ in members]
    if len(set(keys)) != len(keys):
        failures.append(_failure("parse", "native_document_invalid", oid))
    if [v for k, v, _ in members if k == "version"] != ["1.2"]:
        failures.append(_failure("parse", "native_format_unsupported", oid))
    molecule_values = [v for k, v, _ in members if k == "dbtype"]
    units = {"nt" if v == "Nucleotide" else "aa" for v in molecule_values if v in ("Nucleotide", "Protein")}
    unit = next(iter(units)) if len(units) == 1 and all(v in ("Nucleotide", "Protein") for v in molecule_values) else "symbols"
    if not molecule_values or unit == "symbols":
        failures.append(_failure("parse", "native_document_invalid", oid))
    specs = {
        "description": ("database_title", "text", str),
        "db-version": ("database_format_version", "version", int),
        "last-updated": ("database_created_at_native", "text", str),
        "number-of-sequences": ("database_sequence_count", "sequences", int),
        "number-of-letters": ("database_residue_count", unit, int),
        "bytes-total": ("database_bytes", "bytes", int),
        "files": ("database_file_names", "paths", list),
    }
    for key, value, lexeme in members:
        if key not in specs:
            continue
        name, field_unit, expected = specs[key]
        valid = type(value) is expected
        if expected is int:
            valid = valid and value >= 0
        elif expected is list:
            valid = valid and all(type(v) is str for v in value)
        fields.append(_field(name, value if valid else None, field_unit, oid,
                             lexeme=lexeme, pointer="/" + key,
                             missing=None if valid else "native_field_invalid"))
        if not valid:
            failures.append(_failure("parse", "native_document_invalid", oid))
    if not set(specs) <= set(keys):
        failures.append(_failure("parse", "native_document_invalid", oid))
    return fields, failures, units


def parse_blast_database_inspection(content: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict) -> dict:
    """Populate native information fields without treating metadata as a manifest."""
    occurrence, operation, database_binding, outcome = _reader_context(
        occurrence, operation, database_binding, outcome,
        program="blastdbcmd", modes={"info", "metadata"})
    fmt = "blastdb_info_text" if operation["mode"] == "info" else "blastdb_metadata_json"
    if occurrence["role"] not in {"database_metadata", "stdout"} or occurrence["native_format"] != fmt:
        raise ContractError("blast_utility_reader_output_occurrence")
    oid, key = occurrence["occurrence_id"], database_binding["database_key"]
    checks = [_check_bytes(content, occurrence)]
    more_checks, failures = _outcome_observations(outcome, [occurrence], key)
    checks.extend(more_checks)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
    if operation["mode"] == "info":
        fields, parse_failures, units = _info_fields(text, oid, operation)
    else:
        fields, parse_failures, units = _metadata_fields(text, oid)
    failures.extend(parse_failures)
    if not content:
        failures.append(_failure("capture", "output_missing", oid))
    expected_unit = "nt" if operation["molecule"] == "dna" else "aa"
    if units and units != {expected_unit}:
        failures.append(_failure("validation", "database_kind_conflict", oid))
    by_name = {}
    for field in fields:
        by_name.setdefault(field["field_name"], []).append(field)
        if field["field_name"] == "database_format_version" and field["value"] is not None and field["value"] not in (4, 5):
            failures.append(_failure("validation", "incompatible_database_format", oid,
                                     line_number=field["line_number"]))
    for group in by_name.values():
        # Never let a later count or molecule silently overwrite an earlier one.
        if len({json.dumps([f["value"], f["unit"]], sort_keys=True) for f in group}) > 1:
            failures.append(_failure("validation", "database_metadata_conflict", oid))
    checks.append(_check("syntax", "fail" if parse_failures else "pass", [oid],
                         "native_format_parser", [oid], "native_document_invalid" if parse_failures else None))
    metadata_failures = [f for f in failures if f["stage"] == "validation"]
    checks.append(_check("database_metadata", "fail" if metadata_failures else
                         "unknown" if parse_failures else "pass", [key], "native_format_parser", [oid],
                         metadata_failures[0]["code"] if metadata_failures else
                         "native_document_invalid" if parse_failures else None))
    complete = not failures and outcome["state"] == "succeeded" and _complete_capture(occurrence, outcome)
    return validate_blast_utility_record("DatabaseInspection", {
        "version": "blast_database_inspection_v1", "operation": operation,
        "database_binding": database_binding, "output_occurrence": occurrence,
        "original_outcome": outcome, "native_fields": fields,
        "completeness": "complete" if complete else "partial" if fields else "unknown",
        "checks": checks, "failures": failures})


_INFO_LINES = (
    r"Writing messages to .* at verbosity \([A-Za-z]+\)",
    r"(?:ISAM|Legacy|TaxID) testing is (?:ENABLED|DISABLED)\.",
    r"Testing [0-9]+ (?:volume\(s\)|alias\(es\))\.",
    r"Testing CDD files' headers for DELTA-BLAST",
)
_SAMPLE_LINES = (
    r"Testing every ([0-9]+)-th OID\.",
    r"(?:By default, testing|Testing) ([0-9]+) randomly sampled OIDs\.",
    r"Testing first ([0-9]+) and last ([0-9]+) OIDs\.",
)


def parse_blastdbcheck_diagnostics(stdout: bytes, stderr: bytes, *,
        stdout_occurrence: dict, stderr_occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict) -> dict:
    """Read explicit check evidence; requested sampling never supplies a count.

    Summary output does not report actual sequence counts. Detailed per-OID
    statuses can establish the observed count for a single explicitly bound
    volume. A caught exception or missing input remains execution/availability
    information, not a finding that sequence data are corrupt.
    """
    stdout_occurrence, operation, database_binding, outcome = _reader_context(
        stdout_occurrence, operation, database_binding, outcome,
        program="blastdbcheck", modes={"integrity"})
    stderr_occurrence = validate_blast_utility_record("ArtifactOccurrence", stderr_occurrence)
    streams = [(stdout, stdout_occurrence), (stderr, stderr_occurrence)]
    for (_, occurrence), role in zip(streams, ("stdout", "stderr")):
        if occurrence["direction"] != "output" or occurrence["role"] != role or occurrence["native_format"] not in {"blastdbcheck_text", "text"}:
            raise ContractError("blast_utility_integrity_stream")
    if stdout_occurrence["occurrence_id"] == stderr_occurrence["occurrence_id"]:
        raise ContractError("blast_utility_duplicate_occurrence_identity")
    checks = [_check_bytes(content, occurrence) for content, occurrence in streams]
    key = database_binding["database_key"]
    native_checks, failures = _outcome_observations(outcome, [o for _, o in streams], key)
    checks.extend(native_checks)
    diagnostics, status_rows, summary_volumes, total_volumes = [], [], [], []
    full_mode, sample_mode, actual_failure, execution_failure, unknown = False, False, False, False, False
    unavailable_dependency = False
    known_paths = set(database_binding["native_paths"])
    for content, occurrence in streams:
        oid = occurrence["occurrence_id"]
        for number, raw in enumerate(content.splitlines(), 1):
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                line = "\ufffd"
            if not line:
                continue
            if line == "Using `full' mode: every OID will be tested.":
                full_mode = True
                continue
            if any(re.fullmatch(pattern, line) for pattern in _SAMPLE_LINES):
                sample_mode = True
                continue
            volume_count = re.fullmatch(r"Testing ([0-9]+) volume\(s\)\.", line)
            if volume_count:
                total_volumes.append(int(volume_count[1]))
                continue
            if any(re.fullmatch(pattern, line) for pattern in _INFO_LINES) or line in known_paths:
                continue
            status = re.fullmatch(r"(.+?) / (Stride|Sample|EndPoints):\s+Status for OID ([0-9]+): (PASS|FAIL)", line)
            category, native_oid = "unknown", None
            if status:
                path, method, ordinal, result = status.groups()
                native_oid = int(ordinal)
                if path in known_paths:
                    category = "check_pass" if result == "PASS" else "check_failure"
                    status_rows.append((path, native_oid, result))
                    actual_failure |= result == "FAIL"
                else:
                    unknown = True
                    failures.append(_failure("association", "record_association_unresolved", oid, line_number=number))
            elif re.fullmatch(r".+? / (?:Stride|Sample|EndPoints):\s+<testing .+>", line):
                continue
            elif re.fullmatch(r"Result=SUCCESS\. No errors reported for ([0-9]+) (volume\(s\)|alias\(es\))\.", line):
                match = re.fullmatch(r"Result=SUCCESS\. No errors reported for ([0-9]+) (volume\(s\)|alias\(es\))\.", line)
                category = "check_pass"
                if match[2] == "volume(s)":
                    summary_volumes.append(int(match[1]))
            elif "GetTaxInfo() - Taxid " in line and line.endswith(" not found"):
                category, execution_failure, unavailable_dependency = "execution_failure", True, True
                failures.append(_failure("native", "dependency_unavailable", oid, line_number=number,
                                         native_returncode=outcome["returncode"]))
            elif ("caught exception" in line or "No alias or index file found" in line or
                  "No such file or directory" in line or "Cannot open" in line or
                  "does not exist" in line or "BLAST Database error:" in line or
                  "NCBI C++ Exception:" in line or line.startswith("Error: ")):
                category, execution_failure = "execution_failure", True
            elif re.search(r"(?:Failed during .+, oid |failed; oid=)([0-9]+):", line):
                match = re.search(r"(?:Failed during .+, oid |failed; oid=)([0-9]+):", line)
                native_oid, category, actual_failure = int(match[1]), "check_failure", True
            elif "[ERROR]" in line and any(message in line for message in (
                    "db has empty date string", "db has no volumes", "sequence count/length mismatch",
                    "has zero length.", "empty volume", "tax info looks wrong")):
                category, actual_failure = "check_failure", True
            elif re.fullmatch(r"Result=FAILURE\. [0-9]+ errors reported in [0-9]+ (?:volume\(s\)|alias\(es\))\.", line) or re.fullmatch(r"Total errors: [0-9]+", line):
                # A total does not identify whether data or execution failed.
                category = "unknown"
            else:
                unknown = True
                failures.append(_failure("parse", "native_diagnostic_unrecognized", oid, line_number=number))
            diagnostics.append({"occurrence_id": oid, "line_number": number,
                                "category": category, "native_oid": native_oid})
    captured = all(_complete_capture(o, outcome) for _, o in streams)
    successful_volume_report = (len(total_volumes) == 1 and total_volumes[0] > 0
                                and summary_volumes == total_volumes)
    mode_conflict = ((full_mode and sample_mode) or
                     (full_mode and not operation["parameters"]["full"]) or
                     (sample_mode and operation["parameters"]["full"]))
    if mode_conflict:
        failures.append(_failure("validation", "original_attempt_conflict", stdout_occurrence["occurrence_id"]))
    full_pass = (full_mode and not mode_conflict and successful_volume_report and captured
                 and outcome["state"] == "succeeded" and not actual_failure and not execution_failure and not unknown)
    sample_observed = sample_mode and bool(status_rows or successful_volume_report)
    scope = "all_sequences" if full_pass else "selected_sample" if sample_observed and not full_mode else "unknown"
    # A per-volume OID is not a globally unique database sequence ordinal. Avoid
    # manufacturing a merged population for multi-volume diagnostics.
    observed = list(dict.fromkeys(ordinal for _, ordinal, _ in status_rows)) if (
        len({path for path, _, _ in status_rows}) == 1 and total_volumes == [1]) else None
    checked = len(observed) if observed is not None else None
    method = "native_full_check" if full_mode or operation["parameters"]["full"] else "native_sample_check"
    if actual_failure:
        status, reason = "fail", "native_integrity_failure"
    elif full_pass or (scope == "selected_sample" and successful_volume_report and captured
                       and outcome["state"] == "succeeded" and not execution_failure and not unknown and not mode_conflict):
        status, reason = "pass", None
    else:
        status, reason = "unknown", "dependency_unavailable" if unavailable_dependency else "semantic_validation_unavailable"
    if execution_failure or reason is not None:
        failures.append(_failure("validation", reason or "semantic_validation_unavailable", stdout_occurrence["occurrence_id"]))
    checks.append(_check("native_integrity", status, [key], method,
                         [o["occurrence_id"] for _, o in streams], reason))
    return validate_blast_utility_record("DatabaseIntegrity", {
        "version": "blast_database_integrity_v1", "operation": operation,
        "database_binding": database_binding, "stdout_occurrence": stdout_occurrence,
        "stderr_occurrence": stderr_occurrence, "original_outcome": outcome,
        "scope": scope, "observed_checked_count": checked,
        "observed_population_count": None,
        "observed_sampled_oids": observed if scope == "selected_sample" else None,
        "realized_seed": None, "diagnostics": diagnostics, "checks": checks, "failures": failures})


__all__ = ["parse_blast_database_inspection", "parse_blastdbcheck_diagnostics"]
