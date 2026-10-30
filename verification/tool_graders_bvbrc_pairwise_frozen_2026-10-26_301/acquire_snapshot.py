"""Acquire an all-or-nothing stable source copy for the unchanged pairwise test."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

_KNOWN_NOTE_PROVENANCE_PATHS = frozenset([
    'docs/EPISODE_STRUCTURE.md',
    'docs/TIME_AWARE_ESTIMATION.md',
    'docs/PRACTICAL_EXECUTION.md',
    'docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md',
    'docs/TASK_AND_STEERING.md',
    'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/NUMERICAL_LEAF_CONTRACT_004.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_CALCULATION_CONTRACT_005.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_EDGE_CLARIFICATIONS_006.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/MISSING_NATIVE_RECORD_CLARIFICATION_007.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_REFINEMENTS_009.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_CONTRACT_010.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/SHARED_CONTENT_AND_STREAM_FINALIZATION_011.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/BAM_REFERENCE_OBSERVATIONS_013.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/NATIVE_CASES_002.md',
    'verification/tool_graders_atac_differential_plan_2026-10-27_460/PREPARATION_SCOPE_001.md',
    'verification/tool_graders_atac_native_contract_2026-10-27_461/CONTRACT.md',
    'verification/tool_graders_atac_execution_contract_2026-10-27_466/CONTRACT.md',
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/CONTRACT.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_IMPLEMENTATION_HANDOFF_014.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_WORKFLOW_VERIFICATION_015.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/FULL_WORKFLOW_VERIFICATION_011.md',
    'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/COMPLETE_EMPTY_POPULATION_CHECK_012.md',
    'verification/tool_graders_chromatin_workflow_2026-10-27_451/VERIFICATION_SCOPE.md',
    'verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/VERIFICATION_SCOPE.md',
    'verification/tool_graders_hic_workflow_repair_2026-10-27_465/REPAIR_CONTRACT.md',
    'verification/tool_graders_composed_assignment_transport_2026-10-27_458/CONTRACT.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/CONTRACT_001.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/SUMMARY_SHAPE_ADDENDUM_001.md',
    'verification/tool_graders_sequence_derivation_2026-10-26_279/PUBLICATION_SCHEMA_ADDENDUM_001.md',
    'verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md',
    'verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md',
    'verification/tool_graders_alignment_sites_2026-10-26_282/OWN_ACTION_RETURN_PORT_PROPOSAL.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/PLAN_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONSUMER_FINDINGS_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_001.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_002.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_003.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_004.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_005.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_006.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_007.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_008.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_009.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_010.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_011.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_012.md',
    'verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_013.md',
    'verification/tool_graders_rna_comparison_inputs_2026-10-26_366/INTERFACES_001.md',
    'verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_001.md',
    'verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_ADDENDUM_001.md',
    'verification/tool_graders_rna_comparison_presentation_2026-10-27_378/IMPLEMENTATION_CONTRACT_001.md',
    'verification/tool_graders_rna_single_input_text_contract_2026-10-27_384/PLAN_001.md',
])
_SKIPPED_NOTE_PROVENANCE = []


def note_provenance_path(value):
    """Recognize only named governance files and explicitly retired provenance."""
    path = Path(value)
    if path.name.lower() in {'agents.md', 'agent.md', 'goal.md',
                             'original-user-goal.txt', 'immutable_goal.txt'}:
        return True
    if path.name == 'pasted-text-1.txt' and set(path.parts) & {
            'e94d8875-9d86-482e-9bb3-8887aa457b88',
            '6960b4a1-b2e0-46d4-8003-fcb7685a2232'}:
        return True
    normalized = path.as_posix()
    return any(normalized == known or normalized.endswith('/' + known)
               for known in _KNOWN_NOTE_PROVENANCE_PATHS)


def runtime_pin_rows(rows):
    """Retain unknown Markdown and all scientific/runtime pin records."""
    kept = []
    for row in rows:
        if any(note_provenance_path(row[key]) for key in ('path', 'source_path')
               if row.get(key)):
            _SKIPPED_NOTE_PROVENANCE.append({
                'path': row.get('path'), 'source_path': row.get('source_path'),
                'recorded_sha256': row.get('sha256'),
                'validation': 'not_validated_non_runtime_note_provenance',
            })
        else:
            kept.append(row)
    return kept


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
SNAPSHOT = EVIDENCE / "snapshot"
AUTHORITY = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    if 'receipt' in path.name.lower() and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def describe(path):
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise RuntimeError("source_changed_during_read:" + str(path))
    return {"sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw),
            "stat": {key: getattr(after, key) for key in fields}}


def selected_files(method_source):
    result = []
    for original, relative in (
        (ROOT / "gene_annotation_episode", Path("gene_annotation_episode")),
        (method_source, Path("method_loop")),
        (ROOT / "tests", Path("tests")),
        (ROOT / "research/slotted_process_library/publications/2026-10-24-001",
         Path("research/slotted_process_library/publications/2026-10-24-001")),
    ):
        if not original.is_dir():
            raise RuntimeError("missing_snapshot_prerequisite:" + str(original))
        for path in sorted(original.rglob("*")):
            if any(part in EXCLUDED_PARTS for part in path.relative_to(original).parts):
                continue
            if path.is_symlink():
                raise RuntimeError("mutable_symlink_not_allowed:" + str(path))
            if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                result.append((path, SNAPSHOT / relative / path.relative_to(original), "snapshot"))
    result.append((ROOT / "pyproject.toml", SNAPSHOT / "pyproject.toml", "snapshot"))
    authorities = [
        (AUTHORITY, "original-goal.txt"),
        (ROOT / "AGENTS.md", "AGENTS.md"),
        (ROOT / "GOAL.md", "GOAL.md"),
        *[(ROOT / "docs" / name, name) for name in (
            "EPISODE_STRUCTURE.md", "TIME_AWARE_ESTIMATION.md", "TASK_AND_STEERING.md",
            "PRACTICAL_EXECUTION.md", "PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md",
            "TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md")],
        (ROOT / "research/tool_grader_inventory_2026-10-24/WORK_STATUS.json", "WORK_STATUS.json"),
        (ROOT / "verification/tool_graders_blast_regressions_2026-10-26_299/DIAGNOSIS.json", "prior-DIAGNOSIS.json"),
        (ROOT / "verification/tool_graders_blast_regressions_2026-10-26_299/broad_source_provenance_differences.json", "prior-source-differences.json"),
        (ROOT / "verification/tool_graders_blast_geometry_2026-10-26_295/checks_003/RECOVERED_RECEIPT_001.json", "prior-RECOVERED_RECEIPT_001.json"),
    ]
    result.extend((original, EVIDENCE / "authority" / name, "authority") for original, name in authorities)
    result = [row for row in result if runtime_pin_rows([{'path': str(row[0])}])]
    for original, _, _ in result:
        if not original.is_file() or original.is_symlink():
            raise RuntimeError("missing_or_symlinked_prerequisite:" + str(original))
    return sorted(result, key=lambda item: str(item[1]))


def main():
    if SNAPSHOT.exists() or (EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json").exists():
        raise RuntimeError("refuse_to_replace_existing_snapshot")
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.find_spec("method_loop")
    if spec is None or not spec.origin:
        raise RuntimeError("missing_actual_method_loop_package")
    method_source = Path(spec.origin).resolve().parent
    started = stamp()
    files = selected_files(method_source)
    before = {str(source): describe(source) for source, _, _ in files}
    before_finished = stamp()
    for source, destination, _ in files:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            output.write(source.read_bytes())
        destination.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    copied_at = stamp()
    after = {str(source): describe(source) for source, _, _ in files}
    names_stable = files == selected_files(method_source)
    rows = []
    for source, destination, category in files:
        copied = describe(destination)
        original_before, original_after = before[str(source)], after[str(source)]
        rows.append({"original_path": str(source), "copied_path": str(destination),
            "category": category, "sha256": copied["sha256"], "byte_count": copied["byte_count"],
            "source_before": original_before, "source_after": original_after,
            "source_stable": original_before == original_after,
            "copy_matches_source": copied["sha256"] == original_before["sha256"] == original_after["sha256"]})
    stable = names_stable and all(row["source_stable"] and row["copy_matches_source"] for row in rows)
    manifest = {"schema": "stable_isolated_verification_snapshot_v1", "started_at": started,
        "before_hashes_completed_at": before_finished, "copy_completed_at": copied_at,
        "after_hashes_completed_at": stamp(), "source_root": str(ROOT), "snapshot_root": str(SNAPSHOT),
        "actual_method_loop_source": str(method_source), "file_list_stable": names_stable,
        "source_and_copy_stable": stable, "file_count": len(rows),
        "byte_count": sum(row["byte_count"] for row in rows), "files": rows,
        "copy_policy": "Complete source packages and tests/fixtures; exact selected publication and pyproject; no bytecode, caches, virtualenv, runs or symlinks."}
    write(EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json", manifest)
    if not stable:
        raise RuntimeError("snapshot_acquisition_unstable; retained_for_diagnosis_not_execution")
    for folder in (SNAPSHOT / "gene_annotation_episode", SNAPSHOT / "method_loop", SNAPSHOT / "tests", SNAPSHOT / "research", EVIDENCE / "authority"):
        for path in sorted((p for p in folder.rglob("*") if p.is_dir()), reverse=True):
            path.chmod(0o555)
        folder.chmod(0o555)
    (EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json").chmod(0o444)
    receipt = {"manifest_path": str(EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json"),
        "manifest_sha256": describe(EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json")["sha256"],
        "source_and_copy_stable": stable, "file_count": len(rows), "byte_count": manifest["byte_count"],
        "read_only_source_files_and_directories": True, "mutable_output_root": str(SNAPSHOT / "verification")}
    write(EVIDENCE / "SOURCE_SNAPSHOT_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
