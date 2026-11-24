"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with a child; no module of the folder imports another episode folder;
the episode's own form, credit, controller, commission and report behave on real data. Nothing here is faked and
nothing contacts a remote service."""
import ast
import importlib
import re
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding, Rejected
from method_loop import FormError
from yield_control import BoundedQualityYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExecutionJobSubmission
TASK = importlib.import_module(PACKAGE + '.task')
CHILDREN = {'api_job_execution'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
BINDING = 'perturbation_evidence/execution_job_submission'

API_REQUEST = {'version': 'api_service_assignment', 'resource_id': 'bvbrc', 'service': 'bvbrc_appservice',
               'request': {'application': 'rnaseq'}, 'endpoint': 'usable_handoff', 'constraints': {}}
ASSIGNMENT = {'version': 'execution_launch_assignment', 'requests': {'bvbrc': API_REQUEST},
              'immutable_input_versions': [], 'constraints': {}, 'record_refs': ['input_1'], 'handoff_unit': 2.0,
              'scope': {'subjects': ['input_1']}}
CLASSES = 'api_bvbrc_appservice_handoff'


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def parent_input(**changes):
    return EPISODE.read_from_parent(EPISODE.assignment_form.admit({**ASSIGNMENT, **changes}, 'test'),
                                    {'purpose': 'launch'})


def summary(**changes):
    parent = parent_input()
    value = {'assignment': parent['assignment'], 'message': parent['message'], 'record_refs': parent['record_refs'],
             'handoff_unit': 2.0, 'scope': parent['scope'], 'received_handoff_resources': [],
             'permitted': parent['permitted'], 'capabilities': None, 'lookups': [], 'launches': [],
             'handoff_refs': [], 'handoff_resources': [], 'support_refs': [], 'outcomes': [], 'progress': {},
             'controller': None, 'units_consumed': 0}
    return {**value, **changes}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == BINDING == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {'launch_api': BINDING + '/api_job_execution'}
    assert tuple(EPISODE.services) == ('job_access',)
    assert set(EPISODE.tools) == {'execution_capabilities', 'knowledge_lookup', 'launch_instruction_lookup'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_a_child():
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


def test_read_from_parent_admits_the_launch_assignment_and_derives_what_may_be_commissioned():
    parent = parent_input()
    assert parent['permitted'] == {'bvbrc': {'slot': 'launch_api', 'kind': 'api', 'yield_class': CLASSES}}
    assert parent['message'] == {'purpose': 'launch'} and parent['record_refs'] == ['input_1']
    with pytest.raises(ValueError, match='execution_no_permitted_request'):
        parent_input(constraints={'resource_id': 'nowhere'})
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        parent_input(handoff_unit=0.0)
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        parent_input(requests={'other': API_REQUEST})
    with pytest.raises(ValueError, match='invalid_execution_resource_constraints'):
        parent_input(constraints={'allowed_kinds': 'api'})
    with pytest.raises(ValueError, match='invalid_api_execution_assignment'):
        parent_input(requests={'bvbrc': {**API_REQUEST, 'endpoint': 'other'}})


def test_credit_is_the_handoff_unit_for_each_new_resource_with_a_usable_handoff_and_is_not_bounded():
    assert EPISODE.credit(summary(), None) == 0.0
    assert EPISODE.credit(summary(handoff_resources=['bvbrc']), None) == 2.0
    assert EPISODE.credit(summary(handoff_resources=['bvbrc', 'other']), None) == 4.0
    assert EPISODE.credit(summary(handoff_resources=['bvbrc'], received_handoff_resources=['bvbrc']), None) == 0.0
    tree = ast.parse((FOLDER / 'credit.py').read_text())
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not any(isinstance(node, ast.Raise) for node in ast.walk(tree)) and not {'min', 'max'} & names


def test_the_controller_is_bounded_by_the_credit_of_the_requests_still_without_a_handoff():
    settings = {'task_yield_profiles': {'launch:' + CLASSES: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}}
    controller = EPISODE.yield_controller(0.0, settings, parent_input())
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 2.0
    with pytest.raises(ValueError, match=re.escape('execution_original_task_yield_profile_required:launch:' + CLASSES)):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input())
    with pytest.raises(ValueError, match='launch_every_original_request_already_has_a_handoff'):
        EPISODE.yield_controller(0.0, settings, parent_input(received_handoff_resources=['bvbrc']))


def test_the_slot_commissions_the_chosen_request_and_selects_the_return_fields_it_wants():
    value = summary()
    api = EPISODE.msg_to_child('launch_api', {'resource_id': 'bvbrc'}, value)
    assert isinstance(api, ChildMessage)
    assert set(api.selection) == {'execution_handoff_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
                                  'bvbrc_application_outcomes'}
    assert api.assignment['input_refs'] == ['input_1'] and api.assignment['service'] == 'bvbrc_appservice'
    assert api.assignment['completion_target'] == 2.0 and api.assignment['scope'] == {'subjects': ['input_1']}
    assert api.assignment['immutable_input_versions'] == {'versions': []}
    assert api.assignment['request'] == {'application': 'rnaseq'} and api.message == {'initial_report': {}}
    with pytest.raises(ValueError, match='execution_launch_slot_unknown:nowhere'):
        EPISODE.msg_to_child('nowhere', {'resource_id': 'bvbrc'}, value)
    result = {'credit': 2.0, 'finding': {}, 'execution_handoff_refs': ['r'], 'execution_completed': True,
              'bvbrc_appservice_support_refs': ['s'], 'bvbrc_application_outcomes': []}
    assert EPISODE.read_from_child('launch_api', result, value, None) == {
        'handoff_refs': ['r'], 'completed': True, 'support_refs': ['s'], 'outcomes': [], 'credit': 2.0, 'finding': {}}


def test_the_launch_instructions_the_commissioner_pinned_reach_a_request_that_has_none():
    pinned = {'version': 'launch_instruction_selection', 'sections': []}
    value = summary()
    value['assignment'] = {**value['assignment'], 'launch_instructions': pinned}
    assert EPISODE.msg_to_child('launch_api', {'resource_id': 'bvbrc'}, value).assignment[
        'launch_instructions'] == pinned


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('execution_handoff_refs', 'execution_completed', 'execution_result_refs',
                 'bvbrc_appservice_support_refs', 'bvbrc_application_outcomes'):
        assert not form.fields[name].required


def test_the_return_carries_the_systems_credit_the_finding_and_the_selected_facts():
    value = summary(handoff_refs=['r2', 'r1'], handoff_resources=['bvbrc'], support_refs=['s1'],
                    outcomes=[{'source_ref': 'r1', 'field': 'f', 'value': {}}],
                    launches=[{'slot': 'launch_api', 'resource_id': 'bvbrc', 'handoff_refs': ['r1', 'r2'],
                               'completed': True, 'support_refs': ['s1'], 'outcomes': [], 'credit': 2.0,
                               'finding': {}}])
    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 2.0}
    selection = ('execution_handoff_refs', 'execution_completed', 'execution_result_refs',
                 'bvbrc_appservice_support_refs', 'bvbrc_application_outcomes')
    result = EPISODE.final_to_parent(value, completion, selection)
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['r1', 'r2']
    assert result['execution_completed'] is True and result['finding']['new_handoff_count'] == 1
    assert result['execution_result_refs'] == [] and result['bvbrc_appservice_support_refs'] == ['s1']
    assert result['bvbrc_application_outcomes'] == value['outcomes']
    EPISODE.return_form.admit(result, 'return')
    EPISODE.return_form.select(selection).admit(result, 'return')


def test_the_model_selection_schema_names_every_permitted_request_and_every_library_operation():
    schema = TASK._schema(summary())
    branches = schema['properties']['selection']['anyOf']
    children = [branch for branch in branches if branch['properties']['kind']['const'] == 'child']
    assert [branch['properties']['resource_id']['const'] for branch in children] == ['bvbrc']
    tools = {(branch['properties']['tool']['const'], branch['properties']['operation']['const'])
             for branch in branches if branch['properties']['kind']['const'] == 'tool'}
    assert {tool for tool, _ in tools} == {'knowledge_lookup', 'launch_instruction_lookup'}
    assert ('launch_instruction_lookup', 'launch.instructions.select') in tools
    assert TASK.generation_schema(schema)


def test_the_task_rejects_an_answer_that_selects_no_unit():
    with pytest.raises(Rejected):
        EPISODE.action({}, summary(), None, None)
