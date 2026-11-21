"""Real checks of the table evidence extraction binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, and no module imports another episode."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
          'source_evidence_examination.table_evidence_extraction')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
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
    assert dict(classes[0].child_slots) == {}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


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
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_admits_a_table_selection_and_a_byte_window():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original',
            'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': []}
    table = {'source_ref': 'src_1', 'sheet_key': 'rId1', 'offset': 0, 'limit': 20, 'header_row': 1,
             'where': {'match': 'contains', 'value': 'kcat', 'case_sensitive': False}}
    window = {'source_ref': 'src_1', 'representation': 'original', 'offset': 0, 'limit': 100}
    for selection in (table, window):
        assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': selection, 'scope': {},
                      'received_record_refs': ['src_1'], 'finding_unit': 1.0}
        admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
        assert from_parent.read_from_parent(admitted, 'm')['selection'] == selection


def test_the_instruction_text_is_assembled_from_the_real_default_text():
    task = importlib.import_module(MODULE + '.task')
    text = task.instructions(False)
    assert 'Select one ordinary tool at a time.' in text
    assert 'Investigate reported partner removal, addback and coexpression evidence.' in text
    assert 'redeliver_report' not in text and 'request_context' not in text


def test_the_return_is_the_credit_and_the_controlled_sheet_features_and_the_form_admits_it():
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    counts = {'matched_sheet_count': 0, 'matched_loss_sheet_count': 0, 'distinct_experiment_count': 0}
    result = final.final_to_parent({'partner_sheets': [], 'partner_agreement': counts},
                                   {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}, ())
    assert result == {'credit': 1.5, 'finding': {'partner_sheets': [], **counts}}
    final.RETURN_FORM.admit(result, 'return')


def test_the_input_list_is_the_selection_until_a_grader_has_completed_on_it():
    summary = importlib.import_module(MODULE + '.messages.internal_summary')
    items = summary.selection_range({'offset': 10, 'limit': 5})
    assert items == [[10, 15]] and summary.selection_range({'offset': 10, 'limit': 0}) == []
    read = {'kind': 'tool', 'tool': 'source_read', 'outcome': {'status': 'completed'}}
    failed = {'kind': 'tool', 'tool': 'literature_partner_populate', 'outcome': {'status': 'invalid'}}
    graded = {'kind': 'tool', 'tool': 'literature_partner_populate', 'outcome': {'status': 'completed'}}
    assert summary.processed_inputs([read, failed], items) == []
    assert summary.processed_inputs([read, failed, graded], items) == items
