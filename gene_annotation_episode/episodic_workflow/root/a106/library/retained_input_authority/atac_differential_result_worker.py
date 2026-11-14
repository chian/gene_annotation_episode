"""One finite retained-data ATAC operation with exhaustive stream finalization.

Native byte acquisition is an earlier host operation. Saved calculations read
only the supplied sheet and numerical tables. No BAM, service or MACS2 call is
made by this worker. Emitted prefixes survive failure without a fabricated EOF.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.atac_differential_result_contracts import SHEET_FORMAT, TABLE_FORMAT, ROLES, require, validate_atac_result_record
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_atac_differential_contracts import path_value, validate_atac_run_plan
FIXED_OUTPUTS = (('sheet', 'sheet.json', SHEET_FORMAT), ('calculations', 'calculations.json', 'atac_differential_calculations_v1'), ('projection', 'projection.json', 'atac_differential_projection_v1'), ('diagnostics', 'diagnostics.json', 'atac_differential_diagnostics_v1'))
DERIVED_FORMATS = {'partitions': 'atac_interval_partitions_jsonl_v1', 'components': 'atac_interval_components_jsonl_v1', 'regions': 'atac_differential_regions_jsonl_v1'}

def worker_output_specs(plan):
    """Every selected occurrence, including absent raw/derived output roles."""
    specs = [dict(role=role, table_key=None, relative_path=name, format=fmt) for role, name, fmt in FIXED_OUTPUTS]
    if plan['mode'] == 'native_result':
        keys = dict(zip(ROLES, ROLES))
    else:
        keys = {str(i): row['track_key'] for i, row in enumerate(plan['sheet_bundle']['tables'])}
    specs.extend((dict(role='track_table', table_key=key, relative_path='tracks/' + role + '.jsonl', format=TABLE_FORMAT) for role, key in keys.items()))
    specs.extend((dict(role=role, table_key=role, relative_path=role + '.jsonl', format=fmt) for role, fmt in DERIVED_FORMATS.items()))
    return specs

def validate_atac_result_worker_plan(value):
    value = validate_atac_result_record('WorkerPlan', value)
    selector = validate_atac_result_record('ResultSelector', value['selector'])
    directory = path_value(value['directory'], absolute=True)
    require(selector['mode'] == value['mode'], 'atac_worker_mode_mismatch')
    if value['mode'] == 'native_result':
        original = validate_atac_run_plan(value['original_plan'])
        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_atac_differential_capture import validate_atac_native_capture
        validate_atac_native_capture(dict(version='atac_native_capture_v1', **{key: value[key] for key in ('bundle', 'files', 'source_action_receipt_ref', 'writer_closure_receipt_ref', 'driver_state', 'failures')}), original_plan=original)
        request = original['requested_job']['native_atac_differential']['request']
        require(request['comparison_key'] == selector['comparison_key'], 'atac_result_comparison_conflict')
        require([r['specification'] for r in value['files']] == original['outputs'], 'atac_worker_manifest_mismatch')
        retained = ([value['bundle']] if value['bundle'] else []) + [r['retained'] for r in value['files'] if r['retained']]
        for row in value['files']:
            spec, declared, actual = (row['specification'], row['declared'], row['retained'])
            if declared is not None:
                require(all((declared[k] == spec[k] for k in ('relative_path', 'format'))), 'atac_worker_manifest_mismatch')
            if actual is not None:
                require(actual['file']['format'] == spec['format'], 'atac_worker_manifest_mismatch')
            if row['outcome'] == 'verified':
                require(declared is not None and declared['state'] == 'present' and (actual is not None) and all((declared[k] == actual['file'][k] for k in ('sha256', 'size_bytes', 'format'))), 'atac_worker_capture_mismatch')
            elif row['outcome'] == 'declared_absent':
                require(declared is not None and declared['state'] == 'absent' and (actual is None), 'atac_worker_capture_mismatch')
    else:
        saved = value['sheet_bundle']
        public = dict(sheet=saved['sheet']['file'], tables=[dict(track_key=r['track_key'], file=r['file']) for r in saved['tables']])
        require(selector['saved_sheet_bundle'] == public, 'atac_worker_saved_bundle_mismatch')
        validate_atac_result_record('SavedSheetBundle', public)
        retained = [saved['sheet'], *saved['tables']]
    paths = {}
    for record in retained:
        validate_atac_result_record('NativeFileIdentity', record['file'])
        path = path_value(record['path'], absolute=True)
        require(path != directory and directory not in path.parents and (path not in directory.parents), 'atac_worker_input_output_overlap')
        content = {k: record['file'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')}
        require(path not in paths or paths[path] == content, 'atac_worker_path_identity_conflict')
        paths[path] = content
    return value

def validate_atac_result_worker_result(value):
    value = validate_atac_result_record('WorkerResult', value)
    validate_atac_result_record('Parameters', value['parameters'])
    require(value['parameters']['maximum_gap_bp'] < value['parameters']['minimum_length_bp'], 'atac_worker_parameters_mismatch')
    for output, expected in zip(value['outputs'][:4], FIXED_OUTPUTS):
        role, name, fmt = expected
        require(output['role'] == role and output['table_key'] is None and (output['declaration']['relative_path'] == name) and (output['declaration']['format'] == fmt), 'atac_worker_outputs_mismatch')
    require(len(value['outputs']) >= 7, 'atac_worker_outputs_mismatch')
    require([r['role'] for r in value['outputs'][-3:]] == list(DERIVED_FORMATS), 'atac_worker_outputs_mismatch')
    for row in value['outputs'][-3:]:
        key = row['role']
        require(row['table_key'] == key and row['declaration']['relative_path'] == key + '.jsonl' and (row['declaration']['format'] == DERIVED_FORMATS[key]), 'atac_worker_outputs_mismatch')
    raw = value['outputs'][4:-3]
    require(all((r['role'] == 'track_table' and r['table_key'] is not None and (r['declaration']['format'] == TABLE_FORMAT) for r in raw)), 'atac_worker_outputs_mismatch')
    require(len({r['table_key'] for r in raw}) == len(raw), 'atac_worker_outputs_mismatch')
    paths = []
    for row in value['outputs']:
        declaration = row['declaration']
        paths.append(str(path_value(declaration['relative_path'], absolute=False)))
        require((declaration['sha256'] is not None and declaration['size_bytes'] is not None) == (declaration['state'] == 'present'), 'atac_worker_declaration_mismatch')
    require(len(set(paths)) == len(paths) and value['outputs'][3]['declaration']['state'] == 'present', 'atac_worker_outputs_mismatch')
    return value
