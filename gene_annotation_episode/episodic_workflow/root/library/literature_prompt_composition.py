"""Original supplied-state literature prompt composition; no runtime ownership selection."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_render import hidden_records as _interaction_hidden_records, render_received as _interaction_received
from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_prompt import SOURCE_RATIO_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_render import (hidden_records as _ratio_source_hidden_records,
    render_received as _ratio_source_received, render_own_result as _ratio_source_own,
    is_row as _ratio_source_row, rows_from_reports as _ratio_source_rows)
from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_gel_prompt import GEL_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_render as _completion_time
from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_prompt import COMPLETION_TIME_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_active_site_render as _active_site
from gene_annotation_episode.episodic_workflow.root.library.literature_active_site_prompt import ACTIVE_SITE_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_render as _product_partition
import gene_annotation_episode.episodic_workflow.root.library.literature_parent_depletion_render as _parent_depletion
import gene_annotation_episode.episodic_workflow.root.library.literature_stoichiometric_balance_render as _stoichiometric_balance
from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_prompt import PRODUCT_PARTITION_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render as _native_rate
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display as _rate_domains
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_render as _rate_meanings
from gene_annotation_episode.episodic_workflow.root.library.literature_received_fact_render import ReceivedFactDisplay, ResolvedFactDisplay
from .literature_work_display import render_completed_work
from gene_annotation_episode.episodic_workflow.root.library.literature_current_results import (current_interpretation_view, current_scoring_view,
    render_current_findings, render_current_scoring_results)
from . import literature_kinetic_model_display as _kinetic_model
import gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_render as _interaction_model
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_prompt import BINDING_INTERACTION_MODEL_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_prompt as _rate_observations
import gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_render as _product_coupling
from gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_validation_render as _measurement_validation
from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_calibration_recovery_render as _calibration_recovery
from gene_annotation_episode.episodic_workflow.root.library.literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_render as _compiled_assay
from gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK, COMMON_ASSESSMENT_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_render as _ion_discrimination
from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_channel_render as _channel
from gene_annotation_episode.episodic_workflow.root.library.literature_channel_prompt import CHANNEL_TASK
import gene_annotation_episode.episodic_workflow.root.library.literature_numerical_return_presentation as _numerical_return
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_replicate_prompt as _rate_replicates
import gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_render as _endpoint_signal
import gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_render as _summary_precision
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_render as _measurement_comparison
import gene_annotation_episode.episodic_workflow.root.library.literature_concentration_window_render as _concentration_window
from collections.abc import Mapping
from .literature_task_selection import A105_ASSAY_SELECTION_TASK, selected_literature_task_sections
from gene_annotation_episode.episodic_workflow.root.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_a105_worksheet_declarations import VERSION as _WORKSHEET_VERSION, VERSION_V2 as _WORKSHEET_VERSION_V2
from gene_annotation_episode.episodic_workflow.root.library.literature_a105_worksheet_render import render_a105_worksheet
from gene_annotation_episode.episodic_workflow.root.library.decision_outcome_presentation import _band
from gene_annotation_episode.episodic_workflow.root.library.decision_schema_display import _schema
from gene_annotation_episode.episodic_workflow.root.library.decision_prompt_text import text_instructions
from gene_annotation_episode.episodic_workflow.root.library.literature_assay_prompt import ASSAY_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_prompt import BINDING_TASK, BINDING_MODEL_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_transport_prompt import TRANSPORT_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_prompt import PERTURBATION_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_structure_prompt import STRUCTURE_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_prompt import REACTION_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_figure_prompt import FIGURE_TASK
from gene_annotation_episode.episodic_workflow.root.library.literature_partner_prompt import PARTNER_TASK
from gene_annotation_episode.episodic_workflow.root.composition_information import (CONTRACT_INFORMATION_PROFILE, CONTRACT_ARGUMENT_TRANSPORT,
    is_contract_information, requested_contract_information)
from gene_annotation_episode.schema_information_text import render_schema_information
from ..presentation_literature_context import is_literature_experimental_context
from .literature_declared_task_text import _requested_contract_task, _task
from .literature_steering_display import _steering

def render_literature_experimental_prompt(state, instructions, *, lookup_results=()):
    """Render the full recurring task and selected factual steering, purely."""
    if not is_literature_experimental_context(state):
        raise ValueError("literature_experimental_context_required")
    # Select using the original actual assignments, declarations and completed
    # lookups before any numerical-return presentation compaction/sanitization.
    sections = selected_literature_task_sections(state, lookup_results)
    if state.get("literature_experimental_work", {}).get("aspect") == "reference_evidence_parent":
        from .literature_reference_parent_presentation import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions, lookup_results=lookup_results)
    # These are presentation copies only. The runtime keeps the exact original
    # assignment and typed contract for construction, validation and delivery.
    from gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_render import sanitize_private
    lookup_results = sanitize_private(lookup_results, state.get('literature_endpoint_receipt_bindings', {}))
    lookup_results = _summary_precision.sanitize_private(lookup_results, state.get('literature_summary_precision_receipt_bindings', {}))
    lookup_results = _measurement_comparison.sanitize_private(lookup_results, state.get('literature_measurement_comparison_receipt_bindings', {}))
    state = _endpoint_signal.state_view(_rate_observations.grid_state_view(_numerical_return.state_view(state), lookup_results), lookup_results)
    state = _summary_precision.state_view(state, lookup_results)
    state = _measurement_comparison.state_view(state, lookup_results)
    lookup_results = _concentration_window.sanitize_private(lookup_results, state.get('literature_concentration_window_receipt_bindings', {}))
    state = _concentration_window.state_view(state, lookup_results)
    if any(_numerical_return.common_assessment_lookup(outcome) for outcome in lookup_results) or any(
            _compiled_assay.is_common_row(row) for row in _compiled_assay.rows_from_values(lookup_results)):
        state = {**state, 'literature_common_assessment_work': {'version': 'literature_common_assessment_task_v1'}}
    for outcome in lookup_results:
        kind = _numerical_return.lookup_task_kind(outcome)
        if kind == 'literature_product_coupling_cells':
            state = {**state, 'literature_product_coupling_work': {'version': 'literature_product_coupling_task_v1'}}
        elif kind == 'literature_measurement_validation_cells':
            state = {**state, 'literature_measurement_validation_work': {'version': 'literature_measurement_validation_task_v1'}}
        elif kind == 'literature_ion_discrimination_cells':
            state = {**state, 'literature_ion_discrimination_work': {'version': 'literature_ion_discrimination_task_v1'}}
        elif kind == 'literature_channel_cells':
            state = {**state, 'literature_channel_work': {'version': 'literature_channel_task_v1'}}
        elif kind in ('literature_compiled_assay_cells', 'literature_compiled_assay_v2_cells'):
            state = {**state, 'literature_compiled_assay_work': {'version': 'literature_compiled_assay_task_v1'}}
    if any(_product_coupling.rows_from_values(lookup_results)):
        state = {**state, "literature_product_coupling_work": {"version": "literature_product_coupling_task_v1"}}
    if any(_measurement_validation.rows_from_values(lookup_results)):
        state = {**state, "literature_measurement_validation_work": {"version": "literature_measurement_validation_task_v1"}}
    if any(_ion_discrimination.rows_from_values(lookup_results)):
        state = {**state, "literature_ion_discrimination_work": {"version": "literature_ion_discrimination_task_v1"}}
    if any(_channel.rows_from_values(lookup_results)):
        state = {**state, "literature_channel_work": {"version": "literature_channel_task_v1"}}
    if state.get('contract_information_profile') == CONTRACT_INFORMATION_PROFILE:
        return _requested_contract_task(_task(state, instructions, selected_sections=sections), lookup_results) + '\n\n' + _steering(
            state, [row for row in lookup_results if not is_contract_information(row)])
    return _task(state, instructions, selected_sections=sections) + "\n\n" + _steering(state, lookup_results)


