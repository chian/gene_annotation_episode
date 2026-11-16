"""Pure engineering instructions; no adopted catalog or target findings."""
from copy import deepcopy

import pytest

from method_loop.durable import content_digest
from gene_annotation_episode.domain import (FINDING_QUALIFICATIONS,
    OBSERVATION_KINDS, PREDICATES, RECORD_SCHEMAS)
from gene_annotation_episode.episodic_workflow.root.scientific_support_metadata import (
    annotation_policy_routes, support_observation_kinds, validate_support_entry)


def support_entry():
    """Invented body and provenance, independent of production A allocation."""
    return {"entry_version": "scientific_support_entry_v1", "id": "A01",
        "slot": "annotation_distinction", "name": "Synthetic support problem",
        "description": "Engineering instruction only.", "support": {
            "proposition": "Inspect actual correspondence for the assigned question.",
            "operands": [{"operand_id": "correspondence",
                "observation_kinds": ["alignment", "comparison"],
                "hypothesis_predicates": ["functional_family"],
                "assessment_relations": ["strengthens", "weakens"],
                "applicabilities": ["transfer", "incomparable"],
                "extent_bases": ["inferred_extent"],
                "finding_qualifications": ["different_source_subject"],
                "instruction": "Retain the actual source and bounded target attribution."}],
            "qualifications": ["This is synthetic instruction content."],
            "boundary": "No target evidence or score is supplied by this body."},
        "evidence": [{"case_group": "synthetic", "case_id": "synthetic_record",
            "source_url": "https://example.org/synthetic",
            "source_locator": "Engineering fixture",
            "observation": "Invented instruction provenance.",
            "limit": "No biological observation or adopted catalog entry."}]}


def test_support_validation_detaches_all_content_and_returns_sorted_kind_union():
    original = support_entry()
    other = deepcopy(original["support"]["operands"][0])
    other.update(operand_id="second", observation_kinds=["source_content", "alignment"])
    original["support"]["operands"].append(other)
    result = validate_support_entry(original)
    assert result == original and result is not original
    result["support"]["operands"][0]["instruction"] = "Changed caller copy."
    result["evidence"][0]["limit"] = "Changed caller copy."
    assert result != original
    assert support_observation_kinds(original) == ["alignment", "comparison", "source_content"]


@pytest.mark.parametrize("field,values", [
    ("observation_kinds", OBSERVATION_KINDS),
    ("hypothesis_predicates", PREDICATES),
    ("assessment_relations", RECORD_SCHEMAS["assessment"]["properties"]["relation"]["enum"]),
    ("applicabilities", RECORD_SCHEMAS["assessment"]["properties"]["applicability"]["enum"]),
    ("extent_bases", RECORD_SCHEMAS["assessment"]["properties"]["extent_basis"]["enum"]),
    ("finding_qualifications", FINDING_QUALIFICATIONS),
])
def test_support_accepts_every_existing_enum_and_rejects_unknown_empty_duplicate(field, values):
    entry = support_entry()
    entry["support"]["operands"][0][field] = list(values)
    assert validate_support_entry(entry) == entry
    for invalid in ([], ["invented_value"], [values[0], values[0]], None, values[0], tuple(values)):
        entry["support"]["operands"][0][field] = invalid
        with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
            validate_support_entry(entry)


@pytest.mark.parametrize("path", [(), ("support",), ("support", "operands", 0), ("evidence", 0)])
def test_every_object_has_closed_required_fields(path):
    original = support_entry()
    obj = original
    for key in path:
        obj = obj[key]
    fields = list(obj)
    for field in fields + ["extra"]:
        entry, value = deepcopy(original), None
        value = entry
        for key in path:
            value = value[key]
        if field == "extra":
            value[field] = "undeclared"
        else:
            value.pop(field)
        with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
            validate_support_entry(entry)


@pytest.mark.parametrize("path,invalid", [
    (("id",), "A01\n"), (("id",), "P01"), (("id",), "A"),
    (("entry_version",), "scientific_support_entry_v2"),
    (("slot",), "thought_pattern"), (("name",), " \n\t"),
    (("support", "proposition"), ""), (("support", "qualifications"), []),
    (("support", "qualifications"), ["same", "same"]),
    (("support", "operands"), []), (("evidence",), []),
    (("support", "operands", 0, "operand_id"), "two labels"),
    (("support", "operands", 0, "operand_id"), "label\n"),
    (("support", "boundary"), float("nan")),
    (("support", "boundary"), float("inf")),
    (("support", "boundary"), object()),
    (("evidence", 0, "source_locator"), {1: "not JSON"}),
])
def test_malformed_support_has_specific_syntax_failure(path, invalid):
    entry = support_entry()
    value = entry
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = invalid
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)


def test_duplicate_operand_identity_and_duplicate_source_rows_are_invalid():
    entry = support_entry()
    second = deepcopy(entry["support"]["operands"][0])
    second["instruction"] = "Different instruction cannot duplicate an operand ID."
    entry["support"]["operands"].append(second)
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)
    entry = support_entry()
    entry["evidence"].append(deepcopy(entry["evidence"][0]))
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)


@pytest.mark.parametrize("invalid", [["unknown"], ["alignment", "alignment"], "alignment",
    ("alignment",), [None], {"alignment"}, None, [float("nan")]])
def test_route_requests_reject_undeclared_or_duplicate_kind_values(invalid):
    with pytest.raises(ValueError, match="scientific_support_observation_kinds_invalid"):
        annotation_policy_routes(None, None, observation_kinds=invalid)
