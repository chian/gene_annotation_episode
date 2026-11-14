"""Original worker/receipt entry and failure boundaries, without worker execution.

These checks never call execute/run worker functions or main with a plan, create
a native lifecycle, verify a cgroup, calculate science, or restore saved work.
The optional byte-read control uses only pytest's own temporary file.
"""
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest

AXIS='gene_annotation_episode.episodic_workflow.root.a107'


def module(name):return importlib.import_module(AXIS+'.'+name)


@pytest.mark.parametrize('name,error',[
    ('flux_balance_result_worker','fba_worker_requires_one_absolute_plan_path'),
    ('genomic_overlap_result_worker','genomic_overlap_worker_plan_argument')])
def test_original_worker_entry_rejects_missing_plan_before_any_worker_call(name,error):
    worker=module('library.'+name)
    with pytest.raises(ValueError,match='^'+error+'$'):worker.main([])


def test_all_original_genomic_worker_public_contracts_have_one_actual_owner():
    worker=module('library.genomic_overlap_result_worker')
    for name in worker.__all__:assert hasattr(worker,name),name
    for name in ('RetainedFile','CapturedInputFile','NativeWorkerPlan','SavedWorkerPlan',
            'SetConversion','PairConversion','Diagnostics','WorkerOutput','WorkerResult'):
        assert getattr(worker,name).__module__==worker.__name__
    preparation=module('library.native_genomic_overlap_preparation')
    assert preparation.validate_genomic_overlap_result_worker_plan is worker.validate_genomic_overlap_result_worker_plan
    assert preparation.validate_genomic_overlap_result_worker_result is worker.validate_genomic_overlap_result_worker_result


def test_missing_fba_input_retains_original_unavailable_issue():
    worker=module('library.flux_balance_result_worker');issues=[]
    assert worker._read(None,'/sheet',issues) is None
    assert len(issues)==1 and issues[0]['code']=='artifact_missing'
    assert issues[0]['stage']=='capture' and issues[0]['field']=='/sheet'


def test_fba_changed_retained_bytes_are_not_read_as_usable_scientific_values(tmp_path):
    worker=module('library.flux_balance_result_worker')
    path=tmp_path/'declared-retained-byte-control.json';path.write_bytes(b'{"value":0}')
    retained={'path':str(path),'file':{'sha256':'0'*64,'size_bytes':path.stat().st_size}}
    issues=[];assert worker._read(retained,'/sheet',issues) is None
    assert len(issues)==1 and issues[0]['code']=='artifact_identity_conflict'
    assert path.read_bytes()==b'{"value":0}'


def test_genomic_missing_original_input_retains_private_original_failure_type():
    worker=module('library.genomic_overlap_result_worker')
    with pytest.raises(worker._SourceFailure) as error:
        worker._load(None,location={'field_path':'/sheet'},missing_code='input_unavailable',
            requirement='matching_file_identity',inodes={})
    assert type(error.value) is worker._SourceFailure
    assert error.value.failure['code']=='input_unavailable'
    assert error.value.failure['stage']=='capture' and error.value.failure['field_path']=='/sheet'


def receipt_owner():
    owner=SimpleNamespace(store=SimpleNamespace(),run_id='declared_receipt_fixture',native_genomic_overlap_returns=None)
    return module('genomic_overlap_result_receipts').GenomicOverlapResultReceipts(owner)


def test_restored_receipt_worker_absence_stays_distinct_from_a_capture():
    receipts=receipt_owner()
    absent={'worker_plan':None,'worker_capture':None,'worker_execution':None}
    assert receipts.validate_worker(absent) is None
    invalid=deepcopy(absent);invalid['worker_capture']={}
    with pytest.raises(ValueError,match='^genomic_overlap_result_authority_conflict$'):
        receipts.validate_worker(invalid)
    assert absent=={'worker_plan':None,'worker_capture':None,'worker_execution':None}


@pytest.mark.parametrize('reference',[None,7,'source_declared'])
def test_restored_private_reference_classifier_rejects_nonartifact_without_store_access(reference):
    assert receipt_owner().owns_reference(reference) is False


def test_restored_receipt_match_keeps_returned_failed_values_exact():
    owner=module('genomic_overlap_result_receipts')
    # This is a declared protocol comparison operand, not an authenticated
    # native receipt; match_outcome must preserve every original returned value.
    receipt={'facts':{owner.SAVED_SOURCE:[]},'host_failures':[{'fixture':'unavailable'}]}
    original=owner.outcome(receipt)
    assert owner.GenomicOverlapResultReceipts.match_outcome({'result':json.dumps(original)},receipt) is None
    changed=deepcopy(original);changed['result']['host_failures']=[]
    with pytest.raises(ValueError,match='^genomic_overlap_result_authority_conflict$'):
        owner.GenomicOverlapResultReceipts.match_outcome({'result':json.dumps(changed)},receipt)


def test_restored_staged_reader_requires_actual_action_ownership_first():
    with pytest.raises(ValueError,match='^genomic_overlap_result_authority_conflict$'):
        receipt_owner().read_staged(SimpleNamespace())
