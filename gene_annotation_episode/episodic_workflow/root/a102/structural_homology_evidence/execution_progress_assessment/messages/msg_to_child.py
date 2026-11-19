"""What the A102 monitor sends the monitor it may commission (carried from ``to_child_execution_progress_assessment.py``
and the dependency branch of ``from_parent.prepare_assignment``).

Its one child slot is a monitor of its own kind (self-nesting). The child's target must be one of this target's
exposed direct dependencies and the child's permitted committed record types must not exceed this monitor's. The
old runner ran this check inside the child (``prepare_dependency_request`` reading ``parent.assignment``); a child
cannot read its parent here, so the parent checks it before commissioning (a rejection creates no unit).
"""
from __future__ import annotations

from episode_runtime import Commission
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.child_commissions import fill_assignment
from gene_annotation_episode.episodic_workflow.episode_support.records.closed_json import closed_record
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError

from ..goal import GOAL

SLOT = 'execution_progress_assessment'
REPORT = {'decision': 'Use the child finding in the parent cycle', 'measurements': {},
          'information': {'finding': 'What the child established, with its record references'}}


def eligible_dependencies(provider, assignment, scope):
    """The exposed direct dependencies of this monitor's target (old ``services.dependencies``)."""
    return [row['handle'] for row in provider.direct_dependencies(assignment['target_handle'], scope)]


def prepare_dependency_request(provider, parent_assignment, scope, value):
    """The old ``prepare_dependency_request``: the dependency and record-type rules over the parent's assignment."""
    if value['target_handle'] not in set(eligible_dependencies(provider, parent_assignment, scope)):
        raise ContractError('monitor_child_target_not_exposed_direct_dependency')
    if not set(value['permitted_committed_record_types']) <= set(parent_assignment['permitted_committed_record_types']):
        raise ContractError('monitor_child_expands_permitted_record_types')
    return value


def commission(builder, request_goal, *, provider, parent_assignment, scope, selection):
    """The child's commission from an admitted ``child`` selection (raises before any child exists)."""
    value = prepare_dependency_request(provider, parent_assignment, scope, {
        'target_handle': selection['target_handle'],
        'requested_fields': list(selection['requested_fields']),
        'known_progress_refs': list(selection['known_progress_refs']),
        'permitted_committed_record_types': list(selection['permitted_committed_record_types'])})
    assignment = fill_assignment(builder.assignment_form, {'scope': scope, **value})
    goal = EpisodeGoal.child(request_goal, objective=GOAL, result_contract=dict(REPORT))
    request = EpisodeRequest(goal, closed_record({'target_handle': value['target_handle']}), ReportContract(**REPORT))
    return Commission(request, assignment)


__all__ = ['REPORT', 'SLOT', 'commission', 'eligible_dependencies', 'prepare_dependency_request']
