"""The A104 HPC allocation execution episode is a private binding in the ten-file form; its assignment, controller,
credit, report and commissions are the real forms and functions; its commissions are admitted by the real forms of
the three children; and a run of it on the real runner stops at the first unit that needs a job service, with the
BLOCKED-ON-JOB-SERVICE error (no service of the run offers the ledger yet).

Nothing here is faked: the Store, the journal, the model provider (never asked: the first unit is the ledger
lookup), the runner and the controllers are the real ones; a service is a real object behind a factory."""
import ast
import asyncio
from importlib import import_module
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from episode_runtime import BindingRegistry, ChildMessage, EpisodeBinding, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from method_loop import FormError
from yield_control import AccumulationYieldController

from .. import episode as episode_module
from ..credit import credit
from ..episode import HpcAllocationExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM, final_to_parent
from ..messages.msg_to_child import msg_to_child
from ..messages.read_from_child import read_from_child
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..task import CHILD_SLOTS, TOOLS, SERVICES, _selection_schema, catalog, decide, generation_schema
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition')
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
SETTINGS = {'resources': {}, 'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.05}}


def _own_files():
    for path in sorted(FOLDER.rglob('*')):
        relative = path.relative_to(FOLDER)
        if (path.is_file() and '__pycache__' not in relative.parts and relative.parts[0] not in CHILDREN
                and relative.parts[0] != 'tests'):
            yield path, relative


def _child_module(name, dotted):
    return import_module(PACKAGE + '.' + name + '.' + dotted)


def test_the_class_inherits_only_the_system_episode_type():
    assert HpcAllocationExecution.__bases__ == (EpisodeBinding,)
    assert HpcAllocationExecution.binding_path == BINDING_PATH
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    assert dict(HpcAllocationExecution.child_slots) == {
        'launch': BINDING_PATH + '/execution_job_submission', 'monitor': BINDING_PATH + '/execution_progress_assessment',
        'results': BINDING_PATH + '/execution_result_acquisition'}
    assert dict(CHILD_SLOTS) == dict(HpcAllocationExecution.child_slots)
    assert tuple(HpcAllocationExecution.services) == SERVICES == ('hpc_ledger', 'job_access', 'estimate_table')


def test_the_folder_holds_exactly_the_ten_files():
    assert {str(relative) for _, relative in _own_files()} == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path, relative in _own_files():
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if len(relative.parts) == 1 else 0), (relative, node.module)
                modules = [node.module or '']
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                assert '.episodic_workflow.root' not in module and not module.startswith('..'), (relative, module)


def test_every_old_operation_is_a_tool_and_the_catalogue_follows_the_shared_memory():
    names = {entry['name'].replace('.', '_') for entry in catalog({'shared_execution_memory': {}})}
    assert names == set(TOOLS) - {'hpc_state'}
    assert 'hpc.history.refresh' not in {entry['name'] for entry in catalog({})}
    for settings in ({}, {'shared_execution_memory': {}}):
        schema = _selection_schema(settings)
        Draft202012Validator.check_schema(schema)
        generation_schema(schema)
        options = schema['properties']['selection']['anyOf']
        assert len(options) == len(catalog(settings)) + len(CHILD_SLOTS)


def _assignment(**changes):
    value = {'owner_episode_id': 'hpc_owner', 'ledger': 'ledger_1', 'ledger_refs': [], 'commission_id': 'c1',
             'scope': {'subject_refs': []},
             'handoff_unit': 2.0, 'acquired_record_unit': 1.0, 'information_unit': 0.5}
    value.update(changes)
    return value


def _parent_input(**changes):
    assignment = {name: value for name, value in _assignment(**changes).items() if value is not None}
    return read_from_parent(ASSIGNMENT_FORM.admit(assignment, 'assignment'), {})


def test_the_assignment_is_read_once_with_exactly_one_commission_identity():
    parent_input = _parent_input()
    assert parent_input['commission'] == {'commission_id': 'c1'} and parent_input['record_refs'] == []
    by_ref = _parent_input(commission_id=None, commission_source_ref=['source_x'])
    assert by_ref['commission'] == {'commission_source_ref': 'source_x'} and by_ref['record_refs'] == ['source_x']
    with pytest.raises(ValueError, match='hpc_assignment_requires_exactly_one_commission_identity'):
        _parent_input(commission_id=None)
    with pytest.raises(ValueError, match='hpc_assignment_requires_exactly_one_commission_identity'):
        _parent_input(commission_source_ref=['source_x'])
    with pytest.raises(ValueError, match='hpc_assignment_requires_exactly_one_commission_source_ref'):
        _parent_input(commission_id=None, commission_source_ref=['a', 'b'])
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        _parent_input(information_unit=0)
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({k: v for k, v in _assignment().items() if k != 'owner_episode_id'}, 'assignment')


def test_the_controller_accumulates_at_the_cost_of_the_settings():
    controller = yield_controller(0.0, SETTINGS, _parent_input())
    assert isinstance(controller, AccumulationYieldController) and controller.cost == 0.1
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required'):
        yield_controller(0.0, {}, _parent_input())
    with pytest.raises(ValueError, match='explicit_hpc_commission_yield_binding_required'):
        yield_controller(0.0, {'cost': 0, 'parameters': {}}, _parent_input())


def _state(credit_value=3.0, plans=()):
    return {'hpc_credit': {'credit': credit_value, 'components': {'actual': credit_value}, 'contributions': []},
            'hpc_model_ref': 'reference_model', 'hpc_accepted_obligations': ['o1'], 'hpc_result_refs': ['source_r'],
            'hpc_plans': list(plans), 'hpc_commission': {'objective': 'o', 'obligations': {'o1': {'credit': 3.0}}}}


def _summary(**changes):
    value = {'episode': {'owner_episode_id': 'hpc_owner', 'scope': {'subject_refs': []},
                         'commission': {'commission_id': 'c1'}},
             'handoff_unit': 2.0, 'acquired_record_unit': 1.0, 'information_unit': 0.5, 'state': None, 'plans': {},
             'staged_inputs': {}, 'launches': [], 'monitors': [], 'acquisitions': [], 'controller': None,
             'units_consumed': 0}
    value.update(changes)
    return value


def test_the_first_unit_is_the_ledger_lookup_and_the_credit_is_the_ledgers_unbounded():
    unit = decide(_summary(), None, None)
    assert isinstance(unit, ToolCall) and unit.name == 'hpc_state'
    assert unit.arguments == {'episode': _summary()['episode']}
    assert credit(_summary(), None) == 0.0
    assert credit(_summary(state=_state(3.0)), None) == 3.0
    assert credit(_summary(state=_state(1e9)), None) == 1e9 and credit(_summary(state=_state(-4.0)), None) == -4.0


def _practical(resource_id):
    return {'version': 'practical_assignment', 'assignment_id': 'a-' + resource_id, 'resource_id': resource_id,
            'resource_kind': 'hpc', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['/bin/true'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


def _plan(handoff_ref=None):
    return {'plan_ref': 'plan_1', 'plan_id': 'p1', 'candidate_id': 'k1', 'closed': False, 'handoff_ref': handoff_ref,
            'launch_assignment': {'version': 'execution_launch_assignment',
                                  'requests': {'hpc1': _practical('hpc1')}, 'immutable_input_versions': [],
                                  'constraints': {'allowed_resource_ids': ['hpc1'], 'allowed_kinds': ['hpc']}},
            'manifest': {'workspace': '/work/space/hpc/p1', 'units': []}}


def _committed_summary(handoff_ref=None):
    plan = _plan(handoff_ref)
    return _summary(state=_state(plans=[plan]), plans={'plan_1': plan}, staged_inputs={'plan_1': '/inputs/p1.json'})


@pytest.mark.parametrize('slot, arguments, child, handoff', [
    ('launch', {'plan_ref': 'plan_1'}, 'execution_job_submission', None),
    ('monitor', {'target_handle': 'h1', 'requested_fields': ['execution_status'], 'known_progress_refs': [],
                 'permitted_committed_record_types': ['source']}, 'execution_progress_assessment', None),
    ('results', {'plan_ref': 'plan_1', 'selector': {'paths': ['/work/space/hpc/p1/units/u1/result.json']}},
     'execution_result_acquisition', 'handoff_1')])
def test_each_commission_is_admitted_by_the_real_form_of_its_child(slot, arguments, child, handoff):
    message = msg_to_child(slot, arguments, _committed_summary(handoff))
    assert isinstance(message, ChildMessage)
    form = _child_module(child, 'messages.read_from_parent')
    admitted = form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    form.read_from_parent(admitted, dict(message.message))
    _child_module(child, 'messages.final_to_parent').RETURN_FORM.select(message.selection)


def test_a_commission_for_an_unknown_slot_fails():
    with pytest.raises(ValueError, match='hpc_child_slot_unknown:nowhere'):
        msg_to_child('nowhere', {}, _committed_summary())
    with pytest.raises(KeyError):
        msg_to_child('launch', {'plan_ref': 'no_such_plan'}, _committed_summary())


def test_each_childs_admitted_return_is_read():
    launch = _child_module('execution_job_submission', 'messages.final_to_parent').RETURN_FORM.admit({
        'credit': 4.0, 'execution_handoff_refs': ['handoff_1'], 'execution_completed': True,
        'finding': {'handoff_established': True, 'handoff_resources': ['hpc1'], 'new_handoff_count': 1,
                    'launches_run': 1, 'launches': [{'slot': 'launch_hpc', 'resource_id': 'hpc1', 'completed': True,
                                                     'handoff_refs': ['handoff_1']}]}}, 'result')
    assert read_from_child('launch', launch, _summary(), None)['handoff_refs'] == ['handoff_1']
    message = msg_to_child('monitor', {'target_handle': 'h1', 'requested_fields': ['execution_status'],
                                       'known_progress_refs': [], 'permitted_committed_record_types': ['source']},
                           _committed_summary())
    monitor_form = _child_module('execution_progress_assessment', 'messages.final_to_parent').RETURN_FORM
    monitor = monitor_form.select(message.selection).admit({
        'credit': 0.5, 'finding': {'target_handle': 'h1', 'observed': True, 'execution_state': 'executing',
                                   'result_available': False, 'received_progress_ref_count': 1,
                                   'newly_informative_snapshot_count': 1, 'qualification': 'q'},
        'monitoring_progress_refs': ['p'], 'monitoring_target_handle': 'h1',
        'monitoring_execution_state': {'value': 'executing'}, 'monitoring_result_available': {'value': False},
        'monitoring_observed_at_unix_seconds': {'value': 5.0}}, 'result')
    report = read_from_child('monitor', monitor, _summary(), None)
    assert report['progress_refs'] == ['p'] and report['execution_state'] == 'executing'
    with pytest.raises(ValueError, match='hpc_child_slot_unknown:nowhere'):
        read_from_child('nowhere', {}, _summary(), None)


def test_the_result_is_admitted_by_the_return_form_and_carries_the_system_credit():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding'}
    summary = _summary(state=_state(3.0, [_plan('handoff_1')]),
                       launches=[{'plan_ref': 'plan_1'}], monitors=[], acquisitions=[])
    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 3.0}
    names = ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')
    result = final_to_parent(summary, completion, names)
    assert result['credit'] == 3.0 and result['hpc_credit'] == 3.0 and result['hpc_result_refs'] == ['source_r']
    assert result['finding']['plans'] == [{'plan_ref': 'plan_1', 'candidate_id': 'k1', 'handoff_attached': True}]
    RETURN_FORM.admit(result, 'return')


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    yield {'store': store, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path), 'tmp': tmp_path}
    store.close()


def _classes():
    found = [HpcAllocationExecution]
    for name in CHILDREN:
        found.append(_episode_class(_child_module(name, 'episode')))
    route_children = {'execution_job_submission': ('api_job_execution', 'hpc_job_execution', 'local_job_execution')}
    for parent, routes in route_children.items():
        for route in routes:
            found.append(_episode_class(import_module(PACKAGE + '.' + parent + '.' + route + '.episode')))
    return found


def _episode_class(module):
    return next(value for value in vars(module).values()
                if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding
                and value.__module__ == module.__name__)


class _Service:
    """A real object behind a zero-argument factory: the run's service, which offers nothing yet."""


def test_a_run_stops_at_the_first_unit_that_needs_the_ledger_service(world):
    classes = _classes()
    registry = BindingRegistry([cls() for cls in classes])
    settings = {**SETTINGS, 'launch_instructions_directory': str(world['tmp']),
                'tool_knowledge_directory': str(world['tmp'])}
    continuation = {cls.binding_path: settings for cls in classes}
    services = {name: _Service for cls in classes for name in cls.services}
    linked = link(registry, BINDING_PATH, {'assignment': _assignment(), 'message': {}, 'selection': []},
                  run_id='blocked', journal=world['journal'],
                  collaborators={'store': world['store'], 'model_provider': world['provider'],
                                 'continuation': continuation, 'services': services})
    message = 'BLOCKED-ON-JOB-SERVICE: hpc_ledger.open'
    with pytest.raises(NotImplementedError, match=message):
        asyncio.run(linked.run())
    assert message in world['journal'].run_failure('blocked')
    path = ((BINDING_PATH, 'blocked'),)
    assert world['journal'].model_calls('blocked', path) == [] and world['journal'].units('blocked', path) == []
