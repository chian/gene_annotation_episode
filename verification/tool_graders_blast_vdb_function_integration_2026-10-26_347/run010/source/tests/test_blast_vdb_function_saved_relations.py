"""Saved grouping identities must retain their supplied member/sample sources."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode import blast_vdb_function_inputs as module
from gene_annotation_episode import blast_vdb_inputs as v1
from gene_annotation_episode import blast_vdb_calculators as base


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001"


def saved():
    return json.loads((FIXTURES / "whole_sequence.json").read_text())


def replace_sample_names(sheet, value):
    for row in sheet["base_components"]["sample_groups"]["groups"]:
        row["sample_key"] = value
    for row in sheet["entities"]:
        if row["origin_sample_keys"]:
            row["origin_sample_keys"] = [value]


@pytest.mark.parametrize("value", ["invented-shared-sample", "S0"])
def test_coordinated_sample_relabeling_cannot_change_dependency_partition(value):
    sheet = saved(); original = deepcopy(sheet["base_sheet"])
    replace_sample_names(sheet, value)
    assert sheet["base_sheet"] == original
    with pytest.raises(ValueError, match="^blast_vdb_function_reference_out_of_range$"):
        module.validate_blast_vdb_function_sheet(sheet)


@pytest.mark.parametrize("change", [
    lambda s: s["base_components"]["sample_groups"]["groups"][0]["sample_identifier"].update(value="S2"),
    lambda s: s["base_components"]["sample_groups"]["groups"][0].update(metadata_keys=["sample2"]),
    lambda s: s["base_components"]["sample_groups"]["groups"][0]["catalog_member_keys"].clear(),
    lambda s: s["base_components"]["sample_groups"]["groups"][0]["origin_subject_row_keys"].clear(),
    lambda s: s["base_components"]["sample_groups"]["groups"].pop(),
    lambda s: s["base_components"]["membership"]["origins"].append(deepcopy(s["base_components"]["membership"]["origins"][0])),
    lambda s: s["base_components"]["membership"]["origins"].pop(),
    lambda s: s["base_components"]["membership"]["origin_members"][0]["row_keys"].clear(),
    lambda s: s["base_components"]["membership"]["catalogue_members"].pop(),
    lambda s: s["base_components"]["membership"]["origin_bound_subject_count"].update(value=999),
    lambda s: s["base_components"]["sample_groups"]["observed_origin_sample_count"].update(value=999),
])
def test_saved_membership_sources_and_counts_cannot_be_substituted(change):
    sheet = saved(); change(sheet)
    with pytest.raises(ValueError, match="^blast_vdb_function_(reference_out_of_range|record_fields_invalid)$"):
        module.validate_blast_vdb_function_sheet(sheet)


@pytest.mark.parametrize("name", ["whole_sequence", "translated_features", "translated_siblings"])
def test_valid_frozen_groups_remain_identical_without_parsing_or_recalculation(name, monkeypatch):
    sheet = json.loads((FIXTURES / (name + ".json")).read_text())
    original = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved relation checks must not parse, populate or recalculate the v1 base")
    for port in ("_reparse", "_recheck_metadata", "populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo", "parse_ncbi_gbseq_vdb_metadata", "parse_blast_vdb_member_sequences"):
        monkeypatch.setattr(v1, port, forbidden)
    monkeypatch.setattr(base, "calculate_blast_vdb_components", forbidden)
    monkeypatch.setattr(module, "populate_blast_vdb_function_sheet", forbidden)
    result = module.validate_blast_vdb_function_sheet(sheet)
    assert result == sheet == original and result is not sheet


def conflicting_feature_assignment(destination):
    original = json.loads((FIXTURES / "translated_features.json").read_text())
    declaration = deepcopy(original["assignment_records"][0])
    if destination == "missing_feature":
        declaration["target"]["feature_identifier"]["value"] = "different-feature"
    else:
        declaration["target"] = deepcopy(original["assignment_records"][1]["target"])
    populated = module.populate_blast_vdb_function_sheet(original["base_sheet"],
        supplied_assignments=[declaration], dependency_records=[], census_records=[])
    return original, declaration, populated


@pytest.mark.parametrize("destination", ["missing_feature", "other_bound_feature"])
def test_conflicting_assignment_key_retains_exact_entity_and_valid_siblings(destination, monkeypatch):
    original, declaration, sheet = conflicting_feature_assignment(destination)
    key = declaration["assignment_key"]
    variants = [a for a in sheet["assignment_records"] if a["assignment_key"] == key]
    assert len(variants) == 2 and declaration in variants
    link = next(r for r in sheet["link_results"] if r["record_kind"] == "assignment" and r["record_key"] == key)
    assert link["status"] == "incompatible" and len(link["input_pointers"]) == 2
    affected = [o for o in sheet["observations"] if o["assignment_key"] == key]
    assert len(affected) == (1 if destination == "missing_feature" else 2)
    assert all(o["qualification"] == "incompatible" for o in affected)
    # The independent B feature retains its complete original numerical row.
    expected = [o for o in original["observations"] if o["function"] and o["function"]["value"] == "B"]
    actual = [o for o in sheet["observations"] if o["function"] and o["function"]["value"] == "B"]
    assert actual == expected and all(o["qualification"] == "available" for o in actual)
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved conflict validation cannot parse, repopulate or recalculate")
    for port in ("_reparse", "_recheck_metadata", "populate_blast_vdb_sheet", "parse_ncbi_sra_runinfo", "parse_ncbi_gbseq_vdb_metadata", "parse_blast_vdb_member_sequences"):
        monkeypatch.setattr(v1, port, forbidden)
    monkeypatch.setattr(base, "calculate_blast_vdb_components", forbidden)
    monkeypatch.setattr(module, "populate_blast_vdb_function_sheet", forbidden)
    assert module.validate_blast_vdb_function_sheet(sheet) == sheet


@pytest.mark.parametrize("destination", ["missing_feature", "other_bound_feature"])
@pytest.mark.parametrize("change", ["remove_observation", "claim_available"])
def test_saved_conflict_cannot_disappear_or_gain_available_qualification(destination, change):
    _, declaration, sheet = conflicting_feature_assignment(destination)
    observation = next(o for o in sheet["observations"] if o["assignment_key"] == declaration["assignment_key"])
    if change == "remove_observation":
        sheet["observations"].remove(observation)
    else:
        observation.update(qualification="available", reason_code=None, issues=[])
    with pytest.raises(ValueError, match="^blast_vdb_function_(reference_out_of_range|record_fields_invalid)$"):
        module.validate_blast_vdb_function_sheet(sheet)
