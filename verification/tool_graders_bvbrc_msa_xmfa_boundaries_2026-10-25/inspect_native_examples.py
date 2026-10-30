"""Offline fixture arithmetic, not the proposed production XMFA implementation.

Uses an explicit fixture-to-source map grounded in retained upstream tests.
The tiny inspector accepts only the retained example syntax. No network,
aligner, service, episode or proposed production parser is invoked.
"""
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
EXAMPLES = BASE / "native_examples"
HEADER = re.compile(r">\s*(\d+):(\d+)-(\d+)\s+([+-])(?:\s+(.*))?$", re.ASCII)
COMP = str.maketrans("ACGTRYMKBDHVNacgtrymkbdhvn", "TGCAYRKMVHDBNtgcayrkmvhdbn")


def fasta(name):
    records = []
    for line in (EXAMPLES / name).read_text().splitlines():
        if line.startswith(">"):
            records.append({"header": line[1:], "sequence": ""})
        else:
            records[-1]["sequence"] += line
    return records


def inspect(name, sources):
    text = (EXAMPLES / name).read_text()
    blocks, rows = [], []
    for line in text.splitlines():
        if line.startswith("#") or not line:
            continue
        if line.startswith(">"):  # only retained well-formed fixture deflines
            match = HEADER.fullmatch(line)
            assert match, line
            member, start, end, strand, comment = match.groups()
            rows.append({"member": int(member), "start": int(start), "end": int(end),
                         "strand": strand, "comment": comment, "sequence": ""})
        elif line.startswith("="):
            blocks.append({"closed": True, "rows": rows})
            rows = []
        else:
            rows[-1]["sequence"] += line
    if rows:
        blocks.append({"closed": False, "rows": rows})
    summaries = []
    all_covered = {n: set() for n in sources}
    multi_covered = {n: set() for n in sources}
    paired_covered = {n: set() for n in sources}
    for bi, block in enumerate(blocks):
        positive = [r for r in block["rows"] if r["start"] > 0 and r["end"] > 0]
        row_summaries, maps = [], {}
        for ri, r in enumerate(block["rows"]):
            seq = r["sequence"]
            ungapped = seq.replace("-", "")
            interval = [r["start"] - 1, r["end"]] if r["start"] else None
            span = r["end"] - r["start"] + 1 if r["start"] else 0
            valid = len(ungapped) == span
            offsets, consumed = [], 0
            for symbol in seq:
                if symbol == "-" or interval is None or not valid:
                    offsets.append(None)
                else:
                    pos = r["start"] - 1 + consumed if r["strand"] == "+" else r["end"] - 1 - consumed
                    offsets.append(pos)
                    consumed += 1
            maps[r["member"]] = offsets
            source = sources.get(r["member"])
            matches_source = None
            if source is not None and valid and interval is not None:
                expected = source["sequence"][interval[0]:interval[1]]
                if r["strand"] == "-":
                    expected = expected.translate(COMP)[::-1]
                matches_source = expected == ungapped
                assert matches_source, (name, bi, ri)
                all_covered[r["member"]].update(p for p in offsets if p is not None)
                if len(positive) >= 2:
                    multi_covered[r["member"]].update(p for p in offsets if p is not None)
            row_summaries.append({"row_index": ri, "member": r["member"],
                "source_header": source["header"] if source else None,
                "native_start": r["start"], "native_end": r["end"], "strand": r["strand"],
                "interval_0based_half_open": interval, "gapped_columns": len(seq),
                "ungapped_bases": len(ungapped), "gap_characters": seq.count("-"),
                "declared_span_bases": span, "span_matches": valid,
                "matches_source_oriented_interval": matches_source,
                "column_positions_0based": offsets})
        pair_summaries = []
        for a, b in combinations(positive, 2):
            tally = Counter()
            for col, (x, y) in enumerate(zip(a["sequence"], b["sequence"])):
                category = "both_gap" if x == y == "-" else "a_only_gap" if x == "-" else "b_only_gap" if y == "-" else "identical_canonical" if x == y and x in "ACGT" else "substitution" if x in "ACGT" and y in "ACGT" else "ambiguous_or_other"
                tally[category] += 1
                if x != "-" and y != "-" and a["member"] in sources and b["member"] in sources:
                    for r in (a, b):
                        pos = maps[r["member"]][col]
                        if pos is not None:
                            paired_covered[r["member"]].add(pos)
            i, s = tally["identical_canonical"], tally["substitution"]
            pair_summaries.append({"members": [a["member"], b["member"]],
                "counts": dict(tally), "comparable_canonical_columns": i + s,
                "identity_fraction": i / (i + s) if i + s else None,
                "ragged": len(a["sequence"]) != len(b["sequence"])})
        summaries.append({"block_index": bi, "terminated_by_equals": block["closed"],
            "present_members": [r["member"] for r in positive],
            "zero_record_members": [r["member"] for r in block["rows"] if r["start"] == r["end"] == 0],
            "rows": row_summaries, "pairs": pair_summaries})
    coverage = []
    for member, source in sources.items():
        n = len(source["sequence"])
        coverage.append({"member": member, "source_header": source["header"], "length_bases": n,
            "represented_union_bases": len(all_covered[member]),
            "multi_member_block_union_bases": len(multi_covered[member]),
            "cooccupied_column_union_bases": len(paired_covered[member]),
            "represented_fraction": len(all_covered[member]) / n,
            "multi_member_block_fraction": len(multi_covered[member]) / n,
            "cooccupied_column_fraction": len(paired_covered[member]) / n,
            "not_in_multimember_blocks_0based": sorted(set(range(n)) - multi_covered[member])})
    return {"fixture": name, "sha256": hashlib.sha256((EXAMPLES / name).read_bytes()).hexdigest(),
            "block_count": len(blocks), "blocks": summaries, "coverage": coverage}


def main():
    combined = {i + 1: r for i, r in enumerate(fasta("combined.fa"))}
    # This order is literal in separate.xmfa metadata and upstream generating argv.
    separate = {1: fasta("equCab1.fa")[0], 2: fasta("canFam2.fa")[0], 3: fasta("mm9.fa")[0]}
    results = [inspect("combined.xmfa", combined), inspect("separate.xmfa", separate),
               inspect("simple.xmfa", {}), inspect("simple_short.xmfa", {})]
    assert results[0]["block_count"] == 6
    assert results[0]["blocks"][0]["pairs"][0]["counts"] == {
        "identical_canonical": 39, "substitution": 7, "b_only_gap": 2, "a_only_gap": 1}
    assert [r["represented_union_bases"] for r in results[0]["coverage"]] == [50, 41, 49]
    assert [r["multi_member_block_union_bases"] for r in results[0]["coverage"]] == [48, 0, 47]
    assert [r["cooccupied_column_union_bases"] for r in results[0]["coverage"]] == [46, 0, 46]
    import Bio
    from Bio import Align
    independent = []
    for name in ("combined.xmfa", "separate.xmfa", "simple.xmfa", "simple_short.xmfa"):
        try:
            aln = list(Align.parse(EXAMPLES / name, "mauve"))
            independent.append({"fixture": name, "status": "parsed", "block_count": len(aln),
                                "shapes": [list(a.shape) for a in aln],
                                "coordinates": [a.coordinates.tolist() for a in aln]})
        except Exception as exc:
            independent.append({"fixture": name, "status": "raised", "exception": type(exc).__name__, "message": str(exc)})
    node = r"""
const fs = require('fs');
const reader = require(process.argv[1]);
for (const f of process.argv.slice(2)) {
 const text = fs.readFileSync(f, 'utf8');
 const result = reader.parse(text);
 console.log(JSON.stringify({file:f,blocks:result.map(b=>b.map(r=>({member:r.lcb_idx,start:r.start,end:r.end,strand:r.strand,length:r.seq.length})))}));
}
"""
    command = ["node", "-e", node, str(BASE / "retained_sources/p3_mauve/scripts/xmfa-parser.js"),
               str(EXAMPLES / "combined.xmfa"), str(EXAMPLES / "separate.xmfa")]
    completed = subprocess.run(command, text=True, capture_output=True, check=True)
    native_js = [json.loads(line) for line in completed.stdout.splitlines()]
    output = {"kind": "offline_fixture_arithmetic_and_existing_parser_checks",
        "not_run": ["progressiveMauve", "App-MSA", "AppService", "episode_communication", "proposed_production_parser"],
        "python": sys.version, "biopython_version": Bio.__version__, "examples": results,
        "biopython_reader_checks": independent,
        "unmodified_bvbrc_xmfa_parser_checks": {"exit_code": completed.returncode,
                                              "stderr": completed.stderr, "results": native_js}}
    (BASE / "NATIVE_ARITHMETIC.json").write_text(json.dumps(output, indent=2) + "\n")
    for result in results[:2]:
        print(result["fixture"], "blocks", result["block_count"], "coverage", result["coverage"])
    print("Biopython", independent)
    print("BV-BRC native parser", native_js)


if __name__ == "__main__":
    main()
