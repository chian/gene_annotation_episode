"""Pure correspondence reader for Rfam's labelled Infernal alignment display.

The supplied artifact owns the original strings. This reader neither acquires
them nor authenticates artifact custody. Its result binds to one original JSON
row; the bundle consumer additionally checks the source digest and row contents.

Coordinates are zero-based physical query/model positions, with half-open
intervals. Query traversal follows the separately retained strand. RNA display
comparison is case-insensitive and maps T to U; the explicit IUPAC complement
is A:U, C:G, G:C, U:A, R:Y, S:S, W:W, K:M, B:V, D:H, N:N. Ambiguity symbols
must agree exactly with the supplied sequence (after that transformation), but
only A/C/G/U pairs enter consensus equality counts. Consensus is not a physical
reference sequence, and lowercase consensus does not quantify confidence.

An explicit model column, including a deletion, contributes to represented
model intervals; an explicit query residue, including an insertion, contributes
to represented query intervals. Truncation/local-end shorthand contributes its
native counts and physical span, but not invented symbols, pairs or represented
intervals. Such a fully understood abbreviated display is partial with an
``rfam_alignment_correspondence_unrepresented`` issue, distinct from unsupported
grammar. Model length cannot be obtained from display endpoints.

PP bounds are placement bins: 0=[0,.05), digits 1..9=[(d-.5)/10,(d+.5)/10),
*=[.95,1]. Upper bounds are exclusive except for *. A local-end code describes
the native span mean, not every omitted residue. No bin is a point estimate or
an annotation probability. Missing/invalid PP does not discard valid geometry.

Native grammar source: Infernal 1.1.5 cm_alidisplay_Create/Print and its guide.
Current captured Rfam JSON is one unwrapped block. Repeated labelled blocks are
also read with per-block coordinate checks; their remote serialization remains
unobserved. Parsing a mechanically extracted report fixture is not a production
report-to-JSON or cross-artifact correlation operation.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from .domain import ContractError
from .rfam_batch_contracts import (
    RFAM_ALIGNMENT_COUNT_FIELDS,
    RfamAlignmentResult,
    RfamHitIdentity,
    make_issue,
    validate_rfam_alignment_result,
    validate_rfam_hit_identity,
)


_RNA = frozenset("ACGURYSWKMBDHVN")
_COMPLEMENT = str.maketrans("ACGURYSWKMBDHVN", "UGCAYRSWMKVHDBN")
_SHORTHAND = re.compile(r"([<*])\[ *([0-9]+)\]([*>])")
_LABELS = {"nc": "#NC", "ss": "#SS", "match": "#MATCH", "pp": "#PP"}


class _DisplayError(Exception):
    def __init__(self, code, field, *, unsupported=False):
        self.code, self.field, self.unsupported = code, field, unsupported


@dataclass(frozen=True)
class _Axis:
    start: int | None
    text: str
    end: int | None


def _rna(symbol):
    return symbol.upper().replace("T", "U")


def _integer(token, field):
    try:
        return int(token)
    except ValueError as error:
        # Python may reject an excessively long decimal token. That malformed
        # native cell must still return a structured display failure.
        raise _DisplayError("rfam_alignment_invalid", field) from error


def _axis_lines(value, label, field, *, gaps=False):
    if type(value) is not str or not value.strip():
        raise _DisplayError("rfam_alignment_missing", field)
    if not value.isascii() or any(c in value for c in "\x00\t\r"):
        raise _DisplayError("rfam_alignment_invalid", field)
    lines = [line for line in value.split("\n") if line.strip()]
    records = []
    endpoint = r"(?:[0-9]+|-)" if gaps else r"[0-9]+"
    pattern = re.compile(r" *" + re.escape(label) + r" +(" + endpoint + r") +(.+?) +(" + endpoint + r") *")
    for line in lines:
        found = pattern.fullmatch(line)
        if found is None:
            code = "rfam_alignment_invalid" if line.lstrip().startswith(label + " ") else "rfam_alignment_unsupported"
            raise _DisplayError(code, field, unsupported=code.endswith("unsupported"))
        start, body, end = found.groups()
        if (start == "-") != (end == "-"):
            raise _DisplayError("rfam_alignment_coordinate_conflict", field)
        records.append(_Axis(None if start == "-" else _integer(start, field), body,
                             None if end == "-" else _integer(end, field)))
    return records


def _union(intervals):
    result = []
    for left, right in sorted(intervals):
        if result and left <= result[-1][1]:
            result[-1][1] = max(result[-1][1], right)
        else:
            result.append([left, right])
    return result


def _span(start, count, direction=1):
    if not count:
        return None
    final = start + direction * (count - 1)
    return [min(start, final), max(start, final) + 1]


def _posterior(interval, code, *, mean=False):
    if code == "*":
        lower, upper = .95, 1.0
    elif code == "0":
        lower, upper = 0.0, .05
    else:
        number = int(code)
        lower, upper = (2 * number - 1) / 20, (2 * number + 1) / 20
    return dict(query_interval=interval, code=code, lower_bound=lower, upper_bound=upper,
                meaning="span_mean_placement_bin" if mean else "residue_placement_bin")


def _append_segment(segments, segment):
    # Explicit columns can be compacted without changing coordinate direction
    # or text. Shorthand is kept as a separate native segment.
    if (segments and segment["kind"] in ("match", "query_insertion", "model_deletion")
            and segments[-1]["kind"] == segment["kind"]):
        prior = segments[-1]
        for field in ("model_interval", "query_interval"):
            a, b = prior[field], segment[field]
            if (a is None) != (b is None) or (a is not None and a[1] != b[0] and b[1] != a[0]):
                break
        else:
            for field in ("model_interval", "query_interval"):
                if prior[field] is not None:
                    prior[field] = [min(prior[field][0], segment[field][0]), max(prior[field][1], segment[field][1])]
            for field in ("model_text", "query_text"):
                prior[field] += segment[field]
            for field in ("model_count", "query_count"):
                prior[field] += segment[field]
            return
    segments.append(segment)


def _annotations(alignment, widths, issue):
    """Return PP blocks. Other tracks are checked, never used as identities."""
    tracks = {}
    for field, label in _LABELS.items():
        value = alignment.get(field)
        if type(value) is not str or not value.strip():
            issue("rfam_alignment_missing" if value is None or value == "" else "rfam_alignment_invalid", field)
            tracks[field] = None
            continue
        if not value.isascii() or any(c in value for c in "\x00\t\r"):
            issue("rfam_alignment_invalid", field)
            tracks[field] = None
            continue
        lines = [line for line in value.split("\n") if line.strip()]
        if len(lines) != len(widths):
            issue("rfam_alignment_invalid", field)
            tracks[field] = None
            continue
        payloads = []
        for line in lines:
            if not line.startswith(label) or (len(line) > len(label) and line[len(label)] != " "):
                issue("rfam_alignment_unsupported", field)
                payloads = None
                break
            payloads.append(line[len(label):])
        tracks[field] = payloads

    posteriors = []
    for index, width in enumerate(widths):
        # SS/PP contain no leading internal spaces. Their actual source padding
        # anchors NC and MATCH; do not right-align those lossy prose-like tracks.
        indent = None
        for field in ("ss", "pp"):
            if tracks[field] is not None:
                payload = tracks[field][index]
                if payload.strip() and len(payload.strip(" ")) == width:
                    indent = len(payload) - len(payload.lstrip(" "))
                    break
        pp = None
        for field in ("nc", "ss", "match", "pp"):
            if tracks[field] is None:
                continue
            payload = tracks[field][index]
            if field in ("ss", "pp"):
                body = payload.strip(" ")
                if len(body) != width:
                    issue("rfam_alignment_invalid", field)
                    continue
            elif indent is not None:
                if (payload[:indent] != " " * indent or len(payload) < indent + width
                        or payload[indent + width:].strip(" ")):
                    issue("rfam_alignment_invalid", field)
                    continue
                body = payload[indent:indent + width]
            else:
                # With both anchors unavailable, no position-based NC/MATCH
                # interpretation is made. Their original strings are retained.
                continue
            if field == "nc" and any(c not in " v?" for c in body):
                issue("rfam_alignment_unsupported", field)
            elif field == "match" and any(c not in " :+" and _rna(c) not in _RNA for c in body):
                issue("rfam_alignment_unsupported", field)
            elif field == "pp":
                pp = body
        posteriors.append(pp)
    return posteriors


def _alignment_geometry(models, queries, pp_blocks, *, query_sequence,
                        native_start, native_end, native_strand, issue):
    """Shared native-display geometry, independent of JSON/report identities.

    Axes and optional posterior tracks have already been read and checked by
    their native-format reader. This routine interprets identical Infernal
    columns and shorthand without adding acquisition or invented identities.
    """
    direction = 1 if native_strand == "+" else -1
    mpos, qpos = models[0].start - 1, native_start - 1
    counts = {name: 0 for name in RFAM_ALIGNMENT_COUNT_FIELDS}
    segments, pairs, model_intervals, query_intervals, posterior = [], [], [], [], []
    query_first = query_last = None
    for block, (model, query, pp) in enumerate(zip(models, queries, pp_blocks)):
        if model.start != mpos + 1:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "hit_seq")
        block_query_start, block_query_count = qpos, 0
        if query.start is not None and query.start != qpos + 1:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
        column = 0
        while column < len(model.text):
            ms, qs = model.text[column], query.text[column]
            if ms in "*<" or qs in "*<":
                mt, qt = _SHORTHAND.match(model.text, column), _SHORTHAND.match(query.text, column)
                if (mt is None or qt is None or mt.end() != qt.end()
                        or (mt[1], mt[3]) != (qt[1], qt[3]) or (mt[1], mt[3]) == ("<", ">")):
                    raise _DisplayError("rfam_alignment_invalid", "hit_seq")
                mc, qc = _integer(mt[2], "hit_seq"), _integer(qt[2], "user_seq")
                if mc <= 0:
                    raise _DisplayError("rfam_alignment_invalid", "hit_seq")
                is5, is3 = mt[1] == "<", mt[3] == ">"
                if ((is5 and (block != 0 or column != 0))
                        or (is3 and (block != len(models) - 1 or mt.end() != len(model.text)))
                        or ((is5 or is3) and qc != 0)):
                    raise _DisplayError("rfam_alignment_coordinate_conflict", "hit_seq")
                kind = "truncated_model" if is5 or is3 else "local_end"
                mi, qi = _span(mpos, mc), _span(qpos, qc, direction)
                segments.append(dict(kind=kind, model_interval=mi, query_interval=qi,
                                     model_text=mt[0], query_text=qt[0], model_count=mc, query_count=qc,
                                     correspondence_represented=False))
                if is5 or is3:
                    counts["truncated_model_count_5p" if is5 else "truncated_model_count_3p"] += mc
                else:
                    counts["local_end_model_omitted_count"] += mc
                    counts["local_end_query_count"] += qc
                issue("rfam_alignment_correspondence_unrepresented", "hit_seq")
                if pp is not None:
                    codes = pp[column:mt.end()]
                    expected_index = len(codes) - 3
                    code = codes[expected_index]
                    if qc and not is5 and not is3 and code in "0123456789*" and all(
                            c == "." for i, c in enumerate(codes) if i != expected_index):
                        posterior.append(_posterior(qi, code, mean=True))
                    elif qc or codes != "." * len(codes):
                        issue("rfam_alignment_invalid", "pp")
                column = mt.end()
            else:
                if (_rna(ms) not in _RNA and ms != ".") or (_rna(qs) not in _RNA and qs != "-"):
                    raise _DisplayError("rfam_alignment_unsupported", "hit_seq", unsupported=True)
                mc, qc = int(ms != "."), int(qs != "-")
                if not mc and not qc:
                    raise _DisplayError("rfam_alignment_invalid", "user_seq")
                mi, qi = _span(mpos, mc), _span(qpos, qc, direction)
                if qc:
                    if not 0 <= qpos < len(query_sequence):
                        raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
                    expected = _rna(query_sequence[qpos])
                    if direction < 0:
                        expected = expected.translate(_COMPLEMENT)
                    if _rna(qs) != expected:
                        raise _DisplayError("rfam_alignment_query_conflict", "user_seq")
                    query_intervals.append(qi)
                if mc:
                    model_intervals.append(mi)
                kind = "match" if mc and qc else "query_insertion" if qc else "model_deletion"
                _append_segment(segments, dict(kind=kind, model_interval=mi, query_interval=qi,
                                              model_text=ms, query_text=qs, model_count=mc, query_count=qc,
                                              correspondence_represented=True))
                if mc and qc:
                    pairs.append(dict(model_position=mpos, query_position=qpos, consensus_symbol=ms, query_symbol=qs))
                    if _rna(ms) in "ACGU" and _rna(qs) in "ACGU":
                        counts["model_consensus_compared_count"] += 1
                        counts["model_consensus_equal_count"] += _rna(ms) == _rna(qs)
                elif qc:
                    counts["query_insert_count"] += 1
                else:
                    counts["model_delete_count"] += 1
                if pp is not None:
                    code = pp[column]
                    if qc and code in "0123456789*":
                        posterior.append(_posterior(qi, code))
                    elif (qc or code != "."):
                        issue("rfam_alignment_invalid", "pp")
                column += 1
            mpos += mc
            qpos += direction * qc
            block_query_count += qc
        if model.end != mpos:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "hit_seq")
        if block_query_count:
            if query.start is None or query.end != block_query_start + direction * (block_query_count - 1) + 1:
                raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
            if query_first is None:
                query_first = query.start
            query_last = query.end
        elif query.start is not None:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
    if query_first != native_start or query_last != native_end or qpos != native_end - 1 + direction:
        raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
    # Atomic geometry publication: no contradictory full-display prefix is
    # mislabelled as the hit's exact correspondence. Raw evidence survives.
    return dict(counts, display_model_from=models[0].start, display_model_to=models[-1].end,
                  display_query_from=query_first, display_query_to=query_last,
                  segments=segments, paired_positions=pairs, aligned_model_intervals=_union(model_intervals),
                  aligned_query_intervals=_union(query_intervals), posterior_segments=posterior)


def parse_rfam_alignment_display(
    alignment: dict,
    *,
    hit_identity: RfamHitIdentity,
    query_sequence: str,
    native_start: int,
    native_end: int,
    native_strand: Literal["+", "-"],
) -> RfamAlignmentResult:
    """Read supplied native display; malformed native cells return typed issues.

    Invalid caller identity/sequence/strand raises ContractError because no
    correctly bound closed result can be constructed. Malformed display or hit
    endpoints return invalid/unsupported results with null measurements. A bad
    optional annotation track preserves independently validated correspondence.
    """
    identity = validate_rfam_hit_identity(hit_identity)
    if native_strand not in ("+", "-"):
        raise ContractError("rfam_hit_strand_invalid")
    if (type(query_sequence) is not str or not query_sequence or not query_sequence.isascii()
            or any(_rna(c) not in _RNA for c in query_sequence)):
        raise ContractError("rfam_sequence_invalid")
    pointer = identity["hit_key"][len(identity["artifact_ref"]):] + "/alignment"
    result = dict(version="rfam_alignment_components_v1", artifact_ref=identity["artifact_ref"],
                  hit_key=identity["hit_key"], hit_identity=identity, query_strand=native_strand,
                  status="complete", raw_alignment_ref={"artifact_ref": identity["artifact_ref"], "json_pointer": pointer},
                  display_model_from=None, display_model_to=None, display_query_from=None, display_query_to=None,
                  segments=[], paired_positions=[], aligned_model_intervals=[], aligned_query_intervals=[],
                  posterior_segments=[], issues=[], **{name: None for name in RFAM_ALIGNMENT_COUNT_FIELDS})

    def issue(code, field):
        item = make_issue(code, "alignment", hit_key=identity["hit_key"], field=field,
                          source_pointer=pointer + "/" + field)
        if item not in result["issues"]:
            result["issues"].append(item)

    try:
        if (type(native_start) is not int or type(native_end) is not int
                or not 1 <= native_start <= len(query_sequence) or not 1 <= native_end <= len(query_sequence)
                or (native_start > native_end if native_strand == "+" else native_start < native_end)):
            raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
        if alignment is None:
            raise _DisplayError("rfam_alignment_missing", "hit_seq")
        if type(alignment) is not dict:
            raise _DisplayError("rfam_alignment_invalid", "hit_seq")
        models = _axis_lines(alignment.get("hit_seq"), "#CM", "hit_seq")
        queries = _axis_lines(alignment.get("user_seq"), "#SEQ", "user_seq", gaps=True)
        if len(models) != len(queries) or any(len(m.text) != len(q.text) for m, q in zip(models, queries)):
            raise _DisplayError("rfam_alignment_coordinate_conflict", "user_seq")
        if models[0].start < 1 or models[-1].end < 1:
            raise _DisplayError("rfam_alignment_coordinate_conflict", "hit_seq")
        pp_blocks = _annotations(alignment, [len(m.text) for m in models], issue)
        result.update(_alignment_geometry(models, queries, pp_blocks,
            query_sequence=query_sequence, native_start=native_start,
            native_end=native_end, native_strand=native_strand, issue=issue))
        if result["issues"]:
            result["status"] = "partial"
    except _DisplayError as error:
        issue(error.code, error.field)
        result["status"] = "unsupported" if error.unsupported else "invalid"
    return validate_rfam_alignment_result(result)
