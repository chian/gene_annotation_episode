"""Pure readers for the explicitly declared HMMER 3.4 FM writer format.

These functions consume supplied bytes only. They retain native populations and
do not execute, repair, or certify an index. See the 261/F1 contract and the
264/FIELDS.md companion for the public, JSON-serializable subshapes.
"""
from __future__ import annotations

from copy import deepcopy
from bisect import bisect_left, bisect_right
from collections import Counter
import hashlib
import re
import struct


OCCURRENCE_FIELDS = frozenset({"occurrence_id", "direction", "role", "ordinal",
                              "artifact_ref", "sha256", "size_bytes", "completeness"})
PRODUCER_FIELDS = frozenset({"format", "engine_version", "byte_order", "uint8_bytes",
                            "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes"})
SOURCE_BINDING_FIELDS = frozenset({"database_occurrence_id", "source_occurrence_ids",
                                  "source_sha256s", "producer_attempt_id"})
ROW_FIELDS = {
    "index_parameters": frozenset({"parameter", "token", "value", "state"}),
    "exactmatch_hit": frozenset({"group_key", "query_text", "anchor", "anchor_token",
                                 "direction", "target_name"}),
    "exactmatch_counts": frozenset({"Q", "H", "R", "Q_token", "H_token", "R_token",
                                    "population"}),
    "diagnostic": frozenset({"text", "category", "numerical_state"}),
}
NATIVE_STRUCTURE_ISSUE_CODES = frozenset({
    "native_segment_bounds", "native_ambiguity_bounds", "native_block_pair",
    "native_metadata_partition", "native_sa_invalid", "native_counter_invalid",
    "native_bwt_invalid", "native_index_bounds",
})
ISSUE_CODES = frozenset({
    "invalid_occurrence", "size_mismatch", "digest_mismatch", "partial_artifact",
    "unknown_completeness", "invalid_producer_contract", "truncated_header",
    "invalid_header", "truncated_segment", "invalid_string", "truncated_ambiguity",
    "truncated_block", "truncated_array", "invalid_block", "trailing_bytes",
    "unsupported_alphabet", "dna_reader_incompatible", "invalid_symbols",
    "invalid_operation", "invalid_payload", "duplicate_occurrence_id",
    "missing_artifact", "multiple_databases", "unsupported_sequence_format",
    "invalid_fasta", "invalid_query", "invalid_hits", "invalid_counts",
    "source_binding_mismatch", "query_association_unresolved",
    "target_association_unresolved", "unreliable_diagnostic", "invalid_parameters",
    "source_mismatch", "invalid_interval", "symbol_mismatch", "ambiguity_overlap",
    "duplicate_tuple", "count_mismatch", "index_inconsistent", "incomplete_comparison",
    "native_reader_header_incompatible",
}) | NATIVE_STRUCTURE_ISSUE_CODES

HEADER_FIELDS = ("fwd_only", "alph_type", "alph_size", "charBits", "freq_SA",
                 "freq_cnt_sb", "freq_cnt_b", "block_count", "seq_count",
                 "ambiguity_range_count", "total_char_count")
SEGMENT_FIELDS = ("target_id", "target_start", "fm_start", "length", "name_length",
                  "acc_length", "source_length", "desc_length")
BLOCK_FIELDS = ("N", "term_loc", "seq_offset", "ambig_offset", "overlap", "seq_cnt", "ambig_cnt")
ALPHABETS = {0: "ACGT", 4: "ACDEFGHIKLMNPQRSTVWYBJZOUX"}


def issue(code, *, record_key=None, field=None, stage="extract", detail=None):
    """Closed issue vocabulary; detail is factual data, never an instruction."""
    if code not in ISSUE_CODES:
        raise ValueError("unknown FM issue code")
    return {"code": code, "record_key": record_key, "field": field,
            "stage": stage, "detail": detail}


def _locator(start, end, ordinal, line_start=None, line_end=None):
    return {"byte_start": start, "byte_end": end, "line_start": line_start,
            "line_end": line_end, "record_ordinal": ordinal}


def _occurrence_issues(content, occurrence):
    issues = []
    valid = isinstance(occurrence, dict) and set(occurrence) == OCCURRENCE_FIELDS
    if valid:
        valid = (isinstance(occurrence["occurrence_id"], str) and bool(occurrence["occurrence_id"])
                 and occurrence["direction"] in ("input", "output")
                 and isinstance(occurrence["role"], str) and bool(occurrence["role"])
                 and type(occurrence["ordinal"]) is int and occurrence["ordinal"] >= 0
                 and isinstance(occurrence["artifact_ref"], str) and bool(occurrence["artifact_ref"])
                 and isinstance(occurrence["sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", occurrence["sha256"]) is not None
                 and type(occurrence["size_bytes"]) is int and occurrence["size_bytes"] >= 0
                 and occurrence["completeness"] in ("complete", "partial", "unknown"))
    key = occurrence.get("occurrence_id") if isinstance(occurrence, dict) else None
    if not valid:
        issues.append(issue("invalid_occurrence", record_key=key))
    if isinstance(occurrence, dict):
        if occurrence.get("size_bytes") != len(content):
            issues.append(issue("size_mismatch", record_key=key, field="size_bytes",
                                detail={"supplied": occurrence.get("size_bytes"), "actual": len(content)}))
        digest = hashlib.sha256(content).hexdigest()
        if occurrence.get("sha256") != digest:
            issues.append(issue("digest_mismatch", record_key=key, field="sha256",
                                detail={"supplied": occurrence.get("sha256"), "actual": digest}))
        if occurrence.get("completeness") == "partial":
            issues.append(issue("partial_artifact", record_key=key))
        elif occurrence.get("completeness") != "complete":
            issues.append(issue("unknown_completeness", record_key=key))
    return issues


def _valid_producer(contract):
    return (isinstance(contract, dict) and set(contract) == PRODUCER_FIELDS
            and contract.get("format") == "hmmer_fm_3_4"
            and contract.get("engine_version") == "3.4"
            and contract.get("byte_order") in ("little", "big")
            and all(type(contract.get(k)) is int and contract[k] == v for k, v in
                    {"uint8_bytes": 1, "uint16_bytes": 2, "uint32_bytes": 4,
                     "uint64_bytes": 8, "int32_bytes": 4}.items()))


class _ShortRead(Exception):
    pass


class _Reader:
    def __init__(self, content, endian):
        self.content, self.endian, self.offset = content, endian, 0

    def take(self, count):
        if count < 0 or count > len(self.content) - self.offset:
            raise _ShortRead
        start = self.offset
        self.offset += count
        return self.content[start:self.offset]

    def unpack(self, fmt):
        return struct.unpack(self.endian + fmt, self.take(struct.calcsize(self.endian + fmt)))

    def array(self, count, fmt, row_width=1):
        """Bound actual decoding by bytes; retain full rows from a short tail."""
        start = self.offset
        width = struct.calcsize(self.endian + fmt)
        available = min(count, (len(self.content) - start) // (width * row_width))
        raw = self.take(available * row_width * width)
        flat = [v[0] for v in struct.iter_unpack(self.endian + fmt, raw)]
        values = flat if row_width == 1 else [flat[i:i+row_width] for i in range(0, len(flat), row_width)]
        return {"values": values, "expected_count": count, "element_bytes": width,
                "row_width": row_width, "complete": available == count,
                "locator": _locator(start, self.offset, None)}


def _symbols(values, n, alphabet):
    if len(alphabet) == 4:
        return "".join(alphabet[(values[i // 4] >> (6 - 2 * (i % 4))) & 3] for i in range(n))
    if any(value >= len(alphabet) for value in values[:n]):
        return None
    return "".join(alphabet[value] for value in values[:n])


def _native_structure_issues(result):
    """Source-derived imported-index invariants, using supplied decoded data.

    This validates indices, LF reachability, sample values and native checkpoints
    before consumers call unsafe C readers. It does not invoke a calculator,
    search, or repair; native boundary and post-free bugs remain native bugs.
    """
    metadata, segments, ranges = result["metadata"], result["segments"], result["ambiguity_ranges"]
    problems = []
    forward = {b["block_ordinal"]:b for b in result["blocks"] if b["section"] == "forward"}
    seq_cursor, ambig_cursor = 0, 0
    alphabet, size = metadata["alphabet_symbols"], metadata["alph_size"]
    for block in result["blocks"]:
        key,h = block["record_key"],block["header"]
        n = h["N"]
        if not 2 <= n <= 0x7FFFFFFF or h["seq_cnt"] == 0:
            problems.append(issue("native_index_bounds",record_key=key,field="N_seq_cnt"))
        first = forward.get(block["block_ordinal"])
        if block["section"] == "forward":
            if h["seq_offset"] != seq_cursor or h["ambig_offset"] != ambig_cursor:
                problems.append(issue("native_metadata_partition",record_key=key))
            seq_cursor += h["seq_cnt"]
            ambig_cursor += h["ambig_cnt"]
        elif first is None or any(h[f] != first["header"][f] for f in ("N","seq_offset","ambig_offset","seq_cnt","ambig_cnt")) or h["overlap"] != 0:
            problems.append(issue("native_block_pair",record_key=key))
        block_segments = segments[h["seq_offset"]:h["seq_offset"]+h["seq_cnt"]]
        block_ranges = ranges[h["ambig_offset"]:h["ambig_offset"]+h["ambig_cnt"]]
        position = 0
        for segment in block_segments:
            end = segment["target_start"] + segment["length"] - 1
            if (segment["fm_start"] != position or segment["length"] <= 0
                    or segment["target_start"] < 1 or end > 0xFFFFFFFFFFFFFFFF
                    or end > metadata["total_char_count"] or segment["target_id"] > 0x7FFFFFFF
                    or segment["fm_start"] + segment["length"] > n-1):
                problems.append(issue("native_segment_bounds",record_key=segment["record_key"],detail={"block_record_key":key}))
            position = segment["fm_start"] + segment["length"]
        if position != n-1 or len(block_segments) != h["seq_cnt"]:
            problems.append(issue("native_segment_bounds",record_key=key,field="block_partition"))
        previous_upper = -1
        for interval in block_ranges:
            if not previous_upper < interval["lower"] <= interval["upper"] < n-1:
                problems.append(issue("native_ambiguity_bounds",record_key=interval["record_key"],detail={"block_record_key":key}))
            previous_upper = interval["upper"]
        if len(block_ranges) != h["ambig_cnt"]:
            problems.append(issue("native_ambiguity_bounds",record_key=key,field="range_slice"))
        bwt = block["decoded"]["bwt"]
        text = first["decoded"]["text"] if first else None
        if bwt is None or text is None or len(bwt) != n or len(text) != n or h["term_loc"] >= n:
            problems.append(issue("native_bwt_invalid",record_key=key,field="symbols_or_length"))
            continue
        codes = [alphabet.index(c) for c in bwt]
        if codes[h["term_loc"]] != 0 or text[-1] != alphabet[0]:
            problems.append(issue("native_bwt_invalid",record_key=key,field="sentinel_encoding"))
        # Checkpoints are memory indices in native LF traversal, not just scores.
        # Compare every row exactly; in-range fabricated rows can still form cycles.
        expected_b, expected_sb = [[0]*size], [[0]*size]
        total,partial = [0]*size,[0]*size
        for pos,code in enumerate(codes,1):
            total[code] += 1
            partial[code] += 1
            if pos % metadata["freq_cnt_b"] == 0:
                expected_b.append([v % 65536 for v in partial])
            if pos % metadata["freq_cnt_sb"] == 0:
                expected_sb.append(list(total))
                partial = [0]*size
        if n % metadata["freq_cnt_b"]:
            expected_b.append([v % 65536 for v in partial])
        else:
            expected_b[-1] = [v % 65536 for v in partial]
        if n % metadata["freq_cnt_sb"]:
            expected_sb.append(list(total))
        else:
            expected_sb[-1] = list(total)
        for field,expected in (("counters_b",expected_b),("counters_sb",expected_sb)):
            if block["arrays"][field]["values"] != expected:
                problems.append(issue("native_counter_invalid",record_key=key,field=field))
        letters = [c+1 for c in codes]
        letters[h["term_loc"]] = 0
        frequencies = Counter(letters)
        cumulative,cursor = {},0
        for code in range(size+1):
            cumulative[code],cursor = cursor,cursor+frequencies[code]
        seen = Counter()
        lf = []
        for code in letters:
            lf.append(cumulative[code]+seen[code])
            seen[code] += 1
        expected_text = text[:-1][::-1] if block["section"] == "forward" else text[:-1]
        expected_codes = [alphabet.index(c)+1 for c in expected_text]+[0]
        row,suffix,visited,mismatches = h["term_loc"],0,set(),0
        samples = block["arrays"].get("SA",{}).get("values")
        bad_samples = []
        for _ in range(n):
            if row in visited:
                break
            visited.add(row)
            if letters[row] != expected_codes[(suffix-1)%n]:
                mismatches += 1
            if samples is not None and row and row % metadata["freq_SA"] == 0:
                index = row//metadata["freq_SA"]
                if samples[index] != suffix:
                    bad_samples.append(index)
            row,suffix = lf[row],(suffix-1)%n
        if len(visited) != n or row != h["term_loc"] or mismatches:
            problems.append(issue("native_bwt_invalid",record_key=key,field="lf_cycle_text",
                                  detail={"visited_rows":len(visited),"symbol_mismatches":mismatches}))
        if samples is not None:
            for index,value in enumerate(samples):
                unused = index == 0 or index*metadata["freq_SA"] >= n
                if (unused and value != 0) or (not unused and value >= n-1):
                    bad_samples.append(index)
            if bad_samples:
                problems.append(issue("native_sa_invalid",record_key=key,field="SA",detail={"sample_indices":sorted(set(bad_samples))}))
    if seq_cursor != len(segments) or ambig_cursor != len(ranges):
        problems.append(issue("native_metadata_partition",record_key=result["occurrence"]["occurrence_id"]))
    return problems


def extract_hmmer_fm_database(content: bytes, *, occurrence, producer_contract):
    """Decode the complete supplied binary, including partial trailing arrays.

    The native ABI must be supplied, never inferred from the host or a suffix.
    Amino writer data are decoded but downstream DNA-reader compatibility fails.
    """
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    result = {"schema": "hmmer_fm_extraction_v1", "occurrence": deepcopy(occurrence),
              "producer_contract": deepcopy(producer_contract), "metadata": None,
              "segments": [], "ambiguity_ranges": [], "blocks": [],
              "population": {"state": "unsupported", "complete": False,
                             "decoded_segment_count": None, "decoded_ambiguity_range_count": None,
                             "decoded_block_section_count": None, "body_complete": False},
              "issues": _occurrence_issues(content, occurrence)}
    issues = result["issues"]
    oid = occurrence.get("occurrence_id", "") if isinstance(occurrence, dict) else ""
    if not _valid_producer(producer_contract):
        issues.append(issue("invalid_producer_contract", record_key=oid))
        return result
    if any(i["code"] == "invalid_occurrence" for i in issues):
        result["population"]["state"] = "invalid"
        return result
    reader = _Reader(content, "<" if producer_contract["byte_order"] == "little" else ">")
    population = result["population"]
    try:
        header = dict(zip(HEADER_FIELDS, reader.unpack("BBBBIIIHIIQ")))
    except _ShortRead:
        issues.append(issue("truncated_header", record_key=oid, detail={"available_bytes": len(content), "required_bytes": 34}))
        population["state"] = "partial"
        return result
    result["metadata"] = {**header, "alphabet_symbols": ALPHABETS.get(header["alph_type"]),
                          "storage_encoding": "dna_2bit" if header["alph_type"] == 0 else "amino_uint8" if header["alph_type"] == 4 else None,
                          "dna_reader_compatibility": "compatible" if header["alph_type"] == 0 else "incompatible",
                          "actual_bytes": len(content), "header_locator": _locator(0, 34, None)}
    if header["alph_type"] not in ALPHABETS:
        issues.append(issue("unsupported_alphabet", record_key=oid, field="alph_type", detail=header["alph_type"]))
        return result
    expected_size, expected_bits = (4, 2) if header["alph_type"] == 0 else (26, 5)
    if (header["fwd_only"] not in (0, 1) or header["alph_size"] != expected_size
            or header["charBits"] != expected_bits
            or header["freq_SA"] <= 0 or header["freq_SA"] & (header["freq_SA"] - 1)
            or header["freq_cnt_sb"] != 65536
            or not 32 <= header["freq_cnt_b"] <= 4096
            or header["freq_cnt_b"] & (header["freq_cnt_b"] - 1)):
        issues.append(issue("invalid_header", record_key=oid, detail=header))
        population["state"] = "invalid"
        return result
    if header["alph_type"] == 4:
        issues.append(issue("dna_reader_incompatible", record_key=oid, field="alph_type", detail=4))
    if header["alph_type"] == 0 and (header["freq_SA"] > 10000 or header["freq_cnt_b"] % 64):
        result["metadata"]["dna_reader_compatibility"] = "incompatible"
        issues.append(issue("native_reader_header_incompatible", record_key=oid,
                            detail={"freq_SA":header["freq_SA"],"freq_cnt_b":header["freq_cnt_b"]}))
    population.update(state="partial", decoded_segment_count=0, decoded_ambiguity_range_count=0,
                      decoded_block_section_count=0)

    def finish(body_complete=False):
        population.update(decoded_segment_count=len(result["segments"]),
                          decoded_ambiguity_range_count=len(result["ambiguity_ranges"]),
                          decoded_block_section_count=len(result["blocks"]), body_complete=body_complete)
        if body_complete:
            issues.extend(_native_structure_issues(result))
        invalid = any(i["code"] in ({"invalid_occurrence", "size_mismatch", "digest_mismatch",
                                    "invalid_string", "invalid_block", "invalid_symbols", "trailing_bytes"} | NATIVE_STRUCTURE_ISSUE_CODES) for i in issues)
        population["complete"] = body_complete and occurrence.get("completeness") == "complete" and not invalid
        population["state"] = "invalid" if invalid else "decoded" if population["complete"] else "partial"
        return result

    # Iteration is bounded by successful reads, so hostile native counts cannot allocate
    # count-sized lists or run count iterations when the necessary bytes are absent.
    for ordinal in range(header["seq_count"]):
        start = reader.offset
        key = f"{oid}#segment/{ordinal}"
        try:
            row = dict(zip(SEGMENT_FIELDS, reader.unpack("IQIIHHHH")))
            strings = {}
            for field in ("name", "acc", "source", "desc"):
                raw = reader.take(row[field + "_length"] + 1)
                strings[field] = raw[:-1].decode("latin1")
                if raw[-1:] != b"\0" or b"\0" in raw[:-1]:
                    issues.append(issue("invalid_string", record_key=key, field=field))
            result["segments"].append({"record_key": key, "locator": _locator(start, reader.offset, ordinal), **row, **strings})
        except _ShortRead:
            issues.append(issue("truncated_segment", record_key=key, detail={"byte_offset": reader.offset}))
            return finish()
    for ordinal in range(header["ambiguity_range_count"]):
        start = reader.offset
        key = f"{oid}#ambiguity/{ordinal}"
        try:
            lower, upper = reader.unpack("ii")
        except _ShortRead:
            issues.append(issue("truncated_ambiguity", record_key=key, detail={"byte_offset": start}))
            return finish()
        result["ambiguity_ranges"].append({"record_key": key, "locator": _locator(start, reader.offset, ordinal),
                                            "lower": lower, "upper": upper})
    section_count = 1 if header["fwd_only"] else 2
    for ordinal in range(header["block_count"] * section_count):
        start = reader.offset
        block_ordinal, section_ordinal = divmod(ordinal, section_count)
        section = "forward" if section_ordinal == 0 else "reverse"
        key = f"{oid}#block/{block_ordinal}/{section}"
        try:
            block_header = dict(zip(BLOCK_FIELDS, reader.unpack("QIIIIII")))
        except _ShortRead:
            issues.append(issue("truncated_block", record_key=key, detail={"byte_offset": start}))
            return finish()
        n = block_header["N"]
        block = {"record_key": key, "locator": _locator(start, reader.offset, ordinal),
                 "block_ordinal": block_ordinal, "section": section, "header": block_header,
                 "arrays": {}, "decoded": {"text": None, "bwt": None,
                     "text_sentinel_index": n - 1 if section == "forward" and n else None,
                     "bwt_sentinel_index": block_header["term_loc"], "symbol_kind": "generated_index"},
                 "complete": False}
        result["blocks"].append(block)
        if (n < 1 or n > 0xFFFFFFFF or block_header["term_loc"] >= n
                or block_header["overlap"] >= n
                or block_header["seq_offset"] + block_header["seq_cnt"] > header["seq_count"]
                or block_header["ambig_offset"] + block_header["ambig_cnt"] > header["ambiguity_range_count"]):
            issues.append(issue("invalid_block", record_key=key, detail=block_header))
        if n < 1 or n > 0xFFFFFFFF:
            return finish()
        packed = (n + 3) // 4 if header["alph_type"] == 0 else n
        spec = []
        if section == "forward":
            spec.append(("T", packed, "B", 1))
        spec.append(("BWT", packed, "B", 1))
        if section == "forward":
            spec.append(("SA", 1 + n // header["freq_SA"], "I", 1))
        spec.extend((("counters_b", 1 + (n + header["freq_cnt_b"] - 1) // header["freq_cnt_b"], "H", expected_size),
                     ("counters_sb", 1 + (n + header["freq_cnt_sb"] - 1) // header["freq_cnt_sb"], "I", expected_size)))
        for field, count, fmt, width in spec:
            array = reader.array(count, fmt, width)
            block["arrays"][field] = array
            block["locator"]["byte_end"] = reader.offset
            if field in ("T", "BWT") and array["complete"]:
                decoded = _symbols(array["values"], n, ALPHABETS[header["alph_type"]])
                if decoded is None:
                    issues.append(issue("invalid_symbols", record_key=key, field=field))
                block["decoded"]["text" if field == "T" else "bwt"] = decoded
            if not array["complete"]:
                issues.append(issue("truncated_array", record_key=key, field=field,
                                    detail={"expected_rows": count, "decoded_rows": len(array["values"]),
                                            "remaining_bytes": len(content) - reader.offset}))
                return finish()
        block["complete"] = True
    if reader.offset != len(content):
        issues.append(issue("trailing_bytes", record_key=oid,
                            detail={"byte_offset": reader.offset, "count": len(content) - reader.offset}))
    return finish(reader.offset == len(content))


def _lines(content):
    # LF is the native query delimiter. splitlines() would silently remove CR.
    start = 0
    for ordinal, piece in enumerate(content.split(b"\n")):
        if start == len(content):
            break
        has_lf = start + len(piece) < len(content)
        end = start + len(piece) + int(has_lf)
        yield ordinal, start, end, piece, has_lf
        start = end


def _fasta(content, occurrence, start_ordinal, issues):
    oid = occurrence["occurrence_id"]
    records = []
    active = None
    for line, start, end, raw, lf in _lines(content):
        text = raw.decode("latin1")
        if text.startswith(">"):
            if active is not None:
                active["locator"].update(byte_end=start, line_end=line)
            ordinal = len(records)
            header = text[1:].rstrip("\r")
            parts = header.split(None, 1)
            active = {"kind": "fasta", "record_key": f"{oid}#fasta/{ordinal}",
                      "occurrence_id": oid, "locator": _locator(start, end, ordinal, line + 1, line + 1),
                      "source_ordinal": start_ordinal + ordinal,
                      "payload": {"header": header, "raw_header": text + ("\n" if lf else ""), "name": parts[0] if parts else "",
                                  "description": parts[1] if len(parts) > 1 else "", "sequence": "",
                                  "sequence_lines": [], "complete": occurrence["completeness"] == "complete",
                                  "valid": bool(parts)}}
            records.append(active)
        elif active is None:
            if text.strip():
                issues.append(issue("invalid_fasta", record_key=oid, field="preamble", detail={"line": line + 1}))
            continue
        else:
            active["payload"]["sequence_lines"].append(text + ("\n" if lf else ""))
            symbols = "".join(c for c in text if c not in " \t\r\v\f")
            active["payload"]["sequence"] += symbols
            if not re.fullmatch(r"[A-Za-z*.-]*", symbols):
                active["payload"]["valid"] = False
        active["locator"].update(byte_end=end, line_end=line + 1)
    for record in records:
        if not record["payload"]["sequence"] or not record["payload"]["valid"]:
            record["payload"]["valid"] = False
            issues.append(issue("invalid_fasta", record_key=record["record_key"]))
    if content and not records:
        issues.append(issue("invalid_fasta", record_key=oid, field="records"))
    return records


def _queries(content, occurrence, issues):
    records = []
    for ordinal, start, end, raw, lf in _lines(content):
        value = raw.decode("latin1")
        valid = bool(value) and len(raw) <= 254 and re.fullmatch(r"[ACGTUacgtu]+", value) is not None
        key = f"{occurrence['occurrence_id']}#query/{ordinal}"
        records.append({"kind": "query", "record_key": key, "occurrence_id": occurrence["occurrence_id"],
                        "locator": _locator(start, end, ordinal, ordinal + 1, ordinal + 1), "source_ordinal": None,
                        "payload": {"text": value, "raw_line": value + ("\n" if lf else ""),
                                    "line_ending": "LF" if lf else "none", "valid": valid,
                                    "complete": occurrence["completeness"] == "complete"}})
        if not valid:
            issues.append(issue("invalid_query", record_key=key, detail={"length": len(raw), "has_CR": b"\r" in raw}))
    return records


def _row(rows, kind, occurrence, start, end, line, payload, counters):
    ordinal = counters.get(kind, 0)
    counters[kind] = ordinal + 1
    key = f"{occurrence['occurrence_id']}#{kind}/{ordinal}"
    assert set(payload) == ROW_FIELDS[kind]
    row = {"kind": kind, "record_key": key, "locator": _locator(start, end, ordinal, line + 1, line + 1), "payload": payload}
    rows.append(row)
    return row


def _diagnostics(content, occurrence, rows, issues, mode):
    counters = {}
    for line, start, end, raw, _ in _lines(content):
        text = raw.decode("latin1")
        hit = re.fullmatch(r"hit:\s*(\d+)\s*\((\d+)\)\s*", text)
        miss = re.fullmatch(r"miss:\s*(\d+)\s*", text)
        param = re.fullmatch(r"#\s*(bin_length|suffix array sample rate|alphabet|input is asserted to be)\s*:\s*(.*?)\s*", text)
        if hit or miss:
            tokens = [hit[1], hit[2], None] if hit else [None, None, miss[1]]
            _row(rows, "exactmatch_counts", occurrence, start, end, line,
                 {**dict(zip(("Q", "H", "R"), [int(x) if x is not None else None for x in tokens])),
                  **dict(zip(("Q_token", "H_token", "R_token"), tokens)),
                  "population": "raw_fm_intervals" if mode == "count_only" else "native_emitted_locations"}, counters)
        elif param:
            numeric = param[1] in ("bin_length", "suffix array sample rate")
            token = param[2]
            valid = not numeric or token.isdigit()
            _row(rows, "index_parameters", occurrence, start, end, line,
                 {"parameter": param[1], "token": token,
                  "value": int(token) if numeric and valid else token if not numeric else None,
                  "state": "present" if valid else "failed"}, counters)
        else:
            unreliable = text.strip().startswith(("occ calls:", "occ/sec:"))
            category = "unsafe_post_free_statistic" if unreliable else "runtime" if text.startswith("run time:") else "native_text"
            row = _row(rows, "diagnostic", occurrence, start, end, line,
                       {"text": text, "category": category, "numerical_state": "incompatible" if unreliable else "not_interpreted"}, counters)
            if unreliable:
                issues.append(issue("unreliable_diagnostic", record_key=row["record_key"]))
            if text.strip().startswith(("hit:", "miss:")):
                issues.append(issue("invalid_counts", record_key=row["record_key"]))


def _hits(content, occurrence, rows, groups, issues):
    active = None
    counters = {}
    group_ordinal = 0
    for line, start, end, raw, _ in _lines(content):
        text = raw.decode("latin1")
        if not text:
            active = None
            continue
        hit = re.fullmatch(r"\s+(-?\d+)\s+([fr])\s+(\S+)\s*", text)
        if hit and active is not None:
            row = _row(rows, "exactmatch_hit", occurrence, start, end, line,
                       {"group_key": active["record_key"], "query_text": active["query_text"],
                        "anchor": int(hit[1]), "anchor_token": hit[1], "direction": hit[2], "target_name": hit[3]}, counters)
            active["hit_record_keys"].append(row["record_key"])
            active["locator"].update(byte_end=end, line_end=line + 1)
        elif not text[0].isspace() and re.fullmatch(r"[ACGTUacgtu]+", text):
            ordinal = group_ordinal
            group_ordinal += 1
            active = {"record_key": f"{occurrence['occurrence_id']}#query_group/{ordinal}",
                      "occurrence_id": occurrence["occurrence_id"], "query_text": text,
                      "query_record_keys": [], "state": "unresolved", "hit_record_keys": [],
                      "locator": _locator(start, end, ordinal, line + 1, line + 1)}
            groups.append(active)
        else:
            row = _row(rows, "diagnostic", occurrence, start, end, line,
                       {"text": text, "category": "malformed_hit", "numerical_state": "failed"}, counters)
            issues.append(issue("invalid_hits", record_key=row["record_key"]))


def _associate_queries(groups, queries, issues):
    """All viable order-preserving subsequence mappings; no first-name join."""
    earliest, latest = [], []
    cursor = 0
    feasible = True
    for group in groups:
        while cursor < len(queries) and queries[cursor]["payload"]["text"] != group["query_text"]:
            cursor += 1
        if cursor == len(queries):
            feasible = False
        earliest.append(cursor)
        cursor += 1
    cursor = len(queries) - 1
    for group in reversed(groups):
        while cursor >= 0 and queries[cursor]["payload"]["text"] != group["query_text"]:
            cursor -= 1
        latest.append(cursor)
        cursor -= 1
    latest.reverse()
    by_text = {}
    for ordinal, query in enumerate(queries):
        by_text.setdefault(query["payload"]["text"], []).append(ordinal)
    for i, group in enumerate(groups):
        indices = by_text.get(group["query_text"], [])
        candidates = [queries[j]["record_key"] for j in indices[bisect_left(indices,earliest[i]):bisect_right(indices,latest[i])]] if feasible else []
        group["query_record_keys"] = candidates
        group["state"] = "unique" if len(candidates) == 1 else "ambiguous" if candidates else "unresolved"
        if group["state"] != "unique" or not group["hit_record_keys"]:
            issues.append(issue("query_association_unresolved", record_key=group["record_key"], detail={"candidate_keys": candidates}))


def populate_hmmer_fm_sheet(*, operation, inputs, outputs, producer_contract, source_binding=None):
    """Populate one operation sheet from occurrence-bearing role payloads."""
    sheet = {"schema": "hmmer_fm_sheet_v1", "operation": deepcopy(operation),
             "artifact_occurrences": [], "producer_contract": deepcopy(producer_contract),
             "source_binding": deepcopy(source_binding), "database": None, "input_records": [],
             "native_rows": [], "associations": {"source_binding_state": "unknown", "segments": [],
                                                  "query_groups": [], "hit_targets": []}, "issues": []}
    issues, rows = sheet["issues"], sheet["native_rows"]
    valid_operation = (isinstance(operation, dict) and set(operation) == {"program", "mode", "engine_version", "settings"}
                       and operation.get("engine_version") == "3.4" and isinstance(operation.get("settings"), dict)
                       and isinstance(operation.get("program"),str) and isinstance(operation.get("mode"),str)
                       and (operation.get("program"), operation.get("mode")) in
                       {("makehmmerdb", "build"), ("hmmerfm-exactmatch", "locations"), ("hmmerfm-exactmatch", "count_only")})
    if not valid_operation:
        issues.append(issue("invalid_operation", stage="populate"))
        return sheet
    is_build = operation["program"] == "makehmmerdb"
    mode = operation["mode"]
    roles = {"input": {"sequences"} if is_build else {"queries", "fm_database", "source_sequences"},
             "output": {"fm_database", "stdout", "stderr"} if is_build else {"hits", "stdout", "stderr"}}
    payloads = {"input": {}, "output": {}}
    seen = set()
    for direction, mapping in (("input", inputs), ("output", outputs)):
        if not isinstance(mapping, dict):
            issues.append(issue("invalid_payload", field=direction, stage="populate"))
            continue
        for role, items in mapping.items():
            if role not in roles[direction] or not isinstance(items, list):
                issues.append(issue("invalid_payload", field=role, stage="populate"))
                continue
            payloads[direction][role] = []
            for ordinal, item in enumerate(items):
                if not isinstance(item, dict) or set(item) != {"occurrence", "content"} or not isinstance(item.get("content"), bytes):
                    issues.append(issue("invalid_payload", field=role, stage="populate", detail={"ordinal": ordinal}))
                    continue
                occurrence, content = item["occurrence"], item["content"]
                occ_issues = _occurrence_issues(content, occurrence)
                issues.extend(occ_issues)
                if any(i["code"] == "invalid_occurrence" for i in occ_issues):
                    continue
                sheet["artifact_occurrences"].append(deepcopy(occurrence))
                oid = occurrence["occurrence_id"]
                if occurrence["direction"] != direction or occurrence["role"] != role or occurrence["ordinal"] != ordinal:
                    issues.append(issue("invalid_occurrence", record_key=oid, field="role_direction_ordinal"))
                if oid in seen:
                    issues.append(issue("duplicate_occurrence_id", record_key=oid))
                    continue
                seen.add(oid)
                payloads[direction][role].append(item)
    for direction, required in roles.items():
        for role in sorted(required):
            if not payloads[direction].get(role):
                issues.append(issue("missing_artifact", field=role, stage="populate", detail={"direction": direction}))
    source_role = "sequences" if is_build else "source_sequences"
    source_items = payloads["input"].get(source_role, [])
    source_count = 0
    for item in source_items:
        informat = operation["settings"].get("--informat", "fasta")
        if is_build and informat not in (None, "fasta", "fa"):
            issues.append(issue("unsupported_sequence_format", record_key=item["occurrence"]["occurrence_id"], detail=informat))
            continue
        records = _fasta(item["content"], item["occurrence"], source_count, issues)
        source_count += len(records)
        sheet["input_records"].extend(records)
    for item in payloads["input"].get("queries", []):
        sheet["input_records"].extend(_queries(item["content"], item["occurrence"], issues))
    database_items = payloads["output" if is_build else "input"].get("fm_database", [])
    if len(database_items) == 1:
        item = database_items[0]
        sheet["database"] = extract_hmmer_fm_database(item["content"], occurrence=item["occurrence"], producer_contract=producer_contract)
        issues.extend(sheet["database"]["issues"])
    elif len(database_items) > 1:
        issues.append(issue("multiple_databases", stage="populate"))
    if source_binding is not None:
        valid = (isinstance(source_binding, dict) and set(source_binding) == SOURCE_BINDING_FIELDS
                 and len(database_items) == 1 and bool(source_items)
                 and source_binding.get("database_occurrence_id") == database_items[0]["occurrence"]["occurrence_id"]
                 and source_binding.get("source_occurrence_ids") == [i["occurrence"]["occurrence_id"] for i in source_items]
                 and source_binding.get("source_sha256s") == [hashlib.sha256(i["content"]).hexdigest() for i in source_items]
                 and all(i["occurrence"]["sha256"] == hashlib.sha256(i["content"]).hexdigest() for i in source_items + database_items)
                 and isinstance(source_binding.get("producer_attempt_id"), str) and bool(source_binding.get("producer_attempt_id")))
        sheet["associations"]["source_binding_state"] = "matched" if valid else "mismatch"
        if not valid:
            issues.append(issue("source_binding_mismatch", stage="populate"))
    sources = [r for r in sheet["input_records"] if r["kind"] == "fasta"]
    segments = sheet["database"]["segments"] if sheet["database"] else []
    for segment in segments:
        target = segment["target_id"]
        sheet["associations"]["segments"].append({"segment_record_key": segment["record_key"], "target_id": target,
            "source_record_key": sources[target]["record_key"] if target < len(sources) else None,
            "basis": "supplied_source_order", "custody_state": sheet["associations"]["source_binding_state"]})
    for role in ("stdout", "stderr"):
        for item in payloads["output"].get(role, []):
            _diagnostics(item["content"], item["occurrence"], rows, issues, mode)
    groups = sheet["associations"]["query_groups"]
    for item in payloads["output"].get("hits", []):
        _hits(item["content"], item["occurrence"], rows, groups, issues)
    queries = [r for r in sheet["input_records"] if r["kind"] == "query"]
    _associate_queries(groups, queries, issues)
    targets_by_name = {}
    for segment in segments:
        targets_by_name.setdefault(segment["name"], {}).setdefault(segment["target_id"], []).append(segment["record_key"])
    for row in rows:
        if row["kind"] != "exactmatch_hit":
            continue
        name = row["payload"]["target_name"]
        candidates = []
        target_ids = sorted(targets_by_name.get(name, {}))
        for target_id in target_ids:
            source = sources[target_id] if target_id < len(sources) else None
            candidates.append({"target_id": target_id, "source_record_key": source["record_key"] if source else None,
                               "segment_record_keys": list(targets_by_name[name][target_id])})
        if not segments:
            candidates = [{"target_id": s["source_ordinal"], "source_record_key": s["record_key"], "segment_record_keys": []}
                          for s in sources if s["payload"]["name"] == name]
        state = "unique" if len(candidates) == 1 and candidates[0]["source_record_key"] else "ambiguous" if len(candidates) > 1 else "unresolved"
        sheet["associations"]["hit_targets"].append({"hit_record_key": row["record_key"], "state": state, "candidates": candidates})
        if state != "unique":
            issues.append(issue("target_association_unresolved", record_key=row["record_key"], detail={"candidate_count": len(candidates)}))
    return sheet
