"""Research arithmetic for the published TriA/AtzA comparison; no alignment job."""
from fractions import Fraction
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent
packet = json.loads((HERE.parent / "a101_tria_native_010/cells_001.json").read_text())
# Independently transcribed from the published Figure 3, AtzA -> TriA.
changes = [(84, "F", "L"), (92, "V", "L"), (125, "E", "D"),
           (217, "T", "I"), (219, "T", "P"), (253, "I", "L"),
           (255, "G", "W"), (328, "N", "D"), (331, "S", "C")]
observed = [(row["reference_position"], row["reference_residue"], row["target_residue"])
            for row in packet["differences"]]
assert observed == changes
assert all(row["reference_position"] == row["target_position"] for row in packet["differences"])
length = 475
mismatch_positions = {pos for pos, _, _ in changes}
assert len(mismatch_positions) == 9
blocks = []
for start in range(1, length + 1, 50):
    end = min(length, start + 49)
    n = end - start + 1
    m = sum(start <= pos <= end for pos in mismatch_positions)
    blocks.append({"start": start, "end": end, "pairs": n,
                   "identities": n-m, "mismatches": m})
identities = sum(row["identities"] for row in blocks)
identity = Fraction(identities, length)
weighted = sum(Fraction(row["pairs"], length) * Fraction(row["identities"], row["pairs"])
               for row in blocks)
assert identities == 466 and weighted == identity == Fraction(466, 475)
naive_block_mean = sum(Fraction(row["identities"], row["pairs"]) for row in blocks) / len(blocks)
assert naive_block_mean != identity
# Duplicated descriptions of the same physical coordinate do not add residues.
unique_pairs = {(pos, pos) for row in blocks + blocks[:3]
                for pos in range(row["start"], row["end"] + 1)}
assert len(unique_pairs) == length
assert sum(q not in mismatch_positions for q, _ in unique_pairs) == identities
cells = packet["cells"]
for name, value in [("target_length", length), ("reference_length", length),
                    ("aa_identity_count", identities), ("aa_mismatch_count", 9),
                    ("aa_identity_fraction", float(identity)), ("target_coverage", 1),
                    ("reference_coverage", 1)]:
    assert math.isclose(cells[name]["value"], value, rel_tol=1e-12)
for name in ["alignment_score", "bitscore", "evalue", "profile_score",
             "domain_identity_fraction", "required_site_identity_fraction"]:
    assert cells[name]["value"] is None
nt_identity = Fraction(1425 - 9, 1425)
assert math.isclose(cells["nt_identity_fraction_conditional"]["value"], float(nt_identity))
receipt = {
    "kind": "research_arithmetic_not_an_alignment_or_scoring_run",
    "primary_doi": "10.1128/JB.183.8.2405-2410.2001",
    "published_protein_alignment_pairs": length,
    "published_protein_alignment_identities": identities,
    "mismatches_atza_to_tria": changes,
    "blocks_are_printed_intervals_not_domains": blocks,
    "protein_identity_fraction": float(identity),
    "protein_identity_exact": str(identity),
    "length_weighted_block_identity": float(weighted),
    "incorrect_unweighted_block_mean_for_comparison": float(naive_block_mean),
    "target_and_reference_coverage": 1.0,
    "conditional_sense_coding_nt_identity": float(nt_identity),
    "nucleotide_scope_assumption": "1425 nt is the common sense-coding comparison span; nucleotide alignment and stop-codon treatment are not supplied",
    "sequence_measurement_error_distribution": None,
    "whole_axis_coordinate": None,
    "checks": ["nine figure substitutions agree", "475 residues, excluding stop symbol",
               "466 exact identities", "length-weighted block reconciliation",
               "duplicate coordinate descriptions add nothing", "native count cells agree",
               "unreported alignment scores and functional site set stay unknown",
               "conditional nucleotide arithmetic agrees"]
}
output = HERE / "tria_parent_arithmetic_003.json"
payload = json.dumps(receipt, indent=2) + "\n"
if output.exists():
    assert output.read_text() == payload, "Preserve earlier receipt; write an additive correction instead"
else:
    output.write_text(payload)
print(json.dumps({"status": "passed", "checks": receipt["checks"],
                  "protein_identity": float(identity), "receipt": str(output)}))
