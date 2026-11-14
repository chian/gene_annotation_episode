"""Real selected Results schema and complete alignment contract observations."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import hashlib
PREFIX='gene_annotation_episode.episodic_workflow.root.a102.'
CALLER=PREFIX+'bvbrc_alignment_tool_info'
HOME=PREFIX+'scientific_process.execution_result_acquisition.'
EXPECTED_SCHEMA={'type':'object','properties':{'version':{'const':'execution_results_assignment_v1'},
 'handoff_ref':{'type':'string','minLength':1},'selector':{'type':'object'}},
 'required':['version','handoff_ref','selector'],'additionalProperties':False}
PROVIDERS=('bvbrc_msa','bvbrc_metacats')
ASSIGNMENT={'type':'object','properties':{'marker':{'const':'unchanged-contract-control'}},
 'required':['marker'],'additionalProperties':False}

def validate(value,stage):
 assert stage in ('baseline','installed')
 assert set(value)=={'version','stage','consumer','selected_provider','same_schema_object','schema',
  'assignment_input','inputs_unchanged','contracts','source_files','helper_sha256'}
 assert value['version']=='a102_results_contract_consumer_observation_v1'
 assert value['stage']==stage and value['consumer']==CALLER
 assert value['selected_provider']==HOME+('requests' if stage=='baseline' else 'execution_contracts')
 assert set(value['source_files'])=={CALLER.replace('.','/')+'.py',value['selected_provider'].replace('.','/')+'.py'}
 assert value['same_schema_object'] is True and value['inputs_unchanged'] is True
 assert value['schema']==EXPECTED_SCHEMA and value['assignment_input']==ASSIGNMENT
 assert set(value['contracts'])==set(PROVIDERS)
 for provider,rows in value['contracts'].items():
  assert isinstance(rows,list) and rows and all(isinstance(row,dict) for row in rows)
  assert len({row['name'] for row in rows})==len(rows)
  for row in rows:
   assert set(row)=={'name','description','resources','instructions','input_schema','invocation_route'}
   assert row['resources']=='api' and row['invocation_route']['kind']=='commission'
   assert row['invocation_route']['routes'][-1]=={'entry_role':'results','resource_id':'contract-control-api','resource_role':'results'}
 return value

def observe(stage,root,source_map):
 root=Path(root).resolve();consumer=import_module(CALLER)
 selected=import_module(HOME+('requests' if stage=='baseline' else 'execution_contracts'))
 source_files={}
 for module in (consumer,selected):
  expected=root/Path(module.__name__.replace('.','/')+'.py')
  assert Path(module.__file__).resolve()==expected
  key=str(expected.relative_to(root));digest=hashlib.sha256(expected.read_bytes()).hexdigest()
  assert source_map[key]==digest;source_files[key]=digest
 assert consumer.RESULTS_SCHEMA is selected.RESULTS_SCHEMA
 original=deepcopy(selected.RESULTS_SCHEMA);assert original==EXPECTED_SCHEMA
 assignment=deepcopy(ASSIGNMENT);contracts={}
 for provider in PROVIDERS:
  contracts[provider]=consumer.alignment_tool_contracts(resource_id='contract-control-api',assignment_schema=assignment,provider=provider)
  assert assignment==ASSIGNMENT and consumer.RESULTS_SCHEMA==selected.RESULTS_SCHEMA==original
 result={'version':'a102_results_contract_consumer_observation_v1','stage':stage,'consumer':CALLER,
  'selected_provider':selected.__name__,'same_schema_object':True,'schema':original,
  'assignment_input':assignment,'inputs_unchanged':True,'contracts':contracts,'source_files':source_files,
  'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 return validate(result,stage)

def compare(before,after):
 validate(before,'baseline');validate(after,'installed')
 assert before['schema']==after['schema'] and before['assignment_input']==after['assignment_input']
 assert before['contracts']==after['contracts'],'complete tool contracts changed'
 assert before['helper_sha256']==after['helper_sha256']
 return {'same_complete_contracts':True,'same_schema_value':True,'actual_schema_identity_each_stage':True,
  'providers':list(PROVIDERS),'old_provider':before['selected_provider'],'new_provider':after['selected_provider']}
