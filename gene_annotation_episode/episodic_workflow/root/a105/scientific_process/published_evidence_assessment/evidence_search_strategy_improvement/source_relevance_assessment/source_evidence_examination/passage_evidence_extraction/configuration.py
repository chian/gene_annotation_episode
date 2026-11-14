from __future__ import annotations
'Private configuration responsibility for literature_targeted.'
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.source_contracts import CONTRACT_INFORMATION_PROFILE, deepcopy, plain

class LiteratureConfiguration:

    def __init__(self, services, *, outcome_page_size=8, rate_population=False, reference_parent_sources=None, contract_information_profile=None, ratio_source_population=False, ratio_source_evidence_origin='reported_source', controlled_response_population=False, controlled_response_descriptor=None, controlled_response_evidence_origin='reported_source', gel_population=False, gel_descriptor=None, gel_evidence_origin='reported_source', completion_time_population=False, product_partition_population=False, active_site_population=False, parent_depletion_population=False, stoichiometric_balance_population=False, compiled_assay_population=False, channel_population=False, ion_discrimination_population=False, assay_grading_population=False, private_yield_binding=False, yield_bindings=None):
        if type(private_yield_binding) is not bool:
            raise ValueError('boolean_private_literature_yield_binding_required')
        self.private_yield_binding = private_yield_binding
        if yield_bindings is not None and (not private_yield_binding):
            raise ValueError('literature_yield_bindings_require_private_binding')
        from importlib import import_module as _private_yield_module
        validate_yield_bindings = _private_yield_module('gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.yield').validate_yield_bindings
        self._yield_bindings = validate_yield_bindings({} if yield_bindings is None else plain(yield_bindings))
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_literature_outcome_page_size_required')
        self.services = services
        self.outcome_page_size = outcome_page_size
        if type(rate_population) is not bool:
            raise ValueError('boolean_rate_population_binding_required')
        self.rate_population = rate_population
        if type(assay_grading_population) is not bool or (assay_grading_population and (not rate_population)):
            raise ValueError('assay_grading_population_requires_rate_population')
        self.assay_grading_population = assay_grading_population
        if type(channel_population) is not bool or (channel_population and (not rate_population)):
            raise ValueError('channel_population_requires_rate_population')
        self.channel_population = channel_population
        if type(ion_discrimination_population) is not bool or (ion_discrimination_population and (not rate_population)):
            raise ValueError('ion_discrimination_population_requires_rate_population')
        self.ion_discrimination_population = ion_discrimination_population
        if type(compiled_assay_population) is not bool or (compiled_assay_population and (not rate_population)):
            raise ValueError('compiled_assay_population_requires_rate_population')
        self.compiled_assay_population = compiled_assay_population
        if type(completion_time_population) is not bool:
            raise ValueError('boolean_completion_time_population_binding_required')
        if completion_time_population and (not rate_population):
            raise ValueError('completion_time_population_requires_rate_population')
        self.completion_time_population = completion_time_population
        if type(active_site_population) is not bool:
            raise ValueError('boolean_active_site_population_binding_required')
        if active_site_population and (not rate_population):
            raise ValueError('active_site_population_requires_rate_population')
        self.active_site_population = active_site_population
        if type(parent_depletion_population) is not bool or (parent_depletion_population and (not rate_population)):
            raise ValueError('parent_depletion_population_requires_rate_population')
        self.parent_depletion_population = parent_depletion_population
        if type(stoichiometric_balance_population) is not bool or (stoichiometric_balance_population and (not rate_population)):
            raise ValueError('stoichiometric_balance_population_requires_rate_population')
        self.stoichiometric_balance_population = stoichiometric_balance_population
        if type(product_partition_population) is not bool:
            raise ValueError('boolean_product_partition_population_binding_required')
        if product_partition_population and (not rate_population):
            raise ValueError('product_partition_population_requires_rate_population')
        self.product_partition_population = product_partition_population
        if type(ratio_source_population) is not bool:
            raise ValueError('boolean_ratio_source_population_binding_required')
        if ratio_source_population and (not rate_population):
            raise ValueError('ratio_source_population_requires_rate_population')
        if ratio_source_evidence_origin not in ('reported_source', 'synthetic_fixture') or (not ratio_source_population and ratio_source_evidence_origin != 'reported_source'):
            raise ValueError('invalid_ratio_source_evidence_origin_binding')
        self.ratio_source_population = ratio_source_population
        self.ratio_source_evidence_origin = ratio_source_evidence_origin
        if type(controlled_response_population) is not bool:
            raise ValueError('boolean_controlled_response_population_binding_required')
        if controlled_response_population and (not rate_population):
            raise ValueError('controlled_response_population_requires_rate_population')
        if not controlled_response_population and controlled_response_descriptor is not None:
            raise ValueError('controlled_response_descriptor_requires_population')
        self.controlled_response_population = controlled_response_population
        if controlled_response_evidence_origin not in ('reported_source', 'synthetic_fixture') or (not controlled_response_population and controlled_response_evidence_origin != 'reported_source'):
            raise ValueError('invalid_controlled_response_evidence_origin_binding')
        self.controlled_response_evidence_origin = controlled_response_evidence_origin
        self._controlled_response_descriptor = None
        if controlled_response_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import implementation_descriptor
            current = implementation_descriptor(evidence_origin=controlled_response_evidence_origin)
            if controlled_response_descriptor is not None and controlled_response_descriptor != current:
                raise ValueError('controlled_response_implementation_binding_mismatch')
            self._controlled_response_descriptor = deepcopy(current)
        if type(gel_population) is not bool:
            raise ValueError('boolean_gel_population_binding_required')
        if gel_population and (not rate_population):
            raise ValueError('gel_population_requires_rate_population')
        if not gel_population and gel_descriptor is not None:
            raise ValueError('gel_descriptor_requires_population')
        self.gel_population = gel_population
        if gel_evidence_origin not in ('reported_source', 'synthetic_fixture') or (not gel_population and gel_evidence_origin != 'reported_source'):
            raise ValueError('invalid_gel_evidence_origin_binding')
        self.gel_evidence_origin = gel_evidence_origin
        self._gel_descriptor = None
        if gel_population:
            from gene_annotation_episode.episodic_workflow.root.a105.library.literature_gel_storage import implementation_descriptor
            current = implementation_descriptor(evidence_origin=gel_evidence_origin)
            if gel_descriptor is not None and gel_descriptor != current:
                raise ValueError('gel_implementation_binding_mismatch')
            self._gel_descriptor = deepcopy(current)
        from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile is not None and (contract_information_profile != CONTRACT_INFORMATION_PROFILE or not rate_population):
            raise ValueError('unsupported_literature_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        if reference_parent_sources is not None:
            if not rate_population or not isinstance(reference_parent_sources, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in reference_parent_sources)) or (len(set(reference_parent_sources)) != len(reference_parent_sources)):
                raise ValueError('explicit_unique_reference_parent_sources_required')
            reference_parent_sources = tuple(reference_parent_sources)
        self.reference_parent_sources = reference_parent_sources

    @classmethod
    def reference_evidence(cls, services, *, source_refs, contract_information_profile=CONTRACT_INFORMATION_PROFILE, **configuration):
        """Construct a fresh caller-assigned reference-source investigation.

        This explicit entry point defaults to existing on-demand contract
        information. The caller supplies its protocol, model and controller;
        no source is read or scientific action selected here. Explicit None
        retains the existing expanded presentation. The ordinary constructor
        and saved-descriptor reconstruction keep their original defaults.
        """
        configuration.setdefault('rate_population', True)
        return cls(services, reference_parent_sources=source_refs, contract_information_profile=contract_information_profile, **configuration)
