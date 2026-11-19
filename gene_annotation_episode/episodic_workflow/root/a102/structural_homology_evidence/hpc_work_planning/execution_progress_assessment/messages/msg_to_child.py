"""What this monitor sends the ordinary monitor it may commission (carried from
``to_child_execution_progress_assessment.py`` and the old ``allowed_children`` / ``prepare_child_request``).

The one child slot is this monitor's own kind. A child monitor may be commissioned only while the assigned
target exposes a direct dependency; its target must be one of those exposed direct dependencies and its
permitted committed record types may not be wider than this monitor's own.
"""
from __future__ import annotations

from method_loop import ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.child_commissions import (
    commission_child, fill_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.closed_json import closed_record
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, plain)

from ..goal import GOAL, RESULT
from .read_from_parent import admit_assignment

SLOT = 'execution_progress_assessment'
REPORT = {'decision': 'Use the dependency monitor\'s delivered progress in this monitor\'s cycle',
          'measurements': {},
          'information': {'finding': 'The dependency monitor\'s delivered monitoring facts'}}


def dependency_handles(progress, assignment, scope):
    """The exposed direct dependencies of the target (old ``services.dependencies``)."""
    return [row['handle'] for row in progress.direct_dependencies(assignment['target_handle'], plain(scope))]


def allowed_children(progress, assignment, scope):
    """The slot is offered only when the assigned target exposes a direct dependency."""
    return (SLOT,) if dependency_handles(progress, assignment, scope) else ()


def prepare_dependency_request(progress, original, scope, value):
    """Request one exposed direct dependency, preserving the parent's constraints."""
    if value['target_handle'] not in set(dependency_handles(progress, original, scope)):
        raise ContractError('monitor_child_target_not_exposed_direct_dependency')
    if not set(value['permitted_committed_record_types']) <= set(original['permitted_committed_record_types']):
        raise ContractError('monitor_child_expands_permitted_record_types')
    return value


def child_commission(builder, request, progress, original, scope, selected):
    """The admitted commission of one dependency monitor (no unit exists when this raises)."""
    value = admit_assignment(progress, {'version': 'monitor_assignment_v1', **plain(selected)}, scope)
    value = prepare_dependency_request(progress, original, scope, value)
    assignment = fill_assignment(builder.assignment_form,
                                 {'scope': plain(scope), **{name: item for name, item in value.items()
                                                            if name != 'version'}})
    return commission_child(request, objective=GOAL, result_contract={'credit': 'number', 'finding': RESULT},
                            message=closed_record({'target_handle': value['target_handle']}),
                            report_contract=ReportContract(**REPORT), assignment=assignment)
