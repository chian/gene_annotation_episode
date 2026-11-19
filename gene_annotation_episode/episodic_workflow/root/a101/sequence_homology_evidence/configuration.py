"""Construction-time configuration of the A101 head binding.

``tool_registry`` is the head's own A101 ``ToolRegistry`` over the run's shared
store (built by ``home_factory.a101_home_factory``). ``library`` is the frozen
scientific library whose A101 evidence-axis entry the head presents with every
decision and whose thought patterns a commissioning parent chooses from.
``yield_bindings`` declares the head's continuation for its one credit task
(``yield_estimator.HEAD_TASK``). Nothing is defaulted: a missing or malformed
value raises.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sequence_homology_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import evidence_axis_instruction_view
from .contract_binding import AXIS

_THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                   'outcome_contingencies', 'boundary')


class ScientificConfiguration:

    def __init__(self, *, library, tool_registry, yield_bindings):
        from .yield_estimator import HEAD_TASK
        self.library, self.tool_registry = library, tool_registry
        self.evidence_axis = self._evidence_axis_view(library)
        # What a commissioning parent chooses per commission: one library thought pattern
        # and a subset of this head's own tools (ChoiceField / SubsetField of its assignment).
        self.thought_patterns = {header['option_ref']['option_id']:
                                 {name: entry[name] for name in _THOUGHT_FIELDS if name in entry}
                                 for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'
                                 for entry in (library.resolve(header['option_ref']),)}
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('a101_head_selection_options_required')
        if not isinstance(yield_bindings, Mapping) or set(yield_bindings) != {HEAD_TASK}:
            raise ContractError('a101_head_yield_bindings_must_declare_exactly:' + HEAD_TASK)
        self._yield_bindings = json.loads(json.dumps(dict(yield_bindings), allow_nan=False))
        declaration = self._yield_bindings[HEAD_TASK]
        if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                or not isinstance(declaration['parameters'], dict)
                or set(declaration['parameters']) != {'uncertainty_alpha'}
                or not isinstance(declaration['credit_definition'], dict) or not declaration['credit_definition']):
            raise ContractError('a101_head_yield_binding_invalid:' + HEAD_TASK)

    @staticmethod
    def _evidence_axis_view(library):
        """The library's A101 evidence-axis entry, in its own instruction view."""
        entry = library.resolve(library.reference(AXIS))
        if entry.get('entry_version') == INSTRUCTION_VERSION:
            return instruction_view(entry)
        if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
            return evidence_axis_instruction_view(entry)
        raise ContractError('a101_evidence_axis_entry_invalid')
