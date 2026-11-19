"""The episode is a private binding in the final ten-file form: importing ``episode.py`` runs the system's class
definition checks, the folder holds exactly the ten-file set (beside its child folders and tests), no module of it
imports another episode, and its real pieces work together: the real assignment form, ``read_from_parent``, the
real commissions admitted by the real forms of the three children, the real credit and the real controller."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import EpisodeView, JsonRecord

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.'
           'hpc_allocation_execution.execution_job_submission')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = ('api_job_execution', 'hpc_job_execution', 'local_job_execution')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}


def _practical(kind, resource_id):
    return {
        'version': 'practical_assignment_v1', 'assignment_id': 'a-' + resource_id, 'resource_id': resource_id,
        'resource_kind': kind, 'workspace': '/work/job', 'endpoint': 'usable_handoff',
        'requested_job': {'argv': ['/bin/true'], 'environment': {}},
        'progress_requirements': [{'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': '/work/job', 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}


def _api(resource_id):
    return {'version': 'api_service_assignment_v1', 'resource_id': resource_id, 'service': 'ebi_hmmer',
            'request': {'sequence': 'MKV'}, 'endpoint': 'usable_handoff', 'constraints': {}}


def _assignment(handed_off=()):
    return {'version': 'execution_launch_assignment_v1',
            'requests': [_practical('local', 'workstation'), _practical('hpc', 'aurora'), _api('ebi')],
            'immutable_input_versions': {}, 'constraints': {'allowed_kinds': ['local', 'hpc', 'api']},
            'scope': {'subject_refs': []}, 'input_refs': [], 'handoff_unit': 2.0,
            'already_handed_off': list(handed_off)}


def _episode():
    return importlib.import_module(PACKAGE + '.episode').ExecutionJobSubmission


def test_the_class_passes_the_definition_checks_and_inherits_only_the_episode_type():
    episode = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    assert set(classes[0].child_slots) == {'api', 'local', 'hpc'}


def test_the_folder_holds_exactly_the_ten_file_set():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and not path.relative_to(FOLDER).parts[0] in CHILDREN
             and path.relative_to(FOLDER).parts[0] != 'tests'}
    assert found == FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    root = 'gene_annotation_episode.episodic_workflow.root'
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in path.parts or relative.parts[0] in CHILDREN:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            assert not [name for name in names if name == root or name.startswith(root + '.')], (path, names)


def test_each_commission_is_admitted_by_the_real_form_of_its_child():
    cls = _episode()
    parent = cls.read_from_parent(cls.assignment_form.admit(_assignment(), 'assignment'), {})
    summary = cls.internal_summary(_View(parent))
    for slot, resource_id, child in (('local', 'workstation', 'local_job_execution'), ('hpc', 'aurora', 'hpc_job_execution'),
                                     ('api', 'ebi', 'api_job_execution')):
        message = cls.msg_to_child(slot, {'resource_id': resource_id}, summary)
        child_cls = importlib.import_module(PACKAGE + '.' + child + '.episode')
        child_cls = next(value for value in vars(child_cls).values()
                         if isinstance(value, type) and value.__module__ == child_cls.__name__)
        child_cls.assignment_form.admit(message.assignment, 'assignment')
        child_cls.return_form.select(message.selection)


def test_a_commissioned_assignment_gives_its_bounded_controller_its_maximum_and_profile():
    from yield_control import BoundedQualityYieldController
    cls = _episode()
    parent = cls.read_from_parent(cls.assignment_form.admit(_assignment(handed_off=['aurora']), 'assignment'), {})
    assert parent['maximum_credit'] == 4.0
    assert parent['yield_class'] == 'api_ebi_hmmer_handoff+practical_hpc_handoff+practical_local_handoff'
    summary = cls.internal_summary(_View(parent))
    assert cls.credit(summary, None) == 0.0
    settings = {'task_yield_profiles': {'launch:' + parent['yield_class']:
                                        {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}}}
    controller = cls.yield_controller(0.0, settings, parent)
    assert isinstance(controller, BoundedQualityYieldController) and controller.maximum_credit == 4.0
    with pytest.raises(ValueError):
        cls.yield_controller(0.0, {'task_yield_profiles': {}}, parent)


def test_action_commissions_the_slot_of_the_selected_resource_and_rejects_anything_else():
    from episode_runtime import ChildCall, Rejected, ToolCall
    cls = _episode()
    assignment = _assignment()
    assignment['constraints'] = {'allowed_kinds': ['local', 'hpc']}
    parent = cls.read_from_parent(cls.assignment_form.admit(assignment, 'assignment'), {})
    summary = cls.internal_summary(_View(parent))
    assert cls.action({'selection': 'commission:aurora'}, summary, None, None) == ChildCall('hpc', {'resource_id': 'aurora'})
    assert cls.action({'selection': 'execution_capabilities'}, summary, None, None) == ToolCall(
        'execution_capabilities', {'resource_ids': ['workstation', 'aurora']})
    for response in ({'selection': 'commission:ebi'}, {'selection': 'stop'}, {}):
        with pytest.raises(Rejected):
            cls.action(response, summary, None, None)


def test_a_child_result_is_read_and_the_final_report_is_admitted_by_the_return_form():
    cls = _episode()
    parent = cls.read_from_parent(cls.assignment_form.admit(_assignment(), 'assignment'), {})
    result = {'credit': 2.0, 'execution_handoff_refs': ['r1'], 'execution_result_refs': [],
              'execution_completed': True, 'practical_receipt_artifact_refs': ['a1']}
    report = cls.read_from_child('local', result, None, None)
    assert report['handoff_refs'] == ['r1'] and report['artifact_refs'] == ['a1'] and report['completed']
    unit = {'kind': 'child', 'slot': 'local', 'arguments': {'resource_id': 'workstation'}, 'report': report}
    summary = cls.internal_summary(_View(parent, outcomes=[unit], units_consumed=1))
    assert summary['handed_off'] == ['workstation']
    final = cls.final_to_parent(summary, {'credit': 2.0}, ('execution_handoff_refs', 'execution_handoff_artifact_refs'))
    assert final['execution_handoff_artifact_refs'] == ['a1']
    cls.return_form.admit(final, 'result')


def _View(parent_input, outcomes=(), units_consumed=0):
    """The real ``EpisodeView`` of an Episode, built from the real method-loop pieces and the episode's own members."""
    from method_loop import EpisodeGoal, EpisodeRef, EpisodeRequest, Grain
    cls = _episode()
    goal = EpisodeGoal(objective=cls.goal, result_contract=cls.result)
    return EpisodeView(grain=Grain(cls.binding_path, cls.unit, cls.result, cls.yield_controller),
                       key='k', path=((cls.binding_path, 'k'),), units_consumed=units_consumed, updates=(),
                       controller_state=None, episode_ref=EpisodeRef('run', ((cls.binding_path, 'k'),)),
                       request=EpisodeRequest(goal=goal, message=JsonRecord({})), parent_input=parent_input,
                       outcomes=tuple(outcomes))
