"""The A101 head's continuation: its configured yield binding for its own credit task."""
from __future__ import annotations

from method_loop.jsonvalue import content_digest

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import plain
from .contract_binding import AXIS
from .native_correspondence_credit import A101SequenceCredit

# The head's one credit task: A101's native sequence-correspondence projection.
HEAD_TASK = AXIS + ':' + A101SequenceCredit().as_record()['kind']


class SequenceHomologyEvidenceYield:

    def head_yield_controller(self, epoch, initial_credit):
        """Bind this head episode to its configured credit forecast and continuation cutoff.

        The yield declaration for ``HEAD_TASK`` fixes the estimator kind, its
        parameters, the cutoff and the exact credit definition. A head
        configured without one has no continuation and raises.
        """
        if self._yield_bindings is None:
            raise ContractError('a101_head_yield_bindings_not_configured')
        declaration = self._yield_bindings.get(HEAD_TASK)
        if declaration is None:
            raise ContractError('a101_head_yield_binding_missing_for_task:' + HEAD_TASK)
        projector = A101SequenceCredit()
        if content_digest(plain(projector.as_record())) != content_digest(declaration['credit_definition']):
            raise ContractError('a101_head_yield_credit_definition_mismatch:' + HEAD_TASK)
        if declaration['kind'] != projector.yield_method:
            raise ContractError('a101_head_yield_method_credit_mismatch:' + HEAD_TASK)
        from yield_control import BoundedQualityYieldController, YieldParameters
        return BoundedQualityYieldController(epoch, initial_credit, declaration['cutoff'], projector.native_score_maximum,
                                           YieldParameters(**declaration['parameters']))
