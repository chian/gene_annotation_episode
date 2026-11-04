"""Deterministic FM preparation and literal-match diagnostics from saved sheets.

No search executable or acquisition is invoked here. Index consistency, source
agreement, native counts, and optional complete-source literal comparison have
separate populations. None is an annotation-confidence score.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy

from .hmmer_fm_data import issue, _symbols


NUMBER_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"})
CHECK_STATES = frozenset({"pass", "fail", "unknown", "not_applicable"})
DEFAULT_PARAMETERS = {"alphabet_normalization": "none", "coordinate_policy": "native_one_based",
                      "exhaustive_literal_check": False}


def _number(value, unit, inputs, state="present"):
    assert state in NUMBER_STATES
    return {"value": value, "state": state, "unit": unit, "inputs": inputs}


def _check(checks, name, key, state, scope, inputs):
    assert state in CHECK_STATES
    checks.append({"name": name, "record_key": key, "state": state, "scope": scope, "inputs": inputs})


def _truth(value):
    return "unknown" if value is None else "pass" if value else "fail"


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(end, merged[-1][1])
    return merged


def _length(intervals):
    return sum(end - start + 1 for start, end in intervals)


def _normal(sequence, parameters):
    sequence = sequence.upper()  # native case folding, never a source rewrite
    return sequence.replace("U", "T") if parameters["alphabet_normalization"] == "rna_to_dna" else sequence


def _state(sheet, role, direction):
    occurrences = [o for o in sheet["artifact_occurrences"] if o["role"] == role and o["direction"] == direction]
    if not occurrences:
        return "missing"
    ids = {o["occurrence_id"] for o in occurrences}
    if any(i["code"] in {"size_mismatch", "digest_mismatch", "invalid_occurrence", "duplicate_occurrence_id"}
           and i["record_key"] in ids for i in sheet["issues"]):
        return "failed"
    if any(o["completeness"] != "complete" for o in occurrences):
        return "incomplete"
    return "present"


def _dbstate(database):
    if database is None:
        return "missing"
    state = database["population"]["state"]
    return {"decoded": "present", "partial": "incomplete", "unsupported": "incompatible", "invalid": "failed"}[state]


def _array_symbols(block, field, metadata):
    array = block["arrays"].get(field)
    if array is None or not array["complete"]:
        return None
    n = block["header"]["N"]
    needed = (n + 3)//4 if metadata["alph_type"] == 0 else n
    if len(array["values"]) != needed:
        return None
    return _symbols(array["values"], n, metadata["alphabet_symbols"])


def _consistency(block, forward, metadata, checks):
    """Validate retained counter rows and LF/suffix-sample correspondence in O(N).

    This is an internal consistency check on saved arrays, not a suffix-array
    construction, search, or assertion that native matching is correct.
    """
    key, header = block["record_key"], block["header"]
    n, size = header["N"], metadata["alph_size"]
    bwt = _array_symbols(block, "BWT", metadata)
    text = _array_symbols(forward, "T", metadata) if forward else None
    details = {"counter_mismatch_rows": [], "suffix_sample_mismatch_indices": []}
    cached_consistent = (bwt == block["decoded"]["bwt"] and
                         (block["section"] != "forward" or text == block["decoded"]["text"]))
    _check(checks, "decoded_array_symbols", key, _truth(cached_consistent),
           "saved decoded strings agree with full packed arrays; calculations use the arrays", [key, "arrays", "decoded"])
    if not block["complete"] or bwt is None or len(bwt) != n or header["term_loc"] >= n:
        for name in ("bwt_text_consistency", "suffix_samples", "counter_rows", "sentinel_encoding"):
            _check(checks, name, key, "unknown", "complete retained block arrays required", [key])
        return details
    alphabet = metadata["alphabet_symbols"]
    codes = [alphabet.index(c) for c in bwt]
    expected_b = [[0] * size]
    expected_sb = [[0] * size]
    total, partial = [0] * size, [0] * size
    for pos, code in enumerate(codes, 1):
        total[code] += 1
        partial[code] += 1
        if pos % metadata["freq_cnt_b"] == 0:
            expected_b.append([v % 65536 for v in partial])
        if pos % metadata["freq_cnt_sb"] == 0:
            expected_sb.append(list(total))
            partial = [0] * size
    # The writer overwrites the last row even when N is an exact boundary.
    if n % metadata["freq_cnt_b"]:
        expected_b.append([v % 65536 for v in partial])
    else:
        expected_b[-1] = [v % 65536 for v in partial]
    if n % metadata["freq_cnt_sb"]:
        expected_sb.append(list(total))
    else:
        expected_sb[-1] = list(total)
    for field, expected in (("counters_b", expected_b), ("counters_sb", expected_sb)):
        actual = block["arrays"][field]["values"]
        for i in range(max(len(actual), len(expected))):
            if i >= len(actual) or i >= len(expected) or actual[i] != expected[i]:
                details["counter_mismatch_rows"].append({"array": field, "index": _number(i, "row_index", [key, field])})
    _check(checks, "counter_rows", key, "fail" if details["counter_mismatch_rows"] else "pass",
           "every b/sb row; encoded BWT includes sentinel as alphabet[0]; native uint16 wrap retained", [key, "BWT", "counters_b", "counters_sb"])
    sentinel_ok = codes[header["term_loc"]] == 0 and (text is None or text[-1:] == alphabet[0])
    _check(checks, "sentinel_encoding", key, _truth(sentinel_ok),
           "BWT term_loc and stored original T final symbol use alphabet[0] as sentinel placeholder", [key])
    if text is None or len(text) != n:
        _check(checks, "bwt_text_consistency", key, "unknown", "matching forward-section T required", [key])
        _check(checks, "suffix_samples", key, "unknown" if block["section"] == "forward" else "not_applicable", "SA stored only in forward section", [key])
        return details
    letters = [c + 1 for c in codes]
    letters[header["term_loc"]] = 0
    counts = Counter(letters)
    cumulative, cursor = {}, 0
    for code in range(size + 1):
        cumulative[code], cursor = cursor, cursor + counts[code]
    seen = Counter()
    lf = []
    for code in letters:
        lf.append(cumulative[code] + seen[code])
        seen[code] += 1
    original = text[:-1]
    expected_text = (original[::-1] if block["section"] == "forward" else original)
    expected_codes = [alphabet.index(c) + 1 for c in expected_text] + [0]
    row, suffix = header["term_loc"], 0
    visited, mismatches = set(), 0
    samples = block["arrays"].get("SA", {}).get("values")
    for _ in range(n):
        if row in visited:
            break
        visited.add(row)
        if letters[row] != expected_codes[(suffix - 1) % n]:
            mismatches += 1
        if samples is not None and row and row % metadata["freq_SA"] == 0:
            j = row // metadata["freq_SA"]
            if j >= len(samples) or samples[j] != (0xFFFFFFFF if suffix == n - 1 else suffix):
                details["suffix_sample_mismatch_indices"].append(_number(j, "sample_index", [key, "SA"]))
        row, suffix = lf[row], (suffix - 1) % n
    consistent = len(visited) == n and row == header["term_loc"] and mismatches == 0
    details["bwt_symbol_mismatch_count"] = _number(mismatches, "symbols", [key, "T", "BWT"])
    details["lf_visited_rows"] = _number(len(visited), "rows", [key, "BWT", "term_loc"])
    _check(checks, "bwt_text_consistency", key, _truth(consistent),
           "full LF cycle and each preceding symbol against reversed T (forward section) or T (reverse section)", [key, forward["record_key"]])
    if samples is None:
        _check(checks, "suffix_samples", key, "not_applicable", "reverse section stores no SA", [key])
    else:
        if samples[0] != 0:
            details["suffix_sample_mismatch_indices"].append(_number(0, "sample_index", [key, "SA"]))
        if n % metadata["freq_SA"] == 0 and samples[-1] != 0:
            details["suffix_sample_mismatch_indices"].append(_number(len(samples)-1, "sample_index", [key, "SA"]))
        _check(checks, "suffix_samples", key,
               "unknown" if len(visited) != n else "fail" if details["suffix_sample_mismatch_indices"] else "pass",
               "all sampled LF suffix positions; sample zero and unused trailing slot are writer zeros", [key, "SA"])
    return details


def _build_components(sheet, parameters, result):
    rows, checks = result["rows"], result["checks"]
    database = sheet["database"]
    sources = [r for r in sheet["input_records"] if r["kind"] == "fasta"]
    source_role = "sequences" if sheet["operation"]["program"] == "makehmmerdb" else "source_sequences"
    source_state = _state(sheet, source_role, "input")
    if any(not s["payload"]["valid"] for s in sources) or any(i["code"] == "invalid_fasta" for i in sheet["issues"]):
        source_state = "failed"
    if any(i["code"] == "unsupported_sequence_format" for i in sheet["issues"]):
        source_state = "incompatible"
    db_state = _dbstate(database)
    segments = database["segments"] if database else []
    blocks = database["blocks"] if database else []
    ranges = database["ambiguity_ranges"] if database else []
    metadata = database["metadata"] if database else None
    forward = {b["block_ordinal"]: b for b in blocks if b["section"] == "forward"}
    source_keys = [s["record_key"] for s in sources]
    dbkey = database["occurrence"]["occurrence_id"] if database else None
    dbknown = metadata is not None
    comps = {}
    comps["source_occurrence_count"] = _number(len(sources) if source_state not in ("missing", "incompatible") else None, "sequence_occurrences", source_keys, source_state)
    comps["source_artifact_count"] = _number(sum(o["role"] == source_role and o["direction"] == "input" for o in sheet["artifact_occurrences"]), "artifacts", [source_role], source_state)
    source_total = sum(len(s["payload"]["sequence"]) for s in sources)
    comps["source_symbol_total"] = _number(source_total if source_state not in ("missing", "incompatible") else None, "source_symbols", source_keys, source_state)
    decoded_body = database is not None and database["population"]["decoded_segment_count"] is not None
    comps["stored_segment_count"] = _number(len(segments) if decoded_body else None, "segments", [dbkey], db_state)
    comps["distinct_target_count"] = _number(len({s["target_id"] for s in segments}) if decoded_body else None, "source_target_ids", [s["record_key"] for s in segments], db_state)
    comps["declared_total_char_count"] = _number(metadata["total_char_count"] if dbknown else None, "source_symbols_excluding_block_overlap", [dbkey, "total_char_count"], "present" if dbknown else db_state)
    comps["actual_database_bytes"] = _number(metadata["actual_bytes"] if dbknown else database["occurrence"]["size_bytes"] if database else None, "bytes", [dbkey], "present" if database and not any(i["code"] == "size_mismatch" for i in database["issues"]) else db_state)
    comps["indexed_symbols"] = _number(sum(b["header"]["N"]-1 for b in forward.values()) if decoded_body else None, "index_symbols_including_block_overlap", [b["record_key"] for b in forward.values()], db_state)
    comps["indexed_unique_symbols"] = _number(sum(b["header"]["N"]-1-b["header"]["overlap"] for b in forward.values()) if decoded_body else None, "index_symbols_excluding_block_overlap", [b["record_key"] for b in forward.values()], db_state)
    comps["sentinel_count"] = _number(len(forward) if decoded_body else None, "logical_text_block_sentinels", [b["record_key"] for b in forward.values()], db_state)
    comps["stored_bwt_sentinel_count"] = _number(len(blocks) if decoded_body else None, "stored_section_sentinels", [b["record_key"] for b in blocks], db_state)
    comps["ambiguity_range_count"] = _number(len(ranges) if decoded_body else None, "stored_ranges", [r["record_key"] for r in ranges], db_state)
    custody = sheet["associations"]["source_binding_state"]
    _check(checks, "source_custody", dbkey, {"unknown": "unknown", "matched": "pass", "mismatch": "fail"}[custody],
           "supplied producer attempt and exact ordered source artifact identities/digests; independent symbol checks do not establish custody", ["source_binding"])
    _check(checks, "decoded_layout", dbkey, "pass" if db_state == "present" else "unknown" if db_state in ("missing", "incomplete", "incompatible") else "fail",
           "declared ABI, all metadata/arrays, framing, occurrence digest and byte count", [dbkey])
    _check(checks, "dna_reader_compatibility", dbkey, "unknown" if not dbknown else _truth(metadata["dna_reader_compatibility"] == "compatible"),
           "HMMER 3.4 fm_readFMmeta accepts DNA only; amino writer decoding is separate", [dbkey, "alph_type"])
    covered, ambiguous = defaultdict(list), defaultdict(list)
    mapped_all = True
    sequence_cursor, ambiguity_cursor = 0, 0
    partition_ok = True
    for block in forward.values():
        h = block["header"]
        partition_ok = partition_ok and h["seq_offset"] == sequence_cursor and h["ambig_offset"] == ambiguity_cursor
        sequence_cursor += h["seq_cnt"]
        ambiguity_cursor += h["ambig_cnt"]
    if metadata:
        partition_ok = partition_ok and sequence_cursor == metadata["seq_count"] and ambiguity_cursor == metadata["ambiguity_range_count"]
    _check(checks, "metadata_partition", dbkey, _truth(partition_ok) if db_state == "present" else "unknown",
           "forward block sections refer once to every ordered segment/range row; paired sections share those rows", [dbkey])
    for block in blocks:
        header, key = block["header"], block["record_key"]
        seq_end, ambig_end = header["seq_offset"] + header["seq_cnt"], header["ambig_offset"] + header["ambig_cnt"]
        offsets_ok = seq_end <= len(segments) and ambig_end <= len(ranges)
        _check(checks, "block_offsets", key, _truth(offsets_ok), "segment and ambiguity spans refer to retained metadata rows", [key])
        if block["section"] == "reverse":
            first = forward.get(block["block_ordinal"])
            compatible = first is not None and all(header[f] == first["header"][f] for f in ("N", "seq_offset", "seq_cnt", "ambig_offset", "ambig_cnt")) and header["overlap"] == 0
            _check(checks, "paired_block_metadata", key, _truth(compatible), "paired sections share populations; reverse writer overlap is zero", [key, first["record_key"] if first else None])
        details = _consistency(block, forward.get(block["block_ordinal"]), metadata, checks)
        rows.append({"kind": "block_validation", "record_key": key, "components": {}, "details": details})
        if block["section"] != "forward":
            continue
        block_segments = segments[header["seq_offset"]:seq_end]
        block_ranges = ranges[header["ambig_offset"]:ambig_end]
        valid_ranges = all(0 <= r["lower"] <= r["upper"] < header["N"]-1 for r in block_ranges)
        ordered_ranges = all(a["upper"] < b["lower"] for a, b in zip(block_ranges, block_ranges[1:]))
        _check(checks, "ambiguity_bounds", key, _truth(offsets_ok and valid_ranges and ordered_ranges),
               "ordered disjoint zero-based inclusive ranges within this block's nonsentinel text", [r["record_key"] for r in block_ranges])
        concatenation = (offsets_ok and bool(block_segments) and block_segments[0]["fm_start"] == 0
                         and all(a["fm_start"] + a["length"] == b["fm_start"] for a,b in zip(block_segments, block_segments[1:]))
                         and block_segments[-1]["fm_start"] + block_segments[-1]["length"] == header["N"] - 1)
        _check(checks, "block_segment_coverage", key, _truth(concatenation), "segments partition nonsentinel T without internal gaps or overlaps", [s["record_key"] for s in block_segments])
        text = _array_symbols(block, "T", metadata)
        for segment in block_segments:
            skey, target = segment["record_key"], segment["target_id"]
            start, end = segment["target_start"], segment["target_start"]+segment["length"]-1
            source = sources[target] if target < len(sources) else None
            bounds = (source is not None and 1 <= start <= end <= len(source["payload"]["sequence"])
                      and 0 <= segment["fm_start"] < segment["fm_start"]+segment["length"] <= header["N"]-1)
            _check(checks, "segment_coordinates", skey, "unknown" if source is None else _truth(bounds),
                   "target_id indexes supplied original source order; one-based source interval and zero-based block interval", [skey, source["record_key"] if source else None])
            _check(checks, "segment_name", skey, "unknown" if source is None else _truth(segment["name"] == source["payload"]["name"]),
                   "label agreement only, not historical custody or unique identity", [skey, source["record_key"] if source else None])
            if not bounds:
                mapped_all = False
                continue
            covered[source["record_key"]].append((start,end))
            overlaps = []
            for r in block_ranges:
                lo, hi = max(r["lower"], segment["fm_start"]), min(r["upper"], segment["fm_start"]+segment["length"]-1)
                if lo <= hi:
                    a,b = start+lo-segment["fm_start"], start+hi-segment["fm_start"]
                    overlaps.append((a,b))
                    ambiguous[source["record_key"]].append((a,b))
            raw_source = source["payload"]["sequence"][start-1:end]
            normalized = _normal(raw_source, parameters)
            if text is not None and valid_ranges and offsets_ok:
                index = text[segment["fm_start"]:segment["fm_start"]+segment["length"]]
                ambig_positions = {pos-start for a,b in overlaps for pos in range(a,b+1)}
                mismatch_positions = [j for j,(a,b) in enumerate(zip(normalized,index)) if j not in ambig_positions and a != b]
                exact = not mismatch_positions and len(index) == len(normalized)
                expected_ambig = {j for j,c in enumerate(raw_source.upper()) if c not in "ACGTU"} if metadata["alph_type"] == 0 else set()
                _check(checks, "source_symbols_outside_ambiguities", skey, _truth(exact),
                       "case-folded source; only caller-selected U-to-T normalization; recorded ambiguous positions excluded", [skey, source["record_key"], key, "alphabet_normalization"])
                _check(checks, "source_ambiguity_membership", skey, _truth(expected_ambig == ambig_positions),
                       "each original non-ACGTU DNA symbol equals recorded ambiguity membership", [skey, source["record_key"], key])
                rows.append({"kind": "segment_validation", "record_key": skey,
                             "components": {"compared_symbols": _number(len(normalized)-len(ambig_positions), "symbols", [skey]),
                                            "mismatching_symbols": _number(len(mismatch_positions), "symbols", [skey])},
                             "details": {"source_record_key": source["record_key"],
                                         "mismatch_source_positions": [_number(start+j, "one_based_source_coordinate", [skey]) for j in mismatch_positions]}})
            else:
                _check(checks, "source_symbols_outside_ambiguities", skey, "unknown", "complete decoded T and valid ranges required", [skey])
        previous_covered = defaultdict(list)
        for prev in forward.values():
            if prev["block_ordinal"] >= block["block_ordinal"]:
                continue
            h = prev["header"]
            for segment in segments[h["seq_offset"]:h["seq_offset"]+h["seq_cnt"]]:
                previous_covered[segment["target_id"]].append((segment["target_start"], segment["target_start"]+segment["length"]-1))
        repeated = 0
        for segment in block_segments:
            a,b = segment["target_start"], segment["target_start"]+segment["length"]-1
            repeated += sum(max(0,min(b,y)-max(a,x)+1) for x,y in _merge(previous_covered[segment["target_id"]]))
        _check(checks, "block_overlap", key, _truth(repeated == header["overlap"]),
               "declared block overlap equals source-coordinate overlap with earlier blocks", [key])
    coverage_details = []
    for source in sources:
        key, length = source["record_key"], len(source["payload"]["sequence"])
        intervals = _merge(covered[key])
        ambiguity = _merge(ambiguous[key])
        coverage_details.append({"source_record_key": key,
            "covered_intervals": [{"start": _number(a, "one_based_source_coordinate", [key]), "end": _number(b, "one_based_source_coordinate", [key])} for a,b in intervals],
            "ambiguity_intervals": [{"start": _number(a, "one_based_source_coordinate", [key]), "end": _number(b, "one_based_source_coordinate", [key])} for a,b in ambiguity]})
        _check(checks, "source_coverage", key, "unknown" if db_state != "present" else _truth(intervals == ([[1,length]] if length else [])),
               "union of source-coordinate segment intervals covers this complete supplied sequence", [key, dbkey])
    joint_state = source_state if source_state != "present" else db_state if db_state != "present" else "present" if mapped_all else "failed"
    covered_length = sum(_length(_merge(value)) for value in covered.values())
    ambiguous_length = sum(_length(_merge(value)) for value in ambiguous.values())
    comps["covered_source_symbols"] = _number(covered_length if decoded_body and source_state != "missing" else None, "source_symbols", [dbkey, *source_keys], joint_state)
    comps["ambiguity_union_symbols"] = _number(ambiguous_length if decoded_body and source_state != "missing" else None, "source_symbols", [dbkey, *source_keys], joint_state)
    comps["ambiguity_fraction"] = _number(ambiguous_length/source_total if source_total and joint_state == "present" else None, "fraction",
        {"numerator": "ambiguity_union_symbols", "denominator": "source_symbol_total", "denominator_value": source_total if source_state != "missing" else None}, joint_state if joint_state != "present" else "present" if source_total else "missing")
    if metadata:
        _check(checks, "total_char_count", dbkey, "unknown" if joint_state != "present" else _truth(metadata["total_char_count"] == source_total == comps["indexed_unique_symbols"]["value"]),
               "declared total, supplied source symbols, and sum(N-1-overlap) agree; no completeness inference for matches", [dbkey, "source_symbol_total", "indexed_unique_symbols"])
    rows.insert(0, {"kind": "database_summary", "record_key": dbkey, "components": comps, "details": {"source_coverage": coverage_details}})
    return {"sources": sources, "source_state": source_state, "database_state": db_state,
            "source_ambiguity": {k:_merge(v) for k,v in ambiguous.items()}, "source_coverage": covered}


def _tuple_data(key):
    query, source, direction, anchor = key
    return {"query_record_key": query, "source_record_key": source, "direction": direction,
            "anchor": _number(anchor, "one_based_source_coordinate", [query, source])}


def _exact_components(sheet, parameters, result, context):
    rows, checks, issues = result["rows"], result["checks"], result["issues"]
    queries = [r for r in sheet["input_records"] if r["kind"] == "query"]
    sources = {r["record_key"]:r for r in context["sources"]}
    groups = {g["record_key"]:g for g in sheet["associations"]["query_groups"]}
    hit_targets = {h["hit_record_key"]:h for h in sheet["associations"]["hit_targets"]}
    segments = {s["record_key"]:s for s in sheet["database"]["segments"]} if sheet["database"] else {}
    hits = [r for r in sheet["native_rows"] if r["kind"] == "exactmatch_hit"]
    query_state = _state(sheet, "queries", "input")
    if any(not q["payload"]["valid"] or ("U" in q["payload"]["text"].upper() and parameters["alphabet_normalization"] != "rna_to_dna") for q in queries):
        query_state = "incompatible"
    hits_state = _state(sheet, "hits", "output")
    if any(i["code"] == "invalid_hits" for i in sheet["issues"]):
        hits_state = "incomplete"
    mode = sheet["operation"]["mode"]
    counts = {field:[] for field in ("Q", "H", "R")}
    for row in sheet["native_rows"]:
        if row["kind"] == "exactmatch_counts":
            for field in counts:
                if row["payload"][field] is not None:
                    counts[field].append((row["payload"][field], row["record_key"]))
    comps = {"query_occurrence_count": _number(len(queries) if query_state != "missing" else None, "query_occurrences", [q["record_key"] for q in queries], query_state)}
    occurrences = {o["occurrence_id"]:o for o in sheet["artifact_occurrences"]}
    for field, values in counts.items():
        state = "present" if len(values) == 1 else "missing" if not values else "failed"
        if len(values) == 1:
            oid = values[0][1].rsplit("#exactmatch_counts/",1)[0]
            occurrence = occurrences.get(oid)
            state = _state(sheet,occurrence["role"],occurrence["direction"]) if occurrence else "failed"
        comps["native_"+field] = _number(values[0][0] if len(values) == 1 else None,
            {"Q": "query_occurrences_with_raw_interval" if mode == "count_only" else "query_occurrences_with_native_locations",
             "H": "raw_fm_interval_occurrences" if mode == "count_only" else "native_emitted_location_occurrences",
             "R": "query_occurrences_with_no_raw_interval"}[field], [key for _,key in values], state)
    q,h,r = (comps["native_"+f]["value"] for f in ("Q","H","R"))
    native_available = all(comps["native_"+field]["state"] == "present" for field in ("Q","H","R"))
    counts_ok = ((q+r == len(queries) if mode == "count_only" else q+r <= len(queries)) and h >= q and ((h==0)==(q==0))) if native_available else None
    _check(checks, "native_query_population", None, _truth(counts_ok) if query_state == "present" else "unknown",
           "count-only Q+R=N; locations Q+R<=N because native filters can discard every raw match; H>=Q", ["native_Q", "native_H", "native_R", "query_occurrence_count"])
    comps["native_unclassified_queries"] = _number(len(queries)-q-r if native_available and query_state == "present" else None, "query_occurrences",
        {"formula": "query_occurrence_count-native_Q-native_R", "inputs": ["query_occurrence_count", "native_Q", "native_R"]}, "failed" if counts_ok is False and query_state == "present" else "present" if native_available and query_state == "present" else "missing")
    if counts_ok is False:
        issues.append(issue("count_mismatch", field="native_query_population", stage="calculate"))
    directions_known = isinstance(sheet["operation"]["settings"].get("--fwd_only"), bool)
    metadata = sheet["database"]["metadata"] if sheet["database"] else None
    enabled = ["f"] if sheet["operation"]["settings"].get("--fwd_only") or metadata and metadata["fwd_only"] else ["f","r"]
    observed, statuses = Counter(), Counter()
    duplicate_count = 0
    per_query = defaultdict(Counter)
    for row in hits:
        key,payload = row["record_key"],row["payload"]
        group = groups[payload["group_key"]]
        association = hit_targets.get(key, {"state": "unresolved", "candidates": []})
        length, anchor = len(payload["query_text"]), payload["anchor"]
        start,end = (anchor,anchor+length-1) if payload["direction"] == "f" else (anchor-length+1,anchor)
        candidate_results = []
        for candidate in association["candidates"]:
            source = sources.get(candidate["source_record_key"])
            bounds = 1 <= start <= end <= len(source["payload"]["sequence"]) if source else None
            source_text = source["payload"]["sequence"][start-1:end] if source and bounds else None
            comparison = _normal(source_text, parameters) if source_text is not None else None
            if comparison is not None and payload["direction"] == "r":
                comparison = comparison[::-1]
            symbols = comparison == _normal(payload["query_text"], parameters) if comparison is not None else None
            overlap = any(start <= b and a <= end for a,b in context["source_ambiguity"].get(candidate["source_record_key"], [])) if metadata else None
            source_ambiguous = any(c not in "ACGTU" for c in source_text.upper()) if source_text is not None else None
            membership = any(s["target_start"] <= start <= end <= s["target_start"]+s["length"]-1
                             for segkey in candidate["segment_record_keys"] for s in [segments[segkey]]) if candidate["segment_record_keys"] else None
            name_match = source["payload"]["name"] == payload["target_name"] if source else None
            for name,value,scope in (
                ("hit_bounds", bounds, "one-based inclusive f:[c,c+L-1], r:[c-L+1,c]"),
                ("hit_symbols", symbols, "literal source comparison; r reverses the source interval without complement"),
                ("hit_ambiguity", None if overlap is None or source_ambiguous is None else not overlap and not source_ambiguous, "no overlap with indexed ambiguity ranges or ambiguous supplied source symbols"),
                ("hit_index_membership", membership, "complete interval contained in a named index segment for this source ordinal"),
                ("hit_source_name", name_match, "index target name agrees with supplied occurrence at target_id")):
                _check(checks, name, key, _truth(value), scope, [candidate["source_record_key"], *candidate["segment_record_keys"]])
            for code,field,failed in (
                ("invalid_interval","bounds",bounds is False),
                ("symbol_mismatch","symbols",symbols is False),
                ("ambiguity_overlap","ambiguity",overlap is True or source_ambiguous is True),
                ("source_mismatch","index_membership",membership is False),
                ("source_mismatch","source_name",name_match is False)):
                if failed:
                    issues.append(issue(code,record_key=key,field=field,stage="calculate",
                                        detail={"source_record_key":candidate["source_record_key"]}))
            invalid = bounds is False or symbols is False or overlap is True or source_ambiguous is True or membership is False or name_match is False
            complete = (source is not None and source["payload"]["complete"] and source["payload"]["valid"]
                        and context["source_state"] == "present" and context["database_state"] == "present"
                        and all(v is True for v in (bounds,symbols,membership,name_match)) and overlap is False)
            candidate_results.append({"source_record_key": candidate["source_record_key"],
                                      "segment_record_keys": candidate["segment_record_keys"],
                                      "state": "invalid" if invalid else "valid" if complete else "unresolved",
                                      "source_interval_text": source_text, "compared_text": comparison})
        unique = group["state"] == "unique" and association["state"] == "unique"
        status = candidate_results[0]["state"] if unique and len(candidate_results) == 1 else "unresolved"
        if payload["direction"] not in enabled and (directions_known or metadata and metadata["fwd_only"]):
            status = "invalid"
            issues.append(issue("index_inconsistent",record_key=key,field="direction",stage="calculate"))
        if query_state != "present" and status == "valid":
            status = "unresolved"
        if unique and len(candidate_results) == 1:
            identity = (group["query_record_keys"][0], candidate_results[0]["source_record_key"], payload["direction"], anchor)
            observed[identity] += 1
            duplicate = observed[identity] > 1
            _check(checks, "hit_duplicate_tuple", key, "fail" if duplicate else "pass", "same query occurrence, source occurrence, native direction and anchor", [key])
            if duplicate:
                duplicate_count += 1
                issues.append(issue("duplicate_tuple", record_key=key, stage="calculate"))
            per_query[group["query_record_keys"][0]][status] += 1
        statuses[status] += 1
        rows.append({"kind": "location_validation", "record_key": key,
            "components": {"native_anchor": _number(anchor,"one_based_source_coordinate",[key]),
                           "query_length": _number(length,"symbols",[key]),
                           "interval_start": _number(start,"one_based_source_coordinate",[key]),
                           "interval_end": _number(end,"one_based_source_coordinate",[key])},
            "details": {"state": status, "direction": payload["direction"], "query_record_keys": group["query_record_keys"], "candidates": candidate_results}})
    measured = mode == "locations" and hits_state != "missing"
    for name,value in (("emitted_location_count",len(hits)), ("valid_location_count",statuses["valid"]),
                       ("invalid_location_count",statuses["invalid"]), ("unresolved_location_count",statuses["unresolved"])):
        comps[name] = _number(value if measured else None,"emitted_location_occurrences",[r["record_key"] for r in hits],hits_state if mode == "locations" else "missing")
    comps["duplicate_location_count"] = _number(duplicate_count if measured else None,"repeated_resolved_tuple_occurrences",[r["record_key"] for r in hits],hits_state if mode == "locations" else "missing")
    for status in ("valid","invalid","unresolved"):
        comps[status+"_location_fraction"] = _number(statuses[status]/len(hits) if measured and hits and hits_state == "present" else None,"fraction",
            {"numerator":status+"_location_count","denominator":"emitted_location_count","denominator_value":len(hits) if measured else None},
            hits_state if measured and hits_state != "present" else "present" if measured and hits else "missing")
    _check(checks, "native_location_count", None, "not_applicable" if mode == "count_only" else "unknown" if comps["native_H"]["state"] != "present" or hits_state != "present" else _truth(h == len(hits)),
           "native location H versus parsed emitted rows; does not assert literal validity", ["native_H","emitted_location_count"])
    _check(checks, "native_location_query_count", None, "not_applicable" if mode == "count_only" else "unknown" if comps["native_Q"]["state"] != "present" or hits_state != "present" else _truth(q == len(groups)),
           "native location Q versus emitted query groups; duplicate query occurrences stay separate", ["native_Q","query_groups"])
    _check(checks, "count_only_has_no_locations", None, ("unknown" if hits_state != "present" else _truth(not hits)) if mode == "count_only" else "not_applicable",
           "count-only output must contain no locations; missing file remains missing", ["hits"])
    for query in queries:
        key = query["record_key"]
        uncertain = (query_state != "present" or any(g["state"] == "unresolved" or
                     key in g["query_record_keys"] and g["state"] != "unique" for g in groups.values()))
        state = query_state if query_state != "present" else "incomplete" if uncertain else hits_state
        rows.append({"kind":"query_validation","record_key":key,
            "components": {status+"_location_count":_number(per_query[key][status] if measured and not uncertain else None,"location_occurrences",[key],state if mode == "locations" else "missing") for status in ("valid","invalid","unresolved")},
            "details":{"query_text":query["payload"]["text"]}})
    exhaustive = {"requested": parameters["exhaustive_literal_check"], "state":"not_requested", "expected_tuples":[], "missing_tuples":[], "extra_tuples":[]}
    if parameters["exhaustive_literal_check"]:
        available = (query_state == "present" and context["source_state"] == "present" and directions_known
                     and metadata is not None and metadata["dna_reader_compatibility"] == "compatible")
        comparable = available and measured and hits_state == "present" and statuses["unresolved"] == 0
        if available:
            expected = Counter()
            for query in queries:
                text = _normal(query["payload"]["text"], parameters)
                for source in sources.values():
                    sequence = _normal(source["payload"]["sequence"],parameters)
                    for direction in enabled:
                        needle = text if direction == "f" else text[::-1]
                        pos = sequence.find(needle)
                        while pos >= 0:
                            expected[(query["record_key"],source["record_key"],direction,pos+1 if direction=="f" else pos+len(text))] += 1
                            pos = sequence.find(needle,pos+1)
            exhaustive["expected_tuples"] = [_tuple_data(key) for key in expected.elements()]
            exhaustive["state"] = "compared" if comparable else "expected_only"
            comps["expected_literal_location_count"] = _number(sum(expected.values()),"literal_source_location_occurrences",[q["record_key"] for q in queries]+list(sources))
            if comparable:
                missing,extra = expected-observed,observed-expected
                exhaustive["missing_tuples"] = [_tuple_data(key) for key in missing.elements()]
                exhaustive["extra_tuples"] = [_tuple_data(key) for key in extra.elements()]
                comps["missing_literal_location_count"] = _number(sum(missing.values()),"location_occurrences",["expected_tuples","native_locations"])
                comps["extra_literal_location_count"] = _number(sum(extra.values()),"location_occurrences",["expected_tuples","native_locations"])
                _check(checks,"exhaustive_literal_agreement",None,_truth(not missing and not extra),"multiset of every complete supplied query/source occurrence, enabled direction and native anchor; aggregate equality alone is insufficient",["expected_tuples","native_locations"])
        else:
            exhaustive["state"] = "unavailable"
        if not comparable:
            _check(checks,"exhaustive_literal_agreement",None,"unknown","complete source/query populations, known directions and unambiguous complete native locations required",["queries","source_sequences","hits"])
    for name in ("expected_literal_location_count","missing_literal_location_count","extra_literal_location_count"):
        comps.setdefault(name,_number(None,"location_occurrences",["exhaustive_literal_check"],"missing"))
    rows.append({"kind":"exactmatch_summary","record_key":None,"components":comps,"details":{"exhaustive":exhaustive,"enabled_directions":enabled if directions_known else None}})


def calculate_hmmer_fm_components(sheet, *, parameters=None):
    """Recalculate from a saved F1 sheet and explicit validation parameters."""
    supplied = {} if parameters is None else deepcopy(parameters)
    result = {"schema":"hmmer_fm_components_v1","operation":deepcopy(sheet.get("operation")),
              "parameters":supplied,"rows":[],"checks":[],"issues":[]}
    if (not isinstance(supplied,dict) or set(supplied)-set(DEFAULT_PARAMETERS)
            or supplied.get("alphabet_normalization","none") not in ("none","rna_to_dna")
            or supplied.get("coordinate_policy","native_one_based") != "native_one_based"
            or type(supplied.get("exhaustive_literal_check",False)) is not bool):
        result["issues"].append(issue("invalid_parameters",stage="calculate"))
        return result
    resolved = {**DEFAULT_PARAMETERS,**supplied}
    result["parameters"] = resolved
    if sheet.get("schema") != "hmmer_fm_sheet_v1" or any(i["code"] == "invalid_operation" for i in sheet["issues"]):
        result["issues"].append(issue("invalid_operation",stage="calculate"))
        return result
    result["issues"].extend(deepcopy(sheet["issues"]))
    context = _build_components(sheet,resolved,result)
    if sheet["operation"]["program"] == "hmmerfm-exactmatch":
        _exact_components(sheet,resolved,result,context)
    for check in result["checks"]:
        if check["state"] == "fail" and check["name"] in {"counter_rows","bwt_text_consistency","suffix_samples","block_offsets","block_overlap","total_char_count"}:
            result["issues"].append(issue("index_inconsistent",record_key=check["record_key"],field=check["name"],stage="calculate"))
    return result
