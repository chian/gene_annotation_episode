"""Exact original caller-controller selection; original runtime capture callback retained."""
from __future__ import annotations

def select_controller(workflow, path):
    from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
    identity = Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1])
    row = workflow.journal.row('runtime_episodes', identity.episode_id)
    role = path[-1][0]
    binding = workflow.episode_bindings.for_path(path) if role in workflow.episode_bindings.roles else None
    bound = None
    task_controller = getattr(binding, 'yield_controller', None) if getattr(binding, 'private_yield_binding', False) else None
    task_controller is not None
    if getattr(workflow.controller_factory, 'requires_original_task', False):
        request = json.loads(row['request'])
        bound = BindingContext(workflow.run_id, identity.episode_id, role, path, request['message']['scope'], request['message'].get('episode_assignment', {}), request, tuple(workflow.receipts.known(identity.episode_id)) if workflow.receipts is not None else ())
        task_key = credit_definition = None
        scientific_child = len(path) > 1 and (role == 'improvement' or (binding is not None and binding.credit_kind(role) == 'scientific'))
        scientific_child
        controller = workflow.controller_factory(path, row['initial_credit'], context=bound, task_key=task_key, credit_definition=credit_definition)
    else:
        controller = workflow.controller_factory(path, row['initial_credit'])
    binding is not None and task_controller is None
    return (controller, identity)


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'select_controller': select_controller}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.yield')
    globals()['select_controller'] = bound['select_controller']

from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__, _bind_preserved_runtime_providers)
