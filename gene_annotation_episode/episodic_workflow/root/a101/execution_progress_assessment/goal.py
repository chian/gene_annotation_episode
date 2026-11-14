"""MonitorGoal"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain

class MonitorGoal:

    def instructions(self, context):
        self._role(context.role)
        credit_instruction = "The monitor's information-credit projector and bound yield rule govern continuation. " if self.private_yield_binding else "The caller's monitoring projector and configured controller own credit and continuation. "
        return "Investigate which further exposed progress information is useful for the assigned target. Use actual status, measured quantities, committed references and source-bound logs. Liveness establishes process presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, cadence or depth is prescribed. Return the original parent's typed form at your closure even while the target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded facts use saved delivered observations; closure does not poll or compose another report with a model. " + credit_instruction + 'Repeated observation identities and read timestamps alone earn no new information.'

    def planning_context(self, context):
        assignment = self._assignment(context.assignment, context.scope)
        return {'objective': plain(context.request).get('goal'), 'target_handle': assignment['target_handle'], 'requested_fields': assignment['requested_fields'], 'unresolved_question': 'Which exposed progress information would improve the original requested report?', 'progress_definition': 'Actual received information under the caller-bound monitoring projector; repeated identities and timestamps alone earn no credit.', 'yield_settings': deepcopy(self.yield_settings)}
