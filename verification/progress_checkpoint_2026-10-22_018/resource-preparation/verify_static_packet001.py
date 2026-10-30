"""Static packet/schema checks only. Never call operator.main, C/P or SQLite."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import tomllib

from jsonschema import Draft202012Validator, FormatChecker

P=Path(__file__).resolve().parent
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
BASE=Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
PLAN=Path('/tmp/configured-resource-investigation-plan-20261022-001-DAGmrtaT')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def read(name):return json.loads((P/name).read_bytes())
def write(name,value):
    with (P/name).open('xb') as f:f.write(canonical(value)+b'\n')
def validate(schema,value,kind):
    Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/'+kind},
        format_checker=FormatChecker()).validate(value)
def rejected(schema,value,kind):
    try:validate(schema,value,kind)
    except Exception as error:
        assert type(error).__module__.startswith('jsonschema')
        return
    raise AssertionError('schema accepted a negative example')

def main():
    operator=(P/'prepare_caller001.py').read_bytes()
    tree=ast.parse(operator)
    inputs=read('INPUTS001.json')
    # Compile only seven filesystem/JSON static helpers. No module imports,
    # main body, source guard, SQLite helper or application helper is executed.
    names={'canonical','sha','read','no_links','witness','matches','verify_static_inputs'}
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions}==names
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in {
                        'PIN','SCHEMA_SHA','SCOPE_SHA','DELTA_SHA','FOCUS_SHA','INPUT_NAMES'}:
                    constants[target.id]=ast.literal_eval(node.value)
    namespace={'json':json,'hashlib':hashlib,'os':os,'Path':Path,'stat':stat,'tomllib':tomllib,
        'PLAN':P,'CODE':CODE,'RUN':RUN,**constants}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'operator_static_helpers','exec'),namespace)
    namespace['verify_static_inputs'](inputs)
    assert len(inputs['members'])==14
    for name,descriptor in inputs['members'].items():
        data=(P/name).read_bytes()
        assert len(data)==descriptor['bytes'] and sha(data)==descriptor['sha256']
    assert read('INTENDED_INVOCATION001.json')['argv'][-1]==sha((P/'INPUTS001.json').read_bytes())
    assert read('INTENDED_INVOCATION001.json')['operator']['sha256']==sha(operator)

    schema=read('SCHEMAS004.json');Draft202012Validator.check_schema(schema)
    validate(schema,read('C_REQUEST001.json'),'request')
    selected=read('C_REQUEST001.json')['initial_known_record_refs']
    assert len(selected)==len(set(selected))==198
    assert selected==json.loads((BASE/'C_REQUEST001.json').read_bytes())['initial_known_record_refs']
    old_focus=(PLAN/'FOCUS_DRAFT001.txt').read_bytes()
    assert old_focus.replace(b'the existing literature hierarchy and its library are unchanged.',
        b'the existing literature hierarchy is unchanged.')==(P/'focus.txt').read_bytes()
    assert sha((P/'focus.txt').read_bytes())==constants['FOCUS_SHA']
    for name in ('EXPECTED_HANDOFF001.json','PUBLICATION_INPUTS001.json','SCHEMAS004.json'):
        assert (P/name).read_bytes()==(BASE/name).read_bytes()
    publication=read('PUBLICATION_INPUTS001.json')
    for name,descriptor in publication['members'].items():
        data=(Path(publication['root'])/name).read_bytes()
        assert len(data)==descriptor['bytes'] and sha(data)==descriptor['sha256']

    output=read('OPERATOR_OUTPUT_SCHEMA001.json');Draft202012Validator.check_schema(output)
    witness={'path':'/schema-only/no-actual-file','bytes':0,'sha256':'0'*64}
    sample={'version':'configured_resource_investigation_preparation_result_v1','status':'prepared_not_started',
        'run_directory':str(RUN),'workspace':str(RUN/'workspace'),
        'execution_implementation_sha256':constants['PIN'],
        **{name:witness for name in ('custody_result','receipt','case_launch','parameters',
            'working_database_after_prepare','config','focus','policy_source')},
        'native_registry_ref':'schema_only_not_created','public_search_registry_ref':'schema_only_not_created',
        'inherited_refs':200,'source_guards_unchanged':True,
        'native_registry_counts':{'orders':0,'handoffs':0,'samples':0},
        'preserved_old_runtime_counts':{'runtime_runs':1,'runtime_episodes':1,'runtime_actions':179,
            'runtime_observations':175,'runtime_model_calls':180},
        'new_scientific_runs_started':0,'model_http_native_calls':0,'limits':['schema_only_no_execution']}
    validate(output,sample,'result')
    rejected(output,{**sample,'new_scientific_runs_started':1},'result')
    rejected(output,{**sample,'unexpected':True},'result')
    failures=[]
    for phase in output['$defs']['failure']['properties']['phase']['enum']:
        value={'version':'configured_resource_investigation_preparation_failure_v1','phase':phase,
            'exception_type':'SchemaOnly','message':'No actual operator invocation',
            'source_unchanged':None,'source_guard_error_type':None,'run_directory':str(RUN),
            'preserve_partial':True,'automatic_retry':False,'model_http_native_calls':0}
        validate(output,value,'failure');failures.append(value)
    rejected(output,{**failures[0],'automatic_retry':True},'failure')
    write('SCHEMA_ONLY_EXAMPLES001.json',{'status':'schema_examples_not_execution_receipts',
        'success_shape_only':sample,'failure_shapes_only':failures})

    h=hashlib.sha256();members=[]
    for file in sorted(q for package in ('gene_annotation_episode','method_loop')
            for q in (CODE/package).rglob('*.py')):
        data=file.read_bytes();name=file.relative_to(CODE).as_posix()
        h.update(name.encode()+b'\0');h.update(hashlib.sha256(data).digest())
        members.append({'path':name,'bytes':len(data),'sha256':sha(data)})
    assert len(members)==137 and h.hexdigest()==constants['PIN']
    assert sha((CODE/'gene_annotation_episode/scientific_checkpoint_fork.py').read_bytes())=='166d459b38295ab4003ebe39babd22184a96482dba5146b3b2479291ebd423ab'
    assert sha((CODE/'gene_annotation_episode/api_planning_case_policy.py').read_bytes())=='4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f'
    write('STATIC_RUNTIME_GUARD001.json',{'runtime_pin':h.hexdigest(),'files':members})
    write('STATIC_CHECKS001.json',{'status':'passed_static_only','operator_sha256':sha(operator),
        'input_manifest_sha256':sha((P/'INPUTS001.json').read_bytes()),'input_members_verified':14,
        'original198selection_equal':True,'adopted_focus_only_correction_verified':True,
        'C_schema_checked':True,'C_request_schema_valid':True,'output_schema_checked':True,
        'schema_only_result_examples':1,'schema_only_failure_examples':len(failures),'negative_schema_cases':3,
        'publication_members_unchanged':len(publication['members']),'runtime_pin':h.hexdigest(),
        'runtime_files':137,'pure_static_helper_calls':1,'operator_main_calls':0,'C_P_calls':0,
        'application_imports':0,'SQLite_connections':0,'model_service_native_calls':0,
        'source_database_or_active_workspace_files_opened':0,'preparation_executed':False})
    print(json.dumps(read('STATIC_CHECKS001.json'),sort_keys=True))

if __name__=='__main__':main()
