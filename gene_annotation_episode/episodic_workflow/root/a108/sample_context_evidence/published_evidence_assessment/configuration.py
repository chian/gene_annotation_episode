from __future__ import annotations
'configuration for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.source_contracts import CONTRACT_INFORMATION_PROFILE, plain

class LiteratureConfiguration:

    def __init__(self, services, *, outcome_page_size=8, reference_parent_sources=None, contract_information_profile=None, private_yield_binding=False, yield_bindings=None):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_literature_outcome_page_size_required')
        if type(private_yield_binding) is not bool:
            raise ValueError('boolean_private_literature_yield_binding_required')
        if yield_bindings is not None and (not private_yield_binding):
            raise ValueError('literature_yield_bindings_require_private_binding')
        from importlib import import_module as _private_yield_module
        validate_yield_bindings = _private_yield_module('gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.yield_estimator').validate_yield_bindings
        self.services = services
        self.outcome_page_size = outcome_page_size
        self.private_yield_binding = private_yield_binding
        self._yield_bindings = validate_yield_bindings({} if yield_bindings is None else plain(yield_bindings))
        if contract_information_profile is not None and contract_information_profile != CONTRACT_INFORMATION_PROFILE:
            raise ValueError('unsupported_literature_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        if reference_parent_sources is not None:
            if not isinstance(reference_parent_sources, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in reference_parent_sources)) or len(set(reference_parent_sources)) != len(reference_parent_sources):
                raise ValueError('explicit_unique_reference_parent_sources_required')
            reference_parent_sources = tuple(reference_parent_sources)
        self.reference_parent_sources = reference_parent_sources

    @classmethod
    def reference_evidence(cls, services, *, source_refs, contract_information_profile=CONTRACT_INFORMATION_PROFILE, **configuration):
        return cls(services, reference_parent_sources=source_refs, contract_information_profile=contract_information_profile, **configuration)
