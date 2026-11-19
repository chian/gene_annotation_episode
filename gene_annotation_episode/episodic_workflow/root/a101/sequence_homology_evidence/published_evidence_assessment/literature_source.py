"""The A101 literature decision source and continuation on the generic runner.

The literature source is the A101 unit source (``runtime_source.SequenceHomologyEvidenceSource``)
with what is the literature episode's own:

- its receipts: a literature episode commissioned by an A101 head or another A101
  literature episode inherits that parent's frozen receipt prefix; any other one
  (an entry) starts from its scope's subjects;
- its instructions: the A101 investigation instructions, the A101 literature lead and
  the binding's own role ``instruction``;
- its decision context: the commissioned ``question`` instead of the head's evidence
  task and thought pattern.

Each unit is one model selection (a selected source operation, a reasoning commit or a
child commission in a declared literature slot), recorded through ``bound.recorder``
(``decision.<position>.<attempt>``, ``outcome.<position>``). A response that fails
admission creates no unit; every executed outcome, including an invalid or failed one,
enters the iterator with the credit measured after it and its progress receipt. The
returned records are delivered to this episode's receipts; credit is A101's native
sequence correspondence over them. A child's admitted finding feeds this episode's
receipts; child credits are never summed into its own.
"""
from __future__ import annotations

from episode_runtime import grain_name_for
from method_loop import EpisodeRef

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from ..contract_binding import RETURN_FORM
from ..native_correspondence_credit import A101SequenceCredit
from ..runtime_credit import HEAD_BINDING_PATH, head_credit_view, head_scope, head_store
from ..runtime_source import SequenceHomologyEvidenceSource, _State

LITERATURE = HEAD_BINDING_PATH + '/published_evidence_assessment'
_STRATEGY = LITERATURE + '/evidence_search_strategy_improvement'
_RELEVANCE = _STRATEGY + '/source_relevance_assessment'
_EXAMINATION = _RELEVANCE + '/source_evidence_examination'
# The A101 episodes whose receipts a literature episode inherits from when they commission it.
RECEIPT_PARENT_GRAINS = frozenset(grain_name_for(path) for path in (
    HEAD_BINDING_PATH, LITERATURE, _STRATEGY, _RELEVANCE, _EXAMINATION, _EXAMINATION + '/table_evidence_extraction',
    _EXAMINATION + '/source_coverage_improvement', _EXAMINATION + '/passage_evidence_extraction'))
INITIAL_CREDIT_DECISION = 'a101.literature.initial_credit'
LITERATURE_LEAD = (
    'For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep '
    'alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, '
    'and their applicability to the target distinct and source-grounded.\n'
    'This is an iterative literature investigation. Choose one action: a source operation among the commissioned '
    'tools, a reasoning commit of a source-grounded interpretation, or a child commission in a declared literature '
    'slot. A child commission names its slot, its objective, a Store scope within this scope and the assignment its '
    'own form declares (its question and the source operations it may use). Earlier outcomes and returned child '
    'findings inform later choices; no child order, reading quota or complete-document requirement is prescribed. '
    'Preserve the source\'s actual subject, experimental conditions, representation, version and UTF-8 byte '
    'anchors. Distinguish source claims from their applicability to the fixed target. Negative findings and '
    'qualifications can advance the investigation. Navigation, byte coverage and repeated reading earn no '
    'credit by themselves. The configured controller owns continuation; there is no stop action.')


def receipt_parent(bound):
    """The commissioning A101 head or literature episode's id, or None for any other commissioner."""
    if len(bound.path) > 1 and bound.path[-2][0] in RECEIPT_PARENT_GRAINS:
        return EpisodeRef(bound.run_id, tuple(bound.path[:-1])).episode_id
    return None


def open_literature_receipts(bound, store):
    """Bind this literature episode's receipts once and record its initial knowledge."""
    receipts = EpisodeReceipts(store, bound.run_id)
    parent = receipt_parent(bound)
    receipts.bind(bound.episode_id, parent)
    if parent is None:
        receipts.receive(bound.episode_id, list(head_scope(bound, store)['subject_refs']), kind='initial')
    return receipts


def literature_controller(binding, bound, collaborators):
    """The literature episode's continuation, opened with its recorded opening credit."""
    if bound.binding_path != binding.binding_path:
        raise ContractError('a101_literature_controller_opened_for_another_binding:' + bound.binding_path)
    store = head_store(binding, collaborators)
    receipts = open_literature_receipts(bound, store)
    initial = bound.recorder.recorded(INITIAL_CREDIT_DECISION,
                                      lambda: head_credit_view(bound, store, receipts)['credit'])
    return binding.head_yield_controller(bound.episode_id, initial)


class LiteratureSource(SequenceHomologyEvidenceSource):
    """An A101 literature episode's model-selected units over its own tools, receipts and children."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = head_store(binding, collaborators)
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        self._scope = head_scope(bound, self._store)
        self._receipts = open_literature_receipts(bound, self._store)
        self._builders = child_builders
        if bound.report_form.as_record() != RETURN_FORM.as_record():
            # A literature episode reports exactly its credit and finding; no decision fills an added field.
            raise ContractError('a101_literature_report_form_must_be_its_return_form:' + bound.binding_path)
        for slot, builder in child_builders.items():
            if builder.return_form != RETURN_FORM:
                raise ContractError('a101_child_return_form_differs:' + slot)
        self._state = _State()

    def decision_context(self, view, credit_view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'binding_path': self._binding.binding_path,
            'scope': self._scope,
            'question': self._bound.assignment['question'],
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'current_credit': credit_view['credit'],
            'native_correspondence': {key: credit_view[key] for key in
                                      ('a101_sheet', 'interpretation', 'detail_pages')},
            'credit_binding': A101SequenceCredit().as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self.tool_catalog().items())},
            'child_options': {slot: {'binding_path': builder.binding_path,
                                     'assignment_form': builder.assignment_form.as_record()}
                              for slot, builder in sorted(self._builders.items())},
        }

    def instructions(self):
        return '\n'.join((INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, LITERATURE_LEAD, self._binding.instruction))


__all__ = ['INITIAL_CREDIT_DECISION', 'LITERATURE_LEAD', 'LiteratureSource', 'literature_controller',
           'open_literature_receipts', 'receipt_parent']
