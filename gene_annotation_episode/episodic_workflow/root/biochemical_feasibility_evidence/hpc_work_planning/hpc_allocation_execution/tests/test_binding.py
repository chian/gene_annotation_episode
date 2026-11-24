"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module imports
another episode folder; the episode's own forms, assignment reading, credit, commissions and blocked job-service calls
behave on real data. The child folders are read as data by their field names and never imported. Nothing here is faked
and nothing contacts a remote service."""
import ast
import asyncio
import importlib
from pathlib import Path
import re

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCAllocationExecution
TASK = importlib.import_module(PACKAGE + '.task')
CREDIT = importlib.import_module(PACKAGE + '.credit')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
TO_CHILD = importlib.import_module(PACKAGE + '.messages.msg_to_child')
FROM_CHILD = importlib.import_module(PACKAGE + '.messages.read_from_child')
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'owner_episode_id': 'episode_owner', 'commission_id': 'c1', 'scope': {'subject_refs': []},
              'input_refs': [], 'ledger': 'ledger_1', 'ledger_row_refs': []}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0]
            not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + child for slot, child in zip(
        ('launch', 'monitor', 'results'), CHILDREN)}
    assert tuple(EPISODE.services) == ('job_access', 'estimate_table')
    assert all(re.fullmatch(r'[a-z][a-z0-9_]*', name) for name in EPISODE.tools)
    assert len(EPISODE.tools) == 12


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if path.relative_to(FOLDER).parts[0] in CHILDREN:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_one_commission_identity_and_read_from_parent_returns_it():
    form = EPISODE.assignment_form
    parent_input = EPISODE.read_from_parent(form.admit(ASSIGNMENT, 'test'), {})
    assert parent_input == {'owner_episode_id': 'episode_owner', 'commission_identity': {'commission_id': 'c1'},
                            'scope': {'subject_refs': []}, 'input_refs': [], 'ledger': 'ledger_1'}
    source = {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}
    assert EPISODE.read_from_parent(form.admit({**source, 'commission_source_ref': 'source_1'}, 'test'), {})[
        'commission_identity'] == {'commission_source_ref': 'source_1'}
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'commission_source_ref': 'source_1'}, 'test'), {})
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit(source, 'test'), {})
    with pytest.raises(FormError):
        form.admit({key: value for key, value in ASSIGNMENT.items() if key != 'owner_episode_id'}, 'test')


def test_the_return_form_declares_credit_and_finding_and_the_four_old_facts_as_selectable():
    form = FINAL.RETURN_FORM
    assert set(form.fields) == {'credit', 'finding', 'hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations',
                                'hpc_result_refs'}
    assert form.select(('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')) is not None
    with pytest.raises(FormError):
        form.select(('credit',))
    with pytest.raises(FormError):
        form.select(('hpc_unknown',))


def test_the_credit_is_the_owner_ledger_credit_the_last_tool_showed_and_zero_before_any_tool():
    assert CREDIT.credit({'ledger_view': None}, None) == 0.0
    assert CREDIT.credit({'ledger_view': {'credit': {'credit': -1.5, 'components': {}}}}, None) == -1.5


def test_the_controller_is_an_accumulation_controller_built_from_the_settings():
    controller = EPISODE.yield_controller(0.0, {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(KeyError):
        EPISODE.yield_controller(0.0, {}, {})


def test_a_commission_names_its_child_slot_and_a_plan_this_episode_holds():
    with pytest.raises(LookupError):
        TO_CHILD.msg_to_child('wait', {}, {})
    with pytest.raises(LookupError):
        FROM_CHILD.read_from_child('wait', {}, {}, None)
    summary = {'ledger_view': {'plans': [], 'commission': {}}, 'launches': [], 'scope': {}, 'input_refs': []}
    with pytest.raises(StopIteration):
        TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0, 'acquired_record_unit': 1.0},
                              summary)


def test_the_monitor_commission_names_the_monitor_fields_and_selects_the_declared_return_fields():
    message = TO_CHILD.msg_to_child('monitor', {
        'target_handle': 'handle', 'requested_fields': ['execution_status'], 'known_progress_refs': [],
        'permitted_committed_record_types': [], 'information_unit': 1.0}, {'scope': {}, 'input_refs': []})
    assert message.assignment['version'] == 'monitor_assignment'
    assert set(message.assignment) == {'version', 'target_handle', 'requested_fields', 'known_progress_refs',
                                       'permitted_committed_record_types', 'information_unit'}
    assert message.selection == TASK.MONITOR_SELECTION


def test_the_results_commission_names_the_results_fields_and_selects_nothing():
    message = TO_CHILD.msg_to_child('results', {'handoff_ref': 'source_1', 'selector': {'paths': ['a']},
                                                'acquired_record_unit': 2.0}, {'scope': {}, 'input_refs': []})
    assert message.assignment['handoff_ref'] == ['source_1']
    assert set(message.assignment) == {'version', 'handoff_ref', 'selector', 'resource_kind',
                                       'acquired_record_unit'}
    assert message.assignment['resource_kind'] == 'hpc'
    assert message.selection == TASK.RESULTS_SELECTION == ()


def test_the_launch_commission_is_built_from_the_plan():
    request = {'resource_id': 'r', 'resource_kind': 'hpc'}
    plan = {'plan_ref': 'plan_1', 'plan_id': 'p', 'manifest': {}, 'supplied_input_artifact_ref': 'artifact_plan',
            'launch_assignment': {'version': 'execution_launch_assignment', 'requests': {'r': request},
                                  'immutable_input_versions': [], 'constraints': {}}}
    summary = {'ledger_view': {'plans': [plan], 'commission': {'resource_id': 'r', 'objective': 'o',
                                                              'obligations': {}}, 'coordinator_workspace': '/w'},
               'launches': [], 'scope': {}, 'input_refs': []}
    message = TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0,
                                               'acquired_record_unit': 2.0}, summary)
    assert message.assignment['requests'] == {'r': request}
    assert message.assignment['received_handoff_resources'] == []
    assert message.message['hpc_execution_job']['plan_id'] == 'p'
    assert set(message.assignment) == {'version', 'requests', 'immutable_input_versions', 'constraints',
                                       'record_refs', 'handoff_unit', 'acquired_record_unit',
                                       'received_handoff_resources'}
    assert message.selection == TASK.LAUNCH_SELECTION == ()
    summary['launches'] = [{'plan_ref': 'plan_1', 'handoff_refs': ['source_1'], 'completed': True}]
    assert TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0, 'acquired_record_unit': 2.0},
                                 summary).assignment['received_handoff_resources'] == ['r']


def test_what_the_parent_reads_from_each_child_is_what_the_child_declares_as_required():
    launch = FROM_CHILD.read_from_child('launch', {'credit': 1.0, 'execution_handoff_refs': ['source_1'],
                                                   'execution_completed': True}, {}, None)
    assert launch == {'slot': 'launch', 'child_credit': 1.0, 'handoff_refs': ['source_1'], 'completed': True}
    results = FROM_CHILD.read_from_child('results', {'credit': 2.0, 'execution_result_refs': ['source_2'],
                                                     'execution_result_artifact_refs': ['artifact_2'],
                                                     'execution_completed': False}, {}, None)
    assert results['result_refs'] == ['source_2'] and results['result_artifact_refs'] == ['artifact_2']
    with pytest.raises(KeyError):
        FROM_CHILD.read_from_child('launch', {'credit': 1.0, 'execution_completed': True}, {}, None)


def test_every_call_the_job_services_must_answer_is_blocked_and_says_which_call_it_wanted():
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call'):
        TASK.handoff_target(None, 'source_handoff')
    for call, pattern in ((lambda: TASK.observe_target({}, 'k', None), 'observe_target'),
                          (lambda: TASK.read_window({}, '/p', 10, 'k', None), 'read_file'),
                          (lambda: TASK.write_allocation_control({}, ['u'], 'k', None), 'write_allocation_control'),
                          (lambda: TASK.observe_queue_value({}, 'k', None), 'observe_queue'),
                          (lambda: TASK.run_command({}, 'ls', 'k', None), 'run_command')):
        with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job_access; wanted call.*' + pattern):
            asyncio.run(call())
    for call, pattern in ((lambda: TASK.estimate_latest(None, 'r', 'queue'), 'latest'),
                          (lambda: TASK.estimate_observe(None, 'r', 'queue', {}, observed_at=1.0, provenance=[]),
                           'observe'),
                          (lambda: TASK.estimate_history(None, {}, now=1.0), 'history'),
                          (lambda: TASK.estimate_policy(None), 'policy'),
                          (lambda: TASK.estimate_record(None, {}), 'record')):
        with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call.*'
                           + pattern):
            call()


def test_the_return_carries_the_finding_and_each_selectable_field_and_is_admitted_by_the_form():
    plan = {'closed': True}
    summary = {'ledger_view': {'model_ref': 'reference_model', 'plans': [plan, {'closed': False}],
                               'commission': {'obligations': ['o1', 'o2']},
                               'credit': {'contributions': [{'slot': 'actual:o1', 'kind': 'actual'},
                                                            {'slot': 'model', 'kind': 'model'}],
                                          'components': {'actual': 1.0, 'model': 0.5, 'validation': 0.0}}},
               'result_refs': ['src_1']}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.5}
    selection = ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')
    result = FINAL.final_to_parent(summary, completion, selection)
    assert result['credit'] == 1.5 and result['hpc_credit'] == 1.5
    assert result['hpc_model_ref'] == 'reference_model' and result['hpc_accepted_obligations'] == ['o1']
    assert result['hpc_result_refs'] == ['src_1']
    assert result['finding']['remaining_obligations'] == ['o2'] and result['finding']['plans_closed'] == 1
    FINAL.RETURN_FORM.admit(result, 'return')
    FINAL.RETURN_FORM.admit(FINAL.final_to_parent(summary, completion, ()), 'return')


def test_the_internal_summary_lists_actions_launches_and_the_latest_ledger_view_from_the_loop_view():
    from method_loop.episode import EpisodeView
    summary_of = importlib.import_module(PACKAGE + '.messages.internal_summary').internal_summary
    outcomes = (
        {'kind': 'tool', 'tool': 'read_ledger', 'arguments': {'owner_episode_id': 'o', 'topic': 'x'},
         'outcome': {'status': 'ok', 'ledger_view': {'credit': {'credit': 1.0}}, 'record_refs': ['r1']}},
        {'kind': 'child', 'slot': 'launch', 'arguments': {'plan_ref': 'p1'},
         'report': {'handoff_refs': ['h1'], 'completed': True}},
        {'kind': 'child', 'slot': 'results', 'arguments': {'resource_kind': 'k'}, 'report': {'x': 1}},
    )
    view = EpisodeView(grain=None, key='k', path=None, units_consumed=3, updates=(), controller_state=None,
                       episode_ref=None, request=None, parent_input={'commission_id': 'c1'}, outcomes=outcomes)
    summary = summary_of(view)
    assert summary['commission_id'] == 'c1' and summary['units_consumed'] == 3
    assert summary['ledger_view'] == {'credit': {'credit': 1.0}}
    assert summary['actions'][0]['arguments'] == {'topic': 'x'}
    assert [action['name'] for action in summary['actions']] == ['read_ledger', 'launch', 'results']
    assert summary['launches'] == [{'plan_ref': 'p1', 'handoff_refs': ['h1'], 'completed': True}]
    assert summary['acquisitions'] == [{'x': 1}] and summary['monitors'] == []
    assert summary['result_refs'] == ['r1'] and summary['action_yields'] is None
