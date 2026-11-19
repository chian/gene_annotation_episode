"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own form, credit, controller and return behave on real data; the missing adapter service raises where it
is reached. Nothing here is faked and nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').HpcResourceWorkExecution
TASK = importlib.import_module(PACKAGE + '.task')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SHA = 'a' * 64
SELECTION = {'resource_id': 'aurora', 'kind': 'hpc',
             'allocation': {'cpu': 1, 'memory_bytes': None, 'scratch_bytes': None},
             'capability_binding_ref': 'registry_1'}
ASSIGNMENT = {'version': 'resource_launch_assignment_v1', 'job_request': {'argv': ['search']},
              'immutable_input_versions': [{'reference': 'input_1', 'version': 'v1', 'content_sha256': SHA}],
              'constraints': {}, 'resource_selection': SELECTION, 'software_knowledge_refs': [],
              'resource_knowledge_refs': [], 'input_refs': ['input_1']}
HANDOFF = {'version': 'execution_handoff_v1', 'execution_handle': 'job_1', 'resource_selection': SELECTION,
           'submitted_input_versions': [], 'monitoring': {'provider_id': 'aurora', 'target_handle': 'job_1',
                                                          'contract_ref': 'status'},
           'results': {'provider_id': 'aurora', 'target_handle': 'job_1', 'contract_ref': 'results'},
           'checked_at': '2026-11-19T10:00:00+00:00', 'check_record_refs': [], 'state': 'usable', 'failure': None}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def summary(handoffs):
    return {'assignment': ASSIGNMENT, 'execution_handoffs': handoffs,
            'execution_handoff': handoffs[0] if len(handoffs) == 1 else None, 'handoff_refs': ['ref_1'],
            'availability': 'available', 'unavailable_checks': 0, 'calls': [], 'failed_calls': 0}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('resource_adapter',)
    assert set(EPISODE.tools) == {'resource_capabilities', 'resource_inspect', 'resource_check_handoff',
                                'adapter_tool'}


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


def test_the_commission_form_admits_one_launch_assignment_and_read_from_parent_checks_the_selection():
    admitted = EPISODE.assignment_form.admit({**ASSIGNMENT}, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'purpose': 'launch'})
    assert parent_input['assignment']['resource_selection']['resource_id'] == 'aurora'
    assert parent_input['assignment']['launch_instructions'] is None
    assert parent_input['input_refs'] == ['input_1'] and parent_input['message'] == {'purpose': 'launch'}
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        EPISODE.read_from_parent({**ASSIGNMENT, 'resource_selection': {**SELECTION, 'kind': 'local'}}, {})
    with pytest.raises(ValueError, match='explicit_resource_selection_required'):
        EPISODE.read_from_parent({**ASSIGNMENT, 'resource_selection': None}, {})


def test_credit_counts_distinct_usable_handoffs_and_the_controller_is_the_accumulation_controller():
    assert EPISODE.credit(summary([]), None) == 0.0
    assert EPISODE.credit(summary([HANDOFF]), None) == 1.0
    controller = EPISODE.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)


def test_the_return_declares_credit_and_finding_and_returns_the_selected_handoffs():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['execution_handoff'].required and not form.fields['execution_handoffs'].required
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.0}
    chosen = form.select(('execution_handoff', 'execution_handoffs'))
    result = EPISODE.final_to_parent(summary([HANDOFF]), completion, ('execution_handoff', 'execution_handoffs'))
    chosen.admit(result, 'test')
    assert result['credit'] == 1.0 and result['execution_handoff'] == HANDOFF
    assert result['finding']['usable_handoffs'] == 1 and result['handoff_refs'] == ['ref_1']
    none = EPISODE.final_to_parent(summary([]), completion, ('execution_handoff',))
    assert none['execution_handoff'] == {} and none['finding']['usable_handoffs'] == 0
    form.select(('execution_handoff',)).admit(none, 'test')


def test_the_missing_adapter_service_raises_where_it_is_reached():
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.read_adapter(None, 'capabilities')
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.resource_capabilities({}, None)


def test_the_instructions_name_only_the_offered_action_and_the_goal():
    text = TASK.instructions(knowledge=None, launch_library=None)
    assert 'Select one ordinary tool. ' in text and 'reasoning commitment' not in text.split('There are no')[0][-400:]
    assert text.endswith(importlib.import_module(PACKAGE + '.goal').GOAL)


def test_the_inspection_and_the_handoff_check_raise_where_the_adapter_service_is_missing():
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.resource_inspect({'resource_id': 'aurora'}, None)
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        import asyncio
        asyncio.run(TASK.check_adapter_handoff(ASSIGNMENT, HANDOFF, None))


CAPABILITY = {'resource_id': 'aurora', 'kind': 'hpc'}


def test_permitted_applies_the_selection_and_every_constraint():
    permitted = TASK._permitted
    assert permitted({'resource_selection': SELECTION}, CAPABILITY)
    assert not permitted({'resource_selection': {**SELECTION, 'resource_id': 'other'}}, CAPABILITY)
    assert not permitted({'resource_selection': {**SELECTION, 'kind': 'local'}}, CAPABILITY)
    assert permitted({'resource_selection': None}, CAPABILITY)
    assert not permitted({'resource_selection': SELECTION, 'constraints': {'allowed_resource_ids': ['x']}}, CAPABILITY)
    assert permitted({'resource_selection': SELECTION, 'constraints': {'allowed_kinds': ['hpc']}}, CAPABILITY)
    assert not permitted({'resource_selection': SELECTION, 'constraints': {'resource_id': 'x'}}, CAPABILITY)
    assert not permitted({'resource_selection': SELECTION, 'constraints': {'kind': 'local'}}, CAPABILITY)


def test_the_selection_schema_offers_one_branch_per_tool_of_the_catalogue():
    tools = [TASK.CAPABILITIES_TOOL, {'name': 'x.run', 'input_schema': TASK.obj({})}]
    branches = TASK.selection_schema(tools)['properties']['selection']['anyOf']
    assert [branch['properties']['tool']['const'] for branch in branches] == ['resource.capabilities', 'x.run']


def test_outcome_and_failure_shapes():
    failure = TASK._failure('resource_not_bound', ['aurora'])
    outcome = TASK._outcome(failure=failure)
    assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'resource_not_bound'
    assert TASK._outcome({'a': 1})['status'] == 'completed'
    assert TASK._availability_failure({'availability': 'unavailable'}) == 'resource_unavailable'
    assert TASK._availability_failure({'availability': 'available'}) is None


def test_decide_and_action_and_selected_capability_raise_where_the_adapter_service_is_missing():
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.decide({'assignment': ASSIGNMENT}, None, None)
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.action('{}', {'assignment': ASSIGNMENT}, None, None)
    with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapter'):
        TASK.selected_capability(None, ASSIGNMENT, [])


def test_internal_summary_reads_the_handoffs_from_the_outcomes_of_the_tools():
    from types import SimpleNamespace
    internal_summary = importlib.import_module(PACKAGE + '.messages.internal_summary').internal_summary
    capability = {'resource_id': 'aurora', 'availability': 'available'}
    units = [{'kind': 'tool', 'tool': 'resource_capabilities', 'arguments': {},
              'outcome': {'status': 'completed', 'feedback': None, 'result': {'capabilities': [capability]}}},
             {'kind': 'tool', 'tool': 'adapter_tool', 'arguments': {'tool_name': 'submit', 'tool_arguments': {}},
              'outcome': {'status': 'completed', 'feedback': None, 'reply_ref': 'ref_1',
                          'result': {'execution_handoff': HANDOFF}}},
             {'kind': 'tool', 'tool': 'resource_check_handoff', 'arguments': {},
              'outcome': {'status': 'completed', 'feedback': None, 'reply_ref': 'ref_2',
                          'result': {'execution_handoff': {**HANDOFF, 'state': 'unusable'}}}}]
    view = SimpleNamespace(parent_input={'assignment': ASSIGNMENT, 'input_refs': ['input_1'], 'message': {}},
                           outcomes=units, units_consumed=3, controller_state=None)
    result = internal_summary(view)
    assert result['availability'] == 'available' and result['unavailable_checks'] == 1
    assert result['execution_handoffs'] == [HANDOFF] and result['execution_handoff'] == HANDOFF
    assert result['handoff_refs'] == ['ref_1'] and result['failed_calls'] == 0 and len(result['calls']) == 3
