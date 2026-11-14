"""Populate a Rfam numerical sheet from supplied native JSON and identities.

All original rows survive, including duplicate or malformed rows. Native bytes
are retained by the caller at ``capture.artifact_ref``; this reader checks their
digest and never fetches, submits, executes, sleeps, or parses a CM display.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
import re

from .domain import ContractError
from .rfam_batch_contracts import (
    RFAM_ALIGNMENT_FIELDS, RFAM_ALIGNMENT_COUNT_FIELDS,
    RfamBatchInputIdentity, RfamArtifactCapture, RfamModelMetadataBundle,
    RfamAlignmentComponents, RfamParseResult, closed_object, finite_json_copy,
    is_int, is_number, is_sha256, is_text, json_pointer_token, make_issue,
    rfam_digest, validate_rfam_alignment_result, validate_rfam_capture,
    validate_rfam_input_identity)


_FORMAT = "rfam_cmscan_single_json_v1"
_ALIGNMENT_METRICS = ("display_model_from", "display_model_to", "represented_model_positions",
    "model_consensus_equal_count", "model_consensus_compared_count", "model_consensus_equal_fraction")
_FORMAT_FIELDS = ("native_program", "native_program_version", "rfam_release", "search_space_nt",
    "searched_model_count", "reporting_thresholds", "inclusion_thresholds", "native_model_mode")


def _result(status, issues, *, sheet=None, format="unrecognized"):
    return {"version": "rfam_batch_parse_result_v1", "status": status,
            "format": format, "sheet": sheet, "issues": deepcopy(issues)}


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("rfam_json_duplicate_key")
        value[key] = item
    return value


def _invalid_constant(value):
    raise ContractError("rfam_json_invalid")


def _native_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise ContractError("rfam_json_invalid")
    # Preserve a positive native quantity too small for float as unavailable,
    # never as an observed zero. Its exact numeric token stays in raw bytes.
    return token if value == 0 and Decimal(token) != 0 else value


def _metadata_bundle(value, issues):
    if value is None:
        return None
    code = "rfam_model_metadata_conflict"
    try:
        value = finite_json_copy(value, code=code)
        closed_object(value, ("version", "records", "bindings"), code=code)
        if value["version"] != "rfam_model_metadata_v1" or type(value["records"]) is not list or type(value["bindings"]) is not list:
            raise ContractError(code)
        for record in value["records"]:
            closed_object(record, ("metadata_ref", "accession", "model_name", "model_length_positions",
                "model_sha256", "model_release", "source_ref"), code=code)
            if (not is_text(record["metadata_ref"]) or not is_text(record["source_ref"])
                    or record["accession"] is not None and (type(record["accession"]) is not str or re.fullmatch(r"RF[0-9]{5}", record["accession"]) is None)
                    or record["model_length_positions"] is not None and not is_int(record["model_length_positions"], minimum=1)
                    or record["model_sha256"] is not None and not is_sha256(record["model_sha256"])
                    or any(record[k] is not None and not is_text(record[k]) for k in ("model_name", "model_release"))):
                raise ContractError(code)
        for binding in value["bindings"]:
            closed_object(binding, ("hit_key", "metadata_ref", "basis", "evidence_source_ref", "evidence_json_pointer"), code=code)
            if (binding["basis"] not in ("native_model_sha256", "native_model_release")
                    or any(not is_text(binding[k]) for k in ("hit_key", "metadata_ref", "evidence_source_ref", "evidence_json_pointer"))):
                raise ContractError(code)
    except ContractError:
        issues.append(make_issue(code, "metadata", field="model_metadata"))
        return None
    return value


def _alignment_index(bundle, capture, expected_keys, issues):
    if bundle is None:
        return {}, False
    code = "rfam_alignment_binding_conflict"
    try:
        bundle = finite_json_copy(bundle, code=code)
        closed_object(bundle, ("version", "artifact_ref", "source_sha256", "rows"), code=code)
        if (bundle["version"] != "rfam_alignment_components_bundle_v1"
                or bundle["artifact_ref"] != capture["artifact_ref"]
                or bundle["source_sha256"] != capture["source_sha256"] or type(bundle["rows"]) is not list):
            raise ContractError(code)
        index = {}
        for row in bundle["rows"]:
            key = row.get("hit_key") if type(row) is dict else None
            if not is_text(key) or key in index or key not in expected_keys:
                raise ContractError(code)
            index[key] = row
        return index, False
    except ContractError:
        issues.append(make_issue(code, "alignment", field="alignment_components"))
        return {}, True


def _attach_alignment(row, supplied, raw, identity, capture, bundle_invalid):
    missing = row["missing"]
    pointer, key = row["native_json_pointer"], row["hit_key"]
    issue = lambda code: make_issue(code, "alignment", hit_key=key, field="alignment", source_pointer=pointer + "/alignment")
    reason = "alignment_not_parsed"
    if (type(raw.get("alignment")) is dict
            and any(type(raw["alignment"].get(name)) is not str for name in RFAM_ALIGNMENT_FIELDS)):
        row["issues"].append(issue("rfam_alignment_invalid"))
        reason = "alignment_conflict"
    if raw.get("alignment") is None:
        reason = "alignment_missing"
        row["issues"].append(issue("rfam_alignment_missing"))
    elif type(raw["alignment"]) is not dict:
        reason = "alignment_conflict"
        row["issues"].append(issue("rfam_alignment_invalid"))
    elif bundle_invalid:
        reason = "alignment_conflict"
    elif supplied is not None:
        try:
            supplied = validate_rfam_alignment_result(supplied)
            expected = {"artifact_ref": capture["artifact_ref"], "hit_key": key,
                "query_occurrence_key": identity["query_occurrence_key"], "family_accession": row["family_accession"]}
            if supplied["hit_identity"] != expected or supplied["query_strand"] != row["native"]["strand"]:
                raise ContractError("rfam_alignment_binding_conflict")
            if supplied["status"] in ("complete", "partial"):
                if (not row["identity_valid"] or not row["query_coordinates_valid"]
                        or supplied["display_query_from"] != row["native"]["start"]
                        or supplied["display_query_to"] != row["native"]["end"]):
                    raise ContractError("rfam_alignment_coordinate_conflict")
                lo, hi = row["query_interval"]
                if any(a < lo or b > hi for a, b in supplied["aligned_query_intervals"]):
                    raise ContractError("rfam_alignment_coordinate_conflict")
                complement = str.maketrans("ACGTURYSWKMBDHVN", "UGCAAYRSWMKVHDBN")
                for pair in supplied["paired_positions"]:
                    pos = pair["query_position"]
                    if not lo <= pos < hi:
                        raise ContractError("rfam_alignment_coordinate_conflict")
                    observed = identity["submitted_sequence"][pos].upper()
                    if supplied["query_strand"] == "-":
                        observed = observed.translate(complement)
                    if observed.replace("T", "U") != pair["query_symbol"].upper().replace("T", "U"):
                        raise ContractError("rfam_alignment_query_conflict")
            row["alignment_components"] = supplied
            row["issues"].extend(deepcopy(supplied["issues"]))
            if supplied["status"] == "unsupported":
                reason = "alignment_unsupported"
            elif supplied["status"] == "invalid":
                reason = "alignment_conflict"
            else:
                # Supplied exact intervals/counts are useful even with an optional
                # unparsed PP segment. Native omitted correspondence is not zero.
                for field in _ALIGNMENT_METRICS:
                    if field in supplied and supplied[field] is None:
                        missing[field] = "alignment_unsupported" if supplied["status"] == "partial" else "not_reported"
                return
        except ContractError as error:
            row["issues"].append(issue(str(error)))
            reason = "alignment_conflict"
    missing.update({field: reason for field in _ALIGNMENT_METRICS})


def _attach_metadata(row, metadata):
    row["missing"]["model_length_positions"] = "model_length_unavailable"
    row["missing"]["model_coverage_fraction"] = "model_length_unavailable"
    if metadata is None:
        return
    records = [r for r in metadata["records"] if r["accession"] == row["family_accession"]]
    bindings = [b for b in metadata["bindings"] if b["hit_key"] == row["hit_key"]]
    if not records and not bindings:
        return
    # The observed JSON profile supplies no native digest/release evidence.
    # Explicit records remain saved but accession equality is not a binding.
    by_ref = {}
    by_model = {}
    conflicting = False
    for record in records:
        ref = record["metadata_ref"]
        if ref in by_ref and by_ref[ref] != record:
            conflicting = True
        by_ref[ref] = record
        model_key = (("sha256", record["model_sha256"]) if record["model_sha256"] is not None
            else ("release", record["model_release"], record["accession"]) if record["model_release"] is not None else ("ref", ref))
        if record["model_length_positions"] is not None:
            by_model.setdefault(model_key, set()).add(record["model_length_positions"])
    conflicting = conflicting or any(len(lengths) > 1 for lengths in by_model.values())
    if any(b["metadata_ref"] not in by_ref for b in bindings):
        conflicting = True
    reason = "model_metadata_conflict" if conflicting else "model_binding_unverified"
    row["missing"].update(model_length_positions=reason, model_coverage_fraction=reason)
    row["issues"].append(make_issue("rfam_" + reason, "metadata", hit_key=row["hit_key"], field="model_length_positions"))


def _hit(raw, family, ordinal, document_ordinal, identity, capture, supplied, metadata, bundle_invalid):
    pointer = "/hits/" + json_pointer_token(family) + "/" + str(ordinal)
    key = capture["artifact_ref"] + pointer
    issues, missing = [], {}
    row = {"hit_key": key, "native_json_pointer": pointer, "document_ordinal": document_ordinal,
        "family_list_ordinal": ordinal, "query_occurrence_key": identity["query_occurrence_key"],
        "family_name": family, "family_accession": None, "identity_valid": False,
        "native": dict.fromkeys(("start", "end", "strand", "score_bits", "evalue", "gc_fraction")),
        "query_length_nt": identity["submitted_length_nt"], "query_interval": None, "query_coordinates_valid": False,
        "model_metadata_ref": None, "model_length_positions": None, "alignment_components": None,
        "duplicate_of": None, "missing": missing, "issues": issues}
    if type(raw) is not dict:
        issues.append(make_issue("rfam_hit_object_required", "row", hit_key=key, source_pointer=pointer))
        missing.update({name: "identity_rejected" for name in ("native_score_bits", "native_evalue", "native_gc_fraction", "query_span_nt", "query_span_fraction")})
        _attach_alignment(row, None, {}, identity, capture, bundle_invalid)
        _attach_metadata(row, metadata)
        return row
    if raw.get("id") != family or not family:
        issues.append(make_issue("rfam_hit_family_identity_conflict", "row", hit_key=key, field="id", source_pointer=pointer + "/id"))
    acc = raw.get("acc")
    if type(acc) is str and re.fullmatch(r"RF[0-9]{5}", acc):
        row["family_accession"] = acc
    else:
        issues.append(make_issue("rfam_hit_accession_invalid", "row", hit_key=key, field="acc", source_pointer=pointer + "/acc"))
    row["identity_valid"] = not issues
    for native, normalized, metric, minimum, maximum in (
            ("score", "score_bits", "native_score_bits", None, None),
            ("E", "evalue", "native_evalue", 0, None), ("GC", "gc_fraction", "native_gc_fraction", 0, 1)):
        value = raw.get(native)
        if is_number(value) and (minimum is None or value >= minimum) and (maximum is None or value <= maximum):
            row["native"][normalized] = value
        else:
            missing[metric] = "not_reported" if native not in raw or value is None else "invalid_native_value"
            issues.append(make_issue("rfam_hit_numeric_invalid", "cell", hit_key=key, field=native, source_pointer=pointer + "/" + native))
    coordinate_valid = True
    for field in ("start", "end"):
        value = raw.get(field)
        if type(value) is int:
            row["native"][field] = value
        if type(value) is not int:
            code = "rfam_hit_coordinate_invalid"
        elif not 1 <= value <= identity["submitted_length_nt"]:
            code = "rfam_hit_coordinate_out_of_bounds"
        else:
            continue
        coordinate_valid = False
        missing["native_" + field + "_1i"] = "not_reported" if field not in raw else "invalid_native_value"
        issues.append(make_issue(code, "cell", hit_key=key, field=field, source_pointer=pointer + "/" + field))
    if raw.get("strand") not in ("+", "-"):
        coordinate_valid = False
        issues.append(make_issue("rfam_hit_strand_invalid", "cell", hit_key=key, field="strand", source_pointer=pointer + "/strand"))
    else:
        row["native"]["strand"] = raw["strand"]
    if coordinate_valid:
        start, end, strand = (row["native"][k] for k in ("start", "end", "strand"))
        if strand == "+" and start > end or strand == "-" and start < end:
            coordinate_valid = False
            issues.append(make_issue("rfam_hit_strand_coordinate_conflict", "row", hit_key=key, field="strand", source_pointer=pointer))
    row["query_coordinates_valid"] = coordinate_valid
    if coordinate_valid:
        row["query_interval"] = [min(raw["start"], raw["end"]) - 1, max(raw["start"], raw["end"])]
    else:
        missing.update(query_span_nt="coordinates_invalid", query_span_fraction="coordinates_invalid")
    _attach_alignment(row, supplied, raw, identity, capture, bundle_invalid)
    _attach_metadata(row, metadata)
    return row


def populate_rfam_batch_json_sheet(content: bytes, *, input_identity: RfamBatchInputIdentity,
        capture: RfamArtifactCapture, model_metadata: RfamModelMetadataBundle | None = None,
        alignment_components: RfamAlignmentComponents | None = None) -> RfamParseResult:
    """Read all reported native cells; reject contradictory assigned identity."""
    issues = []
    try:
        identity = validate_rfam_input_identity(input_identity)
        capture = validate_rfam_capture(capture)
        if type(content) is not bytes or hashlib.sha256(content).hexdigest() != capture["source_sha256"]:
            raise ContractError("rfam_source_identity_conflict")
        if capture["request_job_id"] != identity["expected_job_id"]:
            raise ContractError("rfam_result_job_identity_conflict")
        if capture["request_sequence_sha256"] != identity["submitted_sequence_sha256"]:
            raise ContractError("rfam_result_sequence_identity_conflict")
    except ContractError as error:
        return _result("rejected", [make_issue(str(error))])
    if capture["representation"] != "json":
        return _result("unsupported", [make_issue("rfam_text_format_unverified")])
    if capture["http_status"] not in (None, 200) or capture["evidence_kind"] == "native_response" and capture["http_status"] is None:
        return _result("rejected", [make_issue("rfam_http_error")])
    try:
        native = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_keys,
            parse_constant=_invalid_constant, parse_float=_native_float)
        finite_json_copy(native, code="rfam_json_invalid")
    except (UnicodeError, ValueError, RecursionError) as error:
        code = str(error) if isinstance(error, ContractError) else "rfam_json_invalid"
        return _result("rejected", [make_issue(code)])
    if type(native) is not dict:
        return _result("rejected", [make_issue("rfam_result_object_required")])
    if type(native.get("hits")) is list and "searchSequence" not in native and "opened" in native:
        return _result("unsupported", [make_issue("rfam_multiple_sequences_schema_unestablished")], format="rfam_multiple_sequences_json_untyped")
    if native.get("jobId") != identity["expected_job_id"]:
        issues.append(make_issue("rfam_result_job_identity_conflict", field="jobId", source_pointer="/jobId"))
    sequence = native.get("searchSequence")
    sequence_code = None
    if "searchSequence" not in native:
        sequence_code = "rfam_result_sequence_identity_absent"
    elif type(sequence) is not str:
        sequence_code = "rfam_result_sequence_identity_not_string"
    elif not sequence:
        sequence_code = "rfam_result_sequence_identity_empty"
    elif not sequence.isascii():
        sequence_code = "rfam_result_sequence_identity_not_ascii"
    elif sequence != identity["submitted_sequence"]:
        sequence_code = "rfam_result_sequence_identity_conflict"
    if sequence_code:
        issues.append(make_issue(sequence_code, field="searchSequence", source_pointer="/searchSequence"))
    if issues:
        return _result("rejected", issues, format=_FORMAT)
    if not capture["body_complete"]:
        issues.append(make_issue("rfam_response_body_incomplete"))
    hits, valid_buckets = native.get("hits"), True
    if type(hits) is not dict:
        issues.append(make_issue("rfam_result_hits_representation", field="hits", source_pointer="/hits"))
        hits, valid_buckets = {}, False
    observed = []
    for family, bucket in hits.items():
        if type(bucket) is not list:
            issues.append(make_issue("rfam_result_hits_representation", field="hits", source_pointer="/hits/" + json_pointer_token(family)))
            valid_buckets = False
            continue
        observed.extend((family, i, raw) for i, raw in enumerate(bucket))
    declared = native.get("numHits")
    count_agrees = is_int(declared) and declared == len(observed) and valid_buckets
    if not count_agrees:
        issues.append(make_issue("rfam_result_hit_count_conflict", field="numHits", source_pointer="/numHits"))
    job = {"job_id": native["jobId"]}
    for name in ("opened", "started", "closed"):
        value = native.get(name)
        job[name] = value if type(value) is str else None
        if value is not None and type(value) is not str:
            issues.append(make_issue("rfam_result_timestamp_invalid", field=name, source_pointer="/" + name))
    metadata = _metadata_bundle(model_metadata, issues)
    expected_keys = {capture["artifact_ref"] + "/hits/" + json_pointer_token(family) + "/" + str(i) for family, i, _ in observed}
    alignment_index, bundle_invalid = _alignment_index(alignment_components, capture, expected_keys, issues)
    rows, seen = [], {}
    for document_ordinal, (family, ordinal, raw) in enumerate(observed):
        key = capture["artifact_ref"] + "/hits/" + json_pointer_token(family) + "/" + str(ordinal)
        row = _hit(raw, family, ordinal, document_ordinal, identity, capture, alignment_index.get(key), metadata, bundle_invalid)
        fingerprint = rfam_digest(raw)
        row["duplicate_of"] = seen.get(fingerprint)
        seen.setdefault(fingerprint, row["hit_key"])
        rows.append(row)
        issues.extend(deepcopy(row["issues"]))
    sheet = {"schema_version": "rfam_batch_sheet_v1", "source": capture, "input": identity, "job": job,
        "format_metadata": dict.fromkeys(_FORMAT_FIELDS),
        "population": {"native_reported_count": declared if is_int(declared) else None,
            "observed_row_count": len(observed), "family_bucket_count": len(hits), "count_agrees": count_agrees,
            "body_complete": capture["body_complete"], "result_identity_matches": True,
            "reported_set_complete": capture["body_complete"] and count_agrees and valid_buckets,
            "provider_filtering_known": None, "all_model_hits_complete": None},
        "hits": rows, "model_metadata": metadata, "issues": issues}
    return _result("partial" if issues else "complete", issues, sheet=sheet, format=_FORMAT)
