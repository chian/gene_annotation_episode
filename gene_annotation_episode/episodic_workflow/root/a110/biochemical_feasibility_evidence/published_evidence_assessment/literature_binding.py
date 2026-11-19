"""The one implementation shared by the seven A110 literature bindings.

Each literature binding (``published_evidence_assessment`` and the six bindings
below it) is an explicit subclass of ``LiteratureBinding`` in its own home's
``episode.py`` and declares what is its own: its contract declarations, its
role ``instruction`` and whether it may acquire public sources
(``acquisition``).

Every literature episode runs the A110 unit source (``unit_source.py``) with:

- its own A110 ``ToolRegistry`` (built by the A110 home factory over the run's
  shared Store, ruling C4);
- its own operations: the source access readers, plus the public literature and
  chemical-source acquisitions when ``acquisition`` is declared. Its commissioner
  chooses the subset this commission may use (``tools``, a ``SubsetField``, C6);
- the record its parent prepared (``assignment``) and the subject ``scope``.

Credit is the A110 finding credit over the assessments the episode knows (its
own committed assessments and those its children returned); unbounded.
"""
from __future__ import annotations

from episode_runtime import RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    A110_SOURCE_LEAD, REACTION_LEAD, REACTION_VIEW_MEANING)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    REASONING_COMMIT_REQUIREMENT)
from ..runtime_contract import ASSIGNMENT, EpisodeRuntimeContract, REQUIRED_COLLABORATORS, RETURN_FORM, SCOPE
from ..unit_source import PROTOCOL, build_unit_episode, selectable_tools

# Reading actual received sources; no acquisition.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.references', 'source.sequence.scan',
                'image.view', 'source.archive.members', 'source.archive.extract', 'source.xlsx.sheets',
                'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                'material.annotations', 'material.parse', 'material.from_source')
# Acquiring public literature and the chemical/reaction source records A110 literature reads.
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     'public.uniprot.search', 'public.uniprot.record', 'public.taxonomy', 'public.ncbi.sequence',
                     'public.rhea.search', 'public.rhea.reaction', 'public.chebi.search', 'public.chebi.compound',
                     'public.kegg.reaction', 'public.reactome.record', 'public.pubchem.compound')
LITERATURE_LEAD = A110_SOURCE_LEAD + '\n\n' + REACTION_LEAD + '\n\n' + REACTION_VIEW_MEANING


class LiteratureBinding(EpisodeRuntimeContract):
    """An A110 literature binding: its own tools, instruction and the A110 unit source."""
    required_collaborators = REQUIRED_COLLABORATORS
    return_form = RETURN_FORM

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        names = ACCESS_TOOLS + (ACQUISITION_TOOLS if self.acquisition else ())
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'assignment': ASSIGNMENT,
            'tools': SubsetField('text', 'The operations of this literature episode this commission may use',
                                 selectable_tools(tool_registry, names)),
        })

    def instructions(self):
        return self.instruction + '\n\n' + LITERATURE_LEAD + '\n\n' + PROTOCOL + '\n' + REASONING_COMMIT_REQUIREMENT

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The literature episode's own model-selected units over its finding credit."""
        return build_unit_episode(self, grain, bound, collaborators, child_builders)
