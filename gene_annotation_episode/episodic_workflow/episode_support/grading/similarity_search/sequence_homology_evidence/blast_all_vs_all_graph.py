"""The similarity graph of an all-vs-all BLAST: report rows to directed edges, and whether the search is complete.

The grader's slot-filling stage for this analysis. It reads the tabular report the job declared and returns the
graph's directed edges, one per ordered pair of distinct sequences, with identity and coverage of BOTH sequences.
It assigns no cluster, no function and no credit, and it never reads a sequence's name for meaning: a sequence is
its identifier only.

Rules kept from the pairwise grader: alternative HSPs of a pair are never summed. A pair's coverage of a sequence is
the union of its HSP intervals on that sequence; its identity and bit score are those of its best HSP (highest bit
score; ties by lower E-value, then earlier query start, then earlier subject start).

Completeness: a query that was really searched always finds itself, so a query with no self-hit was not searched
(or was masked away entirely). A run whose queries lack self-hits, or whose chunks are missing, is ``incomplete``;
it is never read as 'no relatives'.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import intervals

REPORT_FIELDS = ("qaccver", "saccver", "pident", "nident", "length", "mismatch", "gapopen",
                 "qstart", "qend", "sstart", "send", "qlen", "slen", "evalue", "bitscore")
_INTEGERS = ("nident", "length", "mismatch", "gapopen", "qstart", "qend", "sstart", "send", "qlen", "slen")
_REALS = ("pident", "evalue", "bitscore")


def parse_report(text, fields=REPORT_FIELDS):
    """The rows of a tabular report, typed. An empty report has no rows; a malformed row raises."""
    fields = tuple(fields)
    if set(REPORT_FIELDS) - set(fields):
        raise ValueError("blast_all_vs_all_report_fields_missing:" + ",".join(sorted(set(REPORT_FIELDS) - set(fields))))
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != len(fields):
            raise ValueError("blast_all_vs_all_report_row_width:" + str(number))
        row = dict(zip(fields, parts))
        try:
            for name in _INTEGERS:
                row[name] = int(row[name])
            for name in _REALS:
                row[name] = float(row[name])
        except ValueError as error:
            raise ValueError("blast_all_vs_all_report_row_number:" + str(number)) from error
        if min(row[name] for name in _INTEGERS) < 0 or row["qlen"] < 1 or row["slen"] < 1 or row["length"] < 1:
            raise ValueError("blast_all_vs_all_report_row_range:" + str(number))
        rows.append(row)
    return rows


def _covered(pairs, length):
    """The number of positions the 1-based inclusive HSP intervals cover once (the union, never a sum), by the shared
    half-open interval union."""
    return sum(stop - start for start, stop in intervals([(first - 1, last) for first, last in pairs], length=length))


def build_edges(rows):
    """One directed edge per ordered pair ``(query, subject)`` present in the rows, in a fixed order. Self pairs are
    kept (``self: True``): they are the evidence a query was searched, and the graph consumers skip them."""
    groups = {}
    for row in rows:
        groups.setdefault((row["qaccver"], row["saccver"]), []).append(row)
    edges = []
    for (query, subject), hsps in sorted(groups.items()):
        lengths = {(h["qlen"], h["slen"]) for h in hsps}
        if len(lengths) != 1:
            raise ValueError("blast_all_vs_all_pair_with_conflicting_lengths:" + query + ":" + subject)
        qlen, slen = lengths.pop()
        for h in hsps:
            if not (1 <= min(h["qstart"], h["qend"]) and max(h["qstart"], h["qend"]) <= qlen
                    and 1 <= min(h["sstart"], h["send"]) and max(h["sstart"], h["send"]) <= slen):
                raise ValueError("blast_all_vs_all_hsp_outside_sequence:" + query + ":" + subject)
        best = sorted(hsps, key=lambda h: (-h["bitscore"], h["evalue"], min(h["qstart"], h["qend"]),
                                           min(h["sstart"], h["send"])))[0]
        covered_q = _covered([(min(h["qstart"], h["qend"]), max(h["qstart"], h["qend"])) for h in hsps], qlen)
        covered_s = _covered([(min(h["sstart"], h["send"]), max(h["sstart"], h["send"])) for h in hsps], slen)
        edges.append({"query": query, "subject": subject, "self": query == subject,
                      "query_length": qlen, "subject_length": slen,
                      "identity": round(best["nident"] / best["length"], 6),
                      "query_coverage": round(covered_q / qlen, 6),
                      "subject_coverage": round(covered_s / slen, 6),
                      "bitscore": best["bitscore"], "evalue": min(h["evalue"] for h in hsps),
                      "hsp_count": len(hsps)})
    return edges


def completeness(edges, expected_queries, *, chunks_expected=1, chunks_present=None):
    """Whether every expected query was searched. ``expected_queries`` are the query identifiers the run covers;
    ``chunks_present`` is the set of chunk indices whose reports were merged (``None``: one chunk)."""
    expected = list(expected_queries)
    if len(set(expected)) != len(expected):
        raise ValueError("blast_all_vs_all_expected_queries_repeat")
    searched = {edge["query"] for edge in edges if edge["self"]}
    missing = sorted(set(expected) - searched)
    unexpected = sorted(searched - set(expected))
    partial = sorted(edge["query"] for edge in edges if edge["self"] and edge["query"] in set(expected)
                     and (edge["identity"] < 0.99 or edge["query_coverage"] < 0.99))
    present = set(range(chunks_expected)) if chunks_present is None else set(chunks_present)
    missing_chunks = sorted(set(range(chunks_expected)) - present)
    complete = not missing and not missing_chunks and not unexpected
    return {"status": "complete" if complete else "incomplete", "expected_queries": len(expected),
            "searched_queries": len(set(expected) & searched), "missing_queries": missing,
            "unexpected_queries": unexpected, "partial_self_hits": partial, "missing_chunks": missing_chunks}


def merge_chunks(chunks):
    """Merge the graphs of several query chunks of one run. Each chunk is
    ``{'index', 'count', 'queries': [ids], 'edges': [...]}``. The chunks must agree on the count, have distinct
    indices and disjoint queries; the result lists the merged edges, the queries the present chunks cover and the
    indices present. ``completeness`` is then asked against the WHOLE set's identifiers, not these: a missing
    chunk's queries appear nowhere in the results."""
    if not chunks:
        raise ValueError("blast_all_vs_all_no_chunks")
    counts = {chunk["count"] for chunk in chunks}
    if len(counts) != 1:
        raise ValueError("blast_all_vs_all_chunks_disagree_on_count")
    count = next(iter(counts))
    indices = [chunk["index"] for chunk in chunks]
    if len(set(indices)) != len(indices) or any(not 0 <= i < count for i in indices):
        raise ValueError("blast_all_vs_all_chunk_indices_invalid")
    queries = [q for chunk in chunks for q in chunk["queries"]]
    if len(set(queries)) != len(queries):
        raise ValueError("blast_all_vs_all_chunks_overlap")
    merged = sorted((edge for chunk in chunks for edge in chunk["edges"]),
                    key=lambda e: (e["query"], e["subject"]))
    pairs = [(e["query"], e["subject"]) for e in merged]
    if len(set(pairs)) != len(pairs):
        raise ValueError("blast_all_vs_all_chunk_edges_repeat_a_pair")
    owned = {q for chunk in chunks for q in chunk["queries"]}
    if any(e["query"] not in owned for e in merged):
        raise ValueError("blast_all_vs_all_edge_from_a_query_outside_its_chunk")
    return {"edges": merged, "queries_present": sorted(queries), "chunks_expected": count,
            "chunks_present": sorted(indices)}


__all__ = ["REPORT_FIELDS", "build_edges", "completeness", "merge_chunks", "parse_report"]
