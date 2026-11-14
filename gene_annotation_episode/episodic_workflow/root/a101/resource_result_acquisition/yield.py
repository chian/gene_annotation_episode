"""Private results original continuation factory selection; caller settings unchanged."""
import json

class OriginalContinuation:
    def original_continuation_controller(self, workflow, path, row, identity, binding, bound):
        """Retain original factory operands, including the original runtime binding."""
        from gene_annotation_episode.episodic_workflow.root.a101.runtime import BindingContext, _plain
        role = path[-1][0]
        if getattr(workflow.controller_factory, 'requires_original_task', False):
            request = json.loads(row['request'])
            bound = BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
            task_key = credit_definition = None
            scientific_child = len(path) > 1 and (role == 'improvement' or (binding is not None and binding.credit_kind(role) == 'scientific'))
            if scientific_child:
                choose_task = getattr(binding, 'continuation_task', None)
                if choose_task is None:
                    raise ValueError('scientific_continuation_task_not_declared:' + role)
                task_key = choose_task(bound)
                if not isinstance(task_key, str) or not task_key:
                    raise ValueError('scientific_continuation_task_not_declared:' + role)
                credit_definition = _plain(workflow.scientific_projector_for_context(bound).as_record())
            controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
        else:
            controller = workflow.controller_factory(path, row['initial_credit'])
        return controller, bound
