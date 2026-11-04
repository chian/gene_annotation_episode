"""338 arithmetic oracles using actual 342 population and saved validation.

All reports and source/census records here are synthetic. No database search,
network acquisition, model call or episode-return integration is claimed.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_vdb_function_calculators as calculator
from gene_annotation_episode import blast_vdb_function_inputs as inputs_module
from gene_annotation_episode import blast_vdb_inputs as v1
from gene_annotation_episode import blast_vdb_calculators as base
from test_blast_vdb_function_inputs import (
    whole_case, translated_case, feature_case, populate, census_for, explicit,
    function, collect, inputs, hsp, identity, provenance, sequence, feature,
    metadata, entity,
)


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001"


def model(*, temperature=1, grouping="target_duplicates_only", unknown="qualify_separate", priors=None, census=None, scope="whole_sequence", namespace="fixture_function"):
    return dict(version="vdb_function_kernel_v1", temperature_bits=temperature, grouping_model=grouping,
        unknown_source_dependency=unknown, function_priors=priors,
        census_selection=[] if census is None else [dict(assignment_scope=scope, namespace=namespace, census_key=census)])


def rows(result, scope="whole_sequence", namespace="fixture_function"):
    stratum = next(s for s in result["strata"] if s["assignment_scope"] == scope and s["namespace"] == namespace)
    return stratum, {r["function"]["value"]: r for r in stratum["functions"]}


def calculate(sheet, **kwargs):
    return calculator.calculate_blast_vdb_function_components(sheet, model=model(**kwargs))


def sample_memberships(values, samples):
    for i, sample in enumerate(samples):
        values["member_bindings"][i]["sample_key"] = sample
        values["dataset_records"][i]["sample_links"][0].update(sample_key=sample, sample_identifier=identity(sample, "sample"))
        meta = next(m for m in values["reference_metadata"] if m["metadata_key"] == f"sample{i}")
        meta["entity"]["sample_key"] = sample
        meta["identifiers"] = [identity(sample, "sample")]


def case(scores=(20, 20, 20), labels=("A", "B", "A"), *, symbols=None, samples=None):
    symbols = symbols or ["ACGTACGT", "ACGTTCGT", "ACGTGCGT", "ACGTTTGT"][:len(scores)]
    hits = [dict(len=len(s), description=[dict(id=f"m{i}", accession=f"m{i}")], hsps=[hsp(r=s, bit_score=score)])
            for i, (s, score) in enumerate(zip(symbols, scores))]
    values = inputs(collect(hits=hits)["searches"][0], symbols=symbols)
    assignments = [explicit(values, i, label) for i, label in enumerate(labels) if label is not None]
    if samples is not None:
        sample_memberships(values, samples)
    return values, assignments


def with_census(values, assignments, census=None):
    first = populate(values, assignments)
    census = census or census_for(first)
    return populate(values, assignments, censuses=[census])


def add_census_entity(census, template, *, key, sample, symbols=None, label=None):
    row = deepcopy(template)
    row["entity_key"] = key
    row["address"]["member_key"]["member_identifier"] = identity(key)
    row["origin_sample_keys"] = [sample]
    row["sample_relation_status"] = "available"
    if label is not None:
        row["functions"] = [function(label)]
    if symbols is None:
        proof = next(p for p in census["identity_proofs"] if p["entity_key"] == template["entity_key"])
        symbols = proof["symbols"]
    seq = sequence(symbols)
    row["target_identity"].update(sha256=seq["sha256"], length=seq["length"])
    row["parent_sequence_identity"] = {k: seq[k] for k in ("molecule", "sha256", "length")}
    census["entities"].append(row)
    census["identity_proofs"].append(dict(entity_key=key, sequence_source=census["source"], linkage_source=census["source"],
        normalization="full_member_nt_v1", symbols=symbols))
    census["enumeration"]["reported_total"] += 1


def bridge_case():
    values, assignments = case(labels=("A", "B", "C"), samples=("S1", "S2", "S3"))
    census = census_for(populate(values, assignments), extra=False)
    add_census_entity(census, census["entities"][0], key="unreturned-a-in-s2", sample="S2")
    add_census_entity(census, census["entities"][0], key="other-a-target", sample="S4", symbols="AACGTACG")
    return with_census(values, assignments, census)


def assert_weights(result, expected, field="conditional_function_weight", **kwargs):
    stratum, by_function = rows(result, **kwargs)
    assert set(by_function) == set(expected)
    for key, value in expected.items():
        assert by_function[key][field]["value"] == pytest.approx(value, abs=1e-14)
    return stratum, by_function


@pytest.mark.parametrize("temperature,p,c", [(1, (4/5, 1/5), (1/2, 1/2)), (2, (2/3, 1/3), (1/3, 2/3))])
def test_frozen_whole_populator_fixture_exact_weights_and_census(temperature, p, c):
    sheet = json.loads((FROZEN / "whole_sequence.json").read_text())
    original = deepcopy(sheet)
    result = calculate(sheet, temperature=temperature, census=sheet["census_records"][0]["census_key"])
    stratum, f = assert_weights(result, dict(zip(("A", "B"), p)))
    assert_weights(result, dict(zip(("A", "B"), c)), "representation_adjusted_function_weight")
    assert stratum["counts"] == dict(source_entities=3, eligible_entities=3, excluded_entities=0, eligible_hsps=4,
        duplicate_target_units=2, model_groups=2, multilabel_target_units=0, unassigned_target_units=0,
        unscored_entities=0, unknown_origin_subjects=0, unresolved_sample_entities=0)
    assert result["status"] == stratum["status"] == "complete"
    assert stratum["report_complete"] and stratum["metadata_complete"]
    assert f["A"]["function_mass"]["value"] == 1
    assert f["B"]["function_mass"]["value"] == 2 ** (-2/temperature)
    assert f["A"]["census_function_unit_count"]["value"] == 4
    assert f["B"]["census_function_unit_count"]["value"] == 1
    assert f["A"]["census_total_unit_count"]["value"] == 5
    assert result["census_results"][0]["base_entity_count"]["value"] == 6
    assert not result["calibrated_annotation_probability"] and sheet == original
    assert sheet["base_components"]["population_components"]["function_weight_model"]["reason"] == "vdb_function_weight_model_not_defined"
    assert result["model"]["temperature_bits"] == temperature


def test_optional_source_cap_retains_three_distinct_targets_and_changes_budget():
    values, assignments = case(samples=("S1", "S1", "S2"))
    sheet = populate(values, assignments)
    a, af = assert_weights(calculate(sheet), {"A": 2/3, "B": 1/3})
    result = calculate(sheet, grouping="known_source_blocks")
    b, bf = assert_weights(result, {"A": 3/4, "B": 1/4})
    assert a["counts"]["duplicate_target_units"] == b["counts"]["duplicate_target_units"] == 3
    assert a["counts"]["model_groups"] == 3 and b["counts"]["model_groups"] == 2
    assert af["A"]["function_mass"]["value"] == 2
    assert bf["A"]["function_mass"]["value"] == pytest.approx(1.5)
    assert bf["B"]["function_mass"]["value"] == pytest.approx(0.5)
    assert all(e["used_by_model"] for e in result["dependency_measurements"]["edges"])
    assert all(not e["used_by_model"] for e in calculate(sheet)["dependency_measurements"]["edges"])
    assert "source_block_mass_cap" in result["assumptions"]


def test_full_census_bridge_repartitions_only_actual_observations():
    sheet = bridge_case()
    result = calculate(sheet, grouping="known_source_blocks", census=sheet["census_records"][0]["census_key"])
    _, f = assert_weights(result, {"A": 1/3, "B": 1/3, "C": 1/3})
    assert_weights(result, {"A": 1/7, "B": 2/7, "C": 4/7}, "representation_adjusted_function_weight")
    assert [f[k]["function_mass"]["value"] for k in "ABC"] == [1, 1, 1]
    assert [f[k]["census_partition_function_mass"]["value"] for k in "ABC"] == [0.5, 0.5, 1]
    assert [f[k]["census_function_unit_count"]["value"] for k in "ABC"] == [2, 1, 1]
    assert all(f[k]["census_function_unit_count"]["unit"] == "dependence_block" for k in "ABC")
    assert all(f[k]["representation_rate"]["unit"] == "function_mass_per_dependence_block" for k in "ABC")
    assert [f[k]["representation_rate"]["value"] for k in "ABC"] == pytest.approx([1/12, 1/6, 1/3])
    c = result["census_results"][0]
    assert c["model_group_count"]["value"] == 3 and c["base_entity_count"]["value"] == 5
    assert len(c["observed_entity_links"]) == 3
    assert len(sheet["base_components"]["hsps"]) == 3
    assert any(set(g["entity_keys"]) >= {"unreturned-a-in-s2"} for g in c["model_groups"])


@pytest.mark.parametrize("fixture", ["translated_features.json", "translated_siblings.json"])
def test_opposite_strand_feature_duplicates_and_own_qualified_maxima(fixture):
    sheet = json.loads((FROZEN / fixture).read_text())
    result = calculate(sheet, temperature=2)
    stratum, f = assert_weights(result, {"A": 2/3, "B": 1/3}, scope="feature")
    assert stratum["counts"]["source_entities"] == 3
    assert stratum["counts"]["duplicate_target_units"] == 2
    assert f["A"]["source_entity_count"] == 2 and f["A"]["target_unit_count"] == 1
    assert f["A"]["function_mass"]["value"] == 1
    native = [o["native_bit_score"]["value"] for o in sheet["observations"] if o["function"] is not None]
    if fixture == "translated_siblings.json":
        assert 40 in native and 50 in native
        contribution = next(c for g in stratum["groups"] for c in g["function_contributions"] if c["function"] == function("A"))
        assert contribution["best_bit_score"]["value"] == 30
        assert len(contribution["observation_keys"]) == 5
        assert stratum["status"] == "partial"


def conflicting_feature_case(destination):
    original = json.loads((FROZEN / "translated_features.json").read_text())
    declaration = deepcopy(original["assignment_records"][0])
    if destination == "missing_feature":
        declaration["target"]["feature_identifier"]["value"] = "different-feature"
    else:
        declaration["target"] = deepcopy(original["assignment_records"][1]["target"])
    return inputs_module.populate_blast_vdb_function_sheet(original["base_sheet"],
        supplied_assignments=[declaration], dependency_records=[], census_records=[])


@pytest.mark.parametrize("destination", ["missing_feature", "other_bound_feature"])
def test_cross_entity_assignment_conflict_keeps_independent_scores_without_borrowing(destination):
    sheet = conflicting_feature_case(destination)
    before = deepcopy(sheet)
    result = calculate(sheet)
    stratum, f = assert_weights(result, {"A": 2/3, "B": 1/3}, scope="feature")
    # A's incompatible 30-bit instance remains retained but cannot supply
    # weight. The independent 29-bit A and 28-bit B observations remain usable.
    contribution = next(c for g in stratum["groups"] for c in g["function_contributions"] if c["function"] == function("A"))
    excluded = {o["observation_key"] for o in sheet["observations"] if o["qualification"] == "incompatible"}
    assert excluded and excluded.isdisjoint(contribution["winning_observation_keys"])
    assert contribution["best_bit_score"]["value"] == 29
    assert f["A"]["source_entity_count"] == f["B"]["source_entity_count"] == 1
    assert stratum["unknown_reference_kernel_fraction"]["value"] == 0
    assert stratum["status"] == "partial"
    assert result["assignment_results"] == [r for r in sheet["link_results"] if r["record_kind"] == "assignment"]
    assert sheet == before


def test_own_function_score_splitting_and_equal_multilabel_target():
    values, assignments = case(scores=(20, 18), labels=("A", "B"), samples=("S", "S"))
    result = calculate(populate(values, assignments), grouping="known_source_blocks")
    stratum, f = assert_weights(result, {"A": 4/5, "B": 1/5})
    contribution = {c["function"]["value"]: c for c in stratum["groups"][0]["function_contributions"]}
    assert contribution["B"]["best_bit_score"]["value"] == 18
    assert contribution["B"]["within_group_kernel"]["value"] == 0.25
    assert contribution["B"]["split_denominator"]["value"] == 1.25
    values, assignments = case(scores=(20,), labels=("A",))
    assignments.append(explicit(values, 0, "B"))
    stratum, _ = assert_weights(calculate(populate(values, assignments)), {"A": 0.5, "B": 0.5})
    assert stratum["counts"]["multilabel_target_units"] == 1


def test_census_literal_overlapping_functions_can_each_cover_the_same_unit():
    values, assignments = case(scores=(20,), labels=("A",))
    assignments.append(explicit(values, 0, "B"))
    census = census_for(populate(values, assignments), extra=False)
    result = calculate(with_census(values, assignments, census), census=census["census_key"])
    _, f = assert_weights(result, {"A": 0.5, "B": 0.5}, "representation_adjusted_function_weight")
    assert f["A"]["census_function_fraction"]["value"] == f["B"]["census_function_fraction"]["value"] == 1
    assert f["A"]["census_total_unit_count"]["value"] == f["B"]["census_total_unit_count"]["value"] == 1


def test_duplicate_and_repeated_lower_hsp_invariance_with_complete_associations():
    values, assignments = whole_case()
    first = calculate(populate(values, assignments))
    source = values["search"]["native"]["search"]
    hits = deepcopy(source["hits"])
    hits[0]["hsps"] += [hsp(bit_score=22), hsp(bit_score=0)]
    values2 = inputs(collect(hits=hits)["searches"][0], symbols=["ACGTACGT", "ACGTACGT", "ACGTTCGT"])
    assignments2 = [explicit(values2, 0), explicit(values2, 1), explicit(values2, 2, "B")]
    second = calculate(populate(values2, assignments2 + [deepcopy(assignments2[0])]))
    _, a = assert_weights(first, {"A": 0.8, "B": 0.2})
    b, bf = assert_weights(second, {"A": 0.8, "B": 0.2})
    assert a["A"]["function_mass"] == bf["A"]["function_mass"]
    contribution = next(c for g in b["groups"] for c in g["function_contributions"] if c["function"] == function("A"))
    assert len(contribution["winning_observation_keys"]) == 2
    assert len(contribution["observation_keys"]) == 5
    assert b["counts"]["eligible_hsps"] == 6


def test_input_order_invariance_without_rewriting_saved_source_order():
    values, assignments = whole_case()
    a = populate(values, assignments)
    b = populate(values, list(reversed(assignments)))
    ra, rb = calculate(a), calculate(b)
    assert ra["strata"] == rb["strata"]
    assert ra["dependency_measurements"] == rb["dependency_measurements"]
    assert a["assignment_records"] == list(reversed(b["assignment_records"]))


def test_unknown_mass_and_unannotated_duplicate_coverage_are_distinct():
    values, assignments = case(labels=("A", "B", None))
    stratum, _ = assert_weights(calculate(populate(values, assignments)), {"A": 0.5, "B": 0.5})
    assert stratum["unknown_reference_kernel_mass"]["value"] == 1
    assert stratum["assigned_reference_kernel_mass"]["value"] == 2
    assert stratum["unknown_reference_kernel_fraction"]["value"] == pytest.approx(1/3)
    assert stratum["counts"]["unassigned_target_units"] == 1
    values, assignments = case(labels=("A", "B", None), symbols=["ACGTACGT", "ACGTTCGT", "ACGTACGT"])
    result = calculate(populate(values, assignments)); stratum, _ = assert_weights(result, {"A": 0.5, "B": 0.5})
    assert stratum["unknown_reference_kernel_mass"]["value"] == 0
    assert stratum["unknown_reference_kernel_mass"]["linear_status"] == "zero"
    assert stratum["counts"]["unassigned_target_units"] == 0
    assert not stratum["metadata_complete"]
    assert any(len(u["entity_keys"]) == 2 for u in result["dependency_measurements"]["target_units"])
    assert any(i["code"] == "blast_vdb_function_assignment_namespace_unscored" for i in stratum["issues"])


@pytest.mark.parametrize("unknown", ["qualify_separate", "withhold_weights"])
def test_unknown_sample_relation_policy_is_explicit_and_baseline_ignores_it(unknown):
    values, assignments = case()
    values["member_bindings"][0]["sample_key"] = None
    values["dataset_records"][0]["sample_links"] = []
    sheet = populate(values, assignments)
    assert_weights(calculate(sheet, unknown=unknown), {"A": 2/3, "B": 1/3})
    result = calculate(sheet, grouping="known_source_blocks", unknown=unknown)
    stratum, f = rows(result)
    assert not stratum["dependency_complete"] and stratum["counts"]["unresolved_sample_entities"] == 1
    assert stratum["status"] == ("partial" if unknown == "qualify_separate" else "unavailable")
    if unknown == "withhold_weights":
        assert f["A"]["conditional_function_weight"]["value"] is None
        assert f["A"]["conditional_function_weight"]["reason_code"] == "blast_vdb_function_dependency_unknown"
    else:
        assert "unknown_dependency_separate" in result["assumptions"]


def test_explicit_dependency_edges_are_retained_and_used_only_when_selected():
    values, assignments = case(scores=(20, 18), labels=("A", "B"))
    sheet = populate(values, assignments)
    dependency = dict(dependency_key="original-library", relation="same_library", entities=[e["address"] for e in sheet["entities"]],
        sources=[provenance("/library", "synthetic:library")], native_record={"library": "L"})
    sheet = populate(values, assignments, dependencies=[dependency])
    result = calculate(sheet, grouping="known_source_blocks")
    stratum, _ = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert stratum["counts"]["model_groups"] == 1
    edge = next(e for e in result["dependency_measurements"]["edges"] if e["relation"] == "same_library")
    assert edge["sources"] == dependency["sources"] and edge["used_by_model"]
    assert rows(calculate(sheet))[0]["counts"]["model_groups"] == 2


def test_feature_parent_relation_does_not_merge_whole_and_feature_views():
    symbols = "A" * 30 + "C" * 10
    hits = [dict(len=40, description=[dict(id="contig", accession="contig")], hsps=[
        hsp("AAAAAA", hit_from=13, hit_to=18, bit_score=18),
        hsp("A" * 10, "C" * 10, hit_from=31, hit_to=40, bit_score=25)])]
    values = inputs(collect(query="A" * 40, hits=hits)["searches"][0], symbols=[symbols], kind="reference")
    feature(values, interval=[10, 20], identifier="F", kind="misc_feature", function=function("A"))
    feature(values, interval=[30, 40], identifier="G", kind="misc_feature", function=function("B"))
    assignments = [explicit(values, 0, "whole")]
    result = calculate(populate(values, assignments), grouping="known_source_blocks")
    whole, _ = rows(result)
    features, _ = rows(result, scope="feature")
    assert whole["counts"]["model_groups"] == features["counts"]["model_groups"] == 1
    assert len(whole["groups"][0]["entity_keys"]) == 1
    assert len(features["groups"][0]["entity_keys"]) == 2
    assert any(e["relation"] == "same_parent_sequence" for e in result["dependency_measurements"]["edges"])


def test_explicit_zero_prior_preserves_positive_native_mass_and_model():
    values, assignments = whole_case(); sheet = with_census(values, assignments)
    priors = [dict(assignment_scope="whole_sequence", namespace="fixture_function", function=function(k), weight=w) for k, w in (("A", 1), ("B", 0))]
    result = calculate(sheet, priors=priors, census=sheet["census_records"][0]["census_key"])
    _, f = assert_weights(result, {"A": 1, "B": 0})
    assert_weights(result, {"A": 1, "B": 0}, "representation_adjusted_function_weight")
    assert f["B"]["function_mass"]["value"] == 0.25
    assert f["B"]["prior"]["linear_status"] == f["B"]["conditional_function_weight"]["linear_status"] == "zero"
    assert f["B"]["prior"]["log2_value"] is None and result["model"]["function_priors"] == priors
    priors[0]["weight"] = 0
    with pytest.raises(ValueError, match="^blast_vdb_function_model_parameters_invalid$"):
        calculate(sheet, priors=priors)


@pytest.mark.parametrize("weights", [(1e-300, 1e300), (1e308, 1e308)])
def test_priors_use_stable_normalization_with_positive_underflow_distinct_from_zero(weights):
    values, assignments = case(scores=(20, 20), labels=("A", "B"))
    priors = [dict(assignment_scope="whole_sequence", namespace="fixture_function", function=function(k), weight=w) for k, w in zip("AB", weights)]
    result = calculate(populate(values, assignments), priors=priors)
    _, f = rows(result)
    if weights[0] == weights[1]:
        assert_weights(result, {"A": 0.5, "B": 0.5})
    else:
        for name in ("prior", "conditional_function_weight"):
            assert f["A"][name]["value"] is None and f["A"][name]["linear_status"] == "underflow"
            assert f["A"][name]["log2_value"] < -1900
    json.dumps(result, allow_nan=False)


def test_native_zero_bits_is_eligible_and_log_minus_2000_is_positive_underflow():
    values, assignments = case(scores=(0, -2), labels=("A", "B"))
    assert_weights(calculate(populate(values, assignments)), {"A": 0.8, "B": 0.2})
    values, assignments = case(scores=(2000, 0), labels=("A", "B"))
    result = calculate(populate(values, assignments))
    _, f = rows(result)
    assert f["B"]["function_mass"] == dict(value=None, log2_value=-2000.0, unit="function_mass", linear_status="underflow", reason_code="blast_vdb_function_linear_underflow")
    assert f["B"]["conditional_function_weight"]["log2_value"] == -2000
    assert f["B"]["conditional_function_weight"]["value"] is None
    assert any(i["code"] == "blast_vdb_function_linear_underflow" for i in result["issues"])
    json.dumps(result, allow_nan=False)


def test_extreme_finite_scores_and_temperature_preserve_failure_and_other_scope():
    values, assignments = case(scores=(1, 0), labels=("A", "B"))
    feature(values, interval=[0, 8], identifier="valid-feature", kind="misc_feature", function=function("feature-A"))
    sheet = with_census(values, assignments)
    result = calculate(sheet, temperature=1e-320, census=sheet["census_records"][0]["census_key"])
    bad, f = rows(result); good, gf = rows(result, scope="feature")
    assert bad["status"] == "unavailable" and result["status"] == "partial"
    assert f["A"]["function_mass"]["value"] is None
    assert f["A"]["function_mass"]["reason_code"] == "blast_vdb_function_kernel_arithmetic_out_of_range"
    assert f["A"]["census_function_unit_count"]["value"] == 4
    assert bad["largest_assigned_bit_score"]["value"] == 1
    assert sorted(c["best_bit_score"]["value"] for g in bad["groups"] for c in g["function_contributions"]) == [0, 1]
    assert gf["feature-A"]["conditional_function_weight"]["value"] == 1 and good["status"] == "complete"
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("temperature,unavailable", [(1, True), (1e308, False)])
def test_safe_difference_evaluates_representable_final_quotient(temperature, unavailable):
    values, assignments = case(scores=(1e308, -1e308), labels=("A", "B"))
    result = calculate(populate(values, assignments), temperature=temperature)
    if unavailable:
        assert rows(result)[0]["status"] == "unavailable"
    else:
        assert_weights(result, {"A": 0.8, "B": 0.2})


def test_tiny_positive_temperature_with_equal_scores_does_not_invent_overflow():
    values, assignments = case(scores=(1, 1), labels=("A", "B"))
    result = calculate(populate(values, assignments), temperature=1e-320)
    assert_weights(result, {"A": 0.5, "B": 0.5})
    assert result["status"] == "complete"


@pytest.mark.parametrize("change,reason", [
    (lambda c: c["enumeration"].update(complete=False), "census_partial"),
    (lambda c: c["enumeration"].update(pagination_complete=None), "census_partial"),
    (lambda c: c["enumeration"].update(pagination_complete=False), "census_partial"),
    (lambda c: c["enumeration"].update(reported_total=None), "census_partial"),
    (lambda c: c["enumeration"].update(reported_total=100), "census_count_conflict"),
    (lambda c: c["enumeration"].update(base_count_unit="feature_instance"), "census_unit_mismatch"),
    (lambda c: c["datasets"][0]["snapshot"].update(release="different"), "census_snapshot_mismatch"),
    (lambda c: c["datasets"][0].update(sra_mode=2), "census_filter_mismatch"),
    (lambda c: c["datasets"][0].update(include_filtered_reads=True), "census_filter_mismatch"),
    (lambda c: c["datasets"][0]["selected_input"].update(value="other"), "census_scope_mismatch"),
    (lambda c: c.update(scope="dataset_census"), "census_scope_mismatch"),
    (lambda c: c.update(scope="supplied_subset"), "census_scope_mismatch"),
    (lambda c: c["annotation_bindings"][0].update(annotation_snapshot_sha256="f"*64), "census_annotation_snapshot_mismatch"),
    (lambda c: c["identity_proofs"].pop(), "census_membership_unverified"),
    (lambda c: c.update(source=provenance("", "synthetic:report")), "census_membership_unverified"),
    (lambda c: c["entities"][2].update(functions=[]), "census_zero_conflict"),
])
def test_census_failure_keeps_whole_uncorrected_distribution_and_retained_counts(change, reason):
    values, assignments = whole_case()
    census = census_for(populate(values, assignments)); change(census)
    sheet = with_census(values, assignments, census)
    result = calculate(sheet, census=census["census_key"])
    stratum, f = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert all(r["representation_adjusted_function_weight"]["value"] is None for r in f.values())
    assert not result["census_results"][0]["correction_available"]
    if result["census_results"][0]["status"] == "incompatible":
        assert all(r["representation_adjusted_function_weight"]["linear_status"] == "incompatible" for r in f.values())
    assert result["census_results"][0]["base_entity_count"]["value"] == 6
    assert any(i["code"] == "blast_vdb_function_" + reason for i in result["issues"])
    assert stratum["status"] == "partial" and sheet["census_records"] == [census]
    if reason == "census_zero_conflict":
        b = next(r for r in result["census_results"][0]["function_counts"] if r["function"] == function("B"))
        assert b["count"]["value"] == 0 and b["count"]["status"] == "available"


def test_complete_wrong_snapshot_is_descriptively_complete_and_census_is_opt_in():
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    census["datasets"][0]["snapshot"]["release"] = "other"
    sheet = with_census(values, assignments, census)
    result = calculate(sheet)
    stratum, _ = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert stratum["status"] == "complete" and stratum["census_key"] is None
    c = result["census_results"][0]
    assert c["enumeration_complete"] and not c["correction_available"] and c["status"] == "incompatible"
    assert c["function_counts"][0]["fraction"]["value"] == 0.8


def test_missing_census_and_feature_parent_proof_do_not_fabricate_correction():
    values, assignments = whole_case(); stratum, f = rows(calculate(populate(values, assignments)))
    assert f["A"]["representation_adjusted_function_weight"]["reason_code"] == "blast_vdb_function_census_missing"
    values = translated_case(); census = census_for(populate(values), "feature", extra=False)
    census["identity_proofs"] = [p for p in census["identity_proofs"] if p["normalization"] != "full_member_nt_v1"]
    result = calculate(populate(values, censuses=[census]), grouping="known_source_blocks", census=census["census_key"], scope="feature")
    c = result["census_results"][0]
    assert not c["correction_available"]
    assert any(i["code"] == "blast_vdb_function_census_membership_unverified" for i in c["issues"])
    assert all(r["representation_adjusted_function_weight"]["value"] is None for r in rows(result, scope="feature")[1].values())


@pytest.mark.parametrize("completion,status", [(dict(native_returncode=0, producer_complete=True), "no_reported_hits"), (dict(native_returncode=1, producer_complete=False), "unavailable")])
def test_strict_no_hit_precedence_and_failed_capture(completion, status):
    sheet = populate(inputs(collect(hits=[], completion=completion)["searches"][0]))
    result = calculate(sheet)
    assert result["status"] == status and result["strata"] == []
    assert result["dependency_measurements"]["target_units"] == []


def test_no_candidate_is_not_invented_and_scored_unknown_remains_visible():
    values, assignments = case(scores=(20,), labels=("A",))
    assignments[0]["function_ordinal"] = 99
    result = calculate(populate(values, assignments))
    stratum, f = rows(result)
    assert result["status"] == stratum["status"] == "no_eligible_functions"
    assert f == {} and stratum["unknown_reference_kernel_mass"]["value"] == 1
    assert stratum["unknown_reference_kernel_fraction"]["value"] == 1
    assert stratum["largest_assigned_bit_score"]["value"] is None
    assert result["assignment_results"][0]["status"] == "incompatible"


def test_unknown_origin_and_unscored_identity_keep_counts_without_mass():
    values, assignments = case(scores=(20, 20), labels=("A", "B"))
    values["member_bindings"][1]["relationship"] = "catalog_membership"
    result = calculate(populate(values, assignments)); stratum, f = rows(result)
    assert set(f) == {"A"} and f["A"]["conditional_function_weight"]["value"] == 1
    assert stratum["counts"]["unknown_origin_subjects"] == 1
    assert stratum["counts"]["source_entities"] == 2 and stratum["counts"]["unscored_entities"] == 1
    assert stratum["counts"]["duplicate_target_units"] == 2
    assert stratum["unknown_reference_kernel_mass"]["value"] == 0
    assert any(not g["function_contributions"] for g in stratum["groups"])


def test_partial_report_keeps_valid_row_and_named_native_limits():
    hit = dict(len=8, description=[dict(id="a", accession="a")], hsps=[hsp(bit_score=22), None])
    values = inputs(collect(hits=[hit], completion=dict(native_returncode=1, producer_complete=False))["searches"][0])
    assignments = [explicit(values)]
    result = calculate(populate(values, assignments)); stratum, _ = assert_weights(result, {"A": 1})
    assert not stratum["report_complete"] and stratum["status"] == "partial"
    assert stratum["counts"]["eligible_hsps"] == 1
    assert values["search"]["native"]["search"]["hits"][0]["hsps"][1] is None


def test_literal_namespaces_remain_separate():
    values, assignments = case(scores=(20, 20), labels=("A", "B"))
    assignments.append(explicit(values, 0, "literal product", namespace="product"))
    result = calculate(populate(values, assignments))
    assert len(result["strata"]) == 2
    assert_weights(result, {"A": 0.5, "B": 0.5})
    assert_weights(result, {"literal product": 1}, namespace="product")
    assert rows(result, namespace="product")[0]["unknown_reference_kernel_fraction"]["value"] == 0.5


def test_taxonomy_target_context_and_actual_quality_remain_unused_numbers():
    values, assignments = whole_case()
    original = calculate(populate(values, assignments))
    for i, taxid in enumerate((10, 10, 20)):
        meta = next(m for m in values["reference_metadata"] if m["metadata_key"] == f"member{i}")
        meta.update(taxid=taxid, taxid_scope="entity_organism", lineage=[dict(taxid=taxid, rank="species", name=str(taxid))])
    values["target_context"] = dict(query_operand=deepcopy(values["query_binding"]["operand"]), taxid=99,
        lineage=[dict(taxid=99, rank="species", name="other")], independent_of_search=True, source=provenance("/target"))
    values["reference_metadata"][0]["assembly"] = dict(identifier=identity("assembly"), completeness_percent=97.5,
        contamination_percent=12, contig_count=3, contig_n50=100, total_sequence_length=200,
        method="CheckM", method_version="synthetic", source=provenance("/checkm"), linkage_source=provenance("/assembly-link"))
    sheet = populate(values, assignments); changed = calculate(sheet)
    assert rows(original)[1] == rows(changed)[1]
    quality = sheet["base_components"]["source_quality"]["records"][0]
    assert quality["completeness_fraction"]["value"] == 0.975
    assert quality["contamination_fraction"]["value"] == 0.12
    assert {"taxonomy", "target_compatibility", "assembly_quality"} <= set(changed["retained_measurements_not_used"])


def test_pssm_master_axis_is_retained_in_its_own_search_distribution():
    values = translated_case()
    source = values["search"]["native"]["search"]
    pssm = inputs(collect(program="tblastn_vdb", query="PMAKPP", query_kind="pssm", hits=source["hits"])["searches"][0],
        symbols=["CCCATGGCTAAACCCCCC", "TTTAGCCATAAA", "CAGACCCATCCC"], kind="reference")
    for i in range(3):
        feature(pssm, interval=[3, 12] if i == 0 else [0, 9], identifier=f"feature{i}", strand=1 if i == 0 else -1,
            translation="MAK" if i < 2 else "MGL", genetic_code=1, codon_start=1, function=function("A" if i < 2 else "B"), hit=i)
    missing = calculate(populate(pssm), temperature=2)
    assert missing["status"] == "no_eligible_functions"
    mapping = dict(pssm_key="pssm", num_columns=6,
        columns=[dict(column=i, master_position=i, symbol=symbol) for i, symbol in enumerate("PMAKPP")])
    pssm["reference_metadata"].append(metadata("master", entity("query_master", pssm="pssm"),
        source=provenance("/master"), master_mapping=mapping))
    result = calculate(populate(pssm), temperature=2)
    stratum, _ = assert_weights(result, {"A": 2/3, "B": 1/3}, scope="feature")
    assert stratum["query_axis_kind"] == "pssm_master"
    assert pssm["search"]["program_context"]["query_kind"] == "pssm"
    pssm["query_binding"]["axis_kind"] = "sequence"
    conflicted = calculate(populate(pssm), temperature=2)
    assert rows(conflicted, scope="feature")[0]["query_axis_kind"] == "pssm_master"
    assert conflicted["status"] == "no_eligible_functions"


@pytest.mark.parametrize("unknown", ["qualify_separate", "withhold_weights"])
def test_census_unknown_sample_policy_qualifies_or_withholds_only_correction(unknown):
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    census["entities"][-1]["origin_sample_keys"] = []
    census["entities"][-1]["sample_relation_status"] = "unavailable"
    sheet = with_census(values, assignments, census)
    result = calculate(sheet, grouping="known_source_blocks", unknown=unknown, census=census["census_key"])
    stratum, f = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert stratum["dependency_complete"] and stratum["status"] == "partial"
    if unknown == "withhold_weights":
        assert all(r["representation_adjusted_function_weight"]["value"] is None for r in f.values())
        assert not result["census_results"][0]["correction_available"]
    else:
        assert all(r["representation_adjusted_function_weight"]["value"] is not None for r in f.values())
        assert result["census_results"][0]["correction_available"]
        assert "unknown_dependency_separate" in result["assumptions"]


def test_census_member_function_missing_keeps_other_candidate_count_but_no_subset_normalization():
    values, assignments = whole_case(); census = census_for(populate(values, assignments))
    census["entities"][2]["functions"] = []
    census["entities"][-1]["functions"] = [function("B")]
    result = calculate(with_census(values, assignments, census), census=census["census_key"])
    _, f = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert all(r["representation_adjusted_function_weight"]["value"] is None for r in f.values())
    c = result["census_results"][0]
    assert next(r for r in c["function_counts"] if r["function"] == function("A"))["count"]["value"] == 3
    assert any(i["code"] == "blast_vdb_function_census_function_missing" for i in c["issues"])


def test_no_hit_stratum_retains_independent_complete_nonzero_census():
    original, assignments = whole_case(); census = census_for(populate(original, assignments))
    census["annotation_bindings"] = []
    values = inputs(collect(hits=[])["searches"][0])
    values["dataset_records"] = deepcopy(original["dataset_records"])
    for dataset in values["dataset_records"]:
        dataset["metadata_keys"] = []
    result = calculate(populate(values, censuses=[census]), census=census["census_key"])
    stratum, f = rows(result)
    assert result["status"] == stratum["status"] == "no_reported_hits"
    assert not f and not stratum["groups"] and all(n == 0 for n in stratum["counts"].values())
    assert stratum["unknown_reference_kernel_fraction"]["value"] is None
    assert result["census_results"][0]["base_entity_count"]["value"] == 6
    assert result["census_results"][0]["correction_available"]


def test_sample_only_assignment_never_creates_a_function_stratum():
    values, assignments = case(scores=(20,), labels=("A",))
    meta = next(m for m in values["reference_metadata"] if m["metadata_key"] == "sample0")
    meta["functions"] = deepcopy(values["reference_metadata"][0]["functions"])
    assignments[0].update(assignment_scope="sample", metadata_key="sample0", target=dict(member_key=None, feature_identifier=None, sample_key="S0"))
    result = calculate(populate(values, assignments))
    assert result["status"] == "no_eligible_functions" and result["strata"] == []
    assert result["assignment_results"][0]["reason_code"] == "blast_vdb_function_sample_assignment_not_query_function"


def test_native_named_reporting_limit_qualifies_an_otherwise_complete_weight():
    values, assignments = whole_case()
    values["search"]["reporting"]["requested_hit_limit"] = 3
    result = calculate(populate(values, assignments))
    stratum, _ = assert_weights(result, {"A": 0.8, "B": 0.2})
    assert not stratum["report_complete"] and stratum["status"] == "partial"
    assert stratum["native_reporting"]["requested_hit_limit"] == 3


def test_empty_table6_cannot_establish_successful_zero_hits():
    sheet = populate(inputs(collect(raw=b"", format_name="tabular6", fields=["qseqid", "sseqid"])["searches"][0]))
    assert calculate(sheet)["status"] == "unavailable"


def test_no_hit_precedence_keeps_unobserved_source_bindings_out_of_observed_groups():
    values, assignments = whole_case()
    values["search"] = collect(hits=[])["searches"][0]
    sheet = populate(values, assignments)
    assert sheet["base_components"]["status"] == "no_reported_hits"
    assert len(sheet["entities"]) == 3
    result = calculate(sheet, grouping="known_source_blocks", unknown="withhold_weights")
    stratum, f = rows(result)
    assert result["status"] == stratum["status"] == "no_reported_hits"
    assert not f and not stratum["groups"] and all(n == 0 for n in stratum["counts"].values())
    assert len(result["dependency_measurements"]["target_units"]) == 2
    assert result["assignment_results"]


@pytest.mark.parametrize("change", [
    lambda m: m.update(extra=0), lambda m: m.update(version="old"),
    lambda m: m.update(temperature_bits=0), lambda m: m.update(temperature_bits=-1),
    lambda m: m.update(temperature_bits=True), lambda m: m.update(grouping_model=[]),
    lambda m: m.update(unknown_source_dependency="guess"),
    lambda m: m.update(function_priors={}),
])
def test_closed_model_validation_and_detachment(change):
    value = model(); original = deepcopy(value)
    output = calculator.validate_blast_vdb_function_model(value)
    assert output == original and output is not value
    change(value)
    with pytest.raises(ValueError, match="^blast_vdb_function_model_parameters_invalid$"):
        calculator.validate_blast_vdb_function_model(value)


@pytest.mark.parametrize("value", [float("inf"), float("nan"), b"bytes"])
def test_nonfinite_model_or_saved_sheet_is_a_structural_error(value):
    m = model(); m["temperature_bits"] = value
    with pytest.raises(ValueError, match="^blast_vdb_function_finite_json_required$"):
        calculator.validate_blast_vdb_function_model(m)
    values, assignments = whole_case(); sheet = populate(values, assignments)
    sheet["observations"][0]["native_bit_score"]["value"] = value
    with pytest.raises(ValueError, match="^blast_vdb_function_finite_json_required$"):
        calculate(sheet)


def test_actual_candidate_prior_and_census_selector_sets_are_checked():
    values, assignments = whole_case(); sheet = populate(values, assignments)
    with pytest.raises(ValueError, match="^blast_vdb_function_prior_candidate_set_mismatch$"):
        calculate(sheet, priors=[])
    with pytest.raises(ValueError, match="^blast_vdb_function_census_selector_invalid$"):
        calculate(sheet, census="missing")
    bad = model(census="one"); bad["census_selection"] *= 2
    with pytest.raises(ValueError, match="^blast_vdb_function_census_selector_invalid$"):
        calculator.validate_blast_vdb_function_model(bad)


def test_recalculation_uses_real_validator_and_no_parsing_population_acquisition_or_io(monkeypatch):
    values, assignments = whole_case(); sheet = with_census(values, assignments)
    frozen = json.loads(json.dumps(sheet)); before = deepcopy(frozen)
    validator = inputs_module.validate_blast_vdb_function_sheet; calls = []
    def validating(value):
        calls.append(value)
        return validator(value)
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden during saved-sheet arithmetic")
    monkeypatch.setattr(inputs_module, "validate_blast_vdb_function_sheet", validating)
    for name in ("populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo", "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata", "bind_blast_vdb_metadata", "_recheck_metadata", "_reparse"):
        monkeypatch.setattr(v1, name, forbidden)
    monkeypatch.setattr(base, "calculate_blast_vdb_components", forbidden)
    monkeypatch.setattr(inputs_module, "populate_blast_vdb_function_sheet", forbidden)
    monkeypatch.setattr(inputs_module, "extract_blast_vdb_feature_function_assignments", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    for name in ("open", "read_text", "read_bytes"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    first = calculate(frozen, census=frozen["census_records"][0]["census_key"])
    second = calculate(frozen, temperature=2, census=frozen["census_records"][0]["census_key"])
    assert_weights(first, {"A": 0.8, "B": 0.2})
    assert_weights(second, {"A": 2/3, "B": 1/3})
    assert len(calls) == 2 and frozen == before
    assert first["model"]["temperature_bits"] == 1
    first["dependency_measurements"]["target_units"][0]["entity_keys"].clear()
    assert frozen == before


def test_complete_result_shapes_and_no_silent_nan_serialization():
    values, assignments = whole_case(); sheet = with_census(values, assignments)
    result = calculate(sheet, census=sheet["census_records"][0]["census_key"])
    assert set(result) == set("schema search_key status model calibrated_annotation_probability strata assignment_results dependency_measurements census_results issues retained_measurements_not_used assumptions".split())
    stratum, functions = rows(result)
    assert set(stratum) == set("assignment_scope namespace query_axis_kind grouping_model status counts native_reporting report_complete metadata_complete dependency_complete largest_assigned_bit_score largest_all_bit_score groups functions unknown_reference_kernel_mass assigned_reference_kernel_mass total_reference_kernel_mass unknown_reference_kernel_fraction conditional_weight_denominator representation_adjusted_weight_denominator census_key issues".split())
    for row in functions.values():
        assert set(row) == set("function assignment_keys group_keys source_entity_count target_unit_count function_mass prior prior_weighted_mass conditional_function_weight census_function_unit_count census_total_unit_count census_function_fraction census_partition_function_mass census_partition_prior_weighted_mass representation_rate representation_adjusted_function_weight issues".split())
        for key in ("function_mass", "prior", "conditional_function_weight", "representation_rate"):
            assert set(row[key]) == set("value log2_value unit linear_status reason_code".split())
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("case_name", ["unselected", "partial", "incompatible", "empty"])
def test_inherited_measure_missingness_uses_the_exact_309_enum(case_name):
    values, assignments = whole_case()
    census = census_for(populate(values, assignments))
    selected = census["census_key"]
    if case_name == "unselected":
        selected = None
    elif case_name == "partial":
        census["enumeration"]["complete"] = False
    elif case_name == "incompatible":
        census["datasets"][0]["snapshot"]["release"] = "different"
    else:
        values["search"] = collect(hits=[])["searches"][0]
    result = calculate(with_census(values, assignments, census), census=selected)
    allowed = {"missing_input", "not_measured", "incompatible_input", "invalid_native_row", "partial_output"}
    found = []
    def inspect(value):
        if type(value) is list:
            for item in value:
                inspect(item)
        elif type(value) is dict:
            if set(value) == {"value", "unit", "status", "unavailable_reason"} and value["value"] is None:
                assert value["unavailable_reason"] in allowed
                found.append(value)
            for item in value.values():
                inspect(item)
    inspect(result)
    assert found
