"""The real episode module: its class definition checks run at import, its folder holds the ten-file set, it imports no
other episode folder, and its forms and controller functions behave as carried. No run of the real runner is made
here: a run needs the job services (``job_access``, ``estimate_table``) and the job records, which the system does not
provide yet (BLOCKED-ON-JOB-SERVICE)."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning')
FOLDER = Path(__file__).resolve().parent.parent
CHILD_FOLDERS = {'execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
                 'hpc_allocation_execution', 'hpc_resource_prediction'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').HPCEpisode


def _own_files():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or 'tests' in relative.parts or relative.parts[0] in CHILD_FOLDERS:
            continue
        yield path, relative


def test_importing_episode_runs_the_class_definition_checks():
    episode = _episode()
    assert episode.__bases__ == (EpisodeBinding,)
    assert episode.binding_path == 'partner_presence_evidence/hpc_work_planning'
    assert dict(episode.child_slots) == {
        'launch': 'partner_presence_evidence/hpc_work_planning/execution_job_submission',
        'monitor': 'partner_presence_evidence/hpc_work_planning/execution_progress_assessment',
        'results': 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition',
        'hpc_execution': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution',
        'hpc_prediction': 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'}
    assert set(episode.tools) == {'hpc_open', 'hpc_read', 'hpc_compare', 'hpc_history_refresh', 'hpc_discovery_run',
                                  'hpc_candidate_propose', 'hpc_queue_observe', 'hpc_plan', 'hpc_handoff',
                                  'hpc_monitor', 'hpc_monitor_wait', 'hpc_results', 'hpc_allocation_order'}
    assert tuple(episode.services) == ('job_access', 'estimate_table')


def test_folder_holds_exactly_the_ten_file_set():
    files = {str(relative) for _, relative in _own_files()}
    assert files == FILES


def test_no_module_imports_another_episode_folder():
    for path, relative in _own_files():
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
    for name in ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs',
                 'hpc_result_artifact_refs'):
        assert fields[name]['required'] is False


def test_assignment_form_and_read_from_parent_need_exactly_one_commission_identity():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    base = {'scope': {'subject_refs': []}}
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_id': 'c1'}, 'assignment')
    parent = module.read_from_parent(admitted, {})
    assert parent['commission_id'] == 'c1' and parent['commission_source_ref'] is None
    admitted = module.ASSIGNMENT_FORM.admit({**base, 'commission_source_ref': ['source_1']}, 'assignment')
    assert module.read_from_parent(admitted, {})['commission_source_ref'] == 'source_1'
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent(module.ASSIGNMENT_FORM.admit(base, 'assignment'), {})
    with pytest.raises(ValueError, match='exactly_one_commission_identity'):
        module.read_from_parent({**base, 'commission_id': 'c1', 'commission_source_ref': ['source_1']}, {})
    with pytest.raises(ValueError, match='exactly_one_reference'):
        module.read_from_parent({**base, 'commission_source_ref': ['source_1', 'source_2']}, {})
    with pytest.raises(FormError):
        module.ASSIGNMENT_FORM.admit({'commission_id': 'c1'}, 'assignment')


def test_yield_controller_is_the_accumulation_controller_from_the_settings():
    module = importlib.import_module(PACKAGE + '.yield_estimator')
    controller = module.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}, {})
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required'):
        module.yield_controller(0.0, {}, {})


def test_credit_is_the_ledger_credit_of_the_summary_and_zero_before_the_ledger_is_read():
    module = importlib.import_module(PACKAGE + '.credit')
    assert module.credit({'ledger_view': None}, None) == 0.0
    assert module.credit({'ledger_view': {'credit': {'credit': -2.5}}}, None) == -2.5


def test_msg_to_child_of_an_unknown_slot_raises():
    module = importlib.import_module(PACKAGE + '.messages.msg_to_child')
    with pytest.raises(LookupError):
        module.msg_to_child('wait', {}, {'ledger_view': {}})


def test_the_return_carries_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    view = {'plans': [{'closed': True}, {'closed': False}], 'commission': {'obligations': ['o1', 'o2']},
            'credit': {'components': {'actual': 1.0, 'model': 0.0, 'validation': 1.0}}}
    summary = {'ledger_view': view, 'hpc_model_ref': 'reference_model', 'hpc_accepted_obligations': ['o1'],
               'result_refs': ['source_r'], 'result_artifact_refs': ['artifact_r']}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}
    plain = final.final_to_parent(summary, completion, ())
    assert plain['credit'] == 2.0 and plain['finding']['remaining_obligations'] == ['o2']
    final.RETURN_FORM.admit(plain, 'return')
    every = tuple(sorted(name for name, field in final.RETURN_FORM.fields.items() if not field.required))
    full = final.final_to_parent(summary, completion, every)
    final.RETURN_FORM.select(every).admit(full, 'return')
    assert full['hpc_credit'] == 2.0 and full['hpc_result_artifact_refs'] == ['artifact_r']
