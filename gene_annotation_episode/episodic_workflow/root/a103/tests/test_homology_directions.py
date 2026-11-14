"""Actual legacy commissioning, immutable request replay and receiving boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from .homology_direction_checks import actual,commission,form,module,raw_rows
ROWS=[(p,m,r) for p in ('annotation','improvement') for m in (False,True) for r in (False,True)]
IDS=[p+'-'+('declared' if m else 'markerless')+'-'+('receipts' if r else 'no-receipts') for p,m,r in ROWS]

def private():
 runtime=module('runtime');return (Path(runtime.__file__).parent/'to_child_homology_job_monitoring.py').exists()

@pytest.mark.parametrize('parent,marker,receipts',ROWS,ids=IDS)
def test_actual_parent_constructs_original_job_request(tmp_path,parent,marker,receipts):
 with actual(tmp_path,parent=parent,marker=marker,receipts=receipts) as f:
  result=commission(f)
  assert result['unit_type'].endswith('.TimedChildUnit')
  assert json.loads(result['path_raw'])==[[parent,'original-parent'],['job_monitor','child_0']]
  request=json.loads(result['request_raw']);assert request['report_contract']['decision']==f.selection['purpose']
  assert request['report_contract']['measurements']['schema']==form()
  assert ('knowledge_inheritance' in request['message']) is receipts
  assert f.jobs._row(f.job)['submission_requested']==0
  assert raw_rows(f.flow)['runtime_observations']==[]

@pytest.mark.parametrize('parent,marker,receipts',ROWS,ids=IDS)
def test_same_selected_request_replays_exactly(tmp_path,parent,marker,receipts):
 with actual(tmp_path,parent=parent,marker=marker,receipts=receipts) as f:
  first=commission(f);second=commission(f)
  assert first==second
  assert f.flow.journal.row('runtime_actions',f.source.episode_id,0)['result'] is None
  assert f.flow.journal.row('runtime_actions',f.source.episode_id,0)['credit'] is None

@pytest.mark.parametrize('parent,marker,receipts',ROWS,ids=IDS)
def test_new_index_keeps_distinct_original_identity(tmp_path,parent,marker,receipts):
 with actual(tmp_path,parent=parent,marker=marker,receipts=receipts) as f:
  first=commission(f,0);second=commission(f,1)
  assert first['child_id']!=second['child_id'] and first['path_raw']!=second['path_raw']
  assert first['assignment']==second['assignment']
  assert first['descriptor']==second['descriptor']
  assert first['owner_module']==second['owner_module'] and first['task_module']==second['task_module']
  assert first['binding_path']==second['binding_path']==f.parent_home+'/homology_job_monitoring'

@pytest.mark.parametrize('parent,marker,receipts',ROWS,ids=IDS)
def test_invalid_initial_form_is_not_executed_work(tmp_path,parent,marker,receipts):
 with actual(tmp_path,parent=parent,marker=marker,receipts=receipts) as f:
  before=raw_rows(f.flow);changed=deepcopy(f.selection);changed['initial_report_json']=json.dumps({'state':'invented'})
  with pytest.raises(module('communication').ReportBoundaryError):f.flow.selected(f.source,changed,0)
  assert raw_rows(f.flow)==before and f.jobs._row(f.job)['submission_requested']==0

@pytest.mark.parametrize('parent,marker',[(p,m) for p in ('annotation','improvement') for m in (False,True)],
 ids=[p+'-'+('declared' if m else 'markerless') for p in ('annotation','improvement') for m in (False,True)])
def test_selected_request_conflict_preserves_original_rows(tmp_path,parent,marker):
 with actual(tmp_path,parent=parent,marker=marker) as f:
  commission(f);before=raw_rows(f.flow);changed=deepcopy(f.selection);changed['goal']='Changed immutable commission'
  with pytest.raises(module('episode_journal').WorkflowError,match='reconstructed selected work changed'):
   f.flow.selected(f.source,changed,0)
  assert raw_rows(f.flow)==before

@pytest.mark.parametrize('parent,marker,receipts',ROWS,ids=IDS)
@pytest.mark.parametrize('redelivery',(False,True),ids=('initial','redelivery'))
def test_actual_parent_receiving_preserves_typed_progress(tmp_path,parent,marker,receipts,redelivery):
 with actual(tmp_path,parent=parent,marker=marker,receipts=receipts) as f:
  commissioned=commission(f);value={'state':'unresolved'}
  f.flow.progress_provider=module('episode_monitoring').ProgressProvider(f.store,f.flow.execution_backend,run_id=f.flow.run_id)
  f.flow.save_attempt(f.source.episode_id,0,'original-delivery',commissioned['child_id'],
   f.flow.selected(f.source,deepcopy(f.selection),0).child.request.report_contract,form=value)
  result=f.flow.receive_form(f.source,value,form(),0,redelivery=redelivery)
  before=raw_rows(f.flow)
  assert result==[] and f.flow.receive_form(f.source,value,form(),0,redelivery=redelivery)==result
  assert raw_rows(f.flow)==before and f.flow.progress_provider.received_progress_refs(f.source.episode_id)==[]

def test_nested_legacy_improvement_keeps_original_credit_error(tmp_path):
 with actual(tmp_path) as f:
  selection={'kind':'child','goal':'Unresolved inherited nested task','scope':deepcopy(f.scope),
   'purpose':'Retain the original missing task-credit boundary','schema_json':json.dumps(form()),
   'initial_report_json':json.dumps({'state':'unresolved'})}
  before=raw_rows(f.flow)
  with pytest.raises(ValueError,match='scientific_task_credit_not_declared:improvement'):
   f.flow.selected(f.source,selection,0)
  assert raw_rows(f.flow)==before


@pytest.mark.parametrize('role',('job_launch','job_results'),ids=('submission','acquisition'))
@pytest.mark.parametrize('parent,marker',[(p,m) for p in ('annotation','improvement') for m in (False,True)],
 ids=[p+'-'+('declared' if m else 'markerless') for p in ('annotation','improvement') for m in (False,True)])
def test_nonparticipant_job_child_keeps_original_assembler(tmp_path,monkeypatch,role,parent,marker):
 with actual(tmp_path,parent=parent,marker=marker,role=role) as f:
  if private():
   endpoint=module('legacy_'+parent+'.episode')
   def forbidden(*args,**kwargs):raise AssertionError('foreign job role selected monitor parent assembler')
   monkeypatch.setattr(endpoint,'assemble_'+parent+'_homology_monitor_request',forbidden)
  result=commission(f)
  assert json.loads(result['path_raw'])[-1]==[role,'child_0']
  assert f.jobs._row(f.job)['submission_requested']==0

@pytest.mark.parametrize('parent',('annotation','improvement'),ids=('annotation','improvement'))
def test_original_receipt_parent_conflict_rolls_back_commission(tmp_path,parent):
 with actual(tmp_path,parent=parent,receipts=True) as f:
  other=f.flow.build(parent,'other-parent','A distinct existing parent.',f.scope)
  identity=module('runtime').Episode.identity(f.flow.context,f.flow.grains['job_monitor'],'child_0',parent_path=f.source.path)
  f.flow.receipts.bind(identity.episode_id,other.source.episode_id)
  before=raw_rows(f.flow)
  with pytest.raises(ValueError,match='episode_receipt_parent_changed'):f.flow.selected(f.source,deepcopy(f.selection),0)
  assert raw_rows(f.flow)==before
  assert f.flow.journal.row('runtime_actions',f.source.episode_id,0) is None
  assert f.flow.journal.row('runtime_episodes',identity.episode_id) is None
