"""Retained native bytes -> bounded numerical worker -> actual Store records.

The association fixtures add original biological subjects and operand bindings
to existing captured native runs. They are not new HMMER executions or episode
communication tests. Run with .venv/bin/python from the repository root.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.hmmer_native_result_views import NATIVE_HMMER_METRICS, family_for_program
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.native_hmmer_contracts import native_hmmer_digest, requested_job_from_native
from gene_annotation_episode.native_hmmer_result_publication import prepare_native_hmmer_grading, publish_selected_native_hmmer_rows
from gene_annotation_episode.native_hmmer_result_worker import _fasta
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "verification/tool_graders_native_hmmer_producer_2026-10-24/runs"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, sort_keys=True) + "\n")


def prohibit(*args, **kwargs):
    raise AssertionError("saved-sheet recalculation attempted external work or file acquisition")


def build(directory, native_case, role, ordinal, rows):
    original = RUNS / native_case / "attempt"
    bundle = json.loads((original / "bundle.json").read_text())
    program = bundle["program"]
    family = family_for_program(program)
    selector = {"version": "native_hmmer_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "rows": rows, "metrics": list(NATIVE_HMMER_METRICS[family])}}
    with Store(directory / "store") as store:
        bindings = []
        actual = None
        if role is not None:
            input_record = next(r for r in bundle["inputs"] if r["role"] == role)
            actual = _fasta((original / input_record["relative_path"]).read_text())[ordinal]
        store.create_problem(raw_sequence=actual["sequence"] if actual else "ACDEFGHIKLMNPQRSTVWY",
                             molecule="dna" if program in {"nhmmer", "nhmmscan"} else "protein")
        if actual:
            bindings = [{"operand_role": role, "record_ordinal": ordinal, "native_name": actual["name"],
                "native_accession": None, "subject_ref": store.validate_scope()["subject_refs"][0], "reference_ref": None}]
        artifacts = [{"role": row["role"], "format": row["format"], "relative_path": row["relative_path"],
            "artifact_ref": artifact_file(store, original / row["relative_path"])}
            for row in bundle["inputs"] + bundle["artifacts"]]
        # Explicit synthetic association metadata. No scientific output bytes or
        # original captured execution receipt are changed.
        job = bundle["requested_job"]["native_hmmer"]
        job["metadata"] = {}
        job["operand_bindings"] = bindings
        bundle["operand_bindings"] = bindings
        bundle["requested_job"] = requested_job_from_native(job)
        bundle["identity"]["requested_job_sha256"] = native_hmmer_digest(bundle["requested_job"])
        bundle_ref = store.artifact(canonical(bundle), "application/json")
        prepared = prepare_native_hmmer_grading(store, bundle=bundle, bundle_artifact_ref=bundle_ref,
            artifacts=artifacts, directory=directory, policy=POLICY, selector=selector)
        source = store.put("source", {"provider": "episode.execution_result", "accession": None,
            "uri": None, "artifact_ref": bundle_ref, "text_ref": None, "request_ref": None,
            "version": "native_hmmer_result_v1", "retrieved_at": None,
            "auxiliary_artifact_refs": [prepared["source_grading_artifact_ref"], *[r["artifact_ref"] for r in artifacts]]}, origin="tool")
        publication = publish_selected_native_hmmer_rows(store, source_ref=source["id"], bundle=bundle,
            prepared=prepared, scope=store.validate_scope(), selector=selector)
        sheet = json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
        scores = json.loads(store.get_artifact(prepared["scores_artifact_ref"]))
        from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
        from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
        from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores
        calculator = {"protein_domain": calculate_hmmer_search_scores,
            "nucleotide_locus": calculate_nhmmer_scores,
            "alignment_sequence": calculate_hmmalign_scores}[family]
        before = deepcopy(sheet)
        with patch.object(socket, "socket", prohibit), patch.object(subprocess, "Popen", prohibit), patch("builtins.open", prohibit):
            recalculated = calculator(sheet, parameters={})
            assert recalculated == scores
            assert sheet == before
        result = {"evidence_class": "retained_native_outputs_with_explicit_synthetic_store_binding",
            "original_native_bundle": str((original / "bundle.json").relative_to(ROOT)),
            "new_native_scientific_execution": False, "episode_communication_verified_here": False,
            "policy": POLICY.to_dict(), "selector": selector, "binding": bindings,
            "prepared": prepared, "source": source, "publication": publication,
            "observations": [store.get(row["observation_ref"]) for row in publication["rows"] if row["observation_ref"]],
            "recalculation": {"equal_saved_scores": True, "input_sheet_unchanged": True,
                "network_process_and_file_acquisition_prohibited": True}}
        save(directory / "EXAMPLE.json", result)
        save(directory / "sheet.json", sheet)
        save(directory / "scores.json", scores)
        return {"path": str(directory.relative_to(ROOT)), "native_case": native_case,
            "numerical_complete": prepared["numerical_complete"], "selected_rows": publication["rows"],
            "failures": publication["failures"], "recalculation": result["recalculation"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent / "examples")
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    args.directory.mkdir(parents=True, exist_ok=False)
    definitions = [
        ("protein_paired_vs_span", "hmmsearch_search_ordinary", "sequence_database", 2, {"offset": 2, "limit": 1}),
        ("unbound_profile_query", "hmmsearch_search_ordinary", None, None, {"offset": 0, "limit": 1}),
        ("nucleotide_reverse", "nhmmer_profile_ordinary", "sequence_database", 1, {"offset": 1, "limit": 1}),
        ("alignment_original_trim", "hmmalign_align_trim", "sequences", 1, {"offset": 1, "limit": 1}),
    ]
    results = []
    for name, native_case, role, ordinal, rows in definitions:
        directory = args.directory / name
        directory.mkdir()
        results.append(build(directory, native_case, role, ordinal, rows))
    save(args.directory.parent / "EXAMPLES.json", results)
    print(json.dumps({"examples": len(results), "all_saved_sheets_recalculate_exactly": True,
        "new_native_searches": 0, "directory": str(args.directory)}, sort_keys=True))


if __name__ == "__main__":
    main()
