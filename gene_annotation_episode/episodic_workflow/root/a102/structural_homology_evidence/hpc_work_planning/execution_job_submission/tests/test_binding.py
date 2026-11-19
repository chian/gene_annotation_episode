"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders are other episodes and are
not read here); no module of the episode imports another episode folder; the episode's own form, continuation,
commissions and report behave on real data. Nothing here is faked and nothing contacts a remote service."""
import ast
import asyncio
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import BoundedQualityYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ExecutionJobSubmission
TASK = importlib.import_module(PACKAGE + '.task')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
CHILDREN = {'api_job_execution', 'hpc_job_execution', 'local_job_execution'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
WORKSPACE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
RESOURCE = {'kind': 'pbs_ssh', 'workspace': WORKSPACE, 'ssh_argv': ['ssh', 'alcf-bastion'],
            'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
            'scheduler': {'kind': 'pbs'}}
LOCAL = {'kind': 'local', 'workspace': WORKSPACE, 'python_executable': '/usr/bin/python3'}


def request(resource_id, kind, credit=3.0):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'job_' + resource_id, 'resource_id': resource_id,
            'resource_kind': kind, 'workspace': WORKSPACE, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['run_search', '--query', 'q'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': credit,
                                       'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


ASSIGNMENT = {'version': 'execution_launch_assignment_v1',
              'requests': {'aurora': request('aurora', 'hpc'), 'here': request('here', 'local')},
              'immutable_input_versions': [], 'constraints': {}, 'scope': {'subjects': []}, 'input_refs': [],
              'handoff_unit': 1.5}


def own_files():
    """The files of this episode: the folder without the child episode folders."""
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def parent_input(assignment=ASSIGNMENT, message=None):
    admitted = EPISODE.assignment_form.admit(assignment, 'test')
    return EPISODE.read_from_parent(admitted, {} if message is None else message)


class View:
    """The fields of the loop's view the summary reads (the loop's ``EpisodeView`` has more)."""

    def __init__(self, parent, outcomes):
        self.parent_input, self.outcomes, self.units_consumed, self.controller_state = parent, outcomes, len(outcomes), None


def summary(outcomes=(), **changes):
    parent = {**parent_input(), **changes}
    return EPISODE.internal_summary(View(parent, list(outcomes)))


def child_outcome(slot, resource_id, handoff_refs, completed):
    report = {'slot': slot, 'handoff_refs': handoff_refs, 'completed': completed, 'finding': {}}
    return {'kind': 'child', 'slot': slot, 'arguments': {'resource_id': resource_id}, 'report': report}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + child for slot, child in (
        ('launch_api', 'api_job_execution'), ('launch_local', 'local_job_execution'),
        ('launch_hpc', 'hpc_job_execution'))}
    assert tuple(EPISODE.services) == () and set(EPISODE.tools) == {'execution_capabilities'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert own_files() == FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} \
        == CHILDREN | {'messages', 'tests'}


def test_no_module_of_the_episode_imports_another_episode_folder():
    for name in sorted(FILES):
        if not name.endswith('.py'):
            continue
        for node in ast.walk(ast.parse((FOLDER / name).read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    name + ' imports ' + module


def test_the_commission_form_admits_the_old_launch_assignment_and_read_from_parent_derives_the_continuation():
    parent = parent_input()
    assert parent['eligible_resource_ids'] == ['aurora', 'here']
    assert parent['task_yield_key'] == 'launch:practical_hpc_handoff+practical_local_handoff'
    assert parent['remaining_credit'] == 3.0 and parent['request_kinds'] == {'aurora': 'hpc', 'here': 'local'}
    constrained = parent_input({**ASSIGNMENT, 'constraints': {'allowed_kinds': ['hpc']},
                                'already_handed_off_resource_ids': ['aurora']})
    assert constrained['eligible_resource_ids'] == ['aurora'] and constrained['remaining_credit'] == 0
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='invalid_execution_resource_constraints'):
        parent_input({**ASSIGNMENT, 'constraints': {'allowed_resource_ids': 'aurora'}})
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        parent_input({**ASSIGNMENT, 'requests': {'other': request('aurora', 'hpc')}})
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        parent_input({**ASSIGNMENT, 'handoff_unit': 0})


def test_an_api_request_needs_the_api_service_execution_the_library_does_not_have():
    api = {'version': 'api_execution_assignment_v1', 'service': 'ncbi_blast', 'resource_id': 'blast'}
    with pytest.raises(NotImplementedError, match='a102_api_service_execution_not_in_library'):
        parent_input({**ASSIGNMENT, 'requests': {'blast': api}})


def test_the_summary_counts_a_resource_once_and_not_the_ones_already_handed_off():
    assert summary()['new_handoff_resource_ids'] == []
    outcomes = [child_outcome('launch_hpc', 'aurora', ['ref_a'], False),
                child_outcome('launch_hpc', 'aurora', ['ref_b'], True),
                child_outcome('launch_local', 'here', [], False)]
    done = summary(outcomes)
    assert done['handed_off'] == {'aurora': ['ref_a', 'ref_b']} and done['new_handoff_resource_ids'] == ['aurora']
    assert done['completed'] is True and done['handoff_refs'] == ['ref_a', 'ref_b']
    known = summary(outcomes, already_handed_off_resource_ids=['aurora'])
    assert known['new_handoff_resource_ids'] == []


def test_credit_is_the_handoff_unit_times_the_new_resources_and_is_not_bounded():
    credit = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit(summary(), None) == 0
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source and 'min(' not in source and 'max(' not in source
    assert credit.credit.__code__.co_argcount == 2


def test_the_controller_is_the_bounded_quality_controller_capped_by_the_uncredited_requests():
    parent = parent_input()
    settings = {'task_yield_profiles': {parent['task_yield_key']:
                                        {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}}
    controller = EPISODE.yield_controller(0.0, settings, parent)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 3.0
    assert controller.cost == 0.1
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:launch:'):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent)
    none_left = parent_input({**ASSIGNMENT, 'already_handed_off_resource_ids': ['aurora', 'here']})
    with pytest.raises(ValueError, match='launch_no_uncredited_original_request'):
        EPISODE.yield_controller(0.0, settings, none_left)


def test_each_slot_commissions_its_child_with_the_request_and_the_selected_return_fields():
    done = summary()
    hpc = EPISODE.msg_to_child('launch_hpc', {'resource_id': 'aurora'}, done)
    assert hpc.assignment == ASSIGNMENT['requests']['aurora'] and hpc.selection == (
        'execution_handoff_refs', 'execution_completed')
    local = EPISODE.msg_to_child('launch_local', {'resource_id': 'here'}, done)
    assert local.assignment['record_refs'] == [] and local.assignment['resource_id'] == 'here'
    pinned = summary(launch_instructions={'library_id': 'x', 'sections': []},
                     scientific_task={'scientific_question': 'q', 'selected_tool_info': {}})
    assert EPISODE.msg_to_child('launch_hpc', {'resource_id': 'aurora'}, pinned).assignment['launch_instructions'] \
        == {'library_id': 'x', 'sections': []}
    assert EPISODE.msg_to_child('launch_local', {'resource_id': 'here'}, pinned).assignment['scientific_task'] \
        == {'scientific_question': 'q', 'selected_tool_info': {}}
    with pytest.raises(KeyError):
        EPISODE.msg_to_child('launch_hpc', {'resource_id': 'unknown'}, done)
    with pytest.raises(ValueError, match='execution_job_submission_slot_unknown:nope'):
        EPISODE.msg_to_child('nope', {'resource_id': 'aurora'}, done)


def test_read_from_child_keeps_the_handoff_the_child_returned():
    result = {'credit': 3.0, 'finding': {'x': 1}, 'execution_handoff_refs': ['ref_a'], 'execution_completed': True}
    assert EPISODE.read_from_child('launch_hpc', result, {}, None) == {
        'slot': 'launch_hpc', 'handoff_refs': ['ref_a'], 'completed': True, 'finding': {'x': 1}}


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'execution_result_origin',
                 'execution_file_source_refs', 'execution_file_capture_outcomes', *FINAL.PROTEIN_FACT_SOURCES):
        assert not form.fields[name].required
    assert len(FINAL.PROTEIN_FACT_SOURCES) == 4


def test_the_return_carries_credit_the_finding_and_every_selectable_fact_and_the_form_admits_it():
    done = summary([child_outcome('launch_hpc', 'aurora', ['ref_a'], True)])
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}
    names = tuple(name for name in EPISODE.return_form.fields if name not in ('credit', 'finding'))
    result = EPISODE.final_to_parent(done, completion, names)
    assert result['credit'] == 1.5 and result['execution_handoff_refs'] == ['ref_a']
    assert result['execution_completed'] is True and result['execution_result_origin'] == {}
    EPISODE.return_form.admit(result, 'return')


def test_the_capabilities_tool_returns_the_configured_resources_and_inventory_without_discovery():
    class Context:
        settings = {'resources': {'aurora': RESOURCE, 'here': LOCAL}, 'initial_information': {'aurora': {'queues': 1}}}

    outcome = asyncio.run(EPISODE.tools['execution_capabilities']({}, Context()))
    capabilities = outcome['result']['execution_resource_capabilities']
    assert [row['resource_id'] for row in capabilities] == ['aurora', 'here']
    assert capabilities[0]['resource_kind'] == 'hpc' and capabilities[0]['availability'] == 'unknown'
    assert capabilities[0]['tool_names'] == ['exec_command'] and capabilities[0]['inventory_snapshot'] == {'queues': 1}
    assert capabilities[1]['resource_kind'] == 'local' and capabilities[1]['inventory_snapshot'] is None
    contracts = TASK.resource_tool_contracts(Context.settings)
    names = {entry['name'] for entry in contracts}
    assert {'exec_command', 'execution.results.status'} <= names
    with pytest.raises(ValueError, match='invalid_execution_operation_arguments'):
        asyncio.run(EPISODE.tools['execution_capabilities']({'x': 1}, Context()))
    with pytest.raises(ValueError, match='initial_inventory_resource_not_bound'):
        TASK.initial_decision_context({'resources': {'here': LOCAL}, 'initial_information': {'gone': {}}})


def test_the_selection_schema_builds_its_strict_transport_and_the_resource_check_refuses_a_conflicting_request():
    schema = TASK.selection_schema(['aurora', 'here'])
    assert len(schema['properties']['selection']['anyOf']) == 2 and TASK.generation_schema(schema)
    assert len(TASK.selection_schema([])['properties']['selection']['anyOf']) == 1
    settings = {'resources': {'aurora': RESOURCE, 'here': LOCAL}, 'coordinator_workspace': '/tmp/coordinator'}
    TASK.validate_request_for_resource(settings, 'aurora', request('aurora', 'hpc'))
    with pytest.raises(ValueError, match='execution_resource_not_bound'):
        TASK.validate_request_for_resource(settings, 'missing', request('missing', 'hpc'))
    with pytest.raises(ValueError, match='execution_resource_kind_conflict'):
        TASK.validate_request_for_resource(settings, 'aurora', request('aurora', 'local'))
