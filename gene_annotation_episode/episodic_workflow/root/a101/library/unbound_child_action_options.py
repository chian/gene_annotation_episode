"""Substantive A101 policy definitions; original live runtime globals retained."""

def append_unbound_child_options(self, specialist, common_actions, explicit_roles, scientific_child, options):
    if specialist is None and self.scientific_process_binding is None and ('child' in common_actions) and (explicit_roles is None or 'improvement' in explicit_roles):
        options.append(scientific_child)
    if self.job_episodes is not None and specialist is None:
        options.extend((option for option in self.job_episodes.commission_schemas(scientific_child) if explicit_roles is None or option['properties']['role']['const'] in explicit_roles))

def _default_scientific_child_roles(self):
    return (*(() if self.scientific_process_binding is not None else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('append_unbound_child_options', '_default_scientific_child_roles')},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'append_unbound_child_options': 'append_unbound_child_options', '_default_scientific_child_roles': 'Workflow._default_scientific_child_roles'},
        defining_module=None)
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
