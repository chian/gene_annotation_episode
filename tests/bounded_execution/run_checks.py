"""Repository checks using the existing bounded verification lifecycle.

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
import time

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
RUNS = REPO / 'runs'
LEGACY_PACKET = REPO / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'


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


def authenticated_attempt(directory):
    """Authenticate a collected run before reusing its immutable application closure."""
    directory = Path(directory).resolve(strict=True)
    if not directory.is_relative_to(RUNS.resolve()) or not directory.is_dir():
        raise ValueError('retained_attempt_must_stay_under_runs')
    receipt_path, audit_path = directory / 'receipt.json', directory / 'execution_audit.json'
    receipt, audit = json.loads(receipt_path.read_bytes()), json.loads(audit_path.read_bytes())
    original_outer = json.loads((directory / 'handle.json').read_bytes())
    flags = ('source_unchanged', 'dependency_unchanged', 'stdlib_unchanged',
             'binary_unchanged', 'selected_stdlib_source_unchanged')
    if (receipt.get('terminal') is not True or receipt.get('quiescent') is not True
            or any(receipt.get(key) is not True for key in flags)
            or audit.get('outside_modules') != [] or audit.get('unbound_mappings') != []
            or audit.get('native_unchanged') is not True
            or audit.get('original_retained_fixtures_unchanged') is not True
            or type(receipt.get('returncode')) is not int
            or audit.get('pytest_returncode') != receipt['returncode']
            or receipt.get('handle') != str(directory / 'handle.json')
            or receipt.get('unit') != original_outer.get('unit')):
        raise ValueError('retained_attempt_not_authenticated')
    groups = ('source', 'dependency', 'stdlib', 'binary', 'selected_stdlib_source', 'native_library')
    files = []
    for group in groups:
        record = directory / ('selected_stdlib_source_pins.json' if group == 'selected_stdlib_source'
                              else group + '_pins_before.json')
        rows = json.loads(record.read_bytes())
        if (type(rows) is not list or any(type(row) is not dict
                or set(row) != {'path', 'sha256', 'size_bytes'}
                or type(row['path']) is not str or not Path(row['path']).is_absolute()
                or type(row['sha256']) is not str or len(row['sha256']) != 64
                or any(symbol not in '0123456789abcdef' for symbol in row['sha256'])
                or type(row['size_bytes']) is not int or row['size_bytes'] < 0 for row in rows)
                or len({row['path'] for row in rows}) != len(rows)):
            raise ValueError('retained_attempt_pin_record_invalid')
        if any(pin(row['path']) != row for row in rows):
            raise ValueError('retained_attempt_original_bytes_changed')
        if group == 'source':
            expected = {str(p) for p in (directory / 'source_snapshot').rglob('*') if p.is_file()}
            if {row['path'] for row in rows} != expected:
                raise ValueError('retained_attempt_source_inventory_conflict')
        files.append(pin(record))
    return {'attempt': str(directory), 'receipt': pin(receipt_path),
            'execution_audit': pin(audit_path), 'validated_pin_records': files,
            'recorded_returncode': receipt['returncode']}


def selected_native_handle(attempt, filename, unit, request_sha256):
    """Select an existing durable handle without preparing or replacing its request."""
    path = Path(filename).resolve(strict=True)
    if not path.is_relative_to(attempt) or path == attempt / 'handle.json':
        raise ValueError('native_recovery_requires_existing_inner_handle')
    body = json.loads(path.read_bytes())
    policy = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    if (body.get('version') != 'durable_systemd_native_job_v2' or body.get('unit') != unit
            or body.get('request_sha256') != request_sha256
            or body.get('metadata', {}).get('policy') != policy
            or body.get('stage') not in {'prepared', 'submitting', 'released'}):
        raise ValueError('native_recovery_handle_selection_conflict')
    cwd = Path(body['cwd']).resolve(strict=True)
    if (not cwd.is_relative_to(attempt) or not path.is_relative_to(cwd)
            or any(not Path(value).resolve().is_relative_to(cwd)
                   for value in [body['stdout'], body['stderr'], *body['paths'].values()])):
        raise ValueError('native_recovery_control_path_conflict')
    request_path = Path(body['paths']['request'])
    raw = request_path.read_bytes()
    request = json.loads(raw)
    if (type(request) is not dict or set(request) != {'command', 'cwd', 'file_bytes',
            'ready_path', 'release_path', 'result_path', 'stdin_path', 'env'}
            or hashlib.sha256(raw).hexdigest() != request_sha256
            or request.get('command') != body['command'] or request.get('cwd') != str(cwd)
            or request.get('file_bytes') != policy['scratch_bytes']
            or request.get('ready_path') != body['paths']['ready']
            or request.get('release_path') != body['paths']['release']
            or request.get('result_path') != body['paths']['result']):
        raise ValueError('native_recovery_original_request_conflict')
    return path, body, pin(request_path)


parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=('launch', 'status', 'collect',
    'native-resume', 'native-status', 'native-collect'))
parser.add_argument('attempt')
parser.add_argument('--attempt-parent', type=Path)
parser.add_argument('--working-root', type=Path)
parser.add_argument('--mode', choices=('check',), default='check')
parser.add_argument('--dependencies-from', type=Path)
parser.add_argument('--python-executable', type=Path)
parser.add_argument('--stdlib-from', type=Path)
parser.add_argument('--test', action='append', required=False)
parser.add_argument('--support-file', action='append', default=[])
parser.add_argument('--support-tree', action='append', default=[])
parser.add_argument('--no-default-fixtures', action='store_true')
parser.add_argument('--native-executable', action='append', default=[])
parser.add_argument('--existing-native-executable', action='append', default=[])
parser.add_argument('--native-library', action='append', default=[])
parser.add_argument('--test-env', action='append', default=[])
parser.add_argument('--application-source-from', type=Path)
parser.add_argument('--native-handle', type=Path)
parser.add_argument('--native-unit')
parser.add_argument('--native-request-sha256')
parser.add_argument('--recovery-output', type=Path)
args = parser.parse_args()
if sys.version_info[:2] != (3, 12):
    parser.error('verification_runner_requires_python312_bootstrap')
if not args.attempt.isidentifier():
    parser.error('simple attempt name required')
if args.operation == 'launch':
    RUNS.mkdir(exist_ok=True)
attempt_parent = RUNS if args.attempt_parent is None else args.attempt_parent
attempt_parent = attempt_parent.resolve(strict=True)
allowed_roots = (RUNS.resolve(),) if args.operation == 'launch' else (
    RUNS.resolve(), LEGACY_PACKET.resolve())
if not attempt_parent.is_dir() or not any(attempt_parent.is_relative_to(root) for root in allowed_roots):
    parser.error('new runs must stay under runs; existing legacy handles may be observed in place')
attempt = attempt_parent / args.attempt
working_root = attempt if args.working_root is None else args.working_root.resolve(strict=True)
if not any(working_root.is_relative_to(root) for root in allowed_roots) or not attempt.is_relative_to(working_root):
    parser.error('working root must contain the attempt and stay within the selected run area')
native_recovery = args.operation.startswith('native-')
if native_recovery:
    if (args.application_source_from is not None or args.native_handle is None
            or args.native_unit is None or args.native_request_sha256 is None
            or args.recovery_output is None or args.attempt_parent is not None
            or args.working_root is not None):
        parser.error('native recovery requires exact original handle/unit/request and fresh recovery output')
    recovery = args.recovery_output.resolve()
    if (not recovery.is_relative_to(RUNS.resolve()) or recovery.is_relative_to(attempt)
            or attempt.is_relative_to(recovery)):
        parser.error('native recovery output must be separate from the original attempt')
    authentication = authenticated_attempt(attempt)
    selected_handle, original_native, original_request = selected_native_handle(
        attempt, args.native_handle, args.native_unit, args.native_request_sha256)
    recovery.mkdir(parents=True, exist_ok=True)
    recovery_proof = recovery / (args.operation + '-' + str(time.time_ns()) + '.json')
    recovery_body = {'version': 'bounded_native_phase_recovery_v1',
        'operation': args.operation, 'phase': 'authenticated_before_lifecycle',
        'original_attempt': authentication, 'native_handle_before': pin(selected_handle),
        'original_native_handle': original_native, 'original_request': original_request,
        'outer_runner_created': False,
        'resume_may_start_original_prepared_unit': args.operation == 'native-resume'}
    save(recovery_proof, recovery_body)
elif any(value is not None for value in (args.native_handle, args.native_unit,
        args.native_request_sha256, args.recovery_output)):
    parser.error('native recovery arguments require a native lifecycle operation')
elif args.application_source_from is not None and args.operation != 'launch':
    parser.error('application source selection is only valid during launch')
if args.operation == 'launch':
    if args.mode is None:
        parser.error('explicit mode required')
    selected_stdlib = Path('/usr/lib/python3.12') if args.stdlib_from is None else args.stdlib_from
    if not selected_stdlib.is_absolute() or not selected_stdlib.is_dir():
        parser.error('selected_python312_stdlib_unavailable')
    selected_stdlib = selected_stdlib.resolve(strict=True)
    if not (selected_stdlib / 'encodings/__init__.py').is_file():
        parser.error('selected_python312_stdlib_invalid')
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    application_root = REPO
    if args.application_source_from is not None:
        application_root = args.application_source_from.resolve(strict=True)
        if application_root.name != 'source_snapshot':
            parser.error('application source must name an actual retained source_snapshot')
        application_origin = authenticated_attempt(application_root.parent)
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(application_root / package, snapshot / package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if args.application_source_from is not None:
        original_rows = json.loads((application_root.parent / 'source_pins_before.json').read_bytes())
        copied_rows = []
        for row in original_rows:
            relative = Path(row['path']).relative_to(application_root)
            if relative.parts[0] not in {'gene_annotation_episode', 'method_loop'}:
                continue
            copied = pin(snapshot / relative)
            if any(copied[key] != row[key] for key in ('sha256', 'size_bytes')):
                raise ValueError('retained_application_copy_changed')
            copied_rows.append({'original_path': row['path'], **copied})
        if {row['path'] for row in copied_rows} != {str(p)
                for package in ('gene_annotation_episode', 'method_loop')
                for p in (snapshot / package).rglob('*') if p.is_file()}:
            raise ValueError('retained_application_copy_inventory_conflict')
        application_origin['copied_application_files'] = copied_rows
        save(attempt / 'application_source_origin.json', application_origin)
    selected_tests = args.test
    if not selected_tests:
        parser.error('launch requires at least one explicit --test')
    save(attempt / 'selected_tests.json', selected_tests)
    shutil.copytree(REPO / 'tests', snapshot / 'tests', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    fixture_roots, fixture_files = [], []
    if not args.no_default_fixtures:
        fixture_roots.extend([
            'research/slotted_process_library/publications/2026-10-24-001',
            'verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259',
            'verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check005/temporary',
            'verification/tool_graders_hmmer_preparation_capture_2026-10-26_270/check005/temporary',
            'verification/tool_graders_hmmer_preparation_grading_2026-10-26_271/modes001',
            'verification/tool_graders_hmmer_preparation_results_2026-10-26_273/check003/temporary',
        ])
        fixture_files.append(
            'verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check005_native_cases.json')
    fixture_roots.extend(args.support_tree)
    fixture_files.extend([*args.support_file, *args.native_executable])
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
    selected_executables = [
        str(snapshot / (REPO / relative).resolve(strict=True).relative_to(REPO))
        for relative in args.native_executable]
    existing_executables = []
    for supplied in args.existing_native_executable:
        path = Path(supplied)
        if not path.is_absolute():
            raise ValueError('existing_native_executable_must_be_absolute')
        path = path.resolve(strict=True)
        if not path.is_relative_to(REPO) or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError('existing_native_executable_must_be_an_executable_repository_file')
        if str(path) in selected_executables:
            raise ValueError('duplicate_selected_native_executable')
        selected_executables.append(str(path))
        existing_executables.append(pin(path))
    save(attempt / 'selected_native_executables.json', selected_executables)
    save(attempt / 'selected_existing_native_executables.json', existing_executables)
    # Some runtime dependencies, such as NSS DNS providers, are loaded by
    # dlopen rather than ELF dependencies. Bind them before the bounded run;
    # discovery after a test must not retroactively authorize a new mapping.
    selected_libraries = []
    for supplied in args.native_library:
        path = Path(supplied)
        if not path.is_absolute() or not path.is_file():
            raise ValueError('selected_native_library_must_be_an_absolute_file')
        row = pin(path.resolve(strict=True))
        if row['path'] in {item['path'] for item in selected_libraries}:
            raise ValueError('duplicate_selected_native_library')
        selected_libraries.append(row)
    save(attempt / 'selected_native_libraries.json', selected_libraries)
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
    selected_python = REPO / '.venv/bin/python'
    if args.python_executable is not None:
        if not args.python_executable.is_absolute():
            parser.error('selected_python_executable_must_be_absolute')
        selected_python = args.python_executable
    selected_python = selected_python.resolve(strict=True)
    if not selected_python.is_file() or not os.access(selected_python, os.X_OK):
        parser.error('selected_python_executable_unavailable')
    selected_python_pin = pin(selected_python)
    shutil.copyfile(selected_python, python)
    python.chmod(0o555)
    if {k: pin(python)[k] for k in ('sha256', 'size_bytes')} != {k: selected_python_pin[k] for k in ('sha256', 'size_bytes')}:
        raise ValueError('selected_python_copy_changed')
    # Independent-service interpreter startup must also exclude the host user's site.
    # No alternate Python home is declared: the copied lib remains authoritative.
    venv_config = runtime / 'pyvenv.cfg'
    venv_config.write_text('include-system-site-packages = false\n')
    venv_config.chmod(0o444)
    stdlib = runtime / 'lib/python3.12'
    stdlib_source_pins = [pin(p) for p in sorted(selected_stdlib.rglob('*'))
        if p.is_file() and not any(part in {'site-packages', 'dist-packages', '__pycache__'}
            for part in p.relative_to(selected_stdlib).parts) and p.suffix != '.pyc']
    save(attempt / 'selected_stdlib_source_pins.json', stdlib_source_pins)
    shutil.copytree(selected_stdlib, stdlib,
        ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    for original_pin in stdlib_source_pins:
        copied = stdlib / Path(original_pin['path']).relative_to(selected_stdlib)
        observed = pin(copied)
        if any(observed[key] != original_pin[key] for key in ('sha256', 'size_bytes')):
            raise ValueError('selected_stdlib_copy_changed')
    # Existing independent worker fixtures supply their own application PYTHONPATH.
    # Resolve dependencies in the frozen interpreter too, without processing
    # copied environment-specific .pth files or falling back to host packages.
    # A retained stdlib source is already frozen; copytree preserves its root
    # mode. Permit only this new copy's dependency-directory addition, then the
    # ordinary freeze below closes it again. The selected source stays untouched.
    stdlib.chmod(0o755)
    site = stdlib / 'dist-packages'
    site.mkdir()
    (site / 'frozen_dependencies.pth').write_text(str(dependencies) + '\n')
    for name, root in (('source', snapshot), ('dependency', dependencies), ('stdlib', stdlib)):
        freeze(root)
        save(attempt / (name + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python), pin(venv_config)])
    for name in ('temporary', 'tmp', 'cache', 'installed'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependencies))), 'PYTHONHOME': str(runtime),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'PIP_CACHE_DIR': str(attempt / 'cache/pip'),
        'HMMER529_ATTEMPT': str(attempt)}
    selected_test_environment = {}
    for setting in args.test_env:
        key, separator, value = setting.partition('=')
        if (not separator or not (key.startswith('HMMER_NATIVE_ORACLE_')
                or key in {'ORDINARY_PROTEIN_RETAINED_STORE',
                    'ORDINARY_TF_BINDING_GENUINE', 'ORDINARY_TF_BINDING_ATTEMPT_ID',
                    'ORDINARY_TF_BINDING_RETAINED_STORE', 'ORDINARY_TF_BINDING_RETAINED_PROOF',
                    'ORDINARY_TF_BINDING_RETAINED_PROOF_SHA256',
                    'ORDINARY_TF_BINDING_RETAINED_SQLITE_PINS_SHA256'})
                or key in env or key in selected_test_environment):
            raise ValueError('invalid_or_duplicate_test_environment')
        selected_test_environment[key] = value.replace('{snapshot}', str(snapshot)).replace('{attempt}', str(attempt))
    env.update(selected_test_environment)
    save(attempt / 'selected_test_environment.json', selected_test_environment)
    entry = snapshot / PACKET.relative_to(REPO) / 'bounded_entry.py'
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'mode': args.mode,
        'repository_root': str(REPO), 'working_root': str(working_root),
        'tests': selected_tests, 'support_files': args.support_file, 'support_trees': args.support_tree,
        'default_hmmer_fixtures': not args.no_default_fixtures,
        'native_executables': args.native_executable,
        'existing_native_executables': existing_executables,
        'selected_python_source_pin': selected_python_pin,
        'selected_stdlib_source': str(selected_stdlib),
        'selected_stdlib_source_pin_file': pin(attempt / 'selected_stdlib_source_pins.json'),
        'native_libraries': selected_libraries,
        **({'application_source_origin': application_origin} if args.application_source_from is not None else {}),
        'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}, 'swap_bytes': 0})

sys.path[:0] = [str(attempt / 'source_snapshot'), str(attempt / 'dependencies')]
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if native_recovery:
    try:
        outer = status(handle)
        recovery_body.update(original_outer_observation=outer)
        save(recovery_proof, recovery_body)
        if not outer['terminal'] or not outer['quiescent']:
            raise ValueError('native_recovery_requires_quiescent_original_outer')
        native_handle = NativeJobHandle(selected_handle)
        if args.operation == 'native-resume':
            # The original unit may now start for the first time. Its own shared
            # admission and cgroup remain authoritative; no outer job is made.
            resume_start(native_handle)
        view = status(native_handle)
        recovery_body.update(phase='original_native_observed', native_observation=view,
            native_handle_after=pin(selected_handle))
        if args.operation == 'native-collect':
            if not view['terminal'] or not view['quiescent']:
                save(recovery_proof, recovery_body)
                print(json.dumps({'proof': str(recovery_proof), 'state': view['state'],
                    'terminal': view['terminal'], 'quiescent': view['quiescent']}))
                raise SystemExit(3)
            result = collect(native_handle)
            recovery_body.update(phase='original_native_collected', returncode=result.returncode,
                collected_metadata=result.metadata)
        if pin(original_request['path']) != original_request:
            raise ValueError('native_recovery_original_request_changed')
        save(recovery_proof, recovery_body)
        print(json.dumps({'proof': str(recovery_proof), 'unit': original_native['unit'],
            'state': view['state'], 'terminal': view['terminal'], 'quiescent': view['quiescent'],
            **({'returncode': result.returncode} if args.operation == 'native-collect' else {})}))
        if args.operation == 'native-collect':
            raise SystemExit(result.returncode)
    except Exception as error:
        recovery_body.update(phase='lifecycle_failure_retained', failure={
            'exception_type': type(error).__name__, 'code': getattr(error, 'code', str(error)),
            'operational': getattr(error, 'operational', None)})
        save(recovery_proof, recovery_body)
        raise
elif args.operation == 'launch':
    prepare_job(argv, cwd=working_root, policy=LocalJobPolicy(21474836480, 4294967296, None),
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
    selected_stdlib_pins = attempt / 'selected_stdlib_source_pins.json'
    if selected_stdlib_pins.exists():
        before = json.loads(selected_stdlib_pins.read_text())
        after = [pin(row['path']) for row in before]
        save(attempt / 'selected_stdlib_source_pins_after.json', after)
        unchanged['selected_stdlib_source_unchanged'] = before == after
    installed = attempt / 'installed'
    if any(installed.iterdir()):
        freeze(installed)
        save(attempt / 'installed_pins.json', [pin(p) for p in sorted(installed.rglob('*')) if p.is_file()])
    receipt = {'returncode': result.returncode, 'handle': str(handle.path), 'unit': handle.read()['unit'],
        'terminal': view['terminal'], 'quiescent': view['quiescent'], **unchanged, 'metadata': result.metadata}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'metadata'}))
    raise SystemExit(result.returncode if all(unchanged.values()) else 4)
