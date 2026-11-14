"""Actual private callback preservation under controlled boundary operands.

Constructors are bypassed to avoid resource acquisition. Real credit_kind,
assignment_schema, checked selection decoding, role dispatch and yield_controller
are exercised. Dispatch-only cases name every replaced data/service port below.
This is not native execution, full workflow restoration or autonomous science.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
ROLES = ('launch', 'launch_local', 'launch_hpc', 'results')
HOMES = [{"home":"execution_job_submission","role":"launch"},{"home":"execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"execution_job_submission/local_job_execution","role":"launch_local"},{"home":"execution_result_acquisition","role":"results"},{"home":"hpc_work_planning/execution_job_submission","role":"launch"},{"home":"hpc_work_planning/execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"hpc_work_planning/execution_job_submission/local_job_execution","role":"launch_local"},{"home":"hpc_work_planning/execution_result_acquisition","role":"results"},{"home":"hpc_work_planning/hpc_allocation_execution/execution_job_submission","role":"launch"},{"home":"hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution","role":"launch_local"},{"home":"hpc_work_planning/hpc_allocation_execution/execution_result_acquisition","role":"results"},{"home":"scientific_process/execution_job_submission","role":"launch"},{"home":"scientific_process/execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"scientific_process/execution_job_submission/local_job_execution","role":"launch_local"},{"home":"scientific_process/execution_result_acquisition","role":"results"},{"home":"scientific_process/hpc_work_planning/execution_job_submission","role":"launch"},{"home":"scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"scientific_process/hpc_work_planning/execution_job_submission/local_job_execution","role":"launch_local"},{"home":"scientific_process/hpc_work_planning/execution_result_acquisition","role":"results"},{"home":"scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission","role":"launch"},{"home":"scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution","role":"launch_hpc"},{"home":"scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution","role":"launch_local"},{"home":"scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition","role":"results"}]


def _new(home):
    module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    return object.__new__(module.ExecutionEpisode)


def _outcome(operation):
    try:
        value = operation()
    except (ValueError, TypeError, KeyError) as error:
        return {'exception': type(error).__name__, 'message': str(error)}
    return {'value': value}


def observations(row):
    home, role = row['home'], row['role']
    binding = _new(home)
    assert binding.roles == (role,)
    binding.resources = {'cpu': {'kind': 'local'}, 'pbs': {'kind': 'pbs_ssh'}}
    binding.native_flux_balance_results = None
    own_schema = binding.assignment_schema(role, internal=True)
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(own_schema)
    encoded = json.dumps(own_schema, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    result = {'role': role, 'actual_own_schema_sha256': hashlib.sha256(encoded).hexdigest(), 'foreign_rejections': []}
    for foreign in ROLES:
        if foreign == role:
            continue
        schema = _outcome(lambda: binding.assignment_schema(foreign, internal=True))
        assignment = _outcome(lambda: binding.prepare_assignment(object(), foreign, {}, {}, 'guarded-role-check'))
        expected = {'exception': 'ValueError', 'message': 'unknown_execution_episode_role'}
        assert schema == assignment == expected
        result['foreign_rejections'].append({'role': foreign, 'assignment_schema': schema, 'prepare_assignment': assignment})
    # Assignment dispatch uses actual checked() and each real method body;
    # these explicitly controlled ports avoid acquiring/commissioning work.
    ports = []
    binding.assignment_schema = lambda supplied_role, **options: (binding.credit_kind(supplied_role), {'type': 'object'})[1]
    scope = {'subject_refs': []}
    parent = SimpleNamespace(role='launch', assignment={'requests': {}, 'immutable_input_versions': []})
    selection = {'version': 'controlled_assignment_boundary', 'resource_id': 'cpu' if role == 'launch_local' else 'pbs',
        'requests': {}, 'immutable_input_versions': []}
    # Store only plain explicit operands; objects passed to ports are reduced
    # to known parent identity, not scientific evidence.
    def note(name, *args, **kwargs):
        def plain(value):
            if value is parent:
                return {'controlled_parent': 'launch'}
            if isinstance(value, dict):
                return {key: plain(item) for key, item in value.items()}
            if isinstance(value, (list, tuple, type({}.values()))):
                return [plain(item) for item in value]
            return value
        ports.append({'port': name, 'args': plain(args), 'kwargs': plain(kwargs)})
    def launch(value, **kwargs):
        note('_launch', value, **kwargs)
        return deepcopy(value)
    binding._launch = launch
    binding._validate_request = lambda value: deepcopy(value)
    binding._flux_balance_inputs = lambda *args, **kwargs: note('_flux_balance_inputs', *args, **kwargs)
    binding._versions = lambda *args, **kwargs: note('_versions', *args, **kwargs)
    saved = {'retained_original_assignment': 'controlled_saved_response'}
    binding._recorded_results_assignment = lambda *args, **kwargs: saved
    prepared = binding.prepare_assignment(parent, role, deepcopy(selection), scope, 'guarded-role-check')
    assert prepared == (saved if role == 'results' else selection)
    result['assignment_dispatch'] = {'prepared': prepared, 'ports': ports}
    if role in {'launch_local', 'launch_hpc'}:
        own = _new(home)
        own.private_yield_binding = True
        called = []
        def estimate(context, initial_credit, epoch):
            called.append({'role': context.role, 'initial_credit': initial_credit, 'epoch': epoch})
            return 'original-private-factory-selected'
        setattr(own, '_' + role + '_yield_controller', estimate)
        current = own.yield_controller(SimpleNamespace(role=role), 2.5, 'controlled-epoch')
        assert current == 'original-private-factory-selected'
        rejects = []
        for foreign in ROLES:
            if foreign != role:
                actual = _outcome(lambda: own.yield_controller(SimpleNamespace(role=foreign), 2.5, 'controlled-epoch'))
                assert actual == {'exception': 'ValueError', 'message': 'unknown_execution_episode_role'}
                rejects.append({'role': foreign, 'outcome': actual})
        result['yield_dispatch'] = {'called': called, 'foreign_rejections': rejects}
    return result


@pytest.mark.parametrize('row', HOMES, ids=[row['home'] for row in HOMES])
def test_private_guarded_callbacks_preserve_actual_baseline(row):
    fixture = Path(__file__).parent / 'fixtures/organization_preservation/a110_guarded_role_baseline.json'
    baseline = json.loads(fixture.read_bytes())
    assert observations(row) == baseline['observations'][row['home']]
