"""Original supplied-state literature component value display; no runtime ownership selection."""
from . import literature_kinetic_model_display as _kinetic_model
from collections.abc import Mapping
from .literature_text_values import _pick, _references, _section, _table, _values

def _covariance_meanings(parts, rows, records):
    records = records or {}
    rendered = []
    for row in rows:
        for covariance in row.get("covariance_interpretations", ()):
            support = []
            for reference in covariance["support_refs"]:
                record = records.get(reference)
                support.append(record.get("label", "anchored source support") if isinstance(record, Mapping)
                    else "meaning unavailable in the received scientific records")
            rendered.append((row["component"], covariance["first"] + "," + covariance["second"],
                covariance["selection"], covariance["kind"], covariance["interpretation_basis"] or "unreported",
                covariance["variance_status"], covariance["use"], "; ".join(support) or "none supplied"))
    if rendered:
        _section(parts, "Selected covariance meanings", _table(("Component", "Arm pair", "Selection",
            "Covariance kind", "Interpretation basis", "Variance status", "Component use", "Source support"), rendered))


def _structure_endpoint(selector):
    if not isinstance(selector, Mapping):
        return "unknown"
    atoms = ",".join(selector.get("atom_names", ()))
    insertion = selector.get("insertion_code") or "none"
    return (f"{selector.get('auth_chain')} {selector.get('comp_id')}{selector.get('auth_seq_id')} "
        f"insertion={insertion} alt={selector.get('alt_id')}" + (f" atoms={atoms}" if atoms else ""))


def _amount_metadata(parts, content):
    """Render requested amount meanings, not private numerical operands."""
    quantities = content.get("quantity_metadata")
    if not isinstance(quantities, Mapping):
        return
    _section(parts, "Source amount comparison meaning", _values(_pick(content, (
        "comparison_kind", "pair_relationship", "stock_relationship", "variance_status",
        "covariance_origin", "mass_factor_applied_to_rate"))))
    _section(parts, "Numerator and denominator meanings", _table(("Quantity", "Amount role", "Amount basis",
        "Basis relationship", "Qualification", "Approximate", "Subject", "Preparation", "Stock", "Method", "Reported basis", "Condition", "Uncertainty kind"), (
            (role, row.get("amount_role"), row.get("amount_kind"), row.get("basis_status"), row.get("qualification"), row.get("approximate"),
             row.get("subject_ref"), row.get("preparation_ref"), row.get("stock_ref"), row.get("method_ref"),
             row.get("reported_basis_ref"), row.get("condition_ref"), row.get("reported_uncertainty_kind"))
            for role, row in quantities.items())))


def _structure_definitions(parts, content):
    """Render received scientific selectors/criteria, without coordinate dumps."""
    geometry = content.get("geometry_definition")
    if isinstance(geometry, (list, tuple)):
        _section(parts, "Declared geometry panel; fixed denominator " + str(len(geometry)),
            _table(("Member", "Endpoint A", "Endpoint B", "Supporting distance ≤ Å", "Incompatible distance ≥ Å"),
                ((i, _structure_endpoint(row.get("endpoint_a")), _structure_endpoint(row.get("endpoint_b")),
                  row.get("positive_max_A"), row.get("incompatible_min_A")) for i, row in enumerate(geometry))))
    local = content.get("local_validation_definition")
    if isinstance(local, (list, tuple)):
        _section(parts, "Declared local validation panel; fixed denominator " + str(len(local)),
            _table(("Member", "Residue selector"), ((i, _structure_endpoint(row)) for i, row in enumerate(local))))


def _optical_rows(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (list, tuple)):
                    yield from (row for row in values if isinstance(row, Mapping)
                        and row.get("evaluation_scope") == "source_nadh_depletion_endpoint")


def _contains_optical_token(record, tokens):
    anchor = record.get("anchor") if isinstance(record, Mapping) else None
    return isinstance(anchor, Mapping) and any(
        all(anchor.get(key) == token.get(key) for key in ("source_ref", "artifact_ref"))
        and type(anchor.get("start")) is int and type(anchor.get("end")) is int
        and anchor["start"] < token["end"] and token["start"] < anchor["end"] for token in tokens)


def _optical_unknown_token_sources(rows, records):
    """Off-page anchors permit withholding only their declared optical source."""
    result = set()
    for row in rows:
        for quantity in row.get("operands", {}).values():
            if not isinstance(quantity, Mapping):
                continue
            ref = quantity.get("measurement_ref")
            source = quantity.get("measurement_source_ref")
            if (ref is not None and isinstance(source, str)
                    and (ref not in records or not isinstance(records[ref].get("anchor"), Mapping))):
                result.add(source)
    return result


def _optical_hidden_records(reports, records):
    """Typed refs preserve custody; automatic expansion does not expose operands.

    Suppress all optical binding records from the generic record renderer; the
    dedicated optical view resolves safe scientific labels without host IDs.
    Any reachable broad anchored record containing a numerical operand is also
    hidden, even when it is not itself an optical binding.
    """
    rows = list(_optical_rows(reports))
    refs = {ref for row in rows for ref in _references(row)}
    measurements = {quantity.get("measurement_ref") for row in rows
        for quantity in row.get("operands", {}).values() if isinstance(quantity, Mapping)}
    tokens = [records[ref]["anchor"] for ref in measurements if ref in records
        and isinstance(records[ref].get("anchor"), Mapping)]
    unknown_sources = _optical_unknown_token_sources(rows, records)
    return refs | {ref for ref, record in records.items() if _contains_optical_token(record, tokens)
        or isinstance(record.get("anchor"), Mapping) and record["anchor"].get("source_ref") in unknown_sources}


def _optical_received(parts, rows, records):
    """Render requested optical numbers and definitions, never raw operands."""
    first = rows[0]
    measurements = {q.get("measurement_ref") for q in first.get("operands", {}).values() if isinstance(q, Mapping)}
    tokens = [records[ref]["anchor"] for ref in measurements if ref in records
        and isinstance(records[ref].get("anchor"), Mapping)]
    unknown_sources = _optical_unknown_token_sources(rows, records)
    def label(reference):
        if reference is None:
            return "unknown"
        record = records.get(reference)
        if (record is None or _contains_optical_token(record, tokens)
                or isinstance(record.get("anchor"), Mapping) and record["anchor"].get("source_ref") in unknown_sources):
            return "source-bound witness retained for scoped access"
        return record.get("label", record.get("name", "source-bound witness retained for scoped access"))
    units = {"uM2/min2": "(uM/min)^2", "mM_inverse_cm_inverse": "mM^-1 cm^-1"}
    _section(parts, "Admitted requested optical endpoint inputs", _table(
        ("Component", "Value", "Unit", "Status", "Unavailable reason", "Origin"),
        ((row.get("component"), row.get("value"), units.get(row.get("unit"), row.get("unit")),
          row.get("status"), row.get("unavailable_reason"), row.get("origin")) for row in rows)))
    _section(parts, "Optical endpoint and source meaning", _values(_pick(first, (
        "evaluation_scope", "endpoint_kind", "endpoint_assignment", "source_kind", "source_origin"))))
    _section(parts, "Optical source subject and conditions", _table(("Meaning", "Source definition", "Unavailable reason"),
        ((name, label(row.get("ref")), row.get("unavailable_reason")) for name, row in first.get("context", {}).items())))
    _section(parts, "Selected optical relationships", _table(("Meaning", "Selected value"),
        ((name, row.get("value")) for name, row in first.get("interpretations", {}).items())))
    _section(parts, "Optical covariance meaning", _values(_pick(first.get("covariance", {}),
        ("status", "origin", "unavailable_reason"))))
    operands = first.get("operands", {})
    def reuse(name, row):
        local = row.get("local_reuse_ref")
        if local is None:
            return "unknown identity"
        shared = [role for role, other in operands.items() if other.get("local_reuse_ref") == local]
        return ("shared local observation: " + ", ".join(shared) if len(shared) > 1
            else "local custody group; independence unknown")
    _section(parts, "Optical operand meanings; numerical operands retained for scoped access", _table(
        ("Role", "Input status", "Source status", "Source unit dimension", "Qualification", "Approximate",
         "Reported relation", "Source origin", "Converted origin", "Known reuse", "Physical identity",
         "Condition", "Measured entity", "Interval", "Unavailable inputs"),
        ((name, row.get("input_status"), row.get("observation_status"), units.get(row.get("canonical_unit"), row.get("canonical_unit")),
          row.get("qualification"), row.get("approximate"), row.get("observed_relation"),
          row.get("source_origin"), row.get("converted_origin"), reuse(name, row),
          "source identity supplied" if row.get("physical_observation_ref") else "unreported",
          label(row.get("condition_ref")), label(row.get("measured_entity_ref")), label(row.get("interval_ref")),
          ", ".join(row.get("input_unavailable_reasons", ()))) for name, row in operands.items())))
    formulas = {"nadh_extinction_net_rate": "q = -1000*(sample slope - matched blank slope)/(epsilon*path length)",
        "first_order_nadh_extinction_variance": "Vq = J covariance J-transpose; first-order propagation with source-owned primitive order"}
    _section(parts, "Requested optical calculation definitions", _table(("Component", "Meaning"),
        ((row.get("component"), formulas.get(row.get("formula_code"), "unknown")) for row in rows)))


def _kinetic_rows(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (list, tuple)):
                    yield from (row for row in values if isinstance(row, Mapping)
                        and row.get("evaluation_scope") == "source_kinetic_parameter_contrast")


def _kinetic_token_state(rows, records):
    tokens, unknown_sources = [], set()
    for row in rows:
        if _kinetic_model.is_row(row):
            # These exact locations come from authenticated saved witnesses.
            # Alias records overlapping that support cannot expand its private
            # covariance numbers through a different label or reference ID.
            tokens.extend(row.get("model_support_locations", ()))
        for role in ("numerator", "denominator"):
            for token in row.get(role, {}).get("numeric_tokens", ()):
                reference, source = token.get("ref"), token.get("source_ref")
                anchor = records.get(reference, {}).get("anchor")
                if isinstance(anchor, Mapping):
                    tokens.append(anchor)
                elif isinstance(source, str):
                    unknown_sources.add(source)
    return tokens, unknown_sources


def _kinetic_hidden_records(reports, records):
    rows = list(_kinetic_rows(reports))
    tokens, unknown_sources = _kinetic_token_state(rows, records)
    return {ref for row in rows for ref in _references(row)} | {
        ref for ref, record in records.items() if _contains_optical_token(record, tokens)
        or isinstance(record.get("anchor"), Mapping) and record["anchor"].get("source_ref") in unknown_sources}


def _kinetic_received(parts, rows, records):
    tokens, unknown_sources = _kinetic_token_state(rows, records)
    units = {"uM_inverse_min_inverse": "uM^-1 min^-1"}
    def label(reference):
        if reference is None:
            return "unknown"
        record = records.get(reference)
        if (record is None or _contains_optical_token(record, tokens)
                or isinstance(record.get("anchor"), Mapping) and record["anchor"].get("source_ref") in unknown_sources):
            return "source-bound witness retained for scoped access"
        return record.get("label", record.get("name", "source-bound witness retained for scoped access"))
    first = rows[0]
    _section(parts, "Admitted requested kinetic parameter components", _table(
        ("Component", "Value", "Unit", "Status", "Reported relation", "Threshold", "Approximate", "Unavailable reason", "Origin"),
        ((r.get("component"), r.get("value"), units.get(r.get("unit"), r.get("unit")), r.get("status"), r.get("relation"),
          r.get("threshold"), r.get("approximate"), r.get("unavailable_reason"), r.get("origin")) for r in rows)))
    _section(parts, "Kinetic comparison meaning", _values(_pick(first,
        ("evaluation_scope", "contrast_meaning", "model_input_status", "model_reader_capability"))))
    _section(parts, "Selected kinetic experimental relationships", _table(("Meaning", "Selected interpretation"),
        ((k, v.get("value")) for k, v in first.get("comparison", {}).items())))
    for role in ("numerator", "denominator"):
        metadata = first.get(role, {})
        _section(parts, role.capitalize() + " kinetic parameter meaning", _values(_pick(metadata,
            ("parameter_kind", "canonical_unit", "qualification", "approximate", "input_status", "observed_relation",
             "source_origin", "converted_origin", "input_unavailable_reasons"))))
        _section(parts, role.capitalize() + " source subject and experimental context", _table(
            ("Meaning", "Source definition"), ((k, label(reference)) for group in ("subject", "context")
                for k, reference in metadata.get(group, {}).items())))
        _section(parts, role.capitalize() + " source observation identity", _table(
            ("Meaning", "Source definition"), (("physical observation", label(metadata.get("physical_observation_ref"))),)))
        _section(parts, role.capitalize() + " reported uncertainty meaning", _values(_pick(metadata.get("uncertainty", {}),
            ("statistic", "canonical_unit", "repetition_basis", "estimate_basis", "unavailable_reason",
             "count_reading_status", "count_unavailable_reason", "count_notation", "count_relation", "count_approximate"))))
        requested = next((r.get(role, {}).get("uncertainty_values", {}) for r in rows
            if r.get("component") == role + "_parameter"), None)
        if requested is not None:
            _section(parts, role.capitalize() + " requested source uncertainty", _values(requested))
    definitions = {
        "kinetic_numerator_parameter": "the selected numerator parameter in its canonical unit",
        "kinetic_denominator_parameter": "the selected denominator parameter in its canonical unit",
        "kinetic_parameter_difference": "numerator parameter minus denominator parameter",
        "kinetic_parameter_ratio": "numerator parameter divided by denominator parameter",
        "kinetic_log_parameter_contrast": "natural log of numerator parameter minus natural log of denominator parameter",
    }
    from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_model_metadata import FORMULA_MEANINGS as model_definitions
    definitions.update(model_definitions)
    _section(parts, "Requested kinetic calculation definitions", _table(("Component", "Meaning"),
        ((r.get("component"), definitions.get(r.get("formula_code"), "unknown")) for r in rows)))


