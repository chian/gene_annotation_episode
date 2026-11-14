"""Pure Infernal 1.1.5 cmalign readers and numerical sheet population.

All inputs are supplied data. No path is opened, model is called, or work is
launched. Stockholm grammar and PP bins match the shared format utilities;
HMMER's biological geometry is deliberately not used. RF '~' is an EL emission
column. A gap at an RF consensus column does not by itself prove a D state.

Occurrences are zero-based per name within an alignment. A supplied occurrence
explicitly associates the same-name occurrence in native sidecars. Optional
artifact_id/alignment_index on sequence metadata disambiguate multiple outputs.
Inherited alignment accepts the same artifact object shape as Stockholm inputs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import math
import re

from .hmmalign_inputs import (iter_hmmalign_stockholm_records,
                              posterior_bin_bounds, require_finite_json)

SHEET_SCHEMA = "cmalign_sheet_v1"
_FORMATS = {"stockholm", "cmalign_sfile", "cmalign_ifile", "cmalign_elfile"}
_BASES = set("ACGUTRYMKSWHBVDNXI")
_GAPS = set("-._")
_ORIGINS = ("newly_aligned", "inherited", "unknown")
_POPS = ("all", *_ORIGINS)
_CANONICAL = {"AU", "UA", "GC", "CG", "GU", "UG"}
_UNIQUE_WARNING = '# WARNING: seq names have been made unique by adding a prefix of "<seq#>|"'


def _issue(issues, code, **context):
    issues.append({"code": "cmalign_" + code, **context})


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _norm(sequence):
    return sequence.upper().replace("T", "U").replace("X", "N").replace("I", "A")


def _residue(symbol):
    return symbol.upper() in _BASES


def _ungapped(sequence):
    return "".join(s for s in sequence if _residue(s))


def _symbol_class(symbol):
    return ("residue" if _residue(symbol) else "gap" if symbol in _GAPS else
            "missing" if symbol == "~" else "nonresidue" if symbol == "*" else "unavailable")


def _artifact(value, *, inherited=False):
    if (type(value) is not dict or type(value.get("artifact_id")) is not str or not value["artifact_id"]
            or type(value.get("format")) is not str or value.get("format") not in ({"stockholm"} if inherited else _FORMATS)
            or type(value.get("content")) is not str or
            value.get("complete") is not None and type(value["complete"]) is not bool):
        raise ValueError("cmalign_artifact_contract_invalid")


def _lines(artifact):
    offset = 0
    for number, raw in enumerate(artifact["content"].splitlines(keepends=True), 1):
        end = offset + len(raw.encode("utf-8"))
        yield raw.rstrip("\r\n"), {"artifact_id": artifact["artifact_id"], "line": number,
                                   "byte_start": offset, "byte_end": end}
        offset = end


def _translate(value):
    """Adapt shared Stockholm syntax diagnostics, never biological semantics."""
    if type(value) is dict:
        return {k: (v.replace("hmmalign_", "cmalign_", 1) if k == "code" and type(v) is str
                    else _translate(v)) for k, v in value.items()}
    if type(value) is list:
        return [_translate(v) for v in value]
    return value


def parse_cmalign_stockholm(artifact: dict) -> list[dict]:
    """Retain interleaved/Pfam strings, every annotation and original locator."""
    _artifact(artifact, inherited=True)
    return _translate(list(iter_hmmalign_stockholm_records(artifact["content"],
        artifact_ref=artifact["artifact_id"], engine_version="1.1.5")))


def _number(token, *, integer=False, minimum=None):
    if token == "-" and not integer:
        return None
    if integer and re.fullmatch(r"-?\d+", token) is None:
        raise ValueError("integer required")
    value = int(token) if integer else float(token)
    if not math.isfinite(value) or minimum is not None and value < minimum:
        raise ValueError("finite value in range required")
    return value


def parse_cmalign_sfile(artifact: dict) -> dict:
    """Read the actual standard or --verbose 1.1.5 score table."""
    _artifact(artifact)
    if artifact["format"] != "cmalign_sfile":
        raise ValueError("cmalign_sfile_format_required")
    rows, issues, names = [], [], Counter()
    header = False
    verbose = False
    for line, locator in _lines(artifact):
        if line.lstrip().startswith("#"):
            if re.match(r"#\s+idx\s+seq name\s+length\s+cm from\s+cm to\s+trunc\s+bit sc\s+avg pp\s+band calc\s+alignment\s+total\s+mem \(Mb\)", line):
                header = True
                verbose = line.rstrip().endswith("failover")
            continue
        if not line.strip():
            continue
        tokens = line.split()
        if not header or len(tokens) != (16 if verbose else 12):
            _issue(issues, "sfile_header_or_field_count_invalid", locator=locator, tokens=tokens)
            continue
        row = {"locator": locator, "native_tokens": tokens, "name": tokens[1],
               "occurrence": names[tokens[1]], "valid": True, "issues": []}
        names[tokens[1]] += 1
        specs = {"native_index": (0, True, 1), "length": (2, True, 0),
            "cm_from": (3, True, -1), "cm_to": (4, True, -1),
            "bit_score": (6, False, None), "avg_pp": (7, False, 0),
            "band_seconds": (8, False, 0), "alignment_seconds": (9, False, 0),
            "total_seconds": (10, False, 0), "matrix_mb": (11, False, 0)}
        if verbose:
            specs.update(tau=(12, False, 0), thresh1=(13, False, 0), thresh2=(14, False, 0))
            row["failover"] = tokens[15]
        for field, (col, is_int, minimum) in specs.items():
            try:
                row[field] = _number(tokens[col], integer=is_int, minimum=minimum)
                if field == "avg_pp" and row[field] is not None and row[field] > 1:
                    raise ValueError("probability out of range")
            except ValueError:
                row[field] = None
                _issue(row["issues"], "sfile_number_invalid", field=field, locator=locator)
        row["truncation"] = tokens[5]
        if row["truncation"] not in {"no", "5'", "3'", "5'&3'"}:
            _issue(row["issues"], "sfile_truncation_invalid", locator=locator)
        a, b = row["cm_from"], row["cm_to"]
        if a is None or b is None or not (a == b == -1 or 1 <= a <= b):
            _issue(row["issues"], "sfile_coordinates_invalid", locator=locator)
        row["valid"] = not row["issues"]
        rows.append(row)
        issues.extend(row["issues"])
    indices = [r["native_index"] for r in rows]
    if len(indices) != len(set(indices)):
        _issue(issues, "sfile_duplicate_native_index")
        for row in rows:
            row["valid"] = False
    if not header:
        _issue(issues, "sfile_header_missing")
    return {"artifact_id": artifact["artifact_id"], "format": artifact["format"],
            "complete": artifact.get("complete"), "rows": rows, "issues": issues}


def parse_cmalign_insert_file(artifact: dict, *, model: dict | None = None) -> dict:
    """Read --ifile/--elfile model sections and exact original emission ranges."""
    _artifact(artifact)
    if artifact["format"] not in {"cmalign_ifile", "cmalign_elfile"}:
        raise ValueError("cmalign_insert_format_required")
    sections, issues, active = [], [], None
    counts = Counter()
    for line, locator in _lines(artifact):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        tokens = line.split()
        if tokens == ["//"]:
            if active is None:
                _issue(issues, "insert_unexpected_terminator", locator=locator)
            else:
                active["terminated"] = True
                active = None
            continue
        if active is None:
            if (len(tokens) >= 4 and model is not None and type(model.get("name")) is str
                    and _integer(model.get("consensus_length"))):
                active = {"model_name": model["name"], "consensus_length": model["consensus_length"],
                    "locator": locator, "rows": [], "terminated": False, "section_index": len(sections),
                    "native_header_present": False, "header_source": "supplied_model_for_declared_mapali"}
                sections.append(active)
                counts = Counter()
                _issue(issues, "insert_native_model_header_absent_supplied_mapali_association", locator=locator)
            else:
                try:
                    if len(tokens) != 2:
                        raise ValueError("model header")
                    length = _number(tokens[1], integer=True, minimum=0)
                except ValueError:
                    _issue(issues, "insert_model_header_invalid", locator=locator, tokens=tokens)
                    continue
                active = {"model_name": tokens[0], "consensus_length": length, "locator": locator,
                          "rows": [], "terminated": False, "section_index": len(sections),
                          "native_header_present": True, "header_source": "native"}
                sections.append(active)
                counts = Counter()
                continue
        row = {"locator": locator, "native_tokens": tokens, "name": tokens[0],
               "occurrence": counts[tokens[0]], "valid": True, "issues": [], "emissions": []}
        counts[tokens[0]] += 1
        try:
            if len(tokens) < 4 or (len(tokens)-4) % 3:
                raise ValueError("field count")
            row["length"] = _number(tokens[1], integer=True, minimum=0)
            row["first_occupied_model_position"] = _number(tokens[2], integer=True, minimum=-1)
            row["last_occupied_model_position"] = _number(tokens[3], integer=True, minimum=-1)
            a, b = row["first_occupied_model_position"], row["last_occupied_model_position"]
            if not (a == b == -1 or 1 <= a <= b <= active["consensus_length"]):
                raise ValueError("model endpoints")
            used, anchors = set(), set()
            for index in range(4, len(tokens), 3):
                c, u, n = [_number(t, integer=True, minimum=0) for t in tokens[index:index+3]]
                positions = set(range(u, u+n))
                if c > active["consensus_length"] or c in anchors or u < 1 or n < 1 or u+n-1 > row["length"] or used & positions:
                    raise ValueError("invalid emission range")
                used.update(positions)
                anchors.add(c)
                row["emissions"].append({"after_model_position": c, "original_start": u,
                    "count": n, "original_end_inclusive": u+n-1})
            if [e["after_model_position"] for e in row["emissions"]] != sorted(anchors):
                raise ValueError("native anchor order")
        except ValueError:
            row["valid"] = False
            _issue(row["issues"], "insert_row_invalid", locator=locator)
        active["rows"].append(row)
        issues.extend(row["issues"])
    for section in sections:
        if not section["terminated"]:
            _issue(issues, "insert_terminator_missing", locator=section["locator"])
    return {"artifact_id": artifact["artifact_id"], "format": artifact["format"],
            "complete": artifact.get("complete"), "sections": sections, "issues": issues}


def _annotation(record, tag):
    value = record["column_annotations"].get(tag)
    return value["text"] if value and value["valid"] else None


def _association_rows(record, issues):
    """Undo only the fully validated, explicitly warned native name rewrite.

    Original raw rows and their GR/GS associations remain untouched. A numeric
    prefix in an ordinary input identifier is never evidence of this rewrite.
    """
    rows = deepcopy(record["rows"])
    for row in rows:
        row["native_name"] = row["name"]
        row["name_mapping"] = None
    warnings = [e for e in record["original_events"] if e["kind"] == "comment"
                and e["raw"].rstrip("\r\n") == _UNIQUE_WARNING]
    if not warnings:
        return rows
    width = len(str(len(rows)))
    matches = [re.fullmatch(r"([0-9]+)\|(.+)", r["name"]) for r in rows]
    valid = (len(warnings) == 1 and record["header_valid"] and record["complete"]
        and record["declared_complete"] is not False and bool(rows)
        and all(m is not None and m[1] == str(i).zfill(width) and r["identity_unambiguous"] and r["geometry_valid"]
                for i, (m,r) in enumerate(zip(matches,rows))))
    if valid:
        valid = len({m[2] for m in matches}) < len(rows)
    if not valid:
        _issue(issues, "native_name_prefix_mapping_unverified", artifact_id=record["artifact_id"],
               alignment_index=record["alignment_index"])
        for row in rows:
            row["identity_unambiguous"] = False
        return rows
    occurrences = Counter()
    for row, match in zip(rows,matches):
        original = match[2]
        row["name_mapping"] = {"kind":"validated_native_unique_name_prefix", "native_name":row["native_name"],
            "association_name":original, "native_row_index":row["row_index"],
            "association_occurrence":occurrences[original], "warning_locator":deepcopy(warnings[0]["locator"]),
            "source":"Infernal_1.1.5_Easel_stockholm_write"}
        row["name"] = original
        row["occurrence"] = occurrences[original]
        occurrences[original] += 1
    return rows


def _pairs(ss, issues):
    if ss is None:
        return None
    stack, pk, result = [], defaultdict(list), []
    close = {">": "<", ")": "(", "]": "[", "}": "{"}
    for i, char in enumerate(ss):
        if char in "<([{":
            stack.append((i, char))
        elif char in close:
            if not stack or stack[-1][1] != close[char]:
                _issue(issues, "ss_cons_pairing_invalid", column_index=i)
                return None
            left, _ = stack.pop()
            result.append([left, i])
        elif char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            pk[char].append(i)
        elif char in "abcdefghijklmnopqrstuvwxyz":
            if not pk[char.upper()]:
                _issue(issues, "ss_cons_pairing_invalid", column_index=i)
                return None
            result.append([pk[char.upper()].pop(), i])
        elif char not in ":,_-.~":
            _issue(issues, "ss_cons_symbol_invalid", column_index=i)
            return None
    if stack or any(pk.values()):
        _issue(issues, "ss_cons_unclosed_pair")
        return None
    return sorted(result)


def _model_context(model, sidecars, issues):
    supplied = deepcopy(model or {})
    name, length = supplied.get("name"), supplied.get("consensus_length")
    valid = True
    if model is not None and (type(name) is not str or not name or not _integer(length)):
        _issue(issues, "model_metadata_invalid")
        valid = False
    header = supplied.get("native_header")
    if header is not None:
        if type(header) is not str:
            _issue(issues, "model_header_invalid")
            valid = False
        else:
            fields = {}
            for line in header.splitlines():
                items = line.split(None, 1)
                if len(items) == 2 and items[0] in {"NAME", "CLEN", "ACC"}:
                    if items[0] in fields and fields[items[0]] != items[1].strip():
                        _issue(issues, "model_header_multiple_conflicting_values", field=items[0])
                        valid = False
                    fields[items[0]] = items[1].strip()
            if (fields.get("NAME") != name or fields.get("CLEN") != str(length)
                    or supplied.get("accession") is not None and fields.get("ACC") != supplied["accession"]):
                _issue(issues, "model_header_metadata_mismatch")
                valid = False
    sections = [s for p in sidecars for s in p.get("sections", [])]
    identities = {(s["model_name"], s["consensus_length"]) for s in sections}
    if model is None and len(identities) == 1:
        name, length = next(iter(identities))
    elif identities and valid and (len(identities) != 1 or name is not None and (name, length) not in identities):
        _issue(issues, "sidecar_model_metadata_mismatch")
        valid = False
    if name is None or not _integer(length):
        _issue(issues, "model_identity_or_consensus_length_missing")
        valid = False
    return {"name": name, "consensus_length": length if valid else None,
            "valid": valid, "supplied": supplied, "sidecar_identities": [list(x) for x in sorted(identities)]}


def _metadata(row, supplied, global_names, issues):
    candidates = [s for s in supplied if s["name"] == row["name"]
        and (s.get("occurrence") is None or s["occurrence"] == row["occurrence"])
        and (s.get("artifact_id") is None or s["artifact_id"] == row["artifact_id"])
        and (s.get("alignment_index") is None or s["alignment_index"] == row["alignment_index"])]
    if not candidates:
        return None
    if (len(candidates) != 1 or not row["identity_unambiguous"] or
            row["name_count"] > 1 and candidates[0].get("occurrence") is None or
            global_names[row["name"]] > row["name_count"] and
            (candidates[0].get("artifact_id") is None or candidates[0].get("alignment_index") is None)):
        _issue(issues, "sequence_metadata_join_ambiguous", name=row["name"])
        return None
    return deepcopy(candidates[0])


def _join_sidecar(row, parsed, metadata, issues, *, format_name, only_alignment):
    candidates = []
    for artifact in parsed:
        if artifact["format"] != format_name:
            continue
        sections = artifact.get("sections", [None])
        for section in sections:
            for value in (section["rows"] if section is not None else artifact["rows"]):
                if value["name"] != row["name"]:
                    continue
                if row["name_count"] > 1 and metadata and metadata.get("occurrence") is not None:
                    target_occurrence = row.get("score_occurrence", metadata["occurrence"]) if format_name == "cmalign_sfile" else metadata["occurrence"]
                    if value["occurrence"] != target_occurrence:
                        continue
                candidates.append({**deepcopy(value), "artifact_id": artifact["artifact_id"],
                    "artifact_complete": artifact["complete"],
                    "section_complete": section["terminated"] if section is not None else None})
    if not candidates:
        return None
    if (not only_alignment or len(candidates) != 1 or not row["identity_unambiguous"] or
            row["name_count"] > 1 and (not metadata or metadata.get("occurrence") is None)):
        _issue(issues, "sidecar_join_ambiguous", format=format_name, name=row["name"])
        return None
    candidate = candidates[0]
    usable_partial_score = (format_name == "cmalign_sfile" and _integer(candidate.get("native_index"), 1)
                            and _integer(candidate.get("length")))
    if not candidate["valid"] and not usable_partial_score:
        _issue(issues, "sidecar_row_unusable", format=format_name, locator=candidate["locator"])
        return None
    return candidate


def _posterior(sequence, pp, issues):
    bins, columns = Counter(), []
    lower = upper = total = bounded = 0
    for index, symbol in enumerate(sequence):
        residue = _residue(symbol)
        total += residue
        label = pp[index] if pp is not None else None
        bounds = posterior_bin_bounds(label)
        if bounds is not None and not residue:
            _issue(issues, "pp_on_nonresidue", column_index=index)
            bounds = None
        elif label is not None and label not in ".-_~" and bounds is None:
            _issue(issues, "pp_symbol_invalid", column_index=index)
        if bounds is not None:
            bounded += 1
            bins[label] += 1
            lower += bounds["lower_hundredths"]
            upper += bounds["upper_hundredths"]
        columns.append({"column_index": index, "native_label": label, "bounds": bounds})
    return {"native_pp": pp, "columns": columns, "bin_counts": dict(bins),
        "retained_nucleotide_population": total, "available_count": bounded,
        "unavailable_count": total-bounded, "lower_sum_hundredths": lower,
        "upper_sum_hundredths": upper, "upper_inclusive": bool(bounded) and set(bins) == {"*"},
        "population": "retained_nucleotides_with_native_PP; conditional_on_banding_and_truncation_mode"}


def _original_map(row, metadata, score, inserts, els, settings, issues):
    aligned = row["aligned_sequence"]
    retained = _ungapped(aligned)
    original = metadata.get("sequence") if metadata else None
    lengths = []
    if metadata and metadata.get("length") is not None:
        lengths.append(metadata["length"])
    if original is not None:
        lengths.append(len(original))
    lengths.extend(s["length"] for s in (score, inserts, els) if s is not None)
    result = {"original_length": None, "status": "unavailable", "positions": None,
              "omitted_original_positions": None, "normalization": "uppercase; T->U; X->N; I->A"}
    if any(not _integer(n) for n in lengths) or len(set(lengths)) > 1:
        _issue(issues, "original_sequence_length_mismatch")
        result["status"] = "incompatible"
        return result
    if original is not None and (type(original) is not str or any(not _residue(c) for c in original)):
        _issue(issues, "supplied_sequence_symbols_invalid")
        result["status"] = "incompatible"
        return result
    length = lengths[0] if lengths else None
    if length is None:
        _issue(issues, "original_length_missing")
        return result
    result["original_length"] = length
    matchonly = settings.get("matchonly") is True
    if length < len(retained) or not matchonly and length != len(retained):
        _issue(issues, "retained_original_length_mismatch")
        result.update(original_length=None, status="incompatible")
        return result
    positions, omitted = list(range(1, length+1)), []
    if matchonly and len(retained) != length:
        # A global model has no EL emissions. A missing local EL file does not
        # establish their absence, including zero-length native EL transitions.
        if inserts is None or els is None and settings.get("global") is not True:
            _issue(issues, "matchonly_original_map_requires_ifile_and_local_elfile")
            return result
        if any(s and (s["artifact_complete"] is False or s["section_complete"] is not True) for s in (inserts, els)):
            _issue(issues, "matchonly_original_map_requires_complete_sidecar_rows")
            return result
        ranges = [e for s in (inserts, els) if s for e in s["emissions"]]
        removed = [p for e in ranges for p in range(e["original_start"], e["original_start"]+e["count"])]
        if len(removed) != len(set(removed)) or len(removed)+len(retained) != length:
            _issue(issues, "matchonly_omitted_ranges_conflict")
            result["status"] = "incompatible"
            return result
        omitted = sorted(removed)
        excluded = set(removed)
        positions = [p for p in positions if p not in excluded]
    if original is not None and _norm(retained) != _norm("".join(original[p-1] for p in positions)):
        _issue(issues, "supplied_sequence_content_mismatch")
        result.update(original_length=None, status="incompatible")
        return result
    result.update(status="exact", positions=positions, omitted_original_positions=omitted)
    return result


def _population(rows, observation):
    result = {}
    for population in _POPS:
        selected = [r for r in rows if population == "all" or r["origin"] == population]
        counts = Counter(observation(r) for r in selected)
        result[population] = {"row_count": len(selected), "record_keys": [r["record_key"] for r in selected],
                              "counts": dict(counts)}
    return result


def _pair_observation(row, left, right):
    if not row["availability"]["alignment_geometry"]:
        return "unavailable"
    sequence = row["native"]["aligned_sequence"]
    symbols = sequence[left] + sequence[right]
    classes = [_symbol_class(s) for s in symbols]
    for category in ("missing", "gap", "nonresidue", "unavailable"):
        if category in classes:
            return category
    bases = symbols.upper().replace("T", "U")
    if any(s not in "ACGU" for s in bases):
        return "ambiguous"
    return "canonical" if bases in _CANONICAL else "noncanonical"


def populate_cmalign_sheet(artifacts: list[dict], *, operation: dict,
                          sequences: list[dict] | None = None, model: dict | None = None,
                          inherited_alignment: dict | None = None) -> dict:
    """Populate numerical measurements from supplied native artifacts only."""
    require_finite_json([artifacts, operation, sequences, model, inherited_alignment], "cmalign_finite_json_required")
    if (type(artifacts) is not list or type(operation) is not dict or operation.get("program") != "cmalign"
            or type(operation.get("settings")) is not dict or operation.get("native_version") is not None and
            type(operation["native_version"]) is not str or sequences is not None and type(sequences) is not list
            or model is not None and type(model) is not dict):
        raise ValueError("cmalign_input_contract_invalid")
    for artifact in artifacts:
        _artifact(artifact)
    if len({a["artifact_id"] for a in artifacts}) != len(artifacts):
        raise ValueError("cmalign_duplicate_artifact_id")
    supplied = sequences or []
    for s in supplied:
        if (type(s) is not dict or type(s.get("name")) is not str or not s["name"] or
                s.get("occurrence") is not None and not _integer(s["occurrence"]) or
                s.get("origin", "unknown") not in _ORIGINS or
                s.get("sequence") is not None and type(s["sequence"]) is not str):
            raise ValueError("cmalign_sequence_metadata_contract_invalid")
    settings = operation["settings"]
    for key in ("matchonly", "global", "notrunc", "noprob", "miss", "sub"):
        if key in settings and type(settings[key]) is not bool:
            raise ValueError("cmalign_boolean_setting_required:" + key)
    issues, parsed, records = [], [], []
    if operation.get("native_version") not in (None, "1.1.5"):
        _issue(issues, "native_version_not_verified", native_version=operation["native_version"])
    for artifact in artifacts:
        if artifact["format"] == "stockholm":
            for record in parse_cmalign_stockholm(artifact):
                record.update(artifact_id=artifact["artifact_id"], declared_complete=artifact.get("complete"))
                records.append(record)
        else:
            value = (parse_cmalign_sfile(artifact) if artifact["format"] == "cmalign_sfile"
                     else parse_cmalign_insert_file(artifact, model=model if settings.get("mapali") else None))
            parsed.append(value)
            issues.extend(value["issues"])
        if artifact.get("complete") is False:
            _issue(issues, "artifact_declared_incomplete", artifact_id=artifact["artifact_id"])
    model_context = _model_context(model, parsed, issues)
    seed_rows = []
    if inherited_alignment is not None:
        _artifact(inherited_alignment, inherited=True)
        seed_records = parse_cmalign_stockholm(inherited_alignment)
        if (len(seed_records) == 1 and seed_records[0]["header_valid"] and seed_records[0]["complete"]
                and inherited_alignment.get("complete") is not False and not seed_records[0]["issues"]
                and all(r["symbols_valid"] and r["geometry_valid"] and r["identity_unambiguous"] for r in seed_records[0]["rows"])):
            seed_rows.extend(seed_records[0]["rows"])
        else:
            _issue(issues, "inherited_alignment_invalid_or_ambiguous")
        if not seed_rows:
            _issue(issues, "inherited_alignment_rows_unavailable")
    mapali = inherited_alignment is not None or bool(settings.get("mapali"))
    representation_groups = defaultdict(list)
    for artifact in artifacts:
        representation_groups[(artifact["format"], artifact["content"])].append(artifact["artifact_id"])
    duplicate_artifact_groups = [ids for ids in representation_groups.values() if len(ids) > 1]
    for ids in duplicate_artifact_groups:
        _issue(issues, "duplicate_native_representation", artifact_ids=ids)
    association_rows = [_association_rows(record, issues) for record in records]
    global_names = Counter(r["name"] for rows in association_rows for r in rows)
    output_rows, alignments, columns, pairs = [], [], [], []
    for alignment_number, record in enumerate(records):
        alignment_issues = deepcopy(record["issues"])
        prefix = f"artifact:{record['artifact_id']}/alignment:{record['alignment_index']}"
        rf, ss, pp_cons = (_annotation(record, k) for k in ("RF", "SS_cons", "PP_cons"))
        kinds = [("local_end" if c == "~" else "insert" if c in ".-_" else "model") for c in rf] if rf is not None else None
        rf_count = kinds.count("model") if kinds is not None else None
        model_valid = (model_context["valid"] and rf_count == model_context["consensus_length"]
                       and operation.get("native_version") in (None, "1.1.5"))
        if not model_valid:
            _issue(alignment_issues, "rf_model_map_unavailable_or_length_mismatch", rf_model_positions=rf_count,
                   supplied_consensus_length=model_context["consensus_length"])
        if not record["complete"] or record["declared_complete"] is False:
            _issue(alignment_issues, "stockholm_incomplete")
        global_conflict = settings.get("global") is True and kinds is not None and "local_end" in kinds
        matchonly_conflict = settings.get("matchonly") is True and kinds is not None and any(k != "model" for k in kinds)
        if global_conflict:
            _issue(alignment_issues, "global_setting_conflicts_with_native_EL_columns")
        if matchonly_conflict:
            _issue(alignment_issues, "matchonly_setting_conflicts_with_native_insert_columns")
        versions = [e["value"] for e in record["original_events"] if e["kind"] == "GF" and e["tag"] == "AU"]
        if any(v.startswith("Infernal ") and v != "Infernal 1.1.5" for v in versions):
            _issue(alignment_issues, "stockholm_native_version_mismatch", observed=versions)
            model_valid = False
        pair_map = _pairs(ss, alignment_issues)
        if ss is None:
            _issue(alignment_issues, "ss_cons_unavailable")
        local_rows = []
        associated = association_rows[alignment_number]
        name_counts = Counter(r["name"] for r in associated)
        inherited_prefix_valid = (bool(seed_rows) and len(records) == 1 and len(associated) >= len(seed_rows)
            and all(output["name"] == seed["name"] for output, seed in zip(associated, seed_rows)))
        if seed_rows and not inherited_prefix_valid:
            _issue(alignment_issues, "inherited_output_prefix_mismatch_or_ambiguous")
        for associated_row in associated:
            raw = record["rows"][associated_row["row_index"]]
            row = {**deepcopy(associated_row), "artifact_id": record["artifact_id"], "name_count": name_counts[associated_row["name"]]}
            row_issues = deepcopy(row["issues"])
            metadata = _metadata(row, supplied, global_names, row_issues)
            origin = metadata.get("origin", "unknown") if metadata else "unknown"
            inherited_join = None
            if inherited_prefix_valid and row["row_index"] < len(seed_rows):
                # Native cmalign prepends the supplied training rows in order;
                # actual sequence identity is validated below, before using it.
                seed = seed_rows[row["row_index"]]
                inherited_join = {"artifact_id": inherited_alignment["artifact_id"], "seed_record_key": seed["record_key"],
                                  "status": "native_prefix_associated_sequence_verification_pending"}
                if origin == "newly_aligned":
                    _issue(row_issues, "origin_conflict_with_inherited_alignment")
                origin = "inherited"
                if metadata is None:
                    metadata = {"name": row["name"], "occurrence": row["occurrence"],
                                "sequence": _ungapped(seed["aligned_sequence"]), "origin": "inherited"}
            elif origin == "unknown" and not mapali and not (metadata and metadata.get("origin") == "unknown"):
                origin = "newly_aligned"
            elif origin == "unknown" and inherited_prefix_valid and not (metadata and metadata.get("origin") == "unknown"):
                origin = "newly_aligned"
            elif origin == "unknown" and mapali:
                _issue(row_issues, "inherited_membership_requires_supplied_alignment_or_origin")
            if inherited_prefix_valid and row["row_index"] >= len(seed_rows):
                # --sfile excludes the inherited prefix; insert sidecars do not.
                row["score_occurrence"] = row["occurrence"] - sum(s["name"] == row["name"] for s in seed_rows)
            side = {fmt: None if fmt == "cmalign_sfile" and origin == "inherited" else
                          _join_sidecar(row, parsed, metadata, row_issues, format_name=fmt,
                                      only_alignment=len(records) == 1) for fmt in ("cmalign_sfile", "cmalign_ifile", "cmalign_elfile")}
            score, inserts, els = (side[k] for k in ("cmalign_sfile", "cmalign_ifile", "cmalign_elfile"))
            if origin == "inherited" and score is not None:
                _issue(row_issues, "sfile_cannot_relabel_inherited_row")
                score = None
            if score is None and origin != "inherited":
                _issue(row_issues, "score_sidecar_missing_or_unjoined")
            if not model_context["valid"]:
                inserts = els = None
            if (score is not None and model_context["consensus_length"] is not None
                    and score["cm_to"] is not None and score["cm_to"] > model_context["consensus_length"]):
                _issue(row_issues, "score_model_coordinates_out_of_range")
                score = None
            geometry = (record["header_valid"] and row["geometry_valid"] and row["symbols_valid"] and
                        all(_symbol_class(c) != "unavailable" for c in row["aligned_sequence"]))
            if not geometry:
                _issue(row_issues, "alignment_geometry_invalid")
            mapping = _original_map(row, metadata, score, inserts, els, settings, row_issues)
            if inherited_join is not None and mapping["status"] == "exact":
                seed_sequence = _norm(_ungapped(seed["aligned_sequence"]))
                original = metadata.get("sequence") if metadata else None
                if original is not None and _norm(original) == seed_sequence:
                    inherited_join["status"] = "sequence_identity_verified"
                else:
                    _issue(row_issues, "inherited_sequence_identity_mismatch")
                    mapping.update(status="incompatible", positions=None, original_length=None)
            if metadata and metadata.get("accession") is not None:
                accessions = [a["value"] for a in row["sequence_annotations"] if a["tag"] == "AC"]
                if accessions and (not row["sequence_annotations_joined"] or set(accessions) != {metadata["accession"]}):
                    _issue(row_issues, "sequence_accession_mismatch")
                    mapping.update(status="incompatible", positions=None, original_length=None)
            sequence = row["aligned_sequence"]
            pp = _annotation(row, "PP") if geometry else None
            row_global_conflict = global_conflict or (settings.get("global") is True and els is not None and bool(els["emissions"]))
            if row_global_conflict and not global_conflict:
                _issue(row_issues, "global_setting_conflicts_with_native_EL_emissions")
            truncation_conflict = settings.get("notrunc") is True and settings.get("sub") is not True and ("~" in sequence or
                score is not None and score["truncation"] != "no")
            if truncation_conflict:
                _issue(row_issues, "notrunc_setting_conflicts_with_native_truncation")
            if settings.get("noprob") is True and pp is not None:
                _issue(row_issues, "noprob_setting_conflicts_with_native_PP")
            if matchonly_conflict:
                mapping.update(status="incompatible", positions=None, original_length=None)
            posterior = _posterior(sequence, pp, row_issues)
            counts = {"retained_nucleotides": len(_ungapped(sequence)) if geometry else None,
                "model_match_nucleotides": None, "model_gap_positions": None, "missing_model_positions": None,
                "nonresidue_model_positions": None, "retained_insert_nucleotides": None,
                "retained_local_end_nucleotides": None, "deleted_model_positions": None,
                "local_end_skipped_model_positions": None, "total_insert_nucleotides": None,
                "total_local_end_nucleotides": None, "omitted_nucleotides": None}
            correspondence, mpos, rpos = [], 0, 0
            if geometry:
                if kinds is not None:
                    for field in ("model_match_nucleotides", "model_gap_positions", "missing_model_positions",
                                  "nonresidue_model_positions", "retained_insert_nucleotides", "retained_local_end_nucleotides"):
                        counts[field] = 0
                for col, symbol in enumerate(sequence):
                    category = _symbol_class(symbol)
                    kind = kinds[col] if kinds is not None else "unknown"
                    mpos += kind == "model"
                    is_residue = category == "residue"
                    rpos += is_residue
                    original_position = mapping["positions"][rpos-1] if is_residue and mapping["status"] == "exact" else None
                    relationship = f"{kind}_{category}"
                    if kind == "model":
                        field = {"residue": "model_match_nucleotides", "gap": "model_gap_positions",
                                 "missing": "missing_model_positions", "nonresidue": "nonresidue_model_positions"}.get(category)
                        if field:
                            counts[field] += 1
                    elif is_residue and kind in {"insert", "local_end"}:
                        counts[f"retained_{kind}_nucleotides"] += 1
                    correspondence.append({"column_index": col, "symbol": symbol, "kind": kind,
                        "symbol_class": category, "relationship": relationship,
                        "rf_consensus_index": mpos if kind == "model" else None,
                        "model_position": mpos if kind == "model" and model_valid else None,
                        "after_model_position": mpos if kind in {"insert", "local_end"} and model_valid else None,
                        "retained_sequence_position": rpos if is_residue else None,
                        "original_sequence_position": original_position})
                if (model_valid and settings.get("global") is True and settings.get("notrunc") is True
                        and settings.get("sub") is not True and not row_global_conflict and not truncation_conflict
                        and not counts["missing_model_positions"]):
                    counts["deleted_model_positions"] = counts["model_gap_positions"]
                    counts["local_end_skipped_model_positions"] = 0
                if mapping["status"] == "exact":
                    counts["omitted_nucleotides"] = len(mapping["omitted_original_positions"])
                for label, source in (("insert", inserts), ("local_end", els)):
                    native_total = sum(e["count"] for e in source["emissions"]) if source else None
                    retained_count = counts[f"retained_{label}_nucleotides"]
                    if not settings.get("matchonly"):
                        counts[f"total_{label}_nucleotides"] = retained_count
                        if native_total is not None and native_total != retained_count:
                            _issue(row_issues, "sidecar_emission_count_mismatch", kind=label)
                            counts[f"total_{label}_nucleotides"] = None
                    else:
                        counts[f"total_{label}_nucleotides"] = native_total
                    if label == "local_end" and settings.get("global") is True and not row_global_conflict:
                        counts["total_local_end_nucleotides"] = 0
                # Validate occupied endpoints against the native row, and the
                # sidecar's consensus anchors against original sequence order.
                # Equal counts alone cannot establish these associations.
                occupied = [c for c in correspondence if c["kind"] == "model" and c["symbol_class"] == "residue"]
                endpoints = ([occupied[0]["model_position"], occupied[-1]["model_position"]]
                             if occupied else [-1, -1])
                association_conflict = False
                if model_valid:
                    for label, source in (("insert", inserts), ("local_end", els)):
                        if source is None:
                            continue
                        if endpoints != [source["first_occupied_model_position"], source["last_occupied_model_position"]]:
                            _issue(row_issues, "sidecar_occupied_model_endpoints_mismatch", kind=label)
                            association_conflict = True
                        if mapping["status"] == "exact":
                            for emission in source["emissions"]:
                                start, end, anchor = emission["original_start"], emission["original_end_inclusive"], emission["after_model_position"]
                                if any((c["original_sequence_position"] < start and c["model_position"] > anchor) or
                                       (c["original_sequence_position"] > end and c["model_position"] <= anchor) or
                                       start <= c["original_sequence_position"] <= end for c in occupied):
                                    _issue(row_issues, "sidecar_anchor_original_coordinate_mismatch", kind=label)
                                    association_conflict = True
                    if score and endpoints != [score["cm_from"], score["cm_to"]]:
                        _issue(row_issues, "score_occupied_model_endpoints_mismatch")
                        score = None
                if association_conflict:
                    counts["total_insert_nucleotides"] = counts["total_local_end_nucleotides"] = None
                    if settings.get("matchonly"):
                        mapping.update(status="incompatible", positions=None, omitted_original_positions=None)
                        counts["omitted_nucleotides"] = None
                        for entry in correspondence:
                            entry["original_sequence_position"] = None
                # Sidecar original positions must agree with every rendered
                # insert/EL symbol, not merely have an equal aggregate length.
                if mapping["status"] == "exact" and not settings.get("matchonly"):
                    for label, source in (("insert", inserts), ("local_end", els)):
                        if source:
                            observed = {(c["after_model_position"], c["original_sequence_position"]) for c in correspondence
                                        if c["kind"] == label and c["symbol_class"] == "residue"}
                            native = {(e["after_model_position"], p) for e in source["emissions"]
                                      for p in range(e["original_start"], e["original_start"]+e["count"])}
                            if model_valid and native != observed:
                                _issue(row_issues, "sidecar_emission_correspondence_mismatch", kind=label)
                                counts[f"total_{label}_nucleotides"] = None
            key = f"{prefix}/sequence:{row['row_index']}"
            result_row = {"record_key": key, "alignment_key": prefix, "alignment_index": alignment_number,
                "name": row["name"], "occurrence": row["occurrence"], "origin": origin,
                "native_name": row["native_name"], "name_mapping": deepcopy(row["name_mapping"]),
                "locator": deepcopy(row["locator"]), "native": deepcopy(raw), "metadata": metadata,
                "inherited_join": inherited_join, "sidecars": side, "native_scores": deepcopy(score),
                "native_rf": rf, "posterior": posterior, "measurements": counts,
                "mapping": mapping, "correspondence": correspondence,
                "model_length": model_context["consensus_length"] if model_valid else None,
                "availability": {"alignment_geometry": geometry, "model_mapping": model_valid and geometry,
                    "original_mapping": geometry and mapping["status"] == "exact", "pp": pp is not None,
                    "true_deletions": counts["deleted_model_positions"] is not None}, "issues": row_issues}
            local_rows.append(result_row)
            output_rows.append(result_row)
            issues.extend({**i, "record_key": key} for i in row_issues)
        for col in range(record["column_count"] or 0):
            observation = lambda r: (_symbol_class(r["native"]["aligned_sequence"][col])
                if r["availability"]["alignment_geometry"] else "unavailable")
            native_pp = pp_cons[col] if pp_cons is not None else None
            if native_pp is not None and native_pp not in ".-_~" and posterior_bin_bounds(native_pp) is None:
                _issue(issues, "pp_cons_symbol_invalid", alignment_key=prefix, column_index=col)
            columns.append({"record_key": f"{prefix}/column:{col}", "alignment_key": prefix, "column_index": col,
                "kind": kinds[col] if kinds is not None else "unknown",
                "model_position": sum(k == "model" for k in kinds[:col+1]) if kinds is not None and kinds[col] == "model" and model_valid else None,
                "native_rf_symbol": rf[col] if rf is not None else None,
                "native_pp_cons_symbol": native_pp, "native_pp_cons_bounds": posterior_bin_bounds(native_pp),
                "populations": _population(local_rows, observation)})
        for left, right in pair_map or []:
            pairs.append({"record_key": f"{prefix}/pair:{left}:{right}", "alignment_key": prefix,
                "left_column": left, "right_column": right,
                "populations": _population(local_rows, lambda r: _pair_observation(r, left, right))})
        alignments.append({"record_key": prefix, "artifact_id": record["artifact_id"],
            "alignment_index": alignment_number, "native_record": deepcopy(record),
            "native_rf": rf, "native_ss_cons": ss, "native_pp_cons": pp_cons,
            "rf_model_positions": rf_count, "model_mapping_available": model_valid,
            "pair_map_available": pair_map is not None, "pairs": pair_map,
            "column_count": record["column_count"], "row_count": len(local_rows),
            "complete": record["complete"] and record["declared_complete"] is not False,
            "issues": alignment_issues})
        issues.extend({**i, "alignment_key": prefix} for i in alignment_issues)
    status = ("missing" if not records else "invalid" if not any(r["header_valid"] for r in records)
              or output_rows and not any(r["availability"]["alignment_geometry"] for r in output_rows)
              else "partial" if issues else "available")
    result = {"schema": SHEET_SCHEMA, "operation": deepcopy(operation),
        "alignment_kind": "sampled_alignment" if settings.get("algorithm") == "sample" or settings.get("sample") is True else "model_alignment",
        "artifacts": deepcopy(artifacts), "parsed_sidecars": parsed, "model": model_context,
        "duplicate_artifact_groups": duplicate_artifact_groups,
        "supplied_sequences": deepcopy(supplied), "inherited_alignment": deepcopy(inherited_alignment),
        "alignments": alignments, "sequences": output_rows, "columns": columns, "pairs": pairs,
        "normalization": {"sequence_identity": "uppercase; T->U; X->N; I->A (native RNA digitization)",
            "pair_bases": "uppercase; T->U; other ambiguous symbols excluded",
            "coordinates": "alignment columns zero-based; model and original/retained sequence positions one-based"},
        "status": status, "issues": issues}
    require_finite_json(result, "cmalign_sheet_finite_json_required")
    return result


__all__ = ["populate_cmalign_sheet", "parse_cmalign_stockholm", "parse_cmalign_sfile", "parse_cmalign_insert_file"]
