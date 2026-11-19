"""Construction-time configuration of the A105 head binding.

``tool_registry`` is the head's own tool registry over the run's shared store.
``library`` is the frozen experimental-activity library: its A105 evidence-axis
instructions are presented with every decision, and its thought patterns are
the options a commissioning parent chooses from. ``child_roles`` names the
children the head may commission (itself first); ``yield_bindings`` declares its
continuation for ``A105:whole_axis_findings``. Nothing is defaulted: a missing
or malformed value raises.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.experimental_activity_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.experimental_activity_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.configuration.experimental_activity_evidence.process_options import evidence_axis_instruction_view

AXIS = 'A105'
ROLE = 'experimental_activity_evidence'
ROLES = (ROLE,)
_THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                   'outcome_contingencies', 'boundary')


class ScientificConfiguration:

    def __init__(self, *, library, tool_registry, child_roles, yield_bindings):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles or len(set(child_roles)) != len(child_roles)
                or child_roles[0] != ROLE or any(role not in (ROLE, 'literature') for role in child_roles)):
            raise ContractError('scientific_child_roles_invalid')
        self.library, self._child_roles, self.tool_registry = library, tuple(child_roles), tool_registry
        self.evidence_axis = self._evidence_axis_view(library)
        # The selection a commissioning parent makes per commission: one library thought pattern and a subset
        # of this head's own tools.
        self.thought_patterns = {header['option_ref']['option_id']: self._thought_view(library.resolve(header['option_ref']))
                                 for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'}
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('scientific_selection_options_required')
        if not isinstance(yield_bindings, Mapping):
            raise ContractError('scientific_yield_bindings_invalid')
        self._yield_bindings = json.loads(json.dumps(dict(yield_bindings), allow_nan=False))
        from yield_control import AccumulationYieldController, YieldParameters
        # The head's only credit is accumulated distinct findings, so its only controller is the accumulation
        # yield controller (yield_estimator.head_controller).
        for task, declaration in self._yield_bindings.items():
            if (task != AXIS + ':whole_axis_findings' or not isinstance(declaration, dict)
                    or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                    or declaration['kind'] != 'accumulation' or not isinstance(declaration['parameters'], dict)
                    or set(declaration['parameters']) != {'uncertainty_alpha'}
                    or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
                raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
            try:
                AccumulationYieldController('configuration', 0, declaration['cutoff'], YieldParameters(**declaration['parameters']))
            except (TypeError, ValueError) as error:
                raise ContractError('scientific_yield_task_binding_invalid:' + task) from error

    @staticmethod
    def _evidence_axis_view(library):
        """The library's A105 evidence-axis entry, in its own instruction view."""
        for header in library.headers():
            reference = header['option_ref']
            if reference['slot'] == 'evidence_axis' and reference['option_id'] == AXIS:
                entry = library.resolve(reference)
                if entry.get('entry_version') == INSTRUCTION_VERSION:
                    return instruction_view(entry)
                if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                    return evidence_axis_instruction_view(entry)
                raise ContractError('scientific_support_entry_invalid')
        raise ContractError('a105_library_requires_published_a105_evidence_axis_instructions')

    @staticmethod
    def _thought_view(entry):
        """The thought-pattern fields presented with each decision."""
        return {name: entry[name] for name in _THOUGHT_FIELDS if name in entry}
