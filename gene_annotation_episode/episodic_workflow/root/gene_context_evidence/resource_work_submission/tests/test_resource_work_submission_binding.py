"""Real checks of the A103 resource work submission binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder (its
parent, its children or any other), the assignment and return forms admit what they declare, the commission of
each slot names exactly the launch fields, and the pure pieces of the episode (the action schema, the handoff
facts, the credit, the report, the controller) behave as carried. No run is made: the episode needs the
``resource_adapter`` and ``native_events`` services, which are not built."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from yield_control import CompletionYieldController

MODULE = ('gene_annotation_episode.episodic_workflow.root.gene_context_evidence.'
          'resource_work_submission')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
CHILDREN = {'launch_api': 'gene_context_evidence/resource_work_submission/api_resource_work_execution',
            'launch_local': 'gene_context_evidence/resource_work_submission/local_resource_work_execution',
            'launch_hpc': 'gene_context_evidence/resource_work_submission/hpc_resource_work_execution'}

SELECTION = {'resource_id': 'ncbi_blast', 'kind': 'api',
             'allocation': {'cpu': 1, 'memory_bytes': None, 'scratch_bytes': None},
             'capability_binding_ref': 'binding_1'}
ASSIGNMENT = {'version': 'resource_launch_assignment', 'job_request': {'search': 'blastp'},
              'immutable_input_versions': [{'reference': 'inp_1', 'version': None, 'content_sha256': None}],
              'constraints': {}, 'software_knowledge_refs': [], 'resource_knowledge_refs': [],
              'scope': {'subject_refs': ['inp_1']}, 'scope_refs': ['inp_1'], 'input_refs': ['inp_1'],
              'completion_target': 2.0}


def module(name):
    return importlib.import_module(MODULE + name)


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or path.is_dir():
            continue
        if relative.parts[0] in ('tests', 'api_resource_work_execution', 'hpc_resource_work_execution',
                                 'local_resource_work_execution'):
            continue
        found.add(relative.as_posix())
    return found


def summary(**changes):
    parent = module('.messages.read_from_parent')
    admitted = parent.ASSIGNMENT_FORM.admit(ASSIGNMENT, 'assignment')
    value = parent.read_from_parent(admitted, {'purpose': 'x'})
    return {**value, 'adapter_facts': {}, 'child_handoffs': [], 'handoff_refs': [], 'commissions': [],
            'adapter_credit': None, **changes}


def test_the_class_passes_the_definition_checks():
    episode = module('.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = module('.goal')
    assert classes[0].binding_path == goal.BINDING_PATH == 'gene_context_evidence/resource_work_submission'
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == CHILDREN


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
                        assert child.split('/')[-1] not in name, (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_is_admitted_and_read_once_by_read_from_parent():
    parent_input = summary()
    assert parent_input['assignment']['resource_selection'] is None
    assert parent_input['assignment']['launch_instructions'] is None
    assert parent_input['completion_target'] == 2.0 and parent_input['input_refs'] == ['inp_1']


def test_the_return_declares_credit_and_finding_required_and_the_old_fact_sources_selectable():
    fields = module('.messages.final_to_parent').RETURN_FORM.fields
    assert fields['credit'].required and fields['credit'].type == 'number'
    assert fields['finding'].required
    for name in ('execution_handoff', 'execution_handoffs', 'adapter_facts', 'execution_handoff_refs'):
        assert not fields[name].required


@pytest.mark.parametrize('slot', sorted(CHILDREN))
def test_each_commission_names_the_launch_fields_and_selects_the_base_facts(slot):
    to_child = module('.messages.msg_to_child')
    selection = {**SELECTION, 'kind': slot[7:]}
    arguments = {'objective': 'Investigate execution', 'resource_selection': selection, 'initial_report': {},
                 'facts': ['adapter_facts']}
    message = to_child.msg_to_child(slot, arguments, summary())
    assert isinstance(message, ChildMessage)
    assert message.assignment['resource_selection'] == selection
    assert set(message.assignment) == {'version', 'job_request', 'immutable_input_versions', 'constraints',
                                       'software_knowledge_refs', 'resource_knowledge_refs', 'resource_selection',
                                       'scope', 'scope_refs', 'input_refs', 'completion_target'}
    assert message.selection == ('execution_handoff', 'execution_handoffs', 'execution_handoff_refs',
                                 'adapter_facts')
    with pytest.raises(LookupError):
        to_child.msg_to_child('launch_other', arguments, summary())


def test_the_action_schema_offers_the_three_tools_and_the_offered_children():
    task = module('.task')
    schema = task._schema(['launch_api', 'launch_hpc'])
    branches = schema['properties']['selection']['anyOf']
    assert [branch['properties']['slot']['const'] for branch in branches
            if branch['properties']['kind']['const'] == 'child'] == ['launch_api', 'launch_hpc']
    names = [branch['properties'].get('tool', {}).get('const') for branch in branches]
    assert names[:3] == ['resource.capabilities', 'resource.inspect', 'resource.check_handoff']
    assert task.generation_schema(schema)
    assert task.generation_schema(task._schema([]))
    assert set(task.TOOLS) >= {'resource_capabilities', 'resource_inspect', 'resource_check_handoff', 'reason',
                               'wait'}


def test_the_children_are_offered_only_when_bound_with_tools_not_unavailable_and_permitted():
    task = module('.task')

    def capability(resource_id, kind, availability='available', tools=('t',)):
        return {'resource_id': resource_id, 'kind': kind, 'availability': availability, 'observed_at': 'now',
                'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': list(tools)}
    capabilities = [capability('a', 'api'), capability('l', 'local', 'unavailable'),
                    capability('h', 'hpc', tools=())]
    assert task.allowed_children({}, capabilities, {'a', 'l', 'h'}) == ['launch_api']
    assert task.allowed_children({'constraints': {'allowed_kinds': ['hpc']}}, capabilities, {'a', 'l', 'h'}) == []
    assert task.allowed_children({}, capabilities, set()) == []
    declared = task.capabilities_of(capabilities, [], {'a'})
    assert [value['tool_names'] for value in declared] == [['t'], [], []]


def test_the_handoffs_are_deduplicated_by_identity_and_a_single_one_is_the_handoff():
    final = module('.messages.final_to_parent')
    handoff = {'execution_handle': 'h1', 'resource_selection': SELECTION, 'state': 'usable'}
    facts = final.handoff_facts({'execution_handoffs': [handoff], 'extra': 3, 'none': None}, [dict(handoff)])
    assert facts['execution_handoffs'] == [handoff] and facts['execution_handoff'] == handoff
    assert facts['extra'] == 3 and facts['none'] is None
    second = {**handoff, 'execution_handle': 'h2'}
    assert final.handoff_facts({}, [handoff, second])['execution_handoff'] is None


def test_final_to_parent_returns_the_controllers_credit_and_the_selected_facts():
    final = module('.messages.final_to_parent')
    handoff = {'execution_handle': 'h1', 'resource_selection': SELECTION, 'state': 'usable'}
    state = summary(child_handoffs=[handoff], handoff_refs=['art_1'],
                    commissions=[{'slot': 'launch_api', 'finding': {}, 'usable_handoffs': [handoff]}])
    result = final.final_to_parent(state, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.25},
                                   ('execution_handoff', 'execution_handoff_refs'))
    assert result['credit'] == 1.25 and result['finding']['usable_handoffs'] == 1
    assert result['execution_handoff'] == handoff and result['execution_handoff_refs'] == ['art_1']
    assert 'execution_handoffs' not in result
    final.RETURN_FORM.select(('execution_handoff', 'execution_handoff_refs')).admit(result, 'result')


def test_every_selectable_fact_is_returned_and_the_form_admits_the_result():
    final = module('.messages.final_to_parent')
    handoff = {'execution_handle': 'h1', 'resource_selection': SELECTION, 'state': 'usable'}
    state = summary(child_handoffs=[handoff], handoff_refs=['art_1'], adapter_facts={'extra': None},
                    commissions=[{'slot': 'launch_api', 'finding': {}, 'usable_handoffs': [handoff]}])
    selection = [name for name, spec in final.RETURN_FORM.fields.items() if not spec.required]
    result = final.final_to_parent(state, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.25}, selection)
    assert result['adapter_facts'] == {'extra': None} and result['execution_handoffs'] == [handoff]
    assert final.RETURN_FORM.admit(result, 'return') == result




def test_credit_is_the_adapters_credit_unbounded():
    credit = module('.credit')
    assert credit.credit({'adapter_credit': None}, None) == 0.0
    assert credit.credit({'adapter_credit': 7.5}, None) == 7.5


def test_the_controller_is_the_completion_controller_with_the_commissioned_target():
    controller = module('.yield_estimator').yield_controller(
        0.0, {'cost': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}, {'completion_target': 2.0})
    assert isinstance(controller, CompletionYieldController)
    assert controller.target == 2.0
