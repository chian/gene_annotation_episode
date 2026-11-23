"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module imports
another episode folder; the episode's own forms, assignment reading, credit, commissions and blocked job-service calls
behave on real data. Nothing here is faked and nothing contacts a remote service."""
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
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCWorkPlanning
TASK = importlib.import_module(PACKAGE + '.task')
CREDIT = importlib.import_module(PACKAGE + '.credit')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
TO_CHILD = importlib.import_module(PACKAGE + '.messages.msg_to_child')
FROM_CHILD = importlib.import_module(PACKAGE + '.messages.read_from_child')
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
            'hpc_allocation_execution', 'hpc_resource_prediction')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'commission_id': 'c1', 'scope': {'subject_refs': []}, 'input_refs': []}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0]
            not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'biochemical_feasibility_evidence/hpc_work_planning'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + child for slot, child in zip(
        ('hpc_prediction', 'hpc_execution', 'launch', 'monitor', 'results'),
        ('hpc_resource_prediction', 'hpc_allocation_execution', 'execution_job_submission',
         'execution_progress_assessment', 'execution_result_acquisition'))}
    assert tuple(EPISODE.services) == ('job_access', 'estimate_table')
    assert all(re.fullmatch(r'[a-z][a-z0-9_]*', name) for name in EPISODE.tools)
    assert len(EPISODE.tools) == 13 and 'hpc_initialize' in EPISODE.tools


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
    parent_input = EPISODE.read_from_parent(form.admit(ASSIGNMENT, 'test'), {'purpose': 'x'})
    assert parent_input == {'commission_identity': {'commission_id': 'c1'}, 'scope': {'subject_refs': []},
                            'input_refs': [], 'message': {'purpose': 'x'}}
    source = {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}
    assert EPISODE.read_from_parent(form.admit({**source, 'commission_source_ref': ['source_1']}, 'test'), {})[
        'commission_identity'] == {'commission_source_ref': 'source_1'}
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'commission_source_ref': ['source_1']}, 'test'), {})
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit(source, 'test'), {})
    with pytest.raises(ValueError, match='hpc_commission_source_ref_must_hold_exactly_one_reference'):
        EPISODE.read_from_parent(form.admit({**source, 'commission_source_ref': ['a', 'b']}, 'test'), {})
    request = {'name': 'tool', 'resources': 'hpc', 'arguments_json': '{}', 'result_reader': 'reader',
               'objective': 'o'}
    assert EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'tool_request': request}, 'test'), {})[
        'tool_request'] == request
    with pytest.raises(ValueError, match='hpc_tool_request_must_name'):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'tool_request': {'name': 'tool'}}, 'test'), {})
    with pytest.raises(FormError):
        form.admit({key: value for key, value in ASSIGNMENT.items() if key != 'scope'}, 'test')


def test_the_return_form_declares_credit_and_finding_and_the_four_old_facts_as_selectable():
    form = FINAL.RETURN_FORM
    assert set(form.fields) == {'credit', 'finding', 'hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations',
                                'hpc_result_refs'}
    assert form.select(('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')) is not None
    with pytest.raises(FormError):
        form.select(('credit',))
    with pytest.raises(FormError):
        form.select(('hpc_unknown',))


def test_the_credit_is_the_owner_ledger_credit_last_known_and_never_bounded():
    assert CREDIT.credit({'ledger_credit': 0.0}, None) == 0.0
    assert CREDIT.credit({'ledger_credit': -1.5}, None) == -1.5
    assert CREDIT.credit({'ledger_credit': 1e9}, None) == 1e9


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
    summary = {'ledger_view': {'plans': [], 'commission': {}}, 'launches': [], 'scope': {}, 'input_refs': [],
               'message': {}}
    with pytest.raises(StopIteration):
        TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0}, summary)


def test_the_monitor_and_results_commissions_name_the_child_fields_and_select_declared_return_fields():
    summary = {'scope': {}, 'input_refs': []}
    monitor = TO_CHILD.msg_to_child('monitor', {
        'target_handle': 'handle', 'requested_fields': ['execution_status'], 'known_progress_refs': [],
        'permitted_committed_record_types': [], 'information_unit': 1.0}, summary)
    assert monitor.assignment['version'] == 'monitor_assignment'
    assert monitor.selection == TASK.MONITOR_SELECTION
    results = TO_CHILD.msg_to_child('results', {'handoff_ref': 'row_1', 'selector': {'paths': ['a']},
                                                'acquired_record_unit': 2.0}, summary)
    assert results.assignment == {'version': 'execution_results_assignment', 'handoff_ref': ['row_1'],
                                  'selector': {'paths': ['a']}, 'resource_kind': 'hpc',
                                  'acquired_record_unit': 2.0}
    assert results.selection == TASK.RESULTS_SELECTION == ()


def test_the_launch_commission_is_built_from_the_frozen_plan():
    plan = {'plan_ref': 'plan_1', 'plan_id': 'p', 'manifest': {}, 'supplied_input_artifact_ref': 'artifact_plan',
            'launch_assignment': {'version': 'execution_launch_assignment', 'requests': {'r': {'k': 1}},
                                  'immutable_input_versions': [], 'constraints': {'allowed_kinds': ['hpc']}}}
    summary = {'ledger_view': {'plans': [plan], 'commission': {'resource_id': 'r', 'objective': 'o',
                                                              'obligations': {}}, 'coordinator_workspace': '/w'},
               'launches': [], 'scope': {'subject_refs': []}, 'input_refs': ['a'], 'message': {}}
    message = TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0}, summary)
    assert set(message.assignment) == {'version', 'requests', 'immutable_input_versions', 'constraints',
                                       'handoff_unit', 'handed_off_resource_ids', 'record_refs',
                                       'hpc_execution_job'}
    assert message.assignment['requests'] == {'r': {'k': 1}}
    assert message.assignment['record_refs'] == ['a', 'artifact_plan'] and message.assignment['handoff_unit'] == 1.0
    assert message.assignment['handed_off_resource_ids'] == []
    assert message.assignment['hpc_execution_job']['plan_id'] == 'p'
    assert message.selection == TASK.LAUNCH_SELECTION == ('execution_handoff_refs', 'execution_completed')
    summary['launches'] = [{'plan_ref': 'plan_1', 'handoff_refs': ['row_h'], 'completed': True}]
    assert TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0}, summary).assignment[
        'handed_off_resource_ids'] == ['r']


def test_the_execution_sister_gets_the_commission_identity_and_the_prediction_sister_waits_for_ledger_records():
    summary = {'owner_episode_id': 'episode_owner', 'scope': {'subject_refs': []}, 'input_refs': ['a'],
               'commission_identity': {'commission_source_ref': 'source_1'},
               'ledger_view': {'commission': {}, 'ledger': 'ledger_1', 'row_refs': ['row_1']}}
    execution = TO_CHILD.msg_to_child('hpc_execution', {}, summary)
    assert execution.assignment == {'owner_episode_id': 'episode_owner', 'scope': {'subject_refs': []},
                                    'input_refs': ['a'], 'commission_source_ref': 'source_1', 'ledger': 'ledger_1',
                                    'ledger_row_refs': ['row_1']}
    assert execution.selection == TASK.EXECUTION_SELECTION == (
        'hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')
    assert TASK.PREDICTION_SELECTION == ('hpc_credit', 'hpc_accepted_obligations')
    assert TO_CHILD.msg_to_child('hpc_prediction', {}, summary).assignment['ledger_refs'] == ['row_1']


def test_the_children_reports_are_read_from_their_declared_return_fields():
    sister = {'credit': 1.0, 'hpc_credit': 1.0, 'hpc_model_ref': 'm', 'hpc_accepted_obligations': ['o'],
              'hpc_result_refs': ['source_1']}
    assert FROM_CHILD.read_from_child('hpc_execution', sister, {}, None)['hpc_result_refs'] == ['source_1']
    prediction = FROM_CHILD.read_from_child('hpc_prediction', {**sister, 'hpc_ledger_refs': ['row_1']}, {}, None)
    assert prediction['hpc_ledger_refs'] == ['row_1']
    results = FROM_CHILD.read_from_child('results', {'credit': 2.0, 'execution_result_refs': ['source_2'],
                                                     'execution_result_artifact_refs': ['artifact_2'],
                                                     'execution_completed': False}, {}, None)
    assert results['result_refs'] == ['source_2'] and results['result_artifact_refs'] == ['artifact_2']
    assert FROM_CHILD.read_from_child('launch', {'credit': 1.0, 'execution_handoff_refs': ['row_h'],
                                                 'execution_completed': True}, {}, None)['handoff_refs'] == ['row_h']
    monitor = {'credit': 1.0, 'monitoring_progress_refs': [], 'monitoring_target_handle': 'h',
               'monitoring_execution_state': {'value': 'running'}, 'monitoring_result_available': {'value': False},
               'monitoring_observed_at_unix_seconds': {'value': 1.0}, 'monitoring_committed_record_refs': [],
               'monitoring_progress_snapshots': {}}
    assert FROM_CHILD.read_from_child('monitor', monitor, {}, None)['execution_state'] == 'running'


def test_every_call_the_job_services_must_answer_is_blocked_and_says_which_call_it_wanted():
    with pytest.raises(NotImplementedError, match=r'BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call'):
        TASK.handoff_target(None, 'row_handoff')
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


def test_the_tool_request_is_blocked_where_the_old_code_raised_without_the_head_binding():
    with pytest.raises(NotImplementedError, match='scientific_tool_library_required_for_hpc_tool_request'):
        TASK.resolve_tool_request({'name': 'tool'}, {'subject_refs': []})


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
