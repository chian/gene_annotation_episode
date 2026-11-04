"""Native retained Perl/R outputs plus explicitly synthetic damaged inputs."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import builtins
import json
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_metacats_formats import (
    parse_metacats_adjusted_matrix, parse_metacats_chisq_table, parse_metacats_metadata,
    parse_metacats_pair_table, parse_metacats_raw_r_table,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases"
LEGACY = ROOT / "verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/additional_sources/bvbrc_metacats/docs/example_output.tsv"
HEADER = b"Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\tA\tB\n"
PAIR = b"Position\tMultiple_comparison_p-value\tGroups\n"
RAW = "r_write_table_single_result_string"


def artifact(data, name="synthetic-fixture"):
    return {"raw_artifact_ref": name, "source_ref": name + "-source", "sha256": sha256(data).hexdigest()}


def parse(data, kind="chisq", **parameters):
    kwargs = {"artifact": artifact(data), "encoding": "ascii", **parameters}
    if kind == "metadata":
        return parse_metacats_metadata(data, delimiter="tab", header="present", **kwargs)
    kwargs.setdefault("category_id", "supplied-category")
    if kind == "matrix":
        return parse_metacats_adjusted_matrix(data, **kwargs)
    if kind == "chisq":
        kwargs.setdefault("layout", "current_filtered_tsv")
        return parse_metacats_chisq_table(data, **kwargs)
    if kind == "pair":
        kwargs.setdefault("layout", "current_filtered_tsv")
        return parse_metacats_pair_table(data, **kwargs)
    return parse_metacats_raw_r_table(data, kind=kind, layout=RAW, **kwargs)


def native(case, file, kind):
    data = (CASES / case / file).read_bytes()
    return data, parse(data, kind, artifact=artifact(data, "retained-" + case + "-" + file))


def assert_number_ranges(value, data):
    if isinstance(value, dict):
        if set(value) == {"raw_token", "value", "state", "token_kind", "source_location"}:
            loc = value["source_location"]
            assert data[loc["byte_start_0based"]:loc["byte_end_0based_exclusive"]].decode("utf-8") == value["raw_token"]
            assert loc["line_start_1based"] == data[:loc["byte_start_0based"]].count(b"\n") + 1
        for item in value.values():
            assert_number_ranges(item, data)
    elif isinstance(value, list):
        for item in value:
            assert_number_ranges(item, data)


@pytest.mark.parametrize("case,counts", [
    ("aa_two_groups", (12, 12, 1, 1, 3, 3)),
    ("aa_three_groups", (18, 18, 1, 3, 3, 9)),
    ("all_missing", (2, 2, 0, 0, 0, 0)),
    ("metadata_only_first_group", (13, 12, 1, 1, 3, 3)),
    ("native_pair_tail_underflow", (4000, 4000, 1, 0, 3, 3)),
    ("official_na", (14, 14, 143, 143, 765, 765)),
    ("twelve_groups", (48, 48, 1, 0, 3, 198)),
])
def test_all_seven_native_perl_r_runs(case, counts):
    stem = "GROUP" if case == "official_na" else "comparison"
    files = [("metadata.tsv", "metadata", "rows"), (f"output/{stem}.txt", "matrix", "rows"),
             (f"output/{stem}-chisqTable.tsv", "chisq", "rows"),
             (f"output/{stem}-mcTable.tsv", "pair", "rows"),
             (f"output/retained_raw/{stem}-chisqTable.txt", "omnibus", "omnibus_rows"),
             (f"output/retained_raw/{stem}-mcTable.txt", "pairwise", "pair_rows")]
    for (file, kind, rows), count in zip(files, counts):
        data, result = native(case, file, kind)
        assert result["status"] == "ok"
        assert len(result["value"][rows]) == count
        assert result["value"]["completeness"] == "complete"
        assert_number_ranges(result, data)
        json.dumps(result, allow_nan=False)


def test_native_two_group_numbers_and_conserved_placeholders():
    _, result = native("aa_two_groups", "output/comparison-chisqTable.tsv", "chisq")
    row = result["value"]["rows"][0]
    assert row["position_1based"] == 2
    assert row["chi_square"]["raw_token"] == "8.33055648117294"
    assert row["chi_square"]["value"] == 8.33055648117294
    assert row["p_value"]["value"] == 0.00389837142433717
    assert row["df"]["value"] == 1
    assert [(g["symbol_counts"][0]["symbol"], g["symbol_counts"][0]["count"]["value"]) for g in row["group_cells"]] == [("A", 6), ("C", 6)]
    _, result = native("aa_two_groups", "output/comparison-mcTable.tsv", "pair")
    assert result["value"]["rows"][0]["p_value"]["value"] == 0.000533148220906465
    _, raw = native("aa_two_groups", "output/retained_raw/comparison-chisqTable.txt", "omnibus")
    doc = raw["value"]
    assert (doc["wrapper_column_token"], doc["wrapper_row_token"], doc["section_heading_token"]) == ('"resultCST"', '"1"', "Chi-square Analysis Result:")
    conserved = doc["omnibus_rows"][0]
    assert conserved["site_token"] == " Site1 "
    assert conserved["chi_square"]["state"] == conserved["df"]["state"] == "not_measured"
    assert conserved["p_value"]["value"] == 1
    assert conserved["residue_diversity_token"] == "NA"
    assert conserved["positional_groups"] == []
    assert doc["omnibus_rows"][1]["chi_square"]["raw_token"] == " 8.33055648117294 "


def test_native_three_group_and_underflow_preserve_observed_one():
    _, three = native("aa_three_groups", "output/comparison-mcTable.tsv", "pair")
    assert [r["raw_groups_token"] for r in three["value"]["rows"]] == ["A,B", "A,C", "B,C"]
    assert [r["p_value"]["value"] for r in three["value"]["rows"]] == [0.0173810251352965] * 3
    _, raw = native("native_pair_tail_underflow", "output/retained_raw/comparison-mcTable.txt", "pairwise")
    assert raw["value"]["pair_rows"][1]["p_value"]["raw_token"] == " 1 "
    assert raw["value"]["pair_rows"][1]["p_value"]["value"] == 1
    _, filtered = native("native_pair_tail_underflow", "output/comparison-mcTable.tsv", "pair")
    assert filtered["status"] == "ok" and filtered["value"]["rows"] == []
    _, chisq = native("native_pair_tail_underflow", "output/comparison-chisqTable.tsv", "chisq")
    assert chisq["value"]["rows"][0]["p_value"]["value"] == 0


def test_native_metadata_only_group_label_shift_is_not_repaired():
    _, chisq = native("metadata_only_first_group", "output/comparison-chisqTable.tsv", "chisq")
    _, pair = native("metadata_only_first_group", "output/comparison-mcTable.tsv", "pair")
    _, matrix = native("metadata_only_first_group", "output/comparison.txt", "matrix")
    _, metadata = native("metadata_only_first_group", "metadata.tsv", "metadata")
    assert chisq["value"]["group_heading_tokens"] == ["A", "B", "C"]
    assert [g["raw_token"] for g in chisq["value"]["rows"][0]["group_cells"]] == ["6 A", "6 C", ""]
    assert pair["value"]["rows"][0]["raw_groups_token"] == "A,B"
    assert {r["native_group_token"] for r in matrix["value"]["rows"]} == {"2", "3"}
    assert any(r["cells"][1] == "A" for r in metadata["value"]["rows"])
    assert len(metadata["value"]["rows"]) == len(matrix["value"]["rows"]) + 1


def test_twelve_group_positions_and_supplied_padding_remain_distinct():
    _, raw = native("twelve_groups", "output/retained_raw/comparison-chisqTable.txt", "omnibus")
    groups = raw["value"]["omnibus_rows"][1]["positional_groups"]
    assert [g["position_1based"] for g in groups] == list(range(1, 13))
    assert [g["symbol_counts"][0]["symbol"] for g in groups] == list("ACDEFGHIKLMN")
    assert raw["value"]["omnibus_rows"][1]["df"]["value"] == 121
    data = b"z\t 1\t A # -\na\t10\t C # -\nz\t 2\t T # -\n"
    matrix = parse(data, "matrix")["value"]
    assert [r["native_group_token"] for r in matrix["rows"]] == [" 1", "10", " 2"]
    assert [r["native_member_token"] for r in matrix["rows"]] == ["z", "a", "z"]


def test_official_na_full_population_raw_tokens_and_legacy_layout():
    _, raw = native("official_na", "output/retained_raw/GROUP-chisqTable.txt", "omnibus")
    rows = raw["value"]["omnibus_rows"]
    assert len([r for r in rows if r["chi_square"]["state"] == "available"]) == 312
    assert rows[19]["position"]["value"] == 20
    assert rows[19]["chi_square"]["value"] == 13.993712243466
    assert rows[19]["p_value"]["value"] == 0.00291372399137316
    assert rows[19]["positional_groups"][1]["raw_token"] == "group2(2_C,_4_T) "
    data = LEGACY.read_bytes()
    result = parse(data, layout="legacy_example_tsv")
    assert result["status"] == "partial"
    assert result["value"]["header_tokens"][-1] == ""
    assert result["value"]["group_heading_tokens"] == ["Group 1 Residue Diversity", "Group 2 Residue Diversity", ""]
    first = result["value"]["rows"][0]
    assert (first["position_token"], first["position_1based"], first["position_qualification"]) == ("14*", 14, "legacy_star")
    assert first["fewer_5_token"] is None
    assert first["chi_square"]["value"] == 7.139 and first["p_value"]["value"] == 0.007543
    assert first["group_cells"][2] == {"heading_index": 2, "raw_token": "", "symbol_counts": []}
    assert_number_ranges(result, data)
    assert parse(data)["status"] == "invalid"


def test_ordered_metadata_duplicates_empty_extra_cells_and_unknown_columns():
    data = "ID\tcategory\textra\nβ\tB\t\nextra\tA\tvalue\nβ\tB\t\n\t\t\n".encode()
    result = parse(data, "metadata", encoding="utf-8")
    assert result["status"] == "ok"
    assert [r["cells"] for r in result["value"]["rows"]] == [["β", "B", ""], ["extra", "A", "value"], ["β", "B", ""], ["", "", ""]]
    ragged = parse(b"ID\tgroup\na\tA\n\nz\tB\textra\n", "metadata")
    assert ragged["status"] == "partial" and [r["cells"] for r in ragged["value"]["rows"]] == [["a", "A"], [""], ["z", "B", "extra"]]
    data = HEADER.rstrip(b"\n") + b"\tunknown-column\n1\t1\t.5\t1\tN\t2 A\t2 C\tunspecified text\n"
    result = parse(data)
    assert result["status"] == "partial"
    assert result["value"]["group_heading_tokens"][-1] == "unknown-column"
    assert result["value"]["rows"][0]["group_cells"][-1]["raw_token"] == "unspecified text"


@pytest.mark.parametrize("token,state,kind,value", [
    ("0", "available", "finite", 0), ("", "missing", "blank", None),
    ("NA", "not_measured", "native_na", None), ("NaN", "failed", "nonfinite", None),
    ("Inf", "failed", "nonfinite", None), ("oops", "failed", "malformed", None),
    ("1e-999", "failed", "underflow", None), ("1e999", "failed", "overflow", None),
    ("-0.1", "incompatible", "finite", -0.1), ("1.1", "incompatible", "finite", 1.1),
])
def test_p_value_states_preserve_tokens(token, state, kind, value):
    result = parse(PAIR + f"1\t{token}\tA,with,comma,B\n".encode(), "pair")
    row = result["value"]["rows"][0]
    assert (row["p_value"]["raw_token"], row["p_value"]["state"], row["p_value"]["token_kind"], row["p_value"]["value"]) == (token, state, kind, value)
    assert row["raw_groups_token"] == "A,with,comma,B"
    assert "group_ids" not in row


def test_bad_numbers_preserve_independent_valid_measurements():
    data = HEADER + b"0\t-2\t.05\t1.5\tmaybe\tbad A, -1 C, 2.5 G, 9007199254740993 T\t6 C\n"
    result = parse(data)
    row = result["value"]["rows"][0]
    assert result["status"] == "partial"
    assert row["position_qualification"] == "invalid" and row["position_1based"] is None
    assert row["chi_square"]["state"] == row["df"]["state"] == "incompatible"
    counts = row["group_cells"][0]["symbol_counts"]
    assert [r["count"]["state"] for r in counts] == ["failed", "incompatible", "incompatible", "available"]
    assert counts[-1]["count"]["value"] == 9007199254740993
    assert type(counts[-1]["count"]["value"]) is int
    assert row["group_cells"][1]["symbol_counts"][0]["count"]["value"] == 6
    assert_number_ranges(result, data)


def test_utf8_numeric_ranges_and_duplicate_native_symbol_counts():
    data = ("Position\tChi-square_value\tP-value\tDegrees_of_freedom\tFewer_5\tα\tα\r\n"
            "2\t2\t.5\t1\tN\t2 Ψ, 3 Ψ\t1 A\r\n").encode()
    result = parse(data, encoding="utf-8")
    assert result["status"] == "partial"
    counts = result["value"]["rows"][0]["group_cells"][0]["symbol_counts"]
    assert [(c["symbol"], c["count"]["value"]) for c in counts] == [("Ψ", 2), ("Ψ", 3)]
    assert_number_ranges(result, data)
    assert any(d["code"].endswith("duplicate_native_symbol") for d in result["diagnostics"])
    assert any(d["code"].endswith("native_group_heading_unresolved") for d in result["diagnostics"])


@pytest.mark.parametrize("kind,header,valid", [("chisq", HEADER, b"1\t2\t.3\t1\tN\t2 A\t2 C"), ("pair", PAIR, b"1\t.3\tA,B")])
def test_ragged_rows_keep_later_original_indexes_and_missing_newline_is_not_truncation(kind, header, valid):
    result = parse(header + valid, kind)
    assert result["status"] == "ok" and result["value"]["completeness"] == "complete"
    result = parse(header + valid + b"\nshort\n" + valid + b"\textra\n" + valid + b"\n", kind)
    assert result["status"] == "partial"
    assert [r["row_index"] for r in result["value"]["rows"]] == [0, 3]
    assert result["value"]["completeness"] == "partial"


def test_raw_r_is_multiline_data_never_executable_and_partial_is_retained():
    data = b'"resultMC"\n"1" "MGC Multiple Comparison Result:\n Site1 \t .5 \t 1 \t 2 \n Site2 \t .2 \t 1 \t 2 \t unexpected\n Site3 \t NA \t 1 \t 2 \n"\n'
    result = parse(data, "pairwise")
    assert result["status"] == "partial"
    assert [r["row_index"] for r in result["value"]["pair_rows"]] == [0, 2]
    assert_number_ranges(result, data)
    truncated = parse(data[:-2], "pairwise")
    assert truncated["value"]["completeness"] == "truncated"
    assert len(truncated["value"]["pair_rows"]) == 2
    injected = parse(data + b'system("touch /tmp/not-run")\n', "pairwise")
    assert injected["status"] == "partial"
    assert any(d["code"].endswith("raw_wrapper_trailing_data") for d in injected["diagnostics"])
    assert parse(b'system("anything")', "pairwise")["status"] == "invalid"
    assert parse(data.replace(b'"resultMC"', b'"resultCST"'), "pairwise")["status"] == "invalid"


def test_raw_unknown_tokens_duplicate_groups_and_escaped_quotes_are_retained():
    data = b'"resultCST"\n"1" "Chi-square Analysis Result:\n Site2 \t 2 \t .5 \t 1 \t N \t group2(bad_A)|group2(2_C)|unparsed\\"text \n"\n'
    result = parse(data, "omnibus")
    assert result["status"] == "partial"
    row = result["value"]["omnibus_rows"][0]
    assert row["residue_diversity_token"].endswith('unparsed\\"text ')
    assert [g["position_1based"] for g in row["positional_groups"]] == [2, 2]
    assert row["positional_groups"][0]["symbol_counts"][0]["count"]["state"] == "failed"
    assert_number_ranges(result, data)


def test_matrix_native_symbols_unknown_tokens_and_partial_rows():
    result = parse(b"a\t2\t # - a * ?\nb\t3\t # A C\nbad\nc\t4\t TRUE - #\n", "matrix")
    assert result["status"] == "partial"
    assert [r["row_index"] for r in result["value"]["rows"]] == [0, 1, 3]
    assert result["value"]["rows"][0]["symbols"] == ["#", "-", "a", "*", "?"]
    assert result["value"]["rows"][2]["symbols"] == ["TRUE", "-", "#"]
    assert parse(b"not a matrix\n", "matrix")["status"] == "invalid"


def test_digest_layout_encoding_and_no_readable_document_fail_explicitly():
    assert parse(HEADER, artifact={**artifact(HEADER), "sha256": "0" * 64})["status"] == "invalid"
    assert parse(HEADER + b"\xff")["status"] == "invalid"
    assert parse(b"")["status"] == "invalid"
    assert parse(b"unknown\tcolumns\n")["status"] == "invalid"
    assert parse(PAIR.rstrip(b"\n") + b"\textra\n", "pair")["status"] == "invalid"
    for params in ({"layout": "guess"}, {"encoding": "latin1"}, {"category_id": ""}):
        with pytest.raises(ValueError):
            parse(HEADER, **params)
    with pytest.raises(ValueError):
        parse_metacats_pair_table("not bytes", artifact=artifact(b""), layout="current_filtered_tsv", category_id="c", encoding="ascii")


def test_supplied_byte_parsing_and_detachment_without_external_effects(monkeypatch):
    data = HEADER + b"1\t2\t.3\t1\tN\t2 A\t2 C\n"
    supplied = artifact(data)
    before = deepcopy(supplied)
    def forbidden(*args, **kwargs):
        raise AssertionError("external operation in pure parser")
    for owner, name in ((builtins, "open"), (Path, "read_bytes"), (socket, "socket"), (subprocess, "run"), (subprocess, "Popen")):
        monkeypatch.setattr(owner, name, forbidden)
    result = parse(data, artifact=supplied)
    result["value"]["artifact"]["source_ref"] = "mutated"
    assert supplied == before
