"""Real checks of the A106 execution job submission binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, and
the commission and return forms are the ones the carried files declare."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.'
          'execution_job_submission')
CHILD = 'perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution'
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    """Every file of the folder outside tests and outside the child episode folder."""
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if ('__pycache__' in relative.parts or relative.parts[0] in ('tests', 'api_job_execution')
                or path.is_dir()):
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {'launch_api': CHILD}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


def test_no_module_imports_another_episode_folder():
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == MODULE or name.startswith(MODULE + '.'), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_is_read_once_and_the_return_declares_credit_and_finding():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    request = {'version': 'api_service_assignment_v1', 'resource_id': 'bvbrc', 'service': 'bvbrc_appservice',
               'request': {'application': 'RNASeq'}, 'endpoint': 'usable_handoff', 'constraints': {}}
    assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'bvbrc': request},
                  'immutable_input_versions': [], 'constraints': {}, 'scope': {}, 'input_refs': ['sub_1'],
                  'handoff_unit': 2.0}
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['eligible_resource_ids'] == ['bvbrc']
    assert parent_input['task_yield_key'] == 'launch:api_bvbrc_appservice_handoff'
    assert parent_input['remaining_credit'] == 2.0
    assert final.RETURN_FORM.fields['credit'].required and final.RETURN_FORM.fields['finding'].required
    assert not final.RETURN_FORM.fields['execution_handoff_refs'].required


def test_the_commission_selects_a_selectable_field_of_the_child():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    request = {'version': 'api_service_assignment_v1', 'resource_id': 'bvbrc', 'service': 'bvbrc_appservice',
               'request': {'application': 'RNASeq'}, 'endpoint': 'usable_handoff', 'constraints': {}}
    summary = {'requests': {'bvbrc': request}, 'launch_instructions': None, 'handoff_unit': 2.0,
               'input_refs': ['sub_1']}
    message = to_child.msg_to_child('launch_api', {'resource_id': 'bvbrc'}, summary)
    assert message.assignment['completion_target'] == 2.0
    assert message.assignment['input_refs'] == ['sub_1']
    assert 'launch_instructions' not in message.assignment
    assert message.selection == ('bvbrc_appservice_support_refs',)


def test_the_selection_schema_goes_through_the_a106_transport():
    from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
        REASONING_SCHEMA)
    task = importlib.import_module(MODULE + '.task')
    schema = task.selection_schema(['bvbrc'], REASONING_SCHEMA)
    generated = task.generation_schema(schema)
    assert generated['properties']['selection']['anyOf']
    assert len(schema['properties']['selection']['anyOf']) == 3
    assert len(task.selection_schema([], REASONING_SCHEMA)['properties']['selection']['anyOf']) == 2


def test_the_return_gives_credit_finding_and_every_selectable_fact_and_is_admitted():
    episode = importlib.import_module(MODULE + '.episode')
    cls = [value for value in vars(episode).values()
           if isinstance(value, type) and value.__module__ == episode.__name__][0]
    summary = {'commissions': [{'resource_id': 'bvbrc', 'slot': 'launch_api', 'handoff_refs': ['row_1'],
                                'support_refs': ['sup_1'], 'completed': True}],
               'handed_off': {'bvbrc': ['row_1']}, 'new_handoff_resource_ids': ['bvbrc'], 'handoff_refs': ['row_1'],
               'support_refs': ['sup_1'], 'completed': True}
    selection = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                 'bvbrc_appservice_support_refs', 'bvbrc_application_outcomes')
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.0}, selection)
    assert result['credit'] == 2.0 and result['finding']['handoff_resource_ids'] == ['bvbrc']
    assert result['execution_handoff_refs'] == ['row_1'] and result['execution_result_refs'] == []
    assert result['execution_completed'] is True and result['bvbrc_appservice_support_refs'] == ['sup_1']
    assert result['bvbrc_application_outcomes'] == []
    cls.return_form.admit(result, 'return')
    cls.return_form.select(selection).admit(result, 'return')
