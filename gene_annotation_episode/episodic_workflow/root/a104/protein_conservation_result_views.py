"""Literal text views of the one closed ordinary conservation contract.

Only declared provenance slots are omitted. Headers, symbols, values and caller
population labels remain literal even when they resemble control addresses.
This module reads no files and performs no scientific calculation.
"""
from collections.abc import Mapping
import json

from .protein_conservation_result_contracts import (
    PACKET_VERSION, validate_conservation_public_value, validate_conservation_return,
)


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def select_protein_conservation_values(value):
    """Recognize a complete Value/Return, never infer a family from row shape."""
    if not isinstance(value, Mapping) or value.get("version") != PACKET_VERSION:
        return None
    try:
        value = _plain(value)
        validator = validate_conservation_return if "source_ref" in value else validate_conservation_public_value
        return validator(value)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        return None


def _literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _cell(value):
    return _literal(value).replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")


def _table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)])


def _section(parts, title, text):
    parts.extend(["", title, "", text])


def _quantity_rows(name, value):
    if value is None:
        return [(name, None, None, None, None, None, None, None, None, None, None)]
    return [(name, value["value"], value["state"], value["unit"], value["origin"],
        value["numerator"], value["denominator"], value["population_ref"], value["method"],
        value["requirement_ids"], ["retained quantity evidence" for _ in value["evidence"]])]


_QUANTITY_HEADERS = ("Quantity", "Literal value", "State", "Unit", "Origin", "Numerator operand",
    "Denominator operand", "Semantic population", "Method", "Requirement codes", "Evidence roles")


def render_protein_conservation_result(value, number=1):
    """Display copied native rows and derived sites, including empty views."""
    packet = select_protein_conservation_values(value)
    if packet is None:
        raise ValueError("protein_conservation_presentation_value_invalid")
    context = packet["context"]
    parts = ["Selected molecular result " + str(number), "",
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet.get("source_ref")),
            ("Operation", "analyze_protein_conservation"),
            ("Selected native rows and calculated sites", packet["selection"]),
            ("Scientific population request", context["population_request"]),
            ("Population resolution", context["population_resolution"])]), "",
        "Native alignment rows are predicted correspondence from the selected alignment output. "
        "Literal-site conservation is derived from the explicitly selected output-row population. "
        "Its denominator includes every selected literal symbol, including gaps, ambiguity and case-distinct characters. "
        "These fractions are not functional confidence."]
    execution = context["native_execution"]
    _section(parts, "Native process, output capture and parser states", _table(
        ("Recorded property", "Supplied value"), [
            ("Native process state", execution["state"]), ("Native return code", execution["returncode"]),
            ("Reported version (self report)", execution["reported_version"]),
            ("Native alphabet qualification", execution["alphabet"]),
            ("Output capture extent", execution["output_capture"]),
            ("Parser status", execution["parser_status"])]))
    alignment = context["alignment"]
    _section(parts, "Retained alignment dimensions", "null" if alignment is None else _table(
        ("Property", "Supplied value"), [(key, alignment[key]) for key in
            ("format", "layout", "id_rule", "encoding", "declared_row_count", "declared_column_count",
             "observed_row_count", "observed_column_count", "completeness")]))
    population = context["population"]
    _section(parts, "Resolved scientific population", "null" if population is None else _table(
        ("Property", "Supplied value"), [
            ("Semantic label", context["population_request"]["label"]),
            ("Original output-row indices", population["row_indices"]),
            ("Selected alignment columns (zero based)", population["columns_0based"]),
            ("Population completeness", population["completeness"])]))
    _section(parts, "Literal conservation convention and qualifications", _table(
        ("Property", "Supplied value"), [
            ("Convention", context["convention"]), ("Threshold comparison", context["threshold"]),
            ("Separate display rounding", context["display"]),
            ("Source-row order for modal ties", context["ordered_source_row_indices"])]))
    parts.extend(["", "Modal ties use the first actual output-row index in the retained selected population. "
        "The strict unrounded fraction > 0.8 comparison precedes the separate two-decimal display."])
    _section(parts, "Scientific population quantities", _table(_QUANTITY_HEADERS,
        [*_quantity_rows("member_count", context["member_count"]),
         *_quantity_rows("site_count", context["site_count"])]))
    _section(parts, "Native-row and site display record accounting", _table(
        ("Record family", "Retained records", "Selected records", "Returned records", "Omitted records"),
        [(name, row["retained_record_count"], row["selected_record_count"],
            row["returned_record_count"], row["omitted_record_count"])
            for name, row in packet["accounting"].items()]))
    parts.extend(["", "Display record counts and the scientific member/site quantities describe distinct populations. "
        "Null remains unknown; an explicitly empty view does not make the scientific population zero."])
    native_rows = [(row["row_index"], row["raw_header"], row["member_label"], row["sequence"],
        {key: item for key, item in row["source_location"].items() if key != "artifact"})
        for row in packet["native_rows"]]
    _section(parts, "Selected native alignment rows (literal case and symbols)", _table(
        ("Original output-row index", "Raw header", "Member label", "Literal aligned sequence",
            "Original byte/line location"), native_rows) if native_rows else "[]")
    _section(parts, "Selected literal conservation sites", _table(
        ("Alignment column (zero based)", "Literal symbol counts", "Modal symbol",
            "First actual source-row index", "Strict unrounded > 0.8"),
        [(row["column_0based"], row["symbol_counts"], row["modal_symbol"],
            row["modal_first_source_row_index"], row["strict_gt_0_8"]) for row in packet["sites"]])
        if packet["sites"] else "[]")
    for site in packet["sites"]:
        rows = []
        for name in ("modal_count", "majority_fraction", "displayed_2dp_fraction"):
            rows.extend(_quantity_rows(name, site[name]))
        _section(parts, "Retained quantities for column " + str(site["column_0based"]),
            _table(_QUANTITY_HEADERS, rows))
    input_record = context["input"]
    _section(parts, "Original input representation", "null" if input_record is None else _table(
        ("Property", "Supplied value"), [
            ("Selected input namespace", input_record["selection"]["namespace"]),
            ("Input Source association", None if input_record["source_ref"] is None else "received input Source"),
            ("File format", input_record["file"]["format"]),
            ("Retained input bytes", input_record["file"]["size_bytes"]),
            ("Input capture extent", input_record["capture"]),
            ("Header catalog state", input_record["records_state"]), ("Input issues", input_record["issues"])]))
    if input_record is not None:
        _section(parts, "Original input header occurrences", _table(
            ("Original record ordinal", "Literal header", "Byte start", "Byte end", "State", "Issues"),
            [(row["record_ordinal"], row["header"], row["byte_start"], row["byte_end"],
                row["status"], row["issues"]) for row in input_record["records"]])
            if input_record["records"] else "[]")
    _section(parts, "Literal full-header associations (not biological identity)", _table(
        ("Association property", "Supplied value"), [
            ("Catalog state", context["row_associations"]["state"]),
            ("Output-row / input-occurrence relationships", context["row_associations"]["rows"]),
            ("Unmatched input record ordinals", context["row_associations"]["unmatched_input_record_ordinals"])]))
    issues = context["issues"]
    _section(parts, "Retained issues and qualifications", _table(
        ("Code", "Phase", "Severity", "Evidence roles"),
        [(row["code"], row["phase"], row["severity"], ["retained diagnostic evidence" for _ in row["evidence_refs"]])
            for row in issues]) if issues else "[]")
    return "\n".join(parts)


def render_protein_conservation_results(values):
    return "\n\n".join(render_protein_conservation_result(value, number)
        for number, value in enumerate(values, 1))


__all__ = ["select_protein_conservation_values", "render_protein_conservation_result",
    "render_protein_conservation_results"]
