"""The A107 literature episodes' iteration cycle on the generic runner.

A literature episode runs the A107 unit cycle (``head_cycle.HeadCycleSource``) with what
is its own:

- no thought pattern: its commission carries the parent's literature ``assignment``
  (question and context), presented with every decision;
- its instructions: the A107 axis instructions, the A107 literature lead and its role
  ``instruction``;
- its own ``A107ToolRegistry`` and the commission's selected source operations.

Each unit is one model selection (a selected source operation, a reasoning commit or a
child commission in a declared literature slot), recorded through ``bound.recorder``;
an inadmissible response creates no unit and is shown as feedback; every executed
outcome, including an invalid or failed one, enters the controller with the episode's
finding-progress credit and its progress receipt. The result is
``{'credit': current - opening, 'finding': <projection with known_assessment_refs>}``,
the form an A107 parent receives.
"""
from __future__ import annotations

from method_loop import Episode

from ..head_cycle import (CYCLE_GUIDANCE, PROVIDER_METHODS, STORE_METHODS, CycleError, HeadCycleSource,
                          child_slot_options, collaborator, head_result, head_settings, opening_credit,
                          visible_assessment_refs)
from ..axis_instructions import INSTRUCTIONS

LITERATURE_LEAD = (
    'This is an iterative A107 literature investigation of the commissioned question. Choose one action: a '
    'source operation among the commissioned tools, a reasoning commit of a source-grounded interpretation, or a '
    'child commission in a declared literature slot (its question as assignment and the source operations it may '
    'use as tools). Earlier outcomes and returned child findings inform later choices; no child order, reading '
    'quota or complete-document requirement is prescribed. Discover requirements from actual sources and '
    'preserve the assayed subject, partner identity, construct, endpoint and conditions, the source '
    'representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the '
    'fixed target. Negative findings and qualifications can advance the investigation. Navigation, byte coverage '
    'and repeated reading earn no credit by themselves.')


class LiteratureCycleSource(HeadCycleSource):
    """An A107 literature episode's decision source (``next(view)``), executing each selected action."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound, self._builders = binding, bound, child_builders
        self._store = collaborator(collaborators, 'store', STORE_METHODS)
        # The binding's own tool registry (C4), built by the home factory over the run's shared store.
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise CycleError('a107_tool_registry_is_not_over_the_run_store')
        self._provider = collaborator(collaborators, 'model_provider', PROVIDER_METHODS)
        self._settings = head_settings(collaborators, binding.binding_path)
        self._scope = self._store.validate_scope(bound.assignment['scope'])
        self._selected_tools = tuple(bound.assignment['tools'])
        self._question = bound.assignment['assignment']
        self._slots = child_slot_options(child_builders)
        self._objective = bound.request.message.as_record()['objective']
        self._position = None
        self._known, self._received = set(), set()
        self._last_outcome, self._feedback = None, None

    def instructions(self):
        return '\n\n'.join((INSTRUCTIONS['A107'], LITERATURE_LEAD, self._binding.instruction, CYCLE_GUIDANCE))

    def context(self, position, attempt, controller_state):
        view = self._store.reasoning_view(self._scope)
        shown = visible_assessment_refs(view)
        self._known.update(shown)
        self._received.update(shown)
        self._received.update(row['id'] for field in ('observations', 'sources', 'hypotheses', 'annotations')
                              for row in view.get(field, ()))
        return {'version': 'a107_literature_cycle_v1', 'binding_path': self._binding.binding_path,
                'objective': self._objective, 'scope': self._scope, 'assignment': self._question,
                'position': position, 'attempt': attempt,
                'credit': controller_state.current_credit,
                'records': view, 'tool_catalog': self.catalog(),
                'reasoning_schema': self._store.reasoning_schema(), 'child_slots': self._slots,
                'last_outcome': self._last_outcome, 'feedback': self._feedback}


def build_literature_episode(binding, grain, bound, collaborators, child_builders):
    """An A107 literature Episode: its own decision source, executed units and finding-progress result."""
    source = LiteratureCycleSource(binding, bound, collaborators, child_builders)

    def build_result(record):
        # The state recorded after the last completed unit (or the opening baseline),
        # whether the units ran now or replayed on resume.
        source._restore(record.units_consumed)
        return head_result(source._store, source._scope, source._settings,
                           opening_credit(bound, source._store, source._settings), source._known)
    return Episode(grain=grain, key=bound.key, source=source, request=bound.request, build_result=build_result)


__all__ = ['LITERATURE_LEAD', 'LiteratureCycleSource', 'build_literature_episode']
