"""Original supplied-state literature steering display; no runtime ownership selection."""
from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_render import (hidden_records as _ratio_source_hidden_records,
    render_received as _ratio_source_received, render_own_result as _ratio_source_own,
    is_row as _ratio_source_row, rows_from_reports as _ratio_source_rows)
import gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_render as _completion_time
import gene_annotation_episode.episodic_workflow.root.library.literature_active_site_render as _active_site
import gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_render as _product_partition
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render as _native_rate
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display as _rate_domains
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_render as _rate_meanings
from gene_annotation_episode.episodic_workflow.root.library.literature_received_fact_render import ReceivedFactDisplay, ResolvedFactDisplay
from .literature_work_display import render_completed_work
from gene_annotation_episode.episodic_workflow.root.library.literature_current_results import (current_interpretation_view, current_scoring_view,
    render_current_findings, render_current_scoring_results)
from . import literature_kinetic_model_display as _kinetic_model
import gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_render as _interaction_model
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_prompt as _rate_observations
import gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_render as _product_coupling
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_validation_render as _measurement_validation
import gene_annotation_episode.episodic_workflow.root.library.literature_calibration_recovery_render as _calibration_recovery
import gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_render as _compiled_assay
import gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_render as _ion_discrimination
import gene_annotation_episode.episodic_workflow.root.library.literature_channel_render as _channel
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_replicate_prompt as _rate_replicates
import gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_render as _endpoint_signal
import gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_render as _summary_precision
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_render as _measurement_comparison
import gene_annotation_episode.episodic_workflow.root.library.literature_concentration_window_render as _concentration_window
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.library.decision_outcome_presentation import _band
from gene_annotation_episode.episodic_workflow.root.library.decision_schema_display import _schema
from gene_annotation_episode.episodic_workflow.root.library.decision_prompt_text import text_instructions
from .literature_record_projection import _scientific_records, _selected_records
from .literature_supplied_result_display import _received_returns, _source_result, _worksheet_context
from .literature_text_values import _complete_feedback, _pick, _safe, _section, _table, _values

def _steering(state, lookup_results, *, evidence_axis=None):
    parts = ["STEERING", "",
        'For text anchors, select the received source_ref, artifact_ref and '
        'zero-based half-open UTF-8 byte range start/end. Text witnesses use '
        'source_ref, representation and the same byte-range convention. '
        'The host retrieves and stores the exact quotation within that action. '
        'Returned quote values are source evidence, not text to transcribe into '
        'text-anchor or text-witness inputs. Image readings still require your '
        'interpretation of the selected native image region.']
    if state.get('pending_child_delivery') is not None:
        _section(parts, 'Complete the original child return', _values(state['pending_child_delivery']))
    rows = []
    yields = state.get("action_yields", {})
    for row in yields.get("rows", ()):
        expected = row.get("expected_yield", {})
        point, uncertainty = _band(expected.get("band"))
        if expected.get("status") == "unavailable":
            point, uncertainty = "unavailable", expected.get("unavailable_reason") or uncertainty
        rows.append((row.get("category"), row.get("completed_actions"), row.get("total_yield"),
                     point, uncertainty, row.get("attempted_uncompleted")))
    _section(parts, "Own action yields", _table(("Category", "Completed", "Total signed yield",
        "Expected next yield", "Uncertainty or unavailable reason", "Uncompleted attempts"), rows))
    controller = state.get("controller", {})
    estimate = controller.get("estimate", {})
    if estimate:
        point, uncertainty = _band(estimate.get("expected_next_gain"))
        _section(parts, "Current continuation expectation", _table(("Completed actions", "Expected next gain",
            "Uncertainty", "Continuation cost"), [(estimate.get("turns"), point, uncertainty,
                                                   controller.get("decision", {}).get("continuation_cost"))]))
    if yields.get("unavailable_reasons"):
        _section(parts, "Yield information limits", _values(yields["unavailable_reasons"]))
    selected = _selected_records(state, lookup_results)
    working = state.get("working_state", {})
    controlled_records = _scientific_records(state)
    common_hidden = _compiled_assay.hidden_records(list(_compiled_assay.rows_from_values((
        state.get('last_local_outcome', {}), state.get('child_reports', ()),
        state.get('current_report_update', {}), lookup_results))), controlled_records)
    grid_hidden = _rate_observations.hidden_grid_records(list(_rate_observations.rows_from_values((
        state.get("last_local_outcome", {}), state.get("child_reports", ()),
        state.get("current_report_update", {}), lookup_results))), controlled_records)
    concrete = 'literature_completed_work' in state
    if concrete:
        # This copy affects only model presentation. Exact caller-bound facts,
        # historical forms and their custody remain unchanged in the runtime.
        state = {**state, 'current_report_update': current_interpretation_view(
            state.get('current_report_update'), state.get('requested_form'),
            state.get('literature_current_scoring_sheets', ()))}
    a106 = (evidence_axis == 'A106'
        or state.get('literature_experimental_work', {}).get('evidence_axis') == 'A106')
    resolved = concrete or a106
    display_type = ResolvedFactDisplay if resolved else ReceivedFactDisplay
    display = display_type(selected, subjects=working.get("subjects", ()),
        revision_status=working.get("received_revision_status", ()),
        received_refs=(*state.get("literature_received_fact_display", {}).get("received_refs", ()), *common_hidden, *grid_hidden))
    operand_refs = list(dict.fromkeys([
        *(row['id'] for row in selected),
        *state.get("literature_received_fact_display", {}).get("received_refs", ()),
    ]))
    # Source/sequence labels are assigned while rendering the actual outcomes
    # below. Build their reference table afterward, so it uses the same labels
    # rather than naming a source "unresolved" before its identity is displayed.
    operand_reference_index = len(parts)
    def semantic_values(value):
        if isinstance(value, Mapping) and value.get('feedback') is not None:
            # Diagnostic keys, body text and literal handles are the returned
            # error itself. Scientific-name substitution must not rewrite it.
            ordinary = {key: child for key, child in value.items() if key != 'feedback'}
            projected = display.project(_safe(ordinary))
            return _values({**projected, 'feedback': value['feedback']})
        return _values(display.project(_safe(value)))
    if concrete:
        _section(parts, 'Completed work and recorded earned credit',
            render_completed_work(state['literature_completed_work'], table=_table, display=display))
        _section(parts, 'Current saved subscoring and evidence scoring results',
            render_current_scoring_results(state.get('literature_current_scoring_sheets', ()),
                table=_table, display=display))
        _section(parts, 'Received source findings and explicit corrections',
            render_current_findings(controlled_records,
                revision_status=working.get('received_revision_status', ()),
                table=_table, display=display))
    elif 'completed_action_reports' in state:
        from gene_annotation_episode.episodic_workflow.root.episode_work_report import render_completed_action_reports
        parts.extend(['', render_completed_action_reports(state['completed_action_reports'])])
    if state.get('literature_examined_source_inputs'):
        _section(parts, 'Previously examined inputs for your selected source',
            'Source locations and native measurement selectors from your own completed '
            'source actions remain available for the ordinary reasoning/grading action. '
            'The host retrieves the selected text from these locations within that '
            'action. Source text remains evidence and does not establish an assessment.')
        _section(parts, 'Retained source witnesses and measurement addresses',
            _values(state['literature_examined_source_inputs']))
    controlled_bindings = state.get("literature_controlled_response_return_bindings")
    gel_bindings = state.get("literature_gel_return_bindings")
    gel_records = {**controlled_records, **state.get("literature_gel_return_records", {})}
    native_rate_display = state.get("literature_rate_source_display", {})
    native_rate_records = {**controlled_records, **native_rate_display.get("records", {})}
    native_rate_display = {**native_rate_display, "records": native_rate_records}
    native_rate_domain_display = state.get("literature_rate_source_domain_display", {})
    native_rate_domain_records = {**controlled_records, **native_rate_domain_display.get("records", {})}
    native_rate_domain_display = {**native_rate_domain_display, "records": native_rate_domain_records}
    native_rate_meaning_display = state.get("literature_rate_source_meaning_display", {})
    native_rate_meaning_records = {**controlled_records, **native_rate_meaning_display.get("records", {})}
    native_rate_meaning_display = {**native_rate_meaning_display, "records": native_rate_meaning_records}
    if selected and not resolved:
        _section(parts, "Relevant received experimental facts", display.render_records(table=_table))
        _section(parts, "Selected received source excerpts", display.render_passages(table=_table))
        _section(parts, "Local scientific links", "Record and excerpt labels identify this display; they do not establish independent experiments.")
    outcome = state.get("last_local_outcome")
    if outcome is not None:
        current_saved_refs = ({sheet['sheet_ref'] for sheet in current_scoring_view(
            state.get('literature_current_scoring_sheets', ()))} if concrete else set())
        current_saved_outcome = (isinstance(outcome, Mapping)
            and (outcome.get('child_completion') is not None
                 or isinstance(outcome.get('result'), Mapping)
                    and outcome['result'].get('sheet_ref') in current_saved_refs
                 or isinstance(outcome.get('evidence_processing'), Mapping)
                    and bool(outcome['evidence_processing'].get('gradings')))
            and concrete)
        received_window_sheets = {r['sheet_ref'] for r in _concentration_window.rows_from_values(state.get('child_reports', ()))}
        received_comparison_sheets = {r['sheet_ref'] for r in _measurement_comparison.rows_from_values(state.get('child_reports', ()))}
        received_summary_sheets = {r['sheet_ref'] for r in _summary_precision.rows_from_values(state.get('child_reports', ()))}
        received_endpoint_sheets = {row["sheet_ref"] for row in _endpoint_signal.rows_from_reports(state.get("child_reports", ()))}
        received_coupling_sheets = {row["sheet_ref"] for row in _product_coupling.rows_from_reports(state.get("child_reports", ()))}
        received_validation_sheets = {row["sheet_ref"] for row in _measurement_validation.rows_from_reports(state.get("child_reports", ()))}
        received_ion_sheets = {row["sheet_ref"] for row in _ion_discrimination.rows_from_reports(state.get("child_reports", ()))}
        received_channel_sheets = {row["sheet_ref"] for row in _channel.rows_from_reports(state.get("child_reports", ()))}
        received_compiled_sheets = {row["sheet_ref"] for row in _compiled_assay.rows_from_reports(state.get("child_reports", ()))}
        received_recovery_sheets = {row["sheet_ref"] for row in _calibration_recovery.rows_from_reports(state.get("child_reports", ()))}
        received_observation_sheets = {row["sheet_ref"] for row in _rate_observations.rows_from_reports(state.get("child_reports", ()))}
        received_replicate_sheets = {row["sheet_ref"] for row in _rate_replicates.rows_from_reports(state.get("child_reports", ()))}
        received_partition_sheets = {row["sheet_ref"] for row in _product_partition.rows_from_reports(state.get("child_reports", ()))}
        received_completion_time_sheets = {row["sheet_ref"] for row in _completion_time.rows_from_reports(state.get("child_reports", ()))}
        received_active_site_sheets = {row["sheet_ref"] for row in _active_site.rows_from_reports(state.get("child_reports", ()))}
        received_interaction_model_sheets = {row["sheet_ref"] for row in _interaction_model.rows_from_reports(state.get("child_reports", ()))}
        received_kinetic_model_sheets = {row["sheet_ref"] for row in _kinetic_model.rows_from_reports(state.get("child_reports", ()))}
        received_ratio_sheets = {row['sheet_ref'] for row in _ratio_source_rows(state.get('child_reports', ()))}
        from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_render import rows_from_reports as controlled_rows
        received_controlled_sheets = {row['sheet_ref'] for row in controlled_rows(state.get('child_reports', ()))}
        from gene_annotation_episode.episodic_workflow.root.library.literature_gel_render import rows_from_reports as gel_rows
        received_gel_sheets = {row['sheet_ref'] for row in gel_rows(state.get('child_reports', ()))}
        received_native_rate_sheets = {row['sheet_ref'] for row in _native_rate.rows_from_reports(state.get('child_reports', ()))}
        received_native_rate_sheets.update(row['sheet_ref'] for row in _rate_domains.rows_from_reports(state.get('child_reports', ())))
        received_native_rate_sheets.update(row['sheet_ref'] for row in _rate_meanings.rows_from_reports(state.get('child_reports', ())))
        content = outcome.get('result', {}) if isinstance(outcome, Mapping) else {}
        channel_forwarded = (isinstance(content, Mapping) and content.get('view') == 'channel_components'
            and content.get('sheet_ref') in received_channel_sheets)
        ion_forwarded = (isinstance(content, Mapping) and content.get('view') == 'ion_discrimination_components'
            and content.get('sheet_ref') in received_ion_sheets)
        coupling_forwarded = (isinstance(content, Mapping) and content.get('view') == 'product_coupling_components'
            and content.get('sheet_ref') in received_coupling_sheets)
        validation_forwarded = (isinstance(content, Mapping) and content.get('view') == 'measurement_validation_components'
            and content.get('sheet_ref') in received_validation_sheets)
        common_forwarded = (isinstance(content, Mapping) and content.get('record_version') == 'literature_compiled_assay_record_v3'
            and content.get('sheet_ref') in received_compiled_sheets)
        grid_forwarded = (isinstance(content, Mapping) and content.get("view") == "reported_curve_precision_components"
            and content.get("sheet_ref") in received_observation_sheets)
        endpoint_forwarded = isinstance(content, Mapping) and content.get('view') == 'endpoint_signal_components' and content.get('sheet_ref') in received_endpoint_sheets
        summary_forwarded = isinstance(content, Mapping) and content.get('view') == 'kinetic_summary_precision_components' and content.get('sheet_ref') in received_summary_sheets
        comparison_forwarded = isinstance(content, Mapping) and content.get('view') == 'measurement_comparison_components' and content.get('sheet_ref') in received_comparison_sheets
        window_forwarded = isinstance(content, Mapping) and content.get('view') == 'concentration_window_components' and content.get('sheet_ref') in received_window_sheets
        if current_saved_outcome or window_forwarded or comparison_forwarded or summary_forwarded or endpoint_forwarded or grid_forwarded or common_forwarded or coupling_forwarded or validation_forwarded or ion_forwarded or channel_forwarded or (isinstance(outcome, Mapping) and 'result' not in outcome
                and (received_window_sheets | received_comparison_sheets | received_summary_sheets | received_endpoint_sheets | received_coupling_sheets | received_validation_sheets | received_ion_sheets | received_channel_sheets | received_compiled_sheets | received_recovery_sheets | received_observation_sheets | received_replicate_sheets | received_partition_sheets | received_completion_time_sheets | received_active_site_sheets | received_ratio_sheets | received_controlled_sheets | received_gel_sheets | received_native_rate_sheets | received_kinetic_model_sheets | received_interaction_model_sheets).intersection(outcome.get('record_refs', ()))):
            # The original child return's host receipt refs are not an extra
            # scientific return. Its exact admitted rows are rendered below.
            _section(parts, 'Last selected action outcome', semantic_values(_pick(outcome,
                ('status', 'feedback', 'error_code', 'errors', 'conflicts', 'child_completion'))))
        else:
            _source_result(parts, outcome, "Last selected action outcome", controlled_records=controlled_records,
                controlled_bindings=controlled_bindings, controlled_assignment=state.get("literature_assignment"),
                gel_bindings=gel_bindings, gel_assignment=state.get("literature_assignment"), gel_records=gel_records,
                native_rate_display=native_rate_display, native_rate_domain_display=native_rate_domain_display,
                native_rate_meaning_display=native_rate_meaning_display,
                completion_assignment=state.get("literature_assignment"), values=semantic_values)
    if state.get("feedback") is not None and state["feedback"] != (outcome or {}).get("feedback"):
        _section(parts, "Complete returned feedback", _complete_feedback(state["feedback"]))
    current_worksheet = _worksheet_context(state.get("current_report_update"))
    duplicate_context = (current_worksheet is not None and len(state["current_report_update"]) == 1
        and (not any(current_worksheet[1][key] for key in ('assertion_refs', 'quantity_links', 'assertion_links'))
            or any(_worksheet_context(report) is not None
                and _worksheet_context(report)[1] == current_worksheet[1]
                for report in state.get("child_reports", ()))))
    if state.get("current_report_update") and not duplicate_context:
        if (current_worksheet is not None or list(_concentration_window.rows_from_values(state["current_report_update"])) or list(_measurement_comparison.rows_from_values(state["current_report_update"])) or list(_summary_precision.rows_from_values(state["current_report_update"])) or list(_endpoint_signal.rows_from_reports([state["current_report_update"]])) or list(_product_coupling.rows_from_reports([state["current_report_update"]])) or
                list(_measurement_validation.rows_from_reports([state["current_report_update"]])) or
                list(_ion_discrimination.rows_from_reports([state["current_report_update"]])) or
                list(_channel.rows_from_reports([state["current_report_update"]])) or
                list(_compiled_assay.rows_from_reports([state["current_report_update"]])) or
                list(_calibration_recovery.rows_from_reports([state["current_report_update"]])) or
                list(_rate_observations.rows_from_reports([state["current_report_update"]])) or
                list(_rate_replicates.rows_from_reports([state["current_report_update"]])) or
                list(_completion_time.rows_from_reports([state["current_report_update"]])) or
                list(_active_site.rows_from_reports([state["current_report_update"]])) or
                list(_product_partition.rows_from_reports([state["current_report_update"]]))):
            _received_returns(parts, [state["current_report_update"]], records=controlled_records,
                ratio_source_meanings=state.get("literature_ratio_source_return_meanings"),
                controlled_bindings=controlled_bindings, gel_bindings=gel_bindings, gel_records=gel_records,
                native_rate_records=native_rate_records, native_rate_domain_records=native_rate_domain_records,
                native_rate_meaning_records=native_rate_meaning_records, values=semantic_values)
        else:
            _section(parts, "Current requested interpretation", semantic_values(state["current_report_update"]))
    if state.get("child_reports") and not concrete:
        # Concrete literature work uses original parent action/delivery/credit
        # receipts above. Current saved sheets and received source findings are
        # shown once. The original historical forms remain in ordinary history;
        # repeatedly printing every form and visibility inventory adds no result.
        _received_returns(parts, state["child_reports"], records=controlled_records,
            ratio_source_meanings=state.get("literature_ratio_source_return_meanings"),
            controlled_bindings=controlled_bindings, gel_bindings=gel_bindings, gel_records=gel_records,
            native_rate_records=native_rate_records, native_rate_domain_records=native_rate_domain_records,
            native_rate_meaning_records=native_rate_meaning_records, values=semantic_values)
    if state.get("shared_information_context") is not None:
        _section(parts, "Shared investigation updates",
            _values(state["shared_information_context"]))
    pending = state.get("pending_work", {})
    if pending.get("items"):
        _section(parts, "Pending assigned work", _values([_pick(row, (
            "handle", "role", "lifecycle_state", "selected_at", "observed_at",
            "latest_progress_ref", "return_available", "suspension", "event_target")) for row in pending["items"]]))
    if isinstance(state.get("waiting_support"), Mapping):
        _section(parts, "Choosing work or waiting for a child",
            "Compare useful work you can do now with the pending child's expected return. "
            "The episode.estimate_wait tool can inspect support for a proposed condition when useful. "
            "Select kind=wait with condition.version=event_condition_v1 and events containing "
            "the received pending handle, event=returned and after_cursor=0 to await its first return. "
            "For later event subscriptions, use the cursor actually received. "
            "Set reconsider_at=null for an event-only wait, or choose a supported reconsideration time. "
            "Reconsideration wakes this decision; it does not terminate the child or impose a run deadline. "
            "Repeated checks and elapsed time create no scientific credit. Unknown timing or gain "
            "remains unknown, and the existing continuation controller still owns continuation.")
        support = _pick(state["waiting_support"], ("progress_records", "duration_expectations",
            "local_return_history_unavailable_reason", "native_event_targets"))
        _section(parts, "Received information for the waiting decision", semantic_values(support))
    for result in lookup_results:
        _source_result(parts, result, "Requested information; continue this decision", controlled_records=controlled_records,
            controlled_bindings=controlled_bindings, controlled_assignment=state.get("literature_assignment"),
                gel_bindings=gel_bindings, gel_assignment=state.get("literature_assignment"), gel_records=gel_records,
                native_rate_display=native_rate_display, native_rate_domain_display=native_rate_domain_display,
                native_rate_meaning_display=native_rate_meaning_display,
                completion_assignment=state.get("literature_assignment"), values=semantic_values)
    if operand_refs and not resolved:
        references = []
        reference_rows = []
        for reference in operand_refs:
            # A generic record_refs field may precede a source_ref field in
            # the same result. Preserve both labels if that earlier projection
            # already used an unresolved-link label for this exact identity.
            labels = dict.fromkeys((display.ref(reference),
                display.unresolved_labels.get(reference)))
            reference_rows.extend((label, reference) for label in labels if label is not None)
        _section(references, "Received record references for subsequent actions", _table(
            ("Display label", "Persistent reference"), reference_rows))
        parts[operand_reference_index:operand_reference_index] = references
    return "\n".join(parts)


