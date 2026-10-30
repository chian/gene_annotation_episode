"""Finite arithmetic fixtures for current A104 proposal004.

No biological input is loaded, inferred or annotated. Trees/weights/functions
below are synthetic except the three explicitly marked paper-table ratios.
This is not a production reader, native phylogenetic job or method deployment.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
from itertools import combinations, product
from math import comb
import json
import re


@dataclass(frozen=True)
class Node:
    name: str
    length: Q = Q(0)
    children: tuple = ()


def parse(text):
    # Bounded fixture syntax. Missing lengths default to zero ONLY for
    # topology-only fixtures; no missing empirical branch is read this way.
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
            name = 'node_' + str(serial)
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

    def visit(node, path, height):
        assert node.name not in nodes
        nodes[node.name] = node
        paths[node.name] = path + (node.name,)
        depths[node.name] = len(path)
        heights[node.name] = height
        for child in node.children:
            visit(child, paths[node.name], height + child.length)
    visit(root, (), Q(0))
    return nodes, paths, depths, heights


def leaves(node):
    return (frozenset([node.name]) if not node.children else
            frozenset().union(*(leaves(c) for c in node.children)))


def lca(root, a, b):
    _, paths, _, _ = index(root)
    return [x for x, y in zip(paths[a], paths[b]) if x == y][-1]


def distance(root, a, b):
    _, _, _, heights = index(root)
    return heights[a] + heights[b] - 2 * heights[lca(root, a, b)]


def triplet(root, tips):
    if not set(tips) <= leaves(root):
        return None
    _, _, depths, _ = index(root)
    pairs = list(combinations(tips, 2))
    values = [depths[lca(root, a, b)] for a, b in pairs]
    if values.count(max(values)) != 1:
        return None
    return tuple(sorted(pairs[values.index(max(values))]))


def quartet(root, tips):
    tips = frozenset(tips)
    if not tips <= leaves(root):
        return None
    nodes, _, _, _ = index(root)
    splits = set()
    for node in nodes.values():
        side = leaves(node) & tips
        if len(side) == 2:
            splits.add(tuple(sorted((tuple(sorted(side)), tuple(sorted(tips-side))))))
    assert len(splits) <= 1
    return next(iter(splits)) if splits else None


def concordance(gene, organism, intended, size=3):
    intended = sorted(set(intended))
    n = comb(len(intended), size) if len(intended) >= size else 0
    state = triplet if size == 3 else quartet
    counts = dict(match=0, conflict=0, unresolved=0)
    rows = []
    for tips in combinations(intended, size):
        a, b = state(gene, tips), state(organism, tips)
        label = 'unresolved' if a is None or b is None else ('match' if a == b else 'conflict')
        counts[label] += 1
        rows.append(dict(tips=tips, gene=a, organism=b, state=label))
    assert sum(counts.values()) == n
    f = Q(counts['match'], n) if n else Q(0)
    return dict(N=n, **counts, supported=f,
                native_fraction_defined=bool(n),
                completion_bounds=[f, Q(counts['match']+counts['unresolved'], n)] if n else None,
                comparisons=rows)


def prune_query(root):
    nodes, paths, _, _ = index(root)
    parent = nodes[paths['q'][-2]]
    siblings = [c for c in parent.children if c.name != 'q']
    attach = (('root' if parent == root else 'edge', siblings[0].name)
              if len(siblings) == 1 else ('node', parent.name))

    def prune(node, is_root=False):
        if node.name == 'q':
            return None
        kept = tuple(x for c in node.children if (x := prune(c)) is not None)
        if node.children and len(kept) == 1:
            child = kept[0]
            return replace(child, length=Q(0) if is_root else node.length+child.length)
        return replace(node, children=kept)
    return prune(root, True), attach


def membership(root, crown):
    back, (kind, target) = prune_query(root)
    nodes, _, _, _ = index(back)
    crown = frozenset(crown)
    if not crown <= leaves(back):
        return [Q(0), Q(1), 'missing_intended_reference']
    if len(crown) < 2 or crown == leaves(back):
        return [Q(0), Q(1), 'missing_declared_boundary_in_this_fixture']
    matches = [node for node in nodes.values() if leaves(node) == crown]
    if not matches:
        if any(len(node.children) > 2 for node in nodes.values()):
            return [Q(0), Q(1), 'unresolved_membership']
        return [Q(0), Q(0), 'resolved_nonmonophyly']
    c = matches[0]
    if kind == 'root':
        return [Q(0), Q(0), 'outside']
    if target == c.name:
        return [Q(0), Q(1), 'boundary'] if kind == 'node' else [Q(0), Q(0), 'stem']
    j = Q(int(leaves(nodes[target]) < crown))
    return [j, j, 'inside' if j else 'outside']


def graft(root, child_name, distal, pendant):
    def build(node):
        if node.name == child_name:
            assert 0 < distal < node.length
            return Node('graft', node.length-distal,
                        (replace(node, length=distal), Node('q', pendant)))
        return replace(node, children=tuple(build(c) for c in node.children))
    return build(root)


def outlier_factor(b, d):
    # Explicit proposal004 extension at exact zero, with no epsilon.
    if d is not None and d == 0:
        return Q(1)
    if b is None or d is None:
        return None
    assert b >= 0 and d > 0
    return min(Q(1), b/d)


def locality(root, refs):
    refs = sorted(set(refs))
    d = min(distance(root, 'q', r) for r in refs) if refs else None
    nearest = sorted(min(distance(root, r, s) for s in refs if s != r) for r in refs) if len(refs) >= 2 else []
    if not nearest:
        b = None
    else:
        mid = len(nearest)//2
        b = nearest[mid] if len(nearest) % 2 else (nearest[mid-1]+nearest[mid])/2
    return dict(b=b, d=d, O=outlier_factor(b, d))


def association(inventory, functions, claim='f', aliases=None):
    aliases = aliases or {}
    unique = sorted({aliases.get(r, r) for r in inventory})
    known = [set(functions.get(r, ())) for r in unique]
    mixed_for_claim = any(labels - {claim} for labels in known)
    k = sum(labels == {claim} for labels in known)
    n = len(unique)
    return dict(n=n, k_f=k, unknown=sum(not labels for labels in known),
                known_classes=sorted(set().union(*known)),
                mixed_for_claim=mixed_for_claim,
                C=Q(0) if mixed_for_claim or n == 0 else Q(k, n))


def score(root, organism, crown, functions, intended, size=3):
    fun = association(crown, functions)
    refs = [r for r in sorted(set(crown)) if functions.get(r)]
    f, j, o = concordance(root, organism, intended, size), membership(root, crown), locality(root, refs)
    a = Q(0) if fun['C'] == 0 else (fun['C']*f['supported']*j[0]*o['O'] if j[0] == j[1] and o['O'] is not None else None)
    return dict(function=fun, concordance=f, membership=j, locality=o, a=a)


def refinements(node):
    if not node.children:
        return [node]

    def combine(parts):
        if len(parts) == 1:
            return [parts[0]]
        rows = []
        for mask in range(1 << (len(parts)-1)):
            left = [parts[0]] + [parts[i+1] for i in range(len(parts)-1) if mask & (1 << i)]
            right = [parts[i+1] for i in range(len(parts)-1) if not mask & (1 << i)]
            if right:
                for a, b in product(combine(left), combine(right)):
                    rows.append(Node('resolve_'+'_'.join(sorted(leaves(a)|leaves(b))), Q(0), (a,b)))
        return rows
    return [replace(t, name=node.name, length=node.length)
            for kids in product(*(refinements(c) for c in node.children)) for t in combine(list(kids))]


backbone_text = '((a:.3,b:.3)C:.2,c:.5)root;'
backbone = parse(backbone_text)
placements = [('a',Q(1,5),Q(1,10),Q(3,5)), ('b',Q(1,5),Q(1,10),Q(1,5)),
              ('C',Q(1,10),Q(1,10),Q(1,10)), ('c',Q(1,5),Q(1,10),Q(1,10))]
trees = [graft(backbone,e,d,p) for e,d,p,w in placements]
organism = trees[0]  # Independent stipulated organism topology in this fixture.
taxa = ['q','a','b','c']
func = {'a':['f'],'b':['f']}
rows = [score(t,organism,['a','b'],func,taxa) for t in trees]
weights = [r[3] for r in placements]
assert [r['concordance']['match'] for r in rows] == [4,3,3,1]
assert [r['membership'][0] for r in rows] == [1,1,0,0]
assert [r['locality']['O'] for r in rows] == [1,1,1,Q(2,3)]
region = sum(w*r['a'] for w,r in zip(weights,rows))
assert region == Q(3,4)
means_product = (sum(w*r['concordance']['supported'] for w,r in zip(weights,rows)) *
                 sum(w*r['membership'][0] for w,r in zip(weights,rows)) *
                 sum(w*r['locality']['O'] for w,r in zip(weights,rows)))
assert means_product == Q(493,750)

# EDPL attachment-distance matrix; pendant length is not an operand.
attachment_distances = [[Q(0),Q(1,5),Q(1,5),Q(3,5)],
                        [Q(1,5),Q(0),Q(1,5),Q(3,5)],
                        [Q(1,5),Q(1,5),Q(0),Q(2,5)],
                        [Q(3,5),Q(3,5),Q(2,5),Q(0)]]
total_length = sum(n.length for n in index(backbone)[0].values())
edpl = sum(weights[i]*weights[j]*attachment_distances[i][j] for i in range(4) for j in range(4))/total_length
assert edpl == Q(46,325)
far_trees = [graft(backbone,e,d,Q(29,5)) for e,d,p,w in placements]
far_rows = [score(t,organism,['a','b'],func,taxa) for t in far_trees]
far_region = sum(w*r['a'] for w,r in zip(weights,far_rows))
assert far_region == Q(3,40)

# Known other-function reference outside the fixed crown changes no factor.
outside_other = [score(t,organism,['a','b'],dict(func,c=['g']),taxa) for t in trees]
assert [r['a'] for r in outside_other] == [r['a'] for r in rows]
mixed = [score(t,organism,['a','b'],{'a':['f'],'b':['g']},taxa) for t in trees]
multi = [score(t,organism,['a','b'],{'a':['f'],'b':['f','g']},taxa) for t in trees]
assert all(r['a'] == 0 for r in mixed+multi)

# Fixed larger clade: uncharacterized member is not a verified match.
large_text = '((((q:.1,a:.1):.1,b:.2):.1,u:.3)C:.2,c:.5)root;'
large = parse(large_text)
partial = score(large,large,['a','b','u'],func,['q','a','b','u','c'])
assert partial['function']['C'] == Q(2,3) and partial['a'] == Q(2,3)
all_f = score(large,large,['a','b','u'],dict(func,u=['f']),['q','a','b','u','c'])
u_g = score(large,large,['a','b','u'],dict(func,u=['g']),['q','a','b','u','c'])
assert (all_f['a'],u_g['a']) == (1,0)
broad = score(large,large,['a','b','u'],{'a':['h'],'b':['h'],'u':['h']},['q','a','b','u','c'])
# score() uses f as claim, so broaden explicitly through the same formula.
broad_c = association(['a','b','u'],{'a':['h'],'b':['h'],'u':['h']},claim='h')['C']
broad_score = broad_c*broad['concordance']['supported']*broad['membership'][0]*broad['locality']['O']
assert broad_score == 1
assert association(['a','a_alias','b'],func,aliases={'a_alias':'a'}) == association(['a','b'],func)

single = locality(trees[0],['a'])
assert single == dict(b=None,d=Q(3,10),O=None)
one_characterized_bounds = [Q(0),Q(1,2)*region]
assert one_characterized_bounds == [0,Q(3,8)]
zeros = {(str(b),str(d)):outlier_factor(b,d) for b,d in [(Q(1),Q(0)),(Q(0),Q(1)),(Q(0),Q(0)),(None,Q(1)),(None,Q(0))]}
assert list(zeros.values()) == [1,0,1,None,1]

# Intended taxon c missing only from organism tree: no improved denominator.
missing_org = parse('((q,a),b);')
missing = concordance(trees[0],missing_org,taxa)
native_common = concordance(trees[0],missing_org,['q','a','b'])
assert (missing['N'],missing['match'],missing['unresolved'],missing['supported']) == (4,1,3,Q(1,4))
assert native_common['supported'] == 1
assert concordance(parse('(q,a);'),parse('(q,a);'),['q','a'])['supported'] == 0
assert not concordance(parse('(q,a);'),parse('(q,a);'),['q','a'])['native_fraction_defined']
unrooted_rows = [concordance(t,organism,taxa,4) for t in trees]
assert [r['supported'] for r in unrooted_rows] == [1,0,0,0]
quartet_region = sum(w*f['supported']*r['membership'][0]*r['locality']['O'] for w,f,r in zip(weights,unrooted_rows,rows))
assert quartet_region == Q(3,5)
star = parse('(q,a,b,c);')
assert concordance(star,star,taxa,4)['supported'] == 0
assert concordance(star,star,taxa,4)['unresolved'] == 1

boundary = parse('((q:.1,a:.3,b:.3)C:.2,c:.5)root;')
boundary_rows = [score(t,organism,['a','b'],func,taxa) for t in refinements(boundary)]
assert len(boundary_rows) == 3
assert min(r['a'] for r in boundary_rows) == 0 and max(r['a'] for r in boundary_rows) == 1
assert membership(boundary,['a','b']) == [0,1,'boundary']
assert concordance(boundary,organism,taxa)['supported'] == Q(3,4)
nonmono = parse('(((q:.1,a:.1):.1,c:.2):.1,b:.4);')
assert membership(nonmono,['a','b']) == [0,0,'resolved_nonmonophyly']
assert membership(trees[0],['a','missing_b']) == [0,1,'missing_intended_reference']

# Missing included native sample of weight .2 is not dropped/renormalized.
missing_mass_bounds = [Q(3,5),Q(4,5)]
assert missing_mass_bounds[0] == weights[0]*rows[0]['a']
assert missing_mass_bounds[1] == missing_mass_bounds[0]+weights[1]
known_stem_missing_branches = Q(0)  # J=0 fixes contribution despite missing O.

# Whole candidate: minimum within each actual joint draw, then weighted sum.
with_constant_region = sum(w*min(r['a'],Q(2,5)) for w,r in zip(weights,rows))
assert with_constant_region == Q(8,25)
paired = [(Q(1,2),Q(1),Q(0)),(Q(1,2),Q(0),Q(1))]
paired_score = sum(w*min(a,b) for w,a,b in paired)
assert paired_score == 0
assert min(sum(w*a for w,a,b in paired),sum(w*b for w,a,b in paired)) == Q(1,2)
coupling_grid = [Q(i,20) for i in range(11)]
coupling_scores = []
for t in coupling_grid:
    # Marginals: each region is {0:.5,1:.5}; t=P(1,1)=P(0,0).
    pi = {(0,0):t,(1,1):t,(1,0):Q(1,2)-t,(0,1):Q(1,2)-t}
    assert sum(pi.values()) == 1
    assert all(sum(v for xy,v in pi.items() if xy[r] == 1) == Q(1,2) for r in [0,1])
    coupling_scores.append(sum(v*min(xy) for xy,v in pi.items()))
assert [min(coupling_scores),max(coupling_scores)] == [0,Q(1,2)]

# Shared function uncertainty is assigned once, not separately per region.
shared_function_candidate = [min(all_f['a'],Q(2,5)),min(u_g['a'],Q(2,5))]
assert shared_function_candidate == [Q(2,5),Q(0)]

# Reported paper quantities, not synthetic biology or A104 whole scores.
paper_ratios = {'Wege2010_ratio_of_reported_current_ratios':Q(4)/Q(9,10),
                'Stockbridge2012_successful_transport_panel_fraction':Q(8,29),
                'Stockbridge2012_exact_stoichiometry_in_transport_panel':Q(1,8)}
assert paper_ratios['Wege2010_ratio_of_reported_current_ratios'] == Q(40,9)

checks = 0
for c,f,j,o in product([Q(0),Q(1,5),Q(1,2),Q(1)],repeat=4):
    a=c*f*j*o
    assert 0 <= a <= min(c,f,j,o) <= 1
    assert min(a,a) == a
    checks += 1


def export(x):
    if isinstance(x,Q):
        return {'exact':str(x),'decimal':float(x)}
    if isinstance(x,dict):
        return {k:export(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):
        return [export(v) for v in x]
    return x


result = dict(
    status='all assertions passed; finite research arithmetic only',
    base_inputs=dict(backbone=backbone_text,placements=placements,intended_taxa=taxa,functions=func),
    base_rows=rows,base_region=region,incorrect_product_of_means=means_product,
    EDPL=dict(attachment_distances=attachment_distances,total_length=total_length,value=edpl),
    outlier_rows=far_rows,outlier_region=far_region,
    function_coverage=dict(large_tree=large_text,partial=partial,complete_f=all_f['a'],known_g=u_g['a'],broader_h=broad_score),
    single_reference=dict(operands=single,observed_region_bounds=one_characterized_bounds),
    zero_distance_conventions=zeros,
    intended_missing_taxon=dict(fixed_scope=missing,native_common_leaf=native_common),
    unrooted=dict(rows=unrooted_rows,region=quartet_region),
    unresolved_boundary=dict(membership=membership(boundary,['a','b']),refinement_scores=[r['a'] for r in boundary_rows]),
    missing_included_mass_bounds=missing_mass_bounds,
    candidate=dict(with_constant_required_region=with_constant_region,
                   paired_opposite_regions=paired_score,unknown_coupling_bounds=[0,Q(1,2)],
                   included_missing_required_region_bounds=[0,region],
                   never_included_function_alternative=region,
                   shared_function_completion_values=shared_function_candidate,
                   not_applicable_broad_HGT=None),
    paper_arithmetic=paper_ratios,range_grid_checks=checks,
    limits=['No native phylogenetic program, biological dataset or production reader executed.',
            'Current checked fixture004 does not validate historical proposals001/002.',
            'No calibration, adopted-policy, axis-completion or goal-completion claim.'])
print(json.dumps(export(result),indent=2))
