"""The three A110 progress monitors (``.../execution_progress_assessment``) on the generic runner.

Each monitor binding mixes in ``A110MonitorBinding`` before ``runtime_contract.EpisodeRuntimeContract``:
the A110 monitor runtime (``episode_support/jobs/service_calls/biochemical_feasibility_evidence/monitor_runtime.py``: model-selected progress tools,
received-information credit and its own information-accumulation yield continuation) over A110's
child commission (``scope`` and the parent's monitor assignment, monitor_assignment_v1, in
``assignment``). A monitor returns its own credit and its recorded monitoring facts (``finding``,
a record); it declares no child slot. Its own A110 ``ToolRegistry`` over the shared Store is
built by the A110 home factory.
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.biochemical_feasibility_evidence.monitor_runtime import A110MonitorRuntime
from .runtime_contract import CHILD_ASSIGNMENT_FORM

MONITOR_RETURN_FORM = RecordForm({
    'credit': Field('number', "This monitor's own information credit on its unbounded scale"),
    'finding': Field('record', 'The recorded monitoring facts of the assigned execution target'),
})


class A110MonitorBinding(A110MonitorRuntime):
    """The A110 monitor commission over the A110 monitor runtime."""

    unit = 'One progress observation'
    result = 'The observed progress snapshots'
    child_slots = MappingProxyType({})
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = MONITOR_RETURN_FORM

    @property
    def grain_name(self):
        return self.binding_path.replace('/', '__')

    @staticmethod
    def role_assignment(assignment):
        return assignment['assignment']


__all__ = ['A110MonitorBinding', 'MONITOR_RETURN_FORM']
