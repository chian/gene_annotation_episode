from .literature_rate_domain_return_schema import rate_source_domain_cells_schema

def is_row(value):
    from collections.abc import Mapping
    from jsonschema import Draft202012Validator
    # Use a module-level cache assigned lazily to avoid the storage import cycle.
    global _domain_row_validator
    if "_domain_row_validator" not in globals():
        _domain_row_validator = Draft202012Validator(rate_source_domain_cells_schema()["items"])
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    return isinstance(value, Mapping) and _domain_row_validator.is_valid(plain(value))



def base_rows(rows):
    """Validate exact new rows before presenting their original native fields."""
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.episodic_workflow.root.communication import plain
    result = []
    for row in rows:
        if not is_row(row):
            raise ContractError("literature_rate_domain_display_contract_mismatch")
        result.append({key: plain(value) for key, value in row.items() if key != "reported_domain"})
    return result



def rows_from_reports(reports):
    from collections.abc import Mapping
    for report in reports:
        if isinstance(report, Mapping):
            for rows in report.values():
                if isinstance(rows, (list, tuple)) and rows and all(is_row(row) for row in rows):
                    yield from rows



def hidden_records(rows):
    from .literature_rate_source_render import hidden_records as native_hidden_records
    return native_hidden_records(base_rows(rows))



def own_rows(content, display_rows):
    from .literature_rate_source_render import own_rows as native_own_rows
    display_rows = list(display_rows)
    matched = {(row["sheet_ref"], row["component"]) for row in native_own_rows(content, base_rows(display_rows))}
    return [row for row in display_rows if (row["sheet_ref"], row["component"]) in matched]



def render_received(parts, rows, records, *, section, table, comparison_number=None):
    from .literature_rate_source_render import render_received as native_render_received
    rows = list(rows)
    if not rows:
        return
    native_render_received(parts, base_rows(rows), records, section=section, table=table,
        comparison_number=comparison_number)
    render_domains(parts, rows, section=section, table=table)



def render_domains(parts, rows, *, section, table):
    """Only actually returned domain fields, after their common base is shown."""
    from .literature_rate_source_render import _COMPONENTS
    rows = list(rows)
    base_rows(rows)
    section(parts, "Reported-operand numerical domains",
        "Conditional logical enclosures of the reported operands with the recorded endpoint, normalization and units. "
        "Outward projection marks numerical rounding; approximation remains separate. These are not sampling confidence intervals "
        "or evidence of independence or endpoint co-attainability. Status above concerns the point estimate.")
    section(parts, "Requested reported domains", table(
        ("Component", "Domain kind", "Lower", "Lower inclusive", "Upper", "Upper inclusive", "Numerical projection", "Basis", "Conditioning", "Failure"),
        ((_COMPONENTS[row["component"]], *(row["reported_domain"][field] for field in
          ("kind", "lower", "lower_inclusive", "upper", "upper_inclusive", "projection", "basis", "conditioning", "failure"))) for row in rows)))

