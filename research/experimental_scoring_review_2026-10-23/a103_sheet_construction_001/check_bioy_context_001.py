"""Research arithmetic: source count meanings and explicitly synthetic context comparisons."""
from fractions import Fraction
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent

def contrast(p, background):
    if p == background:
        return Fraction(0)
    if p > background:
        return (p-background)/(1-background)
    return (p-background)/background

def single_question_coordinate(signed):
    return max(Fraction(0), signed) * (1-max(Fraction(0), -signed))

# Main article's reported counts. The exact associated-locus count is not supplied.
bioy_genes, represented_genomes = 150, 127
excess_copies = bioy_genes - represented_genomes
assert excess_copies == 23
ratio = Fraction(bioy_genes, represented_genomes)
assert ratio > 1

# These are invented exact cohorts, not a reconstruction of the article's approximate one-third.
p = Fraction(3, 9)
rare_background, common_background = Fraction(1, 10), Fraction(5, 10)
rare_contrast = contrast(p, rare_background)
common_contrast = contrast(p, common_background)
assert rare_contrast == Fraction(7, 27)
assert common_contrast == Fraction(-1, 3)
assert single_question_coordinate(rare_contrast) == Fraction(7, 27)
assert single_question_coordinate(common_contrast) == 0
# Frequency, not count of replicated descriptions, determines the arithmetic.
assert contrast(Fraction(6, 18), rare_background) == rare_contrast
assert contrast(Fraction(0), Fraction(0)) == 0
assert contrast(Fraction(1), Fraction(1)) == 0
assert contrast(Fraction(1), Fraction(0)) == 1
assert contrast(Fraction(0), Fraction(1)) == -1
# An unresolved member remains in the declared complete denominator.
frequency_bounds = [Fraction(3, 10), Fraction(4, 10)]
bounds = [contrast(v, rare_background) for v in frequency_bounds]
assert bounds == [Fraction(2, 9), Fraction(1, 3)]

result = {
    "kind": "research_arithmetic_not_a_genome_analysis_or_production_score",
    "primary_doi": "10.1073/pnas.0609905104",
    "reported_source_counts": {"bioy_genes": bioy_genes, "represented_genomes": represented_genomes},
    "derived_source_count_diagnostics": {"genes_per_represented_genome": float(ratio), "excess_copies_over_one_per_genome": excess_copies},
    "reported_association": {"display": "approximately one-third", "exact_numerator": None, "exact_fraction": None, "precision_bound": None},
    "historical_paper_coordinate": None,
    "historical_missing_operands": ["exact eligible spatial observations", "identical endpoint on matched background", "dependence blocks and stratum denominators"],
    "synthetic_examples": {
        "foreground": {"positive": 3, "total": 9},
        "rare_background": {"positive": 1, "total": 10, "signed_contrast": float(rare_contrast), "single_question_coordinate": float(single_question_coordinate(rare_contrast))},
        "common_background": {"positive": 5, "total": 10, "signed_contrast": float(common_contrast), "single_question_coordinate": float(single_question_coordinate(common_contrast))},
        "unresolved_member": {"positive": 3, "unresolved": 1, "total": 10, "foreground_frequency_bounds": list(map(float, frequency_bounds)), "contrast_bounds_against_1_in_10_background": list(map(float, bounds)), "point": None}
    },
    "checks": ["source denominators stay distinct", "exact association count is not inferred", "rare versus common background contrasts", "boundary denominators", "unresolved-member bounds"]
}
payload = json.dumps(result, indent=2) + "\n"
output = HERE / "bioy_parent_arithmetic_001.json"
if output.exists():
    assert output.read_text() == payload, "Preserve prior receipt; use additive correction"
else:
    output.write_text(payload)
print(json.dumps({"status": "passed", "source_genes_per_genome": float(ratio),
                  "synthetic_signed_contrasts": [float(rare_contrast), float(common_contrast)],
                  "receipt": str(output)}))
