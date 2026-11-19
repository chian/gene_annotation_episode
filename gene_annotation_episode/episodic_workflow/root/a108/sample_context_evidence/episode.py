"""The A108 head binding (``sample_context_evidence``).

Its decision behaviour on the generic runner is ``runtime_source`` (built by
``HeadRuntimeContract.build_episode``); ``ScientificConfiguration`` holds its
construction-time library, child roles and continuation declaration.
"""
from __future__ import annotations

from gene_annotation_episode.domain import ContractError

from .configuration import ROLE, ROLES, ScientificConfiguration
from .runtime_contract import HeadRuntimeContract


class SampleContextEvidenceEpisode(HeadRuntimeContract, ScientificConfiguration):
    """The recursive A108 head: its own sub-scope children and literature assessments."""
    binding_path = 'sample_context_evidence'
    commissioning_parent = 'annotation'
    roles = ROLES

    def child_roles(self, role):
        if role != ROLE:
            raise ContractError('sample_context_evidence_role_not_bound')
        return self._child_roles
