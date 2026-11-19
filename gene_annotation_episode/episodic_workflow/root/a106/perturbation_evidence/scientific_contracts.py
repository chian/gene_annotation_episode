"""The A106 head's fixed identities and the library views its instructions read."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.perturbation_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.configuration.perturbation_evidence.process_options import evidence_axis_instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.construction_records import scientific_digest

AXIS = 'A106'
ROLE = 'perturbation_evidence'
ROLES = (ROLE,)
# A persistent record reference (no in-commit alias).
_REFERENCE = {'type': 'string', 'pattern': '^[a-z][a-z_]*_[a-f0-9]{24,64}$'}

__all__ = ['AXIS', 'ContractError', 'EVIDENCE_AXIS_VERSION', 'INSTRUCTION_VERSION', 'ROLE', 'ROLES', '_REFERENCE',
           'evidence_axis_instruction_view', 'instruction_view', 'plain', 'scientific_digest']
