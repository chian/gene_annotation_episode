"""One finite retained-NMF read/calculation, without fitting or acquisition.

The caller runs this module within the existing local native boundary. All
matrix decoding, joins, sheet validation and arithmetic occur in this worker.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys

from .expression_nmf_common import CALCULATION_SCHEMA, SHEET_SCHEMA, canonical, digest, unique_issues
from .expression_nmf_artifacts import load_expression_nmf_artifacts
from .expression_nmf_calculations import calculate_nmf_sheet
from .expression_nmf_result_contracts import (checked, failure, require, validate_file,
    validate_issue, validate_projection, validate_expression_nmf_result_selector)
from .expression_nmf_result_views import project_nmf_result
from .expression_nmf_sheet import populate_nmf_sheet, validate_nmf_sheet
from .native_expression_nmf_contracts import ARTIFACT_NAMES, POLICY, expression_nmf_environment, validate_expression_nmf_run_plan
from .native_expression_nmf_storage import directory, file_pin, immutable_bytes, immutable_json, read_json, regular

PLAN_VERSION = 'expression_nmf_worker_plan_v1'
RESULT_VERSION = 'expression_nmf_worker_result_v1'
OUTPUTS = (('sheet', 'sheet.json', SHEET_SCHEMA), ('calculations', 'calculations.json', CALCULATION_SCHEMA),
    ('projection', 'projection.json', 'expression_nmf_result_view_v1'),
    ('diagnostics', 'diagnostics.json', 'expression_nmf_result_diagnostics_v1'))


def validate_expression_nmf_worker_plan(value):
    canonical(value)
    require(type(value) is dict and value.get('version') == PLAN_VERSION and value.get('mode') in
        ('native_result', 'saved_sheet_recalculation'), 'invalid_nmf_worker_plan')
    expected = {'version', 'mode', 'directory', 'selector'} | ({'original_plan', 'capture'} if value['mode'] == 'native_result' else {'sheet'})
    require(set(value) == expected and Path(value['directory']).is_absolute()
        and str(Path(value['directory'])) == value['directory'] and '..' not in Path(value['directory']).parts,
        'invalid_nmf_worker_plan')
    selector = validate_expression_nmf_result_selector(value['selector'])
    require(selector['mode'] == value['mode'], 'nmf_worker_mode_mismatch')
    if value['mode'] == 'native_result':
        from .expression_nmf_result_contracts import validate_expression_nmf_native_capture
        plan = validate_expression_nmf_run_plan(value['original_plan'])
        validate_expression_nmf_native_capture(value['capture'], original_plan=plan)
    else:
        require(type(value['sheet']) is dict and set(value['sheet']) == {'file', 'path'}, 'invalid_nmf_saved_operand')
        require(validate_file(value['sheet']['file'], saved=True) == selector['saved_sheet_file']
            and Path(value['sheet']['path']).is_absolute(), 'nmf_saved_operand_mismatch')
    return deepcopy(value)


def validate_expression_nmf_worker_result(value):
    canonical(value)
    require(type(value) is dict and set(value) == {'version', 'mode', 'plan_sha256', 'selector', 'outputs',
        'failures', 'input_identity', 'native_binding', 'native_outcome', 'original_fit_acquired', 'analysis_complete'},
        'invalid_nmf_worker_result')
    require(value['version'] == RESULT_VERSION and value['mode'] in ('native_result', 'saved_sheet_recalculation')
        and type(value['plan_sha256']) is str and len(value['plan_sha256']) == 64, 'invalid_nmf_worker_result')
    validate_expression_nmf_result_selector(value['selector'])
    require(value['selector']['mode'] == value['mode'] and type(value['native_binding']) is bool
        and type(value['original_fit_acquired']) is bool and type(value['analysis_complete']) is bool,
        'invalid_nmf_worker_result')
    require(value['native_outcome'] in ('complete', 'qualified', 'partial', 'failed', 'rejected_input', None), 'invalid_nmf_worker_result')
    require(not value['original_fit_acquired'] or value['mode'] == 'native_result' and value['native_binding'], 'invalid_nmf_worker_acquisition')
    require(not value['analysis_complete'] or value['native_outcome'] in ('complete', 'qualified') and not value['failures'],
        'invalid_nmf_worker_completion')
    if value['input_identity'] is not None:
        require(type(value['input_identity']) is dict and set(value['input_identity']) == {'sha256', 'size_bytes'}, 'invalid_nmf_worker_input_identity')
        validate_file({**value['input_identity'], 'artifact_ref': 'artifact_' + value['input_identity']['sha256'], 'format': 'expression_delimited_bytes_v1'})
    require(type(value['outputs']) is list and len(value['outputs']) == len(OUTPUTS), 'invalid_nmf_worker_outputs')
    for row, (role, name, format_) in zip(value['outputs'], OUTPUTS):
        require(type(row) is dict and set(row) == {'role', 'declaration'} and row['role'] == role, 'invalid_nmf_worker_outputs')
        d = row['declaration']
        require(type(d) is dict and set(d) == {'relative_path', 'format', 'state', 'sha256', 'size_bytes'}
            and d['relative_path'] == name and d['format'] == format_ and d['state'] in ('present', 'absent'), 'invalid_nmf_worker_outputs')
        if d['state'] == 'present':
            validate_file({k: v for k, v in {'artifact_ref': 'artifact_' + str(d['sha256']), **d}.items() if k not in ('relative_path', 'state')})
        else:
            require(d['sha256'] is None and d['size_bytes'] is None, 'invalid_nmf_worker_outputs')
    for row in value['failures']:
        validate_issue(row)
    return deepcopy(value)


def _read_operand(retained):
    pin = file_pin(retained['path'])
    require(all(pin[k] == retained['file'][k] for k in ('sha256', 'size_bytes')), 'nmf_worker_operand_changed')
    return read_json(retained['path'])


def _native(plan, root):
    original, capture = plan['original_plan'], plan['capture']
    job = original['requested_job']['native_expression_nmf']
    incoming = directory(root / 'native-inputs')
    incoming.mkdir(exist_ok=True)
    failures = deepcopy(capture['failures'])
    for row in capture['files']:
        retained = row['retained']
        if retained is None:
            continue
        try:
            pin = file_pin(retained['path'])
            require(all(pin[k] == retained['file'][k] for k in ('sha256', 'size_bytes')), 'nmf_worker_operand_changed')
            target = incoming / ARTIFACT_NAMES[row['role']]
            if target.exists():
                require({k: file_pin(target)[k] for k in ('sha256', 'size_bytes')} ==
                    {k: pin[k] for k in ('sha256', 'size_bytes')}, 'nmf_worker_operand_changed')
            else:
                with regular(retained['path']) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                target.chmod(0o444)
            require(all(file_pin(target)[k] == retained['file'][k] for k in ('sha256', 'size_bytes')), 'nmf_worker_operand_changed')
        except (OSError, ValueError):
            failures.append(failure('worker_input_unavailable', 'worker', field=row['role']))
    loaded = load_expression_nmf_artifacts(incoming / ARTIFACT_NAMES['manifest'],
        expected_input_identity={k: job['input'][k] for k in ('sha256', 'size_bytes')})
    failures = unique_issues(failures, loaded['failures'])
    manifest, bound = loaded['manifest'], True
    expected_environment = expression_nmf_environment(job['software'], attempt_directory=original['attempt_directory'])
    expected_environment.update({k: str(Path(original['identity']['execution_id']).parent) for k in ('TMPDIR', 'TMP', 'TEMP')})
    expected_execution = {'identity': original['identity'], 'software_sha256': digest(job['software']),
        'requested_job_sha256': digest(original['requested_job']), 'realized_environment': expected_environment}
    if (manifest is None or manifest.get('execution') != expected_execution or capture['driver_started'] is not True
            or manifest.get('input_identity') != {k: job['input'][k] for k in ('sha256', 'size_bytes')}):
        failures.append(failure('original_execution_mismatch', 'authority', field='manifest'))
        bound = False
    native, inp = loaded['native_result'], loaded['input_data']
    if native.get('parameters') != job['parameters']:
        failures.append(failure('original_parameters_mismatch', 'authority', field='parameters'))
        bound = False
    if (inp.get('input_identity') != {k: job['input'][k] for k in ('sha256', 'size_bytes')}
            or inp.get('delimiter') != job['input']['delimiter'] or inp.get('metadata') != job['input']['metadata']):
        failures.append(failure('original_input_metadata_mismatch', 'authority', field='input_data'))
        bound = False
    source = native.get('source', {})
    versions = {r['name'].lower().replace('_', '-'): r['version'] for r in job['software']['distributions']}
    actual = source.get('versions', {})
    if native.get('outcome') in ('complete', 'qualified') and (source.get('kind') != 'sklearn_fit'
            or any(actual.get(name) != versions[name] for name in ('scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl'))
            or actual.get('python') != job['software']['python_version']):
        failures.append(failure('native_software_mismatch', 'authority', field='source'))
        bound = False
    native['failures'] = unique_issues(native.get('failures', []), failures)
    sheet = populate_nmf_sheet(input_data=inp, prepared_data=loaded['prepared_data'], native_result=native)
    return sheet, bound


def execute_expression_nmf_worker(plan):
    plan = validate_expression_nmf_worker_plan(plan)
    root = directory(plan['directory'])
    root.mkdir(parents=True, exist_ok=True)
    failures, sheet, calculations, projection, bound = [], None, None, None, False
    try:
        if plan['mode'] == 'native_result':
            sheet, bound = _native(plan, root)
        else:
            sheet = validate_nmf_sheet(_read_operand(plan['sheet']))
            # Historical episode authority is authenticated by the host. The
            # worker validates only this exact received sheet's internal joins.
        calculations = calculate_nmf_sheet(sheet)
        failures.extend(calculations['failures'])
        if plan['mode'] != 'native_result' or bound:
            try:
                projection = project_nmf_result(sheet, calculations, selector=plan['selector']['projection'])
            except (ValueError, KeyError, TypeError, IndexError):
                failures.append(failure('projection_selection_invalid', 'projection', field='selector'))
            if projection is not None:
                try:
                    validate_projection(projection)
                except ValueError:
                    projection = None
                    failures.append(failure('projection_contract_invalid', 'projection', field='projection'))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        failures.append(failure('saved_sheet_incompatible' if plan['mode'] == 'saved_sheet_recalculation'
            else 'worker_output_malformed', 'worker', field='sheet'))
    failures = unique_issues(failures)
    diagnostics = {'schema': 'expression_nmf_result_diagnostics_v1', 'plan_sha256': digest(plan), 'failures': failures}
    values = (sheet, calculations, projection, diagnostics)
    outputs = []
    for (role, name, format_), value in zip(OUTPUTS, values):
        pin = {'sha256': None, 'size_bytes': None}
        if value is not None:
            immutable_json(root / name, value)
            pin = {k: file_pin(root / name)[k] for k in ('sha256', 'size_bytes')}
        outputs.append({'role': role, 'declaration': {'relative_path': name, 'format': format_,
            'state': 'absent' if value is None else 'present', **pin}})
    acquired = bool(plan['mode'] == 'native_result' and bound and sheet is not None
        and sheet['calculation_eligible'] and sheet['native_diagnostics'].get('fit_call_count') == 1)
    complete = bool(sheet is not None and sheet['calculation_eligible'] and sheet['outcome'] in ('complete', 'qualified')
        and projection is not None and not failures and (plan['mode'] != 'native_result' or bound))
    result = validate_expression_nmf_worker_result({'version': RESULT_VERSION, 'mode': plan['mode'],
        'plan_sha256': digest(plan), 'selector': plan['selector'], 'outputs': outputs, 'failures': failures,
        'input_identity': None if sheet is None else sheet['input_identity'], 'native_binding': bound,
        'native_outcome': None if sheet is None else sheet['outcome'], 'original_fit_acquired': acquired,
        'analysis_complete': complete})
    immutable_json(root / 'worker-result.json', result)
    return result


def main():
    require(len(sys.argv) == 2, 'one_nmf_worker_plan_required')
    execute_expression_nmf_worker(read_json(Path(sys.argv[1]).absolute()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
