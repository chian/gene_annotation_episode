"""The A106 progress monitor binding (``perturbation_evidence/execution_progress_assessment``).

Its decisions, credit and continuation are the A106 monitor runtime
(``episode_support/jobs/service_calls/perturbation_evidence/monitor_runtime.py``): model-selected progress tools, its
received-information credit and its own information-accumulation yield
controller. Its commission is A106's operational form: ``scope`` and the
parent's monitor assignment (monitor_assignment_v1) in ``assignment``. Its own
A106 ``ToolRegistry`` is built by the A106 home factory over the shared Store.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.perturbation_evidence.monitor_runtime import A106MonitorRuntime
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.episode_contract import (
    OPERATIONAL_FORM, EpisodeContract)


class MonitorEpisode(A106MonitorRuntime, EpisodeContract):
    binding_path = 'perturbation_evidence/execution_progress_assessment'
    commissioning_parent = 'perturbation_evidence'
    roles = ('monitor',)
    goal = "The parent's knowledge of its pending work's progress"
    unit = "One progress observation"
    result = "The newly informative progress snapshots"
    assignment_form = OPERATIONAL_FORM

    def __init__(self, services, *, information_unit, yield_settings, tool_registry):
        A106MonitorRuntime.__init__(self, information_unit=information_unit, yield_settings=yield_settings,
                                    tool_registry=tool_registry)

    def contract_credit_unit(self, assignment):
        return self.information_unit

    @staticmethod
    def role_assignment(assignment):
        return assignment['assignment']
