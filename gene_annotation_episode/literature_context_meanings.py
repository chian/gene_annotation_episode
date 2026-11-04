"""Source-supported meanings for the existing A108 numerical operands.

Keys align records internally. They are never scientific names. Unreported
definitions have distinct scoped handles, which assert no chemical identity,
biological support or independence. This is not a second numerical sheet.
"""
from copy import deepcopy

from .domain import identity
from .literature_assay_inputs import _fail, _keys

INPUT_VERSION = "a108_context_inputs_v2"
DATA_VERSION = "a108_source_context_measurements_v2"
RECORD_VERSION = "literature_context_record_v2"
NAMESPACE = "literature_context_semantic_cells"
REQUIREMENT_FIELDS = ("definition", "entity", "property", "biological_setting", "function_relation")
ROUTE_FIELDS = ("definition", "biological_setting", "function_relation", "membership_evidence", "joint_scope_evidence")


def witness_display_label(quote):
    """Bound display text; retain the complete exact witness in its anchor.

    Use the same preview convention as the existing native kinetic sheets.
    Paragraph evidence and multiline table spans remain valid source witnesses.
    """
    if len(quote) <= 512 and "\n" not in quote and "\r" not in quote:
        return quote
    prefix = "[source witness preview] "
    preview = " ".join(quote.split())
    available = 512 - len(prefix)
    if len(preview) > available:
        preview = preview[:available - 1] + "…"
    return prefix + preview


def read_meanings(value, inputs, sources):
    """Bind exact witnesses to the actual roster, including explicit unknowns."""
    _keys(value, ("requirements", "routes"), "meanings")
    result = {}
    for plural, fields in (("requirements", REQUIREMENT_FIELDS), ("routes", ROUTE_FIELDS)):
        roster = inputs[plural]
        entries = value[plural]
        if roster is None:
            if entries is not None:
                _fail("context_meaning_roster_mismatch", "meanings." + plural)
            result[plural] = None
            continue
        if not isinstance(entries, list) or len(entries) != len(roster):
            _fail("context_meaning_roster_mismatch", "meanings." + plural)
        by_key = {}
        for index, entry in enumerate(entries):
            path = f"meanings.{plural}[{index}]"
            _keys(entry, ("key", *fields), path)
            key = entry["key"]
            if not isinstance(key, str) or key in by_key:
                _fail("context_meaning_roster_mismatch", path + ".key")
            by_key[key] = {"key": key, **{field: None if entry[field] is None else
                sources.witness(entry[field], path + "." + field) for field in fields}}
        if set(by_key) != {entry["key"] for entry in roster}:
            _fail("context_meaning_roster_mismatch", "meanings." + plural)
        result[plural] = [by_key[entry["key"]] for entry in roster]
    return result


def direct_references(arguments, extraction, initial):
    """Recover the exact selected witness sources without reading source bytes."""
    refs = list(initial)
    if extraction.get("version") == INPUT_VERSION:
        for plural, fields in (("requirements", REQUIREMENT_FIELDS), ("routes", ROUTE_FIELDS)):
            for entry in extraction["meanings"][plural] or ():
                refs.extend(entry[field]["source_ref"] for field in fields if entry[field] is not None)
    return list(dict.fromkeys(refs))


def publish_meanings(extraction, publish):
    """Publish actual anchored meanings and distinct non-evidentiary handles."""
    data_ref = extraction["arguments"]["data_source_ref"] or extraction["arguments"]["source_ref"]
    result = {}
    for plural, fields in (("requirements", REQUIREMENT_FIELDS), ("routes", ROUTE_FIELDS)):
        if extraction["meanings"][plural] is None:
            result[plural] = None
            continue
        rows = []
        for entry in extraction["meanings"][plural]:
            scoped = {"data_source_ref": data_ref, "kind": plural, "key": entry["key"]}
            row = {}
            for field in fields:
                witness = entry[field]
                if field == "definition":
                    continue
                ref_field = field + "_ref"
                if witness is None:
                    row[ref_field] = None
                    continue
                anchor = {k: witness[k] for k in ("source_ref", "artifact_ref", "start", "end", "quote")}
                common = {"source_ref": witness["source_ref"], "anchor": anchor}
                accession = identity("context_literal", {**scoped, "field": field, **anchor})
                if field == "biological_setting":
                    record = {**common, "context_type": "environment", "name": witness_display_label(witness["quote"]),
                              "attributes": [], "related_refs": []}
                    row[ref_field] = publish("context", record)
                elif field.endswith("_evidence"):
                    record = {**common, "reference_type": "literature_result", "accession": accession,
                        "label": witness_display_label(witness["quote"]), "sequence_ref": None, "molecule": None,
                        "length": None, "term_refs": [], "context_refs": []}
                    row[ref_field] = publish("reference", record)
                else:
                    row[ref_field] = publish("term", {**common, "namespace": "literature_context_" + field,
                        "accession": accession, "label": witness_display_label(witness["quote"]), "term_type": "other"})
            witness = entry["definition"]
            anchor = None if witness is None else {k: witness[k] for k in (
                "source_ref", "artifact_ref", "start", "end", "quote")}
            noun = "requirement" if plural == "requirements" else "route"
            row[noun + "_ref"] = publish("reference", {
                "reference_type": "literature_result", "source_ref": data_ref if witness is None else witness["source_ref"],
                "accession": identity("context_literal", {**scoped, "field": "definition"}),
                "label": "Unreported " + noun + " definition" if witness is None else witness_display_label(witness["quote"]),
                "sequence_ref": None, "molecule": None, "length": None,
                "term_refs": [row[f + "_ref"] for f in ("entity", "property", "function_relation")
                              if row.get(f + "_ref") is not None],
                "context_refs": [] if row.get("biological_setting_ref") is None else [row["biological_setting_ref"]],
                "anchor": anchor})
            row["definition_reported"] = witness is not None
            rows.append(row)
        result[plural] = rows
    return result


def semantic_metadata(metadata, bindings):
    result = deepcopy(metadata)
    for index, entry in enumerate(result["requirement_definitions"]):
        entry.update(deepcopy(bindings["requirements"][index]))
    for index, entry in enumerate(result["route_definitions"] or ()):
        entry.update(deepcopy(bindings["routes"][index]))
        entry["requirement_refs"] = [bindings["requirements"][member]["requirement_ref"]
                                     for member in entry["requirements"]]
    return result


def binding_references(bindings):
    return list(dict.fromkeys(value for rows in bindings.values() for row in rows or ()
        for field, value in row.items() if field.endswith("_ref") and value is not None))
