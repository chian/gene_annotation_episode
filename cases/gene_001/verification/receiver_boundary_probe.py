"""Explicit verification fixture around the ordinary configured-model case run.

Inject one transient receiving-interface failure during a selected handoff check.
There is no action script, new episode loop, controller, score, native wrapper,
work delay or job selection here. Every later action belongs to the episodes.
Never describe this injected fault as a naturally observed service failure.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


@contextmanager
def selected_receiver_fault(record_path, registry_directory):
    """Fail one selected operation identity, including its interrupted replay.

    New selected operations see the restored receiver. Assignment and closure
    checks are untouched. The durable fixture record is audit metadata only;
    it never enters a child form, credit, or the shared statistics channel.
    """
    from gene_annotation_episode.homology_episodes import HomologyEpisodes
    from gene_annotation_episode.homology_jobs import HomologyJobs

    record_path = Path(record_path).resolve()
    registry_directory = Path(registry_directory).resolve()
    version = 'selected_receiver_fault_verification_v1'
    selected = ContextVar('verification_selected_handoff_check', default=None)
    original_execute, original_receive = HomologyEpisodes._execute, HomologyJobs.receive

    def read_record():
        if not record_path.exists():
            return None
        value = json.loads(record_path.read_text())
        if value['version'] != version or value['registry_directory'] != str(registry_directory):
            raise ValueError('receiver_verification_record_binding_mismatch')
        return value

    read_record()

    @wraps(original_execute)
    async def execute(binding, source, name, args, *, operation_key):
        if name != 'homology.check_handoff' or binding.jobs.directory.resolve() != registry_directory:
            return await original_execute(binding, source, name, args, operation_key=operation_key)
        assignment = binding.assignment(source)
        token = selected.set({'operation_key': operation_key, 'job_ref': assignment['job_ref'],
            'run_id': source.workflow.run_id, 'episode_id': source.episode_id})
        try:
            return await original_execute(binding, source, name, args, operation_key=operation_key)
        finally:
            selected.reset(token)

    @wraps(original_receive)
    def receive(receiver, handoff):
        action = selected.get()
        if action is not None and receiver.directory.resolve() == registry_directory:
            fault = read_record()
            if fault is None:
                fault = {'version': version, 'registry_directory': str(registry_directory),
                    **action, 'recorded_at_unix_seconds': time.time(),
                    'kind': 'intentionally_injected_transient_receiver_failure',
                    'recovery': 'next_distinct_selected_operation_uses_real_receiver',
                    'not_a_natural_service_failure': True}
                record_path.parent.mkdir(parents=True, exist_ok=True)
                with record_path.open('x', encoding='utf-8') as handle:
                    json.dump(fault, handle, sort_keys=True, indent=2, allow_nan=False)
                    handle.write('\n')
                    handle.flush()
                    os.fsync(handle.fileno())
                descriptor = os.open(record_path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            if fault['operation_key'] == action['operation_key']:
                if fault['job_ref'] != handoff['job_ref'] or fault['run_id'] != action['run_id']:
                    raise ValueError('receiver_verification_operation_identity_mismatch')
                raise sqlite3.OperationalError('verification_injected_receiver_temporarily_unavailable')
        return original_receive(receiver, handoff)

    HomologyEpisodes._execute, HomologyJobs.receive = execute, receive
    try:
        yield
    finally:
        HomologyEpisodes._execute, HomologyJobs.receive = original_execute, original_receive


def main(argv=None):
    from gene_annotation_episode.case_execution import run_prepared_case

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--parameters', type=Path)
    parser.add_argument('--resume', action='store_true')
    arguments = parser.parse_args(argv)
    run_dir = arguments.run_dir.resolve()
    # Explicit fixture configuration is separate from the ordinary case and its
    # scoring policy. A resume must use the same harness bytes and fault identity.
    binding = {'version': 'configured_model_receiver_probe_v1',
        'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'registry_directory': str(run_dir / 'native-jobs'),
        'fault_record': str(run_dir / 'injected-receiver-fault.json'),
        'action_selection': 'configured_episode_models',
        'controller_and_credit': 'unchanged_explicit_case_policy',
        'native_execution': 'ordinary_bound_executable_without_delay_or_wrapper'}
    marker = run_dir / 'receiver-probe.json'
    if marker.exists():
        if json.loads(marker.read_text()) != binding:
            raise ValueError('receiver_verification_harness_changed')
    elif arguments.resume:
        raise ValueError('receiver_verification_resume_requires_original_binding')
    else:
        from gene_annotation_episode._local_job_worker import atomic_json
        atomic_json(marker, binding)
    parameters = json.loads(arguments.parameters.read_text()) if arguments.parameters is not None else None
    with selected_receiver_fault(binding['fault_record'], binding['registry_directory']):
        summary = asyncio.run(run_prepared_case(run_dir, policy_file=arguments.policy,
            parameters=parameters, resume=arguments.resume))
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
