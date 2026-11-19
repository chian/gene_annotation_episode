"""The real episode module: its class definition checks run at import, its folder holds the ten-file set minus the
two child files, it imports no other episode folder, and its form and controller functions behave as carried."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.'
           'hpc_resource_prediction')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').HPCResourcePrediction


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
    assert dict(episode.child_slots) == {}
    assert set(episode.tools) == {'hpc_open', 'hpc_read', 'hpc_compare', 'hpc_history_refresh', 'hpc_discovery_run',
                                  'hpc_candidate_propose', 'hpc_queue_observe', 'hpc_model_fit'}
    assert tuple(episode.services) == ('hpc_ledger', 'job_access', 'estimate_table')


def test_folder_holds_exactly_the_file_set_of_an_episode_without_children():
    files = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == FILES


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


def test_return_form_declares_credit_and_finding_required_and_the_old_facts_selectable():
    fields = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM.as_record()
    assert fields['credit']['required'] and fields['finding']['required']
    for name in ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'):
        assert fields[name]['required'] is False


def test_assignment_form_and_read_from_parent_need_exactly_one_commission_identity():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    base = {'owner_episode_id': 'episode_1', 'scope': {'subject_refs': []}}
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_id': 'c1'}, 'assignment')
    parent = module.read_from_parent(admitted, {})
    assert parent['commission_id'] == 'c1' and parent['commission_source_ref'] is None
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_source_ref': ['source_1']}, 'assignment')
    assert module.read_from_parent(admitted, {})['commission_source_ref'] == 'source_1'
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent(module.ASSIGNMENT_FORM.admit(base, 'assignment'), {})
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent({**base, 'commission_id': 'c1', 'commission_source_ref': ['source_1']}, {})
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({'owner_episode_id': 'episode_1', 'commission_id': 'c1'}, 'assignment')


def test_yield_controller_is_accumulation_and_needs_the_commission_yield_binding_in_settings():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required'):
        module.yield_controller(0.0, {}, {})


def test_the_selection_offers_the_shared_history_tool_only_with_shared_memory():
    task = importlib.import_module(PACKAGE + '.task')
    without = {entry['name'] for entry in task.catalog(False)}
    with_memory = {entry['name'] for entry in task.catalog(True)}
    assert with_memory - without == {'hpc_history_refresh'}
    assert 'hpc_open' not in with_memory
    assert len(task.selection_schema(False)['properties']['selection']['anyOf']) == len(without)


def test_the_ledger_is_not_available_without_its_service():
    task = importlib.import_module(PACKAGE + '.task')
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: hpc_ledger'):
        task._open_ledger(None, 'episode_1')


def test_the_return_carries_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    summary = {'ledger': {}, 'hpc_model_ref': 'reference_model', 'hpc_accepted_obligations': ['o1'],
               'hpc_result_refs': ['source_r'],
               'hpc_credit': {'model_quality_improvement': 0.25, 'prospective_validation_credit': 0.5},
               'hpc_available_training_ids': ['t1', 't2'], 'hpc_candidates': ['c1'], 'hpc_latest_comparison': {}}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}
    plain = final.final_to_parent(summary, completion, ())
    assert plain['credit'] == 2.0 and plain['finding']['available_training_count'] == 2
    final.RETURN_FORM.admit(plain, 'return')
    every = tuple(sorted(name for name, field in final.RETURN_FORM.fields.items() if not field.required))
    full = final.final_to_parent(summary, completion, every)
    final.RETURN_FORM.select(every).admit(full, 'return')
    assert full['hpc_result_refs'] == ['source_r']
