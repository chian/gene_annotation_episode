"""Private annotation goal identity and original contract selection."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime

def improvement_goal(parent, goal_text, name, contract):
    return _original_runtime.EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else _original_runtime.EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
