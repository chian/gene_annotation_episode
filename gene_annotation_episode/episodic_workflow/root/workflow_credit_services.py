"""Root host ports defined by WorkflowCreditServices."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from .communication import plain

class WorkflowCreditServices:

    def annotation_task_required(self):
        return bool(getattr(self.workflow.project_credit, 'task_credit', False))

    def proposed_annotation_for(self, context):
        """Use the task's original assignment, including an ancestor commission."""
        reference = context.assignment.get('proposed_annotation_ref')
        if reference is not None:
            return reference
        for length in range(len(context.path) - 1, 0, -1):
            identity = EpisodeRef(context.run_id, context.path[:length]).episode_id
            row = self.workflow.journal.row('runtime_episodes', identity)
            if row is None:
                continue
            assignment = json.loads(row['request'])['message'].get('episode_assignment', {})
            reference = assignment.get('proposed_annotation_ref')
            if reference is not None:
                return reference
        return None

    def scientific_credit(self, context, receiver_selection):
        workflow = self.workflow
        local = len(context.path) > 1
        projector = workflow.scientific_projector_for_context(context)
        arguments = {}
        if local:
            request = context.request
            contract = request['report_contract']
            arguments.update(assignment={'goal': plain(request['goal']), 'scope': plain(context.scope), 'purpose': contract['decision'], 'schema': plain(contract['measurements']['schema']), 'initial_report': plain(request['message']['initial_report'])}, episode_id=context.episode_id, run_id=context.run_id)
            annotation = self.proposed_annotation_for(context)
            if annotation is not None:
                arguments['assignment']['proposed_annotation_ref'] = annotation
            elif self.annotation_task_required():
                raise ValueError('scientific_task_requires_original_proposed_annotation')
        arguments.update(workflow.projector_receipt_arguments(projector, context.episode_id))
        result = workflow.projection_view(projector, plain(context.scope), **arguments)
        if local and arguments['assignment'].get('proposed_annotation_ref') is not None:
            result['proposed_annotation_ref'] = arguments['assignment']['proposed_annotation_ref']
        return result

    def scientific_support_routes(self, context, *, observation_kinds):
        """Describe the actual separate annotation binding without projecting it."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_support_routes_receiver_identity_mismatch')
        routes = getattr(self.workflow.scientific_process_binding, 'scientific_support_routes', None)
        if routes is not None:
            return routes(self.workflow.project_annotation_score, self.workflow.annotation_score_binding, observation_kinds=observation_kinds)
        from .scientific_support_metadata import annotation_policy_routes
        return annotation_policy_routes(self.workflow.project_annotation_score, self.workflow.annotation_score_binding, observation_kinds=observation_kinds)

    def bound_role_credit(self, context, receiver_selection):
        bindings = self.workflow.role_credit_projectors
        if context.role not in bindings:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return bindings[context.role](context, receiver_selection)

