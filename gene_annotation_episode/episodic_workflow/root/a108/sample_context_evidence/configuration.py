"""Construction-time configuration of the A108 head binding.

``tool_registry`` is the head's own A108 tool registry over the run's shared store.
``library`` is the frozen scientific library whose A108 evidence-axis entry the
head presents with every decision; ``child_roles`` names the children it may
commission (itself first); ``yield_bindings`` declares its continuation for
``A108:whole_axis_findings``. Nothing is defaulted: a missing or malformed
value raises.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.sample_context_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sample_context_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sample_context_evidence.process_options import evidence_axis_instruction_view

AXIS = 'A108'
ROLE = 'sample_context_evidence'
ROLES = (ROLE,)
_KINDS = frozenset({'accumulation', 'completion'})


class ScientificConfiguration:

    def __init__(self, services, *, library, tool_registry, child_roles, yield_bindings):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles or len(set(child_roles)) != len(child_roles)
                or child_roles[0] != ROLE or any(role not in (ROLE, 'literature') for role in child_roles)):
            raise ContractError('scientific_child_roles_invalid')
        self.services, self.library, self._child_roles = services, library, tuple(child_roles)
        self.tool_registry = tool_registry
        self.evidence_axis = self._evidence_axis_view(library)
        # The selection a commissioning parent makes per commission:
        # one thought pattern from the library and a subset of this head's own tools.
        self.thought_patterns = {header['option_ref']['option_id']: self._thought_view(library.resolve(header['option_ref']))
                                 for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'}
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('scientific_selection_options_required')
        if not isinstance(yield_bindings, Mapping):
            raise ContractError('scientific_yield_bindings_invalid')
        self._yield_bindings = json.loads(json.dumps(dict(yield_bindings), allow_nan=False))
        from yield_control import AccumulationYieldController, CompletionYieldController, YieldParameters
        for task, declaration in self._yield_bindings.items():
            if (task != AXIS + ':whole_axis_findings' or not isinstance(declaration, dict)
                    or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                    or declaration['kind'] not in _KINDS or not isinstance(declaration['parameters'], dict)
                    or set(declaration['parameters']) != {'uncertainty_alpha'}
                    or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
                raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
            try:
                parameters = YieldParameters(**declaration['parameters'])
                if declaration['kind'] == 'accumulation':
                    AccumulationYieldController('configuration', 0, declaration['cutoff'], parameters)
                else:
                    CompletionYieldController('configuration', 0, declaration['cutoff'],
                                              declaration['credit_definition']['maximum_credit'], parameters)
            except (KeyError, TypeError, ValueError) as error:
                raise ContractError('scientific_yield_task_binding_invalid:' + task) from error

    @staticmethod
    def _evidence_axis_view(library):
        """The library's A108 evidence-axis entry, in its own instruction view."""
        entry = library.resolve(library.reference(AXIS))
        if entry.get('entry_version') == INSTRUCTION_VERSION:
            return instruction_view(entry)
        if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
            return evidence_axis_instruction_view(entry)
        raise ContractError('scientific_support_entry_invalid')

    @staticmethod
    def _thought_view(entry):
        """The thought-pattern fields presented with each decision."""
        return {name: entry[name] for name in ('id', 'name', 'description', 'use_when', 'live_alternatives',
                                               'decision_guidance', 'outcome_contingencies', 'boundary')
                if name in entry}
