"""The one implementation shared by the seven A104 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: ``binding_path``, ``role``,
``commissioning_parent``, its role ``instruction`` and whether it may acquire
public sources (``acquisition``). Its goal, unit and result are the A104 role
table (``runtime_bindings.ROLE_TEXT``); its child slots are the declared A104
episode tree (``runtime_bindings.EPISODES``).

Construction (``runtime_bindings.a104_home``) gives each binding its own A104
``ToolRegistry`` over the run's shared Store (C4) and the A104 head's
continuation declaration (``services['a104']['head']['continuation']``), which is
the declaration for the same credit.

Its commission (``assignment_form``): ``scope`` (the commissioner's Store scope),
``role_assignment`` (the commissioner's literature question and context for this
episode) and ``tools`` (the subset of this binding's source operations the
commissioner selected, C6: source readers always, public literature acquisition
only when ``acquisition`` is declared).

Credit is A104's evolutionary-history projection (``a104_credit.A104EvolutionaryCredit``)
over the records this literature episode holds (its scope's subjects, its own
outcomes' records and its children's reported evidence references), the axis's
scientific projection rather than tool activity. Continuation is the declared
yield controller for that credit. Credit is never bounded, clamped or rescaled.
The decision source is ``literature_source.LiteratureSource``.
"""
from __future__ import annotations

from collections.abc import Mapping

from episode_runtime import Commission, Field, RecordForm, SubsetField
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

from ..runtime_bindings import SCOPE, UnitInput, _Binding, _head_continuation

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# Acquiring public literature.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')
REPORT_CONTRACT = {
    'decision': 'Admit the A104 literature findings into the commissioning episode',
    'measurements': {'credit': "This literature commission's A104 evolutionary-history credit on its own scale"},
    'information': {'finding': 'The literature findings of this commission and the records they rest on'},
}


class LiteratureBinding(_Binding):
    """An A104 literature binding: its own tools, instruction, credit and decision source."""

    binding_path: str
    role: str
    commissioning_parent: str
    acquisition: bool
    instruction: str
    required_collaborators = ('model_provider', 'store')

    def __init__(self, *, child_slots, roles_by_grain, store, tool_registry, continuation):
        super().__init__(type(self).binding_path, type(self).role, type(self).commissioning_parent, child_slots,
                         roles_by_grain)
        if tool_registry.store is not store:
            raise ContractError('a104_tool_registry_is_not_over_the_run_store')
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        missing = sorted(set(names) - set(tool_registry.catalog(None)))
        if missing:
            raise ContractError('a104_literature_tools_not_in_registry:' + self.binding_path + ':' + ','.join(missing))
        self.store, self.tool_registry = store, tool_registry
        self.selectable_tools = tuple(sorted(names))
        self.continuation = _head_continuation(continuation)
        self.report_contract = REPORT_CONTRACT
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'role_assignment': Field('record', "The commissioner's literature question and context for this episode"),
            'tools': SubsetField('text', 'The source operations of this literature episode this commission may use',
                                 self.selectable_tools),
        })
        self.return_form = RecordForm({
            'credit': Field('number', "This literature episode's unbounded evolutionary-history credit"),
            'finding': Field('record', 'The literature findings of this episode and the records they rest on')})

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        supplied = set(self.assignment_form.fields)
        if not isinstance(entry_input, Mapping) or set(entry_input) != supplied:
            raise ContractError('a104_literature_entry_requires_exactly:' + ','.join(sorted(supplied)))
        assignment = self.assignment_form.admit(dict(entry_input), 'a104_entry_assignment:' + self.binding_path)
        message = UnitInput({'scope': assignment['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=self.return_form.as_record())
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT_CONTRACT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT_CONTRACT)), assignment)

    def build_controller(self, bound, collaborators):
        """The declared yield controller over this episode's evolutionary-history credit, opened over its scope."""
        from yield_control import (AccumulationYieldController, BoundedQualityYieldController,
                                   CompletionYieldController, YieldParameters)
        from ..runtime_source import head_credit_projector, opening_record_refs, store_scope
        if bound.binding_path != self.binding_path:
            raise ContractError('a104_literature_controller_opened_for_another_binding:' + bound.binding_path)
        store = collaborators['store']
        if store is not self.store:
            raise ContractError('a104_literature_store_is_not_the_run_store')
        declaration, projector = self.continuation, head_credit_projector()
        scope = store_scope(store, bound.assignment['scope'])
        opening = projector(store, scope, known_record_refs=opening_record_refs(scope))['credit']
        parameters = YieldParameters(**declaration['parameters'])
        if declaration['kind'] == 'bounded_quality':
            return BoundedQualityYieldController(bound.episode_id, opening, declaration['cutoff'],
                                                 projector.native_score_maximum, parameters)
        if declaration['kind'] == 'completion':
            return CompletionYieldController(bound.episode_id, opening, declaration['cutoff'],
                                             projector.as_record()['maximum_credit'], parameters)
        return AccumulationYieldController(bound.episode_id, opening, declaration['cutoff'], parameters)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'LiteratureBinding', 'REPORT_CONTRACT']
