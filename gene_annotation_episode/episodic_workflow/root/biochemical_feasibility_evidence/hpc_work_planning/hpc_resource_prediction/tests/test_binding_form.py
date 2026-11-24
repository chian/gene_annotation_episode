"""The real episode module: its class definition checks run at import, its folder holds the ten-file set (no
children, so no ``msg_to_child.py`` and no ``read_from_child.py``), it imports no other episode folder, and its
form, controller, credit and report functions behave as carried. Nothing here is faked. The tools reach the
ledger (a work table under custody) and the missing job services (BLOCKED-ON-JOB-SERVICE), so they are not run here."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.biochemical_feasibility_evidence.'
           'hpc_work_planning.hpc_resource_prediction')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').HpcResourcePrediction


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction'
    assert dict(episode.child_slots) == {}
    assert set(episode.tools) == {'hpc_read', 'hpc_compare', 'hpc_history_refresh', 'hpc_discovery_run',
                                  'hpc_candidate_propose', 'hpc_queue_observe', 'hpc_model_fit'}
    assert tuple(episode.services) == ('job_access', 'estimate_table')
    assert not hasattr(episode, 'msg_to_child') and not hasattr(episode, 'read_from_child')


def test_folder_holds_exactly_the_ten_file_set():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts:
            continue
        depth = len(relative.parts)  # a relative import of this level or deeper leaves the folder
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                if node.level >= depth + 1:
                    raise AssertionError(str(relative) + ' imports outside its folder')
                names = [node.module or '']
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                assert not name.startswith('gene_annotation_episode.episodic_workflow.root'), (relative, name)


def test_return_form_declares_credit_and_finding_required_and_two_facts_selectable():
    form = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM.as_record()
    fields = form['fields'] if 'fields' in form else form
    assert fields['credit']['required'] and fields['finding']['required']
    assert fields['credit']['type'] == 'number'
    for name in ('hpc_model_ref', 'hpc_result_refs', 'hpc_ledger_refs'):
        assert fields[name]['required']
    for name in ('hpc_credit', 'hpc_accepted_obligations'):
        assert fields[name]['required'] is False


def test_assignment_form_and_reading_of_the_assignment():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    assignment = {'owner_episode_id': 'ep_1', 'commission_id': 'c1', 'ledger_refs': ['row_a', 'row_b']}
    admitted = module.ASSIGNMENT_FORM.admit(assignment, 'assignment')
    parent_input = module.read_from_parent(admitted, {'launch_instructions': None})
    assert parent_input == {'owner_episode_id': 'ep_1', 'commission_id': 'c1', 'ledger_refs': ['row_a', 'row_b'],
                            'launch_instructions': None}
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({**assignment, 'unknown': 1}, 'assignment')
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({'owner_episode_id': 'ep_1', 'commission_id': 'c1'}, 'assignment')
    with pytest.raises(ValueError, match='requires_exactly_one_of_commission_id_or_commission_source_ref'):
        module.read_from_parent({'owner_episode_id': 'ep_1', 'ledger_refs': []}, {})
    with pytest.raises(ValueError, match='requires_exactly_one_of_commission_id_or_commission_source_ref'):
        module.read_from_parent({'owner_episode_id': 'ep_1', 'commission_id': 'c', 'commission_source_ref': 'r',
                                 'ledger_refs': []}, {})


def test_yield_controller_is_accumulation_and_needs_the_commission_yield_binding_values():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required:hpc_prediction'):
        module.yield_controller(0.0, {}, {})
    with pytest.raises(ValueError, match='explicit_hpc_commission_yield_binding_required:hpc_prediction'):
        module.yield_controller(0.0, {'cost': 0.0, 'parameters': {}}, {})


def test_credit_is_the_scaled_quality_gain_plus_prospective_validation_credit_and_is_not_bounded():
    module = importlib.import_module(PACKAGE + '.credit')
    summary = {'model_scale': 2.0, 'model_quality_improvement': -3.5, 'prospective_validation_credit': 0.25}
    assert module.credit(summary, None) == -6.75
    assert module.quality_improvement(None, 1.0) == 0. and module.quality_improvement(1.0, None) == 0.
    assert module.quality_improvement(-2.0, -0.5) == 1.5
    with pytest.raises(ValueError, match='finite_hpc_prediction_credit_required'):
        module.credit({**summary, 'model_quality_improvement': float('inf')}, None)


def test_the_return_carries_the_finding_and_each_selectable_field_and_is_admitted_by_the_form():
    module = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'model_ref': 'model_7', 'entry_model_ref': 'reference_model', 'entry_quality': -2.0,
               'model_quality': -0.5, 'model_quality_improvement': 1.5, 'prospective_validation_credit': 0.25,
               'training_ids': ['case_1', 'case_2'], 'accepted_obligations': ['obligation_1'],
               'result_source_refs': ['src_1'], 'produced_refs': ['ledger_1', 'ledger_2']}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 4, 'credit': 3.25}
    result = module.final_to_parent(summary, completion, ('hpc_credit', 'hpc_accepted_obligations'))
    assert result['credit'] == 3.25 and result['hpc_credit'] == 3.25
    assert result['hpc_accepted_obligations'] == ['obligation_1'] and result['hpc_model_ref'] == 'model_7'
    assert result['finding']['validation_quality'] == -0.5 and result['hpc_ledger_refs'] == ['ledger_1', 'ledger_2']
    module.RETURN_FORM.admit(result, 'return')
    bare = module.final_to_parent({**summary, 'entry_quality': None, 'model_quality': None}, completion, ())
    module.RETURN_FORM.admit(bare, 'return')
