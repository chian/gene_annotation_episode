"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set, its child folders and nothing else; no module of the episode imports another episode
folder; the episode's own forms and functions behave on real data; its commissions are admitted by the real forms of
its children (read by name at test time, never imported by the episode); the process library the head reads is the
repository's real published one. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildCall, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[6]
EPISODE = importlib.import_module(PACKAGE + '.episode').PerturbationEvidence
OWN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
             'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
             'tests/__init__.py', 'tests/test_binding.py'}
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
            'published_evidence_assessment')
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SLOTS = {'literature': 'perturbation_evidence/published_evidence_assessment',
         'launch': 'perturbation_evidence/execution_job_submission',
         'monitor': 'perturbation_evidence/execution_progress_assessment',
         'results': 'perturbation_evidence/execution_result_acquisition',
         'perturbation_evidence': 'perturbation_evidence'}
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
HYPOTHESIS = 'hypothesis_' + 'a' * 24
EVIDENCE = 'observation_' + 'b' * 24
SOURCE = 'source_' + 'c' * 24
ARTIFACT = 'artifact_' + 'd' * 24
CONTEXT = 'record_' + 'e' * 24
HANDOFF = 'record_' + 'f' * 24


def option(slot, option_id):
    return {'version': 'perturbation_evidence_option_ref_v1', 'library_id': '1' * 64, 'slot': slot,
            'option_id': option_id, 'entry_sha256': '2' * 64}


SELECTION = {'version': 'perturbation_evidence_selection_v3', 'evidence_axis': option('evidence_axis', 'A106'),
             'thought_pattern': option('thought_pattern', 'P07'), 'child_tool_info': []}
TASK = {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A106',
        'credit_unit': 2.0}
ASSIGNMENT = {'selection': SELECTION, 'proposed_annotation_ref': HYPOTHESIS, 'evidence_refs': [EVIDENCE],
              'constraints': {}, 'context': {'evidence_task': TASK}, 'scope': {'subject_refs': ['sub_1']},
              'received_record_refs': [HYPOTHESIS]}


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def child_module(name, name_in_child):
    return importlib.import_module(PACKAGE + '.' + name + '.' + name_in_child)


def own_files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts
            and path.relative_to(FOLDER).parts[0] not in CHILDREN}


def summary_of(parent_input, **more):
    return {**parent_input, 'source_custody': {SOURCE: [SOURCE, ARTIFACT]}, 'handoff_resources': [],
            'progress_snapshots': {}, **more}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == module('goal').BINDING_PATH == 'perturbation_evidence'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == SLOTS
    assert tuple(EPISODE.services) == ()


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children_and_its_child_folders():
    assert own_files() == OWN_FILES
    assert {path.name for path in FOLDER.iterdir() if path.is_dir() and path.name != '__pycache__'} \
        == {'messages', 'tests', *CHILDREN}


def test_no_module_of_the_episode_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        relative = path.relative_to(FOLDER)
        if relative.parts[0] in CHILDREN or relative.parts[0] == 'tests':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level:      # relative: only within this episode's folder
                assert node.level == len(relative.parts), str(relative)
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for name in modules:
                assert not name.startswith(ROOT), str(relative) + ' imports ' + name


def test_the_commission_form_admits_the_assignment_and_the_parent_input_is_read_from_it_alone():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'investigate'})
    assert parent_input['task_key'] == 'A106:whole_axis_findings' and parent_input['task'] == TASK
    assert parent_input['selection'] == SELECTION and parent_input['evidence_refs'] == [EVIDENCE]
    assert set(form.record_refs(admitted)) == {EVIDENCE, HYPOTHESIS}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='original_axis_finding_task_required'):
        EPISODE.read_from_parent({**admitted, 'context': {'evidence_task': {**TASK, 'evidence_axis': 'A105'}}}, {})
    with pytest.raises(ValueError, match='explicit_positive_finding_unit_required'):
        EPISODE.read_from_parent({**admitted, 'context': {'evidence_task': {**TASK, 'credit_unit': 0}}}, {})
    with pytest.raises(ValueError, match='scientific_task_proposed_annotation_required'):
        EPISODE.read_from_parent({key: value for key, value in admitted.items() if key != 'proposed_annotation_ref'},
                                 {})
    with pytest.raises(ValueError, match='perturbation_evidence_selection_invalid'):
        EPISODE.read_from_parent({**admitted, 'selection': {**SELECTION, 'version': 'other'}}, {})


def test_the_controller_is_an_accumulation_controller_built_from_the_parent_input_alone():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    controller = EPISODE.yield_controller(0, {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}, parent_input)
    assert type(controller).__name__ == 'AccumulationYieldController'
    with pytest.raises(ValueError, match='scientific_yield_binding_missing_for_task'):
        EPISODE.yield_controller(0, {'cost': 0.1, 'parameters': {}}, {**parent_input, 'task_key': 'A105:x'})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert not form.fields['committed_record_refs'].required
    assert not form.fields['perturbation_evidence_results'].required
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = summary_of(parent_input, report=None, report_source_held={}, committed_record_refs=[CONTEXT],
                         committed_record_held={CONTEXT: True}, child_reports=[], received_process_results=[],
                         investigation_progress={'credit': 0, 'retained_finding_count': 0})
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}
    result = EPISODE.final_to_parent(summary, completion, ())
    assert result['credit'] == 2.5 and result['finding']['written'] is False
    form.admit(result, 'test')
    result = EPISODE.final_to_parent(summary, completion, ('committed_record_refs',))
    assert result['committed_record_refs'] == [CONTEXT]
    form.select(('committed_record_refs',)).admit(result, 'test')
    received = {'selection': SELECTION, 'proposed_annotation_ref': HYPOTHESIS, 'credit': 1.0, 'completed_actions': 3}
    selection = ('perturbation_evidence_results', 'committed_record_refs')
    result = EPISODE.final_to_parent({**summary, 'received_process_results': [received]}, completion, selection)
    assert result['perturbation_evidence_results'] == [
        {'selection': SELECTION, 'proposed_annotation_ref': HYPOTHESIS, 'credit': 2.5, 'completed_actions': 0},
        received]
    form.select(selection).admit(result, 'return')
    written = {**summary, 'report': {'interpretation': 'x', 'sources': [
        {'source_ref': SOURCE, 'statement': 's', 'qualification': 'q'}], 'qualification': 'q'},
        'report_source_held': {SOURCE: True}, 'child_reports': [{'slot': 'launch', 'report': {'credit': 1.0}}]}
    result = EPISODE.final_to_parent(written, completion, ())
    assert result['finding']['written'] is True and result['finding']['children'] == [{'slot': 'launch', 'credit': 1.0}]
    form.admit(result, 'return')


def test_the_credit_is_real_code_and_the_old_stop_tests_are_not_carried():
    credit_module = module('credit')
    assert EPISODE.credit is credit_module.credit
    for name in ('credit.py', 'yield_estimator.py'):
        text = (FOLDER / name).read_text()
        assert 'NotImplementedError' not in text
        assert 'min(' not in text and 'max(' not in text.replace('maximum', '')


def test_the_model_is_offered_the_tools_the_reasoning_the_report_and_the_children_the_settings_allow():
    task = module('task')
    names = task.offered({})
    assert names[-2:] == ['reason', 'report'] and set(names) <= set(EPISODE.tools)
    assert 'knowledge_search' not in names
    assert 'knowledge_search' in task.offered({'knowledge_library_directory': '.'})
    assert set(task.offered({'knowledge_library_directory': '.'})) <= set(EPISODE.tools)
    assert task.offered_slots({'child_roles': ['literature', 'perturbation_evidence']}) == ['literature',
                                                                                          'perturbation_evidence']
    with pytest.raises(Exception, match='scientific_child_roles_invalid'):
        task.offered_slots({'child_roles': ['wait']})
    commit_schema = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                     'properties': {'terms': {'type': 'array'}}}
    entries = task.catalog({}, SELECTION, {'reasoning_schema': commit_schema}, True)
    assert [entry['name'] for entry in entries] == [name for name in names if name != 'selected_tool']
    selected = [{'name': 'source.read', 'description': 'd', 'resources': 'local',
                 'input_schema': {'type': 'object', 'properties': {'source_ref': task.REF},
                                  'required': ['source_ref'], 'additionalProperties': False}}]
    schema = task.selection_schema(entries, selected, list(SLOTS))
    assert len(schema['properties']['selection']['anyOf']) == len(entries) + 1 + len(SLOTS)
    task.generation_schema(schema)
    answer = {'selection': {'kind': 'tool', 'tool': 'selected_tool',
                            'arguments': {'name': 'source.read', 'arguments': {'source_ref': SOURCE}}}}
    assert task.validate_selection_answer(answer, schema)['tool'] == 'selected_tool'
    assert task.empty_commit({'terms': []}, commit_schema) and not task.empty_commit({'terms': [{}]}, commit_schema)


def test_the_instructions_are_the_library_text_and_the_goal_replaces_or_follows_it():
    task, goal = module('task'), module('goal')
    replaced = task.instructions(goal=goal.GOAL, replaces=True, reasoning=True, knowledge=False, launch=False)
    appended = task.instructions(goal=goal.GOAL, replaces=False, reasoning=True, knowledge=True, launch=True)
    assert replaced.startswith(goal.GOAL[:40]) and goal.GOAL in appended
    assert task.REASONING_COMMIT_REQUIREMENT in replaced and task.KNOWLEDGE_INSTRUCTIONS in appended
    assert task.LAUNCH_INSTRUCTIONS in appended and appended.startswith(task.INSTRUCTIONS[:40])
    assert 'wait' not in goal.GOAL.split('Children own')[0].split('Choose an available tool action')[1][:300]


def test_the_head_reads_the_real_published_process_library(tmp_path):
    task = module('task')
    library = task.PerturbationEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    axis = library.reference('A106')
    selection = {**SELECTION, 'evidence_axis': axis, 'thought_pattern': library.reference('P07')}
    entry, published = task.entry_of(library, selection)
    assert entry['id'] == 'A106' and isinstance(published, bool)
    assert task.replaces_default_instructions(library) in (True, False)
    outcome = library.execute('process.entry', {'option_id': 'P07'})
    assert outcome['status'] == 'completed'


def commission(slot, arguments, summary):
    return EPISODE.msg_to_child(slot, ChildCall(slot, arguments).arguments, summary)


def test_the_literature_commission_is_admitted_by_the_form_of_the_child_and_selects_what_the_task_counts():
    arguments = {'question_context_refs': [CONTEXT], 'source_refs': [SOURCE],
                 'literature_task': {'evidence_axis': 'A106', 'kind': 'verified_source_leads'}}
    task, parent_input = module('task'), EPISODE.read_from_parent(ASSIGNMENT, {})
    schema = task.commission_arguments('literature')
    task.validate_schema(arguments, schema)
    message = commission('literature', arguments, summary_of(parent_input))
    read = child_module('published_evidence_assessment', 'messages.read_from_parent')
    admitted = read.ASSIGNMENT_FORM.admit(message.assignment, 'commission')
    assert set(read.ASSIGNMENT_FORM.record_refs(admitted)) == {CONTEXT, SOURCE, ARTIFACT, HYPOTHESIS}
    assert admitted['literature_task']['credit_unit'] == 2.0
    assert read.read_from_parent(admitted, {})['task_key'] == 'A106:verified_source_leads'
    returns = child_module('published_evidence_assessment', 'messages.final_to_parent').RETURN_FORM
    assert set(message.selection) == {'literature_source_lead_dispositions'}
    assert set(returns.select(message.selection).fields) >= {'credit', 'finding', *message.selection}
    with pytest.raises(KeyError):      # a source this episode does not hold is a wrong commission: it fails
        commission('literature', arguments, summary_of(parent_input, source_custody={}))
    report = EPISODE.read_from_child('literature', {'credit': 1.0, 'finding': {}, 'literature_source_lead_dispositions':
                                                    [{'x': 1}]}, {}, None)
    assert report['facts'] == {'literature_source_lead_dispositions': [{'x': 1}]}


def test_the_launch_monitor_and_results_commissions_are_admitted_by_the_forms_of_their_children():
    task, parent_input = module('task'), EPISODE.read_from_parent(ASSIGNMENT, {})
    summary = summary_of(parent_input, handoff_resources=['bvbrc'],
                         progress_snapshots={'progress_' + '1' * 24: {'target_handle': 'job_1'}})
    launch = {'requests': {'bvbrc': {}}, 'immutable_input_versions': [],
              'constraints': {}, 'launch_instructions': None, 'record_refs': [CONTEXT], 'handoff_unit': 1.0}
    monitor = {'target_handle': 'job_1', 'requested_fields': [],
               'known_progress_refs': ['progress_' + '1' * 24], 'permitted_committed_record_types': [],
               'information_unit': 0.5}
    results = {'handoff_ref': HANDOFF, 'selector': {'kind': 'all'},
               'service': 'bvbrc_appservice', 'return_facts': ['bvbrc_application_outcomes']}
    for slot, arguments in (('launch', launch), ('monitor', monitor), ('results', results)):
        task.validate_schema({key: value for key, value in arguments.items()
                              if key not in ('handoff_unit', 'information_unit')}, task.commission_arguments(slot))
        message = commission(slot, arguments, summary)
        child = {'launch': 'execution_job_submission', 'monitor': 'execution_progress_assessment',
                 'results': 'execution_result_acquisition'}[slot]
        form = child_module(child, 'messages.read_from_parent').ASSIGNMENT_FORM
        admitted = form.admit(message.assignment, 'commission')
        returns = child_module(child, 'messages.final_to_parent').RETURN_FORM
        assert set(returns.select(message.selection).fields) >= {'credit', 'finding', *message.selection}
        if slot == 'launch':
            assert set(form.record_refs(admitted)) == {CONTEXT} and admitted['received_handoff_resources'] == ['bvbrc']
            assert message.selection == ('execution_handoff_refs', 'execution_completed')
        if slot == 'monitor':
            assert 'monitoring_progress_refs' in message.selection and admitted['information_unit'] == 0.5
            assert admitted['known_progress_snapshots'] == summary['progress_snapshots']
        if slot == 'results':
            assert set(form.record_refs(admitted)) == {HANDOFF}
            assert 'bvbrc_application_outcomes' in message.selection
    with pytest.raises(KeyError):
        EPISODE.msg_to_child('wait', launch, summary)


def test_the_commission_of_a_child_of_this_process_is_admitted_by_this_episodes_own_form():
    parent_input = EPISODE.read_from_parent(ASSIGNMENT, {})
    revised = {**SELECTION, 'thought_pattern': option('thought_pattern', 'P08')}
    origin = {'version': 'perturbation_evidence_revision_origin_v1',
              'parent_invocation_ref': 'scientific_invocation_' + '3' * 24,
              'preparation_operation_ref': 'operation_' + '4' * 24}
    arguments = {'selection': revised, 'revision_origin': origin}
    message = commission('perturbation_evidence', arguments, summary_of(parent_input))
    admitted = EPISODE.assignment_form.admit(message.assignment, 'commission')
    child_input = EPISODE.read_from_parent(admitted, {})
    assert child_input['proposed_annotation_ref'] == HYPOTHESIS and child_input['revision_origin'] == origin
    assert child_input['selection']['thought_pattern']['option_id'] == 'P08'
    assert set(message.selection) == {'perturbation_evidence_results', 'committed_record_refs'}
    assert set(EPISODE.return_form.select(message.selection).fields) >= {'credit', 'finding', *message.selection}
    report = EPISODE.read_from_child('perturbation_evidence', {
        'credit': 1.0, 'finding': {}, 'perturbation_evidence_results': [{'a': 1}], 'committed_record_refs': [CONTEXT]},
        {}, None)
    assert report['committed_record_refs'] == [CONTEXT]
    assert report['facts']['perturbation_evidence_results'] == [{'a': 1}]
