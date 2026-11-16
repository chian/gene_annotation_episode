"""Select full literature TASK inserts from actual requested or received work.

Pure instructional selection only: no source access, sheet loading, scientific
calculation, action selection or observations. Capability catalogues and legacy
work booleans are deliberately not evidence that a method was selected.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
import json
from .literature_task_families import A105_ASSAY_SELECTION_TASK, NATIVE_KINETIC_TASK, family_row as a104_family_row

@dataclass(frozen=True)
class _Family:
    source: str
    task: str
    storage_module: str
    repository_class: str
    requested: str
    operation: str
_FAMILIES = (_Family(*a104_family_row('literature_assay_grading_cells')), _Family(*a104_family_row('literature_a105_aggregation_cells')), _Family(*a104_family_row('literature_concentration_window_cells')), _Family(*a104_family_row('literature_amount_cells')), _Family(*a104_family_row('literature_kinetic_cells')), _Family(*a104_family_row('literature_kinetic_summary_precision_cells')), _Family(*a104_family_row('literature_endpoint_signal_cells')), _Family(*a104_family_row('literature_measurement_comparison_cells')), _Family(*a104_family_row('literature_product_coupling_cells')), _Family(*a104_family_row('literature_calibration_recovery_cells')), _Family(*a104_family_row('literature_measurement_validation_cells')), _Family(*a104_family_row('literature_compiled_assay_cells')), _Family(*a104_family_row('literature_compiled_assay_v2_cells')), _Family(*a104_family_row('literature_compiled_assay_v3_cells')), _Family(*a104_family_row('literature_rate_observation_cells')), _Family(*a104_family_row('literature_rate_grid_cells')), _Family(*a104_family_row('literature_rate_replicate_cells')), _Family(*a104_family_row('literature_assay_cells')), _Family(*a104_family_row('literature_binding_cells')), _Family(*a104_family_row('literature_binding_model_cells')), _Family(*a104_family_row('literature_binding_interaction_cells')), _Family(*a104_family_row('literature_binding_interaction_model_cells')), _Family(*a104_family_row('literature_kinetic_model_cells')), _Family(*a104_family_row('literature_transport_cells')), _Family(*a104_family_row('literature_figure_cells')), _Family(*a104_family_row('literature_ratio_source_cells')), _Family(*a104_family_row('literature_controlled_response_component_cells')), _Family(*a104_family_row('literature_gel_component_cells')), _Family(*a104_family_row('literature_completion_time_cells')), _Family(*a104_family_row('literature_active_site_cells')), _Family(*a104_family_row('literature_product_partition_cells')), _Family(*a104_family_row('literature_parent_depletion_cells')), _Family(*a104_family_row('literature_stoichiometric_balance_cells')), _Family(*a104_family_row('literature_channel_cells')), _Family(*a104_family_row('literature_ion_discrimination_cells')))
_BY_SOURCE = {f.source: f for f in _FAMILIES}
_BY_SOURCE.update({alias: _BY_SOURCE[source] for alias, source in {}.items()})
_BY_REQUEST = {f.requested: f.source for f in _FAMILIES}
_BY_REQUEST.update({'requested_gel_views': 'literature_gel_component_cells', 'requested_controlled_response_views': 'literature_controlled_response_component_cells'})

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
        else:
            versions = (getattr(module, 'VERSION', repository.record_version),)
        flag = {'literature_assay_grading_cells': 'assay_grading_population', 'literature_a105_aggregation_cells': 'assay_grading_population', 'literature_compiled_assay_cells': 'compiled_assay_population', 'literature_compiled_assay_v2_cells': 'compiled_assay_population', 'literature_compiled_assay_v3_cells': 'compiled_assay_population', 'literature_ratio_source_cells': 'ratio_source_population', 'literature_controlled_response_component_cells': 'controlled_response_population', 'literature_gel_component_cells': 'gel_population', 'literature_completion_time_cells': 'completion_time_population', 'literature_active_site_cells': 'active_site_population', 'literature_product_partition_cells': 'product_partition_population', 'literature_parent_depletion_cells': 'parent_depletion_population', 'literature_stoichiometric_balance_cells': 'stoichiometric_balance_population', 'literature_channel_cells': 'channel_population', 'literature_ion_discrimination_cells': 'ion_discrimination_population'}.get(family.source, 'rate_population')
        yield (family.source, flag, repository.operations_table, module.PROVIDER, versions)
_SCOPE_SOURCE = {'assay_type_experimental_evidence': 'literature_assay_grading_cells', 'a105_across_experiment_aggregation': 'literature_a105_aggregation_cells', 'source_concentration_window': 'literature_concentration_window_cells', 'source_amount_comparison': 'literature_amount_cells', 'source_measurement_comparison': 'literature_measurement_comparison_cells', 'source_kinetic_summary_precision': 'literature_kinetic_summary_precision_cells', 'source_endpoint_signal_contribution': 'literature_endpoint_signal_cells', 'source_product_coupling': 'literature_product_coupling_cells', 'source_calibration_recovery': 'literature_calibration_recovery_cells', 'source_measurement_validation': 'literature_measurement_validation_cells', 'compiled_source_endpoint': 'literature_compiled_assay_cells', 'common_assertion_contrast': 'literature_compiled_assay_v3_cells', 'source_reported_rate_observations': 'literature_rate_observation_cells', 'source_reported_curve_precision': 'literature_rate_grid_cells', 'source_raw_rate_replicates': 'literature_rate_replicate_cells', 'interpreted_source_endpoint': 'literature_assay_cells', 'interpreted_source_parameter_contrast': 'literature_binding_model_cells', 'interpreted_source_kinetic_response': 'literature_transport_cells', 'reference_experimental_figure_ordinates': 'literature_figure_cells', 'source_preparation_completion_time': 'literature_completion_time_cells', 'active_site_titration_amount': 'literature_active_site_cells', 'reported_selected_product_partition': 'literature_product_partition_cells', 'finite_parent_compound_removal': 'literature_parent_depletion_cells', 'source_soluble_product_stoichiometric_balance': 'literature_stoichiometric_balance_cells', 'source_electrical_activity': 'literature_channel_cells', 'source_ion_discrimination': 'literature_ion_discrimination_cells'}
_ROW_VERSION_SOURCE = {'concentration_window_return_v1': 'literature_concentration_window_cells', 'measurement_comparison_return_v2': 'literature_measurement_comparison_cells', 'kinetic_summary_precision_return_v1': 'literature_kinetic_summary_precision_cells', 'endpoint_signal_return_v1': 'literature_endpoint_signal_cells', 'literature_controlled_response_component_fact_v3': 'literature_controlled_response_component_cells', 'literature_gel_component_fact_v1': 'literature_gel_component_cells'}
_MODEL_VIEWS = {'kinetic_log_model_components': 'literature_kinetic_model_cells', 'binding_interaction_log_model_components': 'literature_binding_interaction_model_cells'}

def _row_source(value):
    if not isinstance(value.get('sheet_ref'), str) or not any((name in value for name in ('component', 'cells'))):
        return None
    version = value.get('row_version', value.get('version'))
    required_versions = {'source_concentration_window': 'concentration_window_return_v1', 'source_measurement_comparison': 'measurement_comparison_return_v2', 'source_kinetic_summary_precision': 'kinetic_summary_precision_return_v1', 'source_endpoint_signal_contribution': 'endpoint_signal_return_v1'}
    expected_version = required_versions.get(value.get('evaluation_scope'))
    if 'component' in value and expected_version and (version != expected_version):
        return None
    source = _ROW_VERSION_SOURCE.get(version)
    if source:
        expected = {'literature_concentration_window_cells': 'source_concentration_window', 'literature_measurement_comparison_cells': 'source_measurement_comparison', 'literature_kinetic_summary_precision_cells': 'source_kinetic_summary_precision', 'literature_endpoint_signal_cells': 'source_endpoint_signal_contribution'}.get(source)
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
        return 'literature_binding_interaction_model_cells' if isinstance(formula, str) and formula.startswith('binding_interaction_model_') else 'literature_binding_interaction_cells'
    if scope == 'compiled_source_endpoint' and value.get('record_version') == 'literature_compiled_assay_record_v3':
        return None
    if scope in _SCOPE_SOURCE:
        return _SCOPE_SOURCE[scope]
    if value.get('candidate_basis') == 'selected_received_source_representations' and value.get('uncertainty_evaluation') == 'numeric_uncertainty_reader_unimplemented':
        return 'literature_ratio_source_cells'
    if isinstance(formula, str) and formula.startswith('binding_') and (not formula.startswith(('binding_model_', 'binding_interaction_'))):
        return 'literature_binding_cells'
    return None

def _selected_operation_sources(tool, arguments=None, *, union=False):
    if union:
        if tool == 'literature.figure.populate':
            return ('literature_figure_cells', 'literature_endpoint_signal_cells')
        return tuple((f.source for f in _FAMILIES if f.operation == tool))
    arguments = arguments if isinstance(arguments, Mapping) else {}
    if tool == 'literature.kinetic.populate':
        version = arguments.get('version')
        return ('literature_kinetic_summary_precision_cells',) if version == 'literature_kinetic_summary_precision_population_v1' else ('literature_kinetic_cells',) if version in (None, 'a104_kinetic_source_selection_v1') else ()
    if tool == 'literature.figure.populate':
        version = arguments.get('version')
        return ('literature_endpoint_signal_cells',) if version == 'literature_figure_endpoint_signal_population_v1' else ('literature_figure_cells',) if version is None else ()
    if tool == 'literature.assay.components.populate':
        version = arguments.get('population_version')
        return ('literature_compiled_assay_v3_cells',) if version == 'a104_common_assessment_population_v1' else ('literature_compiled_assay_v2_cells',) if version == 'a104_compiled_assay_population_v2' else ('literature_compiled_assay_cells',) if version is None else ()
    if tool == 'literature.rate.observations.populate':
        version = arguments.get('version')
        return ('literature_rate_grid_cells',) if version == 'a104_reported_curve_population_v1' else ('literature_rate_observation_cells',) if version is None else ()
    if tool == 'literature.partner.source.populate':
        return ('literature_partner_cells',)
    return tuple((f.source for f in _FAMILIES if f.operation == tool))

def _form_sources(form):
    if not isinstance(form, Mapping):
        return
    nodes = form.get('properties', {}).values() if isinstance(form.get('properties'), Mapping) else (form,)
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        if set(node) == {'$ref'} and isinstance(node['$ref'], str) and node['$ref'].startswith('episode-fact:'):
            source = node['$ref'][len('episode-fact:'):]
            if source in _BY_SOURCE:
                yield source
        elif node.get('x-source') in _BY_SOURCE:
            item = node.get('items')
            properties = item.get('properties') if isinstance(item, Mapping) else None
            if node.get('type') == 'array' and isinstance(properties, Mapping) and ({'sheet_ref', 'component'} <= properties.keys()) and (item.get('additionalProperties') is False):
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
        if tool not in {'literature.kinetic.populate', 'literature.figure.populate', 'literature.assay.components.populate', 'literature.rate.observations.populate'}:
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
        if value.get('admitted_report') is not None:
            return
        arguments = selection.get('arguments')
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except (ValueError, TypeError):
                arguments = None
        yield from _selected_operation_sources(selection.get('tool'), arguments)
    for name, child in value.items():
        if name not in {'selection', 'arguments', 'assignment', 'context', 'private_history', 'admitted_report', 'child_reports', 'current_report_update', 'requested_form', 'report_schema', 'input_schema', 'tools', 'child_options'}:
            yield from _information_sources(child, selected_history=selected_history)

def selected_literature_task_sections(state, lookup_results=()):
    """Return complete relevant inserts once, preserving explicit request order."""
    if not isinstance(state, Mapping):
        return ()
    sources = []
    assignment = state.get('literature_assignment')
    if isinstance(assignment, Mapping):
        sources.extend((_BY_REQUEST[key] for key in assignment if key in _BY_REQUEST))
    sources.extend(_form_sources(state.get('requested_form')))
    goal = state.get('goal')
    if isinstance(goal, Mapping):
        sources.extend(_form_sources(goal.get('result_contract')))
    owned = state.get('literature_owned_population_sources')
    if isinstance(owned, (tuple, list)):
        sources.extend((source for source in owned if isinstance(source, str) and source in _BY_SOURCE))
    sources.extend(_information_sources(state.get('last_local_outcome')))
    attempt = state.get('literature_selected_population_attempt')
    if isinstance(attempt, Mapping) and attempt.get('status') in ('invalid', 'failed', 'error'):
        sources.extend(_selected_operation_sources(attempt.get('tool'), attempt.get('arguments')))
    sources.extend(_information_sources(lookup_results, selected_history=True))
    sections, seen = ([], set())
    for source in sources:
        task = _BY_SOURCE[source].task
        if task not in seen:
            sections.append((source, task))
            seen.add(task)
        if source == 'literature_rate_grid_cells' and REPORTED_CURVE_SCOPE_TASK not in seen:
            sections.append(('reported_curve_scope', REPORTED_CURVE_SCOPE_TASK))
            seen.add(REPORTED_CURVE_SCOPE_TASK)
    return tuple(sections)
