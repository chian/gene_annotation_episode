"""Pure requested-field views of saved genomic overlap calculation snapshots.

The caller supplies the sheet and its actual saved components. This module
validates their joins and selects data; it does not calculate interval measures,
acquire artifacts, establish execution authority, or render a model prompt.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .genomic_overlap_contracts import (
    Components, Projection, Selector, Sheet,
    canonical_genomic_overlap_sheet_sha256,
    validate_genomic_overlap_record,
)

__all__ = ["project_genomic_overlap_result"]


def _require(condition: bool, meaning: str) -> None:
    if not condition:
        raise ValueError("genomic_overlap_projection:" + meaning)


def _ordered_keys(rows: list[dict], field: str, expected: list[str], meaning: str) -> None:
    _require([row[field] for row in rows] == expected, meaning)


def _validate_joins(sheet: Sheet, components: Components, selector: Selector) -> None:
    """Validate identity/order and copied qualifications, without recomputation."""
    request = sheet["request"]
    specs = request["region_sets"]
    set_keys = [row["set_key"] for row in specs]
    pairs = request["comparisons"]
    pair_keys = [row["comparison_key"] for row in pairs]
    _require(len(set(set_keys)) == len(set_keys), "duplicate_set_key")
    _require(len(set(pair_keys)) == len(pair_keys), "duplicate_comparison_key")
    endpoints = [(a, b) for position, a in enumerate(set_keys) for b in set_keys[position + 1:]]
    _require([(row["a_set_key"], row["b_set_key"]) for row in pairs] == endpoints,
             "request_comparison_order")
    _require([row["ordinal"] for row in pairs] == list(range(len(pairs))), "comparison_ordinals")
    _ordered_keys(sheet["sets"], "set_key", set_keys, "sheet_set_order")
    _ordered_keys(components["sets"], "set_key", set_keys, "component_set_order")
    _ordered_keys(sheet["comparisons"], "comparison_key", pair_keys, "sheet_comparison_order")
    _ordered_keys(sheet["reference_relations"], "comparison_key", pair_keys, "reference_order")
    _ordered_keys(components["pairs"], "comparison_key", pair_keys, "component_pair_order")
    selected = selector["comparison_keys"]
    _require(len(set(selected)) == len(selected), "duplicate_comparison_selection")
    _require([key for key in pair_keys if key in selected] == selected, "comparison_selection_order")
    for parameter in ("minimum_a_fraction", "minimum_b_fraction"):
        fraction = selector["parameters"][parameter]
        _require(fraction["numerator"] <= fraction["denominator"], "fraction_threshold")
    if selector["mode"] == "native_result":
        _require(selector["saved_sheet_file"] is None, "native_selector_saved_sheet")
    else:
        identity = selector["saved_sheet_file"]
        _require(identity is not None, "saved_selector_sheet_required")
        _require(identity["format"] == sheet["version"], "saved_selector_sheet_format")
        _require(identity["sha256"] == components["source_sheet_sha256"], "saved_selector_sheet_hash")

    regions, geometry, tokens = {}, {}, set()
    by_set = dict(zip(set_keys, sheet["sets"]))
    by_spec = dict(zip(set_keys, specs))
    for spec, parsed, calculated in zip(specs, sheet["sets"], components["sets"]):
        key = spec["set_key"]
        _require(parsed["source_file"] == spec["source"]["file"], "source_file_join")
        _require(parsed["result_extent"] == calculated["result_extent"], "set_extent_join")
        ordinals = [row["data_ordinal"] for row in parsed["regions"]]
        _require(ordinals == sorted(set(ordinals)), "region_ordinal_order")
        keys = [row["occurrence_key"] for row in parsed["regions"]]
        _require(len(set(keys)) == len(keys), "duplicate_occurrence_key")
        _require([(row["set_key"], row["occurrence_key"]) for row in calculated["region_geometry"]]
                 == [(key, occurrence) for occurrence in keys], "geometry_occurrence_order")
        for row, shape in zip(parsed["regions"], calculated["region_geometry"]):
            identity = key, row["occurrence_key"]
            _require(row["native_token"] not in tokens, "duplicate_native_token")
            tokens.add(row["native_token"])
            regions[identity], geometry[identity] = row, shape

    for pair, native, relation, calculated in zip(
            pairs, sheet["comparisons"], sheet["reference_relations"], components["pairs"]):
        pair_key = pair["comparison_key"]
        a, b = pair["a_set_key"], pair["b_set_key"]
        for row in (relation, calculated):
            _require((row["a_set_key"], row["b_set_key"]) == (a, b), "pair_endpoint_join")
        _require(native["receipt"]["comparison_key"] == pair_key, "receipt_comparison_join")
        for side, key in (("a", a), ("b", b)):
            operand = native["receipt"][side]
            _require(operand["set_key"] == key and operand["original_file"] == by_set[key]["source_file"],
                     "receipt_operand_join")
            _require(relation[side + "_reference"] == by_spec[key]["reference"], "reference_input_join")
        _require(calculated["reference_relation"] == relation["relation"], "reference_relation_join")
        _require(calculated["result_extent"] == native["result_extent"], "pair_extent_join")
        native_rows = {row["pair_key"]: row for row in native["valid_pairs"]}
        edges = {row["pair_key"]: row for row in calculated["edges"]}
        _require(len(native_rows) == len(native["valid_pairs"]), "duplicate_native_pair_key")
        _require(len(edges) == len(calculated["edges"]) and edges.keys() == native_rows.keys(),
                 "edge_pair_join")
        _require(list(edges) == list(native_rows), "edge_pair_order")
        attached_keys: dict[tuple[str, str, str], list[str]] = {}
        for key, row in native_rows.items():
            _require(row["comparison_key"] == pair_key, "native_comparison_join")
            edge = edges[key]
            for side, set_key in (("a", a), ("b", b)):
                endpoint = row[side]
                identity = endpoint["set_key"], endpoint["occurrence_key"]
                _require(endpoint["set_key"] == set_key and identity in regions, "native_occurrence_join")
                _require(all(endpoint[field] == regions[identity][field]
                             for field in ("native_token", "chromosome", "start", "end")),
                         "native_endpoint_join")
                _require((edge[side + "_set_key"], edge[side + "_occurrence_key"]) == identity,
                         "edge_occurrence_join")
                attached_keys.setdefault(("unfiltered", *identity), []).append(key)
                if edge["selected"]:
                    attached_keys.setdefault(("selected", *identity), []).append(key)
            _require(edge["overlap_bp"] == row["native_overlap_bp"], "native_width_join")
        expected = [(pair_key, population, set_key, row["occurrence_key"])
                    for population in ("unfiltered", "selected")
                    for set_key in (a, b) for row in by_set[set_key]["regions"]]
        actual = [(row["comparison_key"], row["population"], row["set_key"], row["occurrence_key"])
                  for row in calculated["occurrences"]]
        _require(actual == expected, "occurrence_population_order")
        for row in calculated["occurrences"]:
            identity = row["set_key"], row["occurrence_key"]
            _require(row["span_bp"] == geometry[identity]["span_bp"], "occurrence_geometry_join")
            _require(row["result_extent"] == calculated["result_extent"], "occurrence_extent_join")
            keys = row["pair_keys"]
            _require(len(set(keys)) == len(keys), "duplicate_occurrence_pair_key")
            for key in keys:
                _require(key in edges, "occurrence_pair_join")
                edge = edges[key]
                _require(identity in ((edge["a_set_key"], edge["a_occurrence_key"]),
                                      (edge["b_set_key"], edge["b_occurrence_key"])),
                         "occurrence_pair_endpoint")
                _require(row["population"] != "selected" or edge["selected"], "selected_occurrence_pair")
            expected_keys = attached_keys.get((row["population"], *identity), [])
            _require(keys == expected_keys, "occurrence_pair_membership_order")

    selection = selector["projection"]
    occurrence_keys = [(row["set_key"], row["occurrence_key"]) for row in selection["occurrence_keys"]]
    _require(len(set(occurrence_keys)) == len(occurrence_keys), "duplicate_occurrence_selection")
    if selection["kind"] != "occurrence_rows":
        _require(not occurrence_keys, "unexpected_occurrence_selection")
    selected_sets = {pair[side] for pair in pairs if pair["comparison_key"] in selected
                     for side in ("a_set_key", "b_set_key")}
    _require(all(key in regions and key[0] in selected_sets for key in occurrence_keys),
             "unknown_occurrence_selection")


def _extent(extents: list[str]) -> str:
    if all(value == "complete" for value in extents):
        return "complete"
    if all(value == "unavailable" for value in extents):
        return "unavailable"
    return "partial"


def _unique_failures(failures: list[dict]) -> list[dict]:
    seen, result = set(), []
    for failure in failures:
        key = json.dumps(failure, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            result.append(failure)
    return result


def _path_matches(path: str | None, paths: list[str]) -> bool:
    return path is not None and any(path == item or path.startswith(item + "/") for item in paths)


def _row_failures(sheet: Sheet, components: Components, *, pair_index: int | None,
                  set_keys: list[str], paths: list[str], native_needed: bool) -> list[dict]:
    """Keep original-stage qualifications and only requested calculated fields."""
    pair_key = None if pair_index is None else sheet["request"]["comparisons"][pair_index]["comparison_key"]
    candidates = sheet["issues"] + components["issues"]
    artifacts = set()
    source_paths = []
    for index, parsed in enumerate(sheet["sets"]):
        if parsed["set_key"] in set_keys:
            artifacts.add(parsed["source_file"]["artifact_ref"])
            source_paths.append(f"/sets/{index}")
            candidates += parsed["issues"] + components["sets"][index]["issues"]
            for row in parsed["invalid_records"]:
                candidates += row["issues"]
    if pair_index is not None:
        reference = sheet["reference_relations"][pair_index]
        candidates += reference["issues"]
        source_paths.append(f"/reference_relations/{pair_index}")
        if native_needed:
            native = sheet["comparisons"][pair_index]
            candidates += native["issues"] + native["receipt"]["issues"] + components["pairs"][pair_index]["issues"]
            source_paths.extend((f"/comparisons/{pair_index}", f"/pairs/{pair_index}"))
            for role in ("stdout", "stderr"):
                if native["receipt"][role] is not None:
                    artifacts.add(native["receipt"][role]["artifact_ref"])
            for row in native["rejected_rows"]:
                candidates += row["issues"]
    result = []
    for failure in candidates:
        if failure["comparison_key"] is not None and failure["comparison_key"] != pair_key:
            continue
        if failure["set_key"] is not None and failure["set_key"] not in set_keys:
            continue
        if not native_needed and failure["stage"] in {"native", "capture", "parse", "authority"}:
            continue
        path = failure["field_path"]
        if failure["stage"] in {"calculate", "project"} and failure["code"] not in {
                "reference_metadata_conflict", "reference_identity_unavailable"}:
            if not _path_matches(path, paths):
                continue
        elif failure["comparison_key"] is None and failure["set_key"] is None:
            if failure["artifact_ref"] not in artifacts and not _path_matches(path, source_paths + paths):
                continue
        result.append(failure)
    return _unique_failures(result)


def _missing_failures(measurements: dict, paths: list[str], *, issues: list[dict],
                      set_key: str | None, comparison_key: str | None,
                      artifact_ref: str | None, locator: dict | None = None) -> list[dict]:
    result = []
    for value, path in zip(measurements.values(), paths):
        missing = value is None or isinstance(value, dict) and value.get("value") is None
        if not missing or any(_path_matches(issue["field_path"], [path]) for issue in issues):
            continue
        zero = isinstance(value, dict) and value["missing_reason"] == "zero_denominator"
        result.append({"code": "zero_denominator" if zero else "requested_field_unavailable",
            "stage": "project", "set_key": set_key, "comparison_key": comparison_key,
            "artifact_ref": artifact_ref, "locator": locator, "field_path": path,
            "expected_value": None, "observed_value": deepcopy(value), "partial_artifact_refs": [],
            "requirement": "nonzero_denominator" if zero else "requested_selected_field"})
    return result


def _pair_dependencies(index: int, fields: list[str], set_indices: dict[str, int], pair: dict) -> list[str]:
    """Fixed input qualifications for requested ratios, not a scoring language."""
    paths = [f"/pairs/{index}/" + field.replace(".", "/") for field in fields]
    for field in fields:
        _, name = field.split(".")
        if name in {"jaccard_bp", "selected_shared_union_fraction"}:
            paths.append(f"/pairs/{index}/unfiltered/combined_union_bp")
            for side in ("a", "b"):
                paths.append(f"/sets/{set_indices[pair[side + '_set_key']]}/union_bp")
        elif name in {"a_union_coverage_fraction", "b_union_coverage_fraction"}:
            paths.append(f"/sets/{set_indices[pair[name[0] + '_set_key']]}/union_bp")
        elif name in {"a_region_overlap_fraction", "b_region_overlap_fraction"}:
            paths.append(f"/sets/{set_indices[pair[name[0] + '_set_key']]}/region_count")
    return paths


def project_genomic_overlap_result(sheet: Sheet, components: Components, *,
                                  selector: Selector) -> Projection:
    """Return the requested measurements and their stored qualifications only.

    API/schema/identity inconsistencies raise ValueError. Scientific missing
    values retain nulls and located failures. All returned containers are detached.
    Selection uses the frozen request order, then occurrence filtering, then the
    explicit page. Page totals count available retained rows, not unknown input
    populations. Paging never upgrades the underlying scientific extent.
    """
    sheet = validate_genomic_overlap_record("Sheet", sheet)
    components = validate_genomic_overlap_record("Components", components)
    selector = validate_genomic_overlap_record("Selector", selector)
    _require(components["source_sheet_sha256"] == canonical_genomic_overlap_sheet_sha256(sheet),
             "source_sheet_hash")
    _require(components["parameters"] == selector["parameters"], "parameter_mismatch")
    _validate_joins(sheet, components, selector)
    selection = selector["projection"]
    kind, fields = selection["kind"], selection["measurement_fields"]
    selected_keys = set(selector["comparison_keys"])
    pair_indices = [i for i, row in enumerate(components["pairs"]) if row["comparison_key"] in selected_keys]
    set_keys = {components["pairs"][i][side] for i in pair_indices for side in ("a_set_key", "b_set_key")}
    set_indices = {row["set_key"]: i for i, row in enumerate(components["sets"])}
    occurrence_filter = {(row["set_key"], row["occurrence_key"]) for row in selection["occurrence_keys"]}
    # Rows carry their source index internally; none of this metadata is projected.
    if kind == "pair_metrics":
        population = [(i, None, components["pairs"][i]) for i in pair_indices]
    elif kind == "set_metrics":
        population = [(i, None, row) for i, row in enumerate(components["sets"]) if row["set_key"] in set_keys]
    else:
        population = [(i, j, row) for i in pair_indices
                      for j, row in enumerate(components["pairs"][i]["occurrences"])
                      if not occurrence_filter or (row["set_key"], row["occurrence_key"]) in occurrence_filter]
    extents = [row["result_extent"] for _, _, row in population]
    if not population and kind == "occurrence_rows":
        extents = [components["pairs"][i]["result_extent"] for i in pair_indices]
    offset, limit = selection["offset"], selection["limit"]
    page = population[offset:offset + limit]
    rows, failures = [], []
    for index, occurrence_index, row in page:
        if kind == "pair_metrics":
            measurements = {field: row[field.split(".")[0]][field.split(".")[1]] for field in fields}
            paths = [f"/pairs/{index}/" + field.replace(".", "/") for field in fields]
            needed = _pair_dependencies(index, fields, set_indices, row)
            issues = _row_failures(sheet, components, pair_index=index,
                set_keys=[row["a_set_key"], row["b_set_key"]], paths=needed, native_needed=True)
            native_file = sheet["comparisons"][index]["receipt"]["stdout"]
            issues += _missing_failures(measurements, paths, issues=issues, set_key=None,
                comparison_key=row["comparison_key"], artifact_ref=None if native_file is None else native_file["artifact_ref"])
            projected = {key: row[key] for key in ("comparison_key", "a_set_key", "b_set_key", "result_extent", "reference_relation")}
            projected.update(observed_interpretation=row["observed"]["interpretation"], measurements=measurements, issues=issues)
        elif kind == "set_metrics":
            measurements = {field: row[field] for field in fields}
            paths = [f"/sets/{index}/{field}" for field in fields]
            issues = _row_failures(sheet, components, pair_index=None,
                set_keys=[row["set_key"]], paths=paths, native_needed=False)
            issues += _missing_failures(measurements, paths, issues=issues, set_key=row["set_key"],
                comparison_key=None, artifact_ref=sheet["sets"][index]["source_file"]["artifact_ref"])
            projected = {"set_key": row["set_key"], "result_extent": row["result_extent"],
                         "measurements": measurements, "issues": issues}
        else:
            measurements = {field: row[field] for field in fields}
            paths = [f"/pairs/{index}/occurrences/{occurrence_index}/{field}" for field in fields]
            native_needed = any(field != "span_bp" for field in fields)
            issues = _row_failures(sheet, components, pair_index=index,
                set_keys=[components["pairs"][index][side] for side in ("a_set_key", "b_set_key")]
                         if native_needed else [row["set_key"]],
                paths=paths, native_needed=native_needed)
            parsed = sheet["sets"][set_indices[row["set_key"]]]
            source = next(item for item in parsed["regions"] if item["occurrence_key"] == row["occurrence_key"])
            issues += _missing_failures(measurements, paths, issues=issues, set_key=row["set_key"],
                comparison_key=row["comparison_key"], artifact_ref=parsed["source_file"]["artifact_ref"], locator=source["locator"])
            projected = {key: row[key] for key in ("comparison_key", "population", "set_key", "occurrence_key", "result_extent")}
            projected["measurements"] = measurements
        rows.append(projected)
        failures += issues

    # An all-occurrences request must qualify absent source rows even when its
    # available page contains only another input. An explicit list already
    # joins known retained occurrences; source failures stay with its page.
    if kind == "occurrence_rows" and not occurrence_filter:
        for key in (row["set_key"] for row in components["sets"] if row["set_key"] in set_keys):
            index = set_indices[key]
            if sheet["sets"][index]["result_extent"] != "complete":
                failures += _row_failures(sheet, components, pair_index=None,
                    set_keys=[key], paths=[], native_needed=False)
    result = {"version": "genomic_overlap_projection_v1",
        "source_sheet_sha256": components["source_sheet_sha256"], "parameters": components["parameters"],
        "kind": kind, "page": {"offset": offset, "limit": limit,
            "total_rows": len(population), "returned_rows": len(rows)},
        "result_extent": _extent(extents),
        "reference_relations": [sheet["reference_relations"][i] for i in pair_indices],
        "pair_rows": rows if kind == "pair_metrics" else [],
        "set_rows": rows if kind == "set_metrics" else [],
        "occurrence_rows": rows if kind == "occurrence_rows" else [],
        "failures": _unique_failures(failures), "measurement_fields": fields}
    return validate_genomic_overlap_record("Projection", result)
