"""Real checks of the result acquisition binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set (no children, so no ``msg_to_child.py`` or
``read_from_child.py``), no module imports another episode folder, the commission forms admit the old assignment,
the controller is one of the three, and the blocked handoff read raises where it is reached."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from yield_control import AccumulationYieldController

MODULE = ('gene_annotation_episode.episodic_workflow.root.perturbation_evidence.'
          'execution_result_acquisition')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
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
    assert goal.BINDING_PATH == ('perturbation_evidence/'
                                 'execution_result_acquisition')
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {}


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


def test_the_assignment_admits_the_old_assignment_and_the_return_declares_credit_and_finding():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    assignment = {'version': 'execution_results_assignment', 'handoff_ref': ['row_1'],
                  'selector': {'version': '1'}, 'service': 'bvbrc_appservice'}
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['handoff_ref'] == 'row_1'
    assert parent_input['selector'] == {'version': '1'}
    assert final.RETURN_FORM.fields['credit'].required and final.RETURN_FORM.fields['finding'].required
    assert final.RETURN_FORM.fields['execution_result_refs'].required
    assert not final.RETURN_FORM.fields['execution_handoff_refs'].required
    with pytest.raises(ValueError, match='execution_results_one_handoff_required'):
        from_parent.read_from_parent({**admitted, 'handoff_ref': ['row_1', 'row_2']}, {})


def test_the_controller_is_the_accumulation_controller_of_the_old_profile_key():
    estimator = importlib.import_module(MODULE + '.yield_estimator')
    parent_input = {'selector': {'version': '1'}, 'service': 'bvbrc_appservice'}
    key = 'results:api_bvbrc_appservice_1'
    assert estimator.yield_key(parent_input) == key
    settings = {'task_yield_profiles': {key: {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}}}
    assert isinstance(estimator.yield_controller(0.0, settings, parent_input), AccumulationYieldController)
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        estimator.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_credit_counts_new_handoff_and_result_identities_only():
    credit = importlib.import_module(MODULE + '.credit').credit
    units = {'handoff_unit': 2.0, 'acquired_record_unit': 3.0}
    base = {'credit_units': units, 'initial_handoff_identities': ['h0'], 'handoff_identities': ['h0'],
            'result_identities': []}
    assert credit({**base, 'credit_units': None}, None) == 0.0
    assert credit(base, None) == 0.0
    assert credit({**base, 'result_identities': ['r1', 'r2']}, None) == 6.0
    assert credit({**base, 'handoff_identities': ['h0', 'h1'], 'result_identities': ['r1']}, None) == 5.0


def test_the_handoff_read_is_blocked_on_the_job_ledger():
    task = importlib.import_module(MODULE + '.task')
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE'):
        task.handoff_target('row_1', None)


def test_the_return_gives_credit_finding_the_acquired_results_and_every_selectable_fact():
    episode = importlib.import_module(MODULE + '.episode')
    cls = [value for value in vars(episode).values()
           if isinstance(value, type) and value.__module__ == episode.__name__][0]
    summary = {'handoff_ref': 'row_1', 'result_refs': ['res_1', 'res_2'], 'execution_completed': True,
               'facts_by_source': {'execution_handoff_refs': ['row_1'], 'execution_result_refs': ['res_1', 'res_2'],
                                   'bvbrc_appservice_support_refs': ['sup_1'], 'execution_completed': True,
                                   'bvbrc_application_outcomes': []}}
    selection = ('execution_handoff_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
                 'bvbrc_application_outcomes')
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 4.0}, selection)
    assert result['credit'] == 4.0 and result['finding']['results_acquired'] == 2
    assert result['execution_result_refs'] == ['res_1', 'res_2'] and result['execution_completed'] is True
    assert result['bvbrc_appservice_support_refs'] == ['sup_1'] and result['bvbrc_application_outcomes'] == []
    cls.return_form.admit(result, 'return')
    cls.return_form.select(selection).admit(result, 'return')
