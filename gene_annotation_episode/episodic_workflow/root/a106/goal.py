"""Construct the original A106 commissioned objective and result contract.

The annotation parent owns this goal construction. The unchanged public and
custom request-envelope branches also consume the same defining function;
the existing private improvement path retains its own goal definition.
"""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def prepare_goal(name, goal_text, parent, contract):
    return EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)

def _bind_original_runtime(namespace):
    names = {'prepare_goal': 'prepare_goal'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime',
        qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.goal'))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
