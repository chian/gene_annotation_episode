"""The A103 literature decision source on the generic runner.

The literature source is the A103 unit source (``runtime_source.GeneContextEvidenceSource``)
with what is the literature episode's own:

- its commission: the parent's literature question (``role_assignment``) and the
  selected source operations instead of a thought pattern and the head's tools;
- its instructions: the A103 literature lead and the binding's role ``instruction``;
- its children: a child commission names a declared literature slot, its objective, a
  sub-scope, its question and the source operations it may use (C6, chosen among the
  child's own declared options); the parent hands on the records it holds within that
  scope.

Each unit is one model selection, recorded through ``bound.recorder``
(``decision.<position>.<attempt>``, ``outcome.<position>``). A response that fails
admission (schema, empty reasoning commit, a child scope or assignment its form refuses)
creates no unit; the model decides again with that feedback. Every executed outcome,
including an invalid or failed one, enters the iterator with the credit measured after it
and its progress receipt. A child's admitted ``finding`` hands its ``evidence_refs`` to
this episode; child credits are never summed into its own.
"""
from __future__ import annotations

from episode_runtime import Commission
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from ..contract_binding import REPORT, ContractRecord
from ..runtime_source import GeneContextEvidenceSource, _State, _embedded, head_scope, initial_known

LITERATURE_LEAD = (
    'For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene identity, '
    'order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their source and '
    'scope.\n'
    'This is an iterative literature investigation of the commissioned question (role_assignment). Choose one '
    'action: a source operation among the commissioned tools, a reasoning commit of a source-grounded '
    'interpretation, or a child commission in a declared literature slot with its objective, a sub-scope, its '
    'question and the source operations it may use. Earlier outcomes and returned child findings inform later '
    'choices; no child order, reading quota or complete-document requirement is prescribed. Preserve the source\'s '
    'actual subject, experimental conditions, representation, version and UTF-8 byte anchors. Distinguish source '
    'claims from their applicability to the fixed target. Negative findings and qualifications can advance the '
    'investigation. Navigation, byte coverage and repeated reading earn no credit by themselves. The configured '
    'controller owns continuation; there is no stop action.\n')


class LiteratureSource(GeneContextEvidenceSource):
    """An A103 literature episode's model-selected units over its own tools and literature children."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a103_tool_registry_is_not_over_the_run_store')
        self._scope = head_scope(self._store, bound.assignment['scope'])
        self._builders = child_builders
        for role, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a103_child_return_form_differs:' + role)
            if 'tools' not in builder.assignment_form.fields:
                raise ContractError('a103_literature_child_assignment_requires_tools:' + role)
        if bound.report_form != binding.return_form:
            # A literature episode reports exactly its credit and finding; no decision fills an added field.
            raise ContractError('a103_literature_report_form_must_be_its_return_form:' + binding.binding_path)
        self._annotation = None
        self._selected_tools = tuple(bound.assignment['tools'])
        self._state = _State(initial_known(bound.assignment))

    # -- presentation -------------------------------------------------------------
    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        for role, builder in sorted(self._builders.items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': role},
                                'objective': {'type': 'string', 'minLength': 1},
                                'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                                'role_assignment': {'type': 'object',
                                                    'description': "The child's literature question and context."},
                                'tools': {'type': 'array', 'uniqueItems': True,
                                          'items': {'enum': list(builder.assignment_form.fields['tools'].options)}}}))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view, credit_view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'binding_path': self._binding.binding_path,
            'scope': self._scope,
            'role_assignment': dict(self._bound.assignment['role_assignment']),
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.known),
            'current_credit': credit_view['credit'],
            'target_sheets': credit_view['target_sheets'],
            'source_contribution_count': credit_view['source_contribution_count'],
            'credit_binding': self._binding.credit_projector.as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self._tool_catalog().items())},
            'child_options': {role: {'binding_path': builder.binding_path,
                                     'assignment_form': builder.assignment_form.as_record()}
                              for role, builder in sorted(self._builders.items())},
        }

    def instructions(self):
        return LITERATURE_LEAD + self._binding.instruction + '\n' + INSTRUCTIONS + '\n' + REASONING_COMMIT_REQUIREMENT

    # -- decisions ----------------------------------------------------------------
    def admit(self, response, schema):
        """The A103 admission; a child selection's commission is also admitted against the child's own form."""
        selection = super().admit(response, schema)
        if selection['kind'] == 'episode_child':
            self._commission(selection)
        return selection

    def _commission(self, selection):
        role = selection['role']
        builder = self._builders[role]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        assignment = {'scope': scope, 'role_assignment': selection['role_assignment'], 'tools': selection['tools'],
                      'evidence_refs': self._store.reference_subset(self._state.known, scope),
                      **builder.assignment_form.declared}
        builder.assignment_form.admit(assignment, 'a103_literature_child_assignment:' + role)
        report = dict(REPORT)
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'], result_contract=report)
        return Commission(EpisodeRequest(goal, ContractRecord({'scope': scope}), ReportContract(**report)), assignment)

    # -- execution ------------------------------------------------------------------
    def _child(self, position, selection):
        role = selection['role']
        builder = self._builders[role]
        commission = self._commission(selection)
        child = builder(role + '_' + str(position), commission)
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result)
            refs = admitted['finding'].get('evidence_refs')
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a103_child_finding_requires_evidence_refs:' + role)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': role, 'record_refs': self._received(refs),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report_of(result, completion, request):
            admitted = builder.admit(result)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report_of)


__all__ = ['LITERATURE_LEAD', 'LiteratureSource']
