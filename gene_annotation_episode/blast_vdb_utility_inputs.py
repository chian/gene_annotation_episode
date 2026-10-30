"""Pure supporting readers for the fixed ``blast_vdb_cmd`` output formats.

The shared VDB lexical reader and common sequence calculation remain the only
authorities for their respective work. These readers neither acquire data nor
construct search context. Captured source authentication belongs to the worker;
these functions validate supplied custody, selection and relationship facts.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .blast_database_extraction import (
    _bindings, _check, _check_bytes, _complete_capture, _failure,
    _outcome_observations, normalize_blast_utility_sequence_symbols,
)
from .blast_database_inspection import _field, _integer
from .blast_utility_contracts import validate_blast_utility_record as core
from .blast_vdb_inputs import read_blast_vdb_sequence_table
from .blast_vdb_utility_contracts import (
    validate_vdb_database_inspection, validate_vdb_sequence_extraction,
    validate_vdb_utility_context, validate_vdb_utility_operation,
)
from .domain import ContractError


def _require(condition, code):
    if not condition:
        raise ContractError("blast_utility_" + code)


def _context(occurrence, operation, database_binding, outcome,
             operation_input_occurrences, vdb_context, stderr_occurrence, modes):
    occurrence = core("ArtifactOccurrence", occurrence)
    operation = validate_vdb_utility_operation(operation)
    database_binding = core("DatabaseBinding", database_binding)
    outcome = core("NativeOutcome", outcome)
    _require(type(operation_input_occurrences) is list, "vdb_operation_input_population")
    inputs = [core("ArtifactOccurrence", row) for row in operation_input_occurrences]
    context = validate_vdb_utility_context(vdb_context, operation=operation,
        database_binding=database_binding, operation_input_occurrences=inputs)
    stderr = core("ArtifactOccurrence", stderr_occurrence)
    _require(operation["mode"] in modes, "reader_operation")
    roles = {"stdout", "extracted_sequences"} if operation["mode"] == "extract_sequences" else {"stdout", "database_metadata"}
    _require(occurrence["direction"] == "output" and occurrence["role"] in roles and
             occurrence["native_format"] == operation["parameters"]["output_format"], "reader_output_occurrence")
    _require(stderr["direction"] == "output" and stderr["role"] == "stderr" and
             stderr["native_format"] == "text", "vdb_output_stream")
    ids = [o["occurrence_id"] for o in [*inputs, occurrence, stderr]]
    ids += [oid for b in [database_binding, *context["dependency_database_bindings"]] for oid in b["occurrence_ids"]]
    _require(len(ids) == len(set(ids)), "duplicate_occurrence_identity")
    _require(set(operation["input_occurrence_ids"]) <= set(ids), "result_input_reference")
    return occurrence, operation, database_binding, outcome, inputs, context, stderr


_DIAGNOSTIC_MESSAGES = (
    ("bioseq_not_found", r"Failed to find Bioseq for '[^']*'"),
    ("sequence_data_absent", r"Bioseq constains no sequence data"),
    ("empty_bioseq", r"Empty Bioseq"),
    ("iterator_error", r"Iterator returns BLAST_SEQSRC_ERROR"),
    ("retrieval_failed", r"Failed to retrieve requested item"),
)


def parse_blast_vdb_diagnostics(contents: bytes, *, occurrence: dict, outcome: dict) -> dict:
    """Retain all stderr bytes and located literal source diagnostic categories.

    No prefix grammar has authentic nonempty-stderr verification here. A known
    source message with a prefix retains both that category and an explicit
    unrecognized-prefix qualification. Either qualification prevents claiming
    a completed selection solely from return code zero.
    """
    occurrence, outcome = core("ArtifactOccurrence", occurrence), core("NativeOutcome", outcome)
    _require(occurrence["direction"] == "output" and occurrence["role"] == "stderr" and
             occurrence["native_format"] == "text", "vdb_output_stream")
    checks = [_check_bytes(contents, occurrence)]
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    rows, failures, offset = [], [], 0
    oid = occurrence["occurrence_id"]
    for number, raw in enumerate(contents.splitlines(keepends=True), 1):
        start, offset = offset, offset + len(raw)
        try:
            line = raw.rstrip(b"\r\n").decode("utf-8")
        except UnicodeDecodeError:
            line = None
        if line is not None and not line.strip():
            continue
        category, prefix = "unknown", None
        if line is not None:
            for name, message in _DIAGNOSTIC_MESSAGES:
                match = re.fullmatch(r"(.*?)" + message, line)
                if match:
                    category, prefix = name, match[1]
                    break
        rows.append({"occurrence_id": oid, "line_number": number,
            "byte_start": start, "byte_end": offset, "native_line": line,
            "category": category, "native_prefix": prefix})
        if category != "unknown":
            failures.append(_failure("native", "selection_incomplete", oid, line_number=number))
        if category == "unknown" or prefix:
            failures.append(_failure("parse", "native_diagnostic_unrecognized", oid, line_number=number))
    return {"version": "blast_vdb_utility_diagnostics_v1", "occurrence": occurrence,
        "original_outcome": outcome,
        "input_identity": {k: occurrence[k] for k in ("sha256", "size_bytes")},
        "native_bytes_hex": contents.hex(), "native_text": text,
        "diagnostics": rows, "checks": checks, "failures": failures}


def _saved_diagnostics(value, outcome):
    keys = {"version", "occurrence", "original_outcome", "input_identity", "native_bytes_hex",
            "native_text", "diagnostics", "checks", "failures"}
    _require(type(value) is dict and set(value) == keys and
             type(value["native_bytes_hex"]) is str, "vdb_diagnostics_invalid")
    try:
        raw = bytes.fromhex(value["native_bytes_hex"])
    except ValueError as error:
        raise ContractError("blast_utility_vdb_diagnostics_invalid") from error
    rebuilt = parse_blast_vdb_diagnostics(raw, occurrence=value["occurrence"], outcome=outcome)
    _require(rebuilt == value, "original_attempt_conflict")
    return rebuilt


def _saved_table(value, occurrence):
    keys = {"schema", "source_ref", "source_version", "input_identity", "native_text", "rows", "issues"}
    _require(type(value) is dict and set(value) == keys and
             value["schema"] == "blast_vdb_sequence_table_v1", "vdb_sequence_table_invalid")
    _require(value["source_ref"] == occurrence["artifact_ref"] and
             value["source_version"] == occurrence["native_format"] and
             value["input_identity"] == {k: occurrence[k] for k in ("sha256", "size_bytes")},
             "input_identity_mismatch")
    if value["native_text"] is None:
        # The lexical port deliberately retains no decoded rows on UTF-8 error.
        # Its raw artifact remains the occurrence; there is no usable sequence.
        unsupported = [{"code": "blast_vdb_format_unsupported", "search_key": None,
            "hit_ordinal": None, "hsp_ordinal": None, "source_pointer": None,
            "details": {"encoding": "utf-8"}}]
        _require(value["rows"] == [] and value["issues"] == unsupported, "vdb_sequence_table_invalid")
        return deepcopy(value), None
    _require(type(value["native_text"]) is str, "vdb_sequence_table_invalid")
    raw = value["native_text"].encode("utf-8")
    check = _check_bytes(raw, occurrence)
    rebuilt = read_blast_vdb_sequence_table(raw, source_ref=occurrence["artifact_ref"],
        source_version=occurrence["native_format"])
    _require(rebuilt == value, "vdb_sequence_table_conflict")
    return rebuilt, check


def parse_blast_vdb_extraction(contents: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict, operation_input_occurrences: list[dict],
        vdb_context: dict, stderr_contents: bytes, stderr_occurrence: dict,
        record_bindings: list[dict] | None = None) -> dict:
    """Read only fixed four-column output, using the existing lexical authority."""
    occurrence = core("ArtifactOccurrence", occurrence)
    _check_bytes(contents, occurrence)
    parsed = read_blast_vdb_sequence_table(contents, source_ref=occurrence["artifact_ref"],
        source_version=occurrence["native_format"])
    diagnostics = parse_blast_vdb_diagnostics(stderr_contents, occurrence=stderr_occurrence, outcome=outcome)
    return normalize_blast_vdb_extraction(parsed, occurrence=occurrence, operation=operation,
        database_binding=database_binding, outcome=outcome, operation_input_occurrences=operation_input_occurrences,
        vdb_context=vdb_context, stderr_diagnostics=diagnostics, record_bindings=record_bindings)


def normalize_blast_vdb_extraction(parsed: dict, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict, operation_input_occurrences: list[dict],
        vdb_context: dict, stderr_diagnostics: dict, record_bindings: list[dict] | None = None) -> dict:
    """Recheck saved lexical evidence and populate the common extraction result."""
    diagnostics = _saved_diagnostics(stderr_diagnostics, outcome)
    occurrence, operation, database_binding, outcome, inputs, context, stderr = _context(
        occurrence, operation, database_binding, outcome, operation_input_occurrences,
        vdb_context, diagnostics["occurrence"], {"extract_sequences"})
    table, custody = _saved_table(parsed, occurrence)
    checks = ([] if custody is None else [custody]) + diagnostics["checks"]
    more_checks, failures = _outcome_observations(outcome, [occurrence, stderr], database_binding["database_key"])
    checks.extend(more_checks); failures.extend(diagnostics["failures"])
    oid = occurrence["occurrence_id"]
    selection = operation["parameters"]["selection"]
    entries = selection["kind"] == "entries"
    selectors = {s["ordinal"]: s["value"] for s in selection["selectors"]} if entries else {}
    bindings = _bindings(record_bindings, selectors)
    records, malformed, unexpected = [], set(), []
    text_lines = (table["native_text"] or "").splitlines(keepends=True)
    if table["native_text"] is None:
        failures.append(_failure("parse", "native_format_unsupported", oid))
    for native in table["rows"]:
        ordinal, number = native["row_ordinal"], native["line_number"]
        key, fields = oid + "#/records/" + str(ordinal), native["fields"]
        identifier = fields["native_identifier"] if fields else None
        if (fields is None or identifier in {None, "", "N/A"} or
                any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in identifier)):
            malformed.add(ordinal)
            failures.append(_failure("parse", "native_row_invalid", oid, key, number))
            continue
        accession = fields["native_accession"]
        accession = None if accession in {"", "N/A"} else accession
        original, length = fields["sequence_symbols"], native["native_reported_length"]
        rc, rf = [], []

        def fail(stage, code):
            failure = _failure(stage, code, oid, key, number)
            if failure not in rf:
                rf.append(failure)

        if native["issues"] or (accession is not None and any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in accession)):
            fail("parse", "native_row_invalid")
        exact = [n for n, value in selectors.items() if value in (identifier, accession)]
        if not entries:
            matched, association = [], "not_applicable"
        elif ordinal in bindings:
            matched, association = bindings[ordinal], "explicit"
            _require(set(exact) <= set(matched), "supplied_binding_conflict")
        elif exact:
            matched, association = exact, "exact"
        else:
            matched, association = [], "unresolved"
            unexpected.append(key)
            fail("association", "record_association_unresolved")
        rc.append(_check("identity", "unknown" if association == "unresolved" else
            "not_applicable" if not entries else "pass", [key],
            "explicit_reference_join" if association == "explicit" else "selected_record_match",
            [oid], "record_association_unresolved" if association == "unresolved" else None))
        normalized, count = normalize_blast_utility_sequence_symbols(original, "dna")
        valid_symbols = count is not None
        if not valid_symbols:
            fail("validation", "sequence_symbol_invalid")
        rc.append(_check("sequence_symbols", "pass" if valid_symbols else "fail", [key],
            "native_format_parser", [oid], None if valid_symbols else "sequence_symbol_invalid"))
        if length is None:
            count, length_reason = None, "native_row_invalid"
        elif valid_symbols and count != length:
            fail("validation", "sequence_length_conflict")
            count, length_reason = None, "sequence_length_conflict"
        elif not valid_symbols:
            length_reason = "sequence_symbol_invalid"
        else:
            length_reason = None
        rc.append(_check("sequence_length", "pass" if length_reason is None else "unknown", [key],
            "sequence_length_agreement", [oid], length_reason))
        if not (text_lines[ordinal].endswith(("\n", "\r")) or _complete_capture(occurrence, outcome)):
            fail("capture", "output_completeness_unestablished")
        candidates = [m for m in context["member_bindings"] if m["native_identifier"] == identifier]
        member = candidates[0] if len(candidates) == 1 else None
        if len(candidates) > 1:
            fail("association", "supplied_binding_conflict")
        records.append({"record_key": key, "native_row_ordinal": ordinal, "line_number": number,
            "matched_selector_ordinals": matched, "association": association, "native_oid": None,
            "native_identifier": identifier, "native_accession": accession,
            "native_reported_length": length, "native_length_basis": "returned_sequence",
            "original_sequence": original, "normalized_sequence": normalized, "returned_symbol_count": count,
            "molecule": "dna", "requested_range": None, "effective_range": None,
            "completeness": "complete" if not rf else "partial", "checks": rc, "failures": rf,
            "vdb_member": deepcopy(member)})
    for ordinal in bindings:
        if ordinal >= len(table["rows"]) or ordinal in malformed:
            failures.append(_failure("association", "supplied_binding_conflict", oid, line_number=ordinal + 1))
    # An identifier may recur legitimately, but conflicting bytes under that
    # same native identifier remain explicit, without arbitrarily choosing one.
    by_identifier = {}
    for row in records:
        by_identifier.setdefault(row["native_identifier"], []).append(row)
    for group in by_identifier.values():
        if len({(r["normalized_sequence"], r["native_reported_length"]) for r in group}) > 1:
            for row in group:
                row["failures"].append(_failure("validation", "duplicate_native_identity", oid,
                    row["record_key"], row["line_number"]))
                row["completeness"] = "partial"
    for row in records:
        checks.extend(row["checks"]); failures.extend(row["failures"])
    if not occurrence["size_bytes"] and entries:
        failures.append(_failure("capture", "output_missing", oid))
    present = {s for row in records for s in row["matched_selector_ordinals"]}
    missing = [s for s in selectors if s not in present]
    if missing:
        failures.append(_failure("association", "selection_incomplete", oid))
    complete = (not failures and outcome["state"] == "succeeded" and
        all(_complete_capture(o, outcome) for o in (occurrence, stderr)) and (bool(records) or not entries))
    syntax_error = any(f["code"] in {"native_row_invalid", "native_format_unsupported"} for f in failures)
    checks.append(_check("syntax", "fail" if syntax_error else "pass", [oid], "native_format_parser", [oid],
        "native_row_invalid" if syntax_error else None))
    checks.append(_check("selection", "pass" if complete else "unknown", [database_binding["database_key"]],
        "selected_record_match", [oid, stderr["occurrence_id"]], None if complete else "selection_incomplete"))
    return validate_vdb_sequence_extraction({"version": "blast_sequence_extraction_v2", "operation": operation,
        "database_binding": database_binding, "original_outcome": outcome, "output_occurrence": occurrence,
        "stderr_occurrence": stderr, "operation_input_occurrences": inputs, "vdb_context": context,
        "scope": {"kind": "selected_entries" if entries else selection["kind"]}, "records": records,
        "missing_selector_ordinals": missing, "unexpected_record_keys": unexpected,
        "population_completeness": "complete_selection" if complete else "partial_selection" if records else "unknown",
        "checks": checks, "failures": failures})


_INFO_LISTS = {"Database(s):": ("vdb_selected_inputs", "native_input_tokens"),
    "Database(s) Full Path:": ("vdb_resolved_paths", "paths"),
    "CSRA Database(s):": ("vdb_csra_inputs", "paths")}
_INFO_NUMBERS = (
    (r"\s*(.*?) sequences; (.*?) total bases \(unclipped\)",
     (("vdb_sequence_count", "sequences"), ("vdb_total_unclipped_bases", "nt"))),
    (r"\s*Longest sequence: (.*?) bases", (("vdb_longest_sequence_bases", "nt"),)),
    (r"\s*Average sequence: (.*?) bases", (("vdb_average_sequence_bases", "nt"),)),
    (r"\s*(.*?) ref sequences; (.*?) total ref bases",
     (("vdb_reference_sequence_count", "sequences"), ("vdb_reference_total_bases", "nt"))),
)
_INFO_REQUIRED = ("vdb_selected_inputs", "vdb_resolved_paths", "vdb_sequence_count",
    "vdb_total_unclipped_bases", "vdb_longest_sequence_bases", "vdb_average_sequence_bases")


def _vdb_info(text, oid):
    fields, failures, active, block = [], [], None, []

    def close(*, terminated=True):
        nonlocal active, block
        if active is None:
            return
        name, unit, line = active
        lexeme = "\n".join(block)
        padded = block[0].startswith(" ")
        payload = block[0][1:] if padded else block[0]
        data_lines = [part for part in [payload, *block[1:]] if part.strip()]
        value, missing = None, None
        if not terminated or not padded or not data_lines:
            missing = "native_field_invalid"
        elif len(data_lines) > 1:
            # NStr::Wrap removes a separating space or splits within a token
            # without recording which happened. Neither split nor join is an
            # inverse. Keep the report, never manufacture fragment paths.
            missing = "ambiguous_population"
        elif len(block) > 1 and not payload.strip():
            # Header padding is not a data line. A sole continuation cannot
            # arise from normalized selected tokens without data loss. Path
            # strings can lose whitespace/backspaces; CSRA also has a final
            # separator which alone can trigger the out-of-line rendering.
            missing = ("native_field_invalid" if name == "vdb_selected_inputs"
                       else "ambiguous_population")
        elif name == "vdb_resolved_paths":
            # Native resolution preserves quoted/link-target whitespace, then
            # joins paths without escaping. Even an inline split is ambiguous.
            if any(c.isspace() for c in payload):
                missing = "ambiguous_population"
            else:
                value = [payload]
        else:
            csra = name == "vdb_csra_inputs"
            if csra and not payload.endswith(" "):
                missing = "native_field_invalid"
            else:
                tokens = (payload[:-1] if csra else payload).split(" ")
                if any(not token for token in tokens):
                    missing = "native_field_invalid"
                elif any(c.isspace() or ord(c) < 32 or ord(c) == 127
                         for token in tokens for c in token):
                    missing = "ambiguous_population" if csra else "native_field_invalid"
                else:
                    value = tokens
        fields.append(_field(name, value, unit, oid, line=line,
            lexeme=lexeme, missing=missing))
        if missing == "ambiguous_population":
            failures.append(_failure("validation", "semantic_validation_unavailable", oid, line_number=line))
        elif missing is not None:
            failures.append(_failure("parse", "native_document_invalid", oid, line_number=line))
        active, block = None, []

    # Native report lines use LF. Preserve path control characters as data;
    # splitlines() would silently turn form feeds and similar bytes into lines.
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        line = line.removesuffix("\r")
        label = next((label for label in _INFO_LISTS if line.startswith(label)), None)
        numerical = next(((re.fullmatch(pattern, line), names) for pattern, names in _INFO_NUMBERS
                          if re.fullmatch(pattern, line)), None)
        if label is not None:
            close()
            active = (*_INFO_LISTS[label], number)
            block = [line[len(label):]]
        elif numerical:
            close()
            match, names = numerical
            for (name, unit), lexeme in zip(names, match.groups()):
                value = _integer(lexeme)
                fields.append(_field(name, value, unit, oid, line=number, lexeme=lexeme,
                    missing=None if value is not None else "native_field_invalid"))
                if value is None:
                    failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))
        elif active is not None and (not line.strip() or not line.startswith(("\t", " "))):
            block.append(line)
        elif line.strip():
            if active is not None:
                block.append(line)
            close(terminated=False)
            failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))
    close(terminated=False)
    all_fields = [(name, unit) for name, unit in _INFO_LISTS.values()]
    all_fields += [item for _, names in _INFO_NUMBERS for item in names]
    for name, unit in all_fields:
        group = [f for f in fields if f["field_name"] == name]
        if not group:
            fields.append(_field(name, None, unit, oid, pointer="", missing="native_field_absent"))
            if name in _INFO_REQUIRED:
                failures.append(_failure("parse", "native_document_invalid", oid))
        else:
            for index, field in enumerate(group[1:], 1):
                conflict = any(f["value"] != field["value"] for f in group[:index])
                failures.append(_failure("validation", "database_metadata_conflict" if conflict else
                    "duplicate_native_identity", oid, line_number=field["line_number"]))
    return fields, failures


_PATH_HEADERS = {"VDB(s):": "vdb", "VDB Alias File(s):": "vdb_alias",
                 "Blats DB Alias File(s):": "blast_db_alias"}


def _vdb_paths(text, oid, mode, database_binding, context):
    sections, rows, failures, by_kind = [], [], [], {}
    current, empty = None, set()
    databases = {b["database_key"]: b for b in [database_binding, *context["dependency_database_bindings"]]}
    dependencies = context["declared_dependencies"]

    def invalid(number=None):
        failures.append(_failure("parse", "native_document_invalid", oid, line_number=number))

    for number, line in enumerate(text.splitlines(), 1):
        label = next((h for h in _PATH_HEADERS if line.startswith(h)), None)
        if label:
            kind = _PATH_HEADERS[label]
            if mode == "paths" and kind != "vdb":
                current = None; invalid(number); continue
            if kind in by_kind:
                current = None; invalid(number); continue
            else:
                current = len(sections); by_kind[kind] = current
                sections.append({"kind": kind, "header_line_number": number, "presence": "reported_empty"})
            tail = line[len(label):].strip()
            if tail == "None":
                empty.add(current)
            elif tail:
                invalid(number)
            continue
        if not line.strip():
            continue
        if current is None:
            invalid(number); continue
        if line == "None":
            if current in empty or sections[current]["presence"] == "reported_values":
                invalid(number)
            empty.add(current)
            continue
        # Native emits one returned path token per line. Its spelling need not
        # contain a slash; retaining the report neither captures a file nor
        # establishes a supplied dependency relationship.
        if any(c.isspace() or ord(c) < 32 for c in line):
            invalid(number); continue
        if current in empty:
            invalid(number)
        section = sections[current]
        section["presence"] = "reported_values"
        matches = [d["ordinal"] for d in dependencies if line in {d["native_reference"],
            databases[d["database_key"]]["native_paths"][d["native_path_index"]]}]
        rows.append({"kind": section["kind"], "section_ordinal": current, "native_path_ordinal": len(rows),
            "native_path": line, "line_number": number, "matched_dependency_ordinals": matches})
    for index, section in enumerate(sections):
        if section["presence"] == "reported_empty" and index not in empty:
            invalid(section["header_line_number"])
    expected = {"vdb"} if mode == "paths" else set(_PATH_HEADERS.values())
    if not expected <= set(by_kind):
        invalid()
    for kind in _PATH_HEADERS.values():
        if kind not in by_kind:
            sections.append({"kind": kind, "header_line_number": None, "presence": "not_reported"})
    return sections, rows, failures


def parse_blast_vdb_inspection(contents: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict, operation_input_occurrences: list[dict],
        vdb_context: dict, stderr_contents: bytes, stderr_occurrence: dict) -> dict:
    """Read native information populations or flat path sections, retaining gaps."""
    occurrence, operation, database_binding, outcome, inputs, context, stderr = _context(
        occurrence, operation, database_binding, outcome, operation_input_occurrences, vdb_context,
        stderr_occurrence, {"info", "paths", "paths_all"})
    diagnostics = parse_blast_vdb_diagnostics(stderr_contents, occurrence=stderr, outcome=outcome)
    checks = [_check_bytes(contents, occurrence), *diagnostics["checks"]]
    more_checks, failures = _outcome_observations(outcome, [occurrence, stderr], database_binding["database_key"])
    checks.extend(more_checks); failures.extend(diagnostics["failures"])
    oid = occurrence["occurrence_id"]
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
        failures.append(_failure("parse", "native_format_unsupported", oid))
    fields, sections, paths = [], [], []
    if operation["mode"] == "info":
        fields, parse_failures = _vdb_info(text, oid)
    else:
        sections, paths, parse_failures = _vdb_paths(text, oid, operation["mode"], database_binding, context)
    failures.extend(parse_failures)
    if not contents:
        failures.append(_failure("capture", "output_missing", oid))
    parsing = [f for f in failures if f["stage"] == "parse"]
    checks.append(_check("syntax", "fail" if parsing else "pass", [oid], "native_format_parser", [oid],
        parsing[0]["code"] if parsing else None))
    qualifications = [f for f in failures if f["stage"] in {"parse", "validation"}]
    checks.append(_check("database_metadata", "unknown" if qualifications else "pass",
        [database_binding["database_key"]], "native_format_parser", [oid],
        qualifications[0]["code"] if qualifications else None))
    complete = not failures and outcome["state"] == "succeeded" and all(
        _complete_capture(o, outcome) for o in (occurrence, stderr))
    usable = any(f["value"] is not None for f in fields) or bool(paths) or any(
        s["header_line_number"] is not None for s in sections)
    return validate_vdb_database_inspection({"version": "blast_database_inspection_v3", "operation": operation,
        "database_binding": database_binding, "original_outcome": outcome, "output_occurrence": occurrence,
        "stderr_occurrence": stderr, "operation_input_occurrences": inputs, "vdb_context": context,
        "native_fields": fields, "path_sections": sections, "path_records": paths,
        "completeness": "complete" if complete else "partial" if usable else "unknown",
        "checks": checks, "failures": failures})


__all__ = ["parse_blast_vdb_extraction", "normalize_blast_vdb_extraction",
           "parse_blast_vdb_inspection", "parse_blast_vdb_diagnostics"]
