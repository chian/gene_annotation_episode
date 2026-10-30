"""Explicit launch/status/collect for the two existing chromatin Workflow suites.

Only stdlib staging and the existing lifecycle bootstrap execute outside the
selected bounded handle. Source, selected installed distributions, interpreter,
stdlib and supplied native fixtures are copied and pinned before dispatch.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
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
TESTS = {'cooler': 'tests/test_native_chromatin_interaction_workflow.py',
         'hic': 'tests/test_native_hic_chromatin_workflow.py'}
# These cover pytest, the statically imported application libraries, the two
# scientific readers, and the already-installed optional jsonschema helpers.
# Optional extras are copied only when installed; no dependency is installed.
REQUIRED = ('numpy', 'h5py', 'scipy', 'biopython', 'pillow', 'pyrodigal', 'archspec',
    'jsonschema', 'attrs', 'jsonschema-specifications', 'referencing', 'rpds-py',
    'typing-extensions', 'pytest', 'iniconfig', 'packaging', 'pluggy', 'pygments')
OPTIONAL = ('idna', 'jsonpointer', 'fqdn', 'rfc3987', 'rfc3986-validator',
    'rfc3987-syntax', 'rfc3339-validator', 'webcolors', 'uri-template',
    'isoduration', 'lark', 'arrow', 'python-dateutil', 'six', 'types-python-dateutil')


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while raw := stream.read(1024 * 1024):
            digest.update(raw)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'size_bytes': path.stat().st_size}


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


def copy_relative(snapshot, relative):
    original, target = REPO / relative, snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, target)
    return {'original': pin(original), 'copied': pin(target)}


def copy_distributions(dependencies):
    # Preserve the existing451/459 import preference, then freeze that selection.
    sites = (REPO / 'reference/episode_tools/.venv/lib/python3.12/site-packages',
             REPO / '.venv/lib/python3.12/site-packages')
    available = {}
    for site in sites:
        for dist in importlib.metadata.distributions(path=[str(site)]):
            key = dist.metadata['Name'].lower().replace('_', '-')
            available.setdefault(key, (dist, site))
    destination_site = dependencies / 'lib/python3.12/site-packages'
    destination_site.mkdir(parents=True)
    copied, records = {}, []
    for name in (*REQUIRED, *(name for name in OPTIONAL if name in available)):
        dist, site = available[name]
        entries = []
        for relative in dist.files or ():
            original = Path(dist.locate_file(relative)).resolve(strict=True)
            target = (destination_site / relative).resolve()
            if not target.is_relative_to(dependencies):
                raise ValueError('installed_distribution_path_escape:' + str(relative))
            identity = pin(original)
            if str(target) in copied:
                if copied[str(target)] != (identity['sha256'], identity['size_bytes']):
                    raise ValueError('conflicting_installed_distribution_file:' + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
                target.chmod(0o555 if os.access(original, os.X_OK) else 0o444)
                copied[str(target)] = identity['sha256'], identity['size_bytes']
            entries.append({'installed': identity, 'copied': str(target)})
        records.append({'name': dist.metadata['Name'], 'version': dist.version,
            'installed_site': str(site), 'requires_dist': dist.requires or [], 'files': entries})
    return destination_site, records


parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=('launch', 'dispatch', 'status', 'collect'))
parser.add_argument('attempt')
parser.add_argument('--mode', choices=tuple(TESTS))
parser.add_argument('--dependency-snapshot', type=Path)
args = parser.parse_args()
if not args.attempt.isidentifier():
    parser.error('attempt must be a simple identifier')
attempt = PACKET / args.attempt

if args.operation == 'launch':
    if args.mode is None:
        parser.error('launch requires an explicitly selected mode')
    attempt.mkdir(exist_ok=False)
    snapshot, dependencies = attempt / 'source_snapshot', attempt / 'dependencies'
    for package in ('gene_annotation_episode', 'method_loop', 'tests'):
        shutil.copytree(REPO / package, snapshot / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    fixture_pins = []
    paths = ('pyproject.toml', 
        str(Path(__file__).relative_to(REPO)), str((PACKET / 'bounded_entry.py').relative_to(REPO)),
        'verification/tool_graders_chromatin_workflow_2026-10-27_451/fixture_helpers.py',
        'verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/fixture_helpers.py',
        'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json',
        
        'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/four-bin-raw-weighted.cool',
        'verification/tool_graders_chromatin_hic_native_2026-10-27_454/native009/valid/output.hic',
        'verification/tool_graders_chromatin_hic_native_2026-10-27_454/native010/present_zero_block/output.hic')
    for relative in paths:
        fixture_pins.append(copy_relative(snapshot, relative))
    publication = Path('research/slotted_process_library/publications/2026-10-24-001')
    shutil.copytree(REPO / publication, snapshot / publication)
    if args.dependency_snapshot is None:
        dependency_site, distribution_records = copy_distributions(dependencies)
    else:
        previous = args.dependency_snapshot.resolve(strict=True)
        if previous.parent != PACKET or not (previous / 'dependency_pins_before.json').is_file():
            raise ValueError('owned_complete_dependency_snapshot_required')
        before = runtime_pin_rows(json.loads((previous / 'dependency_pins_before.json').read_text()))
        if any(pin(row['path']) != row or Path(row['path']).stat().st_mode & 0o222 for row in before):
            raise ValueError('immutable_dependency_snapshot_changed')
        shutil.copytree(previous / 'dependencies', dependencies, copy_function=os.link)
        dependency_site = dependencies / 'lib/python3.12/site-packages'
        distribution_records = json.loads((previous / 'distribution_selection.json').read_text())
        for distribution in distribution_records:
            for row in distribution['files']:
                row['copied'] = str(dependencies / Path(row['copied']).relative_to(previous / 'dependencies'))
        save(attempt / 'dependency_snapshot_reuse.json', {'source': str(previous),
            'mechanism': 'immutable_file_hardlinks_into_distinct_attempt_tree',
            'original_before_manifest': pin(previous / 'dependency_pins_before.json')})
    save(attempt / 'distribution_selection.json', distribution_records)
    save(attempt / 'fixture_and_helper_copies.json', fixture_pins)
    runtime = attempt / 'runtime'
    runtime.mkdir()
    python = runtime / 'python'
    shutil.copyfile(REPO / '.venv/bin/python', python)
    python.chmod(0o555)
    base = Path((REPO / '.venv/pyvenv.cfg').read_text().split('home = ', 1)[1].splitlines()[0]).parent
    standard_library = runtime / 'lib/python3.12'
    shutil.copytree(base / 'lib/python3.12', standard_library,
        ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    for label, root in (('source', snapshot), ('dependency', dependencies), ('standard_library', standard_library)):
        immutable_tree(root)
        save(attempt / (label + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python)])
    save(attempt / 'bootstrap_identity.json', {'interpreter': pin(Path('/proc/self/exe').resolve()),
        'scope': 'stdlib staging and existing local_jobs/native_lifecycle dispatch/status/collect only'})
    for name in ('temporary', 'cache'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependency_site))),
        'PYTHONHOME': str(runtime), 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'),
        'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
        'PIP_CACHE_DIR': str(attempt / 'cache/pip'),
        'WORKFLOW451_ATTEMPT': str(attempt), 'WORKFLOW459_ATTEMPT': str(attempt)}
    entry = snapshot / (PACKET / 'bounded_entry.py').relative_to(REPO)
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'cwd': str(attempt),
        'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None},
        'swap_bytes': 0, 'tests': [TESTS[args.mode]],
        'dependency_scope': 'copied explicit application/test/reader closure with installed schema helpers',
        'native_library_scope': 'copied bundled extension libraries; bounded before/after pins for resolved system runtime closure'})

if args.operation == 'dispatch':
    # Recover only a fully staged, never-dispatched reservation. An existing
    # handle is always followed through status/collect, never relaunched here.
    if (attempt / 'handle.json').exists():
        raise ValueError('existing_handle_must_not_be_redispatched')
    selected = json.loads((attempt / 'selected_request.json').read_text())
    argv, env = selected['argv'], selected['environment']
    save(attempt / 'administrative_dispatch_identity.json', {
        'runner': pin(__file__), 'interpreter': pin(Path('/proc/self/exe').resolve()),
        'reason': 'explicit_dispatch_of_complete_snapshot_after_pre_dispatch_bootstrap_fix'})

sys.path[:0] = [str(attempt / 'source_snapshot'),
    str(attempt / 'dependencies/lib/python3.12/site-packages')]
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if args.operation in ('launch', 'dispatch'):
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    view = status(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': view['state']}))
elif args.operation == 'status':
    view = status(handle)
    save(attempt / 'last_status.json', view)
    print(json.dumps({'handle': str(handle.path), 'state': view['state'], 'terminal': view['terminal'],
        'quiescent': view['quiescent']}))
else:
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({'state': view['state'], 'terminal': view['terminal'], 'quiescent': view['quiescent']}))
        raise SystemExit(3)
    result = collect(handle)
    unchanged = {}
    for label in ('source', 'dependency', 'binary', 'standard_library'):
        before = runtime_pin_rows(json.loads((attempt / (label + '_pins_before.json')).read_text()))
        after = [pin(row['path']) for row in before]
        save(attempt / (label + '_pins_after.json'), after)
        unchanged[label + '_pins_unchanged'] = before == after
    audit = attempt / 'execution_audit.json'
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'],
        'metadata': result.metadata, **unchanged, 'handle': str(handle.path), 'unit': handle.read()['unit'],
        'execution_audit': json.loads(audit.read_text()) if audit.exists() else None}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('metadata', 'execution_audit')}))
    raise SystemExit(result.returncode if all(unchanged.values()) else 4)
