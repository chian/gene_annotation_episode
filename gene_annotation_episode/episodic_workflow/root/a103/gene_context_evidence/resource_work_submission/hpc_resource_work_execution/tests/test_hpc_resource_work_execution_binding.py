"""Real checks of the A103 HPC resource work execution binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set for an episode without children, no module
imports another episode folder, the assignment and return forms admit what they declare, and the pure pieces of
the episode (the action schema, the handoff facts, the credit, the report) behave as carried."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
          'resource_work_submission.hpc_resource_work_execution')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'

SELECTION = {'resource_id': 'aurora', 'kind': 'hpc',
             'allocation': {'cpu': 1, 'memory_bytes': None, 'scratch_bytes': None},
             'capability_binding_ref': 'binding_1'}
ASSIGNMENT = {'version': 'resource_launch_assignment', 'job_request': {'search': 'blastp'},
              'immutable_input_versions': [{'reference': 'inp_1', 'version': None, 'content_sha256': None}],
              'constraints': {}, 'resource_selection': SELECTION, 'software_knowledge_refs': [],
              'resource_knowledge_refs': [], 'scope': {'subject_refs': ['inp_1']}, 'scope_refs': ['inp_1'],
              'input_refs': ['inp_1'], 'completion_target': 1.0}


def module(name):
    return importlib.import_module(MODULE + name)


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = module('.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = module('.goal')
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


def test_the_assignment_is_admitted_and_read_once_by_read_from_parent():
    from_parent = module('.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(ASSIGNMENT, 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['assignment']['launch_instructions'] is None
    assert parent_input['assignment']['resource_selection'] == SELECTION
    assert parent_input['completion_target'] == 1.0


def test_a_selection_of_another_kind_is_refused_when_the_assignment_is_read():
    from_parent = module('.messages.read_from_parent')
    other = {**ASSIGNMENT, 'resource_selection': {**SELECTION, 'kind': 'local'}}
    admitted = from_parent.ASSIGNMENT_FORM.admit(other, 'assignment')
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        from_parent.read_from_parent(admitted, {})


def test_the_return_declares_credit_and_finding_required_and_the_old_fact_sources_selectable():
    final = module('.messages.final_to_parent')
    fields = final.RETURN_FORM.fields
    assert fields['credit'].required and fields['credit'].type == 'number'
    assert fields['finding'].required
    for name in ('execution_handoff', 'execution_handoffs'):
        assert not fields[name].required


def test_the_action_schema_is_offered_to_the_provider_transport():
    task = module('.task')
    catalog = [task.CAPABILITIES_ENTRY, {'name': 'blast.submit', 'description': 'submit',
                                         'input_schema': task.obj({'query_ref': {'type': 'string'}})}]
    schema = task._schema(catalog)
    names = [branch['properties'].get('tool', {}).get('const') for branch in schema['properties']['selection']['anyOf']]
    assert names[:2] == ['resource.capabilities', 'blast.submit']
    assert task.generation_schema(schema)


def test_the_handoffs_are_deduplicated_by_identity_and_a_single_one_is_the_handoff():
    final = module('.messages.final_to_parent')
    handoff = {'execution_handle': 'h1', 'resource_selection': SELECTION, 'state': 'usable'}
    facts = final.handoff_facts({'execution_handoffs': [handoff, dict(handoff)], 'extra': 3, 'none': None})
    assert facts['execution_handoffs'] == [handoff] and facts['execution_handoff'] == handoff
    assert facts['extra'] == 3 and facts['none'] is None
    second = {**handoff, 'execution_handle': 'h2'}
    assert final.handoff_facts({'execution_handoffs': [handoff, second]})['execution_handoff'] is None


def test_final_to_parent_returns_the_controllers_credit_and_the_selected_facts():
    final = module('.messages.final_to_parent')
    handoff = {'execution_handle': 'h1', 'resource_selection': SELECTION, 'state': 'usable'}
    summary = {'assignment': {'resource_selection': SELECTION}, 'handoff_refs': ['art_1'],
               'facts': {'execution_handoffs': [handoff]},
               'capabilities': [{'resource_id': 'aurora', 'kind': 'hpc', 'availability': 'available'}]}
    result = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.25},
                                   ('execution_handoff', 'execution_handoff_refs'))
    assert result['credit'] == 1.25 and result['finding']['usable_handoff'] is True
    assert result['execution_handoff'] == handoff and result['execution_handoff_refs'] == ['art_1']
    assert 'execution_handoffs' not in result
    everything = [name for name, spec in final.RETURN_FORM.fields.items() if not spec.required]
    full = final.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.25}, everything)
    assert full['execution_handoffs'] == [handoff] and full['adapter_facts'] == {}
    assert final.RETURN_FORM.admit(full, 'return') == full


def test_credit_is_the_adapters_credit_unbounded():
    credit = module('.credit')
    assert credit.credit({'adapter_credit': None}, None) == 0.0
    assert credit.credit({'adapter_credit': 7.5}, None) == 7.5
