"""One finite retained-NMF read/calculation, without fitting or acquisition.

The caller runs this module within the existing local native boundary. All
matrix decoding, joins, sheet validation and arithmetic occur in this worker.
"""
from copy import deepcopy
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.expression_nmf_common import CALCULATION_SCHEMA, SHEET_SCHEMA, canonical
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.expression_nmf_result_contracts import require, validate_file, validate_issue, validate_expression_nmf_result_selector
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_expression_nmf_contracts import validate_expression_nmf_run_plan
PLAN_VERSION = 'expression_nmf_worker_plan_v1'
RESULT_VERSION = 'expression_nmf_worker_result_v1'
OUTPUTS = (('sheet', 'sheet.json', SHEET_SCHEMA), ('calculations', 'calculations.json', CALCULATION_SCHEMA), ('projection', 'projection.json', 'expression_nmf_result_view_v1'), ('diagnostics', 'diagnostics.json', 'expression_nmf_result_diagnostics_v1'))

def validate_expression_nmf_worker_plan(value):
    canonical(value)
    require(type(value) is dict and value.get('version') == PLAN_VERSION and (value.get('mode') in ('native_result', 'saved_sheet_recalculation')), 'invalid_nmf_worker_plan')
    expected = {'version', 'mode', 'directory', 'selector'} | ({'original_plan', 'capture'} if value['mode'] == 'native_result' else {'sheet'})
    require(set(value) == expected and Path(value['directory']).is_absolute() and (str(Path(value['directory'])) == value['directory']) and ('..' not in Path(value['directory']).parts), 'invalid_nmf_worker_plan')
    selector = validate_expression_nmf_result_selector(value['selector'])
    require(selector['mode'] == value['mode'], 'nmf_worker_mode_mismatch')
    if value['mode'] == 'native_result':
        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.expression_nmf_result_contracts import validate_expression_nmf_native_capture
        plan = validate_expression_nmf_run_plan(value['original_plan'])
        validate_expression_nmf_native_capture(value['capture'], original_plan=plan)
    else:
        require(type(value['sheet']) is dict and set(value['sheet']) == {'file', 'path'}, 'invalid_nmf_saved_operand')
        require(validate_file(value['sheet']['file'], saved=True) == selector['saved_sheet_file'] and Path(value['sheet']['path']).is_absolute(), 'nmf_saved_operand_mismatch')
    return deepcopy(value)

def validate_expression_nmf_worker_result(value):
    canonical(value)
    require(type(value) is dict and set(value) == {'version', 'mode', 'plan_sha256', 'selector', 'outputs', 'failures', 'input_identity', 'native_binding', 'native_outcome', 'original_fit_acquired', 'analysis_complete'}, 'invalid_nmf_worker_result')
    require(value['version'] == RESULT_VERSION and value['mode'] in ('native_result', 'saved_sheet_recalculation') and (type(value['plan_sha256']) is str) and (len(value['plan_sha256']) == 64), 'invalid_nmf_worker_result')
    validate_expression_nmf_result_selector(value['selector'])
    require(value['selector']['mode'] == value['mode'] and type(value['native_binding']) is bool and (type(value['original_fit_acquired']) is bool) and (type(value['analysis_complete']) is bool), 'invalid_nmf_worker_result')
    require(value['native_outcome'] in ('complete', 'qualified', 'partial', 'failed', 'rejected_input', None), 'invalid_nmf_worker_result')
    require(not value['original_fit_acquired'] or (value['mode'] == 'native_result' and value['native_binding']), 'invalid_nmf_worker_acquisition')
    require(not value['analysis_complete'] or (value['native_outcome'] in ('complete', 'qualified') and (not value['failures'])), 'invalid_nmf_worker_completion')
    if value['input_identity'] is not None:
        require(type(value['input_identity']) is dict and set(value['input_identity']) == {'sha256', 'size_bytes'}, 'invalid_nmf_worker_input_identity')
        validate_file({**value['input_identity'], 'artifact_ref': 'artifact_' + value['input_identity']['sha256'], 'format': 'expression_delimited_bytes_v1'})
    require(type(value['outputs']) is list and len(value['outputs']) == len(OUTPUTS), 'invalid_nmf_worker_outputs')
    for row, (role, name, format_) in zip(value['outputs'], OUTPUTS):
        require(type(row) is dict and set(row) == {'role', 'declaration'} and (row['role'] == role), 'invalid_nmf_worker_outputs')
        d = row['declaration']
        require(type(d) is dict and set(d) == {'relative_path', 'format', 'state', 'sha256', 'size_bytes'} and (d['relative_path'] == name) and (d['format'] == format_) and (d['state'] in ('present', 'absent')), 'invalid_nmf_worker_outputs')
        if d['state'] == 'present':
            validate_file({k: v for k, v in {'artifact_ref': 'artifact_' + str(d['sha256']), **d}.items() if k not in ('relative_path', 'state')})
        else:
            require(d['sha256'] is None and d['size_bytes'] is None, 'invalid_nmf_worker_outputs')
    for row in value['failures']:
        validate_issue(row)
    return deepcopy(value)
