from copy import deepcopy
import json
from pathlib import Path
package=Path('/home/chia/repos/gene_annotation_episode/verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/candidate/gene_annotation_episode')
old=json.loads((package/'bvbrc_proteome_bundle_schemas.json').read_text())
num=json.loads((package/'bvbrc_proteome_directional_numerical_schemas.json').read_text())
def prefix(node, namespace="Directional"):
 if isinstance(node,dict): return {k: '#/$defs/'+namespace+v[8:] if k=='$ref' else prefix(v,namespace) for k,v in node.items()}
 if isinstance(node,list): return [prefix(v,namespace) for v in node]
 return node
def ref(n):return {'$ref':'#/$defs/'+n}
def nullable(n):return {'anyOf':[ref(n),{'type':'null'}]}
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
d=deepcopy(old['$defs']);d.update({'Sheet'+k:prefix(v,'Sheet') for k,v in json.loads((package/'bvbrc_proteome_sheet_schemas.json').read_text())['$defs'].items()});d.update({'Directional'+k:prefix(v) for k,v in num['$defs'].items()})
string={'type':'string','minLength':1}; arr=lambda n:{'type':'array','items':ref(n)}
p=deepcopy(d['ProviderParameters']['properties']);p.update(version={'const':'bvbrc_proteome_bundle_parameters_v2'},primary_document_id={'type':['string','null'],'minLength':1},calculation_parameters=nullable('SheetNativeCalculationParameters'),directional_documents=arr('DirectionalDocumentSelection'),directional_calculation_parameters=nullable('DirectionalDirectionalCalculationParameters'))
d['ProviderParametersV2']=obj(p)
f=deepcopy(d['HostDeclaredFormat']['properties']); f.update(format={'const':'ncbi_blastall_blastp_pairwise_text_v1'},version={'enum':['2.0.11','2.2.2','2.2.21',None]},mode={'const':'protein_database_search_pairwise_display'})
d['DirectionalDeclaredFormat']=obj(f)
base={'document_id':string,'report_key':string,'role':{'const':'proteome_directional_report'},'declared_format':ref('DirectionalDeclaredFormat')}
d['DirectionalDocumentSelection']={'oneOf':[obj({**base,'source_ref':string,'raw_artifact_ref':string}),obj({**base,'requirement_id':string})]}
d['ResolutionOutcomeV2']=deepcopy(d['ResolutionOutcome']);d['ResolutionOutcomeV2']['properties']['selector_kind']['enum'].insert(1,'directional_document')
d['ProteomeNumericalSheetV2']=obj({'version':{'const':'bvbrc_proteome_numerical_sheet_v2'},'legacy_sheet':nullable('SheetNativeSheet'),'directional_sheet':nullable('DirectionalDirectionalSheet'),'directional_operand_binding':{'const':'unbound'}})
s=deepcopy(d['ProviderSheet']['properties']);s.update(version={'const':'bvbrc_proteome_provider_sheet_v2'},parameters=ref('ProviderParametersV2'),input_resolution=arr('ResolutionOutcomeV2'),directional_results=arr('DirectionalReaderDirectionalReportResult'),directional_sheet_result=nullable('DirectionalDirectionalSheetResult'),numerical_sheet=nullable('ProteomeNumericalSheetV2'))
d['ProviderSheetV2']=obj(s)
d['ProviderComponentsV2']=obj({'version':{'const':'bvbrc_proteome_provider_components_v2'},'provider_sheet_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'legacy':nullable('SheetNativeComponentsResult'),'directional':nullable('DirectionalDirectionalComponentsResult')})
(package/'bvbrc_proteome_bundle_v2_schemas.json').write_text(json.dumps({'$schema':old['$schema'],'$defs':d},indent=2,ensure_ascii=False)+'\n')
