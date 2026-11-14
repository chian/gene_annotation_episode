"""A106 original implicit improvement responsibility; distinct private invocation."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def prepare_goal(name, goal_text, parent, contract):
    return EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)

def _bind_original_runtime(namespace):
    names = {'prepare_goal': 'prepare_goal'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.annotation_improvement.goal'))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
