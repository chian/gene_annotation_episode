"""Loss-aware Infernal target-hit sheets, populated from supplied text only.

Supports cmsearch/cmscan tblout formats 1/3 and cmscan format 2. No execution,
acquisition, alignment reconstruction, confidence mapping or annotation credit.
The calculator in infernal_search_grader consumes the saved cells independently.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
import shlex

from .infernal_search_contracts import SHEET_SCHEMA
from .infernal_search_cells import _copy, _issue, _positive, populate_infernal_search_cells
_BASE = ["native_target_name", "native_target_accession", "native_query_name",
         "native_query_accession", "algorithm", "model_from", "model_to",
         "sequence_from", "sequence_to", "strand", "truncation", "pass",
         "gc_fraction", "bias_bits", "bitscore", "evalue", "inclusion"]
_LENGTHS = ["native_model_length", "native_sequence_length"]
_OVERLAP = ["olp", "anyidx", "anyfrct1", "anyfrct2", "winidx", "winfrct1", "winfrct2"]
_INTS = {"model_from", "model_to", "sequence_from", "sequence_to", "pass", "idx", *_LENGTHS}
_NUMBERS = {"gc_fraction", "bias_bits", "bitscore", "evalue"}
_ENUMS = {"algorithm": {"cm", "hmm"}, "strand": {"+", "-"},
          "truncation": {"no", "5'", "3'", "5'&3'", "-"},
          "inclusion": {"!", "?"}, "olp": {"*", "^", "$", "="}}








def _number(token):
    value = float(token)
    if not math.isfinite(value):
        raise ValueError
    # An unrepresentable positive E-value is not native zero. The original
    # decimal token remains retained if no finite numeric cell can hold it.
    if value == 0 and Decimal(token) != 0:
        raise ValueError
    return value


def _columns(fmt, lengths=True):
    if fmt == 1:
        return list(_BASE)
    if fmt == 3:
        return _BASE + _LENGTHS
    return ["idx", *_BASE[:4], "clan", *_BASE[4:], *_OVERLAP] + (_LENGTHS if lengths else [])


def _header(line):
    text = " ".join(line.lstrip()[1:].split())
    if text.startswith("idx target name"):
        return (2, "mdl len" in text) if "mdl from" in text else (0, False)
    if text.startswith("target name accession query name"):
        return (3, True) if "mdl len" in text else (1, False)
    return None


def _token(field, token, issues):
    try:
        if field in _INTS:
            if not re.fullmatch(r"[+]?[0-9]+", token) or int(token) < 1:
                raise ValueError
            return int(token)
        if field in _NUMBERS:
            value = _number(token)
            if field == "evalue" and value < 0 or field == "gc_fraction" and not 0 <= value <= 1:
                raise ValueError
            return value
        if field in _ENUMS:
            if token not in _ENUMS[field]:
                raise ValueError
            return token
        if field in {"anyidx", "winidx"}:
            if token == "-" or field == "winidx" and token == '"':
                return token
            if not re.fullmatch(r"-?[0-9]+", token) or int(token) == 0 or int(token) < -1:
                raise ValueError
            return int(token)
        if field in {"anyfrct1", "anyfrct2", "winfrct1", "winfrct2"}:
            if token == "-" or field.startswith("win") and token == '"':
                return token
            value = _number(token)
            if not 0 <= value <= 1:
                raise ValueError
            return value
        if field.endswith("_accession") or field == "clan":
            return None if token == "-" else token
        return token
    except (ValueError, OverflowError, InvalidOperation):
        _issue(issues, "native_cell_invalid", field=field, token=token)
        return None


def _read_artifact(raw, index, operation):
    issues = []
    locator = {"artifact_id": raw.get("artifact_id"), "artifact_index": index}
    artifact = {**_copy(raw), **locator, "headers": [], "footer": {}, "rows": [], "issues": issues}
    content = raw.get("content")
    if (not isinstance(raw.get("artifact_id"), str) or not raw["artifact_id"]
            or raw.get("format") != "infernal_tblout" or type(raw.get("table_format")) is not int
            or raw["table_format"] not in (1, 2, 3) or not isinstance(content, str)
            or raw.get("complete") is not None and type(raw["complete"]) is not bool):
        _issue(issues, "artifact_contract_invalid")
        artifact.update(status="invalid", effective_complete=None)
        return artifact, []
    # Text is supplied already decoded. Detect replacement characters without
    # pretending that the original byte encoding can be recovered here.
    if "\ufffd" in content or "\x00" in content or any(0xD800 <= ord(c) <= 0xDFFF for c in content):
        _issue(issues, "native_text_possible_decode_loss", severity="warning")
    artifact["sha256_utf8"] = hashlib.sha256(content.encode("utf-8", errors="surrogatepass")).hexdigest()
    lines = content.splitlines()
    footer = defaultdict(list)
    headings, markers = [], []
    for line_no, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            artifact["headers"].append({"line": line_no, "text": line})
            if found := _header(line):
                headings.append(found)
            if line.strip() == "# [ok]":
                markers.append(line_no)
            if match := re.match(r"\s*#\s*([^:]+):\s*(.*)", line):
                footer[match[1].strip()].append({"line": line_no, "value": match[2].strip()})
    artifact["footer"] = {"fields": dict(footer), "complete_marker_lines": markers}
    def declaration(key):
        values = list(dict.fromkeys(row["value"] for row in footer.get(key, [])))
        if len(values) > 1:
            _issue(issues, "native_declaration_conflict", field=key, values=values)
            return None
        return values[0] if values else None
    native_program = declaration("Program")
    native_version_text = declaration("Version")
    native_version = native_version_text.split()[0] if native_version_text else None
    program = native_program or operation.get("program")
    if len({r["value"] for r in footer.get("Program", [])}) > 1:
        program = None
    if native_program and native_program != operation.get("program"):
        _issue(issues, "program_declaration_conflict", native=native_program, supplied=operation.get("program"))
    if program not in ("cmsearch", "cmscan"):
        _issue(issues, "native_program_unsupported", native=program)
        program = None
    if native_version and operation.get("native_version") and native_version != operation["native_version"]:
        _issue(issues, "version_declaration_conflict", native=native_version, supplied=operation["native_version"])
    version = native_version or operation.get("native_version")
    if version is None:
        _issue(issues, "native_version_unknown", severity="warning")
    elif not re.fullmatch(r"1\.1\.(?:[0-5])", version):
        _issue(issues, "native_version_unverified", severity="warning", native_version=version)
    mode = declaration("Pipeline mode")
    if mode and program and mode != {"cmsearch": "SEARCH", "cmscan": "SCAN"}[program]:
        _issue(issues, "pipeline_mode_conflict", native=mode, program=program)
    fmt, lengths = raw["table_format"], raw["table_format"] != 1
    if headings:
        if len(set(headings)) > 1:
            _issue(issues, "native_table_headers_conflict")
            fmt, lengths = 0, False
        else:
            fmt, lengths = headings[0]
        if fmt != raw["table_format"]:
            _issue(issues, "table_format_declaration_conflict", native=fmt, supplied=raw["table_format"])
    elif fmt == 2 and isinstance(version, str) and re.fullmatch(r"1\.1\.[0-4]", version):
        lengths = False
    if fmt == 0:
        _issue(issues, "abbreviated_filter_output_not_target_hit_table")
    if fmt == 2 and program != "cmscan":
        _issue(issues, "format_2_requires_cmscan")
        program = None
    if fmt == 3 and isinstance(version, str) and re.fullmatch(r"1\.1\.[0-4]", version):
        _issue(issues, "table_format_version_conflict", native_version=version, table_format=fmt)
    option_rows = footer.get("Option settings", [])
    option_tokens = []
    for row in option_rows:
        try:
            tokens = shlex.split(row["value"])
            option_tokens.extend(tokens)
            for pos, token in enumerate(tokens[:-1]):
                if token == "--fmt" and tokens[pos+1] != str(fmt):
                    _issue(issues, "native_option_table_format_conflict", option=tokens[pos+1], observed=fmt)
        except ValueError:
            _issue(issues, "native_option_text_unparseable", severity="warning", line=row["line"])
    option_formats = {option_tokens[i+1] for i, token in enumerate(option_tokens[:-1]) if token == "--fmt"}
    if not headings and len(option_formats) == 1 and next(iter(option_formats)) in {"1", "2", "3"}:
        fmt = int(next(iter(option_formats)))
        lengths = fmt != 1 and not (fmt == 2 and isinstance(version, str) and re.fullmatch(r"1\.1\.[0-4]", version))
    if len(option_formats) > 1:
        _issue(issues, "native_option_formats_conflict", values=sorted(option_formats))
    if fmt == 2 and program != "cmscan":
        program = None
    final_marker = bool(markers) and all(not x.strip() for x in lines[markers[-1]:])
    if markers and not final_marker:
        _issue(issues, "data_after_native_completion_marker")
    if markers and raw.get("complete") is False:
        _issue(issues, "completion_declaration_conflict", native=True, supplied=False)
    if not markers:
        _issue(issues, "native_completion_marker_absent", severity="warning")
    effective_complete = (True if final_marker or raw.get("complete") is True else None)
    if raw.get("complete") is False or markers and not final_marker:
        effective_complete = False
    artifact.update(native_program=native_program, effective_program=program,
                    native_version=native_version, effective_version=version,
                    observed_table_format=fmt if headings else None, effective_table_format=fmt,
                    table_format_basis="native_header" if headings else "native_options" if option_formats else "supplied_declaration",
                    native_complete=bool(markers), effective_complete=effective_complete,
                    native_option_tokens=option_tokens,
                    # Capturing the complete table does not restore hits the
                    # selected command deliberately omitted. Its original
                    # settings remain evidence even without a native footer.
                    omitted_overlaps=("--oskip" in option_tokens
                        or operation.get("settings", {}).get("--oskip") is True))
    columns = _columns(fmt, lengths) if fmt else []
    hits = []
    for line_no, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        rowloc = {**locator, "line": line_no}
        row = {"locator": rowloc, "text": line, "issues": []}
        artifact["rows"].append(row)
        tokens = line.split(maxsplit=len(columns)) if columns else line.split()
        row["tokens"] = tokens
        if not columns or len(tokens) < len(columns):
            _issue(row["issues"], "native_row_truncated_or_wrong_format", expected_fixed_fields=len(columns), actual_fields=len(tokens))
            row["status"] = "invalid"
            continue
        values = {name: _token(name, token, row["issues"]) for name, token in zip(columns, tokens)}
        hit_id = json.dumps([raw["artifact_id"], index, line_no], separators=(",", ":"))
        hit = {"hit_id": hit_id, "locator": rowloc, "table_format": fmt, "program": program,
               **dict.fromkeys([*_BASE, *_LENGTHS, "idx", "clan", *_OVERLAP]), **values,
               "description": tokens[len(columns)] if len(tokens) > len(columns) else None,
               "native_tokens": dict(zip(columns + ["description"], tokens)), "issues": row["issues"]}
        if len(tokens) == len(columns):
            _issue(row["issues"], "native_description_missing", severity="warning")
        row.update(hit_id=hit_id, status="partial" if row["issues"] else "available")
        hits.append(hit)
    return artifact, hits










def _resolve_overlaps(hits, artifacts):
    by_scope = defaultdict(list)
    for hit in hits:
        if hit["table_format"] == 2:
            by_scope[tuple(hit["query_list_locator"].values())].append(hit)
    for rows in by_scope.values():
        by_idx = defaultdict(list)
        for hit in rows:
            by_idx[hit["idx"]].append(hit)
        for hit in rows:
            resolved = {}
            for prefix in ("any", "win"):
                token = hit[prefix + "idx"]
                fractions = [hit[prefix + "frct1"], hit[prefix + "frct2"]]
                if token == '"':
                    if prefix != "win" or fractions != ['"', '"'] or "any" not in resolved:
                        _issue(hit["issues"], "overlap_ditto_invalid", field=prefix)
                        entry = {"status": "invalid", "hit_id": None}
                    else:
                        entry = {**deepcopy(resolved["any"]), "ditto_of": "any"}
                        if entry["status"] not in {"resolved", "omitted_reference"}:
                            _issue(hit["issues"], "overlap_ditto_without_reference")
                elif token == "-":
                    entry = {"status": "not_applicable", "hit_id": None}
                    if fractions != ["-", "-"]:
                        _issue(hit["issues"], "overlap_absence_fraction_conflict", field=prefix)
                elif token == -1:
                    entry = {"status": "omitted_reference", "hit_id": None, "index": -1}
                    if not artifacts[hit["locator"]["artifact_index"]]["omitted_overlaps"]:
                        _issue(hit["issues"], "overlap_omitted_reference_without_recorded_oskip", severity="warning")
                elif _positive(token):
                    matches = by_idx.get(token, [])
                    entry = {"status": "unresolved", "hit_id": None, "index": token}
                    if len(matches) != 1:
                        _issue(hit["issues"], "overlap_reference_missing_or_ambiguous", field=prefix, index=token)
                    else:
                        other = matches[0]
                        a, b = hit["sequence_interval"], other["sequence_interval"]
                        overlap = max(0, min(a[1], b[1]) - max(a[0], b[0])) if a and b else None
                        valid = (other is not hit and _positive(hit["idx"]) and token < hit["idx"]
                                 and hit["strand"] == other["strand"] and overlap is not None and overlap > 0
                                 and (prefix != "win" or other["olp"] == "^"))
                        if hit["evalue"] is not None and other["evalue"] is not None:
                            valid = valid and other["evalue"] <= hit["evalue"]
                        artifact = artifacts[hit["locator"]["artifact_index"]]
                        if "--oclan" in artifact["native_option_tokens"]:
                            valid = valid and hit["clan"] is not None and hit["clan"] == other["clan"]
                        if not valid:
                            _issue(hit["issues"], "overlap_reference_relationship_invalid", field=prefix, index=token)
                        else:
                            entry.update(status="resolved", hit_id=other["hit_id"], overlap_length=overlap)
                            expected = [overlap/(a[1]-a[0]), overlap/(b[1]-b[0])]
                            for n, (observed, calculated) in enumerate(zip(fractions, expected), 1):
                                if type(observed) not in (int, float) or abs(observed-calculated) > .000501:
                                    _issue(hit["issues"], "overlap_fraction_coordinate_conflict", field=prefix+"frct"+str(n), calculated=calculated)
                else:
                    entry = {"status": "invalid", "hit_id": None}
                if token not in ("-", '"') and any(type(x) not in (int, float) for x in fractions):
                    _issue(hit["issues"], "overlap_reference_fraction_missing", field=prefix)
                entry["native_fractions"] = fractions
                resolved[prefix] = entry
            if (hit["olp"] in {"*", "^"} and any(hit[p + "idx"] != "-" for p in ("any", "win"))
                    or hit["olp"] == "$" and (hit["anyidx"] in (None, "-") or hit["winidx"] != "-")
                    or hit["olp"] == "=" and any(hit[p + "idx"] in (None, "-") for p in ("any", "win"))):
                _issue(hit["issues"], "overlap_classification_reference_conflict")
            if hit["olp"] == "=" and hit["winidx"] == '"' and resolved["any"]["status"] == "resolved":
                other = next(r for r in rows if r["hit_id"] == resolved["any"]["hit_id"])
                if other["olp"] != "^":
                    _issue(hit["issues"], "overlap_ditto_winner_classification_invalid")
            hit["overlap_references"] = resolved


def populate_infernal_search_sheet(artifacts: list[dict], *, operation: dict,
                                  sequence_metadata: list[dict] | None = None,
                                  model_metadata: list[dict] | None = None) -> dict:
    """Populate finite native cells and explicit joins; never acquire inputs.

    Metadata occurrence qualifies an original input record; tblout alone cannot
    resolve it. Native format-2 list indices only scope overlap references.
    Malformed envelopes raise ValueError; malformed artifacts/rows/cells remain
    diagnosable in the returned sheet beside independent valid measurements.
    """
    if not isinstance(artifacts, list) or any(not isinstance(x, dict) for x in artifacts):
        raise ValueError("infernal_artifact_object_list_required")
    if not isinstance(operation, dict) or not isinstance(operation.get("settings", {}), dict):
        raise ValueError("infernal_operation_object_required")
    operation, artifacts = _copy(operation), _copy(artifacts)
    issues = []
    if operation.get("program") not in ("cmsearch", "cmscan"):
        _issue(issues, "operation_program_invalid")
    if operation.get("native_version") is not None and not isinstance(operation["native_version"], str):
        raise ValueError("infernal_native_version_text_required")
    parsed, hits = [], []
    ids = [a.get("artifact_id") for a in artifacts]
    for index, raw in enumerate(artifacts):
        artifact, rows = _read_artifact(raw, index, operation)
        parsed.append(artifact)
        if ids.count(raw.get("artifact_id")) > 1:
            _issue(artifact["issues"], "artifact_id_ambiguous")
        list_no, previous_query, previous_idx = -1, None, None
        list_valid = False
        for hit in rows:
            query = (hit["native_query_name"], hit["native_query_accession"])
            if hit["table_format"] == 2:
                if hit["idx"] == 1 or query != previous_query or list_no < 0:
                    list_no += 1
                    list_valid = hit["idx"] == 1
                elif not _positive(hit["idx"]) or previous_idx is None or hit["idx"] != previous_idx + 1:
                    list_valid = False
                    _issue(hit["issues"], "native_list_index_discontinuity")
                hit["query_list_locator"] = {"artifact_index": index, "list_index": list_no}
                hit["query_list_boundary_observed"] = list_valid
                previous_idx = hit["idx"]
            else:
                hit["query_list_locator"] = None
                hit["query_list_boundary_observed"] = False
            previous_query = query
            hits.append(hit)
    limitations = ["Native scores are model scores, not annotation probabilities.",
                  "E-values are per query and depend on native search space; returned hits do not define database size.",
                  "Table spans do not establish paired residue coverage, identity or aligned correspondence.",
                  "Printed score/bias precision is one decimal, GC two decimals and E-value two significant digits in 1.1.5.",
                  "Format-2 overlap fractions are rounded to three decimal places in 1.1.5.",
                  "Distinct artifacts, models and hits are not asserted to be independent evidence."]
    tokens = [token for a in parsed for token in a.get("native_option_tokens", [])]
    settings = operation.get("settings", {})
    if "--anytrunc" in tokens or settings.get("--anytrunc") is True or settings.get("truncation") == "any":
        limitations.append("Native --anytrunc E-values are not calibrated for arbitrary truncated searches.")
    if any(flag in tokens for flag in ("--max", "--nohmm")) or settings.get("acceleration") in ("max", "nohmm"):
        limitations.append("Selected native acceleration disables truncated-hit detection.")
    if any(a.get("effective_version") == "1.1.5" for a in parsed):
        limitations.append("Infernal 1.1.5 inclusion code uses reporting-threshold mode; mixed E-value/bit-score modes may ignore the requested inclusion mode. Native inc is retained unchanged.")
    result = populate_infernal_search_cells(operation=operation, artifacts=parsed, hits=hits,
        sequence_metadata=sequence_metadata, model_metadata=model_metadata,
        sequence_populations=[], source_context={"profile": "infernal_tblout"},
        issues=issues, statistical_limitations=limitations)
    # The native overlap-reference grammar depends on assembled intervals.
    # Retain this native relationship reader; it supplies no published score.
    before = {hit["hit_id"]: len(hit["issues"]) for hit in result["hits"]}
    _resolve_overlaps(result["hits"], result["artifacts"])
    for hit in result["hits"]:
        extra = hit["issues"][before[hit["hit_id"]]:]
        result["issues"].extend({**p, **hit["locator"]} for p in extra)
        if extra:
            hit["status"] = "partial"
            result["artifacts"][hit["locator"]["artifact_index"]]["status"] = "partial"
    if result["issues"] and result["status"] == "available":
        result["status"] = "partial"
    return _copy(result)



__all__ = ["populate_infernal_search_sheet", "SHEET_SCHEMA"]
