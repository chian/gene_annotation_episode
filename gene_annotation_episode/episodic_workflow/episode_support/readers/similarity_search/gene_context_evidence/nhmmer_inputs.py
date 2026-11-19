"""Pure HMMER nucleotide-search readers and numerical-sheet construction.

Public streaming interfaces (no path resolution, seeking, or external I/O):
``iter_nhmmer_tblout_rows(stream, *, program, artifact_ref)`` yields every
noncomment row, including invalid rows, with exact original line/byte locators.
``iter_nhmmer_stdout_records(stream, *, program, artifact_ref)`` yields header,
query_start, locus, query_end and completion records, retaining at most one
locus. ``iter_nhmmer_stdout_queries`` yields query summaries without loci.
Streams are text/binary line iterables, text/binary file objects, or supplied
text/bytes. Byte offsets count the supplied UTF-8 representation; binary
streams retain actual byte offsets even for malformed UTF-8.

Native meanings follow HMMER 3.4 p7_tophits_TabularTargets, p7_tophits_Domains,
p7_alidisplay_Print and p7_pli_Statistics. In BOTH programs hmm coordinates are
model positions and ali/env coordinates are sequence positions. The table's
length column is sequence length for nhmmer, model length for nhmmscan.
Tables contain local loci, not protein-style complete-sequence/domain objects.
"""
from __future__ import annotations

from copy import deepcopy
import io
import math
import re


PROGRAMS = frozenset({"nhmmer", "nhmmscan"})
TBL_FIELDS = ("target_name", "target_accession", "query_name", "query_accession",
    "hmm_from", "hmm_to", "ali_from", "ali_to", "env_from", "env_to",
    "length_field", "strand", "evalue", "score_bits", "bias_bits")
_COORD_FIELDS = TBL_FIELDS[4:11]
_QUERY = re.compile(r"^Query:\s+(\S+)\s+\[([ML])=(\d+)\]\s*$")
_RESIDUES = re.compile(r"^\s*(\S+)\s+(-|\d+)\s+([A-Za-z.*-]+)\s+(-|\d+)\s*$")
_MISSING = {"-", ".", "?", "NA", "N/A"}


def finite_json(value, *, name="value"):
    """Validate and copy finite JSON, rejecting non-JSON objects explicitly."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nhmmer_nonfinite_json:" + name)
        return value
    if type(value) is list:
        return [finite_json(item, name=f"{name}/{index}") for index, item in enumerate(value)]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: finite_json(item, name=f"{name}/{key}") for key, item in value.items()}
    raise ValueError("nhmmer_invalid_json_type:" + name)


def _program(program):
    if type(program) is not str or program not in PROGRAMS:
        raise ValueError("nhmmer_unsupported_program")


def _ref(artifact_ref):
    if artifact_ref is not None and (type(artifact_ref) is not str or not artifact_ref):
        raise ValueError("nhmmer_invalid_artifact_ref")


def _issue(code, *, field=None, locator=None, **extra):
    return {"code": code, **({"field": field} if field else {}),
            **({"locator": deepcopy(locator)} if locator else {}), **extra}


def _lines(stream, role, artifact_ref):
    _ref(artifact_ref)
    if isinstance(stream, str):
        stream = io.StringIO(stream)
    elif isinstance(stream, bytes):
        stream = io.BytesIO(stream)
    try:
        iterator = iter(stream)
    except TypeError as exc:
        raise ValueError("nhmmer_invalid_stream") from exc
    offset, number = 0, 0
    for chunk in iterator:
        if not isinstance(chunk, (str, bytes)):
            raise ValueError("nhmmer_invalid_stream_line")
        for raw in chunk.splitlines(keepends=True):
            number += 1
            data = raw.encode("utf-8") if isinstance(raw, str) else raw
            locator = {"artifact_role": role, "artifact_ref": artifact_ref,
                       "line_number": number, "byte_start": offset, "byte_end": offset + len(data)}
            offset += len(data)
            try:
                text = data.decode("utf-8")
                error = None
            except UnicodeDecodeError:
                text, error = data.decode("utf-8", errors="replace"), "nhmmer_invalid_utf8"
            yield {"text": text, "locator": locator, "error": error,
                   **({"raw_bytes_hex": data.hex()} if error else {})}


def _number(token, field, issues, locator, *, integer=False, positive=False, nonnegative=False):
    if token is None or token in _MISSING:
        issues.append(_issue("nhmmer_missing_native_field", field=field, locator=locator))
        return None
    try:
        if integer and not re.fullmatch(r"[+]?[0-9]+", token):
            raise ValueError()
        value = int(token) if integer else float(token)
        if (not math.isfinite(value) or (positive and value <= 0)
                or (nonnegative and value < 0)):
            raise ValueError()
        return value
    except (ValueError, OverflowError):
        issues.append(_issue("nhmmer_invalid_native_number", field=field, locator=locator, raw_value=token))
        return None


def _coordinates(native, issues, locator):
    result = {"convention": "zero_based_half_open", "native_convention": "one_based_inclusive"}
    for axis, start, end in (("model", "hmm_from", "hmm_to"),
                            ("sequence", "ali_from", "ali_to"),
                            ("sequence_envelope", "env_from", "env_to")):
        left, right = native.get(start), native.get(end)
        interval = [min(left, right) - 1, max(left, right)] if left and right else None
        if left and right:
            if axis == "model" and left > right:
                issues.append(_issue("nhmmer_descending_model_coordinates", locator=locator))
                interval = None
            if axis != "model" and left != right and native.get("strand") in {"+", "-"}:
                if (left < right) != (native["strand"] == "+"):
                    issues.append(_issue("nhmmer_strand_coordinate_mismatch", field=axis, locator=locator))
                    interval = None
        result[axis + "_interval"] = interval
    ali, env = result["sequence_interval"], result["sequence_envelope_interval"]
    if ali and env and not (env[0] <= ali[0] < ali[1] <= env[1]):
        issues.append(_issue("nhmmer_envelope_excludes_alignment", locator=locator))
        result["sequence_envelope_interval"] = None
    return result


def iter_nhmmer_tblout_rows(stream, *, program, artifact_ref):
    """Yield independent rows, preserving invalid siblings and raw token values."""
    _program(program)
    occurrence = 0
    incompatible_header = False
    for item in _lines(stream, "tblout", artifact_ref):
        line, locator = item["text"], item["locator"]
        if line.lstrip().startswith("#"):
            # Explicit incompatible headers must never reinterpret the length axis.
            if "target name" in line and ("hmmfrom" not in line or "strand" not in line):
                incompatible_header = True
            if "target name" in line and ((program == "nhmmer" and "modlen" in line)
                    or (program == "nhmmscan" and "sq len" in line)):
                incompatible_header = True
            continue
        if not line.strip():
            continue
        occurrence += 1
        locator["row_occurrence"] = occurrence
        issues = []
        fields = line.split(maxsplit=15)
        raw_fields = {name: fields[i] if i < len(fields) else None for i, name in enumerate(TBL_FIELDS)}
        native = {name: (None if raw_fields[name] in _MISSING else raw_fields[name])
                  for name in TBL_FIELDS[:4]}
        for name in _COORD_FIELDS:
            native[name] = _number(raw_fields[name], name, issues, locator, integer=True, positive=True)
        for name in ("evalue", "score_bits", "bias_bits"):
            native[name] = _number(raw_fields[name], name, issues, locator, nonnegative=name == "evalue")
        native["strand"] = raw_fields["strand"] if raw_fields["strand"] in {"+", "-"} else None
        native.update(description=fields[15].rstrip() if len(fields) > 15 else None,
                      length_field_meaning="sequence_length" if program == "nhmmer" else "model_length",
                      reported=True, included=None)
        if native["strand"] is None:
            issues.append(_issue("nhmmer_invalid_strand", locator=locator))
        if len(fields) < 15:
            issues.append(_issue("nhmmer_truncated_tblout_row", locator=locator, fixed_fields_observed=len(fields)))
        if item["error"]:
            issues.append(_issue(item["error"], locator=locator))
        if incompatible_header:
            issues.append(_issue("nhmmer_incompatible_tblout_header", locator=locator))
        coords = _coordinates(native, issues, locator)
        yield {"record_key": f"tblout:line:{locator['line_number']}", "locator": locator,
            "status": "invalid" if len(fields) < 15 or incompatible_header else "partial" if issues else "valid",
            "native": native, "coordinates": coords, "raw": line, "raw_fields": raw_fields,
            "query_occurrence": None, "target_occurrence": None, "issues": issues,
            **({"raw_bytes_hex": item["raw_bytes_hex"]} if item.get("raw_bytes_hex") else {})}


def _finish_stdout_locus(items, query, target_occurrence, program, show_accessions=False):
    locator = deepcopy(items[0]["locator"])
    locator.update(byte_end=items[-1]["locator"]["byte_end"],
        end_line_number=items[-1]["locator"]["line_number"],
        query_occurrence=query["occurrence"], target_occurrence=target_occurrence)
    raw = "".join(item["text"] for item in items)
    target = items[0]["text"][2:].strip().split(maxsplit=1)
    native = {key: None for key in TBL_FIELDS}
    native.update(query_name=query["name"], query_accession=query.get("accession"),
        target_name=target[0] if target and not show_accessions else None,
        target_accession=target[0] if target and show_accessions else None,
        target_display_id=target[0] if target else None,
        description=target[1] if len(target) > 1 else "", reported=True, included=None,
        length_field_meaning="sequence_length" if program == "nhmmer" else "model_length")
    issues, summary_seen, in_alignment, chunks = [], False, False, []
    pending, previous = None, None
    for item in items[1:]:
        line, loc = item["text"], item["locator"]
        if item["error"]:
            issues.append(_issue(item["error"], locator=loc))
        fields = line.split()
        if fields and fields[0] in {"!", "?"}:
            if summary_seen:
                issues.append(_issue("nhmmer_multiple_locus_summaries", locator=loc))
                continue
            summary_seen = True
            native["included"] = fields[0] == "!"
            native["inclusion_flag"] = fields[0]
            mapping = {"score_bits": 1, "bias_bits": 2, "evalue": 3, "hmm_from": 4,
                       "hmm_to": 5, "ali_from": 7, "ali_to": 8, "env_from": 10,
                       "env_to": 11, "length_field": 13, "accuracy": 14}
            for key, index in mapping.items():
                native[key] = _number(fields[index] if index < len(fields) else None, key, issues, loc,
                    integer=key in _COORD_FIELDS, positive=key in _COORD_FIELDS,
                    nonnegative=key in {"evalue", "accuracy"})
            if native.get("accuracy") is not None and native["accuracy"] > 1:
                native["accuracy"] = None
                issues.append(_issue("nhmmer_accuracy_out_of_range", locator=loc))
            native["boundary_flags"] = [fields[i] if i < len(fields) else None for i in (6, 9, 12)]
            if native["ali_from"] and native["ali_to"]:
                native["strand"] = "+" if native["ali_from"] < native["ali_to"] else "-"
            continue
        if line.strip() == "Alignment:":
            in_alignment = True
            continue
        if not in_alignment:
            continue
        match = _RESIDUES.match(line)
        if match:
            part = {"label": match[1], "from": None if match[2] == "-" else int(match[2]),
                    "text": match[3], "to": None if match[4] == "-" else int(match[4]),
                    "locator": deepcopy(loc), "column_offset": match.start(3)}
            if pending is None:
                pending = {"model": part, "sequence": None, "posterior": None, "annotations": []}
            else:
                pending["sequence"] = part
                chunks.append(pending)
                previous, pending = pending, None
            continue
        pp = re.match(r"^\s*(\S+)\s+PP\s*$", line)
        if pp and previous is not None:
            previous["posterior"] = pp[1]
            previous["posterior_locator"] = deepcopy(loc)
        elif pending is not None:
            pending["annotations"].append({"raw": line, "locator": deepcopy(loc)})
        elif previous is not None and line.strip():
            previous["annotations"].append({"raw": line, "locator": deepcopy(loc)})
    if pending is not None:
        chunks.append(pending)
        issues.append(_issue("nhmmer_truncated_alignment_chunk", locator=locator))
    if not summary_seen:
        issues.append(_issue("nhmmer_missing_locus_summary", locator=locator))
    coordinates = _coordinates(native, issues, locator)
    alignment = None
    if chunks:
        alignment_issues = []
        expected = {"model": native.get("hmm_from"), "sequence": native.get("ali_from")}
        direction = -1 if native.get("strand") == "-" else 1
        model_text, seq_text, pp_parts = [], [], []
        for chunk in chunks:
            for role in ("model", "sequence"):
                part = chunk[role]
                if part is None:
                    alignment_issues.append(_issue("nhmmer_missing_alignment_operand", field=role, locator=locator))
                    continue
                allowed = r"[A-Za-z.]+" if role == "model" else r"[A-Za-z-]+"
                if re.fullmatch(allowed, part["text"]) is None:
                    alignment_issues.append(_issue("nhmmer_invalid_alignment_symbol", field=role, locator=part["locator"]))
                labels = {query["name"], query.get("accession")} if ((role == "model") == (program == "nhmmer")) else {native["target_display_id"]}
                if part["label"] not in labels:
                    alignment_issues.append(_issue("nhmmer_alignment_label_mismatch", field=role, locator=part["locator"]))
                count = sum(c.isalpha() for c in part["text"])
                step = 1 if role == "model" else direction
                # HMMER prints k1,k1-1 for all-insert model chunks; sequence
                # all-delete chunks use '-' endpoints instead.
                if count == 0 and role == "sequence":
                    correct = part["from"] is None and part["to"] is None
                else:
                    correct = (expected[role] is not None and part["from"] == expected[role]
                        and part["to"] == expected[role] + step * (count - 1))
                if not correct:
                    alignment_issues.append(_issue("nhmmer_alignment_chunk_coordinates", field=role, locator=part["locator"]))
                if expected[role] is not None:
                    expected[role] += step * count
                (model_text if role == "model" else seq_text).append(part["text"])
            if chunk["model"] and chunk["sequence"] and len(chunk["model"]["text"]) != len(chunk["sequence"]["text"]):
                alignment_issues.append(_issue("nhmmer_alignment_columns_mismatch", locator=locator))
            pp_parts.append(chunk["posterior"])
        for role, end in (("model", native.get("hmm_to")), ("sequence", native.get("ali_to"))):
            if end is not None and expected[role] != end + (1 if role == "model" else direction):
                alignment_issues.append(_issue("nhmmer_alignment_endpoint_mismatch", field=role, locator=locator))
        model, sequence = "".join(model_text), "".join(seq_text)
        posterior = "".join(pp_parts) if all(part is not None for part in pp_parts) else None
        pp_issues = []
        if posterior is not None and len(posterior) != len(sequence):
            pp_issues.append(_issue("nhmmer_posterior_columns_mismatch", locator=locator))
        if posterior is not None and any(symbol not in "0123456789*." for symbol in posterior):
            pp_issues.append(_issue("nhmmer_invalid_posterior_symbol", locator=locator))
        if not alignment_issues and any(a == "." and b == "-" for a, b in zip(model, sequence)):
            alignment_issues.append(_issue("nhmmer_double_gap_alignment", locator=locator))
        alignment = {"model_aligned": model, "sequence_aligned": sequence, "posterior": posterior,
            "chunks": chunks, "valid": not alignment_issues, "posterior_valid": posterior is not None and not pp_issues,
            "issues": alignment_issues + pp_issues}
        issues.extend(alignment_issues + pp_issues)
    return {"kind": "locus", "record_key": f"stdout:query:{query['occurrence']}:locus:{target_occurrence}",
        "locator": locator, "query_record_key": query["record_key"], "query_occurrence": query["occurrence"],
        "target_occurrence": target_occurrence, "native": native, "coordinates": coordinates,
        "alignment": alignment, "raw": raw, "status": "partial" if issues else "valid", "issues": issues}


def _statistic(item):
    line = item["text"].strip()
    match = re.match(r"^(Query model\(s\)|Target model\(s\)|Target sequences|Query sequence\(s\)):\s*(\d+)\s+\((\d+) (nodes|residues searched)\)", line)
    if match:
        return {"name": match[1], "count": int(match[2]), "count_unit": "models" if "model" in match[1] else "sequences",
            "positions": int(match[3]), "positions_unit": "model_nodes" if match[4] == "nodes" else "nucleotides_searched",
            "raw": item["text"], "locator": deepcopy(item["locator"])}
    match = re.match(r"^(Residues passing .+ filter|Total number of hits):\s*(\d+)\s+\(([^)]+)\)(?:; expected \(([^)]+)\))?", line)
    if match:
        issues = []
        return {"name": match[1], "count": int(match[2]),
            "count_unit": "loci" if match[1] == "Total number of hits" else "nucleotide_positions",
            "native_fraction": _number(match[3], "native_fraction", issues, item["locator"], nonnegative=True),
            "expected_fraction": _number(match[4], "expected_fraction", issues, item["locator"], nonnegative=True) if match[4] else None,
            "raw": item["text"], "locator": deepcopy(item["locator"]), "issues": issues}
    return {"name": None, "raw": item["text"], "locator": deepcopy(item["locator"])}


def _finish_query_statistics(query):
    """Explain native fractions without recovering absent unrounded numerators.

HMMER's Total number of hits row prints a hit COUNT beside a different
fraction: summed aligned sequence positions / (searched residues * models).
It is not hit count divided by search space. The position sum is not printed.
"""
    residues = [item["positions"] for item in query["statistics"]
                if item.get("positions_unit") == "nucleotides_searched"]
    models = [item["count"] for item in query["statistics"] if item.get("count_unit") == "models"]
    denominator = residues[0] * models[0] if len(residues) == len(models) == 1 else None
    for item in query["statistics"]:
        if "native_fraction" not in item:
            continue
        is_total = item["name"] == "Total number of hits"
        item.update(fraction_numerator=None if is_total else item["count"],
            fraction_denominator=denominator, fraction_unit="fraction_of_nucleotide_model_comparisons",
            fraction_input_fields=["native.pos_output" if is_total else "native.filter_position_count",
                                   "native.nres", "native.nmodels"],
            fraction_numerator_unavailable_reason="summed_aligned_position_count_not_printed" if is_total else None,
            fraction_precision="native_rounded_three_significant_digits")
    return query


def iter_nhmmer_stdout_records(stream, *, program, artifact_ref):
    """Yield records with original occurrences; buffer only the current locus."""
    _program(program)
    query, locus, occurrence, target_occurrence = None, [], 0, 0
    in_statistics, end, show_accessions = False, 0, False
    for item in _lines(stream, "stdout", artifact_ref):
        line, locator = item["text"], item["locator"]
        end = locator["byte_end"]
        boundary = (line.startswith(("Query:", ">>", "Internal pipeline")) or line.strip() in {"//", "[ok]"})
        if boundary and locus:
            yield _finish_stdout_locus(locus, query, target_occurrence, program, show_accessions)
            locus = []
        match = _QUERY.match(line.strip())
        if line.startswith("Query:"):
            if query:
                query["issues"].append(_issue("nhmmer_unterminated_query", locator=query["locator"]))
                query.update(kind="query_end", terminated=False)
                yield deepcopy(_finish_query_statistics(query))
            occurrence += 1
            target_occurrence, in_statistics = 0, False
            query = {"kind": "query_start", "record_key": f"stdout:query:{occurrence}",
                "locator": deepcopy(locator), "name": match[1] if match else None,
                "accession": None, "occurrence": occurrence, "length": int(match[3]) if match else None,
                "length_axis": ("model" if match[2] == "M" else "sequence") if match else None,
                "statistics": [], "annotations": [], "locus_count": 0, "issues": []}
            if not match or match[2] != ("M" if program == "nhmmer" else "L"):
                query["issues"].append(_issue("nhmmer_query_header_mismatch", locator=locator))
            yield deepcopy(query)
        elif line.startswith(">>"):
            if query is None:
                yield {"kind": "issue", **_issue("nhmmer_locus_without_query", locator=locator)}
            else:
                target_occurrence += 1
                query["locus_count"] += 1
                locus = [item]
        elif line.startswith("Internal pipeline"):
            in_statistics = True
        elif line.strip() == "//":
            if query:
                query["locator"]["byte_end"] = end
                query["locator"]["end_line_number"] = locator["line_number"]
                query.update(kind="query_end", terminated=True)
                yield deepcopy(_finish_query_statistics(query))
                query = None
            in_statistics = False
        elif line.strip() == "[ok]":
            yield {"kind": "completion", "native_complete": True, "locator": deepcopy(locator)}
        elif locus:
            locus.append(item)
        elif query is not None:
            if line.startswith("Accession:"):
                query["accession"] = line.split(":", 1)[1].strip()
            elif in_statistics and line.strip() and set(line.strip()) != {"-"}:
                query["statistics"].append(_statistic(item))
            elif line.strip():
                query["annotations"].append({"raw": line, "locator": deepcopy(locator)})
        elif line.strip():
            if line.startswith("# prefer accessions over names:") and line.split(":", 1)[1].strip() == "yes":
                show_accessions = True
            yield {"kind": "header", "raw": line, "locator": deepcopy(locator),
                   "issues": [_issue(item["error"], locator=locator)] if item["error"] else []}
    if locus:
        yield _finish_stdout_locus(locus, query, target_occurrence, program, show_accessions)
    if query:
        query.update(kind="query_end", terminated=False)
        query["locator"]["byte_end"] = end
        query["issues"].append(_issue("nhmmer_unterminated_query", locator=query["locator"]))
        yield _finish_query_statistics(query)


def iter_nhmmer_stdout_queries(stream, *, program, artifact_ref):
    """Yield query summaries without collecting their potentially many loci."""
    for record in iter_nhmmer_stdout_records(stream, program=program, artifact_ref=artifact_ref):
        if record["kind"] == "query_end":
            yield record


