"""Pure supplied-byte readers and sheet construction for genomic overlaps.

Inputs use zero-based half-open outer spans, exact chromosome tokens and stable
row occurrences. No function opens a path, acquires data, runs an executable,
chooses a resource or grants an execution identity. Run large inputs in the
caller's bounded calculation worker; complete retained artifacts stay outside
these in-memory records.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import json
import re
from typing import BinaryIO
import unicodedata

from .genomic_overlap_contracts import (
    ComparisonSpec, NativePairReceipt, ParsedOverlapPairs, ParsedRegionSet,
    ReferenceRelation, RegionSetSpec, Request, Sheet, _finite_json_copy,
    validate_genomic_overlap_record,
)

_MAX_COORDINATE = 2**63 - 1
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")


def _failure(code, stage, *, set_key=None, comparison_key=None, artifact_ref=None,
             locator=None, field_path=None, expected_value=None, observed_value=None,
             partial_artifact_refs=(), requirement="none"):
    return {"code": code, "stage": stage, "set_key": set_key,
            "comparison_key": comparison_key, "artifact_ref": artifact_ref,
            "locator": deepcopy(locator), "field_path": field_path,
            "expected_value": deepcopy(expected_value), "observed_value": deepcopy(observed_value),
            "partial_artifact_refs": list(partial_artifact_refs), "requirement": requirement}


def _unique_issues(*groups):
    result, seen = [], set()
    for group in groups:
        for issue in group:
            key = json.dumps(issue, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                result.append(deepcopy(issue))
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _chromosome(value):
    return (type(value) is str and bool(value) and
            not any(char.isspace() or unicodedata.category(char).startswith("C") for char in value))


def _coordinate(value, *, textual):
    if textual:
        if type(value) is not str or not _INTEGER.fullmatch(value):
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return value if type(value) is int else None


def _read_supplied(content):
    if content is None:
        return None, False
    if type(content) is bytes:
        return content, False
    if not callable(getattr(content, "read", None)):
        raise ValueError("genomic_overlap_bytes_or_binary_stream_required")
    chunks = []
    try:
        while True:
            chunk = content.read(1024 * 1024)
            if type(chunk) is not bytes:
                raise ValueError("genomic_overlap_binary_stream_required")
            if not chunk:
                break
            chunks.append(chunk)
    except (OSError, EOFError):
        return b"".join(chunks), True
    return b"".join(chunks), False


def _lines(raw):
    offset = 0
    parts = raw.split(b"\n")
    for index, part in enumerate(parts):
        terminated = index < len(parts) - 1
        if not part and not terminated:
            break
        whole = part + (b"\n" if terminated else b"")
        text_bytes = part[:-1] if terminated and part.endswith(b"\r") else part
        locator = {"kind": "bed_line", "line_number": index + 1,
                   "byte_start": offset, "byte_end": offset + len(whole)}
        yield text_bytes, locator, terminated
        offset += len(whole)


def _validate_line_locations(records, byte_count):
    offset = 0
    for number, row in enumerate(sorted(records, key=lambda r: r["locator"]["line_number"]), 1):
        loc = row["locator"]
        if loc["line_number"] != number or loc["byte_start"] != offset:
            raise ValueError("genomic_overlap_line_location_partition")
        offset = loc["byte_end"]
    if offset != byte_count:
        raise ValueError("genomic_overlap_line_byte_partition")


def _specification(value):
    spec = validate_genomic_overlap_record("RegionSetSpec", value)
    expected = "bed_artifact" if spec["format"] == "bed_outer_span_v1" else "coordinate_rows_artifact"
    if spec["source"]["kind"] != expected or spec["source"]["file"]["format"] != spec["format"]:
        raise ValueError("genomic_overlap_input_format_binding")
    return spec


def _groups(set_key, regions):
    coordinate, full = {}, {}
    for row in regions:
        coordinate.setdefault((row["chromosome"], row["start"], row["end"]), []).append(row)
        full.setdefault(_canonical(row["original_fields"]), []).append(row)
    coordinates = [{"group_key": f"{set_key}:coordinate:{i}", "chromosome": key[0],
                    "start": key[1], "end": key[2],
                    "occurrence_keys": [row["occurrence_key"] for row in rows]}
                   for i, (key, rows) in enumerate(coordinate.items())]
    originals = [{"group_key": f"{set_key}:full_record:{i}",
                  "original_fields": deepcopy(rows[0]["original_fields"]),
                  "occurrence_keys": [row["occurrence_key"] for row in rows]}
                 for i, rows in enumerate(full.values())]
    return coordinates, originals


def _row_values(fields, *, textual):
    if type(fields) is not list or len(fields) < 3:
        return [("unsupported_input_format", "/original_fields", 3,
                 len(fields) if type(fields) is list else fields)], None
    errors = []
    if not _chromosome(fields[0]):
        errors.append(("invalid_chromosome_token", "/original_fields/0", None, fields[0]))
    start, end = (_coordinate(fields[i], textual=textual) for i in (1, 2))
    if start is None or end is None or not 0 <= start < end <= _MAX_COORDINATE:
        code = "zero_width_interval" if start is not None and start == end and 0 <= start <= _MAX_COORDINATE else "invalid_coordinate"
        errors.append((code, "/original_fields", None, fields[:3]))
    return errors, (fields[0], start, end)


def _optional_text(fields, index):
    return fields[index] if len(fields) > index and type(fields[index]) is str and fields[index] else None


def _decode_rows(raw):
    """Recover whole supplied JSON array values even before a broken tail."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        text = raw[:error.start].decode("utf-8")
        unicode_error = True
    else:
        unicode_error = False
    decoder = json.JSONDecoder(parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    index, values = 0, []
    while index < len(text) and text[index].isspace():
        index += 1
    if index == len(text) or text[index] != "[":
        return [], False
    index += 1
    need_value = False
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == "]":
            return values, not need_value and not unicode_error and not text[index + 1:].strip()
        try:
            item, end = decoder.raw_decode(text, index)
            item = _finite_json_copy(item)
        except (json.JSONDecodeError, ValueError):
            return values, False
        values.append(item)
        index = end
        while index < len(text) and text[index].isspace():
            index += 1
        if index < len(text) and text[index] == ",":
            index += 1
            need_value = True
        elif index < len(text) and text[index] == "]":
            return values, not unicode_error and not text[index + 1:].strip()
        else:
            return values, False


def parse_region_set(content: bytes | BinaryIO | None, *,
                     specification: RegionSetSpec, set_position: int) -> ParsedRegionSet:
    """Normalize supplied bytes; preserve invalid occurrences and source locations."""
    spec = _specification(specification)
    if type(set_position) is not int or set_position < 0:
        raise ValueError("genomic_overlap_set_position")
    source, set_key = spec["source"]["file"], spec["set_key"]
    result = {"version": "genomic_overlap_parsed_set_v1", "set_key": set_key,
              "source_file": deepcopy(source), "parsed_byte_count": 0,
              "result_extent": "unavailable", "input_data_row_count": None,
              "regions": [], "ignored_records": [], "invalid_records": [],
              "canonical_order": [], "coordinate_groups": [], "full_record_groups": [], "issues": []}
    raw, read_failed = _read_supplied(content)
    def issue(code, **kwargs):
        return _failure(code, "input", set_key=set_key, artifact_ref=source["artifact_ref"],
                        partial_artifact_refs=[source["artifact_ref"]] if raw is not None else [], **kwargs)
    if raw is None:
        result["issues"].append(issue("input_unavailable", requirement="complete_input"))
        return result
    if len(raw) > source["size_bytes"]:
        # No honest parsed-byte count can exceed this declared source. Retain its
        # identity/failure; do not silently trim the foreign supplied bytes.
        result["issues"].append(issue("input_digest_mismatch", field_path="/source_file/size_bytes",
            expected_value=source["size_bytes"], observed_value=len(raw), requirement="matching_file_identity"))
        return result
    result["parsed_byte_count"] = len(raw)
    full_bytes = len(raw) == source["size_bytes"] and not read_failed
    identity_ok = full_bytes and hashlib.sha256(raw).hexdigest() == source["sha256"]
    if not identity_ok:
        result["issues"].append(issue("input_digest_mismatch", field_path="/source_file/sha256",
            expected_value=source["sha256"], observed_value=hashlib.sha256(raw).hexdigest(),
            requirement="matching_file_identity"))
    if read_failed or not full_bytes:
        result["issues"].append(issue("input_unavailable", field_path="/parsed_byte_count",
            expected_value=source["size_bytes"], observed_value=len(raw), requirement="complete_input"))
    ordinal = 0
    def add(fields, locator, extra_errors=()):
        nonlocal ordinal
        errors, coordinates = _row_values(fields, textual=spec["format"] == "bed_outer_span_v1")
        errors = list(extra_errors) + errors
        if errors:
            issues = [issue(code, locator=locator, field_path=path, expected_value=expected,
                            observed_value=observed, requirement="valid_coordinates" if code in
                            {"invalid_coordinate", "zero_width_interval", "invalid_chromosome_token"}
                            else "complete_input") for code, path, expected, observed in errors]
            result["invalid_records"].append({"data_ordinal": ordinal, "locator": locator,
                "original_fields": deepcopy(fields) if type(fields) is list else None, "issues": issues})
            result["issues"].extend(issues)
        else:
            chrom, start, end = coordinates
            result["regions"].append({"occurrence_key": f"r{ordinal}", "data_ordinal": ordinal,
                "native_token": f"s{set_position}_r{ordinal}", "locator": locator,
                "original_fields": deepcopy(fields), "chromosome": chrom, "start": start, "end": end,
                "name": _optional_text(fields, 3), "raw_strand": _optional_text(fields, 5)})
        ordinal += 1
    syntax_complete = True
    if spec["format"] == "bed_outer_span_v1":
        for line, locator, terminated in _lines(raw):
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError:
                add(None, locator, [("unsupported_input_format", "/original_fields", None, list(line))])
                continue
            if not full_bytes and not terminated:
                add(text.split("\t"), locator, [("input_unavailable", "/original_fields", None, text)])
                continue
            stripped = text.strip()
            if not stripped:
                kind = "blank"
            elif stripped.startswith("#"):
                kind = "comment"
            elif re.match(r"^track(?:\s|$)", stripped):
                kind = "track_header"
            elif re.match(r"^browser(?:\s|$)", stripped):
                kind = "browser_header"
            else:
                add(text.split("\t"), locator)
                continue
            result["ignored_records"].append({"locator": locator, "kind": kind})
    else:
        rows, syntax_complete = _decode_rows(raw)
        for index, row in enumerate(rows):
            add(row, {"kind": "array_index", "index": index})
        if not syntax_complete:
            add(None, {"kind": "array_index", "index": len(rows)},
                [("unsupported_input_format", "/original_fields", None, None)])
    result["input_data_row_count"] = ordinal if full_bytes and syntax_complete else None
    result["result_extent"] = "complete" if identity_ok and syntax_complete and not result["invalid_records"] else "partial"
    result["canonical_order"] = [row["occurrence_key"] for row in sorted(result["regions"],
        key=lambda row: (row["chromosome"].encode("utf-8"), row["start"], row["end"], row["data_ordinal"]))]
    result["coordinate_groups"], result["full_record_groups"] = _groups(set_key, result["regions"])
    return validate_genomic_overlap_record("ParsedRegionSet", result)


def _validate_set(value, *, specification=None, set_position=None):
    parsed = validate_genomic_overlap_record("ParsedRegionSet", value)
    key, rows = parsed["set_key"], parsed["regions"]
    if specification is not None and (key != specification["set_key"] or
            parsed["source_file"] != specification["source"]["file"]):
        raise ValueError("genomic_overlap_set_source_identity")
    if parsed["parsed_byte_count"] > parsed["source_file"]["size_bytes"]:
        raise ValueError("genomic_overlap_parsed_byte_count")
    ordinals, keys, tokens = [], set(), set()
    for row in rows:
        ordinal = row["data_ordinal"]
        if (row["occurrence_key"] != f"r{ordinal}" or row["occurrence_key"] in keys or
                row["native_token"] in tokens or not re.fullmatch(r"s(?:0|[1-9][0-9]*)_r" + str(ordinal), row["native_token"])):
            raise ValueError("genomic_overlap_occurrence_identity")
        if set_position is not None and row["native_token"] != f"s{set_position}_r{ordinal}":
            raise ValueError("genomic_overlap_native_token_position")
        textual = parsed["source_file"]["format"] == "bed_outer_span_v1"
        errors, coordinates = _row_values(row["original_fields"], textual=textual)
        if errors or coordinates != (row["chromosome"], row["start"], row["end"]):
            raise ValueError("genomic_overlap_original_coordinate_correspondence")
        if row["name"] != _optional_text(row["original_fields"], 3) or row["raw_strand"] != _optional_text(row["original_fields"], 5):
            raise ValueError("genomic_overlap_original_optional_correspondence")
        keys.add(row["occurrence_key"]); tokens.add(row["native_token"]); ordinals.append(ordinal)
    if ordinals != sorted(ordinals):
        raise ValueError("genomic_overlap_original_row_order")
    all_ordinals = ordinals + [row["data_ordinal"] for row in parsed["invalid_records"]]
    if len(set(all_ordinals)) != len(all_ordinals) or sorted(all_ordinals) != list(range(len(all_ordinals))):
        raise ValueError("genomic_overlap_data_ordinals")
    if parsed["input_data_row_count"] is not None and parsed["input_data_row_count"] != len(all_ordinals):
        raise ValueError("genomic_overlap_input_row_count")
    if parsed["input_data_row_count"] is not None and parsed["parsed_byte_count"] != parsed["source_file"]["size_bytes"]:
        raise ValueError("genomic_overlap_truncated_input_row_count")
    if parsed["result_extent"] == "complete" and (parsed["invalid_records"] or
            parsed["parsed_byte_count"] != parsed["source_file"]["size_bytes"] or
            parsed["input_data_row_count"] is None or parsed["issues"]):
        raise ValueError("genomic_overlap_incomplete_set_claimed_complete")
    if parsed["result_extent"] == "unavailable" and (parsed["parsed_byte_count"] or rows or
            parsed["ignored_records"] or parsed["invalid_records"] or parsed["input_data_row_count"] is not None):
        raise ValueError("genomic_overlap_unavailable_set_contents")
    expected_order = [row["occurrence_key"] for row in sorted(rows,
        key=lambda row: (row["chromosome"].encode("utf-8"), row["start"], row["end"], row["data_ordinal"]))]
    if parsed["canonical_order"] != expected_order:
        raise ValueError("genomic_overlap_canonical_order")
    for name, expected in zip(("coordinate_groups", "full_record_groups"), _groups(key, rows)):
        actual = parsed[name]
        if len({row["group_key"] for row in actual}) != len(actual) or len(actual) != len(expected):
            raise ValueError("genomic_overlap_duplicate_groups")
        if [{k: v for k, v in row.items() if k != "group_key"} for row in actual] != [
                {k: v for k, v in row.items() if k != "group_key"} for row in expected]:
            raise ValueError("genomic_overlap_duplicate_group_membership")
    if parsed["source_file"]["format"] == "coordinate_rows_v1" and parsed["ignored_records"]:
        raise ValueError("genomic_overlap_coordinate_rows_have_no_bed_headers")
    for row in rows + parsed["invalid_records"] + parsed["ignored_records"]:
        locator = row["locator"]
        if parsed["source_file"]["format"] == "bed_outer_span_v1":
            if locator["kind"] != "bed_line" or not 0 <= locator["byte_start"] < locator["byte_end"] <= parsed["parsed_byte_count"]:
                raise ValueError("genomic_overlap_input_locator")
        elif parsed["source_file"]["format"] == "coordinate_rows_v1":
            if locator["kind"] != "array_index" or locator["index"] != row["data_ordinal"]:
                raise ValueError("genomic_overlap_input_locator")
        else:
            raise ValueError("genomic_overlap_source_format")
    if parsed["source_file"]["format"] == "bed_outer_span_v1":
        _validate_line_locations(rows + parsed["invalid_records"] + parsed["ignored_records"], parsed["parsed_byte_count"])
    return parsed


def _validate_comparisons(specifications, comparisons):
    keys = [spec["set_key"] for spec in specifications]
    if len(keys) != len(set(keys)):
        raise ValueError("genomic_overlap_duplicate_set_key")
    expected = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
    if len(comparisons) != len(expected) or len({p["comparison_key"] for p in comparisons}) != len(comparisons):
        raise ValueError("genomic_overlap_comparison_population")
    for ordinal, (pair, endpoints) in enumerate(zip(comparisons, expected)):
        if (pair["a_set_key"], pair["b_set_key"]) != endpoints or pair["ordinal"] != ordinal:
            raise ValueError("genomic_overlap_comparison_order")


def _reference_issues(spec, parsed, pair_key):
    reference = spec["reference"]
    if reference is None:
        return [], {}
    indexed, issues = {}, []
    def conflict(path, expected, observed, locator=None):
        issues.append(_failure("reference_metadata_conflict", "input", set_key=spec["set_key"],
            comparison_key=pair_key, artifact_ref=spec["source"]["file"]["artifact_ref"], locator=locator,
            field_path=path, expected_value=expected, observed_value=observed,
            requirement="requested_reference_metadata"))
    for i, contig in enumerate(reference["contigs"]):
        chrom = contig["chromosome"]
        if not _chromosome(chrom):
            conflict(f"/reference/contigs/{i}/chromosome", None, chrom)
        previous = indexed.get(chrom)
        if previous:
            for field in ("length_bp", "sequence_accession_version", "sequence_sha256"):
                if previous[field] is not None and contig[field] is not None and previous[field] != contig[field]:
                    conflict(f"/reference/contigs/{i}/{field}", previous[field], contig[field])
            indexed[chrom] = {field: previous[field] if previous[field] is not None else contig[field]
                              for field in ("length_bp", "sequence_accession_version", "sequence_sha256")}
        else:
            indexed[chrom] = contig
    for row in parsed["regions"]:
        contig = indexed.get(row["chromosome"])
        if contig and contig["length_bp"] is not None and row["end"] > contig["length_bp"]:
            conflict("/end", contig["length_bp"], row["end"], row["locator"])
    return issues, indexed


def extract_overlap_reference_metadata(*, specifications: Sequence[RegionSetSpec],
    sets: Mapping[str, ParsedRegionSet], comparisons: Sequence[ComparisonSpec]) -> list[ReferenceRelation]:
    """Qualify coordinate geometry using supplied reference assertions only."""
    specs = [_specification(spec) for spec in specifications]
    pairs = [validate_genomic_overlap_record("ComparisonSpec", pair) for pair in comparisons]
    _validate_comparisons(specs, pairs)
    if set(sets) != {spec["set_key"] for spec in specs}:
        raise ValueError("genomic_overlap_reference_set_keys")
    parsed = {spec["set_key"]: _validate_set(sets[spec["set_key"]], specification=spec, set_position=i)
              for i, spec in enumerate(specs)}
    by_key = {spec["set_key"]: spec for spec in specs}
    results = []
    for pair in pairs:
        a, b = (by_key[pair[side + "_set_key"]] for side in ("a", "b"))
        ai, ac = _reference_issues(a, parsed[a["set_key"]], pair["comparison_key"])
        bi, bc = _reference_issues(b, parsed[b["set_key"]], pair["comparison_key"])
        issues = ai + bi
        ar, br = a["reference"], b["reference"]
        av = ar["assembly_accession_version"] if ar else None
        bv = br["assembly_accession_version"] if br else None
        relation, basis = "unknown", "insufficient_supplied_identity"
        different = av is not None and bv is not None and av != bv
        if different:
            relation, basis = "different_supplied_references", "contradictory_supplied_identity"
            issues.append(_failure("reference_metadata_conflict", "input", comparison_key=pair["comparison_key"],
                field_path="/assembly_accession_version", expected_value=av, observed_value=bv,
                requirement="requested_reference_metadata"))
        if not different:
            for chromosome in sorted(ac.keys() & bc.keys(), key=lambda s: s.encode("utf-8")):
                for field in ("length_bp", "sequence_accession_version", "sequence_sha256"):
                    left, right = ac[chromosome][field], bc[chromosome][field]
                    if left is not None and right is not None and left != right:
                        issues.append(_failure("reference_metadata_conflict", "input",
                            comparison_key=pair["comparison_key"], field_path="/contigs/" + field,
                            expected_value=left, observed_value=right, requirement="requested_reference_metadata"))
            if av is not None and av == bv:
                relation, basis = "same_supplied_reference", "supplied_versioned_reference_identity"
            else:
                relevant = {row["chromosome"] for spec in (a, b) for row in parsed[spec["set_key"]]["regions"]}
                if relevant and all(chrom in ac and chrom in bc and any(ac[chrom][f] is not None and
                        ac[chrom][f] == bc[chrom][f] for f in ("sequence_accession_version", "sequence_sha256"))
                        for chrom in relevant):
                    relation, basis = "same_supplied_reference", "supplied_contig_sequence_identity"
        if ai or bi or (issues and not different):
            relation, basis = "conflicting_metadata", "contradictory_supplied_identity"
        results.append({"comparison_key": pair["comparison_key"], "a_set_key": a["set_key"],
            "b_set_key": b["set_key"], "relation": relation, "basis": basis,
            "a_reference": deepcopy(ar), "b_reference": deepcopy(br), "issues": issues})
    return results


def _native_binding(pair, sets, native):
    if pair["a_set_key"] == pair["b_set_key"] or native["comparison_key"] != pair["comparison_key"]:
        raise ValueError("genomic_overlap_native_comparison_binding")
    for side in ("a", "b"):
        key = pair[side + "_set_key"]
        if key not in sets or native[side]["set_key"] != key or native[side]["original_file"] != sets[key]["source_file"]:
            raise ValueError("genomic_overlap_native_source_binding")
        canonical = native[side]["canonical_file"]
        if canonical is not None and canonical["format"] != "bed4_occurrence_v1":
            raise ValueError("genomic_overlap_canonical_format")
    for name, expected in (("stdout", "bedtools_intersect_wo_bed4_v1"), ("stderr", "native_stderr_text_v1")):
        if native[name] is not None and native[name]["format"] != expected:
            raise ValueError("genomic_overlap_native_format")
    if native["derivation"] in {"validated_empty_input", "not_executed_invalid_input"}:
        if native["outcome"] != "not_executed" or native["realized_argv"] or any(native[k] is not None
                for k in ("returncode", "started_at", "finished_at", "software", "stdout", "stderr")):
            raise ValueError("genomic_overlap_uninvoked_native_facts")
        operands = [sets[pair[side + "_set_key"]] for side in ("a", "b")]
        complete = all(operand["result_extent"] == "complete" for operand in operands)
        if native["derivation"] == "validated_empty_input":
            if native["native_result_extent"] != "complete" or native["completeness_basis"] != "validated_empty_input":
                raise ValueError("genomic_overlap_analytic_extent")
            if complete:
                if not any(not operand["regions"] for operand in operands):
                    raise ValueError("genomic_overlap_invalid_analytic_empty")
                if native["capture_extent"] != "complete":
                    raise ValueError("genomic_overlap_analytic_capture_extent")
            else:
                # Original analytic derivation and current input availability
                # are separate facts. Lost maps cannot prove a current zero,
                # and available malformed/partial maps cannot be called lost.
                if native["capture_extent"] != "unavailable" or any(
                        operand["result_extent"] not in {"complete", "unavailable"} for operand in operands):
                    raise ValueError("genomic_overlap_invalid_analytic_empty")
                if native["environment"]:
                    raise ValueError("genomic_overlap_uninvoked_native_facts")
                for operand in operands:
                    if operand["result_extent"] != "unavailable":
                        continue
                    if not any(issue["set_key"] == operand["set_key"]
                            and issue["comparison_key"] in (None, pair["comparison_key"])
                            and issue["stage"] in {"input", "capture"}
                            and (issue["code"], issue["requirement"]) in {
                                ("input_unavailable", "complete_input"),
                                ("input_digest_mismatch", "matching_file_identity"),
                                ("artifact_digest_mismatch", "matching_file_identity"),
                                ("native_output_unavailable", "complete_input")}
                            for issue in operand["issues"] + native["issues"]):
                        raise ValueError("genomic_overlap_analytic_input_failure")
        elif complete or native["native_result_extent"] != "unavailable" or native["completeness_basis"] != "unavailable":
            raise ValueError("genomic_overlap_invalid_unexecuted_pair")


def _native_complete(native):
    common = native["capture_extent"] == "complete" and native["native_result_extent"] == "complete"
    if native["derivation"] == "validated_empty_input":
        return common and native["completeness_basis"] == "validated_empty_input"
    if native["completeness_basis"] == "closed_successful_native_attempt":
        return (common and native["derivation"] == "bedtools_intersect" and native["outcome"] == "succeeded"
                and native["returncode"] == 0 and native["writer_closed"] is True)
    return (common and native["derivation"] == "supplied_native_output" and
            native["completeness_basis"] == "supplied_full_output_declaration" and
            bool(native["completeness_source_refs"]) and native["returncode"] in (None, 0)
            and native["outcome"] in {"unknown", "succeeded"} and native["writer_closed"] is not False)


def _compatible_supplied_argv(argv):
    """Small declared intersect grammar; no execution or executable discovery."""
    if not argv:
        return True  # Explicit supplied completeness may have unknown invocation.
    if argv[0].rsplit("/", 1)[-1] == "intersectBed":
        options = argv[1:]
    elif len(argv) >= 2 and argv[1] == "intersect":
        options = argv[2:]
    else:
        return False
    seen, index = set(), 0
    while index < len(options):
        flag = options[index]
        if flag not in {"-a", "-b", "-wo", "-sorted"} or flag in seen:
            return False
        seen.add(flag)
        index += 1
        if flag in {"-a", "-b"}:
            if index == len(options) or options[index].startswith("-") and options[index] != "-":
                return False
            index += 1
    return {"-a", "-b", "-wo"}.issubset(seen)


def _canonical_mismatches(native, operands):
    for side, operand in zip(("a", "b"), operands):
        canonical = native[side]["canonical_file"]
        if canonical is None:
            continue
        by_key = {row["occurrence_key"]: row for row in operand["regions"]}
        digest, size = hashlib.sha256(), 0
        for occurrence in operand["canonical_order"]:
            row = by_key[occurrence]
            line = (f"{row['chromosome']}\t{row['start']}\t{row['end']}\t{row['native_token']}\n").encode("utf-8")
            digest.update(line)
            size += len(line)
        for field, expected in (("sha256", digest.hexdigest()), ("size_bytes", size)):
            if canonical[field] != expected:
                yield side, operand["set_key"], field, expected, canonical[field]


def parse_bedtools_intersect_wo(content: bytes | BinaryIO | None, *, pair: ComparisonSpec,
    sets: Mapping[str, ParsedRegionSet], native: NativePairReceipt) -> ParsedOverlapPairs:
    """Read exact BED4/BED4/width rows; reject foreign or repeated occurrence pairs."""
    pair = validate_genomic_overlap_record("ComparisonSpec", pair)
    native = validate_genomic_overlap_record("NativePairReceipt", native)
    sets = {key: _validate_set(value) for key, value in sets.items()}
    if any(key != value["set_key"] for key, value in sets.items()):
        raise ValueError("genomic_overlap_set_mapping")
    _native_binding(pair, sets, native)
    result = {"version": "genomic_overlap_parsed_pairs_v1", "format": "bedtools_intersect_wo_bed4_v1",
              "comparison_key": pair["comparison_key"], "receipt": native, "result_extent": "unavailable",
              "parsed_byte_count": 0, "valid_pairs": [], "rejected_rows": [], "issues": []}
    if native["derivation"] == "validated_empty_input" and native["capture_extent"] == "unavailable":
        if content is not None:
            raise ValueError("genomic_overlap_analytic_native_bytes")
        return result
    raw, read_failed = _read_supplied(content)
    source = native["stdout"]
    def issue(code, **kwargs):
        return _failure(code, "parse", comparison_key=pair["comparison_key"],
            artifact_ref=source["artifact_ref"] if source else None,
            partial_artifact_refs=[source["artifact_ref"]] if source and raw is not None else [], **kwargs)
    if not _compatible_supplied_argv(native["realized_argv"]):
        result["issues"].append(issue("unsupported_input_format", field_path="/receipt/realized_argv",
            expected_value="unstranded_outer_span", observed_value=native["realized_argv"],
            requirement="complete_native_output"))
    if native["derivation"] == "validated_empty_input":
        if raw not in (None, b""):
            raise ValueError("genomic_overlap_analytic_native_bytes")
        result["result_extent"] = "complete"
        return result
    if native["derivation"] == "not_executed_invalid_input" and raw is not None:
        raise ValueError("genomic_overlap_uninvoked_native_bytes")
    if raw is None or source is None:
        result["issues"].append(issue("native_output_unavailable", requirement="original_native_output"))
        return result
    if len(raw) > source["size_bytes"]:
        result["issues"].append(issue("artifact_digest_mismatch", field_path="/stdout/size_bytes",
            expected_value=source["size_bytes"], observed_value=len(raw), requirement="matching_file_identity"))
        return result
    result["parsed_byte_count"] = len(raw)
    full_bytes = len(raw) == source["size_bytes"] and not read_failed
    if not full_bytes or hashlib.sha256(raw).hexdigest() != source["sha256"]:
        result["issues"].append(issue("artifact_digest_mismatch", field_path="/stdout/sha256",
            expected_value=source["sha256"], observed_value=hashlib.sha256(raw).hexdigest(), requirement="matching_file_identity"))
    if native["returncode"] not in (None, 0):
        result["issues"].append(issue("native_nonzero_exit", field_path="/receipt/returncode",
            expected_value=0, observed_value=native["returncode"], requirement="complete_native_output"))
    if not _native_complete(native) or read_failed:
        result["issues"].append(issue("native_output_partial", requirement="complete_native_output"))
    operands = [sets[pair[side + "_set_key"]] for side in ("a", "b")]
    for operand in operands:
        if operand["result_extent"] != "complete":
            result["issues"].append(issue("input_unavailable", set_key=operand["set_key"], requirement="complete_input"))
    for side, set_key, field, expected, observed in _canonical_mismatches(native, operands):
        result["issues"].append(issue("artifact_digest_mismatch", set_key=set_key,
            field_path=f"/receipt/{side}/canonical_file/{field}",
            expected_value=expected, observed_value=observed, requirement="matching_file_identity"))
    indexes = [{row["native_token"]: row for row in operand["regions"]} for operand in operands]
    seen = set()
    for ordinal, (line, locator, terminated) in enumerate(_lines(raw)):
        errors, resolved = [], []
        def reject(code, **kwargs):
            errors.append(issue(code, locator=locator, requirement="complete_native_output", **kwargs))
        try:
            fields = line.decode("utf-8").split("\t")
        except UnicodeDecodeError:
            fields = []
            reject("native_output_malformed", observed_value=list(line))
        if len(fields) != 9:
            reject("native_output_malformed", field_path="/column_count", expected_value=9, observed_value=len(fields))
        elif not full_bytes and not terminated:
            reject("native_output_partial", observed_value=fields)
        else:
            for side_index, side in enumerate(("a", "b")):
                offset = 4 * side_index
                chrom, start_text, end_text, token = fields[offset:offset + 4]
                original = indexes[side_index].get(token)
                start, end = _coordinate(start_text, textual=True), _coordinate(end_text, textual=True)
                if original is None:
                    reject("native_pair_identity_conflict", field_path=f"/{side}/native_token", observed_value=token)
                elif (chrom, start, end) != (original["chromosome"], original["start"], original["end"]):
                    reject("native_pair_identity_conflict", field_path=f"/{side}",
                        expected_value=[original["chromosome"], original["start"], original["end"]],
                        observed_value=fields[offset:offset + 3])
                resolved.append(original)
            width = _coordinate(fields[8], textual=True)
            if width is None:
                reject("native_output_malformed", field_path="/native_overlap_bp", observed_value=fields[8])
            if all(row is not None for row in resolved):
                a, b = resolved
                geometric = min(a["end"], b["end"]) - max(a["start"], b["start"])
                if a["chromosome"] != b["chromosome"] or geometric <= 0 or width != geometric:
                    reject("overlap_width_conflict", field_path="/native_overlap_bp", expected_value=max(0, geometric)
                           if a["chromosome"] == b["chromosome"] else 0, observed_value=width if width is not None else fields[8])
                identity = (a["occurrence_key"], b["occurrence_key"])
                if identity in seen:
                    reject("duplicate_native_pair", field_path="/pair_key", observed_value=list(identity))
        if errors:
            result["rejected_rows"].append({"native_row_ordinal": ordinal, "locator": locator, "issues": errors})
            result["issues"].extend(errors)
            continue
        a, b = resolved
        seen.add((a["occurrence_key"], b["occurrence_key"]))
        endpoints = [{"set_key": operand["set_key"], **{key: row[key] for key in
                      ("occurrence_key", "native_token", "chromosome", "start", "end")}}
                     for operand, row in zip(operands, resolved)]
        result["valid_pairs"].append({"pair_key": f"p{pair['ordinal']}:a{a['data_ordinal']}:b{b['data_ordinal']}",
            "comparison_key": pair["comparison_key"], "native_row_ordinal": ordinal, "locator": locator,
            "a": endpoints[0], "b": endpoints[1], "native_overlap_bp": width})
    result["result_extent"] = "complete" if not result["issues"] and not native["issues"] else "partial"
    return validate_genomic_overlap_record("ParsedOverlapPairs", result)


def _validate_pairs(value, pair, sets):
    parsed = validate_genomic_overlap_record("ParsedOverlapPairs", value)
    native = parsed["receipt"]
    if parsed["comparison_key"] != pair["comparison_key"]:
        raise ValueError("genomic_overlap_parsed_comparison_key")
    _native_binding(pair, sets, native)
    if not _compatible_supplied_argv(native["realized_argv"]) and not any(
            issue["code"] == "unsupported_input_format" and issue["stage"] == "parse"
            and issue["field_path"] == "/receipt/realized_argv"
            and issue["expected_value"] == "unstranded_outer_span"
            and issue["observed_value"] == native["realized_argv"] for issue in parsed["issues"]):
        raise ValueError("genomic_overlap_incompatible_supplied_invocation")
    seen, ordinals = set(), []
    indices = {side: {r["occurrence_key"]: r for r in sets[pair[side + "_set_key"]]["regions"]} for side in ("a", "b")}
    for row in parsed["valid_pairs"]:
        originals = []
        for side in ("a", "b"):
            endpoint = row[side]
            original = indices[side].get(endpoint["occurrence_key"])
            expected = {"set_key": pair[side + "_set_key"], **{key: original[key] for key in
                        ("occurrence_key", "native_token", "chromosome", "start", "end")}} if original else None
            if endpoint != expected:
                raise ValueError("genomic_overlap_pair_endpoint_correspondence")
            originals.append(original)
        a, b = originals
        key = f"p{pair['ordinal']}:a{a['data_ordinal']}:b{b['data_ordinal']}"
        if row["comparison_key"] != pair["comparison_key"] or row["pair_key"] != key or key in seen:
            raise ValueError("genomic_overlap_pair_identity")
        if a["chromosome"] != b["chromosome"] or row["native_overlap_bp"] != min(a["end"], b["end"]) - max(a["start"], b["start"]):
            raise ValueError("genomic_overlap_pair_width")
        seen.add(key); ordinals.append(row["native_row_ordinal"])
    if ordinals != sorted(ordinals):
        raise ValueError("genomic_overlap_native_row_order")
    all_ordinals = ordinals + [row["native_row_ordinal"] for row in parsed["rejected_rows"]]
    if len(set(all_ordinals)) != len(all_ordinals) or sorted(all_ordinals) != list(range(len(all_ordinals))):
        raise ValueError("genomic_overlap_native_row_ordinals")
    source = native["stdout"]
    if source is None and parsed["parsed_byte_count"] or source is not None and parsed["parsed_byte_count"] > source["size_bytes"]:
        raise ValueError("genomic_overlap_native_parsed_bytes")
    for row in parsed["valid_pairs"] + parsed["rejected_rows"]:
        loc = row["locator"]
        if loc["kind"] != "bed_line" or not 0 <= loc["byte_start"] < loc["byte_end"] <= parsed["parsed_byte_count"]:
            raise ValueError("genomic_overlap_native_locator")
    _validate_line_locations(parsed["valid_pairs"] + parsed["rejected_rows"], parsed["parsed_byte_count"])
    if parsed["valid_pairs"] or parsed["result_extent"] == "complete" and native["derivation"] != "validated_empty_input":
        operands = [sets[pair[side + "_set_key"]] for side in ("a", "b")]
        for side, set_key, field, expected, observed in _canonical_mismatches(native, operands):
            if not any(issue["code"] == "artifact_digest_mismatch" and issue["set_key"] == set_key
                    and issue["field_path"] == f"/receipt/{side}/canonical_file/{field}"
                    and issue["expected_value"] == expected and issue["observed_value"] == observed
                    for issue in parsed["issues"]):
                raise ValueError("genomic_overlap_canonical_file_identity")
    if parsed["result_extent"] == "complete":
        if (parsed["rejected_rows"] or parsed["issues"] or native["issues"] or not _native_complete(native)
                or any(sets[pair[side + "_set_key"]]["result_extent"] != "complete" for side in ("a", "b"))):
            raise ValueError("genomic_overlap_incomplete_pair_claimed_complete")
        if native["derivation"] != "validated_empty_input" and (source is None or parsed["parsed_byte_count"] != source["size_bytes"]):
            raise ValueError("genomic_overlap_complete_native_bytes")
    if parsed["result_extent"] == "unavailable" and (parsed["parsed_byte_count"] or parsed["valid_pairs"] or parsed["rejected_rows"]):
        raise ValueError("genomic_overlap_unavailable_pair_contents")
    if native["derivation"] == "validated_empty_input" and (parsed["valid_pairs"] or parsed["rejected_rows"] or parsed["parsed_byte_count"]):
        raise ValueError("genomic_overlap_analytic_pairs")
    if native["derivation"] == "validated_empty_input" and parsed["result_extent"] != (
            "complete" if _native_complete(native) else "unavailable"):
        raise ValueError("genomic_overlap_analytic_pair_extent")
    return parsed


def build_genomic_overlap_sheet(*, request: Request, sets: Sequence[ParsedRegionSet],
    native_pairs: Sequence[ParsedOverlapPairs], reference_relations: Sequence[ReferenceRelation]) -> Sheet:
    """Validate ordered joins and retain complete and qualified partial records."""
    request = validate_genomic_overlap_record("Request", request)
    specs = [_specification(spec) for spec in request["region_sets"]]
    comparisons = request["comparisons"]
    _validate_comparisons(specs, comparisons)
    if len(sets) != len(specs):
        raise ValueError("genomic_overlap_sheet_set_count")
    parsed_sets = [_validate_set(value, specification=spec, set_position=i)
                   for i, (spec, value) in enumerate(zip(specs, sets))]
    by_key = {value["set_key"]: value for value in parsed_sets}
    if len(native_pairs) != len(comparisons):
        raise ValueError("genomic_overlap_sheet_pair_count")
    pairs = [_validate_pairs(value, pair, by_key) for value, pair in zip(native_pairs, comparisons)]
    references = [validate_genomic_overlap_record("ReferenceRelation", value) for value in reference_relations]
    expected = extract_overlap_reference_metadata(specifications=specs, sets=by_key, comparisons=comparisons)
    if references != expected:
        raise ValueError("genomic_overlap_reference_relations")
    issues = _unique_issues(*(row["issues"] for row in parsed_sets),
        *(row["receipt"]["issues"] for row in pairs), *(row["issues"] for row in pairs),
        *(row["issues"] for row in references))
    result = {"version": "genomic_region_overlap_sheet_v1", "request": request,
              "sets": parsed_sets, "comparisons": pairs, "reference_relations": references, "issues": issues}
    return validate_genomic_overlap_record("Sheet", result)


def _validate_sheet(sheet):
    checked = validate_genomic_overlap_record("Sheet", sheet)
    rebuilt = build_genomic_overlap_sheet(request=checked["request"], sets=checked["sets"],
        native_pairs=checked["comparisons"], reference_relations=checked["reference_relations"])
    if checked != rebuilt:
        raise ValueError("genomic_overlap_sheet_issue_provenance")
    return rebuilt


__all__ = ["parse_region_set", "extract_overlap_reference_metadata",
           "parse_bedtools_intersect_wo", "build_genomic_overlap_sheet"]
