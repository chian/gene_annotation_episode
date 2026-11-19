"""Construction-time configuration of the A106 head binding.

``library`` is the frozen perturbation-evidence library whose A106 evidence-axis
entry the head presents with every decision and whose thought patterns a
commissioning parent chooses from; ``tool_library`` is the frozen A106 tool
library whose tools (each a name and its resource kind) a commissioning parent
selects; ``tool_registry`` is the head's own A106 tool registry over the run's
shared store, which executes them; ``child_roles`` names the children it may
commission (itself first); ``yield_bindings`` declares its continuation for
``A106:whole_axis_findings``. Nothing is defaulted: a missing or malformed value
raises.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.evidence_axis_contracts import validate_evidence_axis_entry
from gene_annotation_episode.episodic_workflow.episode_support.instructions.perturbation_evidence.evidence_axis_instructions import validate_instruction_entry
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.construction_records import SELECTION_VERSION, selection_fields, validate_selection
from .episode_contract import CHILD_SLOTS
from .scientific_contracts import (AXIS, ContractError, EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, ROLE,
                                   evidence_axis_instruction_view, instruction_view)


def tool_option(row):
    """One selectable tool as the text option a parent chooses: ``<name>@<resources>``."""
    return row['name'] + '@' + row['resources']


def tool_selector(option):
    """The tool-library selector of a chosen tool option."""
    name, _, resources = option.rpartition('@')
    return {'name': name, 'resources': resources}


class ScientificConfiguration:

    def __init__(self, services, *, library, tool_library, tool_registry, child_roles, yield_bindings):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles or len(set(child_roles)) != len(child_roles)
                or child_roles[0] != ROLE or any(role not in CHILD_SLOTS[ROLE] for role in child_roles)):
            raise ContractError('scientific_child_roles_invalid')
        self.services, self.library, self.tool_library = services, library, tool_library
        self.tool_registry = tool_registry
        self._child_roles = tuple(child_roles)
        self._library_id = library.as_record()['library_id']
        entry = library.resolve(library.reference(AXIS))
        if entry.get('entry_version') == INSTRUCTION_VERSION:
            self.evidence_axis = instruction_view(entry)
        elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
            self.evidence_axis = evidence_axis_instruction_view(entry)
        else:
            raise ContractError('scientific_support_metadata_required')
        axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'evidence_axis']
        self.replaces_default_instructions = bool(axes) and all(
            library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION for reference in axes)
        # What a commissioning parent selects per commission, as in the original A/P selection: one thought
        # pattern of the library and a subset of the tool library's tools the head's registry offers.
        self.thought_patterns = tuple(sorted(header['option_ref']['option_id'] for header in library.headers()
                                             if header['option_ref']['slot'] == 'thought_pattern'))
        self.selectable_tools = tuple(sorted(tool_option(row) for row in
                                             tool_library.parent_tool_info(tool_registry.catalog(None))))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('scientific_selection_options_required')
        if not isinstance(yield_bindings, Mapping):
            raise ContractError('scientific_yield_bindings_invalid')
        self._yield_bindings = json.loads(json.dumps(dict(yield_bindings), allow_nan=False))
        from yield_control import AccumulationYieldController, YieldParameters
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

    def commissioned_selection(self, thought_pattern, tools, available_catalog):
        """The parent-selected A106 process of one commission: the A106 axis, the chosen thought pattern and tools.

        Each selected tool must be in the head's tool library and offered by the
        available tool catalog with an unchanged contract.
        """
        # Materialize the chosen tools as the tool library's canonical tool information (as the original did).
        tool_info = self.tool_library.resolve_tool_info([tool_selector(option) for option in tools], available_catalog)
        selection = validate_selection({'version': SELECTION_VERSION, 'evidence_axis': self.library.reference(AXIS),
                                        'thought_pattern': self.library.reference(thought_pattern),
                                        'child_tool_info': tool_info})
        fields = selection_fields(selection)
        for key in fields[:2]:
            if selection[key]['library_id'] != self._library_id:
                raise ContractError('scientific_selection_library_mismatch')
        entry = self.library.resolve(selection[fields[0]])
        if entry.get('entry_version') == INSTRUCTION_VERSION:
            validate_instruction_entry(entry)
        elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
            validate_evidence_axis_entry(entry)
        else:
            raise ContractError('scientific_support_metadata_required')
        self.library.resolve(selection[fields[1]])
        return selection
