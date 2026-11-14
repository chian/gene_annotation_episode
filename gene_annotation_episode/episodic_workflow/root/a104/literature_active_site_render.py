"""Pure rendering of exactly possessed active-site amount rows."""
from collections.abc import Mapping
from fractions import Fraction
from functools import lru_cache

from jsonschema import Draft202012Validator
from .communication import plain
from .literature_active_site_storage import active_site_cells_schema
from .literature_active_site_calculations import COMPONENTS


@lru_cache(maxsize=1)
def _validator():
    return Draft202012Validator(active_site_cells_schema()["items"])


def is_row(value):
    return (isinstance(value, Mapping) and value.get("evaluation_scope") == "active_site_titration_amount"
        and value.get("component") in COMPONENTS and _validator().is_valid(plain(value)))


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
            for rows in report.values():
                if isinstance(rows, (list, tuple)) and rows and all(is_row(row) for row in rows):
                    yield from rows


def meaning(value):
    return value["witness"]["quote"] if value["status"] == "selected" else value["status"].replace("_", " ")


def _domain(row):
    domain = row["exact_domain"]
    if domain is None:
        return "unknown"
    def edge(value, missing):
        return str(Fraction(int(value["numerator"]), int(value["denominator"]))) if value else missing
    lower, upper = edge(domain["lower"], "-infinity"), edge(domain["upper"], "infinity")
    return lower if lower == upper else ("[" if domain["lower_inclusive"] else "(") + lower + ", " + upper + ("]" if domain["upper_inclusive"] else ")")


def render_received(parts, rows, *, section, table):
    rows = list(rows)
    if not rows:
        return
    if not all(is_row(row) for row in rows):
        raise ValueError("active_site_display_contract_mismatch")
    section(parts, "Requested active-site titration amount components", table(
        ("Component", "Value", "Reported logical domain", "Unit", "Status", "Approximate", "Origin", "Unavailable reason", "Declared conditioning"),
        ((row["component"], row["value"], _domain(row), row["unit"], row["status"], row["approximate"], row["origin"], row["unavailable_reason"], "; ".join(row["conditional_on"])) for row in rows)))
    for row in rows:
        context = [("Experiment", meaning(row["experiment"])), ("Intended change", meaning(row["intended_change"])),
            ("Other changes", " ; ".join(meaning(value) for value in row["other_changes"]) or "none selected"),
            ("Rate application", row["rate_application_status"]),
            ("Full fraction uncertainty", row["fraction_uncertainty"]["reason"] + "; " + row["fraction_uncertainty"]["input_state"])]
        context.extend((field, value["value"] + ": " + " ; ".join(meaning(w) for w in value["support"])) for field, value in row["interpretations"].items())
        for operand in row["operands"]:
            context.extend((operand["role"] + " " + field, meaning(value)) for field, value in operand["meanings"].items())
            for field in ("kind", "sampling_basis"):
                value = operand["reported_uncertainty"][field]
                context.append((operand["role"] + " uncertainty " + field, value["value"] + ": " + " ; ".join(meaning(w) for w in value["support"])))
            context.append((operand["role"] + " source uncertainty", meaning(operand["reported_uncertainty"]["statement"])))
            for label, reading in (("source amount", operand["reading"]), ("source spread", operand["reported_uncertainty"]["reading"])):
                if reading:
                    context.append((operand["role"] + " " + label, reading["number"]["quote"] + " " + (reading["raw_unit"] or "unit unreported") + "; " + reading["bound"]))
        section(parts, "Active-site scientific meanings for " + row["component"], table(("Aspect", "Source meaning"), context))
    section(parts, "Active-site amount interpretation limits", "The density is sites per total monomer; calling it an active monomer fraction requires the source one-site interpretation. The raw density domain stays unchanged; the biological fraction explicitly intersects it with physical [0,1], with an empty intersection unavailable. "
        "Nominal titrant concentration is not an independently standardized active titrant concentration, and chemical purity does not supply an active molar correction. "
        "The reciprocal is a conditional change of physical denominator and is never applied here to a rate. Already active-normalized rates must not be corrected again. "
        "Source regression SD does not establish SEM, preparation CV or full joint uncertainty. Reported limits are logical enclosures, not sampling intervals. "
        "These dependent numerical components do not establish an overall reliability, isolated tag effect or annotation credit.")
