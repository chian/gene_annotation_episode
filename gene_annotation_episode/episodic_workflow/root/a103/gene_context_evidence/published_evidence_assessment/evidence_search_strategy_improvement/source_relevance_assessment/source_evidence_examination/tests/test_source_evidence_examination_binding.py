"""Real checks of the source evidence examination binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, no module imports another episode, the
assignment form admits a page and the commissions carry what the children's forms name."""
import ast
import importlib
from pathlib import Path

from episode_runtime import ChildMessage, EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
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


def page():
    return {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original',
            'artifact_ref': 'art_1', 'question_context_refs': ['ctx_1'], 'prior_delivery_refs': ['dlv_1'],
            'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}


def test_the_assignment_admits_a_page_and_read_from_parent_returns_it():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    admitted = from_parent.ASSIGNMENT_FORM.admit(page(), 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input == {**page(), 'message': {'purpose': 'x'}}


def test_each_commission_names_the_page_the_selection_and_the_records_its_child_reads():
    to_child = importlib.import_module(MODULE + '.messages.msg_to_child')
    summary = {'assignment': {**page(), 'message': {}}}
    window = {'source_ref': 'src_1', 'representation': 'original', 'offset': 0, 'limit': 100}
    table = to_child.msg_to_child('table_evidence_extraction', {'objective': 'o', 'selection': window}, summary)
    assert isinstance(table, ChildMessage) and table.selection == ()
    assert table.assignment['received_record_refs'] == ['src_1', 'art_1']
    assert table.assignment['page']['source_ref'] == 'src_1' and 'record_refs' not in table.assignment
    for slot in ('source_coverage_improvement', 'passage_evidence_extraction'):
        message = to_child.msg_to_child(slot, {'objective': 'o', 'selection': window}, summary)
        assert message.assignment['record_refs'] == ['src_1', 'art_1', 'ctx_1', 'dlv_1']
        assert message.assignment['version'] == 'reading_assignment_v1' and message.objective == 'o'




def test_the_controlled_report_is_admitted_and_the_returned_finding_is_read_by_code_from_it():
    """The report the model writes is admitted by the episode's own form; the finding is what code reads from it,
    admitted by the return form; every text field of the finding is a fixed vocabulary (no model text returns)."""
    import importlib as modules
    final = modules.import_module(MODULE + '.messages.final_to_parent')
    report = final.REPORT_FORM.admit({'target_correspondence': 'not_applicable', 'evidence_type': 'none_applicable', 'readings': [{'source_ref': 'src_1', 'kind': 'bytes', 'offset': 0, 'limit': 100}]}, 'report')
    finding = final.finding_of(report)
    assert finding['reported'] is True and finding['reading_count'] == 1
    result = final.final_to_parent({'finding': finding}, {'ended_by': 'yield_stop', 'units_consumed': 3,
                                                          'credit': 0.5}, ())
    assert final.RETURN_FORM.admit(result, 'result') == result and result['credit'] == 0.5
    fields = final.RETURN_FORM.fields['finding'].form.fields
    assert all(hasattr(spec, 'options') for spec in fields.values() if spec.type == 'text')
    empty = final.finding_of(None)
    assert final.RETURN_FORM.fields['finding'].form.admit(empty, 'finding') == empty


def test_the_input_list_shrinks_as_children_consume_candidates_and_offers_only_unconsumed_windows():
    """The page's input list: candidates of the source; a window handed to a child consumes the candidates inside it,
    the list shrinks, a selection holding only consumed input is not offered, an empty list offers no child."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.gene_context_evidence import (
        literature_input_list as inputs)
    content = ('word ' * 1500).encode('utf-8')
    first = inputs.input_list_state(content, [])
    assert len(first['input_list']) > 2 and first['consumed'] == []
    chunk = first['unconsumed'][0]
    selection = {'spans': [{'source_ref': 's', 'representation': 'text', 'offset': chunk['start'],
                            'limit': chunk['end'] - chunk['start']}]}
    commission = {'slot': 'passage_evidence_extraction', 'selection': selection, 'finding': {'reported': False}}
    second = inputs.input_list_state(content, [commission])
    assert chunk['candidate_id'] in second['consumed'] and chunk['candidate_id'] not in second['input_list']
    assert len(second['input_list']) < len(first['input_list'])
    assert not inputs.selection_offered('passage_evidence_extraction', selection, second['unconsumed'])
    assert inputs.selection_offered('passage_evidence_extraction', selection, first['unconsumed'])
    everything = {'offset': 0, 'limit': len(content)}
    done = inputs.input_list_state(content, [{'slot': 'source_coverage_improvement', 'selection': everything,
                                              'finding': {'reported': False}}])
    assert done['input_list'] == [] and done['remaining_windows'] == []
