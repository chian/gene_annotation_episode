"""Independent arithmetic on these exact retained examples, without package imports.

This is not a replacement native parser or a new scientific execution. It checks
the finite example operands independently of the production implementations.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OWNED = Path(__file__).resolve().parent
MSA = ROOT / "verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples/dna"
META = ROOT / "verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases/aa_two_groups"
XMFA = ROOT / "verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples/combined.xmfa"


def fasta(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            rows.append([line[1:].split()[0], ""])
        elif line:
            rows[-1][1] += line
    assert rows and len({name for name, _ in rows}) == len(rows)
    return rows


def main():
    inputs = [MSA / name for name in ("output.afa", "foma.table", "cons.fasta")]
    inputs += [META / name for name in ("original.fasta", "metadata.tsv", "output/comparison-chisqTable.tsv")]
    inputs.append(XMFA)
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    msa = fasta(MSA / "output.afa")
    widths = {len(sequence) for _, sequence in msa}
    assert widths == {7}
    cells = sum(len(sequence) for _, sequence in msa)
    gaps = sum(sequence.count("-") for _, sequence in msa)
    column = 1
    eligible, excluded = [], []
    for name, sequence in msa:
        left, right = len(sequence) - len(sequence.lstrip("-")), len(sequence.rstrip("-"))
        (eligible if left <= column < right else excluded).append((name, sequence[column]))
    counts = Counter(symbol for _, symbol in eligible)
    entropy = -sum((count / len(eligible)) * math.log2(count / len(eligible)) for count in counts.values())
    frequency = list(csv.DictReader(io.StringIO((MSA / "foma.table").read_text()), delimiter="\t"))
    score = int(next(row for row in frequency if row["Position in Alignment"] == "2")["Score"])
    assert len(msa) == 4 and cells == 28 and gaps == 6 and score == 92
    assert math.isclose(entropy, 0.9182958340544896, rel_tol=1e-14)

    metadata = list(csv.DictReader(io.StringIO((META / "metadata.tsv").read_text()), delimiter="\t"))
    by_member = {row["Seq_ID"]: row["comparison"] for row in metadata}
    meta = fasta(META / "original.fasta")
    assert set(by_member) == {name for name, _ in meta}
    raw = [[sum(sequence[column] == symbol and by_member[name] == group for name, sequence in meta)
            for group in ("A", "B")] for symbol in ("A", "C")]
    epsilon = 0.001
    matrix = [[value + epsilon for value in row] for row in raw]
    row_totals = [sum(row) for row in matrix]
    column_totals = [sum(row[index] for row in matrix) for index in range(2)]
    total = sum(row_totals)
    expected = [[row_totals[i] * column_totals[j] / total for j in range(2)] for i in range(2)]
    delta = min(0.5, *(abs(matrix[i][j] - expected[i][j]) for i in range(2) for j in range(2)))
    chi_square = math.fsum((abs(matrix[i][j] - expected[i][j]) - delta) ** 2 / expected[i][j]
                           for i in range(2) for j in range(2))
    p_value_df1 = math.erfc(math.sqrt(chi_square / 2))
    native = list(csv.DictReader(io.StringIO((META / "output/comparison-chisqTable.tsv").read_text()), delimiter="\t"))
    assert len(native) == 1 and native[0]["Position"] == "2"
    assert len(meta) == 12 and raw == [[6, 0], [0, 6]]
    assert math.isclose(chi_square, 8.330556481172943, rel_tol=1e-14)
    assert math.isclose(p_value_df1, 0.0038983714243371837, rel_tol=1e-14)

    blocks, block, current = [], {}, None
    for line in XMFA.read_text().splitlines():
        if line.startswith("#") or not line:
            continue
        if line == "=":
            assert block
            blocks.append(block)
            block, current = {}, None
        elif line.startswith(">"):
            match = re.fullmatch(r">\s+(\d+):(\d+)-(\d+)\s+([+-])\s+(.+)", line)
            assert match is not None
            current = int(match[1])
            assert current not in block
            block[current] = {"native_header": line, "sequence": ""}
        else:
            assert current is not None
            block[current]["sequence"] += line
    assert not block and len(blocks) == 6
    assert all(len({len(row["sequence"]) for row in one.values()}) == 1 for one in blocks)
    a, b = (blocks[0][member]["sequence"] for member in (1, 3))
    pair = [(left, right) for left, right in zip(a, b, strict=True) if left in "ACGT" and right in "ACGT"]
    identical = sum(left == right for left, right in pair)
    substitutions = sum(left != right for left, right in pair)
    assert (identical, substitutions, len(pair)) == (39, 7, 46)
    after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    assert after == before
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": before,
        "source_bytes_unchanged": True,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "independent standard-library arithmetic on exact retained bytes; no production imports, Workflow, acquisition, native analysis or model call",
        "msa": {"member_count": len(msa), "cell_count": cells, "gap_count": gaps,
            "gap_fraction": gaps / cells, "column_0based": column,
            "eligible_members_and_symbols": eligible, "excluded_terminal_members_and_symbols": excluded,
            "symbol_counts": dict(counts), "entropy_bits": entropy, "native_score": score,
            "entropy_formula": "-sum(p*log2(p)), denominator 3 eligible symbols; internal dash retained, terminal dash excluded"},
        "metacats": {"member_count": len(meta), "column_0based": column,
            "symbol_row_order": ["A", "C"], "group_column_order": ["A", "B"],
            "raw_counts": raw, "epsilon_per_cell": epsilon, "augmented_counts": matrix,
            "expected_counts": expected, "continuity_delta": delta, "degrees_of_freedom": 1,
            "chi_square": chi_square, "chi_square_formula": "sum((abs(observed-expected)-delta)^2/expected)",
            "p_df1_erfc": p_value_df1, "p_formula": "erfc(sqrt(chi_square/2)) for df=1",
            "native_exported_chi_square_token": native[0]["Chi-square_value"],
            "native_exported_p_token": native[0]["P-value"]},
        "xmfa": {"block_count": len(blocks), "block_index": 0, "members": [1, 3],
            "identical_canonical": identical, "substitutions": substitutions,
            "comparable_canonical": len(pair), "identity_fraction": identical / len(pair),
            "native_headers": [blocks[0][member]["native_header"] for member in (1, 3)],
            "original_member_mapping_verified": False, "producer_identity_verified": False},
    }
    with (OWNED / "independent-retained-numbers.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"msa": result["msa"], "metacats": result["metacats"], "xmfa": result["xmfa"]}, sort_keys=True))


if __name__ == "__main__":
    main()
