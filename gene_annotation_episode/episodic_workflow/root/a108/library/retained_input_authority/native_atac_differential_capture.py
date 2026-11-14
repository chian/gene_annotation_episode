"""Byte custody of every original ATAC output occurrence after writer closure.

The caller authenticates the original selected action and terminal/quiescent
writer. This function does not poll, launch, calculate, or confer return access.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority import native_file_capture as capture
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_atac_differential_contracts import STEP_KEYS, path_value, require, validate_atac_record, validate_atac_run_plan

def validate_atac_native_capture(value, *, original_plan):
    plan = validate_atac_run_plan(original_plan)
    value = validate_atac_record('NativeCapture', value)
    require([r['specification'] for r in value['files']] == plan['outputs'], 'invalid_atac_native_capture')
    paths = {}
    for row in value['files']:
        spec, declaration, retained = (row['specification'], row['declared'], row['retained'])
        if declaration is not None:
            capture._declaration(declaration)
            require(all((declaration[k] == spec[k] for k in ('relative_path', 'format'))), 'invalid_atac_native_capture')
        if retained is not None:
            identity = capture._identity(retained['file'])
            require(identity['format'] == spec['format'], 'invalid_atac_native_capture')
            path = path_value(retained['path'], absolute=True)
            require(path.name == identity['sha256'] and path.parent.name == identity['sha256'][:2] and (path.parent.parent.name == 'artifacts'), 'invalid_atac_native_capture')
            content = tuple((identity[k] for k in ('artifact_ref', 'sha256', 'size_bytes')))
            require(path not in paths or paths[path] == content, 'invalid_atac_native_capture')
            paths[path] = content
        equal = declaration is not None and retained is not None and all((declaration[k] == retained['file'][k] for k in ('sha256', 'size_bytes', 'format')))
        outcome = row['outcome']
        require(outcome == 'verified' and declaration is not None and (declaration['state'] == 'present') and equal or (outcome == 'declared_absent' and declaration is not None and (declaration['state'] == 'absent') and (retained is None)) or (outcome == 'unavailable' and retained is None and (declaration is None or declaration['state'] == 'present')) or (outcome == 'digest_mismatch' and declaration is not None and (declaration['state'] == 'present') and (retained is not None) and (not equal)) or (outcome == 'unsealed' and declaration is None and (retained is not None)), 'invalid_atac_native_capture')
        require(row['supplied_extent'] != 'complete' or outcome == 'verified', 'invalid_atac_native_capture')
        require(outcome != 'unsealed' or row['supplied_extent'] in ('partial', 'unknown'), 'invalid_atac_native_capture')
    bundle_row = value['files'][-1]
    require(value['bundle'] is None or (value['bundle'] == bundle_row['retained'] and bundle_row['outcome'] == 'verified'), 'invalid_atac_native_capture')
    require(value['driver_state'] not in ('succeeded', 'failed') or value['bundle'] is not None, 'invalid_atac_native_capture')
    if value['driver_state'] == 'not_run':
        require(value['bundle'] is None and all((r['retained'] is None for r in value['files'])), 'invalid_atac_native_capture')
    keys = {r['file_key'] for r in plan['outputs']}
    for problem in value['failures']:
        require(problem['file_key'] is None or problem['file_key'] in keys, 'invalid_atac_native_capture')
        require(problem['step_key'] is None or problem['step_key'] in STEP_KEYS, 'invalid_atac_native_capture')
    return value
