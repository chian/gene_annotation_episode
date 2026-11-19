"""The A101 head binding (``sequence_homology_evidence``), commissioned by the root annotation episode.

Its decision source on the generic runner is ``runtime_source.SequenceHomologyEvidenceSource``;
its credit and continuation are ``runtime_credit.head_controller``. ``ScientificConfiguration``
holds its construction-time library, own tool registry and yield declaration.
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import ChoiceField, DeclaredField, RecordForm, SubsetField

from .configuration import ScientificConfiguration
from .contract_binding import SCOPE, A101ContractBinding
from .yield_estimator import SequenceHomologyEvidenceYield

HEAD = 'sequence_homology_evidence'
EVIDENCE_TASK = ('A101 sequence homology: which sequence-similar references support or contradict each '
                 'candidate function')


class SequenceHomologyEvidenceEpisode(A101ContractBinding, ScientificConfiguration, SequenceHomologyEvidenceYield):
    """The recursive A101 head: its own tools, reasoning, sub-scope heads and operational/literature children."""
    binding_path = HEAD
    commissioning_parent = 'annotation'
    goal = ('Improve the sequence-homology evidence for the assigned subject: which sequence-similar references '
            'support or contradict each candidate function, as qualified, source-grounded findings')
    unit = 'One selected tool, reasoning or child action of this sequence-homology investigation'
    result = 'Qualified sequence-homology findings with their record references and A101 credit'
    child_slots = MappingProxyType({
        'execution_job_submission': HEAD + '/execution_job_submission',
        'execution_progress_assessment': HEAD + '/execution_progress_assessment',
        'execution_result_acquisition': HEAD + '/execution_result_acquisition',
        'resource_work_submission': HEAD + '/resource_work_submission',
        'resource_result_acquisition': HEAD + '/resource_result_acquisition',
        'published_evidence_assessment': HEAD + '/published_evidence_assessment',
        'sequence_homology_evidence': HEAD,
    })

    @property
    def assignment_form(self):
        """``scope`` is held by the commissioner; the evidence task is the head's own declaration;
        the thought pattern and the tools are the commissioner's choice among the head's options (C3, C6)."""
        return RecordForm({
            'scope': SCOPE,
            'evidence_task': DeclaredField('text', 'The evidence task this axis owns', EVIDENCE_TASK),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
        })

    def build_controller(self, bound, collaborators):
        """The head's own credit (native sequence correspondence over its receipts) and continuation."""
        from .runtime_credit import head_controller
        return head_controller(self, bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The head's own model-selected units (``runtime_source``) over ``bound`` and its collaborators."""
        from method_loop import Episode
        from .runtime_source import SequenceHomologyEvidenceSource
        source = SequenceHomologyEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)
