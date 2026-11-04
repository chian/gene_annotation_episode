"""Instructional coverage and recurring text delivery over synthetic cases.

These checks do not assert that a model interpreted an experiment correctly.
They check that the distinctions needed by concrete misleading source scenarios
remain in the recurring task rather than depending on previous model history.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.literature_assay_prompt import ASSAY_TASK
from gene_annotation_episode.literature_experimental_prompt import (
    VERSION, render_literature_experimental_prompt,
)


SCENARIOS = [
    (
        'An oxygen electrode reports turnover, while a separate overnight assay identifies a product.',
        ('oxygen_consumption', 'product_formation', 'quantitative productive coupling',
         'complementary product-identification experiment'),
    ),
    (
        'The figure labels Ctrl as no inhibitor; no no-enzyme measurement is supplied.',
        ('no-inhibitor reference', 'no-enzyme blank', 'reported net sample-minus-blank'),
    ),
    (
        'A tested protein replaces the reference in one experiment but coexists with it in another.',
        ('replacement', 'coexistence', 'residual reference activity', 'universal reliability multiplier'),
    ),
    (
        'A preparation is purified, but an endpoint may still include a contaminating contribution.',
        ('comparability', 'effect isolation', 'purified preparation', 'measured zero contaminating contribution'),
    ),
    (
        'A printed per-mg specific activity is available, but molar protein concentration is not.',
        ('per-mg specific activity', 'already normalized', 'molar e', 'keep missing operands null'),
    ),
    (
        'An error bar has no definition, and technical replicates share a calibration measurement.',
        ('missing covariance', 'technical repetitions', 'untyped error bar', 'estimated variance is not known variance'),
    ),
    (
        'Two different measured endpoints disagree with a broad conclusion in the same paper.',
        ('same scoped endpoint', 'separate conditions or endpoints', 'unknown', 'conflicting'),
    ),
    (
        'An expression host is named beside a truncated construct, without native protein boundaries.',
        ('source organism distinct from an expression host', 'assayed construct distinct',
         'full-length or native protein', 'use null'),
    ),
]


@pytest.mark.parametrize('source_scenario,needed_distinctions', SCENARIOS,
                         ids=['oxygen-versus-product', 'control-role', 'replacement-versus-coexistence',
                              'purity-versus-attribution', 'normalization', 'uncertainty-and-dependence',
                              'scope-of-contradiction', 'source-and-construct'])
def test_task_supplies_distinctions_needed_for_misleading_synthetic_source(
        source_scenario, needed_distinctions):
    assert source_scenario
    task = ASSAY_TASK.casefold()
    for distinction in needed_distinctions:
        assert distinction.casefold() in task


def _state(source_text):
    return {
        'literature_experimental_work': {'version': VERSION, 'aspect': 'source_assay'},
        'goal': {'objective': 'Determine which experimental measurements support this source assay.'},
        'scope': {},
        'literature_assignment': {'source_refs': [], 'question_context_refs': []},
        'last_local_outcome': {'status': 'completed', 'result': {'text': source_text}},
        'feedback': None,
        'child_reports': [],
    }


def test_complete_assay_instructions_recur_after_source_outcome_repair_and_lookup():
    initial = _state('Synthetic source: Protein P, oxygen electrode, preparation 1.')
    repaired = deepcopy(initial)
    repaired['feedback'] = {'code': 'source_witness_mismatch', 'field': 'primitives.q'}
    repaired['last_local_outcome']['result']['text'] = 'Synthetic source: Ctrl omits inhibitor.'
    lookup = [{'result': {'text': 'Synthetic neighboring caption: technical duplicate measurements.'}}]
    for state, lookups in ((initial, ()), (repaired, ()), (repaired, lookup)):
        original = deepcopy(state)
        text = render_literature_experimental_prompt(state, ASSAY_TASK, lookup_results=lookups)
        task, steering = text.split('\n\nSTEERING\n')
        assert task.startswith('TASK\n\n')
        assert ASSAY_TASK in task
        assert ASSAY_TASK not in steering
        assert state['last_local_outcome']['result']['text'] in steering
        assert state == original
        if lookups:
            assert 'technical duplicate measurements' in steering


def test_operand_meanings_do_not_include_sheet_or_numeric_scoring_implementation():
    # This is guidance for recognizing scientific operands, not a pasted sheet.
    for meaning in ('q only', 'g only', 'k only', 'e to', 'u and v'):
        assert meaning in ASSAY_TASK.casefold()
    assert 'deterministic readers and calculators' in ASSAY_TASK
    for implementation in ('tanh(', 'JΣJ', 'max(0,', 'effect_precision', 'source_presence_index'):
        assert implementation not in ASSAY_TASK
    assert 'source_interpretation' in ASSAY_TASK
    assert 'exact quote proves' in ASSAY_TASK.casefold()
    assert 'not prove the scientific interpretation' in ASSAY_TASK
    assert 'Sequence and structural correspondence remain separate work' in ASSAY_TASK
