"""Fixed invented decimal/finite-interface examples; no source-reader execution."""
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from gene_annotation_episode.literature_controlled_response_calculations import _q


def main():
    rows = []
    for raw in ("0.1", "0.10000000000000000001", "12.000", "1e308", "1e-500"):
        exact, floating = Fraction(raw), float(raw)
        rejected = not math.isfinite(floating) or floating == 0 and exact != 0
        same = False if rejected else exact == _q(floating)
        rows.append({"original_source_lexeme": raw,
            "source_exact": {"numerator": str(exact.numerator), "denominator": str(exact.denominator)},
            "technical_float_conversion": floating, "finite_projection_accepted": not rejected,
            "source_equals_frozen_q_str_interpretation": same,
            "numeric_projection_rounding": not same and not rejected,
            "numeric_range_failure": rejected})
    assert rows[0]["source_equals_frozen_q_str_interpretation"]
    assert rows[1]["numeric_projection_rounding"]
    assert rows[2]["source_equals_frozen_q_str_interpretation"]
    assert rows[3]["source_equals_frozen_q_str_interpretation"]
    assert rows[4]["numeric_range_failure"] and rows[4]["finite_projection_accepted"] is False
    assert Fraction.from_float(.1) != Fraction("0.1")  # Deliberately NOT the comparison criterion.
    with (HERE / "ROUNDTRIP_PROOF_007.json").open("x") as stream:
        json.dump({"scope": "Synthetic frozen-number compatibility only", "rows": rows,
            "binary_float_exact_ratio_is_not_rounding_criterion": True,
            "reader_implemented": False, "runtime_observations": 0}, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "passed", "fixed_examples": len(rows), "ordinary_point_one_is_not_approximate": True}))


if __name__ == "__main__":
    main()
