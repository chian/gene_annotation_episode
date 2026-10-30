"""Administrative launch/collection; scientific imports and tests stay bounded."""
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
operation, name = sys.argv[1:3]
attempt = PACKET / name


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size_bytes': path.stat().st_size}


def save(path, value):
    if Path(path).name == 'receipt.json' and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


if operation == 'launch':
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(REPO / package, snapshot / package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    tests = ['test_chromatin_hic_sheet_contracts.py', 'test_chromatin_hic_return_schema_compatibility.py',
        'test_chromatin_interaction_contracts.py', 'test_chromatin_interaction_tables.py',
        'test_chromatin_interaction_inputs.py', 'test_chromatin_interaction_return_views.py',
        'test_chromatin_interaction_returns.py', 'test_chromatin_cooler_inputs.py']
    files = ['tests/' + name for name in tests] + ['pyproject.toml',
        'tests/test_chromatin_interaction_result_receipts.py',
        'verification/tool_graders_chromatin_hic_records_2026-10-27_456/run_bounded.py',
        'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json',
        'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/four-bin-raw-weighted.cool',
        'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/six-bin-all-full-windows.cool']
    files += [str(p.relative_to(REPO)) for p in (REPO / 'verification/tool_graders_chromatin_hic_contract_2026-10-27_452/schema002').glob('*.actual_schema.json')]
    files += ['verification/tool_graders_chromatin_hic_native_2026-10-27_454/' + name for name in
              ('native004/four.hic', 'native004/BYTE_AUDIT.json', 'native009/valid/output.hic', 'native009/valid/BYTE_AUDIT.json')]
    files += [str(p.relative_to(REPO)) for p in (REPO / 'research/slotted_process_library/publications/2026-10-24-001').rglob('*') if p.is_file()]
    for name in files:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    for path in snapshot.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted([p for p in snapshot.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    snapshot.chmod(0o555)
    for name in ('temporary', 'cache'):
        (attempt / name).mkdir()
    python = REPO / '.venv/bin/python'
    refsite = REPO / 'reference/episode_tools/.venv/lib/python3.12/site-packages'
    rootsite = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, refsite, rootsite))), 'PYTHONNOUSERSITE': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'HIC456_ATTEMPT': str(attempt), 'RECEIPT448_REPO': str(snapshot), 'RECEIPT448_ATTEMPT': str(attempt),
        'TMPDIR': str(attempt / 'temporary'),
        'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
        'HDF5_PLUGIN_PATH': str(attempt / 'no-hdf5-plugins'), 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    argv = [str(python), '-B', '-S', '-m', 'pytest', '-vv', '--tb=long', '-p', 'no:cacheprovider',
        '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
        *[str(snapshot / 'tests' / name) for name in tests], '--junitxml=' + str(attempt / 'junit.xml'), *sys.argv[3:]]
    shutil.copyfile(REPO / 'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json', attempt / 'WORKED_RECORDS.json')
    pins = [pin(p) for p in sorted(snapshot.rglob('*')) if p.is_file()]
    save(attempt / 'source_pins_before.json', pins)
    save(attempt / 'binary_pins_before.json', [pin(python), pin(__file__)])
    sys.path.insert(0, str(snapshot))
else:
    sys.path.insert(0, str(attempt / 'source_snapshot'))

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect
handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'policy': policy.to_dict(), 'cwd': str(attempt)})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': status(handle)['state']}))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps(view))
        raise SystemExit(3)
    result = collect(handle)
    before = runtime_pin_rows(json.loads((attempt / 'source_pins_before.json').read_text()))
    after = [pin(row['path']) for row in before]
    binaries = json.loads((attempt / 'binary_pins_before.json').read_text())
    binaries_after = [pin(row['path']) for row in binaries]
    save(attempt / 'source_pins_after.json', after)
    save(attempt / 'binary_pins_after.json', binaries_after)
    checkout = []
    for row in before:
        path = REPO / Path(row['path']).relative_to(attempt / 'source_snapshot')
        current = pin(path)
        if (current['sha256'], current['size_bytes']) != (row['sha256'], row['size_bytes']):
            checkout.append({'before': row, 'after': current})
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'],
        'metadata': result.metadata, 'source_pins_unchanged': before == after,
        'binary_pins_unchanged': binaries == binaries_after, 'checkout_drift': checkout,
        'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('returncode', 'source_pins_unchanged', 'binary_pins_unchanged', 'unit')}))
    raise SystemExit(result.returncode)
else:
    raise ValueError('unknown operation')
