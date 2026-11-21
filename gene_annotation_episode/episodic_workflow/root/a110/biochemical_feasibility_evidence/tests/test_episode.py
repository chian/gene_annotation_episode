"""The A110 head (biochemical_feasibility_evidence) is a private binding in the ten-file form: importing ``episode.py``
runs the class-definition checks; the folder holds the ten files; no module imports another episode folder; its
commissions are admitted by the real forms of its four children and its own form (the recursive slot); its continuation
is an accumulation controller built from the parent input. Nothing here contacts a resource, and the points that raise
because the old module they need has no placed home are asserted to raise."""
import ast
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

from .. import episode as episode_module
from ..episode import BiochemicalFeasibilityEvidence
from ..execution_job_submission.messages.final_to_parent import RETURN_FORM as LAUNCH_RETURN
from ..execution_job_submission.messages.read_from_parent import ASSIGNMENT_FORM as LAUNCH_FORM
from ..execution_progress_assessment.messages.final_to_parent import RETURN_FORM as MONITOR_RETURN
from ..execution_progress_assessment.messages.read_from_parent import ASSIGNMENT_FORM as MONITOR_FORM
from ..execution_result_acquisition.messages.final_to_parent import RETURN_FORM as RESULTS_RETURN
from ..execution_result_acquisition.messages.read_from_parent import ASSIGNMENT_FORM as RESULTS_FORM
from ..goal import BINDING_PATH
from ..hpc_work_planning.messages.final_to_parent import RETURN_FORM as HPC_RETURN
from ..hpc_work_planning.messages.read_from_parent import ASSIGNMENT_FORM as HPC_FORM
from ..messages.final_to_parent import RETURN_FORM
from ..messages.msg_to_child import msg_to_child
from ..messages.read_from_child import read_from_child
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..task import CHILD_SLOTS, SELECTABLE, TOOLS, process_entry, process_execution, process_revise
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
CHILD_FOLDERS = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
                 'hpc_work_planning')
SHA = 'a' * 64
AXIS_REF = {'version': 'biochemical_feasibility_evidence_option_ref_v1', 'library_id': SHA, 'slot': 'evidence_axis',
            'option_id': 'A110', 'entry_sha256': SHA}
THOUGHT_REF = {'version': 'biochemical_feasibility_evidence_option_ref_v1', 'library_id': SHA,
               'slot': 'thought_pattern', 'option_id': 'P3', 'entry_sha256': SHA}
SELECTION = {'version': 'selection_v1', 'evidence_axis': AXIS_REF, 'thought_pattern': THOUGHT_REF,
             'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
HYPOTHESIS = 'hypothesis_' + '1' * 24
EVIDENCE = 'source_' + '2' * 24
# One outstanding job as ``job_records.outstanding_jobs`` lists it: its handoff row and one check row held of it.
JOB_HANDOFF, JOB_CHECK = 'row_' + '1' * 64, 'row_' + '2' * 64
JOBS = [{'job': 'job_' + '3' * 32, 'handoff_ref': JOB_HANDOFF, 'record_refs': [JOB_HANDOFF, JOB_CHECK]}]


def _assignment(**changes):
    value = {'selection': SELECTION, 'proposed_annotation_ref': [HYPOTHESIS], 'evidence_refs': [EVIDENCE],
             'constraints': {}, 'context': {}, 'scope': {'subject_refs': ['input_' + '3' * 24]},
             'received_record_refs': ['observation_' + '4' * 24]}
    value.update(changes)
    return value


def _summary():
    parent = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {'note': 'x'})
    return {**parent, 'goal': {'objective': 'investigate'}, 'record_refs': [HYPOTHESIS, EVIDENCE],
            'outstanding_jobs': JOBS}


def test_the_class_inherits_only_the_system_episode_type():
    assert BiochemicalFeasibilityEvidence.__bases__ == (EpisodeBinding,)
    assert BiochemicalFeasibilityEvidence.binding_path == BINDING_PATH == 'biochemical_feasibility_evidence'
    assert PACKAGE.endswith(BINDING_PATH.replace('/', '.'))
    slots = dict(BiochemicalFeasibilityEvidence.child_slots)
    assert slots == CHILD_SLOTS
    assert slots['biochemical_feasibility_evidence'] == BINDING_PATH
    assert {value for key, value in slots.items() if key != 'biochemical_feasibility_evidence'} == {
        BINDING_PATH + '/' + folder for folder in CHILD_FOLDERS}
    assert set(BiochemicalFeasibilityEvidence.tools) == set(TOOLS)
    assert tuple(BiochemicalFeasibilityEvidence.services) == ()


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts
             and not {'tests', *CHILD_FOLDERS} & set(path.relative_to(FOLDER).parts)}
    assert found == TEN_FILES


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER).parts
        if '__pycache__' in path.parts or 'tests' in relative or relative[0] in CHILD_FOLDERS:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2), (path, node.module)
                if node.level == 2:
                    assert node.module in (None, 'task', 'credit'), (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module, (path, module)


def test_the_return_form_declares_credit_finding_and_the_old_fact_sources():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding', 'committed_record_refs'}
    assert RETURN_FORM.fields['credit'].type == 'number'
    assert {name for name, spec in RETURN_FORM.fields.items() if not spec.required} == set(
        SELECTABLE['biochemical_feasibility_evidence'])


def test_the_assignment_form_reads_the_old_assignment_properties_and_the_parent_input_carries_them():
    for name in ('selection', 'proposed_annotation_ref', 'evidence_refs', 'constraints', 'context', 'revision_origin'):
        assert name in ASSIGNMENT_FORM.fields
    parent = _summary()
    assert parent['proposed_annotation_ref'] == HYPOTHESIS
    assert parent['continuation_task'] == 'A110:received_scientific_finding_progress'
    assert parent['finding_unit'] == 1
    with pytest.raises(Exception, match='scientific_task_proposed_annotation_required'):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(proposed_annotation_ref=[HYPOTHESIS, EVIDENCE]),
                                               'assignment'), {})
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({key: value for key, value in _assignment().items() if key != 'scope'}, 'assignment')


def _facts(slot):
    return list(SELECTABLE[slot])[:1]


def _admitted(slot, arguments, assignment_form, return_form):
    message = msg_to_child(slot, arguments, _summary())
    assert isinstance(message, ChildMessage)
    assignment_form.admit(message.assignment, slot + '_assignment')
    return_form.select(message.selection)
    return message


def test_each_commission_is_admitted_by_the_real_form_of_its_child():
    arguments = {'objective': 'o', 'purpose': 'p'}
    launch = {**arguments, 'handoff_unit': 1.0, 'acquired_record_unit': 1.0, 'facts': _facts('launch'),
              'assignment': {'requests': {'r': {}}, 'immutable_input_versions': [], 'constraints': {}},
              'input_refs': [EVIDENCE]}
    message = msg_to_child('launch', launch, _summary())
    assert message.assignment['record_refs'] == [EVIDENCE]
    assert message.assignment['scientific_task']['scientific_question'] == 'investigate'
    LAUNCH_RETURN.select(message.selection)
    monitor = {'information_unit': 1.0, 'handoff_ref': JOB_HANDOFF, 'requested_fields': ['execution_status'],
               'facts': _facts('monitor')}
    message = _admitted('monitor', monitor, MONITOR_FORM, MONITOR_RETURN)
    # The job is named by the records this episode holds; nothing the model wrote passes to the monitor.
    assert message.assignment == {'version': 'monitor_assignment_v2', 'handoff_refs': [JOB_HANDOFF],
                                  'known_progress_refs': [JOB_CHECK], 'dependency_handoff_refs': [],
                                  'requested_fields': ['execution_status'], 'information_unit': 1.0}
    assert message.selection == tuple(_facts('monitor')) and message.message == {}
    assert message.objective == 'Assess the progress of job ' + JOBS[0]['job'] + '.'
    with pytest.raises(KeyError):          # a job this episode does not hold as outstanding: the commission fails
        msg_to_child('monitor', {**monitor, 'handoff_ref': 'row_' + '0' * 64}, _summary())
    results = {**arguments, 'acquired_record_unit': 1.0, 'handoff_ref': 'receipt_' + '5' * 24,
               'selector': {'paths': ['a']}, 'resource_kind': 'hpc', 'facts': _facts('results')}
    _admitted('results', results, RESULTS_FORM, RESULTS_RETURN)
    hpc = {**arguments, 'commission_id': 'c', 'input_refs': [], 'facts': _facts('hpc')}
    _admitted('hpc', hpc, HPC_FORM, HPC_RETURN)
    own = {**arguments, 'assignment': {'selection': SELECTION, 'evidence_refs': [EVIDENCE], 'constraints': {}},
           'facts': _facts('biochemical_feasibility_evidence')}
    message = _admitted('biochemical_feasibility_evidence', own, ASSIGNMENT_FORM, RETURN_FORM)
    assert message.assignment['proposed_annotation_ref'] == [HYPOTHESIS]


def test_a_wrong_commission_fails_with_its_error():
    summary = _summary()
    base = {'objective': 'o', 'purpose': 'p', 'handoff_ref': 'receipt_' + '5' * 24, 'selector': {'paths': ['a']},
            'resource_kind': 'hpc', 'acquired_record_unit': 1.0}
    message = msg_to_child('results', {**base, 'facts': ['execution_result_origin']}, summary)
    with pytest.raises(FormError, match='selection_not_a_selectable_field'):
        RESULTS_RETURN.select(('credit',))
    assert message.selection == ('execution_result_origin',)
    with pytest.raises(KeyError):
        msg_to_child('results', {key: value for key, value in base.items() if key != 'selector'}, summary)
    with pytest.raises(LookupError):
        msg_to_child('wait', base, summary)
    with pytest.raises(LookupError):
        read_from_child('wait', {'credit': 1.0, 'finding': {}}, summary, None)


def test_read_from_child_keeps_credit_finding_and_the_facts_the_child_returned():
    report = read_from_child('monitor', {'credit': 2.0, 'finding': {'observed': True}, 'check_refs': [JOB_CHECK]},
                             {}, None)
    assert report == {'slot': 'monitor', 'child_credit': 2.0, 'finding': {'observed': True},
                      'facts': {'check_refs': [JOB_CHECK]}}


def test_the_controller_is_an_accumulation_controller_declared_for_this_credit():
    from ..credit import projector
    parent = _summary()
    declaration = {'kind': 'accumulation', 'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05},
                   'credit_definition': projector(parent).as_record()}
    controller = yield_controller(0.0, {'yield_bindings': {parent['continuation_task']: declaration}}, parent)
    assert isinstance(controller, AccumulationYieldController)
    with pytest.raises(ValueError, match='scientific_yield_binding_missing_for_task'):
        yield_controller(0.0, {'yield_bindings': {}}, parent)
    with pytest.raises(ValueError, match='scientific_yield_credit_definition_mismatch'):
        yield_controller(0.0, {'yield_bindings': {parent['continuation_task']: {
            **declaration, 'credit_definition': {'kind': 'other'}}}}, parent)


def test_the_lookups_whose_old_modules_have_no_placed_home_raise_where_they_are_reached():
    for tool in (process_entry, process_revise, process_execution):
        with pytest.raises(NotImplementedError, match='old_module_not_placed'):
            tool({}, None)


def test_the_return_carries_the_finding_and_every_selectable_field_and_is_admitted_by_the_form():
    from ..messages.final_to_parent import final_to_parent
    summary = {'investigation_progress': {'retained_finding_count': 2, 'inactive_dependencies': ['old']},
               'interpretation': {'interpretation': 'feasible', 'qualification': 'unresolved', 'source_refs': ['src_1']},
               'actions': [{'name': 'reason'}, {'name': 'received_evidence'}], 'committed_record_refs': ['rec_1'],
               'children': [{'slot': 'launch', 'child_credit': 1.0, 'finding': {}}],
               'received': {'native_components': [{'source_ref': 'src_b'}, {'source_ref': 'src_a'}],
                            'execution_findings': [{'source_ref': 'src_c'}]}}
    selectable = [name for name, spec in RETURN_FORM.fields.items() if not spec.required]
    result = final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}, selectable)
    assert result['credit'] == 2.0 and result['finding']['reasoning_commits'] == 1
    assert result['component_axis_native_component_records'] == ['src_a', 'src_b']
    assert result['component_axis_native_execution_records'] == ['src_c']
    RETURN_FORM.admit(result, 'return')
    unwritten = final_to_parent({**summary, 'interpretation': None},
                                {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0}, ())
    assert unwritten['finding']['written'] is False
    RETURN_FORM.admit(unwritten, 'return')
