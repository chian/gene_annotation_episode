"""Finite retained-owner boundaries; no live service, native job, or restoration.

Constructor bypasses below are explicit: actual existing metadata methods run
with passive catalog selectors. They neither exercise nor impersonate a saved
factory/receipt setup. Scientific execution and custody remain separate.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import traceback

from jsonschema import Draft202012Validator
import pytest

AXIS='gene_annotation_episode.episodic_workflow.root.a107'


def module(name):return importlib.import_module(AXIS+'.'+name)


def metadata_owner():
    cls=module('library.received_execution_information.historical_receiving_owner').HistoricalReceivedExecutionOwner
    owner=cls.__new__(cls)
    owner.resources={};owner.api_execution=None
    for name in ('native_expression_nmf_results','native_flux_balance_results','atac_results',
            'native_chromatin_interaction_results','native_rna_structure_results','native_genomic_overlap_results',
            'rna_structure_comparison_results','native_blast_standard_database_results','native_blast_database_results',
            'native_hmmer_preparation_results','native_infernal_preparation_results','native_blast_results','native_infernal_results'):
        setattr(owner,name,None)
    return owner


FAMILIES={
    'fba':('native_flux_balance_results','flux_balance_result_selection','flux_balance_result_selector_v1'),
    'atac':('atac_results','atac_differential_execution_information','atac_differential_result_selector_v1'),
    'chromatin':('native_chromatin_interaction_results','chromatin_interaction_execution_information','chromatin_interaction_result_selector_v1'),
    'genomic':('native_genomic_overlap_results','genomic_overlap_execution_information','genomic_overlap_result_selector_v1'),
    'protein':('resources','protein_structure_selection','protein_structure_result_selector_v1'),
}


def actual_selector(family):
    owner=metadata_owner();field,missing,version=FAMILIES[family]
    if family=='protein':owner.resources={'declared':{'native_protein_structure':[{'declared_metadata_only':True}]}}
    else:setattr(owner,field,object())  # Select metadata presence; no host method runs.
    value=owner.assignment_schema('results')
    Draft202012Validator.check_schema(value)
    branch,=[row for row in value['properties']['selector']['allOf']
        if row['if']['properties']['version'].get('const')==version]
    Draft202012Validator.check_schema(branch['then'])
    return branch['then']


def actual_api_facts(service):
    owner=metadata_owner()
    owner.api_execution=SimpleNamespace(services={'declared':SimpleNamespace(service=service)})
    facts=owner.fact_sources('results')
    prefix='execution_enrichr_' if service=='enrichr' else 'execution_addgene_'
    selected={key:value for key,value in facts.items() if key.startswith(prefix)}
    assert selected
    for row in selected.values():Draft202012Validator.check_schema(row['report_schema'])
    return selected


def actual_local_bindings(key):
    cls=module('library.received_execution_information.historical_local_assignment_validation').HistoricalLocalAssignmentValidation
    supplied={'kind':'local','workspace':'/declared/workspace',
        'policy':{'memory_bytes':5368709120,'scratch_bytes':1048576},key:[]}
    instance=cls(supplied)
    assert instance.configuration==supplied
    return instance.configuration


@pytest.mark.parametrize('family',list(FAMILIES))
def test_actual_received_result_assignment_schema_keeps_independent_reference_scope(family):
    first=actual_selector(family);saved=deepcopy(first)
    first['invented_probe_field']=True
    assert actual_selector(family)==saved


@pytest.mark.parametrize('service',['enrichr','sequence_support'])
def test_actual_received_api_fact_catalog_preserves_source_owned_shapes(service):
    first=actual_api_facts(service);saved=deepcopy(first)
    next(iter(first.values()))['report_schema']['invented_probe_field']=True
    assert actual_api_facts(service)==saved


@pytest.mark.parametrize('key',['native_homer_motif','native_fluorescence','native_genomic_overlap'])
def test_actual_empty_configured_catalog_exposes_no_binding(key):
    assert actual_local_bindings(key)[key]==[]


def test_actual_empty_molecular_catalog_stays_an_invalid_returned_outcome():
    ContractError=module('domain').ContractError
    with pytest.raises(ContractError,match='ordinary_orf_bindings_required'):
        actual_local_bindings('native_molecular_sequence')


def test_original_fluorescence_selector_schema_retains_closed_native_and_saved_metadata():
    owner=module('fluorescence_result_contracts')
    schema=owner.FLUORESCENCE_RESULT_SELECTOR_SCHEMA
    native={'version':'fluorescence_result_selector_v1','mode':'native_result',
        'selection':{'requests':[],'offset':0,'limit':1},'context_fields':[],
        'saved_sheet_file':None,'parameters':None}
    Draft202012Validator(schema).validate(native)
    assert owner.validate_fluorescence_selector(native)==native
    invalid=deepcopy(native);invalid['parameters']={}
    with pytest.raises(ValueError,match='invalid_fluorescence_selector'):
        owner.validate_fluorescence_selector(invalid)
    extra=deepcopy(native);extra['invented_result']=True
    assert not Draft202012Validator(schema).is_valid(extra)


def test_original_protein_schema_accessor_keeps_detached_reference_scope():
    owner=module('protein_structure_selection')
    first=owner.protein_structure_result_selector_schema();original=deepcopy(first)
    Draft202012Validator.check_schema(first)
    first['$defs'].clear()
    assert owner.protein_structure_result_selector_schema()==original


@pytest.mark.parametrize('owner_name,function_name',[
    ('library.addgene_received_fields','requested_addgene_fields'),
    ('library.enrichr_received_fields','requested_enrichr_fields')])
def test_exact_received_field_contracts_reject_changed_schema_with_actual_boundary_error(owner_name,function_name):
    owner=module(owner_name);select=getattr(owner,function_name)
    facts=owner.addgene_sequence_fact_sources() if 'addgene' in owner_name else module('library.enrichr_received_contracts').enrichr_fact_sources()
    key=next(iter(facts));schema={'type':'object','properties':{'selected':deepcopy(facts[key]['report_schema'])}}
    before=deepcopy(schema)
    assert select(schema)=={'selected':key} and schema==before
    schema['properties']['selected']['invented_field']=True
    error_type=module('communication').ReportBoundaryError
    with pytest.raises(error_type) as error:select(schema)
    assert type(error.value) is error_type


@pytest.mark.parametrize('raw,code',[(b'{"same":1,"same":2}','fba_duplicate_json_key'),
    (b'{"number":NaN}','fba_nonfinite_json'),(b'{"number":Infinity}','fba_nonfinite_json')])
def test_restored_fba_decoder_retains_its_original_distinct_errors(raw,code):
    with pytest.raises(ValueError,match='^'+code+'$'):
        module('native_flux_balance_storage').decode_json(raw)


def test_restored_fba_decoder_preserves_null_and_original_array_order():
    assert module('native_flux_balance_storage').decode_json(b'{"values":[null,3,1]}')=={'values':[None,3,1]}


def test_preparation_metadata_does_not_manufacture_an_available_population():
    owner=module('library.fluorescence_preparation_declarations')
    job={'preparations':[],'report_inputs':[]}
    sources={'supplied':None};samples={};domains={};channels={}
    before=deepcopy((job,sources,samples,domains,channels))
    assert owner.add_preparation_declarations(job,sources=sources,samples=samples,domains=domains,channels=channels) is None
    assert owner.validate_report_declarations(job)==set()
    assert (job,sources,samples,domains,channels)==before


def test_preparation_reuses_actual_existing_fluorescence_error_identity():
    selected=module('library.fluorescence_preparation_contracts')
    core=module('library.received_execution_information.historical_fluorescence_contracts')
    with pytest.raises(core.FluorescenceContractError) as error:
        selected.validate_preparation_request({},input_domains=[])
    assert type(error.value) is core.FluorescenceContractError and error.value.code=='invalid_parameters'


def test_selected_preparation_software_checks_literal_original_closure_only():
    owner=module('library.fluorescence_preparation_declarations')
    software={'module_root':'/declared','implementation_files':[
        {'path':'/declared/gene_annotation_episode/native_fluorescence_prepared_contracts.py'}]}
    before=deepcopy(software)
    assert owner.validate_selected_software(software,methods=[],profiles=[]) is None
    assert software==before
    with pytest.raises(ValueError,match='^fluorescence_selected_implementation_closure_missing$'):
        owner.validate_selected_software(software,methods=[],profiles=['biomni_facs_log_548_v1'])


def deployment_binding():
    contracts=module('molecular_sequence_result_contracts')
    native=module('library.molecular_deployment_contracts')
    execution=module('molecular_sequence_execution_contracts')
    profile=contracts.ordinary_molecular_sequence_profile('annotate_open_reading_frames')
    pin=lambda path,digest:{'path':path,'sha256':digest,'size_bytes':0}
    python=pin('/declared/python','0'*64);manifest=pin('/declared/manifest','1'*64)
    reference='artifact_'+manifest['sha256']
    deployment={'version':profile['deployment_version'],'runtime':{'executable':python,'home':'/declared/home'},
        'module':pin('/declared/original.py',native._SOURCE_PROFILES[profile['native_source']]['sha256']),
        'import_roots':['/declared/imports'],'software_files_ref':reference,'software_files_file':manifest}
    software={'version':execution.SOFTWARE_VERSION,'python':python,'python_home':'/declared/home',
        'python_version':'declared','import_roots':['/declared/imports'],
        'software_files_ref':reference,'software_files_file':manifest}
    return {'version':module('library.molecular_binding_metadata').BINDING_VERSION,
        'operation':'annotate_open_reading_frames','deployment':deployment,'software':software}


def test_actual_molecular_deployment_wrapper_uses_original_pins_without_filesystem_access():
    binding=deployment_binding();before=deepcopy(binding)
    assert module('molecular_sequence_ordinary')._deployment(binding['operation'],binding['deployment']) is None
    assert module('library.molecular_binding_metadata').validate_native_molecular_sequence_bindings([binding])==[before]
    assert binding==before


def test_original_molecular_boundary_error_keeps_code_path_and_details():
    binding=deployment_binding();binding['deployment']['module']['sha256']='2'*64
    native=module('library.molecular_deployment_contracts')
    with pytest.raises(native._BoundaryError) as error:
        module('molecular_sequence_ordinary')._deployment(binding['operation'],binding['deployment'])
    assert type(error.value) is native._BoundaryError
    assert error.value.code=='molecular_sequence_original_source_pin_required'
    assert error.value.path=='/deployment/module/sha256' and error.value.details=={}


class DeclaredRecords:
    def __init__(self,records):self.records=deepcopy(records);self.reads=[]
    def get(self,key):self.reads.append(key);return deepcopy(self.records[key])


def test_protein_ancestry_plain_leaf_stays_unprotected_without_granting_authority():
    store=DeclaredRecords({'input':{'id':'input','record_type':'input'}})
    assert module('library.protein_sequence_ancestry').is_protein_structure_sequence_operand(store,'input') is False
    assert store.reads==['input']


def test_protein_ancestry_invalid_typed_record_keeps_actual_existing_structured_error():
    store=DeclaredRecords({'feature':{'id':'feature','record_type':'feature'}})
    error_type=module('protein_structure_authority').ProteinStructureOperandError
    with pytest.raises(error_type) as error:
        module('library.protein_sequence_ancestry').is_protein_structure_sequence_operand(store,'feature')
    assert type(error.value) is error_type and error.value.issue['code']=='invalid_schema'


def probe(mode,destination):
    assert mode in {'baseline','post'}
    cases=[]
    for family,(_,missing,_) in FAMILIES.items():
        # Retained first baseline exposed the earlier unconditional fluorescence
        # export defect. The same-owner restoration is part of this successor.
        cases.append(('actual_'+family+'_selector',lambda family=family:actual_selector(family),'missing_fluorescence_selector_export',None))
    for service,missing in [('enrichr','enrichr_contracts'),('sequence_support','addgene_sequence_returns')]:
        cases.append(('actual_'+service+'_facts',lambda service=service:actual_api_facts(service),missing,None))
    for key,missing in [('native_homer_motif','native_homer_execution'),('native_genomic_overlap','native_genomic_overlap_contracts')]:
        cases.append(('actual_'+key+'_empty_catalog',lambda key=key:actual_local_bindings(key),missing,None))
    cases.append(('actual_fluorescence_empty_catalog',lambda:actual_local_bindings('native_fluorescence'),'missing_export',None))
    cases.append(('actual_molecular_empty_invalid_catalog',lambda:actual_local_bindings('native_molecular_sequence'),
        'molecular_sequence_tools','ordinary_orf_bindings_required'))
    rows=[]
    for name,invoke,missing,post_error in cases:
        row={'case':name}
        try:
            value=invoke();row.update(outcome='returned',value=value,expected_observed=mode=='post' and post_error is None)
        except Exception as error:
            row.update(outcome='raised',exception_type=type(error).__module__+'.'+type(error).__qualname__,message=str(error),
                missing_name=getattr(error,'name',None),traceback=[{'file':f.filename,'line':f.lineno,'function':f.name}
                    for f in traceback.extract_tb(error.__traceback__)])
            if mode=='baseline':
                if missing=='missing_fluorescence_selector_export':
                    row['expected_observed']=type(error) is ImportError and error.name==AXIS+'.fluorescence_result_contracts' and 'FLUORESCENCE_RESULT_SELECTOR_SCHEMA' in str(error)
                elif missing=='missing_export':
                    row['expected_observed']=type(error) is ImportError and 'validate_fluorescence_bindings' in str(error)
                else:row['expected_observed']=type(error) is ModuleNotFoundError and error.name==AXIS+'.'+missing
            else:row['expected_observed']=post_error is not None and isinstance(error,module('domain').ContractError) and post_error in str(error)
        rows.append(row)
    result={'version':'a107_actual_second_retained_consumer_probe_v2','mode':mode,'observations':rows,
        'prior_failed_prediction':'runs/fourth_a107_second_consumer_baseline_01/observations.json',
        'passed':all(row['expected_observed'] for row in rows),'constructor_bypass':
            'Only metadata schema/catalog methods; passive presence flags/API service names select real branches. No factory/receipt identity is asserted.',
        'native_execution':False,'saved_restoration':False,'scientific_validation':False}
    path=Path(destination).resolve();assert 'runs' in path.parts and not path.exists()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'mode':mode,'passed':result['passed'],'observations':len(rows),'output':str(path)}))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':probe(*sys.argv[1:])
