"""Retained outputs from actual tiny bounded executions; no native reruns here."""
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores
from gene_annotation_episode.native_hmmer_contracts import validate_native_hmmer_requested_job
from gene_annotation_episode.native_hmmer_driver import run_native_hmmer, validate_native_hmmer_bundle_files


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_native_hmmer_producer_2026-10-24/runs"
CASES = [
    ("hmmscan_search_ordinary", "domains", 1, "native_domain_score_bits", 72.1),
    ("hmmsearch_search_ordinary", "domains", 4, "native_domain_score_bits", 72.1),
    ("hmmsearch_search_empty", "domains", 0, None, None),
    ("jackhmmer_search_ordinary", "domains", 8, "native_domain_score_bits", 68.2),
    ("nhmmer_sequence_ordinary", "loci", 3, "native_score_bits", 92.2),
    ("nhmmer_profile_ordinary", "loci", 3, "native_score_bits", 120.9),
    ("nhmmer_alignment_ordinary", "loci", 3, "native_score_bits", 120.9),
    ("nhmmer_profile_watson", "loci", 2, "native_score_bits", 120.9),
    ("nhmmscan_search_ordinary", "loci", 3, "native_score_bits", 120.9),
    ("hmmalign_align_ordinary", "sequences", 4, "model_occupancy", 1.0),
    ("hmmalign_align_trim", "sequences", 4, "model_occupancy", 1.0),
    ("hmmalign_align_mapali", "sequences", 14, "model_occupancy", 1.0),
]


@pytest.mark.parametrize("label,family,count,field,expected", CASES)
def test_retained_actual_native_custody_numbers_and_offline_recalculation(monkeypatch, label, family, count, field, expected):
    root = FIXTURES / label
    plan = json.loads((root/"plan.json").read_text())
    bundle = json.loads((root/"attempt/bundle.json").read_text())
    receipt = json.loads((root/"runner_receipt.json").read_text())
    sheet = json.loads((root/"sheet.json").read_text())
    scores = json.loads((root/"scores.json").read_text())
    example = json.loads((root/"example.json").read_text())
    assert bundle["returncode"] == 0 and bundle["failures"] == []
    assert validate_native_hmmer_requested_job(plan["requested_job"]) == bundle["requested_job"]
    assert validate_native_hmmer_bundle_files(bundle, root/"attempt") == bundle
    assert receipt["metadata"]["policy"] == {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
    assert receipt["metadata"]["verified_cgroup"]["memory_max"] == 20*1024**3
    assert 'runtime_max' not in receipt["metadata"]["verified_cgroup"]
    for row in bundle["inputs"]:
        raw = (root/"attempt"/row["relative_path"]).read_bytes()
        assert len(raw) == row["size_bytes"] == row["expected_size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["actual_sha256"] == row["expected_sha256"]
    assert len(scores[family]) == count
    if count:
        key = example["example_row"]["record_key"]
        row = next(row for row in scores[family] if row["record_key"] == key)
        assert row[field] == pytest.approx(expected)
        if family == "loci":
            assert row["model_length"] == 100 and row["sequence_length"] == 120
            assert row["model_span_coverage"] == 1
            assert row["sequence_span_coverage"] == pytest.approx(100/120)
    def forbidden(*a, **k):
        pytest.fail("recalculation or sealed replay attempted new execution/acquisition")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    assert run_native_hmmer(plan) == bundle
    calculator = {"domains": calculate_hmmer_search_scores, "loci": calculate_nhmmer_scores, "sequences": calculate_hmmalign_scores}[family]
    monkeypatch.setattr(Path, "open", forbidden)
    assert calculator(sheet, parameters={}) == scores


def test_retained_actual_signal_failure_is_not_empty_success(monkeypatch):
    root = FIXTURES/"hmmscan_wrong_pressed_companion"
    plan = json.loads((root/"plan.json").read_text())
    bundle = json.loads((root/"attempt/bundle.json").read_text())
    assert bundle["returncode"] == -6
    assert bundle["failures"] == [{"stage": "execution", "code": "native_hmmer_nonzero_returncode", "role": None, "detail": {"returncode": -6}}]
    assert next(a for a in bundle["artifacts"] if a["role"] == "stdout")["size_bytes"] == 0
    assert next(a for a in bundle["artifacts"] if a["role"] == "stderr")["size_bytes"] == 84
    assert validate_native_hmmer_bundle_files(bundle, root/"attempt") == bundle
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("native signal failure replayed"))
    assert run_native_hmmer(plan) == bundle
