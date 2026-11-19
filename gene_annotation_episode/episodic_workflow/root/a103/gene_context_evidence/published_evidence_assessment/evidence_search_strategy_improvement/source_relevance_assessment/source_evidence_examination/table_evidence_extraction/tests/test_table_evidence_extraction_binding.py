"""Real checks of the table evidence extraction binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, and no module imports another episode."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
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
                      'received_record_refs': ['src_1']}
        admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
        assert from_parent.read_from_parent(admitted, 'm')['selection'] == selection




def test_the_controlled_report_is_admitted_and_the_returned_finding_is_read_by_code_from_it():
    """The report the model writes is admitted by the episode's own form; the finding is what code reads from it,
    admitted by the return form; every text field of the finding is a fixed vocabulary (no model text returns)."""
    import importlib as modules
    final = modules.import_module(MODULE + '.messages.final_to_parent')
    report = final.REPORT_FORM.admit({'target_correspondence': 'unresolved', 'evidence_type': 'phylogenetic_cooccurrence', 'readings': [{'source_ref': 'src_1', 'kind': 'sheet_rows', 'offset': 2, 'limit': 3}]}, 'report')
    finding = final.finding_of(report)
    assert finding['reading_count'] == 1 and (finding['covered_offset'], finding['covered_limit']) == (2, 3)
    result = final.final_to_parent({'finding': finding}, {'ended_by': 'yield_stop', 'units_consumed': 3,
                                                          'credit': 0.5}, ())
    assert final.RETURN_FORM.admit(result, 'result') == result and result['credit'] == 0.5
    fields = final.RETURN_FORM.fields['finding'].form.fields
    assert all(hasattr(spec, 'options') for spec in fields.values() if spec.type == 'text')
    empty = final.finding_of(None)
    assert final.RETURN_FORM.fields['finding'].form.admit(empty, 'finding') == empty
