"""The A110 head binding (biochemical_feasibility_evidence).

The head runs the A110 unit source (``unit_source.py``) with its own A110 tool
registry, constructed by the A110 home factory over the run's shared Store
(ruling C4); the runtime ``store`` collaborator must be that Store. Its
commissioner (the root) fills ``scope`` with the subject it holds, copies the
declared ``evidence_task`` and chooses ``tools`` (C6), the subset of the head's
operations this commission may use.
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import DeclaredField, RecordForm, SubsetField

from .head_episode import instructions
from .runtime_contract import EpisodeRuntimeContract, REQUIRED_COLLABORATORS, RETURN_FORM, SCOPE
from .unit_source import build_unit_episode, selectable_tools

EVIDENCE_TASK = DeclaredField('text', 'The evidence axis this head investigates',
                              'A110 biochemical feasibility and chemical/resource accounting')


class BiochemicalFeasibilityEvidenceEpisode(EpisodeRuntimeContract):
    """The A110 evidence-axis head: model-selected tool, reasoning and child units over its finding credit."""
    binding_path = 'biochemical_feasibility_evidence'
    grain_name = binding_path.replace('/', '__')
    goal = 'Improve the evidence on whether the proposed reaction or pathway is chemically and resource feasible under its declared conditions'
    unit = 'One selected scientific tool action or commissioned child investigation'
    result = 'The retained biochemical-feasibility findings and their unbounded credit'
    child_slots = MappingProxyType({'biochemical_feasibility_evidence': 'biochemical_feasibility_evidence', 'execution_job_submission': 'biochemical_feasibility_evidence/execution_job_submission', 'execution_progress_assessment': 'biochemical_feasibility_evidence/execution_progress_assessment', 'execution_result_acquisition': 'biochemical_feasibility_evidence/execution_result_acquisition', 'hpc_work_planning': 'biochemical_feasibility_evidence/hpc_work_planning', 'published_evidence_assessment': 'biochemical_feasibility_evidence/published_evidence_assessment'})
    required_collaborators = REQUIRED_COLLABORATORS
    return_form = RETURN_FORM

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'evidence_task': EVIDENCE_TASK,
            'tools': SubsetField('text', 'The operations of this head this commission may use',
                                 selectable_tools(tool_registry)),
        })

    @staticmethod
    def instructions():
        return instructions()

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The head's own model-selected tool, reasoning and child units over its finding credit."""
        return build_unit_episode(self, grain, bound, collaborators, child_builders)
