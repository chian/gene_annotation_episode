"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children; no module of the folder imports another episode folder;
the episode's own form, credit, controller, commissions and report behave on real data. Nothing here is faked and
nothing contacts a remote service."""
import ast
import importlib
import re
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, BoundedQualityYieldController

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
BINDING = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'

API_REQUEST = {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi', 'service': 'ebi_hmmer',
               'subject_ref': 'input_1', 'algorithm': 'phmmer', 'database': 'swissprot', 'parameters': {},
               'page_size': 50, 'endpoint': 'usable_handoff', 'constraints': {}}
HPC_REQUEST = {
    'version': 'practical_assignment_v1', 'assignment_id': 'job_1', 'resource_id': 'aurora', 'resource_kind': 'hpc',
    'workspace': WORKSPACE, 'endpoint': 'usable_handoff',
    'requested_job': {'argv': ['run_search', '--query', 'q'], 'environment': {'A': 'b'}},
    'progress_requirements': [{'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
    'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
    'inventory_snapshot': {}, 'constraints': {}}
ASSIGNMENT = {'version': 'execution_launch_assignment_v1', 'requests': {'ebi': API_REQUEST, 'aurora': HPC_REQUEST},
              'immutable_input_versions': [], 'constraints': {}, 'record_refs': ['input_1'], 'handoff_unit': 2.0,
              'acquired_record_unit': 0.5}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def parent_input(**changes):
    form = EPISODE.assignment_form
    return EPISODE.read_from_parent(form.admit({**ASSIGNMENT, **changes}, 'test'), {'purpose': 'launch'})


def summary(**changes):
    parent = parent_input()
    value = {'assignment': parent['assignment'], 'message': parent['message'], 'record_refs': parent['record_refs'],
             'handoff_unit': 2.0, 'acquired_record_unit': 0.5, 'scientific_task': None,
             'received_handoff_resources': [], 'permitted': parent['permitted'], 'capabilities': None,
             'lookups': [], 'launches': [], 'handoff_refs': [], 'handoff_resources': [],
             'progress': {}, 'controller': None, 'units_consumed': 0}
    return {**value, **changes}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == BINDING == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: BINDING + '/' + child for slot, child in (
        ('launch_api', 'api_job_execution'), ('launch_hpc', 'hpc_job_execution'),
        ('launch_local', 'local_job_execution'))}
    assert tuple(EPISODE.services) == ('job_access',)
    assert set(EPISODE.tools) == {'execution_capabilities', 'knowledge_lookup', 'launch_instruction_lookup'}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES


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


def test_read_from_parent_admits_the_launch_assignment_and_derives_what_may_be_commissioned():
    parent = parent_input()
    assert parent['permitted'] == {
        'ebi': {'slot': 'launch_api', 'kind': 'api', 'yield_class': 'api_ebi_hmmer_phmmer_swissprot_handoff'},
        'aurora': {'slot': 'launch_hpc', 'kind': 'hpc', 'yield_class': 'practical_hpc_handoff'}}
    assert parent['message'] == {'purpose': 'launch'} and parent['record_refs'] == ['input_1']
    constrained = parent_input(constraints={'allowed_kinds': ['hpc']})
    assert set(constrained['permitted']) == {'aurora'}
    with pytest.raises(ValueError, match='execution_no_permitted_request'):
        parent_input(constraints={'resource_id': 'nowhere'})
    with pytest.raises(FormError, match='unknown_field'):
        EPISODE.assignment_form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        parent_input(handoff_unit=0.0)
    with pytest.raises(ValueError, match='execution_resource_identity_conflict'):
        parent_input(requests={'other': API_REQUEST})
    with pytest.raises(NotImplementedError, match='unplaced:a107_blast_execution'):
        parent_input(requests={'ncbi': {**API_REQUEST, 'resource_id': 'ncbi', 'version': 'blast_graded_v1'}})


def test_credit_is_the_handoff_unit_for_each_new_resource_with_a_usable_handoff_and_is_not_bounded():
    assert EPISODE.credit(summary(), None) == 0.0
    assert EPISODE.credit(summary(handoff_resources=['ebi']), None) == 2.0
    assert EPISODE.credit(summary(handoff_resources=['ebi', 'aurora']), None) == 4.0
    assert EPISODE.credit(summary(handoff_resources=['ebi', 'aurora'], received_handoff_resources=['ebi']),
                          None) == 2.0
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source and 'min(' not in source and 'max(' not in source


def test_the_controller_is_bounded_by_the_credit_of_the_requests_still_without_a_handoff():
    parent = parent_input()
    classes = 'api_ebi_hmmer_phmmer_swissprot_handoff+practical_hpc_handoff'
    settings = {'task_yield_profiles': {'launch:' + classes: {'cutoff': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}}}
    controller = EPISODE.yield_controller(0.0, settings, parent)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 4.0
    with pytest.raises(ValueError, match=re.escape('execution_original_task_yield_profile_required:launch:' + classes)):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent)
    received = parent_input(received_handoff_resources=['ebi', 'aurora'])
    assert isinstance(EPISODE.yield_controller(0.0, settings, received), AccumulationYieldController)
    with pytest.raises(ValueError, match='launch_no_uncredited_requests_but_nonzero_initial_credit'):
        EPISODE.yield_controller(1.0, settings, received)


def test_each_slot_commissions_the_chosen_request_and_selects_the_return_fields_it_wants():
    value = summary()
    api = EPISODE.msg_to_child('launch_api', {'resource_id': 'ebi'}, value)
    assert isinstance(api, ChildMessage) and api.selection == ()
    assert api.assignment['completion_target'] == 2.0 and api.assignment['input_refs'] == ['input_1']
    assert api.assignment['service'] == 'ebi_hmmer'
    hpc = EPISODE.msg_to_child('launch_hpc', {'resource_id': 'aurora'}, value)
    assert hpc.assignment == HPC_REQUEST
    assert hpc.selection == ('execution_handoff_refs', 'execution_completed')
    local = EPISODE.msg_to_child('launch_local', {'resource_id': 'aurora'}, value)
    assert local.assignment['record_refs'] == ['input_1']
    with pytest.raises(ValueError, match='execution_launch_slot_unknown:nowhere'):
        EPISODE.msg_to_child('nowhere', {'resource_id': 'aurora'}, value)
    assert EPISODE.read_from_child('launch_hpc', {'credit': 3.0, 'finding': {}, 'execution_handoff_refs': ['r'],
                                                  'execution_completed': True}, value, None) == {
        'handoff_refs': ['r'], 'completed': True, 'credit': 3.0, 'finding': {}}


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert form.fields['execution_handoff_refs'].required and form.fields['execution_completed'].required
    for name in ('execution_result_refs', 'execution_file_source_refs', 'execution_file_capture_outcomes',
                 'execution_result_origin', 'execution_blast_hsps', 'execution_hmmer_domain_rows',
                 'execution_nhmmer_locus_rows', 'execution_hmmalign_sequence_rows'):
        assert not form.fields[name].required
    for name in FINAL.FIELD_SOURCE:
        assert '.' not in name and not form.fields[name].required


def test_the_return_carries_the_systems_credit_the_finding_and_the_selected_facts():
    value = summary(handoff_refs=['r2', 'r1'], handoff_resources=['aurora'],
                    launches=[{'slot': 'launch_hpc', 'resource_id': 'aurora', 'handoff_refs': ['r1', 'r2'],
                               'completed': True, 'credit': 3.0, 'finding': {}}])
    completion = {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 2.0}
    selection = ('execution_result_refs', 'execution_hmmer_domain_rows')
    result = EPISODE.final_to_parent(value, completion, selection)
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['r1', 'r2']
    assert result['execution_completed'] is True and result['finding']['new_handoff_count'] == 1
    assert result['execution_result_refs'] == [] and result['execution_hmmer_domain_rows'] == []
    EPISODE.return_form.select(selection).admit(result, 'test')
    every = tuple(sorted(name for name, field in EPISODE.return_form.fields.items() if not field.required))
    full = EPISODE.final_to_parent(value, completion, every)
    EPISODE.return_form.select(every).admit(full, 'test')
    assert full['execution_result_origin'] == {} and full['bvbrc_appservice_support_refs'] == []


def test_the_model_selection_schema_names_every_permitted_request_and_both_libraries_and_its_transport_builds():
    from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
        strict_output_schema)
    schema = TASK._schema(summary())
    branches = schema['properties']['selection']['anyOf']
    assert [branch['properties']['resource_id']['const'] for branch in branches[:2]] == ['aurora', 'ebi']
    assert {branch['properties']['tool']['const'] for branch in branches[2:]} == {'knowledge_lookup',
                                                                                   'launch_instruction_lookup'}
    assert strict_output_schema(schema, open_records_as_text=True, argument_transport_error=TASK.TRANSPORT_ERROR)


