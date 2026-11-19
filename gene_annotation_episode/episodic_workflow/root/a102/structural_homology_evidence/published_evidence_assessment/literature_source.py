"""The A102 literature decision source and continuation on the generic runner.

The literature source is the A102 unit source (``runtime_head.StructuralHomologyEvidenceSource``)
with what is the literature episode's own:

- its commission: the parent's literature ``question`` and the selected source
  operations, instead of the head's A102 task, proposed annotation and thought pattern;
- its credit: A102's native structural correspondence over the records it received
  (``literature_binding.literature_credit``), opened at the credit of no received record;
- its instructions: the A102 investigation instructions, the A102 literature lead and the
  binding's own role ``instruction``;
- its children: a child commission names a declared literature slot, its objective, a
  sub-scope and the child's own assignment form (its question and the source operations
  it may use, C6), admitted against that form before acquisition.

Each unit is one model selection, recorded through ``bound.recorder``
(``decision.<position>.<attempt>``, ``outcome.<position>``). A response that fails
admission creates no unit; the model decides again with that feedback. Every executed
outcome, including an invalid or failed one, enters the iterator with the credit measured
after it and its progress receipt. A child's admitted finding hands its ``record_refs`` to
this episode; child credits are never summed into its own.
"""
from __future__ import annotations

import math

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from ..runtime_continuation import A102Continuation, episode_epoch
from ..runtime_head import Record, StructuralHomologyEvidenceSource, _State, head_credit

LITERATURE_LEAD = (
    'For A102, identify the actual molecule, construct, chain and residue numbering of a deposited or described '
    'structure before using a source claim. Keep experimental structure measurements, fitted coordinates, predicted '
    'models, structural correspondence to the target and the authors\' mechanistic interpretation distinct and '
    'source-grounded.\n'
    'This is an iterative literature investigation of the commissioned question. Choose one action: a source '
    'operation among the commissioned tools, a reasoning commit of a source-grounded interpretation, or a child '
    'commission in a declared literature slot with its objective, a sub-scope and the assignment its own form '
    'declares (its question and the source operations it may use). Earlier outcomes and returned child findings '
    'inform later choices; no child order, reading quota or complete-document requirement is prescribed. Preserve '
    'the source\'s actual subject, experimental conditions, representation, version and UTF-8 byte anchors. '
    'Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications '
    'can advance the investigation. Navigation, byte coverage and repeated reading earn no credit by themselves. The '
    'configured controller owns continuation; there is no stop action.\n')


def literature_controller(binding, bound, collaborators):
    """The declared yield controller over the literature credit, opened at the credit of no received record."""
    from yield_control import (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                               YieldParameters)
    if bound.binding_path != binding.binding_path:
        raise ContractError('a102_literature_controller_opened_for_another_binding:' + bound.binding_path)
    store = collaborators['store']
    if binding.tool_registry.store is not store:
        raise ContractError('a102_tool_registry_is_not_over_the_run_store')
    projector, declaration = binding.credit_projector, binding.continuation
    scope = store.validate_scope(bound.assignment['scope'])
    initial, _ = head_credit(projector, store, scope, None, ())
    parameters = YieldParameters(**declaration['parameters'])
    epoch = episode_epoch(bound)
    if declaration['kind'] == 'bounded_quality':
        controller = BoundedQualityYieldController(epoch, initial, declaration['cutoff'],
                                                   projector.native_score_maximum, parameters)
    elif declaration['kind'] == 'completion':
        controller = CompletionYieldController(epoch, initial, declaration['cutoff'],
                                               projector.as_record()['maximum_credit'], parameters)
    else:
        controller = AccumulationYieldController(epoch, initial, declaration['cutoff'], parameters)
    return A102Continuation(controller)


class LiteratureSource(StructuralHomologyEvidenceSource):
    """An A102 literature episode's model-selected units over its own tools, records and literature children."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a102_tool_registry_is_not_over_the_run_store')
        try:
            self._scope = self._store.validate_scope(bound.assignment['scope'])
        except ContractError as error:
            raise ContractError('a102_literature_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error
        # The literature credit has no commissioned A102 task or proposed annotation.
        self._task = None
        self._proposed = None
        self._projector = binding.credit_projector
        self._builders = child_builders
        for slot, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a102_child_return_form_differs:' + slot)
        if bound.report_form != binding.return_form:
            # A literature episode reports exactly its credit and finding; no decision fills an added field.
            raise ContractError('a102_literature_report_form_must_be_its_return_form:' + binding.binding_path)
        self._state = _State()

    def instructions(self):
        return (LITERATURE_LEAD + self._binding.instruction + '\n' + INSTRUCTIONS + '\n'
                + REASONING_COMMIT_REQUIREMENT)

    def decision_context(self, view):
        credit, credit_view = self.credit_view()
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'binding_path': self._binding.binding_path,
            'scope': self._scope,
            'evidence_axis': 'A102',
            'question': self._bound.assignment['question'],
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'current_credit': credit,
            'credit_binding': self._projector.as_record(),
            'credit_details': {key: value for key, value in credit_view.items() if key != 'credit'},
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self._tool_catalog().items())},
            'child_options': self._child_options(),
        }

    def result(self, record):
        """The literature return: its own credit and the records its findings rest on."""
        self._catch_up(record.units_consumed)
        credit, view = self.credit_view()
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a102_literature_credit_must_be_finite')
        refs = list(self._state.received_refs)
        assessments = [ref for ref in refs if self._store.get(ref).get('record_type') == 'assessment']
        return Record({'credit': credit, 'finding': {
            'scope': self._scope, 'question': self._bound.assignment['question'],
            'tools': list(self._bound.assignment['tools']), 'record_refs': refs, 'evidence_refs': assessments,
            'credit_binding': self._projector.as_record(),
            'credit_details': {key: value for key, value in view.items() if key != 'credit'},
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['LITERATURE_LEAD', 'LiteratureSource', 'literature_controller']
