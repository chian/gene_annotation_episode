"""Fixed research fixture; no reader or production score is implemented here."""
from copy import deepcopy
from fractions import Fraction
from math import prod
from pathlib import Path
import json

directory = Path(__file__).resolve().parent
fixture = json.loads((directory / "synthetic_context_units_001.json").read_text())
assert fixture["origin"] == "synthetic"

def check_rows(rows):
    unique = {}
    for row in rows:
        if row["id"] in unique:
            assert unique[row["id"]] == row
        unique[row["id"]] = row
    resolved = []
    for row in unique.values():
        low = row["width_nm"] - row["bound_nm"]
        high = row["width_nm"] + row["bound_nm"]
        access = int(row["access"] == "cytoplasm_connected")
        width_lower = int(90 <= low and high <= 140)
        width_upper = 1 - int(high <= 80 or low >= 150)
        resolved.append((row["weight"], access * width_lower, access * width_upper))
    denominator = sum(row[0] for row in resolved)
    lower = Fraction(sum(w*l for w, l, u in resolved), denominator)
    upper = Fraction(sum(w*u for w, l, u in resolved), denominator)
    # The fixture preserves an unexamined permitted organism-state remainder.
    cap_lower = 1 - prod(1-l for w, l, u in resolved)
    cap_upper = 1 if fixture["unexamined_permitted_remainder"] else 1-prod(1-u for w,l,u in resolved)
    assert 0 <= lower <= upper <= 1
    return lower, upper, cap_lower, cap_upper, denominator

base = check_rows(fixture["units"])
assert base == (Fraction(3,4), Fraction(3,4), 1, 1, 12)
assert Fraction(10,12)*Fraction(9,10) == base[0]
duplicate = check_rows(fixture["units"] + [deepcopy(fixture["units"][0])])
assert duplicate == base
unknown = deepcopy(fixture["units"])
unknown[0]["width_nm"] = 84
partial = check_rows(unknown)
assert partial == (Fraction(2,3), Fraction(3,4), 1, 1, 12)
rare = deepcopy(fixture["units"])
for row in rare[1:]:
    row["width_nm"] = 170
rare_result = check_rows(rare)
assert rare_result == (Fraction(1,12), Fraction(1,12), 1, 1, 12)
negative = deepcopy(rare)
negative[0]["width_nm"] = 170
negative_result = check_rows(negative)
assert negative_result == (0, 0, 0, 1, 12)
# A separate synthetic whole-scope necessary exclusion permits no context.
whole_scope_exclusion = (0,0)
assert whole_scope_exclusion == (0,0)
marginal_product = Fraction(10,12)*Fraction(11,12)
assert marginal_product == Fraction(55,72) and marginal_product != base[0]
assert Fraction(35,40) == Fraction(7,8)
assert Fraction(57+56+57,41+42+43) == Fraction(85,63)
assert (50+10,60+15) == (60,75)

def report(value):
    if isinstance(value, tuple):
        return [report(item) for item in value]
    if isinstance(value, Fraction):
        return {"exact":str(value),"decimal":float(value)}
    return value

receipt = {
    "origin":"synthetic_arithmetic_check_only",
    "base_coverage_bounds_capability_bounds_denominator":report(base),
    "duplicate_unchanged":duplicate == base,
    "partial":report(partial),
    "rare_but_possible":report(rare_result),
    "negative_sample_unexamined_states":report(negative_result),
    "whole_scope_exclusion":whole_scope_exclusion,
    "unpaired_marginal_product_is_not_joint":report(marginal_product),
    "source_boundary_arithmetic":{"35_of_40":report(Fraction(7,8)),
                                 "harvest_density_ratio_not_growth_effect":report(Fraction(85,63)),
                                 "approximate_onset_interval_sum_minutes":[60,75]},
    "status":"all_fixture_assertions_passed",
    "reader_implementation":False,
    "production_credit_implementation":False
}
(directory / "arithmetic_receipt_001.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
