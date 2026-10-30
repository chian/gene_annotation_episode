"""Offline verification of the two finite public-root timing witnesses."""
from pathlib import Path
import hashlib,json,stat
A=Path('/tmp/configured-resource-prefix-R-20261022-zWmbii')
B=Path('/tmp/configured-resource-root-choice8-R-20261022-aIDjVo')
OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def check_bundle(p,digest):
 raw=(p/'MANIFEST001.json').read_bytes();assert sha(raw)==digest
 rows=read(p/'MANIFEST001.json')['files']
 assert {f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file()}=={r['path'] for r in rows}|{'MANIFEST001.json'}
 for r in rows:
  f=p/r['path'];b=f.read_bytes();assert not f.is_symlink() and len(b)==r.get('bytes',r.get('size')) and sha(b)==r['sha256']
  assert stat.S_IMODE(f.stat().st_mode)==0o444
 return {'manifest_sha256':digest,'members':len(rows)}
def main():
 inputs=[check_bundle(A,'8a39d866bd104c4c7fbcd2bfb9781df079fca20028d4f6509b6459411914391c'),check_bundle(B,'d34b6e8147547e506a5e0fa4ab383f63dce5e25334b1699f9567b7d9f0d32b5b')]
 first=read(A/'CAPTURE001.json');second=read(B/'CAPTURE001.json')
 assert first['main']['total_changes']==second['total_changes']==0
 for cut in (first['main'],first['durable'],second):
  assert cut['uri_mode']=='ro' and cut['query_only'] is True and cut['explicit_begin'] is True and cut['immutable'] is False
 data=first['main']['data']
 assert data['C1_original_commissions']==[]
 original=data['root_original_selected_estimate_results'][0]
 proposal_row,=second['original_proposal3_journal']
 assert original['result_text_sha256']==proposal_row['result_text_sha256']
 proposal=proposal_row['result']['result']
 descriptor,=second['original_request8'];raw=(B/descriptor['member']).read_bytes()
 assert sha(raw)==descriptor['request_text_sha256'] and len(raw)==descriptor['utf8_bytes']
 request=json.loads(raw)
 fields=('api_reported_execution_expectations','api_reported_execution_forecasts','api_execution_options','api_timing_planning_disposition')
 for context in (request['context'],request['model_presentation']['context']):
  assert context['api_execution_proposal']==proposal
  for name in fields:assert context[name]==proposal[name]
 action,=second['selected_action8'];job,=second['matching_provider_jobs']
 assert action['tool']=='public.hmmer.search' and action['decision_index']==8 and action['status']=='completed'
 assert job['id'] in (action['nested_job_ref'],action['top_job_ref'])
 assert job['operation_key']==second['run_id']+':'+second['root_episode_id']+':8'
 assert action['selected_arguments']['parameters']=={'E':.01} and proposal['arguments']['parameters']=={}
 expected=proposal['request']
 differences={k:{'estimate':expected[k],'actual':job['request'][k]} for k in set(expected)|set(job['request']) if expected.get(k)!=job['request'].get(k)}
 assert differences=={'parameters':{'estimate':{},'actual':{'E':.01}}}
 forecast,=proposal['api_reported_execution_forecasts']
 assert forecast['reported_result_support']=={'reported_result_count':0} and forecast['status']=='no_matching_history' and forecast['expected_total_seconds'] is None
 result={'status':'verified_with_limits','inputs':inputs,'request8_sha256':sha(raw),'original_proposal_preserved_in_raw_and_model_context':True,'exact_request_difference':differences,'exact_configuration_forecast_established':False,'causal_influence_established':False,'resource_child_demonstrated':False,'application_database_transport_calls':0}
 p=OUT/'RESULT001.json'
 with p.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 p.chmod(0o444);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
