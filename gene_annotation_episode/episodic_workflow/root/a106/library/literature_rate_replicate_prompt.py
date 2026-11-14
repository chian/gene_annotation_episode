"""Recurring scientific instructions and pure rendering of requested raw cells."""
from collections.abc import Mapping


RATE_REPLICATE_TASK = """Evaluate the raw rate measurements for the actual source molecule, experiment and selected reference/test groups. Read the retained table's subject, experiment, arm, condition, endpoint, normalization, native unit, value or limit, sampling-unit identity, physical-measurement identity, sampling basis and value origin. Use the explicit mapped CSV/TSV operation only when those fields are present; it is not an arbitrary publisher-table parser. A selected group name without matching rows is a requested comparison, not a measured source fact.

Distinguish repeated readings within one experimental unit from different units and from independent biological preparations. Average technical readings within each unit before comparing equally weighted unit means. Repeated representations of the same physical measurement are not new measurements; conflicting uses of one measurement identity must remain visible. Equal values do not establish duplication, and matching unit labels alone do not establish independence. Preserve both groups' actual counts and sampling bases.

Determine whether the selected units form matched pairs, independent groups, or an unknown dependence structure from experimental meaning. Choose IID-unit or IID-pair assumptions only when justified; these are conditional models, not consequences of row grouping. Preserve descriptive variability separately from the conditional uncertainty of a mean or difference. Missing, censored and nondetected measurements remain in the actual measurement roster and do not become zero or silently disappear. Retain useful observed-point and unaffected-unit summaries in the saved sheet while leaving incomplete full-set components unavailable.

Compare like endpoints, normalization and compatible rate units. Preserve usable individual group results when a cross-group contrast is unavailable. A rate, retained fraction, SD or conditional SE describes the selected measurement evidence; it does not establish product specificity, molecular attribution, assay error rates, a function probability or annotation credit. Return exactly the requested saved components with their actual source meanings, repetition basis, limitations and selected statistical conditions; do not expand unrequested numerical summaries."""

RATE_REPLICATE_OPERATION_DESCRIPTION = "Read explicitly mapped retained raw-rate CSV/TSV measurements from an actually received source. Select exact subject/experiment and reference/test groups, unit model and dependence; source bytes supply all measured numbers. Technical readings first average within actual units, then unit means receive equal weight. Preserve actual measurement/unit counts, sampling bases, duplicate/conflicting identities and missing/censored partials. SD is descriptive; SE is conditional on the selected design. This finite raw-table operation does not parse arbitrary publisher layouts or supply assay specificity, error rates, target transfer or annotation credit."


def is_row(row):
    return isinstance(row, Mapping) and row.get("evaluation_scope") == "source_raw_rate_replicates" and "component" in row


def rows_from_values(value):
    if is_row(value):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from rows_from_values(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (tuple, list)):
                    yield from (row for row in values if is_row(row))


def render_received(parts, rows, *, section, table):
    comparisons = {}
    for row in rows:
        comparisons.setdefault(row["sheet_ref"], []).append(row)
    for comparison in comparisons.values():
        _render_comparison(parts, comparison, section=section, table=table)


def _render_comparison(parts, rows, *, section, table):
    if not rows:
        return
    first = rows[0]
    section(parts, "Requested raw rate replicate components", table(
        ("Component", "Value", "Unit", "Status", "Unavailable reason", "Statistical conditions", "Origin", "Approximate"),
        ((row["component"], row["value"], row["unit"], row["status"], row["unavailable_reason"],
          ", ".join(row["conditional_on"]), ", ".join(row["input_origins"]), row["approximate"]) for row in rows)))
    section(parts, "Actual measured subject and experiment", table(("Subject", "Experiment", "Unit model", "Across-group dependence"),
        [(first["observed_subject"], first["observed_experiment"], first["unit_model"], first["dependence"])]))
    selected = []
    for role, group in first["groups"].items():
        selection = group["selection"]
        selected.append((role, group["status"], *(selection[field] for field in ("arm", "condition", "endpoint", "normalization"))))
    section(parts, "Requested groups and observed status", table(("Role", "Source status", "Arm", "Condition", "Endpoint", "Normalization"), selected))
    section(parts, "Observed repetition basis and actual counts", table(
        ("Role", "Sampling basis", "Physical measurements", "Representations", "Distinct units", "Complete units"),
        ((role, group["observed"]["sampling_basis"], group["observed"]["measurement_count"], group["observed"]["representation_count"],
          group["observed"]["sampling_unit_count"], group["observed"]["complete_unit_count"])
         for role, group in first["groups"].items() if group["observed"] is not None)))
    section(parts, "Actual units and measurement limitations", table(
        ("Role", "Unit", "Sampling basis", "Physical measurements", "Observed points", "Representations", "Complete", "Conflicting identity", "Limitations"),
        ((role, unit["sampling_unit"], unit["sampling_basis"], unit["measurement_count"], unit["point_count"],
          unit["representation_count"], unit["complete"], unit["conflicting_identity"], ", ".join(unit["limitations"]))
         for role, group in first["groups"].items() if group["observed"] is not None for unit in group["observed"]["units"])))
    section(parts, "Observed unit pairing", table(("Shared units", "Reference-only units", "Test-only units"),
        [tuple(", ".join(first["pairing"][field]) for field in ("shared_units", "reference_only", "test_only"))]))
    section(parts, "Requested calculation meanings", table(("Component", "Calculation"),
        ((row["component"], row["formula"]) for row in rows)))
