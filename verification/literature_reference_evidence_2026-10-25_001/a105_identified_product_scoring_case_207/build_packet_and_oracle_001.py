"""Source-case research only: original-byte packet plus independent rational math.
No production imports, model calls, source acquisition or episode/controller work.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, localcontext
import hashlib,html,json,re
BASE=Path(__file__).resolve().parent
raw=(BASE/'acquisition_001.bin').read_bytes()
text=raw.decode('utf8')
sha=hashlib.sha256(raw).hexdigest()
ref='original_public_html_sha256:'+sha

def span(start,end):
    s=len(text[:start].encode('utf8'));e=len(text[:end].encode('utf8'))
    q=text[start:end]
    assert raw[s:e]==q.encode('utf8')
    return {'artifact_ref':ref,'representation':'original','start':s,'end':e,'quote':q}

def visible(s):
    return html.unescape(re.sub('<[^>]*>','',s))

paragraphs={}
for label in ('P4','P7','P8','P9','P10','P11','P12','P13','P14','P16','P17','P18','P19','P20','P25','P26','P27','P28'):
    m=re.search(r'<p[^>]*id="'+label+r'"[^>]*>',text)
    assert m,label
    end=text.index('</p>',m.end())+4
    paragraphs[label]={'witness':span(m.start(),end),'visible_text':visible(text[m.start():end])}

tables={}
for label in ('T1','T2','T3','T4'):
    m=re.search(r'<section[^>]*id="'+label+r'"[^>]*>',text);assert m,label
    end=text.index('</section>',m.end())+10
    block=text[m.start():end]
    rows=[]
    for r in re.finditer(r'<tr\b[^>]*>.*?</tr>',block,re.S):
        cells=[]
        for c in re.finditer(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',r.group(),re.S):
            a=m.start()+r.start()+c.start(1);b=m.start()+r.start()+c.end(1)
            cells.append({'visible_text':visible(c.group(1)).strip(),'witness':span(a,b)})
        rows.append({'cells':cells,'witness':span(m.start()+r.start(),m.start()+r.end())})
    tables[label]={'witness':span(m.start(),end),'rows':rows}

r3=[r for r in tables['T3']['rows'] if r['cells'] and r['cells'][0]['visible_text'] in ('Wild-type','T252N','T252N/V253T','T252A')]
assert len(r3)==4
roles=['product_activity','nadh_consumption_activity','peroxide_activity','inferred_water_activity','reported_coupling_percent']
expected={'Wild-type':['206','289','0','42','71'],'T252N':['92','216','0','62','42'],'T252N/V253T':['132','343','0','106','38'],'T252A':['0','427','33','197','0']}
source_rows=[];oracle=[]
for row in r3:
    name=row['cells'][0]['visible_text'];cells=row['cells'][1:]
    assert [c['visible_text'] for c in cells]==expected[name]
    quantities={role:{'raw_number':c['visible_text'],'native_value':int(c['visible_text']),
        'unit':'percent' if role=='reported_coupling_percent' else 'min^-1',
        'origin':'reported' if role!='inferred_water_activity' else 'reported_calculated',
        'witness':c['witness']} for role,c in zip(roles,cells)}
    P,H,R,W,C=[F(c['visible_text']) for c in cells]
    eta=P/H;water=(H-R-P)/2
    def show(x):return {'exact_numerator':str(x.numerator),'exact_denominator':str(x.denominator),'value':float(x)}
    with localcontext() as ctx:
        ctx.prec=70
        d=Decimal(int(P))/Decimal(int(H))
        assert abs(d-Decimal(eta.numerator)/Decimal(eta.denominator))<Decimal('1e-68')
        w=(Decimal(int(H))-Decimal(int(R))-Decimal(int(P)))/2
        assert w==Decimal(water.numerator)/Decimal(water.denominator)
    row_key='source_Table3_row:'+name
    source_rows.append({'subject':name,'quantities':quantities,
       'product_semantics':'source_printed_zero_negligible_or_not_detected_unknown_limit' if P==0 else 'positive_reported_turnover',
       'peroxide_semantics':'source_printed_zero_not_detected_unknown_limit' if R==0 else 'positive_reported_turnover',
       'source_pair_relationship':'author_assigned_same_Table3_row',
       'same_physical_aliquot':'unknown','same_preparation':'unknown',
       'complete_matched_time_substrate_and_NADH_conditions':'unknown',
       'normalization':'reported_min^-1_associated_with_reconstituted_P450; precise_amount_quantification_and_active_fraction_unknown',
       'row_key':row_key,'witness':row['witness']})
    oracle.append({'subject':name,'diagnostic_displayed_ratio':show(eta),
       'displayed_ratio_percent':show(eta*100),'native_reported_percent':int(C),
       'displayed_minus_reported_percentage_points':show(eta*100-C),
       'diagnostic_water_from_displayed_operands':show(water),
       'native_reported_water':int(W),'water_reported_minus_displayed_formula':show(W-water),
       'cofactor_times_displayed_ratio':show(H*eta),
       'cofactor_times_reported_percent':show(H*C/100),
       'reported_percent_reconstruction_minus_reported_product':show(H*C/100-P),
       'physical_product_rate':'unknown_limit_nondetection; no exactzero' if P==0 else 'positive_source_report',
       'physical_coupling':'unavailable_nondetection_limit_unknown' if P==0 else 'source_pair_estimate_with_unresolved_detailed_matching',
       'uncertainty':None,'dependency_group':row_key,
       'diagnostic_numerical_closure':show(P+R+2*water-H),
       'closure_independent_check':False})
packet={'paper':{'title':'Efficient Catalytic Turnover of Cytochrome P450cam is Supported by a T252N Mutation','pmcid':'PMC2577879','doi':'10.1016/j.abb.2008.02.044','url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2577879/','original_path':str(BASE/'acquisition_001.bin'),'sha256':sha,'bytes':len(raw)},
    'paragraphs':paragraphs,'tables':tables,'table3_source_rows':source_rows,
    'figure':json.loads((BASE/'FIGURE_CUSTODY_001.json').read_text()),
    'figure_visual_observation':{'viewer':'view_image originalFig4.jpg','derived_numbers':[],
      'double_mutant_label':'T252N/V253N','text_table_double_mutant':'T252N/V253T','association_status':'conflicting_label; no silent image-to-table reassignment'},
    'limits':['No digitized graph values','No replicate count or SD stated forTable3; Fig5 triplicate/SD applies to its own kinetic points','Table3 printedzeros retained as native values with nondetection qualifications, not physicalzero','Author H2O rate is inferred arithmetic, not an independent measuredendpoint','Table2 fittedkcat is a different parameter/experimental representation fromTable3 turnover; no silent pool','No numerical no-P450 partner-only blank supplied in inspected original article','Full parent post-packet reset required before scientific interpretation']}
(BASE/'SOURCE_PACKET_001.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
ratios={}
wt=F(206,289);mut=F(92,216)
ratios['T252N_over_WT_product']=F(92,206)
ratios['T252N_over_WT_nadh']=F(216,289)
ratios['T252N_over_WT_coupling']=mut/wt
assert ratios['T252N_over_WT_nadh']*ratios['T252N_over_WT_coupling']==ratios['T252N_over_WT_product']
result={'scope':'Independent source-case arithmetic only; not production reader, integrated sheet or evidence confidence','source_sha256':sha,'validated_original_byte_anchors':len(paragraphs)+sum(len(t['rows'])+sum(len(r['cells']) for r in t['rows'])+1 for t in tables.values()),'decimal_precision':70,'rows':oracle,'contrast_factorization':{k:show(v) for k,v in ratios.items()},'source_and_formula_checks_passed':True}
(BASE/'NUMERICAL_ORACLE_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'source_sha256':sha,'anchors':result['validated_original_byte_anchors'],'rows':[{k:r[k] for k in ('subject','displayed_ratio_percent','displayed_minus_reported_percentage_points','diagnostic_water_from_displayed_operands','physical_coupling')} for r in oracle],'factorization':result['contrast_factorization']},indent=2))
