"""Controlled saved-producer reservation for RNA reader/receipt tests only.

The declared twenty-GiB historical policy is data, not current authorization.
No native lifecycle preparation, resource approval, process or job is simulated
as successful. The actual current preflight rejection is recorded separately.
Only the reservation operation boundary is supplied; all plan, target, bundle,
grading, saved-action, report and received-custody readers remain actual.
"""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.a107 import native_lifecycle
from gene_annotation_episode.episodic_workflow.root.a107.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_contracts import POLICY
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a107.state import Store


def record_current_preflight_rejection(fixture_module, directory):
    """Exercise the actual original producer reservation under the current bound."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    failure = None
    with Store(directory / 'store') as store:
        try:
            fixture_module.Fixture(store, directory / 'actual-original-request')
        except AcquisitionError as error:
            failure = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                'code': error.code, 'phase': error.phase, 'operational': error.operational,
                'cause_type': type(error.__cause__).__module__ + '.' + type(error.__cause__).__qualname__,
                'cause': str(error.__cause__)}
    assert failure is not None, 'original_twenty_gib_preflight_must_remain_rejected'
    assert failure['code'] == 'whole_workflow_budget_unavailable' and failure['phase'] == 'local_preflight'
    assert failure['operational'] == {'reason': 'native_request_exceeds_environment_bounds',
        'retryable': False, 'prepared_handle_preserved': False}
    assert failure['cause_type'] == 'builtins.ValueError' and failure['cause'] == 'native_request_exceeds_environment_bounds'
    record = {'version': 'rna_original_current_preflight_rejection_v1',
        'actual_current_preflight': True, 'declared_original_policy': POLICY,
        'controlled_producer_port_installed': False, 'native_or_model_operations': 0,
        'failure': failure}
    (directory / 'preflight-rejection.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def controlled_saved_producer_reservation(command, *, cwd, policy, handle_path,
        stdout_path=None, stderr_path=None, stdin_path=None, env=None,
        statistics=None, native_events=None, cpu_threads=1):
    """Supply explicitly synthetic saved-control bytes, never a launch approval."""
    cwd = Path(cwd).resolve(strict=True)
    handle_path = Path(handle_path).resolve()
    assert policy.to_dict() == POLICY and POLICY['memory_bytes'] == 21474836480
    assert stdout_path is stderr_path is stdin_path is statistics is native_events is None
    assert handle_path == cwd / 'native.json' and not handle_path.exists()
    assert command[1:4] == ['-B', '-m',
        'gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_driver']
    assert len(command) == 5 and Path(command[4]).parent == cwd
    assert isinstance(env, dict) and all(isinstance(key, str) and isinstance(value, str) for key, value in env.items())
    paths = {name: str(cwd / ('controlled-saved-producer.' + name)) for name in
        ('request', 'ready', 'release', 'status', 'result', 'launcher')}
    request = {'command': list(command), 'cwd': str(cwd), 'file_bytes': policy.scratch_bytes,
        'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'],
        'stdin_path': None, 'env': dict(env)}
    _immutable(Path(paths['request']), request)
    marker = {'boundary': 'controlled_saved_producer_reservation',
        'genuine_native_producer': False, 'current_resource_authorization': False,
        'native_or_model_operations': 0, 'declared_policy_is_historical_fixture_data': True}
    handle = {'version': native_lifecycle.VERSION,
        'unit': 'controlled-saved-rna-fixture-no-service-dispatched',
        'command': list(command), 'cwd': str(cwd),
        'stdout': str(cwd / 'stdout.log'), 'stderr': str(cwd / 'stderr.log'),
        'paths': paths, 'metadata': {'policy': policy.to_dict(), 'test_fixture': marker},
        'stage': 'prepared', 'started_at': None, 'started_monotonic_ns': None, 'boot_id': None,
        'request_sha256': hashlib.sha256(Path(paths['request']).read_bytes()).hexdigest()}
    for name in ('stdout', 'stderr'):
        Path(handle[name]).write_bytes(b'')
    # No workflow-owner/environment or enforcement claim is invented. This
    # handle cannot pass the real start_prepared workflow identity validation.
    _immutable(handle_path, handle)
    _immutable(cwd / 'controlled-reservation-provenance.json', {
        'version': 'rna_controlled_saved_producer_port_v1', **marker,
        'declared_original_policy': POLICY, 'handle_sha256': hashlib.sha256(handle_path.read_bytes()).hexdigest(),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'actual_read_boundary': 'native_rna_structure_local.local_rna_structure_plan'})
    return native_lifecycle.NativeJobHandle(handle_path)
