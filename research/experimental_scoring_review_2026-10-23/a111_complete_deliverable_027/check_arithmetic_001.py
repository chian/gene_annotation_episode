"""Research arithmetic only. Reads cross-case receipts, never primary source files.

No production imports, model/native scientific jobs, or writes outside this directory.
All scoring transformations here are proposals. Source custody/extraction is credited
to the original researchers; recomputing their numerical outputs is not primary review.
"""
from pathlib import Path
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CHECKS = []


def check(name, truth):
    if not truth:
        raise AssertionError(name)
    CHECKS.append(name)


def near(name, actual, expected):
    check(name, math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-12))


def correlation_fit(panel):
    if not panel:
        raise ValueError('invalid_denominator')
    if any(v is not None and (not math.isfinite(v) or not -1 <= v <= 1) for v in panel):
        raise ValueError('invalid_range')
    known = [max(0, v)**2 for v in panel if v is not None]
    if None in panel:
        return {'point': None, 'bounds': [0, min(known, default=1)]}
    d = min(known)
    return {'point': d, 'bounds': [d, d]}


def noe(distances, bounds, tau=.5):
    if not distances or len(distances) != len(bounds) or tau <= 0:
        raise ValueError('invalid_denominator_or_scale')
    scores = []
    for d, (l, u) in zip(distances, bounds):
        if not 0 <= l <= u or (d is not None and d < 0):
            raise ValueError('invalid_range')
        v = None if d is None else max(0, l-d, d-u)
        scores.append(None if v is None else math.exp(-v*v/(2*tau*tau)))
    low = sum(x for x in scores if x is not None)/len(scores)
    high = low + scores.count(None)/len(scores)
    return {'point': None if None in scores else low, 'bounds': [low, high], 'scores': scores}


def product(*factors):
    if any(v is not None and not 0 <= v <= 1 for v in factors):
        raise ValueError('invalid_range')
    if 0 in factors:
        return 0.0  # Other operand nulls remain null in the input record.
    return None if None in factors else math.prod(factors)


def reduce_question(records):
    """Records contain current, simultaneous canonical observations, not model alternatives."""
    canonical = {}
    for r in records:
        if r.get('status', 'current') != 'current':
            continue
        key = (r['group'], r['observation'])
        value = (r['p'], r['o'])
        if key in canonical and canonical[key] != value:
            raise ValueError('conflicting_current_representations')
        canonical[key] = value
    group_values = {}
    for (g, _), (p, o) in canonical.items():
        if not 0 <= p <= 1 or not 0 <= o <= 1:
            raise ValueError('invalid_range')
        old = group_values.get(g, (0, 0))
        group_values[g] = (max(old[0], p), max(old[1], o))
    p = max((v[0] for v in group_values.values()), default=0)
    o = max((v[1] for v in group_values.values()), default=0)
    return {'P': p, 'O': o, 'Z': p-o, 'A': max(0, p-o),
            'groups': group_values, 'canonical_count': len(canonical)}


def record(name, p=0, o=0, group=None, status='current'):
    return dict(observation=name, group=group or name, p=p, o=o, status=status)


def copy_mean(rows):
    if not rows:
        raise ValueError('invalid_denominator')
    return tuple(sum(r[k] for r in rows)/len(rows) for k in (0, 1))


def aggregate(questions, weights):
    if len(questions) != len(weights) or not weights or any(w < 0 for w in weights):
        raise ValueError('invalid_weights')
    if not math.isclose(sum(weights), 1, abs_tol=1e-12):
        raise ValueError('invalid_weights')
    p = sum(w*q['P'] for w, q in zip(weights, questions))
    o = sum(w*q['O'] for w, q in zip(weights, questions))
    return {'P': p, 'O': o, 'Z': p-o, 'A': max(0, p-o)}


def row_interval(positive_bounds, opposition_bounds):
    p = [max((b[k] for b in positive_bounds), default=0) for k in (0, 1)]
    o = [max((b[k] for b in opposition_bounds), default=0) for k in (0, 1)]
    return {'P': p, 'O': o, 'Z': [p[0]-o[1], p[1]-o[0]]}


def main():
    paths = [BASE/'a111_structural_evidence_sheet_017/ARITHMETIC_RESULTS_001.json',
             BASE/'a111_native_modalities_021/ARITHMETIC_RESULTS_001.json',
             BASE/'a111_sheet_construction_001/parent_arithmetic_001.json']
    before = {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    core, native, parent = [json.loads(p.read_text()) for p in paths]

    # Recompute native-derived conversions from cross-case reviewer outputs only.
    atp = core['sources']['1mjh']['ATP_validation']
    atp_fit = statistics.mean(correlation_fit([float(x['rscc'])])['point'] for x in atp)
    near('reviewer ATP values reproduce proposed copy fit', atp_fit, .9225665)
    near('parent independent receipt agrees on ATP conversion', atp_fit, parent['source']['ATP_copy_mean_fit_proposal'])
    xray_source = {}
    for pdb, native_ligand, ligand_rscc, contact_rscc in [('4kk3','PO4',.967,.773),('4kk4','SEP',.934,.907)]:
        rows = core['sources'][pdb]['selected_validation']
        measured = next(float(r['rscc']) for r in rows if r['resname'] == native_ligand)
        near(pdb+' retained reviewer ligand value', measured, ligand_rscc)
        xray_source[pdb] = {'ligand_D': measured**2, 'contact_D': contact_rscc**2}
    em_source = []
    for source in native['cryoem_native']:
        fits = [correlation_fit(c['Q_score_by_endpoint'])['point'] for c in source['copies']]
        near(source['pdb']+' reviewer Q inputs reproduce copy mean', statistics.mean(fits), source['copy_mean_D'])
        em_source.append({'pdb': source['pdb'], 'copy_D': fits, 'mean_D': statistics.mean(fits)})
    nmr_source = []
    for source in native['nmr_native']:
        bounds = [(r['lower_A'], r['upper_A']) for r in source['restraints']]
        scenario_results = []
        for s in source['scenarios']:
            d = noe(s['distances_A'], bounds)['point']
            near(source['pdb']+' reviewer-derived scenario '+str(s['model']), d, s['D'])
            g = int(s['distances_A'][1] <= 4)
            scenario_results.append((d, d*g, d if g else -d))
        source_dg = [min(s[1] for s in scenario_results), max(s[1] for s in scenario_results)]
        for i in (0,1):
            near(source['pdb']+' source-support envelope '+str(i), source_dg[i], source['joint_D_G_range'][i])
        nmr_source.append({'pdb': source['pdb'], 'support_only_DG': source_dg,
                           'if_le4_support_gt4_opposition_signed': [min(x[2] for x in scenario_results), max(x[2] for x in scenario_results)]})

    # Full synthetic X-ray observations: exact original factors, explicit new reducer.
    xa = product(.8, .95**2, 5/6, 3/4, .9, .9)
    xb = product(.75, .9**2, 1, .5, .95, 1)
    xc = product(1-.1/.5, .9**2, 1, .75, 1, 1)
    xd = product(.6, .8**2, 1, .5, 1, 1)
    x_rows = [record('XA',xa),record('XB',xb),record('XC',o=xc)]
    x = reduce_question(x_rows)
    interface = reduce_question([record('XD',xd)])
    old_x = ((xa+xb-xc)/3+xd)/2
    new_x = aggregate([x, interface],[.5,.5])
    near('old two-family arithmetic preserved as history', old_x, .1240125)
    near('new two-family arithmetic', new_x['Z'], .03575625)
    near('zero-row old denominator counterexample', xa/2, .18275625)

    # Complete EM panel has explicit support and opposition on all four constraints.
    c = math.exp(-.0625)
    em_rows = []
    em_copy_details = []
    for qs, distances in [([.8,.9],[2.8,3.0,3.2,4.2]),([.7,.95],[2.8,3.0,3.2,3.4])]:
        d = correlation_fit(qs)['point']
        gp = sum(2.5 <= y <= 3.5 for y in distances)/4
        go = sum(y >= 4 for y in distances)/4
        p,o = (product(.75,d,g,.75,c,.8) for g in (gp,go))
        em_rows.append((p,o))
        em_copy_details.append({'Q':qs,'distances_A':distances,'D':d,'G_plus':gp,'G_minus':go,'P':p,'O':o})
    em_one = copy_mean(em_rows)
    em_two = (0,product(.5,.6**2,1,.75,1,1))
    em = reduce_question([record('E1',*em_one),record('E2',*em_two)])
    near('EM positive complete-product copy mean', em['P'], .20502690095904114)
    near('EM mixed copy opposing component retained', em_one[1], .033818870261285125)
    near('EM current signed score', em['Z'], .07002690095904114)

    # Complete NMR panel: <=5 supports, >5 opposes for each of two contacts.
    nd1 = noe([4,5.5],[(0,4),(0,5)])['point']
    nd2 = noe([5.25,6.75],[(0,5),(0,6)])['point']
    n1 = product(1,nd1,.5,2/3,1,1)
    n2 = product(1,nd2,1,2/3,1,1)
    nmr = reduce_question([record('N1',n1,n1),record('N2',o=n2)])
    near('NMR mixed first observation preserves opposition', n1, .26775510995210555)
    near('NMR current signed score', nmr['Z'], -.13462801336220948)
    check('negative NMR remains negative with nonnegative support zero', nmr['Z'] < 0 and nmr['A'] == 0)

    ha = aggregate([x,interface,em,nmr],[.25]*4)
    reverse = lambda q: {'P':q['O'],'O':q['P']}
    hb = aggregate([x,interface,reverse(em),reverse(nmr)],[.25]*4)
    delta = ha['Z']-hb['Z']
    near('candidate A complete four-family score', ha['Z'], .0017278468992079146)
    near('candidate B complete four-family score', hb['Z'], .0340284031007921)
    near('shared structural evidence cancels in candidate contrast', delta, (em['Z']+nmr['Z'])/2)

    x_bounds = row_interval([[.145807725,.764246025],[.2317392,.33856]],[[.40656,.57132]])
    d_bounds = [.1521,.23534]
    x_two_bounds = [(x_bounds['Z'][k]+d_bounds[k])/2 for k in (0,1)]
    ha_bounds = [(x_bounds['Z'][k]+d_bounds[k]+em['Z']+nmr['Z'])/4 for k in (0,1)]
    hb_bounds = [(x_bounds['Z'][k]+d_bounds[k]-em['Z']-nmr['Z'])/4 for k in (0,1)]
    near('max interval lower uses B rather than lower A', x_bounds['P'][0], .2317392)
    near('max interval upper uses A', x_bounds['P'][1], .764246025)
    check('two-family lower can be negative', x_two_bounds[0] < 0)
    check('candidate nominal values lie in declared envelopes', ha_bounds[0] <= ha['Z'] <= ha_bounds[1] and hb_bounds[0] <= hb['Z'] <= hb_bounds[1])
    for xa_v,xb_v,xc_v,xd_v in itertools.product(*[[.145807725,.764246025],[.2317392,.33856],[.40656,.57132],d_bounds]):
        xq=reduce_question([record('XA',xa_v),record('XB',xb_v),record('XC',o=xc_v)])
        dq=reduce_question([record('XD',xd_v)])
        av=aggregate([xq,dq,em,nmr],[.25]*4)
        bv=aggregate([xq,dq,reverse(em),reverse(nmr)],[.25]*4)
        near('joint candidate contrast invariant across shared-bound corner',av['Z']-bv['Z'],delta)

    # Algebraic invariants and their deliberate limits.
    same_components = lambda a,b: all(math.isclose(a[k],b[k],abs_tol=1e-12) for k in ('P','O','Z','A'))
    check('zero new group cannot dilute score', same_components(x,reduce_question(x_rows+[record('zero')])) )
    check('zero in existing group cannot dilute score', same_components(x,reduce_question(x_rows+[record('zero2',group='XA')])) )
    check('duplicate representation cannot alter score', same_components(x,reduce_question(x_rows+[x_rows[0]]*7)))
    check('weaker independent positive replicate cannot alter maximum', same_components(x,reduce_question(x_rows+[record('weak',.1)])))
    stronger = reduce_question(x_rows+[record('strong',.5)])
    check('stronger independent support can increase score',stronger['Z'] > x['Z'])
    check('new stronger opposition can decrease score', reduce_question(x_rows+[record('opposition',o=.7)])['Z'] < x['Z'])
    revised = reduce_question([record('fitA',xa,status='historical'),record('fitA',.2)])
    near('superseded stronger fit is not retained by maximum',revised['P'],.2)
    try:
        reduce_question([record('same',.2),record('same',.3)])
    except ValueError:
        CHECKS.append('conflicting current representations require reconciliation')
    else:
        raise AssertionError('accepted inconsistent same-identity values')
    # Alternative conformers are mutually exclusive full reductions, never simultaneous P/O maxima.
    alternatives = [reduce_question([record('same-data',.6)]),reduce_question([record('same-data',o=.4)])]
    alternative_bounds = [min(r['Z'] for r in alternatives),max(r['Z'] for r in alternatives)]
    check('same-dataset alternatives produce signed envelope',alternative_bounds==[-.4,.6])
    near('actually measured state weights combine complete P/O',.7*.4-.3*.2,.22)
    check('empty inventory gives zero documented support, not experimental absence',same_components(reduce_question([]),{'P':0,'O':0,'Z':0,'A':0}))
    check('known zero annihilates unknown product without filling unknown operand',product(None,.8,1,0,.9,None)==0)
    check('unresolved nonzero chain remains null',product(None,.8,1,.5,.9,1) is None)
    missing_q=correlation_fit([.8,None])
    near('missing EM endpoint retains upper bound',missing_q['bounds'][1],.64)
    check('missing EM endpoint stays null',missing_q['point'] is None)
    missing_noe=noe([4.5,None],[(0,4),(0,5)])
    near('missing NOE lower preserves denominator',missing_noe['bounds'][0],math.exp(-.5)/2)
    near('missing NOE upper preserves denominator',missing_noe['bounds'][1],(math.exp(-.5)+1)/2)
    check('missing NOE stays null',missing_noe['point'] is None)
    for label, operation in [('invalid Q',lambda:correlation_fit([1.1])),('empty Q',lambda:correlation_fit([])),('empty NOE',lambda:noe([],[])),('zero tau',lambda:noe([3],[(0,4)],0)),('invalid weight sum',lambda:aggregate([x],[.5]))]:
        try: operation()
        except ValueError: CHECKS.append(label+' rejected')
        else: raise AssertionError(label)
    near('native R-6 calculation',((3**-6+10**-6)/2)**(-1/6),3.366977181405646)
    near('native SUM calculation',(3**-6+10**-6)**(-1/6),2.9996356549220624)
    near('calibrated nondetection gap',max(0,1-.1/.5),.8)
    check('unrevealing detection limit is zero opposition',max(0,1-.6/.5)==0)
    near('separate comparability for source example',math.prod([math.exp(-1.5**2/2),math.exp(-.5**2/2),146/151,1])**.25,.7254825177509818)
    # Split a fixed question into aliases only while conserving weight.
    near('question split conserves contribution',aggregate([x,x],[.3,.7])['Z'],x['Z'])
    after={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    check('three retained input receipts unchanged',before==after)

    result={'status':'research_proposal_only','checks_passed':len(CHECKS),'checks':CHECKS,
            'reused_inputs_sha256':before,'source_recalculation_scope':'cross-case receipts only; no primary-source extraction',
            'source_derived':{'ATP_D_copy_mean':atp_fit,'YwlE':xray_source,'cryoEM':em_source,'NMR':nmr_source},
            'synthetic':{'Xray_rows':[xa,xb,-xc,xd],'Xray_feature':x,'Xray_interface':interface,'Xray_two_family':new_x,'old_Xray_two_family':old_x,
                         'EM_copies':em_copy_details,'EM_observation_E1':em_one,'EM_observation_E2':em_two,'EM_result':em,
                         'NMR_D':[nd1,nd2],'NMR_result':nmr,'candidate_A':ha,'candidate_B':hb,'candidate_A_minus_B':delta,
                         'Xray_feature_bounds':x_bounds,'Xray_two_family_bounds':x_two_bounds,'candidate_A_bounds':ha_bounds,'candidate_B_bounds':hb_bounds,
                         'shared_input_candidate_contrast_bounds':[delta,delta], 'alternative_conformer_signed_bounds':alternative_bounds,
                         'missing_Q':missing_q,'missing_NOE':missing_noe}}
    with (HERE/'ARITHMETIC_RESULTS_001.json').open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'checks_passed':len(CHECKS),'candidate_A':ha,'candidate_B':hb,'delta':delta,'written':'ARITHMETIC_RESULTS_001.json'},indent=2))


if __name__=='__main__': main()
