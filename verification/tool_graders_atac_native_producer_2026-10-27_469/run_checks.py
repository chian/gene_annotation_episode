"""Administrative selection/observation through the existing bounded lifecycle."""
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
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return {'path': str(path), 'sha256': hasher.hexdigest(), 'size_bytes': path.stat().st_size}

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
    tests = ['test_native_atac_differential_contracts.py', 'test_native_atac_differential_producer.py', 'test_native_atac_differential_capture.py']
    files = [*['tests/' + name for name in tests], 'pyproject.toml',  str(Path(__file__).relative_to(REPO))]
    if (PACKET / 'accept_native.py').exists():
        files.append(str((PACKET / 'accept_native.py').relative_to(REPO)))
    native = REPO / 'verification/tool_graders_atac_differential_plan_2026-10-27_460/native001'
    files.append(str((native / 'NATIVE_FILES.json').relative_to(REPO)))
    files.extend(str((native / row['path']).relative_to(REPO)) for row in json.loads((native / 'NATIVE_FILES.json').read_text())['files'])
    for filename in files:
        target = snapshot / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / filename, target)
    for path in snapshot.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    for path in sorted((p for p in snapshot.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True): path.chmod(0o555)
    snapshot.chmod(0o555)
    for part in ('temporary', 'cache'):
        (attempt / part).mkdir()
    python = REPO / '.venv/bin/python'
    site = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, site))), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'ATAC_NATIVE_ATTEMPT': str(attempt),
        'ATAC_NATIVE_REPO': str(REPO), 'ATAC_NATIVE_FIXTURES': str(snapshot / native.relative_to(REPO))}
    if '--native' in sys.argv[3:]:
        argv = [str(python), '-B', '-S', str(snapshot / (PACKET / 'accept_native.py').relative_to(REPO))]
    else:
        argv = [str(python), '-B', '-S', '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
            '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
            *[str(snapshot / 'tests' / name) for name in tests], '--junitxml=' + str(attempt / 'junit.xml'), *sys.argv[3:]]
    save(attempt / 'source_pins_before.json', [pin(p) for p in sorted(snapshot.rglob('*')) if p.is_file()])
    dependencies = [pin(python), pin(__file__)]
    # Freeze installed Python execution dependencies; native acceptance adds its
    # distinct MACS2/NumPy pins before its original native handle is started.
    for package in ('pytest', '_pytest', 'pluggy', 'packaging', 'iniconfig', 'pygments', 'jsonschema', 'attr', 'attrs', 'referencing', 'rpds', 'jsonschema_specifications', 'typing_extensions.py'):
        base = site / package
        paths = [base] if base.is_file() else base.rglob('*') if base.is_dir() else []
        dependencies.extend(pin(p) for p in paths if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    save(attempt / 'binary_pins_before.json', dependencies)
else:
    snapshot = attempt / 'source_snapshot'
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect
handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'policy': policy.to_dict(), 'cwd': str(attempt)})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path, stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': status(handle)['state']}))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({'state': view['state'], 'terminal': view['terminal'], 'quiescent': view['quiescent']}))
        raise SystemExit(3)
    result = collect(handle)
    sources = runtime_pin_rows(json.loads((attempt / 'source_pins_before.json').read_text()))
    binaries = json.loads((attempt / 'binary_pins_before.json').read_text())
    source_after, binary_after = [pin(r['path']) for r in sources], [pin(r['path']) for r in binaries]
    save(attempt / 'source_pins_after.json', source_after)
    save(attempt / 'binary_pins_after.json', binary_after)
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'], 'metadata': result.metadata,
        'source_pins_unchanged': sources == source_after, 'binary_pins_unchanged': binaries == binary_after,
        'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('returncode', 'terminal', 'quiescent', 'source_pins_unchanged', 'binary_pins_unchanged')}))
    raise SystemExit(result.returncode)
else:
    raise ValueError('unsupported operation')
