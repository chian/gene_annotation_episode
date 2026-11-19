"""The A105 source-sheet population operations of one literature episode.

Each population tool saves one source subscoring/measurement sheet through its
own repository in the run's shared store. The rate-family sheets are always
offered; the optional families are the binding's explicit declaration
(``populations``). Purpose-specific grading (``literature.assay_grading.populate``)
and the main A105 sheet (``literature.a105.aggregate``) are always offered: A105
interpretation of applicable evidence requires them (AGENTS.md).

The assay grader reads the cells of the source sheets it grades through
``source_cells`` (by the sheet's cell namespace).
"""
from __future__ import annotations

from importlib import import_module
from types import MappingProxyType

from gene_annotation_episode.domain import ContractError

_LIBRARY = 'gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.'
# The optional population families a binding declares (each needs an explicit boolean).
OPTIONAL = ('ratio_source', 'controlled_response', 'gel', 'completion_time', 'product_partition', 'active_site',
            'parent_depletion', 'stoichiometric_balance', 'compiled_assay', 'channel', 'ion_discrimination')
EVIDENCE_ORIGIN = 'reported_source'
# Repositories by key: (module, class).
_REPOSITORIES = MappingProxyType({
    'rate': ('literature_rate_storage', 'LiteratureRateRepository'),
    'calibration_recovery': ('literature_calibration_recovery_storage', 'LiteratureCalibrationRecoveryRepository'),
    'rate_observation': ('literature_rate_observation_storage', 'LiteratureRateObservationRepository'),
    'rate_replicate': ('literature_rate_replicate_storage', 'LiteratureRateReplicateRepository'),
    'quantity': ('literature_quantity_storage', 'LiteratureQuantityRepository'),
    'assay': ('literature_assay_storage', 'LiteratureAssayRepository'),
    'amount': ('literature_amount_storage', 'LiteratureAmountRepository'),
    'optical': ('literature_optical_storage', 'LiteratureOpticalRepository'),
    'kinetic': ('literature_kinetic_storage', 'LiteratureKineticRepository'),
    'binding_interaction': ('literature_binding_interaction_storage', 'LiteratureBindingInteractionRepository'),
    'ratio': ('literature_ratio_storage', 'LiteratureRatioRepository'),
    'binding': ('literature_binding_storage', 'LiteratureBindingRepository'),
    'binding_model': ('literature_binding_model_storage', 'LiteratureBindingModelRepository'),
    'transport': ('literature_transport_storage', 'LiteratureTransportRepository'),
    'figure': ('literature_figure_storage', 'LiteratureFigureRepository'),
    'endpoint_signal': ('literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository'),
    'concentration_window': ('literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository'),
    'measurement_comparison': ('literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository'),
    'summary_precision': ('literature_kinetic_summary_precision_storage', 'LiteratureKineticSummaryPrecisionRepository'),
    'compiled_assay': ('literature_compiled_assay_storage', 'LiteratureCompiledAssayRepository'),
    'product_coupling': ('literature_product_coupling_storage', 'LiteratureProductCouplingRepository'),
    'measurement_validation': ('literature_measurement_validation_storage',
                               'LiteratureMeasurementValidationRepository'),
    'ion_discrimination': ('literature_ion_discrimination_storage', 'LiteratureIonDiscriminationRepository'),
    'channel': ('literature_channel_storage', 'LiteratureChannelRepository'),
    'completion_time': ('literature_completion_time_storage', 'LiteratureCompletionTimeRepository'),
    'active_site': ('literature_active_site_storage', 'LiteratureActiveSiteRepository'),
    'parent_depletion': ('literature_parent_depletion_storage', 'LiteratureParentDepletionRepository'),
    'stoichiometric_balance': ('literature_stoichiometric_balance_storage',
                               'LiteratureStoichiometricBalanceRepository'),
    'product_partition': ('literature_product_partition_storage', 'LiteratureProductPartitionRepository'),
    'kinetic_model': ('literature_kinetic_model_storage', 'LiteratureKineticModelRepository'),
    'binding_interaction_model': ('literature_binding_interaction_model_storage',
                                  'LiteratureBindingInteractionModelRepository'),
})
# Population tool -> repository key.
TOOLS = MappingProxyType({
    'literature.concentration_window.populate': 'concentration_window',
    'literature.measurement_comparison.populate': 'measurement_comparison',
    'literature.product_coupling.populate': 'product_coupling',
    'literature.measurement_validation.populate': 'measurement_validation',
    'literature.ion_discrimination.populate': 'ion_discrimination',
    'literature.channel.populate': 'channel',
    'literature.assay.components.populate': 'compiled_assay',
    'literature.rate.populate': 'rate',
    'literature.calibration.recovery.populate': 'calibration_recovery',
    'literature.rate.observations.populate': 'rate_observation',
    'literature.rate.replicates.populate': 'rate_replicate',
    'literature.rate.source.populate': 'rate',
    'literature.quantity.populate': 'quantity',
    'literature.assay.populate': 'assay',
    'literature.amount.populate': 'amount',
    'literature.completion_time.populate': 'completion_time',
    'literature.active_site.populate': 'active_site',
    'literature.parent_depletion.populate': 'parent_depletion',
    'literature.stoichiometric_balance.populate': 'stoichiometric_balance',
    'literature.assay_grading.populate': 'grading',
    'literature.a105.aggregate': 'aggregation',
    'literature.product_partition.populate': 'product_partition',
    'literature.optical.populate': 'optical',
    'literature.kinetic.populate': 'kinetic',
    'literature.kinetic.model.populate': 'kinetic_model',
    'literature.binding.interaction.populate': 'binding_interaction',
    'literature.binding.interaction.model.populate': 'binding_interaction_model',
    'literature.ratio.populate': 'ratio',
    'literature.ratio.source.populate': 'ratio_source',
    'literature.controlled_response.source_v3.populate': 'controlled_response',
    'literature.gel.populate': 'gel',
    'literature.binding.populate': 'binding',
    'literature.binding.model.populate': 'binding_model',
    'literature.transport.response.populate': 'transport',
    'literature.figure.populate': 'figure',
})
# The established catalog order of the population tools.
CATALOG_ORDER = tuple(TOOLS)
# Source keys that name a sheet or source in population arguments (checked against an assigned page).
_SHEET_SOURCE_TOOLS = frozenset({'literature.assay_grading.populate', 'literature.a105.aggregate',
                                 'literature.measurement_validation.populate', 'literature.assay.components.populate',
                                 'literature.ion_discrimination.populate'})
_SOURCE_KEYS = frozenset({'source_ref', 'covariance_source_ref', 'activity_covariance_source_ref', 'model_source_ref',
                          'km_sheet_ref', 'data_source_ref', 'coordinate_source_ref', 'validation_source_ref'})
# Repositories that authorize every source read and record read of this episode.
ACCESS_AUTHORITIES = ('endpoint_signal', 'summary_precision', 'measurement_comparison', 'concentration_window')


def validate_populations(populations):
    """The binding's explicit optional population declaration."""
    if not isinstance(populations, dict) or set(populations) != set(OPTIONAL) or any(
            type(value) is not bool for value in populations.values()):
        raise ContractError('a105_literature_populations_must_declare_each_family:' + ','.join(OPTIONAL))
    return dict(populations)


def population_sources(tool_name, arguments):
    """Every source or sheet reference a population's arguments read."""
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'metadata_source_ref' and isinstance(child, str):
                    yield child
                elif ((key == 'sheet_ref' and tool_name in _SHEET_SOURCE_TOOLS)
                      or (key == 'original_source_ref' and tool_name == 'literature.binding.interaction.populate')
                      or key in _SOURCE_KEYS) and isinstance(child, str):
                    yield child
                elif key == 'covariance_source_refs' and tool_name == 'literature.measurement_comparison.populate':
                    yield from child
                else:
                    yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, str) and (value in arguments.get('visual_source_refs', ())
                                         or value in arguments.get('covariance_source_refs', ())):
            yield value
    return set(walk(arguments))


class LiteraturePopulations:
    """The repositories and population tools of one A105 literature episode over the shared store."""

    def __init__(self, store, populations):
        self.store = store
        self.enabled = validate_populations(populations)
        self._repositories = {}

    # -- repositories ------------------------------------------------------------------------------------------------
    def repository(self, key):
        if key in self._repositories:
            return self._repositories[key]
        if key == 'grading':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository
            repository = LiteratureAssayGradingRepository(self.store, read_cells=self.source_cells)
        elif key == 'aggregation':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import LiteratureA105AggregationRepository
            grading = self.repository('grading')
            repository = LiteratureA105AggregationRepository(
                self.store,
                read_cells=lambda context, sheet_ref, components: grading.fact_cells(context, [sheet_ref],
                                                                                    components=components))
        elif key == 'ratio_source':
            self._require(key)
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_ratio_source_storage import LiteratureRatioSourceRepository
            repository = LiteratureRatioSourceRepository(self.store, evidence_origin=EVIDENCE_ORIGIN)
        elif key == 'controlled_response':
            self._require(key)
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_controlled_response_storage import (LiteratureControlledResponseRepository,
                                                                           implementation_descriptor)
            repository = LiteratureControlledResponseRepository(
                self.store, evidence_origin=EVIDENCE_ORIGIN,
                expected_descriptor=implementation_descriptor(evidence_origin=EVIDENCE_ORIGIN))
        elif key == 'gel':
            self._require(key)
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_gel_storage import LiteratureGelRepository, implementation_descriptor
            repository = LiteratureGelRepository(
                self.store, evidence_origin=EVIDENCE_ORIGIN,
                expected_descriptor=implementation_descriptor(evidence_origin=EVIDENCE_ORIGIN))
        else:
            if key in OPTIONAL:
                self._require(key)
            module, name = _REPOSITORIES[key]
            repository = getattr(import_module(_LIBRARY + module), name)(self.store)
        self._repositories[key] = repository
        return repository

    def _require(self, family):
        if not self.enabled[family]:
            raise ContractError('a105_literature_population_not_declared:' + family)

    def tool_repository(self, tool_name, arguments):
        """The repository a population tool writes (two tools select a version-specific sheet)."""
        if tool_name == 'literature.figure.populate' and arguments.get('version') == \
                'literature_figure_endpoint_signal_population_v1':
            return self.repository('endpoint_signal')
        if tool_name == 'literature.kinetic.populate' and arguments.get('version') == \
                'literature_kinetic_summary_precision_population_v1':
            return self.repository('summary_precision')
        return self.repository(TOOLS[tool_name])

    @staticmethod
    def populate(context, tool_name, repository, arguments, operation_key):
        if tool_name == 'literature.controlled_response.source_v3.populate':
            return repository.populate_v3(context, arguments, operation_key)
        if tool_name == 'literature.rate.source.populate':
            return repository.populate_native(context, arguments, operation_key)
        return repository.populate(context, arguments, operation_key)

    # -- catalog -----------------------------------------------------------------------------------------------------
    def catalog(self):
        """The population tools this binding offers, in their established order."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_population_catalog import population_catalog
        entries = population_catalog(assay_grading_population=True,
                                     **{name + '_population': value for name, value in self.enabled.items()})
        positions = {name: index for index, name in enumerate(CATALOG_ORDER)}
        return sorted(entries, key=lambda entry: positions[entry['name']])

    # -- the grader's source-sheet reader -----------------------------------------------------------------------------
    def routes(self):
        """(cell namespace, repository reader) of every source sheet the assay grader may read."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_rate_meaning_delivery import source_meaning_projection
        repo = self.repository

        def namespace(module, name='NAMESPACE'):
            return getattr(import_module(_LIBRARY + module), name)
        routes = [
            (namespace('literature_concentration_window_storage'), lambda: repo('concentration_window')),
            (namespace('literature_measurement_comparison_storage'), lambda: repo('measurement_comparison')),
            (namespace('literature_kinetic_summary_precision_storage'), lambda: repo('summary_precision')),
            (namespace('literature_endpoint_signal_storage'), lambda: repo('endpoint_signal')),
            (namespace('literature_product_coupling_storage'), lambda: repo('product_coupling')),
            (namespace('literature_measurement_validation_storage'), lambda: repo('measurement_validation')),
            ('literature_calibration_recovery_cells', lambda: repo('calibration_recovery')),
            ('literature_rate_observation_cells', lambda: repo('rate_observation')),
            ('literature_rate_grid_cells', lambda: repo('rate_observation').grid_projection()),
            ('literature_rate_replicate_cells', lambda: repo('rate_replicate')),
            ('literature_rate_cells', lambda: repo('rate')),
            ('literature_rate_source_cells', lambda: repo('rate').source_projection()),
            ('literature_rate_source_domain_cells', lambda: repo('rate').source_domain_projection()),
            ('literature_rate_source_meaning_cells', lambda: source_meaning_projection(repo('rate'))),
            ('literature_quantity_cells', lambda: repo('quantity')),
            ('literature_assay_cells', lambda: repo('assay')),
            ('literature_ratio_cells', lambda: repo('ratio')),
            ('literature_binding_cells', lambda: repo('binding')),
            ('literature_binding_model_cells', lambda: repo('binding_model')),
            ('literature_transport_cells', lambda: repo('transport')),
            ('literature_figure_cells', lambda: repo('figure')),
            ('literature_amount_cells', lambda: repo('amount')),
            ('literature_optical_cells', lambda: repo('optical')),
            ('literature_kinetic_cells', lambda: repo('kinetic')),
            ('literature_kinetic_model_cells', lambda: repo('kinetic_model')),
            ('literature_binding_interaction_cells', lambda: repo('binding_interaction')),
            ('literature_binding_interaction_model_cells', lambda: repo('binding_interaction_model')),
        ]
        optional = {
            'ion_discrimination': [(namespace('literature_ion_discrimination_storage'),
                                    lambda: repo('ion_discrimination'))],
            'channel': [(namespace('literature_channel_storage'), lambda: repo('channel'))],
            'compiled_assay': [(namespace('literature_compiled_assay_storage'), lambda: repo('compiled_assay')),
                               (namespace('literature_compiled_assay_storage', 'NAMESPACE_V2'),
                                lambda: repo('compiled_assay').v2_projection()),
                               (namespace('literature_compiled_assay_storage', 'NAMESPACE_V3'),
                                lambda: repo('compiled_assay').v3_projection())],
            'product_partition': [(namespace('literature_product_partition_storage'),
                                   lambda: repo('product_partition'))],
            'completion_time': [(namespace('literature_completion_time_storage'), lambda: repo('completion_time'))],
            'active_site': [(namespace('literature_active_site_storage'), lambda: repo('active_site'))],
            'parent_depletion': [(namespace('literature_parent_depletion_storage'), lambda: repo('parent_depletion'))],
            'stoichiometric_balance': [(namespace('literature_stoichiometric_balance_storage'),
                                        lambda: repo('stoichiometric_balance'))],
            'ratio_source': [('literature_ratio_source_cells', lambda: repo('ratio_source'))],
            'controlled_response': [('literature_controlled_response_component_cells',
                                     lambda: repo('controlled_response'))],
            'gel': [('literature_gel_component_cells', lambda: repo('gel'))],
        }
        for family, entries in optional.items():
            if self.enabled[family]:
                routes.extend(entries)
        return routes

    def source_cells(self, context, namespace, sheet_ref, components):
        """The cells of one source sheet the assay grader grades, read through its own repository."""
        for name, reader in self.routes():
            if name == namespace:
                return reader().fact_cells(context, [sheet_ref], components=components)
        raise ContractError('assay_grading_reader_namespace_unbound:' + str(namespace))


__all__ = ['ACCESS_AUTHORITIES', 'CATALOG_ORDER', 'EVIDENCE_ORIGIN', 'LiteraturePopulations', 'OPTIONAL', 'TOOLS',
           'population_sources', 'validate_populations']
