"""A105 head credit on its own unbounded scale: distinct retained target findings known to this Episode.

The head's commission (``episode_runtime`` assignment) carries its own declared
whole-axis task (``evidence_task``) and the subject ``scope``. Credit is one
``credit_unit`` per distinct retained typed finding among the assessments this
Episode has actually received (its ``EpisodeReceipts`` in the scientific
store). It is never bounded, clamped or rescaled.
"""
from __future__ import annotations

import math

from episode_runtime import RecordForm
from method_loop import EpisodeRef

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress

AXIS = 'A105'
_TASK_FIELDS = {'version', 'kind', 'evidence_axis', 'credit_unit'}


def evidence_task_projector(task):
    """The head's finding-progress projector for its own declared whole-axis task."""
    task = plain(task)
    if (not isinstance(task, dict) or set(task) != _TASK_FIELDS or task['version'] != 'evidence_axis_task_v1'
            or task['kind'] != 'whole_axis_findings' or task['evidence_axis'] != AXIS):
        raise ContractError('original_axis_finding_task_required')
    return ScientificFindingProgress(FindingProgressPolicy(task['credit_unit']))


def parent_episode_id(bound, grain_name):
    """The Episode id of this head's parent when the parent is itself an A105 head, else ``None``.

    Only an A105 head keeps A105 receipts; the root annotation episode (or any
    other commissioning parent) hands the head nothing but its ``scope``.
    """
    parent = tuple(bound.path[:-1])
    if parent and parent[-1][0] == grain_name:
        return EpisodeRef(bound.run_id, parent).episode_id
    return None


class ExperimentalActivityEvidenceCredit:

    def credit_projector(self, assignment):
        """The projector for an admitted head assignment (``scope`` + declared ``evidence_task``)."""
        if not isinstance(self.assignment_form, RecordForm):
            raise ContractError('a105_head_assignment_form_required')
        admitted = self.assignment_form.admit(assignment, 'a105_head_credit_assignment')
        return evidence_task_projector(admitted['evidence_task'])

    def open_receipts(self, store, bound):
        """Bind this Episode's receipts once and receive its subject as initial knowledge.

        Idempotent: a rebuilt Episode recovers the binding it recorded before and
        re-receives the same subject references (receipts are unique per record).
        """
        receipts = EpisodeReceipts(store, bound.run_id)
        receipts.bind(bound.episode_id, parent_episode_id(bound, self.grain_name))
        scope = store.validate_scope(plain(bound.assignment['scope']))
        receipts.receive(bound.episode_id, scope['subject_refs'], kind='initial')
        return receipts

    def known_finding_credit(self, store, bound):
        """Project this Episode's credit from the assessments it has received.

        Returns the scalar ``credit`` and the projection's own finding details.
        """
        projector = self.credit_projector(bound.assignment)
        known = list(EpisodeReceipts(store, bound.run_id).known(bound.episode_id, record_type='assessment'))
        projected = projector(store, plain(bound.assignment['scope']), known_assessment_refs=known)
        credit = float(projected['credit'])
        if not math.isfinite(credit):
            raise ContractError('a105_finite_head_credit_required')
        result = {'credit': credit}
        for key in ('retained_finding_count', 'source_contributions', 'inactive_dependencies', 'detail_pages',
                    'interpretation', 'policy'):
            result[key] = plain(projected[key])
        return result
