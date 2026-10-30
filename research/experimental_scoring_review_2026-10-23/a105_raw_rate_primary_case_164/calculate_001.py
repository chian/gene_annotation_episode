"""Research arithmetic only. Source readings and scientific unit groups are separate.
No production calculator, episode, scientific independence model or credit is run.
"""
from pathlib import Path
import json,hashlib,math,re
from decimal import Decimal,localcontext
from fractions import Fraction
from zipfile import ZipFile
import xml.etree.ElementTree as E

ROOT=Path(__file__).parent
N={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ORIGINAL=ROOT/'originals/S1Data.xlsx'
z=ZipFile(ORIGINAL); xml=z.read('xl/worksheets/sheet1.xml')
cells={x.attrib['r']:x for x in E.fromstring(xml).findall('.//m:sheetData/m:row/m:c',N)}
strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',N)]
def read(c):
 x=cells[c]; s=x.findtext('m:v',namespaces=N)
 return strings[int(s)] if x.attrib.get('t')=='s' else s

def witness(c):
 return {'original_file':'originals/S1Data.xlsx','file_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),'sheet':'Sheet1','zip_member':'xl/worksheets/sheet1.xml','zip_member_sha256':hashlib.sha256(xml).hexdigest(),'cell':c,'source_type':cells[c].get('t','n'),'stored_value_lexeme':read(c),'formula':cells[c].findtext('m:f',namespaces=N)}

groups={}
for substrate,rows in [('DHA',[8,9,10]),('L-EUS',[12,13,14]),('D-EUS',[16,17,18])]:
 obs=[]
 for row in rows:
  label=read('C'+str(row)); cell='J'+str(row)
  obs.append({'source_designated_observation_label':label,'derived_record_identity':{'paper_doi':'10.1371/journal.pbio.3002285','panel':'Fig 2B','column_subject_label':read('J3'),'substrate_label':substrate,'parallel_label':label},'identity_meaning':'source-designated separate reported parallel activity; not a preparation, biological unit or cross-arm pair identity','value':read(cell),'unit':'U/mg','origin':'reported','value_witness':witness(cell),'parallel_label_witness':witness('C'+str(row)),'scientific_sampling_unit':None,'sampling_basis':'unspecified','independence':None,'preparation_id':None,'within_unit_measurement_roster':None})
 groups[substrate]={'observations':obs,'unit_witness':witness('C2'),'subject_witness':witness('J3'),'substrate_witness':witness('C'+str(rows[0]-1)),'source_reported_observation_count':3,'biological_preparation_count':None,'same_preparation_across_substrates':None,'cross_arm_pairing':None}

# Witnesses for already-read source paragraphs. Exact original bytes are retained.
html=(ROOT/'originals/article.html').read_bytes(); decoded=html.decode()
phrases=['The standard reaction mixture (100','The coding gene of phosphoketolase','Determination of kinetics of PKs on GALD','The reaction system without PK was used as the control','Glycoaldehyde was confirmed by GC-MS','Chromogenic detection of acetyl-phosphate','The PKs coding genes from different species','Enzyme kinetics were determined with 0.25','Determination of kinetics of PKs on Xu5P','Determination of kinetics of PKs on F6P']
w=[]
for phrase in phrases:
 for match in re.finditer(r'<p\b[^>]*>.*?</p>',decoded,flags=re.S):
  if phrase in re.sub('<[^>]*>','',match.group()):
   start=len(decoded[:match.start()].encode());end=len(decoded[:match.end()].encode())
   w.append({'phrase_selector':phrase,'file':'originals/article.html','source_sha256':hashlib.sha256(html).hexdigest(),'start_byte':start,'end_byte':end,'quote_original_html':html[start:end].decode()});break

extraction={'version':'case164_exact_source_readings_001','paper_doi':'10.1371/journal.pbio.3002285','source_content_is_goal_authority':False,'subject':'purified recombinant BbPK; paper label Actinobacteria Bifidobacterium','specific_species_strain_and_sequence_binding':None,'construct_source':'pET-28a cloned via NdeI/XhoI; expressed in E. coli BL21(DE3); purified Ni-NTA','exact_construct_boundaries_and_tag_sequence':None,'molecular_arrangement':'same nominal BbPK construct in separate substrate reactions; substrates replace one another, not co-mingled D/L substrates; helper enzymes coexist only if coupled assay applies','rate_protocol_binding':'uncertain: Fig2B/S1Data do not explicitly identify which described assay produced each reported specific activity','groups':groups,'source_witnesses':w,'canonical_amount_time_conversion':{'value':None,'reason':'U definition not located in examined packet; do not substitute conventional definition'},'prepared_csv_mapping_status':'proposal only; source is original XLSX, not current exact header CSV/TSV','annotation_credit':None}
(ROOT/'EXTRACTION_001.json').write_text(json.dumps(extraction,indent=2,ensure_ascii=False))

with localcontext() as ctx:
 ctx.prec=60
 summaries={}
 for name,g in groups.items():
  vals=[Decimal(x['value']) for x in g['observations']]; n=len(vals)
  mean=sum(vals)/Decimal(n); ss=sum((x-mean)**2 for x in vals); variance=ss/Decimal(n-1);sd=variance.sqrt()
  f=[Fraction(x['value']) for x in g['observations']]; fm=sum(f)/len(f);fv=sum((x-fm)**2 for x in f)/(len(f)-1)
  assert Fraction(mean)==fm or abs(Fraction(mean)-fm)<Fraction(1,10**58)
  assert abs(Fraction(variance)-fv)<Fraction(1,10**58)
  summaries[name]={'reported_parallel_count':n,'native_unit':'U/mg','sum':str(sum(vals)),'mean':str(mean),'sum_squared_deviations':str(ss),'sample_variance':str(variance),'sample_sd':str(sd),'cv':str(sd/mean),'exact_mean':{'numerator':str(fm.numerator),'denominator':str(fm.denominator)},'exact_sample_variance':{'numerator':str(fv.numerator),'denominator':str(fv.denominator)},'operand_cells':[x['value_witness']['cell'] for x in g['observations']],'scientific_unit_mean':None,'between_preparation_sd':None,'se':None,'mean_and_sd_scope':'descriptive across source-labelled reported Parallel measurements; underlying unit grouping unknown'}
 contrasts={}
 for alt in ['L-EUS','DHA']:
  d=Decimal(summaries['D-EUS']['mean']);a=Decimal(summaries[alt]['mean']);ratio=a/d
  contrasts['D-EUS_vs_'+alt]={'reference_substrate':'D-EUS','test_substrate':alt,'reference_rate':str(d),'test_rate':str(a),'difference':str(d-a),'difference_unit':'U/mg','test_over_reference':str(ratio),'fractional_decrease':str(1-ratio),'reference_over_test':str(d/a),'formulae':{'reference_rate':'sum(J16:J18)/3','test_rate':'sum(J12:J14)/3' if alt=='L-EUS' else 'sum(J8:J10)/3','difference':'reference_rate - test_rate','test_over_reference':'test_rate/reference_rate','fractional_decrease':'1 - test_rate/reference_rate','reference_over_test':'reference_rate/test_rate'},'dependence':'unknown','difference_se':None,'profile_log_ratio':None,'final_reliability_or_annotation_score':None,'scope':'reported activity contrast under source-nominal common assay; substrate-dependent reporter/coupling response and blanks unquantified'}
 result={'version':'case164_native_arithmetic_001','origin':'derived_from_reported_cells','rounding':'60 digit Decimal; exact Fraction mean/variance verification','summaries':summaries,'contrasts':contrasts,'all_contrasts_share_reference_cells':['J16','J17','J18'],'verification':{'decimal_vs_independent_fraction_means_variances':True,'arithmetic_is_source_extraction_verification':False,'source_measurement_truth_or_assay_validity_verified':False,'production_raw_reader_executed':False,'ordinary_episode_binding_verified':False},'conditional_combination_proposal':{'formula':'Q_L/Q_D = ((mu_L-b_L)/(mu_D-b_D)) * (g_D/g_L) * (f_L/f_D)','mu':'reported activity mean in source U/mg','b':'matched no-PK reporter blank expressed using the same mass normalization and native unit','g':'measured quantitative reporter recovery/gain in each substrate matrix, dimensionless, under established linear response','f':'fraction of blank-corrected response attributable to the intended BbPK product-forming process, dimensionless, requiring selective controls or orthogonal quantitative validation','assumptions':'positive nonzero denominators; calibrated linear coupling; same intended endpoint and normalization; same source unit convention; f correction not already included in g; no independence claim','populated':False,'reason':'no numerical b,g,f for selected raw readings; no aggregate is substituted'}}
 (ROOT/'ARITHMETIC_001.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'summaries':{k:{j:v for j,v in s.items() if j in ['mean','sample_sd','cv','operand_cells']} for k,s in summaries.items()},'contrasts':contrasts},indent=2))
