"""The A104 source coverage improvement episode is a private binding in the ten-file form."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

from .. import episode as episode_module
from ..episode import SourceCoverageImprovement
from ..goal import BINDING_PATH
from ..messages.final_to_parent import FINDING_FORM, LEADS, RETURN_FORM, SCREENING, final_to_parent
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..task import instructions
from ..yield_estimator import yield_controller

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
             'literature_task': {'kind': 'source_answer', 'answer_kind': 'assessment', 'evidence_axis': 'A105',
                                 'credit_unit': 2.0, 'source_refs': ['src_1']},
             'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
             'received_record_refs': ['src_1', 'art_1', 'hyp_1']}
    return {**value, **changes}


def test_the_assignment_form_admits_the_old_assignment_and_read_from_parent_reads_it():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, 'message')
    assert parent_input['window']['limit'] == 10
    assert parent_input['task_key'] == 'A105:source_answer:assessment'


def test_the_assignment_form_refuses_an_unknown_field():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**_assignment(), 'requested_rate_components': []}, 'assignment')


def test_a_window_of_another_source_is_refused_where_the_assignment_is_read():
    window = {'source_ref': 'src_2', 'representation': 'text', 'offset': 0, 'limit': 10}
    assignment = ASSIGNMENT_FORM.admit(_assignment(selection=window), 'assignment')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        read_from_parent(assignment, 'message')


def test_the_return_form_declares_credit_and_finding_as_required():
    required = {name for name, field in RETURN_FORM.fields.items() if field.required}
    assert {'credit', 'finding'} <= required
    assert not RETURN_FORM.fields['literature_screening_answers'].required


def test_the_controller_follows_the_commissioned_task():
    parent_input = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), 'message')
    settings = {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.1}}
    assert type(yield_controller(0, settings, parent_input)).__name__ == 'CompletionYieldController'
    leads = {**parent_input, 'task': {**parent_input['task'], 'kind': 'verified_source_leads'}}
    assert type(yield_controller(0, settings, leads)).__name__ == 'AccumulationYieldController'


def test_the_instruction_text_is_assembled_without_the_actions_this_leaf_lacks():
    text = instructions()
    assert 'substantive child improvement' not in text
    assert 'redeliver_report' not in text
    assert 'report tool' not in text and 'never prose of yours' in text


def test_final_to_parent_returns_credit_and_controlled_features_and_is_admitted():
    summary = {'assay_sheets': [], 'assessments': [], 'sheet_record_refs': ['record_1'],
               'proposed_annotation_ref': 'hyp_1', 'screening_answers': [], 'no_applicable_evidence': [],
               'source_lead_dispositions': [{'source_ref': 'src_1', 'disposition': 'relevant'}]}
    result = final_to_parent(summary, {'credit': 1.5}, (SCREENING, LEADS))
    assert result['credit'] == 1.5 and result['finding']['sheet_record_refs'] == ['record_1']
    assert result[LEADS] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    assert RETURN_FORM.select((SCREENING, LEADS)).admit(result, 'return') == result
    RETURN_FORM.admit(final_to_parent(summary, {'credit': 1.5}, ()), 'return')
    assert set(FINDING_FORM.fields) == {'assay_sheets', 'assessments', 'assay_count', 'assessment_count',
                                        'assay_count_with_evidence_ratio', 'sheet_record_refs'}
