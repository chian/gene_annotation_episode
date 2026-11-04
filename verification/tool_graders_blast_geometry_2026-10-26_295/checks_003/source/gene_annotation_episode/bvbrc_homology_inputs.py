"""Pure, loss-aware readers for the six BV-BRC Homology artifact roles.

The caller retains original bytes and authenticates service/episode custody.
These readers check supplied relationships, never fetch missing artifacts, and
never choose a primary representation. Derived BLAST projections have their
own digests; original artifact identities and row ordinals remain separate.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation

from .blast_grading_inputs import parse_blast_json, parse_blast_tabular
from .blast_search import PROGRAM_UNITS
from .blast_pairwise_grader import _axis_geometry, alignment_components


SCHEMA = "bvbrc_homology_parse_v1"
FIELDS = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
          "qstart", "qend", "sstart", "send", "evalue", "bitscore", "qlen", "slen"]
FORMATS = {"blast_json15_raw": "blast_json15", "homology_processed_json": "homology_processed_json",
           "blast_tabular": "blast_tabular", "blast_tabular_header": "blast_tabular_header",
           "homology_metadata_json": "homology_metadata_json", "blast_archive": "blast_archive"}
MODES = {"database_identification", "pairwise_correspondence"}


def _text(value):
    return isinstance(value, str) and bool(value)


def _index(value):
    return type(value) is int and value >= 0


def _positive(value):
    return type(value) is int and value > 0


def _pointer(value):
    return isinstance(value, str) and (not value or value.startswith("/")) and re.search(r"~(?![01])", value) is None


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _escape(value):
    return value.replace("~", "~0").replace("/", "~1")


def _diagnostic(code, *, artifact=None, locator=None, line=None, severity="error", required_input=None):
    locator = locator or {}
    return {"code": code, "severity": severity,
            "artifact_ref": locator.get("artifact_ref", (artifact or {}).get("raw_artifact_ref")),
            "pointer": locator.get("pointer"), "line": line if line is not None else locator.get("line"),
            **{key: locator.get(key) for key in ("report_index", "hit_index", "description_index", "hsp_index")},
            "required_input": required_input}


def _json(content):
    if not isinstance(content, bytes):
        raise ValueError("homology_native_bytes_required")
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError("homology_json_duplicate_key")
            result[key] = value
        return result
    def number(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("homology_json_nonfinite_number")
        return parsed
    def integer(value):
        result = int(value)
        try:
            finite = math.isfinite(result)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("homology_json_unrepresentable_number")
        return result
    try:
        return json.loads(content.decode("utf-8"), object_pairs_hook=pairs,
                          parse_float=number, parse_int=integer, parse_constant=number)
    except (UnicodeError, json.JSONDecodeError, OverflowError) as error:
        raise ValueError("homology_json_document_invalid") from error


def _binding(binding):
    if not isinstance(binding, dict) or binding.get("schema") != "bvbrc_homology_artifact_bundle_v1":
        raise ValueError("homology_artifact_bundle_required")
    if not isinstance(binding.get("scientific_mode"), str) or binding["scientific_mode"] not in MODES:
        raise ValueError("homology_scientific_mode_invalid")
    if not isinstance(binding.get("primary_representation"), str) or binding["primary_representation"] not in {"raw", "processed", "tabular"}:
        raise ValueError("homology_primary_representation_required")
    if (not isinstance(binding.get("query_bindings"), list) or not isinstance(binding.get("database_binding"), dict)
            or not isinstance(binding.get("artifacts"), list)):
        raise ValueError("homology_input_binding_shape_invalid")
    task = binding.get("original_task")
    if (not isinstance(task, dict) or task.get("required_application_id") != "Homology"
            or task.get("native_application_id") != "Homology" or not _text(task.get("task_id"))
            or not _text(task.get("resource_id")) or not _text(task.get("submission_receipt_ref"))
            or not isinstance(task.get("submitted_parameters"), dict)):
        raise ValueError("homology_artifact_task_mismatch")
    if task.get("effective_parameters") is not None and not isinstance(task["effective_parameters"], dict):
        raise ValueError("homology_effective_parameters_invalid")
    json.dumps(binding, allow_nan=False)
    return binding


def _artifact(content, artifact, binding, role):
    """Check internal custody/byte claims; this is not remote authentication."""
    diagnostics = []
    row = {"artifact": deepcopy(artifact), "status": "complete", "qualifications": [],
           "native_document": None, "native_lines": None, "representation_links": []}
    def issue(code):
        diagnostics.append(_diagnostic(code, artifact=artifact if isinstance(artifact, dict) else {}))
    if not isinstance(artifact, dict):
        issue("homology_artifact_record_required")
    else:
        if artifact.get("role") != role:
            issue("homology_artifact_role_conflict")
        if any(not _text(artifact.get(key)) for key in ("source_ref", "raw_artifact_ref")):
            issue("homology_artifact_reference_required")
        declaration = artifact.get("declared_format")
        if (not isinstance(declaration, dict) or declaration.get("format") != FORMATS[role]
                or not isinstance(declaration.get("mode"), str) or declaration["mode"] not in MODES
                or binding is not None and declaration.get("mode") != binding.get("scientific_mode")
                or declaration.get("version") is not None and not _text(declaration["version"])):
            issue("homology_format_shape_mismatch")
        elif declaration.get("version") is None:
            row["qualifications"].append("native_format_version_unknown")
        if isinstance(content, bytes):
            row["observed_sha256"] = hashlib.sha256(content).hexdigest()
            row["observed_byte_count"] = len(content)
            if artifact.get("sha256") != row["observed_sha256"]:
                issue("homology_artifact_digest_mismatch")
            if type(artifact.get("byte_count")) is not int or artifact["byte_count"] != len(content):
                issue("homology_artifact_size_mismatch")
        else:
            issue("homology_native_bytes_required")
        workspace, association, transfer = (artifact.get(key) for key in ("workspace_object", "task_association", "transfer"))
        if (not isinstance(workspace, dict) or not isinstance(association, dict)
                or not all(_text(workspace.get(key)) for key in ("path", "uuid", "type", "metadata_receipt_ref"))
                or not all(_text(association.get(key)) for key in ("manifest_source_ref", "task_id", "output_path", "output_uuid"))
                or not _pointer(association.get("manifest_record_pointer"))):
            issue("homology_artifact_association_invalid")
        else:
            if workspace["path"] != association["output_path"] or workspace["uuid"] != association["output_uuid"]:
                issue("homology_artifact_object_mismatch")
            if binding is not None and association["task_id"] != binding["original_task"]["task_id"]:
                issue("homology_artifact_task_mismatch")
        if not isinstance(transfer, dict) or not _text(transfer.get("receipt_ref")):
            issue("homology_transfer_record_required")
        else:
            if transfer.get("body_complete") is not True:
                issue("homology_transfer_incomplete")
            size = transfer.get("total_size")
            if type(size) is not int or not isinstance(content, bytes) or size != len(content):
                issue("homology_transfer_incomplete")
            requested, observed = transfer.get("requested_range"), transfer.get("observed_range")
            if requested is not None and (not isinstance(requested, list) or len(requested) != 2
                    or not _index(requested[0]) or requested[1] is not None and (
                        not _index(requested[1]) or requested[1] < requested[0])):
                issue("homology_transfer_range_invalid")
            if observed is not None:
                if (not isinstance(observed, dict) or set(observed) != {"start", "end_inclusive", "total_size"}
                        or not _index(observed.get("start")) or not _index(observed.get("end_inclusive"))
                        or observed["end_inclusive"] < observed["start"]
                        or type(observed.get("total_size")) is not int or observed["total_size"] != size):
                    issue("homology_transfer_range_invalid")
                elif (not isinstance(content, bytes) or observed["start"] != 0 or observed["end_inclusive"] != size - 1
                      or observed["end_inclusive"] - observed["start"] + 1 != len(content)):
                    issue("homology_transfer_incomplete")
                else:
                    row["qualifications"].append("observed_byte_interval_covers_entire_object")
            elif requested is not None:
                row["qualifications"].append("complete_body_despite_requested_range")
            if transfer.get("object_complete", "yes") not in ("yes", "no", "unknown"):
                issue("homology_transfer_completeness_invalid")
            elif transfer.get("object_complete") == "no":
                issue("homology_transfer_incomplete")
        if binding is not None:
            matches = [item for item in binding.get("artifacts", []) if isinstance(item, dict)
                       and item.get("raw_artifact_ref") == artifact.get("raw_artifact_ref")]
            if len(matches) != 1 or matches[0] != artifact:
                issue("homology_artifact_bundle_reference_conflict")
    row["status"] = "invalid" if diagnostics else "complete"
    row["diagnostics"] = diagnostics
    return row


def _envelope(binding):
    result = {"schema": SCHEMA, "status": "complete", "binding": deepcopy(binding),
              "queries": [], "artifacts": [], "diagnostics": []}
    try:
        _binding(binding)
    except (ValueError, TypeError) as error:
        result["status"] = "invalid"
        result["diagnostics"].append(_diagnostic(str(error)))
    return result


def _finish(result):
    if result["status"] == "invalid":
        return result
    usable = any(row.get("normalized_result") is not None for row in result["queries"])
    damaged = (any(row["status"] != "complete" for row in result["queries"])
               or any(row["status"] in {"invalid", "partial"} for row in result["artifacts"]))
    errors = any(row["severity"] == "error" for row in result["diagnostics"])
    if damaged or errors:
        result["status"] = "partial" if usable else "unavailable"
    return result


def _locator(artifact, report_index, pointer, **indices):
    return {"artifact_ref": artifact["raw_artifact_ref"], "report_index": report_index,
            "pointer": pointer, **indices}


def _query_row(locator):
    return {"report_index": locator["report_index"], "status": "complete", "source_locator": locator,
            "normalized_result": None, "query_binding": None, "query_binding_status": "missing",
            "description_links": [], "native_tabular_measurements": [], "diagnostics": []}


def _query_attachment(row, binding):
    result = row["normalized_result"]
    if result is None:
        return
    query, report_index = result["query"], row["report_index"]
    candidates = [item for item in binding["query_bindings"] if isinstance(item, dict)
                  and isinstance(item.get("native_query"), dict)
                  and item["native_query"].get("report_index") == report_index]
    code, status = None, "missing"
    if len(candidates) > 1:
        code, status = "homology_query_binding_ambiguous", "ambiguous"
    elif not candidates:
        code = "homology_query_binding_unavailable"
    else:
        candidate = candidates[0]
        native, transform = candidate["native_query"], candidate.get("sequence_transform", {})
        evidence = candidate.get("id_mapping_evidence")
        repeated = [item for item in binding["query_bindings"] if isinstance(item, dict)
                    and item.get("subject_ref") == candidate.get("subject_ref")]
        if len(repeated) > 1:
            code, status = "homology_query_binding_ambiguous", "ambiguous"
        elif (any(not _text(candidate.get(key)) for key in ("input_source_ref", "subject_ref", "supplied_id"))
              or not _positive(candidate.get("supplied_length")) or not _digest(candidate.get("supplied_sequence_sha256"))
              or not _index(native.get("report_index"))
              or native.get("query_len") is not None and not _positive(native["query_len"])
              or any(native.get(key) is not None and not isinstance(native[key], str) for key in ("query_id", "query_title"))
              or candidate.get("staged_length") is not None and not _positive(candidate["staged_length"])
              or candidate.get("staged_sequence_sha256") is not None and not _digest(candidate["staged_sequence_sha256"])
              or candidate.get("staged_id") is not None and not _text(candidate["staged_id"])
              or candidate.get("member_ref") is not None and not _text(candidate["member_ref"])
              or query.get("native_identity_valid") is False
              or candidate.get("molecule") != PROGRAM_UNITS[result["search"]["program"]][0]
              or not isinstance(evidence, list) or not evidence
              or any(not isinstance(item, dict) or not _text(item.get("source_ref"))
                     or not _pointer(item.get("pointer")) or not _text(item.get("relation")) for item in evidence)):
            code, status = "homology_query_binding_evidence_required", "invalid"
        elif any(native.get(key) != query[value] for key, value in
                 (("query_id", "id"), ("query_title", "title"), ("query_len", "length"))):
            code, status = "homology_query_binding_native_conflict", "conflicting"
        elif not isinstance(transform, dict) or transform.get("kind") not in {"identity", "verified_fasta_normalization"}:
            code, status = "homology_query_sequence_transform_unavailable", "missing"
        else:
            length = candidate.get("staged_length") if candidate.get("staged_length") is not None else candidate["supplied_length"]
            if query["length"] is not None and length != query["length"]:
                code, status = "homology_query_binding_length_conflict", "conflicting"
            elif transform["kind"] == "identity" and (
                    length != candidate["supplied_length"] or candidate.get("staged_sequence_sha256") not in
                    (None, candidate["supplied_sequence_sha256"])):
                code, status = "homology_query_sequence_identity_conflict", "conflicting"
            elif transform["kind"] == "verified_fasta_normalization" and (
                    not _positive(candidate.get("staged_length")) or not _digest(candidate.get("staged_sequence_sha256"))
                    or not _text(transform.get("source_ref")) or not _pointer(transform.get("pointer"))
                    or not _text(transform.get("coordinate_map_ref"))):
                code, status = "homology_query_normalization_evidence_required", "missing"
            else:
                row["query_binding"] = deepcopy(candidate)
                status = "validated"
                if query["length"] is None:
                    query["length"] = length
                    query["length_source"] = {"kind": "verified_supplied_query_binding",
                                               "source_ref": candidate["input_source_ref"], "member_ref": candidate.get("member_ref")}
                if transform["kind"] == "verified_fasta_normalization":
                    row["diagnostics"].append(_diagnostic("homology_original_coordinate_map_content_unavailable",
                        locator=row["source_locator"], severity="qualification", required_input="supplied_coordinate_map_content"))
    row["query_binding_status"] = status
    if code:
        row["diagnostics"].append(_diagnostic(code, locator=row["source_locator"]))
        row["status"] = "partial"


def _decode_description(description):
    """Literal port of retained HomologySearch.decode_title, not a function inference.

    Its outputs are used to validate a supplied processed/sidecar relationship.
    They are never assignments in the absence of the actual metadata artifact.
    """
    result = deepcopy(description)
    identifier, title = description.get("id"), description.get("title")
    if not isinstance(identifier, str) or not isinstance(title, str):
        return result, None
    metadata = {}
    if identifier.startswith("gnl|BL_ORD"):
        match = re.match(r"^(\S+)\s{3}(.*)\s{3}(.*)$", title)
        if match:
            token, function, genome = match.groups()
            prefix = re.match(r"^((fig\|\d+\.\d+.[^.]+\.\d+)|(accn\|[^|]+))", token)
            # Perl retains the enclosing regex's first capture when the
            # substitution fails. Preserve that observed invalid ID literally;
            # _links marks this failed-prefix branch unavailable for association.
            identifier = prefix.group(1) if prefix else token
            rest = token[len(prefix.group(1)):] if prefix else token
            rest = re.sub(r"^\|", "", rest)
            rest = re.sub(r"\|$", "", rest)
            fields = rest.split("|") if rest else []
            while fields and fields[-1] == "":
                fields.pop()  # Perl split drops trailing empty fields.
            if len(fields) == 2:
                metadata.update(locus_tag=fields[0], alt_locus_tag=fields[1])
            elif len(fields) == 1:
                metadata["alt_locus_tag"] = fields[0]
            genome_match = re.match(r"^\[(.*) \| (\d+\.\d+)", genome)
            if genome_match:
                metadata.update(genome_name=genome_match.group(1), genome_id=genome_match.group(2))
            metadata["function"] = function
        elif match := re.match(r"^(\S+)\s+(.*)\s{3}\[(.*?)(\s*\|\s*(\S+))?\]\s*$", title):
            identifier = match.group(1)
            metadata.update(function=match.group(2), genome_name=match.group(3))
            if match.group(5):
                metadata["genome_id"] = match.group(5)
        elif match := re.match(r"^(\S+)\s+\[(.*?)(\s*\|\s*(\S+))?\]\s*$", title):
            identifier = match.group(1)
            metadata["genome_name"] = match.group(2)
            if match.group(4):
                metadata["genome_id"] = match.group(4)
        elif match := re.match(r"^(\S+)\s+(.*)\s*$", title):
            identifier = match.group(1)
            metadata["function"] = result["title"] = match.group(2)
        else:
            identifier = title
    else:
        identifier = re.sub(r"^gnl\|", "", identifier)
        if match := re.match(r"^\s*(.*)\s{3}\[(.*?)(\s*\|\s*(\S+))?\]\s*$", title):
            metadata.update(function=match.group(1), genome_name=match.group(2))
            if match.group(4):
                metadata["genome_id"] = match.group(4)
        elif match := re.match(r"^\s*\[(.*?)(\s*\|\s*(\S+))?\]\s*$", title):
            metadata["genome_name"] = match.group(1)
            if match.group(3):
                metadata["genome_id"] = match.group(3)
    if isinstance(identifier, str) and (match := re.match(r"^(kb\|g\.\d+)", identifier)):
        metadata["genome_id"] = match.group(1)
    result["id"] = identifier
    return result, metadata or None


def _processed_query_id(query_id, title):
    if not isinstance(query_id, str):
        return query_id
    identifier = re.sub(r"^gnl\|", "", query_id)
    if re.match(r"^Query_\d+", identifier) and isinstance(title, str):
        match = re.match(r"^(\S+)", title)
        if match:
            identifier = match.group(1)
    return identifier


def _links(normalized, artifact, processed):
    result = []
    for hit in normalized["hits"]:
        for description in hit["descriptions"]:
            loc = description["source_locator"]
            native = {key: description.get(key) for key in ("id", "accession", "title", "taxid")}
            transformed, _ = _decode_description(native) if not processed else (native, None)
            identifier = transformed.get("id")
            valid = all(native[key] is None or isinstance(native[key], str) for key in ("id", "accession", "title"))
            valid = valid and (native["taxid"] is None or _positive(native["taxid"])) and _text(identifier)
            if (not processed and isinstance(native["id"], str) and native["id"].startswith("gnl|BL_ORD")
                    and isinstance(native["title"], str)
                    and (match := re.match(r"^(\S+)\s{3}(.*)\s{3}(.*)$", native["title"]))
                    and re.match(r"^((fig\|\d+\.\d+.[^.]+\.\d+)|(accn\|[^|]+))", match.group(1)) is None):
                valid = False
            result.append({"report_index": loc["report_index"], "hit_index": loc["hit_index"],
                "description_index": loc["description_index"],
                "raw_description_pointer": None if processed else loc["pointer"],
                "raw_id": None if processed else native["id"], "raw_accession": None if processed else native["accession"],
                "raw_title": None if processed else native["title"],
                "processed_description_pointer": loc["pointer"] if processed else None,
                "processed_id": identifier, "metadata_key": identifier if valid else None,
                "metadata_pointer": "/" + _escape(identifier) if valid else None,
                "status": "validated" if valid else "invalid",
                "transformation_source_ref": artifact["declared_format"].get("producer_source_ref"),
                "diagnostics": (["homology_raw_identifiers_unavailable"] if processed else [])
                    + ([] if valid else ["homology_rewritten_description_invalid"])})
    return result


def _collisions(queries):
    links = defaultdict(list)
    for query in queries:
        for link in query["description_links"]:
            if link.get("metadata_key") is not None:
                links[link["metadata_key"]].append((query, link))
    for rows in links.values():
        if len(rows) > 1:
            for query, link in rows:
                link["status"] = "ambiguous"
                link["diagnostics"].append("homology_metadata_rewritten_id_collision")
                query["diagnostics"].append(_diagnostic("homology_metadata_rewritten_id_collision",
                    locator={**query["source_locator"], **{key: link[key] for key in ("hit_index", "description_index")}}))
                query["status"] = "partial"


def _request(binding):
    task, database = binding["original_task"], binding["database_binding"]
    submitted = task["submitted_parameters"]
    effective = task.get("effective_parameters") or {}
    result = {}
    limit = effective.get("blast_max_hits", submitted.get("blast_max_hits"))
    if limit is not None:
        result["max_target_seqs"] = deepcopy(limit)
    for source_key, target_key in (("reference_release", "database_release"),):
        if database.get(source_key) is not None:
            result[target_key] = deepcopy(database[source_key])
    if database.get("effective_native_database") is not None:
        result["database"] = database["effective_native_database"]
    result["database_scope"] = "searched_database"
    return result


def _read_json(content, *, artifact, binding, processed):
    result = _envelope(binding)
    if result["status"] == "invalid":
        return result
    role = "homology_processed_json" if processed else "blast_json15_raw"
    retained = _artifact(content, artifact, binding, role)
    result["artifacts"].append(retained)
    result["diagnostics"].extend(retained["diagnostics"])
    if retained["status"] == "invalid":
        return _finish(result)
    try:
        document = _json(content)
        retained["native_document"] = document
        entries = document if processed else document.get("BlastOutput2") if isinstance(document, dict) else None
        if not isinstance(entries, list):
            raise ValueError("homology_format_shape_mismatch")
    except ValueError as error:
        retained["status"] = "invalid"
        result["diagnostics"].append(_diagnostic(str(error), artifact=artifact))
        return _finish(result)
    if not entries:
        result["diagnostics"].append(_diagnostic("homology_zero_query_report", artifact=artifact, severity="qualification"))
    for report_index, entry in enumerate(entries):
        pointer = ("" if processed else "/BlastOutput2") + f"/{report_index}"
        locator = _locator(artifact, report_index, pointer)
        row = _query_row(locator)
        result["queries"].append(row)
        projection = json.dumps({"BlastOutput2": [entry]}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        try:
            normalized = parse_blast_json(projection, mode="database", resource="api", request=_request(binding))
        except (ValueError, TypeError) as error:
            row["status"] = "invalid"
            row["diagnostics"].append(_diagnostic(str(error), locator=locator))
            continue
        normalized["source_locator"] = deepcopy(locator)
        normalized["native"].update(representation="derived_single_query_projection",
            original_artifact_ref=artifact["raw_artifact_ref"], original_sha256=artifact["sha256"],
            original_pointer=pointer, projection_sha256=hashlib.sha256(projection).hexdigest())
        normalized["execution"] = {"provider": "bvbrc", "application_id": "Homology", "database_backed": True,
            "scientific_mode": binding["scientific_mode"], "original_task": deepcopy(binding["original_task"])}
        native_search = entry["report"]["results"]["search"]
        normalized["query"]["native_identity_valid"] = (
            all(native_search.get(key) is None or isinstance(native_search[key], str) for key in ("query_id", "query_title"))
            and (native_search.get("query_len") is None or _positive(native_search["query_len"])))
        native_hits = native_search.get("hits")
        parsed_hits = {hit["hit_index"]: hit for hit in normalized["hits"]}
        all_hits = []
        for hit_index, native_hit in enumerate(native_hits if isinstance(native_hits, list) else []):
            hit_pointer = pointer + f"/report/results/search/hits/{hit_index}"
            hit = parsed_hits.get(hit_index, {"hit_index": hit_index, "length": None, "descriptions": [], "hsps": [],
                                                    "unpaired_metadata": {}, "native_invalid": deepcopy(native_hit)})
            hit["source_locator"] = _locator(artifact, report_index, hit_pointer, hit_index=hit_index)
            if isinstance(native_hit, dict):
                descs = native_hit.get("description")
                retained_descs = iter(hit["descriptions"])
                for description_index, native_desc in enumerate(descs if isinstance(descs, list) else []):
                    if not isinstance(native_desc, dict):
                        continue
                    desc = next(retained_descs)
                    # Never sanitize an invalid native identity into a valid null
                    # and thereby authorize an explicit metadata association.
                    for key in ("id", "accession", "title", "taxid"):
                        if key in native_desc:
                            desc[key] = deepcopy(native_desc[key])
                    desc["source_locator"] = _locator(artifact, report_index, hit_pointer + f"/description/{description_index}",
                                                     hit_index=hit_index, description_index=description_index)
                native_hsps = native_hit.get("hsps")
                retained_hsps = iter(hit["hsps"])
                all_hsps = []
                for hsp_index, native_hsp in enumerate(native_hsps if isinstance(native_hsps, list) else []):
                    hsp = next(retained_hsps) if isinstance(native_hsp, dict) else {"native_invalid": deepcopy(native_hsp)}
                    hsp["source_locator"] = _locator(artifact, report_index, hit_pointer + f"/hsps/{hsp_index}",
                                                   hit_index=hit_index, hsp_index=hsp_index)
                    all_hsps.append(hsp)
                hit["hsps"] = all_hsps
            all_hits.append(hit)
        normalized["hits"] = all_hits
        row["normalized_result"] = normalized
        row["description_links"] = _links(normalized, artifact, processed)
        for issue in normalized["issues"]:
            row["diagnostics"].append(_diagnostic(issue["code"], locator={**locator, **issue}))
        task = binding["original_task"]
        declared_version = artifact["declared_format"].get("version")
        if declared_version is not None and declared_version != normalized["search"]["version"]:
            row["diagnostics"].append(_diagnostic("homology_format_version_conflict", locator=locator))
        for params in (task["submitted_parameters"], task.get("effective_parameters") or {}):
            requested = params.get("blast_program")
            if requested and requested != normalized["search"]["program"]:
                row["diagnostics"].append(_diagnostic("homology_program_request_conflict", locator=locator))
        db_type = binding["database_binding"].get("requested_selection", {}).get("db_type")
        reference_unit = PROGRAM_UNITS[normalized["search"]["program"]][1]
        if db_type is not None and db_type not in ({"faa"} if reference_unit == "aa" else {"ffn", "frn", "fna"}):
            row["diagnostics"].append(_diagnostic("homology_program_database_type_conflict", locator=locator))
        expected_db = binding["database_binding"].get("effective_native_database")
        if expected_db is not None and expected_db != normalized["search"]["database"]:
            row["diagnostics"].append(_diagnostic("homology_native_database_conflict", locator=locator))
        _query_attachment(row, binding)
        if any(item["severity"] == "error" for item in row["diagnostics"]):
            row["status"] = "partial"
    _collisions(result["queries"])
    return _finish(result)


def read_homology_raw_json(content: bytes, *, artifact: dict, binding: dict) -> dict:
    return _read_json(content, artifact=artifact, binding=binding, processed=False)


def read_homology_processed_json(content: bytes, *, artifact: dict, binding: dict) -> dict:
    return _read_json(content, artifact=artifact, binding=binding, processed=True)


def read_homology_tabular(content: bytes, *, header_content: bytes, artifact: dict,
                         header_artifact: dict, binding: dict) -> dict:
    result = _envelope(binding)
    if result["status"] == "invalid":
        return result
    table = _artifact(content, artifact, binding, "blast_tabular")
    header = _artifact(header_content, header_artifact, binding, "blast_tabular_header")
    result["artifacts"] = [table, header]
    result["diagnostics"] = table["diagnostics"] + header["diagnostics"]
    if any(item["status"] == "invalid" for item in result["artifacts"]):
        return _finish(result)
    try:
        text, header_text = content.decode("utf-8"), header_content.decode("utf-8")
        header["native_lines"] = header_text.splitlines()
        table["native_lines"] = text.splitlines()
        if (header_text.splitlines() != ["\t".join(FIELDS)]
                or artifact["declared_format"].get("fields") != FIELDS
                or header_artifact["declared_format"].get("fields") != FIELDS):
            raise ValueError("homology_tabular_fields_conflict")
    except (ValueError, UnicodeError) as error:
        table["status"] = "invalid"
        result["diagnostics"].append(_diagnostic(str(error) if isinstance(error, ValueError) else "homology_tabular_utf8_required", artifact=artifact))
        return _finish(result)
    task = binding["original_task"]
    program = (task.get("effective_parameters") or {}).get("blast_program") or task["submitted_parameters"].get("blast_program")
    groups = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        cells = line.split("\t")
        query_id = cells[0] if cells else ""
        if query_id not in groups:
            ordinal = len(groups)
            groups[query_id] = _query_row(_locator(artifact, ordinal, "", line=line_number))
        row = groups[query_id]
        loc = {**row["source_locator"], "line": line_number}
        measurement = {"line": line_number, "source_locator": loc, "native_line": line,
                       "fields": dict(zip(FIELDS, cells)) if len(cells) == len(FIELDS) else None,
                       "mismatch": None, "gapopen": None, "pident": None, "status": "complete", "hsp_locators": []}
        row["native_tabular_measurements"].append(measurement)
        if len(cells) != len(FIELDS) or not query_id or line.startswith("#"):
            measurement["status"] = row["status"] = "partial"
            row["diagnostics"].append(_diagnostic("homology_tabular_row_invalid", locator=loc))
            continue
        if program not in PROGRAM_UNITS:
            row["status"] = "unavailable"
            row["diagnostics"].append(_diagnostic("homology_observed_program_unavailable", locator=loc))
            continue
        request = {**_request(binding), "program": program}
        try:
            one = parse_blast_tabular((line + "\n").encode(), mode="database", resource="api", fields=FIELDS, request=request)
        except ValueError as error:
            row["status"] = "partial"
            row["diagnostics"].append(_diagnostic(str(error), locator=loc))
            continue
        if row["normalized_result"] is None:
            normalized = deepcopy(one)
            normalized["hits"] = []
            normalized["issues"] = []
            normalized["source_locator"] = deepcopy(row["source_locator"])
            normalized["native"] = {"representation": "derived_query_tabular_projection", "rows": [], "fields": FIELDS,
                "original_artifact_ref": artifact["raw_artifact_ref"], "original_sha256": artifact["sha256"]}
            normalized["execution"] = {"provider": "bvbrc", "application_id": "Homology", "database_backed": True,
                                       "scientific_mode": binding["scientific_mode"]}
            row["normalized_result"] = normalized
        normalized = row["normalized_result"]
        if one["query"]["length"] != normalized["query"]["length"]:
            normalized["query"]["length"] = None
            row["diagnostics"].append(_diagnostic("homology_tabular_query_length_conflict", locator=loc))
        normalized["native"]["rows"].append({"line": line_number, "fields": measurement["fields"]})
        for parsed_hit in one["hits"]:
            identifier = parsed_hit["descriptions"][0].get("id")
            matches = [hit for hit in normalized["hits"] if hit["descriptions"][0].get("id") == identifier]
            if matches:
                hit = matches[0]
                if hit["length"] != parsed_hit["length"]:
                    hit["length"] = None
                    row["diagnostics"].append(_diagnostic("homology_tabular_reference_length_conflict", locator=loc))
            else:
                hit = deepcopy(parsed_hit)
                hit["hit_index"] = len(normalized["hits"])
                hit["source_locator"] = {**loc, "hit_index": hit["hit_index"]}
                hit["hsps"] = []
                for di, desc in enumerate(hit["descriptions"]):
                    desc["source_locator"] = {**hit["source_locator"], "description_index": di}
                normalized["hits"].append(hit)
            for hsp in parsed_hit["hsps"]:
                hsp["source_locator"] = {**hit["source_locator"], "line": line_number, "hsp_index": len(hit["hsps"])}
                measurement["hsp_locators"].append(deepcopy(hsp["source_locator"]))
                hit["hsps"].append(hsp)
        for field in ("mismatch", "gapopen", "pident"):
            lexeme = measurement["fields"][field]
            try:
                number = float(lexeme) if field == "pident" else int(lexeme) if re.fullmatch(r"[+]?\d+", lexeme) else None
                if number is not None and math.isfinite(number) and number >= 0 and (field != "pident" or number <= 100):
                    measurement[field] = number
            except (ValueError, OverflowError):
                pass
        for issue in one["issues"]:
            row["diagnostics"].append(_diagnostic(issue["code"], locator=loc))
        if one["issues"]:
            measurement["status"] = "partial"
        normalized["issues"].extend({**issue, "line": line_number} for issue in one["issues"])
    result["queries"] = list(groups.values())
    if not groups:
        result["diagnostics"].append(_diagnostic("homology_zero_hit_query_unestablished", artifact=artifact))
        table["status"] = "partial"
    for row in result["queries"]:
        normalized = row["normalized_result"]
        if normalized:
            normalized["search"]["reported_hit_count"] = len(normalized["hits"]) if not row["diagnostics"] else None
            projection = json.dumps(normalized["native"]["rows"], sort_keys=True).encode()
            normalized["native"]["projection_sha256"] = hashlib.sha256(projection).hexdigest()
            _query_attachment(row, binding)
        if row["diagnostics"] and row["status"] == "complete":
            row["status"] = "partial"
    return _finish(result)


def _entry(parsed, index):
    for artifact in parsed["artifacts"]:
        document = artifact.get("native_document")
        entries = document.get("BlastOutput2") if isinstance(document, dict) else document
        if isinstance(entries, list) and index < len(entries):
            return entries[index]
    return None


def _expected_processed(entry):
    expected = deepcopy(entry)
    try:
        search = expected["report"]["results"]["search"]
        search["query_id"] = _processed_query_id(search.get("query_id"), search.get("query_title"))
        for hit in search.get("hits", []):
            if isinstance(hit, dict) and isinstance(hit.get("description"), list):
                hit["description"] = [_decode_description(desc)[0] if isinstance(desc, dict) else desc
                                      for desc in hit["description"]]
    except (KeyError, TypeError):
        return None
    return expected


def _reported_agrees(lexeme, native):
    """Compare at the table's retained decimal precision, never invent counts."""
    try:
        reported, actual = Decimal(lexeme), Decimal(str(native))
        if not reported.is_finite() or not actual.is_finite():
            return False
        return abs(reported - actual) <= Decimal(5).scaleb(reported.as_tuple().exponent - 1)
    except (InvalidOperation, ValueError, TypeError):
        return False


def _table_hsp_agrees(fields, hsp, query, hit, program, *, coordinate_convention="directional"):
    component = alignment_components(hsp, program=program, query_length=query["length"],
        reference_length=hit["length"], coordinate_convention=coordinate_convention)
    qunit, runit, aunit = PROGRAM_UNITS[program]
    exact = {"length": hsp.get("align_len"), "qlen": query["length"], "slen": hit["length"]}
    for prefix, table, length, unit, symbols in (
            ("query", "q", query["length"], qunit, hsp.get("qseq")),
            ("hit", "s", hit["length"], runit, hsp.get("hseq"))):
        geometry = _axis_geometry(hsp, prefix=prefix, length=length,
            coordinate_unit=unit, alignment_unit=aunit, issues=[],
            coordinate_convention=coordinate_convention,
            symbols=symbols if component["traceback_available"] else None)
        if geometry is None:
            return False
        exact[table + "start"], exact[table + "end"] = geometry[:2]
    try:
        if not all(value is not None and Decimal(fields[key]) == value for key, value in exact.items()):
            return False
    except (InvalidOperation, ValueError, TypeError):
        return False
    if not all(_reported_agrees(fields[key], hsp.get(native)) for key, native in
               (("bitscore", "bit_score"), ("evalue", "evalue"))):
        return False
    identity, length = hsp.get("identity"), hsp.get("align_len")
    if not (_positive(length) and _index(identity)):
        identity, length = component["counts"]["identical_pairs"], component["counts"]["alignment_columns"]
    if _positive(length) and _index(identity):
        percent = Decimal(identity) * 100 / Decimal(length)
        if not _reported_agrees(fields["pident"], percent):
            return False
    if component["traceback_available"]:
        counts = component["counts"]
        substitutions = counts["paired_columns"] - counts["identical_pairs"]
        gapopen = len(re.findall(r"-+", hsp["qseq"])) + len(re.findall(r"-+", hsp["hseq"]))
        try:
            if Decimal(fields["mismatch"]) != substitutions or Decimal(fields["gapopen"]) != gapopen:
                return False
        except (InvalidOperation, ValueError):
            return False
    return True


def reconcile_homology_artifacts(*, raw: dict | None, processed: dict | None,
                                 tabular: dict | None, binding: dict) -> dict:
    result = _envelope(binding)
    if result["status"] == "invalid":
        return result
    supplied = {"raw": raw, "processed": processed, "tabular": tabular}
    valid = {}
    for name, parsed in supplied.items():
        if parsed is None:
            continue
        if not isinstance(parsed, dict) or parsed.get("schema") != SCHEMA or parsed.get("binding") != binding:
            result["diagnostics"].append(_diagnostic("homology_representation_binding_conflict"))
            continue
        valid[name] = parsed
        result["artifacts"].extend(deepcopy(parsed["artifacts"]))
        result["diagnostics"].extend(deepcopy(parsed["diagnostics"]))
    present = {item["artifact"].get("raw_artifact_ref") for item in result["artifacts"]}
    for artifact in binding.get("artifacts", []):
        if artifact.get("raw_artifact_ref") not in present:
            result["artifacts"].append({"artifact": deepcopy(artifact), "status": "unavailable",
                "qualifications": ["retained_by_caller_without_reader_bytes", "archive_decoder_not_provided"]
                    if artifact.get("role") == "blast_archive" else ["reader_bytes_not_supplied"],
                "native_document": None, "native_lines": None, "representation_links": [], "diagnostics": []})
    primary = valid.get(binding["primary_representation"])
    if primary is None:
        result["status"] = "unavailable"
        result["diagnostics"].append(_diagnostic("homology_primary_representation_unavailable"))
        return result
    result["queries"] = deepcopy(primary["queries"])
    selected = {row["report_index"]: row for row in result["queries"]}
    if raw is not None and processed is not None and "raw" in valid and "processed" in valid:
        rqueries, pqueries = raw["queries"], processed["queries"]
        for index in sorted(set(row["report_index"] for row in rqueries + pqueries)):
            original, transformed = _entry(raw, index), _entry(processed, index)
            expected = _expected_processed(original)
            good = original is not None and transformed is not None and expected == transformed
            link = {"kind": "raw_processed_report", "report_index": index,
                    "status": "validated" if good else "conflicting"}
            for artifact in result["artifacts"]:
                if artifact["artifact"].get("role") in {"blast_json15_raw", "homology_processed_json"}:
                    artifact["representation_links"].append(deepcopy(link))
            if not good:
                diag = _diagnostic("homology_processed_transform_conflict", locator={"report_index": index})
                result["diagnostics"].append(diag)
                if index in selected:
                    selected[index]["diagnostics"].append(diag)
                    selected[index]["status"] = "partial"
                    # A processed primary may retain only transformed IDs.
                    # Contradictory supplied raw descriptions cannot validate
                    # those sidecar links. Other original descriptions survive.
                    if binding["primary_representation"] == "processed":
                        for description in selected[index]["description_links"]:
                            hi, di = description["hit_index"], description["description_index"]
                            try:
                                wanted = expected["report"]["results"]["search"]["hits"][hi]["description"][di]
                                actual = transformed["report"]["results"]["search"]["hits"][hi]["description"][di]
                                agrees = wanted == actual
                            except (KeyError, TypeError, IndexError):
                                agrees = False
                            if not agrees:
                                description["status"] = "conflicting"
                                description["diagnostics"].append("homology_processed_transform_conflict")
            if good and index in selected:
                raw_query = next((row for row in rqueries if row["report_index"] == index), None)
                processed_query = next((row for row in pqueries if row["report_index"] == index), None)
                if raw_query and processed_query:
                    linked = deepcopy(raw_query["description_links"])
                    for desc in linked:
                        other = next((item for item in processed_query["description_links"] if
                            (item["hit_index"], item["description_index"]) == (desc["hit_index"], desc["description_index"])), None)
                        if other:
                            desc["processed_description_pointer"] = other["processed_description_pointer"]
                    selected[index]["description_links"] = linked
    # Pair table rows to every matching HSP. Equal duplicate rows are a set of
    # alternatives; no arbitrary first HSP is selected and no new evidence added.
    if "tabular" in valid and ("raw" in valid or "processed" in valid):
        comparison = valid.get("raw") or valid["processed"]
        for tq in valid["tabular"]["queries"]:
            for measurement in tq["native_tabular_measurements"]:
                fields = measurement.get("fields")
                matches = []
                if fields:
                    for q in comparison["queries"]:
                        normalized = q.get("normalized_result")
                        if not normalized:
                            continue
                        query = normalized["query"]
                        aliases = {query["id"], _processed_query_id(query["id"], query["title"])}
                        if fields["qseqid"] not in aliases:
                            continue
                        for hit in normalized["hits"]:
                            ids = {re.sub(r"^gnl\|", "", desc["id"]) for desc in hit["descriptions"] if isinstance(desc.get("id"), str)}
                            if fields["sseqid"] not in ids:
                                continue
                            for hsp in hit["hsps"]:
                                if _table_hsp_agrees(fields, hsp, query, hit, normalized["search"]["program"],
                                        coordinate_convention="blast_json2" if normalized.get("format") == "json2" else "directional"):
                                    matches.append(deepcopy(hsp["source_locator"]))
                link = {"kind": "tabular_hsp_association_set", "line": measurement["line"], "matches": matches,
                        "status": "validated" if len(matches) == 1 else "ambiguous" if matches else "conflicting"}
                for artifact in result["artifacts"]:
                    if artifact["artifact"].get("role") == "blast_tabular":
                        artifact["representation_links"].append(link)
                for q in result["queries"]:
                    relevant = [loc for loc in matches if loc["report_index"] == q["report_index"]]
                    if relevant and binding["primary_representation"] != "tabular":
                        item = deepcopy(measurement)
                        item["hsp_locators"] = relevant
                        item["association_status"] = link["status"]
                        q["native_tabular_measurements"].append(item)
                if not matches:
                    result["diagnostics"].append(_diagnostic("homology_tabular_representation_conflict",
                                                            locator=measurement["source_locator"]))
        for artifact_row in result["artifacts"]:
            if artifact_row["artifact"].get("role") != "blast_tabular":
                continue
            sets = defaultdict(list)
            for link in artifact_row["representation_links"]:
                if link.get("kind") == "tabular_hsp_association_set" and link["matches"]:
                    key = tuple(sorted(json.dumps(loc, sort_keys=True) for loc in link["matches"]))
                    sets[key].append(link)
            for key, links in sets.items():
                if len(links) != len(key):
                    for link in links:
                        link["status"] = "conflicting"
                        result["diagnostics"].append(_diagnostic("homology_tabular_hsp_multiplicity_conflict",
                            artifact=artifact_row["artifact"], line=link["line"]))
                        for query in result["queries"]:
                            for measurement in query["native_tabular_measurements"]:
                                if measurement["line"] == link["line"]:
                                    measurement["association_status"] = "conflicting"
            represented = {json.dumps(loc, sort_keys=True) for link in artifact_row["representation_links"]
                           for loc in link.get("matches", [])}
            for query in comparison["queries"]:
                normalized = query.get("normalized_result")
                for hit in normalized["hits"] if normalized else []:
                    for hsp in hit["hsps"]:
                        if json.dumps(hsp["source_locator"], sort_keys=True) not in represented:
                            result["diagnostics"].append(_diagnostic("homology_tabular_hsp_unrepresented",
                                                                    locator=hsp["source_locator"]))
    if binding["primary_representation"] == "tabular":
        # A headerless table has no rows for zero-hit queries. Preserve their
        # separately supplied native reports without computing from a secondary
        # representation under the caller's table selection.
        for name in ("raw", "processed"):
            if name not in valid:
                continue
            for query in valid[name]["queries"]:
                if query["report_index"] in selected:
                    continue
                retained_query = deepcopy(query)
                retained_query["normalized_result"] = None
                retained_query["native_tabular_measurements"] = []
                retained_query["status"] = "unavailable"
                retained_query["diagnostics"].append(_diagnostic("homology_primary_query_unavailable",
                    locator=query["source_locator"], required_input="query_in_selected_primary_representation"))
                result["queries"].append(retained_query)
                selected[query["report_index"]] = retained_query
    return _finish(result)


__all__ = ["read_homology_raw_json", "read_homology_processed_json", "read_homology_tabular",
           "reconcile_homology_artifacts"]
