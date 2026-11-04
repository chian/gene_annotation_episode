"""Public-path regressions for348's two synthetic census counterexamples."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode import blast_vdb_function_inputs as inputs
from gene_annotation_episode import blast_vdb_function_calculators as calculator
from gene_annotation_episode import blast_vdb_inputs as native
from gene_annotation_episode import blast_vdb_calculators as base


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_vdb_census_relation_repair_2026-10-26_350"
PREFIX = "blast_vdb_function_"
MODEL_POLICIES = [
    ("target_duplicates_only", "qualify_separate"),
    ("target_duplicates_only", "withhold_weights"),
    ("known_source_blocks", "qualify_separate"),
    ("known_source_blocks", "withhold_weights"),
]


def fixture(name):
    raw = (PACKET / "fixtures" / (name + ".json")).read_bytes()
    pins = json.loads((PACKET / "FIXTURE_PINS_001.json").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == pins[name + ".json"]["sha256"]
    return json.loads(raw)


def original_input(name):
    original = fixture(name)
    sheet = original["sheet"]
    return original, {
        "vdb_sheet": deepcopy(sheet["base_sheet"]),
        "supplied_assignments": deepcopy(sheet["assignment_records"]),
        "dependency_records": deepcopy(sheet["dependency_records"]),
        "census_records": deepcopy(sheet["census_records"]),
    }


def model_for(original, grouping, policy):
    model = deepcopy(original["model"])
    model.update(grouping_model=grouping, unknown_source_dependency=policy)
    return model


def census_link(sheet):
    return next(r for r in sheet["link_results"] if r["record_kind"] == "census")


def function_rows(components):
    return {r["function"]["value"]: r for r in components["strata"][0]["functions"]}


def weights(components, field="conditional_function_weight"):
    return {key: row[field]["value"] for key, row in function_rows(components).items()}


def issue_codes(value):
    return {i["code"] for i in value["issues"]}


@contextmanager
def saved_only():
    def forbidden(*args, **kwargs):
        raise AssertionError("saved relation validation/calculation must not parse, populate, acquire or execute")
    with ExitStack() as stack:
        for module, port in (
            (inputs, "populate_blast_vdb_function_sheet"),
            (inputs, "extract_blast_vdb_feature_function_assignments"),
            (base, "calculate_blast_vdb_components"),
            *[(native, port) for port in (
                "populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo",
                "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata",
                "bind_blast_vdb_metadata", "_recheck_metadata", "_reparse")],
        ):
            stack.enter_context(patch.object(module, port, forbidden))
        for port in ("builtins.open", "socket.socket", "socket.create_connection", "subprocess.Popen"):
            stack.enter_context(patch(port, forbidden))
        yield


def checked_calculate(sheet, model):
    before_sheet, before_model = deepcopy(sheet), deepcopy(model)
    with saved_only():
        validated = inputs.validate_blast_vdb_function_sheet(sheet)
        assert validated == sheet and validated is not sheet
        components = calculator.calculate_blast_vdb_function_components(sheet, model=model)
    assert sheet == before_sheet and model == before_model
    return components


def assert_observations_preserved(sheet, original):
    for field in ("base_sheet", "base_components", "assignment_records", "dependency_records", "entities", "observations"):
        assert sheet[field] == original["sheet"][field]


def assert_descriptive_counts(components, grouping, *, base_count=6, target_count=5, groups=None):
    census = components["census_results"][0]
    assert census["enumeration_complete"] is True
    assert census["base_entity_count"]["value"] == base_count
    assert census["target_unit_count"]["value"] == target_count
    if groups is None:
        groups = 5 if grouping == "target_duplicates_only" else 2
    assert census["model_group_count"]["value"] == groups
    return census


def assert_correction_unavailable(components, reason, *, incompatible=False):
    assert not components["census_results"][0]["correction_available"]
    for row in function_rows(components).values():
        for field in ("census_partition_function_mass", "census_partition_prior_weighted_mass",
                      "representation_rate", "representation_adjusted_function_weight"):
            assert row[field]["value"] is None and row[field]["log2_value"] is None
            assert row[field]["reason_code"] == PREFIX + reason
            assert row[field]["linear_status"] == ("incompatible" if incompatible else "unavailable")
        assert row["census_function_unit_count"]["value"] is None
        assert row["census_total_unit_count"]["value"] is None
        assert row["census_function_fraction"]["value"] is None


@pytest.mark.parametrize("grouping,policy", MODEL_POLICIES)
def test_unresolved_optional_census_edge_uses_selected_policy(grouping, policy):
    evidence = fixture("unresolved_census_edge_baseline")
    original = fixture("whole_t1")
    fixture_input = deepcopy(evidence["fixture_input"])
    source_before = deepcopy(fixture_input)
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert fixture_input == source_before
    assert_observations_preserved(sheet, original)
    assert sheet["census_records"] == fixture_input["census_records"]
    link = census_link(sheet)
    assert link["status"] == "available" and link["reason_code"] is None
    assert issue_codes(link) == {PREFIX + "dependency_relation_unresolved"}
    issue = link["issues"][0]
    assert issue["details"] == {
        "census_key": "census-1", "dependency_key": "review348-source-not-supplied", "unresolved_entities": []}
    assert issue in sheet["issues"]
    result = checked_calculate(sheet, model_for(original, grouping, policy))
    assert weights(result) == pytest.approx({"A": .8, "B": .2})
    census = assert_descriptive_counts(result, grouping)
    counts = {r["function"]["value"]: r["count"]["value"] for r in census["function_counts"]}
    assert counts == ({"A": 4, "B": 1} if grouping == "target_duplicates_only" else {"A": 1, "B": 1})
    assert census["target_units"] == original["components"]["census_results"][0]["target_units"]
    if grouping == "target_duplicates_only":
        assert result["status"] == result["strata"][0]["status"] == "complete"
        assert census["status"] == "available" and census["correction_available"]
        assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": .5, "B": .5})
        assert "unknown_dependency_separate" not in result["assumptions"]
    else:
        assert result["status"] == result["strata"][0]["status"] == "partial"
        assert PREFIX + "dependency_unknown" in issue_codes(census)
        # The known S0 links and a1/a2 duplicate keep the four A targets in one
        # block. Only the unsupported same-library A/B edge is excluded.
        assert sorted(len(g["entity_keys"]) for g in census["model_groups"]) == [1, 5]
        if policy == "qualify_separate":
            assert census["status"] == "available" and census["correction_available"]
            assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": .8, "B": .2})
            assert "unknown_dependency_separate" in result["assumptions"]
        else:
            assert census["status"] == "unavailable"
            assert_correction_unavailable(result, "dependency_unknown")


@pytest.mark.parametrize("grouping,policy", MODEL_POLICIES)
def test_available_sample_contradiction_disables_all_corrected_functions(grouping, policy):
    evidence = fixture("census_observed_sample_contradiction")
    original = fixture("full_census_bridge")
    fixture_input = deepcopy(evidence["fixture_input"])
    source_before = deepcopy(fixture_input)
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert fixture_input == source_before
    assert_observations_preserved(sheet, original)
    assert sheet["census_records"] == fixture_input["census_records"]
    observed = sheet["entities"][2]
    census_entity = sheet["census_records"][0]["entities"][2]
    assert observed["address"] == census_entity["address"]
    assert observed["target_identity"] == census_entity["target_identity"]
    assert observed["sample_relation_status"] == census_entity["sample_relation_status"] == "available"
    assert observed["origin_sample_keys"] == ["S3"] and census_entity["origin_sample_keys"] == ["S1"]
    link = census_link(sheet)
    assert link["status"] == "incompatible"
    assert link["reason_code"] == PREFIX + "census_membership_unverified"
    conflict = next(i for i in link["issues"] if i["details"].get("membership_conflict"))
    assert conflict["details"]["entity_key"] == observed["entity_key"]
    assert conflict["details"]["census_entity_key"] == census_entity["entity_key"]
    assert conflict["details"]["observed_origin_sample_keys"] == ["S3"]
    assert conflict["details"]["census_origin_sample_keys"] == ["S1"]
    result = checked_calculate(sheet, model_for(original, grouping, policy))
    assert weights(result) == pytest.approx({"A": 1/3, "B": 1/3, "C": 1/3})
    assert result["status"] == result["strata"][0]["status"] == "partial"
    census = assert_descriptive_counts(result, grouping, base_count=5, target_count=4,
        groups=4 if grouping == "target_duplicates_only" else 2)
    assert census["status"] == "incompatible"
    assert_correction_unavailable(result, "census_membership_unverified", incompatible=True)


def test_original_full_census_bridge_keeps_partition_and_sevenths():
    original, fixture_input = original_input("full_census_bridge")
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert sheet == original["sheet"]
    result = checked_calculate(sheet, original["model"])
    assert result == original["components"]
    assert result["status"] == "complete"
    assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": 1/7, "B": 2/7, "C": 4/7})


@pytest.mark.parametrize("grouping,policy", MODEL_POLICIES)
def test_available_observed_and_unavailable_census_sample_follow_unknown_policy(grouping, policy):
    original, fixture_input = original_input("whole_t1")
    unknown = fixture_input["census_records"][0]["entities"][2]
    unknown.update(origin_sample_keys=[], sample_relation_status="unavailable")
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert_observations_preserved(sheet, original)
    assert sheet["entities"][2]["sample_relation_status"] == "available"
    assert sheet["entities"][2]["origin_sample_keys"] == ["S2"]
    assert sheet["census_records"][0]["entities"][2] == unknown
    assert census_link(sheet)["status"] == "available" and census_link(sheet)["issues"] == []
    result = checked_calculate(sheet, model_for(original, grouping, policy))
    assert weights(result) == pytest.approx({"A": .8, "B": .2})
    census = assert_descriptive_counts(result, grouping)
    if grouping == "target_duplicates_only":
        assert result["status"] == "complete" and census["correction_available"]
        assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": .5, "B": .5})
    else:
        assert result["status"] == "partial"
        assert PREFIX + "dependency_unknown" in issue_codes(census)
        if policy == "qualify_separate":
            assert census["correction_available"] and "unknown_dependency_separate" in result["assumptions"]
            assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": .8, "B": .2})
        else:
            assert_correction_unavailable(result, "dependency_unknown")


@pytest.mark.parametrize("grouping,policy", MODEL_POLICIES)
@pytest.mark.parametrize("defect", ["repeated_endpoint", "single_endpoint", "conflict_and_unresolved"])
def test_census_dependency_conflict_cannot_be_treated_as_optional_unknown(grouping, policy, defect):
    original, fixture_input = original_input("whole_t1")
    census = fixture_input["census_records"][0]
    address = deepcopy(census["entities"][0]["address"])
    census["dependency_records"] = [{
        "dependency_key": "contradictory-dependence", "relation": "same_library",
        "entities": [address] if defect == "single_endpoint" else [address, deepcopy(address)],
        "sources": [] if defect == "conflict_and_unresolved" else [deepcopy(census["source"])],
        "native_record": {"fixture_kind": "synthetic_invalid_dependence"},
    }]
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert_observations_preserved(sheet, original)
    assert sheet["census_records"] == fixture_input["census_records"]
    link = census_link(sheet)
    assert link["status"] == "incompatible"
    assert link["reason_code"] == PREFIX + "dependency_relation_conflict"
    assert all(i["details"]["census_key"] == census["census_key"] and
               i["details"]["dependency_key"] == "contradictory-dependence" for i in link["issues"])
    expected = {PREFIX + "dependency_relation_conflict"}
    if defect == "conflict_and_unresolved":
        expected.add(PREFIX + "dependency_relation_unresolved")
    assert issue_codes(link) == expected
    result = checked_calculate(sheet, model_for(original, grouping, policy))
    assert weights(result) == pytest.approx({"A": .8, "B": .2})
    assert_descriptive_counts(result, grouping)
    assert result["census_results"][0]["status"] == "incompatible"
    assert_correction_unavailable(result, "dependency_relation_conflict", incompatible=True)


@pytest.mark.parametrize("source", ["old_available_sheet", "tampered_original_sheet", "tampered_repaired_link"])
def test_saved_validator_rejects_available_link_over_sample_conflict_without_repopulation(source):
    if source == "old_available_sheet":
        evidence = fixture("census_observed_sample_contradiction")
        sheet, model = deepcopy(evidence["sheet"]), evidence["model"]
    elif source == "tampered_original_sheet":
        original = fixture("full_census_bridge")
        sheet, model = deepcopy(original["sheet"]), original["model"]
        sheet["census_records"][0]["entities"][2]["origin_sample_keys"] = ["S1"]
    else:
        evidence = fixture("census_observed_sample_contradiction")
        sheet = inputs.populate_blast_vdb_function_sheet(**evidence["fixture_input"])
        model = evidence["model"]
        removed = deepcopy(census_link(sheet)["issues"])
        census_link(sheet).update(status="available", reason_code=None, issues=[])
        sheet["issues"] = [i for i in sheet["issues"] if i not in removed]
    original_sheet = deepcopy(sheet)
    with saved_only():
        with pytest.raises(ValueError, match="^blast_vdb_function_record_fields_invalid$"):
            inputs.validate_blast_vdb_function_sheet(sheet)
        with pytest.raises(ValueError, match="^blast_vdb_function_record_fields_invalid$"):
            calculator.calculate_blast_vdb_function_components(sheet, model=model)
    assert sheet == original_sheet


def test_sample_membership_comparison_uses_exact_entity_and_sample_sets():
    original, fixture_input = original_input("whole_t1")
    census = fixture_input["census_records"][0]
    # a1 and a2 share the exact sequence but have different, valid original
    # sample relations. Their sample sets must be joined by address, not digest.
    assert census["entities"][0]["target_identity"] == census["entities"][1]["target_identity"]
    assert census["entities"][0]["origin_sample_keys"] == ["S0"]
    assert census["entities"][1]["origin_sample_keys"] == ["S1"]
    census["entities"][0]["origin_sample_keys"] = ["S0", "S0"]
    sheet = inputs.populate_blast_vdb_function_sheet(**fixture_input)
    assert census_link(sheet)["status"] == "available" and census_link(sheet)["issues"] == []
    assert sheet["census_records"][0]["entities"][0]["origin_sample_keys"] == ["S0", "S0"]
    result = checked_calculate(sheet, model_for(original, "known_source_blocks", "qualify_separate"))
    assert result["status"] == "complete"
    assert weights(result, "representation_adjusted_function_weight") == pytest.approx({"A": .8, "B": .2})
