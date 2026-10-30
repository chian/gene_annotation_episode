"""Inspect existing finite worksheet formats; no selected work or state IO."""
from pathlib import Path
import hashlib
import importlib
import json
import os
import sys
from copy import deepcopy

OWN=Path(__file__).resolve().parent; REPO=OWN.parents[1]
PIN=REPO/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_integration_review_256/joined_pin_008'
sys.dont_write_bytecode=True
sys.path[:]=[str(PIN),str(PIN/'tests'),*[p for p in sys.path if p and Path(p).resolve() not in (OWN,REPO)]]
os.chdir(PIN)
def save(name,value):
    path=OWN/name
    assert not path.exists(),path
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
specs=[
('native_kinetic','native_parameter','literature_kinetic_storage','kinetic_cells_schema','literature_kinetic_cells','requested_kinetic_components','COMPONENTS','cell.value','numerator_parameter'),
('summary_precision','precision','literature_kinetic_summary_precision_storage','summary_precision_cells_schema','literature_kinetic_summary_precision_cells','requested_kinetic_summary_precision_components','COMPONENTS','cell.cell.value','source_reported_sd'),
('endpoint','endpoint_signal','literature_endpoint_signal_storage','endpoint_signal_cells_schema','literature_endpoint_signal_cells','requested_endpoint_signal_components','COMPONENTS','cell.value / cell.conditional_value','retained_fraction'),
('product_coupling','product_coupling','literature_product_coupling_storage','product_coupling_cells_schema','literature_product_coupling_cells','requested_product_coupling_components','COMPONENTS','cell.value / cell.conditional_value','product_per_cofactor'),
('calibration_recovery','calibration','literature_calibration_recovery_storage','calibration_recovery_cells_schema','literature_calibration_recovery_cells','requested_calibration_recovery_components','COMPONENTS','cell.value','recovery'),
('compiled_v2','within_assay','literature_compiled_assay_storage','compiled_assay_v2_cells_schema','literature_compiled_assay_v2_cells','requested_compiled_assay_components_v2','COMPONENTS_V2','cell.value','corrected_activity'),
('common_v3','comparison','literature_compiled_assay_storage','compiled_assay_v3_cells_schema','literature_compiled_assay_v3_cells','requested_compiled_assay_components_v3',None,'cell.value / cell.conditional_value','product_reference_contrast'),
]
rows=[];schemas={};requests=[];rosters={};hashes={}
for code,field,module_name,factory,source,key,attribute,value_location,sample in specs:
    module=importlib.import_module('gene_annotation_episode.'+module_name)
    schema=getattr(module,factory)()
    if attribute is None:
        calc=importlib.import_module('gene_annotation_episode.literature_compiled_assay_calculations')
        components=list(calc.COMMON_COMPONENTS)
    else:components=list(getattr(module,attribute))
    assert schema['x-source']==source and sample in components
    native_component_enum=schema['items']['properties']['component']['enum']
    assert native_component_enum==components
    sample_request={'field':field,'source':source,'components':[sample]}
    requests.append(sample_request);rosters[key]=[sample];schemas[source]=schema
    rows.append({'family':code,'source':source,'assignment_key':key,'schema_factory':module_name+'.'+factory,
        'components':components,'component_count':len(components),'scalar_location':value_location,
        'sample_section_request':sample_request,'sample_submitted_field':{'$ref':'episode-fact:'+source},
        'sample_assignment_roster':{key:[sample]},'new_graded_assay_claim':False})
    for name in (module_name+'.py',):
        old=(PIN/'gene_annotation_episode'/name).read_bytes();current=(REPO/'gene_annotation_episode'/name).read_bytes()
        hashes[name]={'inspected_pin_sha256':hashlib.sha256(old).hexdigest(),
            'current_sha256':hashlib.sha256(current).hexdigest(),'equal':old==current}
context=deepcopy(json.loads((OWN/'WORKSHEET_DECLARATION_PROPOSAL_001.json').read_text())['properties']['assessment_context'])
fields=[r['field'] for r in requests];components=list(dict.fromkeys(c for r in rows for c in r['components']))
def revise(node):
    if isinstance(node,dict):
        if set(node.get('properties',{}))=={'field','sheet_ref','component','quantity'}:
            node['properties']['field']['enum']=fields
            node['properties']['component']['enum']=components
        for child in node.values():revise(child)
    elif isinstance(node,list):
        for child in node:revise(child)
revise(context)
submitted=obj({**{r['field']:{'$ref':'episode-fact:'+r['source']} for r in requests},'assessment_context':context})
expanded=deepcopy(submitted)
for r in requests:expanded['properties'][r['field']]=schemas[r['source']]
from gene_annotation_episode.communication import validate_closed_schema
validate_closed_schema(expanded)
save('SEVEN_FAMILY_MAPPING_002.json',{'format_support_only':True,'families':rows,'metadata_source_hashes':hashes,
    'selected_runs':0,'schemas_or_scientific_values_changed':False})
save('SEVEN_FAMILY_REQUESTS_FORMAT_EXAMPLE_002.json',requests)
save('SEVEN_FAMILY_ASSIGNMENT_ROSTERS_EXAMPLE_002.json',rosters)
save('SEVEN_FAMILY_DECLARATION_FORMAT_EXAMPLE_002.json',submitted)
save('SEVEN_FAMILY_ORIGINAL_SCHEMA_FORMATS_002.json',schemas)
save('SEVEN_FAMILY_FORMAT_GRAMMAR_CHECK_002.json',{'status':'passed','format_example_only':True,
    'field_count':len(specs),'original_native_schema_nodes_unchanged':True,'local_schema_resource_scopes_preserved':True,
    'actual_model_backed_execution':False,'selected_work_rerun':False,'constructor_implemented':False,
    'link_validator_implemented':False,'seven_assays_or_graders_completed':False})
