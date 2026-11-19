"""The three A107 progress monitors (``.../execution_progress_assessment``) on the generic runner.

Each monitor binding mixes in ``A107MonitorBinding`` before ``runtime_binding.DescendantBinding``:
the A107 monitor runtime (``episode_support/jobs/service_calls/partner_presence_evidence/monitor_runtime.py``: model-selected progress tools,
received-information credit and its own information-accumulation yield continuation) over
A107's descendant commission (``scope`` and the parent's monitor assignment, monitor_assignment_v1,
in ``assignment``). A monitor may commission a monitor of its own kind for one exposed direct
job dependency of its target (its ``monitor`` slot).

Its own tool registry is A107's base ``tools.ToolRegistry`` over the shared Store, built by the
A107 home factory from the monitor's ``tools`` settings: ``progress.log`` reads only the received
source window through it, so it needs none of the head's episode-invocation tools.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.partner_presence_evidence.monitor_runtime import A107MonitorRuntime

MONITOR_REPORT = MappingProxyType({
    'decision': "Use the dependency's observed progress in the commissioning monitor's cycle",
    'measurements': {'credit': "The dependency monitor's own information credit on its own scale"},
    'information': {'finding': 'The recorded monitoring facts of the dependency target'},
})


class A107MonitorBinding(A107MonitorRuntime):
    """The A107 monitor commission over the A107 monitor runtime."""

    dependency_slot = 'monitor'

    @staticmethod
    def role_assignment(assignment):
        return assignment['assignment']

    @staticmethod
    def child_assignment(scope, role_assignment):
        return {'scope': scope, 'assignment': role_assignment}

    @staticmethod
    def dependency_report_contract():
        return {'decision': MONITOR_REPORT['decision'], 'measurements': dict(MONITOR_REPORT['measurements']),
                'information': dict(MONITOR_REPORT['information'])}


__all__ = ['A107MonitorBinding', 'MONITOR_REPORT']
