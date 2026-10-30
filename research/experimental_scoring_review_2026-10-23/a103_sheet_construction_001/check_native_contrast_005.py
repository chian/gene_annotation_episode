"""Bounded research verification of two retained native neighborhood examples.

No network request, biological reconstruction or production scorer runs here.
Outputs are separately dated database examples, not historical paper scores.
"""
from decimal import Decimal as D
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]
NEW = BASE / "a103_scored_published_contrast_031"


def read(path):
    return json.loads(path.read_text(), parse_float=D)


bio_rows = read(NEW / "string_bioy_bion_network_002.json")
rib_record = read(BASE / "a103_numerical_sheet_011/string_ribk_pair.json")
rib_rows = rib_record["selected_pair_rows"]
aliases = read(NEW / "uniprot_locus_aliases_001.json")["results"]
mapping = read(NEW / "string_bioy_mapping_001.json")
version = read(NEW / "string_version_001.json")
checks = []


def verify(name, condition):
    assert condition, name
    checks.append(name)


verify("one exact BioY/BioN network row", len(bio_rows) == 1)
verify("one selected exact RibK/RibB network row", len(rib_rows) == 1)
bio, rib = bio_rows[0], rib_rows[0]
verify("BioY/BioN exact unordered identifiers", {bio["stringId_A"], bio["stringId_B"]} == {
    "272942.RCAP_rcc03249", "272942.RCAP_rcc03250"})
verify("RibK/RibB exact unordered identifiers", {rib["stringId_A"], rib["stringId_B"]} == {
    "243232.MJ_0055", "243232.MJ_0056"})
verify("BioY/BioN organism taxon", str(bio["ncbiTaxonId"]) == "272942")
by_name = {r["queryItem"]: r for r in mapping}
verify("name queries map to the scored BioY/BioN pair", (
    by_name["bioY"]["stringId"], by_name["bioN"]["stringId"]
) == ("272942.RCAP_rcc03249", "272942.RCAP_rcc03250"))
entries = {entry["primaryAccession"]: entry for entry in aliases}
for accession, gene_name, locus in [("D5ARG8", "bioY", "RCAP_rcc03249"),
                                    ("D5ARG9", "bioN", "RCAP_rcc03250")]:
    entry = entries[accession]
    verify(accession + " exact gene/locus", any(
        gene.get("geneName", {}).get("value") == gene_name
        and locus in {r["value"] for r in gene.get("orderedLocusNames", [])}
        for gene in entry["genes"]))
    verify(accession + " exact STRING cross-reference", any(
        r["database"] == "STRING" and r["id"] == "272942." + locus
        for r in entry["uniProtKBCrossReferences"]))
    verify(accession + " taxon and SB1003 strain", entry["organism"]["taxonId"] == 272942
           and "SB1003" in entry["organism"]["scientificName"])
verify("cbiQ3 is an explicit BioN synonym", any(
    r["value"] == "cbiQ3" for gene in entries["D5ARG9"]["genes"]
    for r in gene.get("synonyms", [])))
verify("retained version endpoint", version[0]["string_version"] == "12.5")

examples = {}
for name, row, expected in [("BioY_BioN", bio, D(".844")),
                            ("RibK_RibB", rib, D(".956"))]:
    native = row["nscore"]
    verify(name + " actual native neighborhood field", native == expected)
    verify(name + " unit-interval native scale", D(0) <= native <= D(1))
    direction, weight = D(1), D(1)
    t = direction * native
    supporting = weight * max(t, D(0))
    opposing = weight * max(-t, D(0))
    coordinate = supporting * (1 - opposing)
    verify(name + " one-question compilation", coordinate == native and opposing == 0)
    examples[name] = {
        "native_neighborhood": native, "excluded_combined": row["score"],
        "direction": direction, "weight": weight, "t": t,
        "S": supporting, "O": opposing, "c": coordinate,
        "comparison_overlap_C": "not_applicable",
        "matched_count_contrast_E": "not_applicable",
    }
neighborhood_difference = rib["nscore"] - bio["nscore"]
combined_difference = rib["score"] - bio["score"]
verify("native descriptive difference", neighborhood_difference == D(".112"))
verify("combined-channel ordering reversal", combined_difference == D("-.040"))
result = {
    "scope": "retained native records and bounded arithmetic; no fresh service or paper read",
    "checks": checks, "check_count": len(checks), "examples": examples,
    "native_descriptive_difference": neighborhood_difference,
    "excluded_combined_difference": combined_difference,
    "limits": [
        "Reference-locus identity does not establish sequence identity of a historical assay construct.",
        "These separately retrieved database scores are not reported historical paper measurements.",
        "No calibrated cross-species probability comparison is inferred from the .112 difference.",
        "Native biological calibration uncertainty is unreported, not zero.",
        "No new annotation target is assigned either pair's score.",
    ],
}
out = Path(__file__).with_name("native_contrast_parent_arithmetic_005.json")
with out.open("x") as stream:
    json.dump(result, stream, default=str, indent=2)
print(json.dumps({"checks": len(checks), "examples": examples,
                  "native_difference": neighborhood_difference,
                  "receipt": str(out)}, default=str, indent=2))
