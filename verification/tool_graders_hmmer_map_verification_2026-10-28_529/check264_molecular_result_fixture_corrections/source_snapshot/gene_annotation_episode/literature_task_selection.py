"""Select full literature TASK inserts from actual requested or received work.

Pure instructional selection only: no source access, sheet loading, scientific
calculation, action selection or observations. Capability catalogues and legacy
work booleans are deliberately not evidence that a method was selected.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json

from .literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from .literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from .literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from .literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK
from .literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
from .literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK
from .literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
from .literature_compiled_assay_prompt import COMPILED_ASSAY_TASK
from .literature_compiled_assay_prompt import COMMON_ASSESSMENT_TASK
from .literature_rate_observation_prompt import RATE_OBSERVATION_TASK
from .literature_rate_observation_prompt import REPORTED_CURVE_TASK
from .literature_rate_replicate_prompt import RATE_REPLICATE_TASK
from .literature_assay_prompt import ASSAY_TASK
from .literature_binding_prompt import BINDING_TASK
from .literature_binding_prompt import BINDING_MODEL_TASK
from .literature_binding_interaction_model_prompt import BINDING_INTERACTION_MODEL_TASK
from .literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from .literature_transport_prompt import TRANSPORT_TASK
from .literature_perturbation_prompt import PERTURBATION_TASK
from .literature_structure_prompt import STRUCTURE_TASK
from .literature_reaction_prompt import REACTION_TASK
from .literature_context_prompt import CONTEXT_TASK
from .literature_figure_prompt import FIGURE_TASK
from .literature_partner_prompt import PARTNER_TASK
from .literature_ratio_source_prompt import SOURCE_RATIO_TASK
from .literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from .literature_gel_prompt import GEL_TASK
from .literature_completion_time_prompt import COMPLETION_TIME_TASK
from .literature_active_site_prompt import ACTIVE_SITE_TASK
from .literature_product_partition_prompt import PRODUCT_PARTITION_TASK
from .literature_parent_depletion_prompt import PARENT_DEPLETION_TASK
from .literature_stoichiometric_balance_prompt import STOICHIOMETRIC_BALANCE_TASK
from .literature_channel_prompt import CHANNEL_TASK
from .literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from .literature_amount_prompt import AMOUNT_TASK
from .literature_rate_observation_prompt import REPORTED_CURVE_SCOPE_TASK
from .literature_assay_grading_prompt import ASSAY_GRADING_TASK
from .literature_a105_aggregation_prompt import A105_AGGREGATION_TASK

A105_ASSAY_SELECTION_TASK = """For A105 experimental evidence, follow this hierarchy: A105 experimental evidence subscore → subscoring grader → subscoring reader. The grader evaluates the applicable assay protocol and uses readers to obtain its required measurements. Reader outputs return through that assessment into the requested A105 fields. Extracting a number alone does not complete the assay assessment.

For biochemical evidence, the four reusable protocol groups are enzyme activity/rate comparisons; reaction progress/endpoint conversion; product distribution/equilibrium; and reaction coupling/stoichiometric balance. Select the applicable group from the protocol, measured quantity, experimental design and intended comparison. One experiment can supply measurements relevant to more than one group; retain their common measurement ownership. A paper, case, protein name or particular protein–substrate example is not a scientific dispatch key. Those identities, preparation details, reagent amounts and conditions are source-bound inputs. Chemical identity, reporter chemistry, calibration and stoichiometry can still determine whether a method applies.

These protocol groups feed the same assessment dimensions: reliability, validity, relevance and attribution. Assess reliability using the signal, uncertainty, sampling design, independent replication and dependence. Assess validity using the measurement method, calibration, operating regime and controls applicable to the protocol. Assess relevance by what the measured endpoint establishes about the functional assertion and its biological conditions. Attribution concerns whether the measured effect is isolated to the assayed molecule; it is distinct from relevance. Retain a separate populated assessment for every analyzed experiment. Across experiment values, the user-defined A105 combination is reliability SUM, validity SUM, relevance MAXIMUM, attribution MAXIMUM and overall SUM. Use the existing literature parent and selected literature.a105.aggregate operation; preserve incomplete results without zero imputation, weighting, normalization or orthogonality adjustment. Keep comparability explicit: identify nuisance differences outside the deliberately tested change and whether an applicable control quantifies their effects. Preserve contradictions and complementary evidence with their actual scope and shared measurements.

Within the selected assessment, choose a reader by the required quantity and the actual supported source representation, layout and fields. Source names and row labels locate operands after this scientific choice; they do not define additional assay types. Alternative text, table and graph readers can populate the same assessment. Shared corrections, unit conversion and statistical calculations support the grader without becoming additional assay types. A restricted workbook adapter or graph reader remains restricted to its implemented layout, chemistry and measurement model; do not assume a general parser exists.

Interpret the recovered measurements using the selected protocol's considerations, and request supported calculations for the parent's numerical A105 fields. Preserve units, correction stages, uncertainty, comparability, applicability, attribution and dependence as those results pass upward. Return useful partial results and distinguish missing source evidence from unavailable readers, calculations or grader-to-sheet bindings. Use the parent's declared typed return and the actual available operations; do not manufacture a score or claim an unavailable assessment is complete."""

NATIVE_KINETIC_TASK = 'Read the selected source-reported kinetic parameter or requested descriptive parameter comparison for the assayed reference molecule. Identify the exact source row or passage, parameter definition, organism, molecule, construct, substrate, preparation, experimental system, endpoint, conditions and normalization. Keep Km, kcat and kcat/KM distinct. A single parameter can answer a magnitude question without a second comparison arm; preserve a missing denominator rather than inventing a reference, zero, affinity or preference contrast. Possible functions can emerge from supplied sequence, selected contents or snippets; an initial candidate annotation or searchable name is not required.\n\nSelect the complete native number, its actual unit and the source-qualified uncertainty and count with their exact meanings. Preserve bounds, approximations and untyped spread; do not borrow units, uncertainty or repetition meaning from a neighboring parameter or assay. When a comparison is requested, establish the actual molecule/construct relationship, separately assayed substrates, parameter definitions, normalization and protocols. A reported-protocol ratio is not automatically common-condition preference, higher Km is not automatically stronger affinity, and missing comparison relationships do not erase a valid individual parameter. Nominate source-supported selectors; deterministic readers and calculators perform parsing, validation, conversion and available arithmetic.\n\nKeep the parameter magnitude, reported SD, physical preparation count and statistical estimator meaning separate. If summary precision for the same report is requested, preserve shared source and measurement ownership without counting its parameter, spread, count or derived precision as independent evidence. Physical preparation count alone does not establish statistical n, central-value mean identity, covariance or total accuracy. A supplemental kinetic log model requires its own actual two-estimate assignment, received sheet and supported uncertainty-model inputs; do not invoke it merely because a native parameter or descriptive contrast is requested. Return exactly the requested numerical components and necessary scientific qualifications, retaining valid partials and distinguishing missing source information from unimplemented functions. No overall category grade, function probability, target-transfer weight or final annotation credit is inferred.'

@dataclass(frozen=True)
class _Family:
    source: str
    task: str
    storage_module: str
    repository_class: str
    requested: str
    operation: str


# These describe existing instructions and selected-operation metadata only.
# They do not register capabilities or expand any numerical return.
_FAMILIES = (
    _Family("literature_assay_grading_cells", ASSAY_GRADING_TASK, "literature_assay_grading_storage", "LiteratureAssayGradingRepository", "requested_assay_grading_components", "literature.assay_grading.populate"),
    _Family("literature_a105_aggregation_cells", A105_AGGREGATION_TASK, "literature_a105_aggregation_storage", "LiteratureA105AggregationRepository", "requested_a105_aggregation_components", "literature.a105.aggregate"),
    _Family("literature_concentration_window_cells", CONCENTRATION_WINDOW_TASK, "literature_concentration_window_storage", "LiteratureConcentrationWindowRepository", "requested_concentration_window_components", "literature.concentration_window.populate"),
    _Family("literature_amount_cells", AMOUNT_TASK, "literature_amount_storage", "LiteratureAmountRepository", "requested_amount_components", "literature.amount.populate"),
    _Family("literature_kinetic_cells", NATIVE_KINETIC_TASK, "literature_kinetic_storage", "LiteratureKineticRepository", "requested_kinetic_components", "literature.kinetic.populate"),
    _Family("literature_kinetic_summary_precision_cells", KINETIC_SUMMARY_PRECISION_TASK, "literature_kinetic_summary_precision_storage", "LiteratureKineticSummaryPrecisionRepository", "requested_kinetic_summary_precision_components", "literature.kinetic.populate"),
    _Family("literature_endpoint_signal_cells", ENDPOINT_SIGNAL_TASK, "literature_endpoint_signal_storage", "LiteratureEndpointSignalRepository", "requested_endpoint_signal_components", "literature.figure.populate"),
    _Family("literature_measurement_comparison_cells", MEASUREMENT_COMPARISON_TASK, "literature_measurement_comparison_storage", "LiteratureMeasurementComparisonRepository", "requested_measurement_comparison_components", "literature.measurement_comparison.populate"),
    _Family("literature_product_coupling_cells", PRODUCT_COUPLING_TASK, "literature_product_coupling_storage", "LiteratureProductCouplingRepository", "requested_product_coupling_components", "literature.product_coupling.populate"),
    _Family("literature_calibration_recovery_cells", CALIBRATION_RECOVERY_TASK, "literature_calibration_recovery_storage", "LiteratureCalibrationRecoveryRepository", "requested_calibration_recovery_components", "literature.calibration.recovery.populate"),
    _Family("literature_measurement_validation_cells", MEASUREMENT_VALIDATION_TASK, "literature_measurement_validation_storage", "LiteratureMeasurementValidationRepository", "requested_measurement_validation_components", "literature.measurement_validation.populate"),
    _Family("literature_compiled_assay_cells", COMPILED_ASSAY_TASK, "literature_compiled_assay_storage", "LiteratureCompiledAssayRepository", "requested_compiled_assay_components", "literature.assay.components.populate"),
    _Family("literature_compiled_assay_v2_cells", COMPILED_ASSAY_TASK, "literature_compiled_assay_storage", "LiteratureCompiledAssayRepository", "requested_compiled_assay_components_v2", "literature.assay.components.populate"),
    _Family("literature_compiled_assay_v3_cells", COMMON_ASSESSMENT_TASK, "literature_compiled_assay_storage", "LiteratureCompiledAssayRepository", "requested_compiled_assay_components_v3", "literature.assay.components.populate"),
    _Family("literature_rate_observation_cells", RATE_OBSERVATION_TASK, "literature_rate_observation_storage", "LiteratureRateObservationRepository", "requested_rate_observation_components", "literature.rate.observations.populate"),
    _Family("literature_rate_grid_cells", REPORTED_CURVE_TASK, "literature_rate_observation_storage", "LiteratureReportedCurveRepository", "requested_rate_grid_components", "literature.rate.observations.populate"),
    _Family("literature_rate_replicate_cells", RATE_REPLICATE_TASK, "literature_rate_replicate_storage", "LiteratureRateReplicateRepository", "requested_rate_replicate_components", "literature.rate.replicates.populate"),
    _Family("literature_assay_cells", ASSAY_TASK, "literature_assay_storage", "LiteratureAssayRepository", "requested_assay_components", "literature.assay.populate"),
    _Family("literature_binding_cells", BINDING_TASK, "literature_binding_storage", "LiteratureBindingRepository", "requested_binding_components", "literature.binding.populate"),
    _Family("literature_binding_model_cells", BINDING_MODEL_TASK, "literature_binding_model_storage", "LiteratureBindingModelRepository", "requested_binding_model_components", "literature.binding.model.populate"),
    _Family("literature_binding_interaction_cells", BINDING_TASK, "literature_binding_interaction_storage", "LiteratureBindingInteractionRepository", "requested_binding_interaction_components", "literature.binding.interaction.populate"),
    _Family("literature_binding_interaction_model_cells", BINDING_INTERACTION_MODEL_TASK, "literature_binding_interaction_model_storage", "LiteratureBindingInteractionModelRepository", "requested_binding_interaction_model_components", "literature.binding.interaction.model.populate"),
    _Family("literature_kinetic_model_cells", KINETIC_MODEL_TASK, "literature_kinetic_model_storage", "LiteratureKineticModelRepository", "requested_kinetic_model_components", "literature.kinetic.model.populate"),
    _Family("literature_transport_cells", TRANSPORT_TASK, "literature_transport_storage", "LiteratureTransportRepository", "requested_transport_components", "literature.transport.response.populate"),
    _Family("literature_perturbation_cells", PERTURBATION_TASK, "literature_perturbation_storage", "LiteraturePerturbationRepository", "requested_perturbation_components", "literature.perturbation.populate"),
    _Family("literature_structure_cells", STRUCTURE_TASK, "literature_structure_storage", "LiteratureStructureRepository", "requested_structure_components", "literature.structure.populate"),
    _Family("literature_reaction_cells", REACTION_TASK, "literature_reaction_storage", "LiteratureReactionRepository", "requested_reaction_components", "literature.reaction.populate"),
    _Family("literature_context_cells", CONTEXT_TASK, "literature_context_storage", "LiteratureContextRepository", "requested_context_components", "literature.context.populate"),
    _Family("literature_figure_cells", FIGURE_TASK, "literature_figure_storage", "LiteratureFigureRepository", "requested_figure_components", "literature.figure.populate"),
    _Family("literature_partner_cells", PARTNER_TASK, "literature_partner_storage", "LiteraturePartnerRepository", "requested_partner_components", "literature.partner.populate"),
    _Family("literature_ratio_source_cells", SOURCE_RATIO_TASK, "literature_ratio_source_storage", "LiteratureRatioSourceRepository", "requested_ratio_source_components", "literature.ratio.source.populate"),
    _Family("literature_controlled_response_component_cells", CONTROLLED_RESPONSE_TASK, "literature_controlled_response_storage", "LiteratureControlledResponseRepository", "requested_controlled_response_components", "literature.controlled_response.source_v3.populate"),
    _Family("literature_gel_component_cells", GEL_TASK, "literature_gel_storage", "LiteratureGelRepository", "requested_gel_components", "literature.gel.populate"),
    _Family("literature_completion_time_cells", COMPLETION_TIME_TASK, "literature_completion_time_storage", "LiteratureCompletionTimeRepository", "requested_completion_time_components", "literature.completion_time.populate"),
    _Family("literature_active_site_cells", ACTIVE_SITE_TASK, "literature_active_site_storage", "LiteratureActiveSiteRepository", "requested_active_site_components", "literature.active_site.populate"),
    _Family("literature_product_partition_cells", PRODUCT_PARTITION_TASK, "literature_product_partition_storage", "LiteratureProductPartitionRepository", "requested_product_partition_components", "literature.product_partition.populate"),
    _Family('literature_parent_depletion_cells',PARENT_DEPLETION_TASK,'literature_parent_depletion_storage','LiteratureParentDepletionRepository','requested_parent_depletion_components','literature.parent_depletion.populate'),
    _Family('literature_stoichiometric_balance_cells',STOICHIOMETRIC_BALANCE_TASK,'literature_stoichiometric_balance_storage','LiteratureStoichiometricBalanceRepository','requested_stoichiometric_balance_components','literature.stoichiometric_balance.populate'),
    _Family("literature_channel_cells", CHANNEL_TASK, "literature_channel_storage", "LiteratureChannelRepository", "requested_channel_components", "literature.channel.populate"),
    _Family("literature_ion_discrimination_cells", ION_DISCRIMINATION_TASK, "literature_ion_discrimination_storage", "LiteratureIonDiscriminationRepository", "requested_ion_discrimination_components", "literature.ion_discrimination.populate"),
)
_BY_SOURCE = {f.source: f for f in _FAMILIES}
_BY_SOURCE.update({alias: _BY_SOURCE[source] for alias, source in {
    'literature_perturbation_summary_cells': 'literature_perturbation_cells',
    'literature_reaction_semantic_cells': 'literature_reaction_cells',
    'literature_reaction_native_observations': 'literature_reaction_cells',
    'literature_context_semantic_cells': 'literature_context_cells',
    'literature_context_native_observations': 'literature_context_cells',
}.items()})
_BY_REQUEST = {f.requested: f.source for f in _FAMILIES}
_BY_REQUEST.update({"requested_perturbation_summary_components": "literature_perturbation_cells",
    "requested_reaction_native_positions": "literature_reaction_cells",
    "requested_context_native_positions": "literature_context_cells",
    "requested_gel_views": "literature_gel_component_cells",
    "requested_controlled_response_views": "literature_controlled_response_component_cells"})

def population_task_metadata_specs():
    """Existing table/provider/version facts; importing classes installs no state."""
    for family in _FAMILIES:
        module = import_module('.' + family.storage_module, __package__)
        repository = getattr(module, family.repository_class)
        if family.source == 'literature_compiled_assay_v2_cells':
            versions = (module.VERSION_V2,)
        elif family.source == 'literature_compiled_assay_v3_cells':
            versions = (module.VERSION_V3,)
        elif family.source == 'literature_rate_grid_cells':
            versions = (module.GRID_RECORD,)
        elif family.source == 'literature_kinetic_cells':
            versions = (module.VERSION, module.LEGACY_VERSION)
        else:
            versions = (getattr(module, 'VERSION', repository.record_version),)
        flag = {'literature_assay_grading_cells': 'assay_grading_population',
            'literature_a105_aggregation_cells': 'assay_grading_population',
            'literature_compiled_assay_cells': 'compiled_assay_population',
            'literature_compiled_assay_v2_cells': 'compiled_assay_population',
            'literature_compiled_assay_v3_cells': 'compiled_assay_population',
            'literature_ratio_source_cells': 'ratio_source_population',
            'literature_controlled_response_component_cells': 'controlled_response_population',
            'literature_gel_component_cells': 'gel_population',
            'literature_completion_time_cells': 'completion_time_population',
            'literature_active_site_cells': 'active_site_population',
            'literature_product_partition_cells': 'product_partition_population',
            'literature_parent_depletion_cells':'parent_depletion_population',
            'literature_stoichiometric_balance_cells':'stoichiometric_balance_population',
            'literature_channel_cells': 'channel_population',
            'literature_ion_discrimination_cells': 'ion_discrimination_population'}.get(family.source, 'rate_population')
        yield (family.source, flag, repository.operations_table, module.PROVIDER, versions)


_SCOPE_SOURCE = {
    'assay_type_experimental_evidence': 'literature_assay_grading_cells',
    'a105_across_experiment_aggregation': 'literature_a105_aggregation_cells',
    'source_concentration_window': 'literature_concentration_window_cells',
    'source_amount_comparison': 'literature_amount_cells',
    'source_measurement_comparison': 'literature_measurement_comparison_cells',
    'source_kinetic_summary_precision': 'literature_kinetic_summary_precision_cells',
    'source_endpoint_signal_contribution': 'literature_endpoint_signal_cells',
    'source_product_coupling': 'literature_product_coupling_cells',
    'source_calibration_recovery': 'literature_calibration_recovery_cells',
    'source_measurement_validation': 'literature_measurement_validation_cells',
    'compiled_source_endpoint': 'literature_compiled_assay_cells',
    'common_assertion_contrast': 'literature_compiled_assay_v3_cells',
    'source_reported_rate_observations': 'literature_rate_observation_cells',
    'source_reported_curve_precision': 'literature_rate_grid_cells',
    'source_raw_rate_replicates': 'literature_rate_replicate_cells',
    'interpreted_source_endpoint': 'literature_assay_cells',
    'interpreted_source_parameter_contrast': 'literature_binding_model_cells',
    'interpreted_source_kinetic_response': 'literature_transport_cells',
    'interpreted_reference_perturbation': 'literature_perturbation_cells',
    'conditional_deposited_model_geometry': 'literature_structure_cells',
    'reported_reference_reaction_constraints': 'literature_reaction_cells',
    'reference_organism_sample_compatibility': 'literature_context_cells',
    'reference_experimental_figure_ordinates': 'literature_figure_cells',
    'reference_experimental_partner_components': 'literature_partner_cells',
    'source_preparation_completion_time': 'literature_completion_time_cells',
    'active_site_titration_amount': 'literature_active_site_cells',
    'reported_selected_product_partition': 'literature_product_partition_cells',
    'finite_parent_compound_removal':'literature_parent_depletion_cells',
    'source_soluble_product_stoichiometric_balance':'literature_stoichiometric_balance_cells',
    'source_electrical_activity': 'literature_channel_cells',
    'source_ion_discrimination': 'literature_ion_discrimination_cells',
}
_ROW_VERSION_SOURCE = {
    'concentration_window_return_v1': 'literature_concentration_window_cells',
    'measurement_comparison_return_v2': 'literature_measurement_comparison_cells',
    'kinetic_summary_precision_return_v1': 'literature_kinetic_summary_precision_cells',
    'endpoint_signal_return_v1': 'literature_endpoint_signal_cells',
    'literature_controlled_response_component_fact_v3': 'literature_controlled_response_component_cells',
    'literature_gel_component_fact_v1': 'literature_gel_component_cells',
}
_MODEL_VIEWS = {'kinetic_log_model_components': 'literature_kinetic_model_cells',
    'binding_interaction_log_model_components': 'literature_binding_interaction_model_cells'}


def _row_source(value):
    # Only actual sheet outputs/admitted rows are candidates, never source IDs,
    # catalogue entries, schemas, ordinary prose or a worksheet-format roster.
    if not isinstance(value.get('sheet_ref'), str) or not any(
            name in value for name in ('component', 'cells')):
        return None
    version = value.get('row_version', value.get('version'))
    required_versions = {'source_concentration_window': 'concentration_window_return_v1', 'source_measurement_comparison': 'measurement_comparison_return_v2',
        'source_kinetic_summary_precision': 'kinetic_summary_precision_return_v1',
        'source_endpoint_signal_contribution': 'endpoint_signal_return_v1'}
    expected_version = required_versions.get(value.get('evaluation_scope'))
    if 'component' in value and expected_version and version != expected_version:
        return None
    source = _ROW_VERSION_SOURCE.get(version)
    if source:
        # Versioned rows must agree with their independently declared scope.
        expected = {'literature_concentration_window_cells': 'source_concentration_window', 'literature_measurement_comparison_cells': 'source_measurement_comparison',
            'literature_kinetic_summary_precision_cells': 'source_kinetic_summary_precision',
            'literature_endpoint_signal_cells': 'source_endpoint_signal_contribution'}.get(source)
        return source if expected is None or value.get('evaluation_scope') == expected else None
    if value.get('view') in _MODEL_VIEWS:
        return _MODEL_VIEWS[value['view']]
    scope = value.get('evaluation_scope', value.get('evaluated_scope'))
    formula = value.get('formula_code', '')
    if scope == 'source_kinetic_parameter_contrast':
        if isinstance(formula, str) and formula.startswith('kinetic_model_'):
            return 'literature_kinetic_model_cells'
        return 'literature_kinetic_cells'
    if scope == 'source_binding_discrimination_interaction':
        return ('literature_binding_interaction_model_cells' if isinstance(formula, str)
            and formula.startswith('binding_interaction_model_') else 'literature_binding_interaction_cells')
    if scope == 'compiled_source_endpoint' and value.get('record_version') == 'literature_compiled_assay_record_v3':
        return None
    if scope in _SCOPE_SOURCE:
        return _SCOPE_SOURCE[scope]
    if (value.get('candidate_basis') == 'selected_received_source_representations'
            and value.get('uncertainty_evaluation') == 'numeric_uncertainty_reader_unimplemented'):
        return 'literature_ratio_source_cells'
    if isinstance(formula, str) and formula.startswith('binding_') and not formula.startswith(('binding_model_', 'binding_interaction_')):
        return 'literature_binding_cells'
    return None


def _selected_operation_sources(tool, arguments=None, *, union=False):
    if union:
        if tool == 'literature.figure.populate':
            return ('literature_figure_cells', 'literature_endpoint_signal_cells')
        return tuple(f.source for f in _FAMILIES if f.operation == tool)
    arguments = arguments if isinstance(arguments, Mapping) else {}
    if tool == 'literature.kinetic.populate':
        version = arguments.get('version')
        return (('literature_kinetic_summary_precision_cells',) if version == 'literature_kinetic_summary_precision_population_v1'
            else ('literature_kinetic_cells',) if version in (None, 'a105_kinetic_source_selection_v1') else ())
    if tool == 'literature.figure.populate':
        version = arguments.get('version')
        return (('literature_endpoint_signal_cells',) if version == 'literature_figure_endpoint_signal_population_v1'
            else ('literature_figure_cells',) if version is None else ())
    if tool == 'literature.assay.components.populate':
        version = arguments.get('population_version')
        return (('literature_compiled_assay_v3_cells',) if version == 'a105_common_assessment_population_v1'
            else ('literature_compiled_assay_v2_cells',) if version == 'a105_compiled_assay_population_v2'
            else ('literature_compiled_assay_cells',) if version is None else ())
    if tool == 'literature.rate.observations.populate':
        version = arguments.get('version')
        return (('literature_rate_grid_cells',) if version == 'a105_reported_curve_population_v1'
            else ('literature_rate_observation_cells',) if version is None else ())
    if tool == 'literature.partner.source.populate':
        return ('literature_partner_cells',)
    return tuple(f.source for f in _FAMILIES if f.operation == tool)


def _form_sources(form):
    if not isinstance(form, Mapping):
        return
    # Fact projections are explicitly chosen top-level fields. Available facts
    # and nested schema alternatives are not selections.
    nodes = form.get('properties', {}).values() if isinstance(form.get('properties'), Mapping) else (form,)
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        if set(node) == {'$ref'} and isinstance(node['$ref'], str) and node['$ref'].startswith('episode-fact:'):
            source = node['$ref'][len('episode-fact:'):]
            if source in _BY_SOURCE:
                yield source
        elif node.get('x-source') in _BY_SOURCE:
            # The host already owns/validates the original closed declaration.
            # Classify its declared row meaning without rebuilding today's
            # factory (which cold reconstruction explicitly must not require).
            item = node.get('items')
            properties = item.get('properties') if isinstance(item, Mapping) else None
            if (node.get('type') == 'array' and isinstance(properties, Mapping)
                    and {'sheet_ref', 'component'} <= properties.keys()
                    and item.get('additionalProperties') is False):
                yield node['x-source']


def _information_sources(value, *, selected_history=False):
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _information_sources(child, selected_history=selected_history)
        return
    if not isinstance(value, Mapping):
        return
    source = _row_source(value)
    if source:
        yield source
        return
    result = value.get('result')
    if isinstance(result, Mapping) and result.get('view') == 'records':
        selected_history = True
    if value.get('status') in ('invalid', 'failed', 'error') and isinstance(value.get('selected_tool'), str):
        tool = value['selected_tool']
        # A concrete single-method attempt is sufficient. An opaque union
        # failure does not identify which version/branch needs repair.
        if tool not in {'literature.kinetic.populate', 'literature.figure.populate',
                'literature.assay.components.populate', 'literature.rate.observations.populate'}:
            yield from _selected_operation_sources(tool)
    if isinstance(result, Mapping) and value.get('status') == 'completed':
        kind = result.get('information_kind')
        if kind == 'return_contract_information_v1':
            if result.get('source') in _BY_SOURCE:
                yield result['source']
            return
        if kind == 'operation_contract_information_v1':
            yield from _selected_operation_sources(result.get('operation'), union=True)
            return
    if selected_history and isinstance(value.get('selection'), Mapping):
        selection = value['selection']
        # History records can carry an admitted child return beside the
        # parent's selected child action. That return is parent STEERING, not
        # a selection of the child's source-specific TASK. A null field is
        # emitted for ordinary own actions and must not hide their selection.
        if value.get('admitted_report') is not None:
            return
        arguments = selection.get('arguments')
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (ValueError, TypeError):
                arguments = None
        yield from _selected_operation_sources(selection.get('tool'), arguments)
    # Walk actual data envelopes only. Do not reinterpret contracts, source
    # recipes, catalogues or child private state as returned scientific rows.
    for name, child in value.items():
        if name not in {'selection', 'arguments', 'assignment', 'context', 'private_history',
                'admitted_report', 'child_reports', 'current_report_update',
                'requested_form', 'report_schema', 'input_schema', 'tools', 'child_options'}:
            yield from _information_sources(child, selected_history=selected_history)


def selected_literature_task_sections(state, lookup_results=()):
    """Return complete relevant inserts once, preserving explicit request order."""
    if not isinstance(state, Mapping):
        return ()
    sources = []
    assignment = state.get('literature_assignment')
    if isinstance(assignment, Mapping):
        sources.extend(_BY_REQUEST[key] for key in assignment if key in _BY_REQUEST)
    sources.extend(_form_sources(state.get('requested_form')))
    goal = state.get('goal')
    if isinstance(goal, Mapping):
        sources.extend(_form_sources(goal.get('result_contract')))
    owned = state.get('literature_owned_population_sources')
    if isinstance(owned, (tuple, list)):
        sources.extend(source for source in owned if isinstance(source, str) and source in _BY_SOURCE)
    # Prior own work can make its method instructions relevant again. Admitted
    # child returns and the parent's report update inform STEERING; neither
    # commissions that child's method as the parent's TASK.
    sources.extend(_information_sources(state.get('last_local_outcome')))
    attempt = state.get('literature_selected_population_attempt')
    if isinstance(attempt, Mapping) and attempt.get('status') in ('invalid', 'failed', 'error'):
        sources.extend(_selected_operation_sources(attempt.get('tool'), attempt.get('arguments')))
    sources.extend(_information_sources(lookup_results, selected_history=True))
    sections, seen = [], set()
    for source in sources:
        task = _BY_SOURCE[source].task
        if task not in seen:
            sections.append((source, task)); seen.add(task)
        if source == 'literature_rate_grid_cells' and REPORTED_CURVE_SCOPE_TASK not in seen:
            sections.append(('reported_curve_scope', REPORTED_CURVE_SCOPE_TASK)); seen.add(REPORTED_CURVE_SCOPE_TASK)
    return tuple(sections)
