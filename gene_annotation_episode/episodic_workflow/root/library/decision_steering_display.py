"""Original decision steering display for supplied decision information."""
from __future__ import annotations
from .alignment_result_presentation import alignment_report_presentation
from ..infernal_result_presentation import infernal_receiver_context
import json
from ..episode_work_report import render_completed_action_reports
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import render_rna_comparison_own_outcome
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import render_rna_comparison_projections
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import render_rna_structure_groups
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import render_rna_structure_own_outcome
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import render_rna_structure_own_progress
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_presentation import select_rna_comparison_presentation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_presentation import select_rna_structure_presentation
from .decision_outcome_presentation import _band
from .decision_outcome_presentation import _feedback
from .decision_outcome_presentation import _information
from .decision_outcome_presentation import _lookup
from .molecular_provenance_display import _molecular_literal
from .decision_outcome_presentation import _outcome
from .decision_prompt_text import _pick
from .decision_outcome_presentation import _progress
from .decision_outcome_presentation import _received_records
from .decision_record_fields import _record
from .decision_prompt_text import _section
from .decision_prompt_text import _table
from .molecular_value_presentation import _values


def _steering(state, lookup_results):
    parts = ["STEERING"]
    if 'completed_action_reports' in state:
        parts.extend(['', render_completed_action_reports(state['completed_action_reports'])])
    if state.get('pending_child_delivery') is not None:
        _section(parts, 'Complete the original child return', _values(state['pending_child_delivery']))
    if state.get('resource_context') is not None:
        _section(parts, 'Local budget, shared capacity and Aurora planning', _values(state['resource_context']))
    if state.get('execution_initial_information') or state.get('execution_resource_information'):
        for name, title in (
                ('execution_resource_capabilities', 'Actual configured execution resources'),
                ('execution_initial_information', 'Retained initial resource observations'),
                ('execution_resource_information', 'Retained resource observations')):
            if state.get(name) not in (None, {}, []):
                _section(parts, title, json.dumps({name: state[name]}, ensure_ascii=False,
                    allow_nan=False, separators=(',', ':')))
    if state.get('shared_information_context') is not None:
        _section(parts, 'Shared-parent information needs and available deliveries',
            _values(state['shared_information_context']))
    # These channels are resolved against this receiver's actual receipts by
    # the scientific binding. Preserve their numerical subsets, qualifications
    # and dependence rather than leaving them only in the unrendered context.
    for key, title in (
            ('component_axis_scoring_sheets',
             'Current A107/A110 scientific scoring sheets; updated automatically from received results'),
            ('received_partner_and_chemical_evidence',
             'Received A107/A110 scientific component reports; separate quantities'),
            ('received_partner_and_chemical_native_components',
             'Received A107/A110 native components and execution findings'),
            ('received_partner_and_chemical_qualifications',
             'Received A107/A110 per-use scientific qualifications'),
            ('received_gene_context_execution',
             'Received genomic execution outcomes and missing capabilities')):
        if state.get(key):
            # These versioned sheets already carry their complete structure.
            # Repeating a dotted field path for every cell and provenance
            # leaf can exceed the provider interface even for a small dataset.
            # Keep every supplied value and dependency in compact nested JSON.
            body = (_molecular_literal(state[key])
                    if key == 'component_axis_scoring_sheets' else _values(state[key]))
            _section(parts, title, body)
    yields = state.get("action_yields", {})
    rows = []
    for row in yields.get("rows", ()):
        expected = row.get("expected_yield", {})
        point, uncertainty = _band(expected.get("band"))
        if expected.get("status") == "unavailable":
            point = "unavailable"
            uncertainty = expected.get("unavailable_reason") or uncertainty
        rows.append((row["category"], row["completed_actions"], row["total_yield"], point,
            uncertainty, row.get("attempted_uncompleted")))
    _section(parts, "Own completed actions", _table(("Category", "Completed", "Total signed yield",
        "Expected next yield", "Uncertainty or unavailable reason", "Uncompleted attempts"), rows))
    controller = state.get("controller", {})
    estimate = controller.get("estimate", {})
    if estimate:
        point, uncertainty = _band(estimate.get("expected_next_gain"))
        _section(parts, "Current continuation expectation", _table(
            ("Completed actions", "Expected next gain", "Uncertainty", "Continuation cost"),
            [(estimate.get("turns"), point, uncertainty,
                controller.get("decision", {}).get("continuation_cost"))]))
    metrics = _pick(state, ("current_credit", "annotation_score", "monitoring_information_credit"))
    if metrics:
        _section(parts, "Current separate measures", _values(metrics))
    progress = {key: state[key] for key in ("credit_binding", "investigation_progress")
        if state.get(key) is not None}
    if progress:
        _section(parts, "Scientific progress definition and current findings",
            _molecular_literal(progress))
    if yields.get("unavailable_reasons"):
        _section(parts, "Yield information limits", _values(yields["unavailable_reasons"]))
    records = _received_records(state)
    if records:
        _section(parts, "Current interpretations and their received evidence", _values(records))
    if state.get("current_report_update"):
        _section(parts, "Current return interpretation", _values(state["current_report_update"]))
    # Completed-work accounts summarize outcomes and earned credit; they omit
    # source bodies, exact witnesses and command streams. Preserve the latest
    # authorized tool return so the episode can use what it actually acquired.
    if state.get("last_local_outcome") is not None:
        _section(parts, "Last own action outcome", _values(_information(_outcome(state["last_local_outcome"]))))
    if state.get("feedback") is not None and state["feedback"] != (state.get("last_local_outcome") or {}).get("feedback"):
        _section(parts, "Actionable feedback", _values(_feedback(state["feedback"])))
    if state.get("child_reports") and 'completed_action_reports' not in state:
        _section(parts, "Admitted child returns", _values([
            alignment_report_presentation(report) for report in state["child_reports"]]))
    if state.get("received_bvbrc_values"):
        _section(parts, "Received BV-BRC Data API values", _values([
            _pick(group, ("form_field", "fact_source", "facts", "cells", "unavailable"))
            for group in state["received_bvbrc_values"]]))
    pending = state.get("pending_work", {})
    if pending.get("items"):
        rows = []
        for row in pending["items"]:
            current = _pick(row, ("handle", "role", "lifecycle_state", "selected_at", "observed_at",
                "latest_progress_ref", "return_available", "event_target", "original_assignment"))
            resource = row.get("resource_selection")
            if resource is not None:
                current["resource_selection"] = _pick(resource, ("resource_id", "kind", "allocation"))
            rows.append(current)
        _section(parts, "Pending work", _values(rows))
        wanted = {row.get("latest_progress_ref") for row in pending["items"]}
        progress = [_progress(row) for row in state.get("waiting_support", {}).get("progress_records", ())
            if row.get("progress_ref") in wanted and row.get("progress_ref") is not None]
        if progress:
            _section(parts, "Latest received progress for pending work", _values(progress))
    if state.get("resource_tool_estimates"):
        _section(parts, "Execution duration expectations", _values([_pick(row,
            ("job_ref", "proposal_ref", "execution_class_ref", "current_condition_state", "status", "phase",
             "cpu_threads", "memory_limit_bytes", "scratch_limit_bytes", "successful_duration_samples",
             "outcome_support", "expected_total_seconds", "observed_min_seconds", "observed_max_seconds",
             "forecast_duration_measure", "elapsed_seconds", "timing_relation"))
            for row in state["resource_tool_estimates"]]))
    if state.get("job_execution_options"):
        _section(parts, "Operands for the duration expectations", _values(state["job_execution_options"]))
    if state.get("native_event_targets"):
        _section(parts, "Available native event operands", _values([
            {"target": _pick(row["target"], ("handle", "job_ref", "resource_id", "event", "cause")),
                "after_cursor": row["after_cursor"]} for row in state["native_event_targets"]]))
    deliveries = [row for row in state.get("report_deliveries", ())
        if row.get("status") == "pending" or row.get("timing_receipt_issues")]
    if deliveries:
        _section(parts, "Report delivery issues", _values(deliveries))
    parse_failures = [_record(row) for row in state.get("working_state", {}).get("parse_attempts", ())
        if row.get("status") not in {None, "completed"} or row.get("error_count", 0)]
    if parse_failures:
        _section(parts, "Supplied material parsing issues", _values(parse_failures))
    for result in lookup_results:
        _section(parts, "Requested information; continue the same decision", _lookup(result))
    return "\n".join(parts)


def _interval_result_presentation(state, lookup_results):
    """Select declared scientific-result channels before generic masking."""
    from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_presentation import (
        select_genomic_overlap_presentation, render_genomic_overlap_projections)
    from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_presentation import (
        select_chromatin_presentation, render_chromatin_projections)
    from gene_annotation_episode.episodic_workflow.root.library.atac_differential_presentation import (
        select_atac_presentation, render_atac_projections)
    from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_presentation import (
        select_expression_nmf_presentation, render_expression_nmf_projections)
    from gene_annotation_episode.episodic_workflow.root.library.native_profile_presentation import (
        select_native_profile_presentation, render_native_profile_results)
    overlap = select_genomic_overlap_presentation(state, lookup_results=lookup_results)
    chromatin = select_chromatin_presentation(overlap['context'],
        lookup_results=overlap['lookup_results'])
    atac = select_atac_presentation(chromatin['context'],
        lookup_results=chromatin['lookup_results'])
    nmf = select_expression_nmf_presentation(atac['context'],
        lookup_results=atac['lookup_results'])
    profiles = select_native_profile_presentation(nmf['context'],
        lookup_results=nmf['lookup_results'])
    sections = []
    if overlap['projections']:
        sections.append(render_genomic_overlap_projections(overlap['projections']))
    if chromatin['projections']:
        sections.append(render_chromatin_projections(chromatin['projections']))
    if atac['projections']:
        sections.append(render_atac_projections(atac['projections']))
    if nmf['projections']:
        sections.append(render_expression_nmf_projections(nmf['projections']))
    if profiles['projections']:
        sections.append(render_native_profile_results(profiles['projections']))
    return profiles['context'], profiles['lookup_results'], sections


def _render_episode_steering(state, lookup_results, interval_sections):
    """Render a state whose interval channels have already been selected."""
    from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import select_macs2_peak_capture_presentation, render_macs2_peak_captures
    macs2 = select_macs2_peak_capture_presentation(state, lookup_results=lookup_results)
    state, lookup_results = macs2['context'], macs2['lookup_results']
    selected = select_rna_comparison_presentation(infernal_receiver_context(state))
    original = select_rna_structure_presentation(selected["context"])
    parts = [_steering(original["context"], lookup_results)]
    _section(parts, "Last own RNA comparison outcome",
        render_rna_comparison_own_outcome(selected["own_outcome"]))
    if selected["projections"]:
        _section(parts, "Selected RNA comparison facts",
            render_rna_comparison_projections(selected["projections"]))
    _section(parts, "Original RNA result delivery",
        render_rna_structure_own_progress(original["own_progress"]))
    _section(parts, "Last own original RNA result outcome",
        render_rna_structure_own_outcome(original["own_outcome"]))
    if original["groups"]:
        _section(parts, "Selected original RNA facts and callable operands",
            render_rna_structure_groups(original["groups"]))
    if macs2['captures']:
        parts.append(render_macs2_peak_captures(macs2['captures']))
    parts.extend(interval_sections)
    return "\n".join(parts)


def render_episode_steering(state, *, lookup_results=()):
    """Render supplied facts after detached, exact registered selection."""
    state, lookup_results, sections = _interval_result_presentation(state, lookup_results)
    return _render_episode_steering(state, lookup_results, sections)


