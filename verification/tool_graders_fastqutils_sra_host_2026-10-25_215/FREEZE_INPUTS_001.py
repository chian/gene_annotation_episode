"""Freeze the verified211 candidate and exact198 host helper closure."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

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


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UPSTREAM = ROOT / 'verification/tool_graders_fastqutils_sra_implementation_2026-10-25_211'
HELPERS = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/candidate/tests'
FROZEN = HERE / 'candidate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    if 'receipt' in name.lower() and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def main():
    final = json.loads((UPSTREAM / 'FINAL_RECEIPT_001.json').read_text())
    assert final['passed']
    for name, expected in final['files'].items():
        assert sha(UPSTREAM / name) == expected, name
    manifest = json.loads((UPSTREAM / 'checks_001/source_before.json').read_text())
    assert len(manifest) == 1113
    incoming, copies = {}, []
    FROZEN.mkdir(exist_ok=False)

    def copy(source, destination, expected=None):
        if not runtime_pin_rows([{'path': str(source), 'sha256': expected}]):
            return
        observed = sha(source)
        assert expected is None or observed == expected, source
        incoming[str(source)] = observed
        previous = sha(destination) if destination.exists() else None
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert sha(destination) == observed
        copies.append(dict(source=str(source), destination=str(destination), sha256=observed,
                           replaced_sha256=previous))

    for name, expected in manifest.items():
        copy(UPSTREAM / 'candidate' / name, FROZEN / name, expected)
    todo, seen = ['test_bvbrc_fastqutils_episode_flow'], set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        source = HELPERS / (name + '.py')
        for node in ast.walk(ast.parse(source.read_text())):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                       [item.name for item in node.names] if isinstance(node, ast.Import) else [])
            todo.extend(module for module in modules if (HELPERS / (module + '.py')).is_file())
    for name in sorted(seen):
        source, destination = HELPERS / (name + '.py'), FROZEN / 'tests' / (name + '.py')
        # Preserve existing211 helpers whenever identical; reject differences.
        if destination.exists():
            assert sha(source) == sha(destination), name
        copy(source, destination)
    for source in sorted((HELPERS / 'fixtures/bvbrc_fastqutils/integration').rglob('*')):
        if source.is_file():
            copy(source, FROZEN / 'tests' / source.relative_to(HELPERS))
    source = UPSTREAM / 'candidate/tests/fixtures/bvbrc_fastqutils/sra/native_selected_run.json'
    copy(source, HERE / 'native_inputs/native_selected_run.json',
         manifest[str(source.relative_to(UPSTREAM / 'candidate'))])
    protected = [ROOT / 'AGENTS.md', ROOT / 'GOAL.md',
        ROOT / 'research/tool_grader_inventory_2026-10-24/WORK_STATUS.json',
        Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt'),
        UPSTREAM / 'checks_001/source_before.json', UPSTREAM / 'FINAL_RECEIPT_001.json',
        UPSTREAM / 'HANDOFF_001.md', HERE / 'WORKLOAD_001.md',
        ROOT / 'verification/tool_graders_fastqutils_sra_contract_2026-10-25_210/SRA_IMPLEMENTATION_CONTRACT_001.md']
    for path in protected:
        if runtime_pin_rows([{'path': str(path)}]):
            incoming[str(path)] = sha(path)
    before = {str(path): sha(path) for path in sorted(FROZEN.rglob('*')) if path.is_file()}
    before.update({str(path): sha(path) for path in sorted((HERE / 'native_inputs').iterdir()) if path.is_file()})
    save('incoming_before.json', incoming)
    save('frozen_before.json', before)
    save('copy_manifest.json', copies)
    save('helper_dependency_closure.json', sorted(name + '.py' for name in seen))
    report = dict(completed_at=datetime.now(timezone.utc).isoformat(), original_candidate_paths=len(manifest),
        upstream_receipt_paths_verified=len(final['files']), helper_modules=len(seen),
        incoming_paths=len(incoming), frozen_paths=len(before), scientific_pin=final['provider_pin'],
        source_bytes=sum(path.stat().st_size for path in HERE.rglob('*') if path.is_file()),
        production_edited=False, workflow_state_copied=False)
    assert report['source_bytes'] < 4 * 1024**3
    save('freeze_receipt.json', report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
