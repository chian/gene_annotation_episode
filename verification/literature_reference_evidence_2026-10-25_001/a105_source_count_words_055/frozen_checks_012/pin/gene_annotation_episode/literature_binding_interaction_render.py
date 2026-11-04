"""Mechanical display and numerical-label masking for admitted binding rows.

These functions copy already admitted values and do not supply scientific TASK
instructions. Custody remains in the immutable saved selection and references;
masking automatic label expansion never revokes explicit source access.
"""
from collections.abc import Mapping

SCOPE = "source_binding_discrimination_interaction"


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report, Mapping):
            for values in report.values():
                if isinstance(values, (list, tuple)):
                    yield from (row for row in values if isinstance(row, Mapping) and row.get("evaluation_scope") == SCOPE)


def _refs(value):
    if isinstance(value, Mapping):
        for v in value.values():
            yield from _refs(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from _refs(v)
    elif isinstance(value, str) and value.startswith(("reference_", "source_", "context_", "term_")):
        yield value


def _numeric_locations(rows):
    return [token for row in rows for role in row.get("roles", {}).values() for token in role.get("numeric_locations", ())]


def overlaps_numbers(record, locations, witness_location=None):
    """Mask overlapping/broad labels; unknown locations fall back per source."""
    anchor = record.get("anchor")
    visual = record.get("visual_anchor")
    source = witness_location["source_ref"] if witness_location else anchor.get("source_ref") if isinstance(anchor, Mapping) else record.get("source_ref")
    for token in locations:
        if token.get("source_ref") != source:
            continue
        if token.get("kind") == "unresolved":
            return True
        if token.get("kind") == "utf8_span":
            if isinstance(anchor, Mapping):
                start, end = anchor.get("start"), anchor.get("end")
                if isinstance(start, int) and isinstance(end, int) and start < token["end"] and token["start"] < end:
                    return True
            elif anchor is None:
                # No authenticated span bounds a label on this numeric source.
                return True
        elif token.get("kind") == "image_region":
            if witness_location and witness_location["kind"] == "image_region":
                region = witness_location["region"]
            elif isinstance(visual, Mapping):
                region = visual.get("region")
            else:
                return True
            if not isinstance(region, (list, tuple)) or len(region) != 4:
                return True
            a, b = token["region"], region
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                return True
    return False


def hidden_records(reports, records):
    rows = list(rows_from_reports(reports))
    locations = _numeric_locations(rows)
    return {ref for row in rows for ref in _refs(row)} | {
        ref for ref, record in records.items() if overlaps_numbers(record, locations)}


def render_received(parts, rows, records, *, section, table, values):
    locations = _numeric_locations(rows)
    known_locations = {v["canonical_witness_ref"]: v.get("canonical_witness_location") for row in rows for role in row["roles"].values()
        for v in [*role["definitions"].values(), role["physical_fit"]] if v["canonical_witness_ref"]}
    def label(reference):
        record = records.get(reference)
        if record is None or overlaps_numbers(record, locations, known_locations.get(reference)):
            return "source-bound witness retained for scoped access"
        return record.get("label", record.get("name", "source-bound witness retained for scoped access"))
    section(parts, "Admitted requested binding interaction components", table(
        ("Component", "Value", "Threshold", "Unit", "Relation", "Status", "Unavailable reason"),
        ((r["component"], r["value"], r["threshold"], r["unit"], r["relation"], r["status"], r["unavailable_reason"]) for r in rows)))
    first = rows[0]
    section(parts, "Binding interaction source interpretation", values({k: first[k] for k in (
        "comparison_scope", "calculation_input_status", "model_input_status", "model_reader_capability")}))
    section(parts, "Binding parameter meaning", table(("Meaning", "Interpretation", "Status"),
        [("common parameter", first["common_parameter_kind"]["value"], first["common_parameter_kind"]["status"])] +
        [(k, v["value"], v["status"]) for k, v in first["relationships"].items()]))
    for role, metadata in first["roles"].items():
        section(parts, role.replace("_", " ") + " meaning", values({k: metadata[k] for k in (
            "selection_status", "parse_status", "unavailable_reasons")}))
        section(parts, "Source definitions", table(("Meaning", "Status", "Source witness"),
            ((k, v["status"], label(v["canonical_witness_ref"]) if v["canonical_witness_ref"] else "unknown")
                for k, v in metadata["definitions"].items())))
        section(parts, "Selected role parameter kind", values(metadata["parameter_kind"]["value"]))
        section(parts, "Selected source unit reading", table(("Status", "Source witness"),
            [(metadata["unit"]["status"], "; ".join(label(ref) for ref in metadata["unit"]["candidate_refs"]))]))
        uncertainty = metadata["uncertainty"]
        section(parts, "Source uncertainty meanings", table(("Meaning", "Interpretation", "Status"),
            ((k, v["value"], v["status"]) for k, v in uncertainty["meanings"].items())))
        section(parts, "Source uncertainty reading status", values({k: uncertainty[k] for k in (
            "selection_status", "reported_spread_status", "unavailable_reasons")}))
        requested = next((r["roles"][role]["values"] for r in rows if r["roles"][role]["values"]["delivery_status"] == "requested"), None)
        if requested is not None:
            section(parts, role.replace("_", " ") + " requested raw values", values(requested))
