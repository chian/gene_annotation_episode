"""Original336 passive read profiles; no native work or policy construction."""
from copy import deepcopy
from functools import lru_cache
import hashlib
from importlib import import_module
import json
from pathlib import Path
import sqlite3
import pytest

AXES=('a101','a105','a106','a108')
FIXTURE=Path(__file__).resolve().parent/'fixtures/retained_protein_reader_336'

@lru_cache(maxsize=1)
def original_receipts():
    database=FIXTURE/'state/state.sqlite3'
    assert hashlib.sha256(database.read_bytes()).hexdigest()=='efb35ce65a40b064ba9179b08c604779b9274a9da8cbe5311f2ae7fcd10609b7'
    db=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True);db.execute('PRAGMA query_only=ON')
    try:
        rows=[json.loads(r[0])['result'] for r in db.execute("SELECT result FROM runtime_actions WHERE result IS NOT NULL AND json_extract(result,'$.result.version')='native_protein_structure_acquired_result_v1' ORDER BY rowid")]
        assert len(rows)==3 and db.total_changes==0
        return rows
    finally:db.close()

def modules(axis,*,profile=False):
    prefix='gene_annotation_episode.episodic_workflow.root.'+axis+'.library.retained_input_authority.'
    return import_module(prefix+'native_protein_structure_contracts'),import_module(prefix+'retained_protein_read_profile') if profile else None

@pytest.mark.parametrize('axis',AXES)
def test_actual_original_plans_require_explicit_read_and_preserve_bytes(axis):
    contracts,_=modules(axis)
    for receipt in original_receipts():
        plan=deepcopy(receipt['body']['capture']['original_plan']);before=json.dumps(plan,sort_keys=True)
        with pytest.raises(ValueError,match='invalid_schema'):contracts.validate_protein_structure_run_plan(plan)
        result=contracts.validate_protein_structure_run_plan(plan,retained_read=True)
        assert result==plan and result is not plan and json.dumps(plan,sort_keys=True)==before
        assert contracts.validate_protein_structure_bundle(receipt['body']['bundle'],plan=plan,retained_read=True)==receipt['body']['bundle']

@pytest.mark.parametrize('axis',AXES)
def test_current_default_policy_document_is_unchanged(axis):
    contracts,_=modules(axis)
    assert contracts.POLICY=={'memory_bytes':21474836480,'scratch_bytes':4294967296}
    current=contracts.protein_structure_execution_schema('NativeProteinRunPlan')
    assert current==contracts.protein_structure_execution_schema('NativeProteinRunPlan',retained_read=False)
    policy=current['$defs']['NativeProteinRunPlan']['properties']['policy']
    assert policy=={'type':'object','properties':{'memory_bytes':{'const':21474836480},'scratch_bytes':{'const':4294967296}},'required':['memory_bytes','scratch_bytes'],'additionalProperties':False}
    # Explicit synthetic shape control: existing two-field current profile.
    plan=deepcopy(original_receipts()[0]['body']['capture']['original_plan']);del plan['policy']['wall_seconds']
    assert contracts.validate_protein_structure_run_plan(plan)==plan
    assert contracts.validate_protein_structure_run_plan(plan,retained_read=True)==plan

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('field,value',[
    ('memory_bytes',21474836481),('memory_bytes',float(21474836480)),
    ('scratch_bytes',True),('extra',None),('wall_seconds',0),('wall_seconds',False),('wall_seconds','unset')])
def test_changed_historical_plan_policy_is_rejected(axis,field,value):
    contracts,_=modules(axis);plan=deepcopy(original_receipts()[0]['body']['capture']['original_plan']);plan['policy'][field]=value
    before=json.dumps(plan,sort_keys=True)
    with pytest.raises(ValueError,match='invalid_schema'):contracts.validate_protein_structure_run_plan(plan,retained_read=True)
    assert json.dumps(plan,sort_keys=True)==before

@pytest.mark.parametrize('axis',AXES)
def test_actual_worker_profiles_are_passive_and_unchanged(axis):
    _,profile=modules(axis,profile=True)
    for receipt in original_receipts():
        metadata=deepcopy(receipt['body']['worker']['execution']['metadata']);before=json.dumps(metadata,sort_keys=True)
        assert profile.retained_protein_metadata_matches(metadata,released=True)
        assert json.dumps(metadata,sort_keys=True)==before
    current=deepcopy(metadata);del current['policy']['wall_seconds'];del current['enforcement']['wall_time'];del current['verified_cgroup']['runtime_max']
    assert profile.retained_protein_metadata_matches(current,released=True)

@pytest.mark.parametrize('axis',AXES)
@pytest.mark.parametrize('change',['missing_wall','changed_wall','missing_runtime','changed_runtime','float_memory','mixed_policy'])
def test_mixed_or_changed_worker_profile_is_rejected(axis,change):
    _,profile=modules(axis,profile=True);metadata=deepcopy(original_receipts()[0]['body']['worker']['execution']['metadata'])
    if change=='missing_wall':del metadata['enforcement']['wall_time']
    elif change=='changed_wall':metadata['enforcement']['wall_time']='configured'
    elif change=='missing_runtime':del metadata['verified_cgroup']['runtime_max']
    elif change=='changed_runtime':metadata['verified_cgroup']['runtime_max']='changed'
    elif change=='float_memory':metadata['verified_cgroup']['memory_max']=float(metadata['verified_cgroup']['memory_max'])
    else:del metadata['policy']['wall_seconds']
    before=json.dumps(metadata,sort_keys=True)
    assert profile.retained_protein_metadata_matches(metadata,released=True) is False
    assert json.dumps(metadata,sort_keys=True)==before
