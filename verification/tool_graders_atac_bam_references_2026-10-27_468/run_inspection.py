"""Administrative runner adapted from packet460's immutable native lifecycle."""
from pathlib import Path
import hashlib
import json
import os
import shutil
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
PLAN = REPO / 'verification/tool_graders_atac_differential_plan_2026-10-27_460'
operation, name = sys.argv[1:3]
attempt = PACKET / name


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(path, value):
    if Path(path).name == 'receipt.json' and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


if operation == 'launch':
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(REPO / package, snapshot / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for filename in ('inspect_bam_headers.py', 'run_inspection.py'):
        shutil.copyfile(PACKET / filename, snapshot / filename)
    for path in snapshot.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted((p for p in snapshot.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    snapshot.chmod(0o555)
    for directory in ('temporary', 'cache'):
        (attempt / directory).mkdir()
    prepared_path = PLAN / 'prerequisite001/prepared_software.json'
    prepared = json.loads(prepared_path.read_text())
    for record in prepared['files']:
        assert pin(record['path']) == record
    manifest = json.loads((PLAN / 'native001/NATIVE_FILES.json').read_text())
    inputs = []
    for number in (1, 2):
        relative = f'bam_inputs/condition{number}.bam'
        expected = next(row for row in manifest['files'] if row['path'] == relative)
        actual = pin(PLAN / 'native001' / relative)
        assert all(actual[key] == expected[key] for key in ('size_bytes', 'sha256'))
        inputs.append(actual)
    save(attempt / 'inspection_inputs.json', inputs)
    (attempt / 'inspection_inputs.json').chmod(0o444)
    save(attempt / 'input_pins_before.json', inputs + [pin(prepared_path), pin(PLAN / 'native001/NATIVE_FILES.json')])
    save(attempt / 'source_pins_before.json', [pin(p) for p in sorted(snapshot.rglob('*')) if p.is_file()]
         + [pin(attempt / 'inspection_inputs.json')])
    package_root = Path(prepared['python']).parent.parent / 'lib/python3.11/site-packages'
    binaries = [pin(REPO / '.venv/bin/python'), pin(Path(prepared['python']).resolve()), pin(__file__)]
    binaries.extend(pin(p) for p in sorted(package_root.rglob('*'))
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    save(attempt / 'binary_pins_before.json', binaries)
    env = dict(ATAC_REFERENCE_ATTEMPT=str(attempt), PYTHONPATH='', PYTHONNOUSERSITE='1',
               PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(attempt / 'temporary'), TMP=str(attempt / 'temporary'),
               TEMP=str(attempt / 'temporary'), XDG_CACHE_HOME=str(attempt / 'cache'),
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    argv = [prepared['python'], '-B', str(snapshot / 'inspect_bam_headers.py')]
sys.path.insert(0, str(attempt / 'source_snapshot'))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', dict(argv=argv, environment=env, policy=policy.to_dict(), cwd=str(attempt)))
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
                stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps(dict(handle=str(handle.path), unit=handle.read()['unit'], state=status(handle)['state'])))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps(view))
        raise SystemExit(3)
    result = collect(handle)
    receipt = dict(returncode=result.returncode, terminal=view['terminal'], quiescent=view['quiescent'],
                   metadata=result.metadata, handle=str(handle.path), unit=handle.read()['unit'])
    for kind in ('source', 'input', 'binary'):
        before = runtime_pin_rows(json.loads((attempt / (kind + '_pins_before.json')).read_text()))
        after = [pin(row['path']) for row in before]
        save(attempt / (kind + '_pins_after.json'), after)
        receipt[kind + '_pins_unchanged'] = before == after
    save(attempt / 'receipt.json', receipt)
    print(json.dumps(receipt))
    raise SystemExit(result.returncode)
else:
    raise ValueError('unsupported_operation')
