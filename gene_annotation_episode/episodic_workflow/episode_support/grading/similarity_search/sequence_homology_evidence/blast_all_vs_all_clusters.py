"""Clusters and independent members from an all-vs-all similarity graph. Deterministic, pure, no tool and no model.

Two separate questions, two functions:

* ``cluster_components``: which sequences belong to one family. Directed edges that pass the recorded thresholds
  become undirected edges; the clusters are the connected components. Single linkage can chain unrelated families
  through a multi-domain sequence, so the coverage rule requires coverage of the sequences (``both`` by default) and
  every cluster reports its ``density`` (present edges over possible edges) so a chained cluster shows as sparse.
* ``redundancy_groups``: which sequences are near-duplicates. Strict thresholds, greedy from the longest sequence
  down. Near-duplicates are one vote, not several; ``independent_counts`` counts groups, not sequences.

The thresholds and rules are controlled values recorded with the result; nothing here is learned from the data.
"""
from __future__ import annotations

COVERAGE_RULES = ("both", "shorter")
EDGE_RULES = ("reciprocal", "either")


def thresholds(*, min_identity, min_coverage, max_evalue, coverage_rule="both", edge_rule="reciprocal"):
    """The recorded thresholds, validated."""
    for name, value in (("min_identity", min_identity), ("min_coverage", min_coverage)):
        if type(value) not in (int, float) or isinstance(value, bool) or not 0 <= value <= 1:
            raise ValueError("blast_all_vs_all_threshold_range:" + name)
    if type(max_evalue) not in (int, float) or isinstance(max_evalue, bool) or not 0 < max_evalue <= 1000:
        raise ValueError("blast_all_vs_all_threshold_range:max_evalue")
    if coverage_rule not in COVERAGE_RULES or edge_rule not in EDGE_RULES:
        raise ValueError("blast_all_vs_all_rule_unknown")
    return {"min_identity": min_identity, "min_coverage": min_coverage, "max_evalue": max_evalue,
            "coverage_rule": coverage_rule, "edge_rule": edge_rule}


def _passes(edge, limit):
    if edge["identity"] < limit["min_identity"] or edge["evalue"] > limit["max_evalue"]:
        return False
    if limit["coverage_rule"] == "both":
        return min(edge["query_coverage"], edge["subject_coverage"]) >= limit["min_coverage"]
    shorter = edge["query_coverage"] if edge["query_length"] <= edge["subject_length"] else edge["subject_coverage"]
    return shorter >= limit["min_coverage"]


def undirected_edges(edges, limit):
    """Undirected edges ``{'a', 'b', 'identity', 'coverage', 'evalue', 'bitscore'}`` (``a < b``). Under
    ``reciprocal`` both directions must be present and pass; under ``either`` one passing direction is enough. The
    attributes are the conservative ones over the passing directions: lowest identity, lowest coverage, highest
    E-value, lowest bit score. Self edges are skipped."""
    pairs = {}
    for edge in edges:
        if edge["self"]:
            continue
        a, b = sorted((edge["query"], edge["subject"]))
        pairs.setdefault((a, b), []).append(edge)
    result = []
    for (a, b), directed in sorted(pairs.items()):
        passing = [e for e in directed if _passes(e, limit)]
        if limit["edge_rule"] == "reciprocal":
            keep = len(passing) == 2 and {(e["query"], e["subject"]) for e in passing} == {(a, b), (b, a)}
        else:
            keep = bool(passing)
        if keep:
            result.append({"a": a, "b": b, "identity": min(e["identity"] for e in passing),
                           "coverage": min(min(e["query_coverage"], e["subject_coverage"]) for e in passing),
                           "evalue": max(e["evalue"] for e in passing),
                           "bitscore": min(e["bitscore"] for e in passing)})
    return result


def cluster_components(records, undirected):
    """The connected components over every record of the set (isolated records are singleton clusters). Each
    cluster is ``{'cluster', 'members', 'size', 'edge_count', 'density'}``; ``cluster`` is the smallest member
    identifier, so the name is stable. ``density`` is ``None`` for a singleton."""
    ids = sorted(item["id"] for item in records)
    parent = {name: name for name in ids}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name
    for edge in undirected:
        if edge["a"] not in parent or edge["b"] not in parent:
            raise ValueError("blast_all_vs_all_edge_names_a_record_outside_the_set")
        ra, rb = find(edge["a"]), find(edge["b"])
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    members = {}
    for name in ids:
        members.setdefault(find(name), []).append(name)
    counts = {}
    for edge in undirected:
        counts[find(edge["a"])] = counts.get(find(edge["a"]), 0) + 1
    clusters = []
    for root, names in sorted(members.items(), key=lambda item: item[1][0]):
        n = len(names)
        possible = n * (n - 1) // 2
        clusters.append({"cluster": names[0], "members": names, "size": n, "edge_count": counts.get(root, 0),
                         "density": None if n == 1 else round(counts.get(root, 0) / possible, 6)})
    return clusters


def redundancy_groups(records, strict_undirected):
    """Near-duplicate groups by a greedy pass: longest sequence first (ties by identifier), each unassigned sequence
    joins the first representative it shares a strict edge with. Returns ``{'group', 'representative',
    'members'}`` per group, ordered by representative identifier. Use strict thresholds (for example identity and
    coverage of 0.9) for ``strict_undirected``."""
    order = sorted(records, key=lambda item: (-item["length"], item["id"]))
    neighbours = {}
    for edge in strict_undirected:
        neighbours.setdefault(edge["a"], set()).add(edge["b"])
        neighbours.setdefault(edge["b"], set()).add(edge["a"])
    assigned, groups = {}, []
    for item in order:
        name = item["id"]
        if name in assigned:
            continue
        group = [name] + sorted(n for n in neighbours.get(name, ()) if n not in assigned)
        for member in group:
            assigned[member] = name
        groups.append({"group": name, "representative": name, "members": sorted(group)})
    return sorted(groups, key=lambda g: g["representative"])


def independent_counts(clusters, groups):
    """For each cluster, the number of near-duplicate groups it touches: its independent members."""
    group_of = {member: g["group"] for g in groups for member in g["members"]}
    return {c["cluster"]: len({group_of[m] for m in c["members"]}) for c in clusters}


__all__ = ["COVERAGE_RULES", "EDGE_RULES", "cluster_components", "independent_counts", "redundancy_groups",
           "thresholds", "undirected_edges"]
