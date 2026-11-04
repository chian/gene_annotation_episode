"""Native CodonTree tests: one historical artifact and source-derived fixtures.

Current fixtures reproduce the pinned writer syntax. They are not outputs of a
live service run, and the upstream program is never imported or executed here.
"""

from copy import deepcopy
import builtins
import hashlib
import io
import inspect
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

import gene_annotation_episode.bvbrc_codon_tree_native as native
import gene_annotation_episode.phylogeny_format_contracts as formats
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract


STAGING = Path(__file__).resolve().parents[1]
VERIFICATION = Path(__file__).resolve().parents[3]
HISTORICAL_MEMBERSHIP = (
    VERIFICATION / "tool_graders_bvbrc_phylogeny_boundaries_2026-10-24/official_example"
    / "test9_genome_dir/test9_genome_8taxa_10cds_10proteins.pgfamsAndGenesIncludedInAlignment.txt"
)

# These four fixtures follow the *complete* pinned current writer's syntax,
# including its final newlines, empty tab field and fused statistics header.
CURRENT_MEMBERSHIP = (
    "PGF_1\tProteins\t\tfig|g1.peg.1\tfig|g2.peg.2\tdeletedParalogs: \tfig|g1.peg.3\n"
    "PGF_1\tCodons\t\tfig|g1.peg.1\tlacking CodonAlignment for PGF_1: \tfig|g2.peg.2\n"
    "PGF_2\tProteins\t\tfig|g1.peg.4\n"
    "PGF_2\nNo codon alignment PGF_2\n\n"
).encode()
FAMILY_HEADER = b"PGFam\tgaps\tsum_squared_freq\tmean_squared_freq\tnum_pos\tnum_seqs\tworstSeqScoreused_in_tree\n"
CURRENT_FAMILY_STATISTICS = FAMILY_HEADER + (
    "PGF_1\t2\t3.25\t0.8125\t4\t2\t2.0\tTrue\n"
    "PGF_2\t0\t0\t0\t0\t0\tna\tFalse\n"
    "disqualification: low alignment score\n"
    "PGF_3\t3\t1.5\t0.5\t3\t2\t9.0\tFalse\n"
    "bad seqs: {'g/1': 9.0}\n"
    "disqualification: bad seqs\n"
).encode()
GENOME_HEADER = b"Genome\tAllGenes\tSingleCopy\tFiltered_SingleCopy\n"
CURRENT_GENOME_COUNTS = GENOME_HEADER + b"g0\t0\t0\t0\ng1\t12\t8\t3\ng2\t15\t9\t2\n"
ANALYSIS_HEADER = b"Statistics for CodonTree Analysis\n"
CURRENT_ANALYSIS_STATISTICS = ANALYSIS_HEADER + (
    "Num_genomes\t2\nNum_protein_alignments\t2\nNum_aligned_amino_acids\t4\n"
    "Num_CDS_alignments\t2\nNum_aligned_nucleotides\t12\n"
    "PGFams\tPGF_1,PGF_2\n"
    "command_line\traxmlHPC -f I -t tree.nwk -n rooted\n"
    "Total job duration 17 seconds\n"
).encode()


def artifact(data, identity="raw/codon-native"):
    return {"raw_artifact_ref": identity, "source_ref": "source/native-test",
            "sha256": hashlib.sha256(data).hexdigest()}


def membership(data, dialect="homologs_current", **kwargs):
    return native.parse_codon_membership(data, artifact=kwargs.get("artifact", artifact(data)), dialect=dialect)


def families(data, dialect="current_missing_header_tab", **kwargs):
    return native.parse_codon_family_statistics(data, artifact=kwargs.get("artifact", artifact(data)), dialect=dialect)


def genomes(data, **kwargs):
    return native.parse_codon_genome_counts(data, artifact=kwargs.get("artifact", artifact(data)))


def analysis(data, dialect="retained_current_source", **kwargs):
    return native.parse_codon_analysis_statistics(data, artifact=kwargs.get("artifact", artifact(data)), dialect=dialect)


PARSERS = (
    (membership, CURRENT_MEMBERSHIP, "codon_membership"),
    (families, CURRENT_FAMILY_STATISTICS, "codon_family_statistics"),
    (genomes, CURRENT_GENOME_COUNTS, "codon_genome_counts"),
    (analysis, CURRENT_ANALYSIS_STATISTICS, "codon_analysis_statistics"),
)


def codes(result):
    return {row["code"] for row in result["diagnostics"]}


def observations(result, field):
    return [row for row in result["value"]["observations"] if row["field"] == field]


def assert_locations(data, result):
    value = result["value"]
    for row in value["table"]["rows"]:
        location = row["location"]
        start, end = location["byte_start_0based"], location["byte_end_0based_exclusive"]
        assert data[start:end].decode("utf-8") == row["raw_text"]
        assert location["line_start_1based"] == data[:start].count(b"\n") + 1
        assert location["line_end_1based_inclusive"] == location["line_start_1based"]
        assert location["artifact"] == artifact(data)
    for observed in value.get("observations", []):
        location = observed["location"]
        assert data[location["byte_start_0based"]:location["byte_end_0based_exclusive"]].decode("utf-8") == observed["raw_token"]
        assert location["line_start_1based"] == data[:location["byte_start_0based"]].count(b"\n") + 1
    for command in value.get("commands", []):
        location = command["location"]
        assert data[location["byte_start_0based"]:location["byte_end_0based_exclusive"]].decode("utf-8") == command["raw_text"]


def test_import_is_exact_owned_staged_module():
    assert Path(native.__file__).resolve() == STAGING / "gene_annotation_episode/bvbrc_codon_tree_native.py"
    assert Path(formats.__file__).resolve() == STAGING / "gene_annotation_episode/phylogeny_format_contracts.py"


def test_exact_public_signatures_cannot_accept_caller_invented_native_facts():
    for function in (native.parse_codon_membership, native.parse_codon_family_statistics,
                     native.parse_codon_analysis_statistics):
        signature = inspect.signature(function)
        assert list(signature.parameters) == ["data", "artifact", "dialect"]
        assert signature.parameters["artifact"].kind is inspect.Parameter.KEYWORD_ONLY
        assert signature.parameters["dialect"].kind is inspect.Parameter.KEYWORD_ONLY
    assert list(inspect.signature(native.parse_codon_genome_counts).parameters) == ["data", "artifact"]


def test_complete_historical_native_membership_twenty_rows_not_ten():
    data = HISTORICAL_MEMBERSHIP.read_bytes()
    result = membership(data, "pgfams_legacy")
    assert result["status"] == "ok" and result["diagnostics"] == []
    value = result["value"]
    assert value["table"]["completeness"] == "complete"
    assert len(value["rows"]) == 20
    assert len({row["family_id"] for row in value["rows"]}) == 10
    assert sum(row["representation"] == "protein" for row in value["rows"]) == 10
    assert sum(row["representation"] == "coding_nucleotide" for row in value["rows"]) == 10
    assert all(len(row["included_feature_ids"]) == 8 for row in value["rows"])
    assert len(value["table"]["rows"]) == 30
    assert len([row for row in value["table"]["rows"] if row["record_kind"] == "other_retained"]) == 10
    assert [r["source_row_index"] for r in value["rows"]] == [n for n in range(30) if n % 3 != 2]
    assert value["rows"][0]["included_feature_ids"] == [
        "fig|1075089.3.peg.399", "fig|1171377.3.peg.661", "fig|1222034.3.peg.710",
        "fig|1232659.5.peg.254", "fig|1249526.3.peg.657", "fig|1249531.3.peg.2101",
        "fig|1261658.3.peg.624", "fig|1263829.3.peg.1537",
    ]
    assert value["missing_codon_family_ids"] == []
    assert_locations(data, result)


def test_current_membership_markers_and_missing_family_have_exact_association():
    result = membership(CURRENT_MEMBERSHIP)
    assert result["status"] == "ok" and result["diagnostics"] == []
    value = result["value"]
    assert value["rows"] == [
        {"family_id": "PGF_1", "representation": "protein", "included_feature_ids": ["fig|g1.peg.1", "fig|g2.peg.2"],
         "deleted_feature_ids": ["fig|g1.peg.3"], "missing_codon_feature_ids": [], "source_row_index": 0},
        {"family_id": "PGF_1", "representation": "coding_nucleotide", "included_feature_ids": ["fig|g1.peg.1"],
         "deleted_feature_ids": [], "missing_codon_feature_ids": ["fig|g2.peg.2"], "source_row_index": 1},
        {"family_id": "PGF_2", "representation": "protein", "included_feature_ids": ["fig|g1.peg.4"],
         "deleted_feature_ids": [], "missing_codon_feature_ids": [], "source_row_index": 2},
    ]
    assert value["missing_codon_family_ids"] == ["PGF_2"]
    assert value["table"]["rows"][3]["record_kind"] == "missing_codon_alignment"
    assert value["table"]["rows"][4]["family_id"] == "PGF_2"
    assert value["table"]["rows"][5]["record_kind"] == "other_retained"
    assert_locations(CURRENT_MEMBERSHIP, result)


@pytest.mark.parametrize("line", [
    b"F\tProteins\t\ta\tunrecognizedMarker: \tb\n",
    b"F\tProteins\t\ta\tdeletedParalogs:\tb\n",
    b"F\tCodons\t\ta\tlacking CodonAlignment for Other: \tb\n",
    b"F\tProteins\ta\n", b"F\tProteins\t\ta\t\n",
    b"F\tOtherRepresentation\t\ta\n",
])
def test_unknown_membership_marker_or_bad_syntax_cannot_become_feature(line):
    result = membership(line + b"G\tProteins\t\tb\n")
    assert result["status"] == "partial"
    assert len(result["value"]["rows"]) == 1
    assert result["value"]["rows"][0]["family_id"] == "G"
    assert result["value"]["table"]["rows"][0]["raw_text"] == line.decode().rstrip("\n")
    assert result["value"]["table"]["rows"][0]["record_kind"] == "other_retained"


def test_membership_duplicate_features_and_conflicting_records_are_preserved():
    data = b"F\tProteins\t\ta\ta\nF\tProteins\t\ta\ta\nF\tProteins\t\tb\n"
    result = membership(data)
    assert result["status"] == "partial"
    assert len(result["value"]["rows"]) == 3
    assert result["value"]["rows"][0]["included_feature_ids"] == ["a", "a"]
    assert {"codon_duplicate_feature_id", "codon_duplicate_membership_record", "codon_conflicting_membership_record"} <= codes(result)


@pytest.mark.parametrize("data,code", [
    (b"F\nNo codon alignment G\n", "codon_missing_family_mismatch"),
    (b"No codon alignment F\n", "codon_orphan_missing_family"),
    (b"F\n\nNo codon alignment F\n", "codon_unpaired_family_line"),
    (b"F\tProteins\t\ta\nNo codon alignment F\n", "codon_orphan_missing_family"),
    (b"F\n", "codon_unpaired_family_line"),
])
def test_missing_codon_continuation_does_not_attach_to_unrelated_family(data, code):
    result = membership(data)
    assert code in codes(result)
    assert result["value"]["missing_codon_family_ids"] == []


def test_conflicting_missing_codon_family_and_overlap_are_qualified():
    result = membership(b"F\nNo codon alignment F\nF\nNo codon alignment F\nF\tCodons\t\ta\tlacking CodonAlignment for F: \ta\n")
    assert result["status"] == "partial"
    assert result["value"]["missing_codon_family_ids"] == ["F", "F"]
    assert {"codon_conflicting_missing_family", "codon_duplicate_missing_family", "codon_membership_feature_overlap"} <= codes(result)


def test_source_derived_family_statistics_are_populated_with_native_units_and_methods():
    result = families(CURRENT_FAMILY_STATISTICS)
    assert result["status"] == "ok"
    value = result["value"]
    assert value["header_defect"] == "missing_tab_before_used_in_tree"
    assert value["table"]["header_tokens"][-1] == "worstSeqScoreused_in_tree"
    assert value["rows"][0]["used_in_tree"] is True
    assert value["rows"][1]["used_in_tree"] is False
    assert value["rows"][1]["disqualification"] == "low alignment score"
    assert value["rows"][2]["bad_sequence_values"] == [{"genome_id": "g/1", "value": 9.0}]
    assert value["rows"][2]["source_row_indices"] == [3, 4, 5]
    assert value["rows"][2]["disqualification"] == "bad seqs"
    first = value["observations"][:6]
    assert [o["value"] for o in first] == [2, 3.25, 0.8125, 4, 2, 2.0]
    assert [o["unit"] for o in first] == ["characters", "column_summed_squared_fraction", "mean_squared_fraction", "columns", "sequences", "ratio"]
    assert all(o["method"] == "codon_tree_native_pretrim_statistics" for o in value["observations"])
    assert not any(o["field"] == "family_native_ranking_score" for o in value["observations"])
    assert observations(result, "family_native_gaps")[1]["value"] == 0
    missing = observations(result, "family_native_worst_sequence_ratio")[1]
    assert missing["value"] is None and missing["state"] == "missing" and missing["raw_token"] == "na"
    assert_locations(CURRENT_FAMILY_STATISTICS, result)


@pytest.mark.parametrize("header", [
    FAMILY_HEADER.replace(b"worstSeqScoreused_in_tree", b"worstSeqScore\tused_in_tree"),
    FAMILY_HEADER.replace(b"mean_squared_freq", b"meanSquaredFreq"),
    FAMILY_HEADER.replace(b"PGFam", b"PGFams"),
    b"", b"arbitrary header\n",
])
def test_only_exact_source_header_defect_is_accepted(header):
    result = families(header + b"F\t0\t1\t1\t1\t1\t1\tTrue\n")
    assert result["status"] == "invalid" and result["value"] is None
    assert "codon_header_incompatible" in codes(result)


@pytest.mark.parametrize("token", [b"-1", b"1.0", b"1e2", b"nan", b"inf", b"True", b"", b" 1", b"1 "])
def test_bad_native_count_is_failed_without_losing_valid_cells(token):
    result = families(FAMILY_HEADER + b"F\t" + token + b"\t1.5\t0.5\t3\t2\t1.0\tTrue\n")
    assert result["status"] == "partial"
    values = result["value"]["observations"]
    assert values[0]["state"] == "failed" and values[0]["value"] is None
    assert values[0]["raw_token"] == token.decode()
    assert values[1]["value"] == 1.5 and values[3]["value"] == 3
    assert "codon_native_count_invalid" in codes(result)


@pytest.mark.parametrize("token", [b"nan", b"NaN", b"inf", b"-inf", b"1e309", b"not-a-number", b""])
def test_nonfinite_or_malformed_native_statistic_is_failed(token):
    result = families(FAMILY_HEADER + b"F\t0\t" + token + b"\t0.5\t3\t2\t1.0\tTrue\n")
    assert result["status"] == "partial"
    failed = observations(result, "family_native_sum_squared_freq")[0]
    assert failed["value"] is None and failed["state"] == "failed" and failed["raw_token"] == token.decode()
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("token,expected", [
    ("1e-999", None), ("-1e-999", None), ("+1e-999", None),
    ("2e-324", None), ("-2e-324", None), ("0." + "0" * 400 + "1", None),
    ("0", 0.0), ("-0", -0.0), ("+0", 0.0),
    ("0e-999", 0.0), ("-0.000e-999", -0.0), ("+0e+999", 0.0),
    ("5e-324", 5e-324), ("-5e-324", -5e-324),
    ("1.25", 1.25), ("-2.5", -2.5), ("+2.5", 2.5),
    (" 0", None), ("0 ", None), ("1_000.0", None), ("0x0", None),
])
def test_native_float_token_limits_preserve_state_and_original_source(token, expected):
    data = FAMILY_HEADER + f"F\t0\t{token}\t{token}\t3\t2\t{token}\tTrue\n".encode()
    result = families(data)
    assert result["status"] == ("partial" if expected is None else "ok")
    values = result["value"]["observations"]
    assert [values[index]["value"] for index in (0, 3, 4)] == [0, 3, 2]
    for field in ("family_native_sum_squared_freq", "family_native_mean_squared_freq",
                  "family_native_worst_sequence_ratio"):
        observed = observations(result, field)[0]
        assert observed["raw_token"] == token
        assert observed["value"] == expected
        assert observed["state"] == ("failed" if expected is None else "available")
        if expected is not None:
            assert math.copysign(1, observed["value"]) == math.copysign(1, expected)
    invalid = [d for d in result["diagnostics"] if d["code"] == "codon_native_number_invalid"]
    assert len(invalid) == (3 if expected is None else 0)
    assert all(d["phase"] == "native_decode" and d["severity"] == "error" for d in invalid)
    assert_locations(data, result)
    json.dumps(result, allow_nan=False)


def test_negative_finite_statistics_and_missing_boolean_are_not_clamped_or_scored():
    result = families(FAMILY_HEADER + b"F\t0\t-2.5\t-0.5\t5\t2\t-0.0\tna\n")
    assert result["status"] == "ok"
    assert [o["value"] for o in result["value"]["observations"]] == [0, -2.5, -0.5, 5, 2, -0.0]
    assert result["value"]["rows"][0]["used_in_tree"] is None
    assert "codon_boolean_missing" in codes(result)
    invalid = families(FAMILY_HEADER + b"F\t0\t1\t1\t1\t1\t1\t1\n")
    assert invalid["status"] == "partial"
    assert invalid["value"]["rows"][0]["used_in_tree"] is None
    assert "codon_boolean_invalid" in codes(invalid)


def test_malformed_family_rows_are_raw_only_and_orphan_continuations_do_not_reassociate():
    data = FAMILY_HEADER + (
        b"bad seqs: {'orphan': 9}\n"
        b"F\t0\t1\t1\t1\t1\t1\tTrue\n"
        b"broken\t1\n"
        b"disqualification: bad seqs\n"
        b"G\t0\t1\t1\t1\t1\t1\tFalse\n"
        b"disqualification: unclassified reason\n"
    )
    result = families(data)
    assert result["status"] == "partial"
    assert len(result["value"]["rows"]) == 2
    assert result["value"]["rows"][0]["source_row_indices"] == [1]
    assert result["value"]["rows"][0]["disqualification"] is None
    assert result["value"]["rows"][1]["source_row_indices"] == [4, 5]
    assert result["value"]["rows"][1]["disqualification"] is None
    assert {"codon_orphan_qualifier", "codon_malformed_row", "codon_unknown_disqualification"} <= codes(result)


@pytest.mark.parametrize("mapping", [
    "{'g': __import__('os').system('false')}", "{'g': float('inf')}",
    "{'g': {'nested': 1}}", "{'g': [1]}", "{'g': True}",
    "{'g': None}", "{'g': 1e309}", "{'g': -1e309}", "{1: 9}",
    "dict(g=9)", "{'g': 1 + 2}", "{**{'g': 9}}", "{'g': --1}",
    "{'g': nan}", "[('g', 9)]", "{'g': 9", "{g: 9 for g in ['a']}",
])
def test_bad_sequence_mapping_rejects_all_executable_nested_or_nonfinite_values(mapping):
    data = FAMILY_HEADER + b"F\t0\t1\t1\t1\t1\t9\tFalse\n" + ("bad seqs: " + mapping + "\n").encode()
    result = families(data)
    assert result["status"] == "partial"
    assert result["value"]["rows"][0]["bad_sequence_values"] == []
    assert "codon_bad_sequence_map_invalid" in codes(result)
    assert result["value"]["table"]["rows"][1]["raw_text"] == "bad seqs: " + mapping
    assert len(result["value"]["observations"]) == 6


def test_bad_sequence_mapping_detects_duplicate_keys_before_overwrite():
    data = FAMILY_HEADER + b"F\t0\t1\t1\t1\t1\t9\tFalse\nbad seqs: {'g': 9, 'g': 10}\n"
    result = families(data)
    assert "codon_bad_sequence_duplicate_key" in codes(result)
    assert result["value"]["rows"][0]["bad_sequence_values"] == []
    diagnostic = next(d for d in result["diagnostics"] if d["code"] == "codon_bad_sequence_duplicate_key")
    assert diagnostic["phase"] == "association"


def test_scalar_map_preserves_order_signed_values_zero_and_quoted_keys():
    data = FAMILY_HEADER + b"F\t0\t1\t1\t1\t1\t9\tFalse\nbad seqs: {'z': -2.5, 'g\\\'1': +9.0, 'zero': 0}\n"
    result = families(data)
    assert result["status"] == "ok"
    assert result["value"]["rows"][0]["bad_sequence_values"] == [
        {"genome_id": "z", "value": -2.5}, {"genome_id": "g'1", "value": 9.0}, {"genome_id": "zero", "value": 0},
    ]


@pytest.mark.parametrize("token", [
    "1e-999", "-1e-999", "+1e-999", "2e-324", "-2e-324",
    "0." + "0" * 400 + "1", "(1e-999)", "- (1e-999)", "+ 1e-999",
])
def test_scalar_map_underflow_is_raw_only_without_losing_independent_values(token):
    qualifier = f"bad seqs: {{'good': 9.0, 'gé/α': {token}}}"
    data = FAMILY_HEADER + (
        "F\t0\t1\t1\t1\t1\t9\tFalse\n" + qualifier + "\n"
        "G\t0\t1\t1\t1\t1\t8\tFalse\n"
        "bad seqs: {'valid': -2.5}\n"
    ).encode()
    result = families(data)
    assert result["status"] == "partial"
    assert result["value"]["rows"][0]["bad_sequence_values"] == []
    assert result["value"]["rows"][1]["bad_sequence_values"] == [{"genome_id": "valid", "value": -2.5}]
    assert result["value"]["table"]["rows"][1]["raw_text"] == qualifier
    assert result["value"]["rows"][0]["source_row_indices"] == [0, 1]
    assert len(result["value"]["observations"]) == 12
    assert all(o["state"] == "available" for o in result["value"]["observations"])
    invalid = [d for d in result["diagnostics"] if d["code"] == "codon_bad_sequence_map_invalid"]
    assert invalid == [{"code": "codon_bad_sequence_map_invalid", "phase": "native_decode",
                        "path": "/value/table/rows/1", "severity": "error", "evidence_refs": []}]
    assert_locations(data, result)
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("token,expected", [
    ("0", 0), ("+0", 0), ("-0", 0), ("0.0", 0.0),
    ("+0.0", 0.0), ("-0.0", -0.0), ("0e-999", 0.0),
    ("+0.000e-999", 0.0), ("-0.000e-999", -0.0), ("-0e+999", -0.0),
    ("5e-324", 5e-324), ("-5e-324", -5e-324),
    ("+9.5", 9.5), ("- 2.5", -2.5), ("(-2.5)", -2.5),
    ("9007199254740993", 9007199254740993), ("1" + "0" * 400, 10 ** 400),
])
def test_scalar_map_native_signed_scalars_and_explicit_zero_remain_valid(token, expected):
    qualifier = f"bad seqs: {{'gé/α': {token}}}"
    data = FAMILY_HEADER + ("F\t0\t1\t1\t1\t1\t9\tFalse\n" + qualifier + "\n").encode()
    result = families(data)
    assert result["status"] == "ok"
    values = result["value"]["rows"][0]["bad_sequence_values"]
    assert values == [{"genome_id": "gé/α", "value": expected}]
    assert type(values[0]["value"]) is type(expected)
    if type(expected) is float:
        assert math.copysign(1, values[0]["value"]) == math.copysign(1, expected)
    assert result["value"]["table"]["rows"][1]["raw_text"] == qualifier
    assert_locations(data, result)
    json.dumps(result, allow_nan=False)


def test_duplicate_family_records_preserve_every_row_and_observation():
    line = b"F\t0\t1\t1\t1\t1\t9\tFalse\n"
    result = families(FAMILY_HEADER + line + line + b"disqualification: bad seqs\n")
    assert len(result["value"]["rows"]) == 2 and len(result["value"]["observations"]) == 12
    assert "codon_conflicting_family_record" in codes(result)
    assert len({o["observation_id"] for o in result["value"]["observations"]}) == 12
    same = families(FAMILY_HEADER + line + line)
    assert "codon_duplicate_family_record" in codes(same)


def test_repeated_conflicting_qualifiers_never_overwrite_a_resolved_reason():
    data = FAMILY_HEADER + (
        b"F\t0\t1\t1\t1\t1\t9\tFalse\n"
        b"bad seqs: {'g': 9}\nbad seqs: {'g': 10}\n"
        b"disqualification: bad seqs\ndisqualification: low alignment score\ndisqualification: bad seqs\n"
    )
    result = families(data)
    assert result["status"] == "partial"
    row = result["value"]["rows"][0]
    assert row["bad_sequence_values"] == [{"genome_id": "g", "value": 9}, {"genome_id": "g", "value": 10}]
    assert row["disqualification"] is None
    assert row["source_row_indices"] == list(range(6))


def test_genome_counts_are_populated_family_units_with_zero_preserved():
    result = genomes(CURRENT_GENOME_COUNTS)
    assert result["status"] == "ok" and result["diagnostics"] == []
    assert len(result["value"]["observations"]) == 9
    assert [o["value"] for o in result["value"]["observations"]] == [0, 0, 0, 12, 8, 3, 15, 9, 2]
    assert [row["genome_id"] for row in result["value"]["rows"]] == ["g0", "g1", "g2"]
    assert all(o["unit"] == "families" and o["method"] == "codon_tree_native_genome_family_counts" for o in result["value"]["observations"])
    assert_locations(CURRENT_GENOME_COUNTS, result)


def test_genome_count_failures_and_duplicate_conflicts_are_not_overwritten():
    data = GENOME_HEADER + b"g\t10\t8\t3\ng\t10\t8\t3\ng\t11\t8\t3\nh\t-1\t2.5\tna\ni\t1\t2\t3\nbroken\t4\n"
    result = genomes(data)
    assert result["status"] == "partial"
    assert len(result["value"]["rows"]) == 5
    assert len(result["value"]["observations"]) == 15
    assert {"codon_duplicate_genome_record", "codon_conflicting_genome_record", "codon_native_count_invalid",
            "codon_native_number_missing", "codon_count_stage_order_conflict", "codon_malformed_row"} <= codes(result)
    assert [o["state"] for o in result["value"]["observations"][9:12]] == ["failed", "failed", "missing"]


def test_genome_header_must_match_exactly():
    result = genomes(CURRENT_GENOME_COUNTS.replace(b"AllGenes", b"AllCDS"))
    assert result["status"] == "invalid" and result["value"] is None
    assert "codon_header_incompatible" in codes(result)


def test_analysis_reported_counts_keep_source_field_and_cds_defect():
    result = analysis(CURRENT_ANALYSIS_STATISTICS)
    assert result["status"] == "ok"
    value = result["value"]
    assert [o["value"] for o in value["observations"]] == [2, 2, 4, 2, 12]
    assert [o["subject_id"] for o in value["observations"]] == [
        "Num_genomes", "Num_protein_alignments", "Num_aligned_amino_acids", "Num_CDS_alignments", "Num_aligned_nucleotides",
    ]
    assert all(o["field"] == "analysis_native_reported_counts" and o["unit"] == "reported_count"
               and o["method"] == "codon_tree_native_analysis_report" for o in value["observations"])
    assert "codon_reported_cds_uses_protein_count" in codes(result)
    assert value["commands"][0]["role"] == "unknown"
    assert value["commands"][0]["origin"] == "observed"
    assert value["commands"][0]["argv"] == ["raxmlHPC", "-f", "I", "-t", "tree.nwk", "-n", "rooted"]
    assert value["uninterpreted_source_row_indices"] == [5, 7]
    assert value["table"]["rows"][7]["raw_text"] == "Total job duration 17 seconds"
    assert_locations(CURRENT_ANALYSIS_STATISTICS, result)


def test_analysis_cds_count_never_substituted_from_protein_count_or_other_stage():
    data = CURRENT_ANALYSIS_STATISTICS.replace(b"Num_CDS_alignments\t2", b"Num_CDS_alignments\tna")
    result = analysis(data)
    assert result["value"]["observations"][1]["value"] == 2
    assert result["value"]["observations"][3]["value"] is None
    assert result["value"]["observations"][3]["state"] == "missing"


@pytest.mark.parametrize("flag", ["a", "b", "I", "D"])
def test_command_quoted_arguments_are_tokenized_but_role_remains_unknown(flag):
    command = f'raxml -f {flag} -s "data with spaces.afa" -n \'$(touch ignored)\''
    data = CURRENT_ANALYSIS_STATISTICS.replace(b"raxmlHPC -f I -t tree.nwk -n rooted", command.encode())
    result = analysis(data)
    observed = result["value"]["commands"][0]
    assert observed["raw_text"] == command
    assert observed["argv"] == ["raxml", "-f", flag, "-s", "data with spaces.afa", "-n", "$(touch ignored)"]
    assert observed["role"] == "unknown"


def test_bad_command_and_analysis_records_preserve_independent_measurements():
    data = CURRENT_ANALYSIS_STATISTICS.replace(b"raxmlHPC -f I -t tree.nwk -n rooted", b"raxml 'unterminated")
    data += b"Num_genomes\t2\nNum_genomes\t3\nNum_genomes\t-2\nNum_aligned_nucleotides\t12\textra\nUnknown\t8\n"
    result = analysis(data)
    assert result["status"] == "partial"
    assert result["value"]["commands"][0]["argv"] is None
    assert result["value"]["commands"][0]["raw_text"] == "raxml 'unterminated"
    assert len(result["value"]["observations"]) == 8
    assert result["value"]["observations"][-1]["state"] == "failed"
    assert {"codon_command_tokenization_failed", "codon_duplicate_analysis_field", "codon_conflicting_analysis_field",
            "codon_native_count_invalid", "codon_malformed_row", "codon_unrecognized_row"} <= codes(result)


def test_partial_analysis_report_does_not_claim_empty_success_or_complete_final_population():
    result = analysis(ANALYSIS_HEADER + b"Num_genomes\t0\n")
    assert result["status"] == "partial"
    assert result["value"]["table"]["completeness"] == "partial"
    assert result["value"]["observations"][0]["value"] == 0
    assert "codon_analysis_expected_field_missing" in codes(result)


@pytest.mark.parametrize("parse,data,suffix", PARSERS)
def test_closed_shapes_identities_byte_locations_and_input_immutability(parse, data, suffix):
    supplied = artifact(data)
    before = deepcopy(supplied)
    result = parse(data, artifact=supplied)
    assert supplied == before
    assert result == parse(data, artifact=supplied)
    assert set(result) == {"status", "value", "diagnostics"}
    table = result["value"]["table"]
    assert set(table) == {"table_id", "artifact", "dialect", "header_tokens", "rows", "completeness"}
    assert table["table_id"] == "raw/codon-native#" + suffix
    assert table["artifact"] == supplied
    for index, row in enumerate(table["rows"]):
        assert set(row) == {"row_index", "record_kind", "raw_text", "fields", "family_id", "location"}
        assert row["row_index"] == index
        assert set(row["location"]) == {"artifact", "byte_start_0based", "byte_end_0based_exclusive", "line_start_1based", "line_end_1based_inclusive", "xml_path"}
        assert row["fields"] == row["raw_text"].split("\t")
    for observation in result["value"].get("observations", []):
        assert set(observation) == {"observation_id", "field", "value", "raw_token", "state", "unit", "population_id", "subject_id",
                                    "method", "location", "evidence", "uncertainty", "requirement_ids"}
        index = next(row["row_index"] for row in table["rows"]
                     if row["location"]["line_start_1based"] == observation["location"]["line_start_1based"])
        assert observation["observation_id"] == table["table_id"] + f'/row/{index}/' + observation["field"]
        assert observation["evidence"] == [] and observation["requirement_ids"] == [] and observation["uncertainty"] is None
    for command in result["value"].get("commands", []):
        assert set(command) == {"command_id", "role", "argv", "raw_text", "origin", "evidence", "location"}
    for diagnostic in result["diagnostics"]:
        assert set(diagnostic) == {"code", "phase", "path", "severity", "evidence_refs"}
        assert diagnostic["code"] in native.DIAGNOSTIC_CODES
        assert diagnostic["phase"] in {"native_decode", "association"}
        assert diagnostic["severity"] in {"qualification", "error"}
        validate_contract("Diagnostic", diagnostic)
    assert_locations(data, result)
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    table["artifact"]["source_ref"] = "mutated result"
    assert supplied == before


def test_reader_specific_closed_records_and_all_native_references_resolve():
    membership_value = membership(CURRENT_MEMBERSHIP)["value"]
    family_value = families(CURRENT_FAMILY_STATISTICS)["value"]
    genome_value = genomes(CURRENT_GENOME_COUNTS)["value"]
    analysis_value = analysis(CURRENT_ANALYSIS_STATISTICS)["value"]
    assert set(membership_value) == {"table", "rows", "missing_codon_family_ids"}
    assert set(family_value) == {"table", "rows", "observations", "header_defect"}
    assert set(genome_value) == {"table", "rows", "observations"}
    assert set(analysis_value) == {"table", "observations", "commands", "uninterpreted_source_row_indices"}
    for row in membership_value["rows"]:
        assert set(row) == {"family_id", "representation", "included_feature_ids", "deleted_feature_ids",
                            "missing_codon_feature_ids", "source_row_index"}
        source = membership_value["table"]["rows"][row["source_row_index"]]
        assert source["family_id"] == row["family_id"] and source["record_kind"] == "data"
    family_observations = {o["observation_id"]: o for o in family_value["observations"]}
    for row in family_value["rows"]:
        assert set(row) == {"family_id", "observation_ids", "used_in_tree", "bad_sequence_values",
                            "disqualification", "source_row_indices"}
        assert len(row["observation_ids"]) == 6
        for ref in row["observation_ids"]:
            assert family_observations[ref]["subject_id"] == row["family_id"]
        for index in row["source_row_indices"]:
            assert family_value["table"]["rows"][index]["family_id"] == row["family_id"]
        for bad in row["bad_sequence_values"]:
            assert set(bad) == {"genome_id", "value"}
    genome_observations = {o["observation_id"]: o for o in genome_value["observations"]}
    for row in genome_value["rows"]:
        assert set(row) == {"genome_id", "all_families_observation_id", "single_copy_observation_id",
                            "filtered_single_copy_observation_id"}
        for field in ("all_families_observation_id", "single_copy_observation_id", "filtered_single_copy_observation_id"):
            assert genome_observations[row[field]]["subject_id"] == row["genome_id"]


def test_literal_line_controls_do_not_manufacture_extra_physical_rows():
    data = GENOME_HEADER + b"g1\t3\t2\t1\nunknown\x0bcontent\rretained\n" + "g\u2028x\t2\t1\t0\n".encode()
    result = genomes(data)
    assert len(result["value"]["table"]["rows"]) == 3
    assert len(result["value"]["rows"]) == 1
    assert_locations(data, result)


def test_non_byte_inputs_are_rejected_without_conversion():
    for function, options in (
        (native.parse_codon_membership, {"dialect": "homologs_current"}),
        (native.parse_codon_family_statistics, {"dialect": "current_missing_header_tab"}),
        (native.parse_codon_genome_counts, {}),
        (native.parse_codon_analysis_statistics, {"dialect": "retained_current_source"}),
    ):
        for data in (None, "contents", bytearray(b"bytes"), [1, 2]):
            result = function(data, artifact=artifact(b"bytes"), **options)
            assert result["status"] == "invalid" and result["value"] is None
            assert codes(result) == {"codon_data_type_invalid"}


def test_population_identifier_escaping_is_unambiguous_and_unicode_offsets_are_original_bytes():
    data = FAMILY_HEADER + "fam/é%2F\t0\t1.5\t0.5\t3\t2\t1\tTrue\n\nother retained\n".encode()
    result = families(data)
    observed = result["value"]["observations"][0]
    assert observed["subject_id"] == "fam/é%2F"
    assert observed["population_id"].endswith("/population/family/fam%2F%C3%A9%252F")
    assert result["value"]["table"]["rows"][1]["record_kind"] == "other_retained"
    assert result["value"]["table"]["rows"][2]["record_kind"] == "other_retained"
    assert_locations(data, result)
    counts = genomes(GENOME_HEADER + "g/é%2F\t3\t2\t1\n".encode())
    assert counts["value"]["observations"][0]["population_id"].endswith("/population/genome/g%2F%C3%A9%252F")


@pytest.mark.parametrize("parse,data,suffix", PARSERS)
def test_crlf_locations_retain_original_bytes_without_changing_native_tokens(parse, data, suffix):
    data = data.replace(b"\n", b"\r\n")
    result = parse(data)
    assert result["status"] == "ok"
    assert_locations(data, result)


@pytest.mark.parametrize("parse,data,suffix", PARSERS)
def test_artifact_validation_hash_precedes_decode_and_rejects_extra_caller_facts(parse, data, suffix):
    invalid = artifact(data)
    invalid["sha256"] = "0" * 64
    result = parse(b"\xff", artifact=invalid)
    assert result["status"] == "invalid" and result["value"] is None
    assert codes(result) == {"codon_hash_mismatch"}
    assert result["diagnostics"][0]["phase"] == "association"
    invalid = artifact(data)
    invalid["genome_count"] = 999
    result = parse(data, artifact=invalid)
    assert codes(result) == {"codon_artifact_invalid"}
    for invalid in ({}, None, {"raw_artifact_ref": "x", "source_ref": "y", "sha256": "g" * 64}):
        result = parse(data, artifact=invalid)
        assert result["status"] == "invalid" and result["value"] is None
        assert codes(result) == {"codon_artifact_invalid"}
    result = parse(b"\xff", artifact=artifact(b"\xff"))
    assert codes(result) == {"codon_utf8_invalid"}
    result = parse(data, artifact={**artifact(data), "sha256": artifact(data)["sha256"].upper()})
    assert result["status"] == "invalid" and result["value"] is None
    assert codes(result) == {"codon_artifact_invalid"}


@pytest.mark.parametrize("digest", [
    None, 123, b"0" * 64, "", "a" * 63, "a" * 65, "g" * 64,
    "A" * 64, "a" * 63 + "B", " " + "a" * 64, "a" * 64 + "\n",
])
def test_malformed_artifact_hashes_match_shared_contract_without_normalization(digest):
    for parse, data, _ in PARSERS:
        supplied = {**artifact(data), "sha256": digest}
        before = deepcopy(supplied)
        with pytest.raises(ValueError, match="phylogeny_artifact_invalid"):
            formats._artifact(supplied)
        # Invalid artifact identity takes priority over decoding invalid bytes.
        result = parse(b"\xff", artifact=supplied)
        assert result == {
            "status": "invalid", "value": None,
            "diagnostics": [{"code": "codon_artifact_invalid", "phase": "association",
                             "path": "/artifact", "severity": "error", "evidence_refs": []}],
        }
        assert supplied == before


@pytest.mark.parametrize("parse,data,suffix", PARSERS)
def test_empty_or_header_only_is_not_a_successful_zero_result(parse, data, suffix):
    result = parse(b"")
    assert result["status"] == "invalid"
    assert "codon_empty_input" in codes(result)
    if parse is membership:
        assert result["value"]["table"]["completeness"] == "unknown"
    else:
        result = parse(data.split(b"\n")[0] + b"\n")
        assert result["status"] == "invalid"
        assert result["value"]["observations"] == []


@pytest.mark.parametrize("parse,data,suffix", PARSERS)
def test_unterminated_native_records_are_retained_without_claiming_complete_values(parse, data, suffix):
    extra = {membership: b"UNFINISHED\tProteins\t\tx", families: b"UNFINISHED\t0\t1\t1\t1\t1\t1\tTrue",
             genomes: b"UNFINISHED\t9\t8\t7", analysis: b"Num_genomes\t123"}[parse]
    result = parse(data + extra)
    assert result["status"] == "partial"
    assert result["value"]["table"]["completeness"] == "truncated"
    tail = result["value"]["table"]["rows"][-1]
    assert tail["raw_text"] == extra.decode() and tail["record_kind"] == "other_retained"
    assert "codon_truncated_line" in codes(result)
    base = parse(data)["value"]
    for field in ("rows", "observations", "commands"):
        if field in base:
            # Appending bytes changes the artifact digest, including every
            # surviving observation's custody reference. Values/positions stay.
            for record in base[field]:
                if "location" in record:
                    record["location"]["artifact"] = artifact(data + extra)
            assert result["value"][field] == base[field]


@pytest.mark.parametrize("parse,data", [(membership, CURRENT_MEMBERSHIP), (families, CURRENT_FAMILY_STATISTICS), (analysis, CURRENT_ANALYSIS_STATISTICS)])
def test_wrong_dialect_has_no_fallback(parse, data):
    for dialect in ("guess", "", None, ["homologs_current"]):
        result = parse(data, dialect)
        assert result["status"] == "invalid" and result["value"] is None
        assert codes(result) == {"codon_dialect_unsupported"}


def test_supplied_bytes_only_no_file_network_execution_or_eval(monkeypatch):
    examples = [(parse, data, artifact(data), parse(data)) for parse, data, _ in PARSERS]
    historical = HISTORICAL_MEMBERSHIP.read_bytes()
    examples.append((membership, historical, artifact(historical), membership(historical)))
    numeric_edges = FAMILY_HEADER + (
        b"F\t0\t1e-999\t-0e-999\t3\t2\tna\tTrue\n"
        b"bad seqs: {'g': -1e-999}\n"
        b"G\t0\t5e-324\t-2.5\t3\t2\t+0\tFalse\n"
        b"bad seqs: {'g': -0e-999}\n"
    )
    examples.append((families, numeric_edges, artifact(numeric_edges), families(numeric_edges)))
    for parse, data, _ in PARSERS:
        invalid = {**artifact(data), "sha256": artifact(data)["sha256"].upper()}
        examples.append((parse, data, invalid, parse(data, artifact=invalid)))
    def prohibited(*args, **kwargs):
        raise AssertionError("native parser attempted I/O, execution or eval")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (builtins, "eval"), (io, "open"), (Path, "open"),
                            (socket, "socket"), (socket, "create_connection"), (subprocess, "Popen"),
                            (subprocess, "run"), (os, "system"), (os, "popen"), (urllib.request, "urlopen")):
            patch.setattr(owner, name, prohibited)
        for parse, data, supplied, expected in examples:
            assert parse(data, artifact=supplied) == expected
