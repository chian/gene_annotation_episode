"""Small real native jobs and their actual durable receiving interface."""
import time

import pytest

from gene_annotation_episode.local_example.fixture import prepare
from gene_annotation_episode.local_example.service import JobStore


def setup(tmp_path):
    prepare(tmp_path/'example',reads=12,read_length=1200,reference_length=16000,reads_per_block=4)
    return JobStore(tmp_path/'example')


def test_real_native_job_handoff_and_results_survive_launch_owner(tmp_path):
    store=setup(tmp_path)
    assert store.environment()['setup']=={'software':False,'inputs':False,'index':False}
    with pytest.raises(ValueError,match='setup_incomplete'): store.submit()
    store.configure(0,1); store.stage(); store.build_index()
    submitted=store.submit(); job=submitted['job_ref']; handoff=store.handoff(job)
    assert store.submit()['new_submission'] is False
    with pytest.raises(ValueError,match='handoff_fields'):
        store.check_handoff({**handoff,'progress_interface':'wrong_interface'})
    checked=store.check_handoff(handoff)
    assert checked['sample']['job_ref']==job
    store.close()
    receiver=JobStore(tmp_path/'example')
    try:
        started=time.monotonic()
        while receiver.receive(handoff)['state'] in ('submitted','running'):
            assert time.monotonic()-started<30
            time.sleep(.05)
        status=receiver.receive(handoff)
        assert status['state']=='succeeded',status
        assert status['completed_reads']==status['total_reads']==12
        for block in status['available_blocks']: receiver.extract(handoff,block,'test-results-owner')
        result=receiver.delivered_summary()
        assert result['input_reads']==12 and result['mapped_reads']==11
        assert result['primary_alignments']==11
        assert len(result['extracted_blocks'])==3
        assert receiver.db.execute('SELECT count(*) FROM detached_jobs').fetchone()[0]==1
    finally: receiver.close()


def test_handoff_cannot_resolve_wrong_job_or_workspace(tmp_path):
    store=setup(tmp_path)
    try:
        with pytest.raises(ValueError,match='job_reference'): store.receive({'job_ref':'job_wrong'})
        assert store.db.execute('SELECT count(*) FROM handoff_receipts').fetchone()[0]==0
    finally: store.close()
