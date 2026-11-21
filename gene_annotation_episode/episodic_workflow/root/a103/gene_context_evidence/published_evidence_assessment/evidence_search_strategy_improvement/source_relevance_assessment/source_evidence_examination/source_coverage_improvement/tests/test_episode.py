"""The A103 source coverage improvement episode is a private binding in the ten-file form."""
import ast
import json
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

from .. import episode as episode_module
from ..episode import SourceCoverageImprovement
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert SourceCoverageImprovement.__bases__ == (EpisodeBinding,)
    assert SourceCoverageImprovement.binding_path == BINDING_PATH
    assert dict(SourceCoverageImprovement.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2) or 'tests' in path.parts, (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module or module.startswith(PACKAGE), (path, module)


def _assignment(**changes):
    value = {'version': 'reading_assignment_v1',
             'page': {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text',
                      'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': []},
             'selection': {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10},
             'scope': {'subject_refs': ['sub_1']}, 'record_refs': ['src_1', 'art_1']}
    return {**value, **changes}


def test_the_assignment_form_admits_the_old_assignment_and_read_from_parent_reads_it():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, 'message')
    assert parent_input['selection']['limit'] == 10


def test_the_assignment_form_refuses_an_unknown_field():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**_assignment(), 'other': 1}, 'assignment')


def test_a_window_of_another_source_is_refused_where_the_assignment_is_read():
    window = {'source_ref': 'src_2', 'representation': 'text', 'offset': 0, 'limit': 10}
    assignment = ASSIGNMENT_FORM.admit(_assignment(selection=window), 'assignment')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        read_from_parent(assignment, 'message')


def test_the_return_form_declares_credit_and_finding_as_required():
    required = {name for name, field in RETURN_FORM.fields.items() if field.required}
    assert {'credit', 'finding'} <= required


# The unit functions over plain summaries (data, not stand-ins for the system).
from episode_runtime import Rejected, ToolCall  # noqa: E402

from ..messages.final_to_parent import final_to_parent  # noqa: E402
from ..task import TOOLS, decide

SCOPE = {'subject_refs': ['sub_1']}
FINDING = {'source_claim': 'claim', 'source_subject': 'subject', 'qualification': 'q',
           'target_correspondence': 'unresolved', 'windows': [
               {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10, 'quote': 'text'}]}


def _summary(**changes):
    value = {'assignment': {'scope': SCOPE, 'page': {'source_ref': 'src_1'}},
             'catalog': [{'name': 'source.read'}], 'report': None, 'report_sources_held': {},
             'input_list': [[0, 10], [10, 20]]}
    return {**value, **changes}


def test_the_input_list_shrinks_as_windows_are_read_and_an_empty_list_offers_nothing():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.gene_context_evidence import (
        reading_windows as library)
    windows = library.reading_windows(5, 10, 32)
    assert windows == [[5, 15], [15, 25], [25, 32]]
    read = {'kind': 'tool', 'tool': 'source_read',
            'outcome': {'status': 'completed', 'result': {'artifact_ref': 'art_1', 'start': 5, 'end': 25}}}
    other = {**read, 'outcome': {'status': 'completed', 'result': {'artifact_ref': 'art_2', 'start': 0, 'end': 99}}}
    spans = library.read_spans([read, other], 'art_1')
    assert library.remaining_windows(windows, spans) == [[25, 32]]
    with pytest.raises(LookupError):
        decide(_summary(input_list=[]), None, None)


def test_a_read_touching_no_unconsumed_window_is_rejected():
    from ..task import action
    summary = _summary(input_list=[[10, 20]])
    summary['assignment']['page'] = {'source_ref': 'src_1', 'representation': 'text'}
    consumed = {'tool': 'source_read', 'arguments_json': json.dumps({'source_ref': 'src_1', 'offset': 0, 'limit': 10})}
    with pytest.raises(Rejected):
        action(consumed, summary, None, None)
    live = {'tool': 'source_read', 'arguments_json': json.dumps({'source_ref': 'src_1', 'offset': 5, 'limit': 10})}
    assert action(live, summary, None, None).name == 'source_read'


def test_the_first_unit_is_the_catalog_lookup():
    call = decide(_summary(catalog=None), None, None)
    assert isinstance(call, ToolCall) and call.name == 'tool_catalog' and call.arguments == {'scope': SCOPE}




def test_the_controlled_report_is_admitted_and_the_returned_finding_is_read_by_code_from_it():
    """The report the model writes is admitted by the episode's own form; the finding is what code reads from it,
    admitted by the return form; every text field of the finding is a fixed vocabulary (no model text returns)."""
    import importlib as modules
    final = modules.import_module(PACKAGE + '.messages.final_to_parent')
    report = final.REPORT_FORM.admit({'target_correspondence': 'established', 'evidence_type': 'gene_fusion', 'windows': [{'source_ref': 'src_1', 'representation': 'text', 'offset': 10, 'limit': 5}, {'source_ref': 'src_1', 'representation': 'text', 'offset': 40, 'limit': 10}]}, 'report')
    finding = final.finding_of(report)
    assert finding['window_count'] == 2 and finding['evidence_type'] == 'gene_fusion'
    result = final.final_to_parent({'finding': finding}, {'ended_by': 'yield_stop', 'units_consumed': 3,
                                                          'credit': 0.5}, ())
    assert final.RETURN_FORM.admit(result, 'result') == result and result['credit'] == 0.5
    fields = final.RETURN_FORM.fields['finding'].form.fields
    assert all(hasattr(spec, 'options') for spec in fields.values() if spec.type == 'text')
    empty = final.finding_of(None)
    assert final.RETURN_FORM.fields['finding'].form.admit(empty, 'finding') == empty
