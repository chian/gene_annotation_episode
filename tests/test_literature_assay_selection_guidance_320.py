"""Recurring assay-selection guidance through both real prompt renderers.

Synthetic state exercises selection and presentation; it does not establish
scientific accuracy or claim that every described grader is implemented.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.decision_context import INSTRUCTIONS
from gene_annotation_episode.literature_completion_time_prompt import COMPLETION_TIME_TASK
from gene_annotation_episode.literature_assay_grading import CRITERION_QUESTIONS
from gene_annotation_episode.literature_assay_grading_prompt import ASSAY_GRADING_TASK
from gene_annotation_episode.literature_episodes import _population_catalog
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import render_reference_evidence_parent_prompt
from gene_annotation_episode.literature_task_selection import (
    A105_ASSAY_SELECTION_TASK, selected_literature_task_sections,
)
from test_literature_experimental_prompt import state as child_state
from test_literature_reference_parent_prompt import state as parent_state


def presentation(parent, profile=False):
    state = parent_state() if parent else child_state()
    renderer = render_reference_evidence_parent_prompt if parent else render_literature_experimental_prompt
    if profile:
        state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    return state, renderer


@pytest.mark.parametrize('parent', [False, True], ids=['child', 'parent'])
@pytest.mark.parametrize('profile', [False, True], ids=['direct-contract', 'contract-lookup'])
def test_selection_hierarchy_recurs_in_task_without_becoming_factual_steering(parent, profile):
    state, renderer = presentation(parent, profile)
    later = deepcopy(state)
    later['feedback'] = {'code': 'source_layout_unsupported'}
    later['last_local_outcome'] = {'status': 'invalid', 'result': None}
    lookup = {'status': 'completed', 'result': {'text': 'The sampling unit remains unreported.'}}
    original = deepcopy((state, later, lookup))
    for frame, lookups in ((state, ()), (later, ()), (later, (lookup,))):
        text = renderer(frame, INSTRUCTIONS, lookup_results=lookups)
        task, steering = text.split('\n\nSTEERING\n')
        assert task.count(A105_ASSAY_SELECTION_TASK) == 1
        assert A105_ASSAY_SELECTION_TASK not in steering
        assert 'A105 experimental evidence subscore → subscoring grader → subscoring reader' in task
        assert 'source_layout_unsupported' not in task
        if frame is later:
            assert 'source_layout_unsupported' in steering
        if lookups:
            assert 'The sampling unit remains unreported.' in steering
            assert 'The sampling unit remains unreported.' not in task
    assert (state, later, lookup) == original


@pytest.mark.parametrize('parent', [False, True], ids=['child', 'parent'])
def test_caller_supplied_shared_guidance_is_not_duplicated(parent):
    state, renderer = presentation(parent)
    text = renderer(state, INSTRUCTIONS + '\n' + A105_ASSAY_SELECTION_TASK + '\nCaller-selected scope.')
    task, steering = text.split('\n\nSTEERING\n')
    assert task.count(A105_ASSAY_SELECTION_TASK) == 1
    assert 'Caller-selected scope.' in task
    assert A105_ASSAY_SELECTION_TASK not in steering


@pytest.mark.parametrize('parent', [False, True], ids=['child', 'parent'])
def test_available_narrow_readers_keep_their_limits_without_selecting_an_assay(parent):
    state, renderer = presentation(parent)
    names = {'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate'}
    operations = [row for row in _population_catalog(
        parent_depletion_population=True, stoichiometric_balance_population=True) if row['name'] in names]
    assert len(operations) == 2
    if parent:
        state['reference_evidence_parent']['child_population_operations'] = operations
    else:
        state['tools'] = operations
    before = selected_literature_task_sections(state)
    task = renderer(state, INSTRUCTIONS).split('\n\nSTEERING\n')[0]
    assert not before
    assert selected_literature_task_sections(state) == before
    assert 'not a general substrate-depletion table reader' in task
    assert 'Figure 2D XLSX' in task
    assert 'Compound, submixture and time select source rows, not assay types.' in task
    assert 'Selected scientific instructions:' not in task


@pytest.mark.parametrize('parent', [False, True], ids=['child', 'parent'])
def test_actual_measurement_request_selects_same_method_with_different_case_identities(parent):
    state, renderer = presentation(parent)
    state['literature_assignment'] = {
        'requested_completion_time_components': ['completion_time_ratio'],
        'source_refs': ['source_example_a'],
        'context': {'case': 'example A', 'molecule': 'enzyme A', 'substrate': 'substrate A'},
    }
    other = deepcopy(state)
    other['literature_assignment']['source_refs'] = ['source_example_b']
    other['literature_assignment']['context'] = {
        'case': 'example B', 'molecule': 'enzyme B', 'substrate': 'substrate B'}
    expected = (('literature_completion_time_cells', COMPLETION_TIME_TASK),)
    for frame in (state, other):
        assert selected_literature_task_sections(frame) == expected
        task, steering = renderer(frame, INSTRUCTIONS).split('\n\nSTEERING\n')
        assert task.count(A105_ASSAY_SELECTION_TASK) == 1
        assert task.count(COMPLETION_TIME_TASK) == 1
        assert COMPLETION_TIME_TASK not in steering


@pytest.mark.parametrize('parent', [False, True], ids=['child', 'parent'])
@pytest.mark.parametrize('route', ['assignment', 'return', 'owned', 'attempt', 'own_result'])
def test_selected_assay_grader_gets_complete_scientific_task_through_actual_selection_routes(parent, route):
    state, renderer = presentation(parent)
    namespace = 'literature_assay_grading_cells'
    if route == 'assignment':
        state['literature_assignment'] = {'requested_assay_grading_components': ['measured_effect']}
    elif route == 'return':
        state['requested_form'] = {'type': 'object', 'properties': {
            'assessment': {'$ref': 'episode-fact:' + namespace}}}
    elif route == 'owned':
        state['literature_owned_population_sources'] = [namespace]
    elif route == 'attempt':
        state['literature_selected_population_attempt'] = {
            'status': 'invalid', 'tool': 'literature.assay_grading.populate', 'arguments': {}}
    else:
        state['last_local_outcome'] = {'status': 'completed', 'result': {
            'sheet_ref': 'source_selected_assessment', 'evaluation_scope': 'assay_type_experimental_evidence',
            'cells': {}}}
    assert selected_literature_task_sections(state) == ((namespace, ASSAY_GRADING_TASK),)
    task, steering = renderer(state, INSTRUCTIONS).split('\n\nSTEERING\n')
    assert task.count(ASSAY_GRADING_TASK) == 1
    assert ASSAY_GRADING_TASK not in steering
    assert all(question in task for question in CRITERION_QUESTIONS.values())
    assert 'known-variance normal' in task and 'Student-t residual model' in task
    assert 'An overall experimental-evidence score is required' in task
    assert 'experiment_ref' in task and 'revised extraction remains tied to its original experiment' in task
    assert 'Use ligand_binding' in task and 'Use transport_response' in task
    assert 'Use protein_signal' in task and 'Use protein_amount' in task
    assert 'do not multiply them into an effect that already includes their corrections' in task
    if route == 'assignment' and not parent:
        assert 'requested_assay_grading_components' in task and 'measured_effect' in task


def test_assay_grader_catalog_entry_alone_does_not_select_its_scientific_task():
    state, renderer = presentation(False)
    state['tools'] = [{'name': 'literature.assay_grading.populate', 'description': 'Available grading operation.'}]
    state['available_report_facts'] = {'literature_assay_grading_cells': {'meaning': 'Available assessment.'}}
    assert not selected_literature_task_sections(state)
    task = renderer(state, INSTRUCTIONS).split('\n\nSTEERING\n')[0]
    assert A105_ASSAY_SELECTION_TASK in task
    assert ASSAY_GRADING_TASK not in task
