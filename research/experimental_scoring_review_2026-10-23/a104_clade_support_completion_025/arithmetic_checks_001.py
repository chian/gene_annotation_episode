"""Bounded synthetic arithmetic for the A104 positive-clade proposal.

This is a research fixture, not a production reader, phylogenetic inference
tool, or scorer binding. It reads no biological files and writes JSON to stdout.
All trees, weights, dates and event operands below are invented. Native-like
formats illustrate input meanings; they are not native results from an analysis.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
from itertools import combinations, product
import json
import re


@dataclass(frozen=True)
class Node:
    name: str
    length: Q = Q(0)
    children: tuple = ()


def parse(text):
    tokens = re.findall(r"[(),:;]|[^\s(),:;]+", text)
    pos, serial = 0, 0

    def subtree():
        nonlocal pos, serial
        children = []
        if tokens[pos] == '(':
            pos += 1
            while True:
                children.append(subtree())
                separator = tokens[pos]
                pos += 1
                if separator == ')':
                    break
                assert separator == ','
        if tokens[pos] not in ':,);':
            name = tokens[pos]
            pos += 1
        else:
            serial += 1
            name = 'internal_' + str(serial)
        length = Q(0)
        if tokens[pos] == ':':
            pos += 1
            length = Q(tokens[pos])
            pos += 1
        return Node(name, length, tuple(children))

    root = subtree()
    assert tokens[pos:] == [';']
    return root


def index(root):
    nodes, paths, depths, heights = {}, {}, {}, {}

    def visit(node, path, distance):
        assert node.name not in nodes
        nodes[node.name] = node
        paths[node.name] = path + (node.name,)
        depths[node.name] = len(path)
        heights[node.name] = distance
        for child in node.children:
            visit(child, paths[node.name], distance + child.length)
    visit(root, (), Q(0))
    return nodes, paths, depths, heights


def leaves(node):
    return (frozenset([node.name]) if not node.children else
            frozenset().union(*(leaves(child) for child in node.children)))


def lca(root, a, b):
    _, paths, _, _ = index(root)
    common = [x for x, y in zip(paths[a], paths[b]) if x == y]
    return common[-1]


def distance(root, a, b):
    _, _, _, heights = index(root)
    return heights[a] + heights[b] - 2 * heights[lca(root, a, b)]


def topology_state(root, a, b, c):
    _, _, depths, _ = index(root)
    pairs = [(a, b), (a, c), (b, c)]
    values = [depths[lca(root, x, y)] for x, y in pairs]
    peak = max(values)
    if values.count(peak) != 1:
        return 'unresolved'
    return ['ab|c', 'ac|b', 'bc|a'][values.index(peak)]


def prune_query(root, query='q'):
    nodes, paths, _, _ = index(root)
    parent = nodes[paths[query][-2]]
    siblings = [node for node in parent.children if node.name != query]
    if len(siblings) == 1:
        attachment = ('root' if parent == root else 'edge', siblings[0].name)
    else:
        attachment = ('node', parent.name)

    def prune(node, is_root=False):
        if node.name == query:
            return None
        kept = tuple(x for c in node.children if (x := prune(c)) is not None)
        if node.children and len(kept) == 1:
            child = kept[0]
            return replace(child, length=Q(0) if is_root else child.length + node.length)
        return replace(node, children=kept)
    return prune(root, True), attachment


def membership(root, crown, query='q'):
    backbone, attachment = prune_query(root, query)
    nodes, _, _, _ = index(backbone)
    crown = frozenset(crown)
    if not crown <= leaves(backbone):
        return (Q(0), Q(1), 'missing_intended_tip')
    if len(crown) < 2 or crown == leaves(backbone):
        return (Q(0), Q(1), 'missing_proper_multitip_crown')
    matches = [node for node in nodes.values() if leaves(node) == crown]
    if not matches:
        # The fixture calls this branch on complete binary refinements only.
        assert all(len(n.children) <= 2 for n in nodes.values())
        return (Q(0), Q(0), 'resolved_nonmonophyly')
    crown_node = matches[0]
    kind, target = attachment
    if kind == 'root':
        return (Q(0), Q(0), 'outside_root')
    if target == crown_node.name:
        return ((Q(0), Q(1), 'crown_boundary') if kind == 'node' else
                (Q(0), Q(0), 'crown_stem'))
    inside = leaves(nodes[target]) < crown
    value = Q(int(inside))
    return (value, value, 'inside' if inside else 'outside')


def outlier(root, refs):
    refs = sorted(set(refs))
    if len(refs) < 2:
        return {'spacing': None, 'query_distance': distance(root, 'q', refs[0]),
                'factor': None}
    nearest = sorted(min(distance(root, r, other) for other in refs if other != r)
                     for r in refs)
    m = len(nearest) // 2
    spacing = nearest[m] if len(nearest) % 2 else (nearest[m-1] + nearest[m]) / 2
    qdistance = min(distance(root, 'q', r) for r in refs)
    factor = None if spacing == 0 else (Q(1) if qdistance == 0 else min(Q(1), spacing / qdistance))
    return {'spacing': spacing, 'query_distance': qdistance, 'factor': factor}


def placement_contrast(root, positive, contrary):
    counts = {'f': 0, 'g': 0, 'outside': 0, 'unresolved': 0}
    for r in sorted(set(positive)):
        for a in sorted(set(contrary)):
            state = topology_state(root, 'q', r, a)
            counts[{'ab|c': 'f', 'ac|b': 'g', 'bc|a': 'outside',
                    'unresolved': 'unresolved'}[state]] += 1
    n = sum(counts.values())
    assert n and counts['unresolved'] == 0
    return {'counts': counts, 'N': n, 'P': Q(counts['f'] - counts['g'], n)}


def history(root, organism, explanation):
    other = sorted(leaves(root) - {'q'})
    concordant = discordant = 0
    for a, b in combinations(other, 2):
        x, y = topology_state(root, 'q', a, b), topology_state(organism, 'q', a, b)
        assert 'unresolved' not in (x, y)
        if x == y:
            concordant += 1
        else:
            discordant += 1
    n = concordant + discordant
    return {'concordant': concordant, 'discordant': discordant, 'N': n,
            'H': (concordant + discordant * explanation) / n}


def sample(root, organism, crown, positive, contrary, explanation):
    jl, ju, reason = membership(root, crown)
    assert jl == ju
    of = outlier(root, positive)
    hist = history(root, organism, explanation)
    assert of['factor'] is not None
    if contrary:
        contrast = placement_contrast(root, positive, contrary)
        og = outlier(root, contrary)
        assert og['factor'] is not None
        p = contrast['P']
        supporting_contrast = max(Q(0), p) * of['factor'] * hist['H']
        opposition = max(Q(0), -p) * og['factor']
        supporting = min(jl, max(Q(0), p)) * of['factor'] * hist['H']
    else:
        contrast = og = supporting_contrast = None
        supporting = jl * of['factor'] * hist['H']
        opposition = Q(0)
    return {'J': jl, 'membership_reason': reason, 'O_f': of, 'history': hist,
            'contrast': contrast, 'O_g': og, 'support': supporting,
            'opposition': opposition, 'contrast_only_support': supporting_contrast}


def average(samples):
    assert sum(weight for weight, row in samples) == 1
    support = sum(weight * row['support'] for weight, row in samples)
    opposition = sum(weight * row['opposition'] for weight, row in samples)
    return {'L': sum(weight * row['J'] for weight, row in samples),
            'support': support, 'opposition': opposition, 'signed': support-opposition,
            'coordinate': max(Q(0), support-opposition)}


def graft(root, edge_child, distal, pendant):
    def build(node):
        if node.name == edge_child:
            assert 0 < distal < node.length
            return Node('graft', node.length-distal,
                        (replace(node, length=distal), Node('q', pendant)))
        return replace(node, children=tuple(build(c) for c in node.children))
    return build(root)


def resolutions(node):
    """Enumerate tiny rooted binary refinements; added branches have length 0."""
    if not node.children:
        return [node]

    def combine(parts):
        if len(parts) == 1:
            return [parts[0]]
        output = []
        # A bipartition with the first child on the left is counted only once.
        for mask in range(1 << (len(parts)-1)):
            left = [parts[0]] + [parts[i+1] for i in range(len(parts)-1) if mask & (1 << i)]
            right = [parts[i+1] for i in range(len(parts)-1) if not mask & (1 << i)]
            if not right:
                continue
            for a, b in product(combine(left), combine(right)):
                name = 'resolve_' + '_'.join(sorted(leaves(a) | leaves(b)))
                output.append(Node(name, Q(0), (a, b)))
        return output

    output = []
    for kids in product(*(resolutions(child) for child in node.children)):
        for refined in combine(list(kids)):
            output.append(replace(refined, name=node.name, length=node.length))
    return output


TIN = '(((q:.6,f1:.2):.1,f2:.3):.2,(x1:.2,x2:.2):.2);'
TOUT = '((f1:.2,f2:.2):.2,((q:.6,x1:.2):.1,x2:.1):.2);'
inside, outside = parse(TIN), parse(TOUT)
donor, recipient = [Q(4,5), Q(1,5), Q(0)], [Q(0), Q(3,4), Q(1,4)]
K = [[Q(0), Q(3,4), Q(1,8)], [Q(0), Q(1), Q(0)], [Q(0), Q(0), Q(0)]]
routed = [sum(donor[e]*K[e][h] for e in range(3)) for h in range(3)]
B = sum(min(d, r) for d, r in zip(routed, recipient))
M, T = Q(600+200*Q(1,2), 1000), Q(9,10)
E = B*M*T
assert (B, M, T, E) == (Q(17,20), Q(7,10), Q(9,10), Q(1071,2000))

tree_rows = {}
region_rows = {}
for label, contrary in [('no_g', []), ('with_g', ['x1','x2'])]:
    tree_rows[label] = [sample(t, outside, ['f1','f2'], ['f1','f2'], contrary, E)
                        for t in [inside, outside]]
    a, b = tree_rows[label]
    assert a['O_f']['factor'] == Q(3,4) and b['O_f']['factor'] == Q(4,13)
    assert (a['history']['concordant'], b['history']['concordant']) == (0,6)
    region_rows[label] = average([(Q(4,5), a), (Q(1,5), b)])
assert region_rows['no_g']['coordinate'] == Q(3213,10000)
assert region_rows['with_g']['coordinate'] == Q(2213,10000)

candidate_rows = {}
for label, contrary in [('no_g', []), ('with_g', ['x1','x2'])]:
    regions = []
    for weight, explanation in [(Q(4,5), E), (Q(9,10), Q(3,5)), (Q(3,5), Q(1))]:
        a, b = [sample(t, outside, ['f1','f2'], ['f1','f2'], contrary, explanation)
                for t in [inside, outside]]
        regions.append(average([(weight,a),(1-weight,b)]))
    si1, oi1 = min(row['support'] for row in regions[:2]), max(row['opposition'] for row in regions[:2])
    support, opposition = min(si1, regions[2]['support']), max(oi1, regions[2]['opposition'])
    candidate_rows[label] = {'regions': regions, 'support': support, 'opposition': opposition,
                             'signed': support-opposition, 'coordinate': max(Q(0),support-opposition)}
assert candidate_rows['no_g']['coordinate'] == Q(3213,10000)
assert candidate_rows['with_g']['coordinate'] == Q(1213,10000)

backbone_text = '((f1:.3,f2:.3)C:.2,(x1:.2,x2:.2)X:.2)root;'
backbone = parse(backbone_text)
edge_inputs = [('f1',Q(1,5),Q(3,5),Q(3,5)), ('f2',Q(1,5),Q(3,10),Q(1,5)),
               ('C',Q(1,10),Q(3,10),Q(1,10)), ('x1',Q(1,10),Q(3,5),Q(1,10))]
edge_trees = [graft(backbone, edge, distal, pendant) for edge, distal, pendant, weight in edge_inputs]
edge_rows, edge_results = {}, {}
for label, contrary in [('no_g', []), ('with_g', ['x1','x2'])]:
    rows = [sample(t, edge_trees[0], ['f1','f2'], ['f1','f2'], contrary, Q(3,5)) for t in edge_trees]
    weighted = [(edge_inputs[i][3], row) for i,row in enumerate(rows)]
    edge_rows[label], edge_results[label] = rows, average(weighted)
assert [row['history']['concordant'] for row in edge_rows['no_g']] == [6,5,5,0]
assert [row['O_f']['factor'] for row in edge_rows['no_g']] == [Q(3,4),Q(1),Q(6,7),Q(3,7)]
assert edge_rows['no_g'][2]['membership_reason'] == 'crown_stem'
assert edge_results['no_g']['coordinate'] == Q(191,300)
assert edge_results['with_g']['coordinate'] == Q(1217,2100)
contrast_edge_support = sum(edge_inputs[i][3]*row['contrast_only_support'] for i,row in enumerate(edge_rows['with_g']))
contrast_edge_coordinate = contrast_edge_support-edge_results['with_g']['opposition']
assert contrast_edge_coordinate == Q(277,420)
assert contrast_edge_coordinate-edge_results['with_g']['coordinate'] == Q(2,25)

mixed_text = '((((q:.2,g1:.2):.1,g2:.3):.1,(f1:.2,f2:.2):.2):.2,(x1:.2,x2:.2):.2);'
mixed = parse(mixed_text)
mixed_rows = {label: sample(mixed,mixed,['f1','f2','g1','g2'],['f1','f2'],refs,Q(1))
              for label,refs in [('uncharacterized_g',[]),('characterized_g',['g1','g2'])]}
assert mixed_rows['uncharacterized_g']['support'] == Q(1,2)
assert mixed_rows['characterized_g']['support'] == 0 and mixed_rows['characterized_g']['opposition'] == 1

polytomy_text = '(((q:.6,f1:.2):.1,f2:.3,u:.3):.2,(x1:.2,x2:.2):.2);'
polytomy = parse(polytomy_text)
refinements = resolutions(polytomy)
assert len(refinements) == 3
small_crown_states = [membership(t,['f1','f2'])[0] for t in refinements]
large_crown_states = [membership(t,['f1','f2','u'])[0] for t in refinements]
assert set(small_crown_states) == {Q(0),Q(1)} and set(large_crown_states) == {Q(1)}
boundary_text = '((q:.6,f1:.3,f2:.3)C:.2,(x1:.2,x2:.2):.2);'
boundary = parse(boundary_text)
assert membership(boundary,['f1','f2']) == (Q(0),Q(1),'crown_boundary')
assert set(membership(t,['f1','f2'])[0] for t in resolutions(boundary)) == {Q(0),Q(1)}
nonmono = parse('(((q:.2,f1:.2):.1,u:.3):.2,(f2:.2,x:.2):.2);')
assert membership(nonmono,['f1','f2']) == (Q(0),Q(0),'resolved_nonmonophyly')
assert membership(inside,['f1','missing_f2']) == (Q(0),Q(1),'missing_intended_tip')

# Aliases are a set operation; truly distinct zero-spacing references stay distinct.
aliases = {'f1_alias':'f1'}
refs = [aliases.get(r,r) for r in ['f1','f1_alias','f2']]
assert outlier(inside, refs) == outlier(inside,['f1','f2'])
assert outlier(inside,['f1'])['factor'] is None
zero_tree = parse('(((f1:0,f2:0):.1,q:.2):.1,x:.2);')
assert outlier(zero_tree,['f1','f2'])['factor'] is None
assert candidate_rows['no_g']['support'] == min(row['support'] for row in candidate_rows['no_g']['regions']*2)

sparse_region = [Q(0), Q(4,5)*E]
sparse_candidate = [Q(0), min(sparse_region[1],Q(81,200),Q(9,20))]
assert sparse_region == [Q(0),Q(1071,2500)] and sparse_candidate == [Q(0),Q(81,200)]
mass_bounds = [Q(7,10)*Q(3,4)*Q(4,5), Q(85,100)*Q(3,4)*Q(4,5)]
assert mass_bounds == [Q(21,50),Q(51,100)]
joint = [(Q(1,2),Q(1),Q(1),Q(1,5)),(Q(1,2),Q(0),Q(1,2),Q(1))]
joint_mean = sum(w*j*o*h for w,j,o,h in joint)
wrong_means = (sum(w*j for w,j,o,h in joint)*sum(w*o for w,j,o,h in joint)*sum(w*h for w,j,o,h in joint))
assert joint_mean == Q(1,10) and wrong_means == Q(9,40)

# Range, asymmetric opposition, and added-contrast monotonicity checks.
checks = 0
grid = [Q(0),Q(1,5),Q(1,2),Q(1)]
for j, of, og, h, p in product(grid,grid,grid,grid,[-1,Q(-1,2),0,Q(1,2),1]):
    no_g = j*of*h
    support = min(j,max(Q(0),p))*of*h
    opposing = max(Q(0),-p)*og
    signed = support-opposing
    assert 0 <= support <= no_g <= 1 and 0 <= opposing <= 1
    assert -1 <= signed <= 1 and 0 <= max(Q(0),signed) <= 1
    checks += 1


def export(value):
    if isinstance(value,Q):
        return {'exact':str(value),'decimal':float(value)}
    if isinstance(value,dict):
        return {k:export(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [export(v) for v in value]
    return value


result = {
    'status':'all assertions passed; synthetic research arithmetic only',
    'synthetic_inputs':{'T_in':TIN,'T_out':TOUT,'organism_topology':'T_out; stipulated independently',
                        'B':B,'M':M,'T':T,'E':E,'backbone':backbone_text,
                        'edge_rows_edge_distal_pendant_weight':edge_inputs,'mixed_tree':mixed_text,
                        'polytomy':polytomy_text,'boundary':boundary_text},
    'two_tree_samples':tree_rows,'two_tree_regions':region_rows,'whole_candidates':candidate_rows,
    'edge_samples':edge_rows,'edge_results':edge_results,
    'unchanged_contrast_only_edge_coordinate':contrast_edge_coordinate,
    'functional_heterogeneity':mixed_rows,
    'unresolved_examples':{'three_refinements_small_crown':small_crown_states,
                           'three_refinements_large_crown':large_crown_states,
                           'crown_boundary':membership(boundary,['f1','f2']),
                           'missing_tip':membership(inside,['f1','missing_f2'])},
    'identification_bounds':{'one_positive_reference_region':sparse_region,
                             'one_positive_reference_candidate':sparse_candidate,
                             'unavailable_included_comparison':{'support':[Q(0),Q(3213,10000)],
                                'opposition':[Q(0),Q(1)],'signed':[Q(-1),Q(3213,10000)],
                                'coordinate':[Q(0),Q(3213,10000)]},
                             'omitted_placement_mass':mass_bounds},
    'joint_dependence':{'correct_within_sample_mean':joint_mean,'incorrect_product_of_means':wrong_means},
    'range_grid_checks':checks,
    'limits':['No biological files, primary source, inference program or production binding used.',
              'Fixture parser/grafting/refinements are bounded arithmetic aids, not general readers.',
              'No goal, axis, implementation, calibration or adoption completion declared.']}
print(json.dumps(export(result),indent=2))
