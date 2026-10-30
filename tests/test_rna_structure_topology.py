"""Literal coordinate/topology oracles, including formerly incorrect loop cases."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.rna_structure_contracts import COORDINATE_SYSTEM, validate_topology
from gene_annotation_episode.rna_structure_topology import parse_rna_topology

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_structure_core_2026-10-26_354"
CASES = json.loads((PACKET / "topology_oracles.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda row: row["name"])
def test_literal_coordinates_stems_and_exposed_regions(case):
    result = parse_rna_topology(case["structure"], coordinate_system=COORDINATE_SYSTEM)
    assert result["status"] == "valid"
    assert [[pair["i"], pair["j"]] for pair in result["pairs"]] == case["pairs"]
    assert [len(stem["pair_keys"]) for stem in result["stems"]] == case["stems"]
    assert [[region["kind"], region["unpaired_indices"]] for region in result["regions"]] == case["regions"]
    assert validate_topology(result) == result
    dots = sorted(i for region in result["regions"] for i in region["unpaired_indices"])
    assert dots == [i for i, symbol in enumerate(case["structure"]) if symbol == "."]
    assert len(dots) == len(set(dots))


def test_immediate_nesting_not_all_descendants_and_exact_side_arrays():
    topology = parse_rna_topology("((.(...)..(...)...))", coordinate_system=COORDINATE_SYSTEM)
    assert topology["pairs"][0]["child_pair_keys"] == ["pair:1:18"]
    assert topology["pairs"][1]["child_pair_keys"] == ["pair:3:7", "pair:10:14"]
    assert topology["pairs"][2]["parent_pair_key"] == "pair:1:18"
    assert topology["regions"][0]["immediate_branch_pair_keys"] == ["pair:3:7", "pair:10:14"]
    assert topology["regions"][0]["unpaired_intervals"] == [[2, 3], [8, 10], [15, 18]]
    assert topology["regions"][0]["five_prime_unpaired_indices"] is None
    internal = parse_rna_topology("((..((...))..))", coordinate_system=COORDINATE_SYSTEM)
    assert internal["regions"][0]["five_prime_unpaired_indices"] == [2, 3]
    assert internal["regions"][0]["three_prime_unpaired_indices"] == [11, 12]
    assert internal["positions"][2]["unpaired_region_key"] == "region:1:13"
    assert internal["positions"][4]["partner_index"] == 10
    assert internal["positions"][4]["stem_key"] == "stem:4:10"


@pytest.mark.parametrize("text,status,code,index", [
    ("", "invalid", "rna_empty_structure", None),
    ("(..", "invalid", "rna_unbalanced_structure", 0),
    (".)", "invalid", "rna_unbalanced_structure", 1),
    ("(]", "invalid", "rna_mismatched_bracket", 1),
    ("([)]", "unsupported", "rna_crossing_pairs_unsupported", 2),
    ("[{].}", "unsupported", "rna_crossing_pairs_unsupported", 2),
    ("..&..", "invalid", "rna_invalid_structure_symbol", 2),
    ("...\n", "invalid", "rna_invalid_structure_symbol", 3),
])
def test_invalid_and_crossing_strings_have_no_completed_arrays(text, status, code, index):
    result = parse_rna_topology(text, coordinate_system=COORDINATE_SYSTEM)
    assert result["dot_bracket"] == text
    assert result["length_nt"] == len(text)
    assert result["status"] == status
    assert result["issues"][0]["code"] == code
    assert result["issues"][0]["index"] == index
    assert all(result[name] is None for name in ("positions", "pairs", "stems", "regions"))
    assert validate_topology(result) == result


@pytest.mark.parametrize("alter", [
    lambda value: value["pairs"][0].update(j=7),
    lambda value: value["pairs"].append(deepcopy(value["pairs"][0])),
    lambda value: value["pairs"][0].update(child_pair_keys=["pair:2:6"]),
    lambda value: value["positions"][0].update(partner_index=7),
    lambda value: value["stems"][0].update(pair_keys=["pair:0:8"]),
    lambda value: value["regions"][0].update(unpaired_intervals=[[3, 5]]),
    lambda value: value.update(length_nt=9.0),
])
def test_complete_topology_tables_are_cross_checked(alter):
    topology = parse_rna_topology("(((...)))", coordinate_system=COORDINATE_SYSTEM)
    alter(topology)
    with pytest.raises(ValueError, match="rna_topology_table_mismatch"):
        validate_topology(topology)


def test_wrong_coordinate_convention_is_not_silently_converted():
    with pytest.raises(ValueError, match="rna_invalid_input_schema"):
        parse_rna_topology("(...)", coordinate_system="one_based")
