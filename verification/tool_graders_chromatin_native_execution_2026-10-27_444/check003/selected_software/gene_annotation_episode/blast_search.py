"""Native BLAST protocol and HSP geometry, without biological selection."""
from __future__ import annotations
import io
import json
import math
import re
import zipfile

VERSION = "native_blast_single_query_v1"
PROGRAM_UNITS = {"blastn": ("nt", "nt", "nt"), "blastp": ("aa", "aa", "aa"),
    "blastx": ("nt", "aa", "aa"), "tblastn": ("aa", "nt", "aa"), "tblastx": ("nt", "nt", "aa")}


def submission(content):
    text = content.decode("utf-8")
    rid = re.search(r"^\s*RID\s*=\s*([A-Za-z0-9_-]+)\s*$", text, re.M)
    rtoe = re.search(r"^\s*RTOE\s*=\s*(\d+)\s*$", text, re.M)
    if rid is None:
        raise ValueError("blast_submission_rid_missing")
    return rid.group(1), int(rtoe.group(1)) if rtoe else None


def status(content):
    text = content.decode("utf-8")
    found = re.search(r"Status=(WAITING|READY|FAILED|UNKNOWN)\b", text)
    if found is None:
        raise ValueError("blast_status_invalid")
    hits = re.search(r"ThereAreHits=(yes|no)\b", text)
    return {"status": found.group(1), "has_hits": hits.group(1) == "yes" if hits else None}


def document(content):
    """Return the exact JSON member bytes, never a reserialized ZIP merge.

    This binding submits exactly one query. Multiquery/iterative/bl2seq native
    reports remain retained but unsupported instead of being silently combined.
    """
    member = None
    raw = content
    if content.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = [(i, info) for i, info in enumerate(archive.infolist())
                       if not info.is_dir() and info.filename.lower().endswith(".json")]
            decoded = [(i, info, archive.read(info)) for i, info in entries]
            objects = [(i, info, data, json.loads(data)) for i, info, data in decoded]
            manifests = [obj for _, _, _, obj in objects if isinstance(obj, dict) and "BlastJSON" in obj]
            if len(manifests) > 1:
                raise ValueError("blast_archive_manifest_ambiguous")
            if manifests:
                names = [row["File"] for row in manifests[0]["BlastJSON"]]
                if len(names) != 1 or not isinstance(names[0], str):
                    raise ValueError("blast_single_query_archive_required")
                matches = [(i, info, data) for i, info, data in decoded if info.filename == names[0]]
            else:
                matches = [(i, info, data) for i, info, data, obj in objects
                           if isinstance(obj, dict) and "BlastOutput2" in obj]
            if len(matches) != 1:
                raise ValueError("blast_archive_payload_ambiguous_or_missing")
            ordinal, info, raw = matches[0]
            member = {"ordinal": ordinal, "name": info.filename}
    body = json.loads(raw)
    reports = body.get("BlastOutput2") if isinstance(body, dict) else None
    if isinstance(reports, dict):
        reports = [reports]
    if not isinstance(reports, list) or len(reports) != 1:
        raise ValueError("blast_single_query_report_required")
    entry = reports[0]
    if not isinstance(entry, dict) or not isinstance(entry.get("report"), dict):
        raise ValueError("blast_report_required")
    report = entry["report"]
    search = report.get("results", {}).get("search")
    if not isinstance(search, dict):
        raise ValueError("blast_search_report_required")
    if not isinstance(search.get("hits", []), list):
        raise ValueError("blast_hit_array_required")
    return {"json_bytes": raw, "member": member, "report": report, "search": search}


def validate_identity(parsed, request):
    report, search = parsed["report"], parsed["search"]
    if report.get("program") != request["algorithm"]:
        raise ValueError("blast_program_conflicts_with_selected_search")
    title = search.get("query_title")
    if title is not None and (not isinstance(title, str) or title.split(maxsplit=1)[0:1] != [request["subject_ref"]]):
        raise ValueError("blast_query_title_conflicts_with_submitted_subject")
    length = search.get("query_len")
    if length is not None and (type(length) is not int or length != request["query_length"]):
        raise ValueError("blast_query_length_conflicts_with_submitted_subject")
    # query_id can be service-generated Query_1. search_target.db describes the
    # effective DB; documented nt->core_nt resolution is not a wrong-job claim.


def integer(value, name, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("blast_invalid_" + name)
    return value


def scalar(value, name, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError("blast_invalid_" + name)
    return value


def hsp_row(native, *, program, query_length, reference_length, hit_ordinal, hsp_ordinal):
    if not isinstance(native, dict):
        raise ValueError("blast_hsp_object_required")
    ends = {key: integer(native[key], key, minimum=1) for key in ("query_from", "query_to", "hit_from", "hit_to")}
    query = [min(ends["query_from"], ends["query_to"])-1, max(ends["query_from"], ends["query_to"])]
    hit = [min(ends["hit_from"], ends["hit_to"])-1, max(ends["hit_from"], ends["hit_to"])]
    if query[1] > query_length or hit[1] > reference_length:
        raise ValueError("blast_hsp_interval_outside_actual_operand")
    native_fields = {"program": program, "report_ordinal": 0, "hit_ordinal": hit_ordinal,
                     "hsp_ordinal": hsp_ordinal, **ends,
                     "query_coordinate_unit": PROGRAM_UNITS[program][0],
                     "hit_coordinate_unit": PROGRAM_UNITS[program][1],
                     "alignment_unit": PROGRAM_UNITS[program][2]}
    for key in ("query_frame", "hit_frame"):
        if key in native:
            if type(native[key]) is not int:
                raise ValueError("blast_invalid_"+key)
            native_fields[key] = native[key]
    for key in ("query_strand", "hit_strand"):
        if key in native:
            if native[key] not in ("Plus", "Minus"):
                raise ValueError("blast_invalid_"+key)
            native_fields[key] = native[key]
    values = {"bitscore": scalar(native["bit_score"], "bit_score"),
              "alignment_score": scalar(native["score"], "score"),
              "evalue": scalar(native["evalue"], "evalue", minimum=0),
              "query_start": query[0], "query_end": query[1],
              "query_coverage": (query[1]-query[0])/query_length,
              "target_coverage": (hit[1]-hit[0])/reference_length}
    if "identity" in native:
        identity = integer(native["identity"], "identity")
        if "align_len" in native:
            length = integer(native["align_len"], "align_len", minimum=1)
            if identity > length:
                raise ValueError("blast_identity_exceeds_alignment_length")
            values["identity_fraction"] = identity/length
    return {"query_interval": query, "reference_interval": hit,
            "measurements": values, "native_blast": native_fields}
