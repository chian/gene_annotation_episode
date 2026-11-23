"""Exact A106 numerical declarations, separate from investigation instructions.

This bounded catalog names existing return schemas, not new readers or scores.
Decisions can freeze their available declarations before selection.
Saved validation uses only that snapshot; it never substitutes the live factory.

A106 retains its private numerical source-measurement families and its
perturbation operand, intervention grading and final subscore returns.
A105 aggregation/assay return declarations and A108 contextual declarations
are not imported into this binding.
The private service exposes this module through literature_numerical_contracts;
snapshot validation and expansion keep the original saved transport format.

Root contract-information expansion and schema/JSON helper dependencies remain;
this split does not claim their independent parsing implementations are private.
"""
from collections.abc import Mapping
from importlib import import_module
import re

from gene_annotation_episode.episodic_workflow.episode_support.instructions.schema_information_text import _copy_json, schema_fingerprint
from gene_annotation_episode.episodic_workflow.episode_support.forms.schema_support import _schema_nodes


VERSION = 'literature_numerical_contracts'
SAVED_MEMBER = 'literature_numerical_contracts'
_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.:+/\-]*\Z')
_TYPES = frozenset(('null', 'object', 'array', 'number', 'integer', 'boolean', 'string'))

# Declared literature numerical return families. Computational result contracts
# retain their own registries; adding a family here installs no calculation.
_SCHEMAS = {
    'literature_concentration_window_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_concentration_window_storage', 'concentration_window_cells_schema'),
    'literature_measurement_comparison_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_measurement_comparison_storage', 'measurement_comparison_cells_schema'),
    'literature_kinetic_summary_precision_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_kinetic_summary_precision_storage', 'summary_precision_cells_schema'),
    'literature_endpoint_signal_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_endpoint_signal_storage', 'endpoint_signal_cells_schema'),
    'literature_rate_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_storage', 'rate_cells_schema'),
    'literature_rate_source_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_storage', 'rate_source_cells_schema'),
    'literature_rate_source_domain_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_rate_domains', 'rate_source_domain_cells_schema'),
    'literature_rate_source_meaning_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_rate_meaning_delivery', 'rate_source_meaning_cells_schema'),
    'literature_rate_observation_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_observation_storage', 'rate_observation_cells_schema'),
    'literature_rate_grid_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_observation_storage', 'rate_grid_cells_schema'),
    'literature_rate_replicate_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_replicate_storage', 'rate_replicate_cells_schema'),
    'literature_calibration_recovery_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_calibration_recovery_storage', 'calibration_recovery_cells_schema'),
    'literature_product_coupling_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_product_coupling_storage', 'product_coupling_cells_schema'),
    'literature_measurement_validation_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_measurement_validation_storage', 'measurement_validation_cells_schema'),
    'literature_quantity_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_quantity_storage', 'quantity_cells_schema'),
    'literature_assay_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_assay_storage', 'assay_cells_schema'),
    'literature_ratio_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_ratio_storage', 'ratio_cells_schema'),
    'literature_ratio_source_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_ratio_source_storage', 'ratio_source_cells_schema'),
    'literature_binding_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_binding_storage', 'binding_cells_schema'),
    'literature_binding_model_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_binding_model_storage', 'binding_model_cells_schema'),
    'literature_binding_interaction_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_binding_interaction_storage', 'binding_interaction_cells_schema'),
    'literature_binding_interaction_model_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_binding_interaction_model_storage', 'binding_interaction_model_cells_schema'),
    'literature_transport_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_transport_storage', 'transport_response_cells_schema'),
    'literature_amount_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_amount_storage', 'amount_cells_schema'),
    'literature_optical_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_optical_storage', 'optical_cells_schema'),
    'literature_kinetic_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_kinetic_storage', 'kinetic_cells_schema'),
    'literature_kinetic_model_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_kinetic_model_storage', 'kinetic_model_cells_schema'),
    'literature_completion_time_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_completion_time_storage', 'completion_time_cells_schema'),
    'literature_active_site_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_active_site_storage', 'active_site_cells_schema'),
    'literature_product_partition_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_product_partition_storage', 'product_partition_cells_schema'),
    'literature_parent_depletion_cells':('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_parent_depletion_storage','parent_depletion_cells_schema'),
    'literature_stoichiometric_balance_cells':('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_stoichiometric_balance_storage','stoichiometric_balance_cells_schema'),
    'literature_channel_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_channel_storage', 'channel_cells_schema'),
    'literature_compiled_assay_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_compiled_assay_storage', 'compiled_assay_cells_schema'),
    'literature_common_assessment_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_compiled_assay_storage', 'common_assessment_cells_schema'),
    'literature_ion_discrimination_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_ion_discrimination_storage', 'ion_discrimination_cells_schema'),
    'literature_controlled_response_component_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_controlled_response_storage', 'controlled_response_cells_schema'),
    'literature_gel_component_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_gel_native_contracts', 'gel_cells_schema'),
    'literature_figure_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_figure_storage', 'figure_cells_schema'),
    'literature_perturbation_operand_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_perturbation_operands', 'cells_schema'),
    'literature_intervention_grading_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_intervention_storage', 'intervention_cells_schema'),
    'literature_a106_subscore_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_subscore', 'cells_schema'),
    'literature_a108_grading_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage', 'grading_cells_schema'),
    'literature_a108_aggregation_cells': ('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage', 'aggregation_cells_schema'),
}

# These describe returned scientific information, without enumerating internal
# sheet cells, formulas or population implementation. Actual bound source
# meanings remain available alongside them in the original host declaration.
RETURN_MEANINGS = {
    'literature_concentration_window_cells': 'Exactly requested source concentration-window components with actual molecule, construct, preparation, participants, analyte, units, basis and normalization. Preserve native versus calculated origins, per-pair and cross-readout comparability and physical account, interpreted stoichiometric coefficients, qualified timing, conditional sensitivity and covariance selection/status/account_context/dependence. Concentration changes and product-fate fractions do not establish unique molecular attribution, independent replication, target transfer or annotation credit. Unrequested native operands and covariance matrices remain private; missing scientific inputs and unfinished approximate, bounded or raw-table covariance calculations stay distinct.',
    'literature_measurement_comparison_cells': 'Exactly requested source measurement-comparison components with actual studied molecule, endpoint, normalization, estimator scale, source qualifications, protocol differences and declared model applicability. Keep descriptive comparisons, common-estimand calculations, signed optical corrections and conditional scenarios distinct. Preserve covariance account_context/status and shared measurements without unrequested operands or a matrix; no independent-assay count, function probability, target transfer or annotation credit.',
    'literature_kinetic_summary_precision_cells': 'Exactly requested source or explicitly selected scenario precision cells for one kinetic summary, with actual molecule, construct, endpoint, independent unit scales, physical versus statistical sampling meaning and unavailable reasons. Estimated random mean precision is not known population variance. Source SD, counts, derived variance/SE and proposed interval parameters share one contribution; no unrequested numerical operands, target transfer or annotation credit are delivered.',
    'literature_endpoint_signal_cells': 'Exactly requested endpoint amplitude, correction-fraction or variance components with actual subject, endpoint, conditions, finite window, correction stage and applicability. Preserve conditional values, dependent views, manual reading versus physical uncertainty and source origins; no unrequested ordinates, amplitudes, caption results or covariance matrix are expanded.',
    'literature_rate_cells': 'Source-preparation rates and conditional comparisons, retaining actual subject, endpoint, conditions, normalization, units and unavailable statistical inputs.',
    'literature_rate_source_cells': 'Native source-rate comparisons with separate arm subject, construct and preparation identities, reported limits, approximation and statistical qualifications.',
    'literature_rate_source_domain_cells': 'Native rate comparisons and reported-operand domains, retaining bound inclusivity, undefined denominators, conditional relationships and numerical projection limits. These domains are distinct from sampling confidence.',
    'literature_rate_source_meaning_cells': 'Native rate comparisons and domains with recorded intended-change, endpoint, normalization and source-defined unit meanings. Retain witness limitations and requested operand scope.',
    'literature_rate_observation_cells': 'Descriptive summaries and contrasts of selected source-reported entries, retaining witnessed subject/group meanings, repeated or conflicting identities, selected roster, censoring and unknown experimental independence.',
    'literature_rate_grid_cells': 'Requested reported-curve precision scalars and only their named concentration coordinates, preserving actual subject/endpoint, distinct estimators, reporting counts, fixed concentration scope, conditional sampling covariance, source conflicts and shared measurements. Physical preparation count, product attribution and published-estimate covariance remain separate unknowns.',
    'literature_rate_replicate_cells': 'Raw-rate group and sampling-unit summaries, retaining selected and observed groups, actual counts, missing or censored entries, physical identity and conditional dependence. Descriptive variability and conditional mean uncertainty remain separate.',
    'literature_calibration_recovery_cells': 'Recovery-control comparisons with actual control analyte, matrix, endpoint, blank treatment, expected-value basis, measurement reuse and reported uncertainty meanings. Preserve reporter-standard versus activity-spike scope.',
    'literature_product_coupling_cells': 'Source product/cofactor components with actual endpoint roles, reaction-account model, separate descriptive and physical meanings, native nondetection qualifications, shared measurement identities and original covariance account_context. Dependent views supply neither molecular attribution nor independent support.',
    'literature_measurement_validation_cells': 'Source precision and control-separation components with each physical measurement and alternative basis preserved. Reported statistics, deterministic re-expressions and conditional versus interpreted error estimates retain analyte, matrix, endpoint, repetition, population, denominator and shared-measurement meanings.',
    'literature_quantity_cells': 'Single source-reported quantities with quantity role, analyte identity, native value and original uncertainty meaning. Preserve unknown assay conditions, attribution and corrections.',
    'literature_assay_cells': 'Source-anchored assay measurements and corrections with actual interpreted subject, conditions, endpoint, molecular arrangement, measurement dependencies, covariance qualifications and unavailable operands.',
    'literature_ratio_cells': 'Reported relative-signal comparisons with actual denominator and molecular arrangement, representation candidates, conflicts and source origins. Preserve missing calibration and functional-response information.',
    'literature_ratio_source_cells': 'Selected source-reported relative signals and dependent comparisons, preserving actual scientific meanings, reported-estimate domains, representation completeness, conflicts and unresolved scale or physical identity.',
    'literature_binding_cells': 'Source binding parameters and comparisons with actual protein/state/ligand identities, parameter kind, source design, reported limits and fit-spread basis. Keep IC50 and reported fitted Kd meanings distinct.',
    'literature_binding_model_cells': 'Conditional source log-binding-parameter comparisons, preserving actual model origin, covariance account_context, variance status, censoring assumptions and uncertainty limitations.',
    'literature_binding_interaction_cells': 'Source binding comparisons across separately assayed molecular forms and ligands, preserving actual parameter kind, fit identity, protocols, representation conflicts and requested uncertainty scope.',
    'literature_binding_interaction_model_cells': 'Conditional uncertainty and model evidence for the same source binding interaction, preserving ordered physical fit owners, supplied covariance, model source, reporting-event support and actual protocol qualifications.',
    'literature_transport_cells': 'Conditional substrate-response comparisons with actual source concentration, fitted-curve and preparation meanings, supported kinetic relationships, covariance account_context and unavailable-input qualifications.',
    'literature_amount_cells': 'Source amount comparisons with actual quantity roles, preparation/stock relationships, measurement method, units, reported bounds and covariance account_context. Keep mass fraction and nominal molar arm comparisons distinct.',
    'literature_optical_cells': 'Source optical endpoint-rate and uncertainty information, retaining actual subject, construct, preparation, conditions, selected extinction/path relationships, measurement reuse and covariance qualifications.',
    'literature_kinetic_cells': 'Native source kinetic parameters and descriptive contrasts with per-operand molecule/construct identity, protocols, qualification and uncertainty meanings. Preserve dependent representations and the native reader\'s model limitations.',
    'literature_kinetic_model_cells': 'Conditional uncertainty and model evidence for the same source kinetic contrast, retaining ordered physical estimate owners, supplied covariance, model origin and known/estimated/unknown variance distinctions.',
    'literature_completion_time_cells': 'Source-preparation completion times and conditional comparisons with actual endpoint, preparation, conditions, intended change, positive-time domains and strict reported-limit qualifications.',
    'literature_active_site_cells': 'Active-site titration amount comparisons with actual preparation, assay linkage, molecular and stoichiometric basis, titrant standardization, source uncertainty and normalization stage.',
    'literature_product_partition_cells': 'Reported product-composition fractions and dependent partition or closure comparisons, retaining actual species, preparation, endpoint, denominator, measurement basis, stage and unresolved relationships.',
    'literature_parent_depletion_cells':'Original XLSX finite parent-removal arm fractions, reported per-arm SDs, and two dependent active-control differences with source cell identities. Missing raw denominator, joint uncertainty, mutant amount and product formation remain explicit.',
    'literature_stoichiometric_balance_cells':'Original XLSX Figure 2D G2–G6 and Pi concentrations, source SDs, conditional molecule and glucosyl-equivalent balances, descriptive dependent ratios and inferred remainders. Calibration eligibility is checked; validity multiplier, solid-product measurement, ratio uncertainty, target transfer and annotation credit remain absent.',
    'literature_channel_cells': 'Source electrical measurements and conditional comparisons with actual molecular arrangement, current/voltage/conductance meanings, reversal applicability, measurement dependencies and uncertainty qualifications.',
    'literature_compiled_assay_cells': 'Within-assay numerical sections with estimand-scoped joint covariance, physical operand account_context and signed first-order propagation. Operand-propagated uncertainty stays separate from total corrected-activity uncertainty and additional residual variability.',
    'literature_common_assessment_cells': 'Common source-assessment numerical components for the actual functional assertion and comparison, retaining measured endpoints, model applicability, native versus conditional results, scientific relationships, uncertainty account_context and distinct source/implementation limitations. Effect isolation, endpoint relevance and comparability remain distinct; dependent transforms are not independent verification.',
    'literature_ion_discrimination_cells': 'Source ion-discrimination comparisons with actual biological, ion and construct meanings, source scope, distinct reported/estimator/nominal/conditional physical domains, dependencies and uncertainty qualifications.',
    'literature_controlled_response_component_cells': 'Requested controlled-response comparisons with actual alternative meanings, source origins, controls, covariance scope, uncertainty and partial support. Conditional graph-reading domains remain distinct from sampling uncertainty.',
    'literature_gel_component_cells': 'Requested gel display measurements and comparisons with actual experiment/lane meanings, coherent ROI alternatives, methods, dependence and available-only sensitivity. Preserve the distinction between display darkness and calibrated molecular occupancy.',
    'literature_figure_cells': 'Source experimental graph ordinates and signed differences with actual subject/partner arms, endpoint, normalization, representation relationships and original repeat/spread meanings. Preserve conditional digitization bounds.',
    'literature_perturbation_operand_cells': 'Selected original perturbation effects and matching mean variances retain original measurement identities, shared controls and full source cell meanings. No additional experiment, independence claim or recalculated science.',
    'literature_intervention_grading_cells': 'A106 intervention assessments, native diagnostics and conditional signed evidence ratios retain experiment identity, comparison, design and revisions.',
    'literature_a106_subscore_cells': 'A106 final signed log evidence ratio is bound to the subject, assertion, alternative, scope and current original experiments; retain missing scores, dependence and revisions.',
    'literature_a108_grading_cells': 'Requested purpose-specific A108 numerical counts of supporting, conflicting, overlapping and unresolved original organism-context observations. Preserve candidate and actual target organism/context, source-specific scientific criteria, original observation identity, qualified transfer and conditions. Evidence amount counts the supporting/conflicting union once; net support is separate. Repeated source representations add no observation, and these counts are not annotation probability or the Episode progress scalar.',
    'literature_a108_aggregation_cells': 'Requested A108 main evidence scoring sheet components for physiology, environment, availability, localization and overall. Each retains evidence amount and separate support/conflict/overlap/net/unresolved counts, recomputed from possessed original observation unions. Shared observations across sources, children or domains count once. Unselected domains remain unavailable; source context, actual contributors and unresolved relationships remain explicit.',
}


def registered_sources():
    return tuple(_SCHEMAS)


def registered_schema(source):
    """Return an existing detached exact type; acquire no scientific values."""
    if source not in _SCHEMAS:
        return None
    module, factory = _SCHEMAS[source]
    return _copy_json(getattr(import_module(module), factory)())


def is_registered_schema(schema, *, source=None):
    if not isinstance(schema, Mapping):
        return False
    source = schema.get('x-source') if source is None else source
    if source not in _SCHEMAS or schema.get('x-source') != source:
        return False
    return schema_fingerprint(schema) == schema_fingerprint(registered_schema(source))



__all__ = ['VERSION', 'SAVED_MEMBER', 'registered_sources', 'registered_schema', 'RETURN_MEANINGS',
           'is_registered_schema']
