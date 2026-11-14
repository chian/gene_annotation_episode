"""Pure, loss-aware collection of supplied original BLAST report artifacts.

No acquisition, execution, metadata join, scientific calculation or selection
occurs here. The caller retains exact bytes; this copied JSON projection keeps
their hashes, original report/search locations, and unfiltered native objects.
The single-query readers and API program allowlist remain unchanged.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
import math
import re
import zipfile

from . import blast_grading_inputs as _reader
from .blast_program_context import resolve_blast_program_context


SCHEMA = "blast_report_collection_v1"
_INVOCATION = {"execution_program", "scientific_mode", "resource_kind", "query_kind",
               "reference_kind", "request", "effective_options", "operands", "completion"}
_ARTIFACT = {"artifact_key", "role", "format", "fields", "delimiter"}
_OPERAND = {"role", "artifact_key", "record_ordinal", "native_id", "native_title",
            "subject_ref", "molecule", "length", "selected_interval", "identity"}
_REPORT_ROLES = {"primary_report", "tabular_report"}
_ROLES = _REPORT_ROLES | {"native_log", "query_pssm", "query_msa", "checkpoint"}
_FORMATS = {"json15", "json2", "json2_archive", "tabular6", "tabular7"}
_PROGRAM_HEADER = re.compile(r"([A-Z][A-Z0-9_-]+)\s+(\d\S*.*)")


def _json_copy(value):
    """Copy actual JSON values, rejecting Python-only shapes and nonfinite data."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_json_copy(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _json_copy(item) for key, item in value.items()}
    raise ValueError("blast_collection_finite_json_required")


def _keys(value, expected, code):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(code)


def _text(value, *, nullable=False):
    return value is None and nullable or isinstance(value, str) and bool(value.strip())


def _int(value, *, minimum=0, nullable=False):
    return value is None and nullable or type(value) is int and value >= minimum


def _issue(code, pointer="", field=None, **details):
    return {"code": code, "pointer": pointer, "field": field, "details": details}


def _contract(contents, artifacts, invocation):
    if not isinstance(contents, dict) or any(not _text(key) or type(raw) is not bytes
                                              for key, raw in contents.items()):
        raise ValueError("blast_collection_artifact_bytes_required")
    artifacts, invocation = _json_copy(artifacts), _json_copy(invocation)
    _keys(invocation, _INVOCATION, "blast_collection_invocation_fields_invalid")
    resolve_blast_program_context(**{key: invocation[key] for key in
        ("execution_program", "scientific_mode", "query_kind", "reference_kind")},
        reported_program=None, native_version=None)
    if invocation["resource_kind"] not in ("api", "local", "hpc"):
        raise ValueError("blast_collection_resource_kind_invalid")
    if not isinstance(invocation["request"], dict) or not isinstance(invocation["effective_options"], dict):
        raise ValueError("blast_collection_request_and_options_objects_required")
    for key in ("requested_hit_limit", "requested_hsp_limit"):
        if not _int(invocation["effective_options"].get(key), nullable=True):
            raise ValueError("blast_collection_requested_limit_invalid")
    completion = invocation["completion"]
    _keys(completion, {"native_returncode", "producer_complete"}, "blast_collection_completion_fields_invalid")
    if (completion["native_returncode"] is not None and type(completion["native_returncode"]) is not int
            or completion["producer_complete"] is not None and type(completion["producer_complete"]) is not bool):
        raise ValueError("blast_collection_completion_invalid")
    if not isinstance(invocation["operands"], list):
        raise ValueError("blast_collection_operands_array_required")
    for operand in invocation["operands"]:
        _keys(operand, _OPERAND, "blast_collection_operand_fields_invalid")
        if operand["role"] not in ("query", "subject", "database", "profile", "msa", "checkpoint"):
            raise ValueError("blast_collection_operand_role_invalid")
        if any(not _text(operand[key], nullable=True) for key in
               ("artifact_key", "native_id", "native_title", "subject_ref")):
            raise ValueError("blast_collection_operand_text_invalid")
        if not _int(operand["record_ordinal"], nullable=True) or not _int(operand["length"], minimum=1, nullable=True):
            raise ValueError("blast_collection_operand_ordinal_or_length_invalid")
        if operand["molecule"] not in ("dna", "rna", "protein", "unknown"):
            raise ValueError("blast_collection_operand_molecule_invalid")
        interval = operand["selected_interval"]
        if interval is not None and (not isinstance(interval, list) or len(interval) != 2
                or any(not _int(value) for value in interval) or interval[1] <= interval[0]
                or operand["length"] is not None and interval[1] > operand["length"]):
            raise ValueError("blast_collection_operand_interval_invalid")
        identity = operand["identity"]
        if identity is not None:
            _keys(identity, {"namespace", "value", "version"}, "blast_collection_identity_fields_invalid")
            if not _text(identity["namespace"]) or not _text(identity["value"]) or not _text(identity["version"], nullable=True):
                raise ValueError("blast_collection_identity_invalid")
    if not isinstance(artifacts, list):
        raise ValueError("blast_collection_artifacts_array_required")
    seen = set()
    for artifact in artifacts:
        _keys(artifact, _ARTIFACT, "blast_collection_artifact_fields_invalid")
        key = artifact["artifact_key"]
        if not _text(key) or key in seen:
            raise ValueError("blast_collection_artifact_key_invalid_or_duplicate")
        seen.add(key)
        if not isinstance(artifact["role"], str) or artifact["role"] not in _ROLES or not _text(artifact["format"]):
            raise ValueError("blast_collection_artifact_role_or_format_invalid")
        fields, delimiter = artifact["fields"], artifact["delimiter"]
        if fields is not None and (not isinstance(fields, list) or any(not _text(x) for x in fields)):
            raise ValueError("blast_collection_fields_invalid")
        if delimiter is not None and (not isinstance(delimiter, str) or len(delimiter) != 1
                                     or delimiter in "\r\n\x00"):
            raise ValueError("blast_collection_delimiter_invalid")
        if artifact["role"] in _REPORT_ROLES:
            if artifact["format"].startswith("json") and (fields is not None or delimiter is not None):
                raise ValueError("blast_collection_json_field_descriptor_conflict")
            if artifact["format"] == "tabular6" and fields is None:
                raise ValueError("blast_tabular_fields_required")
            if artifact["format"] in ("tabular6", "tabular7") and fields is not None:
                _reader._fields(fields)
                if invocation["execution_program"].endswith("_vdb") and any(x.lower() == "std" for x in fields):
                    raise ValueError("blast_vdb_explicit_tabular_fields_required")
    if set(contents) != seen:
        raise ValueError("blast_collection_contents_descriptor_keys_conflict")
    return artifacts, invocation


def _program_context(report, invocation, pointer, issues):
    values = {key: invocation[key] for key in
              ("execution_program", "scientific_mode", "query_kind", "reference_kind")}
    values.update(reported_program=report.get("program"), native_version=report.get("version"))
    invalid = False
    for field, native in (("reported_program", "program"), ("native_version", "version")):
        if values[field] is not None and not _text(values[field]):
            issues.append(_issue("blast_native_" + native + "_invalid", pointer + "/" + native, native))
            values[field], invalid = None, True
    try:
        result = resolve_blast_program_context(**values)
    except ValueError as error:
        field = "version" if "version" in str(error) else "program"
        issues.append(_issue(str(error), pointer + "/" + field, field))
        result = {**values, "geometry_program": None}
    if invalid:
        result["geometry_program"] = None
    return result


def _bind_query(query, invocation, pointer, issues, *, blocked=False):
    candidates, conflicts = [], []
    geometry = resolve_blast_program_context(**{key: invocation[key] for key in
        ("execution_program", "scientific_mode", "query_kind", "reference_kind")},
        reported_program=None, native_version=None)["geometry_program"]
    molecules = {"dna", "rna"} if geometry in ("blastn", "blastx", "tblastx") else {"protein"}
    for ordinal, operand in enumerate(invocation["operands"]):
        if operand["role"] != "query":
            continue
        identifier, title = query["id"], query["title"]
        names = {operand[key] for key in ("native_id", "native_title") if operand[key] is not None}
        if not any(value is not None and value in names for value in (identifier, title)):
            continue
        reasons = []
        if identifier is not None and operand["native_id"] is not None and identifier != operand["native_id"]:
            # NCBI emits these generated query identifiers alongside the actual
            # supplied title. Only this source-established case can use title.
            if (re.fullmatch(r"Query_\d+", identifier) is None
                    or re.fullmatch(r"Query_\d+", operand["native_id"]) is not None):
                reasons.append("native_id")
        if title is not None and operand["native_title"] is not None and title != operand["native_title"]:
            reasons.append("native_title")
        if query["length"] is not None and operand["length"] is not None and query["length"] != operand["length"]:
            interval = operand["selected_interval"]
            if interval is None or query["length"] != interval[1] - interval[0]:
                reasons.append("length")
        if operand["molecule"] != "unknown" and operand["molecule"] not in molecules:
            reasons.append("molecule")
        if reasons:
            conflicts.append({"operand_ordinal": ordinal, "fields": reasons})
        else:
            candidates.append(operand)
    if blocked:
        issues.append(_issue("blast_query_binding_incompatible_native_identity", pointer))
        return None
    if len(candidates) == 1:
        return deepcopy(candidates[0])
    code = "blast_query_binding_ambiguous" if len(candidates) > 1 else (
        "blast_query_binding_conflict" if conflicts else "blast_query_binding_unavailable")
    issues.append(_issue(code, pointer, conflicts=conflicts, matching_operands=len(candidates)))
    return None


def _reporting(invocation, present, count):
    return {"native_hit_array_present": present, "native_hit_count": count,
            "requested_hit_limit": invocation["effective_options"].get("requested_hit_limit"),
            "requested_hsp_limit": invocation["effective_options"].get("requested_hsp_limit"),
            **invocation["completion"]}


def _convert_issues(rows, pointer, issues):
    for row in rows:
        details = {key: value for key, value in row.items() if key not in ("code", "field")}
        issues.append(_issue(row["code"], pointer, row.get("field"), **details))


def _query(search, pointer, issues):
    rows = []
    query = _reader._query(search.get("query_id"), search.get("query_title"), search.get("query_len"), {}, rows)
    _convert_issues(rows, pointer, issues)
    return query


def _hsp(native, issues):
    # Native REAL scores must fit the shared reader's finite float operation.
    # A malformed, enormous JSON integer must not abort valid sibling searches.
    supplied = native
    if isinstance(native, dict):
        for field in _reader._SCORES:
            value = native.get(field)
            if type(value) is int:
                try:
                    math.isfinite(value)
                except OverflowError:
                    if supplied is native:
                        supplied = deepcopy(native)
                    supplied.pop(field)
                    issues.append({"code": "blast_hsp_field_invalid", "field": field})
    return _reader._hsp(supplied, issues)


def _json_search(document, report, native_search, *, key, invocation, raw_sha,
                 report_pointer, member_name=None, member_sha256=None, iteration=None, inherited=()):
    pointer, issues = key["search_pointer"], deepcopy(list(inherited))
    context = _program_context(report, invocation, report_pointer, issues)
    if not isinstance(native_search, dict):
        issues.append(_issue("blast_search_object_required", pointer, native=native_search))
        search = {}
    else:
        search = native_search
    query = _query(search, pointer, issues)
    hits, row_map = [], []
    native_hits = search.get("hits")
    present = isinstance(native_hits, list)
    if not present:
        issues.append(_issue("blast_hit_array_invalid" if "hits" in search else "blast_hit_array_not_reported", pointer + "/hits", "hits"))
    for hit_index, row in enumerate(native_hits if present else []):
        hit_pointer = pointer + f"/hits/{hit_index}"
        if not isinstance(row, dict):
            issues.append(_issue("blast_hit_object_required", hit_pointer))
            continue
        length = row.get("len")
        if length is not None and not _int(length, minimum=1):
            issues.append(_issue("blast_reference_length_invalid", hit_pointer + "/len", "len"))
            length = None
        hit = {"hit_index": hit_index, "length": length, "descriptions": [], "unpaired_metadata": {}, "hsps": []}
        mapping = {"hit_index": hit_index, "description_ordinals": [], "hsp_ordinals": []}
        for field, output, mapper, validator in (("description", "descriptions", "description_ordinals", _reader._description),
                                                 ("hsps", "hsps", "hsp_ordinals", _hsp)):
            values = row.get(field)
            if not isinstance(values, list):
                issues.append(_issue("blast_" + field + "_array_invalid_or_missing", hit_pointer + "/" + field, field))
                continue
            for ordinal, value in enumerate(values):
                row_issues = []
                normalized = validator(value, row_issues)
                _convert_issues(row_issues, hit_pointer + f"/{field}/{ordinal}", issues)
                if normalized is not None:
                    hit[output].append(normalized)
                    mapping[mapper].append(ordinal)
        hits.append(hit)
        row_map.append(mapping)
    target = report.get("search_target")
    if not isinstance(target, dict):
        issues.append(_issue("blast_search_target_object_invalid", report_pointer + "/search_target"))
        target = {}
        context["geometry_program"] = None
    if "subjects" in target and (not isinstance(target["subjects"], list)
            or not target["subjects"] or any(not _text(item) for item in target["subjects"])):
        issues.append(_issue("blast_search_subjects_array_invalid", report_pointer + "/search_target/subjects"))
        context["geometry_program"] = None
    mode = invocation["scientific_mode"]
    if (mode == "pairwise" and "db" in target or mode == "database" and "subjects" in target):
        issues.append(_issue("blast_pairwise_database_mode_conflict", report_pointer + "/search_target"))
        context["geometry_program"] = None
    database = target.get("db")
    if database is not None and not isinstance(database, str):
        issues.append(_issue("blast_database_text_invalid", report_pointer + "/search_target/db"))
        database = None
    if mode == "pairwise" and present and len(native_hits) > 1:
        issues.append(_issue("blast_single_pairwise_subject_required", pointer + "/hits"))
    params, stats = report.get("params", {}), search.get("stat", {})
    for name, value in (("params", params), ("stat", stats)):
        if not isinstance(value, dict):
            issues.append(_issue("blast_" + name + "_object_invalid", (report_pointer if name == "params" else pointer) + "/" + name))
    for container, loc in ((report, report_pointer), (search, pointer)):
        if "stage" in container:
            issues.append(_issue("blast_native_stage_semantics_unestablished", loc + "/stage", "stage"))
    binding = _bind_query(query, invocation, pointer, issues,
        blocked=any(item["code"] in ("blast_query_id_invalid", "blast_query_title_invalid", "blast_query_length_invalid")
                    for item in issues))
    normalized = {"schema": _reader.SCHEMA, "mode": mode, "resource": invocation["resource_kind"],
        "format": "json2", "query": query,
        "search": {"program": invocation["execution_program"], "version": context["native_version"],
                   "database": database, "parameters": deepcopy(params) if isinstance(params, dict) else {},
                   "statistics": deepcopy(stats) if isinstance(stats, dict) else {},
                   "request": deepcopy(invocation["request"]), "hit_array_present": present,
                   "reported_hit_count": len(native_hits) if present else None},
        "hits": hits, "native": {"document": deepcopy(document),
            "archive_member": {"ordinal": key["member_ordinal"], "name": member_name, "sha256": member_sha256}
                if key["member_ordinal"] is not None else None,
            "sha256": raw_sha}, "issues": deepcopy(issues)}
    return {"search_key": key, "program_context": context, "stage": None, "iteration": iteration,
            "normalized": normalized, "row_map": row_map, "operand_binding": binding,
            "reporting": _reporting(invocation, present, len(native_hits) if present else None),
            "native": {"report": deepcopy(report), "search": deepcopy(search), "line_numbers": None},
            "issues": issues}


def _read_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("blast_native_duplicate_json_key")
            result[key] = value
        return result
    try:
        return _json_copy(json.loads(raw, object_pairs_hook=pairs))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("blast_native_json_invalid") from error
    except (ValueError, RecursionError) as error:
        if str(error) in ("blast_native_duplicate_json_key", "blast_collection_finite_json_required"):
            raise
        raise ValueError("blast_native_json_invalid") from error


def _collect_document(document, *, artifact_key, member_ordinal, invocation, raw_sha, searches, issues,
                      member_name=None, member_sha256=None, inherited=()):
    def fail(code, pointer="", **details):
        issues.append({"artifact_key": artifact_key, "member_ordinal": member_ordinal,
                       **_issue(code, pointer, **details)})
    outer = document.get("BlastOutput2") if isinstance(document, dict) else None
    if not isinstance(outer, (list, dict)):
        fail("blast_report_document_layout_unsupported", native=document)
        return
    entries = outer if isinstance(outer, list) else [outer]
    if not entries:
        fail("blast_report_collection_empty", "/BlastOutput2")
    for report_index, entry in enumerate(entries):
        base = "/BlastOutput2" + (f"/{report_index}" if isinstance(outer, list) else "")
        if not isinstance(entry, dict) or not isinstance(entry.get("report"), dict):
            fail("blast_report_object_required", base, native=entry)
            continue
        report, report_pointer = entry["report"], base + "/report"
        results = report.get("results")
        if not isinstance(results, dict):
            fail("blast_results_object_required", report_pointer + "/results", native=report)
            continue
        branches = [name for name in results if name in ("search", "bl2seq", "iterations")]
        local = deepcopy(list(inherited))
        if len(branches) != 1 or set(results) - set(branches):
            issue = _issue("blast_results_layout_unsupported", report_pointer + "/results", native=results)
            local.append(issue)
            fail(issue["code"], issue["pointer"], native=report)
        for branch in branches:
            pointer = report_pointer + "/results/" + branch
            value = results[branch]
            if branch == "search":
                values = [(value, pointer, None, local)]
            elif not isinstance(value, list):
                fail("blast_" + branch + "_array_required", pointer, native=value)
                continue
            elif not value:
                fail("blast_search_collection_empty", pointer, native=value)
                continue
            elif branch == "bl2seq":
                extra = [] if invocation["scientific_mode"] == "pairwise" else [
                    _issue("blast_pairwise_database_mode_conflict", pointer)]
                values = [(search, pointer + f"/{ordinal}", None, local + extra) for ordinal, search in enumerate(value)]
            else:
                values, rounds = [], set()
                for ordinal, iteration in enumerate(value):
                    where = pointer + f"/{ordinal}"
                    if not isinstance(iteration, dict):
                        fail("blast_iteration_object_required", where, native=iteration)
                        continue
                    number, iter_issues = iteration.get("iter_num"), deepcopy(local)
                    if not _int(number, minimum=1):
                        iter_issues.append(_issue("blast_iteration_number_invalid", where + "/iter_num", "iter_num"))
                        number = None
                    elif number in rounds:
                        iter_issues.append(_issue("blast_iteration_number_duplicate", where + "/iter_num", "iter_num", value=number))
                    rounds.add(number)
                    values.append((iteration.get("search"), where + "/search", number, iter_issues))
            for native_search, where, number, inherited_issues in values:
                result = _json_search(document, report, native_search,
                    key={"artifact_key": artifact_key, "member_ordinal": member_ordinal,
                         "report_index": report_index, "search_pointer": where},
                    invocation=invocation, raw_sha=raw_sha, report_pointer=report_pointer, member_name=member_name,
                    member_sha256=member_sha256, iteration=number, inherited=inherited_issues)
                if any(row["code"] in ("blast_results_layout_unsupported", "blast_pairwise_database_mode_conflict")
                       for row in inherited_issues):
                    result["program_context"]["geometry_program"] = None
                searches.append(result)


def _archive(raw, artifact, invocation, searches, issues):
    key, documents, member_names = artifact["artifact_key"], [], {}
    artifact["members"] = []
    def fail(code, ordinal=None, pointer="", **details):
        issues.append({"artifact_key": key, "member_ordinal": ordinal, **_issue(code, pointer, **details)})
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for ordinal, info in enumerate(archive.infolist()):
                descriptor = {"member_ordinal": ordinal, "name": info.filename,
                              "size_bytes": info.file_size, "sha256": None}
                artifact["members"].append(descriptor)
                member_names.setdefault(info.filename, []).append(ordinal)
                try:
                    data = archive.read(info)
                except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, NotImplementedError) as error:
                    fail("blast_archive_member_unreadable", ordinal, error_type=type(error).__name__)
                    continue
                descriptor.update(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                try:
                    documents.append((ordinal, info.filename, _read_json(data)))
                except ValueError as error:
                    fail(str(error), ordinal)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        fail("blast_native_archive_invalid", error_type=type(error).__name__)
        return
    duplicates = {name for name, ordinals in member_names.items() if len(ordinals) > 1}
    for name in sorted(duplicates):
        fail("blast_archive_member_name_duplicate", name=name, member_ordinals=member_names[name])
    manifests = [(ordinal, doc) for ordinal, _, doc in documents if isinstance(doc, dict) and "BlastJSON" in doc]
    names = set()
    if len(manifests) > 1:
        fail("blast_archive_manifest_ambiguous")
    for ordinal, doc in manifests:
        rows = doc["BlastJSON"]
        if not isinstance(rows, list):
            fail("blast_archive_manifest_invalid", ordinal, "/BlastJSON", native=rows)
            continue
        for index, row in enumerate(rows):
            pointer = f"/BlastJSON/{index}"
            if not isinstance(row, dict) or not _text(row.get("File")):
                fail("blast_archive_manifest_entry_invalid", ordinal, pointer, native=row)
                continue
            name = row["File"]
            if name in names:
                fail("blast_archive_manifest_entry_duplicate", ordinal, pointer, name=name)
            names.add(name)
            if name not in member_names:
                fail("blast_archive_manifest_member_missing", ordinal, pointer, name=name)
    if not any(isinstance(doc, dict) and "BlastOutput2" in doc for _, _, doc in documents):
        fail("blast_archive_report_missing")
    for ordinal, name, document in documents:
        if isinstance(document, dict) and "BlastJSON" in document and "BlastOutput2" not in document:
            continue
        inherited = []
        if name in duplicates:
            inherited.append(_issue("blast_archive_member_name_duplicate", name=name, member_ordinals=member_names[name]))
        if manifests and name not in names:
            inherited.append(_issue("blast_archive_report_not_in_manifest", name=name))
        _collect_document(document, artifact_key=key, member_ordinal=ordinal, invocation=invocation,
            raw_sha=artifact["sha256"], searches=searches, issues=issues, member_name=name,
            member_sha256=artifact["members"][ordinal]["sha256"], inherited=inherited)


def _sections(text, artifact):
    """Retain contiguous query/round sections; never merge a repeated query."""
    sections, lines, has_query, has_data, query_id = [], [], False, False, None
    fields = _reader._fields(artifact["fields"]) if artifact["fields"] is not None else None
    delimiter = artifact["delimiter"] or "\t"
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        content = line.rstrip("\r\n")
        heading = content[1:].strip() if content.startswith("#") else None
        boundary = False
        if heading is not None:
            boundary = bool(_PROGRAM_HEADER.fullmatch(heading) and (has_query or has_data))
            boundary |= heading.startswith("Query:") and has_query
            boundary |= heading.startswith("Iteration:") and (has_query or has_data)
        elif content.strip():
            if artifact["format"] == "tabular6" and fields is not None:
                cells = content.split(delimiter)
                if len(cells) == len(fields):
                    row = dict(zip(fields, cells))
                    new_id = row.get("qseqid") or row.get("qaccver") or row.get("qacc")
                    if new_id and query_id is not None and new_id != query_id:
                        boundary = True
                    if new_id:
                        query_id = new_id
        if boundary:
            sections.append(lines)
            lines, has_query, has_data = [], False, False
        lines.append((number, line))
        has_query |= heading is not None and heading.startswith("Query:")
        has_data |= heading is None and bool(content.strip())
    if lines or not sections:
        sections.append(lines)
    return sections


def _tabular_control_messages_supported(text, artifact):
    """Recognize the source-defined report grammar, not a convergence state."""
    if artifact["format"] != "tabular7":
        return False
    headers = []
    for line in text.splitlines():
        if line.startswith("#"):
            match = _PROGRAM_HEADER.fullmatch(line[1:].strip())
            if match:
                headers.append((match.group(1), match.group(2)))
    return bool(headers) and all(program in {"PSIBLAST", "DELTABLAST"}
                                and version == "2.17.0+" for program, version in headers)


def _tabular_search(text, lines, artifact, invocation, ordinal, *, control_messages_supported=None):
    pointer, issues = f"/sections/{ordinal}", []
    declared = _reader._fields(artifact["fields"]) if artifact["fields"] is not None else None
    fields, delimiter = declared, artifact["delimiter"] or "\t"
    report, title, database, iteration, declared_rows = {}, None, None, None, None
    native_rows, hits, row_map, groups = [], [], [], {}
    query_ids, lengths, length_conflicts = set(), set(), set()
    invalid_rows, fields_conflict = 0, False
    if control_messages_supported is None:
        control_messages_supported = _tabular_control_messages_supported(text, artifact)
    for line_number, exact_line in lines:
        line = exact_line.rstrip("\r\n")
        if not line.strip():
            continue
        where = pointer + f"/lines/{line_number}"
        if line.startswith("#"):
            heading = line[1:].strip()
            if match := _PROGRAM_HEADER.fullmatch(heading):
                report.update(program=match.group(1), version=heading)
            elif heading.startswith("Query:"):
                title = heading[len("Query:"):].strip() or None
            elif heading.startswith("Database:"):
                database = heading[len("Database:"):].strip()
            elif heading.startswith("Iteration:"):
                value = heading[len("Iteration:"):].strip()
                if value.isascii() and value.isdigit() and int(value) > 0:
                    iteration = int(value)
                else:
                    issues.append(_issue("blast_iteration_number_invalid", where, "iteration"))
            elif heading.startswith("Fields:"):
                try:
                    header_fields = _reader._fields([x.strip() for x in heading[len("Fields:"):].split(",")])
                    if fields is not None and fields != header_fields:
                        fields_conflict = True
                        issues.append(_issue("blast_tabular_declared_fields_conflict", where, "fields"))
                    fields = header_fields
                except ValueError as error:
                    fields_conflict = True
                    issues.append(_issue(str(error), where, "fields"))
            elif match := re.fullmatch(r"(\d+) hits? found", heading):
                value = int(match.group(1))
                if declared_rows is not None and value != declared_rows:
                    issues.append(_issue("blast_tabular_hit_count_conflict", where))
                declared_rows = value
            continue
        cells = line.split(delimiter)
        if (control_messages_supported and not fields_conflict and fields is not None
                and {"qseqid", "sseqid"} <= set(fields)
                and len(cells) != len(fields)
                and exact_line in ("Search has CONVERGED!\n", "Search has CONVERGED!\r\n")):
            # Keep the complete message in original section/report text. It is
            # not an HSP row; convergence scope belongs to the separate extractor.
            continue
        hsp_ordinal = len(native_rows)
        native = {"line": line_number, "values": cells}
        native_rows.append(native)
        if fields is None or len(cells) != len(fields) or fields_conflict:
            invalid_rows += 1
            issues.append(_issue("blast_tabular_fields_unavailable_or_conflicting" if fields is None or fields_conflict
                                 else "blast_tabular_column_count_invalid", where,
                                 expected=len(fields) if fields is not None else None, actual=len(cells)))
            continue
        row = dict(zip(fields, cells))
        native["fields"] = deepcopy(row)
        identifier = row.get("qseqid") or row.get("qaccver") or row.get("qacc")
        if identifier:
            query_ids.add(identifier)
        elif title is None:
            issues.append(_issue("blast_tabular_query_identifier_required", where))
        numbers = {}
        for field in _reader._TAB_INTS | _reader._TAB_NUMBERS:
            if field in row:
                try:
                    numbers[field] = _reader._tab_number(row[field], field)
                except ValueError:
                    issues.append(_issue("blast_tabular_number_invalid", where, field))
        if numbers.get("qlen") is not None:
            lengths.add(numbers["qlen"])
        temporary = []
        try:
            subject_key, descriptions, unpaired = _reader._tab_descriptions(row, temporary, line_number)
        except ValueError as error:
            invalid_rows += 1
            issues.append(_issue(str(error), where))
            continue
        _convert_issues(temporary, where, issues)
        hsp = {native_field: numbers[field] if field in numbers else row[field]
               for field, native_field in _reader._TAB_HSP.items() if field in row
               and (field not in _reader._TAB_INTS | _reader._TAB_NUMBERS or numbers.get(field) is not None)}
        if row.get("frames"):
            pieces = row["frames"].split("/")
            try:
                if len(pieces) != 2:
                    raise ValueError("frame_pair_required")
                for field, value in zip(("query_frame", "hit_frame"), pieces):
                    number = _reader._tab_number(value, "qframe")
                    if field in hsp and hsp[field] != number:
                        raise ValueError("frame_conflict")
                    if number is not None:
                        hsp[field] = number
            except ValueError:
                hsp.pop("query_frame", None)
                hsp.pop("hit_frame", None)
                issues.append(_issue("blast_tabular_frames_invalid", where, "frames"))
        if row.get("sstrand") in ("plus", "minus", "Plus", "Minus"):
            hsp["hit_strand"] = row["sstrand"].title()
        temporary = []
        hsp = _reader._hsp(hsp, temporary)
        _convert_issues(temporary, where, issues)
        if subject_key not in groups:
            groups[subject_key] = len(hits)
            hits.append({"hit_index": len(hits), "length": numbers.get("slen"),
                         "descriptions": [], "unpaired_metadata": {}, "hsps": []})
            row_map.append({"hit_index": len(row_map), "description_ordinals": [], "hsp_ordinals": []})
        index = groups[subject_key]
        hit, mapping = hits[index], row_map[index]
        length = numbers.get("slen")
        if length is not None and hit["length"] is not None and length != hit["length"]:
            length_conflicts.add(subject_key)
            issues.append(_issue("blast_tabular_reference_length_conflict", where, "slen", hit_index=index))
        hit["length"] = None if subject_key in length_conflicts else hit["length"] or length
        for description in descriptions:
            if description not in hit["descriptions"]:
                mapping["description_ordinals"].append(len(hit["descriptions"]))
                hit["descriptions"].append(description)
        for field, values in unpaired.items():
            existing = hit["unpaired_metadata"].setdefault(field, [])
            existing.extend(value for value in values if value not in existing)
        hit["hsps"].append(hsp)
        mapping["hsp_ordinals"].append(hsp_ordinal)
    context = _program_context(report, invocation, pointer, issues)
    conflict = len(query_ids) > 1 or len(lengths) > 1
    if len(query_ids) > 1:
        issues.append(_issue("blast_tabular_query_identity_conflict", pointer, identifiers=sorted(query_ids)))
    if len(lengths) > 1:
        issues.append(_issue("blast_tabular_query_length_conflict", pointer, lengths=sorted(lengths)))
    query = {"id": next(iter(query_ids)) if len(query_ids) == 1 else None,
             "title": title, "length": next(iter(lengths)) if len(lengths) == 1 else None}
    binding = _bind_query(query, invocation, pointer, issues, blocked=conflict)
    if declared_rows is not None and declared_rows != len(native_rows):
        issues.append(_issue("blast_tabular_reported_row_count_mismatch", pointer, reported=declared_rows, observed=len(native_rows)))
    present = bool(native_rows) or declared_rows == 0
    if not present:
        issues.append(_issue("blast_tabular_empty_without_zero_hit_report", pointer))
    sequence_set = database is not None and database.startswith("User specified sequence set (Input:")
    mode = invocation["scientific_mode"]
    if (mode == "pairwise" and database is not None and not sequence_set or mode == "database" and sequence_set):
        issues.append(_issue("blast_pairwise_database_mode_conflict", pointer))
        context["geometry_program"] = None
    if mode == "pairwise" and len(hits) > 1:
        issues.append(_issue("blast_single_pairwise_subject_required", pointer))
    section_text = "".join(line for _, line in lines)
    native_search = {"text": section_text, "fields": fields, "rows": native_rows,
                     "declared_alignment_row_count": declared_rows}
    count = len(hits) if present and not invalid_rows else None
    normalized = {"schema": _reader.SCHEMA, "mode": mode, "resource": invocation["resource_kind"], "format": "tabular",
        "query": query, "search": {"program": invocation["execution_program"], "version": context["native_version"],
            "database": None if mode == "pairwise" else database, "parameters": {}, "statistics": {},
            "request": deepcopy(invocation["request"]), "hit_array_present": present, "reported_hit_count": count},
        "hits": hits, "native": {**deepcopy(native_search), "sha256": artifact["sha256"],
            "table_layout": {"format": artifact["format"],
                             "declared_fields": deepcopy(artifact["fields"]), "delimiter": delimiter}},
        "issues": deepcopy(issues)}
    return {"search_key": {"artifact_key": artifact["artifact_key"], "member_ordinal": None,
                           "report_index": 0, "search_pointer": pointer},
            "program_context": context, "stage": None, "iteration": iteration, "normalized": normalized,
            "row_map": row_map, "operand_binding": binding, "reporting": _reporting(invocation, present, count),
            "native": {"report": {"text": text, **report}, "search": native_search,
                       "line_numbers": [row["line"] for row in native_rows]}, "issues": issues}


def parse_blast_report_collection(contents, *, artifacts, invocation) -> dict:
    """Collect every supplied original search without executing or scoring it.

    Caller-contract defects raise explicit ValueError codes. Malformed native
    artifacts/searches remain qualified in collection/per-search issues while
    valid siblings survive. An unresolved program context has null geometry.
    JSON array ordinals and tabular section/data-row ordinals are never compacted.
    Unsupported formats and unestablished stage meanings remain explicit.
    """
    artifacts, invocation = _contract(contents, artifacts, invocation)
    searches, issues = [], []
    for artifact in artifacts:
        raw, key = contents[artifact["artifact_key"]], artifact["artifact_key"]
        artifact.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        if artifact["role"] not in _REPORT_ROLES:
            continue
        format_name = artifact["format"]
        if format_name not in _FORMATS:
            issues.append({"artifact_key": key, "member_ordinal": None,
                           **_issue("blast_report_format_unsupported", format=format_name)})
            continue
        if format_name == "json2_archive":
            _archive(raw, artifact, invocation, searches, issues)
        elif format_name in ("json2", "json15"):
            try:
                document = _read_json(raw)
            except ValueError as error:
                issues.append({"artifact_key": key, "member_ordinal": None, **_issue(str(error))})
                continue
            _collect_document(document, artifact_key=key, member_ordinal=None, invocation=invocation,
                raw_sha=artifact["sha256"], searches=searches, issues=issues)
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeError:
                issues.append({"artifact_key": key, "member_ordinal": None, **_issue("blast_tabular_utf8_required")})
                continue
            control_messages_supported = _tabular_control_messages_supported(text, artifact)
            for ordinal, lines in enumerate(_sections(text, artifact)):
                searches.append(_tabular_search(text, lines, artifact, invocation, ordinal,
                    control_messages_supported=control_messages_supported))
    return {"schema": SCHEMA, "invocation": invocation, "artifacts": artifacts,
            "searches": searches, "issues": issues}


__all__ = ["parse_blast_report_collection", "SCHEMA"]
