"""Check proposal examples from retained public bytes and upstream parser output.

This is evidence verification, not the proposed native reader or a scientific run.
It makes no network calls and invokes no native scientific executable.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import re


ROOT = Path(__file__).resolve().parent


def ratio(numerator, denominator):
    value = Fraction(numerator, denominator)
    return {"numerator": numerator, "denominator": denominator,
            "reduced_fraction": str(value), "decimal_for_display": float(value)}


def correspondence(hsp):
    query, subject = hsp[11], hsp[14]
    assert len(query) == len(subject) == int(hsp[4])
    qpos, spos = int(hsp[9]), int(hsp[12])
    qpositions, spositions, pairs = set(), set(), []
    for qchar, schar in zip(query, subject):
        assert qchar != "-" or schar != "-"
        if qchar != "-":
            qpositions.add(qpos)
        if schar != "-":
            spositions.add(spos)
        if qchar != "-" and schar != "-":
            pairs.append((qpos, spos, qchar == schar))
        qpos += qchar != "-"
        spos += schar != "-"
    assert qpos - 1 == int(hsp[10]) and spos - 1 == int(hsp[13])
    assert sum(equal for _, _, equal in pairs) == int(hsp[5])
    return {"alignment_columns": len(query), "paired_columns": len(pairs),
            "identity_columns": sum(equal for _, _, equal in pairs),
            "query_gap_columns": query.count("-"),
            "subject_gap_columns": subject.count("-"),
            "query_positions": qpositions, "subject_positions": spositions,
            "pairs": pairs}


def main():
    receipts = []
    for name in ("ACQUISITION_RECEIPTS_002.json", "ACQUISITION_RECEIPTS_003.json"):
        receipts.extend(json.loads((ROOT / name).read_text()))
    for row in receipts:
        content = (ROOT / row["file"]).read_bytes()
        assert len(content) == row["byte_count"]
        assert hashlib.sha256(content).hexdigest() == row["sha256"]

    early = json.loads((ROOT / "biopython_text_2202L_blastp_001_upstream_parsed.json").read_text())
    later = json.loads((ROOT / "biopython_text_2221L_blastp_001_upstream_parsed.json").read_text())
    assert [len(q[3]) for q in early] == [15, 8]
    assert [sum(len(s[3]) for s in q[3]) for q in early] == [16, 9]
    assert [len(q[3]) for q in later] == [1, 1, 1]
    assert [sum(len(s[3]) for s in q[3]) for q in later] == [1, 2, 1]
    descriptions = []
    text = (ROOT / "biopython_text_2221L_blastp_001.txt").read_text()
    for tail in text.split("Sequences producing significant alignments:")[1:]:
        table = tail.split("\n\n", 1)[1].split("\n>", 1)[0]
        descriptions.append(len([line for line in table.splitlines() if line.strip()]))
    assert descriptions == [10, 10, 10]

    a = [correspondence(h) for h in early[0][3][0][3]]
    aq = set.union(*(h["query_positions"] for h in a))
    ass = set.union(*(h["subject_positions"] for h in a))
    assert (len(aq), len(ass)) == (219, 144)
    assert (a[0]["query_gap_columns"], a[0]["subject_gap_columns"]) == (4, 32)
    assert a[0]["paired_columns"] == 140
    subject_to_query = {}
    for h in a:
        for qpos, spos, _ in h["pairs"]:
            subject_to_query.setdefault(spos, set()).add(qpos)
    conflicts = sorted(pos for pos, qs in subject_to_query.items() if len(qs) > 1)
    assert conflicts
    early_text = (ROOT / "biopython_text_2202L_blastp_001.txt").read_text()
    first_subject = early_text.split("\n>", 1)[1].split("\n>", 1)[0]
    scores = first_subject.split(" Score =")[1:]
    assert len(scores) == 2 and "Gaps =" not in scores[1]

    b = [correspondence(h) for h in later[1][3][0][3]]
    bq = set.union(*(h["query_positions"] for h in b))
    bs = set.union(*(h["subject_positions"] for h in b))
    assert (len(bq), len(bs)) == (529, 529)
    assert not (b[0]["query_positions"] & b[1]["query_positions"])
    assert sum(h["identity_columns"] for h in b) == 468

    nohit = (ROOT / "biopython_text_2011L_blastp_002.txt").read_text()
    assert nohit.count("Query=") == 1 and "No hits found" in nohit
    assert not re.search(r"^>", nohit, re.M)
    assert "6999 sequences; 1,461,753 total letters" in nohit
    assert "Number of sequences better than 10.0: 0" in nohit

    result = {
        "operation": "native public fixture evidence checks; not proposed reader implementation or live scientific execution",
        "passed": True,
        "native_cardinalities": {
            "2.2.2": {"queries": 2, "subjects": 23, "hsps": 25},
            "2.2.21": {"queries": 3, "description_rows": 30, "subjects": 3, "hsps": 4},
            "2.0.11": {"queries": 1, "subjects": 0, "hsps": 0, "explicit_no_hits": True}},
        "early_first_subject": {
            "first_hsp_identity": ratio(53, 176),
            "first_hsp_legacy_query_endpoint_fraction": ratio(171, 1922),
            "first_hsp_legacy_subject_endpoint_fraction": ratio(143, 249),
            "all_hsp_query_union_coverage": ratio(219, 1922),
            "all_hsp_subject_union_coverage": ratio(144, 249),
            "first_hsp_paired_columns": 140,
            "first_hsp_query_gaps": 4, "first_hsp_subject_gaps": 32,
            "second_hsp_native_gap_field": "missing",
            "second_hsp_traceback_gap_columns": 0,
            "subject_positions_mapping_to_distinct_query_positions": conflicts},
        "later_second_query": {
            "first_hsp_legacy_endpoint_fraction": ratio(413, 600),
            "first_hsp_inclusive_coverage": ratio(414, 600),
            "all_hsp_union_coverage_both_operands": ratio(529, 600),
            "disjoint_all_hsp_identity_fraction": ratio(468, 529)},
        "limitations": ["Published primary fixture provenance, not BV-BRC task custody",
                        "Upstream parser output includes fallback values; source bytes control missingness",
                        "No native program, database search, or service job executed"]}
    (ROOT / "NATIVE_NUMERICAL_VERIFICATION_001.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "result": "NATIVE_NUMERICAL_VERIFICATION_001.json"}))


if __name__ == "__main__":
    main()
