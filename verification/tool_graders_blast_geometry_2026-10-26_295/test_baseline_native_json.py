"""Actual native counterexample retained separately from production regressions."""
from pathlib import Path

from gene_annotation_episode.blast_grading_inputs import parse_blast_json
from gene_annotation_episode.blast_pairwise_grader import build_pairwise_sheet


def test_actual_negative_translated_json_has_geometry():
    root = Path(__file__).resolve().parents[2]
    path = root / "verification/tool_graders_blast_pairwise_2026-10-26_294/native_examples/blastx_reverse_json15/attempt/report.json"
    result = parse_blast_json(path.read_bytes(), mode="pairwise", resource="local")
    hsp = build_pairwise_sheet(result)["hsps"][0]["components"]
    assert hsp["geometry_available"], hsp["issues"]
    assert hsp["pairs"][0] == {"query_start": 239, "query_end": 242,
        "reference_start": 0, "reference_end": 1, "identical": True}
