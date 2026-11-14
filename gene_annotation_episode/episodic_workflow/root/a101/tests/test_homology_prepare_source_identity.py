"""Actual prepare method with real Store; parser port is an explicit control.

Only the installed source layout is exercised; the saved pre-native class copy
and its AST-dump hash pin were retired. No native process, parsed observations
or scientific score is produced or claimed by these metadata-capture controls.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from .. import homology_results as actual
from ..state import Store
from ..local_jobs import LocalJobPolicy

NAMES=('phmmer_format.py','phmmer_result_worker.py','phmmer_grading_worker.py',
       'hmmer_search_inputs.py','hmmer_search_grader.py','hmmer_graders.py')
LIBRARY=('hmmer_graders.py', 'hmmer_search_grader.py', 'hmmer_search_inputs.py', 'phmmer_format.py', 'phmmer_grading_values.py', 'phmmer_alignment_values.py')
sha=lambda data:hashlib.sha256(data).hexdigest()


def source_class(tmp_path,monkeypatch,epoch,calls):
    async def controlled_parser(function,directory,request,policy):
        assert function is actual._parse
        calls.append({'directory':str(directory),'request':request,'policy':policy})
        return {'native':{'controlled_boundary':True,'executed':False},
                'failure':{'code':'controlled_parser_boundary_not_executed'}}
    monkeypatch.setattr(actual,'run_cancellable_native',controlled_parser)
    if epoch!='installed':
        raise ValueError('unplanned_source_epoch:'+epoch)
    base=Path(actual.__file__).parent
    expected=sha(b''.join((base/('library' if name in LIBRARY else '')/name).read_bytes() for name in (*NAMES, 'phmmer_grading_values.py', 'phmmer_alignment_values.py')))
    return actual.HomologyResults,expected


def inputs(store,tmp_path):
    sequence='MKTAYIAKQRQISFVKSHFSRQ'
    query=store.create_problem(raw_sequence=sequence,molecule='protein')['subject_refs'][0]
    query_file=tmp_path/'query.faa';query_file.write_text('>controlled-query\n'+sequence+'\n')
    reference=tmp_path/'references.faa';reference.write_text('>controlled-reference\nMKTAYIAKQRQISFVKSHFSRQ\n')
    native=tmp_path/'controlled.stdout';native.write_text('# controlled capture: no native report and no observed alignments\n')
    supplied=actual.NativePhmmerInput(query,query_file,reference,native,tmp_path/'absent-hits.tbl',
        sha(reference.read_bytes()),'a'*64,{'kind':'controlled_capture_boundary_no_native_process'})
    return supplied,{'subject_refs':[query]},sha(sequence.encode())


@pytest.mark.parametrize('epoch',('installed',))
def test_actual_prepare_captures_source_identity_and_reuses_cache_without_claiming_results(tmp_path,monkeypatch,epoch):
    calls=[];cls,expected=source_class(tmp_path,monkeypatch,epoch,calls)
    with Store(tmp_path/'state') as store:
        supplied,scope,query_hash=inputs(store,tmp_path);adapter=cls(store,policy=LocalJobPolicy.from_config())
        first=asyncio.run(adapter.prepare(supplied,scope))
        first_row=store.db.execute('SELECT signature,body FROM homology_result_snapshots WHERE source_ref=?',(first,)).fetchone();first_body=json.loads(first_row['body'])
        assert len(calls)==1 and calls[0]['request']['expected_query_sha256']==query_hash
        assert first_body['parser_implementation_sha256']==expected
        assert first_body['query_ref']==supplied.query_ref and first_body['database_sha256']==supplied.database_sha256
        assert first_body['parse_execution']['failure']['code']=='controlled_parser_boundary_not_executed'
        assert first_body['parse_execution']['native']=={'controlled_boundary':True,'executed':False}
        assert first_body['parse_inventory']=={'parsed_row_count':None,'native_error_count':None,'grading_error_count':None,'parser_finished':False}
        assert first_body['native_termination_seen'] is False
        second_inputs=replace(supplied,provenance={'kind':'controlled_second_capture_context','native_parameters':{'command':['controlled','not-executed']}})
        second=asyncio.run(adapter.prepare(second_inputs,scope))
        second_row=store.db.execute('SELECT signature,body FROM homology_result_snapshots WHERE source_ref=?',(second,)).fetchone();second_body=json.loads(second_row['body'])
        assert len(calls)==1 and first!=second and first_row['signature']==second_row['signature']
        assert first_body['execution_source_ref']!=second_body['execution_source_ref']
        assert second_body['native_parameters']=={'command':['controlled','not-executed']}
        assert second_body['parser_implementation_sha256']==expected
        assert store.count('observation')==store.count('assessment')==store.count('annotation')==0
        assert store.db.execute('SELECT count(*) FROM homology_parse_cache').fetchone()[0]==1


@pytest.mark.parametrize('epoch',('installed',))
def test_actual_prepare_rejects_changed_reference_before_parser(tmp_path,monkeypatch,epoch):
    calls=[];cls,_=source_class(tmp_path,monkeypatch,epoch,calls)
    with Store(tmp_path/'state') as store:
        supplied,scope,_=inputs(store,tmp_path);adapter=cls(store,policy=LocalJobPolicy.from_config())
        supplied.reference_fasta.write_text('>controlled-reference\nMCHANGED\n')
        with pytest.raises(actual.ContractError,match='native_reference_database_identity_changed') as caught:
            asyncio.run(adapter.prepare(supplied,scope))
        assert calls==[] and caught.value.detail['retained_source_ref']
        assert store.db.execute('SELECT count(*) FROM homology_result_snapshots').fetchone()[0]==0
        assert store.count('observation')==store.count('assessment')==store.count('annotation')==0
