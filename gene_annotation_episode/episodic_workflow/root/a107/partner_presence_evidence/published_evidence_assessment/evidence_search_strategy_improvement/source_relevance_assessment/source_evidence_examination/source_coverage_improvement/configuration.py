"""Private A107 configuration."""
from __future__ import annotations
from .contracts import CONTRACT_INFORMATION_PROFILE

class LiteratureConfiguration:

    def __init__(self, services, *, outcome_page_size=8, reference_parent_sources=None, contract_information_profile=None):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_a107_literature_outcome_page_size_required')
        self.services = services
        self.outcome_page_size = outcome_page_size
        if contract_information_profile is not None and contract_information_profile != CONTRACT_INFORMATION_PROFILE:
            raise ValueError('unsupported_a107_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        if reference_parent_sources is not None:
            if not isinstance(reference_parent_sources, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in reference_parent_sources)) or len(set(reference_parent_sources)) != len(reference_parent_sources):
                raise ValueError('explicit_unique_reference_parent_sources_required')
            reference_parent_sources = tuple(reference_parent_sources)
        self.reference_parent_sources = reference_parent_sources

    @classmethod
    def reference_evidence(cls, services, *, source_refs, contract_information_profile=CONTRACT_INFORMATION_PROFILE, **configuration):
        return cls(services, reference_parent_sources=source_refs, contract_information_profile=contract_information_profile, **configuration)

    def contract_information_configuration(self):
        return self._contract_information_profile

    def reasoning_action_schema(self, context, commit_schema):
        return None

    def reasoning_has_task_content(self, context, selection):
        return False

    def execute_reasoning(self, context, selection, operation_key):
        return None
