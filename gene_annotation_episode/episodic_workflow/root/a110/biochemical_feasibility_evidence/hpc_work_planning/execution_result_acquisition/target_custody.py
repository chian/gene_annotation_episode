"""Private A110 Results target_custody"""
from __future__ import annotations
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class ResultsTargetCustody:

    def _context_target(self, context, target):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_launch(plain(context.assignment)) or is_compact_assignment(plain(context.assignment)):
            own = read_request_binding(self.store, self.run_id, context.episode_id)
            original = read_request_binding(self.store, self.run_id, target['origin_episode_id'])
            if not any((row['assignment'] == target['assignment'] for row in own['requests'])) or target['assignment'] != original['requests'][0]['assignment'] or (context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        if context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target
