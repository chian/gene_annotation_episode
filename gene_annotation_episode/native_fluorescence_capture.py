"""Stream original fluorescence outputs into Store custody after writer closure.

This does not grant episode authority or load scientific event arrays. The
result owner authenticates the selected action and writer-closure references.
"""
from pathlib import Path

from .fluorescence_execution_common import digest, require, unique, validate_failure
from .native_fluorescence_contracts import validate_fluorescence_native_capture, validate_fluorescence_run_plan
from .native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file


def capture_fluorescence_native_files(store, *, original_plan, source_action_receipt_ref,
        writer_closure_receipt_ref, driver_started, command_proof=None):
    plan = validate_fluorescence_run_plan(original_plan)
    # Validate the complete control request before accessing any producer file.
    capture = {'version': 'fluorescence_native_capture_v1', 'original_plan_sha256': digest(plan),
        'files': [{**row, 'retained': None} for row in plan['outputs']],
        'source_action_receipt_ref': source_action_receipt_ref, 'writer_closure_receipt_ref': writer_closure_receipt_ref,
        'driver_started': driver_started, 'failures': []}
    validate_fluorescence_native_capture(capture, original_plan=plan)
    snapshots = ({row['path']: row for row in command_proof['output_snapshots']}
        if command_proof is not None else None)
    for row in capture['files']:
        try:
            if snapshots is None:
                file = capture_native_file(store, directory=plan['attempt_directory'],
                    relative_path=row['relative_path'], format=row['format'])
            else:
                from .terminal_scientific_evidence import captured_terminal_file
                snapshot = snapshots.get(str(Path(plan['attempt_directory']) / row['relative_path']))
                if snapshot is None or not snapshot.get('available'):
                    raise NativeFileCaptureError('capture_file_unavailable')
                file = captured_terminal_file(store, snapshot, format=row['format'])
            row['retained'] = {'file': file, 'path': str(retained_native_file(store, file))}
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
            index = int(row['role'].split(':')[1]) if ':' in row['role'] else None
            capture['failures'].append(validate_failure({'code': 'capture_file_unavailable', 'stage': 'capture',
                'input_index': index, 'role': row['role']}))
    capture['failures'] = unique(capture['failures'])
    return validate_fluorescence_native_capture(capture, original_plan=plan)


def validate_terminal_fluorescence_files(capture, *, original_plan, command_proof):
    """Match retained results to the original completed command's file version."""
    from .terminal_scientific_evidence import terminal_file_identity
    plan = validate_fluorescence_run_plan(original_plan)
    require(command_proof['original_plan'] == plan, 'fluorescence_terminal_capture_plan_mismatch')
    snapshots = {row['path']: row for row in command_proof['output_snapshots']}
    for row in capture['files']:
        snapshot = snapshots.get(str(Path(plan['attempt_directory']) / row['relative_path']))
        expected = (terminal_file_identity(snapshot, row['format'])
            if snapshot is not None and snapshot.get('available') else None)
        actual = row['retained']['file'] if row['retained'] is not None else None
        require(actual == expected, 'fluorescence_terminal_capture_file_mismatch')
