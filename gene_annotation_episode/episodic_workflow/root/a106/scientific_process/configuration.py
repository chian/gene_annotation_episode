"""Private scientific configuration."""
from __future__ import annotations
from .scientific_contracts import ContractError, INSTRUCTION_VERSION, ROLE, _object

class ScientificConfiguration:

    def __init__(self, services, *, library, tool_library, child_roles, tool_retrieval=None, contract_information_profile=None, yield_bindings=None):
        if not isinstance(child_roles, (tuple, list)) or not child_roles or any((not isinstance(role, str) or not role for role in child_roles)) or (len(set(child_roles)) != len(child_roles)) or (ROLE not in child_roles):
            raise ContractError('scientific_child_roles_invalid')
        self.services, self.library, self.tool_library = (services, library, tool_library)
        self._child_roles = tuple(child_roles)
        self._library_record = _object(library.as_record(), 'scientific_library_invalid')
        self._tools_record = _object(tool_library.as_record(), 'scientific_tool_library_invalid')
        axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] in ('evidence_axis', 'annotation_distinction')]
        self.replaces_default_instructions = bool(axes) and all((library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION for reference in axes))
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_tool_retrieval import configuration
        self.tool_retrieval = configuration(tool_retrieval)
        from gene_annotation_episode.episodic_workflow.root.a106.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ContractError('unsupported_scientific_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self._yield_bindings = None if yield_bindings is None else _object(yield_bindings, 'scientific_yield_bindings_invalid')
        if self._yield_bindings is not None:
            if not isinstance(self._yield_bindings, dict):
                raise ContractError('scientific_yield_bindings_invalid')
            from gene_annotation_episode.episodic_workflow.root.a106.numerical import BoundedYieldController, CompletionYieldController, YieldController, YieldParameters
            for task, declaration in self._yield_bindings.items():
                if not isinstance(task, str) or ':' not in task or (not isinstance(declaration, dict)) or (set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}) or (declaration['kind'] not in {'accumulation', 'bounded_quality', 'completion'}) or (not isinstance(declaration['parameters'], dict)) or (set(declaration['parameters']) != {'uncertainty_alpha'}) or (not isinstance(declaration['credit_definition'], dict)) or (not declaration['credit_definition']):
                    raise ContractError('scientific_yield_task_binding_invalid:' + str(task))
                try:
                    parameters = YieldParameters(**declaration['parameters'])
                    if declaration['kind'] == 'bounded_quality':
                        BoundedYieldController('configuration', 0, declaration['cutoff'], 1.0, parameters)
                    elif declaration['kind'] == 'completion':
                        CompletionYieldController('configuration', 0, declaration['cutoff'], parameters)
                    else:
                        YieldController('configuration', 0, declaration['cutoff'], parameters)
                except (TypeError, ValueError) as error:
                    raise ContractError('scientific_yield_task_binding_invalid:' + task) from error
