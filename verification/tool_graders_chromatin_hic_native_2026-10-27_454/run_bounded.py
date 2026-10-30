"""Packet-local launch/collection only, using the existing native lifecycle."""
from pathlib import Path
import hashlib
import json
import sys



_KNOWN_NOTE_PROVENANCE_PATHS = frozenset([
    "docs/EPISODE_STRUCTURE.md",
    "docs/TIME_AWARE_ESTIMATION.md",
    "docs/PRACTICAL_EXECUTION.md",
    "docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md",
    "docs/TASK_AND_STEERING.md",
    "docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/NUMERICAL_LEAF_CONTRACT_004.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_CALCULATION_CONTRACT_005.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/INTERVAL_EDGE_CLARIFICATIONS_006.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/MISSING_NATIVE_RECORD_CLARIFICATION_007.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_REFINEMENTS_009.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/CALCULATION_INPUT_CONTRACT_010.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/SHARED_CONTENT_AND_STREAM_FINALIZATION_011.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/BAM_REFERENCE_OBSERVATIONS_013.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/NATIVE_CASES_002.md",
    "verification/tool_graders_atac_differential_plan_2026-10-27_460/PREPARATION_SCOPE_001.md",
    "verification/tool_graders_atac_native_contract_2026-10-27_461/CONTRACT.md",
    "verification/tool_graders_atac_execution_contract_2026-10-27_466/CONTRACT.md",
    "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/CONTRACT.md",
    "verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_IMPLEMENTATION_HANDOFF_014.md",
    "verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_WORKFLOW_VERIFICATION_015.md",
    "verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/FULL_WORKFLOW_VERIFICATION_011.md",
    "verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/COMPLETE_EMPTY_POPULATION_CHECK_012.md",
    "verification/tool_graders_chromatin_workflow_2026-10-27_451/VERIFICATION_SCOPE.md",
    "verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/VERIFICATION_SCOPE.md",
    "verification/tool_graders_hic_workflow_repair_2026-10-27_465/REPAIR_CONTRACT.md",
    "verification/tool_graders_composed_assignment_transport_2026-10-27_458/CONTRACT.md",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/CONTRACT_001.md",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/SUMMARY_SHAPE_ADDENDUM_001.md",
    "verification/tool_graders_sequence_derivation_2026-10-26_279/PUBLICATION_SCHEMA_ADDENDUM_001.md",
    "verification/tool_graders_alignment_sites_2026-10-26_284/CONTRACT_001.md",
    "verification/tool_graders_alignment_sites_2026-10-26_284/RETURN_CONTRACT_002.md",
    "verification/tool_graders_alignment_sites_2026-10-26_282/OWN_ACTION_RETURN_PORT_PROPOSAL.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/PLAN_001.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONSUMER_FINDINGS_001.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_001.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_002.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_003.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_004.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_005.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_006.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_007.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_008.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_009.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_010.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_011.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_012.md",
    "verification/tool_graders_rna_comparison_contract_2026-10-26_362/CONTRACT_ADDENDUM_013.md",
    "verification/tool_graders_rna_comparison_inputs_2026-10-26_366/INTERFACES_001.md",
    "verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_001.md",
    "verification/tool_graders_rna_comparison_views_2026-10-26_368/INTERFACES_ADDENDUM_001.md",
    "verification/tool_graders_rna_comparison_presentation_2026-10-27_378/IMPLEMENTATION_CONTRACT_001.md",
    "verification/tool_graders_rna_single_input_text_contract_2026-10-27_384/PLAN_001.md"
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




PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
PYTHON = REPO / "reference/episode_tools/.venv/bin/python"


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path), "resolved_path": str(path.resolve()),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def save(path, value):
    if Path(path).name == 'receipt.json' and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, start_job, status, wait_job

operation, name, *arguments = sys.argv[1:]
if "/" in name or name in {"", ".", ".."}:
    raise ValueError("invalid_attempt_name")
attempt = PACKET / name
handle = NativeJobHandle(attempt / "handle.json")

if operation == "launch":
    script, *selected_arguments = arguments
    script = PACKET / script
    if script.parent != PACKET or not script.is_file():
        raise ValueError("packet_script_required")
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / "selected_input.py"
    snapshot.write_bytes(script.read_bytes())
    snapshot.chmod(0o444)
    (attempt / "cache").mkdir()
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296,
                            wall_seconds=None)
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONPATH": "",
        "XDG_CACHE_HOME": str(attempt / "cache"),
        "PIP_CACHE_DIR": str(attempt / "cache/pip"),
        "HDF5_PLUGIN_PATH": str(attempt / "no_external_hdf5_plugins"),
    }
    sources = [Path(__file__), script, snapshot]
    sources += [REPO / "gene_annotation_episode" / filename for filename in
                ("__init__.py", "local_jobs.py", "native_lifecycle.py", "_local_job_worker.py",
                 "acquisition.py", "domain.py", "public_configuration.py")]
    sources += [PYTHON, Path(sys.executable)]
    save(attempt / "source_pins_before.json", [pin(path) for path in sources])
    argv = [str(PYTHON), "-B", str(snapshot), *selected_arguments]
    save(attempt / "selected_request.json", {
        "argv": argv, "cwd": str(attempt), "policy": policy.to_dict(),
        "environment": environment, 
        
        "source_script": str(script), "selected_script_snapshot": str(snapshot),
        "scope": "prerequisite_fixture_verification_only",
    })
    start_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
              stdout_path=attempt / "stdout.txt", stderr_path=attempt / "stderr.txt",
              env=environment)
    save(attempt / "launch_status.json", status(handle))
    print(json.dumps({"attempt": str(attempt), "handle_path": str(handle.path),
                      "unit": handle.read()["unit"], "state": status(handle)["state"]}))
elif operation == "collect":
    # Follow the original handle through the shared wait function; never resubmit.
    outcome = wait_job(handle)
    final = status(handle)
    before = runtime_pin_rows(json.loads((attempt / "source_pins_before.json").read_text()))
    after = [pin(item["path"]) for item in before]
    save(attempt / "source_pins_after.json", after)
    save(attempt / "terminal_status.json", final)
    save(attempt / "receipt.json", {
        "returncode": outcome.returncode, "metadata": outcome.metadata,
        "stdout_path": str(outcome.stdout_path), "stderr_path": str(outcome.stderr_path),
        "handle_path": str(handle.path), "unit": handle.read()["unit"],
        "terminal": final["terminal"], "quiescent": final["quiescent"],
        "source_pins_unchanged": before == after,
        "changes": [{"before": old, "after": new} for old, new in zip(before, after) if old != new],
    })
    print(json.dumps({"attempt": str(attempt), "returncode": outcome.returncode,
                      "terminal": final["terminal"], "quiescent": final["quiescent"],
                      "source_pins_unchanged": before == after}))
    raise SystemExit(outcome.returncode)
else:
    raise ValueError("unknown_operation")
