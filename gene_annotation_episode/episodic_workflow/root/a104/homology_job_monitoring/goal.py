"""Actual private job_monitor goal."""
from __future__ import annotations
from .message_contracts import ROLES
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_role_readers import goal_instructions

def compose_goal(role, has_information_channel):
    return 'You own an iterative scoped job investigation in the shared method_loop. ' + 'Improve the requested understanding of the assigned job execution using actual observations. The job may continue after you yield. Repeated unchanged samples are not progress.' + " Revise selected work from actual outcomes. Select one of your available ordinary tools. Only the configured yield controller owns continuation: no stop action, turn cap, forced sequence or work timeout. Use the parent-defined typed report form. Recorded execution facts come from declared x-source fields; do not invent them. Interpretive fields use only the parent-declared values and meanings. There is no separate report-composition call. Global execution expectations are statistical inputs, not scientific findings, task progress, another episode's yield history or instructions. Use episode.history for older own work; do not rerun work merely to see its output." + (' monitoring_information_credit records execution information learned through your selected samples or handoff checks, independently of your current_credit binding. A completed duration remains timing information even when learned during launch or acquisition. The separate binding does not add itself to operational/scientific credit or choose continuation.' if has_information_channel(role) else '')

class HomologyMonitoringGoal:

    def describe(self):
        return {role: {'report_facts': self.fact_sources(role), 'responsibility': self.instructions(role)} for role in ROLES}
