from pathlib import Path
from copy import deepcopy
import hashlib,json,shutil
root=Path(__file__).resolve().parents[1]; target=root/'candidate/tests/fixtures/bvbrc_comparative_systems_bundle'; target.mkdir(exist_ok=True)
contract=root.parent/'tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185'
examples={x['example_id']:x['value'] for x in json.loads((contract/'FILLED_EXAMPLES_001.json').read_text())['examples']}
build=json.loads((root/'candidate/tests/fixtures/bvbrc_comparative_systems_native/build_inputs.json').read_text())
paths={hashlib.sha256(p.read_bytes()).hexdigest():p for p in (contract/'source_executed_synthetic').rglob('*') if p.is_file()}
inputs={}
for name in ['pathway_subsystem','families','hex_256']:
 n=build[name+'_sheet']; p=deepcopy(examples['provider_parameters'])
 p.update(analysis_id=n['analysis_id'],document_selection=n['document_selection'],population_assignments=n['population_assignments'],reference_memberships=[],supplied_data_selection=examples['data_population_selection'] if name=='pathway_subsystem' else None,calculation_parameters=examples[name+'_components']['parameters'])
 p['calculation_parameters']['requests']=[r for r in p['calculation_parameters']['requests'] if r['reference_membership_id'] is None]
 task={'resource_id':'synthetic_api','task_id':'synthetic_remote_'+name,'required_application_id':'ComparativeSystems','native_application_id':'ComparativeSystems','submitted_parameters':{k:n['original_request'][k] for k in ['genome_ids','genome_groups','output_path','output_file']},'submitted_start_parameters':{},'scheduler_returned_parameters':None,'effective_parameters':None,'submission_receipt_ref':'synthetic_task_receipt_'+name,'submission_operation_key':'synthetic_run:synthetic_api:0','submission_source_ref':'synthetic_submission_'+name}
 bundle={'version':'bvbrc_appservice_artifact_bundle_v1','original_task':task,'artifacts':[],'input_bindings':[],'query_bindings':[],'supplied_scientific_metadata':[],'supplied_contents':[],'acquisition_receipt_refs':[],'requested_selector_sha256':'0'*64,'status':'ok','missing_requirements':[],'diagnostics':[]}
 byte_files={}
 for d in n['source_documents']:
  src=paths[d['sha256']]; fn=name+'_'+d['document_id']+src.suffix; shutil.copyfile(src,target/fn); byte_files[d['raw_artifact_ref']]=fn
  receipt='synthetic_download:'+d['document_id']; path='/synthetic/'+src.name
  bundle['artifacts'].append({'role':d['role'],'requirement_ids':['requirement:'+d['document_id']],**{k:d[k] for k in ['source_ref','raw_artifact_ref','sha256','byte_count']},'workspace_object':{'path':path,'uuid':'synthetic-uuid-'+d['document_id'],'type':'json' if src.suffix=='.json' else 'text','metadata_receipt_ref':'synthetic-metadata'},'task_association':{'kind':'task_result_manifest','evidence_ref':'synthetic-manifest','pointer':'/outputs/'+d['document_id'],'task_id':task['task_id'],'output_path':path,'output_uuid':'synthetic-uuid-'+d['document_id'],'byte_version_status':'current_bytes_observed','version_evidence':[]},'transfer':{'receipt_ref':receipt,'body_complete':True,'requested_range':None,'observed_range':None,'total_size':d['byte_count'],'object_complete':'yes'},'declared_format':{'format':d['format_profile'],'version':None,'mode':None,'producer_source_ref':None,'transformation_evidence':[]}})
  bundle['acquisition_receipt_refs'].append(receipt)
 evidence=deepcopy(n['producer_evidence'][0]); wrapped={'producer_evidence':evidence}; raw=json.dumps(wrapped,ensure_ascii=False).encode(); fn=name+'_producer.json'; (target/fn).write_bytes(raw)
 selected=p['producer_evidence_selections'][0]; content={'source_ref':selected['source_ref'],'artifact_field':'artifact_ref','artifact_ref':selected['raw_artifact_ref'],'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
 binding={'content':content,'pointer':selected['record_path']}; bundle['supplied_scientific_metadata'].append(binding); byte_files[content['artifact_ref']]=fn
 q={'evidence':evidence,'qualification':{'original_task_ref':task['submission_receipt_ref'],'basis':'source_execution','evidence_source_refs':[content['source_ref']],'host_binding_verified':True,'evidence_fields_verified':True,'receiver_possession_verified':True}}
 data=[]
 if name=='pathway_subsystem':
  d=examples['qualified_data_wrapper']; data=[d]; raw=(contract/'SYNTHETIC_DATA_RESPONSE_001.json').read_bytes(); fn='later_pathway_data.json'; (target/fn).write_bytes(raw); rb=d['raw_binding']; byte_files[rb['raw_artifact_ref']]=fn
  bundle['supplied_contents'].append({'source_ref':rb['source_ref'],'artifact_field':'artifact_ref','artifact_ref':rb['raw_artifact_ref'],'sha256':rb['sha256'],'byte_count':rb['byte_count']})
 inputs[name]={'classification':'source-executed synthetic native outputs; hypothetical wrapper flags; NO REAL HOST ADMISSION','bundle':bundle,'parameters':p,'supplied_values':[{'evidence':binding,'value':evidence}],'qualified_producer_evidence':[q],'qualified_data_inputs':data,'byte_files':byte_files}
(target/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
manifest={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'byte_count':p.stat().st_size} for p in target.iterdir() if p.is_file()}
(target/'MANIFEST.json').write_text(json.dumps({'classification':'synthetic unit inputs; not service output/host admission','files':manifest},indent=2)+'\n')
print('retained fixture files',len(manifest))
