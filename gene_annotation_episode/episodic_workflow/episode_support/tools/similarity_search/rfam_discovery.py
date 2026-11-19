"""Represent native Rfam batch discovery without assigning target biology.

Coordinates in the reported hit locate the submitted physical sequence. The
alignment's #CM display locates consensus model positions, not residues of a
physical external reference. Exact unprojected native fields remain in source.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from urllib.parse import urlsplit

BASE_URL = "https://batch.rfam.org"
VERSION = "rfam_batch_discovery_v1"
JOB = re.compile(r"infernal_cmscan-[A-Za-z0-9_-]+")
ACCESSION = re.compile(r"RF[0-9]{5}")


def result_url(job_id: str) -> str:
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        raise ValueError("rfam_job_identity_invalid")
    return BASE_URL + "/result/" + job_id


def validate_result_url(url: str, job_id: str) -> None:
    # The returned handle authorizes this one provider/job, never an arbitrary
    # URL, credentials, different job, query string or fragment.
    if not isinstance(url, str) or urlsplit(url) != urlsplit(result_url(job_id)):
        raise ValueError("rfam_result_url_identity_conflict")


def submission_handle(content: bytes) -> str:
    body = json.loads(content)
    if not isinstance(body, dict):
        raise ValueError("rfam_submission_object_required")
    job_id = body["jobId"]
    validate_result_url(body["resultURL"], job_id)
    return job_id


def result_body(content: bytes, *, job_id: str, sequence_sha256: str) -> dict:
    body = json.loads(content)
    if not isinstance(body, dict):
        raise ValueError("rfam_result_object_required")
    if body.get("jobId") != job_id:
        raise ValueError("rfam_result_job_identity_conflict")
    if "searchSequence" not in body:
        raise ValueError("rfam_result_sequence_identity_absent")
    sequence = body["searchSequence"]
    if not isinstance(sequence, str):
        raise ValueError("rfam_result_sequence_identity_not_string")
    if not sequence:
        raise ValueError("rfam_result_sequence_identity_empty")
    try:
        encoded = sequence.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("rfam_result_sequence_identity_not_ascii") from error
    if hashlib.sha256(encoded).hexdigest() != sequence_sha256:
        raise ValueError("rfam_result_sequence_identity_conflict")
    if (not isinstance(body.get("hits"), dict) or type(body.get("numHits")) is not int
            or body["numHits"] < 0):
        raise ValueError("rfam_result_hits_representation")
    return body


def hit_row(native: dict, *, family_key: str, sequence_length: int) -> dict:
    if not isinstance(native, dict):
        raise ValueError("rfam_hit_object_required")
    accession, name = native.get("acc"), native.get("id")
    if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
        raise ValueError("rfam_hit_accession_invalid")
    if not isinstance(name, str) or not name or name != family_key:
        raise ValueError("rfam_hit_family_identity_conflict")
    start, end, strand = native.get("start"), native.get("end"), native.get("strand")
    if (type(start) is not int or type(end) is not int or strand not in ("+", "-")
            or not 1 <= min(start, end) <= max(start, end) <= sequence_length):
        raise ValueError("rfam_hit_sequence_coordinates_invalid")
    values = {}
    for source_key, key in (("score", "bitscore"), ("E", "evalue"), ("GC", "gc_fraction")):
        value = native.get(source_key)
        if type(value) not in {int, float} or not math.isfinite(value):
            raise ValueError("rfam_hit_numeric_value_invalid")
        if (source_key == "E" and value < 0) or (source_key == "GC" and not 0 <= value <= 1):
            raise ValueError("rfam_hit_numeric_value_invalid")
        values[key] = value
    if "alignment" in native and not isinstance(native["alignment"], dict):
        raise ValueError("rfam_hit_alignment_representation")
    return {"accession": accession, "source_family_label": name,
        "sequence_interval": [min(start, end)-1, max(start, end)],
        "native_start": start, "native_end": end, "strand": strand,
        **values, "coordinate_system": "zero_based_half_open"}


FAILURE_FEEDBACK_VERSION = "rfam_native_submission_feedback_v1"


def submission_failure_feedback(content: bytes, *, http_status: int, submitted_length: int) -> dict | None:
    """Project one known native error meaning, never a new admission rule.

    An arbitrary HTTP400/body does not imply a length failure. Keep exact source
    bytes in the existing diagnostic; only this actual provider sentence supplies
    a numeric upper bound to the responsible Episode.
    """
    if http_status != 400 or type(submitted_length) is not int or submitted_length < 1:
        return None
    try:
        body = json.loads(content)
    except (ValueError, UnicodeError):
        return None
    detail = body.get("detail") if isinstance(body, dict) else None
    if not isinstance(detail, str):
        return None
    match = re.fullmatch(r"Sequence length must be less than or equal to ([0-9]+(?:,[0-9]{3})*) nucleotides", detail)
    if match is None:
        return None
    try:
        maximum = int(match.group(1).replace(",", ""))
    except ValueError:
        # Unrepresentable native metadata must not replace the actual failure.
        return None
    return {"version": FAILURE_FEEDBACK_VERSION, "kind": "submitted_sequence_length_limit",
        "basis": "native_error_detail", "native_field": "detail", "unit": "nt",
        "maximum_length": maximum, "submitted_length": submitted_length,
        "submitted_exceeds_reported_maximum": submitted_length > maximum}
