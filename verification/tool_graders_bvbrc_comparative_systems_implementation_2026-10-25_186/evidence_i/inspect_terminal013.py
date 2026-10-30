import asyncio,json
from pathlib import Path
from copy import deepcopy
from types import SimpleNamespace
from gene_annotation_episode.state import Store
from gene_annotation_episode.api_service_execution import APIServiceExecution
from test_api_bvbrc_appservice import CONFIG
from gene_annotation_episode.bvbrc_comparative_systems_bundle_adapter import implementation_sha256
root=Path('../evidence_i/pytest_012/test_latest_invalid_keeps_orig0')
with Store(root/'state') as store:
 row=store.db.execute('SELECT run_id,episode_id,decision_index,action FROM runtime_actions WHERE decision_index=5').fetchone()
 configuration=deepcopy(CONFIG)
 configuration['scientific_adapters']=[{'adapter_id':'bvbrc_comparative_systems','adapter_version':'1','implementation_sha256':implementation_sha256()}]
 api=APIServiceExecution(store,run_id=row['run_id'],directory=root,configuration={'selected-api':configuration},tool_registry=SimpleNamespace(store=store,clients={}),handoff_unit=2,acquired_record_unit=3)
 def forbidden(*args,**kwargs): raise AssertionError('terminal replay must not reach transport')
 api.services['selected-api'].client.rpc=forbidden
 api.services['selected-api'].client.download=forbidden
 context=api.appservice.custody.context(row['episode_id'])
 action=json.loads(row['action'])
 counts=[store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('runtime_actions','runtime_observations')]
 outcome=asyncio.run(api.execute(context,action['tool'],action['arguments'],f"{row['run_id']}:{row['episode_id']}:5"))
 assert outcome['feedback']['code']=='api_assignment_already_completed',outcome
 assert counts==[store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('runtime_actions','runtime_observations')]
 Path('../evidence_i/LATEST_FAILURE_REASON_001.json').write_text(json.dumps({'outcome':outcome,'counts_unchanged':counts,'transport_calls':0,'basis':'replay of already selected rejected action after original terminal; no new selection'},indent=2)+'\n')
 print(outcome)
