"""Deterministic profile-search measurements from saved, supplied-data sheets.

Native scores retain their precision and are never summed. Representative
identity is identical displayed pairs / paired displayed columns. Model/query
coverage uses unions of *paired* zero-based half-open intervals, in model
positions and original query aa/nt units respectively; incomplete geometry
keeps observed subset counts but no full-coverage value. Selected coverage
intersects that union with the supplied selected interval without offsetting
native coordinates. Margins are native bits minus actual same-model/release
thresholds, with no implied native category or probability.

The supplied model/function/dependence records remain explicit associations.
No sequence-population probability, taxonomy transfer, category weight,
independence multiplier, credit, or annotation calculation occurs here.
``target_context`` is retained by the input sheet and unused in this version.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math
import re

from . import blast_grading_inputs as _native
from . import blast_report_collection as _collection
from . import alignment_correspondence as _correspondence
from .blast_pairwise_grader import alignment_components
from .blast_profile_inputs import _validate_sheet
from .blast_program_context import resolve_blast_program_context


SCHEMA = "blast_profile_components_v1"
# Closed diagnostic categories. Wrapped collector/alignment issues retain their
# entire original objects in details, including the original codes and fields.
ISSUE_CODES = frozenset({
    "blast_profile_collector_issue", "blast_profile_alignment_issue",
    "blast_profile_program_context_unresolved", "blast_profile_program_context_conflict",
    "blast_profile_mode_incompatible", "blast_profile_search_key_conflict",
    "blast_profile_report_source_conflict", "blast_profile_archive_member_unverifiable",
    "blast_profile_archive_member_conflict", "blast_profile_stage_unavailable",
    "blast_profile_stage_incompatible", "blast_profile_stage_source_unavailable",
    "blast_profile_database_unavailable", "blast_profile_database_preparation_conflict",
    "blast_profile_database_identity_conflict", "blast_profile_database_identity_unavailable",
    "blast_profile_reported_database_conflict", "blast_profile_native_source_conflict",
    "blast_profile_row_map_conflict", "blast_profile_query_unbound",
    "blast_profile_query_binding_conflict", "blast_profile_query_digest_unavailable",
    "blast_profile_query_length_conflict", "blast_profile_selected_query_bounds_conflict",
    "blast_profile_model_record_missing", "blast_profile_description_unavailable",
    "blast_profile_native_description_conflict", "blast_profile_model_identifier_link_missing",
    "blast_profile_model_identifier_conflict", "blast_profile_model_binding_ambiguous",
    "blast_profile_model_binding_unavailable", "blast_profile_model_length_unavailable",
    "blast_profile_model_length_conflict", "blast_profile_threshold_unavailable",
    "blast_profile_threshold_conflict", "blast_profile_threshold_margin_nonfinite",
    "blast_profile_threshold_release_unavailable", "blast_profile_table_layout_unavailable",
    "blast_profile_table_layout_invalid", "blast_profile_table_layout_conflict",
    "blast_profile_geometry_incomplete", "blast_profile_function_model_missing",
    "blast_profile_relation_model_missing", "blast_profile_native_completion_unavailable",
    "blast_profile_hit_hsps_unavailable", "blast_profile_report_unavailable",
})


def _issue(key, code, *, hit=None, hsp=None, pointer=None, **details):
    assert code in ISSUE_CODES
    return {"code": code, "search_key": deepcopy(key), "hit_ordinal": hit,
            "hsp_ordinal": hsp, "source_pointer": pointer, "details": details}


def _positive(value):
    return value if type(value) is int and value > 0 else None


def _fraction(numerator, denominator, *, complete=True):
    return {"numerator": numerator, "denominator": denominator,
            "value": _correspondence._ratio(numerator, denominator) if complete else None,
            "unit": "fraction"}


def _row_key(key, hit, hsp=None, description=None):
    return {"search_key": deepcopy(key), "hit_ordinal": hit,
            "hsp_ordinal": hsp, "description_ordinal": description}


def _get(document, pointer):
    value = document
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise ValueError("array_pointer_invalid")
            value = value[int(part)]
        else:
            value = value[part]
    return value


def _collector_issues(search):
    key, result, seen = search["search_key"], [], []
    lines = search["native"].get("line_numbers") or []
    for original in search["issues"] + search["normalized"]["issues"]:
        if original in seen:
            continue
        seen.append(original)
        pointer = original.get("pointer") if isinstance(original, dict) else None
        hit = hsp = None
        if isinstance(pointer, str):
            suffix = pointer.removeprefix(key["search_pointer"])
            match = re.match(r"/hits/(\d+)(?:/hsps/(\d+))?", suffix)
            if match:
                hit = int(match[1])
                hsp = int(match[2]) if match[2] is not None else None
            elif match := re.fullmatch(r"/lines/(\d+)", suffix):
                number = int(match[1])
                if number in lines:
                    hsp = lines.index(number)
                    hit = next((row["hit_index"] for row in search["row_map"]
                                if hsp in row.get("hsp_ordinals", [])), None)
        result.append(_issue(key, "blast_profile_collector_issue", hit=hit, hsp=hsp,
                             pointer=pointer, native_issue=deepcopy(original)))
    return result


def _qualify_context(sheet, issues):
    search, source, binding = (sheet[x] for x in ("search", "report_source", "search_binding"))
    key, context = search["search_key"], search["program_context"]
    compatible, available, geometry = True, True, None

    def record(code, *, conflict=False, **details):
        nonlocal compatible, available
        issues.append(_issue(key, code, pointer=key["search_pointer"], **details))
        available = False
        compatible &= not conflict

    names = ("execution_program", "reported_program", "scientific_mode", "query_kind",
             "reference_kind", "native_version")
    try:
        resolved = resolve_blast_program_context(**{name: context[name] for name in names})
    except (KeyError, ValueError) as error:
        record("blast_profile_program_context_conflict", conflict=True, reason=str(error))
    else:
        if context.get("geometry_program") is None:
            record("blast_profile_program_context_unresolved")
        elif context != resolved:
            record("blast_profile_program_context_conflict", conflict=True)
        else:
            geometry = resolved["geometry_program"]
    program = context.get("execution_program")
    if (program not in ("rpsblast", "rpstblastn", "deltablast")
            or context.get("scientific_mode") != "database"
            or context.get("query_kind") != "sequence"
            or context.get("reference_kind") != ("sequence" if program == "deltablast" else "profile")):
        record("blast_profile_mode_incompatible", conflict=True)
    native_search = search["normalized"]["search"]
    if (native_search.get("program") != program
            or native_search.get("version") != context.get("native_version")
            or search["normalized"].get("mode") != context.get("scientific_mode")):
        record("blast_profile_program_context_conflict", conflict=True, component="normalized_search")
        geometry = None
    if binding["search_key"] != key:
        record("blast_profile_search_key_conflict", conflict=True, component="search_binding")
    if source["artifact_key"] != key["artifact_key"] or source["member_ordinal"] != key["member_ordinal"]:
        record("blast_profile_report_source_conflict", conflict=True)
    member = search["normalized"]["native"].get("archive_member")
    if key["member_ordinal"] is None:
        if member is not None or source["member_sha256"] is not None:
            record("blast_profile_archive_member_conflict", conflict=True)
    elif (not isinstance(member, dict) or member.get("sha256") is None
          or source["member_sha256"] is None):
        record("blast_profile_archive_member_unverifiable")
    elif member.get("ordinal") != key["member_ordinal"] or member["sha256"] != source["member_sha256"]:
        record("blast_profile_archive_member_conflict", conflict=True)
    if binding["stage"] is None:
        record("blast_profile_stage_unavailable")
    elif binding["stage"] != "domain_database":
        record("blast_profile_stage_incompatible", conflict=True)
    if binding["provenance"] is None:
        record("blast_profile_stage_source_unavailable")
    database = binding["database_identity"]
    if database is None:
        record("blast_profile_database_unavailable")
    else:
        preparation = database["preparation_type"]
        if preparation == "unknown":
            record("blast_profile_database_unavailable", field="preparation_type")
        elif preparation != ("delta" if program == "deltablast" else "rps"):
            record("blast_profile_database_preparation_conflict", conflict=True)
        # DELTA's report target can name its sequence database. Its domain
        # identity comes from the exact per-search source binding, not that
        # invocation-wide field. Normal RPS has only the profile target.
        reported = native_search.get("database")
        if program in ("rpsblast", "rpstblastn") and reported is not None and reported != database["value"]:
            record("blast_profile_reported_database_conflict", conflict=True,
                   reported=reported, supplied=database["value"])
    return geometry, available, compatible


def _source_rows(sheet, issues):
    """Revalidate original locations with the existing pure collector readers.

    This reparse uses supplied text/objects only. It does not repair a missing
    row_map or change the saved search. A contradicted map cannot qualify rows.
    """
    search, source = sheet["search"], sheet["report_source"]
    key, normalized = search["search_key"], search["normalized"]
    context, reporting = search["program_context"], search["reporting"]
    try:
        invocation = {name: context[name] for name in
                      ("execution_program", "scientific_mode", "query_kind", "reference_kind")}
        invocation.update(resource_kind=normalized["resource"], request=normalized["search"]["request"],
            effective_options={name: reporting.get(name) for name in ("requested_hit_limit", "requested_hsp_limit")},
            completion={name: reporting.get(name) for name in ("native_returncode", "producer_complete")},
            operands=[search["operand_binding"]] if search["operand_binding"] is not None else [])
        if normalized["format"] == "json2":
            document = normalized["native"]["document"]
            base = "/BlastOutput2" + (f"/{key['report_index']}" if isinstance(document["BlastOutput2"], list) else "")
            report_pointer = base + "/report"
            if (not key["search_pointer"].startswith(report_pointer + "/results/")
                    or not isinstance(document["BlastOutput2"], list) and key["report_index"] != 0):
                raise ValueError("report_index_pointer_conflict")
            suffix = key["search_pointer"][len(report_pointer + "/results/"):]
            if re.fullmatch(r"search|bl2seq/(0|[1-9][0-9]*)|iterations/(0|[1-9][0-9]*)/search", suffix) is None:
                raise ValueError("search_pointer_layout_invalid")
            native_iteration = (_get(document, key["search_pointer"].removesuffix("/search")).get("iter_num")
                                if suffix.startswith("iterations/") else None)
            if search["iteration"] != _positive(native_iteration):
                raise ValueError("native_iteration_label_conflict")
            report, native_search = _get(document, report_pointer), _get(document, key["search_pointer"])
            member = normalized["native"].get("archive_member") or {}
            expected = _collection._json_search(document, report, native_search, key=key,
                invocation=invocation, raw_sha=normalized["native"].get("sha256"),
                report_pointer=report_pointer, member_name=member.get("name"),
                member_sha256=member.get("sha256"), iteration=search["iteration"])
        else:
            match = re.fullmatch(r"/sections/(0|[1-9][0-9]*)", key["search_pointer"])
            if match is None or key["member_ordinal"] is not None or key["report_index"] != 0:
                raise ValueError("table_search_key_invalid")
            text = search["native"]["report"]["text"]
            layout = normalized["native"].get("table_layout")
            if layout is None:
                issues.append(_issue(key, "blast_profile_table_layout_unavailable", pointer=key["search_pointer"]))
                return [], {}, False
            if (not isinstance(layout, dict) or set(layout) != {"format", "declared_fields", "delimiter"}
                    or layout["format"] not in ("tabular6", "tabular7")
                    or not isinstance(layout["delimiter"], str) or len(layout["delimiter"]) != 1
                    or layout["delimiter"] in "\r\n\x00"):
                issues.append(_issue(key, "blast_profile_table_layout_invalid", pointer=key["search_pointer"]))
                return [], {}, False
            try:
                if layout["declared_fields"] is not None or layout["format"] == "tabular6":
                    _native._fields(layout["declared_fields"])
            except ValueError as error:
                issues.append(_issue(key, "blast_profile_table_layout_invalid", pointer=key["search_pointer"], reason=str(error)))
                return [], {}, False
            descriptor = {"artifact_key": key["artifact_key"], "format": layout["format"],
                "fields": layout["declared_fields"], "delimiter": layout["delimiter"],
                "sha256": normalized["native"].get("sha256")}
            section = int(match[1])
            sections = _collection._sections(text, descriptor)
            expected = _collection._tabular_search(text, sections[section], descriptor, invocation, section)
        if (expected["search_key"] != key or expected["native"] != search["native"]
                or expected["normalized"]["hits"] != normalized["hits"]
                or expected["normalized"]["query"] != normalized["query"]
                or expected["normalized"]["search"] != normalized["search"]
                or expected["operand_binding"] != search["operand_binding"]
                or normalized["format"] == "tabular" and expected["normalized"]["native"] != normalized["native"]
                or expected["reporting"] != reporting):
            raise ValueError("native_projection_conflict")
        # The collector retains malformed native tokens but sanitizes its
        # context fields to null. Reuse that exact rule so malformed program
        # text cannot erase independently readable HSP measurements.
        if any(expected["program_context"].get(name) != context.get(name) for name in
               ("execution_program", "reported_program", "scientific_mode", "query_kind", "reference_kind", "native_version")):
            raise ValueError("native_program_context_conflict")
        if expected["row_map"] != search["row_map"]:
            issues.append(_issue(key, "blast_profile_row_map_conflict", pointer=key["search_pointer"]))
            return [], {}, False
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
        code = ("blast_profile_table_layout_conflict" if normalized["format"] == "tabular"
                and str(error) == "native_projection_conflict" else "blast_profile_native_source_conflict")
        issues.append(_issue(key, code, pointer=key["search_pointer"],
                             reason=str(error)))
        return [], {}, False
    rows, descriptions = [], {}
    for hit, mapping in zip(normalized["hits"], search["row_map"]):
        ordinal = mapping["hit_index"]
        for description, d in zip(hit["descriptions"], mapping["description_ordinals"]):
            raw = (_get(normalized["native"]["document"], key["search_pointer"] + f"/hits/{ordinal}/description/{d}")
                   if normalized["format"] == "json2" else description)
            descriptions[(ordinal, d)] = {name: raw.get(name) for name in ("id", "accession", "title", "taxid")}
        for hsp, j in zip(hit["hsps"], mapping["hsp_ordinals"]):
            pointer = key["search_pointer"]
            lines = data_rows = None
            if normalized["format"] == "json2":
                pointer += f"/hits/{ordinal}/hsps/{j}"
                raw_hsp = _get(normalized["native"]["document"], pointer)
                applicable_descriptions = list(mapping["description_ordinals"])
            else:
                raw_hsp = search["native"]["search"]["rows"][j]
                lines, data_rows = [raw_hsp["line"]], [j]
                fields = raw_hsp.get("fields", {})
                direct, applicable_descriptions = [], []
                if any(fields.get(name) for name in ("sseqid", "sacc", "saccver")):
                    direct = _native._tab_descriptions(fields, [], raw_hsp["line"])[1][:1]
                for d in mapping["description_ordinals"]:
                    if direct and {name: direct[0].get(name) for name in ("id", "accession", "title", "taxid")} == descriptions[(ordinal, d)]:
                        applicable_descriptions.append(d)
            member = normalized["native"].get("archive_member") or {}
            locator = {"artifact_ref": source["artifact_ref"], "report_index": key["report_index"],
                "pointer": pointer, "search_key": deepcopy(key), "member_ordinal": key["member_ordinal"],
                "member_sha256": member.get("sha256"), "native_format": normalized["format"],
                "hit_index": ordinal, "description_index": None, "hsp_index": j,
                "line_numbers": lines, "data_row_ordinals": data_rows}
            rows.append({"hit": hit, "hsp": hsp, "native_hsp": raw_hsp, "ordinal": ordinal,
                "hsp_ordinal": j, "locator": locator, "descriptions": applicable_descriptions})
        if not hit["hsps"]:
            issues.append(_issue(key, "blast_profile_hit_hsps_unavailable", hit=ordinal,
                                 pointer=key["search_pointer"]))
    return rows, descriptions, True


def _query_lengths(sheet, geometry, issues):
    search, binding = sheet["search"], sheet["query_binding"]
    key, reported = search["search_key"], _positive(search["normalized"]["query"].get("length"))
    if binding is None or search["operand_binding"] is None:
        issues.append(_issue(key, "blast_profile_query_unbound", pointer=key["search_pointer"]))
        return reported, None, None
    operand = binding["operand"]
    expected_unit = "nt" if geometry == "blastx" else "aa"
    molecules = ("dna", "rna") if expected_unit == "nt" else ("protein",)
    if (operand != search["operand_binding"] or operand["role"] != "query"
            or operand["molecule"] not in molecules or binding["axis_kind"] != "sequence"
            or binding["coordinate_unit"] != expected_unit or geometry is None):
        issues.append(_issue(key, "blast_profile_query_binding_conflict", pointer=key["search_pointer"]))
        return reported, None, None
    full, selected = binding["full_length"], operand["selected_interval"]
    acceptable = {full} | ({_correspondence.interval_length(selected)} if selected is not None else set())
    if operand["length"] != full or reported is not None and reported not in acceptable:
        issues.append(_issue(key, "blast_profile_query_length_conflict", pointer=key["search_pointer"],
                             reported=reported, supplied=full))
        return reported, None, None
    if binding["sequence_sha256"] is None:
        issues.append(_issue(key, "blast_profile_query_digest_unavailable", pointer=key["search_pointer"]))
        # The exact original operand and its source-bound full length remain
        # usable coordinate facts. An absent sequence identity digest prevents
        # a biological publication claim, not arithmetic with that known length.
    return reported, full, deepcopy(selected)


def _database_match(selected, model):
    if selected is None:
        return "unavailable"
    if any(selected[name] != model[name] for name in ("namespace", "value", "preparation_type")):
        return "incompatible"
    missing = False
    for name in ("version", "release", "scope"):
        if selected[name] != model[name]:
            if selected[name] is not None and model[name] is not None:
                return "incompatible"
            missing = True
    # Same named database with no version/release does not establish the model
    # population used by this search, even when both missing values compare equal.
    if missing or selected["version"] is None and selected["release"] is None:
        return "unavailable"
    return "available"


def _identifier_match(identifier, description):
    """Literal identifiers or native gnl|namespace|value / version spellings.

    An arbitrary alias, a title, taxon, provenance pointer or similar score is
    never an identifier mapping. Native general-ID namespace spelling follows
    BLAST/NCBI Seq-id's gnl form; dotted versions must match when supplied.
    """
    value, version = identifier["value"], identifier["version"]
    candidates = [description[name] for name in ("id", "accession") if isinstance(description[name], str)]
    conflict = False
    for candidate in candidates:
        literal = candidate
        namespace = None
        if match := re.fullmatch(r"gnl\|([^|]+)\|([^|]+)\|?", candidate):
            namespace, candidate = match.groups()
        matches = literal == value or candidate == value or version is not None and candidate == value + "." + version
        if matches:
            if namespace is not None and namespace.casefold() != identifier["namespace"].casefold():
                conflict = True
                continue
            # A supplied version cannot contradict a version already carried
            # by the exact identifier. An unversioned spelling needs a source
            # record for the version; the frozen inputs do not provide that link.
            suffix = re.fullmatch(r"(.+)\.([0-9]+)", candidate)
            if version is not None and (suffix is None or suffix[2] != version):
                if suffix is not None:
                    conflict = True
                continue
            return "available"
        if version is not None and candidate.startswith(value + "."):
            conflict = True
    return "incompatible" if conflict else "unavailable"


def _bindings(sheet, descriptions, eligible, compatible, source_ok, issues):
    search, key = sheet["search"], sheet["search"]["search_key"]
    records = {row["profile_key"]: row for row in sheet["profile_records"]}
    result = []
    for index, binding in enumerate(sheet["profile_bindings"]):
        hit, description = binding["hit_ordinal"], binding["description_ordinal"]
        pointer = key["search_pointer"] + (f"/hits/{hit}/description/{description}"
                    if search["normalized"]["format"] == "json2" else "")
        status = "available" if eligible and source_ok else "unavailable" if compatible else "incompatible"
        local = []

        def mark(code, state, **details):
            nonlocal status
            status = state if status != "incompatible" else status
            local.append(_issue(key, code, hit=hit, pointer=pointer,
                                binding_index=index, description_ordinal=description, **details))

        record = records.get(binding["profile_key"])
        if binding["search_key"] != key:
            mark("blast_profile_search_key_conflict", "incompatible")
        if record is None:
            mark("blast_profile_model_record_missing", "unavailable", profile_key=binding["profile_key"])
        native = descriptions.get((hit, description))
        if native is None:
            mark("blast_profile_description_unavailable", "unavailable")
        elif native != binding["native_description"]:
            mark("blast_profile_native_description_conflict", "incompatible")
        if record is not None:
            match = _database_match(sheet["search_binding"]["database_identity"], record["database_identity"])
            if match != "available":
                mark("blast_profile_database_identity_conflict" if match == "incompatible" else
                     "blast_profile_database_identity_unavailable", match,
                     selected_database_identity=sheet["search_binding"]["database_identity"],
                     model_database_identity=record["database_identity"])
            if native is not None:
                match = _identifier_match(record["model_identifier"], native)
                if match != "available":
                    mark("blast_profile_model_identifier_conflict" if match == "incompatible" else
                         "blast_profile_model_identifier_link_missing", match)
        result.append({"binding": binding, "status": status, "issues": local})
        issues.extend(local)
    for hit in {row["binding"]["hit_ordinal"] for row in result}:
        plausible = [row for row in result if row["binding"]["hit_ordinal"] == hit and row["status"] == "available"]
        if len({row["binding"]["profile_key"] for row in plausible}) > 1:
            issue = _issue(key, "blast_profile_model_binding_ambiguous", hit=hit, pointer=key["search_pointer"],
                           profile_keys=list(dict.fromkeys(row["binding"]["profile_key"] for row in plausible)))
            issues.append(issue)
            for row in plausible:
                row["status"] = "ambiguous"
                row["issues"].append(issue)
    return result


def _union(intervals):
    result = []
    for start, end in sorted(set(tuple(row) for row in intervals)):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def _intersection(left, right):
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        a, b = left[i], right[j]
        if max(a[0], b[0]) < min(a[1], b[1]):
            result.append([max(a[0], b[0]), min(a[1], b[1])])
        if a[1] < b[1]:
            i += 1
        else:
            j += 1
    return result


def _size(intervals):
    return _correspondence.interval_union_length(intervals)


def _threshold(record, name, records):
    identity = record["model_identifier"]
    related = [row for row in records if row["model_identifier"] == identity
               and _database_match(record["database_identity"], row["database_identity"]) == "available"]
    values = {row[name] for row in related if row[name] is not None}
    return (None, "conflict") if len(values) > 1 else (record[name], "unavailable" if record[name] is None else None)


def calculate_blast_profile_components(sheet) -> dict:
    """Recalculate inspectable v1 quantities without any I/O or model calls."""
    sheet = _validate_sheet(sheet)
    search, key = sheet["search"], sheet["search"]["search_key"]
    issues = _collector_issues(search)
    geometry, eligible, compatible = _qualify_context(sheet, issues)
    rows, descriptions, source_ok = _source_rows(sheet, issues)
    reported, full, selected = _query_lengths(sheet, geometry, issues)
    bindings = _bindings(sheet, descriptions, eligible, compatible, source_ok, issues)
    records = {row["profile_key"]: row for row in sheet["profile_records"]}
    hsps, row_complete = [], {}
    qunit = "nt" if search["program_context"].get("execution_program") == "rpstblastn" else "aa"
    for row in rows:
        hit, j, pointer = row["ordinal"], row["hsp_ordinal"], row["locator"]["pointer"]
        local = []
        components = alignment_components(row["hsp"], program=geometry, query_length=full or reported,
            reference_length=row["hit"]["length"],
            coordinate_convention="blast_json2" if search["normalized"]["format"] == "json2" else "directional")
        for original in components["issues"]:
            local.append(_issue(key, "blast_profile_alignment_issue", hit=hit, hsp=j,
                                pointer=pointer, native_issue=deepcopy(original)))
        complete = components["geometry_available"]
        if complete and selected is not None and any(pair["query_start"] < selected[0] or pair["query_end"] > selected[1]
                                                     for pair in components["pairs"]):
            complete = False
            local.append(_issue(key, "blast_profile_selected_query_bounds_conflict", hit=hit, hsp=j,
                                pointer=pointer, selected_interval=selected))
        row_complete[(hit, j)] = complete
        matches = []
        selected_bindings = [item for item in bindings if item["binding"]["hit_ordinal"] == hit
                             and item["binding"]["description_ordinal"] in row["descriptions"]]
        for profile_key in dict.fromkeys(item["binding"]["profile_key"] for item in selected_bindings):
            associations = [item for item in selected_bindings if item["binding"]["profile_key"] == profile_key]
            states = {item["status"] for item in associations}
            state = next((value for value in ("ambiguous", "incompatible", "available", "unavailable") if value in states))
            record = records.get(profile_key)
            match = {"profile_key": profile_key, "binding_status": state,
                     "model_columns": record["num_columns"] if record is not None and state == "available" else None}
            local.extend(issue for item in associations for issue in item["issues"] if issue not in local)
            for prefix in ("specific", "reporting"):
                name = prefix + "_bits_threshold"
                threshold, reason = _threshold(record, name, sheet["profile_records"]) if record is not None else (None, None)
                if reason:
                    local.append(_issue(key, "blast_profile_threshold_" + reason, hit=hit, hsp=j,
                                        pointer=pointer, profile_key=profile_key, field=name))
                bits = components["native_scores"]["bit_score"]
                selected_database = sheet["search_binding"]["database_identity"]
                same_release = (record is not None and selected_database is not None
                    and record["database_identity"]["release"] is not None
                    and record["database_identity"]["release"] == selected_database["release"])
                if threshold is not None and not same_release:
                    local.append(_issue(key, "blast_profile_threshold_release_unavailable", hit=hit, hsp=j,
                        pointer=pointer, profile_key=profile_key, field=name,
                        selected_release=selected_database["release"] if selected_database is not None else None,
                        model_release=record["database_identity"]["release"] if record is not None else None))
                margin = (bits - threshold if state == "available" and same_release
                          and bits is not None and threshold is not None else None)
                if type(margin) is float and not math.isfinite(margin):
                    margin = None
                    local.append(_issue(key, "blast_profile_threshold_margin_nonfinite", hit=hit, hsp=j,
                                        pointer=pointer, profile_key=profile_key, field=name))
                match[name], match[prefix + "_bits_margin"] = threshold, margin
            matches.append(match)
        if not selected_bindings:
            local.append(_issue(key, "blast_profile_model_binding_unavailable", hit=hit, hsp=j, pointer=pointer))
        counts = components["counts"]
        hsps.append({"row_key": _row_key(key, hit, j), "source_locator": row["locator"],
            "native_hsp": deepcopy(row["native_hsp"]), "geometry_program": geometry,
            "query_axis_kind": "sequence", "reference_axis_kind": "profile_model", "native_components": components,
            "reported_query_length": reported, "full_query_length": full, "selected_query_interval": selected,
            "reported_model_length": row["hit"]["length"],
            "representative_symbol_identity": {
                "numerator": counts["identical_pairs"] if eligible else None,
                "denominator": counts["paired_columns"] if eligible else None,
                "value": components["fractions"]["paired_identity"] if eligible else None,
                "unit": "fraction"},
            "model_matches": matches, "issues": local})
        issues.extend(issue for issue in local if issue not in issues)
    models = []
    for profile_key, record in records.items():
        associated = [item for item in bindings if item["binding"]["profile_key"] == profile_key]
        established = [hsp for hsp in hsps if any(match["profile_key"] == profile_key and match["binding_status"] == "available"
                                               for match in hsp["model_matches"])]
        states = {item["status"] for item in associated}
        state = ("available" if established else next((value for value in ("ambiguous", "incompatible", "unavailable")
                                                        if value in states), "unavailable"))
        local = [issue for item in associated for issue in item["issues"]]
        mapped = [hsp for hsp in established if hsp["native_components"]["geometry_available"]]
        query_intervals = _union([[p["query_start"], p["query_end"]] for hsp in mapped for p in hsp["native_components"]["pairs"]])
        model_intervals = _union([[p["reference_start"], p["reference_end"]] for hsp in mapped for p in hsp["native_components"]["pairs"]])
        complete = bool(established) and all(row_complete[(hsp["row_key"]["hit_ordinal"], hsp["row_key"]["hsp_ordinal"])] for hsp in established)
        # A skipped malformed HSP in a bound hit prevents an observed subset
        # from becoming complete model coverage. Its original issue is retained.
        bound_hits = {hsp["row_key"]["hit_ordinal"] for hsp in established}
        if search["normalized"]["format"] == "json2":
            native_hits = search["native"]["search"].get("hits", [])
            if any(not isinstance(hit, dict) for hit in native_hits):
                # An unreadable hit has no established model identity.
                complete = False
            for hit in bound_hits:
                native_hsps = _get(search["normalized"]["native"]["document"], key["search_pointer"] + f"/hits/{hit}/hsps")
                actual = [hsp for hsp in established if hsp["row_key"]["hit_ordinal"] == hit]
                complete &= len(actual) == len(native_hsps)
        elif len(rows) != len(search["native"]["search"]["rows"]):
            # A malformed table row has no trustworthy model association.
            # It might add paired positions to any currently bound model.
            complete = False
        if any(item["status"] != "available" for item in associated):
            complete = False
        lengths = list(dict.fromkeys(hsp["reported_model_length"] for hsp in established if hsp["reported_model_length"] is not None))
        columns = record["num_columns"] if state == "available" else None
        model_denominator = columns
        if state == "available":
            if columns is None or not lengths or any(hsp["reported_model_length"] is None for hsp in established):
                model_denominator = None
                local.append(_issue(key, "blast_profile_model_length_unavailable", profile_key=profile_key))
            elif any(length != columns for length in lengths):
                model_denominator = None
                local.append(_issue(key, "blast_profile_model_length_conflict", profile_key=profile_key,
                                    reported_model_lengths=lengths, model_columns=columns))
            if not complete:
                local.append(_issue(key, "blast_profile_geometry_incomplete", profile_key=profile_key))
        qcount, mcount = (_size(query_intervals), _size(model_intervals)) if mapped else (None, None)
        selected_count = _size(_intersection(query_intervals, [selected])) if mapped and selected is not None else None
        models.append({"profile_key": profile_key, "profile_record": deepcopy(record), "binding_status": state,
            "row_keys": [deepcopy(hsp["row_key"]) for hsp in established], "reported_model_lengths": lengths,
            "geometry_complete": complete, "observed_paired_query_intervals": query_intervals,
            "observed_paired_model_intervals": model_intervals, "paired_query_units": qcount,
            "paired_model_positions": mcount, "query_coverage": _fraction(qcount, full, complete=complete),
            "selected_query_coverage": _fraction(selected_count, _correspondence.interval_length(selected),
                                                 complete=complete),
            "model_coverage": _fraction(mcount, model_denominator, complete=complete),
            "query_unit": qunit, "model_unit": "position", "issues": local})
        issues.extend(issue for issue in local if issue not in issues)
    functions = {}
    by_model = {row["profile_key"]: row for row in models}
    for index, binding in enumerate(sheet["function_bindings"]):
        model = by_model.get(binding["profile_key"])
        if model is None:
            issues.append(_issue(key, "blast_profile_function_model_missing", binding_index=index,
                                 profile_key=binding["profile_key"]))
            continue
        function_key = (binding["function"]["namespace"], binding["function"]["value"])
        item = functions.setdefault(function_key, {"function": deepcopy(binding["function"]),
                                      "profile_keys": [], "hsp_row_keys": [], "binding_indices": []})
        if binding["profile_key"] not in item["profile_keys"]:
            item["profile_keys"].append(binding["profile_key"])
        item["hsp_row_keys"].extend(row for row in model["row_keys"] if row not in item["hsp_row_keys"])
        item["binding_indices"].append(index)
    dependence_issues = []
    for index, relation in enumerate(sheet["model_relations"]):
        missing = [relation[field] for field in ("left_profile_key", "right_profile_key") if relation[field] not in records]
        if missing:
            dependence_issues.append(_issue(key, "blast_profile_relation_model_missing", relation_index=index,
                                            missing_profile_keys=missing))
    overlaps = []
    for left, right in combinations([row for row in models if row["binding_status"] == "available"
                                    and row["paired_query_units"] is not None], 2):
        overlaps.append({"left_profile_key": left["profile_key"], "right_profile_key": right["profile_key"],
            "paired_query_overlap_units": _size(_intersection(left["observed_paired_query_intervals"], right["observed_paired_query_intervals"])),
            "query_unit": qunit, "complete_for_reported_hsps": left["geometry_complete"] and right["geometry_complete"]})
    issues.extend(dependence_issues)
    reporting = search["reporting"]
    completed = reporting.get("producer_complete") is True and reporting.get("native_returncode") == 0
    if not completed:
        issues.append(_issue(key, "blast_profile_native_completion_unavailable", pointer=key["search_pointer"],
                             producer_complete=reporting.get("producer_complete"), native_returncode=reporting.get("native_returncode")))
    if not compatible:
        status = "incompatible"
    elif not source_ok:
        status = "unavailable" if any(issue["code"] == "blast_profile_table_layout_unavailable" for issue in issues) else "incompatible"
    elif not eligible:
        status = "unavailable"
    elif not hsps:
        if (completed and reporting.get("native_hit_array_present") is True
                and reporting.get("native_hit_count") == 0 and not search["normalized"]["hits"]):
            status = "no_reported_hits"
        else:
            status = "unavailable"
            issues.append(_issue(key, "blast_profile_report_unavailable", pointer=key["search_pointer"]))
    else:
        status = "partial" if issues else "complete"
    return {"schema": SCHEMA, "search_key": deepcopy(key), "status": status, "hsps": hsps, "models": models,
        "function_components": list(functions.values()),
        "dependence": {"relations": deepcopy(sheet["model_relations"]), "query_overlaps": overlaps, "issues": dependence_issues},
        "taxonomy": {"status": "unavailable", "population": "model_training_sequences", "components": None,
                     "reason": "model_training_membership_not_supplied"}, "issues": issues}


__all__ = ["calculate_blast_profile_components", "SCHEMA", "ISSUE_CODES"]
