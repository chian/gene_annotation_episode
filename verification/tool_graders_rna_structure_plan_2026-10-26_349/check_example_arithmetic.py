"""Independent hand-specified coordinate arithmetic; not a proposed grader.

The predictor example is transcribed from the official tutorial, not executed
on this machine. All other structures are supplied planning examples.
"""
from collections import Counter
from pathlib import Path
import json

cases = [
    {"id": "supplied_hairpin", "sequence": "GGGAAACCC", "structure": "(((...)))",
     "pairs": [[0, 8], [1, 7], [2, 6]], "stems": [3], "hairpin_sizes": [3], "internal_sizes": [], "exterior": []},
    {"id": "supplied_two_hairpins", "sequence": None, "structure": "((...))..((...))",
     "pairs": [[0, 6], [1, 5], [9, 15], [10, 14]], "stems": [2, 2], "hairpin_sizes": [3, 3], "internal_sizes": [], "exterior": [7, 8]},
    {"id": "supplied_internal_loop", "sequence": None, "structure": "((..((...))..))",
     "pairs": [[0, 14], [1, 13], [4, 10], [5, 9]], "stems": [2, 2], "hairpin_sizes": [3], "internal_sizes": [4], "exterior": []},
    {"id": "supplied_unpaired", "sequence": "AAAA", "structure": "....",
     "pairs": [], "stems": [], "hairpin_sizes": [], "internal_sizes": [], "exterior": [0, 1, 2, 3]},
    {"id": "official_documented_mfe", "sequence": "CUACGGCGCGGCGCCCUUGGCGA", "structure": "...........((((...)))).",
     "pairs": [[11, 21], [12, 20], [13, 19], [14, 18]], "stems": [4], "hairpin_sizes": [3], "internal_sizes": [],
     "exterior": list(range(11)) + [22], "documented_mfe_kcal_mol": -5.00,
     "source_url": "https://www.tbi.univie.ac.at/RNA/ViennaRNA/doc/html/usage/tutorial/RNAfold.html#mfe-structure-of-a-single-sequence"},
]

for case in cases:
    n, pairs = len(case["structure"]), case["pairs"]
    assert case["sequence"] is None or len(case["sequence"]) == n
    paired = sorted(x for pair in pairs for x in pair)
    assert len(paired) == len(set(paired))
    assert all(case["structure"][i] == "(" and case["structure"][j] == ")" for i, j in pairs)
    unpaired = [i for i in range(n) if i not in paired]
    assert all(case["structure"][i] == "." for i in unpaired)
    assert len(unpaired) == sum(case["hairpin_sizes"]) + sum(case["internal_sizes"]) + len(case["exterior"])
    case["expected"] = {
        "n_nt": n, "pair_count": len(pairs), "paired_nt": len(paired),
        "unpaired_nt": len(unpaired), "paired_fraction": len(paired) / n,
        "unpaired_fraction": len(unpaired) / n, "stem_count": len(case["stems"]),
        "longest_stem_pairs": max(case["stems"], default=0),
        "mean_stem_pairs": sum(case["stems"]) / len(case["stems"]) if case["stems"] else None,
        "stack_count": sum(length - 1 for length in case["stems"]),
        "mean_pair_span_nt": sum(j - i for i, j in pairs) / len(pairs) if pairs else None,
        "hairpin_count": len(case["hairpin_sizes"]), "internal_loop_count": len(case["internal_sizes"]),
        "external_unpaired_nt": len(case["exterior"]),
        "ordered_pair_symbols": None if case["sequence"] is None else dict(Counter(case["sequence"][i] + case["sequence"][j] for i, j in pairs)),
        "mfe_per_nt_kcal_mol_nt": case["documented_mfe_kcal_mol"] / n if "documented_mfe_kcal_mol" in case else None,
    }
print(json.dumps({"verification_kind": "hand_specified_coordinate_arithmetic", "cases": cases}, indent=2, allow_nan=False))
(Path.cwd() / "examples.json").write_text(json.dumps(cases, indent=2, allow_nan=False) + "\n")
