"""Deterministic views of explicitly selected, acquired GenBank context.

These operations neither choose comparative organisms nor infer orthology,
operons or target functions. Source product names remain source labels. All
coordinates are zero-based half-open; left/right flanks follow the source
reference axis, rather than an assumed transcriptional orientation.

The caller supplies the stored body and its actual native acquisition request.
A fetched subsequence has unavailable flanks, not evidence of absent genes.
Only an entire represented record whose source asserts circularity can wrap.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Mapping

from .acquisition import parse_genbank


VERSION = "source_feature_neighborhood_v1"
INTERPRETATION = "external_source_context_not_target_function_or_orthology"


def _integer(value, name, *, minimum=None):
    if type(value) is not int or minimum is not None and value < minimum:
        raise ValueError(f"invalid_{name}")
    return value


def _aliases(record):
    result = {record["accession"], *record.get("accessions", ())}
    accessions = record.get("accessions", ())
    version = record.get("sequence_version")
    if accessions and "." not in accessions[0] and type(version) is int:
        result.add(f"{accessions[0]}.{version}")
    return result


def _metadata(record):
    return {"accession": record["accession"], "name": record.get("name"),
        "source_record_index": record["source_record_index"], "length": record["length"],
        "accessions": list(record.get("accessions", ())),
        "sequence_version": record.get("sequence_version"),
        "topology": record.get("topology"),
        "molecule_type": record["annotations"].get("molecule_type"),
        "sequence_available": record["sequence_available"],
        "source_organism_label": record["annotations"].get("organism"),
        "source_taxonomy_labels": list(record["annotations"].get("taxonomy", ())),
        "source_dbxrefs": list(record.get("dbxrefs", ())),
        "description": record["description"]}


def _mapping(record, request):
    length = record["length"]
    result = {"status": "available", "kind": "record_native",
        "original_accession": record["accession"], "strand": 1,
        "available_original_interval": {"start": 0, "end": length},
        "basis": "returned_genbank_record_coordinates", "is_fetched_subset": False}
    if request is None:
        return result
    if not isinstance(request, Mapping):
        raise ValueError("source_request_must_be_native_request_mapping")
    if "seq_start" not in request and "seq_stop" not in request:
        return {**result, "kind": "full_record_request"}
    result.update(kind="requested_subsequence", is_fetched_subset=True,
                  basis="native_efetch_one_based_inclusive_seq_start_seq_stop")
    result["original_accession"] = request.get("id", record["accession"])
    try:
        # EFetch requests may have been persisted as native HTTP strings.
        values = [request[key] for key in ("seq_start", "seq_stop")]
        if any(isinstance(value, bool) or not isinstance(value, (int, str)) for value in values):
            raise ValueError
        first, last = (int(value) for value in values)
        if isinstance(request.get("strand", 1), bool):
            raise ValueError
        strand = int(request.get("strand", 1))
        if first < 1 or last < first or strand not in {1, 2}:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        return {**result, "status": "unavailable", "reason": "invalid_native_fetch_interval",
                "available_original_interval": None}
    result.update(strand=strand, requested_original_interval={"start": first-1, "end": last})
    if request.get("id", record["accession"]) not in _aliases(record):
        return {**result, "status": "unavailable", "reason": "request_accession_does_not_identify_record",
                "available_original_interval": None}
    if last-first+1 != length:
        return {**result, "status": "unavailable", "reason": "request_response_length_mismatch",
                "available_original_interval": None}
    result["available_original_interval"] = {"start": first-1, "end": last}
    return result


def _original_interval(start, end, mapping):
    if mapping["status"] != "available":
        return None
    available = mapping["available_original_interval"]
    if mapping["strand"] == 1:
        return {"start": available["start"]+start, "end": available["start"]+end}
    return {"start": available["end"]-end, "end": available["end"]-start}


def _local_parts(feature, record):
    return [(index, part) for index, part in enumerate(feature["segments"])
            if part.get("ref") in {None, *_aliases(record)}
            and type(part.get("start")) is int and type(part.get("end")) is int
            and 0 <= part["start"] < part["end"] <= record["length"]]


def _feature_view(feature, record, digest, mapping):
    result = deepcopy(feature)
    result["source_feature_key"] = f"genbank:{digest}:{record['source_record_index']}:{feature['source_feature_index']}"
    result["source_accession"] = record["accession"]
    result["source_labels"] = {key: list(feature["qualifiers"].get(key, ()))
        for key in ("locus_tag", "old_locus_tag", "protein_id", "gene", "product", "EC_number")}
    result["label_interpretation"] = "native_source_assertions_not_target_assignments"
    result["mapped_original_segments"] = []
    for index, part in _local_parts(feature, record):
        interval = _original_interval(part["start"], part["end"], mapping)
        strand = part["strand"]
        if mapping["strand"] == 2:
            strand = {"+": "-", "-": "+"}.get(strand, strand)
        result["mapped_original_segments"].append({"feature_segment_index": index,
            "interval": interval, "strand": strand,
            "boundary_semantics": "nominal_fetched_bounds_mapped_source_fuzziness_retained_in_segments"})
    return result


def _selector(selector):
    if not isinstance(selector, Mapping):
        raise ValueError("selector_must_be_mapping")
    keys = set(selector) & {"locus_tag", "protein_id", "coordinate"}
    if len(keys) != 1 or set(selector) - keys - {"feature_kind", "coordinate_frame"}:
        raise ValueError("choose_one_explicit_focal_selector")
    kind = next(iter(keys))
    if kind == "coordinate":
        _integer(selector[kind], "focal_coordinate", minimum=0)
        if selector.get("coordinate_frame", "record") not in {"record", "original"}:
            raise ValueError("invalid_coordinate_frame")
    elif not isinstance(selector[kind], str) or not selector[kind] or "coordinate_frame" in selector:
        raise ValueError("invalid_focal_identifier")
    if "feature_kind" in selector and (not isinstance(selector["feature_kind"], str) or not selector["feature_kind"]):
        raise ValueError("invalid_feature_kind")
    return kind


def _focal_arc(feature, record, can_wrap):
    parts = _local_parts(feature, record)
    if len(parts) != len(feature["segments"]) or not parts:
        return None
    ordered = [part for _, part in parts]
    if can_wrap and feature["strand"] in {"+", "-"}:
        # Preserve the source's traversal. The shortest circular arc would
        # silently reinterpret a long join as a different origin-spanning gene.
        if feature["strand"] == "-":
            ordered.reverse()
        start, end, offset = ordered[0]["start"], ordered[0]["end"], 0
        previous = ordered[0]["start"]
        for part in ordered[1:]:
            if part["start"] < previous:
                offset += record["length"]
            end = max(end, part["end"]+offset)
            previous = part["start"]
        return start, end
    return min(part["start"] for part in ordered), max(part["end"] for part in ordered)


def _possibly_overlaps_window(feature, record, window):
    """Conservative location uncertainty; never declare these resolved neighbors."""
    for part in feature["segments"]:
        if part.get("ref") not in {None, *_aliases(record)}:
            continue
        start, end = part.get("start"), part.get("end")
        lower = (start if type(start) is int and part.get("start_kind")
                 in {"ExactPosition", "AfterPosition"} else 0)
        upper = (end if type(end) is int and part.get("end_kind")
                 in {"ExactPosition", "BeforePosition"} else record["length"])
        if any(max(lower, segment["start"]) < min(upper, segment["end"])
               for segment in window["available_segments"]):
            return True
    return False


def _window(start, end, length, can_wrap, mapping):
    requested_length = end-start
    if can_wrap:
        first = start % length
        unique_length = min(length, requested_length)
        first_end = min(length, first+unique_length)
        parts = [{"start": first, "end": first_end, "requested_offset": 0}]
        if first_end-first < unique_length:
            parts.append({"start": 0, "end": unique_length-(first_end-first),
                          "requested_offset": first_end-first})
        missing_left = missing_right = 0
    else:
        first, last = max(0, start), min(length, end)
        parts = ([{"start": first, "end": last, "requested_offset": first-start}]
                 if first < last else [])
        unique_length = sum(part["end"]-part["start"] for part in parts)
        missing_left, missing_right = max(0, -start), max(0, end-length)
    return {"requested": {"start": start, "end": end, "length": requested_length,
                "coordinate_frame": "returned_record_reference_axis_unclipped"},
            "requested_original_interval_unclipped": _original_interval(start, end, mapping),
            "available_segments": [{**part, "original_interval": _original_interval(
                part["start"], part["end"], mapping)} for part in parts],
            "available_unique_bp": unique_length,
            "missing_left_bp": missing_left, "missing_right_bp": missing_right,
            "requested_span_exceeds_record_length": requested_length > length,
            "repeated_circular_bp": max(0, requested_length-length) if can_wrap else 0,
            "wrap_used": can_wrap and (start < 0 or end > length or len(parts) > 1),
            "wrap_permitted": can_wrap,
            "boundary_kind": "fetched_subset_boundary" if mapping["is_fetched_subset"] else "record_boundary",
            "unavailable_flank_meaning": "outside_acquired_context_not_biological_absence"}


def genbank_neighborhood(content: bytes | str, *, accession: str, selector: Mapping,
                         left_bp: int, right_bp: int, source_request=None):
    """Return actual source features intersecting an explicitly requested window.

    Select by exact locus_tag/protein_id, or a single base coordinate. An
    optional feature_kind disambiguates annotation types. Coordinate selectors
    use the returned-record frame by default; coordinate_frame='original'
    requires a valid native fetch mapping. Identifier matches at distinct
    locations return ambiguity instead of selecting a favored candidate.

    Co-located gene/CDS entries can jointly identify the same focal footprint.
    A coordinate selector anchors that coordinate, without expanding to the
    entire length of whichever features happen to overlap it. Native qualifier
    strings and all feature parts remain source annotations, not conclusions.
    """
    _integer(left_bp, "left_flank", minimum=0)
    _integer(right_bp, "right_flank", minimum=0)
    if not isinstance(accession, str) or not accession:
        raise ValueError("explicit_accession_required")
    selector_kind = _selector(selector)
    if isinstance(content, str):
        content = content.encode("utf-8")
    if not isinstance(content, bytes):
        raise ValueError("stored_genbank_bytes_required")
    digest = hashlib.sha256(content).hexdigest()
    records = parse_genbank(content)
    matches = [record for record in records if accession in _aliases(record)]
    result = {"status": "completed", "context_status": "unavailable",
        "selection_status": None, "reason": None, "selector": dict(selector),
        "requested_accession": accession, "source_sha256": digest,
        "operation_version": VERSION, "coordinate_system": "zero_based_half_open",
        "interpretation": INTERPRETATION, "source": None, "coordinate_mapping": None,
        "focal_features": [], "window": None, "features": [],
        "uncertain_placement_features": [], "unlocated_features": []}
    if len(matches) != 1:
        result.update(selection_status="source_record_not_found" if not matches else "source_record_ambiguous",
            available_records=[_metadata(record) for record in records])
        return result
    record = matches[0]
    mapping = _mapping(record, source_request)
    result.update(source=_metadata(record), coordinate_mapping=mapping)
    if record["length"] <= 0:
        result.update(selection_status="source_record_empty")
        return result
    molecule_type = str(record["annotations"].get("molecule_type", "")).lower()
    if "protein" in molecule_type or molecule_type == "aa":
        result.update(selection_status="not_applicable", reason="protein_record_has_no_genomic_neighborhood")
        return result
    can_wrap = record.get("topology") == "circular" and not mapping["is_fetched_subset"]
    feature_pool = [feature for feature in record["features"]
                    if "feature_kind" not in selector or feature["kind"] == selector["feature_kind"]]
    if selector_kind == "coordinate":
        point = selector["coordinate"]
        if selector.get("coordinate_frame", "record") == "original":
            if mapping["status"] != "available":
                result.update(selection_status="coordinate_mapping_unavailable")
                return result
            available = mapping["available_original_interval"]
            if not available["start"] <= point < available["end"]:
                result.update(selection_status="coordinate_outside_available_context")
                return result
            point = (point-available["start"] if mapping["strand"] == 1
                     else available["end"]-1-point)
        if not 0 <= point < record["length"]:
            result.update(selection_status="coordinate_outside_available_context")
            return result
        focal = [feature for feature in feature_pool if any(
            part["start"] <= point < part["end"] for _, part in _local_parts(feature, record))]
        focal_start, focal_end = point, point+1
        result["selection_status"] = "coordinate_selected"
    else:
        focal = [feature for feature in feature_pool
                 if selector[selector_kind] in feature["qualifiers"].get(selector_kind, ())]
        if not focal:
            result.update(selection_status="identifier_not_found_in_acquired_annotations",
                examined_identifier_scope={"qualifier": selector_kind,
                    "feature_kind": selector.get("feature_kind"), "feature_count": len(feature_pool),
                    "meaning": "source_annotation_lookup_not_gene_absence"})
            return result
        footprints = {tuple((part["start"], part["end"], part["strand"], part.get("ref"))
                            for part in feature["segments"]) for feature in focal}
        if len(footprints) != 1:
            result.update(selection_status="identifier_ambiguous", focal_features=[
                _feature_view(feature, record, digest, mapping) for feature in focal])
            return result
        arc = _focal_arc(focal[0], record, can_wrap)
        if arc is None:
            result.update(selection_status="focal_location_unavailable", focal_features=[
                _feature_view(feature, record, digest, mapping) for feature in focal])
            return result
        focal_start, focal_end = arc
        result["selection_status"] = "co_located_matches" if len(focal) > 1 else "identifier_selected"
    result["focal_features"] = [_feature_view(feature, record, digest, mapping) for feature in focal]
    window = _window(focal_start-left_bp, focal_end+right_bp, record["length"], can_wrap, mapping)
    result.update(window=window, context_status="available",
        focal_span={"start": focal_start, "end": focal_end,
                    "coordinate_frame": "record_reference_axis_possibly_unwrapped",
                    "basis": "selected_coordinate" if selector_kind == "coordinate" else
                             "nominal_source_annotation_bounds_fuzziness_not_resolved"})
    focal_indices = {feature["source_feature_index"] for feature in focal}
    for feature in record["features"]:
        local = _local_parts(feature, record)
        view = _feature_view(feature, record, digest, mapping)
        visible = []
        for index, part in local:
            for window_index, segment in enumerate(window["available_segments"]):
                start, end = max(part["start"], segment["start"]), min(part["end"], segment["end"])
                if start < end:
                    offset = segment["requested_offset"]+start-segment["start"]
                    visible.append({"feature_segment_index": index, "window_segment_index": window_index,
                        "start": start, "end": end, "strand": part["strand"],
                        "requested_window_start_offset": offset,
                        "requested_window_end_offset": offset+end-start})
        fuzzy = any(part.get("start_kind") != "ExactPosition" or part.get("end_kind") != "ExactPosition"
                    for part in feature["segments"])
        if ((fuzzy or len(local) != len(feature["segments"]))
                and _possibly_overlaps_window(feature, record, window)):
            result["uncertain_placement_features"].append(view)
        if not visible:
            continue
        visible_bp = sum(part["end"]-part["start"] for part in visible)
        total_bp = sum(part["end"]-part["start"] for _, part in local)
        view.update(visible_segments=visible, is_focal=feature["source_feature_index"] in focal_indices,
            window_visibility="complete_nominal_location" if visible_bp == total_bp
                and len(local) == len(feature["segments"]) else "partial_nominal_location",
            intersection_basis="nominal_source_boundaries_fuzziness_not_resolved",
            window_order_offset=min(part["requested_window_start_offset"] for part in visible))
        result["features"].append(view)
    result["features"].sort(key=lambda feature: (feature["window_order_offset"], feature["source_feature_index"]))
    result["unlocated_features"] = deepcopy(record.get("unlocated_features", []))
    result["annotation_result"] = ("features_in_examined_source_window" if result["features"] else
        "no_known_overlap_in_source_annotations_placements_unresolved" if result["uncertain_placement_features"]
        or result["unlocated_features"] else "no_features_in_examined_source_annotations")
    result["biological_absence_established"] = False
    result["source_feature_count"] = len(record["features"])
    return result
