"""Pure HMMER protein-search native-output parsers and metadata extractors.

Streaming interfaces (never open a path):
``iter_hmmer_table_rows(stream, *, program, role, artifact_ref, engine_version=None)``
yields ``{kind: hit|domain|annotation|issue, data: dict}`` per supplied line.
``iter_hmmer_stdout_queries(stream, *, program, artifact_ref, engine_version=None)``
yields bundles with query/hits/domains/iterations/statistics/issues, retaining at
most one query occurrence. Bytes streams retain exact byte offsets; text streams
use UTF-8 byte offsets. Occurrences are zero based, native domain ordinals are
one based. No parser selects hits, resources, retries or scientific conclusions.

``iter_hmmer_stdout_events(stream, *, program, artifact_ref, engine_version=None)``
yields ``{kind: query|hit|domain|iteration|statistic|annotation|issue, data: dict}``
while retaining at most one target block. Query events contain header facts;
native // and [ok] completion observations are annotation events. Iteration
events arrive at round closure and retain native summary measurements. Domain
to-hit associations are left for the caller's exact, ambiguity-aware join.
"""
from __future__ import annotations

from copy import deepcopy
import io
import json
import math
import re

PROGRAMS = {"phmmer", "hmmscan", "hmmsearch", "jackhmmer"}
TBL_FIELDS = "target_name target_accession query_name query_accession sequence_evalue sequence_score_bits sequence_bias_bits best_domain_evalue best_domain_score_bits best_domain_bias_bits expected_domains regions clustered_regions overlapping_envelopes envelopes domains reported_domains included_domains".split()
DOM_FIELDS = "target_name target_accession target_length query_name query_accession query_length sequence_evalue sequence_score_bits sequence_bias_bits reported_domain_ordinal reported_domain_count conditional_evalue independent_evalue domain_score_bits domain_bias_bits hmm_from hmm_to ali_from ali_to env_from env_to accuracy".split()
INT_FIELDS = set("target_length query_length reported_domain_ordinal reported_domain_count regions clustered_regions overlapping_envelopes envelopes domains reported_domains included_domains hmm_from hmm_to ali_from ali_to env_from env_to".split())
TEXT_FIELDS = {"target_name", "target_accession", "query_name", "query_accession"}
QUERY_RE = re.compile(r"^Query:\s+(\S+)\s+\[([LM])=(\d+)\]")
RESIDUE_RE = re.compile(r"^\s*(\S+)\s+(\d+|-)\s+([A-Za-z.*-]+)\s+(\d+|-)\s*$")


def finite_json(value, *, code="hmmer_nonfinite_or_nonjson_input"):
    """Validate JSON values without accepting Python objects/coerced keys."""
    if value is None or type(value) in (bool, str, int):
        return
    if type(value) is float:
        if math.isfinite(value):
            return
        raise ValueError(code)
    if type(value) is list:
        for item in value:
            finite_json(item, code=code)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            finite_json(item, code=code)
        return
    raise ValueError(code)


def _program(program):
    if not isinstance(program, str) or program not in PROGRAMS:
        raise ValueError("hmmer_unsupported_protein_program")


def _key(ref, role, position):
    return json.dumps([ref, role, position], separators=(",", ":"), sort_keys=True)


def _row(ref, role, position, locator=None):
    return {"record_key": _key(ref, role, position),
            "locator": {"artifact_ref": deepcopy(ref), "artifact_role": role, **(locator or {})},
            "native": {}, "issues": []}


def _issue(code, row=None, **details):
    return {"code": code, **({"record_key": row["record_key"], "locator": deepcopy(row["locator"])} if row else {}), **details}


def _number(value, *, integer=False, minimum=None, maximum=None):
    if value is None or value == "-":
        return None
    if type(value) is bool or not isinstance(value, (str, int, float)):
        raise ValueError("hmmer_invalid_numeric_value")
    try:
        number = int(value) if integer else float(value)
    except (ValueError, OverflowError):
        raise ValueError("hmmer_invalid_numeric_value") from None
    if integer and str(value).strip() != str(number) and value != number:
        raise ValueError("hmmer_invalid_integer_value")
    if not math.isfinite(number) or minimum is not None and number < minimum or maximum is not None and number > maximum:
        raise ValueError("hmmer_numeric_value_out_of_range")
    return number


def _put_number(row, field, value, **kwargs):
    try:
        row["native"][field] = _number(value, **kwargs)
    except ValueError as error:
        row["native"][field] = None
        row["issues"].append(_issue(str(error), row, field=field, supplied=value))


def _status(value, row, field):
    if value is None or type(value) is bool:
        return value
    row["issues"].append(_issue("hmmer_invalid_native_flag", row, field=field))
    return None


def _text_identity(value, row, field):
    if value is None or isinstance(value, str):
        return value
    row["issues"].append(_issue("hmmer_identity_must_be_string_or_null", row, field=field, supplied=deepcopy(value)))
    return None


def _statistic_fields(text):
    """Extract only directly printed native statistical populations."""
    patterns = (
        (r"^Query model\(s\):\s+(\d+)\s+\((\d+) nodes\)", ("query_model_count", "query_model_positions")),
        (r"^Target model\(s\):\s+(\d+)\s+\((\d+) nodes\)", ("target_model_count", "target_model_positions")),
        (r"^Query sequence\(s\):\s+(\d+)\s+\((\d+) residues searched\)", ("query_sequence_count", "query_residues_searched")),
        (r"^Target sequences:\s+(\d+)\s+\((\d+) residues searched\)", ("target_sequence_count", "target_residues_searched")),
    )
    for pattern, names in patterns:
        match = re.match(pattern, text)
        if match: return dict(zip(names, map(int, match.groups())))
    for pattern, name in ((r"^Initial search space \(Z\):\s+(\S+)", "Z"), (r"^Domain search space\s+\(domZ\):\s+(\S+)", "domZ")):
        match = re.match(pattern, text)
        if match:
            try: return {name: _number(match[1], minimum=0)}
            except ValueError: return {}
    return {}


def _lines(stream):
    if isinstance(stream, (str, bytes)) or not hasattr(stream, "__iter__"):
        raise ValueError("hmmer_stream_required")
    offset = 0
    for lineno, raw in enumerate(stream, 1):
        if isinstance(raw, bytes):
            size = len(raw)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None
        elif isinstance(raw, str):
            text, size = raw, len(raw.encode("utf-8"))
        else:
            raise ValueError("hmmer_invalid_stream_line")
        yield lineno, offset, offset + size, text
        offset += size


def iter_hmmer_table_rows(stream, *, program, role, artifact_ref, engine_version=None):
    """Read independent fixed-format rows, preserving damaged sibling fields."""
    _program(program)
    finite_json(artifact_ref)
    if role not in {"tblout", "domtblout"}:
        raise ValueError("hmmer_unsupported_table_role")
    fields = TBL_FIELDS if role == "tblout" else DOM_FIELDS
    for lineno, start, end, text in _lines(stream):
        row = _row(artifact_ref, role, lineno, {"line_number": lineno, "byte_span": [start, end]})
        if text is None:
            yield {"kind": "issue", "data": _issue("hmmer_native_not_utf8", row)}
            continue
        if not text.strip():
            continue
        row["raw_line"] = text
        if text.startswith("#"):
            row["text"] = text.rstrip("\r\n")
            yield {"kind": "annotation", "data": row}
            continue
        parts = text.rstrip("\r\n").split(maxsplit=len(fields))
        if len(parts) < len(fields):
            yield {"kind": "issue", "data": _issue("hmmer_truncated_table_row", row, expected_columns=len(fields), observed_columns=len(parts), raw_line=text)}
            continue
        row["native_fields"] = dict(zip(fields, parts))
        row["description"] = parts[len(fields)] if len(parts) > len(fields) else ""
        for name, value in zip(fields, parts):
            if name in TEXT_FIELDS:
                row[name] = None if value == "-" else value
                continue
            kwargs = {"integer": name in INT_FIELDS}
            if name in INT_FIELDS or "evalue" in name or name == "expected_domains":
                kwargs["minimum"] = 0
            if name == "accuracy":
                kwargs.update(minimum=0, maximum=1)
            _put_number(row, name, value, **kwargs)
        row.update(query_occurrence=None, target_occurrence=None, iteration=None,
                   iteration_scope="final_round_only" if program == "jackhmmer" else "single_search",
                   is_reported=True, is_included=None)
        if role == "domtblout":
            ordinal, count = row["native"].get("reported_domain_ordinal"), row["native"].get("reported_domain_count")
            if ordinal is not None and count is not None and not 1 <= ordinal <= count:
                row["issues"].append(_issue("hmmer_reported_domain_ordinal_count_inconsistent", row))
        yield {"kind": "hit" if role == "tblout" else "domain", "data": row}


def _stdout_query(lines, *, program, artifact_ref, occurrence):
    first = lines[0]
    match = QUERY_RE.match(first[3])
    q = _row(artifact_ref, "stdout_query", first[0], {"artifact_role": "stdout", "line_number": first[0],
          "byte_span": [first[1], lines[-1][2]], "query_occurrence": occurrence})
    q.update(name=match[1], length=int(match[3]), kind="profile" if match[2] == "M" else "protein_sequence",
             occurrence=occurrence, complete=any(x[3].strip() == "//" for x in lines if x[3]))
    bundle = {"query": q, "hits": [], "domains": [], "iterations": [], "statistics": [], "issues": [], "annotations": []}
    iteration, scores, included, target = 1, False, True, None
    target_counts = {}
    current = None
    models = {1: q["length"] if program != "hmmscan" else None}
    def context(row):
        row.update(query_name=q["name"], query_accession=q.get("accession"), query_record_key=q["record_key"],
                   query_occurrence=occurrence, iteration=iteration)
        row["locator"].update(query_occurrence=occurrence, iteration=iteration)
        return row
    def iterrow(number, lineno, start, end):
        r = context(_row(artifact_ref, "stdout_iteration", lineno, {"artifact_role": "stdout", "line_number": lineno, "byte_span": [start, end]}))
        r.update(iteration=number, dependent_round=program == "jackhmmer", native_converged=None,
                 native_new_targets=None, native_alignment_subsequences=None, native_previous_subsequences=None)
        return r
    bundle["iterations"].append(iterrow(1, first[0], first[1], first[2]))
    def finish_alignment():
        nonlocal current
        if current is None:
            return
        d, chunks = current
        display = {"model": "", "aseq": "", "mline": "", "ppline": "", "chunks": chunks,
                   "model_name": None, "sequence_name": None}
        if not chunks or any("sequence" not in c for c in chunks):
            d["issues"].append(_issue("hmmer_incomplete_alignment_display", d))
            display["valid"] = False
        else:
            display["valid"] = True
        for c in chunks:
            display["model"] += c["model"]["aligned"]
            display["aseq"] += c.get("sequence", {}).get("aligned", "")
            display["mline"] += c.get("mline", " " * len(c["model"]["aligned"]))
            display["ppline"] += c.get("ppline", "." * len(c["model"]["aligned"]))
            display["model_name"] = c["model"]["name"]
            if "sequence" in c:
                display["sequence_name"] = c["sequence"]["name"]
        if not any("ppline" in c for c in chunks):
            display["ppline"] = None
        d["alignment"] = display
        current = None
    for lineno, start, end, text in lines[1:]:
        if text is None:
            bundle["issues"].append({"code": "hmmer_native_not_utf8", "line_number": lineno, "byte_span": [start, end]})
            continue
        rmatch = re.match(r"@@ Round:\s+(\d+)", text)
        if rmatch:
            finish_alignment()
            iteration = int(rmatch[1]); target = None; scores = False
            bundle["iterations"].append(iterrow(iteration, lineno, start, end))
        ir = bundle["iterations"][-1]
        for pattern, field in [(r"@@ New targets included:\s+(\d+)", "native_new_targets"),
                               (r"@@ Model size:\s+(\d+)", "model_length")]:
            m = re.match(pattern, text)
            if m:
                ir[field] = int(m[1])
                if field == "model_length": models[iteration] = int(m[1])
        m = re.match(r"@@ New alignment includes:\s+(\d+) subseqs \(was (\d+)\)", text)
        if m:
            ir.update(native_alignment_subsequences=int(m[1]), native_previous_subsequences=int(m[2]))
        if "@@ CONVERGED" in text:
            ir["native_converged"] = True
        if "@@ Continuing to next round" in text:
            ir["native_converged"] = False
        if text.startswith("Accession:"):
            q["accession"] = text.split(":", 1)[1].strip()
        if text.startswith("Scores for complete sequence"):
            finish_alignment(); scores = True; included = True; target = None
            continue
        if "------ inclusion threshold ------" in text:
            included = False
        if text.startswith("Domain annotation"):
            scores = False
        if scores:
            fields = text.split(maxsplit=10)
            flag = fields.pop(0) if fields and fields[0] in {"+", "-"} else None
            try:
                if len(fields) < 9:
                    continue
                vals = [_number(fields[i], integer=i == 7, minimum=0 if i in {0, 3, 6, 7} else None) for i in range(8)]
            except ValueError:
                continue
            row = context(_row(artifact_ref, "stdout_hit", lineno, {"artifact_role": "stdout", "line_number": lineno, "byte_span": [start, end]}))
            names = ["sequence_evalue", "sequence_score_bits", "sequence_bias_bits", "best_domain_evalue", "best_domain_score_bits", "best_domain_bias_bits", "expected_domains", "reported_domains"]
            row["native"] = dict(zip(names, vals))
            row.update(target_name=fields[8], target_accession=None, description=" ".join(fields[9:]),
                       is_reported=True, is_included=included, native_membership_flag=flag,
                       is_new=flag == "+" if program == "jackhmmer" else None,
                       is_dropped=flag == "-" if program == "jackhmmer" else None, raw_line=text)
            bundle["hits"].append(row)
            continue
        if text.startswith(">>"):
            finish_alignment()
            name = text[2:].strip().split()[0]
            target_counts[iteration] = target_counts.get(iteration, 0) + 1
            target = (name, target_counts[iteration] - 1)
            continue
        if text.startswith(("Internal pipeline", "//", "@@")):
            finish_alignment()
            if not text.startswith("@@"):
                target = None
        fields = text.split()
        if target and len(fields) == 16 and fields[0].isdigit() and fields[1] in {"!", "?"}:
            d = context(_row(artifact_ref, "stdout_domain", lineno, {"artifact_role": "stdout", "line_number": lineno, "byte_span": [start, end], "target_occurrence": target[1], "reported_domain_ordinal": int(fields[0])}))
            d.update(target_name=target[0], target_accession=None, target_occurrence=target[1],
                     is_reported=True, is_included=fields[1] == "!", raw_line=text)
            mapping = {"reported_domain_ordinal": 0, "domain_score_bits": 2, "domain_bias_bits": 3,
                       "conditional_evalue": 4, "independent_evalue": 5, "hmm_from": 6, "hmm_to": 7,
                       "ali_from": 9, "ali_to": 10, "env_from": 12, "env_to": 13, "accuracy": 15}
            for name, index in mapping.items():
                _put_number(d, name, fields[index], integer=name in INT_FIELDS,
                            minimum=0 if name in INT_FIELDS or "evalue" in name or name == "accuracy" else None,
                            maximum=1 if name == "accuracy" else None)
            d["native"].update(model_length=models.get(iteration), sequence_length=q["length"] if program == "hmmscan" else None)
            bundle["domains"].append(d)
            continue
        dm = re.match(r"\s*== domain (\d+)\s", text)
        if dm and target:
            finish_alignment()
            found = [d for d in bundle["domains"] if d["iteration"] == iteration and d["target_name"] == target[0]
                     and d["target_occurrence"] == target[1] and d["native"].get("reported_domain_ordinal") == int(dm[1])]
            if len(found) == 1:
                current = (found[0], [])
            else:
                bundle["issues"].append({"code": "hmmer_alignment_domain_association_ambiguous", "line_number": lineno})
            continue
        if current:
            d, chunks = current
            rm = RESIDUE_RE.match(text)
            if rm:
                part = {"name": rm[1], "from": None if rm[2] == "-" else int(rm[2]), "to": None if rm[4] == "-" else int(rm[4]), "aligned": rm[3], "line_number": lineno}
                if not chunks or "sequence" in chunks[-1]:
                    chunks.append({"model": part, "column_start": rm.start(3)})
                else:
                    chunks[-1]["sequence"] = part
                continue
            if chunks:
                c = chunks[-1]; col = c["column_start"]; length = len(c["model"]["aligned"])
                if text.rstrip().endswith(" PP"):
                    c["ppline"] = text[col:col + length]
                elif "sequence" not in c and text.strip() and not text.rstrip().endswith((" RF", " CS", " MM")):
                    c["mline"] = text[col:col + length].ljust(length)
            continue
        if ":" in text and not text.startswith("@@"):
            bundle["statistics"].append(context(_row(artifact_ref, "stdout_statistic", lineno, {"artifact_role": "stdout", "line_number": lineno, "byte_span": [start, end]})) | {"raw_line": text, "native": _statistic_fields(text)})
    finish_alignment()
    for d in bundle["domains"]:
        candidates = [h for h in bundle["hits"] if h["iteration"] == d["iteration"] and h["target_name"] == d["target_name"]]
        if len(candidates) == 1:
            d["hit_record_key"] = candidates[0]["record_key"]
            for k, v in candidates[0]["native"].items():
                if k.startswith("sequence_"): d["native"][k] = v
        elif len(candidates) > 1:
            d["issues"].append(_issue("hmmer_stdout_hit_association_ambiguous", d))
    if not q["complete"]:
        q["issues"].append(_issue("hmmer_query_terminator_missing", q))
    return bundle


def iter_hmmer_stdout_queries(stream, *, program, artifact_ref, engine_version=None):
    """Yield exact query occurrences, including all dependent jackhmmer rounds."""
    _program(program); finite_json(artifact_ref)
    group, occurrence = [], 0
    for item in _lines(stream):
        if item[3] and QUERY_RE.match(item[3]):
            if group:
                yield _stdout_query(group, program=program, artifact_ref=artifact_ref, occurrence=occurrence)
                occurrence += 1
            group = [item]
        elif group:
            group.append(item)
    if group:
        yield _stdout_query(group, program=program, artifact_ref=artifact_ref, occurrence=occurrence)


def iter_hmmer_stdout_events(stream, *, program, artifact_ref, engine_version=None):
    """Stream bounded target blocks; no full-hit-population list or index.

Every emitted native locator is absolute in the supplied stream. Internal
context lines are used only to interpret a block, and never emitted as facts.
The caller may persist and join events in SQLite without holding query results.
"""
    _program(program); finite_json(artifact_ref)
    header = None
    occurrence = -1
    round_context = []
    target_block = []
    target_occurrence = 0
    iteration = 1
    iteration_row = None
    scores = False
    included = True
    # Native occurrence counters refer to target blocks in the round, not to
    # a dictionary of all returned target names; memory stays bounded.
    target_number = 0

    def context(row):
        if header is not None:
            qmatch = QUERY_RE.match(header[3])
            row.update(query_name=qmatch[1], query_record_key=_key(artifact_ref, "stdout_query", header[0]),
                       query_occurrence=occurrence, iteration=iteration)
            row["locator"].update(query_occurrence=occurrence, iteration=iteration)
        return row

    def flush_target():
        if not target_block:
            return []
        bundle = _stdout_query([header, *round_context, *target_block], program=program,
                               artifact_ref=artifact_ref, occurrence=occurrence)
        events = []
        for d in bundle["domains"]:
            # Target occurrence is the absolute target block ordinal within
            # this query round; names are preserved independently.
            d["target_occurrence"] = target_occurrence
            d["locator"]["target_occurrence"] = target_occurrence
            d.pop("hit_record_key", None)
            events.append({"kind": "domain", "data": d})
        events.extend({"kind": "issue", "data": x} for x in bundle["issues"])
        target_block.clear()
        return events

    for item in _lines(stream):
        lineno, start, end, text = item
        loc = {"artifact_role": "stdout", "line_number": lineno, "byte_span": [start, end]}
        if text is None:
            yield {"kind": "issue", "data": {"code": "hmmer_native_not_utf8", "locator": {"artifact_ref": artifact_ref, **loc}}}
            if target_block: target_block.append(item)
            continue
        match = QUERY_RE.match(text)
        round_match = re.match(r"@@ Round:\s+(\d+)", text)
        if match or round_match or text.startswith((">>", "Internal pipeline", "//")):
            yield from flush_target()
        if match:
            if iteration_row is not None:
                yield {"kind": "iteration", "data": iteration_row}
            header = item; occurrence += 1; iteration = 1; round_context = []; target_number = 0
            q = _row(artifact_ref, "stdout_query", lineno, loc | {"query_occurrence": occurrence})
            q.update(name=match[1], length=int(match[3]), kind="profile" if match[2] == "M" else "protein_sequence", occurrence=occurrence, complete=None)
            yield {"kind": "query", "data": q}
            iteration_row = context(_row(artifact_ref, "stdout_iteration", lineno, loc))
            iteration_row.update(dependent_round=program == "jackhmmer", native_converged=None)
            scores = False; continue
        if round_match:
            if iteration_row is not None:
                yield {"kind": "iteration", "data": iteration_row}
            iteration = int(round_match[1]); round_context = [item]; target_number = 0
            iteration_row = context(_row(artifact_ref, "stdout_iteration", lineno, loc))
            iteration_row.update(dependent_round=program == "jackhmmer", native_converged=None)
        if text.startswith("@@ Model size:"):
            round_context.append(item)
        if text.startswith("@@") and iteration_row is not None:
            for pattern, field in ((r"@@ New targets included:\s+(\d+)", "native_new_targets"), (r"@@ Model size:\s+(\d+)", "model_length")):
                m = re.match(pattern, text)
                if m: iteration_row[field] = int(m[1])
            m = re.match(r"@@ New alignment includes:\s+(\d+) subseqs \(was (\d+)\)", text)
            if m: iteration_row.update(native_alignment_subsequences=int(m[1]), native_previous_subsequences=int(m[2]))
            if "CONVERGED" in text: iteration_row["native_converged"] = True
            if "Continuing to next round" in text: iteration_row["native_converged"] = False
        if text.startswith("Scores for complete sequence"):
            scores = True; included = True; score_header = item; continue
        if "------ inclusion threshold ------" in text:
            included = False
        if text.startswith("Domain annotation"):
            scores = False
        if scores and header is not None:
            ctx = [header, *round_context, score_header]
            if not included:
                ctx.append((lineno, start, start, "  ------ inclusion threshold ------\n"))
            parsed = _stdout_query([*ctx, item], program=program, artifact_ref=artifact_ref, occurrence=occurrence)
            for hit in parsed["hits"]:
                yield {"kind": "hit", "data": hit}
            continue
        if text.startswith(">>") and header is not None:
            target_block = [item]; target_occurrence = target_number; target_number += 1; continue
        if target_block:
            target_block.append(item); continue
        if text.strip() == "//":
            if iteration_row is not None:
                yield {"kind": "iteration", "data": iteration_row}; iteration_row = None
            a = context(_row(artifact_ref, "stdout_annotation", lineno, loc))
            a.update(text=text, native_query_terminated=True)
            yield {"kind": "annotation", "data": a}; continue
        is_statistic = ":" in text and not text.startswith(("#", "@@"))
        row = context(_row(artifact_ref, "stdout_statistic" if is_statistic else "stdout_annotation", lineno, loc))
        row["raw_line"] = text
        if is_statistic: row["native"] = _statistic_fields(text)
        if text.strip() == "[ok]": row["native_output_terminated"] = True
        if text.strip(): yield {"kind": "statistic" if is_statistic else "annotation", "data": row}
    yield from flush_target()
    if iteration_row is not None:
        yield {"kind": "iteration", "data": iteration_row}


def _operation(program, fmt, version):
    return {"program": program, "format": fmt, "engine_version": version, "alphabet": "amino",
            "mode": {"phmmer": "sequence_database_search", "hmmscan": "profile_database_scan",
                     "hmmsearch": "profile_sequence_database_search", "jackhmmer": "iterative_sequence_database_search"}[program]}


def _empty(operation):
    return {"schema": "hmmer_search_native_v1", "operation": operation, "hits": [], "domains": [],
            "queries": [], "iterations": [], "statistics": [], "annotations": [], "issues": [], "artifacts": {}, "checkpoints": []}


def parse_hmmer_api_result(payload, *, algorithm, artifact_ref):
    """Parse full provider result/page before filtering; indices are never renumbered."""
    if not isinstance(algorithm, str) or algorithm not in {"phmmer", "hmmscan"}:
        raise ValueError("hmmer_unsupported_api_algorithm")
    if type(payload) is not dict:
        raise ValueError("hmmer_api_payload_must_be_object")
    finite_json(payload); finite_json(artifact_ref)
    result_key = "result" if "result" in payload else "results" if "results" in payload else None
    result = payload.get(result_key) if result_key else payload
    out = _empty(_operation(algorithm, "hmmer_api_json", None))
    out["artifacts"] = {"api_json": {"artifact_ref": deepcopy(artifact_ref), "payload": deepcopy(payload)}}
    out["completion"] = {"provider_status": payload.get("status"), "page_count": payload.get("page_count"),
                         "output_complete": None, "hit_population_complete": None}
    if not isinstance(result, dict) or not isinstance(result.get("hits"), list):
        out["issues"].append({"code": "hmmer_api_result_hits_missing_or_invalid"})
        return out
    prefix = "/" + result_key if result_key else ""
    stats = result.get("stats", {})
    out["statistics"] = deepcopy(stats)
    if isinstance(stats, dict) and stats.get("algo") is not None and stats.get("algo") != algorithm:
        out["issues"].append({"code": "hmmer_api_algorithm_mismatch", "reported": stats.get("algo"), "selected": algorithm})
    query = _row(artifact_ref, "api_query", prefix, {"artifact_role": "api_json", "json_pointer": prefix, "query_occurrence": 0})
    query.update(name=None, accession=None, length=None, kind="protein_sequence", occurrence=0)
    out["queries"].append(query)
    for hi, raw in enumerate(result["hits"]):
        pointer = f"{prefix}/hits/{hi}"
        hit = _row(artifact_ref, "api_hit", pointer, {"artifact_role": "api_json", "hit_array_index": hi, "json_pointer": pointer})
        if not isinstance(raw, dict):
            out["issues"].append(_issue("hmmer_api_hit_not_object", hit, supplied=raw)); continue
        hit.update(native_record=deepcopy(raw), target_name=_text_identity(raw.get("name"), hit, "name"), target_accession=_text_identity(raw.get("acc"), hit, "acc"),
                   identifiers={k: deepcopy(raw.get(k)) for k in ("name", "acc", "index", "seqidx", "metadata")},
                   query_record_key=query["record_key"], query_occurrence=0, iteration=1,
                   is_reported=_status(raw.get("is_reported"), hit, "is_reported"),
                   is_included=_status(raw.get("is_included"), hit, "is_included"))
        mapping = {"sequence_evalue": "evalue", "sequence_score_bits": "score", "sequence_bias_bits": "bias",
                   "expected_domains": "nexpected", "regions": "nregions", "clustered_regions": "nclustered", "overlapping_envelopes": "noverlaps",
                   "envelopes": "nenvelopes", "domains": "ndom", "reported_domains": "nreported", "included_domains": "nincluded"}
        for name, source in mapping.items():
            _put_number(hit, name, raw.get(source), integer=name in INT_FIELDS,
                        minimum=0 if name in INT_FIELDS or "evalue" in name or name == "expected_domains" else None)
        out["hits"].append(hit)
        ds = raw.get("domains")
        if not isinstance(ds, list):
            hit["issues"].append(_issue("hmmer_api_domains_missing_or_invalid", hit)); continue
        for di, rd in enumerate(ds):
            dp = f"{pointer}/domains/{di}"
            d = _row(artifact_ref, "api_domain", dp, {"artifact_role": "api_json", "hit_array_index": hi, "domain_array_index": di, "json_pointer": dp})
            if not isinstance(rd, dict):
                out["issues"].append(_issue("hmmer_api_domain_not_object", d, supplied=rd)); continue
            d.update(native_record=deepcopy(rd), query_record_key=query["record_key"], query_occurrence=0, iteration=1,
                     hit_record_key=hit["record_key"], target_name=hit["target_name"], target_accession=hit["target_accession"],
                     is_reported=_status(rd.get("is_reported"), d, "is_reported"), is_included=_status(rd.get("is_included"), d, "is_included"))
            for name, source in {"domain_score_bits": "bitscore", "domain_bias_nats": "dombias", "envelope_score_nats": "envsc", "domain_correction_nats": "domcorrection", "optimal_accuracy_sum": "oasc", "conditional_evalue": "cevalue", "independent_evalue": "ievalue", "env_from": "ienv", "env_to": "jenv"}.items():
                _put_number(d, name, rd.get(source), integer=name in INT_FIELDS, minimum=0 if "evalue" in name or name in INT_FIELDS else None)
            ad = rd.get("alignment_display")
            if isinstance(ad, dict):
                d["alignment"] = {k: deepcopy(ad.get(k)) for k in ("model", "aseq", "mline", "ppline", "identity", "similarity")}
                model_name = _text_identity(ad.get("hmmname"), d, "alignment_display.hmmname")
                sequence_name = _text_identity(ad.get("sqname"), d, "alignment_display.sqname")
                d["alignment"].update(model_name=model_name, sequence_name=sequence_name, native_display=deepcopy(ad))
                for name, source in {"hmm_from": "hmmfrom", "hmm_to": "hmmto", "ali_from": "sqfrom", "ali_to": "sqto", "model_length": "m", "sequence_length": "l", "display_columns": "n"}.items():
                    _put_number(d, name, ad.get(source), integer=True, minimum=0)
                qname = sequence_name if algorithm == "hmmscan" else model_name
                qlength = d["native"].get("sequence_length" if algorithm == "hmmscan" else "model_length")
                if query["name"] is None:
                    query.update(name=qname, length=qlength)
                elif (qname, qlength) != (query["name"], query["length"]):
                    d["issues"].append(_issue("hmmer_api_query_identity_or_length_conflict", d))
                d["query_name"] = qname
                expected = model_name if algorithm == "hmmscan" else sequence_name
                if expected is not None and hit["target_name"] is not None and expected != hit["target_name"]:
                    d["issues"].append(_issue("hmmer_api_target_display_identity_mismatch", d))
                    d["alignment"]["valid"] = False
            else:
                d["issues"].append(_issue("hmmer_alignment_display_unavailable", d))
            for key in ("sequence_evalue", "sequence_score_bits", "sequence_bias_bits"):
                d["native"][key] = hit["native"].get(key)
            out["domains"].append(d)
    for h in out["hits"]:
        h["query_name"] = query["name"]
    return out


def _same_row(a, b, domain):
    # --acc selects a display label; table name/accession fields preserve the
    # explicit relationship and permit this exact join without guessed aliases.
    for role in ("query", "target"):
        labels = {x for x in (a.get(role + "_name"), a.get(role + "_accession")) if x is not None}
        if b.get(role + "_name") not in labels: return False
    names = ["reported_domain_ordinal", "hmm_from", "hmm_to", "ali_from", "ali_to"] if domain else ["sequence_evalue", "sequence_score_bits"]
    return all(a["native"].get(k) == b["native"].get(k) for k in names)


def _merge_tables(table, printed, *, domain, program, issues):
    matched = set()
    final = {}
    for r in printed:
        key = r.get("query_record_key")
        final[key] = max(final.get(key, 0), r.get("iteration") or 0)
    for row in table:
        candidates = [r for r in printed if _same_row(row, r, domain) and
                      (program != "jackhmmer" or r["iteration"] == final.get(r.get("query_record_key")))]
        twins = [r for r in table if _same_row(row, r, domain)]
        if len(candidates) == len(twins) == 1:
            other = candidates[0]; matched.add(other["record_key"])
            row["associations"] = [{"record_key": other["record_key"], "locator": deepcopy(other["locator"])}]
            row["native_representations"] = [deepcopy(other)]
            for key in ("query_record_key", "query_occurrence", "target_occurrence", "iteration", "is_included", "alignment", "hit_record_key", "native_membership_flag", "is_new", "is_dropped"):
                if key in other: row[key] = deepcopy(other[key])
            for key, val in other["native"].items():
                if key not in row["native"] or row["native"][key] is None: row["native"][key] = val
            row["issues"].extend(other["issues"])
        elif candidates:
            row["issues"].append(_issue("hmmer_table_stdout_association_ambiguous", row, candidate_keys=[r["record_key"] for r in candidates]))
        elif printed:
            row["issues"].append(_issue("hmmer_table_stdout_association_missing", row))
    # Unjoined representations remain explicit; consumers must not count them as
    # independent observations merely because their artifact roles differ.
    return table + [r for r in printed if r["record_key"] not in matched]


def _checkpoint_records(checkpoint, index):
    """Keep each appended native model/alignment record and declared round role."""
    role = checkpoint.get("role")
    if not isinstance(role, str) or role not in {"chkhmm", "chkali", "included_msa"}:
        raise ValueError("hmmer_unknown_checkpoint_role")
    text = checkpoint.get("text")
    if not isinstance(text, str): raise ValueError("hmmer_checkpoint_text_required")
    records, start, lines = [], 0, []
    byte = 0
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        lines.append(line); byte += len(line.encode("utf-8"))
        if line.strip() == "//":
            content = "".join(lines)
            r = _row(checkpoint.get("artifact_ref"), role, [index, len(records)], {"record_occurrence": len(records), "byte_span": [start, byte]})
            r.update(text=content, checkpoint_role="model_at_round_start" if role == "chkhmm" else "included_alignment_at_round_end" if role == "chkali" else "final_round_included_alignment",
                     iteration=checkpoint.get("iteration"), query_occurrence=checkpoint.get("query_occurrence"), complete=True)
            pattern = r"^NAME\s+(\S+)" if role == "chkhmm" else r"^#=GF ID\s+(\S+)"
            m = re.search(pattern, content, re.M); r["name"] = m[1] if m else None
            if role == "chkhmm":
                m = re.search(r"^LENG\s+(\d+)", content, re.M); r["model_length"] = int(m[1]) if m else None
            else:
                r["native_sequence_rows"] = [line.split() for line in lines if line.strip() and not line.startswith("#") and line.strip() != "//"]
            records.append(r); start = byte; lines = []
    if "".join(lines).strip():
        r = _row(checkpoint.get("artifact_ref"), role, [index, len(records)], {"record_occurrence": len(records), "byte_span": [start, byte]})
        r.update(text="".join(lines), complete=False, iteration=checkpoint.get("iteration"))
        r["issues"].append(_issue("hmmer_checkpoint_terminator_missing", r)); records.append(r)
    return records


def parse_hmmer_search_artifacts(*, program, artifacts, artifact_refs, engine_version, checkpoints=()):
    _program(program)
    if type(artifacts) is not dict or type(artifact_refs) is not dict:
        raise ValueError("hmmer_artifacts_must_be_objects")
    finite_json(artifacts); finite_json(artifact_refs); finite_json(engine_version)
    if engine_version is not None and not isinstance(engine_version, str):
        raise ValueError("hmmer_engine_version_must_be_string_or_null")
    if set(artifacts) - {"stdout", "tblout", "domtblout", "included_msa"}:
        raise ValueError("hmmer_unsupported_artifact_role")
    if any(not isinstance(t, str) for t in artifacts.values()): raise ValueError("hmmer_artifact_text_required")
    if not set(artifacts).issubset(artifact_refs): raise ValueError("hmmer_artifact_ref_missing")
    if not isinstance(checkpoints, (list, tuple)): raise ValueError("hmmer_checkpoints_must_be_array")
    finite_json(list(checkpoints))
    out = _empty(_operation(program, "hmmer3_protein_text", engine_version))
    out["artifacts"] = {r: {"artifact_ref": deepcopy(artifact_refs[r]), "text": t} for r, t in artifacts.items()}
    table_hits, table_domains, printed_hits, printed_domains = [], [], [], []
    for role, dest in (("tblout", table_hits), ("domtblout", table_domains)):
        if role not in artifacts: continue
        for event in iter_hmmer_table_rows(io.StringIO(artifacts[role]), program=program, role=role, artifact_ref=artifact_refs[role], engine_version=engine_version):
            kind, row = event["kind"], event["data"]
            if kind in {"hit", "domain"}: dest.append(row)
            else: out["issues" if kind == "issue" else "annotations"].append(row)
    if "stdout" in artifacts:
        for b in iter_hmmer_stdout_queries(io.StringIO(artifacts["stdout"]), program=program, artifact_ref=artifact_refs["stdout"], engine_version=engine_version):
            out["queries"].append(b["query"]); printed_hits.extend(b["hits"]); printed_domains.extend(b["domains"])
            for key in ("iterations", "statistics", "issues", "annotations"): out[key].extend(b[key])
        if not out["queries"]:
            out["issues"].append({"code": "hmmer_stdout_query_header_unavailable"})
    for role, text in artifacts.items():
        reported = re.search(r"^# (?:Program:\s*|(phmmer|hmmscan|hmmsearch|jackhmmer) ::)", text, re.M)
        if reported:
            actual = reported[1] or text[reported.end():].split()[0]
            if actual != program: out["issues"].append({"code": "hmmer_native_program_mismatch", "artifact_role": role, "reported": actual, "selected": program})
        version = re.search(r"^# (?:Version:\s*|HMMER\s+)(\S+)", text, re.M)
        if version and engine_version is not None and version[1] != engine_version.split()[0]:
            out["issues"].append({"code": "hmmer_native_version_mismatch", "artifact_role": role, "reported": version[1], "selected": engine_version})
    out["hits"] = _merge_tables(table_hits, printed_hits, domain=False, program=program, issues=out["issues"])
    out["domains"] = _merge_tables(table_domains, printed_domains, domain=True, program=program, issues=out["issues"])
    hit_keys = {a["record_key"]: h["record_key"] for h in out["hits"] for a in h.get("associations", [])}
    for d in out["domains"]:
        if d.get("hit_record_key") in hit_keys: d["hit_record_key"] = hit_keys[d["hit_record_key"]]
        if not d.get("hit_record_key"):
            candidates = [h for h in out["hits"] if all(h.get(k) == d.get(k) for k in ("query_name", "target_name", "query_occurrence", "iteration"))]
            if len(candidates) == 1: d["hit_record_key"] = candidates[0]["record_key"]
    if not out["queries"]:
        names = list(dict.fromkeys(r.get("query_name") for r in out["hits"] + out["domains"]))
        for name in names:
            q = _row(None, "table_query_identity", name, {"query_name": name})
            q.update(name=name, occurrence=None, length=None, kind="profile" if program == "hmmsearch" else "protein_sequence", complete=None)
            out["queries"].append(q)
    termination = {r: any(line.strip() in {"[ok]", "# [ok]"} for line in t.splitlines()) for r, t in artifacts.items() if r != "included_msa"}
    out["completion"] = {"native_termination": termination, "output_complete": all(termination.values()) if termination else None,
                         "hit_population_complete": None}
    if termination and not all(termination.values()): out["issues"].append({"code": "hmmer_native_termination_missing", "artifact_roles": [r for r, v in termination.items() if not v]})
    supplied_checkpoints = list(checkpoints)
    if "included_msa" in artifacts:
        supplied_checkpoints.append({"role": "included_msa", "text": artifacts["included_msa"], "artifact_ref": artifact_refs["included_msa"]})
    for i, cp in enumerate(supplied_checkpoints):
        if not isinstance(cp, dict):
            out["issues"].append({"code": "hmmer_checkpoint_not_object", "checkpoint_index": i}); continue
        try: out["checkpoints"].extend(_checkpoint_records(cp, i))
        except ValueError as e: out["issues"].append({"code": str(e), "checkpoint_index": i})
    return out


def _identity_match(meta, name, accession, occurrence):
    if not isinstance(meta, dict): return False
    present = False
    for field, actual in (("name", name), ("accession", accession)):
        if meta.get(field) is not None:
            present = True
            if actual is None or meta[field] != actual: return False
    if meta.get("occurrence") is not None and meta["occurrence"] != occurrence: return False
    return present


def _metadata(row, choices, *, name, accession, occurrence, role):
    candidates = [m for m in choices if _identity_match(m, name, accession, occurrence)]
    if len(candidates) > 1:
        row["issues"].append(_issue("hmmer_metadata_join_ambiguous", row, role=role)); return None
    if not candidates: return None
    meta = deepcopy(candidates[0])
    seq = meta.get("sequence"); length = meta.get("length")
    if length is not None and (type(length) is not int or length <= 0):
        row["issues"].append(_issue("hmmer_metadata_length_invalid", row, role=role)); return None
    if seq is not None and (not isinstance(seq, str) or length is not None and len(seq) != length):
        row["issues"].append(_issue("hmmer_metadata_sequence_length_mismatch", row, role=role)); return None
    if length is None and isinstance(seq, str): meta["length"] = len(seq)
    return meta


def _interval(row, name, left, right, length):
    a, b = row["native"].get(left), row["native"].get(right)
    if a is None or b is None: return None
    if not (type(a) is int and type(b) is int and 1 <= a <= b) or length is not None and b > length:
        row["issues"].append(_issue("hmmer_coordinate_invalid", row, axis=name, native_from=a, native_to=b, length=length)); return None
    return [a - 1, b]


def _alignment_quantities(row, program):
    ad = row.get("alignment")
    if not isinstance(ad, dict): return {"valid": False, "reason": "alignment_display_unavailable"}
    model, seq = ad.get("model"), ad.get("aseq")
    if ad.get("valid") is False or not isinstance(model, str) or not isinstance(seq, str) or len(model) != len(seq) or not model:
        row["issues"].append(_issue("hmmer_alignment_geometry_invalid", row)); return {"valid": False, "reason": "alignment_geometry_invalid"}
    sequence_role = "query" if program == "hmmscan" else "target"
    model_role = "target" if program == "hmmscan" else "query"
    expected_sequence = {row.get(sequence_role + "_name"), row.get(sequence_role + "_accession")}
    expected_model = {row.get(model_role + "_name"), row.get(model_role + "_accession")}
    model_is_learned = program == "jackhmmer" and row.get("iteration") != 1
    if (ad.get("sequence_name") is not None and ad["sequence_name"] not in expected_sequence or
            not model_is_learned and ad.get("model_name") is not None and ad["model_name"] not in expected_model):
        row["issues"].append(_issue("hmmer_alignment_operand_label_mismatch", row)); return {"valid": False, "reason": "alignment_operand_label_mismatch"}
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz." for c in model) or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz*-" for c in seq):
        row["issues"].append(_issue("hmmer_alignment_symbols_invalid", row)); return {"valid": False, "reason": "alignment_symbols_invalid"}
    paired = [i for i, (m, s) in enumerate(zip(model, seq)) if m != "." and s != "-"]
    inserts = [i for i, (m, s) in enumerate(zip(model, seq)) if m == "." and s != "-"]
    deletes = [i for i, (m, s) in enumerate(zip(model, seq)) if m != "." and s == "-"]
    if len(paired) + len(inserts) + len(deletes) != len(model):
        row["issues"].append(_issue("hmmer_alignment_double_gap", row)); return {"valid": False, "reason": "alignment_double_gap"}
    for axis, count in (("model", len(paired) + len(deletes)), ("sequence", len(paired) + len(inserts))):
        interval = row["intervals"].get(axis)
        if interval is not None and interval[1] - interval[0] != count:
            row["issues"].append(_issue("hmmer_alignment_endpoint_count_mismatch", row, axis=axis)); return {"valid": False, "reason": "alignment_endpoint_count_mismatch"}
    # Validate every wrapped stdout chunk's native endpoints, including gaps.
    consumed = {"model": 0, "sequence": 0}
    for chunk in ad.get("chunks", []):
        for axis, gap in (("model", "."), ("sequence", "-")):
            part = chunk.get(axis); interval = row["intervals"].get(axis)
            if not part or interval is None: continue
            count = sum(c != gap for c in part["aligned"])
            expected = (interval[0] + consumed[axis] + 1, interval[0] + consumed[axis] + count) if count else (None, None)
            if (part.get("from"), part.get("to")) != expected:
                row["issues"].append(_issue("hmmer_alignment_chunk_coordinates_invalid", row, axis=axis)); return {"valid": False, "reason": "alignment_chunk_coordinates_invalid"}
            consumed[axis] += count
    identities = sum(model[i].upper() == seq[i].upper() for i in paired)
    ml = ad.get("mline")
    api_matches = sum(c.isalpha() for c in ml) if isinstance(ml, str) and len(ml) == len(model) else None
    q = {"valid": True, "paired_positions": len(paired), "insert_positions": len(inserts), "delete_positions": len(deletes),
         "alignment_columns": len(model), "consensus_identical_positions": identities,
         "api_identity_numerator": api_matches, "api_identity_denominator": min(len(paired)+len(deletes), len(paired)+len(inserts)),
         "paired_column_indices": paired, "insert_column_indices": inserts, "delete_column_indices": deletes,
         "actual_sequence_correspondence": False}
    # Actual sequence identity requires both declared operands and exact interval
    # agreement. A learned/profile consensus remains a consensus even if equal.
    mmeta, smeta = row["joins"].get("model"), row["joins"].get("sequence")
    eligible = program == "phmmer" or program == "jackhmmer" and row.get("iteration") == 1
    if eligible and mmeta and smeta and mmeta.get("kind") == smeta.get("kind") == "protein_sequence":
        operands = []
        for axis, meta, aligned, gap in (("model", mmeta, model, "."), ("sequence", smeta, seq, "-")):
            interval = row["intervals"].get(axis); full = meta.get("sequence")
            if interval is None or not isinstance(full, str): operands.append(None); continue
            match = "".join(c for c in aligned if c != gap).upper() == full[interval[0]:interval[1]].upper()
            operands.append(match)
            if not match: row["issues"].append(_issue("hmmer_alignment_operand_sequence_mismatch", row, axis=axis))
        q["actual_sequence_correspondence"] = operands == [True, True]
    return q


def build_hmmer_search_sheet(native, *, inputs):
    """Join explicit operands and extract measurements; calculators remain separate."""
    if type(native) is not dict or native.get("schema") != "hmmer_search_native_v1":
        raise ValueError("hmmer_invalid_native_schema")
    if type(inputs) is not dict: raise ValueError("hmmer_inputs_must_be_object")
    finite_json(native); finite_json(inputs)
    out = deepcopy(native); out["schema"] = "hmmer_search_sheet_v1"; out["inputs"] = deepcopy(inputs)
    program = out["operation"]["program"]; _program(program)
    out.setdefault("issues", [])
    for collection in ("queries", "hits", "domains", "iterations"):
        rows = out.setdefault(collection, [])
        if not isinstance(rows, list): raise ValueError("hmmer_native_rows_must_be_arrays:" + collection)
        valid = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("record_key"), str) or not isinstance(row.get("locator"), dict):
                out["issues"].append({"code": "hmmer_native_row_identity_invalid", "collection": collection, "index": index, "supplied": deepcopy(row)})
                continue
            row.setdefault("issues", [])
            if not isinstance(row.get("native", {}), dict):
                row["issues"].append(_issue("hmmer_native_numeric_components_not_object", row)); row["native"] = {}
            row.setdefault("native", {})
            for field, value in list(row["native"].items()):
                if value is not None and (type(value) not in (int, float)):
                    row["issues"].append(_issue("hmmer_invalid_native_numeric_component", row, field=field, supplied=deepcopy(value)))
                    row["native"][field] = None
            valid.append(row)
        out[collection] = valid
    query_metas = [inputs["query"]] if isinstance(inputs.get("query"), dict) else []
    targets = inputs.get("targets", [])
    if not isinstance(targets, list): raise ValueError("hmmer_targets_must_be_array")
    for i, meta in enumerate(targets):
        if not isinstance(meta, dict): out["issues"].append({"code": "hmmer_target_metadata_not_object", "target_index": i})
    query_index = {q["record_key"]: q for q in out["queries"]}
    for q in out["queries"]:
        q["metadata"] = _metadata(q, query_metas, name=q.get("name"), accession=q.get("accession"), occurrence=q.get("occurrence"), role="query")
        # A zero-hit API payload can legitimately lack a query label. Keep the
        # supplied operand distinct instead of inventing a native identity.
        if q.get("name") is None and len(query_metas) == 1: q["supplied_query"] = deepcopy(query_metas[0])
    for row in out["hits"] + out["domains"]:
        q = query_index.get(row.get("query_record_key"), {})
        row["joins"] = {
            "query": _metadata(row, query_metas, name=row.get("query_name", q.get("name")), accession=row.get("query_accession", q.get("accession")), occurrence=row.get("query_occurrence"), role="query"),
            "target": _metadata(row, targets, name=row.get("target_name"), accession=row.get("target_accession"), occurrence=row.get("target_occurrence"), role="target")}
        row["joins"]["model"] = row["joins"]["target" if program == "hmmscan" else "query"]
        row["joins"]["sequence"] = row["joins"]["query" if program == "hmmscan" else "target"]
        if program == "jackhmmer" and row.get("iteration") != 1:
            # Later models are learned from the previous included alignment;
            # the original sequence metadata do not supply their coordinates.
            row["joins"]["model"] = None
    for row in out["domains"]:
        n = row["native"]
        for axis, native_key in (("model", "target_length" if program == "hmmscan" else "query_length"), ("sequence", "query_length" if program == "hmmscan" else "target_length")):
            direct = n.get(axis + "_length")
            table = n.get(native_key)
            meta = row["joins"].get(axis)
            supplied = meta.get("length") if meta else None
            values = [x for x in (direct, table, supplied) if x is not None]
            if len(set(values)) > 1:
                row["issues"].append(_issue("hmmer_operand_length_conflict", row, axis=axis, lengths=values))
                row["joins"][axis] = None
            length = direct if direct is not None else table if table is not None else supplied
            n[axis + "_length"] = length if type(length) is int and length > 0 else None
        row["intervals"] = {"model": _interval(row, "model", "hmm_from", "hmm_to", n["model_length"]),
                            "sequence": _interval(row, "sequence", "ali_from", "ali_to", n["sequence_length"]),
                            "envelope": _interval(row, "envelope", "env_from", "env_to", n["sequence_length"])}
        ali, env = row["intervals"]["sequence"], row["intervals"]["envelope"]
        if ali and env and not (env[0] <= ali[0] <= ali[1] <= env[1]):
            row["issues"].append(_issue("hmmer_envelope_does_not_contain_alignment", row))
            row["intervals"]["envelope"] = None
        row["quantities"] = _alignment_quantities(row, program)
        row["coordinate_convention"] = {"native": "one_based_inclusive", "intervals": "zero_based_half_open", "model_axis": "target" if program == "hmmscan" else "query", "sequence_axis": "query" if program == "hmmscan" else "target"}
    acquisition = inputs.get("acquisition", {})
    if acquisition is not None and not isinstance(acquisition, dict): raise ValueError("hmmer_acquisition_must_be_object")
    acquisition = acquisition or {}
    completion = out.get("completion", {})
    if acquisition.get("output_complete") is True and completion.get("output_complete") is False:
        out["issues"].append({"code": "hmmer_completion_metadata_contradiction"})
    if acquisition.get("hit_population_complete") is True:
        stats = out.get("statistics", {})
        total = stats.get("nreported") if isinstance(stats, dict) else None
        if type(total) is int and sum(h.get("is_reported") is True for h in out["hits"]) != total:
            out["issues"].append({"code": "hmmer_hit_population_incomplete", "native_reported_population": total, "returned_hit_rows": len(out["hits"])})
    return out
