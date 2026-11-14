"""Pure cmemit generated-data extraction, with no target-gene evidence claims.

The input is supplied native text/bytes and an explicit model extraction. Case,
native names, annotations and model order survive. A2M insertion gap columns are
not reconstructed: its compact strings do not preserve the original matrix.
Full native artifacts (including undecoded traces) remain the caller's custody.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import math
import re

from .hmmalign_inputs import iter_hmmalign_stockholm_records
from .infernal_preparation_schema import (
    field_input, issue, locator, new_sheet, record_key, validate_common_sheet, value,
)


ROW_FIELDS = {
    "generated_sequence": frozenset({"kind", "record_key", "locator", "model_keys", "origin",
        "name", "description", "sequence", "alphabet", "residue_sha256", "sample_index",
        "embedded_interval", "alignment_key", "values"}),
    "generated_alignment": frozenset({"kind", "record_key", "locator", "model_keys", "origin",
        "format", "sequence_keys", "annotations", "values"}),
    "generated_trace": frozenset({"kind", "record_key", "locator", "model_keys", "sequence_keys", "name", "trace_family", "values"}),
}
SEQUENCE_VALUE_NAMES = frozenset({"residue_count", "canonical_count", "gc_count",
                                 "ambiguity_count", "gap_count", "column_count"})
COMPONENT_NAMES = frozenset({*SEQUENCE_VALUE_NAMES, "gc_fraction_canonical", "gc_denominator",
    "gap_fraction", "row_count", "expected_sequence_count", "actual_sequence_count", "score_bits", "structure_score_bits"})
CHECK_NAMES = frozenset()
ISSUE_CODES = frozenset({
    "cmemit_model_population_incomplete", "cmemit_model_type_incompatible",
    "cmemit_engine_version_unverified", "cmemit_setting_missing", "cmemit_settings_incompatible",
    "cmemit_format_incompatible", "cmemit_payload_digest_mismatch", "cmemit_text_encoding_invalid",
    "cmemit_capture_partial", "cmemit_capture_unknown", "cmemit_output_empty",
    "cmemit_fasta_header_missing", "cmemit_fasta_header_invalid", "cmemit_sequence_symbols_invalid",
    "cmemit_missing_sequence_symbols", "cmemit_sequence_partial", "cmemit_sequence_geometry_invalid",
    "cmemit_stockholm_header_missing", "cmemit_stockholm_version_unsupported",
    "cmemit_stockholm_terminator_missing", "cmemit_malformed_annotation", "cmemit_malformed_sequence",
    "cmemit_annotation_geometry_invalid", "cmemit_annotation_association_ambiguous",
    "cmemit_interleaved_occurrence_ambiguous", "cmemit_alignment_geometry_invalid",
    "cmemit_clustal_header_missing", "cmemit_phylip_header_invalid", "cmemit_phylip_rows_incomplete",
    "cmemit_phylip_name_truncated", "cmemit_a2m_insert_columns_not_retained",
    "cmemit_annotations_not_measured", "cmemit_model_association_unresolved",
    "cmemit_model_association_conflicting", "cmemit_name_invalid", "cmemit_sample_index_invalid",
    "cmemit_alphabet_conflict", "cmemit_embedding_interval_invalid", "cmemit_embedding_length_mismatch",
    "cmemit_trace_not_decoded", "cmemit_trace_empty", "cmemit_expected_count_mismatch",
    "cmemit_trace_family_unknown", "cmemit_trace_header_missing", "cmemit_trace_terminator_missing",
    "cmemit_trace_score_invalid", "cmemit_trace_score_duplicate", "cmemit_trace_score_missing",
    "cmemit_trace_body_not_decoded", "cmemit_trace_association_unresolved", "cmemit_trace_family_conflict",
    "cmemit_hmm_structure_score_not_measured",
    "cmemit_model_family_conflict",
})
_RESIDUES = frozenset("ACGTURYKMSWBDHVNX")
_CANONICAL = frozenset("ACGTU")
_GAPS = frozenset("-._")
_MISSING = frozenset("~?")
_ALIGNMENT_FORMATS = frozenset({"stockholm", "pfam", "afa", "a2m", "clustal", "phylip"})


def _add(sheet, code, *, artifact=None, row=None, field=None, stage="extraction", severity="error"):
    if code not in ISSUE_CODES:
        raise ValueError("cmemit_unknown_issue_code")
    sheet["issues"].append(issue(code, stage=stage, severity=severity,
        artifact_ref=artifact["artifact_ref"] if artifact else (row["locator"]["artifact_ref"] if row else None),
        record_key=row["record_key"] if row else None, field=field))


def _text(payload, sheet):
    if type(payload) is not dict or set(payload) != {"artifact", "content"}:
        raise ValueError("cmemit_payload_fields_invalid")
    artifact, content = payload["artifact"], payload["content"]
    if artifact not in sheet["artifacts"]:
        raise ValueError("cmemit_payload_artifact_not_retained")
    if type(content) is str:
        try:
            raw = content.encode("utf-8")
        except UnicodeError:
            _add(sheet, "cmemit_text_encoding_invalid", artifact=artifact, stage="format")
            return None
    elif type(content) is bytes:
        raw = content
    else:
        raise TypeError("cmemit_payload_text_or_bytes_required")
    if len(raw) != artifact["size_bytes"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
        _add(sheet, "cmemit_payload_digest_mismatch", artifact=artifact, stage="validation")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        _add(sheet, "cmemit_text_encoding_invalid", artifact=artifact, stage="format")
        return None


def _lines(text):
    result, offset = [], 0
    for n, raw in enumerate(text.splitlines(keepends=True), 1):
        size = len(raw.encode("utf-8"))
        result.append({"text": raw.rstrip("\r\n"), "line": n, "byte_start": offset, "byte_end": offset + size})
        offset += size
    return result


def _location(artifact, ordinal, lines):
    if not lines:
        return locator(artifact["artifact_ref"], ordinal)
    return locator(artifact["artifact_ref"], ordinal,
        line_start=lines[0]["line"], line_end=lines[-1]["line"],
        byte_start=lines[0]["byte_start"], byte_end=lines[-1]["byte_end"])


def _event_location(artifact, event, ordinal=None):
    p = event["locator"]
    return locator(artifact["artifact_ref"], ordinal, line_start=p["line"], line_end=p["line"],
                   byte_start=p["byte_start"], byte_end=p["byte_end"])


def _settings(sheet):
    operation = sheet["operation"]
    if operation["program"] != "cmemit":
        raise ValueError("cmemit_program_required")
    settings = operation["settings"]
    if "--outformat" in settings and type(settings["--outformat"]) is not str:
        raise ValueError("cmemit_alignment_format_string_required")
    for flag in ("-N", "--idx", "-e"):
        if flag in settings and (type(settings[flag]) is not int or settings[flag] <= 0):
            raise ValueError("cmemit_positive_integer_setting_required")
    for flag in ("--a5p", "--a3p", "--seed"):
        if flag in settings and (type(settings[flag]) is not int or settings[flag] < 0):
            raise ValueError("cmemit_nonnegative_integer_setting_required")
    for flag in ("--rna", "--dna", "--hmmonly", "--nohmmonly", "--u5p", "--u3p", "-l", "--iid"):
        if flag in settings and type(settings[flag]) is not bool:
            raise ValueError("cmemit_boolean_setting_required")
    if "--exp" in settings and (type(settings["--exp"]) not in (int, float) or settings["--exp"] <= 0):
        raise ValueError("cmemit_positive_exponent_required")
    incompatible = (settings.get("--rna") and settings.get("--dna") or
        settings.get("--hmmonly") and settings.get("--nohmmonly") or
        "-e" in settings and settings.get("--u5p") and settings.get("--u3p"))
    aligned = operation["mode"] == "sample_aligned"
    if ("--a5p" in settings) != ("--a3p" in settings):
        incompatible = True
    if "--a5p" in settings and "--a3p" in settings:
        first, last = settings["--a5p"], settings["--a3p"]
        incompatible |= not aligned or (first == 0) != (last == 0) or first > last
    if operation["mode"] != "sample_unaligned" and any(settings.get(k) for k in ("-e", "--u5p", "--u3p")):
        incompatible = True
    if incompatible:
        _add(sheet, "cmemit_settings_incompatible", stage="validation")
    if operation["engine_version"] != "1.1.5":
        _add(sheet, "cmemit_engine_version_unverified", stage="validation", severity="warning")
    for flag in (["-N", "--idx"] if operation["mode"] != "consensus" else []):
        if flag not in settings:
            _add(sheet, "cmemit_setting_missing", field=flag, severity="warning")
    if not (settings.get("--rna") or settings.get("--dna")):
        _add(sheet, "cmemit_setting_missing", field="output_alphabet", severity="warning")


def _sequence(sheet, artifact, name, description, sequence, location, *, alignment_key=None, partial=False,
              geometry_valid=True, columns_known=True):
    ordinal = sum(r["kind"] == "generated_sequence" for r in sheet["output_records"])
    location = {**location, "record_ordinal": ordinal}
    residues = "".join(c for c in sequence if c.upper() in _RESIDUES)
    symbols_valid = all(c.upper() in _RESIDUES or c in _GAPS | _MISSING for c in sequence)
    if alignment_key is None and any(c in _GAPS for c in sequence):
        symbols_valid = False
    state = "truncated" if partial else "invalid" if not symbols_valid else "present"
    inputs = [field_input(location, "sequence")]
    counts = {"residue_count": len(residues), "canonical_count": sum(c.upper() in _CANONICAL for c in sequence),
              "gc_count": sum(c.upper() in "GC" for c in sequence),
              "ambiguity_count": sum(c.upper() in _RESIDUES - _CANONICAL for c in sequence),
              "gap_count": sum(c in _GAPS for c in sequence), "column_count": len(sequence)}
    values = {}
    for key, number in counts.items():
        unit = "column" if key in {"gap_count", "column_count"} else "nt"
        cell_state = state
        if key == "column_count" and (alignment_key is None or not columns_known):
            cell_state = "not_measured"
        elif key == "column_count" and not geometry_valid:
            cell_state = "invalid"
        values[key] = value(number if cell_state == "present" else None, state=cell_state,
                            basis="derived", unit=unit, inputs=inputs)
    settings = sheet["operation"]["settings"]
    # Infer only a directly discriminating symbol; otherwise retain the explicit
    # selected alphabet. No model or filename silently supplies an output default.
    upper = set(sequence.upper())
    alphabet = "RNA" if "U" in upper and "T" not in upper else "DNA" if "T" in upper and "U" not in upper else None
    selected = "DNA" if settings.get("--dna") else "RNA" if settings.get("--rna") else None
    if alphabet is None and not ({"U", "T"} <= upper):
        alphabet = selected
    row = {"kind": "generated_sequence", "record_key": record_key(artifact["artifact_ref"], "generated_sequence", ordinal),
        "locator": location, "model_keys": [], "origin": "generated_consensus" if sheet["operation"]["mode"] == "consensus" else "generated_sample",
        "name": name, "description": description, "sequence": sequence, "alphabet": alphabet,
        "residue_sha256": hashlib.sha256(residues.upper().encode("ascii")).hexdigest() if state == "present" else None,
        "sample_index": None, "embedded_interval": None, "alignment_key": alignment_key, "values": values}
    sheet["output_records"].append(row)
    if not symbols_valid:
        _add(sheet, "cmemit_sequence_symbols_invalid", row=row, field="sequence", stage="format")
    if any(c in _MISSING for c in sequence):
        _add(sheet, "cmemit_missing_sequence_symbols", row=row, field="sequence", severity="warning")
    if partial:
        _add(sheet, "cmemit_sequence_partial", row=row)
    if not geometry_valid:
        _add(sheet, "cmemit_sequence_geometry_invalid", row=row, field="column_count")
    if {"U", "T"} <= upper or selected is not None and alphabet != selected:
        _add(sheet, "cmemit_alphabet_conflict", row=row, field="alphabet", stage="validation")
    if "-e" in settings:
        match = re.fullmatch(r"(.+)/(\d+)-(\d+)", name)
        if match:
            start, end = int(match[2]), int(match[3])
            if start >= 1 and end >= start:
                row["embedded_interval"] = {"start": start - 1, "end": end}
            if start < 1 or end < start or end > len(residues):
                _add(sheet, "cmemit_embedding_interval_invalid", row=row, field="embedded_interval", stage="validation")
            elif settings.get("--u5p") and start != 1 or settings.get("--u3p") and end != settings["-e"]:
                _add(sheet, "cmemit_embedding_interval_invalid", row=row, field="embedded_interval", stage="validation")
        else:
            _add(sheet, "cmemit_embedding_interval_invalid", row=row, field="embedded_interval", stage="validation")
        if not partial and symbols_valid and len(residues) != settings["-e"]:
            _add(sheet, "cmemit_embedding_length_mismatch", row=row, field="residue_count", stage="validation")
    return row


def _fasta_parts(text, sheet, artifact):
    parts, current = [], None
    for line in _lines(text):
        s = line["text"]
        if s.startswith(">"):
            if current is not None:
                parts.append(current)
            header = s[1:].split(None, 1)
            current = {"name": header[0] if header else "", "description": header[1] if len(header) > 1 else None,
                       "sequence": "", "lines": [line]}
            if not header:
                _add(sheet, "cmemit_fasta_header_invalid", artifact=artifact, stage="format")
        elif current is None:
            if s.strip():
                _add(sheet, "cmemit_fasta_header_missing", artifact=artifact, stage="format")
        else:
            current["lines"].append(line)
            current["sequence"] += "".join(s.split())
    if current is not None:
        parts.append(current)
    return parts


def _alignment(sheet, artifact, lines, column_count, *, valid=True, complete=True):
    ordinal = sum(r["kind"] == "generated_alignment" for r in sheet["output_records"])
    loc = _location(artifact, ordinal, lines)
    row = {"kind": "generated_alignment", "record_key": record_key(artifact["artifact_ref"], "generated_alignment", ordinal),
        "locator": loc, "model_keys": [], "origin": "generated_sample", "format": artifact["format"],
        "sequence_keys": [], "annotations": {"gf": [], "gs": [], "gr": [], "gc": []},
        "values": {"row_count": value(0, basis="derived", inputs=[field_input(loc, "sequence_rows")]),
                   "column_count": value(column_count if valid and complete else None,
                       state=None if valid and complete and column_count is not None else "truncated" if not complete else "invalid" if not valid else "not_measured",
                       basis="derived", unit="column", inputs=[field_input(loc, "alignment_columns")])}}
    sheet["output_records"].append(row)
    if not valid:
        _add(sheet, "cmemit_alignment_geometry_invalid", row=row, field="column_count")
    if artifact["format"] not in {"stockholm", "pfam"}:
        _add(sheet, "cmemit_annotations_not_measured", row=row, severity="information")
    return row


def _set_members(alignment, rows):
    alignment["sequence_keys"] = [r["record_key"] for r in rows]
    alignment["values"]["row_count"] = value(len(rows), basis="derived",
        inputs=[field_input(alignment["locator"], "sequence_rows")])


def _stockholm(text, sheet, artifact):
    records = list(iter_hmmalign_stockholm_records(text, artifact_ref=artifact["artifact_ref"],
                                                  engine_version=sheet["operation"]["engine_version"]))
    for record in records:
        events = record["original_events"]
        lines = [{**e["locator"], "text": e["raw"]} for e in events]
        complete = record["complete"] and not (record is records[-1] and artifact["completeness"] == "partial")
        geometry_valid = record["header_valid"] and all(r["geometry_valid"] and r["identity_unambiguous"] for r in record["rows"])
        al = _alignment(sheet, artifact, lines, record["column_count"], valid=geometry_valid, complete=complete)
        rows, source_to_row, event_blocks = [], {}, {}
        for source in record["rows"]:
            fragments = source["fragments"]
            location = _location(artifact, 0, [p["locator"] for p in fragments])
            row = _sequence(sheet, artifact, source["name"], None, source["aligned_sequence"], location,
                alignment_key=al["record_key"], partial=not complete,
                geometry_valid=source["geometry_valid"] and source["identity_unambiguous"])
            rows.append(row)
            source_to_row[source["record_key"]] = row
            for fragment in fragments:
                event_blocks[fragment["locator"]["line"]] = fragment["block_index"]
            for problem in source["issues"]:
                code = problem["code"].replace("hmmalign_", "cmemit_")
                if code in ISSUE_CODES:
                    _add(sheet, code, row=row)
        _set_members(al, rows)
        for problem in record["issues"]:
            code = problem["code"].replace("hmmalign_", "cmemit_")
            if code == "cmemit_row_annotation_join_ambiguous":
                code = "cmemit_annotation_association_ambiguous"
            if code in ISSUE_CODES:
                _add(sheet, code, row=al)
        # Derive each annotation's actual interleaved block without the science
        # wrapper's occurrence-based metadata joins for duplicate names.
        block, active = 0, False
        by_name = defaultdict(list)
        for row in rows:
            by_name[row["name"]].append(row)
        for event in events:
            kind = event["kind"]
            if kind in {"sequence", "GC", "GR"}:
                event_blocks[event["locator"]["line"]] = block
                active = True
            elif kind in {"blank", "terminator"} and active:
                block += 1
                active = False
            if kind not in {"GF", "GS", "GR", "GC"}:
                continue
            name, sequence_key = event.get("name"), None
            candidates = by_name[name] if name is not None else []
            if kind in {"GS", "GR"}:
                if len(candidates) == 1 and not any(i["record_key"] == candidates[0]["record_key"] and
                    i["code"] in {"cmemit_interleaved_occurrence_ambiguous", "cmemit_sequence_geometry_invalid"} for i in sheet["issues"]):
                    sequence_key = candidates[0]["record_key"]
                else:
                    _add(sheet, "cmemit_annotation_association_ambiguous", row=al, field=event["tag"], stage="association")
            annotation = {"tag": event["tag"], "value": event["value"], "name": name,
                "locator": _event_location(artifact, event),
                "block_index": event_blocks.get(event["locator"]["line"]) if kind in {"GC", "GR"} else None,
                "sequence_key": sequence_key}
            al["annotations"][kind.lower()].append(annotation)
            if kind == "GS" and event["tag"] == "DE" and sequence_key:
                candidates[0]["description"] = event["value"] if candidates[0]["description"] is None else candidates[0]["description"]


def _fasta_alignment(text, sheet, artifact):
    parts = _fasta_parts(text, sheet, artifact)
    settings = sheet["operation"]["settings"]
    n = settings.get("-N")
    # Neither AFA nor A2M carries an alignment-record delimiter. Grouping requires
    # explicit N and the selected complete model population; otherwise retain a
    # single unresolved group rather than inventing omitted boundaries.
    groups = [parts[i:i+n] for i in range(0, len(parts), n)] if n else ([parts] if parts else [])
    for group_index, group in enumerate(groups):
        lines = [line for part in group for line in part["lines"]]
        lengths = {len(p["sequence"]) for p in group}
        compact = artifact["format"] == "a2m" and any(any(c.islower() or c == "." for c in p["sequence"]) for p in group)
        match_lengths = {sum(c.isupper() or c == "-" for c in p["sequence"]) for p in group}
        valid = len(match_lengths if compact else lengths) <= 1
        complete = not (group_index == len(groups)-1 and artifact["completeness"] == "partial")
        al = _alignment(sheet, artifact, lines, None if compact else next(iter(lengths), 0), valid=valid, complete=complete)
        if compact:
            _add(sheet, "cmemit_a2m_insert_columns_not_retained", row=al, severity="information")
        rows = [_sequence(sheet, artifact, p["name"], p["description"], p["sequence"], _location(artifact, 0, p["lines"]),
                alignment_key=al["record_key"], partial=not complete and i == len(group)-1,
                geometry_valid=valid, columns_known=not compact) for i, p in enumerate(group)]
        _set_members(al, rows)


def _clustal(text, sheet, artifact):
    groups, active = [], []
    for line in _lines(text):
        if line["text"].startswith("CLUSTAL") and active:
            groups.append(active)
            active = []
        active.append(line)
    if active:
        groups.append(active)
    for gi, lines in enumerate(groups):
        nonblank = [l for l in lines if l["text"].strip()]
        header_ok = bool(nonblank and nonblank[0]["text"].startswith("CLUSTAL"))
        al = _alignment(sheet, artifact, lines, None, valid=header_ok)
        if not header_ok:
            _add(sheet, "cmemit_clustal_header_missing", row=al, stage="format")
        blocks, block = [], []
        for line in lines[1:]:
            raw = line["text"]
            if not raw.strip():
                if block:
                    blocks.append(block)
                    block = []
            elif raw[0].isspace() and set(raw.strip()) <= set("*:. "):
                continue
            else:
                tokens = raw.split()
                if len(tokens) in {2, 3} and (len(tokens) == 2 or tokens[2].isdigit()):
                    block.append({"name": tokens[0], "sequence": tokens[1], "line": line})
                else:
                    _add(sheet, "cmemit_malformed_sequence", row=al, stage="format")
        if block:
            blocks.append(block)
        keys, widths, assembled = [], [], {}
        for b, block in enumerate(blocks):
            seen, these_keys = Counter(), []
            widths.append({len(p["sequence"]) for p in block})
            for p in block:
                key = (p["name"], seen[p["name"]])
                seen[p["name"]] += 1
                these_keys.append(key)
                assembled.setdefault(key, {"name": p["name"], "sequence": "", "lines": []})
                assembled[key]["sequence"] += p["sequence"]
                assembled[key]["lines"].append(p["line"])
            keys.append(these_keys)
        valid = header_ok and all(len(w) == 1 for w in widths) and all(k == keys[0] for k in keys)
        columns = sum(next(iter(w)) for w in widths) if valid else None
        al["values"]["column_count"] = value(columns, state=None if valid else "invalid", basis="derived", unit="column",
            inputs=[field_input(al["locator"], "alignment_columns")])
        if not valid:
            _add(sheet, "cmemit_alignment_geometry_invalid", row=al)
        partial = artifact["completeness"] == "partial" and gi == len(groups)-1
        rows = [_sequence(sheet, artifact, p["name"], None, p["sequence"], _location(artifact, 0, p["lines"]),
                alignment_key=al["record_key"], partial=partial, geometry_valid=valid) for p in assembled.values()]
        _set_members(al, rows)


def _phylip(text, sheet, artifact):
    lines, pos = _lines(text), 0
    while pos < len(lines):
        if not lines[pos]["text"].strip():
            pos += 1
            continue
        first = pos
        match = re.fullmatch(r"\s*(\d+)\s+(\d+)\s*", lines[pos]["text"])
        if not match:
            _add(sheet, "cmemit_phylip_header_invalid", artifact=artifact, stage="format")
            return
        n, columns = int(match[1]), int(match[2])
        pos += 1
        parts, malformed = [], False
        for _ in range(n):
            if pos >= len(lines) or not lines[pos]["text"].strip():
                break
            line = lines[pos]
            raw = line["text"]
            if len(raw) < 11:
                malformed = True
                break
            parts.append({"name": raw[:10].strip(), "sequence": "".join(raw[10:].split()), "lines": [line]})
            pos += 1
        # cmemit's PHYLIP writer uses interleaved continuation blocks without
        # names. A count-mismatched block is retained as partial, never padded.
        while parts and len(parts) == n and any(len(p["sequence"]) < columns for p in parts):
            while pos < len(lines) and not lines[pos]["text"].strip():
                pos += 1
            if pos >= len(lines) or re.fullmatch(r"\s*\d+\s+\d+\s*", lines[pos]["text"]):
                break
            for p in parts:
                if pos >= len(lines) or not lines[pos]["text"].strip():
                    break
                p["sequence"] += "".join(lines[pos]["text"].split())
                p["lines"].append(lines[pos])
                pos += 1
        valid = not malformed and n > 0 and len(parts) == n and all(len(p["sequence"]) == columns for p in parts)
        al = _alignment(sheet, artifact, lines[first:pos], columns, valid=valid,
            complete=not (pos >= len(lines) and artifact["completeness"] == "partial"))
        if not valid:
            _add(sheet, "cmemit_phylip_rows_incomplete", row=al, stage="format")
        _add(sheet, "cmemit_phylip_name_truncated", row=al, severity="information")
        rows = [_sequence(sheet, artifact, p["name"], None, p["sequence"], _location(artifact, 0, p["lines"]),
            alignment_key=al["record_key"], geometry_valid=len(p["sequence"]) == columns,
            partial=len(p["sequence"]) < columns) for p in parts]
        _set_members(al, rows)
        if malformed:
            return


def emission_family(model, settings):
    """Native 1.1.5 CM-vs-filter choice, using supplied topology or flags only."""
    if settings.get("--nohmmonly"):
        return "cm"
    if settings.get("--hmmonly"):
        return "hmm"
    cell = model.get("topology", {}).get("base_pair_nodes", {})
    return ("cm" if cell["value"] > 0 else "hmm") if cell.get("state") == "present" else None


def _expected_name(model, model_ordinal, mode, index, settings):
    base = model["name"] if model["name"] is not None else str(model_ordinal + 1)
    if mode == "consensus":
        family = emission_family(model, settings)
        return None if family is None else base + "-" + family + "consensus"
    return base + "-sample" + str(index)


def _associate(sheet, artifact, population_complete):
    models = sheet["input_records"]
    sequences = [r for r in sheet["output_records"] if r["kind"] == "generated_sequence"]
    alignments = [r for r in sheet["output_records"] if r["kind"] == "generated_alignment"]
    mode, settings = sheet["operation"]["mode"], sheet["operation"]["settings"]
    n = 1 if mode == "consensus" else settings.get("-N")
    offset = None if mode == "consensus" else settings.get("--idx")
    ready = population_complete and n is not None and (mode == "consensus" or offset is not None)
    ready &= sheet["operation"]["engine_version"] == "1.1.5"
    ready &= not any(i["code"] in {"cmemit_settings_incompatible", "cmemit_payload_digest_mismatch",
        "cmemit_model_type_incompatible", "cmemit_interleaved_occurrence_ambiguous"} for i in sheet["issues"])
    for i, sequence in enumerate(sequences):
        name = sequence["name"]
        if "-e" in settings:
            match = re.fullmatch(r"(.+)/(\d+)-(\d+)", name)
            name = match[1] if match else name
        candidates = []
        for mi, model in enumerate(models):
            base = model["name"] if model["name"] is not None else str(mi + 1)
            if mode == "consensus":
                expected = _expected_name(model, mi, mode, None, settings)
                if expected == name:
                    candidates.append((mi, None))
            else:
                match = re.fullmatch(re.escape(base) + r"-sample(\d+)", name)
                if match:
                    index = int(match[1])
                    if offset is None or n is None:
                        candidates.append((mi, index))
                    elif offset <= index < offset + n:
                        candidates.append((mi, index))
                    else:
                        _add(sheet, "cmemit_sample_index_invalid", row=sequence, field="sample_index", stage="association")
        assigned = None
        if ready and i < len(models) * n:
            mi, j = divmod(i, n)
            expected = _expected_name(models[mi], mi, mode, None if mode == "consensus" else offset + j, settings)
            aligned_ok = (not alignments or (mi < len(alignments) and sequence["alignment_key"] == alignments[mi]["record_key"]
                           and len(alignments[mi]["sequence_keys"]) == n))
            name_ok = expected is not None and name == (expected[:10] if artifact["format"] == "phylip" else expected)
            duplicate_name = sum(m["name"] == models[mi]["name"] for m in models) > 1
            complete_order = artifact["completeness"] == "complete" and len(sequences) == len(models) * n
            if name_ok and aligned_ok and (not duplicate_name or complete_order):
                assigned = (mi, None if mode == "consensus" else offset + j)
        if assigned is not None:
            mi, index = assigned
            sequence["model_keys"] = [models[mi]["record_key"]]
            sequence["sample_index"] = index
            status = "validated"
        else:
            sequence["model_keys"] = [models[mi]["record_key"] for mi, _ in candidates]
            status = "conflicting" if ready and candidates and len(candidates) == 1 else "unresolved"
            _add(sheet, "cmemit_model_association_" + status, row=sequence, stage="association")
            if not candidates and artifact["format"] != "phylip":
                _add(sheet, "cmemit_name_invalid", row=sequence, field="name", stage="association")
        sheet["associations"].append({"relation": "generated_from", "input_keys": list(sequence["model_keys"]),
                                     "output_keys": [sequence["record_key"]], "status": status})
    for al in alignments:
        members = [r for r in sequences if r["record_key"] in al["sequence_keys"]]
        keys = list(dict.fromkeys(k for r in members for k in r["model_keys"]))
        statuses = [a["status"] for a in sheet["associations"] if any(k in al["sequence_keys"] for k in a["output_keys"])]
        valid = len(keys) == 1 and bool(statuses) and all(s == "validated" for s in statuses)
        model = next((m for m in models if len(keys) == 1 and m["record_key"] == keys[0]), None)
        ids = [a["value"] for a in al["annotations"]["gf"] if a["tag"] == "ID"]
        if ids and (model is None or any(s != model["name"] for s in ids)):
            valid = False
            _add(sheet, "cmemit_model_association_conflicting", row=al, field="GF.ID", stage="association")
        descriptions = [a["value"] for a in al["annotations"]["gf"] if a["tag"] == "DE" and
                        a["value"].startswith("Synthetic sequence alignment generated by cmemit")]
        if model is not None:
            family = emission_family(model, settings)
            if family is not None and any(("hmm" if "[hmm-mode]" in d else "cm") != family for d in descriptions):
                valid = False
                _add(sheet, "cmemit_model_family_conflict", row=al, field="GF.DE", stage="association")
        al["model_keys"] = keys
        sheet["associations"].append({"relation": "generated_from", "input_keys": keys,
            "output_keys": [al["record_key"]], "status": "validated" if valid else "unresolved"})
    if ready and artifact["completeness"] == "complete" and len(sequences) != len(models) * n:
        _add(sheet, "cmemit_expected_count_mismatch", artifact=artifact, field="sequence_count", stage="validation")


def _trace(text, sheet, artifact):
    if not text.strip():
        _add(sheet, "cmemit_trace_empty", artifact=artifact, severity="information")
        return
    groups, active = [], []
    for line in _lines(text):
        s = line["text"].strip()
        if s.startswith(">") and active:
            groups.append(active)
            active = []
        if s or active:
            active.append(line)
        if s == "//":
            groups.append(active)
            active = []
    if active:
        groups.append(active)
    sequences = [r for r in sheet["output_records"] if r["kind"] == "generated_sequence"]
    models = {r["record_key"]: r for r in sheet["input_records"]}
    settings = sheet["operation"]["settings"]
    sequence_associations = {k: a for a in sheet["associations"] for k in a["output_keys"]}
    complete_population = artifact["completeness"] == "complete" and len(groups) == len(sequences) and all(
        g[-1]["text"].strip() == "//" for g in groups) and not any(i["artifact_ref"] == artifact["artifact_ref"] and
        i["code"] == "cmemit_payload_digest_mismatch" for i in sheet["issues"])
    for ordinal, lines in enumerate(groups):
        texts = [line["text"].strip() for line in lines]
        families = [f for marker, f in (("Parsetree dump", "cm_parsetree"), ("HMM trace dump", "hmm_trace")) if marker in texts]
        if len(families) != 1:
            _add(sheet, "cmemit_trace_family_unknown", artifact=artifact, stage="format")
            continue
        family = families[0]
        name = texts[0][1:].strip() if texts[0].startswith(">") else None
        loc = _location(artifact, ordinal, lines)
        row = {"kind": "generated_trace", "record_key": record_key(artifact["artifact_ref"], "generated_trace", ordinal),
            "locator": loc, "model_keys": [], "sequence_keys": [], "name": name, "trace_family": family, "values": {}}
        sheet["native_rows"].append(row)
        if not name:
            _add(sheet, "cmemit_trace_header_missing", row=row, stage="format")
        complete = texts[-1] == "//"
        if not complete:
            _add(sheet, "cmemit_trace_terminator_missing", row=row, stage="format")
        for field, label in (("score_bits", "SCORE"), ("structure_score_bits", "STRUCTURE SCORE")):
            hits = []
            for line in lines:
                match = re.fullmatch(r"\s*" + re.escape(label) + r":\s*(\S+)\s+bits\s*", line["text"])
                if match:
                    hits.append((line, match[1]))
            if not hits:
                state = "not_measured" if sheet["operation"]["mode"] == "sample_aligned" else "missing" if complete else "truncated"
                row["values"][field] = value(state=state, unit="bit", inputs=[field_input(loc, label)])
                if sheet["operation"]["mode"] != "sample_aligned":
                    _add(sheet, "cmemit_trace_score_missing", row=row, field=field)
                continue
            line, token = hits[0]
            inputs = [field_input(_location(artifact, ordinal, [line]), label)]
            try:
                number = float(token)
                valid = math.isfinite(number)
            except ValueError:
                number, valid = None, False
            if len(hits) != 1:
                _add(sheet, "cmemit_trace_score_duplicate", row=row, field=field)
                valid = False
            if not valid:
                row["values"][field] = value(state="invalid", unit="bit", inputs=inputs, native_token=token)
                _add(sheet, "cmemit_trace_score_invalid", row=row, field=field)
            elif family == "hmm_trace" and field == "structure_score_bits" and number == 0:
                # cmemit.c sets struct_sc=0 in the HMM branch without computing
                # a CM structural score. Keep the printed sentinel, not a claim
                # that a zero structural measurement was made.
                row["values"][field] = value(state="not_measured", unit="bit", inputs=inputs, native_token=token)
                _add(sheet, "cmemit_hmm_structure_score_not_measured", row=row, field=field, severity="information")
            else:
                row["values"][field] = value(number, unit="bit", inputs=inputs, native_token=token)
                if family == "hmm_trace" and field == "structure_score_bits":
                    _add(sheet, "cmemit_trace_family_conflict", row=row, field=field, stage="validation")
        candidate = sequences[ordinal] if complete_population else None
        if candidate is not None and sequence_associations.get(candidate["record_key"], {}).get("status") == "validated":
            model = models[candidate["model_keys"][0]]
            expected_name = (model["name"] or str(list(models).index(model["record_key"]) + 1)) + "-sample" + str(candidate["sample_index"])
            expected_family = emission_family(model, settings)
            if name == expected_name and expected_family == ("cm" if family == "cm_parsetree" else "hmm"):
                row["model_keys"] = list(candidate["model_keys"])
                row["sequence_keys"] = [candidate["record_key"]]
            elif name == expected_name:
                _add(sheet, "cmemit_trace_family_conflict", row=row, stage="association")
        if not row["sequence_keys"]:
            _add(sheet, "cmemit_trace_association_unresolved", row=row, stage="association", severity="warning")
        sheet["associations"].append({"relation": "generated_from", "input_keys": list(row["model_keys"]),
            "output_keys": [row["record_key"]], "status": "validated" if row["sequence_keys"] else "unresolved"})
        _add(sheet, "cmemit_trace_body_not_decoded", row=row, severity="information")


def populate_cmemit_sheet(*, operation, artifacts, models, output, trace=None):
    """Populate the closed cmemit sheet solely from supplied data.

    Invalid argument shapes raise ValueError/TypeError. Malformed native data
    yields specific issues and retains parseable siblings. Missing defaults stay
    missing; expected counts and sample indices never guess an absent N/idx.
    """
    sheet = new_sheet(operation, artifacts)
    _settings(sheet)
    if type(models) is not dict or set(models) != {"artifact", "format", "records", "issues", "population_complete"}:
        raise ValueError("cmemit_model_extraction_invalid")
    if type(models["population_complete"]) is not bool or type(models["records"]) is not list:
        raise ValueError("cmemit_model_extraction_invalid")
    if models["artifact"] not in sheet["artifacts"]:
        raise ValueError("cmemit_model_artifact_not_retained")
    sheet["input_records"] = deepcopy(models["records"])
    sheet["issues"].extend(deepcopy(models["issues"]))
    if not models["population_complete"]:
        _add(sheet, "cmemit_model_population_incomplete", artifact=models["artifact"], severity="warning")
    keys = []
    for model in sheet["input_records"]:
        if model.get("kind") != "model" or model.get("locator", {}).get("artifact_ref") != models["artifact"]["artifact_ref"]:
            raise ValueError("cmemit_model_record_invalid")
        keys.append(model["record_key"])
        if model["model_type"] != "cm":
            _add(sheet, "cmemit_model_type_incompatible", row=model, stage="validation")
    if len(keys) != len(set(keys)):
        raise ValueError("cmemit_duplicate_model_record_key")
    text = _text(output, sheet)
    artifact = output["artifact"]
    mode = operation["mode"]
    if artifact["completeness"] != "complete":
        _add(sheet, "cmemit_capture_" + artifact["completeness"], artifact=artifact, severity="warning")
    allowed = _ALIGNMENT_FORMATS if mode == "sample_aligned" else {"fasta"}
    format_ok = artifact["format"] in allowed
    selected_format = operation["settings"].get("--outformat")
    if mode == "sample_aligned" and selected_format is not None and selected_format.lower() != artifact["format"]:
        format_ok = False
    if not format_ok:
        _add(sheet, "cmemit_format_incompatible", artifact=artifact, stage="format")
    elif text is not None:
        if not text.strip():
            _add(sheet, "cmemit_output_empty", artifact=artifact, severity="information")
        elif artifact["format"] in {"stockholm", "pfam"}:
            _stockholm(text, sheet, artifact)
        elif artifact["format"] in {"afa", "a2m"}:
            _fasta_alignment(text, sheet, artifact)
        elif artifact["format"] == "clustal":
            _clustal(text, sheet, artifact)
        elif artifact["format"] == "phylip":
            _phylip(text, sheet, artifact)
        else:
            parts = _fasta_parts(text, sheet, artifact)
            for i, part in enumerate(parts):
                _sequence(sheet, artifact, part["name"], part["description"], part["sequence"],
                    _location(artifact, i, part["lines"]), partial=artifact["completeness"] == "partial" and i == len(parts)-1)
    _associate(sheet, artifact, models["population_complete"])
    if trace is not None:
        if trace["artifact"]["format"] != "infernal_trace":
            raise ValueError("cmemit_trace_format_required")
        trace_text = _text(trace, sheet)
        if trace_text is not None:
            _trace(trace_text, sheet, trace["artifact"])
    validate_common_sheet(sheet)
    return sheet


__all__ = ["populate_cmemit_sheet", "ROW_FIELDS", "COMPONENT_NAMES", "ISSUE_CODES", "CHECK_NAMES"]
