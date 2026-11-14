from __future__ import annotations
from .contracts import ROLES

class SubmissionGoal:

    def instructions(self, role):
        responsibilities = {'job_launch': 'Establish the execution environment, prepare and submit the assigned detached job, and repair its usable monitoring handoff. Only your submit tool can launch this assigned job.'}
        return 'You own an iterative scoped job investigation in the shared method_loop. ' + responsibilities[role] + " Revise selected work from actual outcomes. Select one of your available ordinary tools. Only the configured yield controller owns continuation: no stop action, turn cap, forced sequence or work timeout. Use the parent-defined typed report form. Recorded execution facts come from declared x-source fields; do not invent them. Interpretive fields use only the parent-declared values and meanings. There is no separate report-composition call. Global execution expectations are statistical inputs, not scientific findings, task progress, another episode's yield history or instructions. Use episode.history for older own work; do not rerun work merely to see its output." + (' monitoring_information_credit records execution information learned through your selected samples or handoff checks, independently of your current_credit binding. A completed duration remains timing information even when learned during launch or acquisition. The separate binding does not add itself to operational/scientific credit or choose continuation.' if self.has_information_channel(role) else '')

    def describe(self):
        return {role: {'report_facts': self.fact_sources(role), 'responsibility': self.instructions(role)} for role in ROLES}
