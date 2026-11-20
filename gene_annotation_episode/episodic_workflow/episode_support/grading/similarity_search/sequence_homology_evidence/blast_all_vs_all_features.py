"""Controlled features of an all-vs-all result, read by code from the clustered graph. Pure; no tool, no model.

Two readings of the same graph:

* ``target_context_features``: the family context of one target inside the set: its cluster, how many independent
  members the cluster has, how its neighbours resemble it, and how far the annotated members agree.
* ``hit_list_coherence_features``: whether a chosen subset of the set (for example the top hits of a database
  search) forms one family or several.

Every value is a number, a boolean or an annotation identifier the caller supplied (a controlled name from a
looked-up list; this module never reads a name for meaning). A feature that cannot be computed is ABSENT, never
defaulted. Near-duplicate members vote once: counts and agreement are over redundancy groups, not sequences. These
features describe the graph; they assign no support and no credit, and the sheet's own scorer decides what they mean.
"""
from __future__ import annotations

from collections import Counter
from statistics import median


def _cluster_of(name, clusters):
    return next((c for c in clusters if name in c["members"]), None)


def _vote(names, groups_by_member, annotations):
    """One annotation per redundancy group (the commonest among its annotated members; ties by smaller identifier),
    for the groups that have at least one annotated member."""
    votes = {}
    for name in names:
        label = annotations.get(name)
        if label is not None:
            votes.setdefault(groups_by_member[name], []).append(label)
    return {group: sorted(Counter(labels).items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for group, labels in votes.items()}


def target_context_features(target, clusters, groups, undirected, annotations, completeness):
    """The controlled features of ``target``'s family context. ``annotations`` maps a member identifier to an
    annotation identifier or ``None``. ``completeness`` is the record of ``blast_all_vs_all_graph.completeness``."""
    features = {"graph_status": completeness["status"]}
    if completeness["expected_queries"]:
        features["searched_fraction"] = round(completeness["searched_queries"] / completeness["expected_queries"], 6)
    cluster = _cluster_of(target, clusters)
    if cluster is None:
        features["target_in_set"] = False
        return features
    groups_by_member = {m: g["group"] for g in groups for m in g["members"]}
    others = [m for m in cluster["members"] if m != target]
    neighbours = [e for e in undirected if target in (e["a"], e["b"])]
    features.update({
        "target_in_set": True, "cluster_count": len(clusters),
        "largest_cluster_size": max(c["size"] for c in clusters),
        "cluster_size": cluster["size"], "singleton": cluster["size"] == 1,
        "independent_member_count": len({groups_by_member[m] for m in cluster["members"]}),
        "neighbor_count": len(neighbours)})
    if cluster["density"] is not None:
        features["cluster_density"] = cluster["density"]
    if neighbours:
        identities = [e["identity"] for e in neighbours]
        features.update({"neighbor_identity_min": min(identities), "neighbor_identity_median": median(identities),
                         "neighbor_identity_max": max(identities),
                         "neighbor_coverage_min": min(e["coverage"] for e in neighbours)})
    annotated = [m for m in others if annotations.get(m) is not None]
    features["annotated_member_count"] = len(annotated)
    voted = _vote(others, groups_by_member, annotations)
    features["independent_annotated_count"] = len(voted)
    if voted:
        tally = sorted(Counter(voted.values()).items(), key=lambda kv: (-kv[1], kv[0]))
        features["top_annotation"] = tally[0][0]
        features["annotation_agreement"] = round(tally[0][1] / len(voted), 6)
        features["distinct_annotation_count"] = len(tally)
    return features


def hit_list_coherence_features(subset, clusters, groups, reference=None):
    """Whether the members of ``subset`` that are in the set form one family. ``reference`` (optional) is a member
    whose place among them is asked for, for example the database search's query."""
    present = sorted(name for name in set(subset) if _cluster_of(name, clusters) is not None)
    features = {"hit_count": len(present)}
    if not present:
        return features
    groups_by_member = {m: g["group"] for g in groups for m in g["members"]}
    per_cluster = Counter(_cluster_of(name, clusters)["cluster"] for name in present)
    largest, count = sorted(per_cluster.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    features.update({"cluster_count_among_hits": len(per_cluster), "largest_cluster_hit_count": count,
                     "largest_cluster_fraction": round(count / len(present), 6),
                     "independent_hit_count": len({groups_by_member[name] for name in present})})
    if reference is not None:
        found = _cluster_of(reference, clusters)
        features["reference_in_set"] = found is not None
        if found is not None:
            features["reference_in_largest_cluster"] = found["cluster"] == largest
    return features


__all__ = ["hit_list_coherence_features", "target_context_features"]
