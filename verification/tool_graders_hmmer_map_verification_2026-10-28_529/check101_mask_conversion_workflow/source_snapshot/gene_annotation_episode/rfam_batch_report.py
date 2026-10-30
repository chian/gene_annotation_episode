"""Parse supplied Rfam cmscan 1.1.5 report bytes without acquiring any data.

Summary rows and displays are joined within a native query block using unique
rank and model identity, then cross-checked cell by cell including coordinates.
Repeated ranks are never resolved by position or by picking the first record.
The complete source lines remain available even for malformed native cells.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from decimal import Decimal
import math
import re

from .rfam_batch_alignment import _Axis, _DisplayError, _alignment_geometry, _rna, _RNA
from .rfam_batch_table import (
    _capture, parse_rfam_report_membership, validate_rfam_batch_file_input,
)
from .rfam_batch_report_contracts import (
    REPORT_FORMAT, REPORT_PARSE_VERSION, REPORT_SHEET_VERSION, REPORT_CORRESPONDENCE_VERSION,
    RFAM_ALIGNMENT_COUNT_FIELDS, RfamReportNativeCells, report_issue,
)

_SCORE_FIELDS = ("rank", "inclusion", "evalue", "score", "bias", "model_name",
                 "query_from", "query_to", "strand", "model_type", "truncation", "gc")
_ALIGN_FIELDS = ("rank", "inclusion", "evalue", "score", "bias", "model_type",
                 "model_from", "model_to", "model_boundary", "query_from", "query_to",
                 "strand", "query_boundary", "accuracy", "truncation", "gc")
_SCORE_HEADER = "rank E-value score bias modelname start end mdl trunc gc description"
_ALIGN_HEADER = "rank E-value score bias mdl mdl from mdl to seq from seq to acc trunc gc"
_AXIS = re.compile(r" *([^\s]+) +([0-9]+|-) +(.+?) +([0-9]+|-) *")


def _source(lines, numbers):
    return [{"line": n, "text": lines[n - 1]} for n in sorted(set(numbers))]


def _cell(token, field):
    if field in {"rank", "model_from", "model_to", "query_from", "query_to"}:
        if field == "rank":
            if not re.fullmatch(r"\([0-9]+\)", token):
                raise ValueError
            token = token[1:-1]
        if not token.isascii() or not token.isdecimal():
            raise ValueError
        value = int(token)
        if value < 1:
            raise ValueError
        return value
    if field in {"evalue", "score", "bias", "accuracy", "gc"}:
        value = float(token)
        if (not math.isfinite(value) or value == 0 and Decimal(token) != 0
                or field == "evalue" and value < 0):
            raise ValueError
        if field in {"accuracy", "gc"} and not 0 <= value <= 1:
            raise ValueError
        return value
    allowed = {"inclusion": {"!", "?"}, "strand": {"+", "-"},
               "model_type": {"cm", "hmm"}, "truncation": {"no", "5'", "3'", "5'&3'"}}
    if field in allowed and token not in allowed[field]:
        raise ValueError
    if field in {"model_boundary", "query_boundary"} and not re.fullmatch(r"[\[.~][\].~]", token):
        raise ValueError
    return token


def _row(line, number, fields, query, issues):
    tokens = line.split(maxsplit=len(fields))
    raw, values = {}, {}
    if len(tokens) < len(fields):
        issues.append(report_issue("rfam_report_row_invalid", native_query_name=query, source_line=number))
        return raw, values
    for field, token in zip(fields, tokens):
        raw[field] = token
        try:
            values[field] = _cell(token, field)
        except (ValueError, OverflowError):
            values[field] = None
            issues.append(report_issue("rfam_report_cell_invalid", field=field,
                                       native_query_name=query, source_line=number))
    # Score descriptions are arbitrary native text; alignment summaries have
    # exactly the declared columns. Unsupported verbose fields stay explicit.
    if fields == _ALIGN_FIELDS and len(tokens) != len(fields):
        issues.append(report_issue("rfam_report_native_header_unsupported", source_line=number,
                                   native_query_name=query, field="alignment_summary"))
    return raw, values


def _empty_correspondence():
    return dict(version=REPORT_CORRESPONDENCE_VERSION, status="invalid",
        display_model_from=None, display_model_to=None, display_query_from=None, display_query_to=None,
        segments=[], paired_positions=[], aligned_model_intervals=[], aligned_query_intervals=[],
        posterior_segments=[], blocks=[], issues=[], **{k: None for k in RFAM_ALIGNMENT_COUNT_FIELDS})


def _display(lines, start, end, hit, query):
    result = _empty_correspondence()
    name, model_name = hit["native_query_name"], hit["model_name"]

    def issue(code, field, line=None):
        item = report_issue(code, field=field, native_query_name=name,
                            source_line=start if line is None else line,
                            severity="warning" if code == "rfam_alignment_correspondence_unrepresented" else "error")
        if item not in result["issues"]:
            result["issues"].append(item)

    axes = [(n, match) for n in range(start, end) if (match := _AXIS.fullmatch(lines[n - 1]))]
    try:
        if not axes:
            raise _DisplayError("rfam_alignment_missing", "display")
        if len(axes) % 2:
            raise _DisplayError("rfam_alignment_invalid", "display")
        models, queries, posteriors = [], [], []
        for index in range(0, len(axes), 2):
            (mn, m), (qn, q) = axes[index:index + 2]
            if m[1] != model_name:
                raise _DisplayError("rfam_report_display_model_conflict", "model_name")
            if q[1] != name:
                raise _DisplayError("rfam_report_display_query_conflict", "native_query_name")
            try:
                model = _Axis(int(m[2]), m[3], int(m[4]))
                query_axis = _Axis(None if q[2] == "-" else int(q[2]), q[3],
                                   None if q[4] == "-" else int(q[4]))
            except ValueError as error:
                raise _DisplayError("rfam_alignment_invalid", "display") from error
            width, indent = len(model.text), m.start(3)
            if (len(query_axis.text) != width or q.start(3) != indent
                    or (query_axis.start is None) != (query_axis.end is None)):
                raise _DisplayError("rfam_alignment_coordinate_conflict", "display")
            before = start if index == 0 else axes[index - 1][0] + 1
            after = end if index + 2 == len(axes) else axes[index + 2][0]
            used = [mn, qn]

            def track(label, left, right):
                located = [n for n in range(left, right) if re.search(r"\s" + label + r"\s*$", lines[n - 1])]
                used.extend(located)
                if not located:
                    if label != "RF":
                        issue("rfam_alignment_missing", label.lower(), mn)
                    return None
                if len(located) != 1:
                    issue("rfam_alignment_invalid", label.lower(), located[0])
                    return None
                n, text = located[0], lines[located[0] - 1]
                suffix = text[indent + width:]
                if (len(text) < indent + width + len(label) + 1 or text[:indent].strip()
                        or suffix.strip() != label):
                    issue("rfam_alignment_invalid", label.lower(), n)
                    return None
                return text[indent:indent + width]

            nc, cs = track("NC", before, mn), track("CS", before, mn)
            pp, rf = track("PP", qn + 1, after), track("RF", qn + 1, after)
            match = None
            if qn == mn + 2:
                used.append(mn + 1)
                text = lines[mn]
                if len(text) >= indent + width and not text[:indent].strip() and not text[indent + width:].strip():
                    match = text[indent:indent + width]
            if match is None:
                issue("rfam_alignment_missing", "match", mn + 1)
            elif any(c not in " :+" and _rna(c) not in _RNA for c in match):
                issue("rfam_alignment_unsupported", "match", mn + 1)
            if nc is not None and any(c not in " v?" for c in nc):
                issue("rfam_alignment_unsupported", "nc", mn)
            if cs is not None and any(c not in "<>()[]{}:,_-.~" and not c.isalpha() for c in cs):
                issue("rfam_alignment_unsupported", "cs", mn)
            result["blocks"].append(dict(source_lines=_source(lines, used), model_line=mn, query_line=qn,
                model_from=model.start, model_to=model.end, query_from=query_axis.start, query_to=query_axis.end,
                model_text=model.text, query_text=query_axis.text, nc=nc, cs=cs, match=match, pp=pp, rf=rf))
            models.append(model)
            queries.append(query_axis)
            posteriors.append(pp)
        if models[0].start < 1 or models[-1].end < 1:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "model")
        native = hit["native"]
        if query is None or hit["strand"] is None or native["query_from"] is None or native["query_to"] is None:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "query")
        geometry = _alignment_geometry(models, queries, posteriors,
            query_sequence=query["submitted_sequence"], native_start=native["query_from"],
            native_end=native["query_to"], native_strand=hit["strand"], issue=issue)
        # Summary coordinates are emitted endpoints; truncation shorthand is
        # displayed outside them. Local-end shorthand remains inside the span.
        if (native["model_from"] != geometry["display_model_from"] + geometry["truncated_model_count_5p"]
                or native["model_to"] != geometry["display_model_to"] - geometry["truncated_model_count_3p"]):
            raise _DisplayError("rfam_alignment_coordinate_conflict", "model")
        expected_trunc = ("5'&3'" if geometry["truncated_model_count_5p"] and geometry["truncated_model_count_3p"]
            else "5'" if geometry["truncated_model_count_5p"] else "3'" if geometry["truncated_model_count_3p"] else "no")
        if native["truncation"] != expected_trunc:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "truncation")
        result.update(geometry)
        result["status"] = "partial" if result["issues"] else "complete"
    except _DisplayError as error:
        issue(error.code, error.field)
        result["status"] = "unsupported" if error.unsupported else "invalid"
    return result


def _coordinates(hit, query):
    native = hit["native"]
    start, end, strand = native["query_from"], native["query_to"], hit["strand"]
    valid = (query is not None and start is not None and end is not None and strand in {"+", "-"}
        and 1 <= start <= query["submitted_length_nt"] and 1 <= end <= query["submitted_length_nt"]
        and (start <= end if strand == "+" else start >= end))
    boundary, truncation = native["query_boundary"], native["truncation"]
    if valid and boundary is not None and truncation is not None:
        first, last = (1, query["submitted_length_nt"]) if strand == "+" else (query["submitted_length_nt"], 1)
        expected = ("~" if truncation in {"5'", "5'&3'"} else "[" if start == first else ".")
        expected += ("~" if truncation in {"3'", "5'&3'"} else "]" if end == last else ".")
        valid = boundary == expected
    mstart, mend, mbound = native["model_from"], native["model_to"], native["model_boundary"]
    model_valid = mstart is None or mend is None or mstart <= mend
    if mstart is not None and mbound is not None and truncation is not None:
        model_valid = model_valid and mbound[0] == ("~" if truncation in {"5'", "5'&3'"} else "[" if mstart == 1 else ".")
        model_valid = model_valid and (mbound[1] == "~") == (truncation in {"3'", "5'&3'"})
    if not model_valid:
        hit["missing"].update(model_from="coordinates_invalid", model_to="coordinates_invalid")
        hit["issues"].append(report_issue("rfam_report_coordinates_invalid", field="model_coordinates",
            native_query_name=hit["native_query_name"], source_line=hit["alignment_summary_line"]))
    if not valid:
        hit["missing"].update(query_from="coordinates_invalid", query_to="coordinates_invalid")
        hit["issues"].append(report_issue("rfam_report_coordinates_invalid", field="query_coordinates",
            native_query_name=hit["native_query_name"], source_line=hit["score_line"] or hit["alignment_summary_line"]))
    return valid


def _query_hits(lines, membership, end, query, artifact_ref):
    name, start = membership["native_query_name"], membership["query_header_line"]
    scores, summaries, issues = [], [], []
    mode = None
    model_name = header_line = None
    alignment_header_valid = False
    for n in range(start + 1, end):
        line = lines[n - 1]
        if line == "Hit scores:":
            mode = "scores"
        elif line == "Hit alignments:":
            mode = "alignments"
        elif line.startswith("Internal CM pipeline"):
            mode = None
        elif line.startswith(">>") and mode == "alignments":
            if summaries:
                summaries[-1]["end"] = n
            parts = line[2:].split()
            model_name, header_line = (parts[0] if parts else None), n
            alignment_header_valid = False
        elif line.lstrip().startswith("rank "):
            normalized = " ".join(line.split())
            expected = _SCORE_HEADER if mode == "scores" else _ALIGN_HEADER
            if normalized != expected:
                issues.append(report_issue("rfam_report_native_header_unsupported", source_line=n, native_query_name=name))
            if mode == "alignments":
                alignment_header_valid = normalized == _ALIGN_HEADER
        elif re.match(r"^\s*\([^()\s]*\)\s", line) and mode in {"scores", "alignments"}:
            local = []
            raw, values = _row(line, n, _SCORE_FIELDS if mode == "scores" else _ALIGN_FIELDS, name, local)
            row = dict(line=n, raw=raw, values=values, issues=local)
            if mode == "scores":
                scores.append(row)
            else:
                if summaries and summaries[-1]["header"] == header_line:
                    summaries[-1]["end"] = n
                row.update(model=model_name, header=header_line, end=end, header_valid=alignment_header_valid)
                if not alignment_header_valid:
                    row["values"]["accuracy"] = None
                    local.append(report_issue("rfam_report_native_header_unsupported", field="accuracy", native_query_name=name, source_line=n))
                summaries.append(row)
    stats = [n for n in range(start + 1, end) if lines[n - 1].startswith("Internal CM pipeline")]
    if summaries and stats:
        summaries[-1]["end"] = min(summaries[-1]["end"], stats[0])
    rank_counts = Counter(row["values"].get("rank") for row in scores)
    summary_counts = Counter(row["values"].get("rank") for row in summaries)
    consumed, hits = set(), []

    def build(score, summary, *, ambiguous=False):
        values = {} if score is None else dict(score["values"])
        native = {key: values.get(key) for key in RfamReportNativeCells.__annotations__}
        hit = dict(hit_key=artifact_ref + "/lines/" + str((score or summary)["line"]),
            query_occurrence_key=None if query is None else query["query_occurrence_key"],
            native_query_name=name, model_name=values.get("model_name") if score else summary["model"],
            family_accession=None, strand=values.get("strand"), query_header_line=start,
            score_line=None if score is None else score["line"],
            alignment_header_line=None if summary is None else summary["header"],
            alignment_summary_line=None if summary is None else summary["line"], native=native,
            raw_cells={"score": {} if score is None else score["raw"], "alignment": {} if summary is None else summary["raw"]},
            source_lines=[], correspondence=None, missing={}, issues=[])
        numbers = [] if score is None else [score["line"]]
        if score:
            hit["issues"].extend(score["issues"])
        if summary:
            hit["issues"].extend(summary["issues"])
            numbers.extend(range(summary["header"] or summary["line"], summary["end"]))
            for key in (*native, "strand"):
                if key not in summary["values"]:
                    continue
                value = summary["values"][key]
                if score is not None and key in values and values[key] != value:
                    value = None
                    hit["issues"].append(report_issue("rfam_report_cell_conflict", field=key,
                        native_query_name=name, source_line=summary["line"]))
                    hit["missing"][key] = "native_cell_conflict"
                if key == "strand":
                    hit[key] = value
                else:
                    native[key] = value
        if score is None:
            hit["issues"].append(report_issue("rfam_report_summary_unmatched", native_query_name=name,
                source_line=summary["line"]))
        if ambiguous:
            hit["issues"].append(report_issue("rfam_report_rank_ambiguous", field="rank",
                native_query_name=name, source_line=(score or summary)["line"]))
            hit["missing"]["correspondence"] = "ambiguous_rank"
        if query is None:
            hit["missing"]["query_occurrence_key"] = "identity_rejected"
        valid = _coordinates(hit, query)
        for key, value in native.items():
            if value is None:
                hit["missing"].setdefault(key, "invalid_native_value" if key in hit["raw_cells"]["score"] or key in hit["raw_cells"]["alignment"] else "not_reported")
        if summary and not ambiguous and valid and "model_from" not in hit["missing"] and "model_to" not in hit["missing"]:
            hit["correspondence"] = _display(lines, summary["line"] + 1, summary["end"], hit, query)
            hit["issues"].extend(hit["correspondence"]["issues"])
            if any(i["code"] in {"rfam_alignment_query_conflict", "rfam_report_display_query_conflict"}
                   for i in hit["correspondence"]["issues"]):
                hit["query_occurrence_key"] = None
                hit["missing"]["query_occurrence_key"] = "identity_rejected"
        elif summary is None:
            hit["issues"].append(report_issue("rfam_report_alignment_missing", native_query_name=name,
                source_line=hit["score_line"]))
            hit["missing"].setdefault("correspondence", "alignment_missing")
        else:
            hit["missing"].setdefault("correspondence", "identity_rejected" if query is None else "coordinates_invalid")
        hit["source_lines"] = _source(lines, numbers)
        return hit

    for score in scores:
        rank = score["values"].get("rank")
        matches = [i for i, row in enumerate(summaries) if rank is not None
                   and row["values"].get("rank") == rank and row["model"] == score["values"].get("model_name")]
        ambiguous = rank is not None and (rank_counts[rank] > 1 or summary_counts[rank] > 1)
        if len(matches) == 1 and not ambiguous:
            consumed.add(matches[0])
            hits.append(build(score, summaries[matches[0]]))
        else:
            hit = build(score, None, ambiguous=ambiguous)
            if ambiguous:
                # All candidate source descriptions survive, but none is
                # arbitrarily selected as this row's correspondence. They do
                # not become an extra duplicate copy of the scored hit list.
                consumed.update(matches)
                numbers = [row["line"] for row in hit["source_lines"]]
                for index in matches:
                    summary = summaries[index]
                    numbers.extend(range(summary["header"] or summary["line"], summary["end"]))
                hit["source_lines"] = _source(lines, numbers)
            hits.append(hit)
    for index, summary in enumerate(summaries):
        if index not in consumed:
            rank = summary["values"].get("rank")
            hits.append(build(None, summary, ambiguous=rank is not None and (rank_counts[rank] > 1 or summary_counts[rank] > 1)))
    hits.sort(key=lambda h: h["score_line"] or h["alignment_summary_line"])
    if membership["reported_hit_count"] is not None and membership["reported_hit_count"] != len(scores):
        issues.append(report_issue("rfam_batch_report_count_conflict", native_query_name=name,
            source_line=membership["reported_hit_count_line"]))
    if not scores and membership["reported_hit_count"] == 0:
        # A count alone cannot conceal malformed nonempty score content.
        nohit = any("[No hits detected that satisfy reporting thresholds]" in lines[n - 1] for n in range(start + 1, end))
        if not nohit:
            issues.append(report_issue("rfam_report_summary_missing", native_query_name=name, source_line=start))
    return hits, issues


def populate_rfam_batch_report_sheet(content: bytes, *, input_identity, capture, submitted_content: bytes) -> dict:
    """Validate custody and original membership, then retain native report cells."""
    def result(status, issues, sheet=None):
        from .rfam_batch_infernal import rfam_parse_envelope
        return rfam_parse_envelope(representation="out", status=status,
            format=REPORT_FORMAT if sheet is not None else "unrecognized", sheet=sheet, issues=issues)

    try:
        validate_rfam_batch_file_input(input_identity, submitted_content=submitted_content)
        capture = _capture(capture, content)
        for field, expected, code in (
            ("request_job_id", input_identity["expected_job_id"], "rfam_batch_result_job_conflict"),
            ("request_file_sha256", input_identity["submitted_file_sha256"], "rfam_batch_result_file_conflict"),
            ("submission_source_ref", input_identity["submission_source_ref"], "rfam_batch_submission_source_conflict")):
            if capture[field] != expected:
                raise ValueError(code)
    except ValueError as error:
        return result("rejected", [report_issue(str(error))])
    membership = parse_rfam_report_membership(content, capture=capture)
    issues = deepcopy(membership["issues"])
    fatal = {item["code"] for item in issues}
    if fatal & {"rfam_batch_report_query_file_conflict"}:
        return result("rejected", issues)
    if fatal & {"rfam_batch_report_profile_unsupported", "rfam_batch_representation_unsupported", "rfam_batch_native_text_unsupported"}:
        return result("unsupported", issues)
    lines = content.decode("ascii").splitlines()
    queries = {q["native_query_name"]: q for q in input_identity["queries"]}
    counts = Counter(q["native_query_name"] for q in membership["queries"])
    for name in queries.keys() - counts.keys():
        issues.append(report_issue("rfam_batch_report_query_missing", native_query_name=name))
    headers = [n for n, line in enumerate(lines, 1) if line.startswith("Query:")]
    hits = []
    for row in membership["queries"]:
        name = row["native_query_name"]
        query = queries.get(name)
        if query is None:
            issues.append(report_issue("rfam_batch_report_foreign_query", native_query_name=name, source_line=row["query_header_line"]))
        elif query["submitted_length_nt"] != row["length_nt"]:
            issues.append(report_issue("rfam_batch_report_length_conflict", native_query_name=name, source_line=row["query_header_line"]))
            query = None
        if counts[name] != 1:
            query = None
        end = next((n for n in headers if n > row["query_header_line"]), len(lines) + 1)
        local_hits, local_issues = _query_hits(lines, row, end, query, capture["artifact_ref"])
        hits.extend(local_hits)
        issues.extend(local_issues)
    # A complete population is distinct from complete residue correspondence.
    # Native truncation shorthand and bad optional tracks do not invent or lose
    # hit rows. Missing/conflicting summary rows do qualify the population.
    population_codes = {"rfam_report_row_invalid", "rfam_report_rank_ambiguous", "rfam_report_summary_unmatched",
                        "rfam_report_alignment_missing", "rfam_report_cell_conflict",
                        "rfam_alignment_query_conflict", "rfam_report_display_query_conflict"}
    population_complete = membership["complete"] and not issues and not any(
        issue["code"] in population_codes for hit in hits for issue in hit["issues"])
    all_issues = [*issues, *(i for h in hits for i in h["issues"])]
    from .rfam_batch_infernal import populate_rfam_report_cells
    sheet = populate_rfam_report_cells(capture=capture, input_identity=input_identity,
        membership=membership, hits=hits, population_complete=population_complete,
        issues=all_issues, content=content)
    return result("partial" if all_issues else "complete", all_issues, sheet)


__all__ = ["populate_rfam_batch_report_sheet"]
