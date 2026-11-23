"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders are other episodes and are
not read here); no module of the episode imports another episode folder; the episode's own form, continuation,
commissions and report behave on real data. Nothing here is faked and nothing contacts a remote service."""
import ast
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
HPC = {'kind': 'pbs_ssh', 'workspace': WORKSPACE, 'ssh_argv': ['ssh', 'alcf-bastion'],
       'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test', 'scheduler': {'kind': 'pbs'}}
LOCAL = {'kind': 'local', 'workspace': WORKSPACE, 'python_executable': '/usr/bin/python3'}


def request(resource_id, kind, credit=3.0):
    return {'version': 'practical_assignment', 'assignment_id': 'job_' + resource_id, 'resource_id': resource_id,
            'resource_kind': kind, 'workspace': WORKSPACE, 'endpoint': 'usable_handoff',
            'requested_job': {'argv': ['run_search', '--query', 'q'], 'environment': {}},
            'progress_requirements': [{'key': 'handoff', 'credit': credit,
                                       'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': WORKSPACE, 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {}}


ASSIGNMENT = {'version': 'execution_launch_assignment',
              'requests': {'aurora': request('aurora', 'hpc'), 'here': request('here', 'local')},
              'immutable_input_versions': [], 'constraints': {}, 'handoff_unit': 1.5}


def own_files():
    """The files of this episode: the folder without the child episode folders."""
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def parent_input(assignment=ASSIGNMENT, message=None):
    admitted = EPISODE.assignment_form.admit(assignment, 'test')
    return EPISODE.read_from_parent(admitted, {} if message is None else message)


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'gene_context_evidence/hpc_work_planning/execution_job_submission'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {slot: EPISODE.binding_path + '/' + child for slot, child in (
        ('launch_api', 'api_job_execution'), ('launch_local', 'local_job_execution'),
        ('launch_hpc', 'hpc_job_execution'))}
    assert tuple(EPISODE.services) == ('estimate_table', 'job_access')
    assert set(EPISODE.tools) == {'execution_capabilities'}


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
    with pytest.raises(ValueError, match='execution_request_version_unknown'):
        parent_input({**ASSIGNMENT, 'requests': {'x': {'version': 'blast_graded_request'}}})


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


def test_read_from_child_keeps_the_handoff_the_child_returned():
    result = {'credit': 3.0, 'finding': {'handoff_established': True}, 'execution_handoff_refs': ['ref_a'],
              'execution_completed': True}
    assert EPISODE.read_from_child('launch_api', result, {}, None) == {
        'slot': 'launch_api', 'handoff_refs': ['ref_a'], 'usable_handoff': True, 'completed': True,
        'child_credit': 3.0, 'finding': {'handoff_established': True}}
    refused = {**result, 'finding': {'handoff_established': False}}
    assert EPISODE.read_from_child('launch_api', refused, {}, None)['usable_handoff'] is False
    assert EPISODE.read_from_child('launch_local', {**result, 'execution_handoff_refs': []}, {}, None)[
        'usable_handoff'] is False


def test_the_return_declares_credit_and_finding_as_required_and_the_old_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'execution_result_origin',
                 'execution_blast_hsps', 'execution_blast_pairwise_result_refs', 'bvbrc_appservice_support_refs'):
        assert not form.fields[name].required
    assert all(not form.fields[name].required for name in FINAL.FIELDS)
    assert len(FINAL.FIELDS) > 20


def test_the_selection_schema_builds_its_strict_transport_and_the_resource_check_refuses_a_conflicting_request():
    schema = TASK.selection_schema(['aurora', 'here'])
    assert len(schema['properties']['selection']['anyOf']) == 2 and TASK.generation_schema(schema)
    assert len(TASK.selection_schema([])['properties']['selection']['anyOf']) == 1
    settings = {'resources': {'aurora': HPC, 'here': LOCAL}, 'coordinator_workspace': '/tmp/coordinator'}
    TASK.validate_request_for_resource(settings, 'aurora', request('aurora', 'hpc'), {})
    with pytest.raises(ValueError, match='execution_resource_not_bound'):
        TASK.validate_request_for_resource(settings, 'missing', request('missing', 'hpc'), {})
    with pytest.raises(ValueError, match='execution_resource_kind_conflict'):
        TASK.validate_request_for_resource(settings, 'aurora', request('aurora', 'local'), {})


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    summary = {'commissions': [{'resource_id': 'aurora', 'slot': 'launch_hpc', 'usable_handoff': True,
                                'completed': True}],
               'handed_off': ['aurora'], 'new_handoff_resource_ids': ['aurora'], 'handoff_refs': ['r1'],
               'completed': True}
    selection = [name for name, spec in FINAL.RETURN_FORM.fields.items() if not spec.required]
    result = FINAL.final_to_parent(summary, {'credit': 2.0}, selection)
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['r1']
    assert result['finding']['new_handoff_count'] == 1 and result['execution_result_origin'] == {}
    assert FINAL.RETURN_FORM.admit(result, 'return') == result
