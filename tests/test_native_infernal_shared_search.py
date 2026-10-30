"""Retained native search bytes reach the common v2 sheet and selected rows.

The captured files are actual earlier producer output. Temporary plans and the
byte-corruption case are controlled integration fixtures, not new native runs.
"""
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode import native_infernal_result_worker as worker
from gene_annotation_episode.infernal_search_contracts import sheet_digest
from test_native_infernal_result_worker import execute, plan_for, values


@pytest.mark.parametrize("program", ["cmsearch", "cmscan"])
def test_native_search_byte_custody_and_selected_values_use_common_sheet(tmp_path, monkeypatch, program):
    plan = plan_for(tmp_path, program)
    descriptor = next(row for row in plan["artifacts"] if row["format"] == "infernal_tblout")
    raw = Path(descriptor["path"]).read_bytes()
    calculate = worker.calculate_infernal_search_scores
    calls = []

    def tracked(sheet, *, parameters=None):
        calls.append(sheet)
        return calculate(sheet, parameters=parameters)

    monkeypatch.setattr(worker, "calculate_infernal_search_scores", tracked)
    manifest, sheet, scores, selected, diagnostics = execute(plan)
    assert manifest["numerical_complete"], diagnostics
    assert len(calls) == 1
    assert sheet["schema"] == "infernal_search_sheet_v2"
    assert scores["schema"] == "infernal_search_scores_v2"
    assert scores["sheet_digest"] == sheet_digest(sheet)
    assert sheet["artifacts"][0]["source_descriptor"] == {
        "profile": "infernal_tblout", "source_ref": None,
        "artifact_ref": descriptor["artifact_ref"],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_byte_length": len(raw), "byte_hash_verified": True}
    assert scores["hits"][0]["components"]["bitscore"] == 71.4
    for row in selected:
        saved = next(hit for hit in scores["hits"] if hit["hit_id"] == row["record_key"])
        measured = values(row)
        for name in ("bitscore", "evalue", "sequence_span_length", "sequence_span_fraction"):
            assert measured[name] == saved["components"][name]


def test_changed_captured_table_cannot_claim_verified_original_bytes(tmp_path):
    plan = plan_for(tmp_path)
    descriptor = next(row for row in plan["artifacts"] if row["format"] == "infernal_tblout")
    path = Path(descriptor["path"])
    path.write_bytes(path.read_bytes().replace(b"71.4", b"91.4"))
    manifest, sheet, scores, selected, diagnostics = execute(plan)
    assert not manifest["numerical_complete"]
    assert any(row["code"] == "native_infernal_captured_search_bytes_mismatch" for row in diagnostics)
    assert not selected
    assert sheet is None or not sheet["artifacts"]
