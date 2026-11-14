"""Original supplied-state literature record projection; no runtime ownership selection."""
from gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_render import hidden_records as _interaction_hidden_records, render_received as _interaction_received
from gene_annotation_episode.episodic_workflow.root.library.literature_ratio_source_render import (hidden_records as _ratio_source_hidden_records,
    render_received as _ratio_source_received, render_own_result as _ratio_source_own,
    is_row as _ratio_source_row, rows_from_reports as _ratio_source_rows)
import gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_render as _product_partition
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render as _native_rate
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_domain_display as _rate_domains
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_meaning_render as _rate_meanings
from . import literature_kinetic_model_display as _kinetic_model
import gene_annotation_episode.episodic_workflow.root.library.literature_binding_interaction_model_render as _interaction_model
import gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_prompt as _rate_observations
import gene_annotation_episode.episodic_workflow.root.library.literature_product_coupling_render as _product_coupling
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_validation_render as _measurement_validation
import gene_annotation_episode.episodic_workflow.root.library.literature_compiled_assay_render as _compiled_assay
import gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_render as _ion_discrimination
import gene_annotation_episode.episodic_workflow.root.library.literature_endpoint_signal_render as _endpoint_signal
import gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_render as _summary_precision
import gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_render as _measurement_comparison
import gene_annotation_episode.episodic_workflow.root.library.literature_concentration_window_render as _concentration_window
from collections.abc import Mapping
from .literature_component_value_display import _kinetic_hidden_records, _optical_hidden_records
from .literature_text_values import _references

def _scientific_records(state):
    """Use authenticated host metadata when present; retain historical pure views."""
    display = state.get("literature_received_fact_display")
    if isinstance(display, Mapping):
        return dict(display.get("records", {}))
    working = state.get("working_state", {})
    return {row["id"]: row for field in
        ("terms", "references", "contexts", "observations", "hypotheses", "assessments")
        for row in working.get(field, ()) if isinstance(row, Mapping) and isinstance(row.get("id"), str)}


def _selected_records(state, lookup_results=()):
    """Resolve only references needed by assignment, last result or typed return."""
    records = _scientific_records(state)
    def possessed_links(value):
        # Parent forms choose their own field names. Their actual admitted
        # values can refer to a possessed record without an *_refs spelling.
        if isinstance(value, Mapping):
            for child in value.values():
                yield from possessed_links(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                yield from possessed_links(child)
        elif isinstance(value, str) and value in records:
            yield value
    pending = list(dict.fromkeys([
        *_references(state.get("literature_assignment", {})),
        *_references(state.get("last_local_outcome", {})),
        *_references(state.get("child_reports", ())),
        *_references(state.get("current_report_update", {})),
        *_references(state.get("literature_completed_work", ())),
        *state.get("current_report_basis_refs", ()),
        *_references(lookup_results),
        *possessed_links(state.get("child_reports", ())),
        *possessed_links(state.get("current_report_update", {})),
        *possessed_links(lookup_results),
    ]))
    # Numerical operand references preserve host custody in an amount return;
    # they do not request automatic exposure of the child's raw operand values.
    # Only a requested individual amount authorizes that role's expansion.
    hidden_amount_measurements = _unrequested_amount_measurements(state.get("child_reports", ()), records)
    hidden_optical = _optical_hidden_records(state.get("child_reports", ()), records)
    kinetic_reports = list(state.get("child_reports", ()))
    own_kinetic = _kinetic_model.own_rows((state.get("last_local_outcome") or {}).get("result", {}))
    if own_kinetic:
        kinetic_reports.append({"own_kinetic_model": own_kinetic})
    lookup_kinetic = list(_kinetic_model.rows_from_values(lookup_results))
    if lookup_kinetic:
        kinetic_reports.append({"requested_kinetic_model_lookup": lookup_kinetic})
    hidden_kinetic = _kinetic_hidden_records(kinetic_reports, records)
    interaction_reports = list(state.get("child_reports", ()))
    own_interaction = _interaction_model.own_rows((state.get("last_local_outcome") or {}).get("result", {}))
    model_rows = [*_interaction_model.rows_from_reports(interaction_reports), *own_interaction,
        *_interaction_model.rows_from_values(lookup_results)]
    hidden_interaction = (_interaction_hidden_records(interaction_reports, records)
        | _interaction_model.hidden_records(model_rows, records)
        | _interaction_model.hidden_results((state.get("last_local_outcome", {}), lookup_results), records))
    hidden_ratio_source = _ratio_source_hidden_records(state.get("child_reports", ()), records)
    from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_render import hidden_records as controlled_hidden_records, is_row as controlled_row
    controlled_reports = list(state.get("child_reports", ()))
    own = (state.get("last_local_outcome") or {}).get("result", {})
    if isinstance(own, Mapping) and isinstance(own.get("cells"), (tuple, list)) and all(controlled_row(row) for row in own["cells"]):
        controlled_reports.append({"own_controlled_components": own["cells"]})
    hidden_controlled = controlled_hidden_records(controlled_reports, records,
        bindings=state.get("literature_controlled_response_return_bindings"))
    from gene_annotation_episode.episodic_workflow.root.library.literature_gel_render import hidden_records as gel_hidden_records, is_row as gel_row
    gel_reports = list(state.get("child_reports", ()))
    own = (state.get("last_local_outcome") or {}).get("result", {})
    if isinstance(own, Mapping) and isinstance(own.get("cells"), (tuple, list)) and all(gel_row(row) for row in own["cells"]):
        gel_reports.append({"own_gel_components": own["cells"]})
    hidden_gel = gel_hidden_records(gel_reports, records,
        bindings=state.get("literature_gel_return_bindings"))
    native_rows = list(_native_rate.rows_from_reports(state.get("child_reports", ())))
    own = (state.get("last_local_outcome") or {}).get("result", {})
    native_rows.extend(_native_rate.own_rows(own, state.get("literature_rate_source_display", {}).get("cells", ())))
    domain_rows = list(_rate_domains.rows_from_reports(state.get("child_reports", ())))
    domain_rows.extend(_rate_domains.own_rows(own, state.get("literature_rate_source_domain_display", {}).get("cells", ())))
    native_rows.extend(_rate_domains.base_rows(domain_rows))
    meaning_rows = list(_rate_meanings.rows_from_reports(state.get("child_reports", ())))
    meaning_rows.extend(_rate_meanings.rows_from_values(lookup_results))
    meaning_rows.extend(_rate_meanings.own_rows(own, state.get("literature_rate_source_meaning_display", {}).get("cells", ())))
    native_rows.extend(_rate_domains.base_rows(_rate_meanings.base_rows(meaning_rows)))
    hidden_native_rate = _native_rate.hidden_records(native_rows)
    partition_rows = list(_product_partition.rows_from_values((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    hidden_partition = _product_partition.hidden_records(partition_rows)
    ion_rows = list(_ion_discrimination.rows_from_values((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    hidden_ion = _ion_discrimination.hidden_records(ion_rows, records)
    validation_rows = list(_measurement_validation.rows_from_values((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    hidden_validation = _measurement_validation.hidden_records(validation_rows, records)
    coupling_rows = list(_product_coupling.rows_from_values((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    hidden_coupling = _product_coupling.hidden_records(coupling_rows, records)
    common_rows = list(_compiled_assay.rows_from_values((state.get('last_local_outcome', {}),
        state.get('child_reports', ()), state.get('current_report_update', {}), lookup_results)))
    hidden_common = _compiled_assay.hidden_records(common_rows, records)
    grid_rows = list(_rate_observations.rows_from_values((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    hidden_grid = _rate_observations.hidden_grid_records(grid_rows, records)
    covariance_support = set(_covariance_support_refs((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results), records))
    endpoint_rows = list(_endpoint_signal.rows_from_values((state.get('last_local_outcome'),
        state.get('child_reports'), state.get('current_report_update'), lookup_results)))
    hidden_endpoint = _endpoint_signal.hidden_records(endpoint_rows, records, state.get('literature_endpoint_receipt_bindings'))
    summary_rows = list(_summary_precision.rows_from_values((state.get('last_local_outcome'),
        state.get('child_reports'), state.get('current_report_update'), lookup_results)))
    hidden_summary = _summary_precision.hidden_records(summary_rows, records, state.get('literature_summary_precision_receipt_bindings'))
    comparison_rows = list(_measurement_comparison.rows_from_values((state.get('last_local_outcome'),
        state.get('child_reports'), state.get('current_report_update'), lookup_results)))
    window_rows = list(_concentration_window.rows_from_values((state.get('last_local_outcome'),
        state.get('child_reports'), state.get('current_report_update'), lookup_results)))
    hidden_window = _concentration_window.hidden_records(window_rows, records,
        state.get('literature_concentration_window_receipt_bindings'))
    hidden_comparison = _measurement_comparison.hidden_records(comparison_rows, records,
        state.get('literature_measurement_comparison_receipt_bindings'))
    selected = {}
    for reference in pending:
        if reference in selected or reference not in records or reference in hidden_amount_measurements or reference in hidden_optical or reference in hidden_kinetic or reference in hidden_interaction or reference in hidden_ratio_source or reference in hidden_controlled or reference in hidden_gel or reference in hidden_native_rate or reference in hidden_partition or reference in hidden_ion or reference in hidden_validation or reference in hidden_coupling or reference in hidden_common or reference in hidden_grid or reference in hidden_endpoint or reference in hidden_summary or reference in hidden_comparison or reference in hidden_window:
            continue
        row = records[reference]
        if reference in covariance_support:
            # The selected support identity is returned, not its raw operands.
            # Exact anchors remain durable; source reading stays explicit.
            row = {**row, "anchor": None, "visual_anchor": None}
        selected[reference] = row
        pending.extend(ref for ref in _references(row) if ref not in selected)
    return list(selected.values())


def _unrequested_amount_measurements(reports, records):
    hidden, requested, associated = set(), set(), {}
    for report in reports:
        if not isinstance(report, Mapping):
            continue
        for rows in report.values():
            if not isinstance(rows, (list, tuple)):
                continue
            for row in rows:
                if not isinstance(row, Mapping) or row.get("evaluation_scope") != "source_amount_comparison":
                    continue
                for role in ("numerator", "denominator"):
                    quantity = row.get(role)
                    reference = quantity.get("measurement_ref") if isinstance(quantity, Mapping) else None
                    if isinstance(reference, str):
                        hidden.add(reference)
                        associated.setdefault(reference, set()).update(ref for field, ref in quantity.items()
                            if field.endswith("_ref") and isinstance(ref, str))
                        if row.get("component") == role + "_amount":
                            requested.add(reference)
    hidden -= requested
    result = set(hidden)
    for measurement in hidden:
        anchor = records.get(measurement, {}).get("anchor")
        if not isinstance(anchor, Mapping):
            continue
        for reference in associated.get(measurement, ()):
            candidate = records.get(reference, {}).get("anchor")
            if (isinstance(candidate, Mapping)
                    and all(candidate.get(key) == anchor.get(key) for key in ("source_ref", "artifact_ref"))
                    and type(candidate.get("start")) is int and type(candidate.get("end")) is int
                    and candidate["start"] <= anchor["start"] < anchor["end"] <= candidate["end"]):
                # A broad source-basis/identity witness can expose the same raw
                # operand too. Preserve its original host/typed reference, but
                # do not auto-expand that witness into the receiving prompt.
                result.add(reference)
    return result


_A106_COVARIANCE_FORMULAS = {
    "perturbation_mean_variance": "Va+Vb-2Cov_mean",
    "perturbation_variance_lower": "covariance_inequality_variance_bound",
    "perturbation_variance_upper": "covariance_inequality_variance_bound",
    "restoration_mean_variance": "Va+Vb-2Cov_mean",
    "restoration_variance_lower": "covariance_inequality_variance_bound",
    "restoration_variance_upper": "covariance_inequality_variance_bound",
    "shared_contrast_covariance": "Cov_WR-Cov_WK-Cov_KR+V_K",
}


def _covariance_support_refs(value, records):
    """Mask only authenticated A106 covariance support in recognized contracts."""
    def selected(row):
        for qualifier in row.get("covariance_interpretations", ()):
            if not isinstance(qualifier, Mapping):
                continue
            for reference in qualifier.get("support_refs", ()):
                record = records.get(reference)
                if (not isinstance(record, Mapping) or record.get("record_type") != "reference"
                        or record.get("origin") != "tool" or record.get("reference_type") != "literature_result"
                        or record.get("label") != "Covariance interpretation support"):
                    continue
                anchor = record.get("anchor")
                if not isinstance(anchor, Mapping) or any(name not in anchor for name in (
                        "source_ref", "artifact_ref", "start", "end", "quote")):
                    continue
                from gene_annotation_episode.domain import identity
                expected = identity("perturbation_literal", {"field": "covariance_support",
                    "first": qualifier.get("first"), "second": qualifier.get("second"), **dict(anchor)})
                if record.get("accession") == expected and record.get("source_ref") == anchor["source_ref"]:
                    yield reference
    if isinstance(value, Mapping):
        if value.get("evaluated_scope") == "interpreted_reference_perturbation":
            name = value.get("component")
            if (name in _A106_COVARIANCE_FORMULAS
                    and value.get("formula_code") == "perturbation_summary_" + name + "_v2"):
                yield from selected(value)
            cells = value.get("cells")
            if isinstance(cells, Mapping):
                for name, formula in _A106_COVARIANCE_FORMULAS.items():
                    row = cells.get(name)
                    if isinstance(row, Mapping) and row.get("formula") == formula:
                        yield from selected(row)
        for child in value.values():
            yield from _covariance_support_refs(child, records)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _covariance_support_refs(child, records)


