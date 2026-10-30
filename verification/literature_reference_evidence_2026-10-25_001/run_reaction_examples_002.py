"""Additive precision/origin handoff examples; preserve examples001 unchanged.

Reuse the original controlled Workflow/replay machinery against new isolated
stores. Extra assertions require the scientific precision metadata from003 at
the selected outcome, frozen typed child form and admitted parent boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import run_reaction_examples as previous

BASE = Path(__file__).resolve().parent
OWNED = BASE / "reaction_examples_002"
PRECISION_FIELDS = (
    "independent_n", "reported_sample_sd", "derived_sample_sd", "ratio_uncertainty",
    "uncertainty_interpretation", "ratio_origin", "budget_origin",
)
SOURCE_FILES = (
    "gene_annotation_episode/literature_reaction_inputs.py",
    "gene_annotation_episode/literature_reaction_calculations.py",
    "gene_annotation_episode/literature_reaction_storage.py",
    "gene_annotation_episode/literature_reaction_prompt.py",
    "gene_annotation_episode/literature_episodes.py",
    "gene_annotation_episode/episode_services.py",
    "gene_annotation_episode/literature_experimental_prompt.py",
    "tests/test_literature_reaction_integration.py",
    "verification/literature_reference_evidence_2026-10-25_001/run_reaction_examples.py",
    "verification/literature_reference_evidence_2026-10-25_001/run_reaction_examples_002.py",
)
_PREVIOUS_CHECK = previous.check_cells


def hashes(paths):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def protected_hashes():
    paths = [BASE / "run_reaction_examples.py"]
    paths.extend(sorted(path for path in (BASE / "reaction_examples_001").rglob("*") if path.is_file()))
    return hashes(paths)


def source_hashes():
    return hashes([previous.ROOT / path for path in SOURCE_FILES])


def check_precision(metadata, *, name):
    assert set(PRECISION_FIELDS).issubset(metadata)
    primary = name == "primary_csid_reported_ratio"
    assert metadata["independent_n"] == (None if primary else 2)
    assert metadata["reported_sample_sd"] is None
    if primary:
        assert metadata["derived_sample_sd"] is None
    else:
        assert math.isclose(metadata["derived_sample_sd"], math.sqrt(.02), rel_tol=1e-12)
    assert metadata["ratio_uncertainty"] == ("unreported" if primary else "descriptive_sample_sd")
    assert metadata["uncertainty_interpretation"] == "descriptive_not_confidence_interval"
    assert metadata["ratio_origin"] == ("reported" if primary else "synthetic")
    assert metadata["budget_origin"] == (None if primary else "synthetic")


def check_cells(rows, *, name):
    _PREVIOUS_CHECK(rows, name=name)
    for row in rows:
        check_precision(row, name=name)


def check_saved_precision(directory, name):
    receipt = json.loads((directory / "RECEIPT.json").read_text())
    outcome = receipt["outcome"]["result"]
    check_precision(outcome, name=name)
    rows = receipt["actual_frozen_child_form"]["measurements"]
    check_cells(rows, name=name)
    admitted = receipt["actual_admitted_parent_subset"]
    check_cells(admitted, name=name)
    assert rows == admitted
    details = receipt["saved_payload"]["sheet"]["ratio_details"]
    for row in rows:
        assert row["independent_n"] == details["independent_n"]
        assert row["reported_sample_sd"] == details["reported_sample_sd"]
        assert row["derived_sample_sd"] == details["derived_sample_sd"]["value"]
        assert {field: row[field] for field in PRECISION_FIELDS} == {
            field: outcome[field] for field in PRECISION_FIELDS}
    return {"case": name, "status": "passed", "requested_cells": len(rows),
        "selected_outcome_and_frozen_admitted_metadata_equal": True,
        "precision_metadata": {field: rows[0][field] for field in PRECISION_FIELDS},
        "original_source_sha256": receipt["direct_source_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--reopen", action="store_true")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory != OWNED:
        raise ValueError("owned_reaction_example002_directory_required")
    protected_before = protected_hashes()
    sources_before = source_hashes()
    previous.check_cells = check_cells
    if args.reopen:
        cases = [previous.reopen_case(directory / name) for name in previous.NAMES]
        precision = [check_saved_precision(directory / name, name) for name in previous.NAMES]
        result = {"status": "passed", "model_backed": False,
            "scope": "fresh process closed controlled Workflow replay; not live host restart",
            "cases": cases, "precision_checks": precision}
        target = directory / "REOPEN_RECEIPT.json"
    else:
        directory.mkdir(parents=True, exist_ok=False)
        cases = [previous.run_case(directory / name, name) for name in previous.NAMES]
        precision = [check_saved_precision(directory / name, name) for name in previous.NAMES]
        result = {"status": "passed", "model_backed": False,
            "cases": cases, "precision_checks": precision}
        target = directory / "EXAMPLES_RECEIPT.json"
    protected_after = protected_hashes()
    assert protected_before == protected_after, "original001_files_must_remain_unchanged"
    result["preserved001_files"] = protected_after
    result["source_sha256_before"] = sources_before
    result["source_sha256_after"] = source_hashes()
    result["source_files_unchanged_during_command"] = sources_before == result["source_sha256_after"]
    previous.save(target, result)
    print(json.dumps({"status": result["status"], "model_backed": False,
        "cases": [{"case": row["case"], "status": row["status"],
            "precision_metadata": row["precision_metadata"]} for row in precision],
        "preserved001_file_count": len(protected_after),
        "source_files_unchanged_during_command": result["source_files_unchanged_during_command"]}))
