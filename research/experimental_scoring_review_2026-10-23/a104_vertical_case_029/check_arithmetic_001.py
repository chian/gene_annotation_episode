"""Check arithmetic for the retained source example; no scientific inference."""
from fractions import Fraction
from math import comb
from pathlib import Path
import json

intended_displayed_members = ["Paer", "Pstu", "Pflu", "Pput", "Avin"]
reported_characterized_members = ["Paer", "Pstu"]
assert len(intended_displayed_members) == len(set(intended_displayed_members)) == 5
assert set(reported_characterized_members) <= set(intended_displayed_members)
coverage = Fraction(len(reported_characterized_members), len(intended_displayed_members))
assert coverage == Fraction(2, 5)
assert comb(5, 3) == 10
assert comb(5, 4) == 5

result = {
    "meaning": "Real-source member-count arithmetic; no tree construction or complete score",
    "intended_displayed_members": intended_displayed_members,
    "reported_characterized_members": reported_characterized_members,
    "n_displayed": 5,
    "k_reported": 2,
    "source_listed_coverage_fraction": str(coverage),
    "source_listed_coverage": float(coverage),
    "strict_canonical_C_f": None,
    "conditional_five_taxon_rooted_triplets": comb(5, 3),
    "conditional_five_taxon_unrooted_quartets": comb(5, 4),
    "rooted_comparison_justified": False,
    "M": None, "D": None, "U": None, "F": None,
    "J": None, "O": None, "whole_A104_score": None,
    "native_bootstrap_replicates": 1000,
    "figure_legend_filled_strict_lower_count": 988,
    "figure_legend_filled_min_integer_fraction": 989 / 1000,
    "figure_legend_open_strict_lower_count": 900,
    "figure_legend_open_min_integer_fraction": 901 / 1000,
    "specific_subgroup_boundary_bootstrap": None,
    "unresolved_mapping": {"Avin_displayed_GI": "53612601", "Avin_link_GI": "13105295"},
    "limitations": [
        "Coverage is for five selected displayed members, not every natural clade member",
        "Original assay-to-canonical-protein/strain identity was not independently rechecked",
        "No matched organismal tree, branch lengths or query placement supplied",
        "Integer bootstrap legend conversions are not assigned to an unverified subgroup boundary",
    ],
}
out = Path(__file__).with_name("arithmetic_results_001.json")
if out.exists():
    raise FileExistsError("Preserve the earlier arithmetic result; use a new numbered output")
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"source_coverage": float(coverage), "conditional_triplets": 10,
                  "conditional_quartets": 5, "whole_A104_score": None}))
