"""Per-search target taxonomy stays separate across saved PSI/DELTA results."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
from tests.test_blast_iteration_inputs import make_inputs


def example():
    args = make_inputs()
    for metadata in args["sequence_metadata"]:
        for record in metadata["reference_metadata"]:
            record["lineage"] = [dict(taxid=10, rank="genus", name="synthetic genus")]
    args["target_contexts"] = []
    for index, search in enumerate(args["collection"]["searches"]):
        args["target_contexts"].append(dict(search_key=deepcopy(search["search_key"]),
            target_context=dict(query_operand=deepcopy(search["operand_binding"]),
                taxid=1 if index == 0 else 3,
                lineage=[dict(taxid=10 if index == 0 else 20, rank="genus", name="supplied genus")],
                independent_of_search=True,
                source=dict(source_ref="synthetic:target-metadata", pointer=f"/targets/{index}"))))
    return args


def run(args):
    sheet = populate_blast_iteration_sheet(**args)
    return sheet, calculate_blast_iteration_components(sheet)


def taxonomy(row):
    return row["sequence_components"]["components"]["database_sheet"]["taxonomy"]


def test_distinct_targets_change_only_their_own_comparisons_and_survive_saved_recalculation():
    args = example()
    before = deepcopy(args)
    sheet, result = run(args)
    assert args == before
    assert sheet["schema"] == "blast_iteration_sheet_v2"
    assert result["schema"] == "blast_iteration_components_v2"
    first, second = result["searches"]
    assert first["target_context_qualification"] == dict(status="available", input_indices=[0])
    assert second["target_context_qualification"] == dict(status="available", input_indices=[1])
    for row, expected_taxid, expected_match in ((first, 10, 1.0), (second, 20, 0.0)):
        rank, = taxonomy(row)["ranks"]
        assert rank["target_taxid_at_rank"] == expected_taxid
        assert rank["target_matching_fraction"] == expected_match
        assert rank["unambiguous_group_count"] == 2
        assert row["counts"]["parsed_hsp_count"]["value"] == 2
        assert row["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    saved = json.loads(json.dumps(sheet, allow_nan=False))
    assert calculate_blast_iteration_components(saved) == result
    assert sheet == populate_blast_iteration_sheet(**before)


@pytest.mark.parametrize("mode", ["missing", "null", "duplicate", "conflict"])
def test_unqualified_target_keeps_native_measurements_and_never_borrows_a_sibling(mode):
    args = example()
    first = args["target_contexts"][0]
    if mode == "missing":
        args["target_contexts"].pop(0)
    elif mode == "null":
        first["target_context"] = None
    else:
        duplicate = deepcopy(first)
        if mode == "conflict":
            duplicate["target_context"]["lineage"][0]["taxid"] = 99
        args["target_contexts"].append(duplicate)
    sheet, result = run(args)
    first, second = result["searches"]
    qualification = first["target_context_qualification"]
    assert qualification["status"] == ("incompatible" if mode == "conflict" else "unavailable")
    assert qualification["input_indices"] == ([] if mode == "missing" else [0, 2] if mode in ("duplicate", "conflict") else [0])
    assert taxonomy(first)["ranks"][0]["target_matching_fraction"] is None
    assert taxonomy(second)["ranks"][0]["target_matching_fraction"] == 0.0
    assert first["counts"]["parsed_hsp_count"]["value"] == 2
    assert first["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    if mode in ("duplicate", "conflict"):
        assert len(sheet["target_contexts"]) == 3
        assert any(issue["code"] == "blast_iteration_duplicate_search_association" for issue in first["issues"])
    if mode == "conflict":
        assert any(issue["code"] == "blast_iteration_conflicting_search_association" for issue in first["issues"])


@pytest.mark.parametrize("field,value", [("artifact_key", "different-artifact"), ("member_ordinal", 7),
    ("report_index", 7), ("search_pointer", "/different/search")])
def test_complete_search_address_is_required(field, value):
    args = example()
    args["target_contexts"][0]["search_key"][field] = value
    sheet, result = run(args)
    assert sheet["target_contexts"][0] == args["target_contexts"][0]
    assert result["searches"][0]["target_context_qualification"] == dict(status="unavailable", input_indices=[])
    assert taxonomy(result["searches"][0])["ranks"][0]["target_matching_fraction"] is None
    assert any(issue["code"] == "blast_iteration_orphan_search_key" and issue["details"]["role"] == "target_contexts"
               for issue in result["issues"])


def test_old_global_context_is_retained_only_in_unchanged_v1_contract():
    args = example()
    args["target_context"] = args.pop("target_contexts")[0]["target_context"]
    sheet, result = run(args)
    assert sheet["schema"] == "blast_iteration_sheet_v1" and "target_contexts" not in sheet
    assert result["schema"] == "blast_iteration_components_v1"
    assert all("target_context_qualification" not in row for row in result["searches"])
    assert [taxonomy(row)["ranks"][0]["target_matching_fraction"] for row in result["searches"]] == [1.0, 1.0]


@pytest.mark.parametrize("bad", [False, {}, "bad", [False], [{"search_key": {}, "target_context": {}}]])
def test_invalid_target_context_rows_fail_the_sheet_contract(bad):
    args = example()
    args["target_contexts"] = bad
    with pytest.raises(ValueError):
        populate_blast_iteration_sheet(**args)


def test_v2_rejects_global_fallback_and_nonfinite_fields():
    args = example()
    args["target_context"] = deepcopy(args["target_contexts"][0]["target_context"])
    with pytest.raises(ValueError):
        populate_blast_iteration_sheet(**args)
    args["target_context"] = None
    args["target_contexts"][0]["target_context"]["taxid"] = float("nan")
    with pytest.raises(ValueError, match="finite_json"):
        populate_blast_iteration_sheet(**args)


def test_profile_route_retains_exact_target_without_borrowing_sequence_taxonomy():
    args = make_inputs([["P1"]], program="deltablast", stages=["domain_database"])
    target = dict(taxid=7, lineage=[dict(taxid=70, rank="genus")],
                  independent_of_search=True, source="synthetic:target")
    args["target_contexts"] = [dict(search_key=deepcopy(args["collection"]["searches"][0]["search_key"]),
        target_context=target)]
    sheet, result = run(args)
    row = result["searches"][0]
    assert row["target_context_qualification"] == dict(status="available", input_indices=[0])
    assert row["sequence_components"] is None
    assert row["profile_components"] is not None
    assert sheet["target_contexts"][0]["target_context"] == target
