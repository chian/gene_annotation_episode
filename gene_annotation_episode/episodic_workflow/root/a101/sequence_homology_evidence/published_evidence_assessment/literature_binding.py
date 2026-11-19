"""The one implementation shared by the seven A101 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: ``binding_path``, ``goal``,
``unit``, ``result``, ``child_slots``, ``commissioning_parent``, its role
``instruction`` and whether it may acquire public sources (``acquisition``).

Construction (``home_factory.a101_home_factory``) gives each binding its own
A101 ``ToolRegistry`` over the run's shared Store (C4) and the A101 continuation
declaration for its credit task (``yield_estimator.HEAD_TASK``).

Its commission (``assignment_form``):

- ``scope``: the Store scope the commissioner holds;
- ``question``: the commissioner's record of the literature question for this
  episode (its question, context and the records it passes on);
- ``tools``: the subset of this binding's source operations the commissioner
  selected (``SubsetField``, C6). Source readers always; the public literature
  acquisitions only when the binding declares ``acquisition``.

Its credit is A101's native sequence-correspondence projection
(``A101SequenceCredit``) over the records this literature episode has received
(``EpisodeReceipts``), as the A101 literature credit was the axis's scientific
projection over the episode's receipts. Its continuation is the A101 yield
declaration for that credit task. Credit is never bounded, clamped or rescaled.
Its decision source is ``literature_source.LiteratureSource``.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from episode_runtime import Field, RecordForm, SubsetField

from gene_annotation_episode.domain import ContractError

from ..contract_binding import SCOPE, A101ContractBinding
from ..yield_estimator import HEAD_TASK, SequenceHomologyEvidenceYield

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# Acquiring public literature.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset')
QUESTION = Field('record', "The commissioning parent's literature question for this episode: its question, "
                           'context and the records it passes on')


def literature_yield_bindings(yield_bindings):
    """The A101 continuation declaration for ``HEAD_TASK``: exactly kind, cutoff, parameters, credit_definition."""
    if not isinstance(yield_bindings, Mapping) or set(yield_bindings) != {HEAD_TASK}:
        raise ContractError('a101_literature_yield_bindings_must_declare_exactly:' + HEAD_TASK)
    bindings = json.loads(json.dumps(dict(yield_bindings), allow_nan=False))
    declaration = bindings[HEAD_TASK]
    if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
            or not isinstance(declaration['parameters'], dict)
            or set(declaration['parameters']) != {'uncertainty_alpha'}
            or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
        raise ContractError('a101_literature_yield_binding_invalid:' + HEAD_TASK)
    return bindings


class LiteratureBinding(A101ContractBinding, SequenceHomologyEvidenceYield):
    """An A101 literature binding: its own tools, instruction, credit and decision source."""

    acquisition: bool
    instruction: str

    def __init__(self, *, tool_registry, yield_bindings):
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        missing = sorted(set(names) - set(tool_registry.catalog(None)))
        if missing:
            raise ContractError('a101_literature_tools_not_in_registry:' + self.binding_path + ':' + ','.join(missing))
        self.tool_registry = tool_registry
        self.selectable_tools = tuple(sorted(names))
        self._yield_bindings = literature_yield_bindings(yield_bindings)
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'question': QUESTION,
            'tools': SubsetField('text', 'The source operations of this literature episode this commission may use',
                                 self.selectable_tools),
        })

    def build_controller(self, bound, collaborators):
        """The literature episode's continuation over its own native-correspondence credit."""
        from .literature_source import literature_controller
        return literature_controller(self, bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The literature episode's own model-selected units (``literature_source``)."""
        from method_loop import Episode
        from .literature_source import LiteratureSource
        source = LiteratureSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ACCESS_TOOLS', 'ACQUISITION_TOOLS', 'LiteratureBinding', 'QUESTION', 'literature_yield_bindings']
