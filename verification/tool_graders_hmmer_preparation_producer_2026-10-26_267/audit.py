"""Read saved producer evidence and hash its actual source; no native commands."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

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


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.native_hmmer_preparation_driver import validate_preparation_bundle_files


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


check = HERE / sys.argv[1]
intent = json.loads((check / "intent.json").read_bytes())
runtime_sources = runtime_pin_rows([{'path': path, 'sha256': digest} for path, digest in intent["source_hashes"].items()])
assert all(sha(ROOT / row['path']) == row['sha256'] for row in runtime_sources)
cases = []
for receipt in sorted((check / "temporary").rglob("native-lifecycle-receipt.json")):
    case = receipt.parent
    plan_file = case / "plan.json"
    if not plan_file.exists():
        matches = list(case.rglob("hmmer-preparation-plan.json"))
        assert len(matches) == 1
        plan_file = matches[0]
    plan = json.loads(plan_file.read_bytes())
    bundle_file = Path(plan["attempt_directory"]) / "bundle.json"
    bundle = validate_preparation_bundle_files(json.loads(bundle_file.read_bytes()), bundle_file.parent)
    measured = json.loads(receipt.read_bytes())
    assert measured["metadata"]["verified_cgroup"]["memory_max"] == 20 * 1024**3
    assert measured["metadata"]["verified_cgroup"]["runtime_max"] == "infinity"
    assert measured["metadata"]["policy"]["scratch_bytes"] == 4 * 1024**3
    cases.append({"case": str(case.relative_to(HERE)), "program": bundle["program"], "mode": bundle["mode"],
        "returncode": bundle["returncode"], "failure_codes": [r["code"] for r in bundle["failures"]],
        "artifact_bytes": {r["role"]: r["size_bytes"] for r in bundle["artifacts"]},
        "native_abi": bundle["native_abi"], "plan": str(plan_file.relative_to(HERE)),
        "bundle": str(bundle_file.relative_to(HERE)), "receipt": str(receipt.relative_to(HERE)),
        "bundle_sha256": sha(bundle_file), "receipt_sha256": sha(receipt)})
seen = {(case["program"], case["mode"]) for case in cases if case["returncode"] == 0}
assert seen == {(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes}
suite = ET.parse(check / "junit.xml").getroot()[0]
assert suite.attrib["failures"] == "0" and suite.attrib["errors"] == "0"
case_output = HERE / (check.name + "_native_cases.json")
manifest_output = HERE / (check.name + "_source_manifest.json")
assert not case_output.exists() and not manifest_output.exists()
case_output.write_text(json.dumps({"verification": check.name, "pytest": suite.attrib,
    "actual_native_case_count": len(cases), "successful_program_mode_count": len(seen), "cases": cases,
    "skipped_note_provenance": list(_SKIPPED_NOTE_PROVENANCE),
    "pin_validation_scope": "scientific_and_runtime_inputs_excluding_reported_note_provenance"}, indent=2) + "\n")

sources = list(intent["source_hashes"])
sources += ["gene_annotation_episode/" + path for path in (
    "native_infernal_contracts.py", "native_infernal_driver.py", "native_infernal_preparation_contracts.py",
    "native_infernal_preparation_job_schema.py", "native_infernal_preparation_driver.py", "native_infernal_preparation_local.py",
    "native_lifecycle.py", "local_jobs.py", "_local_job_worker.py", "practical_execution_state.py")]
sources += ["AGENTS.md", "GOAL.md", "docs/EPISODE_STRUCTURE.md", "docs/TIME_AWARE_ESTIMATION.md",
    "docs/PRACTICAL_EXECUTION.md", "docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md",
    "verification/tool_graders_hmmer_preparation_2026-10-26_261/PRODUCER_CONTRACT_001.md",
    "verification/tool_graders_hmmer_preparation_2026-10-26_261/FM_PRODUCER_CONSUMER_HANDOFF_001.md",
    "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/REPORT.md"]
for program in PROGRAM_MODES:
    sources += [f"resources/software/infernal-1.1.5/hmmer/src/{program}",
        f"resources/software/infernal-1.1.5/hmmer/src/{program}.c",
        f"verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/contracts/{program}.md"]
sources += ["resources/software/infernal-1.1.5/hmmer/src/" + name for name in
    ("p7_config.h", "p7_hmmfile.c", "p7_builder.c", "fm_general.c", "fm_sse.c")]
sources += ["resources/software/infernal-1.1.5/easel/" + name for name in
    ("esl_config.h", "esl_alphabet.c", "esl_msa.c", "esl_msaweight.c", "esl_msaweight.h", "esl_msafile.c",
     "esl_msafile_stockholm.c", "esl_vectorops.c", "esl_scorematrix.c", "formats/BLOSUM62")]
sources += [str(path.relative_to(ROOT)) for path in (HERE / "FIELDS.md", HERE / "run_tests.py", HERE / "audit.py", HERE / "SSI_ORIGINAL_PATH_HANDOFF_001.md")]
paths = [ROOT / path for path in sources]
paths = [Path(row['path']) for row in runtime_pin_rows([{'path': str(path)} for path in paths])]
manifest = {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path):
    {"size_bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(set(paths))}
manifest_output.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"tests": suite.attrib["tests"], "actual_native_cases": len(cases), "successful_program_modes": len(seen),
    "source_files": len(manifest), "native_cases_sha256": sha(case_output),
    "source_manifest_sha256": sha(manifest_output)}))
