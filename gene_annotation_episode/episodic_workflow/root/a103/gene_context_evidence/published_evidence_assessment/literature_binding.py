"""The one implementation shared by the seven A103 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: ``binding_path``, ``goal``,
``unit``, ``result``, ``child_slots``, ``commissioning_parent``, its role
``instruction`` and whether it may acquire public sources (``acquisition``).

Construction (``gene_context_evidence/home.py``) gives each binding its own
``A103ToolRegistry`` over the run's shared Store (C4) and the A103 continuation
declaration for its credit task (``episode.CONTINUATION_TASK``).

Its commission (``assignment_form``): ``scope`` (the commissioner's Store scope),
``role_assignment`` (the commissioner's literature question and context for this
episode), ``tools`` (the subset of this binding's source operations the
commissioner selected, C6: source readers always, public literature acquisition
only when ``acquisition`` is declared) and optionally ``evidence_refs`` (the
records the commissioner holds and hands on).

Credit is A103's measured-context projection (``a103_credit.A103ContextCredit``)
over the records this literature episode holds, as the A103 literature credit
was the axis's scientific projection over the episode's records. Continuation is
the A103 yield declaration for that credit. Credit is never bounded, clamped or
rescaled. The decision source is ``literature_source.LiteratureSource``.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from episode_runtime import Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import A103ContextCredit
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical
from ..contract_binding import A103ContractBinding
from ..episode import CONTINUATION_TASK

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets',
                'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# Acquiring public literature.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')
_KINDS = frozenset({'accumulation', 'bounded_quality', 'completion'})


def literature_continuation(yield_bindings, projector):
    """The A103 continuation declaration for ``CONTINUATION_TASK``, bound to ``projector``."""
    if not isinstance(yield_bindings, Mapping) or set(yield_bindings) != {CONTINUATION_TASK}:
        raise ContractError('a103_literature_yield_binding_required:' + CONTINUATION_TASK)
    declaration = json.loads(json.dumps(dict(yield_bindings[CONTINUATION_TASK]), allow_nan=False))
    if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
            or declaration['kind'] not in _KINDS or not isinstance(declaration['parameters'], dict)
            or set(declaration['parameters']) != {'uncertainty_alpha'}):
        raise ContractError('a103_literature_yield_binding_invalid:' + CONTINUATION_TASK)
    if canonical(declaration['credit_definition']) != canonical(projector.as_record()):
        raise ContractError('a103_literature_yield_credit_definition_mismatch:' + CONTINUATION_TASK)
    if declaration['kind'] != projector.yield_method:
        raise ContractError('a103_literature_yield_method_credit_mismatch:' + CONTINUATION_TASK)
    return declaration


class LiteratureBinding(A103ContractBinding):
    """An A103 literature binding: its own tools, instruction, credit and decision source."""

    acquisition: bool
    instruction: str
    required_collaborators = ('store', 'model_provider')

    def __init__(self, *, tool_registry, yield_bindings):
        if not callable(getattr(tool_registry, 'execute_async', None)) or not callable(
                getattr(tool_registry, 'current_invocation', None)):
            raise ContractError('a103_literature_tool_registry_required:' + self.binding_path)
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        missing = sorted(set(names) - set(tool_registry.catalog(None)))
        if missing:
            raise ContractError('a103_literature_tools_not_in_registry:' + self.binding_path + ':' + ','.join(missing))
        self.tool_registry = tool_registry
        self.selectable_tools = tuple(sorted(names))
        self.credit_projector = A103ContextCredit()
        self.continuation = literature_continuation(yield_bindings, self.credit_projector)
        self.assignment_form = RecordForm({
            'scope': Field('record', 'The subject scope the commissioning parent holds'),
            'role_assignment': Field('record', "The commissioner's literature question and context for this episode"),
            'tools': SubsetField('text', 'The source operations of this literature episode this commission may use',
                                 self.selectable_tools),
            'evidence_refs': Field('list', 'Records the commissioning parent holds and hands on', required=False),
        })

    def build_controller(self, bound, collaborators):
        """The declared yield controller over this episode's measured-context credit."""
        from yield_control import (AccumulationYieldController, BoundedQualityYieldController,
                                   CompletionYieldController, YieldParameters)
        from ..runtime_source import head_scope, initial_known
        if bound.binding_path != self.binding_path:
            raise ContractError('a103_literature_controller_opened_for_another_binding:' + bound.binding_path)
        store = collaborators['store']
        if self.tool_registry.store is not store:
            raise ContractError('a103_tool_registry_is_not_over_the_run_store')
        scope = head_scope(store, bound.assignment['scope'])
        initial = self.credit_projector(store, scope, known_record_refs=initial_known(bound.assignment),
                                        assignment=None)['credit']
        declaration = self.continuation
        parameters = YieldParameters(**declaration['parameters'])
        if declaration['kind'] == 'bounded_quality':
            return BoundedQualityYieldController(bound.episode_id, initial, declaration['cutoff'],
                                                 self.credit_projector.native_score_maximum, parameters)
        if declaration['kind'] == 'completion':
            return CompletionYieldController(bound.episode_id, initial, declaration['cutoff'],
                                             self.credit_projector.as_record()['maximum_credit'], parameters)
        return AccumulationYieldController(bound.episode_id, initial, declaration['cutoff'], parameters)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'LiteratureBinding', 'literature_continuation']
