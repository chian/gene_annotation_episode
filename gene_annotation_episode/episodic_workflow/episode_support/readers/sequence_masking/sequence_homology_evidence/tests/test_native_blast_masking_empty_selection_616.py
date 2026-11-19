"""Explicitly empty record selection has no numerical-input requirement."""
from unittest.mock import patch

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_masking.sequence_homology_evidence import sequence_masking_calculations as calculations
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import project_masking_result
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.sequence_masking_contracts import PARAMETERS
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.tests.test_native_blast_masking_results_616 import selector


def operation(program="dustmasker", format="interval", mode="mask"):
    return {"version": "sequence_masking_operation_v1", "program": program, "mode": mode,
        "engine_version": None, "input_format": "fasta", "output_format": format,
        "masking_style": "not_applicable" if mode == "create_counts" else "interval" if format == "interval" else "soft",
        "parse_seqids": False, "requested_parameters": {k: None for k in PARAMETERS[(program, mode)]}}


@pytest.mark.parametrize("records,expected", [
    ({"mode": "selected", "entries": []}, "complete"),
    ({"mode": "all"}, "unavailable"),
])
def test_missing_sheet_respects_explicit_empty_selected_population(records, expected):
    choice = selector(records=records, quantities=["masked_positions", "masked_fraction"])
    with patch.object(calculations, "calculate_sequence_masking_components", side_effect=AssertionError("calculated")):
        result = project_masking_result(source_ref="source-synthetic-empty-selection", operation=operation(),
            native_outcome={"returncode": None, "state": "unknown", "output_complete": False},
            sheet=None, calculations=None, statistics=None, occurrences=[], selector=choice,
            failures=[], saved_data=[])
    assert result["status"]["state"] == expected
    assert result["status"]["native_state"] == "unknown"
    assert result["quantities"] == []
    assert result["record_refs"] == ["source-synthetic-empty-selection"]
    assert {f["code"] for f in result["failures"]} == (
        set() if expected == "complete" else {"saved_masking_sheet_unavailable"})
