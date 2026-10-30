"""Exact A105 numerical declarations, separate from investigation instructions.

This bounded catalog names existing return schemas, not new readers or scores.
New legacy decisions can freeze their available declarations before selection.
Saved validation uses only that snapshot; it never substitutes today's factory.
"""
from collections.abc import Mapping
from importlib import import_module
import re

from .episode_contract_information import ContractInformationError, FACT_REFERENCE_PREFIX, expand_fact_form
from .schema_information_text import _copy_json, schema_fingerprint
from .schema_support import _schema_nodes


VERSION = 'literature_numerical_contracts_v1'
SAVED_MEMBER = 'literature_numerical_contracts'
_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.:+/\-]*\Z')
_TYPES = frozenset(('null', 'object', 'array', 'number', 'integer', 'boolean', 'string'))

# Only existing A105 measurement/experimental-component return families belong
# here. Later literature axes and computational result contracts stay separate.
_SCHEMAS = {
    'literature_endpoint_signal_cells': ('literature_endpoint_signal_storage', 'endpoint_signal_cells_schema'),
    'literature_rate_cells': ('literature_rate_storage', 'rate_cells_schema'),
    'literature_rate_source_cells': ('literature_rate_storage', 'rate_source_cells_schema'),
    'literature_rate_source_domain_cells': ('literature_rate_domains', 'rate_source_domain_cells_schema'),
    'literature_rate_source_meaning_cells': ('literature_rate_meaning_delivery', 'rate_source_meaning_cells_schema'),
    'literature_rate_observation_cells': ('literature_rate_observation_storage', 'rate_observation_cells_schema'),
    'literature_rate_grid_cells': ('literature_rate_observation_storage', 'rate_grid_cells_schema'),
    'literature_rate_replicate_cells': ('literature_rate_replicate_storage', 'rate_replicate_cells_schema'),
    'literature_calibration_recovery_cells': ('literature_calibration_recovery_storage', 'calibration_recovery_cells_schema'),
    'literature_product_coupling_cells': ('literature_product_coupling_storage', 'product_coupling_cells_schema'),
    'literature_measurement_validation_cells': ('literature_measurement_validation_storage', 'measurement_validation_cells_schema'),
    'literature_quantity_cells': ('literature_quantity_storage', 'quantity_cells_schema'),
    'literature_assay_cells': ('literature_assay_storage', 'assay_cells_schema'),
    'literature_ratio_cells': ('literature_ratio_storage', 'ratio_cells_schema'),
    'literature_ratio_source_cells': ('literature_ratio_source_storage', 'ratio_source_cells_schema'),
    'literature_binding_cells': ('literature_binding_storage', 'binding_cells_schema'),
    'literature_binding_model_cells': ('literature_binding_model_storage', 'binding_model_cells_schema'),
    'literature_binding_interaction_cells': ('literature_binding_interaction_storage', 'binding_interaction_cells_schema'),
    'literature_binding_interaction_model_cells': ('literature_binding_interaction_model_storage', 'binding_interaction_model_cells_schema'),
    'literature_transport_cells': ('literature_transport_storage', 'transport_response_cells_schema'),
    'literature_amount_cells': ('literature_amount_storage', 'amount_cells_schema'),
    'literature_optical_cells': ('literature_optical_storage', 'optical_cells_schema'),
    'literature_kinetic_cells': ('literature_kinetic_storage', 'kinetic_cells_schema'),
    'literature_kinetic_model_cells': ('literature_kinetic_model_storage', 'kinetic_model_cells_schema'),
    'literature_completion_time_cells': ('literature_completion_time_storage', 'completion_time_cells_schema'),
    'literature_active_site_cells': ('literature_active_site_storage', 'active_site_cells_schema'),
    'literature_product_partition_cells': ('literature_product_partition_storage', 'product_partition_cells_schema'),
    'literature_channel_cells': ('literature_channel_storage', 'channel_cells_schema'),
    'literature_compiled_assay_cells': ('literature_compiled_assay_storage', 'compiled_assay_cells_schema'),
    'literature_compiled_assay_v2_cells': ('literature_compiled_assay_storage', 'compiled_assay_v2_cells_schema'),
    'literature_compiled_assay_v3_cells': ('literature_compiled_assay_storage', 'compiled_assay_v3_cells_schema'),
    'literature_ion_discrimination_cells': ('literature_ion_discrimination_storage', 'ion_discrimination_cells_schema'),
    'literature_controlled_response_component_cells': ('literature_controlled_response_storage', 'controlled_response_cells_schema'),
    'literature_gel_component_cells': ('literature_gel_native_contracts', 'gel_cells_schema'),
    'literature_figure_cells': ('literature_figure_storage', 'figure_cells_schema'),
}

# These describe returned scientific information, without enumerating internal
# sheet cells, formulas or population implementation. Actual bound source
# meanings remain available alongside them in the original host declaration.
RETURN_MEANINGS = {
    'literature_endpoint_signal_cells': 'Exactly requested endpoint amplitude, correction-fraction or variance components with actual subject, endpoint, conditions, finite window, correction stage and applicability. Preserve conditional values, dependent views, manual reading versus physical uncertainty and source origins; no unrequested ordinates, amplitudes, caption results or covariance matrix are expanded.',
    'literature_rate_cells': 'Source-preparation rates and conditional comparisons, retaining actual subject, endpoint, conditions, normalization, units and unavailable statistical inputs.',
    'literature_rate_source_cells': 'Native source-rate comparisons with separate arm subject, construct and preparation identities, reported limits, approximation and statistical qualifications.',
    'literature_rate_source_domain_cells': 'Native rate comparisons and reported-operand domains, retaining bound inclusivity, undefined denominators, conditional relationships and numerical projection limits. These domains are distinct from sampling confidence.',
    'literature_rate_source_meaning_cells': 'Native rate comparisons and domains with recorded intended-change, endpoint, normalization and source-defined unit meanings. Retain witness limitations and requested operand scope.',
    'literature_rate_observation_cells': 'Descriptive summaries and contrasts of selected source-reported entries, retaining witnessed subject/group meanings, repeated or conflicting identities, selected roster, censoring and unknown experimental independence.',
    'literature_rate_grid_cells': 'Requested reported-curve precision scalars and only their named concentration coordinates, preserving actual subject/endpoint, distinct estimators, reporting counts, fixed concentration scope, conditional sampling covariance, source conflicts and shared measurements. Physical preparation count, product attribution and published-estimate covariance remain separate unknowns.',
    'literature_rate_replicate_cells': 'Raw-rate group and sampling-unit summaries, retaining selected and observed groups, actual counts, missing or censored entries, physical identity and conditional dependence. Descriptive variability and conditional mean uncertainty remain separate.',
    'literature_calibration_recovery_cells': 'Recovery-control comparisons with actual control analyte, matrix, endpoint, blank treatment, expected-value basis, measurement reuse and reported uncertainty meanings. Preserve reporter-standard versus activity-spike scope.',
    'literature_product_coupling_cells': 'Source product/cofactor components with actual endpoint roles, reaction-account model, separate descriptive and physical meanings, native nondetection qualifications, shared measurement identities and original covariance ownership. Dependent views supply neither molecular attribution nor independent support.',
    'literature_measurement_validation_cells': 'Source precision and control-separation components with each physical measurement and alternative basis preserved. Reported statistics, deterministic re-expressions and conditional versus interpreted error estimates retain analyte, matrix, endpoint, repetition, population, denominator and shared-measurement meanings.',
    'literature_quantity_cells': 'Single source-reported quantities with quantity role, analyte identity, native value and original uncertainty meaning. Preserve unknown assay conditions, attribution and corrections.',
    'literature_assay_cells': 'Source-anchored assay measurements and corrections with actual interpreted subject, conditions, endpoint, molecular arrangement, measurement dependencies, covariance qualifications and unavailable operands.',
    'literature_ratio_cells': 'Reported relative-signal comparisons with actual denominator and molecular arrangement, representation candidates, conflicts and source origins. Preserve missing calibration and functional-response information.',
    'literature_ratio_source_cells': 'Selected source-reported relative signals and dependent comparisons, preserving actual scientific meanings, reported-estimate domains, representation completeness, conflicts and unresolved scale or physical identity.',
    'literature_binding_cells': 'Source binding parameters and comparisons with actual protein/state/ligand identities, parameter kind, source design, reported limits and fit-spread basis. Keep IC50 and reported fitted Kd meanings distinct.',
    'literature_binding_model_cells': 'Conditional source log-binding-parameter comparisons, preserving actual model origin, covariance ownership, variance status, censoring assumptions and uncertainty limitations.',
    'literature_binding_interaction_cells': 'Source binding comparisons across separately assayed molecular forms and ligands, preserving actual parameter kind, fit identity, protocols, representation conflicts and requested uncertainty scope.',
    'literature_binding_interaction_model_cells': 'Conditional uncertainty and model evidence for the same source binding interaction, preserving ordered physical fit owners, supplied covariance, model source, reporting-event support and actual protocol qualifications.',
    'literature_transport_cells': 'Conditional substrate-response comparisons with actual source concentration, fitted-curve and preparation meanings, supported kinetic relationships, covariance ownership and unavailable-input qualifications.',
    'literature_amount_cells': 'Source amount comparisons with actual quantity roles, preparation/stock relationships, measurement method, units, reported bounds and covariance ownership. Keep mass fraction and nominal molar arm comparisons distinct.',
    'literature_optical_cells': 'Source optical endpoint-rate and uncertainty information, retaining actual subject, construct, preparation, conditions, selected extinction/path relationships, measurement reuse and covariance qualifications.',
    'literature_kinetic_cells': 'Native source kinetic parameters and descriptive contrasts with per-operand molecule/construct identity, protocols, qualification and uncertainty meanings. Preserve dependent representations and the native reader\'s model limitations.',
    'literature_kinetic_model_cells': 'Conditional uncertainty and model evidence for the same source kinetic contrast, retaining ordered physical estimate owners, supplied covariance, model origin and known/estimated/unknown variance distinctions.',
    'literature_completion_time_cells': 'Source-preparation completion times and conditional comparisons with actual endpoint, preparation, conditions, intended change, positive-time domains and strict reported-limit qualifications.',
    'literature_active_site_cells': 'Active-site titration amount comparisons with actual preparation, assay linkage, molecular and stoichiometric basis, titrant standardization, source uncertainty and normalization stage.',
    'literature_product_partition_cells': 'Reported product-composition fractions and dependent partition or closure comparisons, retaining actual species, preparation, endpoint, denominator, measurement basis, stage and unresolved relationships.',
    'literature_channel_cells': 'Source electrical measurements and conditional comparisons with actual molecular arrangement, current/voltage/conductance meanings, reversal applicability, measurement dependencies and uncertainty qualifications.',
    'literature_compiled_assay_cells': 'Within-assay source numerical sections with actual subject, endpoint, correction stages, amount normalization, controls, shared measurement dependencies, covariance and applicability qualifications.',
    'literature_compiled_assay_v2_cells': 'Versioned within-assay numerical sections with estimand-scoped joint covariance, physical operand ownership and signed first-order propagation. Operand-propagated uncertainty stays separate from total corrected-activity uncertainty and additional residual variability.',
    'literature_compiled_assay_v3_cells': 'Common source-assessment numerical components for the actual functional assertion and comparison, retaining measured endpoints, model applicability, native versus conditional results, scientific relationships, uncertainty ownership and distinct source/implementation limitations. Effect isolation, endpoint relevance and comparability remain distinct; dependent transforms are not independent verification.',
    'literature_ion_discrimination_cells': 'Source ion-discrimination comparisons with actual biological, ion and construct meanings, source scope, distinct reported/estimator/nominal/conditional physical domains, dependencies and uncertainty qualifications.',
    'literature_controlled_response_component_cells': 'Requested controlled-response comparisons with actual alternative meanings, source origins, controls, covariance scope, uncertainty and partial support. Conditional graph-reading domains remain distinct from sampling uncertainty.',
    'literature_gel_component_cells': 'Requested gel display measurements and comparisons with actual experiment/lane meanings, coherent ROI alternatives, methods, dependence and available-only sensitivity. Preserve the distinction between display darkness and calibrated molecular occupancy.',
    'literature_figure_cells': 'Source experimental graph ordinates and signed differences with actual subject/partner arms, endpoint, normalization, representation relationships and original repeat/spread meanings. Preserve conditional digitization bounds.',
}


def registered_sources():
    return tuple(_SCHEMAS)


def registered_schema(source):
    """Return an existing detached exact type; acquire no scientific values."""
    if source not in _SCHEMAS:
        return None
    module, factory = _SCHEMAS[source]
    return _copy_json(getattr(import_module('.' + module, __package__), factory)())


def is_registered_schema(schema, *, source=None):
    if not isinstance(schema, Mapping):
        return False
    source = schema.get('x-source') if source is None else source
    if source not in _SCHEMAS or schema.get('x-source') != source:
        return False
    return schema_fingerprint(schema) == schema_fingerprint(registered_schema(source))


def uses_fact_references(schema):
    """Identify explicit chosen fact aliases, preserving literal native refs."""
    return any(isinstance(node, Mapping) and any(type(node.get(key)) is str
        and node[key].startswith(FACT_REFERENCE_PREFIX)
        for key in ('$ref', '$dynamicRef', '$recursiveRef')) for _, node in _schema_nodes(schema))


def freeze_contracts(*, facts_by_role, permitted_child_roles, action_schema):
    """Select exact available types; preserve caller roles and scientific meanings.

    A custom legacy form remains usable through its original literal route. It
    does not acquire a registered alias merely by sharing a source selector.
    """
    roles = list(permitted_child_roles)
    selected, source_types = {}, {}
    for role in roles:
        facts = facts_by_role.get(role, {})
        source_types[role] = {source: {'type': _copy_json(row['type'])}
            for source, row in facts.items()}
        selected[role] = {source: _copy_json(row) for source, row in facts.items()
            if source in _SCHEMAS and isinstance(row, Mapping)
            and isinstance(row.get('meaning'), str)
            and is_registered_schema(row.get('report_schema'), source=source)
            and schema_fingerprint(row.get('type')) == schema_fingerprint(row['report_schema']['type'])}
    if not any(selected.values()):
        return None
    record = {'version': VERSION, 'permitted_child_roles': roles,
        'fact_sources_by_role': selected, 'fact_sources_sha256': schema_fingerprint(selected),
        'source_types_by_role': source_types, 'source_types_sha256': schema_fingerprint(source_types),
        'action_schema_sha256': schema_fingerprint(action_schema)}
    validate_frozen_contracts({SAVED_MEMBER: record, 'schema': action_schema})
    return record


def validate_frozen_contracts(saved):
    """Check original snapshot relationships without consulting any factory."""
    record = _copy_json(saved.get(SAVED_MEMBER))
    keys = {'version', 'permitted_child_roles', 'fact_sources_by_role',
        'fact_sources_sha256', 'source_types_by_role', 'source_types_sha256', 'action_schema_sha256'}
    if (not isinstance(record, dict) or set(record) != keys or record['version'] != VERSION
            or record['fact_sources_sha256'] != schema_fingerprint(record['fact_sources_by_role'])
            or record['source_types_sha256'] != schema_fingerprint(record['source_types_by_role'])
            or record['action_schema_sha256'] != schema_fingerprint(saved['schema'])):
        raise ContractInformationError('original_literature_numerical_contracts_mismatch')
    roles, facts, types = (record['permitted_child_roles'], record['fact_sources_by_role'],
        record['source_types_by_role'])
    if (not isinstance(roles, list) or any(type(role) is not str or _NAME.fullmatch(role) is None for role in roles)
            or len(set(roles)) != len(roles) or not isinstance(facts, dict)
            or set(facts) != set(roles) or not isinstance(types, dict) or set(types) != set(roles)):
        raise ContractInformationError('original_literature_numerical_roles_mismatch')
    for role, rows in facts.items():
        if not isinstance(rows, dict):
            raise ContractInformationError('original_literature_numerical_fact_map_mismatch')
        if not isinstance(types[role], dict):
            raise ContractInformationError('original_literature_numerical_source_types_mismatch')
        for source, row in types[role].items():
            if (type(source) is not str or _NAME.fullmatch(source) is None
                    or not isinstance(row, dict) or set(row) != {'type'}):
                raise ContractInformationError('original_literature_numerical_source_types_mismatch')
            kinds = row['type'] if isinstance(row['type'], list) else [row['type']]
            if (not kinds or any(type(kind) is not str or kind not in _TYPES for kind in kinds)
                    or len(set(kinds)) != len(kinds)):
                raise ContractInformationError('original_literature_numerical_source_types_mismatch')
        for source, row in rows.items():
            if (source not in _SCHEMAS or not isinstance(row, dict)
                    or not {'type', 'meaning', 'report_schema'} <= row.keys()
                    or type(row['meaning']) is not str or not isinstance(row['report_schema'], dict)
                    or row['report_schema'].get('x-source') != source
                    or row['report_schema'].get('type') != 'array' or row['type'] != 'array'
                    or types[role].get(source) != {'type': 'array'}):
                raise ContractInformationError('original_literature_numerical_fact_mismatch')
    return record


def expand_numerical_form(submitted_schema_json, *, child_role, saved):
    """Expand selected aliases only from the original bounded host snapshot."""
    record = validate_frozen_contracts(saved)
    return expand_fact_form(submitted_schema_json, child_role=child_role,
        facts_by_role=record['fact_sources_by_role'],
        permitted_child_roles=record['permitted_child_roles'])


__all__ = ['VERSION', 'SAVED_MEMBER', 'registered_sources', 'registered_schema',
    'RETURN_MEANINGS', 'is_registered_schema', 'uses_fact_references', 'freeze_contracts',
    'validate_frozen_contracts', 'expand_numerical_form']
