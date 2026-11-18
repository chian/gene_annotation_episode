'A106 original unbound improvement/job child options, shared by actual public/unbound parent task paths. Original captured specialist, explicit role filter and job-family callbacks remain authoritative; no new child capability is supplied.'
from __future__ import annotations
from .live_runtime_functions import bind_functions as _bind_functions

def append_unbound_child_options(self, source, specialist, common_actions, explicit_roles, scientific_child, options):
    if specialist is None and self.perturbation_evidence_binding is None and ('child' in common_actions) and (explicit_roles is None or 'improvement' in explicit_roles):
        options.append(scientific_child)
    if self.job_episodes is not None and specialist is None:
        options.extend((option for option in self.job_episodes.commission_schemas(scientific_child) if explicit_roles is None or option['properties']['role']['const'] in explicit_roles))

def _default_scientific_child_roles(self):
    return (*(() if self.perturbation_evidence_binding is not None else ('improvement',)), *(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.entry_roles)

def _bind_original_runtime(namespace):
    names = {'append_unbound_child_options': 'append_unbound_child_options', '_default_scientific_child_roles': 'Workflow._default_scientific_child_roles'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names}, runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.library.unbound_child_action_options'))
    globals()['_default_scientific_child_roles'].__module__ = 'gene_annotation_episode.episodic_workflow.root.a106.runtime'

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
