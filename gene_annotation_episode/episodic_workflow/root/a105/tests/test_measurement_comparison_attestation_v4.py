"""Finite comparison attestation controls; original retained data are never rewritten."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import pytest
from ..library import literature_measurement_comparison_storage as storage
from ..state import Store

HERE=Path(__file__).resolve().parent
AUTH=json.loads((HERE/'fixtures/comparison_attestation_authority.json').read_text())
ARCHIVE=HERE/'fixtures/retained_reference/a105_measurement_comparison_binding_268'
SAVED=ARCHIVE/'pytest_003/test_actual_parent_converted_s0/state'
FORM=ARCHIVE/'ORIGINAL_FORM_268.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

@pytest.fixture
def pure_repository():
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    try:yield storage.LiteratureMeasurementComparisonRepository(SimpleNamespace(db=db),'pure-pin-control')
    finally:db.close()

def test_current_v4_authenticates_original_proven_equivalent_twenty(pure_repository):
    receipt=pure_repository._original_implementation()
    assert receipt['version']=='measurement_comparison_original_implementation_v4'
    assert receipt['bound_descriptor'] is None
    assert list(receipt['files'])==AUTH['prospective_roster']
    for name,h in AUTH['prospective_pure_pins'].items():
        assert receipt['files'][name]==h==sha(storage.source_file(name).read_bytes())

@pytest.mark.parametrize('logical_name',list(AUTH['prospective_pure_pins']))
def test_every_v4_pure_dependency_rejects_unapproved_bytes(pure_repository,tmp_path,monkeypatch,logical_name):
    assert pure_repository._original_implementation()['version']=='measurement_comparison_original_implementation_v4'
    actual=storage.source_file;altered=tmp_path/logical_name
    altered.write_bytes(actual(logical_name).read_bytes()+b'\n# controlled unapproved dependency change\n')
    monkeypatch.setattr(storage,'source_file',lambda name:altered if name==logical_name else actual(name))
    with pytest.raises(storage.ContractError,match='measurement_comparison_prospective_dependency_mismatch'):
        pure_repository._original_implementation()

def test_original_three_pin_maps_and_version_specific_rosters_remain_exact():
    for name,value in AUTH['historical_pure_maps'].items():assert getattr(storage,name)==value
    for version in ('measurement_comparison_original_implementation_v1','measurement_comparison_original_implementation_v2','measurement_comparison_original_implementation_v3'):
        assert storage._RECEIPT_ROSTERS[version]==(tuple(AUTH['original_roster']),)
    assert storage._RECEIPT_ROSTERS['measurement_comparison_original_implementation_v4']==(tuple(AUTH['prospective_roster']),)

@pytest.fixture
def historical_repository(monkeypatch):
    before={str(p.relative_to(ARCHIVE)):sha(p.read_bytes()) for p in ARCHIVE.rglob('*') if p.is_file()}
    assert before==AUTH['retained_fixture_files']
    assert not any((SAVED/('state.sqlite3'+suffix)).exists() for suffix in ('-wal','-shm','-journal'))
    store=Store.__new__(Store);store.path=SAVED;store._savepoint=0
    store.db=sqlite3.connect((SAVED/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=ON')
    archived_form=json.loads(FORM.read_bytes())
    try:
        # The retained standalone003 Store and shared-loop005 form are distinct
        # publications. Authenticate the actual standalone operation first;
        # only its top-level sheet identity may differ from the saved row oracle.
        row,=list(store.db.execute('SELECT run_id,episode_id,operation_key,signature,outcome FROM literature_measurement_comparison_operations'))
        assert (row['run_id'],row['episode_id'],row['operation_key'])==('comparison268','child268','selected268')
        outcome=json.loads(row['outcome']);assert outcome['status']=='completed'
        ref=outcome['result']['sheet_ref'];cells=outcome['result']['cells']
        assert len(cells)==len(archived_form['numbers'])==4
        assert len({cell['sheet_ref'] for cell in archived_form['numbers']})==1
        assert all(cell['sheet_ref']==ref for cell in cells)
        dump=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        assert dump([{key:value for key,value in cell.items() if key!='sheet_ref'} for cell in archived_form['numbers']])==dump([{key:value for key,value in cell.items() if key!='sheet_ref'} for cell in cells])
        form=deepcopy(archived_form)
        for cell in form['numbers']:cell['sheet_ref']=ref
        assert dump(form['numbers'])==dump(cells)
        request=json.loads(row['signature'])
        assert request['run_id']==row['run_id'] and request['episode_id']==row['episode_id'] and request['operation_key']==row['operation_key']
        repository=storage.LiteratureMeasurementComparisonRepository(store,row['run_id'])
        source=store.get(ref);allowed={source['artifact_ref'],source['request_ref']};get=store.get_artifact;reads=[]
        def saved_only(key):
            assert key in allowed,'Original source reacquisition/calculation input access forbidden'
            reads.append(key);return get(key)
        def forbidden(*args,**kwargs):raise AssertionError('Historical read must not republish/recalculate')
        monkeypatch.setattr(store,'get_artifact',saved_only)
        for name in ('artifact','put','create_problem'):monkeypatch.setattr(store,name,forbidden)
        monkeypatch.setattr(repository,'_original_implementation',forbidden)
        monkeypatch.setattr(storage,'_project_once',forbidden)
        yield repository,ref,form,source,request
        assert set(reads)==allowed and store.db.total_changes==0
    finally:
        assert store.db.total_changes==0
        store.close()
        assert before=={str(p.relative_to(ARCHIVE)):sha(p.read_bytes()) for p in ARCHIVE.rglob('*') if p.is_file()}

def test_actual_original_v1_saved_read_and_exact_rows_without_source_reacquisition(historical_repository):
    repository,ref,form,source,request=historical_repository
    saved=repository.read(ref);receipt=saved['original_implementation']
    assert receipt['version']=='measurement_comparison_original_implementation_v1'
    assert receipt['bound_descriptor'] is None and set(receipt['files'])==set(AUTH['original_roster'])
    assert all(receipt['files'][n]==h for n,h in AUTH['historical_pure_maps']['_PURE_HASHES'].items())
    assert repository.project_cells([ref],permitted_record_refs=[ref],components=[r['component'] for r in form['numbers']])==form['numbers']
    assert saved['source_metadata'][saved['input_source_ref']]['artifact_ref']==saved['input_artifact_ref']
    assert request['operation_key'] and form['limit']=='source_qualifications_retained'

@pytest.mark.parametrize('mutation',['unknown_version','changed_pure_hash','extra_file','missing_file','changed_descriptor'])
def test_actual_saved_read_rejects_changed_receipt_metadata_without_saved_writes(historical_repository,monkeypatch,mutation):
    repository,ref,form,source,request=historical_repository
    original=repository.read(ref);altered=deepcopy(original)
    receipt=altered['original_implementation']
    if mutation=='unknown_version':receipt['version']='unrecognized-comparison-epoch'
    elif mutation=='changed_pure_hash':receipt['files']['literature_measurement_comparison_inputs.py']='0'*64
    elif mutation=='extra_file':receipt['files']['unowned_extra.py']='0'*64
    elif mutation=='missing_file':del receipt['files']['literature_measurement_comparison_inputs.py']
    elif mutation=='changed_descriptor':receipt['bound_descriptor']={'binding_id':'unrelated-publisher'}
    original_json=repository._json
    # Explicit saved-reader metadata seam; never a fabricated historical Store or artifact.
    monkeypatch.setattr(repository,'_json',lambda key:deepcopy(altered) if key==source['artifact_ref'] else original_json(key))
    with pytest.raises(storage.ContractError,match='measurement_comparison_saved_binding_mismatch'):
        repository.read(ref)
    assert original['original_implementation']!=altered['original_implementation']

@pytest.mark.parametrize('variance_status',['known','estimated'])
def test_current_table_publication_retains_uncertainty_action_and_cold_read(tmp_path,variance_status):
    from .test_literature_measurement_comparison_binding_268 import setup,selected
    components=['native_left','protocol_difference','protocol_ratio','difference_variance']
    store,context,args,binding,_=setup(tmp_path,components=components,table=True,covariance=[[4,1],[1,9]],variance_status=variance_status)
    try:
        current,outcome,rows=selected(store,context,args,binding,key='same-original-comparison-control')
        assert outcome['status']=='completed'
        by_name={r['component']:r for r in rows}
        assert by_name['protocol_difference']['cell']['value']==-2 and by_name['difference_variance']['cell']['value']==11
        uncertainty=by_name['difference_variance']['cell']['uncertainty']
        assert uncertainty['variance_status']==variance_status
        assert uncertainty['sampling_distribution']=='not_assumed'
        assert by_name['difference_variance']['cell']['interpretation']=='protocol_difference_uncertainty_'+variance_status+'_covariance'
        assert all(row['assertion_context']['molecule']['status']=='not_selected' for row in rows)
        repository=binding._measurement_comparison_repository();ref=outcome['result']['sheet_ref'];saved=repository.read(ref)
        assert saved['original_implementation']['version']=='measurement_comparison_original_implementation_v4'
        assert saved['original_implementation']['bound_descriptor'] is None
        operation=store.db.execute('SELECT signature,outcome FROM literature_measurement_comparison_operations WHERE operation_key=?',('same-original-comparison-control',)).fetchone()
        assert json.loads(operation['signature'])['operation_key']=='same-original-comparison-control'
        assert json.loads(operation['outcome'])['operation_ref']==outcome['operation_ref']
        before=json.dumps(saved,sort_keys=True)
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    finally:store.close()
    cold=Store.__new__(Store);cold.path=tmp_path;cold._savepoint=0
    cold.db=sqlite3.connect((tmp_path/'state.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True);cold.db.row_factory=sqlite3.Row;cold.db.execute('PRAGMA query_only=ON')
    try:
        restored=storage.LiteratureMeasurementComparisonRepository(cold,context.run_id).read(ref)
        assert json.dumps(restored,sort_keys=True)==before and cold.db.total_changes==0
    finally:cold.close()

@pytest.mark.parametrize('version',['measurement_comparison_original_implementation_v1','measurement_comparison_original_implementation_v2','measurement_comparison_original_implementation_v3'])
def test_old_versions_do_not_accept_unproven_current_private_roster(historical_repository,monkeypatch,version):
    repository,ref,form,source,request=historical_repository
    original_json=repository._json;altered=deepcopy(original_json(source['artifact_ref']))
    pins=AUTH['historical_pure_maps'][{'measurement_comparison_original_implementation_v1':'_PURE_HASHES','measurement_comparison_original_implementation_v2':'_PURE_HASHES_V2','measurement_comparison_original_implementation_v3':'_PURE_HASHES_V3'}[version]]
    altered['original_implementation']={'version':version,'bound_descriptor':None,
      'files':{name:pins.get(name,'0'*64) for name in AUTH['prospective_roster']}}
    # Deliberate invalid in-memory reader operand, not an authenticated historical publication.
    monkeypatch.setattr(repository,'_json',lambda key:deepcopy(altered) if key==source['artifact_ref'] else original_json(key))
    with pytest.raises(storage.ContractError,match='measurement_comparison_saved_binding_mismatch'):
        repository.read(ref)
