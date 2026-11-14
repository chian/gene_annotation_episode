"""Actual physical-parent identity, source operands and retained refusal boundary."""
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .. import runtime
from ..episode import LegacyAnnotationEpisode
from ..legacy_improvement.episode import LegacyImprovementEpisode
from ..homology_service_setup import legacy_parent_types, homology_binding_types
from ..implementation import ANNOTATION_IMPLEMENTATION_MEMBERS, annotation_implementation_files
from .hierarchy_oracles import PACKAGE, original_selected, original_private_function
from .homology_direction_checks import actual, commission
from .parent_exchange_checks import parent_host, isolated_rows


def check_moved_parent_and_children(directory):
    expected = {'job_launch': 'homology_job_submission', 'job_monitor': 'homology_job_monitoring',
                'job_results': 'homology_result_acquisition'}
    assert legacy_parent_types()['annotation'] is LegacyAnnotationEpisode
    assert LegacyAnnotationEpisode.binding_path == 'legacy_annotation'
    assert LegacyAnnotationEpisode.__module__ == PACKAGE + '.episode'
    for role, home in expected.items():
        with actual(directory / role, parent='annotation', role=role) as host:
            binding = host.binding
            cls = import_module(PACKAGE + '.' + home + '.episode').HomologyEpisode
            assert type(binding) is cls is homology_binding_types()['legacy_annotation'][role]
            assert binding.binding_path == 'legacy_annotation/' + home
            assert binding.commissioning_parent == 'legacy_annotation'
            assert host.flow.legacy_parent_for_path(host.source.path) is LegacyAnnotationEpisode
            assert type(host.source) is LegacyAnnotationEpisode.decision_source_type
            with isolated_rows(host):
                with patch.object(runtime.Workflow, 'selected', original_selected()):
                    before = commission(host, 7)
            with isolated_rows(host):
                after = commission(host, 7)
            assert before == after
            assert after['owner_module'] == PACKAGE + '.' + home + '.episode'
            assert after['task_module'] == PACKAGE + '.' + home + '.task'
            assert after['binding_path'] == 'legacy_annotation/' + home


def descriptor_observation(binding, policy_path, altered):
    reads = []
    native_read = Path.read_bytes
    def supplied_read(path):
        raw = native_read(path)
        if path.resolve() == policy_path:
            reads.append(str(path.resolve()))
            return raw + (b'\n# supplied descriptor operand mutation\n' if altered else b'')
        return raw
    with patch.object(Path, 'read_bytes', supplied_read):
        record = binding.as_record()
    return record, reads


def check_real_descriptor_policy_operand(directory):
    axis = Path(runtime.__file__).parent
    policy_path = (axis / 'library/hpc_handoff_report_contract.py').resolve()
    own = tuple(axis / name for name in ANNOTATION_IMPLEMENTATION_MEMBERS)
    assert len(own) == len(set(own)) == 40
    assert all(path.parent == axis for path in own)
    assert annotation_implementation_files() == own + (policy_path,)
    assert axis / 'runtime.py' not in own and policy_path not in own
    with parent_host(directory, 'hpc') as host:
        bindings = [LegacyAnnotationEpisode, LegacyImprovementEpisode, host.scientific]
        hpc_homes = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
                     'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
        for home in hpc_homes:
            cls = import_module(PACKAGE + '.' + home.replace('/', '.') + '.episode').HPCEpisode
            bindings.append(cls(host.services, store=host.store, run_id=host.journal.run_id,
                directory=directory / home, resources={'original-hpc': {'kind': 'pbs_ssh'}}, commissions={}))
        resource_homes = ('resource_work_submission', 'resource_work_submission/api_resource_work_execution',
            'resource_work_submission/local_resource_work_execution', 'resource_work_submission/hpc_resource_work_execution',
            'resource_result_acquisition')
        for prefix in ('', 'scientific_process/'):
            for home in resource_homes:
                cls = import_module(PACKAGE + '.' + (prefix + home).replace('/', '.') + '.episode').ResourceEpisode
                bindings.append(cls(host.services))
        for binding in bindings:
            original, reads = descriptor_observation(binding, policy_path, False)
            changed, changed_reads = descriptor_observation(binding, policy_path, True)
            assert len(reads) == len(changed_reads) == 1
            assert original['implementation_sha256'] != changed['implementation_sha256']
            assert {key: value for key, value in original.items() if key != 'implementation_sha256'} == {
                key: value for key, value in changed.items() if key != 'implementation_sha256'}
    # No file bytes were modified; only an explicit read operand was varied.


def check_nested_improvement_refusals(directory):
    credit = import_module(PACKAGE + '.legacy_improvement.credit')
    continuation = import_module(PACKAGE + '.legacy_improvement.yield')
    path = (('annotation', 'original'), ('improvement', 'nested'))
    context = SimpleNamespace(path=path, role='improvement')
    with parent_host(directory, 'improvement', parent_role='improvement') as host:
        flow = SimpleNamespace(context=host.context, grains=host.grains,
            controller_factory=SimpleNamespace(requires_original_task=True), run_id=host.journal.run_id,
            receipts=None, journal=SimpleNamespace(row=lambda *args: {
                'request': '{"message":{"scope":{},"episode_assignment":{}}}', 'initial_credit': 0.0}))
        for key, callback, args, message in (
            ('improvement_credit', credit.credit_projector, (flow, context), 'scientific_task_credit_not_declared:improvement'),
            ('improvement_credit', credit.credit_binding, (flow, context), 'scientific_task_credit_not_declared:improvement'),
            ('improvement_yield', continuation.yield_controller, (flow, path), 'scientific_continuation_task_not_declared:improvement')):
            original = original_private_function(key, callback.__name__)
            for observed in (original, callback):
                try:
                    observed(*args)
                except ValueError as error:
                    assert str(error) == message
                else:
                    raise AssertionError('the original conditional refusal was removed')
