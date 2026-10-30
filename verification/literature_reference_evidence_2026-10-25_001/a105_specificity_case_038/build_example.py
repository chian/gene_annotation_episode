"""Research-only source custody and deterministic arithmetic for one primary paper.

No network, model, scientific state, production scorer or target-credit path.
"""
from pathlib import Path
import hashlib,json,math,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent
raw=(OUT/'source/PMC2711008.bioc.xml').read_bytes()
r=ET.fromstring(raw)
ps=r.findall('.//passage')
sha=lambda b:hashlib.sha256(b).hexdigest()
records=[]
for i,p in enumerate(ps):
 info={n.get('key'):n.text for n in p.findall('infon')}
 records.append({'passage':i,'section_type':info.get('section_type'),'type':info.get('type'),'text':p.findtext('text',''),'bioc_offset':p.findtext('offset'),'table_xml':info.get('xml')})
(OUT/'source/passages.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n')
table_xml=records[63]['table_xml']
(OUT/'source/Table1.decoded.xml').write_text(table_xml)
t=ET.fromstring(table_xml)
rows=[]
for tr in t.findall('./tbody/tr'):
 values=[''.join(td.itertext()) for td in tr.findall('td')]
 parsed=[]
 for token in values[1:]:
  a,b=token.split('±');parsed.append({'value':float(a.strip()),'plus_minus':float(b.strip()),'raw':token,'uncertainty_kind':'unspecified'})
 rows.append({'substrate':values[0],'Km_uM':parsed[0],'kcat_per_s':parsed[1],'efficiency_per_uM_per_min':parsed[2]})
selection={'case_group':'spec_cysq_pap_not_imp','metadata_only_before_primary_read':True,'gene':'Rv2131c / cysQ','source_organism':'Mycobacterium tuberculosis H37Rv','source_url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/','doi':'10.1021/bi702453s','retained_metadata_path':'research/slotted_process_library/corpus/specificity/cases.jsonl','retained_actual_observations_read':False,'companion_2010_read':False,'primary_bytes_sha256':sha(raw),'primary_bytes':len(raw),'acquired_via':'https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC2711008/unicode','web_access_attempt':'PMC browser URL returned recaptcha; no experimental text read there','primary_read_coverage':{'passages_read':[0,75],'complete_available_methods_passages':[10,36],'complete_available_results_discussion_passages':[37,69],'summary_passages':[70,73],'supporting_information_notice':[74,75],'table_1_passages':[62,64],'not_read':['references beyond incidental first items displayed','supplementary spectra','rendered figure images','raw kinetic fits or original instrument data'],'representation_limits':['BioC prose omits equations 1-3 as rendered formulas','figure captions read; images not visually examined','Table1 full embedded XML and footnote read']},'source_corrections':'SOURCE_CORRECTIONS.md SC01 separates YeaG recovery-growth versus survival; no YeaG quantities reused'}
(OUT/'SELECTION.json').write_text(json.dumps(selection,indent=2)+'\n')
by={x['substrate']:x for x in rows};P=by['PAP']['efficiency_per_uM_per_min']['value']
calculations=[]
for alt in ['IMP','FBP']:
 a=by[alt]['efficiency_per_uM_per_min']['value'];e=math.log(P/a)
 calculations.append({'alternative':alt,'numerator_PAP':P,'denominator_alternative':a,'ratio':P/a,'log_ratio':e,'difference_efficiency':P-a,'signed_profile_numerator_e_squared_over_2':e*e/2,'signed_index_inner_numerator_e_squared_over_4':e*e/4,'source_profile_log_ratio':None,'source_signed_index':None,'reason':'reported_plus_minus_statistic_unspecified; joint_observation_model_and_sampling_covariance_unreported; common_condition_mapping_unmeasured'})
for x in rows:
 x['quotient_of_reported_parameter_means']=60*x['kcat_per_s']['value']/x['Km_uM']['value']
 x['reported_efficiency_not_replaced_by_recomputed_quotient']=True
 x['relative_untyped_error_magnitude']=x['efficiency_per_uM_per_min']['plus_minus']/x['efficiency_per_uM_per_min']['value']
result={'version':'case038_research_numeric_example_v1','origin':'reported_table_inputs_and_deterministic_derived_values','synthetic_measurements':False,'rows':rows,'contrasts':calculations,'shared_observation':'PAP efficiency 42 is common numerator; two contrasts are not independent','condition_difference':{'PAP':{'pH':8.5,'MgCl2_mM':0.5,'enzyme_nM':5,'time_min':4,'temperature_C':30,'method':'ESI-MS AMP product quantitation','substrate_range_uM':[0.625,50]},'IMP':{'pH':9.0,'MgCl2_mM':10,'enzyme_nM':110,'time_min':15,'temperature_C':30,'method':'malachite-green released Pi','substrate_range_uM':[1000,5500]},'FBP':{'pH':9.0,'MgCl2_mM':10,'enzyme_nM':110,'time_min':15,'temperature_C':30,'method':'malachite-green released Pi','substrate_range_uM':[90,900]}},'diagnostics':{'IMP_highest_assayed_concentration_over_reported_Km':5500/7110,'IMP_reported_Km_over_highest_assayed_concentration':7110/5500,'MgCl2_alternative_over_PAP':10/.5,'enzyme_concentration_alternative_over_PAP':110/5,'duration_alternative_over_PAP':15/4},'score_compilation':{'single_comparison':'S_j=e_j*abs(e_j)/(2*V_j); B_j=tanh(S_j/2), only if supported known-normal log-summary model','both_preferences':'S_both=min(e_IMP^2/(2*V_IMP),e_FBP^2/(2*V_FBP)) for the positive observed contrasts under the declared unrestricted joint-normal effect model; B_both=tanh(S_both/2)','source_profile_log_ratio':None,'source_signed_index':None,'uncertainty_or_quality_weights_invented':False,'target_transfer_or_final_annotation_credit':None}}
(OUT/'NUMERICAL_EXAMPLE.json').write_text(json.dumps(result,indent=2)+'\n')
# Source spans in the retained human-readable derivative are exact UTF8 custody
# witnesses. They do not assert independent physical observation identities.
textbytes=(OUT/'source/PMC2711008.bioc.txt').read_bytes()
selected=[]
for i in [14,18,19,21,27,30,32,34,42,54,55,57,63,64,65,66,68,69]:
 text=records[i]['text'];needle=text.encode();start=textbytes.index(needle)
 selected.append({'passage':i,'source_path':'source/PMC2711008.bioc.txt','representation':'derived_text_from_primary_BioC','start_utf8_byte':start,'end_utf8_byte':start+len(needle),'text':text,'source_sha256':sha(textbytes)})
(OUT/'SOURCE_SELECTIONS.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False)+'\n')
manifest=[]
for p in sorted((OUT/'source').iterdir()):
 b=p.read_bytes();manifest.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':sha(b)})
(OUT/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Finite numerical/custody checks, not production/integration tests.
assert len(rows)==3
assert calculations[0]['ratio']==42/.0027
assert calculations[1]['ratio']==1680
assert by['IMP']['Km_uM']['value']>5500
assert all(x['uncertainty_kind']=='unspecified' for row in rows for x in [row['Km_uM'],row['kcat_per_s'],row['efficiency_per_uM_per_min']])
assert all(textbytes[x['start_utf8_byte']:x['end_utf8_byte']].decode()==x['text'] for x in selected)
print(json.dumps({'source_sha256':sha(raw),'contrasts':calculations,'finite_assertions':'passed','source_selection_spans':len(selected)},indent=2))
