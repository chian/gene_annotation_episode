"""The A106 head binding (``perturbation_evidence``).

Its decision behaviour on the generic runner is ``runtime_source`` (built by
``HeadContract.build_episode``); ``ScientificConfiguration`` holds its
construction-time library, tool library, own tool registry, child roles and
continuation declaration, and ``PerturbationEvidenceYield`` builds its declared
yield controller.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .configuration import ScientificConfiguration
from .episode_contract import CHILD_SLOTS, HeadContract, head_form, scientific_credit_unit
from .goal import ScientificGoal
from .scientific_contracts import AXIS, ContractError, ROLE, ROLES
from .yield_estimator import TASK, PerturbationEvidenceYield


class PerturbationEvidenceEpisode(HeadContract, ScientificConfiguration, ScientificGoal, PerturbationEvidenceYield):
    """The recursive A106 head: its own sub-scope children and literature assessments."""
    binding_path = 'perturbation_evidence'
    goal = "The parent's annotation question, answered by distinct retained perturbation-evidence findings about the target"
    unit = "One selected tool, reasoning or child action of the perturbation investigation"
    result = "The distinct retained perturbation findings and their accumulated credit"
    commissioning_parent = 'annotation'
    roles = ROLES

    def __init__(self, services, **configuration):
        super().__init__(services, **configuration)
        if TASK not in self._yield_bindings:
            raise ContractError('scientific_yield_binding_missing_for_task:' + TASK)
        policy = self._yield_bindings[TASK]['credit_definition'].get('policy')
        if not isinstance(policy, Mapping) or 'finding_unit' not in policy:
            raise ContractError('scientific_yield_credit_definition_requires_finding_unit:' + TASK)
        unit = policy['finding_unit']
        # The declared evidence task carries the finding unit of the head's own declared credit definition.
        self.assignment_form = head_form(unit, self.thought_patterns, self.selectable_tools)

    def child_roles(self, role):
        if role != ROLE:
            raise ContractError('perturbation_evidence_role_not_bound')
        return self._child_roles

    @property
    def child_slots(self):
        """Declared slots limited to this head's configured child roles."""
        return MappingProxyType({slot: path for slot, path in CHILD_SLOTS[self.binding_path].items()
                                 if slot in self._child_roles})

    _literature_binding = None

    def bind_literature(self, literature):
        """Take the literature binding, whose own commission check and typed report the literature child uses."""
        if self._literature_binding is not None:
            raise ContractError('a106_head_literature_already_bound')
        if literature.binding_path != CHILD_SLOTS[self.binding_path]['literature']:
            raise ContractError('a106_head_literature_binding_required:' + str(literature.binding_path))
        self._literature_binding = literature

    @property
    def literature_binding(self):
        if self._literature_binding is None:
            raise ContractError('a106_head_literature_unbound')
        return self._literature_binding

    def contract_credit_unit(self, assignment):
        return scientific_credit_unit(assignment)

    def instructions(self):
        """The A106 investigation instructions this head presents with every decision."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
        specialized = self.specialized_instructions()
        instructions = specialized if self.replaces_default_instructions else INSTRUCTIONS + '\n' + specialized
        return instructions + '\n' + REASONING_COMMIT_REQUIREMENT


__all__ = ['AXIS', 'PerturbationEvidenceEpisode']
