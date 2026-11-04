"""Pure HMMER Stockholm readers and the hmmalign numerical sheet builder.

Streaming interfaces accept a str or an iterable of complete text lines:
  iter_hmmalign_stockholm_events(stream, *, artifact_ref)
  iter_hmmalign_stockholm_records(stream, *, artifact_ref, engine_version)
  iter_hmmalign_stockholm_rows(stream, *, artifact_ref, engine_version)
Events use constant auxiliary space; assembled interleaved rows require buffering
one alignment record. Locators are 1-based lines and 0-based half-open UTF-8 byte
intervals in the supplied stream, never filesystem offsets obtained by I/O.

Duplicate names have 0-based occurrences in each alignment block. Equal block
multiplicities preserve those occurrences; unequal multiplicities are ambiguous
and are never used to join metadata. All original lines and annotations survive.

``inputs.sequences[].occurrence`` refers to the output name occurrence (not an
index in a filtered input list). Optional alignment_index disambiguates multiple
Stockholm records. ``inputs.mapali`` accepts artifact_ref and actual stockholm
text. ``profile.map`` is the native M-element list of 1-based seed columns;
checksum is the uint32 HMM CKSUM. Claiming compatibility without actual seed
symbols cannot establish it. All additional supplied metadata is retained.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from io import StringIO
import json
import re


NATIVE_SCHEMA = "hmmalign_native_v1"
SHEET_SCHEMA = "hmmalign_sheet_v1"
_GAPS = "-._"
_SEQUENCE = re.compile(r"[A-Za-z.*_~\-]+")
_ALPHABETS = {"amino": "ACDEFGHIKLMNPQRSTVWY-BJZOUX*~",
              "dna": "ACGT-RYMKSWHBVDN*~", "rna": "ACGU-RYMKSWHBVDN*~"}


def require_finite_json(value, code):
    def check(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError(code)
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError(code)
    try:
        check(value)
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(code) from error


def _identity(value, code):
    if value is not None and (type(value) is not str or not value):
        raise ValueError(code)


def _issue(code, **context):
    return {"code": code, **context}


def iter_hmmalign_stockholm_events(stream, *, artifact_ref):
    """Yield every supplied line once, retaining exact text and byte locations."""
    _identity(artifact_ref, "hmmalign_artifact_ref_invalid")
    if type(stream) is str:
        stream = StringIO(stream)
    elif isinstance(stream, (dict, bytes)) or stream is None:
        raise ValueError("hmmalign_text_stream_required")
    try:
        iterator = iter(stream)
    except TypeError as error:
        raise ValueError("hmmalign_text_stream_required") from error
    offset = 0
    for line_number, raw in enumerate(iterator, 1):
        if type(raw) is not str:
            raise ValueError("hmmalign_stream_complete_text_lines_required")
        text = raw.removesuffix("\n").removesuffix("\r")
        if "\n" in text or "\r" in text:
            raise ValueError("hmmalign_stream_complete_text_lines_required")
        try:
            size = len(raw.encode("utf-8"))
        except UnicodeError as error:
            raise ValueError("hmmalign_text_encoding_invalid") from error
        event = {"raw": raw, "locator": {"artifact_role": "stockholm", "artifact_ref": artifact_ref,
                 "line": line_number, "byte_start": offset, "byte_end": offset+size}}
        offset += size
        if not text.strip():
            event["kind"] = "blank"
        elif text.startswith("# STOCKHOLM"):
            event.update(kind="header", version=text.removeprefix("# STOCKHOLM").strip())
        elif text.strip() == "//":
            event["kind"] = "terminator"
        elif text.startswith(("#=GF", "#=GS", "#=GC", "#=GR")):
            parts = text.split(None, 3 if text.startswith(("#=GS", "#=GR")) else 2)
            kind = text[2:4]
            event["kind"] = kind
            expected = 4 if kind in {"GS", "GR"} else 3
            if len(parts) != expected or (kind in {"GC", "GR"} and any(c.isspace() for c in parts[-1])):
                event["kind"] = "malformed_annotation"
            else:
                event.update(tag=parts[-2], value=parts[-1])
                if kind in {"GS", "GR"}:
                    event["name"] = parts[1]
        elif text.startswith("#"):
            event["kind"] = "comment"
        else:
            parts = text.split()
            if len(parts) == 2:
                event.update(kind="sequence", name=parts[0], value=parts[1])
            else:
                event["kind"] = "malformed_sequence"
        yield event


def _column_annotations(events, block_count, widths, issues, *, row_key=None):
    by_tag = defaultdict(list)
    for event in events:
        by_tag[event["tag"]].append(event)
    annotations = {}
    for tag, pieces in by_tag.items():
        counts = Counter(p["block_index"] for p in pieces)
        valid = (set(counts) == set(range(block_count)) and all(n == 1 for n in counts.values())
                 and all(widths.get(p["block_index"]) == len(p["value"]) for p in pieces))
        if not valid:
            issues.append(_issue("hmmalign_annotation_geometry_invalid", tag=tag, record_key=row_key))
        annotations[tag] = {"text": "".join(p["value"] for p in pieces), "valid": valid,
                            "fragments": deepcopy(pieces)}
    return annotations


def _parse_record(events, alignment_index, engine_version):
    issues, blocks, active = [], [], []
    for event in events:
        if event["kind"] in {"sequence", "GC", "GR"}:
            active.append(event)
        elif event["kind"] in {"blank", "terminator"} and active:
            blocks.append(active)
            active = []
        if event["kind"].startswith("malformed"):
            issues.append(_issue("hmmalign_"+event["kind"], locator=event["locator"]))
    if active:
        blocks.append(active)
    header = next((e for e in events if e["kind"] == "header"), None)
    complete = any(e["kind"] == "terminator" for e in events)
    if header is None:
        issues.append(_issue("hmmalign_stockholm_header_missing"))
    elif header["version"] != "1.0":
        issues.append(_issue("hmmalign_stockholm_version_unsupported", version=header["version"]))
    if not complete:
        issues.append(_issue("hmmalign_stockholm_terminator_missing"))
    by_key, gc, widths, block_counts = {}, [], {}, []
    for block_index, block in enumerate(blocks):
        counts = Counter()
        widths_seen = Counter(len(e["value"]) for e in block if e["kind"] == "sequence")
        gc_widths = {len(e["value"]) for e in block if e["kind"] == "GC" and e["tag"] == "RF"}
        if len(gc_widths) == 1:
            width = next(iter(gc_widths))
        elif widths_seen and len([n for n in widths_seen if widths_seen[n] == max(widths_seen.values())]) == 1:
            width = max(widths_seen, key=widths_seen.get)
        else:
            width = None
        widths[block_index] = width
        rows_in_block = defaultdict(list)
        gr = defaultdict(list)
        for event in block:
            piece = {**deepcopy(event), "block_index": block_index}
            if event["kind"] == "sequence":
                name, occurrence = event["name"], counts[event["name"]]
                counts[name] += 1
                key = (name, occurrence)
                if key not in by_key:
                    row_index = len(by_key)
                    record_key = f"alignment:{alignment_index}/sequence:{row_index}"
                    by_key[key] = {"record_key": record_key, "name": name, "occurrence": occurrence,
                        "row_index": row_index, "alignment_index": alignment_index,
                        "locator": {**deepcopy(event["locator"]), "alignment_index": alignment_index,
                                    "row_index": row_index, "name_occurrence": occurrence},
                        "fragments": [], "annotation_fragments": [], "issues": []}
                by_key[key]["fragments"].append(piece)
                rows_in_block[name].append(by_key[key])
            elif event["kind"] == "GC":
                gc.append(piece)
            else:
                gr[(event["name"], event["tag"])].append(piece)
        for (name, tag), pieces in gr.items():
            candidates = rows_in_block[name]
            if len(candidates) != len(pieces):
                issues.append(_issue("hmmalign_row_annotation_join_ambiguous", name=name, tag=tag,
                                     block_index=block_index, annotation_count=len(pieces), row_count=len(candidates)))
            else:
                for row, piece in zip(candidates, pieces):
                    row["annotation_fragments"].append(piece)
        block_counts.append(counts)
    rows = list(by_key.values())
    geometry_known = all(v is not None for v in widths.values())
    column_count = sum(widths.values()) if geometry_known else None
    for (name, occurrence), row in by_key.items():
        ambiguous = len({counts[name] for counts in block_counts}) > 1
        if ambiguous:
            row["issues"].append(_issue("hmmalign_interleaved_occurrence_ambiguous", name=name, occurrence=occurrence))
        row["identity_unambiguous"] = not ambiguous
        row["aligned_sequence"] = "".join(p["value"] for p in row["fragments"])
        valid_symbols = bool(_SEQUENCE.fullmatch(row["aligned_sequence"]))
        row["symbols_valid"] = valid_symbols
        row["geometry_valid"] = (geometry_known and len(row["fragments"]) == len(blocks)
            and all(len(p["value"]) == widths[p["block_index"]] for p in row["fragments"]))
        if not valid_symbols:
            row["issues"].append(_issue("hmmalign_sequence_symbols_invalid"))
        if not row["geometry_valid"]:
            row["issues"].append(_issue("hmmalign_sequence_geometry_invalid"))
        row["column_annotations"] = _column_annotations(row["annotation_fragments"], len(blocks), widths,
                                                       row["issues"], row_key=row["record_key"])
        row["sequence_annotations"] = [deepcopy(e) for e in events if e["kind"] == "GS" and e["name"] == name]
        row["sequence_annotations_joined"] = all(counts[name] == 1 for counts in block_counts)
    column_annotations = _column_annotations(gc, len(blocks), widths, issues)
    return {"record_key": f"alignment:{alignment_index}", "alignment_index": alignment_index,
            "locator": deepcopy(events[0]["locator"]), "engine_version": engine_version,
            "header_valid": header is not None and header["version"] == "1.0", "complete": complete,
            "column_count": column_count, "block_count": len(blocks), "rows": rows,
            "column_annotations": column_annotations, "original_events": deepcopy(events), "issues": issues}


def iter_hmmalign_stockholm_records(stream, *, artifact_ref, engine_version):
    """Yield records, preserving partial records and buffering one alignment."""
    _identity(engine_version, "hmmalign_engine_version_invalid")
    events, index = [], 0
    for event in iter_hmmalign_stockholm_events(stream, artifact_ref=artifact_ref):
        if event["kind"] == "header" and any(e["kind"] != "blank" for e in events):
            yield _parse_record(events, index, engine_version)
            index += 1
            events = []
        events.append(event)
        if event["kind"] == "terminator":
            yield _parse_record(events, index, engine_version)
            index += 1
            events = []
    if any(e["kind"] != "blank" for e in events):
        yield _parse_record(events, index, engine_version)


def iter_hmmalign_stockholm_rows(stream, *, artifact_ref, engine_version):
    """Yield complete occurrence-keyed rows; one record is assembled at a time."""
    for record in iter_hmmalign_stockholm_records(stream, artifact_ref=artifact_ref, engine_version=engine_version):
        for row in record["rows"]:
            yield {**row, "alignment_complete": record["complete"],
                   "alignment_column_annotations": deepcopy(record["column_annotations"]),
                   "alignment_issues": deepcopy(record["issues"])}


def parse_hmmalign_stockholm(text, *, artifact_ref, engine_version):
    """Parse supplied original text; no identifier is opened or resolved."""
    if type(text) is not str:
        raise ValueError("hmmalign_text_required")
    records = list(iter_hmmalign_stockholm_records(text, artifact_ref=artifact_ref, engine_version=engine_version))
    issues = [{**i, "alignment_index": r["alignment_index"]} for r in records for i in r["issues"]]
    status = ("missing" if not records else "truncated" if any(not r["complete"] for r in records)
              else "invalid" if any(not r["header_valid"] for r in records)
              else "completed" if any(r["rows"] for r in records) else "completed_empty")
    return {"schema": NATIVE_SCHEMA, "operation": {"program": "hmmalign", "format": "stockholm",
             "engine_version": engine_version, "alphabet": None, "mode": "profile_alignment"},
            "artifacts": {"stockholm": text}, "artifact_refs": {"stockholm": artifact_ref},
            "alignments": records, "status": status, "issues": issues}


def _alphabet(value):
    if type(value) is not str:
        return None
    return {"protein": "amino", "amino": "amino", "dna": "dna", "rna": "rna"}.get(value.lower())


def _normalize(sequence, alphabet):
    result = sequence.upper()
    if alphabet in {"dna", "rna"}:
        result = result.replace("X", "N").replace("I", "A")
        result = result.replace("U", "T") if alphabet == "dna" else result.replace("T", "U")
    return result


def _is_residue(symbol):
    return symbol.isascii() and symbol.isalpha()


def _ungapped(sequence):
    # '*' is Easel's nonresidue, not an observed amino-acid/base measurement.
    return "".join(c for c in sequence if _is_residue(c))


def stockholm_digital_checksum(rows, *, alphabet):
    """Easel esl_msa_Checksum digital uint32, over supplied aligned row strings.

    This is the HMMER compatibility check, not a cryptographic identity. Names
    and annotations are excluded by the native algorithm. Keep custody separate.
    """
    kind = _alphabet(alphabet)
    if kind is None or type(rows) is not list or any(type(r) is not str for r in rows):
        raise ValueError("hmmalign_checksum_inputs_invalid")
    if len({len(r) for r in rows}) > 1:
        raise ValueError("hmmalign_checksum_row_geometry_invalid")
    codes = {symbol: i for i, symbol in enumerate(_ALPHABETS[kind])}
    val = 0
    for row in rows:
        for symbol in _normalize(row, kind).replace(".", "-").replace("_", "-"):
            if symbol not in codes:
                raise ValueError("hmmalign_checksum_symbol_invalid")
            val = (val + codes[symbol]) & 0xFFFFFFFF
            val = (val + (val << 10)) & 0xFFFFFFFF
            val ^= val >> 6
    val = (val + (val << 3)) & 0xFFFFFFFF
    val ^= val >> 11
    return (val + (val << 15)) & 0xFFFFFFFF


def posterior_bin_bounds(symbol):
    """Return integer hundredths and endpoint flags, never a midpoint estimate."""
    if symbol == "*":
        return {"lower_hundredths": 95, "upper_hundredths": 100, "lower_inclusive": True, "upper_inclusive": True}
    if type(symbol) is str and len(symbol) == 1 and symbol in "0123456789":
        number = int(symbol)
        return {"lower_hundredths": max(0, number*10-5), "upper_hundredths": number*10+5,
                "lower_inclusive": True, "upper_inclusive": False}
    return None


def _mapali_context(inputs, profile, alphabet, issues, engine_version):
    supplied = inputs.get("mapali")
    result = {"selected": supplied is not None, "status": "not_selected", "computed_checksum": None,
              "profile_checksum": profile.get("checksum"), "rows": [], "model_columns": None,
              "artifact_ref": None, "issues": []}
    if supplied is None:
        return result
    result["status"] = "unavailable"
    local = result["issues"]
    if type(supplied) is not dict or type(supplied.get("stockholm")) is not str:
        local.append(_issue("hmmalign_mapali_actual_alignment_required"))
    else:
        ref = supplied.get("artifact_ref")
        result["artifact_ref"] = ref
        if ref is not None and (type(ref) is not str or not ref):
            local.append(_issue("hmmalign_mapali_artifact_ref_invalid"))
        else:
            seed = parse_hmmalign_stockholm(supplied["stockholm"], artifact_ref=ref, engine_version=engine_version)
            result["native_alignment"] = seed
            if (len(seed["alignments"]) != 1 or seed["status"] != "completed"
                    or any(not r["symbols_valid"] or not r["geometry_valid"] or not r["identity_unambiguous"]
                           for a in seed["alignments"] for r in a["rows"])):
                local.append(_issue("hmmalign_mapali_alignment_invalid"))
            else:
                record = seed["alignments"][0]
                result["rows"] = deepcopy(record["rows"])
                mapping, length = profile.get("map"), profile.get("length")
                if (type(length) is not int or length < 1 or type(mapping) is not list
                        or len(mapping) != length or any(type(n) is not int or not 1 <= n <= record["column_count"] for n in mapping)
                        or any(a >= b for a, b in zip(mapping, mapping[1:]))):
                    local.append(_issue("hmmalign_mapali_profile_map_invalid_or_missing"))
                else:
                    result["model_columns"] = [n-1 for n in mapping]
                try:
                    checksum = stockholm_digital_checksum([r["aligned_sequence"] for r in result["rows"]], alphabet=alphabet)
                    result["computed_checksum"] = checksum
                    expected = profile.get("checksum")
                    if type(expected) is not int or not 0 <= expected <= 0xFFFFFFFF:
                        local.append(_issue("hmmalign_mapali_profile_checksum_missing_or_invalid"))
                    elif expected != checksum:
                        local.append(_issue("hmmalign_mapali_checksum_mismatch", expected=expected, computed=checksum))
                    if supplied.get("checksum") is not None and supplied["checksum"] != checksum:
                        local.append(_issue("hmmalign_mapali_supplied_checksum_mismatch"))
                except ValueError as error:
                    local.append(_issue(str(error)))
    if not local:
        result["status"] = "compatible"
    elif any(i["code"].endswith("mismatch") for i in local):
        result["status"] = "incompatible"
    issues.extend(deepcopy(local))
    return result


def _sequence_metadata(row, inputs, native_record_count, issues):
    supplied = inputs.get("sequences", [])
    if type(supplied) is not list:
        return None
    candidates = []
    for index, item in enumerate(supplied):
        if type(item) is not dict or item.get("name") != row["name"]:
            continue
        if item.get("occurrence") is not None and (type(item["occurrence"]) is not int or item["occurrence"] != row["occurrence"]):
            continue
        if item.get("alignment_index") is not None and (type(item["alignment_index"]) is not int or
                                                       item["alignment_index"] != row["alignment_index"]):
            continue
        candidates.append((index, item))
    if not candidates:
        return None
    duplicates = sum(r.get("name") == row["name"] for r in supplied if type(r) is dict)
    if (len(candidates) != 1 or not row["identity_unambiguous"] or
            candidates[0][1].get("occurrence") is None and (row["name_count"] > 1 or duplicates > 1) or
            native_record_count > 1 and candidates[0][1].get("alignment_index") is None):
        issues.append(_issue("hmmalign_sequence_metadata_join_ambiguous", record_key=row["record_key"]))
        return None
    index, item = candidates[0]
    return {"input_index": index, "supplied": deepcopy(item)}


def _sequence_mapping(sequence, metadata, trim, alphabet, issues):
    result = {"status": "unavailable", "original_length": None, "candidate_intervals": [],
              "original_interval": None, "trimmed_residues": None, "normalization": "native_alphabet_case_insensitive"}
    if metadata is None:
        result["reason"] = "sequence_metadata_missing_or_ambiguous"
        return result
    supplied = metadata["supplied"]
    length, original = supplied.get("length"), supplied.get("sequence")
    if length is not None and (type(length) is not int or length < 0):
        issues.append(_issue("hmmalign_original_length_invalid"))
        result["reason"] = "original_length_invalid"
        return result
    if original is not None and (type(original) is not str or any(not _is_residue(c) for c in original)):
        issues.append(_issue("hmmalign_original_sequence_invalid"))
        result["reason"] = "original_sequence_invalid"
        return result
    if original is not None:
        if length is not None and length != len(original):
            issues.append(_issue("hmmalign_original_sequence_length_mismatch"))
            result["reason"] = "original_sequence_length_mismatch"
            return result
        length = len(original)
    retained = _ungapped(sequence)
    if length is not None and (len(retained) > length or trim is False and len(retained) != length):
        issues.append(_issue("hmmalign_retained_original_length_mismatch"))
        result["reason"] = "retained_original_length_mismatch"
        return result
    result["original_length"] = length
    if original is not None:
        a, b = _normalize(original, alphabet), _normalize(retained, alphabet)
        starts = ([0] if a == b else [] if trim is False else
                  [i for i in range(len(a)-len(b)+1) if a[i:i+len(b)] == b])
        if not starts:
            issues.append(_issue("hmmalign_original_sequence_mismatch"))
            result.update(status="incompatible", original_length=None, reason="original_sequence_mismatch")
            return result
        result["candidate_intervals"] = [[i, i+len(b)] for i in starts]
        result["status"] = "unique" if len(starts) == 1 else "ambiguous"
        result["original_interval"] = result["candidate_intervals"][0] if len(starts) == 1 else None
        if len(starts) > 1:
            issues.append(_issue("hmmalign_trim_offset_ambiguous", candidate_count=len(starts)))
    else:
        result.update(status="length_only", reason="original_sequence_not_supplied")
    if trim is True and length is not None:
        result["trimmed_residues"] = length-len(retained)
    elif trim is False:
        result["trimmed_residues"] = 0
    return result


def _posterior(sequence, pp, issues):
    columns, counts = [], Counter()
    lower = upper = bounded = total = 0
    for index, symbol in enumerate(sequence):
        residue = _is_residue(symbol)
        total += residue
        code = pp[index] if pp is not None else None
        bounds = posterior_bin_bounds(code)
        if bounds is not None and not residue:
            issues.append(_issue("hmmalign_pp_on_nonresidue", column_index=index, symbol=symbol, pp=code))
            bounds = None
        elif code is not None and code != "." and bounds is None:
            issues.append(_issue("hmmalign_pp_symbol_invalid", column_index=index, pp=code))
        if bounds is not None:
            counts[code] += 1
            bounded += 1
            lower += bounds["lower_hundredths"]
            upper += bounds["upper_hundredths"]
        columns.append({"column_index": index, "symbol": code, "bounds": bounds})
    return {"columns": columns, "bin_counts": dict(counts), "residue_population": total,
            "bounded_residue_count": bounded, "unavailable_residue_count": total-bounded,
            "lower_sum_hundredths": lower, "upper_sum_hundredths": upper,
            "mean_upper_inclusive": all(code == "*" for code in counts),
            "population": "retained_residues_with_available_native_PP", "native_pp": pp}


def _annotation_objects(value):
    return type(value) is dict and all(type(a) is dict and type(a.get("text")) is str and
                                      type(a.get("valid")) is bool for a in value.values())


def _parsed_alignment_shape(alignment):
    return (type(alignment) is dict and type(alignment.get("rows")) is list
        and type(alignment.get("record_key")) is str and type(alignment.get("alignment_index")) is int
        and type(alignment.get("header_valid")) is bool and type(alignment.get("complete")) is bool
        and (alignment.get("column_count") is None or type(alignment["column_count"]) is int and alignment["column_count"] >= 0)
        and _annotation_objects(alignment.get("column_annotations")))


def _parsed_row_shape(row):
    return (type(row) is dict and all(type(row.get(k)) is str for k in ("record_key", "name", "aligned_sequence"))
        and all(type(row.get(k)) is int and row[k] >= 0 for k in ("row_index", "occurrence", "alignment_index"))
        and all(type(row.get(k)) is bool for k in ("geometry_valid", "symbols_valid", "identity_unambiguous"))
        and type(row.get("locator")) is dict and type(row.get("issues")) is list
        and _annotation_objects(row.get("column_annotations")))


def build_hmmalign_sheet(native, *, inputs):
    """Extract counts, column correspondence and validated joins, without I/O."""
    require_finite_json(native, "hmmalign_native_finite_json_required")
    require_finite_json(inputs, "hmmalign_inputs_finite_json_required")
    if (type(native) is not dict or native.get("schema") != NATIVE_SCHEMA or type(native.get("alignments")) is not list
            or type(native.get("operation")) is not dict or native["operation"].get("program") != "hmmalign"
            or type(native.get("issues")) is not list or type(native.get("artifact_refs")) is not dict
            or "stockholm" not in native["artifact_refs"] or type(native.get("status")) is not str or native["status"] not in
            {"missing", "completed", "completed_empty", "truncated", "invalid"}):
        raise ValueError("hmmalign_native_schema_invalid")
    if type(inputs) is not dict:
        raise ValueError("hmmalign_inputs_object_required")
    profile = inputs.get("profile")
    if profile is None:
        profile = {}
    if type(profile) is not dict:
        raise ValueError("hmmalign_profile_object_required")
    if inputs.get("trim") is not None and type(inputs["trim"]) is not bool:
        raise ValueError("hmmalign_trim_boolean_required")
    trim, issues = inputs.get("trim"), deepcopy(native["issues"])
    if inputs.get("sequences") is not None and type(inputs["sequences"]) is not list:
        raise ValueError("hmmalign_sequences_array_required")
    for index, item in enumerate(inputs.get("sequences") or []):
        if (type(item) is not dict or type(item.get("name")) is not str or not item["name"] or
                item.get("occurrence") is not None and (type(item["occurrence"]) is not int or item["occurrence"] < 0) or
                item.get("alignment_index") is not None and (type(item["alignment_index"]) is not int or item["alignment_index"] < 0)):
            issues.append(_issue("hmmalign_sequence_metadata_invalid", input_index=index))
    alphabet = _alphabet(profile.get("alphabet"))
    if profile.get("alphabet") is not None and alphabet is None:
        issues.append(_issue("hmmalign_profile_alphabet_invalid"))
    mapali = _mapali_context(inputs, profile, alphabet, issues, native["operation"].get("engine_version"))
    sequences, columns, alignments = [], [], []
    for alignment in native["alignments"]:
        if not _parsed_alignment_shape(alignment):
            issues.append(_issue("hmmalign_native_alignment_invalid"))
            continue
        index = alignment["alignment_index"]
        raw_rf = alignment["column_annotations"].get("RF")
        rf = raw_rf["text"] if raw_rf and raw_rf["valid"] else None
        mask = [c not in ".-_~" for c in rf] if rf is not None else None
        rf_length = sum(mask) if mask is not None else None
        model_length = profile.get("length", rf_length)
        if model_length is None:
            model_length = rf_length
        model_valid = type(model_length) is int and model_length > 0
        if not model_valid or rf_length is not None and model_length != rf_length:
            if model_length is not None:
                issues.append(_issue("hmmalign_profile_length_mismatch_or_invalid", alignment_index=index,
                                     profile_length=model_length, rf_model_positions=rf_length))
            model_length = None
        model_columns = [i for i, value in enumerate(mask or []) if value]
        raw_pp_cons = alignment["column_annotations"].get("PP_cons")
        pp_cons = raw_pp_cons["text"] if raw_pp_cons and raw_pp_cons["valid"] else None
        names = Counter(r["name"] for r in alignment["rows"] if _parsed_row_shape(r))
        local_rows = []
        for source_row in alignment["rows"]:
            if not _parsed_row_shape(source_row):
                issues.append(_issue("hmmalign_native_sequence_row_invalid", alignment_index=index))
                continue
            row = deepcopy(source_row)
            row["name_count"] = names[row["name"]]
            row_issues = deepcopy(row["issues"])
            metadata = _sequence_metadata(row, inputs, len(native["alignments"]), row_issues)
            declared_origin = metadata["supplied"].get("origin") if metadata else None
            if declared_origin is not None and (type(declared_origin) is not str or
                    declared_origin not in {"inherited", "mapali", "new", "newly_aligned", "unknown"}):
                row_issues.append(_issue("hmmalign_sequence_origin_invalid"))
                declared_origin = None
            origin = ("unknown" if declared_origin == "unknown" else
                      "inherited" if declared_origin in {"inherited", "mapali"} else
                      "newly_aligned" if declared_origin in {"new", "newly_aligned"} or not mapali["selected"] else "unknown")
            inherited = None
            if mapali["selected"] and row["row_index"] < len(mapali["rows"]):
                candidate = mapali["rows"][row["row_index"]]
                # Native hmmalign prepends seed rows in their original order.
                if candidate["name"] == row["name"]:
                    origin = "inherited"
                    compatible = mapali["status"] == "compatible" and mask is not None and row["geometry_valid"]
                    if compatible:
                        a = "".join(candidate["aligned_sequence"][c] for c in mapali["model_columns"])
                        b = "".join(row["aligned_sequence"][c] for c in model_columns)
                        compatible = _normalize(a, alphabet).replace(".", "-").replace("_", "-") == _normalize(b, alphabet).replace(".", "-").replace("_", "-")
                        original_symbols = _normalize(_ungapped(candidate["aligned_sequence"]), alphabet)
                        retained_symbols = _normalize(_ungapped(row["aligned_sequence"]), alphabet)
                        compatible = compatible and (retained_symbols == original_symbols if trim is False else
                                                     retained_symbols in original_symbols)
                    inherited = {"seed_record_key": candidate["record_key"], "artifact_ref": mapali["artifact_ref"],
                                 "status": "verified" if compatible else "unverified"}
                    if not compatible:
                        row_issues.append(_issue("hmmalign_inherited_model_columns_unverified"))
                    if metadata is None and compatible:
                        original = _ungapped(candidate["aligned_sequence"])
                        metadata = {"mapali_row_index": row["row_index"], "supplied": {"name": row["name"],
                             "occurrence": row["occurrence"], "sequence": original, "length": len(original), "origin": "inherited"}}
                else:
                    row_issues.append(_issue("hmmalign_mapali_output_prefix_mismatch"))
                    origin = "unknown"
            if origin == "inherited" and (inherited is None or inherited["status"] != "verified"):
                row_issues.append(_issue("hmmalign_inherited_join_not_verified"))
            if declared_origin in {"new", "newly_aligned"} and origin == "inherited":
                row_issues.append(_issue("hmmalign_sequence_origin_conflict"))
                # A contradictory new-input record must not become an inherited
                # row's sequence/taxon/function join merely by sharing its name.
                metadata = None
                if inherited is not None and inherited["status"] == "verified":
                    original = _ungapped(mapali["rows"][row["row_index"]]["aligned_sequence"])
                    metadata = {"mapali_row_index": row["row_index"], "supplied": {"name": row["name"],
                         "occurrence": row["occurrence"], "sequence": original, "length": len(original), "origin": "inherited"}}
            if origin == "unknown" and mapali["status"] == "compatible" and row["row_index"] >= len(mapali["rows"]):
                origin = "newly_aligned"
            sequence = row["aligned_sequence"]
            if alphabet is not None and any(symbol not in _ALPHABETS[alphabet] for symbol in
                                           _normalize(sequence, alphabet).replace(".", "-").replace("_", "-")):
                row["symbols_valid"] = False
                row_issues.append(_issue("hmmalign_sequence_profile_alphabet_mismatch"))
            mapping = _sequence_mapping(sequence, metadata, trim, alphabet, row_issues)
            if metadata is not None:
                metadata["status"] = ("verified" if mapping["original_length"] is not None else
                    "identity_only" if mapping["status"] == "length_only" else "incompatible")
                metadata["sequence_mapping_status"] = mapping["status"]
            usable = row["geometry_valid"] and row["symbols_valid"] and alignment["header_valid"]
            pp_annotation = row["column_annotations"].get("PP")
            pp = pp_annotation["text"] if pp_annotation and pp_annotation["valid"] and usable else None
            posterior = _posterior(sequence, pp, row_issues)
            counts = {"retained_residues": len(_ungapped(sequence)) if row["symbols_valid"] else None,
                      "match_state_residues": None, "deleted_model_positions": None, "insert_state_residues": None,
                      "terminal_unaligned_residues": None, "missing_model_positions": None,
                      "nonresidue_model_positions": None}
            correspondence = []
            if usable and mask is not None and model_columns:
                first, last = model_columns[0], model_columns[-1]
                counts.update(match_state_residues=0, deleted_model_positions=0, insert_state_residues=0,
                              terminal_unaligned_residues=0, missing_model_positions=0, nonresidue_model_positions=0)
                residue_index, model_position = 0, 0
                for col, (symbol, match) in enumerate(zip(sequence, mask)):
                    residue = _is_residue(symbol)
                    model_position += match
                    terminal = col < first or col > last
                    if match:
                        counts["match_state_residues"] += residue
                        counts["deleted_model_positions"] += symbol in _GAPS
                        counts["missing_model_positions"] += symbol == "~"
                        counts["nonresidue_model_positions"] += symbol == "*"
                    elif residue:
                        counts["terminal_unaligned_residues" if terminal else "insert_state_residues"] += 1
                    start = mapping["original_interval"][0] if mapping["original_interval"] is not None else None
                    correspondence.append({"column_index": col, "model_position": model_position if match else None,
                        "retained_sequence_position": residue_index if residue else None,
                        "original_sequence_position": start+residue_index if residue and start is not None else None,
                        "symbol": symbol, "relationship": "model_match" if match and residue else
                        "model_deletion" if match and symbol in _GAPS else "missing" if symbol == "~" else
                        "nonresidue" if symbol == "*" else "terminal_unaligned" if terminal and residue else
                        "internal_insertion" if residue else "insertion_gap"})
                    residue_index += residue
            fragment = "native_missing_data" if "~" in sequence else "declared" if metadata and metadata["supplied"].get("fragment") is True else "not_declared"
            sheet_row = {"record_key": row["record_key"], "locator": row["locator"], "name": row["name"],
                "occurrence": row["occurrence"], "alignment_index": index, "native": deepcopy(source_row),
                "origin": origin, "fragment": fragment, "inherited_join": inherited, "metadata_join": metadata,
                "mapping": mapping, "measurements": counts, "model_length": model_length,
                "rf_model_positions": rf_length, "native_rf": rf, "posterior": posterior,
                "correspondence": correspondence, "availability": {"geometry": usable, "rf": mask is not None,
                    "pp": pp is not None, "original_mapping": mapping["status"]}, "issues": row_issues}
            sequences.append(sheet_row)
            local_rows.append(sheet_row)
            issues.extend({**i, "record_key": row["record_key"]} for i in row_issues)
        for col in range(alignment["column_count"] or 0):
            eligible = [r for r in local_rows if r["availability"]["geometry"]]
            symbols = [(r, r["native"]["aligned_sequence"][col]) for r in eligible]
            populations = {}
            for label in ("all", "newly_aligned", "inherited", "unknown", "fragment", "nonfragment"):
                chosen = [(r, s) for r, s in symbols if label == "all" or r["origin"] == label or
                          label == "fragment" and r["fragment"] != "not_declared" or
                          label == "nonfragment" and r["fragment"] == "not_declared"]
                observable = [(r, s) for r, s in chosen if s != "~"]
                populations[label] = {"occupancy_numerator": sum(_is_residue(s) for _, s in observable),
                    "occupancy_denominator": len(observable), "missing_rows": len(chosen)-len(observable),
                    "row_count": len(chosen), "record_keys": [r["record_key"] for r, _ in chosen]}
            pp_code = pp_cons[col] if pp_cons is not None else None
            pp_bounds = posterior_bin_bounds(pp_code)
            if pp_code is not None and pp_code != "." and pp_bounds is None:
                issues.append(_issue("hmmalign_pp_cons_symbol_invalid", alignment_index=index, column_index=col,
                                     pp_cons=pp_code))
            if pp_bounds is not None and mask is not None and not mask[col]:
                issues.append(_issue("hmmalign_pp_cons_on_insert_column", alignment_index=index, column_index=col))
                pp_bounds = None
            columns.append({"record_key": f"alignment:{index}/column:{col}", "alignment_index": index,
                "locator": {"artifact_role": "stockholm", "artifact_ref": native["artifact_refs"]["stockholm"],
                            "alignment_index": index, "column_index": col},
                "column_index": col, "native_rf_symbol": rf[col] if rf is not None else None,
                "model_position": sum(mask[:col+1]) if mask is not None and mask[col] else None,
                "homologous_model_column": mask[col] if mask is not None else None, "populations": populations,
                "native_pp_cons_symbol": pp_code, "native_pp_cons_bounds": pp_bounds,
                "pp_cons_population": "newly_aligned_match_state_residues_with_native_PP",
                "pp_cons_observed_denominator": sum(r["origin"] == "newly_aligned" and
                    r["posterior"]["columns"][col]["bounds"] is not None for r in eligible)
                    if mask is not None and mask[col] else None})
        alignments.append({"record_key": alignment["record_key"], "alignment_index": index,
            "column_count": alignment["column_count"], "model_length": model_length,
            "rf_model_positions": rf_length, "native_rf": rf, "native_pp_cons": pp_cons,
            "complete": alignment["complete"], "row_count": len(local_rows)})
    acquisition = inputs.get("acquisition")
    if acquisition is not None and type(acquisition) is not dict:
        raise ValueError("hmmalign_acquisition_object_required")
    declared_complete = (acquisition or {}).get("output_complete")
    if declared_complete is not None and type(declared_complete) is not bool:
        raise ValueError("hmmalign_output_complete_boolean_required")
    if declared_complete is True and native["status"] in {"missing", "truncated", "invalid"}:
        issues.append(_issue("hmmalign_acquisition_native_completeness_conflict"))
    operation = {**deepcopy(native["operation"]), "alphabet": alphabet,
                 "mode": "mapali_trim" if mapali["selected"] and trim else "mapali" if mapali["selected"] else
                         "trim" if trim else "ordinary" if trim is False else "profile_alignment"}
    result = {"schema": SHEET_SCHEMA, "operation": operation, "inputs": deepcopy(inputs),
        "artifact_refs": deepcopy(native["artifact_refs"]), "native_result": deepcopy(native),
        "status": native["status"], "acquisition": deepcopy(acquisition), "mapali": mapali,
        "sequences": sequences, "columns": columns, "alignments": alignments, "issues": issues}
    require_finite_json(result, "hmmalign_sheet_finite_json_required")
    return result


__all__ = ["parse_hmmalign_stockholm", "build_hmmalign_sheet", "iter_hmmalign_stockholm_events",
           "iter_hmmalign_stockholm_records", "iter_hmmalign_stockholm_rows", "stockholm_digital_checksum"]
