"""Synthetic arithmetic/counterexamples; no remote calls or database execution."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.blast_database_grader import (
    build_database_sheet, calculate_database_probabilities,
)


def hsp(score=10, *, query_start=1, qseq="ACDEF", hseq="ACDEF"):
    return {"bit_score": score, "score": score * 2, "evalue": 0.01,
        "query_from": query_start, "query_to": query_start + len(qseq.replace("-", "")) - 1,
        "hit_from": 1, "hit_to": len(hseq.replace("-", "")), "align_len": len(qseq),
        "identity": sum(a == b and a != "-" for a, b in zip(qseq, hseq)),
        "gaps": qseq.count("-") + hseq.count("-"), "qseq": qseq, "hseq": hseq}


def hit(index, accession, score=10, taxid=562):
    return {"hit_index": index, "length": 10,
        "descriptions": [{"accession": accession, "title": "A reported protein title", "taxid": taxid}],
        "unpaired_metadata": {}, "hsps": [hsp(score)]}


def result(hits=None, **request):
    hits = hits if hits is not None else [hit(0, "A", 10), hit(1, "B", 9)]
    return {"schema": "blast_normalized_result_v1", "mode": "database", "resource": "api",
        "format": "json2", "query": {"id": "synthetic_query", "title": None, "length": 10},
        "search": {"program": "blastp", "version": "synthetic", "database": "synthetic_db",
            "parameters": {}, "statistics": {}, "request": request,
            "hit_array_present": True, "reported_hit_count": len(hits)},
        "hits": hits, "native": {"synthetic": True}, "issues": []}


def metadata(accession, function, taxid=562, *, sequence_group=None):
    return {"accession": accession, "taxid": taxid,
        "functions": [{"function": function, "label": function, "evidence": ["source_reported"],
                       "source": "synthetic_metadata"}],
        "lineage": [{"taxid": 2, "rank": "superkingdom", "name": "Bacteria"},
                    {"taxid": 561, "rank": "genus", "name": "Escherichia"},
                    {"taxid": taxid, "rank": "species", "name": "fixture_species"}],
        "source": "synthetic_metadata", "origin": {"sample_type": "cultured_isolate"},
        "assembly": {}, "sequence_group": sequence_group, "study_groups": []}


def profile(**changes):
    value = {"database": "synthetic_db", "release": None, "source": "synthetic_db_census",
        "count_unit": "unique_sequences", "total_count": 1000,
        "function_counts": {"F": 200, "G": 50}, "scope": "searched_database"}
    value.update(changes)
    return value


def test_native_measurements_and_inputs_preserved_without_mutation():
    native = result()
    rows = [metadata("A", "F"), metadata("B", "G")]
    before = deepcopy((native, rows))
    sheet = build_database_sheet(native, reference_metadata=rows)
    assert (native, rows) == before
    assert sheet["normalized_result"] == native
    assert sheet["reference_metadata"] == rows
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] == 0.5
    assert sheet["hits"][0]["measurements"]["reference_paired_coverage"] == 0.5
    assert sheet["hits"][0]["measurements"]["identical_unique_pair_count"] == 5
    assert sheet["hits"][0]["hsp_components"][0]["native_scores"]["bit_score"] == 10
    assert sheet["coverage"]["matched_metadata_row_count"] == 2
    assert json.loads(json.dumps(sheet, allow_nan=False))["schema"] == "blast_database_sheet_v1"


def test_hand_calculated_probabilities_and_database_representation():
    native = result([hit(0, "A", 10), hit(1, "B", 9), hit(2, "C", 10)])
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G"),
        metadata("C", "F")], database_profile=profile())
    scored = calculate_database_probabilities(sheet)
    assert scored["function_masses"] == {"F": 2, "G": 0.5}
    assert scored["unadjusted_probabilities"] == {"F": 0.8, "G": 0.2}
    assert scored["representation_adjusted_probabilities"] == {"F": 0.5, "G": 0.5}
    assert scored["calibrated_annotation_probability"] is False
    assert sheet["database_representation"]["available_for_adjustment"]
    assert "taxonomy" in scored["retained_measurements_not_used_by_this_model"]


def test_repeated_aliases_and_duplicate_hsps_do_not_create_votes():
    rows = [metadata("A", "F"), metadata("B", "G")]
    base = build_database_sheet(result(), reference_metadata=rows)
    repeated = result()
    repeated["hits"][0]["descriptions"] *= 3
    repeated["hits"][0]["hsps"] *= 4
    other = build_database_sheet(repeated, reference_metadata=rows * 2)
    assert calculate_database_probabilities(other)["unadjusted_probabilities"] == calculate_database_probabilities(base)["unadjusted_probabilities"]
    assert other["hits"][0]["measurements"]["query_paired_coverage"] == 0.5
    assert other["hits"][0]["measurements"]["overlap_pair_representations"] == 15


def test_same_accession_across_hits_collapses_but_same_local_alignment_does_not():
    rows = [metadata("A", "F"), metadata("B", "G")]
    base = build_database_sheet(result(), reference_metadata=rows)
    duplicate = build_database_sheet(result([hit(0, "A", 10), hit(1, "B", 9), hit(2, "A", 10)]), reference_metadata=rows)
    assert duplicate["dependence"]["duplicate_native_hit_count"] == 1
    assert calculate_database_probabilities(base)["unadjusted_probabilities"] == calculate_database_probabilities(duplicate)["unadjusted_probabilities"]
    assert base["dependence"]["group_count"] == 2
    assert base["dependence"]["unknown_cross_hit_sequence_identity"] is True


def test_explicit_sequence_groups_merge_distinct_accessions():
    sheet = build_database_sheet(result([hit(0, "A"), hit(1, "A_alias"), hit(2, "B", 9)]),
        reference_metadata=[metadata("A", "F", sequence_group="same_complete_sequence"),
                            metadata("A_alias", "F", sequence_group="same_complete_sequence"),
                            metadata("B", "G", sequence_group="other_complete_sequence")])
    assert len(sheet["sequence_groups"]) == 2
    assert sheet["dependence"]["unknown_cross_hit_sequence_identity"] is False
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"]["F"] == pytest.approx(2/3)


def test_each_alias_keeps_its_function_and_taxon_association():
    native = result([hit(0, "A")])
    native["hits"][0]["descriptions"].append({"accession": "ARCH", "title": "Another assignment", "taxid": 2157})
    archaea = metadata("ARCH", "G", 2157)
    archaea["lineage"] = [{"taxid": 2157, "rank": "superkingdom", "name": "Archaea"}]
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), archaea])
    assert len(sheet["sequence_groups"]) == 1
    assert sheet["sequence_groups"][0]["functions"] == ["F", "G"]
    by_function = {row["function"]: row for row in sheet["functions"]}
    assert [row["taxid"] for row in by_function["F"]["taxonomy"]["taxa"]] == [562]
    assert [row["taxid"] for row in by_function["G"]["taxonomy"]["taxa"]] == [2157]
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] == {"F": 0.5, "G": 0.5}


def test_metadata_taxon_conflicts_remain_unmatched_not_overwritten():
    wrong = metadata("A", "G", 2157)
    sheet = build_database_sheet(result(), reference_metadata=[metadata("A", "F"), wrong])
    assert sheet["coverage"]["unmatched_metadata_indices"] == [1]
    assert sheet["hits"][0]["associations"][0]["taxid"] == 562
    assert [row["function"] for row in sheet["functions"]] == ["F"]
    assert any(row["code"] == "metadata_taxon_conflicts_with_native" for row in sheet["issues"])


def test_missing_native_taxon_can_be_populated_by_exact_accession_without_mixing_rows():
    native = result([hit(0, "A", taxid=None)])
    a, b = metadata("A", "F", 562), metadata("A", "G", 2157)
    sheet = build_database_sheet(native, reference_metadata=[a, b])
    assert [(row["taxid"], row["functions"][0]["function"]) for row in sheet["hits"][0]["associations"]] == [(562, "F"), (2157, "G")]


def test_unpaired_tabular_taxonomy_not_guessed_and_titles_not_interpreted():
    native = result([hit(0, "A", taxid=None)])
    native["hits"][0]["unpaired_metadata"] = {"staxids": [562, 2157], "sallacc": ["A", "B"]}
    sheet = build_database_sheet(native)
    assert sheet["hits"][0]["unpaired_metadata"] == native["hits"][0]["unpaired_metadata"]
    assert sheet["functions"] == []
    assert sheet["taxonomy"]["taxa"] == []
    scored = calculate_database_probabilities(sheet)
    assert scored["unadjusted_probabilities"] is None
    assert scored["unannotated_reference_kernel_fraction"] == 1


def test_taxonomic_consistency_counts_and_independent_target_context():
    native = result([hit(0, "A"), hit(1, "B"), hit(2, "C", taxid=2157)])
    rows = [metadata("A", "F"), metadata("B", "F"), metadata("C", "F", 2157)]
    rows[-1]["lineage"] = [{"taxid": 2157, "rank": "superkingdom", "name": "Archaea"}]
    target = {"taxid": 562, "lineage": rows[0]["lineage"], "source": "synthetic_independent_target",
              "independent_of_search": True}
    sheet = build_database_sheet(native, reference_metadata=rows, target_context=target)
    rank = next(row for row in sheet["taxonomy"]["ranks"] if row["rank"] == "superkingdom")
    assert rank["same_taxon_pair_count"] == 1
    assert rank["comparable_pair_count"] == 3
    assert rank["same_taxon_pair_fraction"] == pytest.approx(1/3)
    assert rank["target_matching_groups"] == 2
    assert rank["target_conflicting_groups"] == 1
    assert rank["target_matching_fraction"] == pytest.approx(2/3)
    assert sheet["taxonomy"]["target_independent_of_search"] is True
    # A target taxon inferred from these hits stays tagged dependent. It does
    # not change this initial kernel model or become an independent prior.
    target["independent_of_search"] = False
    dependent = build_database_sheet(native, reference_metadata=rows, target_context=target)
    assert not dependent["taxonomy"]["target_independent_of_search"]
    assert calculate_database_probabilities(sheet) == calculate_database_probabilities(dependent)


def test_quality_retains_actual_zero_and_contamination_above_one():
    rows = [metadata("A", "F"), metadata("B", "G")]
    rows[0]["assembly"] = {"accession": "ASM_A", "assembly_level": "Complete Genome",
        "completeness_fraction": 0.0, "contamination_fraction": 1.2,
        "quality_method": "CheckM", "contig_count": 1, "contig_n50": 1000}
    rows[1]["assembly"] = {"accession": "ASM_B", "completeness_fraction": 0.95,
        "contamination_fraction": 0.02, "quality_method": "CheckM"}
    sheet = build_database_sheet(result(), reference_metadata=rows)
    quality = sheet["hits"][0]["associations"][0]["quality_measurements"]
    assert quality["completeness_fraction"] == 0
    assert quality["contamination_fraction"] == 1.2
    assert quality["total_sequence_length"] is None
    completeness = next(row for row in sheet["source_quality"]["numerical_summaries"] if row["field"] == "completeness_fraction")
    assert completeness["mean"] == pytest.approx(0.475)
    assert not any(row["code"] == "assembly_measurement_invalid" for row in sheet["issues"])


@pytest.mark.parametrize("changes,reason", [
    ({"count_unit": "accessions"}, "database_profile_requires_sequence_count_unit"),
    ({"database": "other_database"}, "database_profile_identity_mismatch"),
    ({"release": "2026-10-24"}, "database_profile_release_unmatched"),
    ({"scope": "all_taxa_before_query_filter"}, "database_profile_scope_mismatch"),
    ({"function_counts": {"F": 0, "G": 50}}, "database_function_count_below_observed_groups:F"),
])
def test_incompatible_database_profile_cannot_adjust(changes, reason):
    sheet = build_database_sheet(result(), reference_metadata=[metadata("A", "F"), metadata("B", "G")],
                                 database_profile=profile(**changes))
    scored = calculate_database_probabilities(sheet)
    assert scored["unadjusted_probabilities"] is not None
    assert scored["representation_adjusted_probabilities"] is None
    assert reason in scored["representation_adjustment_unavailable_reasons"]


def test_exact_release_and_scope_can_be_matched():
    sheet = build_database_sheet(result(database_release="release1", database_scope="bacteria_only"),
        reference_metadata=[metadata("A", "F"), metadata("B", "G")],
        database_profile=profile(release="release1", scope="bacteria_only"))
    assert sheet["database_representation"]["available_for_adjustment"]


def test_missing_profile_and_censored_hits_remain_explicit():
    sheet = build_database_sheet(result(hitlist_size=2), reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    scored = calculate_database_probabilities(sheet)
    assert sheet["search_limits"]["limit_reached"] is True
    assert sheet["search_limits"]["whole_database_result_complete"] is None
    assert scored["representation_adjusted_probabilities"] is None
    assert "database_profile_not_supplied" in scored["representation_adjustment_unavailable_reasons"]


def test_unknown_traceback_does_not_become_endpoint_span_coverage():
    native = result()
    for row in native["hits"]:
        row["hsps"][0].pop("qseq")
        row["hsps"][0].pop("hseq")
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    assert sheet["hits"][0]["measurements"]["query_paired_coverage"] is None
    assert sheet["hits"][0]["measurements"]["reference_paired_coverage"] is None
    assert sheet["hits"][0]["measurements"]["maximum_bit_score"] == 10


def test_empty_and_missing_hit_array_distinct():
    native = result([])
    sheet = build_database_sheet(native)
    assert sheet["search_limits"]["hit_array_present"] is True
    assert calculate_database_probabilities(sheet)["unadjusted_probabilities"] is None
    native["search"]["hit_array_present"] = False
    native["search"]["reported_hit_count"] = None
    other = build_database_sheet(native)
    assert other["search_limits"]["hit_array_present"] is False
    assert other["search_limits"]["reported_hit_count"] is None


def test_replaceable_temperature_and_priors_recalculate_without_mutating_sheet():
    sheet = build_database_sheet(result(), reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    saved = deepcopy(sheet)
    ordinary = calculate_database_probabilities(sheet)
    changed = calculate_database_probabilities(sheet, model={"temperature_bits": 2, "function_priors": {"F": 0.25, "G": 0.75}})
    assert ordinary["unadjusted_probabilities"]["F"] == pytest.approx(2/3)
    assert changed["unadjusted_probabilities"]["F"] == pytest.approx(0.25/(0.25+0.75/(2**0.5)))
    assert sheet == saved


@pytest.mark.parametrize("model", [{"temperature_bits": 0}, {"temperature_bits": True},
    {"function_priors": {"F": 1}}, {"unknown_weight": 1}, {"function_priors": {"F": -1, "G": 1}}])
def test_invalid_model_parameters_rejected(model):
    sheet = build_database_sheet(result(), reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    with pytest.raises(ValueError):
        calculate_database_probabilities(sheet, model=model)


def test_invalid_mode_and_nonfinite_input_rejected():
    native = result()
    native["mode"] = "pairwise"
    with pytest.raises(ValueError, match="database_blast_mode_required"):
        build_database_sheet(native)
    native["mode"] = "database"
    native["hits"][0]["hsps"][0]["bit_score"] = float("nan")
    with pytest.raises(ValueError):
        build_database_sheet(native)


def test_conflicting_taxa_cannot_silently_merge_same_accession():
    sheet = build_database_sheet(result([hit(0, "A", taxid=562), hit(1, "A", taxid=2157)]),
        reference_metadata=[metadata("A", "F", 562), metadata("A", "G", 2157)])
    assert len(sheet["sequence_groups"]) == 2
    assert any(row["code"] == "sequence_identity_conflict" for row in sheet["issues"])


def test_missing_identity_cannot_bridge_conflicting_full_sequence_groups():
    # Hit B has an alias shared with each side. Transitive union must not hide
    # the conflict between the actual complete-sequence identities at the ends.
    native = result([hit(0, "A"), hit(1, "BRIDGE"), hit(2, "C")])
    native["hits"][0]["descriptions"].append({"accession": "LEFT_ALIAS", "taxid": 562})
    native["hits"][1]["descriptions"].extend([{"accession": "LEFT_ALIAS", "taxid": 562},
                                             {"accession": "RIGHT_ALIAS", "taxid": 562}])
    native["hits"][2]["descriptions"].append({"accession": "RIGHT_ALIAS", "taxid": 562})
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F", sequence_group="full_1"),
        metadata("C", "G", sequence_group="full_2")])
    assert len(sheet["sequence_groups"]) == 2
    assert any(row["code"] == "sequence_identity_conflict" for row in sheet["issues"])


def test_missing_score_is_not_a_zero_probability():
    native = result()
    native["hits"][0]["hsps"][0].pop("bit_score")
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    scored = calculate_database_probabilities(sheet)
    assert scored["functions_without_measured_bit_scores"] == ["F"]
    assert scored["unadjusted_probabilities"] == {"G": 1.0}
    assert scored["unscored_sequence_group_count"] == 1


def test_strong_unannotated_hit_does_not_underflow_known_function_comparison():
    native = result([hit(0, "A", 10), hit(1, "B", 9), hit(2, "NO_FUNCTION", 10000)])
    sheet = build_database_sheet(native, reference_metadata=[metadata("A", "F"), metadata("B", "G")])
    scored = calculate_database_probabilities(sheet)
    assert scored["unadjusted_probabilities"] == {"F": pytest.approx(2/3), "G": pytest.approx(1/3)}
    assert scored["unannotated_reference_kernel_fraction"] == 1.0
    assert scored["largest_group_bit_score"] == 10000
    assert scored["largest_scored_function_group_bit_score"] == 10


def test_ambiguous_target_lineage_is_retained_without_last_row_wins():
    target = {"lineage": [{"taxid": 2, "rank": "superkingdom", "name": "Bacteria"},
                           {"taxid": 2157, "rank": "superkingdom", "name": "Archaea"}],
              "independent_of_search": True}
    sheet = build_database_sheet(result(), reference_metadata=[metadata("A", "F")], target_context=target)
    assert sheet["taxonomy"]["ambiguous_target_ranks"] == [{"rank": "superkingdom", "taxids": [2, 2157]}]
    rank = next(row for row in sheet["taxonomy"]["ranks"] if row["rank"] == "superkingdom")
    assert rank["target_taxid_at_rank"] is None
    assert rank["target_matching_fraction"] is None
