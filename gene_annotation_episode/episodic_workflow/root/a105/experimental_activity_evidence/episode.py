"""The A105 head binding (``experimental_activity_evidence``).

Its decision behaviour on the generic runner is ``runtime_source`` (built by
``HeadRuntimeContract.build_episode``); ``ScientificConfiguration`` holds its
construction-time library, tool registry, child roles and continuation
declaration; its credit and controller are ``credit`` and ``yield_estimator``.
"""
from __future__ import annotations

from gene_annotation_episode.domain import ContractError

from .configuration import ROLE, ROLES, ScientificConfiguration
from .credit import ExperimentalActivityEvidenceCredit
from .runtime_binding import HeadRuntimeContract
from .yield_estimator import ExperimentalActivityEvidenceYield


class ExperimentalActivityEvidenceEpisode(HeadRuntimeContract, ScientificConfiguration,
                                          ExperimentalActivityEvidenceCredit, ExperimentalActivityEvidenceYield):
    """The recursive A105 head: narrower experimental-activity children and literature assessments."""
    binding_path = 'experimental_activity_evidence'
    commissioning_parent = 'annotation'
    roles = ROLES

    def child_roles(self, role):
        if role != ROLE:
            raise ContractError('experimental_activity_evidence_role_not_bound')
        return self._child_roles
