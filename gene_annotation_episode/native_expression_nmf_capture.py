"""Stream the five original NMF artifact files into existing Store custody.

Only the results owner qualifies selected launch authority and writer closure.
Manifest parsing and matrix relationships belong to the finite result worker.
"""
from copy import deepcopy
from pathlib import Path

from .expression_nmf_common import digest, unique_issues
from .expression_nmf_result_contracts import failure, require, validate_file, validate_issue
from .native_expression_nmf_contracts import ARTIFACT_FORMATS, ARTIFACT_NAMES, validate_expression_nmf_run_plan
from .native_file_capture import NativeFileCaptureError, capture_native_file, retained_native_file


from .expression_nmf_result_contracts import validate_expression_nmf_native_capture


def capture_expression_nmf_native_files(store, *, original_plan, source_action_receipt_ref,
        writer_closure_receipt_ref, driver_started):
    plan = validate_expression_nmf_run_plan(original_plan)
    rows, failures = [], []
    for specification in plan['outputs']:
        row = {**specification, 'retained': None}
        try:
            file = capture_native_file(store, directory=plan['attempt_directory'],
                relative_path=row['relative_path'], format=row['format'])
            row['retained'] = {'file': file, 'path': str(retained_native_file(store, file))}
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
            # Missing factors can be a declared failed native result. The
            # worker reads that distinction from the actual retained manifest.
            if row['role'] != 'factors':
                failures.append(failure('capture_file_unavailable', 'capture', field=row['role']))
        rows.append(row)
    return validate_expression_nmf_native_capture(dict(version='expression_nmf_native_capture_v1',
        original_plan_sha256=digest(plan), files=rows, source_action_receipt_ref=source_action_receipt_ref,
        writer_closure_receipt_ref=writer_closure_receipt_ref, driver_started=driver_started,
        failures=unique_issues(failures)), original_plan=plan)
