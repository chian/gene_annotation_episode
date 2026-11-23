"""Captured-byte reporting and unchanged legacy replay for BLAST utilities.

No BLAST executable or database build runs here. Producer calls are explicit
engineering fixtures; the check096 diagnostic bytes and saved publication are
retained native evidence, authenticated against their original hashes.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import blast_database_extraction as extraction
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.sequence_homology_evidence import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import native_blast_utility_driver as driver
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.native_blast_utility_contracts import native_blast_utility_output_completeness, producer_failure, validate_native_blast_utility_bundle
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_blast_utility_contracts_625 import binding, occurrence, operation, outcome
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_native_blast_utility_producer_628 import FAMILY, plan_fixture
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_native_blast_utility_publication_631 import capture_fixture, payload, prepare, publish, selector


def failure_codes(result):
    return {row["code"] for row in result["failures"]}


@pytest.mark.parametrize("basis,returncode,closed,measured,expected", [
    ("captured_bytes", 7, True, True, "complete"),
    ("captured_bytes", 0, True, True, "complete"),
    ("captured_bytes", None, True, True, "complete"),
    ("captured_bytes", 7, True, False, "unknown"),
    ("captured_bytes", None, False, True, "unknown"),
    (None, 7, True, True, "partial"),
    (None, 0, True, True, "complete"),
    (None, None, True, True, "partial"),
    (None, 0, True, False, "unknown"),
    (None, None, False, True, "unknown"),
])
def test_completeness_means_captured_bytes_only_with_explicit_basis(
        basis, returncode, closed, measured, expected):
    bundle = {"writer_closed": closed, "returncode": returncode}
    if basis is not None:
        bundle["output_completeness_basis"] = basis
    before = deepcopy(bundle)
    assert native_blast_utility_output_completeness(bundle, measured) == expected
    assert bundle == before


def test_unclosed_writer_cannot_claim_complete_measured_output(tmp_path):
    _, capture = capture_fixture(tmp_path, "create_sequence_database")
    bundle = deepcopy(capture["original_bundle"])
    bundle.update(output_completeness_basis="captured_bytes", returncode=None,
                  writer_closed=False, inventory_complete=False, finished_at=None,
                  failures=[producer_failure("output_inventory_incomplete", relative_path="db/tiny")])
    for row in bundle["artifacts"]:
        row["completeness"] = "unknown"
    assert validate_native_blast_utility_bundle(bundle, capture["plan"]) == bundle
    bundle["artifacts"][0]["completeness"] = "complete"
    with pytest.raises(ValueError, match="bundle_output_completeness_conflict"):
        validate_native_blast_utility_bundle(bundle, capture["plan"])


@pytest.mark.parametrize("changes,completeness,expected", [
    ({"state": "failed", "returncode": 7}, "complete", {"native_nonzero_exit"}),
    ({"state": "failed", "returncode": None, "started": False}, "complete", {"native_start_failed"}),
    ({"state": "unknown", "returncode": None}, "complete", {"native_outcome_unavailable"}),
    ({}, "partial", {"output_completeness_unestablished"}),
    ({}, "unknown", {"output_completeness_unestablished"}),
    ({"inventory_complete": False}, "complete", {"output_inventory_incomplete"}),
    ({"state": "incomplete", "returncode": None, "inventory_complete": False}, "complete",
     {"native_outcome_unavailable", "output_inventory_incomplete"}),
    ({"state": "incomplete", "returncode": None, "writer_closed": False, "inventory_complete": False}, "unknown",
     {"native_outcome_unavailable", "output_inventory_incomplete", "output_writer_not_closed", "output_completeness_unestablished"}),
])
def test_native_inventory_writer_and_occurrence_qualifications_are_independent(changes, completeness, expected):
    native = validate_blast_utility_record("NativeOutcome", outcome(**changes))
    row = occurrence()
    row["completeness"] = completeness
    checks, failures = extraction._outcome_observations(native, [row], "tiny")
    assert {failure["code"] for failure in failures} == expected
    for failure in failures:
        validate_blast_utility_record("UtilityFailure", failure)
        assert failure["stage"] == ("native" if failure["code"].startswith("native_") else "capture")
    assert checks[0]["reason"] == ("native_outcome_unavailable" if native["state"] in {"unknown", "incomplete"}
        else "native_nonzero_exit" if native["state"] == "failed" and native["started"]
        else "native_start_failed" if native["state"] == "failed" else None)


def test_occurrence_qualification_identifies_the_actual_partial_stream():
    first, second = occurrence("stdout"), occurrence("stderr", role="stderr")
    second["completeness"] = "partial"
    _, failures = extraction._outcome_observations(outcome(), [first, second], "tiny")
    assert [(r["code"], r["occurrence_id"]) for r in failures] == [
        ("output_completeness_unestablished", "stderr")]


@pytest.mark.parametrize("completeness,newline,row_complete", [
    ("partial", False, False), ("unknown", False, False),
    ("partial", True, True), ("complete", False, True),
])
def test_partial_final_rows_preserve_symbols_without_false_inventory_failure(completeness, newline, row_complete):
    raw = b"0\tlcl|ALPHA\tALPHA\t8\tACGTACGT" + (b"\n" if newline else b"")
    row = occurrence(fmt="blastdbcmd_tabular", data=raw)
    row["completeness"] = completeness
    result = extraction.parse_blastdbcmd_sequences(raw, occurrence=row, operation=operation(),
        database_binding=binding(), outcome=outcome(state="failed", returncode=7))
    record, = result["records"]
    assert record["original_sequence"] == "ACGTACGT" and record["returned_symbol_count"] == 8
    assert (record["completeness"] == "complete") == row_complete
    assert (record["effective_range"] is not None) == row_complete
    assert result["population_completeness"] == "partial_selection"
    assert "native_nonzero_exit" in failure_codes(result)
    assert "output_inventory_incomplete" not in failure_codes(result)
    if not row_complete:
        assert failure_codes(record) == {"output_completeness_unestablished"}


