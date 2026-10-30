"""Saved native ASCII counts and deliberately malformed synthetic examples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.sequence_masking_contracts import validate_sequence_masking_record
from gene_annotation_episode.windowmasker_statistics import parse_windowmasker_statistics, validate_windowmasker_statistics


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_masking_native_oracle_2026-10-28_612/retained_native"


def descriptor(raw, complete="complete"):
    return {"occurrence_id": "statistics", "direction": "input", "role": "statistics", "ordinal": 0,
        "artifact_ref": "retained:statistics", "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "completeness": complete}


def parse(raw, binding=None, complete="complete"):
    return parse_windowmasker_statistics(raw, occurrence=descriptor(raw, complete),
                                        format="ascii_statistics", reference_binding=binding)


def statuses(stats):
    return {r["name"]: (r["status"], r["reason"]) for r in validate_windowmasker_statistics(stats)}


def test_saved_native_complete_counts_percentiles_thresholds_and_reference_identity():
    manifest = json.loads((FIXTURES / "ORACLE_MANIFEST.json").read_text())
    case = next(c for c in manifest["cases"] if c["mode"] == "create_counts")
    pin = case["primary_output"]; raw = (FIXTURES / pin["path"]).read_bytes()
    assert len(raw) == pin["size_bytes"] == 15201
    assert hashlib.sha256(raw).hexdigest() == pin["sha256"] == "bf4a5a6123b09a10b5f07654085b00381763d40b9a7e116dd9788152090dc59e"
    binding = {"kind": "generated", "statistics_occurrence_id": "statistics",
        "reference_occurrence_ids": ["window_reference.fa"], "producer_source_ref": "oracle612:create_counts",
        "producer_attempt_id": manifest["attempt"], "provenance": "authenticated_generation"}
    stats = parse(raw, binding)
    assert stats["format_version"] == "1.1.0" and stats["algorithm_version"] == "1.0.0"
    assert stats["unit_length"] == 3
    assert len(stats["unit_counts"]) == 21 and len(stats["percentiles"]) == 501
    assert stats["unit_counts"][0]["unit_code_hex"] == "0"
    assert stats["unit_counts"][-1]["unit_code_hex"] == "34"
    assert stats["unit_counts"][-1]["unit_code"] == 52
    assert min(r["native_count"] for r in stats["unit_counts"]) == 1
    assert max(r["native_count"] for r in stats["unit_counts"]) == 64
    assert stats["thresholds"] == {"t_low": 3, "t_extend": 126, "t_threshold": 126, "t_high": 126}
    assert stats["percentiles"][1]["percentage_lexeme"] == "57.1429"
    assert stats["reference_binding"] == binding
    assert not stats["failures"]
    assert all(c["status"] == "pass" for c in stats["checks"])
    assert validate_windowmasker_statistics(json.loads(json.dumps(stats))) == stats["checks"]


def test_synthetic_unknown_metadata_and_absent_percentiles_do_not_invent_values():
    stats = parse(b"##future: arbitrary native metadata\n3\n0 1\n>t_low 3\n>t_extend 4\n>t_threshold 8\n>t_high 64\n")
    assert stats["metadata_lines"][0]["text"] == "##future: arbitrary native metadata"
    assert stats["format_version"] is None and stats["algorithm_version"] is None
    assert stats["percentiles"] == []
    assert stats["reference_binding"] is None
    assert not stats["failures"]
    checks = statuses(stats)
    assert checks["statistics_percentile_range"] == ("not_applicable", "percentile_metadata_absent")
    assert checks["statistics_reference_relationship"] == ("unknown", "reference_provenance_unknown")
    # The explicit reference is not the mask target and is not promoted.
    binding = {"kind": "supplied", "statistics_occurrence_id": "statistics",
        "reference_occurrence_ids": ["a_different_reference"], "producer_source_ref": None,
        "producer_attempt_id": None, "provenance": "caller_declared"}
    stats = parse(b"3\n0 1\n>t_low 3\n>t_extend 4\n>t_threshold 8\n>t_high 64\n", binding)
    assert statuses(stats)["statistics_reference_relationship"] == ("unknown", "reference_caller_declared")


@pytest.mark.parametrize("bad,code", [(b"nonsense", "statistics_unit_row_syntax"),
    (b"a -1", "statistics_unit_row_syntax"), (b"##pct: 1 nan", "statistics_percentile_nonfinite"),
    (b"##pct: x 10", "statistics_percentile_syntax"), (b"4", "duplicate_statistics_unit_length"),
    (b">t_low 7", "duplicate_statistics_threshold")])
def test_synthetic_malformed_content_retains_other_valid_rows(bad, code):
    raw = b"3\n0 5\n>t_low 3\n" + bad + b"\n>t_extend 4\n>t_threshold 8\n>t_high 64\n"
    stats = parse(raw)
    assert stats["unit_counts"] == [{"line_number": 2, "unit_code_hex": "0", "unit_code": 0, "native_count": 5}]
    assert code in {f["code"] for f in stats["failures"]}
    assert stats["thresholds"]["t_low"] == 3


def test_synthetic_range_duplicates_order_metadata_conflicts_and_partial_custody():
    raw = (b"##parameters:unit=3 t_low=9 t_high=64\n##pct: 2 101\n##pct: 1 50\n"
           b"3\n3f 7\n0 1\n0 2\n40 4\n>t_low 3\n>t_extend 0\n>t_threshold 8\n>t_high 64\n")
    stats = parse(raw, complete="partial")
    assert len(stats["unit_counts"]) == 4
    checks = statuses(stats)
    for name in ("statistics_unique_units", "statistics_native_unit_order", "statistics_unit_code_range",
                 "statistics_metadata_agreement", "statistics_percentile_range", "statistics_percentile_count_order"):
        assert checks[name][0] == "fail"
    assert checks["statistics_output_completeness"][0] == "unknown"
    assert stats["thresholds"]["t_low"] == 3
    assert stats["percentiles"][0]["percentage"] == 101


def test_synthetic_missing_unit_thresholds_and_unknown_provenance_stay_unknown():
    stats = parse(b"# comment only\n")
    assert stats["unit_length"] is None
    assert all(v is None for v in stats["thresholds"].values())
    assert statuses(stats)["statistics_unit_code_range"][0] == "unknown"
    assert {f["code"] for f in stats["failures"]} >= {"statistics_threshold_missing", "statistics_unit_length_missing_or_duplicate"}


def test_malformed_schema_is_contract_error_not_native_failure():
    binding = {"kind": "generated", "statistics_occurrence_id": "statistics",
        "reference_occurrence_ids": [], "producer_source_ref": None, "producer_attempt_id": None,
        "provenance": "authenticated_generation"}
    with pytest.raises(ContractError, match="statistics_generation_provenance"):
        parse(b"3\n", binding)
    stats = parse(b"3\n0 1\n>t_low 3\n>t_extend 4\n>t_threshold 8\n>t_high 64\n")
    for mutate in (lambda s: s.update(extra=1), lambda s: s["unit_counts"][0].update(native_count=True),
                   lambda s: s["unit_counts"][0].update(unit_code_hex="f")):
        bad = deepcopy(stats); mutate(bad)
        with pytest.raises(ContractError):
            validate_sequence_masking_record("WindowMaskerStatistics", bad)
    with pytest.raises(ContractError, match="statistics_format"):
        parse_windowmasker_statistics(b"3\n", occurrence=descriptor(b"3\n"), format="binary", reference_binding=None)


def test_generation_binding_does_not_require_a_self_referential_source_digest():
    binding = {"kind": "generated", "statistics_occurrence_id": "statistics",
        "reference_occurrence_ids": ["captured_reference"], "producer_source_ref": None,
        "producer_attempt_id": "actual_attempt", "provenance": "authenticated_generation"}
    stats = parse(b"3\n0 1\n>t_low 3\n>t_extend 4\n>t_threshold 8\n>t_high 64\n", binding)
    assert stats["reference_binding"] == binding
    assert statuses(stats)["statistics_reference_relationship"] == ("pass", None)


@pytest.mark.parametrize("prefix,code", [(b"1 ", "statistics_unit_row_syntax"),
    (b"##pct: ", "statistics_percentile_syntax"), (b">t_high ", "statistics_threshold_syntax"),
    (b"##parameters:t_high=", "statistics_metadata_parameter_conflict")])
def test_synthetic_oversized_decimal_native_token_retains_valid_rows(prefix, code):
    token = prefix + b"9" * 5000 + (b" 10" if prefix.startswith(b"##pct:") else b"")
    raw = b"3\n0 1\n" + token + b"\n>t_low 3\n>t_extend 4\n>t_threshold 8\n>t_high 64\n"
    stats = parse(raw)
    assert stats["unit_counts"] == [{"line_number": 2, "unit_code_hex": "0", "unit_code": 0, "native_count": 1}]
    assert code in {f["code"] for f in stats["failures"]}
