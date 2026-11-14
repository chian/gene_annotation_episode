"""One remote original FBA driver and its existing finite numerical readers.

The enclosing authenticated HPC request owns transport. This adapter creates no
local-backend receipts and grants only the explicitly selected output data.
"""
from copy import deepcopy
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .execution_contracts import canonical, digest
from .flux_balance_contracts import validate_flux_balance_record
from .flux_balance_result_worker import _native, _record_failure
from .flux_balance_calculations import calculate_flux_balance_sheet
from .flux_balance_result_views import project_fba_result
from .flux_balance_result_contracts import validate_fba_projection
from .native_flux_balance_contracts import (ATTEMPT_DIRECTORY_NAME, POLICY,
    SOURCE_FUNCTION_SHA256, RUN_PLAN_FILENAME, DRIVER_MODULE, OWNER_FILENAME,
    STARTED_FILENAME, ENVIRONMENT_FILENAME, flux_balance_environment,
    flux_balance_output_files, flux_balance_driver_argv, validate_flux_balance_run_plan)


VERSION = 'a110_flux_balance_hpc_v2'


def require(condition, code):
    if not condition:
        raise ValueError('a110_remote_fba_'+code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def retained(raw, format_, root):
    identity = sha(raw)
    path = root/'artifacts'/identity[:2]/identity
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, 'retained_bytes_conflict')
    else:
        path.write_bytes(raw)
    return {'file': {'artifact_ref': 'artifact_'+identity, 'sha256': identity,
        'size_bytes': len(raw), 'format': format_}, 'path': str(path)}


def calculate(request, unit):
    selected, binding = request['selection'], request['binding']
    science, software = selected['request'], binding['software']
    assets, resolved = {}, {}
    for identity, asset in request['assets'].items():
        raw = base64.b64decode(asset['bytes_base64'], validate=True)
        require(sha(raw) == identity == asset['file']['sha256']
            and len(raw) == asset['file']['size_bytes'], 'original_input_bytes_conflict')
        path = unit/'inputs'/identity
        if path.exists():
            require(path.read_bytes() == raw, 'original_input_path_conflict')
        else:
            path.write_bytes(raw)
        assets[identity] = {'file': asset['file'], 'path': str(path)}
    for row in request['resolved_files']:
        require(row['file']['sha256'] in assets, 'original_file_selection_missing')
        resolved[canonical(row['selection'])] = assets[row['file']['sha256']]
    def file_for(selection):
        require(canonical(selection) in resolved, 'unreceived_file_selection')
        return resolved[canonical(selection)]['file']
    def bound(value):
        source = value.get('source')
        return validate_flux_balance_record('Bound', {'kind': value['kind'], 'value': value['value'],
            'native_token': value.get('native_token'), 'float_hex': value.get('float_hex'),
            'source': None if source is None else {'file': file_for(source['file']), 'pointer': source['pointer']}})
    original_model = science['model_input']
    model = resolved[canonical(original_model['file'])]
    lifecycle = unit/'.episode-operations'/digest({'run': request['run_id'], 'episode': request['episode_id']})/digest(request['operation_key'])
    lifecycle.mkdir(parents=True, exist_ok=True)
    attempt = lifecycle/ATTEMPT_DIRECTORY_NAME
    job = {'version': 'native_flux_balance_job_v1', 'operation': science['operation'], 'mode': science['mode'],
        'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
        'model_input': {'file': {'path': model['path'], **{key: model['file'][key] for key in ('sha256', 'size_bytes')}},
            'artifact_ref': model['file']['artifact_ref'], 'format': model['file']['format'],
            'original_loader_selection': original_model['original_loader_selection'],
            'repository_identifier': original_model['repository_identifier'],
            'acquisition_receipt_file': None if original_model['acquisition_receipt_file'] is None
                else file_for(original_model['acquisition_receipt_file'])},
        'constraints': None if science['constraints'] is None else [{'reaction_id': row['reaction_id'],
            'lower': bound(row['lower']), 'upper': bound(row['upper'])} for row in science['constraints']],
        'objective': deepcopy(science['objective']), 'solver_options': deepcopy(science['solver_options']),
        'software': software, 'output_prefix': 'fba-output', 'flux_output_name': 'fluxes.csv',
        'source_function_sha256': SOURCE_FUNCTION_SHA256}
    environment = flux_balance_environment(software, attempt_directory=str(attempt), lifecycle_directory=str(lifecycle))
    requested_job = {'argv': [software['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME],
        'environment': environment, 'native_flux_balance': job}
    identity = {'run_id': request['run_id'], 'episode_id': request['episode_id'],
        'resource_id': request['resource_id'], 'execution_id': str(lifecycle/'native.json'),
        'attempt_id': digest(request['operation_key']), 'operation_key': request['operation_key'],
        'requested_job_sha256': digest(requested_job), 'assignment_sha256': digest(request)}
    plan = validate_flux_balance_run_plan({'version': 'flux_balance_run_plan_v1', 'identity': identity,
        'requested_job': requested_job, 'attempt_directory': str(attempt), 'policy': POLICY,
        'outputs': flux_balance_output_files(job)})
    plan_path = lifecycle/RUN_PLAN_FILENAME
    raw_plan = (canonical(plan)+'\n').encode()
    if plan_path.exists():
        require(plan_path.read_bytes() == raw_plan, 'original_plan_conflict')
    else:
        plan_path.write_bytes(raw_plan)
    # The original driver runs in its pinned interpreter/import closure. The
    # wrapper's validator imports cannot contaminate the driver's software audit.
    with (unit/'fba-driver.stdout').open('wb') as stdout, (unit/'fba-driver.stderr').open('wb') as stderr:
        outcome = subprocess.run(flux_balance_driver_argv(plan), cwd=lifecycle,
            env={**os.environ, **environment}, stdout=stdout, stderr=stderr, check=False)
    evidence_root = unit/'native-evidence'
    files = []
    for declaration in plan['outputs']:
        path = attempt/declaration['relative_path']
        files.append({**declaration, 'retained': retained(path.read_bytes(), declaration['format'], evidence_root)
            if path.is_file() else None})
    controls = {}
    for role, name, format_ in (('owner', OWNER_FILENAME, 'flux_balance_owner_plan_v1'),
            ('started', STARTED_FILENAME, 'flux_balance_started_control_v1'),
            ('environment', ENVIRONMENT_FILENAME, 'flux_balance_environment_observation_v1')):
        path = attempt/name
        controls[role] = retained(path.read_bytes(), format_, evidence_root) if path.is_file() else None
    prior_files = {canonical(row['file']): row for row in resolved.values()
        if row['file']['sha256'] != model['file']['sha256']}
    prior_sources = [retained(Path(row['path']).read_bytes(), row['file']['format'], evidence_root)
        for row in prior_files.values()]
    # The existing native reader checks owner/start/environment/manifest and
    # selected-request associations. The outer HPC receipt supplies transport
    # authority; no private ordinary/local action or writer receipt is forged.
    capture = {'files': files, 'controls': controls, 'prior_sources': prior_sources,
        'failures': [], 'driver_started': (attempt/STARTED_FILENAME).is_file()}
    issues = []
    sheet, calculations, projection, association, evidence = None, None, None, 'unavailable', []
    try:
        sheet, association, evidence = _native({'original_plan': plan, 'capture': capture}, issues)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError, RecursionError) as error:
        issues.append(_record_failure(error, '/sheet', stage='parse'))
    if sheet is not None:
        try:
            calculations = calculate_flux_balance_sheet(sheet, parameters=selected['calculation_parameters'])
        except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
            issues.append(_record_failure(error, '/selection/calculation_parameters', stage='parse'))
    if calculations is not None:
        try:
            projection = validate_fba_projection(project_fba_result(sheet, calculations, selector=selected['projection']))
        except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
            issues.append(_record_failure(error, '/selection/projection', stage='project'))
    saved = []
    for value, format_ in ((sheet, 'flux_balance_sheet_v1'), (calculations, 'flux_balance_calculations_v1')):
        if value is not None:
            saved.append(retained(canonical(value).encode(), format_, evidence_root))
    native = None if sheet is None else sheet['native']
    execution_state = None if native is None else {key: deepcopy(native[key])
        for key in ('execution_outcome', 'objective_application', 'solve_call_count')}
    observed_solver = None if native is None else {key: deepcopy(native['solver'][key])
        for key in ('interface', 'name', 'version', 'cobra_version', 'optlang_version')}
    return {'version': VERSION, 'selection': deepcopy(selected), 'dataset_id': original_model['repository_identifier'],
        'origin': 'computational_model', 'projection': projection,
        'native_execution_state': execution_state,
        'requested_projection_status': 'available' if projection is not None else 'unavailable',
        'native_association': association, 'native_evidence_roles': evidence,
        'driver_returncode': outcome.returncode, 'diagnostics': issues,
        'original_attempt': identity, 'original_plan_sha256': digest(plan),
        'software': {'selected_manifest_sha256': sha(json.dumps(software,
                sort_keys=True, separators=(',', ':'), allow_nan=False).encode()),
            'declared_solver_interface': software['solver_interface'], 'declared_python_version': software['python_version'],
            'declared_distributions': deepcopy(software['distributions']), 'observed_solver_versions': observed_solver,
            'full_manifest_retention': 'original_frozen_request; reference_does_not_grant_other_numerical_cells'},
        'native_file_identities': [{key: row[key] for key in ('role', 'relative_path', 'format')}
            | {'identity': None if row['retained'] is None else row['retained']['file']} for row in files],
        'remote_saved_outputs': [{key: row['file'][key] for key in ('sha256', 'size_bytes', 'format')}
            | {'local_numerical_receipt_granted': False} for row in saved],
        'limitations': ['Only the selected projection is numerically admitted by this component source.',
            'Remote files remain upstream artifacts; their paths/digests grant no other worksheet cells.',
            'A steady-state linear FBA solution is neither chemical/thermodynamic proof nor molecular activity.',
            'Annotation-to-reaction mappings, constraints, objective and environmental assumptions remain explicit.'],
        'combined_scientific_score': None}
