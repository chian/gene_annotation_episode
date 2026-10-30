"""Bounded views of explicitly received native BLAST HSPs, without execution."""
from __future__ import annotations

from copy import deepcopy
import json
import re

from . import blast_search as blast
from .domain import ContractError, identity


MAX_ALIGNMENT_COLUMNS = 4096
BLAST_HSP_FACT_SCHEMA = {"type": "array", "items": {"type": "object", "additionalProperties": False,
    "properties": {
        "hsp_ref": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "reference_ref": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        **{name: {"type": "number"} for name in (
            "bitscore", "alignment_score", "evalue", "query_coverage", "target_coverage")},
        "identity_fraction": {"type": ["number", "null"]},
    }, "required": ["hsp_ref", "reference_ref", "bitscore", "alignment_score", "evalue",
                    "query_coverage", "target_coverage", "identity_fraction"]}}


def require_permitted_hsp(observation_ref, permitted_inputs):
    if (not isinstance(permitted_inputs, (tuple, list))
            or any(not isinstance(ref, str) or not ref for ref in permitted_inputs)):
        raise ContractError("blast_hsp_inputs_not_bound")
    if observation_ref not in permitted_inputs:
        raise ContractError("blast_hsp_input_not_received")


def _immutable_record(row):
    payload = {key: value for key, value in row.items() if key not in {"id", "record_type", "origin"}}
    if row["id"] != identity(row["record_type"], {"origin": row["origin"], "record": payload}):
        raise ContractError("blast_hsp_record_identity_conflict")


def _original_hsp(store, observation_ref, permitted_inputs, scope):
    require_permitted_hsp(observation_ref, permitted_inputs)
    scope = store.validate_scope(scope)
    observation = store.get(observation_ref)
    if observation.get('native_blast_database') is not None:
        from .native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, observation)
        raise ContractError('native_blast_database_biological_reference_unavailable')
    if (observation.get("record_type") != "observation" or observation.get("origin") != "tool"
            or observation.get("kind") != "comparison"
            or not (observation.get("native_blast") or observation.get("native_blast_pairwise"))):
        raise ContractError("native_blast_hsp_observation_required")
    if "native_blast" in observation and "native_blast_pairwise" in observation:
        raise ContractError("native_blast_pairwise_mixed_native_markers")
    _immutable_record(observation)
    if not store.reference_subset([observation_ref], scope):
        raise ContractError("blast_hsp_outside_assigned_scope")
    footprint = [segment for interval in observation.get('operand_intervals') or []
                 if interval['role'] == 'query' and store.roots(interval['subject_ref'])
                 for segment in store.map_segments(interval['subject_ref'],
                     [{'start': interval['start'], 'end': interval['end']}])]
    if footprint and not store.scope_covers(footprint, scope):
        raise ContractError("blast_hsp_outside_assigned_scope")
    if len(observation["subject_refs"]) != 1 or len(observation["source_subject_refs"]) != 1:
        raise ContractError("blast_hsp_operand_identity_conflict")
    if observation.get("native_blast_pairwise"):
        from .native_blast_hsp_views import native_blast_pairwise_hsp
        bound = native_blast_pairwise_hsp(store, observation)
        return observation, bound["source"], bound["reference"], bound["native_hsp"]
    source = store.get(observation["source_ref"])
    if source.get("record_type") != "source" or source.get("provider") != "ncbi_blast" or source.get("origin") != "external":
        raise ContractError("native_blast_source_required")
    _immutable_record(source)
    try:
        metadata = json.loads(store.get_artifact(source["request_ref"]))
        request = metadata["request"]
        parsed = blast.document(store.get_artifact(source["artifact_ref"]))
        blast.validate_identity(parsed, request)
        native_locator = observation["native_blast"]
        if native_locator["report_ordinal"] != 0:
            raise ValueError("blast_single_query_report_required")
        hit = parsed["search"]["hits"][native_locator["hit_ordinal"]]
        native = hit["hsps"][native_locator["hsp_ordinal"]]
        query_ref = observation["subject_refs"][0]
        reference_ref = observation["source_subject_refs"][0]
        reference = store.get(reference_ref)
        if (request["subject_ref"] != query_ref or request["query_length"] != store.subject_length(query_ref)
                or reference.get("record_type") != "reference" or reference["source_ref"] != source["id"]
                or reference["length"] != hit["len"]):
            raise ValueError("blast_hsp_operand_identity_conflict")
        _immutable_record(reference)
        descriptions = [row for row in (hit.get("description") or []) if isinstance(row, dict)]
        first = descriptions[0] if descriptions else {}
        accession = first.get("accession") or first.get("id")
        if (not isinstance(accession, str) or len(accession) > 200
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]*", accession) is None):
            accession = identity("source_local_hit", {"source_ref": source["id"], "hit_ordinal": native_locator["hit_ordinal"]})
        if reference["accession"] != accession:
            raise ValueError("blast_hsp_reference_identity_conflict")
        row = blast.hsp_row(native, program=request["algorithm"], query_length=request["query_length"],
            reference_length=reference["length"], hit_ordinal=native_locator["hit_ordinal"],
            hsp_ordinal=native_locator["hsp_ordinal"])
        if row["native_blast"] != native_locator:
            raise ValueError("blast_hsp_native_geometry_conflict")
        expected_intervals = [
            {"role": role, "subject_ref": ref, "start": interval[0], "end": interval[1],
             "unit": store.subject_unit(ref), "model_unit": blast.PROGRAM_UNITS[request["algorithm"]][2]}
            for role, ref, interval in (("query", query_ref, row["query_interval"]),
                                      ("reference", reference_ref, row["reference_interval"]))]
        if observation.get("operand_intervals") != expected_intervals:
            raise ValueError("blast_hsp_operand_geometry_conflict")
        measured = {item["name"]: item["value"] for item in observation["measurements"]}
        if measured.get("reference_ref") != {"type": "reference", "ref": reference_ref}:
            raise ValueError("blast_hsp_reference_identity_conflict")
        for name, value in row["measurements"].items():
            if measured.get(name) != {"type": "number", "value": value, "unit_ref": None}:
                raise ValueError("blast_hsp_native_measurement_conflict")
        original_rids = []
        for ref in source.get("parent_source_refs", []):
            parent = store.get(ref)
            if parent.get("provider") == "ncbi_blast":
                try:
                    original_rids.append(blast.submission(store.get_artifact(parent["artifact_ref"]))[0])
                except (ValueError, UnicodeError):
                    pass
        if request.get("job_id") not in original_rids:
            raise ValueError("blast_original_submission_identity_conflict")
    except (ValueError, TypeError, KeyError, IndexError) as error:
        raise ContractError(str(error) if isinstance(error, ValueError)
                            else "blast_hsp_native_record_invalid") from error
    return observation, source, reference, native


def _grade_read(grader, *args, **kwargs):
    try:
        return grader(*args, **kwargs)
    except ValueError as error:
        return {'sheet': None, 'scores': None,
                'failure': {'code': str(error), 'category': 'grading_input'}}


def read_blast_hsp(store, observation_ref, column_offset, column_limit, *, permitted_inputs,
                   scope, grade_result=None):
    """Read one received HSP and a bounded native alignment-column window.

    The host supplies permitted inputs. An operand scope alone grants no source
    access. All values come from the retained response; no alignment is rerun,
    full reference sequence acquired, record published or credit assigned here.
    """
    if (type(column_offset) is not int or column_offset < 0 or type(column_limit) is not int
            or not 1 <= column_limit <= MAX_ALIGNMENT_COLUMNS):
        raise ContractError("bounded_blast_alignment_window_required")
    observation, source, reference, native = _original_hsp(store, observation_ref, permitted_inputs, scope)
    query, hit, midline = native.get("qseq"), native.get("hseq"), native.get("midline")
    alignment, unavailable = None, None
    if query is None and hit is None:
        unavailable = "native_alignment_not_reported"
    elif (not isinstance(query, str) or not isinstance(hit, str) or len(query) != len(hit)
            or "align_len" in native and native["align_len"] != len(query)
            or midline is not None and (not isinstance(midline, str) or len(midline) != len(query))):
        unavailable = "native_alignment_incomplete"
    else:
        if column_offset > len(query):
            raise ContractError("blast_alignment_window_out_of_bounds")
        end = min(len(query), column_offset + column_limit)
        alignment = {"column_offset": column_offset, "column_end": end, "total_columns": len(query),
            "query": query[column_offset:end], "reference": hit[column_offset:end],
            "midline": midline[column_offset:end] if midline is not None else None,
            "next_column_offset": end if end < len(query) else None}
    from .alignment_site_native import blast_grading
    from .tool_grading_artifacts import retain_tool_grading
    grading = blast_grading(store, observation, source, reference, native,
        column_offset, column_limit, grade_result=grade_result or _grade_read)
    retained = retain_tool_grading(store, provider=source['provider'],
        native_artifact_ref=source['artifact_ref'], grading=grading)
    sheet, scores = grading.get('sheet'), grading.get('scores') or {}
    columns = sheet['columns'] if sheet is not None and sheet['realized_window'] is not None else None
    preview_fields = ('column', 'query_symbol', 'reference_symbol', 'query_interval',
        'reference_interval', 'query_unit', 'reference_unit', 'alignment_unit',
        'query_direction', 'reference_direction', 'relationship')
    preview = ([{key: row[key] for key in preview_fields} for row in columns[:12]]
               if columns is not None else None)
    marker = "native_blast_pairwise" if "native_blast_pairwise" in observation else "native_blast"
    return {"observation_ref": observation_ref, "source_ref": source["id"], "reference_ref": reference["id"],
            marker: deepcopy(observation[marker]),
            "measurements": deepcopy(observation["measurements"]),
            "operand_intervals": deepcopy(observation["operand_intervals"]),
            "alignment_available": alignment is not None, "alignment_unavailable_reason": unavailable,
            "alignment": alignment, "full_reference_sequence_available": reference["sequence_ref"] is not None,
            'site_grading_artifact_ref': retained,
            'data_status': sheet['status'] if sheet is not None else 'unavailable',
            'column_correspondence': preview,
            'column_correspondence_count': len(columns) if columns is not None else None,
            'column_correspondence_preview_limit': 12,
            'selected_column_components': scores.get('summary'),
            'site_grading_failure': grading.get('failure')}


def blast_hsp_facts(store, references):
    """Project already qualified acquisition records; never acquire or grade."""
    result = []
    for reference in dict.fromkeys(references):
        record = store.get(reference)
        if record.get('record_type') != 'observation' or not record.get('native_blast'):
            continue
        if (record.get('origin') != 'tool' or record.get('kind') != 'comparison'
                or len(record.get('source_subject_refs', [])) != 1):
            raise ContractError('native_blast_hsp_observation_required')
        _immutable_record(record)
        source = store.get(record['source_ref'])
        if source.get('provider') != 'ncbi_blast':
            raise ContractError('native_blast_source_required')
        values = {row['name']: row['value'] for row in record['measurements']}
        native = {}
        for name in ('bitscore', 'alignment_score', 'evalue', 'query_coverage', 'target_coverage'):
            if values.get(name, {}).get('type') != 'number':
                raise ContractError('blast_hsp_native_measurement_required')
            native[name] = values[name]['value']
        identity_value = values.get('identity_fraction')
        if identity_value is not None and identity_value.get('type') != 'number':
            raise ContractError('blast_hsp_native_measurement_required')
        result.append({'hsp_ref': reference, 'reference_ref': record['source_subject_refs'][0],
            **native, 'identity_fraction': identity_value['value'] if identity_value is not None else None})
    return result


__all__ = ["read_blast_hsp", "require_permitted_hsp", "MAX_ALIGNMENT_COLUMNS",
           "blast_hsp_facts", "BLAST_HSP_FACT_SCHEMA"]
