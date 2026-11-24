"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, controller, report and blocked ledger behave on real data. Nothing here is faked and
nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HpcResourcePrediction
TASK = importlib.import_module(PACKAGE + '.task')
CREDIT = importlib.import_module(PACKAGE + '.credit')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SETTINGS = {'commissions': {'c1': {'yield_bindings': {'hpc_prediction': {
    'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.5}}}}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == 'gene_context_evidence/hpc_work_planning/hpc_resource_prediction'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('job_access', 'estimate_table')
    assert set(EPISODE.tools) == {'hpc_initialize', 'hpc_read', 'hpc_compare', 'hpc_history_refresh',
                                  'hpc_discovery_run', 'hpc_candidate_propose', 'hpc_queue_observe',
                                  'hpc_model_fit'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_without_children():
    assert files() == FILES
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_assignment_form_admits_one_commission_identity_and_read_from_parent_reads_it():
    form = EPISODE.assignment_form
    admitted = form.admit({'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1', 'commission_id': 'c1'}, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {})
    assert parent_input == {'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1', 'commission_identity': {'commission_id': 'c1'},
                            'launch_instructions': None}
    by_ref = form.admit({'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1', 'commission_source_ref': ['source_1']}, 'test')
    assert EPISODE.read_from_parent(by_ref, {'launch_instructions': {'sections': []}})[
        'commission_identity'] == {'commission_source_ref': 'source_1'}
    with pytest.raises(FormError):
        form.admit({'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1', 'commission_id': 'c1', 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='exactly_one'):
        EPISODE.read_from_parent(form.admit({'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1'}, 'test'), {})
    with pytest.raises(ValueError, match='exactly_one'):
        EPISODE.read_from_parent(form.admit({'ledger': 'hpc_ledger_1', 'owner_episode_id': 'hpc_1', 'commission_id': 'c1',
                                             'commission_source_ref': ['source_1']}, 'test'), {})


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'):
        assert not form.fields[name].required


def test_the_credit_is_the_scaled_quality_gain_plus_the_validation_credit_and_is_signed_and_unbounded():
    inputs = {'model_scale': 4.0, 'entry_quality': 0.25, 'current_quality': 0.75,
              'prospective_validation_credit': 0.5}
    assert CREDIT.credit({'credit_inputs': None}, None) == 0.0
    assert CREDIT.credit({'credit_inputs': inputs}, None) == 4.0 * 0.5 + 0.5
    assert CREDIT.credit({'credit_inputs': {**inputs, 'current_quality': -2.25}}, None) == 4.0 * -2.5 + 0.5
    assert CREDIT.credit({'credit_inputs': {**inputs, 'current_quality': None}}, None) == 0.5
    assert CREDIT.credit({'credit_inputs': {**inputs, 'entry_quality': None}}, None) == 0.5


def test_the_controller_is_the_accumulation_controller_the_commission_binds_and_fails_without_a_binding():
    identity = {'commission_id': 'c1'}
    controller = EPISODE.yield_controller(0.0, SETTINGS, {'commission_identity': identity})
    assert isinstance(controller, AccumulationYieldController) and controller.cost == 0.01
    with pytest.raises(ValueError, match='hpc_commission_yield_binding_required'):
        EPISODE.yield_controller(0.0, {'commissions': {'c1': {}}}, {'commission_identity': identity})
    with pytest.raises(NotImplementedError, match='commission_source_ref'):
        EPISODE.yield_controller(0.0, SETTINGS, {'commission_identity': {'commission_source_ref': 's'}})


def test_the_report_returns_the_selected_facts_and_checks_them_against_the_recorded_evidence():
    summary = {'ledger': {'hpc_model_ref': 'model_a', 'hpc_model_refs': ['reference_model', 'model_a'],
                          'hpc_accepted_obligations': ['o1']},
               'credit_inputs': {'entry_quality': 0.25, 'current_quality': None, 'prospective_validation_credit': 0.5,
                                 'model_scale': 4.0},
               'hpc_credit': {'model_quality_improvement': 0.0}, 'hpc_result_refs': ['source_1']}
    result = FINAL.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 0.5},
                                   ('hpc_credit', 'hpc_model_ref'))
    assert result == {'credit': 0.5, 'finding': {
        'model_ref': 'model_a', 'model_quality_improvement': 0.0, 'prospective_validation_credit': 0.5,
        'actual_job_credit_counted_here': False, 'entry_quality': 0.25}, 'hpc_credit': 0.5,
        'hpc_model_ref': 'model_a'}
    assert set(EPISODE.return_form.select(('hpc_credit', 'hpc_model_ref')).fields) >= set(result)
    everything = ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')
    full = FINAL.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 0.5}, everything)
    assert full['hpc_result_refs'] == ['source_1'] and FINAL.RETURN_FORM.admit(full, 'return') == full


def test_the_ledger_is_blocked_on_the_job_service_and_raises_where_it_is_opened():
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: hpc_ledger'):
        TASK.open_ledger(None, 'hpc_1')
