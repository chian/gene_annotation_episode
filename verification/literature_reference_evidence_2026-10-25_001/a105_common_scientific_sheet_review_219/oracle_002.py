"""Root source cross-check and explicitly conditional numerical design oracles.

Research verification only: no production calculator, model, episode or credit.
"""
from pathlib import Path
from html.parser import HTMLParser
from fractions import Fraction as F
from decimal import Decimal, localcontext
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent
ROOT = Path('/home/chia/repos/gene_annotation_episode')
CASE = ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_scoring_case_207'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(CASE/'primary_read_001.txt') == '96f9df15eae2737c6ebe31e808f1599cfcdda92fdfcc4db6ffb617fe95d9a02c'
assert digest(CASE/'acquisition_001.bin') == 'fe5ba79bc3152f6d94f730cc7e02b43c041fbcb5092afa434386ba3c60c2e7de'

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables=[]; self.table=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table':
            assert self.table is None
            self.table=[]
        elif self.table is not None and tag=='tr': self.row=[]
        elif self.row is not None and tag in ('td','th'): self.cell=[]
    def handle_data(self,data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(re.sub(r'\s+',' ',' '.join(self.cell)).strip()); self.cell=None
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row); self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table); self.table=None

parser=Tables(); parser.feed((CASE/'acquisition_001.bin').read_text())
def table_containing(*headers):
    selected=[t for t in parser.tables if all(re.sub(r'\s+','',h) in re.sub(r'\s+','', ' '.join(' '.join(r) for r in t)) for h in headers)]
    assert len(selected)==1,(headers,len(selected))
    return selected[0]
kinetic=table_containing('kcat','Km')
coupling=table_containing('NADH consumption','Coupling efficiency')
binding=table_containing('Kd','Camphor')
def row(table,name):
    selected=[r for r in table if r and (r[0]==name or name=='Wild-type' and r[0].startswith('Wild-type'))]
    assert len(selected)==1,(name,selected)
    return selected[0]
native={
    'Wild-type':dict(P=206,H=289,kcat=124,Km=30,Kd='1.8',Kd_spread='0.1'),
    'T252N':dict(P=92,H=216,kcat=54,Km=96,Kd=34,Kd_spread=2),
    'T252N/V253T':dict(P=132,H=343,kcat=165,Km=388,Kd=12,Kd_spread=1),
    'T252A':dict(P=0,H=427,kcat=None,Km=None,Kd='2.9',Kd_spread='0.2'),
}
source_rows={}
for name,d in native.items():
    cr,kr,br=row(coupling,name),row(kinetic,name),row(binding,name)
    assert F(cr[1])==d['P'] and F(cr[2])==d['H'],cr
    if d['kcat'] is None:
        assert all(value.startswith('ND') for value in kr[1:3]),kr
    else:
        assert F(kr[1].split('±')[0])==d['kcat'] and F(kr[2].split('±')[0])==d['Km'],kr
    centre,spread=br[1].split('±')
    assert F(centre.strip())==F(str(d['Kd'])) and F(spread.strip())==F(str(d['Kd_spread'])),br
    source_rows[name]={'table2':kr,'table3':cr,'table4':br}
primary=(CASE/'primary_read_001.txt').read_text()
assert 'camphor (2 mM)' in primary and 'a specified amount of the substrate' in primary
assert 'Each point represents the mean ± SD of a triplicate assay' in primary
assert 'negligible' in primary and 'Not detected' in primary

def encoded(q): return {'numerator':str(q.numerator),'denominator':str(q.denominator),'display':float(q)}
def dec(q): return Decimal(q.numerator)/Decimal(q.denominator)
wt=native['Wild-type']; S=F(2000); result={}
for name in ('T252N','T252N/V253T'):
    d=native[name]; P,Q=F(d['P']),F(wt['P']); kt,kr=F(str(d['Kd'])),F(str(wt['Kd']))
    rp=P/Q; theta=S/(S+kt); theta_wt=S/(S+kr); rt=theta/theta_wt
    residual=rp/rt
    # Invert the same stated model, WITHOUT treating the inferred S as measured.
    matching_S=(rp*kt-kr)/(1-rp)
    assert matching_S>0 and (matching_S+kr)/(matching_S+kt)==rp
    j=(1/P,-1/Q,1/(S+kt),-1/(S+kr),1/(S+kt)-1/(S+kr))
    with localcontext() as context:
        context.prec=75
        values=list(map(dec,(P,Q,kt,kr,S))); epsilon=Decimal('1e-8')
        def log_residual(v):
            p,q,k,l,s=v
            return p.ln()-q.ln()+(s+k).ln()-(s+l).ln()
        for index,expected in enumerate(j):
            high=values.copy(); low=values.copy()
            high[index]+=epsilon; low[index]-=epsilon
            observed=(log_residual(high)-log_residual(low))/(2*epsilon)
            assert abs(observed-dec(expected))<Decimal('1e-18'),(index,observed,expected)
        # Explicitly synthetic joint-error modes: this is NOT paper covariance.
        modes=((F(1),F('0.5'),F(2),F('0.1'),F(20)),
               (F('-0.2'),F('0.4'),F(1),F('0.3'),F(-10)))
        synthetic_variance=sum(sum(a*b for a,b in zip(j,mode))**2 for mode in modes)
        fd_variance=Decimal(0)
        for mode in modes:
            high=[v+epsilon*dec(m) for v,m in zip(values,mode)]
            low=[v-epsilon*dec(m) for v,m in zip(values,mode)]
            fd_variance+=((log_residual(high)-log_residual(low))/(2*epsilon))**2
        assert abs(fd_variance-dec(synthetic_variance))<Decimal('1e-20')
        log_value=str(log_residual(values))
    result[name]={
        'product_contrast':encoded(rp),
        'saturation_turnover_contrast':encoded(F(d['kcat'],wt['kcat'])),
        'low_substrate_efficiency_contrast':encoded(F(d['kcat'],d['Km'])/F(wt['kcat'],wt['Km'])),
        'conditional_theta_at_stipulated_free_S_2000_uM':encoded(theta),
        'conditional_occupancy_contrast':encoded(rt),
        'conditional_prediction_error':encoded(rp-rt),
        'conditional_residual_ratio':encoded(residual),
        'conditional_log_residual':log_value,
        'conditional_binding_only_matching_free_S_uM_NOT_observed':encoded(matching_S),
        'log_residual_primitive_order':['P_test','P_reference','Kd_test','Kd_reference','shared_free_S'],
        'log_residual_gradient_exact':[encoded(v) for v in j],
        'all_five_derivatives_independently_checked':True,
        'synthetic_error_mode_variance_exact':encoded(synthetic_variance),
        'synthetic_variance_checked_by_directional_finite_differences':True,
        'source_reported_residual_covariance':None,'source_standardized_residual':None,
    }
payload={'scope':'Root independently transcribed primary-table values and conditional design arithmetic; no production/model/integration/credit claim',
    'source_sha256':{'primary_text':digest(CASE/'primary_read_001.txt'),'original_html':digest(CASE/'acquisition_001.bin')},
    'source_rows':source_rows,'numeric_scenario_origin':'proposed sensitivity using source central estimates; fixed free S=2000uM is not established for product assay',
    'results':result,'limits':['No observed product substrate concentration or binding/catalysis applicability supplied','No source Table3 or joint estimate covariance','Table4 plus-minus semantics unspecified','No zero/LOD for nondetection','No active fraction/background/recovery/nuisance corrections invented','Kd unsupported by current kinetic-reader contract; no relabeling as Km']}
with (BASE/'ROOT_NUMERICAL_ORACLES_001.json').open('x') as f:json.dump(payload,f,indent=2);f.write('\n')
print(json.dumps({'source_tables_cross_checked':3,'source_arms':4,'conditional_results':{k:{n:v[n] for n in ['product_contrast','conditional_occupancy_contrast','conditional_residual_ratio','conditional_binding_only_matching_free_S_uM_NOT_observed']} for k,v in result.items()},'all_derivative_checks_pass':True},indent=2))
