"""Finite retained-table calculation; no native reacquisition or execution.

The host supplies original controls and captured regular files. This worker
uses C1 read-only arrays and C2 calculations in one context, then declares
closed bytes. File production does not grant result authority or completion.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.chromatin_interaction_contracts import validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_chromatin_interaction_contracts import TABLE_ROLES, require, path_value, validate_chromatin_run_plan
OUTPUTS = (('sheet', 'sheet.json', 'chromatin_interaction_sheet_v1'), ('components', 'components.json', 'chromatin_interaction_components_v1'), ('projection', 'projection.json', 'chromatin_interaction_projection_v1'), ('diagnostics', 'diagnostics.json', 'chromatin_interaction_result_diagnostics_v1'))

def validate_chromatin_result_worker_plan(value):
    value = validate_chromatin_record('WorkerPlan', value)
    directory = path_value(value['directory'], absolute=True)
    selector = value['selector']
    require(selector['mode'] == value['mode'])
    retained = []
    if value['mode'] == 'native_result':
        original = validate_chromatin_run_plan(value['original_plan'])
        request = original['requested_job']['native_chromatin_interactions']['request']
        require(set(selector['population_keys']) <= {p['population_key'] for p in request['populations']})
        require(selector['saved_sheet_bundle'] is None)
        require([r['specification'] for r in value['files']] == original['outputs'][:-1])
        if value['bundle'] is not None:
            require(value['driver_state'] == 'sealed_bundle' and value['bundle']['file']['format'] == 'chromatin_interaction_native_bundle_v1')
            retained.append(value['bundle'])
        for row in value['files']:
            spec, capture = (row['specification'], row['capture'])
            if row['declaration_source'] == 'none':
                require(capture is None)
            else:
                require(capture is not None and all((capture['declared'][k] == spec[k] for k in ('relative_path', 'format'))))
                require(row['declaration_source'] != 'bundle' or value['driver_state'] == 'sealed_bundle')
                require(row['declaration_source'] != 'population' or spec['role'] in TABLE_ROLES)
            if row['retained'] is not None:
                require(row['retained']['file']['format'] == spec['format'])
                require(capture is None or row['retained']['file'] == capture['observed'])
                retained.append(row['retained'])
            if capture is not None:
                _validate_capture(capture)
        if value['driver_state'] == 'not_started':
            require(value['bundle'] is None and all((r['retained'] is None and r['capture'] is None for r in value['files'])))
    else:
        bundle = value['sheet_bundle']
        require(bundle['sheet']['file']['format'] == 'chromatin_interaction_sheet_v1')
        require(selector['saved_sheet_bundle'] == {'sheet': bundle['sheet']['file'], 'tables': [r['file'] for r in bundle['tables']]})
        retained = [bundle['sheet'], *bundle['tables']]
    paths = {}
    for row in retained:
        path = path_value(row['path'], absolute=True)
        require(path != directory and directory not in path.parents and (path not in directory.parents))
        content = {k: row['file'][k] for k in ('artifact_ref', 'sha256', 'size_bytes')}
        require(path not in paths or paths[path] == content)
        paths[path] = content
    return value

def _validate_capture(value):
    declaration, actual = (value['declared'], value['observed'])
    equal = actual is not None and all((actual[k] == declaration[k] for k in ('sha256', 'size_bytes', 'format')))
    require(value['outcome'] == 'verified' and declaration['state'] == 'present' and equal and (value['failure'] is None) or (value['outcome'] == 'declared_absent' and declaration['state'] == 'absent' and (actual is None) and (value['failure'] is None)) or (value['outcome'] == 'unavailable' and declaration['state'] == 'present' and (actual is None) and (value['failure'] == 'capture_file_unavailable')) or (value['outcome'] == 'digest_mismatch' and declaration['state'] == 'present' and (actual is not None) and (not equal) and (value['failure'] == 'capture_file_digest_mismatch')))

def validate_chromatin_result_worker_result(value):
    value = validate_chromatin_record('WorkerResult', value)
    fixed = value['outputs'][:4]
    require(len(fixed) == 4)
    for row, (role, name, format) in zip(fixed, OUTPUTS):
        require(row['role'] == role and row['table_key'] is None and (row['declaration']['relative_path'] == name) and (row['declaration']['format'] == format))
    tables = value['outputs'][4:]
    require(all((r['role'] == 'table' and r['table_key'] is not None for r in tables)))
    require(len({r['table_key'] for r in tables}) == len(tables))
    paths = [str(path_value(r['declaration']['relative_path'], absolute=False)) for r in value['outputs']]
    require(len(paths) == len(set(paths)))
    present = [r['declaration']['state'] == 'present' for r in fixed]
    require(present[3] and (not present[1] or present[0]) and (not present[2] or all(present[:2])))
    require(value['source_sheet_sha256'] == (fixed[0]['declaration']['sha256'] if present[0] else None))
    require(value['state'] == ('produced' if all(present[:3]) else 'partial' if any(present[:3]) else 'unavailable'))
    return value
