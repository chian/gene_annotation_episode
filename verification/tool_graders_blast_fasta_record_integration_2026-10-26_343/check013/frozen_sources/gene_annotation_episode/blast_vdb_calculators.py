"""Deterministic VDB geometry, membership and source-qualified measurements.

All counts name their entity; all fractions retain numerator and denominator.
Partial unions are observed subsets, never full-coverage estimates. There is no
VDB function-probability model. The saved sheet is never mutated and calculation
does not acquire records, read files or execute tools.

The private shared mechanics ports are blast_sequence_database._rows:
  _rows({'search': Search, 'report_source': ReportSource}, issues:list)
  -> (normalized_or_none, RowIndex, incomplete_hit_ordinals:set, native_ordinals:list)
It rechecks retained JSON/table rows and attaches original locators. No sequence
database admission, metadata kernel or probability calculation is invoked.
For span-only validation the exact existing geometry port is
  _axis_geometry(hsp, *, prefix='query'|'hit', length=int|None,
      coordinate_unit='nt'|'aa', alignment_unit='nt'|'aa', issues=list,
      coordinate_convention='blast_json2'|'directional', symbols=None)
  -> (traversal_start, traversal_end, width, direction) | None.
No symbol argument is supplied for span-only native endpoints; positional
coverage always requires the complete public column-correspondence calculation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import re

from Bio.Data import CodonTable
from Bio.Seq import Seq

from .blast_vdb_inputs import (_copy, _validate_sheet, _issue, _token, _recheck_metadata,
                               _symbols, _sra_equal)
from .blast_program_context import resolve_blast_program_context
from .blast_pairwise_grader import (alignment_components, blast_hsp_column_correspondence,
                                   _axis_geometry)
from .blast_sequence_database import _rows

__all__ = ["calculate_blast_vdb_components"]


def _measure(value, unit, reason=None):
    return dict(value=value, unit=unit, status="available" if value is not None else
                "incompatible" if reason == "incompatible_input" else "unavailable",
                unavailable_reason=None if value is not None else reason or "missing_input")


def _ratio(numerator, denominator, complete=True, reason=None):
    usable = numerator is not None and denominator is not None and denominator > 0 and complete and reason is None
    return dict(numerator=numerator, denominator=denominator,
        value=numerator / denominator if usable else None, unit="fraction",
        complete_for_reported_hsps=bool(complete), unavailable_reason=None if usable else
        reason or ("partial_output" if not complete else "not_measured" if denominator == 0 else "missing_input"))


def _union(intervals):
    result = []
    for start, end in sorted(set(tuple(x) for x in intervals)):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def _length(intervals):
    return sum(b - a for a, b in _union(intervals))


def _intersect(first, second):
    return _union([[max(a, c), min(b, d)] for a, b in first for c, d in second if max(a, c) < min(b, d)])


def _member_key(binding):
    return {k: deepcopy(binding[k]) for k in ("dataset_key", "member_kind", "member_identifier")}


def _add_unique(rows, value):
    if value not in rows:
        rows.append(deepcopy(value))


def _add(issues, key, code, *, hit=None, hsp=None, **details):
    issues.append(_issue(code, key=key, hit=hit, hsp=hsp, pointer=key["search_pointer"], **details))


def _positive(value):
    return value if type(value) is int and value > 0 else None


def _source_rows(sheet, issues):
    search, source = sheet["search"], sheet["report_source"]
    key, context, normalized = search["search_key"], search["program_context"], search["normalized"]
    invalid = False; unavailable = False
    if any(source[k] != key[k] for k in ("artifact_key", "member_ordinal")):
        _add(issues, key, "report_source_conflict"); invalid = True
    member = normalized["native"].get("archive_member")
    if key["member_ordinal"] is not None:
        if not isinstance(member, dict) or member.get("ordinal") != key["member_ordinal"]:
            _add(issues, key, "report_source_conflict"); invalid = True
        elif member.get("sha256") is None:
            _add(issues, key, "member_digest_unverifiable"); unavailable = True
        elif member["sha256"] != source["member_sha256"]:
            _add(issues, key, "member_digest_conflict"); invalid = True
    elif member is not None:
        _add(issues, key, "report_source_conflict"); invalid = True
    try:
        resolved = resolve_blast_program_context(**{k: v for k, v in context.items() if k != "geometry_program"})
        if context["reported_program"] is None or context["geometry_program"] is None:
            _add(issues, key, "program_context_unresolved"); unavailable = True
        elif resolved != context:
            _add(issues, key, "program_context_conflict"); invalid = True
    except (TypeError, ValueError) as error:
        _add(issues, key, "program_context_conflict", resolver_error=str(error)); invalid = True
    report = search["native"].get("report", {})
    if (normalized["mode"] != "database" or normalized["search"]["program"] != context["execution_program"]
            or normalized["search"]["version"] != context["native_version"]
            or any(report.get(a) != context[b] for a, b in (("program", "reported_program"), ("version", "native_version")))):
        _add(issues, key, "program_context_conflict"); invalid = True
    fmt = normalized["format"]
    if fmt == "json2":
        target = report.get("search_target")
        if not isinstance(target, dict) or "subjects" in target or target.get("db") != normalized["search"]["database"]:
            _add(issues, key, "report_source_conflict"); invalid = True
        native = search["native"].get("search", {})
        if isinstance(native, dict):
            native_hits = native.get("hits")
            expected = dict(hit_array_present=isinstance(native_hits, list),
                reported_hit_count=len(native_hits) if isinstance(native_hits, list) else None,
                statistics=native.get("stat", {}) if isinstance(native.get("stat", {}), dict) else {},
                parameters=report.get("params", {}) if isinstance(report.get("params", {}), dict) else {})
            if any(normalized["search"][k] != value for k, value in expected.items()):
                _add(issues, key, "native_reporting_conflict", fields=[k for k, v in expected.items() if normalized["search"][k] != v]); invalid = True
    elif fmt == "tabular":
        layout = normalized["native"].get("table_layout")
        if layout is None:
            _add(issues, key, "table_layout_unavailable"); unavailable = True
        elif (not isinstance(layout, dict) or set(layout) != {"format", "declared_fields", "delimiter"}
              or layout["format"] not in {"tabular6", "tabular7"} or not isinstance(layout["delimiter"], str)
              or len(layout["delimiter"]) != 1 or layout["delimiter"] in "\r\n\0"
              or layout["declared_fields"] is not None and
              (not isinstance(layout["declared_fields"], list) or any(str(x).strip().lower() == "std" for x in layout["declared_fields"]))):
            _add(issues, key, "table_layout_invalid"); invalid = True
    else:
        _add(issues, key, "format_unsupported"); unavailable = True
    empty_index = {"search": dict(search_key=deepcopy(key), hit_ordinal=None, hsp_ordinal=None, description_ordinal=None), "hits": []}
    if invalid or unavailable:
        return None, empty_index, set(), [], "incompatible" if invalid else "unavailable"
    mechanical = []
    result, index, incomplete, native = _rows({"search": search, "report_source": source}, mechanical)
    for issue in mechanical:
        code = "table_layout_unavailable" if "table_layout_unavailable" in issue["code"] else "table_layout_invalid" if "table_layout_invalid" in issue["code"] else "native_row_map_conflict"
        _add(issues, key, code, original_issue=issue)
    return result, index, incomplete, native, "incompatible" if result is None else None


def _metadata(sheet, issues):
    result = []
    key = sheet["search"]["search_key"]
    for ordinal, row in enumerate(sheet["reference_metadata"]):
        if not _recheck_metadata(row):
            _add(issues, key, "metadata_native_extraction_unverified", metadata_key=row["metadata_key"], metadata_index=ordinal)
            continue
        entity = row["entity"]
        if (entity["kind"] in {"member", "feature"} and entity["member_identifier"] not in row["identifiers"]
                and entity["kind"] != "feature"):
            _add(issues, key, "metadata_entity_conflict", metadata_key=row["metadata_key"]); continue
        sequence = row["sequence"]
        if sequence is not None and _symbols(sequence["symbols"], sequence["length"], sequence["molecule"]) != sequence:
            _add(issues, key, "sequence_identity_conflict", metadata_key=row["metadata_key"]); continue
        if row["feature"] is not None and row["feature"]["feature_identifier"] != entity["feature_identifier"]:
            _add(issues, key, "metadata_entity_conflict", metadata_key=row["metadata_key"]); continue
        result.append(row)
    return result


def _datasets(sheet, issues):
    key, search = sheet["search"]["search_key"], sheet["search"]
    result = {}
    for dataset in sheet["dataset_records"]:
        context = dataset["search_context"]
        if context["search_key"] != key:
            _add(issues, key, "dataset_selection_unverified", dataset_key=dataset["dataset_key"], supplied_search_key=context["search_key"])
            continue
        # The supplied dataset record is a caller-owned relation. Only actual
        # retained contradictions invalidate it; no Store custody is claimed.
        conflicts = []
        params = search["normalized"]["search"]["parameters"]
        for field, native_names in (("subject_genetic_code", ("db_gencode", "db-genetic-code")),
                                    ("sra_mode", ("sra_mode",)), ("include_filtered_reads", ("include_filtered_reads",))):
            for name in native_names:
                if name in params and context[field] != params[name]:
                    conflicts.append(field)
        if conflicts:
            _add(issues, key, "dataset_options_conflict", dataset_key=dataset["dataset_key"], fields=conflicts)
        result[dataset["dataset_key"]] = {"record": dataset, "options_valid": not conflicts}
    return result


def _query_axis(sheet, datasets, metadata, issues):
    search = sheet["search"]; context = search["program_context"]; key = search["search_key"]
    query = sheet["query_binding"]
    axis_kind = "pssm_master" if context["query_kind"] == "pssm" else "sequence"
    unit = "nt" if context["execution_program"] == "blastn_vdb" else "aa"
    axis = dict(axis_kind=axis_kind, reported_length=search["normalized"]["query"]["length"],
                full_length=None, selected_interval=None, effective_query_interval=None, coordinate_unit=unit)
    if query is None or search["operand_binding"] is None:
        _add(issues, key, "query_axis_unbound"); return axis
    operand = query["operand"]; reasons = []
    if operand != search["operand_binding"] or operand["role"] != "query":
        reasons.append("operand")
    if query["axis_kind"] != axis_kind or query["coordinate_unit"] != unit:
        reasons.append("axis_kind")
    if operand["molecule"] not in ({"dna", "rna"} if unit == "nt" else {"protein"}):
        reasons.append("molecule")
    if operand["length"] != query["full_length"]:
        reasons.append("full_length")
    selected, reported = operand["selected_interval"], axis["reported_length"]
    if reported is not None and reported != query["full_length"] and (selected is None or reported != selected[1] - selected[0]):
        reasons.append("reported_length")
    if axis_kind == "pssm_master":
        selected_keys = {d["record"]["search_context"]["input_pssm_key"] for d in datasets.values()}
        maps = [m["master_mapping"] for m in metadata if m["entity"]["kind"] == "query_master"
                and m["entity"]["pssm_key"] == query["pssm_key"] and m["source"] == query["master_mapping_ref"] and m["master_mapping"]]
        valid = len(maps) == 1 and selected_keys == {query["pssm_key"]} and query["pssm_key"] is not None
        if valid:
            master = maps[0]
            valid = (master["pssm_key"] == query["pssm_key"] and master["num_columns"] == query["full_length"]
                     and [c["column"] for c in master["columns"]] == list(range(master["num_columns"]))
                     and all(c["master_position"] is None or c["master_position"] < query["full_length"] for c in master["columns"]))
        if not valid:
            _add(issues, key, "query_master_mapping_unavailable"); reasons.append("master_mapping")
        _add(issues, key, "query_biological_identity_unestablished")
    elif query["sequence_sha256"] is None:
        _add(issues, key, "query_biological_identity_unestablished")
    if reasons:
        _add(issues, key, "query_axis_conflict", fields=reasons); return axis
    axis.update(full_length=query["full_length"], selected_interval=deepcopy(selected))
    extents = [d["record"]["search_context"]["query_extent"] for d in datasets.values()]
    values = {(e["mode"], _token(e["interval"])) for e in extents}
    if len(values) > 1:
        _add(issues, key, "query_axis_conflict", fields=["query_extent"])
    elif extents:
        extent = extents[0]
        if extent["mode"] == "full" and selected is None:
            axis["effective_query_interval"] = [0, query["full_length"]]
        elif extent["mode"] == "interval" and extent["interval"] == selected:
            axis["effective_query_interval"] = deepcopy(selected)
        elif extent["mode"] != "unknown":
            _add(issues, key, "query_axis_conflict", fields=["query_extent"])
    return axis


def _member_metadata(metadata, member):
    return [m for m in metadata if m["entity"]["kind"] == "member" and
            m["entity"]["dataset_key"] == member["dataset_key"] and m["entity"]["member_identifier"] == member["member_identifier"]]


def _members(sheet, normalized, index, datasets, metadata, issues):
    key = sheet["search"]["search_key"]; valid = {}
    byhit = {h["row_key"]["hit_ordinal"]: h for h in index["hits"]}
    nativehits = {h["hit_index"]: h for h in normalized["hits"]}
    for i, member in enumerate(sheet["member_bindings"]):
        h = member["hit_ordinal"]
        reason = None
        if member["search_key"] != key or h not in byhit or member["dataset_key"] not in datasets:
            reason = "member_identifier_unlinked"
        else:
            descriptions = {d["row_key"]["description_ordinal"]: d for d in byhit[h]["descriptions"]}
            d = descriptions.get(member["description_ordinal"])
            native = nativehits[h]["descriptions"][d["component_index"]] if d else None
            if native is None or {f: native.get(f) for f in ("id", "accession", "title", "taxid")} != member["native_description"]:
                reason = "member_identifier_unlinked"
            elif member["member_identifier"]["value"] not in (native.get("id"), native.get("accession")):
                values = [v for v in (native.get("id"), native.get("accession")) if isinstance(v, str)]
                if not any(v.startswith("gnl|SRA|") and v[8:] == member["member_identifier"]["value"] for v in values):
                    reason = "member_identifier_unlinked"
            if member["reference_identity"] is not None and member["reference_identity"]["identifier"] != member["member_identifier"]:
                reason = "member_identifier_unlinked"
            if member["read_identity"] is not None:
                read = member["read_identity"]["native_read_name"]
                if read != member["member_identifier"]["value"] and "gnl|SRA|" + read != member["member_identifier"]["value"]:
                    reason = "member_identifier_unlinked"
        if reason:
            _add(issues, key, reason, hit=h, binding_index=i); continue
        kind = member["member_kind"]
        reference_kind = sheet["search"]["program_context"]["reference_kind"]
        if (reference_kind == "vdb_read" and kind == "reference" or reference_kind == "vdb_reference" and kind == "read"):
            _add(issues, key, "member_kind_conflict", hit=h, binding_index=i); continue
        if kind == "unknown":
            _add(issues, key, "member_kind_unknown", hit=h, binding_index=i)
        valid[i] = member
    catalogue, origins, origin_members = {}, [], {}
    for h in index["hits"]:
        ordinal = h["row_key"]["hit_ordinal"]
        indices = [i for i, m in valid.items() if m["hit_ordinal"] == ordinal]
        claimed = [i for i in indices if valid[i]["relationship"] == "reported_origin"]
        candidate_keys = {_token(_member_key(valid[i])) for i in indices}
        claimed_keys = {_token(_member_key(valid[i])) for i in claimed}
        status = "available" if len(claimed_keys) == 1 else "ambiguous" if len(claimed_keys) > 1 or len(candidate_keys) > 1 else "unavailable"
        origin_indices = claimed if status == "available" else []
        origins.append(dict(row_key=deepcopy(h["row_key"]), status=status,
            member_keys=list({_token(_member_key(valid[i])): _member_key(valid[i]) for i in origin_indices}.values()),
            binding_indices=origin_indices))
        if status != "available":
            _add(issues, key, "member_origin_ambiguous" if status == "ambiguous" else "member_origin_unavailable", hit=ordinal,
                 binding_indices=indices)
        for i in indices:
            mkey = _member_key(valid[i]); token = _token(mkey)
            row = catalogue.setdefault(token, dict(member_key=mkey, binding_indices=[], row_keys=[]))
            _add_unique(row["binding_indices"], i); _add_unique(row["row_keys"], h["row_key"])
            if i in origin_indices:
                row = origin_members.setdefault(token, dict(member_key=mkey, binding_indices=[], row_keys=[]))
                _add_unique(row["binding_indices"], i); _add_unique(row["row_keys"], h["row_key"])
    complete = all(o["status"] == "available" for o in origins)
    summary = dict(row_keys=deepcopy(index), native_search_statistics=deepcopy(sheet["search"]["normalized"]["search"]["statistics"]),
        selected_dataset_keys=[d["dataset_key"] for d in sheet["dataset_records"]],
        reported_subject_count=_measure(len(index["hits"]), "subject"),
        reported_hsp_count=_measure(sum(len(h["hsps"]) for h in index["hits"]), "hsp"),
        origin_bound_subject_count=_measure(sum(o["status"] == "available" for o in origins), "subject"),
        origin_unbound_subject_count=_measure(sum(o["status"] in {"unavailable", "incompatible"} for o in origins), "subject"),
        origin_ambiguous_subject_count=_measure(sum(o["status"] == "ambiguous" for o in origins), "subject"),
        origins=origins, catalogue_members=list(catalogue.values()), origin_members=list(origin_members.values()),
        counts_by_kind=[dict(kind=k, catalog_member_count=_measure(sum(r["member_key"]["member_kind"] == k for r in catalogue.values()), "member"),
            origin_member_count=_measure(sum(r["member_key"]["member_kind"] == k for r in origin_members.values()), "member"))
            for k in ("read", "reference", "wgs_sequence", "unknown")], complete_for_reported_subjects=complete)
    return summary, valid


def _full_member_length(indices, valid, metadata, reported, key, hit, issues):
    lengths = []
    for i in indices:
        member = valid[i]; ref = member["reference_identity"]
        own = [m["sequence"]["length"] for m in _member_metadata(metadata, member) if m["sequence"] and m["sequence"]["molecule"] == "nt"]
        if ref and ref["full_length"] is not None:
            own.append(ref["full_length"])
        if not own or len(set(own)) != 1:
            return None
        lengths.extend(own)
    if not lengths:
        return None
    if len(set(lengths)) != 1 or reported is not None and lengths[0] != reported:
        _add(issues, key, "sequence_length_conflict", hit=hit, bound_lengths=lengths, reported_length=reported)
        return None
    return lengths[0]


def _coverage(qintervals, rintervals, complete, axis, reported, full, *, reason=None):
    qn, rn = _length(qintervals), _length(rintervals)
    qn = qn if qintervals or complete else None
    rn = rn if rintervals or complete else None
    selection = axis["effective_query_interval"]
    sn = _length(_intersect(qintervals, [selection])) if selection and qn is not None else None
    sd = selection[1] - selection[0] if selection else None
    return dict(full_query_coverage=_ratio(qn, axis["full_length"], complete, reason),
        selected_query_coverage=_ratio(sn, sd, complete, reason),
        reported_reference_coverage=_ratio(rn, reported, complete), full_member_coverage=_ratio(rn, full, complete))


def _geometry(sheet, normalized, index, incomplete, axis, valid, metadata, issues):
    search = sheet["search"]; key = search["search_key"]
    program = search["program_context"]["geometry_program"]
    convention = "blast_json2" if normalized["format"] == "json2" else "directional"
    hsps, subjects = [], []
    for hit, mapping in zip(normalized["hits"], index["hits"]):
        ordinal = hit["hit_index"]
        indices = [i for i, m in valid.items() if m["hit_ordinal"] == ordinal]
        reported = _positive(hit["length"])
        local = []
        full = _full_member_length(indices, valid, metadata, reported, key, ordinal, local)
        qlength = axis["full_length"] or _positive(axis["reported_length"])
        # Native bounds are authoritative even if supplied member length conflicts.
        rlength = reported or full
        current = []; allq, allr = [], []
        for native, row in zip(hit["hsps"], mapping["hsps"]):
            native = {k: deepcopy(v) for k, v in native.items() if k != "source_locator"}
            components = alignment_components(native, program=program, query_length=qlength,
                reference_length=rlength, coordinate_convention=convention)
            correspondence = blast_hsp_column_correspondence(native, program=program, query_length=qlength,
                reference_length=rlength, coordinate_convention=convention)
            usable = components["geometry_available"] and correspondence["geometry_status"] == "available"
            qintervals = _union([[p["query_start"], p["query_end"]] for p in components["pairs"]]) if usable else []
            rintervals = _union([[p["reference_start"], p["reference_end"]] for p in components["pairs"]]) if usable else []
            own = [{**_issue(i["code"], key=key, hit=ordinal, hsp=row["row_key"]["hsp_ordinal"],
                pointer=row["source_locator"]["pointer"], original_issue=deepcopy(i)), "code": i["code"]} for i in correspondence["issues"]]
            reason = None; selection = axis["effective_query_interval"]
            if selection and any(a < selection[0] or b > selection[1] for a, b in qintervals):
                _add(own, key, "coordinates_outside_selection", hit=ordinal, hsp=row["row_key"]["hsp_ordinal"])
                reason = "incompatible_input"
            spans = {}
            for name, prefix, length, unit in (("query_span", "query", qlength, axis["coordinate_unit"]),
                                                ("reference_span", "hit", rlength, "nt")):
                geometry = _axis_geometry(native, prefix=prefix, length=length, coordinate_unit=unit,
                    alignment_unit="nt" if program == "blastn" else "aa", issues=[], coordinate_convention=convention)
                spans[name] = _measure(abs(native[prefix + "_to"] - native[prefix + "_from"]) + 1 if geometry else None,
                                       unit, "invalid_native_row")
            counts = components["counts"]; paired, identical = counts["paired_columns"], counts["identical_pairs"]
            substitutions = paired - identical if paired is not None and identical is not None and paired >= identical else None
            raw_hsp = (search["native"]["search"]["hits"][ordinal]["hsps"][row["row_key"]["hsp_ordinal"]]
                       if normalized["format"] == "json2" else native)
            item = dict(row_key=deepcopy(row["row_key"]), source_locator=deepcopy(row["source_locator"]), native_hsp=deepcopy(raw_hsp),
                geometry_program=program, query_axis_kind=axis["axis_kind"], reference_axis_kind="vdb_member",
                native_components=components, correspondence=correspondence, **spans,
                substitutions=_measure(substitutions, "alignment_column"),
                **_coverage(qintervals, rintervals, usable, axis, reported, full, reason=reason),
                member_binding_indices=indices[:], issues=own)
            hsps.append(item); current.append(item); allq.extend(qintervals); allr.extend(rintervals)
        complete = bool(current) and ordinal not in incomplete and all(h["correspondence"]["geometry_status"] == "available" for h in current)
        if ordinal in incomplete:
            _add(local, key, "native_hsp_set_incomplete", hit=ordinal)
        qintervals, rintervals = _union(allq), _union(allr)
        selection_conflict = any(i["code"] == "blast_vdb_coordinates_outside_selection" for h in current for i in h["issues"])
        bits = [h["native_components"]["native_scores"]["bit_score"] for h in current if h["native_components"]["native_scores"]["bit_score"] is not None]
        evalues = [h["native_components"]["native_scores"]["evalue"] for h in current if h["native_components"]["native_scores"]["evalue"] is not None]
        subject = dict(row_key=deepcopy(mapping["row_key"]), source_locator=deepcopy(mapping["source_locator"]),
            hsp_row_keys=[deepcopy(h["row_key"]) for h in current],
            descriptions=[dict(row_key=deepcopy(d["row_key"]), source_locator=deepcopy(d["source_locator"]),
                native_description={k: deepcopy(v) for k, v in hit["descriptions"][d["component_index"]].items() if k != "source_locator"})
                for d in mapping["descriptions"]],
            coordinate_context={"query": deepcopy(axis), "reference": {"reported_length": reported, "full_length": full, "coordinate_unit": "nt"}},
            geometry_complete=complete, observed_paired_query_intervals=qintervals, observed_paired_reference_intervals=rintervals,
            observed_paired_query_units=_measure(_length(qintervals) if qintervals or complete else None, axis["coordinate_unit"]),
            observed_paired_reference_nt=_measure(_length(rintervals) if rintervals or complete else None, "nt"),
            **_coverage(qintervals, rintervals, complete, axis, reported, full, reason="incompatible_input" if selection_conflict else None),
            maximum_bit_score=_measure(max(bits) if bits else None, "bits"), minimum_evalue=_measure(min(evalues) if evalues else None, "expected_chance_match"),
            hsp_count=_measure(len(current), "hsp"), member_binding_indices=indices[:], sequence_group_key=None, issues=local)
        subjects.append(subject)
        issues.extend(local)
        issues.extend(i for h in current for i in h["issues"])
    return hsps, subjects


def _sequence_groups(sheet, subjects, valid, metadata, issues):
    key = sheet["search"]["search_key"]; groups = {}
    for subject in subjects:
        hit = subject["row_key"]["hit_ordinal"]
        offered = [b for b in sheet["sequence_identity_bindings"] if b["binding"]["hit_index"] == hit]
        bindings = [b["binding"] for b in offered if b["search_key"] == key and b["binding"]["report_index"] == key["report_index"]]
        identities = {(b["digest"], b["sequence_length"], b["molecule"]) for b in bindings}
        reported = subject["coordinate_context"]["reference"]["reported_length"]
        okay = bool(bindings) and len(bindings) == len(offered) and len(identities) == 1
        okay &= all(b["sequence_group"] == "sha256:" + b["digest"] and (reported is None or b["sequence_length"] == reported) for b in bindings)
        linked_sequences = [m["sequence"] for i in subject["member_binding_indices"] for m in _member_metadata(metadata, valid[i]) if m["sequence"]]
        if okay and any((s["sha256"], s["length"], s["molecule"]) not in identities for s in linked_sequences):
            okay = False
        if not okay:
            _add(issues, key, "sequence_identity_conflict" if offered else "sequence_identity_unavailable", hit=hit)
            continue
        digest, length, molecule = next(iter(identities)); groupkey = "sha256:" + digest
        subject["sequence_group_key"] = groupkey
        group = groups.setdefault(groupkey, dict(sequence_group_key=groupkey, digest=digest, molecule=molecule, length=length,
            subject_row_keys=[], member_keys=[], binding_indices=[]))
        _add_unique(group["subject_row_keys"], subject["row_key"])
        for i in subject["member_binding_indices"]:
            member = valid[i]; own = [m["sequence"] for m in _member_metadata(metadata, member) if m["sequence"]]
            reference = member["reference_identity"]
            demonstrated = any(s["sha256"] == digest and s["length"] == length and s["molecule"] == molecule for s in own)
            demonstrated |= reference is not None and reference["sequence_sha256"] == digest and reference["full_length"] == length
            if demonstrated:
                _add_unique(group["member_keys"], _member_key(member)); _add_unique(group["binding_indices"], i)
    grouped = sum(len(g["subject_row_keys"]) for g in groups.values())
    for group in groups.values():
        group.update(subject_count=_measure(len(group["subject_row_keys"]), "subject"), member_count=_measure(len(group["member_keys"]), "member"))
    return dict(groups=list(groups.values()), demonstrated_group_count=_measure(len(groups), "sequence_group"),
        grouped_subject_count=_measure(grouped, "subject"), ungrouped_subject_count=_measure(len(subjects) - grouped, "subject"),
        duplicate_subject_representations=_measure(grouped - len(groups), "subject"), complete_for_reported_subjects=grouped == len(subjects))


def _samples(sheet, membership, valid, datasets, metadata, issues):
    key = sheet["search"]["search_key"]; groups = {}; resolved = set()
    identity_sets = {}
    for dataset in datasets.values():
        for link in dataset["record"]["sample_links"]:
            identity_sets.setdefault(link["sample_key"], set()).add(_token(link["sample_identifier"]))
    conflicting_sample_keys = {k for k, ids in identity_sets.items() if len(ids) > 1}
    origin = {_token(m["member_key"]): m for m in membership["origin_members"]}
    for row in membership["catalogue_members"]:
        memberkey = row["member_key"]; token = _token(memberkey)
        members = [valid[i] for i in row["binding_indices"]]
        samplekeys = {m["sample_key"] for m in members if m["sample_key"] is not None}
        dataset = datasets[memberkey["dataset_key"]]["record"]
        links = [l for l in dataset["sample_links"] if l["sample_key"] in samplekeys]
        if len(samplekeys) != 1 or len(links) != 1:
            _add(issues, key, "sample_link_conflict" if len(samplekeys) > 1 else "sample_link_unavailable", member_key=memberkey); continue
        link = links[0]
        if link["sample_key"] in conflicting_sample_keys:
            _add(issues, key, "sample_link_conflict", sample_key=link["sample_key"]); continue
        candidates = [m for m in metadata if m["metadata_key"] in dataset["metadata_keys"] and m["entity"]["kind"] == "sample"
            and m["entity"]["dataset_key"] == dataset["dataset_key"] and m["entity"]["sample_key"] == link["sample_key"]
            and link["sample_identifier"] in m["identifiers"] and
            (link["biosample_identifier"] is None or link["biosample_identifier"] in m["identifiers"])]
        if not candidates or len(dataset["sample_links"]) > 1:
            # No member-specific demultiplexing adapter exists in this contract.
            _add(issues, key, "sample_link_unavailable", member_key=memberkey); continue
        skey = link["sample_key"]
        if skey in groups and groups[skey]["sample_identifier"] != link["sample_identifier"]:
            _add(issues, key, "sample_link_conflict", sample_key=skey); continue
        group = groups.setdefault(skey, dict(sample_key=skey, sample_identifier=deepcopy(link["sample_identifier"]),
            biosample_identifiers=[], dataset_keys=[], origin_member_keys=[], catalog_member_keys=[], origin_subject_row_keys=[], metadata_keys=[]))
        if link["biosample_identifier"] is not None:
            _add_unique(group["biosample_identifiers"], link["biosample_identifier"])
        _add_unique(group["dataset_keys"], dataset["dataset_key"]); _add_unique(group["catalog_member_keys"], memberkey)
        for m in candidates:
            _add_unique(group["metadata_keys"], m["metadata_key"])
        if token in origin:
            resolved.add(token); _add_unique(group["origin_member_keys"], memberkey)
            for rkey in origin[token]["row_keys"]:
                _add_unique(group["origin_subject_row_keys"], rkey)
    unresolved = len(origin) - len(resolved)
    return dict(groups=list(groups.values()), observed_origin_sample_count=_measure(sum(bool(g["origin_member_keys"]) for g in groups.values()), "sample"),
        catalog_sample_count=_measure(len(groups), "sample"), unresolved_origin_member_count=_measure(unresolved, "member"),
        complete_for_origin_members=unresolved == 0 and membership["complete_for_reported_subjects"])


def _taxonomy(sheet, subjects, sequence_groups, samples, valid, metadata, axis, issues):
    key = sheet["search"]["search_key"]; local = []; taxa = []; ranks = set(); per_subject = {}
    for subject in subjects:
        rowkey = subject["row_key"]; hit = rowkey["hit_ordinal"]
        taxids = set(); linked = []
        for d in subject["descriptions"]:
            if subject["source_locator"]["native_format"] == "json2":
                t = _positive(d["native_description"].get("taxid"))
                if t:
                    taxids.add(t)
            else:
                # Plural staxids are deliberately not paired to a description.
                for ordinal in d["source_locator"]["data_row_ordinals"] or []:
                    raw = sheet["search"]["native"]["search"]["rows"][ordinal].get("fields", {})
                    if re.fullmatch(r"[1-9][0-9]*", raw.get("staxid", "")):
                        taxids.add(int(raw["staxid"]))
        for i in subject["member_binding_indices"]:
            for m in _member_metadata(metadata, valid[i]):
                if m["taxid_scope"] in {"entity_organism", "reported_subject"} and m["taxid"] is not None:
                    taxids.add(m["taxid"]); _add_unique(linked, m)
        rankmap = {}
        for m in linked:
            seen = {}
            for row in m["lineage"]:
                seen.setdefault(row["rank"], set()).add(row["taxid"])
                ranks.add(row["rank"]); rankmap.setdefault(row["rank"], set()).add(row["taxid"])
            if any(len(v) > 1 for v in seen.values()):
                _add(local, key, "taxonomy_lineage_conflict", hit=hit, metadata_key=m["metadata_key"])
        if not taxids:
            _add(local, key, "taxonomy_scope_unavailable", hit=hit)
        taxa.append(dict(row_key=deepcopy(rowkey), taxids=sorted(taxids), metadata_keys=[m["metadata_key"] for m in linked],
                         status="available" if len(taxids) == 1 else "ambiguous" if taxids else "unavailable"))
        per_subject[_token(rowkey)] = rankmap
    sample_context = []
    for group in samples["groups"]:
        rows = [m for m in metadata if m["metadata_key"] in group["metadata_keys"] and m["taxid_scope"] == "sample_context"]
        sample_context.append(dict(sample_key=group["sample_key"], taxids=sorted({m["taxid"] for m in rows if m["taxid"] is not None}),
                                   metadata_keys=[m["metadata_key"] for m in rows]))
    target = sheet["target_context"]; query = sheet["query_binding"]
    target_valid = (target is not None and query is not None and target["query_operand"] == query["operand"]
        and axis["axis_kind"] == "sequence" and axis["full_length"] is not None and query["sequence_sha256"] is not None)
    targetmap = {}
    if target_valid:
        for row in target["lineage"]:
            targetmap.setdefault(row["rank"], set()).add(row["taxid"]); ranks.add(row["rank"])
        if any(len(v) > 1 for v in targetmap.values()):
            target_valid = False; _add(local, key, "taxonomy_lineage_conflict", target=True)
    if not target_valid:
        _add(local, key, "target_context_unbound")
    rankrows = []
    for rank in sorted(ranks):
        groupvalues = []
        for group in sequence_groups["groups"]:
            values = set()
            for rowkey in group["subject_row_keys"]:
                values.update(per_subject[_token(rowkey)].get(rank, set()))
            groupvalues.append(values)
        counts = Counter(next(iter(v)) for v in groupvalues if len(v) == 1)
        k = sum(counts.values()); same = sum(n * (n - 1) // 2 for n in counts.values()); pairs = k * (k - 1) // 2
        tv = targetmap.get(rank, set()) if target_valid else set()
        taxid = next(iter(tv)) if len(tv) == 1 else None
        matching = sum(v == {taxid} for v in groupvalues) if taxid is not None else None
        conflicting = sum(bool(v) and taxid not in v for v in groupvalues) if taxid is not None else None
        ambiguous = sum(taxid in v and len(v) > 1 for v in groupvalues) if taxid is not None else None
        rankrows.append(dict(rank=rank, taxon_group_counts=[dict(taxid=t, count=n) for t, n in sorted(counts.items())],
            unambiguous_group_count=k, ambiguous_group_count=sum(len(v) > 1 for v in groupvalues), unknown_group_count=sum(not v for v in groupvalues),
            same_taxon_pair_count=same, comparable_pair_count=pairs, same_taxon_pair_fraction=_ratio(same, pairs),
            different_taxon_pair_fraction=_ratio(pairs - same, pairs), target_taxid=taxid,
            target_matching_groups=matching, target_conflicting_groups=conflicting, target_ambiguous_groups=ambiguous,
            target_matching_fraction=_ratio(matching, matching + conflicting if matching is not None else None)))
    issues.extend(local)
    return dict(subject_taxa=taxa, sample_context=sample_context, sequence_group_ranks=rankrows,
        target_status="available" if target_valid else "incompatible" if target is not None else "unavailable",
        target_independent_of_search=target["independent_of_search"] if target is not None else None, issues=local)


def _quality(sheet, membership, metadata, issues):
    key = sheet["search"]["search_key"]; rows, local = [], []; covered = set()
    members = [r["member_key"] for r in membership["catalogue_members"]]
    for m in metadata:
        assembly = m["assembly"]
        if assembly is None:
            continue
        linked = [k for k in members if m["entity"]["kind"] == "member" and m["entity"]["dataset_key"] == k["dataset_key"]
                  and m["entity"]["member_identifier"] == k["member_identifier"]]
        if not linked or m["linkage_source"] is None:
            _add(local, key, "assembly_link_unavailable", metadata_key=m["metadata_key"]); continue
        cp, ct = assembly["completeness_percent"], assembly["contamination_percent"]
        cf = cp / 100 if cp is not None and 0 <= cp <= 100 else None
        tf = ct / 100 if ct is not None and ct >= 0 else None
        rows.append(dict(metadata_key=m["metadata_key"], dataset_key=m["entity"]["dataset_key"], member_keys=deepcopy(linked),
            assembly_identifier=deepcopy(assembly["identifier"]), method=assembly["method"], method_version=assembly["method_version"],
            completeness_fraction=_measure(cf, "fraction", "incompatible_input" if cp is not None else None),
            contamination_fraction=_measure(tf, "fraction", "incompatible_input" if ct is not None else None),
            contig_count=_measure(assembly["contig_count"], "contig"), contig_n50=_measure(assembly["contig_n50"], "nt"),
            total_sequence_length=_measure(assembly["total_sequence_length"], "nt"), source=deepcopy(assembly["source"]),
            linkage_source=deepcopy(assembly["linkage_source"])))
        covered.update(_token(k) for k in linked)
    missing = [k for k in members if _token(k) not in covered]
    issues.extend(local)
    return dict(records=rows, missing_member_keys=deepcopy(missing), issues=local)


def _codons(feature, member, metadata, datasets, key, issues, projection):
    """Construct exact ordered base triples using an explicitly selected code.

    The additive translation_map retains every computed triplet, terminal stop,
    and leading/trailing base in original member coordinates.
    """
    mid = feature["translation_metadata_key"]
    matches = [m for m in metadata if m["metadata_key"] == mid and m["entity"]["kind"] == "feature"
               and m["entity"]["dataset_key"] == member["dataset_key"] and m["entity"]["member_identifier"] == member["member_identifier"]
               and m["entity"]["feature_identifier"] == feature["feature_identifier"]]
    if len(matches) != 1 or matches[0]["feature"] is None:
        _add(issues, key, "feature_translation_missing", feature_identifier=feature["feature_identifier"]); return None
    meta = matches[0]; native = meta["feature"]
    projection["member_sequence_metadata_key"] = native["member_sequence_metadata_key"]
    if not native["translation"]:
        _add(issues, key, "feature_translation_missing", metadata_key=mid); return None
    fields = ("segments", "strand", "genetic_code", "codon_start")
    if any(native[k] != feature[k] for k in fields) or native["key"] != feature["feature_kind"]:
        _add(issues, key, "feature_location_conflict", metadata_key=mid); return None
    if (feature["location_status"] != "exact" or len(feature["segments"]) != 1 or feature["feature_kind"] != "CDS"
            or native["partial5"] is True or native["partial3"] is True or
            any(q["name"] in {"transl_except", "ribosomal_slippage", "exception"} for q in native["qualifiers"])):
        _add(issues, key, "feature_translation_unsupported", metadata_key=mid); return None
    code, start = feature["genetic_code"], feature["codon_start"]
    context = datasets[member["dataset_key"]]
    selected_code = context["record"]["search_context"]["subject_genetic_code"]
    if code is None or start is None or selected_code is None:
        _add(issues, key, "feature_code_missing", metadata_key=mid); return None
    if code != selected_code or not context["options_valid"]:
        _add(issues, key, "feature_code_conflict", metadata_key=mid, feature_code=code, selected_code=selected_code); return None
    source = [m for m in _member_metadata(metadata, member) if m["metadata_key"] == native["member_sequence_metadata_key"] and m["sequence"]]
    if len(source) != 1 or source[0]["sequence"]["molecule"] != "nt":
        _add(issues, key, "feature_sequence_unavailable", metadata_key=mid); return None
    sequence = source[0]["sequence"]; strand = feature["strand"]
    reference = member["reference_identity"]
    if reference is not None and ((reference["sequence_sha256"] is not None and reference["sequence_sha256"] != sequence["sha256"])
            or reference["full_length"] is not None and reference["full_length"] != sequence["length"]):
        _add(issues, key, "feature_sequence_unavailable", metadata_key=mid, member_sequence_conflict=True); return None
    if strand not in (-1, 1):
        _add(issues, key, "feature_strand_conflict", metadata_key=mid); return None
    a, b = feature["segments"][0]
    if b > sequence["length"]:
        _add(issues, key, "feature_location_conflict", metadata_key=mid); return None
    positions = list(range(a, b)) if strand == 1 else list(range(b - 1, a - 1, -1))
    fragment = sequence["symbols"][a:b]
    if strand == -1:
        fragment = str(Seq(fragment).reverse_complement())
    if feature["feature_sequence_sha256"] is not None and hashlib.sha256(fragment.encode("ascii")).hexdigest() != feature["feature_sequence_sha256"]:
        _add(issues, key, "feature_sequence_unavailable", metadata_key=mid, digest_conflict=True); return None
    projection["leading_untranslated_member_positions"] = positions[:start - 1]
    coding, positions = fragment[start - 1:], positions[start - 1:]
    try:
        table = CodonTable.unambiguous_dna_by_id[code]
        usable = len(coding) - len(coding) % 3
        translated = str(Seq(coding[:usable]).translate(table=code, cds=False))
    except (KeyError, ValueError):
        _add(issues, key, "feature_translation_unsupported", metadata_key=mid, genetic_code=code); return None
    supplied = "".join(native["translation"].split()).upper()
    projection["trailing_untranslated_member_positions"] = positions[usable:]
    projection["codons"] = [dict(ordinal=i, member_positions=positions[3*i:3*i+3],
        oriented_triplet=coding[3*i:3*i+3], translated_symbol=symbol,
        feature_residue_index=None, feature_symbol=None, terminal_stop=symbol == "*" and i == len(translated)-1)
        for i, symbol in enumerate(translated)]
    actual = translated[:-1] if translated.endswith("*") and len(translated) == len(supplied) + 1 else translated
    start_alternative = (len(actual) == len(supplied) and len(actual) > 0 and actual[1:] == supplied[1:]
                         and supplied[0] == "M" and coding[:3].replace("U", "T") in table.start_codons)
    if "*" in actual or actual != supplied and not start_alternative:
        projection.update(status="incompatible", unavailable_reason="incompatible_input")
        _add(issues, key, "feature_symbol_conflict", metadata_key=mid, calculated_translation=translated, supplied_translation=supplied); return None
    mapping = {tuple(positions[i * 3:i * 3 + 3]): (i, translated[i], supplied[i]) for i in range(len(supplied))}
    for i, symbol in enumerate(supplied):
        projection["codons"][i].update(feature_residue_index=i, feature_symbol=symbol)
    projection.update(status="available", unavailable_reason=None)
    # Native input retains all bases; explicit unmatched/terminal/start details
    # are attached only when a qualification is needed, never new observations.
    if start_alternative and actual != supplied:
        _add(issues, key, "feature_symbol_conflict", metadata_key=mid, alternative_start=True,
             search_symbol=actual[0], annotated_symbol=supplied[0], correspondence_retained=True)
    return mapping, len(supplied), strand


def _features(sheet, hsps, subjects, valid, metadata, datasets, issues):
    key = sheet["search"]["search_key"]; groups = {}
    for i, feature in enumerate(sheet["feature_bindings"]):
        member = valid.get(feature["member_binding_index"])
        token = _token([_member_key(member), feature["feature_identifier"]]) if member else _token([i])
        groups.setdefault(token, []).append((i, feature, member))
    output = []
    for entries in groups.values():
        indices = [e[0] for e in entries]; feature, member = entries[0][1:]; local = []
        if member is None:
            _add(issues, key, "feature_member_conflict", feature_binding_indices=indices); continue
        mkey = _member_key(member)
        hit_ordinals = {f["hit_ordinal"] for _, f, _ in entries}
        matching = [s for s in subjects if s["row_key"]["hit_ordinal"] in hit_ordinals]
        linked = (len(matching) == len(hit_ordinals) and all(
            m is not None and f["search_key"] == key == m["search_key"] and f["hit_ordinal"] == m["hit_ordinal"]
            and f["member_identifier"] == m["member_identifier"] and _member_key(m) == mkey
            for _, f, m in entries))
        # A feature instance can be reported through more than one native hit.
        # Original hit/binding ordinals identify those observations; they are
        # not part of the feature's biological location or translation identity.
        observation_fields = {"function", "provenance", "member_binding_index", "hit_ordinal"}
        shape = {k: v for k, v in feature.items() if k not in observation_fields}
        linked &= all({k: v for k, v in f.items() if k not in observation_fields} == shape for _, f, _ in entries)
        segments = feature["segments"]
        exact = (feature["location_status"] == "exact" and bool(segments)
                 and _length(segments) == sum(b - a for a, b in segments)
                 and [min(a for a, b in segments), max(b for a, b in segments)] == feature["member_interval"])
        if feature["strand"] in (1, -1):
            exact &= segments == sorted(segments, reverse=feature["strand"] == -1)
        if linked:
            exact &= all(s["coordinate_context"]["reference"]["reported_length"] is None
                or feature["member_interval"][1] <= s["coordinate_context"]["reference"]["reported_length"] for s in matching)
        if not linked:
            _add(local, key, "feature_member_conflict", feature_binding_indices=indices)
        if not exact:
            _add(local, key, "feature_location_unavailable", feature_binding_indices=indices)
        selected_hsps = [h for h in hsps if h["row_key"]["hit_ordinal"] in hit_ordinals] if linked else []
        translated = sheet["search"]["program_context"]["geometry_program"] == "tblastn" and feature["feature_kind"] == "CDS"
        translation_map = None
        if translated:
            translation_map = dict(status="unavailable", unavailable_reason="missing_input", member_sequence_metadata_key=None,
                translation_metadata_key=feature["translation_metadata_key"], genetic_code=feature["genetic_code"],
                codon_start=feature["codon_start"], strand=feature["strand"], leading_untranslated_member_positions=None,
                trailing_untranslated_member_positions=None, codons=[], issues=[])
        map_issues = []
        sequence_conflict = any(i["code"] == "blast_vdb_sequence_identity_conflict" and i["hit_ordinal"] in hit_ordinals for i in issues)
        if translated and sequence_conflict:
            _add(map_issues, key, "feature_sequence_unavailable", feature_binding_indices=indices, supplied_sequence_conflict=True)
        codons = _codons(feature, member, metadata, datasets, key, map_issues, translation_map) if linked and exact and translated and not sequence_conflict else None
        if translation_map is not None:
            translation_map["issues"] = deepcopy(map_issues)
            if any(i["code"] in {"blast_vdb_feature_code_conflict", "blast_vdb_feature_location_conflict", "blast_vdb_feature_symbol_conflict"}
                   and not i["details"].get("correspondence_retained") for i in map_issues):
                translation_map.update(status="incompatible", unavailable_reason="incompatible_input")
        local.extend(map_issues)
        hrows = []; overlap_intervals = []; subject_intervals = []; residues = set()
        complete = linked and exact and all(s["geometry_complete"] for s in matching)
        any_correspondence = False; translation_conflict = False
        for hsp in selected_hsps:
            own = []; available = exact and hsp["correspondence"]["geometry_status"] == "available"
            paired, aligned, qcount, cc, partial = [], [], 0, 0, 0
            matched, identical, substitutions = set(), 0, 0
            mapping_ok = codons is not None
            for column in hsp["correspondence"]["columns"] if available else []:
                reference = column["reference_interval"]
                if reference is None:
                    continue
                intersection = _intersect([reference], segments); n = _length(intersection)
                aligned.extend(intersection)
                if column["query_interval"] is None:
                    continue
                subject_intervals.append(reference); paired.extend(intersection)
                if column["alignment_unit"] == "nt":
                    qcount += n
                elif n == 3:
                    qcount += 1; cc += 1
                else:
                    partial += n
                if n and codons is not None:
                    mapping, _, strand = codons
                    direction = column["reference_direction"]
                    triplet = tuple(range(*reference)) if direction == 1 else tuple(range(reference[1] - 1, reference[0] - 1, -1))
                    if direction != strand:
                        _add(own, key, "feature_strand_conflict", hit=hsp["row_key"]["hit_ordinal"], hsp=hsp["row_key"]["hsp_ordinal"]); mapping_ok = False
                    elif triplet not in mapping:
                        _add(own, key, "feature_codon_phase_conflict", hit=hsp["row_key"]["hit_ordinal"], hsp=hsp["row_key"]["hsp_ordinal"], base_positions=list(triplet)); mapping_ok = False
                    else:
                        residue, search_symbol, feature_symbol = mapping[triplet]
                        if column["reference_symbol"].upper() != search_symbol:
                            _add(own, key, "feature_symbol_conflict", hit=hsp["row_key"]["hit_ordinal"], hsp=hsp["row_key"]["hsp_ordinal"], base_positions=list(triplet)); mapping_ok = False
                        else:
                            matched.add(residue)
                            if column["query_symbol"].upper() == feature_symbol:
                                identical += 1
                            else:
                                substitutions += 1
            if not mapping_ok:
                matched = set(); identical = substitutions = None
            elif available:
                any_correspondence |= bool(matched)
            translation_conflict |= bool(own)
            residues.update(matched); overlap_intervals.extend(paired)
            n = _length(paired) if available else None
            hrows.append(dict(row_key=deepcopy(hsp["row_key"]), paired_reference_overlap_nt=_measure(n, "nt"),
                aligned_reference_overlap_nt=_measure(_length(aligned) if available else None, "nt"),
                paired_query_overlap_units=_measure(qcount if available else None, hsp["native_components"]["coordinate_units"]["query"]),
                complete_paired_codons=_measure(cc if available and translated else None, "codon", "not_measured" if not translated else None),
                partial_codon_overlap_nt=_measure(partial if available and translated else None, "nt", "not_measured" if not translated else None),
                corresponding_feature_residues=_measure(len(matched) if mapping_ok and available else None, "aa", "not_measured" if not translated else None),
                identical_query_feature_residues=_measure(identical if mapping_ok and available else None, "aa", "not_measured" if not translated else None),
                substitutions_query_feature=_measure(substitutions if mapping_ok and available else None, "aa", "not_measured" if not translated else None), issues=own))
        n = _length(overlap_intervals) if linked and exact and (overlap_intervals or complete) else None
        length = _length(segments) if exact else None
        total_paired = _length(subject_intervals) if subject_intervals or complete else None
        functions = []
        feature_metadata = [m for m in metadata if m["entity"]["kind"] == "feature" and m["entity"]["dataset_key"] == mkey["dataset_key"]
            and m["entity"]["member_identifier"] == mkey["member_identifier"] and m["entity"]["feature_identifier"] == feature["feature_identifier"]]
        source_functions = [f["function"] for m in feature_metadata for f in m["functions"]]
        for _, f, _ in entries:
            if f["function"] is not None and f["function"] in source_functions:
                _add_unique(functions, f["function"])
        residue_complete = complete and codons is not None and not translation_conflict
        relation = "incompatible" if not linked else "unavailable" if not exact or n is None else "nonoverlap" if n == 0 and complete else "translated_correspondence" if any_correspondence and residue_complete else "overlap_only"
        local.extend(i for h in hrows for i in h["issues"])
        output.append(dict(feature_binding_indices=indices, member_key=mkey, feature_identifier=deepcopy(feature["feature_identifier"]),
            functions=functions, relation_status=relation, hsp_rows=hrows, translation_map=translation_map, paired_reference_overlap_nt=_measure(n, "nt"),
            feature_length_nt=_measure(length, "nt"), feature_paired_nt_coverage=_ratio(n, length, complete),
            paired_subject_fraction_in_feature=_ratio(n, total_paired, complete), corresponding_feature_residue_union=sorted(residues) if codons is not None and not translation_conflict else None,
            feature_translation_length=_measure(codons[1] if codons else None, "aa", "not_measured" if not translated else None),
            feature_paired_residue_coverage=_ratio(len(residues) if codons and not translation_conflict else None,
                codons[1] if codons else None, residue_complete, "not_measured" if not translated else None), issues=local))
        issues.extend(local)
    return output


def _entity(kind, *, member=None, group=None, feature=None, sample=None):
    return dict(kind=kind, member_key=deepcopy(member), sequence_group_key=group,
                feature_identifier=deepcopy(feature), sample_key=sample)


def _population(sheet, membership, sequences, samples, features, datasets, metadata, issues,
                *, report_unavailable_reason=None):
    key = sheet["search"]["search_key"]; output = []; local = []
    model = dict(status="unavailable", components=None, reason="vdb_function_weight_model_not_defined")
    if sheet["population_records"] is None:
        _add(local, key, "population_missing")
    units = {"reads": "read", "references": "reference", "wgs_sequences": "wgs_sequence",
             "unique_sequences": "unique_sequence", "features": "feature", "samples": "sample"}
    reporting = sheet["search"]["reporting"]
    report_complete = reporting["native_returncode"] == 0 and reporting["producer_complete"] is True and membership["complete_for_reported_subjects"]
    report_complete &= reporting["requested_hit_limit"] is None and reporting["requested_hsp_limit"] is None
    report_complete &= not any(i["code"] in {"blast_vdb_native_hsp_set_incomplete", "blast_hsp_object_required",
        "blast_hit_object_required", "blast_tabular_column_count_invalid", "blast_tabular_fields_unavailable_or_conflicting",
        "blast_tabular_subject_identifier_required"} for i in issues)
    for population in sheet["population_records"] or []:
        own = []; matched = []; scope_valid = True
        def fail(code, **details):
            nonlocal scope_valid
            _add(own, key, code, population_key=population["population_key"], **details); scope_valid = False
        if not population["datasets"]:
            fail("population_scope_mismatch")
        seen = set()
        for supplied in population["datasets"]:
            dkey = supplied["dataset_key"]
            if dkey not in datasets or dkey in seen:
                fail("population_scope_mismatch"); continue
            seen.add(dkey); actual = datasets[dkey]["record"]; context = actual["search_context"]
            if supplied["identifier"] is None or supplied["identifier"] != actual["identifier"]:
                fail("population_scope_mismatch", dataset_key=dkey)
            if supplied["snapshot"] != actual["snapshot"] or not any(v is not None for v in supplied["snapshot"].values()):
                fail("population_snapshot_unavailable", dataset_key=dkey)
            if (any(supplied[f] is None or context[f] is None or supplied[f] != context[f] for f in ("sra_mode", "include_filtered_reads"))
                    or not datasets[dkey]["options_valid"]):
                fail("population_filter_mismatch", dataset_key=dkey)
            matched.append(dkey)
        total = population["total_count"]; members = population["members"]; kind = units[population["count_unit"]]
        entity_complete = report_complete
        if kind == "unique_sequence":
            entity_complete &= sequences["complete_for_reported_subjects"]
        elif kind == "sample":
            entity_complete &= samples["complete_for_origin_members"]
        enumeration = {_token(e) for e in members} if members is not None else None
        if members is not None and (total is None or len(enumeration) != len(members) or len(enumeration) != total
                or any(e["kind"] != kind or e["member_key"] is not None and e["member_key"]["dataset_key"] not in seen for e in members)):
            fail("population_count_conflict")
        if not population["complete"]:
            _add(own, key, "population_partial", population_key=population["population_key"])
        observed = []
        if kind in {"read", "reference", "wgs_sequence"}:
            observed = [_entity(kind, member=r["member_key"]) for r in membership["origin_members"]
                if r["member_key"]["member_kind"] == kind and r["member_key"]["dataset_key"] in seen]
        elif kind == "unique_sequence":
            observed = [_entity(kind, group=g["sequence_group_key"]) for g in sequences["groups"]]
        elif kind == "sample":
            observed = [_entity(kind, sample=s["sample_key"]) for s in samples["groups"]
                        if any(m["dataset_key"] in seen for m in s["origin_member_keys"])]
        else:
            observed = [_entity(kind, member=f["member_key"], feature=f["feature_identifier"]) for f in features
                if f["member_key"]["dataset_key"] in seen and f["relation_status"] in {"overlap_only", "translated_correspondence"}
                and f["paired_reference_overlap_nt"]["value"] is not None and f["paired_reference_overlap_nt"]["value"] > 0]
        observed_set = {_token(e) for e in observed}
        numerator = (len(observed_set & enumeration)
                     if enumeration is not None and scope_valid and report_unavailable_reason is None else None)
        if enumeration is None:
            _add(own, key, "population_membership_unverified", population_key=population["population_key"])
        frows = []
        for function in population["function_counts"] or []:
            count = function["count"]; fvalid = scope_valid and total is not None and count <= total
            expected_scope = "feature" if kind == "feature" else "sample" if kind == "sample" else "whole_sequence"
            if function["assignment_scope"] != expected_scope:
                fvalid = False
                _add(own, key, "population_function_assignments_unavailable", population_key=population["population_key"],
                    function=function["function"], assignment_scope=function["assignment_scope"], count_unit=population["count_unit"])
            fmembers = [f["entities"] for f in population["function_members"] or [] if f["function"] == function["function"]]
            fset = {_token(e) for e in fmembers[0]} if len(fmembers) == 1 else None
            if count > (total if total is not None else count) or (fset is not None and
                    (len(fset) != count or len(fset) != len(fmembers[0]) or enumeration is None or not fset <= enumeration)):
                fvalid = False; _add(own, key, "population_count_conflict", population_key=population["population_key"], function=function["function"])
            assigned = set()
            if kind == "feature":
                assigned = {_token(_entity(kind, member=f["member_key"], feature=f["feature_identifier"])) for f in features
                            if function["function"] in f["functions"] and f["relation_status"] in {"overlap_only", "translated_correspondence"}
                            and (f["paired_reference_overlap_nt"]["value"] or 0) > 0}
            elif kind in {"read", "reference", "wgs_sequence"}:
                for entity in observed:
                    for m in _member_metadata(metadata, entity["member_key"]):
                        if any(a["function"] == function["function"] for a in m["functions"]):
                            assigned.add(_token(entity))
            elif kind == "sample":
                for entity in observed:
                    if any(m["entity"]["kind"] == "sample" and m["entity"]["sample_key"] == entity["sample_key"]
                           and any(a["function"] == function["function"] for a in m["functions"]) for m in metadata):
                        assigned.add(_token(entity))
            fn = (len(assigned & observed_set & fset)
                  if fvalid and fset is not None and assigned and report_unavailable_reason is None else None)
            if fn is None:
                _add(own, key, "population_function_assignments_unavailable", population_key=population["population_key"], function=function["function"])
            frows.append(dict(function=deepcopy(function["function"]), assignment_scope=function["assignment_scope"],
                population_function_count=_measure(count, population["count_unit"]),
                population_function_fraction=_ratio(count, total, population["complete"], None if fvalid else "incompatible_input"),
                observed_function_entity_count=_measure(fn, population["count_unit"], report_unavailable_reason),
                observed_fraction_of_function_population=_ratio(fn, count, entity_complete and population["complete"],
                    report_unavailable_reason or (None if fvalid else "incompatible_input"))))
        usable = scope_valid and total is not None
        complete = entity_complete and population["complete"]
        output.append(dict(population_key=population["population_key"], count_unit=population["count_unit"],
            status="incompatible" if not scope_valid else "available" if usable and numerator is not None and complete else "unavailable",
            matched_dataset_keys=matched, total_count=_measure(total, population["count_unit"]),
            observed_entity_count=_measure(numerator, population["count_unit"], report_unavailable_reason),
            observed_fraction_of_supplied_population=_ratio(numerator, total, complete,
                report_unavailable_reason or (None if usable else "incompatible_input")),
            function_components=frows, issues=own))
        local.extend(own)
    issues.extend(local)
    return dict(records=output, function_weight_model=model, issues=local)


def calculate_blast_vdb_components(sheet) -> dict:
    """Recalculate the accepted VDB component contract from a saved sheet only."""
    sheet = _copy(sheet); _validate_sheet(sheet)
    search = sheet["search"]; key = search["search_key"]
    issues = [_issue(i["code"], key=key, pointer=i.get("pointer"), original_issue=i) for i in search["issues"]]
    normalized, index, incomplete, native_ordinals, failure = _source_rows(sheet, issues)
    metadata = _metadata(sheet, issues); datasets = _datasets(sheet, issues)
    axis = _query_axis(sheet, datasets, metadata, issues)
    reporting = search["reporting"]
    actual_present = search["normalized"]["search"]["hit_array_present"]
    actual_count = search["normalized"]["search"]["reported_hit_count"]
    reporting_valid = reporting["native_hit_array_present"] == actual_present and reporting["native_hit_count"] == actual_count
    if not reporting_valid:
        _add(issues, key, "native_reporting_conflict")
    executed = reporting["native_returncode"] == 0 and reporting["producer_complete"] is True
    if not executed:
        _add(issues, key, "execution_completion_unqualified")
    zero = (failure is None and actual_present is True and actual_count == 0 and not native_ordinals
            and reporting_valid and executed and axis["full_length"] is not None)
    report_unavailable_reason = ("incompatible_input" if failure == "incompatible" else "missing_input"
                                 if failure or not index["hits"] and not zero else None)
    # Native ordinals include rejected JSON subjects; the retained-valid counts
    # remain the declared denominator, with missing siblings made explicit.
    retained_ordinals = {h["row_key"]["hit_ordinal"] for h in index["hits"]}
    rows_complete = (report_unavailable_reason is None and not incomplete
                     and retained_ordinals == set(native_ordinals))
    empty_normalized = {"hits": []}
    membership, valid = _members(sheet, normalized or empty_normalized, index, datasets, metadata, issues)
    membership["complete_for_reported_subjects"] &= rows_complete and reporting_valid and executed
    if report_unavailable_reason is not None:
        for field in ("reported_subject_count", "reported_hsp_count", "origin_bound_subject_count", "origin_unbound_subject_count", "origin_ambiguous_subject_count"):
            membership[field] = _measure(None, "hsp" if field == "reported_hsp_count" else "subject", report_unavailable_reason)
        for row in membership["counts_by_kind"]:
            row["catalog_member_count"] = _measure(None, "member", report_unavailable_reason)
            row["origin_member_count"] = _measure(None, "member", report_unavailable_reason)
    hsps, subjects = _geometry(sheet, normalized, index, incomplete, axis, valid, metadata, issues) if normalized is not None else ([], [])
    sequences = _sequence_groups(sheet, subjects, valid, metadata, issues)
    sequences["complete_for_reported_subjects"] &= rows_complete and reporting_valid and executed
    samples = _samples(sheet, membership, valid, datasets, metadata, issues)
    if report_unavailable_reason is not None:
        for field in ("demonstrated_group_count", "grouped_subject_count", "ungrouped_subject_count", "duplicate_subject_representations"):
            sequences[field] = _measure(None, "sequence_group" if field == "demonstrated_group_count" else "subject", report_unavailable_reason)
        for field in ("observed_origin_sample_count", "catalog_sample_count", "unresolved_origin_member_count"):
            samples[field] = _measure(None, "member" if field == "unresolved_origin_member_count" else "sample", report_unavailable_reason)
    taxonomy = _taxonomy(sheet, subjects, sequences, samples, valid, metadata, axis, issues)
    quality = _quality(sheet, membership, metadata, issues)
    features = _features(sheet, hsps, subjects, valid, metadata, datasets, issues)
    population = _population(sheet, membership, sequences, samples, features, datasets, metadata, issues,
                             report_unavailable_reason=report_unavailable_reason)
    if failure:
        status = failure
    elif not subjects:
        status = "no_reported_hits" if zero else "unavailable"
        if not zero:
            _add(issues, key, "native_zero_hit_unqualified")
    else:
        # Optional inputs do not invent applicability. Unknown feature/taxon/
        # population scope remains partial; the undefined model is excluded.
        required = (executed and reporting_valid and all(s["geometry_complete"] and s["full_member_coverage"]["value"] is not None
                    and s["selected_query_coverage"]["value"] is not None for s in subjects)
                    and membership["complete_for_reported_subjects"] and sequences["complete_for_reported_subjects"]
                    and samples["complete_for_origin_members"] and all(t["status"] == "available" for t in taxonomy["subject_taxa"])
                    and bool(features) and bool(population["records"]) and all(r["status"] == "available" for r in population["records"]))
        status = "complete" if required and not issues else "partial"
    return dict(schema="blast_vdb_components_v1", search_key=deepcopy(key), status=status, hsps=hsps, subjects=subjects,
        membership=membership, sequence_groups=sequences, sample_groups=samples, feature_components=features,
        taxonomy=taxonomy, source_quality=quality, population_components=population, issues=issues)
