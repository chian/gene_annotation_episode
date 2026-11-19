"""The one implementation shared by the seven A107 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: ``binding_path``, ``goal``,
``unit``, ``result``, ``child_slots``, ``commissioning_parent``, its role
``instruction`` and whether it may acquire public sources (``acquisition``).

Construction (``partner_presence_evidence.episode.home_factory``) gives each
binding its own ``A107ToolRegistry`` over the run's shared Store (C4).

Its commission (``assignment_form``): ``scope`` (the commissioner's Store scope),
``assignment`` (the commissioner's literature question and context for this
episode) and ``tools`` (the subset of this binding's source operations the
commissioner selected, C6: source readers always, public literature acquisition
only when ``acquisition`` is declared).

Credit is the A107 axis projection, ``investigation_progress.ScientificFindingProgress``:
one explicit ``finding_unit`` per distinct retained typed finding among the
assessments this episode has received (its own reasoning, decisions and child
returns). Continuation is the A107 ``AccumulationYieldController`` with the
binding's explicit ``continuation`` settings ``{cutoff, parameters, finding_unit}``.
Credit is never clamped or rescaled. The decision source is
``literature_cycle.LiteratureCycleSource``.

Not offered: the partner-sheet populations (``literature.partner.populate``,
``literature.partner.source.populate``): no ``A107ToolRegistry`` operation exposes them.
"""
from __future__ import annotations

from collections.abc import Mapping

from episode_runtime import Commission, Field, RecordForm, SubsetField
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from ..head_cycle import STORE_METHODS, CycleRecord, collaborator, head_settings, opening_credit
from ..runtime_binding import DescendantBinding, RuntimeBindingError, UnitRecord, _contract

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets',
                'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# Acquiring public literature.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')


class LiteratureBinding(DescendantBinding):
    """An A107 literature binding: its own tools, instruction, finding credit and decision source."""

    acquisition: bool
    instruction: str

    def __init__(self, *, tool_registry):
        from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
        if type(tool_registry) is not A107ToolRegistry:
            raise RuntimeBindingError('a107_literature_requires_its_own_a107_tool_registry:' + self.binding_path)
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        missing = sorted(set(names) - set(tool_registry.catalog(None)))
        if missing:
            raise RuntimeBindingError('a107_literature_tools_not_in_registry:' + self.binding_path + ':'
                                      + ','.join(missing))
        self.tool_registry = tool_registry
        self.selectable_tools = tuple(sorted(names))
        self.assignment_form = RecordForm({
            'scope': Field('record', "The commissioning parent's Store scope for this episode"),
            'assignment': Field('record', "The commissioner's literature question and context for this episode"),
            'tools': SubsetField('text', 'The source operations of this literature episode this commission may use',
                                 self.selectable_tools),
        })

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        fields = {'objective', 'scope', 'assignment', 'tools'} | ({'report_contract'} if parent_goal else set())
        if not isinstance(entry_input, Mapping) or set(entry_input) != fields \
                or type(entry_input['objective']) is not str or not entry_input['objective'].strip():
            raise RuntimeBindingError('a107_literature_entry_requires_' + '_'.join(sorted(fields)) + ':'
                                      + self.binding_path)
        assignment = self.assignment_form.admit({name: entry_input[name] for name in ('scope', 'assignment', 'tools')},
                                                self.binding_path)
        message = UnitRecord({'objective': entry_input['objective']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'],
                                    result_contract={'binding_path': self.binding_path, 'result': self.result})
            return Commission(EpisodeRequest(goal, message), assignment)
        contract = _contract(entry_input['report_contract'], self.binding_path)
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment)

    def build_controller(self, bound, collaborators):
        """The A107 accumulation yield controller, opened at the commission's finding-progress baseline."""
        from yield_control import AccumulationYieldController, YieldParameters
        if bound.binding_path != self.binding_path:
            raise RuntimeBindingError('a107_controller_opened_for_another_binding:' + bound.binding_path)
        settings = head_settings(collaborators, self.binding_path)
        store = collaborator(collaborators, 'store', STORE_METHODS)
        return AccumulationYieldController(bound.episode_id, opening_credit(bound, store, settings),
                                           settings['cutoff'], YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        from .literature_cycle import build_literature_episode
        return build_literature_episode(self, grain, bound, collaborators, child_builders)

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping) or 'credit' not in record:
            raise RuntimeBindingError('a107_recorded_unit_requires_credit:' + self.binding_path)
        return CycleRecord(dict(record))


__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'LiteratureBinding']
