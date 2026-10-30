"""Contract arithmetic audit only; no production imports or scientific execution.

Read the actual retained native text independently of the production reader,
compare it with the saved reader projections, and emit checkable exact integers
and fractions. This is not a proposed production parser/calculator implementation.
Run from anywhere: python3 /absolute/path/to/verify_examples.py
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NATIVE = ROOT / "tests/fixtures/bvbrc_proteome_directional"
FILLED = ROOT / "verification/tool_graders_bvbrc_proteome_directional_2026-10-25_172"
AA20 = set("ACDEFGHIKLMNPQRSTVWY")


def exact_ratio(n, d):
    if d == 0:
        return {"numerator": n, "denominator": d, "decimal_18_places": None}
    with localcontext() as context:
        context.prec = 60
        context.rounding = ROUND_HALF_EVEN
        decimal = format(Decimal(n) / Decimal(d), ".18f")
    reduced = Fraction(n, d)
    return {"numerator": n, "denominator": d,
            "reduced": f"{reduced.numerator}/{reduced.denominator}",
            "decimal_18_places": decimal}


def ranges(values):
    result = []
    for value in sorted(set(values)):
        if result and result[-1][1] + 1 == value:
            result[-1][1] = value
        else:
            result.append([value, value])
    return result


def native_decimal(text):
    return Decimal("1" + text if text.lower().startswith("e") else text)


def inspect_cells(node, raw, source, path=""):
    """Verify every native lexical cell against its exact retained byte slices."""
    count = 0
    if isinstance(node, dict):
        if set(node) == {"state", "value", "native_text", "locations"}:
            if node["state"] == "missing":
                assert node["value"] is None and node["native_text"] is None
                assert node["locations"] == []
            else:
                parts = []
                for loc in node["locations"]:
                    assert loc["source_ref"] == source["source_ref"], path
                    assert loc["sha256"] == source["sha256"], path
                    span = loc["span"]
                    parts.append(raw[span["byte_start"]:span["byte_end"]].decode())
                # Reader's multiline fields retain exact joined native slices.
                assert "".join(parts) == node["native_text"], (path, parts, node)
            count += 1
        else:
            for key, value in node.items():
                count += inspect_cells(value, raw, source, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            count += inspect_cells(value, raw, source, f"{path}/{index}")
    return count


def blocks_from_text(text):
    queries = re.findall(r"^Query:\s*(\d+)\s+([A-Za-z*\-]+)\s+(\d+)\s*$", text, re.M)
    subjects = re.findall(r"^Sbjct:\s*(\d+)\s+([A-Za-z*\-]+)\s+(\d+)\s*$", text, re.M)
    assert len(queries) == len(subjects)
    result = []
    for q, s in zip(queries, subjects):
        result.append({"query_start": int(q[0]), "query_symbols": q[1], "query_end": int(q[2]),
                       "subject_start": int(s[0]), "subject_symbols": s[1], "subject_end": int(s[2])})
    return result


def audit_hsp(blocks):
    pairs, columns = [], []
    query_occupied, subject_occupied = set(), set()
    joined_q, joined_s = "", ""
    previous = None
    for block_index, b in enumerate(blocks):
        q, s = b["query_symbols"].upper(), b["subject_symbols"].upper()
        assert len(q) == len(s)
        assert b["query_end"] - b["query_start"] + 1 == len(q.replace("-", ""))
        assert b["subject_end"] - b["subject_start"] + 1 == len(s.replace("-", ""))
        if previous:
            assert b["query_start"] == previous["query_end"] + 1
            assert b["subject_start"] == previous["subject_end"] + 1
        previous = b
        qi, si = b["query_start"], b["subject_start"]
        for column, (a, c) in enumerate(zip(q, s)):
            assert (a, c) != ("-", "-")
            qp = None if a == "-" else qi
            sp = None if c == "-" else si
            record = {"block": block_index, "column": column,
                      "query_position_1based": qp, "subject_position_1based": sp,
                      "query_symbol": a, "subject_symbol": c}
            columns.append(record)
            if qp is not None:
                query_occupied.add(qp)
                qi += 1
            if sp is not None:
                subject_occupied.add(sp)
                si += 1
            if qp is not None and sp is not None:
                pairs.append(record)
        joined_q += q
        joined_s += s
    identical = sum(p["query_symbol"] == p["subject_symbol"] for p in pairs)
    resolved = [p for p in pairs if p["query_symbol"] in AA20 and p["subject_symbol"] in AA20]
    resolved_identical = sum(p["query_symbol"] == p["subject_symbol"] for p in resolved)
    ambiguous = [p for p in pairs if p not in resolved]
    stops = [p for p in pairs if "*" in (p["query_symbol"], p["subject_symbol"])]
    counts = {"alignment_columns": len(columns), "paired_columns": len(pairs),
              "displayed_symbol_identical_pairs": identical,
              "displayed_symbol_nonidentical_pairs": len(pairs) - identical,
              "resolved_amino_acid_pairs": len(resolved),
              "resolved_amino_acid_identical_pairs": resolved_identical,
              "resolved_amino_acid_substituted_pairs": len(resolved) - resolved_identical,
              "ambiguous_or_nonresidue_pairs": len(ambiguous),
              "unresolved_symbol_pairs": len(ambiguous) - len(stops),
              "stop_containing_pairs": len(stops),
              "query_gap_columns": joined_q.count("-"),
              "subject_gap_columns": joined_s.count("-"),
              "query_gap_runs": len(re.findall(r"-+", joined_q)),
              "subject_gap_runs": len(re.findall(r"-+", joined_s)),
              "occupied_query_positions": len(query_occupied),
              "occupied_subject_positions": len(subject_occupied)}
    assert counts["paired_columns"] + counts["query_gap_columns"] + counts["subject_gap_columns"] == counts["alignment_columns"]
    return {"counts": counts,
            "query_occupied_ranges_1based_inclusive": ranges(query_occupied),
            "subject_occupied_ranges_1based_inclusive": ranges(subject_occupied),
            "ambiguous_query_ranges_1based_inclusive": ranges(p["query_position_1based"] for p in ambiguous),
            "displayed_symbol_identity": exact_ratio(identical, len(pairs)),
            "resolved_amino_acid_identity": exact_ratio(resolved_identical, len(resolved)),
            "_pairs": pairs, "_columns": columns,
            "_query_occupied": query_occupied, "_subject_occupied": subject_occupied}


def audit_union(hsps, qlength, slength):
    qocc, socc = set(), set()
    pairs = defaultdict(list)
    qmaps, smaps = defaultdict(set), defaultdict(set)
    qsymbols, ssymbols = defaultdict(set), defaultdict(set)
    for hindex, hsp in enumerate(hsps):
        qocc |= hsp["_query_occupied"]
        socc |= hsp["_subject_occupied"]
        for column in hsp["_columns"]:
            q, s = column["query_position_1based"], column["subject_position_1based"]
            if q is not None:
                qsymbols[q].add(column["query_symbol"])
                qmaps[q].add(s)
            if s is not None:
                ssymbols[s].add(column["subject_symbol"])
                smaps[s].add(q)
        for p in hsp["_pairs"]:
            key = p["query_position_1based"], p["subject_position_1based"]
            pairs[key].append((hindex, p["query_symbol"], p["subject_symbol"]))
    qpaired = {q for q, _ in pairs}
    spaired = {s for _, s in pairs}
    alternative_q = {q for q, values in qmaps.items() if len(values - {None}) > 1}
    alternative_s = {s for s, values in smaps.items() if len(values - {None}) > 1}
    gap_conflict_q = {q for q, values in qmaps.items() if None in values and len(values) > 1}
    gap_conflict_s = {s for s, values in smaps.items() if None in values and len(values) > 1}
    symbol_conflict_q = {q for q, values in qsymbols.items() if len(values) > 1}
    symbol_conflict_s = {s for s, values in ssymbols.items() if len(values) > 1}
    ordered = sorted(pairs)
    crossing = any(s1 >= s2 for (_, s1), (_, s2) in zip(ordered, ordered[1:]))
    compatible = not any([alternative_q, alternative_s, gap_conflict_q, gap_conflict_s,
                          symbol_conflict_q, symbol_conflict_s, crossing])
    unique_identical = sum(all(a == b for _, a, b in support) for support in pairs.values())
    result = {
        "displayed_hsp_count": len(hsps),
        "hsp_column_occurrence_sum": sum(h["counts"]["alignment_columns"] for h in hsps),
        "hsp_paired_column_occurrence_sum": sum(h["counts"]["paired_columns"] for h in hsps),
        "occupied_query_union_count": len(qocc), "occupied_subject_union_count": len(socc),
        "paired_query_union_count": len(qpaired), "paired_subject_union_count": len(spaired),
        "distinct_coordinate_pairs": len(pairs),
        "repeated_coordinate_pair_occurrences": sum(map(len, pairs.values())) - len(pairs),
        "query_occupied_union_coverage": exact_ratio(len(qocc), qlength),
        "subject_occupied_union_coverage": exact_ratio(len(socc), slength),
        "query_paired_union_coverage": exact_ratio(len(qpaired), qlength),
        "subject_paired_union_coverage": exact_ratio(len(spaired), slength),
        "query_occupied_ranges_1based_inclusive": ranges(qocc),
        "subject_occupied_ranges_1based_inclusive": ranges(socc),
        "alternative_query_mapping_positions": ranges(alternative_q),
        "alternative_subject_mapping_positions": ranges(alternative_s),
        "query_gap_vs_pair_conflict_positions": ranges(gap_conflict_q),
        "subject_gap_vs_pair_conflict_positions": ranges(gap_conflict_s),
        "query_symbol_conflict_positions": ranges(symbol_conflict_q),
        "subject_symbol_conflict_positions": ranges(symbol_conflict_s),
        "strictly_increasing_pair_order": not crossing,
        "compatible_displayed_partial_correspondence": compatible,
        "compatible_union_displayed_symbol_identity": exact_ratio(unique_identical, len(pairs)) if compatible else None,
    }
    return result


def without_private(node):
    if isinstance(node, dict):
        return {k: without_private(v) for k, v in node.items() if not k.startswith("_")}
    if isinstance(node, list):
        return [without_private(v) for v in node]
    return node


def audit_report(code, name):
    raw = (NATIVE / name).read_bytes()
    text = raw.decode()
    saved_path = FILLED / f"FILLED_NATIVE_{code}_001.json"
    saved = json.loads(saved_path.read_text())
    source = saved["source"]["content"]
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == source["sha256"] and len(raw) == source["byte_count"]
    cell_count = inspect_cells(saved, raw, source)
    qtexts = re.split(r"(?m)^Query=", text)[1:]
    assert len(qtexts) == len(saved["queries"])
    out_queries = []
    for qi, (qt, sq) in enumerate(zip(qtexts, saved["queries"])):
        qlength = int(re.search(r"\(([\d,]+) letters\)", qt)[1].replace(",", ""))
        assert qlength == sq["length"]["value"]
        descriptions = []
        if "Sequences producing significant alignments:" in qt:
            description_text = qt.split("Sequences producing significant alignments:", 1)[1].split("\n>", 1)[0]
            descriptions = re.findall(r"(?m)^(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9eE.+-]+)\s*$", description_text)
        assert len(descriptions) == len(sq["descriptions"]), (code, qi)
        for (label, score, expect), row in zip(descriptions, sq["descriptions"]):
            assert label == row["label"]["value"]
            assert score == row["bit_score"]["native_text"]
            assert expect == row["evalue"]["native_text"]
            assert native_decimal(score) == Decimal(row["bit_score"]["value"])
            assert native_decimal(expect) == Decimal(row["evalue"]["value"])
        stexts = re.split(r"(?m)^>", qt)[1:]
        assert len(stexts) == len(sq["subjects"])
        out_subjects = []
        for si, (st, ss) in enumerate(zip(stexts, sq["subjects"])):
            slength = int(re.search(r"Length\s*=\s*([\d,]+)", st)[1].replace(",", ""))
            assert slength == ss["length"]["value"]
            htexts = re.split(r"(?m)^\s+Score\s*=", st)[1:]
            assert len(htexts) == len(ss["hsps"])
            out_hsps = []
            for hi, (ht, sh) in enumerate(zip(htexts, ss["hsps"])):
                blocks = blocks_from_text(ht)
                assert len(blocks) == len(sh["traceback_blocks"])
                for b, sb in zip(blocks, sh["traceback_blocks"]):
                    assert all(value == sb[key]["value"] for key, value in b.items())
                reported = {}
                for label, prefix in [("Identities", "identity"), ("Positives", "positive"), ("Gaps", "gap")]:
                    match = re.search(rf"{label}\s*=\s*(\d+)/(\d+)\s*\((\d+)%\)", ht)
                    reported[prefix] = None if match is None else [int(v) for v in match.groups()]
                    for offset, suffix in enumerate(["count", "denominator", "printed_percent"]):
                        expected = None if match is None else (match[offset+1] if suffix == "printed_percent" else int(match[offset+1]))
                        assert sh[f"{prefix}_{suffix}"]["value"] == expected
                score = re.search(r"^\s*([\d.]+) bits\s*\((\d+)\), Expect(?:\((\d+)\))?\s*=\s*([^,\s]+)", ht)
                assert score, (code, qi, si, hi)
                scores = dict(zip(["bit_score", "raw_score", "expect_group_count", "expect"], score.groups()))
                for key, val in scores.items():
                    assert sh[key]["native_text"] == val
                    if val is None:
                        assert sh[key]["value"] is None
                    elif key in {"raw_score", "expect_group_count"}:
                        assert sh[key]["value"] == int(val)
                    else:
                        assert Decimal(sh[key]["value"]) == native_decimal(val)
                hsp = audit_hsp(blocks)
                assert reported["identity"][0] == hsp["counts"]["displayed_symbol_identical_pairs"]
                assert reported["identity"][1] == hsp["counts"]["alignment_columns"]
                if reported["gap"] is not None:
                    assert reported["gap"][0] == hsp["counts"]["query_gap_columns"] + hsp["counts"]["subject_gap_columns"]
                hsp.update(ordinal=hi, native_pointer=f"/queries/{qi}/subjects/{si}/hsps/{hi}",
                           reported_counts_and_printed_percent=reported, native_lexical_scores=scores,
                           block_count=len(blocks),
                           query_paired_coverage=exact_ratio(hsp["counts"]["paired_columns"], qlength),
                           subject_paired_coverage=exact_ratio(hsp["counts"]["paired_columns"], slength))
                out_hsps.append(hsp)
            out_subjects.append({"ordinal": si, "reported_subject_length": slength,
                                 "hsps": out_hsps, "union": audit_union(out_hsps, qlength, slength)})
        out_queries.append({"ordinal": qi, "reported_query_length": qlength,
                            "native_no_hit_marker_present": "No hits found" in qt,
                            "displayed_description_count": len(descriptions),
                            "displayed_subject_count": len(out_subjects),
                            "displayed_hsp_count": sum(len(s["hsps"]) for s in out_subjects),
                            "subjects": out_subjects})
    return {"fixture": name, "sha256": digest, "byte_count": len(raw),
            "saved_projection": str(saved_path.relative_to(ROOT)),
            "saved_native_cells_checked_including_missing_invariants": cell_count,
            "query_count": len(out_queries),
            "description_count": sum(q["displayed_description_count"] for q in out_queries),
            "subject_count": sum(q["displayed_subject_count"] for q in out_queries),
            "hsp_count": sum(q["displayed_hsp_count"] for q in out_queries),
            "queries": out_queries}


def synthetic_block(q, s, qstart=1, sstart=1):
    return {"query_start": qstart, "query_end": qstart + len(q.replace("-", "")) - 1,
            "query_symbols": q, "subject_start": sstart,
            "subject_end": sstart + len(s.replace("-", "")) - 1, "subject_symbols": s}


def synthetic_examples():
    base = audit_hsp([synthetic_block("ACDE", "ACDE")])
    overlap = audit_hsp([synthetic_block("DEFG", "DEFG", 3, 3)])
    shifted = audit_hsp([synthetic_block("ACDE", "ACDE", 1, 2)])
    substituted = audit_hsp([synthetic_block("ACDE", "ACDF")])
    gap = audit_hsp([synthetic_block("AC-D", "ACTD")])
    crossing = audit_hsp([synthetic_block("FG", "FG", 5, 1)])
    cases = {
        "duplicate_and_consistent_overlap": audit_union([base, base, overlap], 10, 10),
        "alternative_mapping": audit_union([base, shifted], 10, 10),
        "same_coordinates_different_symbols": audit_union([base, substituted], 10, 10),
        "pair_versus_gap": audit_union([base, gap], 10, 10),
        "noncollinear_disjoint_segments": audit_union([audit_hsp([synthetic_block("AC", "AC", 1, 5)]), crossing], 10, 10),
        "ambiguity_and_stop": without_private(audit_hsp([synthetic_block("AXBC*U", "AYDC*U")])),
        "gapped_hsp": without_private(audit_hsp([synthetic_block("ACD-EFG", "ACTVE-G", 2, 4)])),
    }
    assert cases["duplicate_and_consistent_overlap"]["distinct_coordinate_pairs"] == 6
    assert cases["duplicate_and_consistent_overlap"]["compatible_union_displayed_symbol_identity"]["numerator"] == 6
    assert cases["alternative_mapping"]["compatible_union_displayed_symbol_identity"] is None
    assert cases["same_coordinates_different_symbols"]["compatible_union_displayed_symbol_identity"] is None
    assert cases["pair_versus_gap"]["compatible_union_displayed_symbol_identity"] is None
    assert cases["noncollinear_disjoint_segments"]["compatible_union_displayed_symbol_identity"] is None
    return cases


def main():
    reports = {code: audit_report(code, name) for code, name in [
        ("2011", "biopython_text_2011L_blastp_002.txt"),
        ("2202", "biopython_text_2202L_blastp_001.txt"),
        ("2221", "biopython_text_2221L_blastp_001.txt")]}
    r = reports["2221"]
    assert (r["description_count"], r["subject_count"], r["hsp_count"]) == (30, 3, 4)
    s = r["queries"][1]["subjects"][0]
    assert s["union"]["query_occupied_union_coverage"]["numerator"] == 529
    assert s["union"]["query_occupied_union_coverage"]["denominator"] == 600
    assert s["union"]["compatible_union_displayed_symbol_identity"]["numerator"] == 468
    assert s["union"]["compatible_union_displayed_symbol_identity"]["denominator"] == 529
    assert s["hsps"][0]["counts"]["ambiguous_or_nonresidue_pairs"] == 61
    assert s["hsps"][0]["counts"]["resolved_amino_acid_substituted_pairs"] == 0
    assert (reports["2202"]["description_count"], reports["2202"]["subject_count"], reports["2202"]["hsp_count"]) == (23, 23, 25)
    assert reports["2011"]["queries"][0]["native_no_hit_marker_present"]
    for name, body in [("NUMERICAL_NATIVE_EXAMPLES_001.json", without_private(reports)),
                       ("SYNTHETIC_NUMERICAL_EXAMPLES_001.json", synthetic_examples())]:
        (HERE / name).write_text(json.dumps(body, indent=2, allow_nan=False) + "\n")
    write_excerpt(reports)
    for code, report in reports.items():
        print(code, "native cells checked (including missing-state invariants)", report["saved_native_cells_checked_including_missing_invariants"],
              "queries/descriptions/subjects/HSPs", [report[k] for k in ("query_count", "description_count", "subject_count", "hsp_count")])
    print("2221 query1 subject0 union:", json.dumps(s["union"], sort_keys=True))
    for q in reports["2202"]["queries"]:
        print("2202 query", q["ordinal"], "subject0 union:", json.dumps(q["subjects"][0]["union"], sort_keys=True))


def write_excerpt(reports):
    """Save small numerical excerpts with native paths, not a fake complete sheet."""
    selected = []
    for code, qi in [("2221", 1), ("2202", 0), ("2202", 1)]:
        full = json.loads((FILLED / f"FILLED_NATIVE_{code}_001.json").read_text())
        numeric = reports[code]["queries"][qi]["subjects"][0]
        observed = []
        for hi, h in enumerate(full["queries"][qi]["subjects"][0]["hsps"]):
            cells = {}
            for k in ["identity_count", "identity_denominator", "positive_count",
                      "positive_denominator", "gap_count", "gap_denominator",
                      "bit_score", "raw_score", "expect"]:
                cells[k] = {"native_pointer": f"/queries/{qi}/subjects/0/hsps/{hi}/{k}",
                            "state": h[k]["state"], "value": h[k]["value"],
                            "native_text": h[k]["native_text"]}
            observed.append({"hsp_ordinal": hi, "native_cells": cells,
                             "derived_trace_counts": numeric["hsps"][hi]["counts"]})
        union = numeric["union"]
        identity = union["compatible_union_displayed_symbol_identity"]
        selected.append({
            "fixture": reports[code]["fixture"],
            "source_sha256": reports[code]["sha256"],
            "report_key": full["report_key"], "query_ordinal": qi, "subject_ordinal": 0,
            "reported_query_length": full["queries"][qi]["length"]["value"],
            "reported_subject_length": full["queries"][qi]["subjects"][0]["length"]["value"],
            "observed_hsps": observed,
            "calculated_union": union,
            "compatible_identity_cell": {
                "state": "value" if identity is not None else "conflict",
                "value": None if identity is None else {
                    "numerator": identity["numerator"], "denominator": identity["denominator"],
                    "decimal": identity["decimal_18_places"]},
                "unit": "fraction", "uncertainty": None,
                "reasons": [] if identity is not None else ["alternative_subject_mapping"],
            },
        })
    body = {"artifact_kind": "explicitly_incomplete_numerical_sheet_excerpt",
            "not_a_conforming_complete_sheet": True,
            "note": "Native locations/full query and description membership remain in the source projections; this excerpt selects three subject occurrences for human review.",
            "parameters": {"version": "bvbrc_proteome_directional_parameters_v1",
                           "formula_version": "displayed_blastp_correspondence_v1",
                           "amino_acid_alphabet": "standard20", "ratio_decimal_places": 18,
                           "rounding": "half_even"},
            "selected_subjects": selected}
    (HERE / "FILLED_NUMERICAL_SHEET_EXCERPT_001.json").write_text(json.dumps(body, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
