from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificConfiguration:
    def __init__(self, services, *, library, tool_library, child_roles, tool_retrieval=None,
                 contract_information_profile=None, yield_bindings=None):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles
                or any(not isinstance(role, str) or not role for role in child_roles)
                or len(set(child_roles)) != len(child_roles) or ROLE not in child_roles):
            raise ContractError("scientific_child_roles_invalid")
        self.services, self.library, self.tool_library = services, library, tool_library
        self._child_roles = tuple(child_roles)
        self._library_record = _object(library.as_record(), "scientific_library_invalid")
        self._tools_record = _object(tool_library.as_record(), "scientific_tool_library_invalid")
        axes = [header['option_ref'] for header in library.headers()
                if header['option_ref']['slot'] == 'evidence_axis']
        # This runtime capability is binding-wide. Opt in only for a wholly
        # instruction-only publication; other catalogs use the default
        # instruction composition.
        self.replaces_default_instructions = bool(axes) and all(
            library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION
            for reference in axes)
        from gene_annotation_episode.episodic_workflow.root.library.scientific_tool_configuration import configuration
        self.tool_retrieval = configuration(tool_retrieval)
        from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ContractError('unsupported_scientific_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self._yield_bindings = (None if yield_bindings is None else
            _object(yield_bindings, 'scientific_yield_bindings_invalid'))
        if self._yield_bindings is not None:
            if not isinstance(self._yield_bindings, dict):
                raise ContractError('scientific_yield_bindings_invalid')
            from gene_annotation_episode.episodic_workflow.root.numerical import (BoundedYieldController, CompletionYieldController,
                YieldController, YieldParameters)
            for task, declaration in self._yield_bindings.items():
                if (not isinstance(task, str) or ':' not in task
                        or not isinstance(declaration, dict)
                        or set(declaration) != {'kind', 'cutoff', 'parameters',
                                                'credit_definition'}
                        or declaration['kind'] not in {'accumulation', 'bounded_quality', 'completion'}
                        or not isinstance(declaration['parameters'], dict)
                        or set(declaration['parameters']) != {'uncertainty_alpha'}
                        or not isinstance(declaration['credit_definition'], dict)
                        or not declaration['credit_definition']):
                    raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
                try:
                    parameters = YieldParameters(**declaration['parameters'])
                    if declaration['kind'] == 'bounded_quality':
                        BoundedYieldController('configuration', 0, declaration['cutoff'], 1., parameters)
                    elif declaration['kind'] == 'completion':
                        CompletionYieldController('configuration', 0, declaration['cutoff'], parameters)
                    else:
                        YieldController('configuration', 0, declaration['cutoff'], parameters)
                except (TypeError, ValueError) as error:
                    raise ContractError('scientific_yield_task_binding_invalid:' + task) from error

    def contract_information_profile(self, context):
        """Expose frozen contract information to scientific commissioning parents."""
        return (self._contract_information_profile
                if context.role in ('annotation', ROLE) else None)

    @property
    def private_yield_binding(self):
        return self._yield_bindings is not None

