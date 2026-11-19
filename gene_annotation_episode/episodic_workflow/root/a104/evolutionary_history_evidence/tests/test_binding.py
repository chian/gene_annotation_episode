"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode with children (its child episode folders aside); no module imports
another episode folder; the episode's own forms and commissions behave on real data. Nothing here is faked and
nothing contacts a remote service."""
import ast
import importlib
from pathlib import Path
import re

import pytest

from episode_runtime import ChildMessage, EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').EvolutionaryHistoryEvidence
TO_CHILD = importlib.import_module(PACKAGE + '.messages.msg_to_child')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
            'hpc_work_planning', 'published_evidence_assessment')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/msg_to_child.py',
         'messages/read_from_child.py', 'messages/internal_summary.py', 'messages/final_to_parent.py',
         'tests/__init__.py', 'tests/test_binding.py', 'tests/a104_world.py', 'tests/test_a104_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
SUMMARY = {'proposed_annotation_ref': 'hypothesis_' + 'a' * 24, 'record_refs': ['input_' + 'b' * 24],
           'path_depth': 1}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.relative_to(FOLDER).parts[0]
            not in CHILDREN}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert EPISODE.binding_path == 'evolutionary_history_evidence'
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {
        'evolutionary_history_evidence': 'evolutionary_history_evidence',
        'hpc': 'evolutionary_history_evidence/hpc_work_planning',
        'launch': 'evolutionary_history_evidence/execution_job_submission',
        'monitor': 'evolutionary_history_evidence/execution_progress_assessment',
        'results': 'evolutionary_history_evidence/execution_result_acquisition',
        'literature': 'evolutionary_history_evidence/published_evidence_assessment'}
    assert tuple(EPISODE.services) == ()
    assert all(re.fullmatch(r'[a-z][a-z0-9_]*', name) for name in EPISODE.tools)


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_with_children():
    assert files() == FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if path.relative_to(FOLDER).parts[0] in CHILDREN:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_return_form_requires_credit_and_finding_and_selects_the_declared_facts():
    form = EPISODE.return_form
    assert form.fields['credit'].type == 'number' and form.fields['credit'].required
    assert form.fields['finding'].required
    selected = form.select(('committed_record_refs',))
    assert selected.fields['committed_record_refs'].required
    with pytest.raises(FormError):
        form.select(('credit',))
    with pytest.raises(FormError):
        form.select(('hpc_credit',))


def test_the_own_commission_inherits_the_annotation_and_names_every_record():
    scope = {'subject_refs': ['input_' + 'c' * 24]}
    arguments = {'objective': 'narrower', 'purpose': 'compare', 'scope': scope, 'return_fields': [],
                 'assignment': {'selection': {}, 'evidence_refs': [], 'constraints': {}, 'context': {}}}
    message = TO_CHILD.msg_to_child('evolutionary_history_evidence', arguments, SUMMARY)
    assert isinstance(message, ChildMessage)
    assert message.assignment['proposed_annotation_ref'] == SUMMARY['proposed_annotation_ref']
    assert message.assignment['record_refs'] == [SUMMARY['proposed_annotation_ref'], scope['subject_refs'][0],
                                                 SUMMARY['record_refs'][0]]
    assert message.selection == ('committed_record_refs',)
    assert TO_CHILD.msg_to_child('evolutionary_history_evidence', arguments, {**SUMMARY, 'path_depth': 2}
                                 ).selection == ('committed_record_refs',)


def test_final_to_parent_returns_credit_and_the_controlled_finding_and_is_admitted():
    sheet = {'evidence_type': 'clade_placement', 'sheet_refs': ['source_' + 'e' * 24], 'attribution_state':
             'attributed_phylogeny_received', 'missing_input_count': 0, 'bootstrap_support': 0.92,
             'bootstrap_matches': 920, 'bootstrap_replicates': 1000, 'analyses_agreeing': 2}
    summary = {'a104_sheets': [sheet], 'a104_targets': [], 'credit_view': {'credit': 0.5, 'source_contribution_count': 1},
               'committed_record_refs': ['record_' + 'd' * 24]}
    result = FINAL.final_to_parent(summary, {'credit': 0.5}, ('committed_record_refs',))
    assert result['credit'] == 0.5 and result['committed_record_refs'] == ['record_' + 'd' * 24]
    assert result['finding']['clade_placement_count'] == 1 and result['finding']['history_comparison_count'] == 0
    admitted = FINAL.RETURN_FORM.select(('committed_record_refs',)).admit(result, 'return')
    assert FINAL.RETURN_FORM.select(('committed_record_refs',)).record_refs(admitted) == (
        'source_' + 'e' * 24, 'record_' + 'd' * 24)
    bare = FINAL.final_to_parent({**summary, 'a104_sheets': []}, {'credit': 0.0}, ())
    FINAL.RETURN_FORM.admit(bare, 'return')
    assert all(spec.type != 'text' or hasattr(spec, 'options') for spec in FINAL.SHEET_FORM.fields.values())


def test_the_credit_projector_follows_the_named_task_and_falls_back_to_the_general_projector():
    credit = importlib.import_module(PACKAGE + '.credit')
    library = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.grading.'
                                      'evolutionary_history_evidence.credit')
    for name, kind in (('panel_identity', library.A104PanelIdentityCredit),
                       ('alignment_suitability', library.A104AlignmentSuitabilityCredit),
                       ('robustness', library.A104RobustnessCredit),
                       ('another_task', library.A104EvolutionaryCredit)):
        assert type(credit.credit_projector({'a104_task': {'name': name}})) is kind
    assert type(credit.credit_projector({'a104_task': {'name': 'robustness', 'allowed_tasks': ['robustness']}})
                ) is library.A104RobustnessCredit
    assert type(credit.credit_projector({'a104_task': None})) is library.A104EvolutionaryCredit


def test_read_from_parent_reads_the_assignment_and_rejects_an_undeclared_selection():
    module = importlib.import_module(PACKAGE + '.messages.read_from_parent')
    assert set(module.ASSIGNMENT_FORM.fields) == {'selection', 'proposed_annotation_ref', 'evidence_refs',
                                                  'constraints', 'context', 'revision_origin', 'scope',
                                                  'record_refs'}
    with pytest.raises(Exception):
        module.read_from_parent({'selection': {}, 'evidence_refs': [], 'constraints': {}, 'context': {},
                                 'scope': {}}, {'purpose': 'p', 'initial_report': {}})


def test_read_from_child_takes_only_credit_finding_and_the_selected_refs_from_its_own_kind():
    module = importlib.import_module(PACKAGE + '.messages.read_from_child')
    result = {'credit': 1.5, 'finding': {'sheets': []}, 'committed_record_refs': ['x']}
    assert module.read_from_child('evolutionary_history_evidence', result, {}, None) == result
    assert module.read_from_child('evolutionary_history_evidence', {'credit': 1.5, 'finding': {}}, {}, None) == {
        'credit': 1.5, 'finding': {}}
