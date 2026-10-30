"""Offline MinHash tests; synthetic BV-BRC rows are never live measurements."""
from copy import deepcopy
import ast
from fractions import Fraction
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_minhash_grader import (
    MINHASH_DIAGNOSTIC_CODES,
    calculate_minhash_components,
    calculate_minhash_shared_hash_fraction,
    parse_minhash_result,
)


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24/sources"


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure grading must not acquire data or execute jobs")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def request(mode="genome", max_hits=1):
    return {"version": "1.1", "id": "synthetic-rpc",
            "method": f"Minhash.compute_genome_distance_for_{mode}2",
            "params": ["synthetic.query" if mode == "genome" else "/owner/workspace/input.fa",
                       1.0, 1.0, max_hits, 1, 1, 1, 0]}


def parse(rows, mode="genome", **kwargs):
    return parse_minhash_result(rows, mode=mode, request=kwargs.get("request", request(mode)),
                               provenance=kwargs.get("provenance", {"kind": "synthetic"}))


def metadata(index=0, genome="synthetic.reference", **values):
    return {"row_index": index, "genome_id": genome,
            "kmer_length": 1, "query_length": 2, "reference_length": 2,
            "alphabet_size": 2, "provenance": {"kind": "explicit_synthetic_example"}, **values}


def codes(value):
    return {item["code"] for item in value["diagnostics"]}


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_retained_upstream_mash_values_in_synthetic_bvbrc_wrapper(mode):
    source = NATIVE / "Mash/test/ref/genomes.dist"
    fields = source.read_text().splitlines()[0].split("\t")
    assert fields == ["genome1.fna", "reads", "0.12101", "4.48626e-214", "41/1000"]
    rows = [["synthetic.reference", *fields[2:]]]
    provenance = {"kind": "upstream_native_values_in_synthetic_bvbrc_wrapper",
                  "source_path": str(source.relative_to(ROOT)), "live_bvbrc_output": False}
    result = parse(rows, mode, provenance=provenance)
    assert result["status"] == "ok"
    sheet = result["sheet"]
    assert sheet["native_result"] == rows
    assert sheet["rows"][0]["reported_distance"] == 0.12101
    assert sheet["rows"][0]["reported_pvalue"] == 4.48626e-214
    assert sheet["rows"][0]["shared_hashes"] == 41
    assert sheet["rows"][0]["compared_union_hashes"] == 1000
    result = calculate_minhash_components(sheet)
    assert result["rows"][0]["shared_hash_fraction"] == 0.041
    assert result["rows"][0]["recomputed_distance"] is None
    assert result["rows"][0]["recomputed_pvalue"] is None
    assert "pair_metadata_missing" in codes(result)
    assert all(value is None for value in sheet["search_metadata"].values())


def test_small_exact_binomial_and_saved_sheet_recalculation():
    rows = [["synthetic.reference", "0.223144", "0.259259", "2/3"]]
    sheet = parse(rows)["sheet"]
    before = deepcopy(sheet)
    original_meta = [metadata()]
    meta_before = deepcopy(original_meta)
    first = calculate_minhash_components(sheet, pair_metadata=original_meta)["rows"][0]
    # A=2^1=2, r1=r2=1/2, random J=1/3.
    # P[Binomial(3,1/3)>=2] = 3*(1/3)^2*(2/3)+(1/3)^3 = 7/27.
    exact = 3 * Fraction(1, 3)**2 * Fraction(2, 3) + Fraction(1, 3)**3
    assert exact == Fraction(7, 27)
    assert first["shared_hash_fraction"] == 2 / 3
    assert first["recomputed_distance"] == pytest.approx(math.log(5 / 4))
    assert first["recomputed_pvalue"] == pytest.approx(float(exact))
    null = first["calculation_inputs"]["null_model"]
    assert null["query_random_kmer_probability"] == 0.5
    assert null["reference_random_kmer_probability"] == 0.5
    assert null["random_jaccard"] == pytest.approx(1 / 3)
    assert sheet == before and original_meta == meta_before
    saved = json.loads(json.dumps(sheet, allow_nan=False))
    second = calculate_minhash_components(saved, pair_metadata=[metadata(kmer_length=2)])["rows"][0]
    # Same observations, new explicit k: A=4, random J=1/5, tail=13/125.
    assert second["recomputed_distance"] == pytest.approx(math.log(5 / 4) / 2)
    assert second["recomputed_pvalue"] == pytest.approx(float(Fraction(13, 125)))
    assert second["reported_distance"] == first["reported_distance"] == 0.223144
    assert second["reported_pvalue"] == first["reported_pvalue"] == 0.259259
    assert saved == sheet


def test_native_types_counts_token_zero_and_null_remain_distinct():
    rows = [["a", 0, 0.0, "000/003"], ["a", "0.0", "0e0", "0/3"],
            ["a", None, None, None], ["b", "0.1"]]
    result = parse(rows)
    assert result["status"] == "partial"
    parsed = result["sheet"]["rows"]
    assert type(parsed[0]["native_row"][1]) is int
    assert type(parsed[0]["native_row"][2]) is float
    assert type(parsed[1]["native_row"][1]) is str
    assert parsed[0]["counts_token"] == "000/003"
    assert parsed[0]["shared_hashes"] == 0
    assert parsed[2]["reported_distance"] is None
    assert "null_native_field" in codes(parsed[2])
    assert "missing_native_field" in codes(parsed[3])
    assert result["sheet"]["native_result"] == rows


def test_duplicate_rows_preserved_beyond_requested_limit_and_exact_metadata_joins():
    rows = [["a", 0.1, 0.01, "2/3"], ["a", 0.2, 0.02, "1/3"],
            ["b", 0.3, 0.03, "3/3"]]
    sheet = parse(rows, request=request(max_hits=1))["sheet"]
    assert len(sheet["rows"]) == 3
    supplied = [metadata(2, "b", kmer_length=3), metadata(1, "a", kmer_length=2),
                metadata(0, "a", kmer_length=1)]
    result = calculate_minhash_components(sheet, pair_metadata=supplied)
    assert [row["row_index"] for row in result["rows"]] == [0, 1, 2]
    assert [row["genome_id"] for row in result["rows"]] == ["a", "a", "b"]
    assert [row["calculation_inputs"]["kmer_length"] for row in result["rows"]] == [1, 2, 3]
    assert [row["shared_hash_fraction"] for row in result["rows"]] == pytest.approx([2/3, 1/3, 1])


def test_zero_overlap_full_overlap_and_zero_denominator():
    native = [["a", "1", "1", "0/3"], ["b", 0, 0.25, "3/3"], ["c", 0, 1, "0/0"]]
    sheet = parse(native)["sheet"]
    result = calculate_minhash_components(sheet, pair_metadata=[metadata(i, row[0]) for i, row in enumerate(native)])
    zero, full, empty = result["rows"]
    assert (zero["shared_hash_fraction"], zero["recomputed_distance"], zero["recomputed_pvalue"]) == (0, 1, 1)
    assert (full["shared_hash_fraction"], full["recomputed_distance"]) == (1, 0)
    assert full["recomputed_pvalue"] == pytest.approx(1/27)
    assert (empty["reported_distance"], empty["reported_pvalue"]) == (0, 1)
    assert empty["shared_hash_fraction"] is None
    assert empty["recomputed_distance"] is None
    assert empty["recomputed_pvalue"] is None
    assert "zero_union_calculations_unavailable" in codes(empty)


def test_distance_saturation_is_explicit():
    sheet = parse([["synthetic.reference", 1, 0.1, "1/1000"]])["sheet"]
    row = calculate_minhash_components(sheet, pair_metadata=[metadata()])["rows"][0]
    assert row["recomputed_distance"] == 1
    assert row["unsaturated_distance"] == pytest.approx(math.log(1001/2))
    assert "distance_saturated_at_one" in codes(row)


@pytest.mark.parametrize("invalid", [True, False, float("nan"), float("inf"), -0.1,
                                     "NaN", "Infinity", "1_0", " 0.1", "1e9999", "-1e-9999", 1.1])
def test_invalid_numbers_preserve_native_and_valid_neighbor_cells(invalid):
    result = parse([["a", invalid, invalid, "1/2"], ["b", 0, 0, "1/1"]])
    assert result["status"] == "partial"
    row = result["sheet"]["rows"][0]
    assert row["reported_distance"] is None
    assert row["reported_pvalue"] is None
    assert row["shared_hashes"] == 1
    assert result["sheet"]["rows"][1]["reported_distance"] == 0
    calculated = calculate_minhash_components(result["sheet"])
    assert calculated["rows"][0]["shared_hash_fraction"] == 0.5


@pytest.mark.parametrize("token", [True, 0, [], "1", "1/2/3", "-1/3", "1/-3", "1.0/3", "1/2 ", "3/2"])
def test_invalid_counts_never_calculate_a_fraction(token):
    result = parse([["synthetic.reference", 0.1, 0.2, token]])
    assert result["status"] == "partial"
    row = result["sheet"]["rows"][0]
    assert row["counts_token"] == token
    components = calculate_minhash_components(result["sheet"], pair_metadata=[metadata()])["rows"][0]
    assert components["shared_hash_fraction"] is None
    assert components["recomputed_distance"] is None
    assert components["recomputed_pvalue"] is None


def test_missing_null_malformed_rows_and_extra_fields_do_not_drop_neighbors():
    rows = [None, {}, [], [None, 0, 0, "1/1"], ["a", 0, 0, "1/1", "extra"], ["b", 0, 0, "1/1"]]
    result = parse(rows)
    assert result["status"] == "partial"
    assert len(result["sheet"]["rows"]) == len(rows)
    assert result["sheet"]["native_result"] == rows
    calculated = calculate_minhash_components(result["sheet"])
    assert len(calculated["rows"]) == len(rows)
    assert calculated["rows"][-1]["shared_hash_fraction"] == 1
    assert calculated["rows"][3]["shared_hash_fraction"] is None


@pytest.mark.parametrize("value", [None, {"result": [[]]}, {"id": "job", "status": "completed"}, "a\t0\t0\t1/1"])
def test_outer_native_value_rejects_rpc_envelopes_tasks_tsv_and_missing(value):
    result = parse(value)
    assert result["status"] == "invalid"
    assert result["sheet"]["native_result"] == value
    assert "native_result_array_required" in codes(result)


def test_empty_result_is_not_a_complete_negative_search():
    result = parse([])
    assert result["status"] == "ok"
    assert result["sheet"]["rows"] == []
    assert "empty_result_completeness_unknown" in codes(result)
    assert result["sheet"]["search_metadata"]["truncated"] is None
    assert "empty_result_completeness_unknown" in codes(calculate_minhash_components(result["sheet"]))


def test_all_malformed_rows_still_have_indexed_unavailable_calculations():
    result = parse([None, {}])
    assert result["status"] == "invalid"
    calculated = calculate_minhash_components(result["sheet"])
    assert [row["row_index"] for row in calculated["rows"]] == [0, 1]
    assert all(row["shared_hash_fraction"] is None for row in calculated["rows"])


@pytest.mark.parametrize("mode", ["genome", "fasta"])
def test_exact_method_eight_arguments_no_mutation_or_defaults(mode):
    selected = request(mode)
    selected["params"][1:4] = ["0.01", 0, 0]
    selected["params"][4] = 7  # Native integer truth value, not a Python bool.
    selected_before = deepcopy(selected)
    native = [["a", 0, 0, "1/1"]]
    provenance = {"kind": "synthetic", "nested": [1, "1", 0, None], "kmer_length": 21}
    parsed = parse(native, mode, request=selected, provenance=provenance)
    assert parsed["status"] == "ok"
    assert parsed["sheet"]["request"] == selected_before == selected
    assert parsed["sheet"]["provenance"] == provenance
    assert parsed["sheet"]["search_metadata"]["kmer_length"] is None
    native[0][1] = 1
    provenance["nested"].append(2)
    selected["params"].append("later")
    assert parsed["sheet"]["native_result"][0][1] == 0
    assert parsed["sheet"]["provenance"]["nested"] == [1, "1", 0, None]
    assert len(parsed["sheet"]["request"]["params"]) == 8


@pytest.mark.parametrize("replacement", ["x", None, [], ["id", 0, 0, 1, 1, 1, 1], ["id", 0, 0, 1, 1, 1, 1, 0, 1]])
def test_request_arity_and_exact_mode_association(replacement):
    selected = request()
    selected["params"] = replacement
    assert parse([], request=selected)["status"] == "invalid"
    selected = request("fasta")
    assert parse([], request=selected)["status"] == "invalid"


@pytest.mark.parametrize("operand", [">query\nACGT", "input.fa", "./input.fa", "/tmp/input.fa", "file:///local/a.fa", "https://host/a.fa", "/owner/ws/../a.fa"])
def test_fasta_operand_is_workspace_path_not_inline_or_local_input(operand):
    selected = request("fasta")
    selected["params"][0] = operand
    result = parse([], "fasta", request=selected)
    assert result["status"] == "invalid"
    assert "workspace_fasta_path_required" in codes(result)


def test_wrong_and_duplicate_metadata_associations_are_not_joined():
    sheet = parse([["a", 0, 0, "2/3"], ["a", 0, 0, "1/3"]])["sheet"]
    supplied = [metadata(0, "wrong"), metadata(1, "a"), metadata(1, "a"), metadata(2, "a"), metadata(True, "a")]
    result = calculate_minhash_components(sheet, pair_metadata=supplied)
    assert {"pair_metadata_genome_id_mismatch", "ambiguous_pair_metadata", "pair_metadata_row_index_mismatch"} <= codes(result)
    assert all(row["recomputed_distance"] is None for row in result["rows"])
    assert [row["shared_hash_fraction"] for row in result["rows"]] == pytest.approx([2/3, 1/3])
    assert len(result["rows"][1]["calculation_inputs"]["pair_metadata_candidates"]) == 2


@pytest.mark.parametrize("field", ["kmer_length", "query_length", "reference_length", "alphabet_size"])
@pytest.mark.parametrize("value", [None, 0, -1, True, 1.5, "2", float("nan")])
def test_missing_invalid_metadata_stays_unknown(field, value):
    sheet = parse([["synthetic.reference", 0, 0, "2/3"]])["sheet"]
    result = calculate_minhash_components(sheet, pair_metadata=[metadata(**{field: value})])
    row = result["rows"][0]
    assert row["shared_hash_fraction"] == pytest.approx(2/3)
    assert row["recomputed_pvalue"] is None
    assert row["calculation_inputs"][field] is None
    assert (row["recomputed_distance"] is None) == (field == "kmer_length")


def test_metadata_requires_structured_provenance_and_does_not_infer_from_sheet_provenance():
    sheet = parse([["synthetic.reference", 0, 0, "2/3"]], provenance=metadata())["sheet"]
    result = calculate_minhash_components(sheet)
    assert result["rows"][0]["recomputed_distance"] is None
    result = calculate_minhash_components(sheet, pair_metadata=[metadata(provenance=None)])
    assert result["rows"][0]["recomputed_distance"] is None
    assert "structured_metadata_provenance_required" in codes(result)


def test_small_tail_survives_cancellation_and_underflow_is_qualified():
    sheet = parse([["synthetic.reference", "0.1", "1e-1000", "100/100"]])["sheet"]
    assert sheet["rows"][0]["reported_pvalue"] == 0
    assert "native_numeric_conversion_underflow" in codes(sheet["rows"][0])
    row = calculate_minhash_components(sheet, pair_metadata=[metadata()])["rows"][0]
    assert row["recomputed_pvalue"] == pytest.approx((1/3)**100, rel=1e-12, abs=0)
    assert 0 < row["recomputed_pvalue"] < 1e-40
    row = calculate_minhash_components(sheet, pair_metadata=[metadata(kmer_length=100)])["rows"][0]
    assert row["recomputed_pvalue"] == 0
    assert "recomputed_pvalue_underflow" in codes(row)


def test_random_overlap_stays_representable_when_product_of_ris_underflows():
    sheet = parse([["synthetic.reference", 1, 0, "1/2"]])["sheet"]
    row = calculate_minhash_components(sheet, pair_metadata=[metadata(
        kmer_length=400, alphabet_size=4, query_length=1, reference_length=1)])["rows"][0]
    null = row["calculation_inputs"]["null_model"]
    assert null["query_random_kmer_probability"] * null["reference_random_kmer_probability"] == 0
    assert null["random_jaccard"] > 0
    assert row["recomputed_pvalue"] == pytest.approx(2**-800, rel=1e-12, abs=0)


def test_underflowed_random_null_keeps_log_value_and_explicit_qualification():
    sheet = parse([["synthetic.reference", 1, 0, "1/2"]])["sheet"]
    row = calculate_minhash_components(sheet, pair_metadata=[metadata(kmer_length=2000)])["rows"][0]
    assert row["calculation_inputs"]["null_model"]["kmer_space"] is None
    assert math.isfinite(row["calculation_inputs"]["null_model"]["log_random_jaccard"])
    assert row["recomputed_pvalue"] == 0
    assert {"random_jaccard_underflow", "recomputed_pvalue_underflow"} <= codes(row)
    json.dumps(row, allow_nan=False)


@pytest.mark.parametrize("field,value", [("shared_hashes", 3), ("reported_pvalue", 0.9), ("row_index", 1), ("genome_id", "wrong")])
def test_saved_sheet_association_or_cell_corruption_is_not_used(field, value):
    sheet = parse([["synthetic.reference", 0.1, 0.2, "2/3"]])["sheet"]
    sheet["rows"][0][field] = value
    result = calculate_minhash_components(sheet, pair_metadata=[metadata()])
    assert "sheet_native_row_mismatch" in codes(result)
    assert result["rows"][0]["shared_hash_fraction"] is None


def test_large_counts_remain_exact_and_float_binomial_limit_is_explicit():
    shared, union = 2**53, 2**53 + 1
    sheet = parse([["synthetic.reference", 0, 0, f"{shared}/{union}"]])["sheet"]
    assert sheet["rows"][0]["compared_union_hashes"] == union
    row = calculate_minhash_components(sheet, pair_metadata=[metadata()])["rows"][0]
    assert row["recomputed_distance"] > 0
    assert row["recomputed_pvalue"] is None
    assert "binomial_integer_precision_unsupported" in codes(row)


def test_no_provenance_measurement_inference_or_annotation_scores():
    sheet = parse([["a", 0, 0, "1/1"]], provenance={"taxon": "a", "confidence": 0.9})["sheet"]
    result = calculate_minhash_components(sheet)
    assert not ({"confidence", "annotation_probability", "function", "taxon"} & result["rows"][0].keys())
    assert result["rows"][0]["calculation_inputs"]["kmer_length"] is None


def test_calculator_rejects_wrong_sheet_or_missing_native_rows():
    assert "minhash_sheet_required" in codes(calculate_minhash_components({}))
    sheet = parse([["a", 0, 0, "1/1"]])["sheet"]
    sheet["rows"] = []
    assert "sheet_native_row_count_mismatch" in codes(calculate_minhash_components(sheet))


@pytest.mark.parametrize("shared,union,expected", [(2, 3, 2 / 3), (0, 3, 0.0), (3, 3, 1.0)])
def test_common_shared_hash_fraction_retains_exact_python_division(shared, union, expected):
    actual = calculate_minhash_shared_hash_fraction(shared, union, row_identity_available=True)
    assert type(actual) is float and actual == expected


@pytest.mark.parametrize("shared,union", [
    (0, 0), (1, 0), (-1, 2), (3, 2), (None, 3), (2, None),
    (True, 3), (2, True), (False, 3), (2, False), (2.0, 3), (2, 3.0),
    ("2", 3), (2, "3"), (float("nan"), 3), (2, float("inf")),
])
def test_common_shared_hash_fraction_leaves_invalid_counts_unavailable(shared, union):
    assert calculate_minhash_shared_hash_fraction(shared, union, row_identity_available=True) is None


@pytest.mark.parametrize("identity", [False, None, 0, 1, "true", [], {}])
def test_common_shared_hash_fraction_requires_exact_true_identity(identity):
    assert calculate_minhash_shared_hash_fraction(2, 3, row_identity_available=identity) is None


def test_calculator_calls_common_fraction_helper_without_changing_other_components(monkeypatch):
    import gene_annotation_episode.bvbrc_minhash_grader as grader
    observed = []
    original = grader.calculate_minhash_shared_hash_fraction

    def tracked(shared, union, *, row_identity_available):
        observed.append((shared, union, row_identity_available))
        return original(shared, union, row_identity_available=row_identity_available)

    monkeypatch.setattr(grader, "calculate_minhash_shared_hash_fraction", tracked)
    sheet = parse([["synthetic.reference", "0.223144", "0.259259", "2/3"]])["sheet"]
    result = calculate_minhash_components(sheet, pair_metadata=[metadata()])["rows"][0]
    assert observed == [(2, 3, True)]
    assert result["shared_hash_fraction"] == 2 / 3
    assert result["recomputed_distance"] == pytest.approx(0.22314355131420976)
    assert result["recomputed_pvalue"] == pytest.approx(0.2592592592592592)
    assert result["reported_distance"] == 0.223144
    assert result["reported_pvalue"] == 0.259259


@pytest.mark.parametrize("shared,union,expected", [(2**54, 2**54 + 1, 1.0), (1, 10**400, 0.0)])
def test_fraction_rounding_and_underflow_keep_existing_diagnostics(shared, union, expected):
    sheet = parse([["synthetic.reference", 0, 0, f"{shared}/{union}"]])["sheet"]
    row = calculate_minhash_components(sheet)["rows"][0]
    assert calculate_minhash_shared_hash_fraction(shared, union, row_identity_available=True) == expected
    assert row["shared_hash_fraction"] == expected
    assert "shared_fraction_underflow_or_rounding" in codes(row)
    assert row["recomputed_distance"] is None and row["recomputed_pvalue"] is None


def test_finite_diagnostic_collection_matches_the_existing_issue_sites():
    source = ROOT / "gene_annotation_episode/bvbrc_minhash_grader.py"
    declared = set(MINHASH_DIAGNOSTIC_CODES)
    actual = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_issue":
            for item in ast.walk(node.args[1]):
                if isinstance(item, ast.Constant) and type(item.value) is str:
                    actual.add(item.value)
    assert len(declared) == len(MINHASH_DIAGNOSTIC_CODES)
    assert declared == actual
