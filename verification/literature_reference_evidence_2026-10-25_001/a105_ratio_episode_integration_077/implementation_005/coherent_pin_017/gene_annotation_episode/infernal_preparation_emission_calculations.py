"""Saved-data cmemit composition and validation, independent of acquisition.

All counts describe generated output. GC uses G+C over A+C+G+T+U; ambiguity
does not enter that denominator. Gap fraction uses literal gap symbols divided
by actual known alignment columns. Missing symbols (~ or ?) are neither gaps
nor residues. A2M compact insertion layouts have no asserted full-column ratio.
No composition quantity is a probability of biological function.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from .infernal_preparation_emission import COMPONENT_NAMES, ROW_FIELDS, SEQUENCE_VALUE_NAMES
from .infernal_preparation_schema import (
    check, field_input, issue, new_calculations, validate_common_sheet, value,
)


ISSUE_CODES = frozenset({"cmemit_saved_counts_inconsistent", "cmemit_saved_digest_inconsistent",
    "cmemit_zero_canonical_denominator", "cmemit_zero_column_denominator",
    "cmemit_saved_alignment_geometry_invalid", "cmemit_saved_annotation_geometry_invalid"})
CHECK_NAMES = frozenset({"cmemit_counts_consistent", "cmemit_residue_digest_matches",
    "cmemit_model_association", "cmemit_output_capture_complete", "cmemit_model_population_complete",
    "cmemit_sequence_count_matches", "cmemit_alphabet_matches", "cmemit_embedding_interval_valid",
    "cmemit_embedding_length_matches", "cmemit_sample_index_matches", "cmemit_generated_name_matches",
    "cmemit_alignment_geometry", "cmemit_annotation_geometry", "cmemit_trace_decoded"})
_UNITS = {"residue_count": "nt", "canonical_count": "nt", "gc_count": "nt", "ambiguity_count": "nt",
    "gc_fraction_canonical": "fraction", "gc_denominator": "nt", "gap_count": "column", "column_count": "column",
    "gap_fraction": "fraction", "row_count": "count", "expected_sequence_count": "count", "actual_sequence_count": "count",
    "score_bits": "bit", "structure_score_bits": "bit"}
_RESIDUES = frozenset("ACGTURYKMSWBDHVNX")
_GAPS = frozenset("-._")


def _components():
    return {name: value(state="not_measured", basis="derived", unit=_UNITS[name]) for name in sorted(COMPONENT_NAMES)}


def _problem(result, code, row, field, severity="error"):
    result["issues"].append(issue(code, stage="calculation", severity=severity,
        artifact_ref=row["locator"]["artifact_ref"], record_key=row["record_key"], field=field))


def _cell(row, field, *, component=None):
    source = row["values"][field]
    return value(source["value"], state=source["state"], basis="derived", unit=_UNITS[component or field],
                 inputs=[field_input(row["locator"], "values." + field)])


def _ratio(result, row, components, numerator, denominator, target, zero_code):
    a, b = components[numerator], components[denominator]
    inputs = a["inputs"] + b["inputs"]
    if a["state"] != "present" or b["state"] != "present":
        state = next((s for s in ("invalid", "failed", "truncated", "incompatible", "missing", "not_measured")
                      if s in {a["state"], b["state"]}), "missing")
        components[target] = value(state=state, basis="derived", unit="fraction", inputs=inputs)
    elif b["value"] == 0:
        components[target] = value(state="not_measured", basis="derived", unit="fraction", inputs=inputs)
        _problem(result, zero_code, row, denominator, "information")
    else:
        components[target] = value(a["value"] / b["value"], basis="derived", unit="fraction", inputs=inputs)


def _validate_sheet(sheet):
    validate_common_sheet(sheet)
    if sheet["operation"]["program"] != "cmemit":
        raise ValueError("cmemit_program_required")
    keys = []
    for row in sheet["input_records"]:
        if row.get("kind") != "model":
            raise ValueError("cmemit_input_model_required")
        keys.append(row["record_key"])
    for row in sheet["native_rows"]:
        if (row.get("kind") != "generated_trace" or set(row) != ROW_FIELDS["generated_trace"] or
            row["trace_family"] not in {"cm_parsetree", "hmm_trace"} or
            set(row["values"]) != {"score_bits", "structure_score_bits"} or
            type(row["model_keys"]) is not list or type(row["sequence_keys"]) is not list):
            raise ValueError("cmemit_saved_trace_invalid")
        if row["name"] is not None and type(row["name"]) is not str:
            raise ValueError("cmemit_saved_trace_name_invalid")
        for cell in row["values"].values():
            if cell["unit"] != "bit":
                raise ValueError("cmemit_saved_trace_unit_invalid")
        keys.append(row["record_key"])
    for row in sheet["output_records"]:
        kind = row.get("kind")
        if kind not in {"generated_sequence", "generated_alignment"} or set(row) != ROW_FIELDS[kind]:
            raise ValueError("cmemit_saved_row_fields_invalid")
        keys.append(row["record_key"])
        if type(row["model_keys"]) is not list or any(type(k) is not str for k in row["model_keys"]):
            raise ValueError("cmemit_saved_model_keys_invalid")
        if row["origin"] not in {"generated_sample", "generated_consensus"}:
            raise ValueError("cmemit_generated_origin_required")
        if kind == "generated_sequence":
            if set(row["values"]) != SEQUENCE_VALUE_NAMES or type(row["sequence"]) is not str or type(row["name"]) is not str:
                raise ValueError("cmemit_saved_sequence_invalid")
            if row["sample_index"] is not None and (type(row["sample_index"]) is not int or row["sample_index"] < 1):
                raise ValueError("cmemit_saved_sample_index_invalid")
            interval = row["embedded_interval"]
            if interval is not None and (type(interval) is not dict or set(interval) != {"start", "end"} or
                any(type(v) is not int for v in interval.values()) or interval["start"] < 0 or interval["end"] <= interval["start"]):
                raise ValueError("cmemit_saved_interval_invalid")
        else:
            if set(row["values"]) != {"row_count", "column_count"} or set(row["annotations"]) != {"gf", "gs", "gr", "gc"}:
                raise ValueError("cmemit_saved_alignment_invalid")
            if type(row["sequence_keys"]) is not list:
                raise ValueError("cmemit_saved_members_invalid")
            for family, annotations in row["annotations"].items():
                if type(annotations) is not list:
                    raise ValueError("cmemit_saved_annotations_invalid")
                for ann in annotations:
                    if set(ann) != {"tag", "value", "name", "locator", "block_index", "sequence_key"} or any(
                        type(ann[k]) is not str for k in ("tag", "value")):
                        raise ValueError("cmemit_saved_annotation_invalid")
                    if ann["block_index"] is not None and (type(ann["block_index"]) is not int or ann["block_index"] < 0):
                        raise ValueError("cmemit_saved_annotation_block_invalid")
                    if family in {"gf", "gc"} and (ann["name"] is not None or ann["sequence_key"] is not None):
                        raise ValueError("cmemit_saved_annotation_association_invalid")
        for name, cell in row["values"].items():
            if cell["unit"] != _UNITS[name] or cell["state"] == "present" and (type(cell["value"]) is not int or cell["value"] < 0):
                raise ValueError("cmemit_saved_count_invalid")
    if len(keys) != len(set(keys)):
        raise ValueError("cmemit_saved_duplicate_record_key")
    model_keys = {r["record_key"] for r in sheet["input_records"]}
    outputs = {r["record_key"]: r for r in [*sheet["output_records"], *sheet["native_rows"]]}
    for row in sheet["native_rows"]:
        if set(row["model_keys"]) - model_keys:
            raise ValueError("cmemit_saved_model_reference_unknown")
        for key in row["sequence_keys"]:
            if (key not in outputs or outputs[key]["kind"] != "generated_sequence" or
                outputs[key]["model_keys"] != row["model_keys"]):
                raise ValueError("cmemit_saved_trace_reference_invalid")
    for row in sheet["output_records"]:
        if set(row["model_keys"]) - model_keys:
            raise ValueError("cmemit_saved_model_reference_unknown")
        if row["kind"] == "generated_sequence" and row["alignment_key"] is not None:
            parent = outputs.get(row["alignment_key"])
            if parent is None or parent["kind"] != "generated_alignment" or row["record_key"] not in parent["sequence_keys"]:
                raise ValueError("cmemit_saved_alignment_reference_invalid")
        if row["kind"] == "generated_alignment":
            if len(row["sequence_keys"]) != len(set(row["sequence_keys"])):
                raise ValueError("cmemit_saved_duplicate_member")
            for key in row["sequence_keys"]:
                member = outputs.get(key)
                if member is None or member["kind"] != "generated_sequence" or member["alignment_key"] != row["record_key"]:
                    raise ValueError("cmemit_saved_sequence_reference_invalid")
            for family in ("gs", "gr"):
                for ann in row["annotations"][family]:
                    if ann["sequence_key"] is not None and (ann["sequence_key"] not in row["sequence_keys"] or
                        outputs[ann["sequence_key"]]["name"] != ann["name"]):
                        raise ValueError("cmemit_saved_annotation_reference_invalid")
    for rel in sheet["associations"]:
        if rel["relation"] != "generated_from" or set(rel["input_keys"]) - model_keys or set(rel["output_keys"]) - outputs.keys():
            raise ValueError("cmemit_saved_association_invalid")
        if rel["status"] == "validated" and (len(rel["input_keys"]) != 1 or any(
            outputs[k]["model_keys"] != rel["input_keys"] for k in rel["output_keys"])):
            raise ValueError("cmemit_saved_association_conflict")


def _issue_check(sheet, row, name, codes, *, applicable=True):
    if not applicable:
        return check(name, "not_applicable")
    relevant = [i for i in sheet["issues"] if i["code"] in codes and
                (i["record_key"] == row["record_key"] or i["record_key"] is None)]
    return check(name, "fail" if relevant else "pass", [field_input(row["locator"], "sequence")])


def _association_check(sheet, row):
    relations = [r for r in sheet["associations"] if row["record_key"] in r["output_keys"]]
    status = "pass" if relations and all(r["status"] == "validated" for r in relations) else (
        "fail" if any(r["status"] == "conflicting" for r in relations) else "unknown")
    return check("cmemit_model_association", status, [field_input(row["locator"], "model_keys")])


def _sequence_components(sheet, result, row, components, checks):
    sequence = row["sequence"]
    upper = sequence.upper()
    actual = {"residue_count": sum(c in _RESIDUES for c in upper),
              "canonical_count": sum(c in "ACGTU" for c in upper), "gc_count": sum(c in "GC" for c in upper),
              "ambiguity_count": sum(c in _RESIDUES - set("ACGTU") for c in upper),
              "gap_count": sum(c in _GAPS for c in sequence), "column_count": len(sequence)}
    consistent, have = True, False
    for name in SEQUENCE_VALUE_NAMES:
        components[name] = _cell(row, name)
        if row["values"][name]["state"] == "present":
            have = True
            if row["values"][name]["value"] != actual[name]:
                consistent = False
                components[name] = value(state="invalid", basis="derived", unit=_UNITS[name],
                                          inputs=components[name]["inputs"])
                _problem(result, "cmemit_saved_counts_inconsistent", row, name)
    checks.append(check("cmemit_counts_consistent", "pass" if consistent and have else "fail" if not consistent else "unknown",
                        [field_input(row["locator"], "sequence")]))
    residue = "".join(c for c in upper if c in _RESIDUES)
    digest_valid = row["residue_sha256"] is not None and hashlib.sha256(residue.encode("ascii")).hexdigest() == row["residue_sha256"]
    checks.append(check("cmemit_residue_digest_matches", "pass" if digest_valid else "unknown" if row["residue_sha256"] is None else "fail",
                        [field_input(row["locator"], "sequence")]))
    if row["residue_sha256"] is not None and not digest_valid:
        _problem(result, "cmemit_saved_digest_inconsistent", row, "residue_sha256")
    components["gc_denominator"] = deepcopy(components["canonical_count"])
    _ratio(result, row, components, "gc_count", "gc_denominator", "gc_fraction_canonical", "cmemit_zero_canonical_denominator")
    _ratio(result, row, components, "gap_count", "column_count", "gap_fraction", "cmemit_zero_column_denominator")
    components["actual_sequence_count"] = value(1, basis="derived", inputs=[field_input(row["locator"], "record_key")])
    settings = sheet["operation"]["settings"]
    checks.extend([
        _issue_check(sheet, row, "cmemit_alphabet_matches", {"cmemit_alphabet_conflict"}, applicable=row["alphabet"] is not None),
        _issue_check(sheet, row, "cmemit_embedding_interval_valid", {"cmemit_embedding_interval_invalid"}, applicable="-e" in settings),
        _issue_check(sheet, row, "cmemit_embedding_length_matches", {"cmemit_embedding_length_mismatch"}, applicable="-e" in settings),
        _issue_check(sheet, row, "cmemit_sample_index_matches", {"cmemit_sample_index_invalid"}, applicable=sheet["operation"]["mode"] != "consensus"),
        _issue_check(sheet, row, "cmemit_generated_name_matches", {"cmemit_name_invalid"}),
    ])
    # Revalidate saved relationships from their actual retained data. Extraction
    # issues are preserved evidence, not the sole authority for recalculation.
    by_check = {c["check"]: c for c in checks}
    selected = "DNA" if settings.get("--dna") else "RNA" if settings.get("--rna") else None
    alphabet_bad = ({"U", "T"} <= set(upper) or row["alphabet"] == "DNA" and "U" in upper or
                    row["alphabet"] == "RNA" and "T" in upper or selected is not None and
                    (selected == "DNA" and "U" in upper or selected == "RNA" and "T" in upper))
    if alphabet_bad:
        by_check["cmemit_alphabet_matches"]["outcome"] = "fail"
    if "-e" in settings:
        interval = row["embedded_interval"]
        match = re.fullmatch(r"(.+)/(\d+)-(\d+)", row["name"])
        interval_ok = (interval is not None and match is not None and
            interval == {"start": int(match[2])-1, "end": int(match[3])} and
            0 <= interval["start"] < interval["end"] <= actual["residue_count"] and
            (not settings.get("--u5p") or interval["start"] == 0) and
            (not settings.get("--u3p") or interval["end"] == settings["-e"]))
        by_check["cmemit_embedding_interval_valid"]["outcome"] = "pass" if interval_ok else "fail"
        if components["residue_count"]["state"] == "present":
            by_check["cmemit_embedding_length_matches"]["outcome"] = "pass" if actual["residue_count"] == settings["-e"] else "fail"
    # Unresolved sample identities and partial sequences cannot pass a test by
    # merely having no extraction error attached to their nullable fields.
    for c in checks:
        if c["check"] == "cmemit_sample_index_matches" and row["sample_index"] is None and c["outcome"] == "pass":
            c["outcome"] = "unknown"
        if (c["check"] in {"cmemit_embedding_length_matches", "cmemit_embedding_interval_valid"} and
                row["values"]["residue_count"]["state"] != "present" and c["outcome"] == "pass"):
            c["outcome"] = "unknown"


def _alignment_components(sheet, result, row, components, checks):
    members = [r for r in sheet["output_records"] if r["record_key"] in row["sequence_keys"]]
    components["row_count"] = _cell(row, "row_count")
    components["column_count"] = _cell(row, "column_count")
    components["actual_sequence_count"] = value(len(members), basis="derived", inputs=[field_input(row["locator"], "sequence_keys")])
    col = row["values"]["column_count"]
    if col["state"] == "present":
        valid = all(len(r["sequence"]) == col["value"] for r in members)
        outcome = "pass" if valid else "fail"
    else:
        valid, outcome = False, "fail" if col["state"] == "invalid" else "unknown"
    if row["values"]["row_count"]["value"] != len(members):
        outcome = "fail"
    if outcome == "fail":
        _problem(result, "cmemit_saved_alignment_geometry_invalid", row, "column_count")
    checks.append(check("cmemit_alignment_geometry", outcome, [field_input(row["locator"], "sequence_keys")]))
    if row["format"] not in {"stockholm", "pfam"}:
        checks.append(check("cmemit_annotation_geometry", "not_applicable"))
    else:
        extraction_bad = any(i["record_key"] == row["record_key"] and i["code"] in {
            "cmemit_annotation_geometry_invalid", "cmemit_malformed_annotation", "cmemit_annotation_association_ambiguous"}
            for i in sheet["issues"])
        groups = {}
        for family in ("gr", "gc"):
            for annotation in row["annotations"][family]:
                key = (family, annotation["name"], annotation["tag"])
                groups.setdefault(key, []).append(annotation)
        good = not extraction_bad
        for annotations in groups.values():
            blocks = [a["block_index"] for a in annotations]
            good &= None not in blocks and len(set(blocks)) == len(blocks)
            if col["state"] == "present":
                good &= sum(len(a["value"]) for a in annotations) == col["value"]
        outcome = "fail" if not good else "pass" if valid and groups else "unknown"
        if not good:
            _problem(result, "cmemit_saved_annotation_geometry_invalid", row, "annotations")
        checks.append(check("cmemit_annotation_geometry", outcome, [field_input(row["locator"], "annotations")]))


def calculate_cmemit_components(sheet, *, parameters):
    """Calculate named generated-data quantities from a saved sheet alone.

    No formula parameters are currently needed; nonempty parameters are rejected
    rather than silently ignored. Original sheet and its observations are not
    mutated. Each model row carries expected and validated actual sample counts;
    each alignment carries its row count; each sequence carries composition.
    """
    if type(parameters) is not dict or parameters:
        raise ValueError("cmemit_parameters_must_be_empty")
    _validate_sheet(sheet)
    result = new_calculations(sheet["operation"], parameters)
    settings, mode = sheet["operation"]["settings"], sheet["operation"]["mode"]
    artifacts = {a["artifact_ref"]: a for a in sheet["artifacts"]}
    sequences = [r for r in sheet["output_records"] if r["kind"] == "generated_sequence"]
    output_artifacts = [a for a in sheet["artifacts"] if a["role"] in {"generated_sequences", "generated_alignment"}]
    population_known = not any(i["code"] == "cmemit_model_population_incomplete" for i in sheet["issues"])
    n = 1 if mode == "consensus" else settings.get("-N")
    expected = n if population_known and type(n) is int and n > 0 else None
    for row in [*sheet["input_records"], *sheet["output_records"], *sheet["native_rows"]]:
        components, checks = _components(), []
        reference = [field_input(row["locator"], "record_key")]
        kind = row["kind"]
        if kind == "generated_sequence":
            _sequence_components(sheet, result, row, components, checks)
        elif kind == "generated_alignment":
            _alignment_components(sheet, result, row, components, checks)
        elif kind == "generated_trace":
            for name in ("score_bits", "structure_score_bits"):
                # These remain reported native header values, including their
                # original printed precision, rather than a recalculated score.
                components[name] = deepcopy(row["values"][name])
            checks.append(check("cmemit_trace_decoded", "unknown", reference))
        else:
            contributing = [a for a in sheet["associations"] if a["input_keys"] == [row["record_key"]]
                            and any(k == s["record_key"] for k in a["output_keys"] for s in sequences)]
            uncertain = any(a["status"] != "validated" for a in contributing) or any(
                a["status"] != "validated" and (not a["input_keys"] or row["record_key"] in a["input_keys"])
                for a in sheet["associations"] if any(k == s["record_key"] for k in a["output_keys"] for s in sequences))
            count = sum(s["model_keys"] == [row["record_key"]] for s in sequences)
            invalid_output = any(i["code"] in {"cmemit_format_incompatible", "cmemit_text_encoding_invalid",
                "cmemit_payload_digest_mismatch", "cmemit_fasta_header_missing", "cmemit_phylip_header_invalid"} for i in sheet["issues"])
            state = "missing" if uncertain else "invalid" if invalid_output else "present"
            components["actual_sequence_count"] = value(count if state == "present" else None, state=state,
                basis="derived", inputs=[field_input(s["locator"], "model_keys") for s in sequences] or reference)
            checks.append(check("cmemit_model_population_complete", "pass" if population_known else "unknown", reference))
        if kind in {"model", "generated_alignment"}:
            valid_association = kind == "model" or _association_check(sheet, row)["outcome"] == "pass"
            components["expected_sequence_count"] = value(expected if valid_association else None, basis="derived", inputs=reference)
            a, b = components["actual_sequence_count"], components["expected_sequence_count"]
            capture_complete = bool(output_artifacts) and all(a["completeness"] == "complete" for a in output_artifacts)
            outcome = "unknown" if not capture_complete or a["state"] != "present" or b["state"] != "present" else (
                "pass" if a["value"] == b["value"] else "fail")
            checks.append(check("cmemit_sequence_count_matches", outcome, a["inputs"] + b["inputs"]))
        if kind != "model":
            checks.append(_association_check(sheet, row))
            capture = artifacts[row["locator"]["artifact_ref"]]["completeness"]
            checks.append(check("cmemit_output_capture_complete", "pass" if capture == "complete" else "unknown", reference))
        result["rows"].append({"record_key": row["record_key"], "components": components, "checks": checks})
    return result


__all__ = ["calculate_cmemit_components", "ROW_FIELDS", "COMPONENT_NAMES", "ISSUE_CODES", "CHECK_NAMES"]
