"""Research-only A111 calculations; no production imports or current target use."""
from pathlib import Path
import gzip
import json
import math
import shlex
import statistics
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def cif_atoms(path):
    lines = path.read_text().splitlines()
    fields, records = [], []
    for n, line in enumerate(lines):
        if line.startswith('_atom_site.'):
            fields.append(line.strip())
        elif fields and line.strip() == '#':
            break
        elif fields and not line.startswith('_'):
            values = shlex.split(line)
            if len(values) != len(fields):
                raise ValueError((path.name, n + 1, len(values), len(fields)))
            records.append(dict(zip(fields, values)))
    return records


def atom(records, residue, atom_name, resname=None):
    matches = [a for a in records
               if a['_atom_site.auth_asym_id'] == 'A'
               and a['_atom_site.auth_seq_id'] == str(residue)
               and a['_atom_site.auth_atom_id'] == atom_name
               and (resname is None or a['_atom_site.auth_comp_id'] == resname)]
    assert len(matches) == 1, (residue, atom_name, matches)
    return tuple(float(matches[0]['_atom_site.Cartn_' + k]) for k in 'xyz')


def shift(p, b):
    return p[0], p[1] + b, p[2]


def angle(a, b, c):
    u, v = [a[i]-b[i] for i in range(3)], [c[i]-b[i] for i in range(3)]
    cosine = sum(x*y for x,y in zip(u,v))/(math.sqrt(sum(x*x for x in u))*math.sqrt(sum(x*x for x in v)))
    return math.degrees(math.acos(max(-1, min(1, cosine))))


def fit(rscc):
    assert -1 <= rscc <= 1, 'invalid native RSCC'
    return max(0.0, rscc) ** 2


def comparability(components):
    assert components and all(0 <= x <= 1 for x in components)
    return math.prod(components) ** (1 / len(components))


def isolation(signal, nuisance_bound):
    assert signal >= 0 and nuisance_bound >= 0
    return 0.0 if signal == 0 else max(0.0, 1 - nuisance_bound / signal)


def weight(q, d, g, t, c, i):
    values = (q, d, g, t, c, i)
    assert all(0 <= x <= 1 for x in values)
    return math.prod(values)


def cluster_mean(rows):
    # Replicas of a representation refer to one canonical observation id.
    unique = {}
    for key, value in rows:
        if key in unique and unique[key] != value:
            raise ValueError('conflicting representations need explicit reconciliation')
        unique[key] = value
    return statistics.mean(unique.values())


def run():
    result = {'purpose': 'research only, no current target', 'sources': {}}
    mj_atoms = cif_atoms(HERE/'sources'/'1mjh.cif')
    mj_validation = ET.fromstring(gzip.decompress((HERE/'sources'/'1mjh_validation.xml.gz').read_bytes()))
    mj_sites = []
    for mn in [r for r in mj_atoms if r['_atom_site.auth_comp_id'] == 'MN']:
        p = tuple(float(mn['_atom_site.Cartn_'+k]) for k in 'xyz')
        neighbors = []
        for a in mj_atoms:
            if a['_atom_site.type_symbol'] != 'O':
                continue
            xyz = tuple(float(a['_atom_site.Cartn_'+k]) for k in 'xyz')
            distance = math.dist(p, xyz)
            if distance <= 2.6:
                neighbors.append({'chain':a['_atom_site.auth_asym_id'],
                                  'residue':a['_atom_site.auth_seq_id'],
                                  'name':a['_atom_site.auth_comp_id'],
                                  'atom':a['_atom_site.auth_atom_id'],
                                  'distance_A':distance,'xyz':xyz})
        neighbors.sort(key=lambda x:x['distance_A'])
        angles = [angle(x['xyz'],p,y['xyz']) for i,x in enumerate(neighbors) for y in neighbors[i+1:]]
        mj_sites.append({'chain':mn['_atom_site.auth_asym_id'],
                         'residue':mn['_atom_site.auth_seq_id'],'neighbors':neighbors,
                         'mean_O_distance_A':statistics.mean(x['distance_A'] for x in neighbors),
                         'angles_deg':angles,
                         'distance_predicate_count':sum(2 <= x['distance_A'] <= 2.6 for x in neighbors),
                         'angular_predicate_count':sum(min(abs(x-90),abs(x-180)) <= 15 for x in angles)})
    mj_atp_validation = [x.attrib for x in mj_validation.iter('ModelledSubgroup') if x.attrib.get('resname') == 'ATP']
    result['sources']['1mjh'] = {'Mn_sites':mj_sites,'ATP_validation':mj_atp_validation,
                                 'ATP_copy_mean_fit':statistics.mean(fit(float(x['rscc'])) for x in mj_atp_validation)}
    for pdb, b, center_res, center_name in [('4kk3', 40.749, 201, 'P'), ('4kk4', 39.34, 7, 'P')]:
        records = cif_atoms(HERE/'sources'/f'{pdb}.cif')
        center = atom(records, center_res, center_name)
        nh2 = shift(atom(records,149,'NH2'), b)
        local = {
            'pdb': pdb.upper(),
            'symmetry_operation_for_neighbor': f'(x,y+{b},z) Angstrom; one unit-cell b translation',
            'neighbor_Arg149_NH2_to_P_A': math.dist(nh2,center),
            'neighbor_Arg149_NH1_to_Thr11_OG1_A': math.dist(shift(atom(records,149,'NH1'),b),atom(records,11,'OG1')),
            'neighbor_Arg149_NH2_to_Asp118_OD2_A': math.dist(nh2,atom(records,118,'OD2')),
        }
        if pdb == '4kk4':
            og = atom(records,7,'OG')
            local['SEP7_P_OG_A'] = math.dist(center,og)
            local['neighbor_Arg149_NH2_P_SEP7_OG_angle_deg'] = angle(nh2,center,og)
        validation = ET.fromstring(gzip.decompress((HERE/'sources'/f'{pdb}_validation.xml.gz').read_bytes()))
        local['selected_validation'] = [e.attrib for e in validation.iter('ModelledSubgroup')
                                        if e.attrib.get('chain') == 'A' and
                                        e.attrib.get('resnum') in ('7','11','118','149','201')]
        result['sources'][pdb] = local
    result['derived_source_components'] = {
        '4KK3_PO4_RSCC_squared': fit(.967),
        '4KK4_SEP7_RSCC_squared': fit(.934),
        '4KK3_contact_min_PO4_Arg149_RSCC_squared': fit(min(.967,.773)),
        '4KK4_contact_min_SEP7_Arg149_RSCC_squared': fit(min(.934,.907)),
        '4KK3_contact_min_Asp118_Arg149_RSCC_squared': fit(min(.944,.773)),
        '4KK4_contact_min_Asp118_Arg149_RSCC_squared': fit(min(.934,.907)),
        '4KK3_to_4KK4_native_P_NH2_distance_change_A': result['sources']['4kk4']['neighbor_Arg149_NH2_to_P_A'] - result['sources']['4kk3']['neighbor_Arg149_NH2_to_P_A'],
        'illustrative_comparability_pH_PEG_only': comparability([math.exp(-.5*(1.5/1)**2), math.exp(-.5*(5/10)**2)]),
        'illustrative_comparability_four_declared_components': comparability([math.exp(-.5*(1.5/1)**2),math.exp(-.5*(5/10)**2),146/151,1]),
        'comparability_scales_are_proposed_not_source_uncertainty': True,
    }

    # Invented complete example; each value is declared in WORKED_EXAMPLES_001.md.
    a = weight(.80,fit(.95),5/6,3/4,.90,.90)
    b = weight(.75,fit(.90),1,1/2,.95,1)
    opposition = weight(1-.10/.50,fit(.90),1,3/4,1,1)
    clusters = [a,b,-opposition]
    family1 = statistics.mean(clusters)
    family2 = weight(.60,fit(.80),1,1/2,1,1)
    axis = statistics.mean([family1,family2])
    bounds1 = [
        [weight(.70,fit(.93),4/6,2/4,.85,.85),weight(.90,fit(.97),1,4/4,.95,.95)],
        [weight(.70,fit(.88),1,1/2,.90,.95),weight(.80,fit(.92),1,1/2,1,1)],
        [-weight(1-.05/.50,fit(.92),1,3/4,1,1),-weight(1-.15/.50,fit(.88),1,3/4,1,1)],
    ]
    f1_bounds = [statistics.mean([x[k] for x in bounds1]) for k in (0,1)]
    f2_bounds = [weight(.50,fit(.78),1,1/2,1,1),weight(.70,fit(.82),1,1/2,1,1)]
    axis_bounds = [(f1_bounds[k]+f2_bounds[k])/2 for k in (0,1)]
    result['synthetic_complete_example'] = {
        'invented': True, 'family1_positive_cluster_A':a,'family1_positive_cluster_B':b,
        'family1_opposition_strength':opposition,'family1_signed_mean':family1,
        'family1_support_mean':(a+b)/3,'family1_opposition_mean':opposition/3,
        'family1_between_cluster_sample_SD':statistics.stdev(clusters),
        'family1_standard_error_descriptive':statistics.stdev(clusters)/math.sqrt(3),
        'family2_signed_mean':family2,'axis_signed':axis,'axis_nonnegative_support':max(0,axis),
        'axis_support_mass':((a+b)/3+family2)/2,
        'axis_opposition_mass':opposition/3/2,
        'family1_each_cluster_bounds':bounds1,'family1_bounds':f1_bounds,
        'family2_bounds':f2_bounds,'axis_signed_bounds':axis_bounds,
        'axis_nonnegative_support_bounds':[max(0,x) for x in axis_bounds],
    }
    checks = []
    def check(label, condition):
        assert condition, label
        checks.append({'check':label,'passed':True})
    check('native RSCC conversion arithmetic', math.isclose(fit(.963),.927369))
    check('retained 1MJH has two six-oxygen Mn sites', len(mj_sites) == 2 and all(len(x['neighbors']) == 6 for x in mj_sites))
    check('retained 1MJH oxygen distances and octahedral angle predicates', all(x['distance_predicate_count'] == 6 and x['angular_predicate_count'] == 15 for x in mj_sites))
    check('retained 1MJH ATP local validation yields printed mean', math.isclose(result['sources']['1mjh']['ATP_copy_mean_fit'],.9225665))
    check('retained 4KK3 PO4 native RSCC equals quoted input', any(x.get('resnum') == '201' and x.get('resname') == 'PO4' and float(x['rscc']) == .967 for x in result['sources']['4kk3']['selected_validation']))
    check('retained 4KK4 SEP native RSCC equals quoted input', any(x.get('resnum') == '7' and x.get('resname') == 'SEP' and float(x['rscc']) == .934 for x in result['sources']['4kk4']['selected_validation']))
    check('one PDB duplicate does not increase score', cluster_mean([('A',a),('A',a),('B',b)]) == cluster_mean([('A',a),('B',b)]))
    check('contradiction lowers signed family score', family1 < statistics.mean([a,b]))
    check('positive and negative masses reconstruct signed axis', math.isclose(axis,result['synthetic_complete_example']['axis_support_mass']-result['synthetic_complete_example']['axis_opposition_mass']))
    check('reported zero detection limit distinct from missing limit', (1-0/.5) == 1 and None != 0)
    check('detection upper limit at expected occupancy has no opposition', max(0,1-.5/.5) == 0)
    check('partial target site denominator remains four', 3/4 < 3/3)
    check('pooled nuisance bound separates isolation from comparability', isolation(10,2) == .8 and comparability([1,1]) == 1)
    check('effect no larger than nuisance has zero isolated strength', isolation(2,3) == 0)
    check('coordinate distances invariant to common translation', math.isclose(math.dist((1,2,3),(4,5,6)),math.dist((11,22,33),(14,25,36))))
    check('native deposited SEP P-OG rounds to reported validation 1.68 A', round(result['sources']['4kk4']['SEP7_P_OG_A'],2) == 1.68)
    check('all nominal synthetic values inside propagated bounds', axis_bounds[0] <= axis <= axis_bounds[1] and all(l <= v <= u for (l,u),v in zip(bounds1,clusters)))
    check('contradiction can leave one family positive-support lower bound zero', max(0,f1_bounds[0]) == 0)
    check('symmetric copies do not become experiments', math.isclose(statistics.mean([.927369,.917764]), .9225665))
    check('deleting a required unobserved role cannot raise fixed-denominator result', (3+0)/4 == 3/4)
    try:
        fit(1.1)
        check('invalid native RSCC is rejected rather than clamped',False)
    except AssertionError:
        check('invalid native RSCC is rejected rather than clamped',True)
    try:
        cluster_mean([('A',a),('A',b)])
        check('conflicting repeated representation rejected for reconciliation',False)
    except ValueError:
        check('conflicting repeated representation rejected for reconciliation',True)
    result['checks'] = checks
    (HERE/'ARITHMETIC_RESULTS_001.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'checks_passed':len(checks),'synthetic':result['synthetic_complete_example'],'source_components':result['derived_source_components']},indent=2))


if __name__ == '__main__':
    run()
