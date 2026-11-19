"""Configured yield declarations open the real yield_control controllers the runner accepts."""
import pytest

from method_loop import Controller
from yield_control import AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.configuration.yield_declarations import (
    checked_yield_declaration, open_yield_controller)

DEFINITION = {'kind': 'native_sequence_correspondence', 'unit': 1.0}
DECLARATIONS = {'A101:native_sequence_correspondence': {
    'kind': 'bounded_quality', 'cutoff': 0.02, 'parameters': {'uncertainty_alpha': 0.1},
    'credit_definition': DEFINITION}}


def test_declaration_is_checked_against_its_credit_definition_and_kind():
    task = 'A101:native_sequence_correspondence'
    found = checked_yield_declaration(DECLARATIONS, task, credit_definition=dict(DEFINITION),
                                      yield_method='bounded_quality', code_prefix='a101_head')
    assert found is DECLARATIONS[task]
    with pytest.raises(ValueError, match='^a101_head_yield_binding_missing_for_task:A101:other$'):
        checked_yield_declaration(DECLARATIONS, 'A101:other', credit_definition=DEFINITION,
                                  yield_method='bounded_quality', code_prefix='a101_head')
    with pytest.raises(ValueError, match='^scientific_yield_credit_definition_mismatch:'):
        checked_yield_declaration(DECLARATIONS, task, credit_definition={**DEFINITION, 'unit': 2.0},
                                  yield_method='bounded_quality', code_prefix='scientific')
    with pytest.raises(ValueError, match='^scientific_yield_method_credit_mismatch:'):
        checked_yield_declaration(DECLARATIONS, task, credit_definition=DEFINITION,
                                  yield_method='accumulation', code_prefix='scientific')
    with pytest.raises(ValueError, match='^a101_head_yield_bindings_not_configured$'):
        checked_yield_declaration(None, task, credit_definition=DEFINITION, yield_method='bounded_quality',
                                  code_prefix='a101_head')


def test_each_kind_opens_its_own_controller_that_the_method_loop_accepts():
    common = {'epoch': 'episode-id', 'initial_credit': 1.0, 'cutoff': 0.05, 'parameters': {'uncertainty_alpha': 0.1}}
    accumulation = open_yield_controller('accumulation', **common)
    bounded = open_yield_controller('bounded_quality', maximum_credit=4.0, **common)
    completion = open_yield_controller('completion', target=3.0, **common)
    assert type(accumulation) is AccumulationYieldController
    assert type(bounded) is BoundedQualityYieldController and bounded.maximum_credit == 4.0
    assert type(completion) is CompletionYieldController and completion.target == 3.0
    for controller in (accumulation, bounded, completion):
        assert isinstance(controller, Controller)
        assert type(controller.state().stop) is bool
        assert controller.state().current_credit == 1.0  # the opening credit is kept unchanged
        assert controller.settings.uncertainty_alpha == 0.1 and controller.cost == 0.05


def test_operands_of_another_kind_or_an_unknown_kind_raise():
    common = {'epoch': 'e', 'initial_credit': 0.0, 'cutoff': 0.05, 'parameters': {}}
    with pytest.raises(ValueError, match='accumulation_yield_takes_no_maximum_or_target'):
        open_yield_controller('accumulation', target=1.0, **common)
    with pytest.raises(ValueError, match='bounded_quality_yield_requires_its_declared_maximum_only'):
        open_yield_controller('bounded_quality', **common)
    with pytest.raises(ValueError, match='completion_yield_requires_its_commission_target_only'):
        open_yield_controller('completion', maximum_credit=1.0, **common)
    with pytest.raises(ValueError, match='yield_kind_not_available'):
        open_yield_controller('remaining_commissioned_credit', **common)
    with pytest.raises(TypeError, match='minimum_history'):
        open_yield_controller('accumulation', **{**common, 'parameters': {'minimum_history': 3}})
