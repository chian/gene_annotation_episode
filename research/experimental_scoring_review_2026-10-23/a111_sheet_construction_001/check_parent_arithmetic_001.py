"""Independent research arithmetic; no production imports, no target annotation."""
from pathlib import Path
import gzip
import json
import math
import shlex
import statistics
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
SOURCE = BASE.parent / 'a111_structural_evidence_sheet_017' / 'sources'
checks = []


def check(label, condition):
    assert condition, label
    checks.append(label)


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)


lines = (SOURCE / '1mjh.cif').read_text().splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith('_atom_site.'))
fields = []
while lines[start].startswith('_atom_site.'):
    fields.append(lines[start].strip())
    start += 1
atoms = []
for line in lines[start:]:
    if line.strip() == '#':
        break
    values = shlex.split(line)
    check('atom row has all declared columns', len(values) == len(fields)) if not atoms else None
    if len(values) != len(fields):
        raise ValueError('malformed coordinate row')
    atoms.append(dict(zip(fields, values)))


def position(atom):
    return tuple(float(atom['_atom_site.Cartn_' + dim]) for dim in 'xyz')


sites = []
for atom in atoms:
    if atom['_atom_site.auth_comp_id'] != 'MN':
        continue
    center = position(atom)
    oxygen_neighbors = []
    for other in atoms:
        if other['_atom_site.type_symbol'] != 'O':
            continue
        distance = math.dist(center, position(other))
        if distance <= 2.6:
            oxygen_neighbors.append((other, distance))
    distances = [distance for other, distance in oxygen_neighbors]
    angles = []
    for index, (first, _) in enumerate(oxygen_neighbors):
        a = tuple(x-y for x, y in zip(position(first), center))
        for second, _ in oxygen_neighbors[index+1:]:
            b = tuple(x-y for x, y in zip(position(second), center))
            cosine = sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)))
            angles.append(math.degrees(math.acos(max(-1, min(1, cosine)))))
    sites.append({'chain': atom['_atom_site.auth_asym_id'],
                  'oxygen_count': len(distances), 'distance_range_A': [min(distances), max(distances)],
                  'distance_mean_A': statistics.mean(distances),
                  'distance_2_to_2_6_passes': sum(2 <= d <= 2.6 for d in distances),
                  'angle_count': len(angles),
                  'angle_90_or_180_within_15_passes': sum(min(abs(a-90),abs(a-180)) <= 15 for a in angles)})
check('two Mn sites', len(sites) == 2)
check('six oxygen neighbors at each deposited site', all(s['oxygen_count'] == 6 for s in sites))
check('example distance predicates 6/6', all(s['distance_2_to_2_6_passes'] == 6 for s in sites))
check('example angle predicates 15/15', all(s['angle_count'] == s['angle_90_or_180_within_15_passes'] == 15 for s in sites))

validation = ET.fromstring(gzip.decompress((SOURCE / '1mjh_validation.xml.gz').read_bytes()))
atp = [e.attrib for e in validation.iter('ModelledSubgroup') if e.attrib.get('resname') == 'ATP']
check('two ATP copies in validation', len(atp) == 2)
check('native ATP RSCCs', sorted(float(e['rscc']) for e in atp) == [.958, .963])
check('model occupancy one for both ATP copies', all(float(e['avgoccu']) == 1 for e in atp))
atp_fit = statistics.mean(float(e['rscc'])**2 for e in atp)
check('ATP-only mean proposed fit', close(atp_fit, .9225665))

# Complete invented example, independent of the paper's missing target input.
def w(q, rscc, geometry, target, comparability, isolation):
    return q * max(0, rscc)**2 * geometry * target * comparability * isolation

row_a = w(.8, .95, 5/6, 3/4, .9, .9)
row_b = w(.75, .9, 1, .5, .95, 1)
row_c = -w(1-.1/.5, .9, 1, .75, 1, 1)
row_d = w(.6, .8, 1, .5, 1, 1)
check('invented A contribution', close(row_a, .3655125))
check('invented B contribution', close(row_b, .2885625))
check('invented calibrated nondetection contribution', close(row_c, -.486))
check('invented second family', close(row_d, .192))
family_1 = (row_a+row_b+row_c)/3
signed = (family_1+row_d)/2
positive = ((row_a+row_b)/3+row_d)/2
negative = (-row_c/3)/2
check('first family signed mean', close(family_1, .056025))
check('axis signed example', close(signed, .1240125))
check('positive minus negative reconstructs one contribution', close(positive-negative, signed))

row_bounds = [
    [w(.7,.93,4/6,2/4,.85,.85), w(.9,.97,1,1,.95,.95)],
    [w(.7,.88,1,.5,.9,.95), w(.8,.92,1,.5,1,1)],
    [-w(1-.05/.5,.92,1,.75,1,1), -w(1-.15/.5,.88,1,.75,1,1)],
]
family_bounds = [sum(row[k] for row in row_bounds)/3 for k in (0,1)]
other_bounds = [w(.5,.78,1,.5,1,1),w(.7,.82,1,.5,1,1)]
axis_bounds = [(family_bounds[k]+other_bounds[k])/2 for k in (0,1)]
check('axis lower enclosure', close(axis_bounds[0], .0437544875))
check('axis upper enclosure', close(axis_bounds[1], .23371100416666665))
check('nominal lies inside enclosure', axis_bounds[0] <= signed <= axis_bounds[1])

# Demonstrate the specific averaging convention, not a biological result.
one_group = row_a
with_unrelated_group = (row_a+0)/2
check('current-roster mean halves with one added zero-target group', close(with_unrelated_group, one_group/2))

result = {'purpose':'research arithmetic only', 'checks_passed':len(checks), 'checks':checks,
          'source':{'pdb':'1MJH','ATP_copy_mean_fit_proposal':atp_fit,'Mn_sites':sites},
          'synthetic':{'rows':[row_a,row_b,row_c,row_d], 'positive':positive,'negative':negative,
                       'signed_axis':signed,'axis_bounds':axis_bounds},
          'averaging_tradeoff':{'one_group':one_group,'added_zero_target_group':with_unrelated_group}}
with (BASE/'parent_arithmetic_001.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
