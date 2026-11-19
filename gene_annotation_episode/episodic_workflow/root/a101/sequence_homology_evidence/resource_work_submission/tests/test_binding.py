"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children; no module of the folder imports another episode folder;
the episode's own form, messages, credit, controller and return behave on real data; the missing resource adapter
service raises where it is reached. Nothing here is faked and nothing contacts a remote service. The child
episodes are not imported (a commission is the child's own form's business; this test does not look at it)."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ResourceWorkSubmission
TASK = importlib.import_module(PACKAGE + '.task')
MESSAGES = importlib.import_module(PACKAGE + '.messages.msg_to_child')
FROM_CHILD = importlib.import_module(PACKAGE + '.messages.read_from_child')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
CHILDREN = ('api_resource_work_execution', 'hpc_resource_work_execution', 'local_resource_work_execution')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SHA = 'a' * 64
SELECTION = {'resource_id': 'aurora', 'kind': 'hpc',
             'allocation': {'cpu': 1, 'memory_bytes': None, 'scratch_bytes': None},
             'capability_binding_ref': 'registry_1'}
ASSIGNMENT = {'version': 'resource_launch_assignment_v1', 'job_request': {'argv': ['search']},
              'immutable_input_versions': [{'reference': 'input_1', 'version': 'v1', 'content_sha256': SHA}],
              'constraints': {}, 'software_knowledge_refs': [], 'resource_knowledge_refs': [],
              'scope': {'subject_refs': ['subject_1']}, 'scope_refs': ['subject_1'], 'input_refs': ['input_1'],
              'completion_target': 2.0}
HANDOFF = {'version': 'execution_handoff_v1', 'execution_handle': 'job_1', 'resource_selection': SELECTION,
           'submitted_input_versions': [], 'monitoring': {'provider_id': 'aurora', 'target_handle': 'job_1',
                                                          'contract_ref': 'status'},
           'results': {'provider_id': 'aurora', 'target_handle': 'job_1', 'contract_ref': 'results'},
           'checked_at': '2026-11-19T10:00:00+00:00', 'check_record_refs': [], 'state': 'usable', 'failure': None}
CAPABILITY = {'resource_id': 'aurora', 'kind': 'hpc', 'availability': 'available',
              'observed_at': '2026-11-19T10:00:00+00:00', 'provenance_refs': [], 'knowledge_entry_ids': [],
              'tool_names': ['hpc.submit']}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def parent_input(**changes):
    assignment = {**{name: value for name, value in ASSIGNMENT.items()
                     if name not in ('scope', 'scope_refs', 'input_refs', 'completion_target')},
                  'resource_selection': None, 'launch_instructions': None}
    return {'assignment': {**assignment, **changes}, 'scope': ASSIGNMENT['scope'], 'scope_refs': ['subject_1'],
            'input_refs': ['input_1'], 'completion_target': 2.0, 'message': {}}


def summary(handoffs=(), **changes):
    value = {**parent_input(), 'role': 'launch', 'capabilities': None, 'calls': [], 'commissions': [],
             'reasonings': [], 'last_outcome': None, 'execution_handoffs': list(handoffs),
             'execution_handoff': handoffs[0] if len(handoffs) == 1 else None, 'handoff_refs': ['ref_1'],
             'adapter_facts': {}, 'unavailable_checks': 0, 'units_consumed': 0, 'action_yields': None,
             'reasoning_schema': {'type': 'object', 'properties': {'terms': {'type': 'array'}},
                                  'required': ['terms'], 'additionalProperties': False}}
    value.update(changes)
    return value


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == 'sequence_homology_evidence/resource_work_submission'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {
        'launch_api': EPISODE.binding_path + '/api_resource_work_execution',
        'launch_hpc': EPISODE.binding_path + '/hpc_resource_work_execution',
        'launch_local': EPISODE.binding_path + '/local_resource_work_execution'}
    assert tuple(EPISODE.services) == ('resource_adapters',)
    assert set(EPISODE.tools) == {'resource_capabilities', 'resource_inspect', 'resource_check_handoff', 'reason',
                                  'knowledge_lookup', 'launch_instruction_lookup'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child / 'episode.py').is_file()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if path.relative_to(FOLDER).parts[0] in CHILDREN:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module
                assert not (module.startswith(PACKAGE + '.') and module.split('.')[len(PACKAGE.split('.'))] in CHILDREN)


def test_the_commission_form_admits_one_launch_assignment_and_read_from_parent_reads_it():
    admitted = EPISODE.assignment_form.admit({**ASSIGNMENT}, 'test')
    read = EPISODE.read_from_parent(admitted, {'purpose': 'launch'})
    assert read['assignment']['resource_selection'] is None and read['assignment']['launch_instructions'] is None
    assert read['scope_refs'] == ['subject_1'] and read['input_refs'] == ['input_1']
    assert read['completion_target'] == 2.0 and read['message'] == {'purpose': 'launch'}
    chosen = EPISODE.read_from_parent({**admitted, 'resource_selection': SELECTION}, {})
    assert chosen['assignment']['resource_selection'] == SELECTION
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        EPISODE.read_from_parent({**ASSIGNMENT, 'completion_target': 0}, {})


def test_credit_counts_distinct_usable_handoffs_in_the_commissioned_unit_and_the_controller_accumulates():
    assert EPISODE.credit(summary(), None) == 0.0
    assert EPISODE.credit(summary([HANDOFF]), None) == 2.0
    controller = EPISODE.yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}, {})
    assert isinstance(controller, AccumulationYieldController)


def test_the_commission_of_each_slot_states_its_assignment_message_and_selection():
    chosen = {'resource_selection': SELECTION, 'launch_instructions': None}
    api = EPISODE.msg_to_child('launch_api', chosen, summary())
    assert isinstance(api, ChildMessage)
    assert api.assignment['resource_selection'] == SELECTION and 'launch_instructions' not in api.assignment
    assert api.assignment['scope_refs'] == ['subject_1'] and api.assignment['input_refs'] == ['input_1']
    assert api.assignment['completion_target'] == 2.0 and api.message == {'scope': ASSIGNMENT['scope']}
    assert set(api.selection) == {'execution_handoff', 'execution_handoffs', 'adapter_facts',
                                  'execution_handoff_refs'}
    hpc = EPISODE.msg_to_child('launch_hpc', chosen, summary())
    assert hpc.assignment['input_refs'] == ['input_1'] and 'scope' not in hpc.assignment
    assert set(hpc.selection) == {'execution_handoff', 'execution_handoffs'}
    pins = {'library_id': 'library', 'sections': []}
    local = EPISODE.msg_to_child('launch_local', {**chosen, 'launch_instructions': pins}, summary())
    assert 'input_refs' not in local.assignment and local.assignment['launch_instructions'] == pins
    assert local.message == {'scope': ASSIGNMENT['scope']}
    with pytest.raises(KeyError):
        EPISODE.msg_to_child('launch_unknown', chosen, summary())


def test_read_from_child_reads_every_shape_the_children_return():
    api = {'credit': 2.0, 'finding': {}, 'execution_handoff': HANDOFF, 'execution_handoffs': [HANDOFF],
           'adapter_facts': {'x': 1}, 'execution_handoff_refs': ['ref_1']}
    assert FROM_CHILD.read_from_child('launch_api', api, summary(), None) == {
        'slot': 'launch_api', 'credit': 2.0, 'finding': {}, 'execution_handoffs': [HANDOFF],
        'adapter_facts': {'x': 1}, 'handoff_refs': ['ref_1']}
    hpc = {'credit': 0.0, 'finding': {}, 'handoff_refs': ['ref_2'], 'execution_handoff': {}, 'execution_handoffs': []}
    assert FROM_CHILD.read_from_child('launch_hpc', hpc, summary(), None)['handoff_refs'] == ['ref_2']
    local = {'credit': 0.0, 'finding': {}, 'execution_handoff': [], 'execution_handoffs': []}
    assert FROM_CHILD.read_from_child('launch_local', local, summary(), None)['handoff_refs'] == []


def test_the_return_declares_credit_and_finding_and_returns_the_selected_facts():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert all(not form.fields[name].required for name in ('execution_handoff', 'execution_handoffs',
                                                           'adapter_facts', 'execution_handoff_refs'))
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}
    names = ('execution_handoff', 'execution_handoffs', 'adapter_facts', 'execution_handoff_refs')
    value = summary([HANDOFF], capabilities=[CAPABILITY],
                    commissions=[{'index': 0, 'slot': 'launch_hpc', 'resource_id': 'aurora', 'credit': 2.0,
                                  'finding': {}, 'handoff_count': 1}])
    result = EPISODE.final_to_parent(value, completion, names)
    form.select(names).admit(result, 'test')
    assert result['credit'] == 2.0 and result['execution_handoff'] == HANDOFF
    assert result['finding']['usable_handoffs'] == 1 and result['execution_handoff_refs'] == ['ref_1']
    assert result['finding']['resource_availability'][0]['availability'] == 'available'
    none = EPISODE.final_to_parent(summary(), completion, ('execution_handoff',))
    assert none['execution_handoff'] == {} and none['finding']['usable_handoffs'] == 0
    form.select(('execution_handoff',)).admit(none, 'test')
    form.admit(EPISODE.final_to_parent(value, completion, ()), 'return')
    form.admit(result, 'return')


def test_the_missing_adapter_service_raises_where_it_is_reached():
    for call in (lambda: TASK.read_adapters(None, 'bound_resource_ids'), lambda: TASK.adapters(None),
                 lambda: TASK.decide(summary(), None, None), lambda: TASK.action({}, summary(), None, None),
                 lambda: TASK.resource_capabilities({}, None), lambda: TASK.resource_inspect(
                     {'resource_id': 'aurora'}, None)):
        with pytest.raises(NotImplementedError, match='BLOCKED-ON-JOB-SERVICE: resource_adapters'):
            call()


def test_the_old_capability_rules_are_kept():
    unbound = {**CAPABILITY, 'resource_id': 'other'}
    values = TASK.capabilities_of([CAPABILITY, unbound], {'aurora': CAPABILITY}, {'aurora'})
    assert [value['tool_names'] for value in values] == [['hpc.submit'], []]
    with pytest.raises(ValueError, match='resource_capability_identity_mismatch'):
        TASK.capabilities_of([], {'other': CAPABILITY}, {'aurora'})
    assert TASK.allowed_slots(summary()['assignment'], values, {'aurora'}) == ['launch_hpc']
    assert TASK.allowed_slots({**summary()['assignment'], 'constraints': {'allowed_kinds': ['api']}}, values,
                              {'aurora'}) == []
    assert TASK.allowed_slots(summary()['assignment'], [{**CAPABILITY, 'availability': 'unavailable'}],
                              {'aurora'}) == []


def test_the_model_answer_is_checked_against_the_assignment_before_a_commission_is_made():
    assignment = {**summary()['assignment'], 'resource_selection': SELECTION,
                  'launch_instructions': None}
    chosen = {'role': 'launch_hpc', 'assignment': {'resource_selection': SELECTION, 'launch_instructions': None}}
    TASK.check_child_selection(chosen, assignment, [CAPABILITY], ['launch_hpc'])
    with pytest.raises(ValueError, match='child_role_not_available_to_parent'):
        TASK.check_child_selection(chosen, assignment, [CAPABILITY], [])
    other = {**chosen, 'assignment': {'resource_selection': {**SELECTION, 'resource_id': 'other'},
                                      'launch_instructions': None}}
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        TASK.check_child_selection(other, assignment, [CAPABILITY], ['launch_hpc'])
    pinned = {**assignment, 'launch_instructions': {
        'version': 'launch_instruction_selection_v1', 'library_id': 'launch_instructions_' + SHA,
        'sections': [{'entry_id': 'entry', 'section_id': 'section', 'sha256': SHA}]}}
    with pytest.raises(ValueError, match='launch_instruction_inheritance_conflict'):
        TASK.check_child_selection(chosen, pinned, [CAPABILITY], ['launch_hpc'])


def test_the_answer_schema_offers_the_tools_the_reasoning_commit_and_only_the_allowed_children():
    commit = summary()['reasoning_schema']
    branches = TASK.selection_schema(commit, ['launch_hpc'], [])['properties']['selection']['anyOf']
    kinds = [branch['properties']['kind']['const'] for branch in branches]
    assert kinds == ['tool', 'tool', 'tool', 'reason', 'episode_child']
    assert branches[-1]['properties']['role']['enum'] == ['launch_hpc']
    assert 'episode_child' not in [branch['properties']['kind']['const'] for branch in
                                   TASK.selection_schema(commit, [], [])['properties']['selection']['anyOf']]
    assert TASK.empty_commit({'commit': {'terms': []}}, commit)
    assert not TASK.empty_commit({'commit': {'terms': []}, 'evidence_processing': {'kind': 'no_applicable_evidence'}},
                                 commit)
    assert TASK.named_refs({'terms': [{'source_ref': 'a', 'x_refs': ['b', '@c'], 'alias_ref': '@d'}]}) == ['a', 'b']


def test_the_instructions_name_the_goal_and_the_reasoning_requirement():
    text = TASK.instructions(knowledge=None, launch_library=None)
    assert 'A commissioned child returns ONLY' not in text and TASK.HISTORY in text
    assert TASK.GOAL in text and 'A common scientific reason action needs at least one proposed commit row' in text
