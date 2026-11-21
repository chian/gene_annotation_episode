"""Real checks of the A102 execution job submission binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds the ten-file set, no module imports another episode folder, and the
commission this episode builds is admitted by the real forms of its three resource children."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding, Rejected
from method_loop import FormError
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

MODULE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.'
          'execution_job_submission')
BINDING = 'structural_homology_evidence/execution_job_submission'
SLOTS = {'launch_api': BINDING + '/api_job_execution', 'launch_local': BINDING + '/local_job_execution',
         'launch_hpc': BINDING + '/hpc_job_execution'}
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
CHILDREN = ('api_job_execution', 'hpc_job_execution', 'local_job_execution')
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    """Every file of the folder outside tests and outside the child episode folders."""
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if ('__pycache__' in relative.parts or relative.parts[0] == 'tests' or relative.parts[0] in CHILDREN
                or path.is_dir()):
            continue
        found.add(relative.as_posix())
    return found


def module(name):
    return importlib.import_module(MODULE + '.' + name)


API = {'version': 'api_service_assignment_v1', 'resource_id': 'ncbi', 'service': 'ncbi_blast',
       'request': {'program': 'blastp'}, 'endpoint': 'usable_handoff', 'constraints': {}}


def practical(kind, resource_id):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'job-' + resource_id,
            'resource_id': resource_id, 'resource_kind': kind, 'workspace': '/work',
            'endpoint': 'usable_handoff', 'requested_job': {'argv': ['run', 'it'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': 1.0,
                                       'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': '/work', 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


def assignment(**changes):
    value = {'version': 'execution_launch_assignment_v1',
             'requests': {'ncbi': API, 'box': practical('local', 'box'), 'cluster': practical('hpc', 'cluster')},
             'immutable_input_versions': [], 'constraints': {}, 'scope': {'subject_refs': []},
             'input_refs': ['sub_1'], 'handoff_unit': 2.0}
    value.update(changes)
    return value


def parent_input(**changes):
    form = module('messages.read_from_parent')
    return form.read_from_parent(form.ASSIGNMENT_FORM.admit(assignment(**changes), 'assignment'), {'purpose': 'x'})


def test_the_class_passes_the_definition_checks():
    episode = module('episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = module('goal')
    assert goal.BINDING_PATH == BINDING
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == SLOTS


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


def test_the_assignment_is_read_once_and_the_continuation_derives_from_it():
    read = parent_input()
    assert read['eligible_resource_ids'] == ['box', 'cluster', 'ncbi']
    assert read['request_kinds'] == {'ncbi': 'api', 'box': 'local', 'cluster': 'hpc'}
    assert read['task_yield_key'] == 'launch:api_ncbi_blast_handoff+practical_hpc_handoff+practical_local_handoff'
    assert read['remaining_credit'] == 6.0
    constrained = parent_input(constraints={'allowed_kinds': ['hpc']}, already_handed_off_resource_ids=[])
    assert constrained['eligible_resource_ids'] == ['cluster'] and constrained['remaining_credit'] == 2.0
    form = module('messages.read_from_parent').ASSIGNMENT_FORM
    with pytest.raises(FormError):
        form.admit({name: value for name, value in assignment().items() if name != 'handoff_unit'}, 'assignment')
    with pytest.raises(ValueError):
        parent_input(requests={'wrong_id': practical('local', 'box')})


def test_the_return_declares_credit_and_finding_and_the_old_fact_sources_as_selectable():
    form = module('messages.final_to_parent').RETURN_FORM
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                 'execution_result_origin', 'execution_file_source_refs', 'execution_file_capture_outcomes'):
        assert not form.fields[name].required
    with pytest.raises(FormError):
        form.select(('credit',))


def test_the_return_carries_credit_the_finding_and_every_selectable_fact_and_the_form_admits_it():
    final = module('messages.final_to_parent')
    summary = {'commissions': [{'resource_id': 'ncbi', 'slot': 'launch_api', 'handoff_refs': ['h1'],
                                'completed': True}],
               'handed_off': ['ncbi'], 'new_handoff_resource_ids': ['ncbi'], 'handoff_refs': ['h1'],
               'completed': True}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.0}
    names = tuple(name for name in final.RETURN_FORM.fields if name not in ('credit', 'finding'))
    result = final.final_to_parent(summary, completion, names)
    assert result['credit'] == 2.0 and result['finding']['handoff_resource_ids'] == ['ncbi']
    assert result['execution_handoff_refs'] == ['h1'] and result['execution_completed'] is True
    assert result['execution_result_origin'] == {} and result['execution_result_refs'] == []
    final.RETURN_FORM.admit(result, 'return')


@pytest.mark.parametrize('slot, resource_id, child', [('launch_api', 'ncbi', 'api_job_execution'),
                                                      ('launch_local', 'box', 'local_job_execution'),
                                                      ('launch_hpc', 'cluster', 'hpc_job_execution')])
def test_each_commission_is_admitted_by_the_real_form_of_its_child(slot, resource_id, child):
    message = module('messages.msg_to_child').msg_to_child(slot, {'resource_id': resource_id}, parent_input())
    admitted = importlib.import_module(MODULE + '.' + child + '.messages.read_from_parent')
    admitted.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')
    returned = importlib.import_module(MODULE + '.' + child + '.messages.final_to_parent')
    returned.RETURN_FORM.select(message.selection)


def test_a_commission_for_the_wrong_kind_of_child_fails():
    to_child = module('messages.msg_to_child')
    with pytest.raises(KeyError):
        to_child.msg_to_child('launch_api', {'resource_id': 'box'}, parent_input())
    with pytest.raises(ValueError):
        to_child.msg_to_child('launch_other', {'resource_id': 'box'}, parent_input())


def test_the_controller_is_bounded_quality_with_the_credit_of_the_uncredited_requests():
    read = parent_input(requests={'cluster': practical('hpc', 'cluster')})
    settings = {'resources': {'cluster': {'kind': 'pbs_ssh'}},
                'task_yield_profiles': {read['task_yield_key']: {'cutoff': 0.1,
                                                                 'parameters': {'uncertainty_alpha': 0.5}}}}
    controller = module('yield_estimator').yield_controller(0.0, settings, read)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 2.0
    with pytest.raises(ValueError, match='execution_resource_not_bound'):
        module('yield_estimator').yield_controller(0.0, {**settings, 'resources': {}}, read)
    with pytest.raises(ValueError, match='execution_resource_kind_conflict'):
        module('yield_estimator').yield_controller(0.0, {**settings, 'resources': {'cluster': {'kind': 'local'}}},
                                                   read)
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        module('yield_estimator').yield_controller(0.0, {**settings, 'task_yield_profiles': {}}, read)


def test_the_local_launch_child_is_commissioned_with_the_request_alone():
    read = parent_input()
    message = module('messages.msg_to_child').msg_to_child('launch_local', {'resource_id': 'box'}, read)
    assert message.assignment == read['requests']['box']
    assert message.selection == ('execution_handoff_refs', 'execution_completed')


def test_the_answer_is_a_commission_of_a_permitted_resource():
    task = module('task')
    episode = module('episode').ExecutionJobSubmission
    assert set(episode.tools) == {'execution_capabilities'}
    assert tuple(episode.services) == ('job_access',)
    summary = parent_input()
    assert task.answer_schema(summary)['properties']['action']['properties'] == {
        'name': {'type': 'string', 'enum': ['commission_launch']},
        'resource_id': {'type': 'string', 'enum': ['box', 'cluster', 'ncbi']}}
    # The model names the resource; the slot is the resource child that owns the resource's kind.
    for resource_id, slot in (('box', 'launch_local'), ('cluster', 'launch_hpc'), ('ncbi', 'launch_api')):
        assert episode.action({'action': {'name': 'commission_launch', 'resource_id': resource_id}}, summary, None,
                              None) == ChildCall(slot, {'resource_id': resource_id})
    narrowed = task.answer_schema({**summary, 'eligible_resource_ids': ['box']})
    assert narrowed['properties']['action']['properties']['resource_id']['enum'] == ['box']
    # An answer outside the schema is rejected (no unit); the episode has no reasoning commit.
    for answer in ({}, {'action': {'name': 'commission_launch', 'resource_id': 'nowhere'}},
                   {'action': {'name': 'reason', 'kind': 'tool', 'arguments': {'commit': {'terms': []}}}}):
        with pytest.raises(Rejected):
            episode.action(answer, summary, None, None)

