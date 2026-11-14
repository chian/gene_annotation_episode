"""Original annotation objective and result-contract identity."""
from __future__ import annotations
from .. import runtime as _runtime

def improvement_goal(parent, goal_text, name, contract):
    return _runtime.EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else _runtime.EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
