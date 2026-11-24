"""The passage evidence extraction episode (A106): a private binding of the system's episode type."""
from episode_runtime import EpisodeBinding

from . import credit as credit_file, goal as goal_file, task as task_file, yield_estimator as yield_file
from .messages import (final_to_parent as final_file, internal_summary as summary_file,
                       read_from_parent as from_parent_file)


class PassageEvidenceExtraction(EpisodeBinding):
    binding_path = goal_file.BINDING_PATH
    goal = goal_file.GOAL
    unit = goal_file.UNIT
    result = goal_file.RESULT
    child_slots = task_file.CHILD_SLOTS
    tools = task_file.TOOLS
    services = task_file.SERVICES
    decide = task_file.decide
    offered_actions = task_file.offered_actions
    action = task_file.action
    credit = credit_file.credit
    ceiling = credit_file.ceiling
    yield_controller = yield_file.yield_controller
    assignment_form = from_parent_file.ASSIGNMENT_FORM
    read_from_parent = from_parent_file.read_from_parent
    internal_summary = summary_file.internal_summary
    return_form = final_file.RETURN_FORM
    final_to_parent = final_file.final_to_parent
