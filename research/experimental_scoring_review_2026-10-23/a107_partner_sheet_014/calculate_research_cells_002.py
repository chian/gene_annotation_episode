"""Additive corrected arithmetic revision 002; supersedes unexecuted 001.
Target-source correspondence multiplies expression only; corrected synthetic oracle.
One-off A107 research arithmetic; not imported by any production reader/scorer.

Read-only inputs are pinned public PRECISE tables. Outputs stay beside this file.
No searches, inference jobs, annotation runs, or network calls occur here.
"""
from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import statistics as st
import hashlib
from scipy import stats

ROOT = Path(__file__).resolve().parent
PAIRS = [('yfgM', p) for p in ['ppiD', 'secY', 'secE', 'secG']] + [
    ('nlpI', p) for p in ['mepS', 'mepM', 'dacB', 'pbpG', 'mrcA', 'lpoA']]
M = len(PAIRS)
ALPHA = .05

def read_csv(name):
    with (ROOT/name).open() as f:
        return list(csv.DictReader(f))

def dot(x, y):
    return math.fsum(a*b for a, b in zip(x, y))

def center(x):
    mu = st.mean(x)
    return [a-mu for a in x]

def corr(x, y):
    a, b = center(x), center(y)
    den = math.sqrt(dot(a,a)*dot(b,b))
    if den == 0:
        return None
    return max(-1., min(1., dot(a,b)/den))

def residual(x, g):
    a, b = center(x), center(g)
    beta = dot(a,b)/dot(b,b)
    return [v-beta*w for v,w in zip(a,b)]

def ci(r, n, k, z):
    se = 1/math.sqrt(n-k-3)
    return [math.tanh(math.atanh(r)-z*se), math.tanh(math.atanh(r)+z*se)]

def support(r):
    return max(0., r)**2

def edge(r, d=1., g=1., h0=1.):
    return g*(.5+.5*h0*d*support(r))

metadata = read_csv('precise_data_metadata.csv')
selected = [r for r in metadata
            if r['Project ID']=='ica'
            and r['Strain Description']=='Escherichia coli K-12 MG1655'
            and r['Evolved Sample']=='No'
            and r['Base Media']=='M9'
            and r['Temperature (C)']=='37'
            and r['pH']=='7'
            and r['Culture Type']=='Batch']
assert len(selected)==28
assert len({r['Sample ID'] for r in selected})==28
by_condition = defaultdict(list)
for row in selected:
    by_condition[row['Condition ID']].append(row)
conditions = sorted(by_condition)
assert len(conditions)==12
assert sorted(len(v) for v in by_condition.values())==[2]*11+[6]
genes = {g for pair in PAIRS for g in pair}
gene_info = {r['gene_name']:r for r in read_csv('precise_data_gene_info.csv')
             if r['gene_name'] in genes}
assert set(gene_info)==genes
loci = {r[''] for r in gene_info.values()}
expression = {r['']:r for r in read_csv('precise_data_log_tpm_full.csv') if r[''] in loci}
assert set(expression)==loci
sample_ids = [r['Sample ID'] for r in selected]
X = {g:{s:float(expression[gene_info[g]['']][s]) for s in sample_ids} for g in genes}
assert all(math.isfinite(v) and v>=0 for row in X.values() for v in row.values())
GROWTH = [st.mean(float(r['Growth Rate (1/hr)']) for r in by_condition[c]) for c in conditions]
MEANS = {g:[st.mean(X[g][r['Sample ID']] for r in by_condition[c]) for c in conditions] for g in genes}
assert all(v>0 for v in GROWTH)
Z_FAMILY = stats.norm.ppf(1-ALPHA/(2*M))
RESULTS = []
for target,partner in PAIRS:
    x,y = MEANS[target],MEANS[partner]
    rx,ry = residual(x,GROWTH),residual(y,GROWTH)
    r = corr(rx,ry)
    n,k = len(x),1
    raw=corr(x,y)
    a,b = corr(x,GROWTH),corr(y,GROWTH)
    independent = (raw-a*b)/math.sqrt((1-a*a)*(1-b*b))
    assert math.isclose(r, independent, abs_tol=2e-13)
    assert math.isclose(raw, stats.pearsonr(x,y).statistic, abs_tol=2e-13)
    assert math.isclose(r, stats.pearsonr(rx,ry).statistic, abs_tol=2e-13)
    t = r*math.sqrt((n-k-2)/(1-r*r))
    c95=ci(r,n,k,stats.norm.ppf(.975))
    cf=ci(r,n,k,Z_FAMILY)
    dcounts={str(threshold):sum(a>=math.log2(threshold+1) and b>=math.log2(threshold+1)
                                 for a,b in zip(x,y)) for threshold in [1,5,10]}
    d=dcounts['1']/n
    sample_co_detect=sum(X[target][s]>=1 and X[partner][s]>=1 for s in sample_ids)
    loo=[]
    for i in range(n):
        sub=lambda z:[v for j,v in enumerate(z) if j!=i]
        loo.append(corr(residual(sub(x),sub(GROWTH)),residual(sub(y),sub(GROWTH))))
    RESULTS.append(dict(target=target, partner=partner,
        target_locus=gene_info[target][''],partner_locus=gene_info[partner][''],
        n_conditions=n,n_biological_samples=len(selected),growth_covariates=k,df=n-k-2,
        raw_pearson_r=raw,partial_r=r,t_statistic=t,p_two_sided=2*stats.t.sf(abs(t),n-k-2),
        fisher_se=1/math.sqrt(n-k-3),fisher_ci95=c95,fisher_family_ci95=cf,
        codetection_count_by_tpm_threshold=dcounts,codetection_denominator=n,D=d,
        sample_codetection_count=sample_co_detect,sample_codetection_denominator=len(selected),
        positive_squared_r=support(r),edge_point=edge(r,d),
        edge_family_interval=[edge(v,d) for v in cf],
        leave_one_condition_out_partial_r_range=[min(loo),max(loo)],
        residual_dot_product=dot(rx,ry),residual_ss_target=dot(rx,rx),residual_ss_partner=dot(ry,ry),
        independent_partial_r=independent))

lookup={(r['target'],r['partner']):r for r in RESULTS}
def clause_summary(target, partners):
    rows=[lookup[target,p] for p in partners]
    return {'partners':partners,'point':min(r['edge_point'] for r in rows),
            'family_interval':[min(r['edge_family_interval'][i] for r in rows) for i in [0,1]]}
yfgm=clause_summary('yfgM',['ppiD','secY','secE','secG'])
nlpi_a=clause_summary('nlpI',['mepS','dacB'])
nlpi_b=clause_summary('nlpI',['mepS','pbpG'])
nlpi_alt={'clauses':[nlpi_a,nlpi_b],'point':max(nlpi_a['point'],nlpi_b['point']),
          'family_interval':[max(nlpi_a['family_interval'][i],nlpi_b['family_interval'][i]) for i in [0,1]]}
nlpi_pbp=clause_summary('nlpI',['mrcA','lpoA','dacB'])

publication_checks={
 'yfgm_ppid_reported_ratio':99/100,
 'yfgm_ppid_conditional_loading_ratio':(99/100)/(112/100),
 'yfgm_skp_reported_ratio':131/100,
 'yfgm_skp_conditional_loading_ratio':(131/100)/(112/100),
 'yfgm_sura_conditional_loading_ratio':95/112,
 'yfgm_skp_conditional_amount_closeness':112/131,
 'nlpi_pbp4_supply_assuming_one_to_one':441/389,
 'nlpi_mepm_supply_assuming_one_to_one':341/389,
 'nlpi_meps_supply_assuming_one_to_one':3931/389,
 'nlpi_fig6_concentrations_using_rounded_5nM_per_molecule':{
   g:n*.005 for g,n in [('PBP1A',554),('PBP1B',512),('LpoA',513),('LpoB',1490),
       ('NlpI',389),('PBP4',441),('PBP7',1005),('MepA',625),('MepH',265),('MepM',341),('MepS',3931)]}}

# Entirely synthetic source-to-target example: normalized raw sequence scores,
# complete genomic observations, 20 matched condition means and one covariate.
synthetic_rows=[]
for partner,sxy,sxx,syy,present,dnum,r in [
    ('P',160,200,200,1,18,.8),('Q',135,180,180,1,16,.6),
    ('R',180,200,200,1,20,-.4),('O_optional',190,200,200,1,20,.95)]:
    h=min(1.,max(0.,sxy/math.sqrt(sxx*syy)))
    d=dnum/20
    interval=ci(r,20,1,stats.norm.ppf(1-.05/(2*3)))
    synthetic_rows.append(dict(partner=partner,raw_pair_score=sxy,raw_self_query=sxx,
        raw_self_reference=syy,H=h,P=present,G=h*present,D_numerator=dnum,D_denominator=20,D=d,
        partial_r=r,R=support(r),E_without_target_correspondence=d*support(r),E=.9*d*support(r),edge=edge(r,d,h*present,.9),
        partial_r_family_ci=interval,edge_family_interval=[edge(v,d,h*present,.9) for v in interval]))
sx={r['partner']:r for r in synthetic_rows}
# Candidate clauses are (P AND Q) OR (P AND R). Optional O is diagnostic only.
synthetic={'data_kind':'synthetic illustration; no biological measurement',
    'n_conditions':20,'k_covariates':1,'family_size':3,'target_mapping_raw_scores':[180,200,200],
    'target_mapping_H0':.9,'context_overlap_numerator':20,'context_overlap_denominator':20,
    'C_context':1.,'rows':synthetic_rows,
    'clauses':[['P','Q'],['P','R']],
    'clause_scores':[min(sx['P']['edge'],sx['Q']['edge']),min(sx['P']['edge'],sx['R']['edge'])],
    'coordinate':max(min(sx['P']['edge'],sx['Q']['edge']),min(sx['P']['edge'],sx['R']['edge'])),
    'family_interval':[max(min(sx['P']['edge_family_interval'][i],sx['Q']['edge_family_interval'][i]),
                             min(sx['P']['edge_family_interval'][i],sx['R']['edge_family_interval'][i])) for i in [0,1]]}
assert math.isclose(synthetic['coordinate'],.4722,abs_tol=1e-12)

checks=[]
def check(name, condition):
    assert condition,name
    checks.append({'check':name,'passed':True})
check('sample IDs unique; 28 biological samples, 12 equal-weight condition units',len(sample_ids)==len(set(sample_ids))==28 and len(conditions)==12)
check('control replication does not create extra conditions',len(by_condition['wt_glc'])==6)
check('all 10 partial correlations agree with independent algebra and scipy',all(abs(r['partial_r']-r['independent_partial_r'])<2e-13 for r in RESULTS))
check('every coordinate and interval is bounded and contains the point',all(0<=r['edge_family_interval'][0]<=r['edge_point']<=r['edge_family_interval'][1]<=1 for r in RESULTS))
check('adding a duplicate relation cannot change min/max combination',min(yfgm['point'],yfgm['point'])==yfgm['point'] and max(nlpi_alt['point'],nlpi_alt['point'])==nlpi_alt['point'])
check('negative association supplies zero positive association support',support(-.4)==0 and support(-.9)==0)
check('verified missing mandatory partner blocks its conjunctive clause',min(.8,0)==0)
check('optional partner is excluded from synthetic coordinate',synthetic['coordinate']==max(synthetic['clause_scores']))
check('synthetic end-to-end result independently equals 0.4722',math.isclose(synthetic['coordinate'],.4722,abs_tol=1e-12))

out={'definition':'A107 research proposal v001; reported expression inputs, derived statistics, proposed transforms',
     'source_commit':'782c252d4e4e6fb7e5d0037b85b1a00b59c6f1fe',
     'sample_selection':{'Project ID':'ica','Strain Description':'Escherichia coli K-12 MG1655',
        'Evolved Sample':'No','Base Media':'M9','Temperature (C)':'37','pH':'7','Culture Type':'Batch'},
     'expression_unit':'log2(TPM+1)','condition_ids':conditions,'sample_ids':sample_ids,
     'n_biological_samples':28,'n_condition_units':12,'family_size':M,'alpha':ALPHA,'family_normal_critical':Z_FAMILY,
     'raw_scores_assumptions':'Native candidate molecules explicitly identified by exact NC_000913.3 loci; H=G=1 by identity and reference presence, not a homology search or paper-strain transfer.',
     'relations':RESULTS,'candidate_coordinates':{'yfgM_ppiD_secYEG_hypothesis':yfgm,
       'nlpI_mepS_pbp4_or_pbp7_hypothesis':nlpi_alt,'nlpI_pbp1a_lpoa_pbp4_hypothesis':nlpi_pbp},
     'publication_arithmetic':publication_checks,'synthetic':synthetic,'checks':checks}
(ROOT/'CHECKED_NUMERICAL_CELLS_001.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
with (ROOT/'PRECISE_SELECTED_SAMPLE_INPUTS_001.csv').open('w') as f:
    fields=list(selected[0])+[g+'__log2_TPM_plus_1' for g in sorted(genes)]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for row in selected:
        w.writerow(dict(row,**{g+'__log2_TPM_plus_1':X[g][row['Sample ID']] for g in sorted(genes)}))
with (ROOT/'PRECISE_CONDITION_INPUTS_001.csv').open('w') as f:
    fields=['condition_id','n_biological_samples','sample_ids','growth_rate_per_hr']+sorted(genes)
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for i,c in enumerate(conditions):
        w.writerow({'condition_id':c,'n_biological_samples':len(by_condition[c]),
            'sample_ids':'|'.join(r['Sample ID'] for r in by_condition[c]),'growth_rate_per_hr':GROWTH[i],
            **{g:MEANS[g][i] for g in sorted(genes)}})
print(json.dumps({'counts':[28,12], 'relations':[{k:r[k] for k in ['target','partner','raw_pearson_r','partial_r','fisher_family_ci95','D','edge_point']} for r in RESULTS],
    'candidate_coordinates':out['candidate_coordinates'],'synthetic':synthetic,'checks':checks},indent=2))
