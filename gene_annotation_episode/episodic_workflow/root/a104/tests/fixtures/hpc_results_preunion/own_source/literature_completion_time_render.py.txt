"""Pure rendering of exactly possessed completion-time component rows."""
from collections.abc import Mapping
from fractions import Fraction
from functools import lru_cache

from jsonschema import Draft202012Validator
from .communication import plain
from .literature_completion_time_storage import completion_time_cells_schema


@lru_cache(maxsize=1)
def _validator():
    return Draft202012Validator(completion_time_cells_schema()["items"])


def is_row(value):
    return (isinstance(value, Mapping)
        and value.get("evaluation_scope") == "source_preparation_completion_time"
        and value.get("component") in ("numerator_time", "denominator_time", "completion_time_ratio", "inverse_completion_time_ratio")
        and _validator().is_valid(plain(value)))


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
            for value in report.values():
                if isinstance(value, (list, tuple)) and value and all(is_row(row) for row in value):
                    yield from value


def meaning(value):
    return value["witness"]["quote"] if value["status"] == "selected" else value["status"].replace("_", " ")


def _edge(value):
    return str(Fraction(int(value["numerator"]), int(value["denominator"]))) if value else None


def _domain(row):
    d = row["exact_domain"]
    if d is None:
        return "unknown"
    lower, upper = _edge(d["lower"]), _edge(d["upper"])
    if lower == upper and lower is not None:
        return lower
    return ("[" if d["lower_inclusive"] else "(") + (lower if lower is not None else "-infinity") + ", " + (
        upper if upper is not None else "infinity") + ("]" if d["upper_inclusive"] else ")")


def render_received(parts, rows, *, section, table):
    rows = list(rows)
    if not rows:
        return
    if not all(is_row(row) for row in rows):
        raise ValueError("completion_time_display_contract_mismatch")
    section(parts, "Requested preparation completion-time components", table(
        ("Component", "Value", "Reported logical domain", "Unit", "Status", "Approximate", "Origin", "Unavailable reason"),
        ((row["component"], row["value"], _domain(row), row["unit"], row["status"], row["approximate"],
          row["origin"], row["unavailable_reason"]) for row in rows)))
    # Definitions accompany each row: different returned comparisons must not
    # silently inherit the first row's experimental relationship.
    for row in rows:
        section(parts, "Completion-time experimental meanings for " + row["component"], table(
            ("Aspect", "Source meaning"), [
                ("Experiment", meaning(row["experiment"])), ("Intended change", meaning(row["intended_change"])),
                ("Other changes", " ; ".join(meaning(value) for value in row["other_changes"]) or "none selected"),
                *[(field, value["value"] + ": " + " ; ".join(meaning(w) for w in value["support"]))
                    for field, value in row["comparison"].items()],
                *[(operand["role"] + " " + field, meaning(value)) for operand in row["operands"]
                    for field, value in operand["meanings"].items()],
                *[(operand["role"] + " source qualification", operand["qualification"]["value"] + ": " +
                    " ; ".join(meaning(w) for w in operand["qualification"]["support"])) for operand in row["operands"]],
                *[(operand["role"] + " reported time", operand["reading"]["number"]["quote"] + " " +
                    (operand["reading"]["raw_unit"] or "unit unreported") + "; " + operand["reading"]["bound"])
                    for operand in row["operands"] if operand["reading"] is not None],
            ]))
    section(parts, "Completion-time comparison limits",
        "Strictly positive physical times condition these logical domains; they are not sampling confidence intervals. "
        "The ratio and its inverse are dependent comparisons of preparation endpoint times. "
        "They do not establish molecular activity retention, intrinsic rate, contaminant fraction, effect isolation or annotation credit. "
        "Protocol differences and unknown retained molecule amounts remain explicit limitations.")
