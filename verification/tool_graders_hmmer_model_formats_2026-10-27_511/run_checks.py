"""HMMER model-format checks using the existing bounded verification runner.

Only stdlib staging and local lifecycle bootstrap run on the host. Application
imports, installation, dependency inspection, scientific work and tests execute
inside the selected 20 GiB/4 GiB/zero-swap/no-wall-limit handle.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
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


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': path.stat().st_size}


def save(path, data):
    if Path(path).name == 'receipt.json' and _SKIPPED_NOTE_PROVENANCE:
        data = {**data, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def freeze(root):
    for path in root.rglob('*'):
        if path.is_file():
            path.chmod(0o555 if os.access(path, os.X_OK) else 0o444)
    for path in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=('launch', 'status', 'collect'))
parser.add_argument('attempt')
parser.add_argument('--mode', choices=('check',), default='check')
parser.add_argument('--dependencies-from', type=Path)
parser.add_argument('--test', action='append', required=False)
parser.add_argument('--support-file', action='append', default=[])
parser.add_argument('--support-tree', action='append', default=[])
parser.add_argument('--native-executable', action='append', default=[])
args = parser.parse_args()
if not args.attempt.isidentifier():
    parser.error('simple attempt name required')
attempt = PACKET / args.attempt
if args.operation == 'launch':
    if args.mode is None:
        parser.error('explicit mode required')
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(REPO / package, snapshot / package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    selected_tests = args.test
    if not selected_tests:
        parser.error('launch requires at least one explicit --test')
    save(attempt / 'selected_tests.json', selected_tests)
    shutil.copytree(REPO / 'tests', snapshot / 'tests', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    fixture_roots = [
        'research/slotted_process_library/publications/2026-10-24-001',
        'verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259',
        'verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check005/temporary',
        'verification/tool_graders_hmmer_preparation_capture_2026-10-26_270/check005/temporary',
        'verification/tool_graders_hmmer_preparation_grading_2026-10-26_271/modes001',
        'verification/tool_graders_hmmer_preparation_results_2026-10-26_273/check003/temporary',
        *args.support_tree,
    ]
    fixture_files = [
        'verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check005_native_cases.json',
        *args.support_file,
        *args.native_executable,
    ]
    skipped_fixture_entries = []
    def fixture_ignore(directory, names):
        skipped = set(shutil.ignore_patterns('__pycache__', '*.pyc', 'GOAL.md',
            '*SCOPE_AMENDMENT*')(directory, names))
        for name in names:
            path = Path(directory) / name
            kind = path.lstat().st_mode
            if not (stat.S_ISREG(kind) or stat.S_ISDIR(kind)):
                skipped.add(name)
                skipped_fixture_entries.append({'path': str(path), 'mode': kind,
                    'reason': 'archived_special_fixture_or_alias_not_regular_artifact'})
        return skipped
    for relative in fixture_roots + fixture_files:
        source = (REPO / relative).resolve(strict=True)
        if not source.is_relative_to(REPO) or source.name == 'GOAL.md':
            raise ValueError('support path must stay inside the repository and exclude goal files')
        destination = snapshot / source.relative_to(REPO)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=fixture_ignore)
        else:
            shutil.copyfile(source, destination)
            if os.access(source, os.X_OK):
                destination.chmod(0o555)
    save(attempt / 'skipped_fixture_entries.json', skipped_fixture_entries)
    save(attempt / 'selected_native_executables.json', [
        str(snapshot / (REPO / relative).resolve(strict=True).relative_to(REPO))
        for relative in args.native_executable])
    for path in PACKET.glob('*.py'):
        dest = snapshot / path.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(REPO / 'pyproject.toml', snapshot / 'pyproject.toml')
    dependencies = attempt / 'dependencies'
    original = (args.dependencies_from.resolve(strict=True) if args.dependencies_from else
        REPO / '.venv/lib/python3.12/site-packages')
    shutil.copytree(original, dependencies, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    runtime = attempt / 'runtime'
    runtime.mkdir()
    # Separately selected native services do not inherit the enclosing worker's
    # PYTHONHOME. The standard bin/lib layout keeps their interpreter and stdlib
    # resolution within this same frozen closure too.
    (runtime / 'bin').mkdir()
    python = runtime / 'bin/python'
    shutil.copyfile(REPO / '.venv/bin/python', python)
    python.chmod(0o555)
    # Independent-service interpreter startup must also exclude the host user's site.
    # No alternate Python home is declared: the copied lib remains authoritative.
    venv_config = runtime / 'pyvenv.cfg'
    venv_config.write_text('include-system-site-packages = false\n')
    venv_config.chmod(0o444)
    stdlib = runtime / 'lib/python3.12'
    shutil.copytree('/usr/lib/python3.12', stdlib,
        ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    # Existing independent worker fixtures supply their own application PYTHONPATH.
    # Resolve dependencies in the frozen interpreter too, without processing
    # copied environment-specific .pth files or falling back to host packages.
    site = stdlib / 'dist-packages'
    site.mkdir()
    (site / 'frozen_dependencies.pth').write_text(str(dependencies) + '\n')
    for name, root in (('source', snapshot), ('dependency', dependencies), ('stdlib', stdlib)):
        freeze(root)
        save(attempt / (name + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python), pin(venv_config)])
    for name in ('temporary', 'cache', 'installed'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependencies))), 'PYTHONHOME': str(runtime),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'PIP_CACHE_DIR': str(attempt / 'cache/pip'),
        'HMMER511_ATTEMPT': str(attempt)}
    entry = snapshot / PACKET.relative_to(REPO) / 'bounded_entry.py'
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'mode': args.mode,
        'tests': selected_tests, 'support_files': args.support_file, 'support_trees': args.support_tree,
        'native_executables': args.native_executable,
        'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}, 'swap_bytes': 0})

sys.path[:0] = [str(attempt / 'source_snapshot'), str(attempt / 'dependencies')]
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if args.operation == 'launch':
    prepare_job(argv, cwd=attempt, policy=LocalJobPolicy(21474836480, 4294967296, None),
        handle_path=handle.path, stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'state': status(handle)['state'], 'unit': handle.read()['unit']}))
elif args.operation == 'status':
    view = status(handle)
    save(attempt / 'last_status.json', view)
    print(json.dumps({k: view[k] for k in ('state', 'terminal', 'quiescent')}))
else:
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({k: view[k] for k in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    unchanged = {}
    for name in ('source', 'dependency', 'stdlib', 'binary'):
        before = runtime_pin_rows(json.loads((attempt / (name + '_pins_before.json')).read_text()))
        after = [pin(row['path']) for row in before]
        save(attempt / (name + '_pins_after.json'), after)
        unchanged[name + '_unchanged'] = before == after
    installed = attempt / 'installed'
    if any(installed.iterdir()):
        freeze(installed)
        save(attempt / 'installed_pins.json', [pin(p) for p in sorted(installed.rglob('*')) if p.is_file()])
    receipt = {'returncode': result.returncode, 'handle': str(handle.path), 'unit': handle.read()['unit'],
        'terminal': view['terminal'], 'quiescent': view['quiescent'], **unchanged, 'metadata': result.metadata}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'metadata'}))
    raise SystemExit(result.returncode if all(unchanged.values()) else 4)
