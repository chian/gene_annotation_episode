"""Measured evidence extents used by state ownership validation.

Coordinates and original-input attribution are independent of annotation scoring.
No applicability categories, evidence grades or score weights are assigned here.
"""
from __future__ import annotations

import math
from numbers import Real
from .domain import ContractError


def _number(value, name, *, minimum=0., maximum=None):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result) or result < minimum or (
            maximum is not None and result > maximum):
        raise ValueError(f"{name} is outside its numeric domain")
    return result


def _merge(segments):
    result = []
    for start, end in sorted(segments):
        if start == end:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def _intersection(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        start, end = max(left[i][0], right[j][0]), min(left[i][1], right[j][1])
        if start < end:
            result.append((start, end))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return result


def _mapped_coverage(store, subject_refs):
    """Only genuine submitted/derived subjects can occupy original input units."""
    result = {}
    for ref in subject_refs:
        subject = store.get(ref)
        if subject.get("record_type") not in {"input", "read_subject", "feature", "product"}:
            continue
        for span in store.coverage(ref):
            result.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
    return {ref: _merge(spans) for ref, spans in result.items()}


def _span_dimension(store, span):
    """Internal keys name actual reads; public extents keep library/member IDs."""
    if "member_ref" in span:
        return store.footprint_dimension(span)["id"]
    return span["target_ref"]


class _BoundedExtentMetric(ContractError):
    """A retained threshold cannot supply this projection's scalar geometry."""


def _metric(observation, name):
    values = []
    for index, row in enumerate(observation.get("measurements", ())):
        if row["name"] != name or row["value"]["type"] != "number":
            continue
        atom = row["value"]
        if "bound" in atom:
            raise _BoundedExtentMetric("bounded_measurement_cannot_supply_exact_extent", detail={
                "observation_ref": observation["id"], "measurement_name": name,
                "field_path": ["measurements", index, "value"], "measurement_value": dict(atom),
                "required_representation": "unbounded_extent_operand",
                "meaning": "bounded_measurement_retained_without_scalar_extent_projection"})
        values.append(atom["value"])
    return values[0] if len(values) == 1 else None


def _observation_extent(store, observation):
    """Map a native interval exactly, or retain a declared fractional proxy.

    A product's explicit native derivation path can map actual query symbols
    into original input units, including reverse, framed and compound paths.
    An older aggregate parent footprint is not a residue map: its fractional
    query coverage continues to scale the evidence operand rather than invent
    coordinates. An exactly mapped interval is not scaled by coverage again.
    Reported external experiments cannot supply native target coordinates by
    reusing their reported query start/end numbers.
    """
    if observation.get('native_blast_standard_database') is not None:
        from .native_blast_standard_database_result_publication import validate_standard_blast_database_observation
        validate_standard_blast_database_observation(store, observation)
    if observation.get('native_blast_database') is not None:
        from .native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, observation)
    footprint = _mapped_coverage(store, observation["subject_refs"])
    if observation["kind"] not in {"alignment", "profile_match", "comparison", "structure_match"}:
        return footprint, 1., {"extent_mode": "subject_footprint"}
    coverage = _metric(observation, "query_coverage")
    if coverage is not None:
        coverage = _number(coverage, "query_coverage", maximum=1)
    start, end = _metric(observation, "query_start"), _metric(observation, "query_end")
    if (observation.get("origin") == "tool" and len(observation["subject_refs"]) == 1
            and start is not None and end is not None):
        subject_ref = observation["subject_refs"][0]
        subject = store.get(subject_ref)
        if (footprint and subject["record_type"] in {"input", "read_subject", "feature", "product"}
                and hasattr(store, "has_exact_mapping")
                and store.has_exact_mapping(subject_ref)):
            if (isinstance(start, bool) or isinstance(end, bool)
                    or int(start) != start or int(end) != end or not 0 <= start < end):
                raise ValueError("native query interval is outside its actual subject")
            mapped = store.map_segments(subject_ref, [{"start": int(start), "end": int(end)}])
            exact = {}
            for span in mapped:
                exact.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
            mapping = store.sequence_mapping(subject_ref)
            original_units = {span["unit"] for span in mapping["path"]}
            query_unit = ("aa" if mapping["units_per_symbol"] == 3 else
                          next(iter(original_units)) if len(original_units) == 1 else "symbol")
            return {ref: _merge(spans) for ref, spans in exact.items()}, 1., {
                "extent_mode": ("native_input_query_interval" if subject["record_type"] == "input"
                                else "native_query_interval_mapped_to_original_input"),
                "native_query_interval": {"start": int(start), "end": int(end), "unit": query_unit},
                "query_coverage": coverage, "mapping_subject_ref": subject_ref,
                "mapping_version": mapping["version"]}
        if subject["record_type"] == "input":
            if (isinstance(start, bool) or isinstance(end, bool)
                    or int(start) != start or int(end) != end
                    or not 0 <= start < end <= subject["length"]):
                raise ValueError("native query interval is outside its actual input")
            return {subject["id"]: [(int(start), int(end))]}, 1., {
                "extent_mode": "native_input_query_interval",
                "native_query_interval": {"start": int(start), "end": int(end),
                                          "unit": subject["unit"]},
                "query_coverage": coverage}
    if coverage is not None:
        return footprint, coverage, {
            "extent_mode": "fractional_query_coverage_without_residue_map",
            "query_coverage": coverage}
    return footprint, 1., {"extent_mode": "subject_footprint_no_native_interval"}


def _observation_extents(store, observation):
    """Keep native operand coordinate systems distinct from input attribution.

    Both actual operands may occupy original input units. Each uses its own
    interval and mapping, so an external query cannot turn the whole reference
    input into alignment coverage. Exact physical paths on external references
    and their derivatives do not supply any original-input footprint.
    """
    if observation.get('native_blast_standard_database') is not None:
        from .native_blast_standard_database_result_publication import validate_standard_blast_database_observation
        validate_standard_blast_database_observation(store, observation)
    if observation.get('native_blast_database') is not None:
        from .native_blast_database_result_publication import validate_native_blast_database_observation
        validate_native_blast_database_observation(store, observation)
    intervals = observation.get("operand_intervals")
    if observation.get("origin") != "tool" or intervals is None:
        footprint, factor, details = _observation_extent(store, observation)
        if intervals:
            details = {**details, "operand_intervals": [dict(row) for row in intervals]}
        return [(footprint, factor, details)]

    extents = []
    for operand in intervals:
        subject_ref, role = operand["subject_ref"], operand["role"]
        footprint = _mapped_coverage(store, [subject_ref])
        if not footprint:
            # A source coordinate path can be exact without belonging to the
            # caller's input. Preserve it below; never relabel its numbers.
            continue
        subject = store.get(subject_ref)
        metric = "query_coverage" if role == "query" else "target_coverage"
        coverage = _metric(observation, metric)
        if coverage is not None:
            coverage = _number(coverage, metric, maximum=1)
        interval = {"start": operand["start"], "end": operand["end"], "unit": operand["unit"]}
        # The observation retains the complete operand list. A contribution
        # needs its own interval, not another copy of every other measured site.
        details = {"native_operand_interval": dict(operand), metric: coverage}
        exact_mapping = (hasattr(store, "has_exact_mapping")
                         and store.has_exact_mapping(subject_ref))
        if exact_mapping:
            mapped = store.map_segments(subject_ref, [{"start": operand["start"], "end": operand["end"]}])
            exact = {}
            for span in mapped:
                exact.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
            if not exact:
                continue
            footprint = {ref: _merge(spans) for ref, spans in exact.items()}
            mode = ("native_input_query_interval" if role == "query" and subject["record_type"] == "input"
                    else f"native_{role}_interval_mapped_to_original_input")
            details.update(extent_mode=mode, mapping_subject_ref=subject_ref,
                           mapping_version=store.sequence_mapping(subject_ref)["version"])
            factor = 1.
        elif subject["record_type"] == "input":
            # Lightweight interface fixtures may omit the exact-map API.
            if not 0 <= operand["start"] < operand["end"] <= subject["length"]:
                raise ValueError("native operand interval is outside its actual input")
            footprint = {subject_ref: [(operand["start"], operand["end"])]}
            details["extent_mode"] = ("native_input_query_interval" if role == "query"
                                      else "native_reference_interval_mapped_to_original_input")
            factor = 1.
        else:
            # Preserve the declared aggregate-product proxy for this operand;
            # it must not rescale an exactly mapped other operand.
            details["extent_mode"] = ("fractional_query_coverage_without_residue_map" if role == "query"
                                      else "fractional_reference_coverage_without_residue_map")
            factor = coverage if coverage is not None else 1.
        details[f"native_{role}_interval"] = interval
        extents.append((footprint, factor, details))
    if extents:
        return extents
    coverage = _metric(observation, "query_coverage")
    factor = _number(coverage, "query_coverage", maximum=1) if coverage is not None else 1.
    unmeasured = _mapped_coverage(store, [*observation["subject_refs"],
                                        *observation.get("source_subject_refs", ())])
    return [({}, factor, {"extent_mode": "source_subject_operand_intervals",
        "operand_intervals": [dict(row) for row in intervals], "query_coverage": coverage,
        "unmeasured_native_target_refs": sorted(unmeasured)})]


def _assessment_extent(assessment, store=None):
    """Already validated original-unit attribution, never a source measurement.

    The state boundary validates units, bounds, hypothesis coverage and assigned
    scope. Keeping this on the assessment lets several target interpretations
    reuse one immutable source observation without relabeling its subjects.
    """
    result = {}
    for span in assessment.get("target_footprint") or ():
        result.setdefault(_span_dimension(store, span), []).append((span["start"], span["end"]))
    return {ref: _merge(spans) for ref, spans in result.items()}


def _dimension_metadata(store, dimension_ref):
    """Metadata only: never read sequence, quality, title or source artifacts."""
    subject = store.get(dimension_ref)
    if subject["record_type"] == "read_subject":
        return {"id": dimension_ref, "target_ref": subject["library_ref"],
            "member_ref": subject["member_ref"], "length": subject["length"],
            "unit": subject["unit"]}
    if subject["record_type"] == "input" and subject.get("target_kind") != "read_library":
        return {"id": dimension_ref, "target_ref": dimension_ref,
            "length": subject["length"], "unit": subject["unit"]}
    raise ValueError("credit dimension must be an original sequence or read subject")


def _public_footprint(store, footprint):
    result = []
    for dimension_ref, segments in footprint.items():
        metadata = _dimension_metadata(store, dimension_ref)
        identity = {key: metadata[key] for key in ("target_ref", "member_ref", "unit") if key in metadata}
        result.extend({**identity, "start": start, "end": end} for start, end in segments)
    return result

