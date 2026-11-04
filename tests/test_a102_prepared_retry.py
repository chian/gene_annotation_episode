"""Admission retry changes no scientific request or durable native handle."""
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.a102_tools import A102ToolRegistry
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobResult
from gene_annotation_episode.state import Store


def test_new_action_can_retry_the_same_prepared_work_without_resubmission(tmp_path,monkeypatch):
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='MAAA',molecule='protein')['subject_refs']
        tools=A102ToolRegistry(store,a102_work_directory=tmp_path/'native')
        scope={'subject_refs':[target]};context=SimpleNamespace(run_id='run',episode_id='episode')
        directory=tools.work_directory(context,'structure.bind',{'target_ref':target},scope)
        assert directory==tools.work_directory(context,'structure.bind',{'target_ref':target},scope)
        assert directory!=tools.work_directory(SimpleNamespace(run_id='run',episode_id='sibling'),
            'structure.bind',{'target_ref':target},scope)
        starts=[]
        def start(handle,**kwargs):
            starts.append(handle.read()['unit'])
            if len(starts)==1:raise AcquisitionError('local_resource_busy',phase='local_admission')
        def wait(handle,**kwargs):
            (directory/'worker-result.json').write_text(json.dumps({'status':'completed',
                'result':{'synthetic_lifecycle_fixture':True},'failure':None}))
            (directory/'stdout.log').write_text('');(directory/'stderr.log').write_text('')
            return LocalJobResult(0,directory/'stdout.log',directory/'stderr.log',{})
        monkeypatch.setattr('gene_annotation_episode.a102_tools.start_prepared',start)
        monkeypatch.setattr('gene_annotation_episode.a102_tools.wait_job',wait)
        with pytest.raises(AcquisitionError,match='local_resource_busy'):
            tools._job({'operation':'bind'},directory)
        original=(directory/'native-handle.json').read_bytes()
        result,_=tools._job({'operation':'bind'},directory)
        assert result=={'synthetic_lifecycle_fixture':True}
        assert starts[0]==starts[1]
        assert (directory/'native-handle.json').read_bytes()==original
