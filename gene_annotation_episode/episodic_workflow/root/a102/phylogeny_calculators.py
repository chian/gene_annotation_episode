"""Deterministic arithmetic on saved phylogeny documents and explicit operands.

This module neither parses bytes nor acquires metadata. Populations and maps
are supplied by the caller. Raw documents remain untouched; quantities retain
their exact operands, units and missing states. No annotation score is defined.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import math

from . import phylogeny_calculation_contracts as c
from .phylogeny_format_contracts import validate_alignment_document, validate_tree_record


def _count(value, population, unit, method, **kwargs):
    return c.quantity(value, population=population, unit=unit, method=method, **kwargs)


def _finite_sum(values):
    try:
        return math.fsum(values)
    except (OverflowError, ValueError):
        c.fail("arithmetic_nonfinite")


def _state(alignment, population):
    if alignment["completeness"] == population["completeness"] == "complete":
        return "available"
    return "truncated" if "truncated" in (alignment["completeness"], population["completeness"]) else "missing"


def _pairs(pairs, allowed):
    c.sequence(pairs)
    result = []
    for pair in pairs:
        c.sequence(pair)
        c.require(len(pair) == 2, "pair_shape_invalid")
        for index in pair:
            c.integer(index)
            c.require(index in allowed, "pair_member_outside_population")
        result.append(tuple(pair))
    c.require(len(result) == len(set(result)), "duplicate_pair")
    return result


def _alphabet_symbols(alphabet):
    if alphabet == "dna":
        return set("ACGT"), set("RYSWKMBDHVN"), set()
    if alphabet == "rna":
        return set("ACGU"), set("RYSWKMBDHVN"), set()
    if alphabet == "protein":
        return set("ACDEFGHIKLMNPQRSTVWY"), set("BZJX"), {"*"}
    return set(), set(), set()


def alignment_components(alignment: dict, *, population: dict, alphabet: str,
                         case_policy: str, pairs: tuple[tuple[int, int], ...] = ()) -> dict:
    """Count selected cells, canonical conservation and disjoint pair categories.

    Canonical fractions divide all selected cells; site entropy/majority divide
    canonical states only. Literal symbol counts always preserve original case.
    Identical groups compare the whole supplied row under the explicit policy.
    """
    alignment = validate_alignment_document(alignment)
    c.alignment_population(population, alignment)
    c.require(alphabet in ("dna", "rna", "protein", "unknown"), "alphabet_invalid")
    c.require(case_policy in ("uppercase", "literal"), "case_policy_invalid")
    requested_pairs = _pairs(pairs, set(population["row_indices"]))
    pid = population["population_id"]
    state = _state(alignment, population)
    complete = state == "available"
    population_reqs = [] if complete else [c.scope(pid) + "/alignment_population_incomplete"]
    alphabet_reqs = [c.scope(pid) + "/alphabet_required"] if alphabet == "unknown" else []
    classified = complete and alphabet != "unknown"
    rows = {r["row_index"]: r["sequence"] for r in alignment["rows"]}
    selected_rows, columns = population["row_indices"], population["columns_0based"]
    n, length = len(selected_rows), len(columns)
    canonical, ambiguity, stops = _alphabet_symbols(alphabet)
    normalized = {i: rows[i].upper() if case_policy == "uppercase" else rows[i] for i in selected_rows}
    # Unicode case expansion would change positional correspondence.
    c.require(all(len(normalized[i]) == len(rows[i]) for i in selected_rows), "case_policy_changes_coordinates")
    def count(value, unit, method, *, known=complete, requirements=population_reqs):
        return _count(value if known else None, pid, unit, method,
                      state=state if not complete else "missing", requirements=requirements if not known else ())
    def frac(num, den, method, *, known=complete, requirements=population_reqs):
        return c.ratio(num if known else None, den if known else None, population=pid, method=method,
                       state=state if not complete else "missing", requirements=requirements if not known else ())
    sites, totals = [], Counter()
    for column in columns:
        raw_counts = Counter(rows[i][column] for i in selected_rows if column < len(rows[i]))
        counts = Counter(normalized[i][column] for i in selected_rows if column < len(normalized[i]))
        values = {"gap": counts["-"], "canonical": sum(counts[s] for s in canonical),
                  "ambiguity": sum(counts[s] for s in ambiguity), "stop": sum(counts[s] for s in stops)}
        values["other_nongap"] = sum(counts.values()) - sum(values.values())
        totals.update(values)
        row = {"column_0based": column,
               "symbol_counts": [{"symbol": s, "count": v} for s, v in sorted(raw_counts.items())]}
        for kind, value in values.items():
            known = complete if kind == "gap" else classified
            row[kind + "_count"] = count(value, "characters", kind + "_symbol_count", known=known,
                                         requirements=population_reqs + (alphabet_reqs if kind != "gap" else []))
        row["gap_fraction"] = frac(values["gap"], n, "site_gap_fraction")
        row["canonical_fraction"] = frac(values["canonical"], n, "site_canonical_fraction",
                                          known=classified, requirements=population_reqs + alphabet_reqs)
        denom = values["canonical"]
        row["canonical_majority_fraction"] = frac(max((counts[s] for s in canonical), default=0), denom,
             "canonical_majority_fraction", known=classified, requirements=population_reqs + alphabet_reqs)
        entropy = -math.fsum((counts[s] / denom) * math.log2(counts[s] / denom)
                            for s in canonical if counts[s]) if denom and classified else None
        row["canonical_entropy_bits"] = c.quantity(entropy, population=pid, unit="bits",
             method="canonical_entropy_bits", denominator=denom if classified else None,
             state=state if not complete else "missing", requirements=population_reqs + alphabet_reqs)
        sites.append(row)
    row_components = []
    for i in selected_rows:
        # A surviving complete row can still be measured when another row is
        # truncated; no aggregate denominator is recovered from this fact.
        row_complete = all(j < len(rows[i]) for j in columns)
        nongaps = sum(rows[i][j] != "-" for j in columns if j < len(rows[i]))
        row_components.append({"row_index": i,
            "nongap_count": count(nongaps, "characters", "row_nongap_count", known=row_complete),
            "matrix_occupancy": frac(nongaps, length, "row_matrix_occupancy", known=row_complete)})
    pair_components = []
    for a, b in requested_pairs:
        values = Counter()
        for j in columns:
            if j >= len(normalized[a]) or j >= len(normalized[b]):
                continue
            left, right = normalized[a][j], normalized[b][j]
            if left == right == "-":
                values["both_gap_positions"] += 1
            elif left == "-":
                values["a_gap_only_positions"] += 1
            elif right == "-":
                values["b_gap_only_positions"] += 1
            elif left in canonical and right in canonical:
                values["identical_positions" if left == right else "substitutions"] += 1
            else:
                values["unpaired_nongap_ambiguous_positions"] += 1
        row = {"row_a": a, "row_b": b}
        for name in ("identical_positions", "substitutions", "both_gap_positions", "a_gap_only_positions",
                     "b_gap_only_positions", "unpaired_nongap_ambiguous_positions"):
            depends_on_alphabet = name in ("identical_positions", "substitutions", "unpaired_nongap_ambiguous_positions")
            row[name] = count(values[name], "columns", "pairwise_" + name,
                              known=classified if depends_on_alphabet else complete,
                              requirements=population_reqs + (alphabet_reqs if depends_on_alphabet else []))
        row["identity_fraction"] = frac(values["identical_positions"],
            values["identical_positions"] + values["substitutions"], "pairwise_canonical_identity",
            known=classified, requirements=population_reqs + alphabet_reqs)
        pair_components.append(row)
    grouped = defaultdict(list)
    if complete:
        for i in selected_rows:
            grouped[normalized[i]].append(i)
    result = {"population_id": pid, "alignment_id": alignment["alignment_id"],
        "member_count": count(n, "rows", "selected_row_count"),
        "site_count": count(length, "columns", "selected_column_count"),
        "cell_count": count(n * length, "characters", "selected_cell_count"),
        "sites": sites, "rows": row_components, "pairs": pair_components,
        "identical_sequence_groups": [{"row_indices": indices,
             "size": count(len(indices), "rows", "identical_final_sequence_group_size")}
             for indices in grouped.values() if len(indices) > 1]}
    for kind in ("gap", "canonical", "ambiguity", "stop", "other_nongap"):
        known = complete if kind == "gap" else classified
        reqs = population_reqs + (alphabet_reqs if kind != "gap" else [])
        result[kind + "_cells"] = count(totals[kind], "characters", kind + "_symbol_count", known=known, requirements=reqs)
        result[kind + "_fraction"] = frac(totals[kind], n * length, kind + "_cell_fraction", known=known, requirements=reqs)
    return result


def ungapped_coordinate_map(alignment: dict, *, row_indices: tuple[int, ...]) -> tuple[dict, ...]:
    """Map supplied row columns to staged nongap offsets, never original bases."""
    alignment = validate_alignment_document(alignment)
    c.unique_indices(row_indices, stored=False)
    c.require(all(i < len(alignment["rows"]) for i in row_indices), "coordinate_row_outside_alignment")
    result = []
    for i in row_indices:
        offset = 0
        for column, symbol in enumerate(alignment["rows"][i]["sequence"]):
            result.append({"alignment_id": alignment["alignment_id"], "row_index": i,
                           "column_0based": column, "ungapped_position_0based": None if symbol == "-" else offset})
            offset += symbol != "-"
    return tuple(result)


def _interval_union_size(intervals):
    total, last = 0, None
    for start, end in sorted(intervals):
        if last is None or start >= last:
            total += end - start
            last = end
        elif end > last:
            total += end - last
            last = end
    return total


def original_member_coverage(alignment: dict, *, population: dict, members: tuple[dict, ...],
                             correspondences: tuple[dict, ...]) -> dict:
    """Union explicit original intervals; partial maps never imply full coverage."""
    alignment = validate_alignment_document(alignment)
    c.alignment_population(population, alignment)
    c.sequence(members)
    c.sequence(correspondences)
    pid, aid = population["population_id"], alignment["alignment_id"]
    selected_rows, selected_columns = set(population["row_indices"]), set(population["columns_0based"])
    expected, original_facts = {}, {}
    for row in members:
        c.shape(row, {"row", "member", "original_length", "original_sequence_sha256", "evidence"}, "coverage_member_shape_invalid")
        c.shape(row["row"], {"alignment_id", "row_index"}, "row_reference_invalid")
        c.integer(row["row"]["row_index"])
        c.require(row["row"]["alignment_id"] == aid and row["row"]["row_index"] in selected_rows, "coverage_row_identity_conflict")
        m = c.member(row["member"])
        key = (row["row"]["row_index"], m)
        c.require(key not in expected, "duplicate_coverage_member")
        c.integer(row["original_length"], nullable=True)
        c.digest(row["original_sequence_sha256"], nullable=True)
        c.evidence(row["evidence"])
        prior = original_facts.get(m)
        if prior is not None:
            for field in ("original_length", "original_sequence_sha256"):
                c.require(prior[field] is None or row[field] is None or prior[field] == row[field], "original_member_facts_conflict")
        original_facts[m] = {field: row[field] if row[field] is not None else prior[field] if prior else None
                             for field in ("original_length", "original_sequence_sha256")}
        expected[key] = row
    c.require(selected_rows == {key[0] for key in expected}, "coverage_member_population_incomplete")
    offsets = {(x["row_index"], x["column_0based"]): x["ungapped_position_0based"]
               for x in ungapped_coordinate_map(alignment, row_indices=tuple(population["row_indices"]))}
    mappings = {}
    intervals = defaultdict(list)
    for record in correspondences:
        c.shape(record, {"alignment_id", "row_index", "column_0based", "staged_ungapped_position_0based",
            "original_member", "original_interval_0based_half_open", "strand", "translation_table", "transformation_id", "evidence"},
            "correspondence_shape_invalid")
        for field in ("row_index", "column_0based"):
            c.integer(record[field])
        key = record["row_index"], record["column_0based"]
        c.require(record["alignment_id"] == aid and key in offsets, "correspondence_identity_conflict")
        c.integer(record["staged_ungapped_position_0based"], nullable=True)
        c.require(record["staged_ungapped_position_0based"] is None or
                  record["staged_ungapped_position_0based"] == offsets[key], "staged_coordinate_conflict")
        c.require(record["strand"] in ("+", "-", "unknown"), "strand_invalid")
        c.integer(record["translation_table"], nullable=True, minimum=1)
        c.text(record["transformation_id"], nullable=True)
        c.evidence(record["evidence"])
        original_member, interval = record["original_member"], record["original_interval_0based_half_open"]
        member_key = None if original_member is None else c.member(original_member)
        if member_key is not None:
            c.require((key[0], member_key) in expected, "correspondence_member_identity_conflict")
        if offsets[key] is None:
            c.require(interval is None, "gap_original_coordinate_conflict")
        if interval is not None:
            c.sequence(interval, stored=True)
            c.require(len(interval) == 2 and member_key is not None, "original_interval_invalid")
            for pos in interval:
                c.integer(pos)
            c.require(interval[0] < interval[1], "original_interval_invalid")
            length = expected[(key[0], member_key)]["original_length"]
            c.require(length is None or interval[1] <= length, "original_interval_outside_member")
        semantic = (member_key, tuple(interval) if interval is not None else None,
                    record["strand"], record["translation_table"], record["transformation_id"])
        c.require(key not in mappings or mappings[key] == semantic, "correspondence_conflict")
        mappings[key] = semantic
        if interval is not None and key[1] in selected_columns:
            intervals[(key[0], member_key)].append(tuple(interval))
    requirements, diagnostics, result_rows = [], [], []
    complete_population = _state(alignment, population) == "available"
    for (row_index, m), row in expected.items():
        scope = c.scope(pid, "row", str(row_index), "member", m[0], m[1])
        map_complete = complete_population and all(
            (row_index, j) in offsets and (offsets[(row_index, j)] is None or
             ((row_index, j) in mappings and mappings[(row_index, j)][0] is not None and mappings[(row_index, j)][1] is not None))
            for j in selected_columns)
        missing = []
        for needed, reason, role, kind in (
            (not map_complete, "original_residue_map_required", "original_residue_map", "scientific_metadata"),
            (row["original_length"] is None, "original_member_length_required", "original_member_length", "input_metadata")):
            if needed:
                req = c.requirement(scope, reason, role=role, kind=kind, source_refs=[alignment["artifact"]["source_ref"]])
                requirements.append(req)
                missing.append(req["requirement_id"])
        covered = _interval_union_size(intervals[(row_index, m)])
        if not map_complete:
            diagnostics.append(c.diagnostic("original_map_incomplete", path="/rows/" + str(len(result_rows))))
        length = row["original_length"]
        result_rows.append({"row_index": row_index, "member": deepcopy(row["member"]),
            "original_length": _count(length, pid, "positions", "supplied_original_member_length",
                origin="native_observed", evidence_rows=row["evidence"],
                requirements=[scope + "/original_member_length_required"] if length is None else []),
            "original_covered_positions": _count(covered if map_complete or intervals[(row_index, m)] else None,
                pid, "positions", "original_interval_union" if map_complete else "known_original_interval_union",
                requirements=[scope + "/original_residue_map_required"] if not map_complete and not intervals[(row_index, m)] else []),
            "original_member_coverage": c.ratio(covered if map_complete else None, length,
                population=pid, method="original_member_coverage", requirements=missing)})
    return {"population_id": pid, "alignment_id": aid, "rows": result_rows,
            "missing_requirements": requirements, "diagnostics": diagnostics}


def _tips(tree):
    return {node["node_index"] for node in tree["nodes"] if not node["child_indices"]}


def _canonical_side(side, universe):
    left, right = tuple(sorted(side)), tuple(sorted(universe - set(side)))
    return min((left, right), key=lambda x: (len(x), x))


def _tree_splits(tree, selected=None, tip_map=None):
    """Restrict edge bipartitions and deduplicate representational edges.

    Restricting edge leaf sets then dropping trivial splits is the split-set
    equivalent of pruning omitted leaves and suppressing degree-two nodes.
    """
    all_tips = _tips(tree)
    selected = all_tips if selected is None else set(selected)
    tip_map = {i: i for i in selected} if tip_map is None else tip_map
    universe = set(tip_map[i] for i in selected)
    descendant_sets = {}
    for node in reversed(tree["nodes"]):
        index = node["node_index"]
        if not node["child_indices"]:
            descendant_sets[index] = {tip_map[index]} if index in selected else set()
        else:
            descendant_sets[index] = set().union(*(descendant_sets[i] for i in node["child_indices"]))
    splits = defaultdict(list)
    for node in tree["nodes"]:
        if node["parent_index"] is None:
            continue
        side = descendant_sets[node["node_index"]]
        if len(side) >= 2 and len(universe - side) >= 2:
            splits[_canonical_side(side, universe)].append(node["node_index"])
    return dict(splits), universe


def _split_id(tree_id, side):
    return tree_id + "/split/" + ",".join(str(i) for i in side)


def _path_edges(tree, a, b):
    ancestors = {}
    current, path = a, []
    while current is not None:
        ancestors[current] = tuple(path)
        path.append(current)
        current = tree["nodes"][current]["parent_index"]
    current, b_path = b, []
    while current not in ancestors:
        b_path.append(current)
        current = tree["nodes"][current]["parent_index"]
    return list(ancestors[current]) + b_path


def _support_rows(tree, support_observations, native_measurements):
    c.sequence(native_measurements)
    c.sequence(support_observations)
    native = {}
    for row in native_measurements:
        c.native_observation(row)
        c.require(row["observation_id"] not in native, "duplicate_native_observation")
        native[row["observation_id"]] = row
    by_node = defaultdict(list)
    seen = set()
    for row in support_observations:
        c.shape(row, {"tree_id", "node_index", "native_observation_id", "source_kind", "method", "scale",
                      "command_id", "bootstrap_population_id", "evidence"}, "support_observation_shape_invalid")
        c.integer(row["node_index"])
        c.require(row["tree_id"] == tree["tree_id"] and row["node_index"] < len(tree["nodes"]), "support_tree_identity_conflict")
        c.require(row["node_index"] != tree["root_node_index"], "root_support_not_edge")
        c.require(row["source_kind"] in ("internal_label", "branch_comment", "phyloxml_confidence"), "support_source_kind_invalid")
        c.require(row["method"] in c.SUPPORT_METHODS and row["scale"] in c.SUPPORT_SCALES, "support_semantics_invalid")
        c.text(row["command_id"], nullable=True)
        c.text(row["bootstrap_population_id"], nullable=True)
        c.evidence(row["evidence"])
        c.text(row["native_observation_id"])
        c.require(row["native_observation_id"] in native, "support_native_observation_missing")
        c.require(row["native_observation_id"] not in seen, "duplicate_support_observation")
        seen.add(row["native_observation_id"])
        observation = native[row["native_observation_id"]]
        c.require(observation["field"] == "branch_support_native" and
                  observation["subject_id"] == tree["tree_id"] + "/node/" + str(row["node_index"]),
                  "support_native_relationship_conflict")
        expected_unit = {"percent": "percent", "fraction": "fraction", "statistic": "native_statistic",
                         "native_unknown": "native_unknown"}[row["scale"]]
        c.require(observation["unit"] == expected_unit, "support_native_scale_conflict")
        c.require(observation["method"] in ("native_unknown", row["method"]), "support_native_method_conflict")
        if observation["value"] is not None and row["scale"] in ("percent", "fraction"):
            upper = 100 if row["scale"] == "percent" else 1
            c.require(0 <= observation["value"] <= upper, "support_value_outside_scale")
        by_node[row["node_index"]].append((row, observation))
    return native, by_node


def _rescaled_support(rows, pid, node_index):
    scope = c.scope(pid, "node", str(node_index))
    if not rows:
        return "native_unknown", "native_unknown", c.quantity(None, population=pid, unit="fraction",
            method="native_unknown", state="not_measured")
    methods, scales = {r[0]["method"] for r in rows}, {r[0]["scale"] for r in rows}
    values = {(r[1]["state"], r[1]["value"]) for r in rows}
    method = next(iter(methods)) if len(methods) == 1 else "native_unknown"
    scale = next(iter(scales)) if len(scales) == 1 else "native_unknown"
    conflict = len(methods) != 1 or len(scales) != 1 or len(values) != 1
    requirements = []
    state, value = "missing", None
    if conflict:
        requirements.append(scope + "/support_observations_conflict")
        state = "incompatible"
    else:
        state, value = next(iter(values))
        if method == "native_unknown":
            requirements.append(scope + "/support_method_unresolved")
        if scale == "native_unknown":
            requirements.append(scope + "/support_scale_unresolved")
        if requirements or scale == "statistic":
            value = None
            state = "missing" if requirements else "not_measured"
    rescaled = value / 100 if value is not None and scale == "percent" else value
    # Native requirements remain in their observation table. A failed native
    # support value is not a fabricated conflict or an acquisition decision.
    return method, scale, c.quantity(rescaled, population=pid, unit="fraction", method=method,
        numerator=value, denominator=100 if scale == "percent" else 1 if scale == "fraction" else None,
        state=state if state != "available" else "missing", requirements=requirements,
        evidence_rows=[e for _, obs in rows for e in obs["evidence"]])


def tree_components(tree: dict, *, leaf_population: dict, support_observations: tuple[dict, ...],
                    native_measurements: tuple[dict, ...], branch_unit: str,
                    pairs: tuple[tuple[int, int], ...]) -> dict:
    """Whole-tree topology, signed lengths, explicit support and exact paths."""
    tree = validate_tree_record(tree)
    c.shape(leaf_population, {"population_id", "tree_id", "node_indices", "completeness", "evidence"},
            "leaf_population_shape_invalid")
    c.text(leaf_population["population_id"])
    c.unique_indices(leaf_population["node_indices"])
    c.evidence(leaf_population["evidence"])
    c.require(leaf_population["tree_id"] == tree["tree_id"], "leaf_population_identity_conflict")
    c.require(leaf_population["completeness"] == "complete" and set(leaf_population["node_indices"]) == _tips(tree),
              "whole_tree_leaf_population_required")
    c.require(branch_unit in c.BRANCH_UNITS, "branch_unit_invalid")
    requested_pairs = _pairs(pairs, set(range(len(tree["nodes"]))))
    native, support = _support_rows(tree, support_observations, native_measurements)
    pid, tid = leaf_population["population_id"], tree["tree_id"]
    nodes = tree["nodes"]
    edges = [node["node_index"] for node in nodes if node["parent_index"] is not None]
    length_observations = defaultdict(list)
    for observation in native.values():
        prefix = tid + "/node/"
        if observation["field"] != "branch_length" or observation["subject_id"] is None or not observation["subject_id"].startswith(prefix):
            continue
        suffix = observation["subject_id"][len(prefix):]
        c.require(suffix.isdigit() and str(int(suffix)) == suffix and int(suffix) < len(nodes), "length_native_node_invalid")
        index = int(suffix)
        c.require(observation["value"] == nodes[index]["branch_length"], "length_native_value_conflict")
        if observation["unit"] != "native_unknown" and branch_unit != "native_unknown":
            c.require(observation["unit"] == branch_unit, "branch_unit_conflict")
        length_observations[index].append(observation)
    edge_units = {}
    for i in edges:
        known_units = {r["unit"] for r in length_observations[i] if r["unit"] != "native_unknown"}
        c.require(len(known_units) <= 1, "branch_unit_conflict")
        edge_units[i] = next(iter(known_units)) if known_units else "native_unknown"
    known_units = set(edge_units.values()) - {"native_unknown"}
    c.require(len(known_units) <= 1, "branch_unit_conflict")
    aggregate_unit = next(iter(known_units)) if known_units and "native_unknown" not in edge_units.values() else "native_unknown"
    split_edges, all_tips = _tree_splits(tree)
    splits = [{"split_id": _split_id(tid, side), "tree_id": tid, "side_node_indices": list(side),
               "complement_node_indices": sorted(all_tips - set(side)), "edge_node_indices": edge_indices}
              for side, edge_indices in sorted(split_edges.items())]
    edge_split = {i: row["split_id"] for row in splits for i in row["edge_node_indices"]}
    branches = []
    for i in edges:
        method, scale, rescaled = _rescaled_support(support[i], pid, i)
        length = nodes[i]["branch_length"]
        branches.append({"node_index": i, "split_id": edge_split.get(i),
            "length": _count(length, pid, edge_units[i], "native_branch_length", origin="native_fitted",
                 requirements=[c.scope(pid, "node", str(i)) + "/branch_lengths_required"] if length is None else [],
                 evidence_rows=[e for r in length_observations[i] for e in r["evidence"]]),
            "native_support_observation_ids": [r[0]["native_observation_id"] for r in support[i]],
            "support_method": method, "support_scale": scale, "support_rescaled": rescaled})
    lengths = [nodes[i]["branch_length"] for i in edges]
    missing = sum(x is None for x in lengths)
    known_sum = _finite_sum(x for x in lengths if x is not None)
    partial_units = {edge_units[i] for i in edges if nodes[i]["branch_length"] is not None}
    partial_unit = next(iter(partial_units)) if len(partial_units) == 1 else "native_unknown"
    # Degree-two root suppression changes no remaining node's degree.
    unrooted_polytomies = sum(len(node["child_indices"]) + (node["parent_index"] is not None) > 3 for node in nodes)
    distances = []
    for a, b in requested_pairs:
        path = _path_edges(tree, a, b)
        values = [nodes[i]["branch_length"] for i in path]
        missing_path = any(x is None for x in values)
        units = {edge_units[i] for i in path}
        unit = next(iter(units)) if len(units) == 1 else "native_unknown"
        distances.append({"node_a": a, "node_b": b, "value": _count(
            None if missing_path else _finite_sum(values), pid, unit, "patristic_distance",
            requirements=[c.scope(pid, "node", str(i)) + "/branch_lengths_required" for i in path if nodes[i]["branch_length"] is None])})
    return {"population_id": pid, "tree_id": tid,
        "tip_count": _count(len(all_tips), pid, "tips", "tree_tip_count"),
        "internal_node_count": _count(len(nodes) - len(all_tips), pid, "nodes", "internal_node_count"),
        "rooted_representation_polytomies": _count(sum(len(n["child_indices"]) > 2 for n in nodes), pid, "nodes", "rooted_child_degree_gt2"),
        "unrooted_degree_polytomies": _count(unrooted_polytomies, pid, "nodes", "unrooted_degree_gt3"),
        "branch_length_sum": _count(None if missing else known_sum, pid, aggregate_unit, "branch_length_sum",
             requirements=[c.scope(pid) + "/branch_lengths_required"] if missing else []),
        "known_branch_length_sum": _count(known_sum, pid, partial_unit, "known_branch_length_sum"),
        "missing_branch_length_count": _count(missing, pid, "edges", "missing_branch_length_count"),
        "splits": splits, "branches": branches, "distances": distances}


def bootstrap_split_frequencies(reference: dict, *, replicates: tuple[dict, ...], replicate_population: dict,
                                tip_join: dict, method: str) -> dict:
    """Use only explicitly mapped compatible replicates as the denominator."""
    reference = validate_tree_record(reference)
    c.sequence(replicates)
    replicates = [validate_tree_record(tree) for tree in replicates]
    c.require(method in ("rapid_bootstrap", "rell_bootstrap"), "bootstrap_method_invalid")
    c.shape(replicate_population, {"population_id", "tree_ids", "expected_replicates", "completeness", "expected_count_evidence"},
            "bootstrap_population_shape_invalid")
    pid = replicate_population["population_id"]
    c.text(pid)
    c.strings(replicate_population["tree_ids"])
    c.integer(replicate_population["expected_replicates"], nullable=True)
    c.require(replicate_population["completeness"] in c.COMPLETENESS, "population_completeness_invalid")
    c.evidence(replicate_population["expected_count_evidence"])
    ids = [tree["tree_id"] for tree in replicates]
    c.require(len(ids) == len(set(ids)), "duplicate_replicate_tree")
    c.require(set(ids) == set(replicate_population["tree_ids"]), "bootstrap_population_identity_conflict")
    expected = replicate_population["expected_replicates"]
    c.require(expected is None or expected >= len(ids), "bootstrap_expected_count_conflict")
    c.shape(tip_join, {"reference_tree_id", "mappings"}, "replicate_join_shape_invalid")
    c.require(tip_join["reference_tree_id"] == reference["tree_id"], "replicate_reference_conflict")
    c.sequence(tip_join["mappings"], stored=True)
    joins = {}
    reference_tips = _tips(reference)
    for mapping in tip_join["mappings"]:
        c.shape(mapping, {"replicate_tree_id", "pairs"}, "replicate_mapping_shape_invalid")
        c.text(mapping["replicate_tree_id"])
        tid = mapping["replicate_tree_id"]
        c.require(tid in ids, "replicate_mapping_absent_tree")
        c.require(tid not in joins, "duplicate_replicate_mapping")
        c.sequence(mapping["pairs"], stored=True)
        pairs = []
        for pair in mapping["pairs"]:
            c.shape(pair, {"reference_node_index", "replicate_node_index"}, "replicate_pair_shape_invalid")
            c.integer(pair["reference_node_index"])
            c.integer(pair["replicate_node_index"])
            c.require(pair["reference_node_index"] in reference_tips, "replicate_reference_tip_invalid")
            pairs.append((pair["reference_node_index"], pair["replicate_node_index"]))
        c.require(len({p[0] for p in pairs}) == len(pairs) and len({p[1] for p in pairs}) == len(pairs),
                  "replicate_mapping_not_injective")
        joins[tid] = pairs
    reference_splits, _ = _tree_splits(reference)
    matched, usable, excluded = Counter(), 0, []
    for tree in replicates:
        tid, terminal = tree["tree_id"], _tips(tree)
        if tid not in joins:
            excluded.append({"tree_id": tid, "reason_code": "replicate_tip_mapping_missing"})
            continue
        pairs = joins[tid]
        c.require(all(p[1] in terminal for p in pairs), "replicate_terminal_identity_invalid")
        if {p[0] for p in pairs} != reference_tips or {p[1] for p in pairs} != terminal:
            excluded.append({"tree_id": tid, "reason_code": "replicate_tip_population_incompatible"})
            continue
        splits, _ = _tree_splits(tree, tip_map={rep: ref for ref, rep in pairs})
        usable += 1
        matched.update(reference_splits.keys() & splits.keys())
    conditional = bool(excluded) or replicate_population["completeness"] != "complete" or expected != len(replicates)
    frequency_method = ("conditional_" if conditional else "") + method + "_frequency"
    frequency_reqs = [c.scope(pid) + "/bootstrap_replicates_not_retained"] if usable == 0 and expected != 0 else []
    return {"reference_tree_id": reference["tree_id"], "population_id": pid,
        "supplied_replicates": _count(len(replicates), pid, "trees", "supplied_replicate_count"),
        "expected_replicates": _count(expected, pid, "trees", "supplied_expected_replicate_count",
            origin="native_observed", evidence_rows=replicate_population["expected_count_evidence"],
            requirements=[c.scope(pid) + "/bootstrap_expected_count_required"] if expected is None else []),
        "usable_replicates": _count(usable, pid, "trees", "compatible_mapped_replicate_count"),
        "excluded_replicates": excluded,
        "rows": [{"split_id": _split_id(reference["tree_id"], side),
                  "matches": _count(matched[side], pid, "trees", "bootstrap_split_match_count"),
                  "denominator": _count(usable, pid, "trees", "compatible_mapped_replicate_count"),
                  "frequency": c.ratio(matched[side], usable, population=pid, method=frequency_method,
                                       requirements=frequency_reqs)} for side in sorted(reference_splits)]}


def function_composition(*, population: dict, assignments: tuple[dict, ...],
                         equivalences: tuple[dict, ...] = ()) -> dict:
    """Count each explicitly associated member once per supplied function.

    This is observed metadata composition. A member may count in several
    functions; no unit weight is divided among those labels.
    """
    keys = c.composition_population(population)
    members = dict(zip(keys, population["member_subjects"]))
    c.sequence(assignments)
    c.sequence(equivalences)
    canonical, equivalence_ids = {}, set()
    for row in equivalences:
        c.shape(row, {"equivalence_id", "function_keys", "canonical_function_key", "evidence"}, "function_equivalence_shape_invalid")
        c.text(row["equivalence_id"])
        c.require(row["equivalence_id"] not in equivalence_ids, "duplicate_function_equivalence")
        equivalence_ids.add(row["equivalence_id"])
        c.strings(row["function_keys"])
        c.require(bool(row["function_keys"]), "empty_function_equivalence")
        c.text(row["canonical_function_key"])
        c.evidence(row["evidence"])
        for key in row["function_keys"] + [row["canonical_function_key"]]:
            c.require(key not in canonical or canonical[key] == row["canonical_function_key"], "function_equivalence_conflict")
            canonical[key] = row["canonical_function_key"]
    grouped, assigned, assignment_ids = defaultdict(set), set(), set()
    for row in assignments:
        c.shape(row, {"assignment_id", "subject", "function_key", "function_label", "source_record_id", "evidence"},
                "function_assignment_shape_invalid")
        key = c.subject(row["subject"])
        c.require(key in members, "function_assignment_subject_conflict")
        for field in ("assignment_id", "function_key", "source_record_id"):
            c.text(row[field])
        c.text(row["function_label"], empty=True)
        c.evidence(row["evidence"])
        c.require(row["assignment_id"] not in assignment_ids, "duplicate_function_assignment")
        assignment_ids.add(row["assignment_id"])
        grouped[canonical.get(row["function_key"], row["function_key"])].add(key)
        assigned.add(key)
    pid, complete = population["population_id"], population["membership_completeness"] == "complete"
    reqs = [] if complete else [c.scope(pid) + "/composition_population_required"]
    state = c.unavailable_state(population["membership_completeness"])
    def count(number, method):
        return _count(number if complete else None, pid, "members", method, state=state, requirements=reqs)
    return {"population_id": pid, "unit": population["unit"],
        "total_members": count(len(keys), "composition_member_count"),
        "members_with_recorded_assignment": count(len(assigned), "members_with_recorded_function_assignment"),
        "members_without_recorded_assignment": count(len(keys) - len(assigned), "members_without_recorded_function_assignment"),
        "rows": [{"function_key": function, "member_subjects": [deepcopy(members[k]) for k in keys if k in subjects],
            "assigned_members": count(len(subjects), "members_assigned_function"),
            "fraction_all": c.ratio(len(subjects) if complete else None, len(keys) if complete else None,
                population=pid, method="function_fraction_all_members", state=state, requirements=reqs),
            "fraction_recorded": c.ratio(len(subjects) if complete else None, len(assigned) if complete else None,
                population=pid, method="function_fraction_recorded_members", state=state, requirements=reqs)}
                 for function, subjects in sorted(grouped.items())]}


def taxon_components(*, population: dict, rank: str, assignments: tuple[dict, ...]) -> dict:
    """Taxon representation at one exact supplied rank, among known members."""
    keys = c.taxon_population(population)
    members = dict(zip(keys, population["member_subjects"]))
    c.text(rank)
    c.sequence(assignments)
    assigned = {}
    for row in assignments:
        c.shape(row, {"subject", "taxon_id", "rank", "lineage", "source_record_id", "evidence"}, "taxon_assignment_shape_invalid")
        key = c.subject(row["subject"])
        c.require(key in members, "taxon_assignment_subject_conflict")
        c.text(row["taxon_id"])
        c.text(row["rank"], nullable=True)
        c.text(row["source_record_id"])
        c.evidence(row["evidence"])
        c.sequence(row["lineage"], stored=True)
        rank_values = {}
        for ancestor in [{"taxon_id": row["taxon_id"], "rank": row["rank"]}] + row["lineage"]:
            c.shape(ancestor, {"taxon_id", "rank"}, "taxon_lineage_shape_invalid")
            c.text(ancestor["taxon_id"])
            c.text(ancestor["rank"], nullable=True)
            if ancestor["rank"] is not None:
                c.require(ancestor["rank"] not in rank_values or rank_values[ancestor["rank"]] == ancestor["taxon_id"],
                          "taxon_rank_conflict")
                rank_values[ancestor["rank"]] = ancestor["taxon_id"]
        if rank in rank_values:
            c.require(key not in assigned or assigned[key] == rank_values[rank], "taxon_assignment_conflict")
            assigned[key] = rank_values[rank]
    grouped = defaultdict(set)
    for key, taxon in assigned.items():
        grouped[taxon].add(key)
    pid, complete = population["population_id"], population["membership_completeness"] == "complete"
    reqs = [] if complete else [c.scope(pid) + "/composition_population_required"]
    state = c.unavailable_state(population["membership_completeness"])
    known = len(assigned)
    same_pairs = sum(len(v) * (len(v) - 1) // 2 for v in grouped.values())
    known_pairs = known * (known - 1) // 2
    def count(value, unit, method):
        return _count(value if complete else None, pid, unit, method, state=state, requirements=reqs)
    # A population genuinely containing fewer than two members cannot gain a
    # pair by acquiring taxon labels. Unknown labels in a larger population can.
    pair_reqs = reqs or ([c.scope(pid, "rank", rank) + "/taxon_associations_required"]
                        if known_pairs == 0 and len(keys) >= 2 and len(keys) > known else [])
    return {"population_id": pid, "rank": rank,
        "known_members": count(known, "members", "members_with_recorded_taxon_at_rank"),
        "unknown_members": count(len(keys) - known, "members", "members_without_recorded_taxon_at_rank"),
        "distinct_known_taxa": count(len(grouped), "taxa", "distinct_recorded_taxa_at_rank"),
        "same_taxon_pairs": count(same_pairs, "pairs", "same_taxon_unordered_pairs"),
        "known_taxon_pairs": count(known_pairs, "pairs", "known_taxon_unordered_pairs"),
        "same_taxon_pair_fraction": c.ratio(same_pairs if complete else None, known_pairs if complete else None,
            population=pid, method="same_taxon_pair_fraction", state=state, requirements=pair_reqs),
        "rows": [{"taxon_id": taxon, "member_subjects": [deepcopy(members[k]) for k in keys if k in subjects],
                  "member_count": count(len(subjects), "members", "members_with_recorded_taxon")}
                 for taxon, subjects in sorted(grouped.items())]}


def compare_unrooted_relationships(gene_tree: dict, *, comparison_id: str, organismal_tree: dict,
                                   injective_tip_join: tuple[dict, ...]) -> dict:
    """Compare shared-tip unrooted split sets; no transfer diagnosis is made."""
    gene_tree = validate_tree_record(gene_tree)
    organismal_tree = validate_tree_record(organismal_tree)
    c.text(comparison_id)
    c.sequence(injective_tip_join)
    gene_tips, organismal_tips = _tips(gene_tree), _tips(organismal_tree)
    gene_to_org, subjects = {}, set()
    for pair in injective_tip_join:
        c.shape(pair, {"gene_tree_id", "gene_node_index", "organismal_tree_id", "organismal_node_index", "subject", "evidence"},
                "comparison_pair_shape_invalid")
        c.integer(pair["gene_node_index"])
        c.integer(pair["organismal_node_index"])
        c.require(pair["gene_tree_id"] == gene_tree["tree_id"] and pair["organismal_tree_id"] == organismal_tree["tree_id"],
                  "comparison_tree_identity_conflict")
        a, b = pair["gene_node_index"], pair["organismal_node_index"]
        c.require(a in gene_tips and b in organismal_tips, "comparison_terminal_identity_invalid")
        c.require(a not in gene_to_org and b not in gene_to_org.values(), "comparison_join_not_injective")
        subject = c.subject(pair["subject"])
        c.require(subject not in subjects, "comparison_subject_not_injective")
        c.evidence(pair["evidence"])
        gene_to_org[a] = b
        subjects.add(subject)
    gene_splits, _ = _tree_splits(gene_tree, selected=gene_to_org)
    org_native_splits, _ = _tree_splits(organismal_tree, selected=gene_to_org.values())
    org_mapped_splits, _ = _tree_splits(organismal_tree, selected=gene_to_org.values(),
                                     tip_map={b: a for a, b in gene_to_org.items()})
    # Native split IDs use that tree's own restricted terminal indices, while
    # equality uses the explicit gene-coordinate correspondence.
    mapped_to_native = {mapped: _canonical_side({gene_to_org[i] for i in mapped}, set(gene_to_org.values()))
                        for mapped in org_mapped_splits}
    shared = gene_splits.keys() & org_mapped_splits.keys()
    rf = len(gene_splits.keys() ^ org_mapped_splits.keys())
    restricted_gene = [{"split_id": _split_id(comparison_id + "/gene", side), "tree_id": gene_tree["tree_id"],
                        "side_node_indices": list(side), "complement_node_indices": sorted(gene_to_org.keys() - set(side)),
                        "edge_node_indices": edges} for side, edges in sorted(gene_splits.items())]
    restricted_organismal = [{"split_id": _split_id(comparison_id + "/organismal", side), "tree_id": organismal_tree["tree_id"],
                        "side_node_indices": list(side), "complement_node_indices": sorted(set(gene_to_org.values()) - set(side)),
                        "edge_node_indices": edges} for side, edges in sorted(org_native_splits.items())]
    return {"comparison_id": comparison_id, "matched_tip_pairs": deepcopy(list(injective_tip_join)),
        "omitted_gene_tips": [{"tree_id": gene_tree["tree_id"], "node_index": i} for i in sorted(gene_tips - gene_to_org.keys())],
        "omitted_organismal_tips": [{"tree_id": organismal_tree["tree_id"], "node_index": i}
                                   for i in sorted(organismal_tips - set(gene_to_org.values()))],
        "matched_tips": _count(len(gene_to_org), comparison_id, "tips", "explicit_matched_tip_count"),
        "gene_splits": _count(len(gene_splits), comparison_id, "splits", "restricted_gene_nontrivial_unrooted_splits"),
        "organismal_splits": _count(len(org_mapped_splits), comparison_id, "splits", "restricted_organismal_nontrivial_unrooted_splits"),
        "shared_splits": _count(len(shared), comparison_id, "splits", "shared_nontrivial_unrooted_splits"),
        "rf": _count(rf, comparison_id, "splits", "unrooted_robinson_foulds"),
        "rf_fraction": c.ratio(rf, len(gene_splits) + len(org_mapped_splits), population=comparison_id,
                               method="unrooted_robinson_foulds_fraction"),
        "restricted_gene_splits": restricted_gene,
        "restricted_organismal_splits": restricted_organismal,
        "shared_split_pairs": [{"gene_split_id": _split_id(comparison_id + "/gene", side),
                                "organismal_split_id": _split_id(comparison_id + "/organismal", mapped_to_native[side])}
                               for side in sorted(shared)]}


def calculation_requirements(component: dict) -> list[dict]:
    """Resolve finite missing-input IDs on an already-calculated component.

    No numbers are recalculated. Original coverage's explicit requirements keep
    their supplied source references. Unknown reasons and ID conflicts fail.
    """
    c.require(type(component) is dict, "component_shape_invalid")
    emitted, explicit = set(), {}
    stack = [component]
    while stack:
        node = stack.pop()
        if type(node) is dict:
            if "requirement_ids" in node:
                c.strings(node["requirement_ids"])
                emitted.update(node["requirement_ids"])
            if "missing_requirements" in node:
                c.sequence(node["missing_requirements"], stored=True)
                for req in node["missing_requirements"]:
                    c.shape(req, {"requirement_id", "kind", "role", "source_refs", "reason_code"}, "requirement_shape_invalid")
                    c.text(req["requirement_id"])
                    c.strings(req["source_refs"])
                    c.require(req["reason_code"] in c.REQUIREMENT_REASONS, "requirement_reason_unknown")
                    expected_kind, expected_role = c.REQUIREMENT_REASONS[req["reason_code"]]
                    c.require(req["kind"] == expected_kind and req["role"] == expected_role and
                              req["requirement_id"].endswith("/" + req["reason_code"]), "requirement_meaning_conflict")
                    rid = req["requirement_id"]
                    c.require(rid not in explicit or explicit[rid] == req, "requirement_meaning_conflict")
                    explicit[rid] = req
            stack.extend(node.values())
        elif type(node) in (list, tuple):
            stack.extend(node)
    result = {}
    for rid in emitted | explicit.keys():
        prefix, separator, reason = rid.rpartition("/")
        c.require(bool(separator) and prefix.startswith("phylogeny/") and len(prefix) > len("phylogeny/") and
                  reason in c.REQUIREMENT_REASONS, "requirement_reason_unknown")
        result[rid] = deepcopy(explicit[rid]) if rid in explicit else c.requirement(prefix, reason)
    return [result[rid] for rid in sorted(result)]


__all__ = ["alignment_components", "ungapped_coordinate_map", "original_member_coverage", "tree_components",
           "bootstrap_split_frequencies", "function_composition", "taxon_components", "compare_unrooted_relationships",
           "calculation_requirements"]


def literal_site_conservation(alignment: dict, *, population: dict,
        convention: str = c.LITERAL_CONSERVATION_CONVENTION) -> dict:
    """Describe literal modal symbols using shared counts and fraction arithmetic.

    Every selected row contributes, including gaps, ambiguity and case-distinct
    symbols. Equal modal counts choose the first retained alignment source row,
    independent of requested row ordering or labels. The strict 0.8 comparison
    precedes two-decimal display rounding; neither is annotation confidence.
    """
    c.require(convention == c.LITERAL_CONSERVATION_CONVENTION,
              "literal_conservation_convention_invalid")
    alignment = validate_alignment_document(alignment)
    common = alignment_components(alignment, population=population,
        alphabet="unknown", case_policy="literal", pairs=())
    pid = population["population_id"]
    ordered = sorted(population["row_indices"])
    denominator = common["member_count"]["value"]
    complete = common["member_count"]["state"] == "available"
    missing_state = "not_measured" if complete else common["member_count"]["state"]
    requirements = common["member_count"]["requirement_ids"]
    sites = []
    for site in common["sites"]:
        counts = {row["symbol"]: row["count"] for row in site["symbol_counts"]}
        modal = max(counts.values()) if complete and denominator else None
        winner = first = None
        if modal is not None:
            first = next(index for index in ordered
                if counts[alignment["rows"][index]["sequence"][site["column_0based"]]] == modal)
            winner = alignment["rows"][first]["sequence"][site["column_0based"]]
        fraction = c.ratio(modal, denominator, population=pid,
            method="literal_modal_all_rows_fraction", state=missing_state, requirements=requirements)
        raw = fraction["value"]
        sites.append({"column_0based": site["column_0based"],
            "symbol_counts": deepcopy(site["symbol_counts"]), "modal_symbol": winner,
            "modal_first_source_row_index": first,
            "modal_count": c.quantity(modal, population=pid, unit="characters",
                method="literal_modal_symbol_count", state=missing_state, requirements=requirements),
            "majority_fraction": fraction, "strict_gt_0_8": None if raw is None else raw > 0.8,
            "displayed_2dp_fraction": c.quantity(None if raw is None else float(format(raw, ".2f")),
                population=pid, unit="fraction", method="literal_modal_fraction_fixed_2",
                numerator=modal, denominator=denominator, state=missing_state, requirements=requirements)})
    return c.validate_literal_site_conservation_components({
        "version": c.LITERAL_CONSERVATION_VERSION, "convention": convention,
        "alignment_id": alignment["alignment_id"], "population_id": pid,
        "ordered_source_row_indices": ordered, "member_count": deepcopy(common["member_count"]),
        "site_count": deepcopy(common["site_count"]),
        "threshold": {"comparison": "strict_greater_than", "value": 0.8, "basis": "unrounded_binary64_ratio"},
        "display": {"decimal_places": 2, "rounding": "binary64_fixed_2_ties_to_even"}, "sites": sites},
        alignment=alignment, population=population)


__all__.append("literal_site_conservation")
