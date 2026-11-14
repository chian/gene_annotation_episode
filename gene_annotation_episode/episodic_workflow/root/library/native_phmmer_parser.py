"""Original cancellable parser execution and retained outcome handling."""
import json
import os
from pathlib import Path
import sys
from gene_annotation_episode._local_job_worker import atomic_json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.native_lifecycle import NativeJobHandle, resume_start, start_job, wait_job


def _parse(directory, request, policy, *, cancel_event=None):
    outcome_path = directory/'parse_outcome.json'
    if outcome_path.is_file():
        return json.loads(outcome_path.read_text())
    handle = NativeJobHandle(directory/'parser.handle.json')
    try:
        if not handle.path.exists():
            atomic_json(directory/'request.json', request)
            environment = {'PYTHONPATH': str(Path(__file__).resolve().parents[4])+os.pathsep+os.environ.get('PYTHONPATH', '')}
            start_job([sys.executable, '-m', 'gene_annotation_episode.episodic_workflow.root.library.phmmer_result_worker', str(directory/'request.json')],
                cwd=directory, policy=policy, handle_path=handle.path, env=environment,
                stdout_path=directory/'parser.stdout', stderr_path=directory/'parser.stderr', cancel_event=cancel_event)
        else:
            resume_start(handle, cancel_event=cancel_event)
        result = wait_job(handle, cancel_event=cancel_event)
        failure = None if result.returncode == 0 else {'code': 'phmmer_parser_nonzero_exit', 'native_returncode': result.returncode}
        if failure and (directory/'failure.json').is_file():
            failure.update(json.loads((directory/'failure.json').read_text()))
        outcome = {'native': result.metadata, 'failure': failure}
    except AcquisitionError as error:
        if error.phase == 'local_admission' and (error.operational or {}).get('retryable'):
            # No parser ran. Preserve its prepared handle, and let the owner
            # retry acquisition without caching a failed or empty analysis.
            raise
        outcome = {'native': error.operational, 'failure': {'code': error.code, 'phase': error.phase,
                                                         'resource': (error.operational or {}).get('resource')}}
    atomic_json(outcome_path, outcome)
    return outcome


