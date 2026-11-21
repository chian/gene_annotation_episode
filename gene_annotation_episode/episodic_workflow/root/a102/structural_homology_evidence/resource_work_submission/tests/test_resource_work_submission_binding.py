"""Real checks of the resource work submission binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set of an episode with children, no module imports another episode
folder, the assignment is read once, the return is controlled data, and the pure pieces (which resources are
launchable, the answer schema, the credit, the controller) behave as written. Nothing is faked, and nothing
contacts a remote service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

MODULE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.'
          'resource_work_submission')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
CHILDREN = {'launch_api': 'api_resource_work_execution', 'launch_local': 'local_resource_work_execution',
            'launch_hpc': 'hpc_resource_work_execution'}
ASSIGNMENT = {'version': 'resource_launch_assignment_v1', 'work_refs': ['art_work'], 'input_refs': ['art_input'],
              'allowed_kinds': ['local', 'hpc'], 'completion_target': 2.0}


def module(name):
    return importlib.import_module(MODULE + name)


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] in ('tests',) or path.is_dir():
            continue
        if relative.parts[0] in CHILDREN.values():
            continue
        found.add(relative.as_posix())
    return found


def capability(resource_id, kind, availability='available', tools=('t',)):
    return {'resource_id': resource_id, 'kind': kind, 'availability': availability, 'observed_at': 'now',
            'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': list(tools)}


def parent_input(**changes):
    from_parent = module('.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit({**ASSIGNMENT, **changes}, 'assignment'),
                                        {})


def test_the_class_passes_the_definition_checks_and_declares_the_defined_actions():
    episode = module('.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = module('.goal')
    assert classes[0].binding_path == goal.BINDING_PATH == 'structural_homology_evidence/resource_work_submission'
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {
        slot: goal.BINDING_PATH + '/' + name for slot, name in CHILDREN.items()}
    assert tuple(classes[0].services) == ('resource_adapter', 'instruction_libraries')
    assert set(classes[0].tools) == {'inspect_resource', 'check_handoff', 'knowledge_lookup',
                                     'launch_instruction_lookup'}


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
                    for child in CHILDREN.values():
                        assert child not in name, (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_is_read_once_and_splits_the_target_into_the_two_launch_units():
    assert parent_input() == {'work_ref': 'art_work', 'input_refs': ['art_input'],
                              'allowed_kinds': ['local', 'hpc'], 'resource_id': None, 'completion_target': 2.0,
                              'launch_units': {'handoff_unit': 1.0, 'check_unit': 1.0}}
    assert parent_input(resource_id='local', job_refs=['row_1'])['resource_id'] == 'local'
    form = module('.messages.read_from_parent').ASSIGNMENT_FORM
    for wrong in ({**ASSIGNMENT, 'allowed_kinds': ['cloud']}, {**ASSIGNMENT, 'job_request': {'argv': ['true']}},
                  {key: value for key, value in ASSIGNMENT.items() if key != 'work_refs'}):
        with pytest.raises(FormError):
            form.admit(wrong, 'assignment')


def test_the_return_is_controlled_data_credit_finding_and_the_job_rows():
    final = module('.messages.final_to_parent')
    fields = final.RETURN_FORM.fields
    assert {name: (spec.type, spec.required) for name, spec in fields.items()} == {
        'credit': ('number', True), 'finding': ('record', True), 'handoff_refs': ('record_refs', True),
        'check_refs': ('record_refs', False)}
    assert {name: spec.type for name, spec in final.FINDING_FORM.fields.items()} == {
        'job_state': 'text', 'route_kind': 'text'}
    with pytest.raises(FormError):
        final.FINDING_FORM.admit({'job_state': 'finished', 'route_kind': 'a model-written qualification'}, 'finding')


def test_a_resource_is_launchable_only_when_bound_with_tools_not_unavailable_and_permitted():
    task = module('.task')
    capabilities = task.capabilities_of(
        [capability('a', 'api'), capability('l', 'local', 'unavailable'), capability('h', 'hpc', tools=()),
         capability('m', 'local', 'unknown')], {})
    everything = {'a', 'l', 'h', 'm'}
    assert task.launchable(parent_input(allowed_kinds=['api', 'local', 'hpc']), capabilities, everything) == [
        'a', 'm']
    assert task.launchable(parent_input(allowed_kinds=['hpc']), capabilities, everything) == []
    assert task.launchable(parent_input(allowed_kinds=['api', 'local']), capabilities, {'m'}) == ['m']
    assert task.launchable(parent_input(allowed_kinds=['api', 'local'], resource_id='a'), capabilities,
                           everything) == ['a']
    replaced = task.capabilities_of([capability('a', 'api', 'unknown')], {'a': capability('a', 'api')})
    assert replaced['a']['availability'] == 'available'


def test_the_answer_schema_is_one_the_model_endpoint_takes_and_offers_the_launch_once():
    task = module('.task')
    capabilities = task.capabilities_of([capability('l', 'local'), capability('h', 'hpc')], {})
    before = task.answer_schema({**parent_input(), 'jobs': []}, capabilities, {'l'})
    after = task.answer_schema({**parent_input(), 'jobs': [{'handoff_ref': 'row_1'}]}, capabilities, {'l'})
    assert violations(before) == [] and violations(after) == []
    actions = [[branch['properties']['action']['enum'][0] for branch in schema['properties']['selection']['anyOf']]
               for schema in (before, after)]
    always = ['knowledge_lookup', 'launch_instruction_lookup']
    assert actions == [['inspect_resource', 'launch_work', *always], ['inspect_resource', 'check_handoff', *always]]


def test_credit_counts_the_held_handoff_and_its_usable_check_in_the_launch_units():
    credit = module('.credit').credit
    units = parent_input(completion_target=7.0)['launch_units']
    assert credit({'launch_units': units, 'handoff_held': False, 'usable_handoff_held': False}, None) == 0.0
    assert credit({'launch_units': units, 'handoff_held': True, 'usable_handoff_held': False}, None) == 3.5
    assert credit({'launch_units': units, 'handoff_held': True, 'usable_handoff_held': True}, None) == 7.0


def test_the_controller_is_the_completion_controller_with_the_commissioned_target():
    estimator = module('.yield_estimator')
    controller = estimator.yield_controller(0.0, {'cost': 0.01, 'parameters': {'uncertainty_alpha': 0.05}},
                                            parent_input())
    assert isinstance(controller, CompletionYieldController) and controller.target == 2.0
