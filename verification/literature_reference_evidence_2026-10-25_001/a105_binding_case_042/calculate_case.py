"""Research-only source transcription and calls to existing pure binding calculators."""
from pathlib import Path
import json,math,hashlib
from gene_annotation_episode.literature_binding_reader import read_binding_parameter_table
from gene_annotation_episode.literature_binding_calculations import populate_binding_contrast
from gene_annotation_episode.literature_binding_models import populate_binding_model
P=Path(__file__).resolve().parent
ligands=['hya','shuffled','hya_7C_to_G','hya_8C_to_G','hya_8C_to_A','hya_8C_to_T']
values={'wild_type':['32 ± 2','>1000','>510','>740','>1000','>1000'], 'E43A':['11 ± 1','>1000','17 ± 3','7 ± 3','6 ± 1','8 ± 1']}
ys=[(65,81),(89,106),(115,131),(139,155),(164,180),(189,205)]
rows=[]
for subject,tokens in values.items():
 x=(410,478) if subject=='wild_type' else (504,596)
 for i,(ligand,token) in enumerate(zip(ligands,tokens)):
  rows.append({'subject':'E_coli_IscR_'+subject,'state':'apo','experiment':'2013_Table3_competition_250mM_KCl','ligand':ligand,'expression':token,'locator':{'original_source_ref':'PMC3676455_Table3','original_artifact_ref':'table3.jpg_sha256_'+hashlib.sha256((P/'table3.jpg').read_bytes()).hexdigest(),'image_region':[x[0],ys[i][0],x[1],ys[i][1]]}})
table={'version':'binding_parameter_table_v1','table_id':'PMC3676455_Table3','parameter_kind':'ic50','unit':'nM','uncertainty_basis':'fit_to_averaged_curve','minimum_experiment_count':3,'rows':rows}
(P/'TABLE3_RETAINED_VISUAL_TRANSCRIPTION.json').write_text(json.dumps(table,indent=2)+'\n')
results=[]
for subject in values:
 for ligand in ligands[1:]:
  extraction=read_binding_parameter_table({'source_ref':'owned_Table3_transcription','artifact_ref':'TABLE3_RETAINED_VISUAL_TRANSCRIPTION.json','text':json.dumps(table),'representation':'retained_visual_transcription'},expected_subject='E_coli_IscR_'+subject,expected_state='apo',expected_experiment='2013_Table3_competition_250mM_KCl',reference_ligand='hya',test_ligand=ligand,parameter_kind='ic50')
  sheet=populate_binding_contrast(extraction);model=populate_binding_model(sheet)
  assert sheet['cells']['native_parameter_ratio']['value'] is not None
  assert model['cells']['source_profile_log_ratio']['value'] is None
  assert model['cells']['source_profile_log_ratio']['unavailable_reason']=='binding_sampling_model_unreported'
  results.append({'subject':subject,'test_ligand':ligand,'sheet':sheet,'model_without_source':model})
(P/'NUMERICAL_CELLS.json').write_text(json.dumps(results,indent=2)+'\n')
interaction=[]
for ligand in ligands[2:]:
 w=next(r for r in results if r['subject']=='wild_type' and r['test_ligand']==ligand)['sheet']['cells']['native_parameter_ratio']
 e=next(r for r in results if r['subject']=='E43A' and r['test_ligand']==ligand)['sheet']['cells']['native_parameter_ratio']
 interaction.append({'test_ligand':ligand,'formula':'(IC50_WT_mutant/IC50_WT_hya)/(IC50_E43A_mutant/IC50_E43A_hya)','value':w['value']/e['value'],'relation':'gt','log_value':math.log(w['value'])-math.log(e['value']),'origin':'derived','meaning':'descriptive arithmetic on one printed WT limit and three printed point estimates','confidence_bound':None,'parameter_identification_bound':None,'statistical_score':None,'qualification':'WT and E43A nominal protein inputs22and20nM differ; no supplied response correction or joint sampling/censor model'})
(P/'PROPOSED_FOUR_CELL_ARITHMETIC.json').write_text(json.dumps(interaction,indent=2)+'\n')
(P/'CALCULATION_RECEIPT.json').write_text(json.dumps({'source':'actual primary Table3 image visual transcription; no synthetic numerical measurements','pure_existing_reader_calculator_calls':len(results),'all_source_profiles_correctly_unavailable':True,'further_arithmetic':'four descriptive four-cell ratios; research-only, no new production functions','episode_execution':False,'tests_run':False,'annotation_credit_computed':False},indent=2)+'\n')
for r in results:
 c=r['sheet']['cells']; print(r['subject'],r['test_ligand'],c['native_parameter_ratio']['relation'],c['native_parameter_ratio']['value'],c['log_native_parameter_ratio']['value'])
print('four_cell',json.dumps(interaction))
