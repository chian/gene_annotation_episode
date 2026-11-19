"""The three A104 progress monitors (``.../execution_progress_assessment``) on the generic runner.

``MonitorBinding`` is an A104 descendant binding (``runtime_bindings.DescendantBinding``:
its path, role ``monitor``, commissioning parent and ``{'scope', 'assignment'}``
commission; it returns ``credit`` and ``report``) whose decisions, credit and
continuation are the A104 monitor runtime (``episode_support/jobs/service_calls/evolutionary_history_evidence/monitor_runtime.py``):
progress tools selected by the model, received-information credit and its own
information-accumulation yield continuation. The commission's ``assignment`` is
the parent's monitor assignment (monitor_assignment_v1). A104 monitors declare no
child slot, so a monitor does not commission dependency monitors.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.evolutionary_history_evidence.monitor_runtime import A104MonitorRuntime
from .runtime_bindings import DescendantBinding


class MonitorBinding(A104MonitorRuntime, DescendantBinding):
    """One A104 progress monitor: an A104 descendant over the A104 monitor runtime."""

    result_field = 'report'

    def __init__(self, binding_path, commissioning_parent, child_slots, roles_by_grain, *, information_unit,
                 yield_settings, tool_registry):
        DescendantBinding.__init__(self, binding_path, 'monitor', commissioning_parent, child_slots, roles_by_grain)
        A104MonitorRuntime.__init__(self, information_unit=information_unit, yield_settings=yield_settings,
                                    tool_registry=tool_registry)

    @staticmethod
    def role_assignment(assignment):
        return assignment['assignment']


__all__ = ['MonitorBinding']
