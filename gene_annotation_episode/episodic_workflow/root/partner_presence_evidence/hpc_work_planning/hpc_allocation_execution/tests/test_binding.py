"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module imports
another episode folder; the episode's own forms, assignment reading, credit, controller, commissions, report check
and blocked job-service calls behave on real data. Nothing here is faked and nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path
import re

import pytest

from episode_runtime import EpisodeBinding, ToolCall
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
         'tests/__init__.py', 'tests/test_binding.py', 'tests/test_hpc_allocation_execution_runs.py',
         'tests/test_branch_hpc_allocation_execution_model_run.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'owner_episode_id': 'episode_owner', 'ledger': 'hpc_ledger_1', 'ledger_row_refs': [],
              'commission_id': 'c1', 'scope': {'subject_refs': []}, 'input_refs': []}
PLAN = {'plan_ref': 'plan_1', 'plan_id': 'p1', 'candidate_id': 'cand', 'handed_off': False, 'closed': False,
        'manifest': {'workspace': '/ws/hpc/p1'}, 'launch_input_ref': 'artifact_plan',
        'launch_assignment': {'version': 'execution_launch_assignment',
                              'requests': {'aurora': {'version': 'practical_assignment', 'resource_kind': 'hpc',
                                                      'resource_id': 'aurora'}},
                              'immutable_input_versions': [],
                              'constraints': {'allowed_resource_ids': ['aurora'], 'allowed_kinds': ['hpc']}}}
VIEW = {'plans': [PLAN], 'commission': {'resource_id': 'aurora', 'objective': 'o', 'obligations': {'o1': {}, 'o2': {}}},
        'ledger_refs': ['row_commission', 'row_plan', 'artifact_plan'], 'model_ref': 'reference_model',
        'credit': {'credit': 2.0, 'components': {'actual': 1.0, 'model': 0.0, 'validation': 1.0},
                   'contributions': [{'slot': 'actual:o1', 'kind': 'actual'}]}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0]
            not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'
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
    assert parent_input == {'owner_episode_id': 'episode_owner', 'ledger': 'hpc_ledger_1', 'commission_identity': {'commission_id': 'c1'},
                            'scope': {'subject_refs': []}, 'input_refs': []}
    source = {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}
    assert EPISODE.read_from_parent(form.admit({**source, 'commission_source_ref': 'source_1'}, 'test'), {})[
        'commission_identity'] == {'commission_source_ref': 'source_1'}
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit({**ASSIGNMENT, 'commission_source_ref': 'source_1'}, 'test'), {})
    with pytest.raises(ValueError, match='exactly_one_of_commission_id_and_commission_source_ref_required'):
        EPISODE.read_from_parent(form.admit(source, 'test'), {})
    with pytest.raises(FormError):
        form.admit({key: value for key, value in ASSIGNMENT.items() if key != 'owner_episode_id'}, 'test')


def test_the_return_form_is_controlled_data_with_the_ledger_rows_always_returned():
    fields = FINAL.RETURN_FORM.as_record()
    assert {name for name, field in fields.items() if field['required']} == {'credit', 'finding', 'hpc_ledger_refs'}
    assert {name for name, field in fields.items() if not field['required']} == {'hpc_result_refs',
                                                                               'hpc_result_artifact_refs'}
    assert {field['type'] for field in fields.values()} == {'number', 'record', 'record_refs'}
    assert {field['type'] for field in FINAL.FINDING_FORM.as_record().values()} == {'integer'}   # no text passes
    with pytest.raises(FormError):
        FINAL.RETURN_FORM.select(('credit',))
    with pytest.raises(FormError):
        FINAL.RETURN_FORM.select(('hpc_model_ref',))


def test_the_credit_is_what_the_ledger_gained_since_this_episode_first_read_it():
    assert CREDIT.credit({'ledger_view': None}, None) == 0.0
    assert CREDIT.credit({'ledger_view': {'credit': {'credit': -1.5, 'components': {}}}, 'entry_credit': 0.5}, None) == -2.0


def test_the_controller_is_an_accumulation_controller_built_from_the_cost_and_parameters_settings():
    controller = EPISODE.yield_controller(0.0, {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(KeyError):
        EPISODE.yield_controller(0.0, {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}, {})


def test_the_first_unit_reads_the_owner_commission_through_the_episodes_own_tool():
    summary = {'ledger_view': None, 'owner_episode_id': 'episode_owner', 'ledger': 'hpc_ledger_1',
               'commission_identity': {'commission_id': 'c1'}, 'scope': {'subject_refs': []}}
    call = TASK.decide(summary, None, None)
    assert isinstance(call, ToolCall) and call.name == 'hpc_read'
    assert call.arguments == {'reference': 'commission', 'owner_episode_id': 'episode_owner', 'ledger': 'hpc_ledger_1',
                              'commission_identity': {'commission_id': 'c1'}, 'scope': {'subject_refs': []}}


def test_a_commission_names_its_child_slot_and_a_plan_this_episode_holds():
    with pytest.raises(LookupError):
        TO_CHILD.msg_to_child('wait', {}, {})
    with pytest.raises(LookupError):
        FROM_CHILD.read_from_child('wait', {}, {}, None)
    summary = {'ledger_view': {'plans': [], 'commission': {}}, 'launches': [], 'scope': {}, 'input_refs': []}
    with pytest.raises(StopIteration):
        TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0, 'acquired_record_unit': 1.0},
                              summary)


def test_the_launch_commission_passes_the_plans_launch_input_in_custody():
    summary = {'ledger_view': VIEW, 'launches': [], 'scope': {}, 'input_refs': ['source_in']}
    message = TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0,
                                               'acquired_record_unit': 2.0}, summary)
    assert set(message.assignment) == {'version', 'requests', 'immutable_input_versions', 'constraints',
                                       'record_refs', 'handoff_unit', 'acquired_record_unit',
                                       'received_handoff_resources'}
    assert message.assignment['requests'] == PLAN['launch_assignment']['requests']
    # The frozen plan is an artifact the ledger names: it is passed as a record, not as a path.
    assert message.assignment['record_refs'] == ['source_in', 'artifact_plan']
    assert message.message['hpc_execution_job']['launch_input_ref'] == 'artifact_plan'
    assert 'supplied_input_file' not in message.message['hpc_execution_job']
    assert message.assignment['received_handoff_resources'] == []
    assert message.selection == () == TASK.LAUNCH_SELECTION
    launched = {**summary, 'launches': [{'plan_ref': 'plan_1', 'handoff_refs': ['source_h'], 'completed': True}]}
    again = TO_CHILD.msg_to_child('launch', {'plan_ref': 'plan_1', 'handoff_unit': 1.0, 'acquired_record_unit': 2.0,
                                             'launch_instructions': {'sections': []}}, launched)
    assert again.assignment['received_handoff_resources'] == ['aurora']
    assert again.assignment['launch_instructions'] == {'sections': []}


def test_the_monitor_and_results_commissions_name_the_child_fields_and_select_declared_return_fields():
    summary = {'ledger_view': VIEW, 'launches': [{'plan_ref': 'plan_1', 'handoff_refs': ['source_h'],
                                                  'completed': True}], 'scope': {}, 'input_refs': []}
    monitor = TO_CHILD.msg_to_child('monitor', {
        'target_handle': 'handle', 'requested_fields': ['execution_status'],
        'permitted_committed_record_types': [], 'information_unit': 1.0}, summary)
    assert monitor.assignment['version'] == 'monitor_assignment'
    assert monitor.assignment['known_progress_refs'] == []
    assert monitor.selection == TASK.MONITOR_SELECTION
    results = TO_CHILD.msg_to_child('results', {'handoff_ref': 'source_h', 'selector': {'paths': ['a']},
                                                'acquired_record_unit': 2.0}, summary)
    assert results.assignment == {'handoff_ref': ['source_h'], 'selector': {'paths': ['a']}, 'resource_kind': 'hpc',
                                  'workspace': '/ws/hpc/p1', 'acquired_record_unit': 2.0}
    assert results.selection == () == TASK.RESULTS_SELECTION
    with pytest.raises(StopIteration):
        TO_CHILD.msg_to_child('results', {'handoff_ref': 'source_other', 'selector': {}, 'acquired_record_unit': 1.0},
                              summary)


def test_what_the_parent_takes_from_each_childs_result():
    launch = FROM_CHILD.read_from_child('launch', {'credit': 1.0, 'execution_handoff_refs': ['source_h'],
                                                   'execution_completed': True}, {}, None)
    assert launch == {'slot': 'launch', 'child_credit': 1.0, 'handoff_refs': ['source_h'], 'completed': True}
    results = FROM_CHILD.read_from_child('results', {'credit': 1.0, 'execution_result_refs': ['source_r'],
                                                     'execution_completed': False}, {}, None)
    assert results['result_refs'] == ['source_r'] and results['completed'] is False


def test_no_call_of_the_task_is_a_stub_and_the_instructions_state_purpose_ledger_actions_and_credit():
    source = (FOLDER / 'task.py').read_text()
    assert 'NotImplementedError' not in source and 'BLOCKED-ON' not in source and 'ledger.path' not in source
    text = TASK.INSTRUCTIONS
    assert text.startswith('You are the allocation-execution episode of one HPC commission. Your job is to plan the '
                           'allocation from the HPC ledger')
    for phrase in ('What you are shown.', 'How to work.', 'What earns credit.', 'a plan is launched once',
                   'completion is not acceptance', 'never replace an uncertain submission'):
        assert phrase in text
    for name in ('hpc_queue_observe', 'hpc_compare', 'hpc_plan', 'launch', 'hpc_handoff', 'hpc_monitor',
                 'hpc_results'):
        assert name in text
    assert 'SSH' not in text and 'hpc_child_scope' not in text and 'iterator' not in text


def test_the_result_returns_the_controllers_credit_counts_and_the_ledger_rows():
    summary = {'ledger_view': VIEW, 'ledger_state': {'accepted_obligations': ['o1']},
               'result_refs': ['source_r'], 'result_artifact_refs': ['artifact_r']}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}
    result = FINAL.final_to_parent(summary, completion, ('hpc_result_refs', 'hpc_result_artifact_refs'))
    assert result == {'credit': 2.0, 'hpc_ledger_refs': ['row_commission', 'row_plan', 'artifact_plan'],
                      'hpc_result_refs': ['source_r'], 'hpc_result_artifact_refs': ['artifact_r'],
                      'finding': {'accepted_obligations': 1, 'remaining_obligations': 1, 'plans_frozen': 1,
                                  'plans_handed_off': 0, 'plans_closed': 0, 'results_published': 1}}
    FINAL.RETURN_FORM.select(('hpc_result_refs', 'hpc_result_artifact_refs')).admit(result, 'result')
    FINAL.RETURN_FORM.select(()).admit(FINAL.final_to_parent(summary, completion, ()), 'result')
