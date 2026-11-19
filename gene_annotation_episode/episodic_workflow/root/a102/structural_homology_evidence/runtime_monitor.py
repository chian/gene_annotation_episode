"""A102 progress monitors (``execution_progress_assessment``) on the generic runner.

Each of the three monitor bindings mixes in ``A102MonitorBinding``: the A102
monitor runtime (``episode_support/jobs/service_calls/structural_homology_evidence/monitor_runtime.py``: progress tools,
model-selected decisions, received-information credit and its own
information-accumulation yield continuation) over A102's flat monitor
commission (``MONITOR_ASSIGNMENT``: the scope and the monitor_assignment_v1
fields). A monitor may commission a monitor of its own kind for one exposed
direct job dependency of its target (its ``execution_progress_assessment`` slot).
"""
from __future__ import annotations

from episode_runtime import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.monitor_runtime import A102MonitorRuntime
from .contract_binding import MONITOR, REPORT

# The monitor's own assignment (monitor_assignment_v1) and the scope it observes in.
MONITOR_ASSIGNMENT = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning A102 parent'),
    'version': DeclaredField('text', 'The monitor assignment version', 'monitor_assignment_v1'),
    'target_handle': Field('text', 'The execution handle whose progress is observed'),
    'requested_fields': Field('list', 'The progress fields requested from each observation'),
    'known_progress_refs': Field('list', 'Progress snapshots the parent already holds (the information baseline)'),
    'permitted_committed_record_types': Field('list', 'Committed record types the parent permits to be exposed'),
})


class A102MonitorBinding(A102MonitorRuntime):
    """The A102 monitor commission over the A102 monitor runtime (mixed in before ``A102ContractBinding``)."""

    assignment_form = MONITOR_ASSIGNMENT
    dependency_slot = MONITOR

    @staticmethod
    def role_assignment(assignment):
        return {name: value for name, value in assignment.items() if name != 'scope'}

    @staticmethod
    def child_assignment(scope, role_assignment):
        return {'scope': scope, **{name: value for name, value in role_assignment.items() if name != 'version'}}

    @staticmethod
    def dependency_report_contract():
        return {'decision': REPORT['decision'], 'measurements': dict(REPORT['measurements']),
                'information': dict(REPORT['information'])}


__all__ = ['A102MonitorBinding', 'MONITOR_ASSIGNMENT']
