"""The one implementation shared by the seven A102 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: ``binding_path``,
``commissioning_parent``, its role ``instruction`` and whether it may acquire
public sources (``acquisition``). Its goal, unit, result and child slots are the
A102 axis tables (``contract_binding``).

Construction (``contract_binding.a102_home_factory``) gives each binding its own
A102 ``ToolRegistry`` over the run's shared Store (C4) and the A102 literature
continuation declaration (``services['a102']['literature']``).

Its commission (``assignment_form``):

- ``scope``: the Store scope the commissioner holds;
- ``question``: the commissioner's record of the literature question for this
  episode (its question, context and the records it names);
- ``tools``: the subset of this binding's source operations the commissioner
  selected (``SubsetField``, C6). Source readers always; the public literature
  acquisitions only when the binding declares ``acquisition``.

Its credit is A102's native structural correspondence (``a102_credit.A102StructuralCredit``)
over the records this literature episode has received (its own outcomes and its
children's admitted findings), the axis's scientific projection rather than tool
activity. Its continuation is the declared yield controller for that credit. Credit
is never bounded, clamped or rescaled. Its decision source is
``literature_source.LiteratureSource``.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math

from episode_runtime import Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import A102StructuralCredit
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError, canonical
from ..contract_binding import A102ContractBinding

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# Acquiring public literature and the deposited structure entries a source names.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     'public.rcsb.entry', 'public.emdb.entry')
QUESTION = Field('record', "The commissioning parent's literature question for this episode: its question, "
                           'context and the records it names')
_KINDS = frozenset({'accumulation', 'bounded_quality', 'completion'})


def literature_credit():
    """The A102 literature credit projector."""
    return A102StructuralCredit()


def literature_continuation(declaration):
    """The A102 literature continuation: exactly kind, cutoff, parameters, credit_definition, for its own credit."""
    from yield_control import YieldParameters
    if not isinstance(declaration, Mapping):
        raise ContractError('a102_literature_continuation_declaration_required')
    declaration = json.loads(json.dumps(dict(declaration), allow_nan=False))
    projector = literature_credit()
    if (set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
            or declaration['kind'] not in _KINDS or not isinstance(declaration['parameters'], dict)
            or set(declaration['parameters']) != {'uncertainty_alpha'}
            or isinstance(declaration['cutoff'], bool) or not isinstance(declaration['cutoff'], (int, float))
            or not math.isfinite(declaration['cutoff'])):
        raise ContractError('a102_literature_continuation_invalid')
    if canonical(declaration['credit_definition']) != canonical(projector.as_record()):
        raise ContractError('a102_literature_continuation_credit_definition_mismatch')
    if declaration['kind'] != projector.yield_method:
        raise ContractError('a102_literature_continuation_method_credit_mismatch')
    YieldParameters(**declaration['parameters'])
    return declaration


class LiteratureBinding(A102ContractBinding):
    """An A102 literature binding: its own tools, instruction, credit and decision source."""

    acquisition: bool
    instruction: str
    required_collaborators = ('store', 'model_provider')

    def __init__(self, *, tool_registry, continuation):
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        missing = sorted(set(names) - set(tool_registry.catalog(None)))
        if missing:
            raise ContractError('a102_literature_tools_not_in_registry:' + self.binding_path + ':' + ','.join(missing))
        self.tool_registry = tool_registry
        self.selectable_tools = tuple(sorted(names))
        self.credit_projector = literature_credit()
        self.continuation = literature_continuation(continuation)
        self._assignment_form = RecordForm({
            'scope': Field('record', 'The subject scope the commissioning parent holds'),
            'question': QUESTION,
            'tools': SubsetField('text', 'The source operations of this literature episode this commission may use',
                                 self.selectable_tools),
        })

    @property
    def assignment_form(self):
        return self._assignment_form

    def build_controller(self, bound, collaborators):
        """The declared yield controller over this episode's native structural correspondence credit."""
        from .literature_source import literature_controller
        return literature_controller(self, bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'LiteratureBinding', 'QUESTION', 'literature_continuation',
           'literature_credit']
