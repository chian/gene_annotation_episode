"""The A106 literature sheet repositories of one literature episode, over the run's store.

Each repository is built lazily
over the custody-scoped ``store`` of the running unit; construction and
discovery create no state. ``populate`` executes one selected A106 population
tool against the repository that owns it.

Which optional populations a binding offers is its own explicit configuration
(``populations``); the evidence origin of the ratio-source, controlled-response
and gel populations is declared with them. Nothing is defaulted.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError

_LIBRARY = 'gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence'
OPTIONAL_POPULATIONS = ('ratio_source', 'controlled_response', 'gel', 'completion_time', 'product_partition',
                        'active_site', 'parent_depletion', 'stoichiometric_balance', 'compiled_assay', 'channel',
                        'ion_discrimination')
_ORIGIN_POPULATIONS = ('ratio_source', 'controlled_response', 'gel')
_EVIDENCE_ORIGINS = ('reported_source', 'synthetic_fixture')
_SOURCE_REPOSITORIES = {
    'amount': 'LiteratureAmountRepository', 'assay': 'LiteratureAssayRepository',
    'binding_interaction': 'LiteratureBindingInteractionRepository', 'binding_model': 'LiteratureBindingModelRepository',
    'binding': 'LiteratureBindingRepository', 'calibration_recovery': 'LiteratureCalibrationRecoveryRepository',
    'controlled_response': 'LiteratureControlledResponseRepository', 'figure': 'LiteratureFigureRepository',
    'gel': 'LiteratureGelRepository', 'kinetic': 'LiteratureKineticRepository', 'optical': 'LiteratureOpticalRepository',
    'perturbation': 'LiteraturePerturbationRepository', 'quantity': 'LiteratureQuantityRepository',
    'rate_observation': 'LiteratureRateObservationRepository', 'rate_replicate': 'LiteratureRateReplicateRepository',
    'rate': 'LiteratureRateRepository', 'ratio': 'LiteratureRatioRepository',
    'ratio_source': 'LiteratureRatioSourceRepository', 'transport': 'LiteratureTransportRepository',
}
# Own-module repositories: name -> (module, class).
_OWN = {
    'endpoint_signal': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'),
    'concentration_window': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository'),
    'measurement_comparison': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository'),
    'summary_precision': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_kinetic_summary_precision_storage', 'LiteratureKineticSummaryPrecisionRepository'),
    'compiled_assay': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_compiled_assay_storage', 'LiteratureCompiledAssayRepository'),
    'product_coupling': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_product_coupling_storage', 'LiteratureProductCouplingRepository'),
    'measurement_validation': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_measurement_validation_storage', 'LiteratureMeasurementValidationRepository'),
    'ion_discrimination': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_ion_discrimination_storage', 'LiteratureIonDiscriminationRepository'),
    'channel': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_channel_storage', 'LiteratureChannelRepository'),
    'completion_time': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_completion_time_storage', 'LiteratureCompletionTimeRepository'),
    'active_site': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_active_site_storage', 'LiteratureActiveSiteRepository'),
    'perturbation_operand': ('gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_perturbation_operands', 'LiteraturePerturbationOperandProjection'),
    'parent_depletion': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_parent_depletion_storage', 'LiteratureParentDepletionRepository'),
    'stoichiometric_balance': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_stoichiometric_balance_storage', 'LiteratureStoichiometricBalanceRepository'),
    'product_partition': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_product_partition_storage', 'LiteratureProductPartitionRepository'),
    'binding_interaction_model': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_binding_interaction_model_storage',
                                  'LiteratureBindingInteractionModelRepository'),
    'kinetic_model': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_kinetic_model_storage', 'LiteratureKineticModelRepository'),
    'a106_subscore': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_subscore_storage', 'LiteratureA106SubscoreRepository'),
}
# Population tool -> the repository that owns it (``('source', name)`` or ``('own', name)``).
POPULATION_OWNERS = {
    'literature.concentration_window.populate': ('own', 'concentration_window'),
    'literature.measurement_comparison.populate': ('own', 'measurement_comparison'),
    'literature.product_coupling.populate': ('own', 'product_coupling'),
    'literature.measurement_validation.populate': ('own', 'measurement_validation'),
    'literature.ion_discrimination.populate': ('own', 'ion_discrimination'),
    'literature.channel.populate': ('own', 'channel'),
    'literature.assay.components.populate': ('own', 'compiled_assay'),
    'literature.rate.populate': ('source', 'rate'),
    'literature.calibration.recovery.populate': ('source', 'calibration_recovery'),
    'literature.rate.observations.populate': ('source', 'rate_observation'),
    'literature.rate.replicates.populate': ('source', 'rate_replicate'),
    'literature.rate.source.populate': ('source', 'rate'),
    'literature.quantity.populate': ('source', 'quantity'),
    'literature.assay.populate': ('source', 'assay'),
    'literature.amount.populate': ('source', 'amount'),
    'literature.completion_time.populate': ('own', 'completion_time'),
    'literature.active_site.populate': ('own', 'active_site'),
    'literature.parent_depletion.populate': ('own', 'parent_depletion'),
    'literature.stoichiometric_balance.populate': ('own', 'stoichiometric_balance'),
    'literature.intervention_grading.populate': ('own', 'intervention_grading'),
    'literature.a106.finalize': ('own', 'a106_subscore'),
    'literature.product_partition.populate': ('own', 'product_partition'),
    'literature.optical.populate': ('source', 'optical'),
    'literature.kinetic.populate': ('source', 'kinetic'),
    'literature.kinetic.model.populate': ('own', 'kinetic_model'),
    'literature.binding.interaction.populate': ('source', 'binding_interaction'),
    'literature.binding.interaction.model.populate': ('own', 'binding_interaction_model'),
    'literature.ratio.populate': ('source', 'ratio'),
    'literature.ratio.source.populate': ('source', 'ratio_source'),
    'literature.controlled_response.source_v3.populate': ('source', 'controlled_response'),
    'literature.gel.populate': ('source', 'gel'),
    'literature.binding.populate': ('source', 'binding'),
    'literature.binding.model.populate': ('source', 'binding_model'),
    'literature.transport.response.populate': ('source', 'transport'),
    'literature.perturbation.populate': ('source', 'perturbation'),
    'literature.figure.populate': ('source', 'figure'),
}
_CATALOG_ORDER = tuple(POPULATION_OWNERS)


@dataclass(frozen=True)
class LiteratureContext:
    """What the A106 sheet repositories read of the Episode whose unit runs: the run and Episode identity (the
    system's), its role and path, the assigned scope, the commission and the records it holds (custody: what the
    old Store called received)."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    request: dict
    received_record_refs: tuple


def validate_populations(populations, evidence_origins):
    """The binding's explicit optional populations and the evidence origin each origin-bearing one declares."""
    if not isinstance(populations, (list, tuple)) or any(name not in OPTIONAL_POPULATIONS for name in populations) \
            or len(set(populations)) != len(populations):
        raise ContractError('a106_literature_populations_must_be_unique_known_names')
    if not isinstance(evidence_origins, Mapping) or set(evidence_origins) != {
            name for name in populations if name in _ORIGIN_POPULATIONS}:
        raise ContractError('a106_literature_evidence_origin_required_for_each_origin_population')
    if any(origin not in _EVIDENCE_ORIGINS for origin in evidence_origins.values()):
        raise ContractError('a106_literature_evidence_origin_invalid')
    return tuple(populations), dict(evidence_origins)


def population_catalog(populations):
    """The A106 source, perturbation and intervention population operations this binding offers."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_population_catalog import intervention_entries, perturbation_entry
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_source_population_catalog import population_catalog as source_catalog
    result = source_catalog(**{name + '_population': name in populations for name in OPTIONAL_POPULATIONS})
    result.append(perturbation_entry())
    result.extend(intervention_entries())
    positions = {name: index for index, name in enumerate(_CATALOG_ORDER)}
    unknown = [entry['name'] for entry in result if entry['name'] not in positions]
    if unknown:
        raise ContractError('a106_literature_population_owner_unbound:' + ','.join(unknown))
    result.sort(key=lambda entry: positions[entry['name']])
    return result


class LiteratureRepositories:
    """The A106 sheet repositories of one literature episode."""

    def __init__(self, store, run_id, populations, evidence_origins):
        self.store, self.run_id = store, run_id
        self.populations = tuple(populations)
        self.evidence_origins = dict(evidence_origins)
        self._built = {}

    def _descriptor(self, name):
        module = import_module(_LIBRARY + '.literature_' + name + '_storage')
        return module.implementation_descriptor(evidence_origin=self.evidence_origins[name])

    def source(self, name):
        """One of A106's source repositories (``literature_<name>_storage``)."""
        options = {}
        if name == 'ratio_source':
            options = {'evidence_origin': self.evidence_origins['ratio_source']}
        elif name in ('controlled_response', 'gel'):
            options = {'expected_descriptor': self._descriptor(name), 'evidence_origin': self.evidence_origins[name]}
        if name in ('ratio_source', 'controlled_response', 'gel') and name not in self.populations:
            raise ContractError('a106_literature_population_not_offered:' + name)
        key = ('source', name, json.dumps(options, sort_keys=True, allow_nan=False))
        if key not in self._built:
            module = import_module(_LIBRARY + '.literature_' + name + '_storage')
            self._built[key] = getattr(module, _SOURCE_REPOSITORIES[name])(self.store, self.run_id, **options)
        return self._built[key]

    def own(self, name):
        """One of A106's own-module repositories, or the intervention grading repository."""
        key = ('own', name)
        if key not in self._built:
            if name == 'intervention_grading':
                from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage import LiteratureInterventionRepository
                self._built[key] = LiteratureInterventionRepository(self.store, self.run_id,
                                                                    read_cells=self.intervention_source_cells)
            else:
                module, cls = _OWN[name]
                self._built[key] = getattr(import_module(module), cls)(self.store, self.run_id)
        return self._built[key]

    def owner(self, tool_name, arguments):
        """The repository that executes ``tool_name`` with these arguments."""
        if tool_name == 'literature.figure.populate' and arguments.get('version') == \
                'literature_figure_endpoint_signal_population_v1':
            return self.own('endpoint_signal')
        if tool_name == 'literature.kinetic.populate' and arguments.get('version') == \
                'literature_kinetic_summary_precision_population_v1':
            return self.own('summary_precision')
        kind, name = POPULATION_OWNERS[tool_name]
        return self.source(name) if kind == 'source' else self.own(name)

    def populate(self, context, tool_name, arguments, operation_key):
        repository = self.owner(tool_name, arguments)
        if tool_name == 'literature.controlled_response.source_v3.populate':
            return repository.populate_v3(context, arguments, operation_key)
        if tool_name == 'literature.rate.source.populate':
            return repository.populate_native(context, arguments, operation_key)
        return repository.populate(context, arguments, operation_key)

    def population_routes(self):
        """Each saved sheet namespace a grading reader may read: (namespace, repository)."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_subscore_storage as subscore
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_concentration_window_storage as window
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_endpoint_signal_storage as endpoint
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_intervention_storage as intervention
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_kinetic_summary_precision_storage as summary
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_measurement_comparison_storage as comparison
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_measurement_validation_storage as validation
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence import literature_perturbation_operands as operands
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_product_coupling_storage as coupling
        routes = [(window.NAMESPACE, lambda: self.own('concentration_window')),
                  (comparison.NAMESPACE, lambda: self.own('measurement_comparison')),
                  (summary.NAMESPACE, lambda: self.own('summary_precision')),
                  (endpoint.NAMESPACE, lambda: self.own('endpoint_signal')),
                  (coupling.NAMESPACE, lambda: self.own('product_coupling')),
                  (validation.NAMESPACE, lambda: self.own('measurement_validation')),
                  (operands.NAMESPACE, lambda: self.own('perturbation_operand')),
                  (intervention.NAMESPACE, lambda: self.own('intervention_grading')),
                  (subscore.NAMESPACE, lambda: self.own('a106_subscore'))]
        for name in ('ion_discrimination', 'channel', 'parent_depletion', 'stoichiometric_balance'):
            if name in self.populations:
                module = import_module(_OWN[name][0])
                routes.append((module.NAMESPACE, lambda name=name: self.own(name)))
        if 'compiled_assay' in self.populations:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence import literature_compiled_assay_storage as compiled
            routes += [(compiled.NAMESPACE, lambda: self.own('compiled_assay')),
                       (compiled.NAMESPACE_V2, lambda: self.own('compiled_assay').v2_projection()),
                       (compiled.NAMESPACE_V3, lambda: self.own('compiled_assay').v3_projection())]
        for name in ('product_partition', 'completion_time', 'active_site'):
            if name in self.populations:
                routes.append((import_module(_OWN[name][0]).NAMESPACE,
                               lambda name=name: self.own(name)))
        if 'ratio_source' in self.populations:
            routes.append(('literature_ratio_source_cells', lambda: self.source('ratio_source')))
        if 'controlled_response' in self.populations:
            routes.append(('literature_controlled_response_component_cells', lambda: self.source('controlled_response')))
        if 'gel' in self.populations:
            routes.append(('literature_gel_component_cells', lambda: self.source('gel')))
        return routes

    def intervention_source_cells(self, context, namespace, sheet_ref, components):
        """The saved cells the intervention grader reads for one sheet of one namespace."""
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import FACT_SOURCE
        if namespace == FACT_SOURCE:
            return self.application_outcome_cells(context, sheet_ref, components)
        for name, repository in self.population_routes():
            if name == namespace:
                return repository().fact_cells(context, [sheet_ref], components=components)
        raise ContractError('assay_grading_reader_namespace_unbound')

    def application_outcome_cells(self, context, publication_ref, fields):
        """The ``bvbrc_application_outcomes`` rows of the requested fields of one received AppService publication.

        The publication is the ``bvbrc_appservice_acquired_bundle_v1`` record an A106 results episode published on
        the shared Store and this episode received; its original selection is projected from the saved adapter
        sheet and components it binds (``project_application_facts``).
        """
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import FACT_SOURCE, project_application_facts
        from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.perturbation_evidence.appservice_publication import read_adapter_contents, read_publication
        body = read_publication(self.store, publication_ref)
        sheet, components = read_adapter_contents(self.store, body)
        rows = project_application_facts(body, sheet=sheet, components=components)[FACT_SOURCE]
        return [row for row in rows if row['field'] in fields]


__all__ = ['LiteratureContext', 'LiteratureRepositories', 'OPTIONAL_POPULATIONS', 'POPULATION_OWNERS',
           'population_catalog', 'validate_populations']
