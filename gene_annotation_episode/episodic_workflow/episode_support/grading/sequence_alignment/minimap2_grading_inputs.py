"""Native-output parsers for minimap2 PAF placement measurements.

The native convention is pinned to minimap2 2.31 (align.c mm_update_extra and
format.c write_cs_ds_core/write_tags). PAF matching/block counts exclude
ambiguous columns; cg geometry includes them; cs compares normalized ACGTN.
Neither a normalized N match nor CIGAR M establishes original-symbol equality.
No acquisition, execution, resource choice, annotation inference or credit is
performed here. Full supplied data is retained for independent recalculation.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re


SHEET_SCHEMA = "minimap2_placement_sheet_v1"
PRESETS = ("map-ont", "map-pb", "map-hifi", "lr:hq", "map-iclr", "sr")
_CIGAR = re.compile(r"([1-9][0-9]*)([MIDN=X])")
_CS = re.compile(r"(:[1-9][0-9]*|=[ACGTNacgtn]+|\*[ACGTNacgtn]{2}|[+-][ACGTNacgtn]+|~[ACGTNacgtn]{2}[0-9]+[ACGTNacgtn]{2})")
_INT = re.compile(r"[+-]?[0-9]+")
_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")
NATIVE_TAG_TYPES = {**dict.fromkeys(("AS", "ms", "NM", "cm", "s1", "s2", "rl", "zd", "nn"), "i"),
                    "dv": "f", "de": "f"}
COUNT_FIELDS = ("paired_positions", "inserted_bases", "deleted_bases", "query_gap_columns",
                "reference_gap_columns", "reference_skipped_bases", "alignment_columns",
                "cs_equal_positions", "cs_substituted_positions")
_CORE_FIELDS = ("query_name", "query_length", "query_interval", "strand", "reference_name",
                "reference_length", "reference_interval", "matching_bases", "block_length",
                "mapping_quality", "tags")


def require_finite_json(value, code):
    """Check the storage boundary without changing native values or identities."""
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


def _integer(text, code):
    if type(text) is not str or _INT.fullmatch(text) is None:
        raise ValueError(code)
    return int(text)


def _tag_value(type_, value):
    code = "invalid_native_paf_tag_value"
    if type_ == "i":
        return _integer(value, code)
    if type_ == "f":
        if re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value) is None:
            raise ValueError(code)
        try:
            number = float(value)
        except ValueError as error:
            raise ValueError(code) from error
        if not value or value != value.strip() or not math.isfinite(number):
            raise ValueError(code)
        return number
    if type_ == "A":
        if len(value) != 1 or not 33 <= ord(value) <= 126:
            raise ValueError(code)
    elif type_ == "H":
        if re.fullmatch(r"(?:[0-9A-Fa-f]{2})*", value) is None:
            raise ValueError(code)
    elif type_ == "B":
        values = value.split(",")
        if len(values) < 2 or values[0] not in {"c", "C", "s", "S", "i", "I", "f"}:
            raise ValueError(code)
        bounds = {"c": (-128, 127), "C": (0, 255), "s": (-32768, 32767),
                  "S": (0, 65535), "i": (-2147483648, 2147483647), "I": (0, 4294967295)}
        for item in values[1:]:
            number = _tag_value("f" if values[0] == "f" else "i", item)
            if values[0] in bounds and not bounds[values[0]][0] <= number <= bounds[values[0]][1]:
                raise ValueError(code)
    if any(not 32 <= ord(char) <= 126 for char in value):
        raise ValueError(code)
    return value


def _parse_tags(raw_tags):
    tags, names = [], set()
    for raw in raw_tags:
        parts = raw.split(":", 2)
        if (len(parts) != 3 or re.fullmatch(r"[A-Za-z][A-Za-z0-9]", parts[0]) is None
                or parts[1] not in {"A", "i", "f", "Z", "H", "B"}):
            raise ValueError("invalid_native_paf_tag")
        name, type_, value = parts
        if name in names:
            raise ValueError("native_paf_duplicate_tag:" + name)
        names.add(name)
        _tag_value(type_, value)
        tags.append({"name": name, "type": type_, "value": value})
    return tags


def cigar_operations(cigar):
    pieces = list(_CIGAR.finditer(cigar or ""))
    if not pieces or "".join(match[0] for match in pieces) != cigar:
        raise ValueError("invalid_native_paf_cigar")
    return [{"operation": match[2], "length": int(match[1])} for match in pieces]


def cs_operations(cs):
    pieces = list(_CS.finditer(cs or ""))
    if not pieces or "".join(match[0] for match in pieces) != cs:
        raise ValueError("invalid_native_paf_cs")
    result = []
    for match in pieces:
        text = match[0]
        op = text[0]
        size = int(text[1:]) if op == ":" else 1 if op == "*" else int(text[3:-2]) if op == "~" else len(text)-1
        if size < 1 or op == "~" and size < 2:
            raise ValueError("invalid_native_paf_cs")
        result.append({"operation": op, "length": size, "value": text[1:]})
    return result


def _path(operations, *, cs=False):
    result = []
    for item in operations:
        op, size = item["operation"], item["length"]
        kind = ({":": "M", "=": "M", "*": "M", "+": "I", "-": "D", "~": "N"}[op]
                if cs else "M" if op in "M=X" else op)
        if result and result[-1]["operation"] == kind:
            result[-1]["length"] += size
        else:
            result.append({"operation": kind, "length": size})
    return result


def _tag_quantities(tags, issues):
    by_name = {item["name"]: item for item in tags}
    quantities = dict.fromkeys(NATIVE_TAG_TYPES)
    for name, expected in NATIVE_TAG_TYPES.items():
        item = by_name.get(name)
        if item is None:
            continue
        if item["type"] != expected:
            issues.append({"code": "native_tag_type_mismatch", "tag": name, "expected": expected,
                           "actual": item["type"]})
            continue
        value = _tag_value(expected, item["value"])
        # Negative DP scores are valid. Counts and divergence are not DP scores.
        if (name in {"NM", "cm", "rl", "nn", "zd"} and value < 0
                or name in {"dv", "de"} and not 0 <= value <= 1
                or name == "zd" and value > 3):
            issues.append({"code": "native_tag_value_out_of_domain", "tag": name, "value": value})
        else:
            quantities[name] = value
    return quantities


def _cs_counts(ops):
    equal = sum(item["length"] for item in ops if item["operation"] in {"=", ":"})
    substitutions = sum(item["length"] for item in ops if item["operation"] == "*")
    explicit_ambiguity = equal_ambiguity = unknown_equal = 0
    for item in ops:
        op, value = item["operation"], item["value"].upper()
        if op == ":":
            unknown_equal += item["length"]
        elif op == "=":
            equal_ambiguity += value.count("N")
            explicit_ambiguity += value.count("N")
        elif op in {"+", "-"}:
            explicit_ambiguity += value.count("N")
        elif op == "*":
            if value[0] == value[1]:
                raise ValueError("native_paf_cs_substitution_has_equal_symbols")
            explicit_ambiguity += int("N" in value)
    return equal, substitutions, explicit_ambiguity, equal_ambiguity, unknown_equal


def _paths(row, issues):
    by_name = {item["name"]: item for item in row["tags"]}
    quantities = _tag_quantities(row["tags"], issues)
    cg, cs = by_name.get("cg"), by_name.get("cs")
    if cg and cg["type"] != "Z":
        raise ValueError("invalid_native_paf_cigar")
    if cs and cs["type"] != "Z":
        raise ValueError("invalid_native_paf_cs")
    cg_ops = cigar_operations(cg["value"]) if cg else []
    cs_ops = cs_operations(cs["value"]) if cs else []
    cg_path, cs_path = _path(cg_ops), _path(cs_ops, cs=True)
    expected = (row["query_interval"][1]-row["query_interval"][0],
                row["reference_interval"][1]-row["reference_interval"][0])
    for label, path in (("cigar", cg_path), ("cs", cs_path)):
        if path and (sum(p["length"] for p in path if p["operation"] in "MI"),
                     sum(p["length"] for p in path if p["operation"] in "MDN")) != expected:
            raise ValueError("native_paf_" + label + "_extent_mismatch")
    if cg_path and cs_path and cg_path != cs_path:
        raise ValueError("native_paf_base_path_mismatch")
    path = cg_path or cs_path
    counts = dict.fromkeys(COUNT_FIELDS)
    relationship = {"status": "unavailable", "reason": "base_path_missing", "ambiguity_source": None}
    if path:
        totals = {op: sum(p["length"] for p in path if p["operation"] == op) for op in "MIDN"}
        counts.update(paired_positions=totals["M"], inserted_bases=totals["I"], deleted_bases=totals["D"],
            query_gap_columns=totals["D"], reference_gap_columns=totals["I"],
            reference_skipped_bases=totals["N"], alignment_columns=totals["M"]+totals["I"]+totals["D"])
        columns = counts["alignment_columns"]
        if row["matching_bases"] > totals["M"] or row["block_length"] > columns:
            raise ValueError("native_paf_block_length_mismatch")
        ambiguity = quantities["nn"]
        ambiguity_source = "nn" if ambiguity is not None else None
        cs_data = _cs_counts(cs_ops) if cs_ops else None
        if cs_data:
            equal, substitutions, explicit, equal_ambiguous, unknown_equal = cs_data
            counts.update(cs_equal_positions=equal, cs_substituted_positions=substitutions)
            if ambiguity is not None and not explicit <= ambiguity <= explicit + unknown_equal:
                raise ValueError("native_paf_cs_ambiguity_mismatch")
            if ambiguity is None and unknown_equal == 0:
                ambiguity, ambiguity_source = explicit, "fully_explicit_cs_symbols"
            if ambiguity is not None:
                matches = equal - equal_ambiguous - (ambiguity-explicit)
                if matches != row["matching_bases"]:
                    raise ValueError("native_paf_matching_bases_mismatch")
            elif not equal-equal_ambiguous-unknown_equal <= row["matching_bases"] <= equal-equal_ambiguous:
                raise ValueError("native_paf_matching_bases_mismatch")
        if ambiguity is not None:
            if columns != row["block_length"] + ambiguity:
                raise ValueError("native_paf_block_length_mismatch")
            relationship = {"status": "verified", "reason": None, "ambiguity_source": ambiguity_source}
        else:
            relationship = {"status": "unavailable", "reason": "native_ambiguity_count_missing_or_invalid",
                            "ambiguity_source": None}
    return cg_ops, cs_ops, path, counts, quantities, relationship


def parse_minimap2_paf_row(line: bytes | str, *, native_version: str | None = None) -> dict:
    """Read exactly one mapped PAF row, with strict extents and finite tags.

    Unmapped --paf-no-hit rows are outside the placement contract. Unknown nn
    never becomes zero. Invalid optional scientific tag *semantics* retain the
    typed raw tag and an issue; malformed tag syntax/types reject the row.
    """
    if native_version is not None and (type(native_version) is not str or not native_version):
        raise ValueError("minimap2_native_version_invalid")
    try:
        text = line.decode("ascii") if isinstance(line, bytes) else line
        if type(text) is not str or not text.isascii():
            raise ValueError("invalid_native_paf_row")
        text = text.removesuffix("\n").removesuffix("\r")
        if "\n" in text or "\r" in text:
            raise ValueError("invalid_native_paf_row")
        fields = text.split("\t")
        if len(fields) < 12:
            raise ValueError("invalid_native_paf_row")
        qlen, qs, qe, rlen, rs, re_, matches, block, mapq = (
            _integer(fields[i], "invalid_native_paf_row") for i in (1, 2, 3, 6, 7, 8, 9, 10, 11))
        if (not fields[0] or not fields[5] or fields[4] not in {"+", "-"}
                or any(char.isspace() for name in (fields[0], fields[5]) for char in name)
                or not 0 <= qs < qe <= qlen or not 0 <= rs < re_ <= rlen
                or not 0 <= matches <= block or not 0 <= mapq <= 255):
            raise ValueError("invalid_native_paf_row")
        tags = _parse_tags(fields[12:])
    except UnicodeError as error:
        raise ValueError("invalid_native_paf_row") from error
    by_name = {item["name"]: item for item in tags}
    issues = []
    tp = by_name.get("tp")
    native_type = tp["value"] if tp and tp["type"] == "A" and tp["value"] in {"P", "S", "I", "i"} else None
    if tp is not None and native_type is None:
        issues.append({"code": "native_alignment_type_invalid", "tag": "tp"})
    row = {"query_name": fields[0], "query_length": qlen, "query_interval": [qs, qe],
        "strand": fields[4], "reference_name": fields[5], "reference_length": rlen,
        "reference_interval": [rs, re_], "matching_bases": matches, "block_length": block,
        "mapping_quality": mapq, "mapping_quality_available": mapq != 255, "tags": tags,
        "base_alignment_available": "cg" in by_name,
        "cigar": by_name.get("cg", {}).get("value"), "cs": by_name.get("cs", {}).get("value"),
        "native_alignment_type": native_type, "native_line": text, "issues": issues}
    _paths(row, issues)
    return row


def _metadata(supplied, role, native, issues):
    result = {"supplied": deepcopy(supplied), "status": "not_supplied", "length": native.get(role + "_length"),
              "sequence_status": "not_supplied", "sequence": None}
    if supplied is None:
        return result
    result["status"] = "valid"
    if type(supplied) is not dict:
        result.update(status="invalid", length=None)
        issues.append({"code": "operand_metadata_object_required", "operand": role})
        return result
    for key, expected in (("name", native.get(role + "_name")), ("length", native.get(role + "_length"))):
        value = supplied.get(key)
        if type(value) is not (str if key == "name" else int) or value != expected:
            result.update(status="invalid", length=None)
            issues.append({"code": "operand_metadata_" + key + "_mismatch", "operand": role,
                           "native": expected, "supplied": value})
    if "sequence" in supplied:
        seq = supplied["sequence"]
        if (type(seq) is not str or type(supplied.get("length")) is not int or len(seq) != supplied["length"]
                or re.fullmatch(r"[ACGTRYSWKMBDHVNacgtryswkmbdhvn]*", seq) is None):
            result["sequence_status"] = "invalid"
            issues.append({"code": "operand_metadata_sequence_invalid", "operand": role})
        elif result["status"] == "valid":
            result.update(sequence_status="valid", sequence=seq)
        else:
            result["sequence_status"] = "unjoined"
    return result


def _correspondence(row, path):
    qstep = 1 if row["strand"] == "+" else -1
    q = row["query_interval"][0] if qstep == 1 else row["query_interval"][1]-1
    r, column = row["reference_interval"][0], 0
    result = []
    for item in path:
        op, size = item["operation"], item["length"]
        hasq, hasr = op in "MI", op in "MDN"
        qi = [min(q, q+qstep*(size-1)), max(q, q+qstep*(size-1))+1] if hasq else [q+(qstep == -1)]*2
        ri = [r, r+size] if hasr else [r, r]
        end = column + (0 if op == "N" else size)
        result.append({"operation": op, "length": size, "query_interval": qi,
                       "reference_interval": ri, "query_first": q if hasq else None,
                       "query_step": qstep if hasq else None, "column_interval": [column, end]})
        q += qstep*size if hasq else 0
        r += size if hasr else 0
        column = end
    return result


def _original_symbols(row, segments, metadata, counts, quantities, issues):
    result = {"status": "unavailable", "equal_positions": None, "substituted_positions": None,
              "normalization": "uppercase_original_IUPAC_symbols_query_complemented_on_reverse_strand"}
    if not segments or any(metadata[role]["sequence_status"] != "valid" for role in ("query", "reference")):
        return result
    query, reference = (metadata[role]["sequence"].upper() for role in ("query", "reference"))
    equal = nonambiguous_equal = ambiguity = 0
    for part in segments:
        op, size = part["operation"], part["length"]
        if op == "N":
            continue
        for offset in range(size):
            a = query[part["query_first"] + part["query_step"]*offset] if op in "MI" else None
            if a is not None and row["strand"] == "-":
                a = a.translate(_COMPLEMENT)
            b = reference[part["reference_interval"][0]+offset] if op in "MD" else None
            ambiguous = any(s is not None and s not in "ACGT" for s in (a, b))
            ambiguity += ambiguous
            if op == "M":
                equal += a == b
                nonambiguous_equal += a == b and not ambiguous
    if (nonambiguous_equal != row["matching_bases"]
            or counts["alignment_columns"]-ambiguity != row["block_length"]
            or quantities["nn"] is not None and ambiguity != quantities["nn"]):
        issues.append({"code": "operand_sequence_native_count_mismatch"})
        for role in ("query", "reference"):
            metadata[role].update(status="invalid", length=None, sequence_status="incompatible")
        result["status"] = "incompatible"
        return result
    result.update(status="available", equal_positions=equal,
                  substituted_positions=counts["paired_positions"]-equal)
    return result


def _validate_cs_metadata(row, operations, metadata, issues):
    """Validate supplied operand symbols against explicit normalized cs symbols.

    Short-form equal-length operations only constrain equality when both actual
    operands are supplied. Neither form licenses reconstructing original IUPAC
    symbols. A mismatch invalidates only the implicated metadata join.
    """
    if not operations:
        return
    sequences = {role: meta["sequence"].upper() for role, meta in metadata.items()
                 if meta["sequence_status"] == "valid"}
    bad = set()
    qstep = 1 if row["strand"] == "+" else -1
    q = row["query_interval"][0] if qstep == 1 else row["query_interval"][1]-1
    r = row["reference_interval"][0]
    def norm(symbol):
        return symbol if symbol in "ACGT" else "N"
    def query_slice(size):
        sequence = sequences.get("query")
        if sequence is None:
            return None
        chars = (sequence[q+qstep*i] for i in range(size))
        return "".join(norm(char if qstep == 1 else char.translate(_COMPLEMENT)) for char in chars)
    def reference_slice(start, size):
        sequence = sequences.get("reference")
        return "".join(norm(char) for char in sequence[start:start+size]) if sequence is not None else None
    for item in operations:
        op, size, value = item["operation"], item["length"], item["value"].upper()
        actual = {"query": query_slice(size) if op in ":=*+" else None,
                  "reference": reference_slice(r, size) if op in ":=*-" else None}
        expected = {"query": value if op in "=+" else value[1] if op == "*" else None,
                    "reference": value if op in "=-" else value[0] if op == "*" else None}
        for role in ("query", "reference"):
            if expected[role] is not None and actual[role] is not None and expected[role] != actual[role]:
                bad.add(role)
        if op == ":" and actual["query"] is not None and actual["reference"] is not None:
            if actual["query"] != actual["reference"]:
                bad.update(("query", "reference"))
        if op == "~" and "reference" in sequences:
            if reference_slice(r, 2) != value[:2] or reference_slice(r+size-2, 2) != value[-2:]:
                bad.add("reference")
        q += qstep*size if op in ":=*+" else 0
        r += size if op in ":=*-~" else 0
    for role in sorted(bad):
        metadata[role].update(status="invalid", length=None, sequence_status="incompatible")
        issues.append({"code": "operand_sequence_cs_mismatch", "operand": role})


def _salvage_tags(native, issues):
    """Keep individually valid optional quantities from a damaged parsed record."""
    tags = native.get("tags")
    if type(tags) is not list:
        return []
    valid, counts = [], {}
    for index, tag in enumerate(tags):
        try:
            if type(tag) is not dict or any(type(tag.get(key)) is not str for key in ("name", "type", "value")):
                raise ValueError("invalid_native_paf_tag")
            checked = _parse_tags([":".join(tag[key] for key in ("name", "type", "value"))])[0]
            valid.append(checked)
            counts[checked["name"]] = counts.get(checked["name"], 0)+1
        except ValueError as error:
            issues.append({"code": str(error), "tag_index": index})
    # A duplicate has no uniquely selected value, including equal duplicates.
    return [tag for tag in valid if counts[tag["name"]] == 1]


def _serialize_parsed(native):
    q, r = native["query_interval"], native["reference_interval"]
    if (type(q) is not list or len(q) != 2 or type(r) is not list or len(r) != 2
            or type(native["tags"]) is not list):
        raise ValueError("minimap2_native_fields_invalid")
    integer_values = [native["query_length"], *q, native["reference_length"], *r,
                      native["matching_bases"], native["block_length"], native["mapping_quality"]]
    if any(type(value) is not int for value in integer_values):
        raise ValueError("minimap2_native_integer_required")
    tags = []
    for tag in native["tags"]:
        if type(tag) is not dict or any(type(tag.get(k)) is not str for k in ("name", "type", "value")):
            raise ValueError("invalid_native_paf_tag")
        tags.append(":".join(tag[k] for k in ("name", "type", "value")))
    if any(type(native.get(k)) is not str for k in ("query_name", "reference_name", "strand")):
        raise ValueError("minimap2_native_identity_required")
    return "\t".join(map(str, [native["query_name"], native["query_length"], *q, native["strand"],
        native["reference_name"], native["reference_length"], *r, native["matching_bases"], native["block_length"],
        native["mapping_quality"], *tags]))


def build_minimap2_placement_sheet(native: dict, *, preset: str, native_version: str | None,
        query_metadata: dict | None = None, reference_metadata: dict | None = None) -> dict:
    """Populate a retained numerical sheet from a supplied parsed PAF row.

    Bad joined metadata cannot change native identities or geometry. Missing or
    malformed parsed records keep their finite native facts, with null affected
    derived fields and precise issues. Structural row parsing remains strict.
    """
    if type(native) is not dict:
        raise ValueError("minimap2_native_object_required")
    require_finite_json([native, query_metadata, reference_metadata], "finite_json_minimap2_native_required")
    if type(preset) is not str or preset not in PRESETS:
        raise ValueError("unsupported_genomic_mapping_preset")
    if native_version is not None and (type(native_version) is not str or not native_version):
        raise ValueError("minimap2_native_version_invalid")
    issues, valid, parsed = [], False, None
    try:
        parsed = parse_minimap2_paf_row(_serialize_parsed(native), native_version=native_version)
        for field in ("cigar", "cs", "native_alignment_type", "base_alignment_available", "mapping_quality_available"):
            if field in native and native[field] != parsed[field]:
                raise ValueError("minimap2_parsed_field_conflict:" + field)
        if "native_line" in native:
            retained = parse_minimap2_paf_row(native["native_line"], native_version=native_version)
            if any(retained[field] != parsed[field] for field in _CORE_FIELDS):
                raise ValueError("minimap2_native_line_field_conflict")
        issues.extend(parsed["issues"])
        valid = True
    except (ValueError, KeyError, TypeError, IndexError) as error:
        issues.append({"code": str(error) if not isinstance(error, KeyError) else "minimap2_native_field_missing",
                       **({"field": str(error.args[0])} if isinstance(error, KeyError) else {})})
    facts = {}
    for role in ("query", "reference"):
        length = native.get(role + "_length")
        facts[role + "_length"] = length if type(length) is int and length >= 0 else None
        facts[role + "_name"] = native.get(role + "_name") if type(native.get(role + "_name")) is str else None
        interval = native.get(role + "_interval")
        interval_valid = (type(interval) is list and len(interval) == 2 and all(type(n) is int for n in interval)
            and 0 <= interval[0] < interval[1] and facts[role+"_length"] is not None
            and interval[1] <= facts[role+"_length"])
        facts[role+"_interval"] = deepcopy(interval) if interval_valid else None
    for field in ("matching_bases", "block_length", "mapping_quality"):
        value = native.get(field)
        facts[field] = value if type(value) is int and value >= 0 and (field != "mapping_quality" or value <= 255) else None
    if facts["matching_bases"] is not None and facts["block_length"] is not None and facts["matching_bases"] > facts["block_length"]:
        facts["matching_bases"] = None
    facts["strand"] = native.get("strand") if type(native.get("strand")) is str and native["strand"] in {"+", "-"} else None
    metadata = {role: _metadata(value, role, facts, issues)
                for role, value in (("query", query_metadata), ("reference", reference_metadata))}
    counts = dict.fromkeys(COUNT_FIELDS)
    quantities = dict.fromkeys(NATIVE_TAG_TYPES)
    cg, cs, path, segments = [], [], [], []
    relationship = {"status": "unavailable", "reason": "invalid_native_record", "ambiguity_source": None}
    if valid:
        path_issues = []
        cg, cs, path, counts, quantities, relationship = _paths(parsed, path_issues)
        segments = _correspondence(parsed, path)
        _validate_cs_metadata(facts, cs, metadata, issues)
    else:
        quantities = _tag_quantities(_salvage_tags(native, issues), issues)
    original = _original_symbols(facts, segments, metadata, counts, quantities, issues)
    return {"schema": SHEET_SCHEMA, "status": "invalid" if not valid else "partial" if issues else "complete",
        "preset": preset, "native_version": native_version, "native_result": deepcopy(native),
        "native_convention": "minimap2_2_31_PAF_blen_excludes_ambiguous_columns_and_reference_skips",
        "native_parameters": deepcopy(native.get("native_parameters")),
        "native_valid": valid, "native_facts": facts, "metadata": metadata,
        "native_tag_quantities": quantities, "native_alignment_type": parsed["native_alignment_type"] if valid else None,
        "cg_operations": cg, "cs_operations": cs, "correspondence": segments,
        "coordinate_system": "zero_based_half_open_original_operands_reference_forward",
        "measured_counts": counts, "count_relationship": relationship, "original_symbols": original,
        "availability": {"geometry": bool(path), "cs_equality": bool(cs),
            "native_identity": facts["matching_bases"] is not None and facts["block_length"] is not None,
            "native_identity_kind": ("native_record_invalid" if not valid else "base_alignment" if path else
                "base_alignment_path_unavailable" if any(quantities[tag] is not None for tag in ("AS", "ms", "NM", "nn"))
                else "approximate_chaining"),
            "query_coverage": metadata["query"]["length"] is not None,
            "reference_coverage": metadata["reference"]["length"] is not None}, "issues": issues,
        "limitations": ["native_placements_are_not_function_taxonomy_or_orthology_assignments",
            "native_tp_is_not_a_SAM_supplementary_flag", "reported_placements_are_not_independent_evidence",
            "normalized_cs_equality_does_not_establish_original_symbol_equality",
            "PAF_MAPQ_is_not_an_annotation_probability", "only_explicitly_supplied_metadata_is_joined"]}


__all__ = ["parse_minimap2_paf_row", "build_minimap2_placement_sheet"]
