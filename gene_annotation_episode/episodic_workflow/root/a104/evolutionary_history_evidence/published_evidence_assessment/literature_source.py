"""The A104 literature decision source on the generic runner.

The literature source is the A104 unit source (``runtime_source.EvolutionaryHistoryEvidenceSource``)
with what is the literature episode's own:

- its commission: the parent's literature question (``role_assignment``) and the
  selected source operations, instead of the head's evidence task, thought pattern and tools;
- its instructions: the A104 literature lead, the binding's role ``instruction`` and the
  A104 investigation instructions;
- its children: a child commission names a declared literature slot, its objective, a
  sub-scope, its question and the source operations it may use (C6, chosen among the
  child's own declared options), admitted against the child's form before acquisition.
  Each child is commissioned with its own return form plus the record references its
  findings rest on (C5, ``runtime_source.descendant_report``).

Each unit is one model selection, recorded through ``bound.recorder``
(``decision.<position>.<attempt>``, ``outcome.<position>``). A response that fails
admission creates no unit; the model decides again with that feedback. Every executed
outcome, including an invalid or failed one, enters the iterator with the credit measured
after it and its progress receipt. A child's reported ``evidence_refs`` become records this
episode holds; child credits are never summed into its own.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

from jsonschema import Draft202012Validator

from episode_runtime import Commission
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.runtime_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import decode_response
from ..runtime_bindings import UnitInput
from ..runtime_source import (EVIDENCE_REFS, EvolutionaryHistoryEvidenceSource, _State, _embedded,
                              descendant_report, head_credit_projector, store_scope)

LITERATURE_LEAD = (
    'For A104, identify the actual sequences, taxa, gene or protein family and the phylogenetic or comparative '
    'method behind a source claim before using it. Keep orthology and paralogy inferences, gene-tree and '
    'species-tree relationships, conservation measurements, ancestral reconstructions, horizontal transfer claims '
    'and their applicability to the target distinct and source-grounded.\n'
    'This is an iterative literature investigation of the commissioned question (role_assignment). Choose one '
    'action: a source operation among the commissioned tools, a reasoning commit of a source-grounded '
    'interpretation, or a child commission in a declared literature slot with its objective, a sub-scope, its '
    'question and the source operations it may use. Earlier outcomes and returned child findings inform later '
    'choices; no child order, reading quota or complete-document requirement is prescribed. Preserve the source\'s '
    'actual subject, experimental conditions, representation, version and UTF-8 byte anchors. Distinguish source '
    'claims from their applicability to the fixed target. Negative findings and qualifications can advance the '
    'investigation. Navigation, byte coverage and repeated reading earn no credit by themselves. The configured '
    'controller owns continuation; there is no stop action.\n')


class LiteratureSource(EvolutionaryHistoryEvidenceSource):
    """An A104 literature episode's model-selected units over its own tools and literature children."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a104_tool_registry_is_not_over_the_run_store')
        self._scope = store_scope(self._store, bound.assignment['scope'])
        self._projector = head_credit_projector()
        self._builders = dict(child_builders)
        for slot, builder in self._builders.items():
            if 'tools' not in builder.assignment_form.fields or 'role_assignment' not in builder.assignment_form.fields:
                raise ContractError('a104_literature_child_assignment_requires_role_assignment_and_tools:' + slot)
        self._reports = {slot: descendant_report(builder) for slot, builder in self._builders.items()}
        extra = set(bound.report_form.fields) - set(binding.return_form.fields) - {EVIDENCE_REFS}
        if extra:
            # A literature episode supplies its credit, finding and the records they rest on; nothing else.
            raise ContractError('a104_literature_report_form_field_not_held:' + ','.join(sorted(extra)))
        self._state = _State(self._scope)

    def _controller_input(self, position, outcome):
        """The credit measured after unit ``position``, its progress receipt and the unit's kind and status."""
        credit = self.credit_view()['credit']
        return UnitInput({'credit': credit, 'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        for slot, builder in sorted(self._builders.items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': slot},
                                'objective': {'type': 'string', 'minLength': 1,
                                              'description': 'The child episode objective.'},
                                'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                                'role_assignment': {'type': 'object',
                                                    'description': "The child's literature question and context."},
                                'tools': {'type': 'array', 'uniqueItems': True,
                                          'items': {'enum': list(builder.assignment_form.fields['tools'].options)}}}))
        return obj({'selection': {'anyOf': options}})

    def child_options(self):
        """Each declared literature child slot with what commissioning it does."""
        from ..runtime_bindings import ROLE_TEXT
        options = {}
        for slot, builder in self._builders.items():
            goal, unit, result = ROLE_TEXT[slot]
            options[slot] = {'binding_path': builder.binding_path, 'improves': goal, 'unit': unit, 'returns': result,
                             'report_information': dict(self._reports[slot][0]['information'])}
        return options

    def decision_context(self, view, credit_view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'binding_path': self._binding.binding_path,
            'scope': self._scope,
            'role_assignment': dict(self._bound.assignment['role_assignment']),
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.known_record_refs),
            'current_credit': credit_view['credit'],
            'target_sheets': credit_view['target_sheets'],
            'source_contribution_count': credit_view['source_contribution_count'],
            'credit_binding': self._projector.as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self._tool_catalog().items())},
            'child_options': self.child_options(),
        }

    def instructions(self):
        return (LITERATURE_LEAD + self._binding.instruction + '\n' + INSTRUCTIONS + '\n'
                + REASONING_COMMIT_REQUIREMENT)

    # -- decisions ----------------------------------------------------------------
    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a104_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child':
            # The child's own scope and assignment form checks, before acquisition (a failure is a rejection).
            self._commission(selection)
        return selection

    def _commission(self, selection):
        slot = selection['role']
        builder = self._builders[slot]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        assignment = {'scope': scope, 'role_assignment': selection['role_assignment'], 'tools': selection['tools'],
                      **builder.assignment_form.declared}
        assignment = builder.assignment_form.admit(assignment, 'a104_literature_child_assignment:' + slot)
        contract, form = self._reports[slot]
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'], result_contract=contract)
        return Commission(EpisodeRequest(goal, UnitInput({'scope': scope}), ReportContract(**contract)), assignment, form)

    # -- execution ------------------------------------------------------------------
    def _child(self, position, selection):
        slot = selection['role']
        builder = self._builders[slot]
        commission = self._commission(selection)
        contract, form = self._reports[slot]
        child = builder(slot + '_' + str(position), commission)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            refs = admitted[EVIDENCE_REFS]
            if any(type(ref) is not str for ref in refs):
                raise ContractError('a104_child_report_requires_record_references')
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': slot, 'record_refs': list(refs),
                'child_credit': admitted['credit'],
                'child_report': {name: admitted[name] for name in admitted if name not in ('credit', EVIDENCE_REFS)},
                'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in contract['information']}
        return ChildEpisodeUnit(child, receive, report)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The literature return: its A104 credit and the findings it holds."""
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a104_literature_credit_must_be_finite')
        refs = list(self._state.known_record_refs)
        returned = {'credit': credit, 'finding': {
            'scope': self._scope, 'role_assignment': dict(self._bound.assignment['role_assignment']),
            'tools': list(self._bound.assignment['tools']), 'known_record_refs': refs, 'evidence_refs': refs,
            'target_sheets': view['target_sheets'], 'source_contribution_count': view['source_contribution_count'],
            'credit_binding': self._projector.as_record(), 'interpretation': view['interpretation'],
            'ended_by': record.ended_by, 'units': record.units_consumed}}
        if EVIDENCE_REFS in self._bound.report_form.fields:
            # The commissioner's typed report (C5) asks for the records the findings rest on.
            returned[EVIDENCE_REFS] = refs
        return UnitInput(returned)


__all__ = ['LITERATURE_LEAD', 'LiteratureSource']
