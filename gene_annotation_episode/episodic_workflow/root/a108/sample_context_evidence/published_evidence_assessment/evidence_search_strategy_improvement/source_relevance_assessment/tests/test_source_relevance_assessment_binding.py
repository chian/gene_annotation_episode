"""Real checks of the A108 source relevance assessment binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a search assignment with its commissioned task, the yield controller follows the task and the
commission carries what the child's own form names."""
import ast
import importlib
from pathlib import Path

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'source_evidence_examination'}
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
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {name: goal.BINDING_PATH + '/' + name for name in CHILDREN}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES
    for child in CHILDREN:
        assert (FOLDER / child).is_dir()


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
                    assert not any(name.startswith(MODULE + '.' + child) for child in CHILDREN), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > len(Path(relative).parts):
                raise AssertionError((relative, 'relative import above the episode folder'))


def assignment(task=None):
    return {'version': 'search_assignment_v1', 'question_context_refs': ['context_111111111111111111111111'],
            'search_result_refs': ['source_111111111111111111111111', 'source_222222222222222222222222'],
            'literature_task': task or {'version': 'literature_local_task_v1', 'evidence_axis': 'A108',
                                        'credit_unit': 2, 'kind': 'verified_source_leads'},
            'proposed_annotation_ref': 'hypothesis_111111111111111111111111', 'scope': {'subject_refs': ['input_111111111111111111111111']},
            'received_record_refs': ['hypothesis_111111111111111111111111']}


def parent_input(task=None):
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    return from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(task), 'assignment'),
                                        {'purpose': 'x'})


def test_the_assignment_admits_a_search_assignment_and_read_from_parent_reads_it():
    value = parent_input()
    assert value['task_key'] == 'A108:verified_source_leads'
    assert value['search_result_refs'] == ['source_111111111111111111111111', 'source_222222222222222222222222'] and value['message'] == {'purpose': 'x'}


def test_the_yield_controller_follows_the_commissioned_task():
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    settings = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(yield_file.yield_controller(0.0, settings, parent_input())).__name__ == 'AccumulationYieldController'
    answer = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'credit_unit': 2,
              'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': ['source_111111111111111111111111']}
    controller = yield_file.yield_controller(0.0, settings, parent_input(answer))
    assert type(controller).__name__ == 'CompletionYieldController'


def summary_of(task):
    value = parent_input(task)
    return {'literature_assignment': {'version': 'search_assignment_v1', **{
                name: value[name] for name in ('question_context_refs', 'search_result_refs')},
                'literature_task': value['task'], 'proposed_annotation_ref': 'hypothesis_111111111111111111111111'},
            'task': value['task'], 'proposed_annotation_ref': 'hypothesis_111111111111111111111111', 'scope': value['scope'],
            'received_record_refs': value['received_record_refs'], 'proposed_annotation_subject_refs': ['input_111111111111111111111111'],
            'held_source_custody': {
                'source_111111111111111111111111': {'artifact_ref': 'artifact_111111111111111111111111', 'text_ref': 'artifact_222222222222222222222222', 'stdout_ref': None, 'stderr_ref': None,
                             'parent_source_refs': ['source_000000000000000000000000']},
                'source_000000000000000000000000': {'artifact_ref': 'artifact_000000000000000000000000', 'text_ref': None, 'stdout_ref': None, 'stderr_ref': None,
                             'parent_source_refs': []}}}


def test_the_commission_names_the_page_the_records_and_the_fields_it_wants():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    child_form = importlib.import_module(MODULE + '.source_evidence_examination.messages.read_from_parent')
    page = {'source_ref': 'source_111111111111111111111111', 'representation': 'original', 'artifact_ref': 'artifact_111111111111111111111111',
            'question_context_refs': ['context_111111111111111111111111'], 'prior_delivery_refs': []}
    message = to_child.msg_to_child('source_evidence_examination', {'objective': 'o', 'page': page},
                                    summary_of(None))
    assert isinstance(message, ChildMessage) and message.objective == 'o'
    assert message.selection == ('literature_source_lead_dispositions',)
    assert message.assignment['version'] == 'page_assignment_v1'
    assert message.assignment['received_record_refs'] == [
        'source_111111111111111111111111', 'artifact_111111111111111111111111', 'artifact_222222222222222222222222', 'source_000000000000000000000000', 'artifact_000000000000000000000000', 'context_111111111111111111111111', 'hypothesis_111111111111111111111111', 'input_111111111111111111111111']
    child_form.ASSIGNMENT_FORM.admit(message.assignment, 'assignment')


def test_an_assessment_task_is_narrowed_to_the_page_source():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'credit_unit': 2,
            'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': ['source_111111111111111111111111', 'source_222222222222222222222222']}
    page = {'source_ref': 'source_111111111111111111111111', 'representation': 'text', 'artifact_ref': 'artifact_222222222222222222222222',
            'question_context_refs': [], 'prior_delivery_refs': []}
    message = to_child.msg_to_child('source_evidence_examination', {'objective': 'o', 'page': page},
                                    summary_of(task))
    assert message.assignment['literature_task']['source_refs'] == ['source_111111111111111111111111']
    assert message.selection == ()


