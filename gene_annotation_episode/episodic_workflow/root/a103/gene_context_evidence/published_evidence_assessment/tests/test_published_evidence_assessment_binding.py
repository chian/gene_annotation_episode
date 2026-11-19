"""Real checks of the published evidence assessment binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a literature assignment, the instruction text composes over the library text, the commission
carries what the child's form names and the return form admits an assessment and credit."""
import ast
import importlib
from pathlib import Path

import pytest

from method_loop import FormError

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
          'published_evidence_assessment')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'evidence_search_strategy_improvement'}
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] in ({'tests'} | CHILDREN) or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert goal.BINDING_PATH == 'gene_context_evidence/published_evidence_assessment'
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {name: goal.BINDING_PATH + '/' + name for name in CHILDREN}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child).is_dir()


def test_no_module_imports_another_episode_folder():
    own = MODULE
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
                    assert name == own or name.startswith(own + '.'), (relative, name)
                    assert not any(name.startswith(own + '.' + child) for child in CHILDREN), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def literature():
    return {'version': 'literature_assignment_v1', 'question_context_refs': ['ctx_1'], 'source_refs': ['src_0'],
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_0', 'art_0']}


def test_the_assignment_admits_a_literature_assignment_and_read_from_parent_returns_it():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(literature(), 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input == {**literature(), 'message': {'purpose': 'x'}}
    with pytest.raises(FormError):
        from_parent.ASSIGNMENT_FORM.admit({**literature(), 'prior_search_refs': []}, 'assignment')


def test_the_instructions_compose_over_the_library_text_and_end_with_the_tool_text():
    task = importlib.import_module(MODULE + '.task')
    goal = importlib.import_module(MODULE + '.goal')
    text = task.instructions(knowledge=None, launch=None)
    assert goal.GOAL in text and text.endswith(task.TOOL_INSTRUCTION)
    assert 'evidence_search_strategy_improvement' in text


def test_the_commission_names_the_sources_and_the_records_its_child_reads():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    summary = {'assignment': {**literature(), 'message': {}}, 'held_record_refs': ['art_0', 'ctx_1', 'src_0', 'src_1']}
    arguments = {'objective': 'o', 'prior_search_refs': ['src_1']}
    message = to_child.msg_to_child('evidence_search_strategy_improvement', arguments, summary)
    assert isinstance(message, ChildMessage) and message.selection == () and message.objective == 'o'
    assert message.assignment == {
        'version': 'strategy_assignment_v1', 'question_context_refs': ['ctx_1'], 'prior_search_refs': ['src_1'],
        'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['art_0', 'ctx_1', 'src_0', 'src_1']}


def test_action_turns_an_answer_into_a_tool_call_or_a_child_call_and_rejects_the_rest():
    import json

    from episode_runtime import ChildCall, Rejected, ToolCall
    task = importlib.import_module(MODULE + '.task')
    summary = {'assignment': {**literature(), 'message': {}},
               'catalog': [{'name': task.ACCESS['source_read']}]}
    scope = literature()['scope']

    def answer(operation, arguments):
        return {'operation': operation, 'arguments_json': json.dumps(arguments)}
    assert task.action(answer('source_read', {'a': 1}), summary, None, None) == ToolCall(
        'source_read', {'arguments': {'a': 1}, 'scope': scope})
    assert task.action(answer('report', {'x': 1}), summary, None, None) == ToolCall('report', {'report': {'x': 1}})
    commission = {'objective': 'o', 'prior_search_refs': ['src_1']}
    assert task.action(answer('evidence_search_strategy_improvement', commission), summary, None, None) == ChildCall(
        'evidence_search_strategy_improvement', commission)
    for bad in (answer('public_pmc_files', {}), {'operation': 'report', 'arguments_json': '[]'}, {}):
        with pytest.raises(Rejected):
            task.action(bad, summary, None, None)


def test_the_yield_controller_is_the_bounded_quality_controller():
    from yield_control import BoundedQualityYieldController
    estimator = importlib.import_module(MODULE + '.yield_estimator')
    controller = estimator.yield_controller(0.0, {'cost': 1.0, 'parameters': None}, {})
    assert isinstance(controller, BoundedQualityYieldController)


def test_the_controlled_report_is_admitted_and_the_returned_finding_is_read_by_code_from_it():
    """The report the model writes is admitted by the episode's own form; the finding is what code reads from it,
    admitted by the return form; every text field of the finding is a fixed vocabulary (no model text returns)."""
    import importlib as modules
    final = modules.import_module(MODULE + '.messages.final_to_parent')
    report = final.REPORT_FORM.admit({'assessments': [{'source_ref': 'src_1', 'target_correspondence': 'established', 'evidence_type': 'conserved_neighborhood'}, {'source_ref': 'src_2', 'target_correspondence': 'unresolved', 'evidence_type': 'none_applicable'}]}, 'report')
    finding = final.finding_of(report)
    assert finding['assessed_source_refs'] == ['src_1'] and finding['conserved_neighborhood_count'] == 1 and finding['unresolved_correspondence_count'] == 1
    result = final.final_to_parent({'finding': finding}, {'ended_by': 'yield_stop', 'units_consumed': 3,
                                                          'credit': 0.5}, ())
    assert final.RETURN_FORM.admit(result, 'result') == result and result['credit'] == 0.5
    fields = final.RETURN_FORM.fields['finding'].form.fields
    assert all(hasattr(spec, 'options') for spec in fields.values() if spec.type == 'text')
    empty = final.finding_of(None)
    assert final.RETURN_FORM.fields['finding'].form.admit(empty, 'finding') == empty
