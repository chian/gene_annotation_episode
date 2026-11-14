"""Retain scientific files from the original general command's frozen outputs.

Purpose-specific adapters retain their manifest and scientific validation. This
port changes only where already closed original bytes are obtained; it never
executes work, prepares a job or accepts a later live-path replacement.
"""
from copy import deepcopy
from pathlib import Path

from . import native_file_capture
from .terminal_scientific_evidence import captured_terminal_file, terminal_file_identity


def capture_execution_file(store, *, directory, relative_path, format, command_proof=None):
    if command_proof is None:
        return native_file_capture.capture_native_file(store, directory=directory,
            relative_path=relative_path, format=format)
    native_file_capture._path(directory, absolute=True)
    native_file_capture._path(relative_path, absolute=False)
    if directory != command_proof['original_plan']['attempt_directory']:
        raise ValueError('terminal_capture_original_directory_mismatch')
    path = str(Path(directory) / relative_path)
    snapshots = [row for row in command_proof['output_snapshots'] if row['path'] == path]
    if len(snapshots) != 1 or not snapshots[0]['available']:
        raise native_file_capture.NativeFileCaptureError('capture_file_unavailable')
    return captured_terminal_file(store, snapshots[0], format=format)


def capture_execution_declarations(store, *, directory, declarations, command_proof=None):
    if command_proof is None:
        return native_file_capture.capture_declared_native_files(store, directory=directory,
            declarations=declarations)
    native_file_capture._path(directory, absolute=True)
    if type(declarations) is not list:
        raise native_file_capture.NativeFileCaptureError('invalid_file_declaration')
    declared = [native_file_capture._declaration(value) for value in declarations]
    if len({row['relative_path'] for row in declared}) != len(declared):
        raise native_file_capture.NativeFileCaptureError('invalid_file_declaration')
    result = []
    for declaration in declared:
        row = {'declared': deepcopy(declaration), 'observed': None,
            'outcome': 'declared_absent', 'failure': None}
        if declaration['state'] == 'present':
            try:
                observed = capture_execution_file(store, directory=directory,
                    relative_path=declaration['relative_path'], format=declaration['format'],
                    command_proof=command_proof)
            except native_file_capture.NativeFileCaptureError as error:
                if error.code != 'capture_file_unavailable':
                    raise
                row.update(outcome='unavailable', failure='capture_file_unavailable')
            else:
                row['observed'] = observed
                equal = all(observed[key] == declaration[key] for key in ('sha256', 'size_bytes'))
                row['outcome'] = 'verified' if equal else 'digest_mismatch'
                row['failure'] = None if equal else 'capture_file_digest_mismatch'
        result.append(row)
    return result


def validate_execution_file(file, *, original_plan, relative_path, format, command_proof):
    """A non-null retained identity must name this exact executed version."""
    if command_proof['original_plan'] != original_plan:
        raise ValueError('terminal_capture_original_plan_mismatch')
    if file is None:
        return
    path = str(Path(original_plan['attempt_directory']) / relative_path)
    snapshots = [row for row in command_proof['output_snapshots'] if row['path'] == path]
    if (len(snapshots) != 1 or not snapshots[0]['available']
            or file != terminal_file_identity(snapshots[0], format)):
        raise ValueError('terminal_capture_executed_file_mismatch')
