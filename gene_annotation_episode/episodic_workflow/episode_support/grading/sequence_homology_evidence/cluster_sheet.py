"""The grading of a clustering of an all-vs-all set (``cluster_sheet_v1``), and the graph the clustering reads.

THE SCORE. The pairwise matrix holds BLAST BIT SCORES (the best alignment of each ordered pair, the existing
``blast_all_vs_all_graph.build_edges``). A bit score is the raw alignment score put on a common scale by the scoring
system's statistics (matrix, gap costs), so it does not depend on the size of the set the search ran in, as an E-value
does, and it does not depend on a scoring-system choice, as a raw score does. It still grows with sequence length, so
the clustering reads the BLAST SCORE RATIO instead: ``bits(a, b) / min(bits(a, a), bits(b, b))`` (``score_ratio_graph``),
in [0, 1], the bit score of the pair over the best score the shorter of the two could reach (its score against itself).
Of the two directions of a pair the larger bit score is taken (the directions differ only by BLAST's heuristics), and the
ratio is capped at 1.

THE CLUSTERING is MCL (the Markov Cluster algorithm, van Dongen), run by the program ``mcl`` on that weighted graph. MCL is the
established method for clustering a BLAST similarity graph (TribeMCL, OrthoMCL): it works on the weights themselves and, unlike
connected components or single linkage, a chain of weak links through a multi-domain sequence does not merge two families.

THE TUNING is a controlled choice of the all-vs-all child's model, per commission (the owner: a method that must be tuned for every
protein differently is not tuned by code, the agent does it): the inflation (``INFLATIONS``: lower is coarser, higher finer) and
the graph's CONTRAST (``CONTRASTS``): ``none`` (the ratios as they are), ``rescale`` (each weight rescaled to the set's own range,
``(ratio - lowest) / (1 - lowest)``) or ``percentile_<q>`` (only the edges whose ratio is at or above the q-th percentile of the
set's ratios are kept, with their ratios). A set of one family has ratios all high (on the C2 set 0.74 to 1.0), so MCL on the
plain ratios gives one cluster; the contrast lets the model separate what the set itself separates.

THE SHEET holds the clusters and where the target falls among each candidate's sequences. The test value of a candidate
group is the SHARE of the group's sequences that are in the target's cluster, in [0, 1]: the same scale as the other
tests of the head (a database search's value is the subscore of a hit's alignments, 0 to 1, about 0.8 to 1 for a typical
strong result), and about 1 for a strong typical result (every sequence of the candidate groups with the target) and 0
when none does. Nothing here reads a file or runs a program."""
SCHEMA = 'cluster_sheet_v1'
METHOD = 'mcl'
INFLATIONS = (1.4, 2.0, 4.0)
CONTRASTS = ('none', 'rescale', 'percentile_25', 'percentile_50', 'percentile_75', 'percentile_90')
TARGET_ID = 'target'
EDGE_WEIGHT = 'bit_score_ratio_to_the_smaller_self_score'


def score_ratio_graph(edges, ids):
    """The undirected weighted graph MCL reads: ``[(a, b, weight)]`` for each pair of distinct sequences with a hit in
    either direction, ``a`` before ``b`` in ``ids``, weight = the larger bit score of the pair over the smaller self score
    (at most 1). ``edges`` are ``blast_all_vs_all_graph.build_edges`` rows; a sequence with no self edge has no score to
    normalise by and raises (the caller checked completeness)."""
    selfs = {edge['query']: edge['bitscore'] for edge in edges if edge['self']}
    order = {name: index for index, name in enumerate(ids)}
    best = {}
    for edge in edges:
        if edge['self']:
            continue
        a, b = sorted((edge['query'], edge['subject']), key=order.__getitem__)
        best[a, b] = max(best.get((a, b), 0.0), edge['bitscore'])
    return [(a, b, min(1.0, bits / min(selfs[a], selfs[b]))) for (a, b), bits in sorted(
        best.items(), key=lambda item: (order[item[0][0]], order[item[0][1]]))]


def percentile(values, q):
    """The ``q``-th percentile of ``values`` (linear interpolation between the closest ranks)."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    below = int(position)
    above = min(below + 1, len(ordered) - 1)
    return ordered[below] + (ordered[above] - ordered[below]) * (position - below)


def contrast_undefined(graph, contrast):
    """Whether ``contrast`` has no meaning on ``graph``: ``rescale`` needs the set's lowest ratio below 1."""
    return contrast == 'rescale' and min(weight for _, _, weight in graph) >= 1.0


def contrast_graph(graph, contrast):
    """The graph MCL reads under ``contrast`` (``CONTRASTS``): ``none``, ``rescale`` or ``percentile_<q>``."""
    weights = [weight for _, _, weight in graph]
    if contrast == 'none':
        return list(graph)
    if contrast == 'rescale':
        lowest = min(weights)
        return [(a, b, (weight - lowest) / (1 - lowest)) for a, b, weight in graph]
    cut = percentile(weights, int(contrast.removeprefix('percentile_')))
    return [(a, b, weight) for a, b, weight in graph if weight >= cut]


def abc_text(graph):
    """The graph as MCL's ``--abc`` input: one ``a<TAB>b<TAB>weight`` line per edge."""
    return ''.join(a + '\t' + b + '\t' + format(weight, '.6f') + '\n' for a, b, weight in graph)


def parse_clusters(text):
    """The clusters of MCL's output: one line per cluster, its members separated by tabs."""
    return [line.split('\t') for line in text.splitlines() if line]


def with_singletons(clusters, ids):
    """``clusters`` and, for each of ``ids`` MCL did not place (it reads edges, so a sequence with none is absent from its
    output), a cluster of its own."""
    placed = {name for found in clusters for name in found}
    return [*clusters, *([name] for name in ids if name not in placed)]


def cluster_facts(clusters, members):
    """The controlled facts of a clustering the child's model sees: ``cluster_count``, ``sizes`` (the largest ten, descending),
    ``target_cluster_size`` and per candidate group ``size``, ``in_target_cluster`` and ``clusters_spanned`` (how many clusters
    its sequences fall across)."""
    cluster_of = {name: index for index, cluster in enumerate(clusters) for name in cluster}
    target = cluster_of[TARGET_ID]
    groups = {}
    for row in members:
        if row['candidate'] is not None:
            groups.setdefault(row['candidate'], []).append(row['id'])
    return {'cluster_count': len(clusters), 'sizes': sorted((len(cluster) for cluster in clusters), reverse=True)[:10],
            'target_cluster_size': len(clusters[target]),
            'groups': [{'candidate': candidate, 'size': len(names),
                        'in_target_cluster': sum(1 for name in names if cluster_of[name] == target),
                        'clusters_spanned': len({cluster_of[name] for name in names})} for candidate, names in groups.items()]}


def grade_clustering(clusters, members, *, method, parameters, commission):
    """The sheet of a clustering. ``clusters`` is the list of member-id lists; ``members`` the set's rows in file order:
    ``{'id', 'candidate' (None for the target), 'accession', 'md5'}`` (the target's id is ``TARGET_ID``). Every member must
    be in exactly one cluster and every clustered id must be a member. ``commission`` is the identity of the set (``search_ref``, sorted
    ``candidates``, ``per_candidate``): the head reads it to refuse a commission it already holds. Per candidate group (the members of one candidate):
    its ``size``, how many are ``in_target_cluster`` and the ``share`` (that over the size): the test's value."""
    ids = [row['id'] for row in members]
    placed = [name for cluster in clusters for name in cluster]
    if sorted(placed) != sorted(ids):
        raise ValueError('cluster_sheet_clusters_differ_from_the_members')
    target = next(index for index, cluster in enumerate(clusters) if TARGET_ID in cluster)
    inside = set(clusters[target])
    groups = {}
    for row in members:
        if row['candidate'] is not None:
            groups.setdefault(row['candidate'], []).append(row['id'])
    cluster_of = {name: index for index, cluster in enumerate(clusters) for name in cluster}
    return {'sheet': {
        'schema': SCHEMA, 'method': method, 'parameters': parameters, 'commission': commission,
        'set': {'sequences': len(ids), 'target_id': TARGET_ID, 'cluster_count': len(clusters),
                'largest_cluster_size': max(len(cluster) for cluster in clusters),
                'singleton_count': sum(1 for cluster in clusters if len(cluster) == 1)},
        'clusters': [{'index': index, 'size': len(cluster), 'members': cluster} for index, cluster in enumerate(clusters)],
        'members': [{**row, 'cluster': cluster_of[row['id']]} for row in members],
        'target_cluster': {'index': target, 'size': len(inside)},
        'groups': [{'candidate': candidate, 'size': len(names), 'in_target_cluster': sum(1 for name in names if name in inside),
                    'share': sum(1 for name in names if name in inside) / len(names)}
                   for candidate, names in groups.items()]}}


def group_values(sheet):
    """The candidate groups of a graded clustering and their test values, ``[(candidate, share, size, in_target_cluster)]``:
    a candidate with no sequence in the set is not in ``groups`` and gives nothing."""
    return [(row['candidate'], row['share'], row['size'], row['in_target_cluster']) for row in sheet['groups']]


__all__ = ['CONTRASTS', 'EDGE_WEIGHT', 'INFLATIONS', 'METHOD', 'SCHEMA', 'TARGET_ID', 'abc_text', 'cluster_facts', 'contrast_graph', 'contrast_undefined',
           'grade_clustering', 'group_values', 'parse_clusters', 'percentile', 'score_ratio_graph', 'with_singletons']
