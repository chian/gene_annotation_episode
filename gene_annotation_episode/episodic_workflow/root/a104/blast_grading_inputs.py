"""Loss-aware native BLAST readers for tool-facing scoring sheets.

These functions parse already acquired bytes. They neither run BLAST nor fetch
metadata. JSON2/JSON15 share NCBI's BlastOutput2 schema. Tabular data needs its
declared column names: sorted taxon/name sets are never zipped to accession sets.

Format authorities:
https://www.ncbi.nlm.nih.gov/IEB/ToolBox/CPP_DOC/asn_spec/blastxml2.asn.html
https://www.ncbi.nlm.nih.gov/books/NBK279684/
https://www.ncbi.nlm.nih.gov/sites/books/NBK569862/
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
import math
import re
import zipfile

from .blast_search import PROGRAM_UNITS


SCHEMA = "blast_normalized_result_v1"
_MODES = {"pairwise", "database"}
_RESOURCES = {"api", "hpc", "local"}
_INT_MIN = {"query_from": 1, "query_to": 1, "hit_from": 1, "hit_to": 1,
            "identity": 0, "positive": 0, "align_len": 1, "gaps": 0,
            "num": 0, "density": 0}
_SCORES = {"bit_score", "score", "evalue"}
_STRINGS = {"qseq", "hseq", "midline"}

STANDARD_TABULAR_FIELDS = ["qseqid", "sseqid", "pident", "length", "mismatch",
    "gapopen", "qstart", "qend", "sstart", "send", "evalue", "bitscore"]

# NCBI's '# Fields:' display labels, not an inferred column order.
_LABELS = {
    "query id": "qseqid", "query gi": "qgi", "query acc.": "qacc",
    "query acc.ver": "qaccver", "query length": "qlen",
    "subject id": "sseqid", "subject ids": "sallseqid", "subject gi": "sgi",
    "subject gis": "sallgi", "subject acc.": "sacc", "subject acc.ver": "saccver",
    "subject accs": "sallacc", "subject accs.": "sallacc", "subject length": "slen",
    "q. start": "qstart", "q. end": "qend", "s. start": "sstart", "s. end": "send",
    "query seq": "qseq", "subject seq": "sseq", "evalue": "evalue",
    "e-value": "evalue", "bit score": "bitscore", "score": "score",
    "alignment length": "length", "% identity": "pident", "identical": "nident",
    "mismatches": "mismatch", "positives": "positive", "gap opens": "gapopen",
    "gaps": "gaps", "% positives": "ppos", "query/sbjct frames": "frames",
    "query frame": "qframe", "sbjct frame": "sframe", "btop": "btop",
    "subject tax ids": "staxids", "subject sci names": "sscinames",
    "subject com names": "scomnames", "subject blast names": "sblastnames",
    "subject super kingdoms": "sskingdoms", "subject title": "stitle",
    "subject titles": "salltitles", "subject strand": "sstrand",
    "% query coverage per subject": "qcovs", "% query coverage per hsp": "qcovhsp",
    "% query coverage per unique subject": "qcovus",
}
_TAB_HSP = {"bitscore": "bit_score", "score": "score", "evalue": "evalue",
    "nident": "identity", "positive": "positive", "length": "align_len",
    "gaps": "gaps", "qstart": "query_from", "qend": "query_to",
    "sstart": "hit_from", "send": "hit_to", "qframe": "query_frame",
    "sframe": "hit_frame", "qseq": "qseq", "sseq": "hseq",
    "pident": "identity_percent", "qcovhsp": "query_coverage_percent",
    "qcovs": "query_subject_coverage_percent", "qcovus": "query_unique_subject_coverage_percent"}
_TAB_INTS = {"nident", "positive", "length", "gaps", "qstart", "qend", "sstart",
             "send", "qframe", "sframe", "qlen", "slen", "mismatch", "gapopen"}
_TAB_NUMBERS = {"bitscore", "score", "evalue", "pident", "ppos", "qcovs", "qcovhsp", "qcovus"}
_SET_FIELDS = {"sallseqid": ";", "sallgi": ";", "sallacc": ";", "staxids": ";",
               "sscinames": ";", "scomnames": ";", "sblastnames": ";",
               "sskingdoms": ";", "salltitles": "<>"}


def _issue(issues, code, **locator):
    issues.append({"code": code, **locator})


def _positive_integer(value):
    return type(value) is int and value > 0


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _require_json_value(value):
    """Reject NaN/Infinity even in unknown native fields or caller metadata."""
    try:
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError("blast_finite_json_value_required") from error


def _context(mode, resource, request):
    if not isinstance(mode, str) or mode not in _MODES:
        raise ValueError("blast_grading_mode_invalid")
    if not isinstance(resource, str) or resource not in _RESOURCES:
        raise ValueError("blast_resource_invalid")
    if request is not None and not isinstance(request, dict):
        raise ValueError("blast_request_object_required")
    request = deepcopy(request or {})
    _require_json_value(request)
    return request


def _program(reported, request):
    requested = request.get("program", request.get("algorithm"))
    program = reported or requested
    if not isinstance(program, str) or program not in PROGRAM_UNITS:
        raise ValueError("blast_supported_program_required")
    if reported and requested and reported != requested:
        raise ValueError("blast_program_request_conflict")
    return program


def _query(identifier, title, length, request, issues):
    if identifier is not None and not isinstance(identifier, str):
        _issue(issues, "blast_query_id_invalid")
        identifier = None
    if title is not None and not isinstance(title, str):
        _issue(issues, "blast_query_title_invalid")
        title = None
    if length is not None and not _positive_integer(length):
        _issue(issues, "blast_query_length_invalid")
        length = None
    requested = request.get("query_length")
    if requested is not None and not _positive_integer(requested):
        raise ValueError("blast_request_query_length_invalid")
    if length is not None and requested is not None and length != requested:
        raise ValueError("blast_query_length_request_conflict")
    if length is None:
        length = requested
    return {"id": identifier, "title": title, "length": length}


def _hsp(native, issues, **locator):
    if not isinstance(native, dict):
        _issue(issues, "blast_hsp_object_required", **locator)
        return None
    result = deepcopy(native)
    for key, value in native.items():
        valid = True
        if key in _INT_MIN:
            valid = type(value) is int and value >= _INT_MIN[key]
        elif key in {"query_frame", "hit_frame"}:
            valid = type(value) is int and -3 <= value <= 3
        elif key in _SCORES:
            valid = _finite(value) and (key != "evalue" or value >= 0)
        elif key in _STRINGS:
            valid = isinstance(value, str)
        elif key in {"query_strand", "hit_strand"}:
            valid = isinstance(value, str) and value in {"Plus", "Minus"}
        if not valid:
            result.pop(key, None)
            _issue(issues, "blast_hsp_field_invalid", field=key, **locator)
    missing = [key for key in ("query_from", "query_to", "hit_from", "hit_to") if key not in result]
    if missing:
        _issue(issues, "blast_hsp_coordinates_incomplete", fields=missing, **locator)
    return result


def _description(row, issues, **locator):
    if not isinstance(row, dict):
        _issue(issues, "blast_description_object_required", **locator)
        return None
    result = deepcopy(row)
    for key in ("id", "accession", "title", "sciname"):
        if key in result and not isinstance(result[key], str):
            result.pop(key)
            _issue(issues, "blast_description_field_invalid", field=key, **locator)
    if "taxid" in result and not _positive_integer(result["taxid"]):
        result.pop("taxid")
        _issue(issues, "blast_description_field_invalid", field="taxid", **locator)
    return result


def _json_document(content):
    if not isinstance(content, bytes):
        raise ValueError("blast_native_bytes_required")
    member, raw = None, content
    try:
        if content.startswith(b"PK\x03\x04"):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = [(ordinal, info, archive.read(info)) for ordinal, info in enumerate(archive.infolist())
                           if not info.is_dir() and info.filename.lower().endswith(".json")]
                objects = [(ordinal, info, data, json.loads(data)) for ordinal, info, data in entries]
                manifests = [obj for _, _, _, obj in objects if isinstance(obj, dict) and "BlastJSON" in obj]
                if len(manifests) > 1:
                    raise ValueError("blast_archive_manifest_ambiguous")
                if manifests:
                    rows = manifests[0]["BlastJSON"]
                    if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
                            or not isinstance(rows[0].get("File"), str)):
                        raise ValueError("blast_single_query_archive_required")
                    matches = [(n, info, data) for n, info, data, _ in objects if info.filename == rows[0]["File"]]
                else:
                    matches = [(n, info, data) for n, info, data, obj in objects
                               if isinstance(obj, dict) and "BlastOutput2" in obj]
                if len(matches) != 1:
                    raise ValueError("blast_archive_payload_ambiguous_or_missing")
                ordinal, info, raw = matches[0]
                member = {"ordinal": ordinal, "name": info.filename}
        document = json.loads(raw)
        _require_json_value(document)
        return document, member
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("blast_native_json_invalid") from error


def parse_blast_json(content: bytes, *, mode: str, resource: str, request: dict | None = None) -> dict:
    """Normalize exactly one native JSON2/JSON15 query, direct or ZIP-wrapped.

    Malformed independent hits/HSP fields remain in ``native.document`` while
    valid measurements survive in ``hits`` with explicit issues. Ambiguous
    multiquery or pairwise-versus-database wrappers are rejected, not guessed.
    """
    request = _context(mode, resource, request)
    body, member = _json_document(content)
    entries = body.get("BlastOutput2") if isinstance(body, dict) else None
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError("blast_single_query_report_required")
    report = entries[0].get("report") if isinstance(entries[0], dict) else None
    if not isinstance(report, dict):
        raise ValueError("blast_report_required")
    program = _program(report.get("program"), request)
    results = report.get("results")
    target = report.get("search_target", {})
    if not isinstance(results, dict) or not isinstance(target, dict):
        raise ValueError("blast_search_report_required")
    if "iterations" in results or len(set(results) & {"search", "bl2seq"}) != 1:
        raise ValueError("blast_single_noniterative_search_required")
    if "bl2seq" in results:
        if mode != "pairwise":
            raise ValueError("blast_pairwise_database_mode_conflict")
        searches = results["bl2seq"]
        if not isinstance(searches, list) or len(searches) != 1:
            raise ValueError("blast_single_pairwise_search_required")
        search = searches[0]
    else:
        search = results["search"]
    if mode == "pairwise" and "db" in target:
        raise ValueError("blast_pairwise_database_mode_conflict")
    if mode == "database" and "subjects" in target:
        raise ValueError("blast_pairwise_database_mode_conflict")
    if mode == "pairwise" and "subjects" in target:
        if not isinstance(target["subjects"], list) or len(target["subjects"]) != 1:
            raise ValueError("blast_single_pairwise_subject_required")
    if not isinstance(search, dict):
        raise ValueError("blast_search_report_required")
    issues = []
    query = _query(search.get("query_id"), search.get("query_title"), search.get("query_len"), request, issues)
    native_hits = search.get("hits")
    present = isinstance(native_hits, list)
    if "hits" in search and not present:
        _issue(issues, "blast_hit_array_invalid")
    elif not present:
        _issue(issues, "blast_hit_array_not_reported")
    if mode == "pairwise" and present and len(native_hits) > 1:
        raise ValueError("blast_single_pairwise_subject_required")
    hits = []
    for hit_index, row in enumerate(native_hits if present else []):
        if not isinstance(row, dict):
            _issue(issues, "blast_hit_object_required", hit_index=hit_index)
            continue
        length = row.get("len")
        if length is not None and not _positive_integer(length):
            _issue(issues, "blast_reference_length_invalid", hit_index=hit_index)
            length = None
        descriptions = row.get("description", [])
        if not isinstance(descriptions, list):
            _issue(issues, "blast_description_array_invalid", hit_index=hit_index)
            descriptions = []
        normalized_descriptions = []
        for description_index, value in enumerate(descriptions):
            item = _description(value, issues, hit_index=hit_index, description_index=description_index)
            if item is not None:
                normalized_descriptions.append(item)
        hsps = row.get("hsps")
        if not isinstance(hsps, list):
            _issue(issues, "blast_hsp_array_not_reported" if hsps is None else "blast_hsp_array_invalid", hit_index=hit_index)
            hsps = []
        normalized_hsps, hsp_source_map = [], []
        for hsp_index, value in enumerate(hsps):
            item = _hsp(value, issues, hit_index=hit_index, hsp_index=hsp_index)
            if item is not None:
                normalized_hsps.append(item)
                hsp_source_map.append({"hit_index": hit_index, "hsp_index": hsp_index})
        hits.append({"hit_index": hit_index, "length": length, "descriptions": normalized_descriptions,
                     "unpaired_metadata": {}, "hsps": normalized_hsps,
                     "hsp_source_map": hsp_source_map})
    params, stats = report.get("params", {}), search.get("stat", {})
    if not isinstance(params, dict):
        params = {}
        _issue(issues, "blast_parameters_object_invalid")
    if not isinstance(stats, dict):
        stats = {}
        _issue(issues, "blast_statistics_object_invalid")
    version, database = report.get("version"), target.get("db")
    if version is not None and not isinstance(version, str):
        version = None
        _issue(issues, "blast_version_text_invalid")
    if database is not None and not isinstance(database, str):
        database = None
        _issue(issues, "blast_database_text_invalid")
    return {"schema": SCHEMA, "mode": mode, "resource": resource, "format": "json2", "query": query,
        "search": {"program": program, "version": version,
                   "database": database, "parameters": deepcopy(params), "statistics": deepcopy(stats),
                   "request": request, "hit_array_present": present,
                   "reported_hit_count": len(native_hits) if present else None},
        "hits": hits, "native": {"document": body, "archive_member": member,
                                 "sha256": hashlib.sha256(content).hexdigest()}, "issues": issues}


def _fields(fields):
    if not isinstance(fields, list) or not fields or any(not isinstance(x, str) or not x.strip() for x in fields):
        raise ValueError("blast_tabular_fields_required")
    result = []
    for name in fields:
        name = _LABELS.get(name.strip().lower(), name.strip().lower())
        result.extend(STANDARD_TABULAR_FIELDS if name == "std" else [name])
    if len(set(result)) != len(result):
        raise ValueError("blast_tabular_duplicate_fields")
    return result


def _tab_number(value, field):
    if value in {"", "N/A", "NA", "n/a"}:
        return None
    if field in _TAB_INTS:
        if re.fullmatch(r"[+-]?\d+", value) is None:
            raise ValueError("integer_required")
        number = int(value)
        if field in {"qframe", "sframe"}:
            if not -3 <= number <= 3:
                raise ValueError("frame_invalid")
        elif field in {"qlen", "slen", "qstart", "qend", "sstart", "send", "length"}:
            if number <= 0:
                raise ValueError("positive_integer_required")
        elif number < 0:
            raise ValueError("nonnegative_integer_required")
        return number
    number = float(value)
    if not math.isfinite(number) or field == "evalue" and number < 0:
        raise ValueError("finite_number_required")
    if field in {"pident", "ppos", "qcovs", "qcovhsp", "qcovus"} and not 0 <= number <= 100:
        raise ValueError("percentage_outside_range")
    return number


def _tab_descriptions(row, issues, line):
    """Keep primary-field relationships; preserve sets without inventing joins."""
    primary = {}
    if row.get("sseqid"):
        primary["id"] = row["sseqid"]
    if row.get("saccver") or row.get("sacc"):
        primary["accession"] = row.get("saccver") or row["sacc"]
    if row.get("stitle"):
        primary["title"] = row["stitle"]
    sets = {key: value.split(separator) for key, separator in _SET_FIELDS.items()
            if (value := row.get(key)) and value not in {"N/A", "NA", "n/a"}}
    if "staxids" in sets:
        valid_taxa = []
        invalid_taxa = []
        for value in sets["staxids"]:
            if re.fullmatch(r"[1-9]\d*", value):
                valid_taxa.append(int(value))
            else:
                invalid_taxa.append(value)
                _issue(issues, "blast_tabular_taxid_invalid", line=line)
        sets["staxids"] = valid_taxa
        if invalid_taxa:
            sets["invalid_staxids"] = invalid_taxa
    descriptions = [primary] if primary.get("id") or primary.get("accession") else []
    for accession in sets.get("sallacc", []):
        if accession and not any(x.get("accession") == accession for x in descriptions):
            descriptions.append({"accession": accession})
    if not descriptions:
        descriptions = [{"id": value} for value in sets.get("sallseqid", []) if value]
    if not descriptions:
        raise ValueError("blast_tabular_subject_identifier_required")
    ambiguous_aliases = (len(descriptions) > 1 or len(sets.get("sallseqid", [])) > 1)
    if not ambiguous_aliases and len(sets.get("staxids", [])) == 1 and not sets.get("invalid_staxids"):
        descriptions[0]["taxid"] = sets["staxids"][0]
        if len(sets.get("sscinames", [])) == 1:
            descriptions[0]["sciname"] = sets["sscinames"][0]
    # Even singleton sets remain separately available; no alias alignment is
    # implied by their position in any other list.
    if any(len(sets.get(key, [])) > 1 for key in ("staxids", "sscinames")) or ambiguous_aliases:
        _issue(issues, "blast_tabular_reference_metadata_unpaired", line=line)
    key = row.get("sseqid") or row.get("saccver") or row.get("sacc")
    if not key:
        key = tuple(sorted(row.get("sallacc", row.get("sallseqid", "")).split(";")))
    return key, descriptions, sets


def parse_blast_tabular(content: bytes | str, *, mode: str, resource: str,
                        fields: list[str] | None = None, request: dict | None = None) -> dict:
    """Read outfmt 6/7 using supplied names or the actual ``# Fields`` line.

    Tabular reports do not ordinarily contain database search statistics or
    exact accession–taxon associations for merged subjects. These facts remain
    unavailable. A bare empty file is not evidence of a completed zero-hit run.
    """
    request = _context(mode, resource, request)
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8")
        except UnicodeError as error:
            raise ValueError("blast_tabular_utf8_required") from error
    elif isinstance(content, str):
        text = content
    else:
        raise ValueError("blast_tabular_text_required")
    declared = _fields(fields) if fields is not None else None
    current_fields = declared
    issues, native_rows, hits = [], [], []
    hit_map, query_ids, query_lengths = {}, set(), set()
    query_title, reported_program, version, database = None, None, None, None
    query_headers, declared_rows, invalid_rows, raw_rows = 0, None, 0, 0
    length_conflicts = set()
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if line.startswith("#"):
            heading = line[1:].strip()
            if match := re.fullmatch(r"(BLASTN|BLASTP|BLASTX|TBLASTN|TBLASTX)\s+(.+)", heading):
                new_program = match.group(1).lower()
                if reported_program and reported_program != new_program:
                    raise ValueError("blast_tabular_program_conflict")
                reported_program, version = new_program, heading
            elif heading.startswith("Query:"):
                query_headers += 1
                if query_headers > 1:
                    raise ValueError("blast_single_query_report_required")
                query_title = heading[len("Query:"):].strip()
            elif heading.startswith("Database:"):
                new_database = heading[len("Database:"):].strip()
                if database is not None and database != new_database:
                    raise ValueError("blast_tabular_database_conflict")
                database = new_database
            elif heading.startswith("Fields:"):
                header_fields = _fields([x.strip() for x in heading[len("Fields:"):].split(",")])
                if declared is not None and declared != header_fields:
                    raise ValueError("blast_tabular_declared_fields_conflict")
                if current_fields is not None and current_fields != header_fields:
                    raise ValueError("blast_tabular_fields_changed")
                current_fields = header_fields
            elif match := re.fullmatch(r"(\d+) hits? found", heading):
                value = int(match.group(1))
                if declared_rows is not None and declared_rows != value:
                    raise ValueError("blast_tabular_hit_count_conflict")
                declared_rows = value
            elif match := re.fullmatch(r"BLAST processed (\d+) quer(?:y|ies)", heading):
                if int(match.group(1)) != 1:
                    raise ValueError("blast_single_query_report_required")
            continue
        raw_rows += 1
        if current_fields is None:
            raise ValueError("blast_tabular_fields_required")
        values = line.split("\t")
        if len(values) != len(current_fields):
            _issue(issues, "blast_tabular_column_count_invalid", line=line_no,
                   expected=len(current_fields), actual=len(values))
            native_rows.append({"line": line_no, "values": values})
            invalid_rows += 1
            continue
        row = dict(zip(current_fields, values))
        native_rows.append({"line": line_no, "fields": deepcopy(row)})
        query_id = row.get("qseqid") or row.get("qaccver") or row.get("qacc")
        if query_id:
            query_ids.add(query_id)
        if len(query_ids) > 1:
            raise ValueError("blast_single_query_report_required")
        if not query_id and query_title is None:
            raise ValueError("blast_tabular_query_identifier_required")
        try:
            key, descriptions, unpaired = _tab_descriptions(row, issues, line_no)
        except ValueError as error:
            _issue(issues, str(error), line=line_no)
            invalid_rows += 1
            continue
        numbers = {}
        for field in _TAB_INTS | _TAB_NUMBERS:
            if field not in row:
                continue
            try:
                numbers[field] = _tab_number(row[field], field)
            except ValueError:
                _issue(issues, "blast_tabular_number_invalid", line=line_no, field=field)
        if numbers.get("qlen") is not None:
            query_lengths.add(numbers["qlen"])
        if len(query_lengths) > 1:
            raise ValueError("blast_tabular_query_length_conflict")
        hsp = {native: numbers[field] if field in numbers else row[field]
               for field, native in _TAB_HSP.items() if field in row
               and (field not in _TAB_INTS | _TAB_NUMBERS or numbers.get(field) is not None)}
        if row.get("frames"):
            frames = row["frames"].split("/")
            if len(frames) == 2:
                try:
                    qframe, sframe = (_tab_number(frames[0], "qframe"), _tab_number(frames[1], "sframe"))
                    for name, value in (("query_frame", qframe), ("hit_frame", sframe)):
                        if name in hsp and hsp[name] != value:
                            raise ValueError("frame_conflict")
                        if value is not None:
                            hsp[name] = value
                except ValueError:
                    _issue(issues, "blast_tabular_frames_invalid", line=line_no)
            else:
                _issue(issues, "blast_tabular_frames_invalid", line=line_no)
        if row.get("sstrand") in {"plus", "minus", "Plus", "Minus"}:
            hsp["hit_strand"] = row["sstrand"].title()
        hsp = _hsp(hsp, issues, line=line_no)
        if key not in hit_map:
            hit = {"hit_index": len(hits), "length": numbers.get("slen"),
                   "descriptions": [], "unpaired_metadata": {}, "hsps": []}
            hit_map[key] = hit
            hits.append(hit)
        hit = hit_map[key]
        length = numbers.get("slen")
        if length is not None and hit["length"] is not None and length != hit["length"]:
            length_conflicts.add(key)
            _issue(issues, "blast_tabular_reference_length_conflict", line=line_no, hit_index=hit["hit_index"])
        if key in length_conflicts:
            hit["length"] = None
        elif hit["length"] is None:
            hit["length"] = length
        for description in descriptions:
            if description not in hit["descriptions"]:
                hit["descriptions"].append(description)
        for name, vals in unpaired.items():
            current = hit["unpaired_metadata"].setdefault(name, [])
            current.extend(value for value in vals if value not in current)
        hit["hsps"].append(hsp)
    program = _program(reported_program, request)
    if mode == "pairwise" and len(hits) > 1:
        raise ValueError("blast_single_pairwise_subject_required")
    # BLAST+ 2.17.0 prints a Database header even for -subject. Its explicit
    # sequence-set marker is not a searched database name.
    subject_set = database is not None and database.startswith("User specified sequence set (Input:")
    if mode == "pairwise" and database is not None and not subject_set:
        raise ValueError("blast_pairwise_database_mode_conflict")
    if mode == "database" and subject_set:
        raise ValueError("blast_pairwise_database_mode_conflict")
    if declared_rows is not None and declared_rows != raw_rows:
        _issue(issues, "blast_tabular_reported_row_count_mismatch", reported=declared_rows, observed=raw_rows)
    present = raw_rows > 0 or declared_rows == 0
    if not present:
        _issue(issues, "blast_tabular_empty_without_zero_hit_report")
    query = _query(next(iter(query_ids), None), query_title, next(iter(query_lengths), None), request, issues)
    return {"schema": SCHEMA, "mode": mode, "resource": resource, "format": "tabular", "query": query,
        "search": {"program": program, "version": version,
                   "database": None if mode == "pairwise" else database or request.get("database"),
                   "parameters": {}, "statistics": {}, "request": request,
                   "hit_array_present": present,
                   "reported_hit_count": len(hits) if present and invalid_rows == 0 else None},
        "hits": hits, "native": {"text": text, "fields": current_fields, "rows": native_rows,
                                 "declared_alignment_row_count": declared_rows,
                                 "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}, "issues": issues}


__all__ = ["parse_blast_json", "parse_blast_tabular", "STANDARD_TABULAR_FIELDS", "SCHEMA"]
