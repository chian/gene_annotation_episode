"""Explicit launch/status/collect of one pinned finite AppService custody check.

The only host application imports bootstrap the existing native lifecycle.
Application/test imports execute inside that handle's bounded process.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
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
parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=('launch', 'status', 'collect'))
parser.add_argument('attempt')
parser.add_argument('tests', nargs='*')
args = parser.parse_args()
if not args.attempt.isidentifier():
    parser.error('attempt must be a simple identifier')
attempt = PACKET / args.attempt


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'size_bytes': path.stat().st_size}


def save(path, value):
    if Path(path).name == 'receipt.json' and _SKIPPED_NOTE_PROVENANCE:
        value = {**value, 'skipped_note_provenance': list(_SKIPPED_NOTE_PROVENANCE),
                 'pin_validation_scope': 'scientific_and_runtime_inputs_excluding_reported_note_provenance'}
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def immutable_tree(root):
    for path in root.rglob('*'):
        if path.is_file():
            path.chmod(0o555 if os.access(path, os.X_OK) else 0o444)
    for path in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


if args.operation == 'launch':
    attempt.mkdir(exist_ok=False)
    snapshot, dependencies = attempt / 'source_snapshot', attempt / 'dependencies'
    for package in ('gene_annotation_episode', 'method_loop', 'tests'):
        shutil.copytree(REPO / package, snapshot / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    selected = args.tests or ['tests/test_bvbrc_appservice_custody.py', 'tests/test_bvbrc_appservice_compact_custody.py']
    for name in selected:
        if name.split('::', 1)[0] not in {'tests/test_bvbrc_appservice_custody.py', 'tests/test_bvbrc_appservice_compact_custody.py', 'tests/test_bvbrc_appservice_host.py', 'tests/test_bvbrc_appservice_inputs.py', 'tests/test_bvbrc_appservice_native_monitor.py', 'tests/test_bvbrc_appservice_monitor_workflow.py'} or not (snapshot / name.split('::', 1)[0]).is_file():
            raise ValueError('explicit_owned_test_file_required:' + name)
    for filename in ('pyproject.toml', str(Path(__file__).relative_to(REPO))):
        target = snapshot / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / filename, target)
    # The complete installed site closure is copied and pinned. -S plus the
    # exact PYTHONPATH prevents mutable host packages or plugin discovery.
    shutil.copytree(REPO / '.venv/lib/python3.12/site-packages', dependencies,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    runtime = attempt / 'runtime'
    runtime.mkdir()
    python = runtime / 'python'
    shutil.copyfile(REPO / '.venv/bin/python', python)
    python.chmod(0o555)
    base = Path((REPO / '.venv/pyvenv.cfg').read_text().split('home = ', 1)[1].splitlines()[0]).parent
    standard_library = runtime / 'lib/python3.12'
    shutil.copytree(base / 'lib/python3.12', standard_library,
                    ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    immutable_tree(snapshot)
    immutable_tree(dependencies)
    immutable_tree(standard_library)
    for name in ('temporary', 'cache'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependencies))),
           'PYTHONHOME': str(runtime), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'),
           'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
           'PIP_CACHE_DIR': str(attempt / 'cache/pip'), 'BVBRC479_ATTEMPT': str(attempt)}
    argv = [str(python), '-B', '-S', '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
            '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
            '--junitxml=' + str(attempt / 'junit.xml'), *[str(snapshot / name) for name in selected]]
    for label, root in (('source', snapshot), ('dependency', dependencies), ('standard_library', standard_library)):
        save(attempt / (label + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python)])
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'cwd': str(attempt),
        'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None},
        'swap_bytes': 0, 'tests': selected, 'dependency_scope': 'complete_installed_site_packages_and_standard_library'})

sys.path.insert(0, str(attempt / 'source_snapshot'))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if args.operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
                stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    view = status(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': view['state']}))
elif args.operation == 'status':
    view = status(handle)
    save(attempt / 'last_status.json', view)
    print(json.dumps({'handle': str(handle.path), 'state': view['state'],
                      'terminal': view['terminal'], 'quiescent': view['quiescent']}))
else:
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({'state': view['state'], 'terminal': view['terminal'], 'quiescent': view['quiescent']}))
        raise SystemExit(3)
    result = collect(handle)
    unchanged = {}
    labels = ['source', 'dependency', 'binary']
    if (attempt / 'standard_library_pins_before.json').exists():
        labels.append('standard_library')
    for label in labels:
        before = runtime_pin_rows(json.loads((attempt / (label + '_pins_before.json')).read_text()))
        after = [pin(row['path']) for row in before]
        save(attempt / (label + '_pins_after.json'), after)
        unchanged[label + '_pins_unchanged'] = before == after
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'],
               'metadata': result.metadata, **unchanged, 'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'metadata'}))
    raise SystemExit(result.returncode)
