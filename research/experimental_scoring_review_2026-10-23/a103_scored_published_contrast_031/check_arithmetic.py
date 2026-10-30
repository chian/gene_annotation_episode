"""Bounded research check for the saved A103 BioY reference-pair example.

No network access, production imports, general reader or policy installation.
The RibK comparison values are inherited from the parent's verified example.
"""

import datetime
import hashlib
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKS = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def read(name):
    return json.loads((ROOT / name).read_text(), parse_float=Decimal)


def num(value):
    return float(value) if value is not None else None


def cell(value, units, origin, inputs, calculation, *, bounds=None,
         state=None, missing_reason=None, calibration="unreported"):
    if state is None:
        state = "bounded" if bounds is not None else "point"
    lo, hi = bounds if bounds is not None else (value, value)
    if state == "not_applicable":
        value = lo = hi = None
    return {
        "state": state, "point": num(value), "lower": num(lo), "upper": num(hi),
        "units": units, "origin": origin, "input_refs": inputs,
        "calculation_ref": calculation, "missing_reason": missing_reason,
        "identification_uncertainty": (
            "outer_bounds" if state == "bounded" else
            "not_applicable" if state == "not_applicable" else "none"
        ),
        "sampling_interval": None, "calibration_uncertainty": calibration,
        "calibration_ref": None,
    }


pair = {"272942.RCAP_rcc03249", "272942.RCAP_rcc03250"}
mapping = read("string_bioy_mapping_001.json")
exact = read("string_bioy_bion_network_002.json")
expanded = read("string_bioy_bion_network_001.json")
uniprot = read("uniprot_locus_aliases_001.json")["results"]
version = read("string_version_001.json")
check("all three STRING mapping records retained", len(mapping) == 3)
by_query = {r["queryItem"]: r for r in mapping}
check("BioY query maps to declared reference locus", by_query["bioY"]["stringId"] == "272942.RCAP_rcc03249")
check("BioN query maps to declared reference locus", by_query["bioN"]["stringId"] == "272942.RCAP_rcc03250")
check("BioN alternate display name retained", by_query["bioN"]["preferredName"] == "cbiQ3")
check("third mapping retained but excluded from pair", by_query["bioM"]["stringId"] == "272942.RCAP_rcc03251")
check("exact request returns one row", len(exact) == 1)
row = exact[0]
check("exact returned pair agrees with mapped entities", {row["stringId_A"], row["stringId_B"]} == pair)
check("returned taxon agrees", str(row["ncbiTaxonId"]) == "272942")
check("neighborhood is .844", row["nscore"] == Decimal(".844"))
check("combined is .999 and differs from neighborhood", row["score"] == Decimal(".999") and row["score"] != row["nscore"])
check("all 44 initial rows retained", len(expanded) == 44)
same_pair = [(i, r) for i, r in enumerate(expanded)
             if {r["stringId_A"], r["stringId_B"]} == pair]
check("one representation of selected pair in initial response", len(same_pair) == 1)
check("initial selected row is 34 and equals exact response", same_pair[0] == (34, row))
check("version endpoint reports 12.5", version == [{"string_version": "12.5", "stable_address": "https://version-12-5.string-db.org"}])
check("restricted UniProt query returned two records", len(uniprot) == 2)
by_accession = {r["primaryAccession"]: r for r in uniprot}
for accession, gene, locus in (
    ("D5ARG8", "bioY", "RCAP_rcc03249"),
    ("D5ARG9", "bioN", "RCAP_rcc03250"),
):
    record = by_accession[accession]
    gene_record = record["genes"][0]
    check(f"{accession} names the expected gene", gene_record["geneName"]["value"] == gene)
    check(f"{accession} includes exact locus", locus in {x["value"] for x in gene_record["orderedLocusNames"]})
    check(f"{accession} names SB1003 and taxon 272942", "SB1003" in record["organism"]["scientificName"] and record["organism"]["taxonId"] == 272942)
    check(f"{accession} cross-links exact STRING entity", "272942." + locus in {x["id"] for x in record["uniProtKBCrossReferences"] if x["database"] == "STRING"})
check("BioN cbiQ3 alias is explicit in UniProt", "cbiQ3" in {x["value"] for x in by_accession["D5ARG9"]["genes"][0]["synonyms"]})

s = Fraction(row["nscore"])
d = w = Fraction(1)
t = d * s
S = w * max(t, 0)
O = w * max(-t, 0)
c = S * (1 - O)
check("one-question BioY compilation is 211/250", (t, S, O, c) == (Fraction(211, 250), Fraction(211, 250), 0, Fraction(211, 250)))
ribk_s = Fraction(956, 1000)  # Parent-verified inherited comparator, not a new query.
ribk_combined = Fraction(959, 1000)
bioy_combined = Fraction(row["score"])
neighborhood_difference = ribk_s - s
combined_difference = bioy_combined - ribk_combined
check("neighborhood descriptive difference is 14/125", neighborhood_difference == Fraction(14, 125))
check("combined descriptive difference is 1/25", combined_difference == Fraction(1, 25))
check("numeric ordering reverses across excluded combined channel", ribk_s > s and bioy_combined > ribk_combined)

source = "string_bioy_bion_network_002.json#/0/nscore"
formula = "../a103_complete_deliverable_023/NUMERICAL_SHEET.md#the-numerical-sheet"
not_applicable = lambda: cell(None, "fraction", "proposed_policy", [], formula,
                             state="not_applicable", missing_reason="not_this_route",
                             calibration="not_applicable")
score_cell = cell(s, "fraction", "dataset_observed", [source], "identity")
t_cell = cell(t, "signed_index", "proposed_policy", [source, "direction=+1"], "t=d*s")
question = {
    "question_ref": "bioy_bion_reference_neighborhood",
    "scope_ref": "Rhodobacter_capsulatus_SB1003_reference_loci",
    "metric_route": "native_neighborhood_score",
    "metric_selection_basis": "specified_native_channel",
    "predicate": {
        "relation": "native_neighborhood_association",
        "subject_ref": "272942.RCAP_rcc03249",
        "anchor_or_module_ref": "272942.RCAP_rcc03250",
        "expected_pattern_ref": "FILLED_CONTRAST.md#what-was-investigated",
        "direction_evidence_ref": "SOURCE_AND_IDENTITY_TRACE.md#published-bioy-case-inspected-scope-and-denominator-diagnosis",
        "spatial_rule": None,
    },
    "native": {
        "program": "STRING", "program_version": "12.5_observed_same_session",
        "database_version": "12.5_observed_same_session",
        "definition_ref": "https://string-db.org/help/api/#retrieving-interaction-network",
        "pair_ids": sorted(pair), "taxon_ref": "ncbitaxon:272942",
        "target_mapping_status": "exact_scored_entity",
        "mapping_evidence_refs": ["string_bioy_mapping_001.json", "uniprot_locus_aliases_001.json"],
        "channel": "neighborhood", "field_name": "nscore", "raw_value": num(s),
        "raw_scale": "unit_interval", "score": score_cell,
        "direction": "supports_context_predicate",
        "direction_evidence_ref": "FILLED_CONTRAST.md#what-was-investigated",
        "calibration_endpoint": "functional_association", "calibration_population_ref": None,
        "included_evidence": {"direct": None, "transferred": None, "source_genome_refs": None},
        "retrieval": {
            "record_ref": "string_bioy_bion_network_002.json#/0",
            "timestamp": "request_manifest.json#network_002.response_saved_utc",
            "network_type": "functional", "cutoff": 0, "limit": None,
            "returned_rows": 1, "selected_pair_rows": 1, "truncated": False,
        },
        "auxiliary_channel_values": [
            {"field_name": key, "raw_value": num(Fraction(row[key])), "units": "unit_interval",
             "source_ref": "string_bioy_bion_network_002.json#/0/" + key}
            for key in ("score", "fscore", "pscore", "ascore", "escore", "dscore", "tscore")
        ],
    },
}
result = {
    "axis_id": "A103", "sheet_version": "a103_complete_deliverable_023",
    "candidate_ref": "BioY_BioN_reference_neighborhood_association",
    "context_predicate_refs": [question["question_ref"]],
    "question_results": [{
        "question_ref": question["question_ref"], "weight": 1,
        "metric_route": "native_neighborhood_score", "C": not_applicable(),
        "E": not_applicable(), "t": t_cell, "native_score": score_cell,
        "stratum_results": [],
    }],
    "supporting_total": cell(S, "fraction", "proposed_policy", ["t", "w=1"], "sum(w*max(t,0))"),
    "opposing_total": cell(O, "fraction", "proposed_policy", ["t", "w=1"], "sum(w*max(-t,0))"),
    "coordinate": cell(c, "fraction", "proposed_policy", ["S", "O"], "S*(1-O)"),
    "projection_status": "point", "calibration_status": "support_index_not_exact_function_probability",
    "missing_input_paths": [], "failures": [], "duplicate_observation_refs": ["string_bioy_bion_network_001.json#/34"],
    "excluded_member_refs": [], "dependency_question_refs": [],
    "source_component_links": [{
        "source_ref": "string_bioy_bion_network_002.json", "locator_ref": "#/0/nscore",
        "component_paths": ["native.score", "t", "supporting_total", "coordinate"],
        "coverage": "own_dated_native_result_read",
    }], "scenario_results": [],
}
unknowns = {
    "historical_BioY_count_route": {
        "C": cell(None, "fraction", "proposed_policy", [], formula, bounds=(0, 1), missing_reason="not_reported"),
        "E": cell(None, "signed_index", "proposed_policy", [], formula, bounds=(-1, 1), missing_reason="not_reported"),
        "t": cell(None, "signed_index", "proposed_policy", [], formula, bounds=(-1, 1), missing_reason="not_reported"),
        "coordinate": cell(None, "fraction", "proposed_policy", [], formula, bounds=(0, 1), missing_reason="not_reported"),
    },
    "unmapped_supplied_target_coordinate": cell(None, "fraction", "proposed_policy", [], formula,
                                                bounds=(0, 1), missing_reason="unmapped_target"),
    "biological_calibration_interval": None,
    "historical_assayed_construct_sequence_identity": None,
}
artifact = {
    "artifact_kind": "research_filled_reference_example_not_production_input",
    "context_questions": [question], "result": result,
    "separate_unknowns_not_used_as_zero": unknowns,
    "scope": "Exact reference pair only; no supplied target material or assayed construct was mapped.",
}
(ROOT / "filled_cells.json").write_text(json.dumps(artifact, indent=2) + "\n")
input_files = ["string_bioy_mapping_001.json", "string_bioy_bion_network_001.json", "string_bioy_bion_network_002.json", "string_version_001.json", "uniprot_locus_aliases_001.json"]
receipt = {
    "executed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "checks_passed": len(CHECKS), "checks": CHECKS,
    "input_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in input_files},
    "native_score_fraction": str(s), "t": str(t), "S": str(S), "O": str(O), "c": str(c),
    "neighborhood_difference": str(neighborhood_difference),
    "combined_difference": str(combined_difference),
    "limits": ["No production code or reader invoked.", "RibK values inherited, not freshly verified.",
               "No biological calibration, independent replication or assayed-construct identity established.",
               "No supplied sequence/snippet/ybhP mapping performed."]
}
(ROOT / "arithmetic_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"checks_passed": len(CHECKS), "t": str(t), "S": str(S), "O": str(O), "c": str(c),
                  "neighborhood_difference": str(neighborhood_difference), "combined_difference": str(combined_difference)}))
