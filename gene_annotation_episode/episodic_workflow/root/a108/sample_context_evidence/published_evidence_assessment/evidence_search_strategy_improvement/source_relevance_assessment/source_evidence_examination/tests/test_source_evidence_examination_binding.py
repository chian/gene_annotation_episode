"""Real checks of the A108 source evidence examination binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode folder, the
assignment form admits a page with its commissioned task and the commissions carry what the children's forms name."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
          'source_evidence_examination')
FOLDER = Path(__file__).resolve().parent.parent
CHILDREN = {'passage_evidence_extraction', 'source_coverage_improvement', 'table_evidence_extraction'}
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


def assignment():
    return {'version': 'page_assignment', 'source_ref': 'src_1', 'representation': 'original',
            'artifact_ref': 'art_1', 'question_context_refs': ['ctx_1'], 'prior_delivery_refs': ['dlv_1'],
            'literature_task': {'version': 'literature_local_task', 'evidence_axis': 'A108', 'credit_unit': 2,
                                'kind': 'verified_source_leads'},
            'proposed_annotation_ref': 'hypothesis_1', 'scope': {'subject_refs': ['sub_1']},
            'received_record_refs': ['src_1', 'art_1', 'hypothesis_1']}


def test_the_assignment_admits_a_page_and_read_from_parent_reads_it():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment(), 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['task_key'] == 'A108:verified_source_leads'
    assert parent_input['page']['source_ref'] == 'src_1' and parent_input['message'] == {'purpose': 'x'}


def test_the_yield_controller_follows_the_commissioned_task():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    yield_file = importlib.import_module(MODULE + '.yield_estimator')
    parent_input = from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(), 'assignment'), {})
    settings = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}
    controller = yield_file.yield_controller(0.0, settings, parent_input)
    assert type(controller).__name__ == 'AccumulationYieldController'


def test_each_commission_names_the_page_the_selection_and_the_fields_it_wants():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    parent_input = from_parent.read_from_parent(from_parent.ASSIGNMENT_FORM.admit(assignment(), 'assignment'), {})
    page = parent_input['page']
    summary = {'literature_assignment': {**page, 'literature_task': parent_input['task'],
                                         'proposed_annotation_ref': 'hypothesis_1'},
               'task': parent_input['task'], 'proposed_annotation_ref': 'hypothesis_1',
               'scope': parent_input['scope'], 'received_record_refs': parent_input['received_record_refs']}
    summary['page'] = page
    summary['content_candidates'] = [{'candidate_id': 'prose_chunk:0000', 'candidate_type': 'prose_chunk', 'index': 0,
                                      'start': 0, 'end': 100},
                                     {'candidate_id': 'source_table:t', 'candidate_type': 'source_table', 'index': 0,
                                      'start': 100, 'end': 160}]
    summary['report_windows'] = [[0, 100]]
    arguments = {'passage_evidence_extraction': {'candidate_id': 'prose_chunk:0000'},
                 'table_evidence_extraction': {'candidate_id': 'source_table:t'},
                 'source_coverage_improvement': {}}
    for slot in sorted(CHILDREN):
        message = to_child.msg_to_child(slot, arguments[slot], summary)
        assert isinstance(message, ChildMessage) and message.objective == 'find_applicable_evidence'
        assert message.selection == ('literature_source_lead_dispositions',)
        assert message.assignment['version'] == 'reading_assignment'
        assert message.assignment['received_record_refs'] == ['src_1', 'art_1', 'hypothesis_1', 'ctx_1', 'dlv_1']


def test_any_task_but_verified_source_leads_is_a_wrong_commission():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    wrong = {**assignment(), 'literature_task': {'version': 'literature_local_task', 'evidence_axis': 'A108',
                                                 'credit_unit': 2, 'kind': 'source_answer',
                                                 'answer_kind': 'assessment', 'source_refs': ['src_1']}}
    admitted = from_parent.ASSIGNMENT_FORM.admit(wrong, 'assignment')
    with pytest.raises(Exception):
        from_parent.read_from_parent(admitted, {})


def test_the_page_offers_no_tool_but_its_automatic_assessment():
    task = importlib.import_module(MODULE + '.task')
    assert set(task.TOOLS) == {'assess_content'}
    assert set(task.CHILD_SLOTS) == CHILDREN


