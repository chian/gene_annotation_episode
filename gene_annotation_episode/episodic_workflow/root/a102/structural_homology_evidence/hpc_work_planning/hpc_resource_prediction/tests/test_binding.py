"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, controller, report and blocked ledger and service calls behave on real data. Nothing
here is faked and nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding, ToolCall
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCResourcePrediction
TASK = importlib.import_module(PACKAGE + '.task')
CREDIT = importlib.import_module(PACKAGE + '.credit')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'owner_episode_id': 'hpc_1', 'commission_id': 'static', 'ledger_refs': ['row_1', 'row_2'],
              'yield_binding': {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}
SUMMARY = {'owner_episode_id': 'hpc_1', 'episode_id': 'episode_1', 'initialized': True, 'facts': {
    'hpc_credit': 1.5, 'hpc_model_ref': 'model_a', 'hpc_accepted_obligations': [], 'hpc_result_refs': []},
    'ledger': {'hpc_credit': {'credit': 1.5, 'model_quality_improvement': 0.5,
                              'prospective_validation_credit': 0.0, 'actual_job_credit_counted_here': False}}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def admitted(**changes):
    return EPISODE.assignment_form.admit({**ASSIGNMENT, **changes}, 'test')


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
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


def test_the_commission_form_admits_the_assignment_and_read_from_parent_derives_the_inputs():
    parent_input = EPISODE.read_from_parent(admitted(), {'purpose': 'predict'})
    assert parent_input == {'owner_episode_id': 'hpc_1', 'commission_identity': {'commission_id': 'static'},
                            'ledger_refs': ['row_1', 'row_2'],
                            'yield_binding': {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}},
                            'message': {'purpose': 'predict'}}
    sourced = {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}
    source = EPISODE.assignment_form.admit({**sourced, 'commission_source_ref': ['source_1']}, 'test')
    assert EPISODE.read_from_parent(source, {})['commission_identity'] == {'commission_source_ref': 'source_1'}
    with pytest.raises(FormError):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError):
        EPISODE.assignment_form.admit({key: value for key, value in ASSIGNMENT.items() if key != 'ledger_refs'}, 'test')


def test_a_wrong_assignment_raises_where_it_is_read():
    with pytest.raises(ValueError, match='hpc_prediction_exactly_one_commission_required'):
        EPISODE.read_from_parent(admitted(commission_source_ref=['source_1']), {})
    with pytest.raises(ValueError, match='hpc_prediction_exactly_one_commission_required'):
        EPISODE.read_from_parent(EPISODE.assignment_form.admit(
            {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}, 'test'), {})
    sourced = {key: value for key, value in ASSIGNMENT.items() if key != 'commission_id'}
    two = EPISODE.assignment_form.admit({**sourced, 'commission_source_ref': ['a', 'b']}, 'test')
    with pytest.raises(ValueError, match='hpc_prediction_one_commission_source_required'):
        EPISODE.read_from_parent(two, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    for name in ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'):
        assert not fields[name].required


def test_the_controller_accumulates_with_the_commission_binding_as_its_cost():
    parent_input = EPISODE.read_from_parent(admitted(), {})
    controller = EPISODE.yield_controller(0.0, {}, parent_input)
    assert isinstance(controller, AccumulationYieldController) and controller.cost == 0.1
    with pytest.raises(KeyError):
        EPISODE.yield_controller(0.0, {}, {key: value for key, value in parent_input.items() if key != 'yield_binding'})


def test_before_the_first_unit_credit_is_zero_and_the_first_unit_is_the_initialization():
    summary = {**SUMMARY, 'initialized': False}
    assert EPISODE.credit(summary, None) == 0.0
    call = EPISODE.decide(summary, None, None)
    assert call == ToolCall('hpc_initialize', {'owner_episode_id': 'hpc_1'})


def test_credit_is_real_code_and_reaches_the_blocked_ledger_after_initialization():
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: HPC ledger evidence record'):
        EPISODE.credit(SUMMARY, None)


def test_each_ledger_and_service_primitive_names_what_it_wants_and_raises():
    for call, wanted in ((lambda: TASK.ledger_find(None, 'o', 'i'), 'HPC_LEDGER).select'),
                         (lambda: TASK.ledger_select(None, 'o', 'k'), 'HPC_LEDGER).select'),
                         (lambda: TASK.ledger_write(None, 'o', 'i', 'k', {}), 'HPC_LEDGER).put'),
                         (lambda: TASK.ledger_credits(None, 'o'), 'HPC_CREDITS).select'),
                         (lambda: TASK.ledger_write_credit(None, 'o', 's', 'k', 1.0, 'e'), 'HPC_CREDITS).put'),
                         (lambda: TASK.shared_memory_record(None), "'as_record'"),
                         (lambda: TASK.estimate_history(None, {}, now=0.0), 'history('),
                         (lambda: TASK.estimate_latest(None, 'r', 'queue'), 'latest('),
                         (lambda: TASK.estimate_observe(None, 'r', 'queue', {}, observed_at=0.0, provenance=[]),
                          'observe(')):
        with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE') as raised:
            call()
        assert wanted in str(raised.value)


def test_the_selection_schema_and_its_strict_transport_build_and_offer_the_history_tool_only_with_memory():
    names = {entry['name'] for entry in TASK.operation_catalog(False)}
    assert names == {'hpc_read', 'hpc_compare', 'hpc_discovery_run', 'hpc_candidate_propose', 'hpc_queue_observe',
                     'hpc_model_fit'}
    assert 'hpc_history_refresh' in {entry['name'] for entry in TASK.operation_catalog(True)}
    for memory in (False, True):
        schema = TASK.selection_schema(memory)
        assert TASK.generation_schema(schema)
    assert TASK.memory_configured({}) is False and TASK.memory_configured({'shared_execution_memory': {}})


def test_the_resources_need_a_pbs_ssh_resource():
    assert TASK.resources_of({'resources': {'aurora': {'kind': 'pbs_ssh', 'ssh_argv': ['ssh']}}})
    with pytest.raises(ValueError, match='explicit_hpc_resource_required'):
        TASK.resources_of({'resources': {'local': {'kind': 'local'}}})


def test_the_return_carries_credit_the_finding_and_every_selectable_fact_and_the_form_admits_it():
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.5}
    names = tuple(name for name in EPISODE.return_form.fields if name not in ('credit', 'finding'))
    result = EPISODE.final_to_parent(SUMMARY, completion, names)
    assert result['credit'] == 1.5 and result['hpc_credit'] == 1.5 and result['hpc_model_ref'] == 'model_a'
    assert result['finding']['model_quality_improvement'] == 0.5
    EPISODE.return_form.admit(result, 'return')
