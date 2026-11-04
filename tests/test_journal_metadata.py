"""Repeated contract schemas stay complete without growing every SQL row."""
import json
import sqlite3

import pytest

from gene_annotation_episode.decision_exchanges import DecisionExchanges
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_journal import Journal,WorkflowError
from gene_annotation_episode.journal_metadata import MARKER,ROOT_FLAG,MEDIA_TYPE
from gene_annotation_episode.state import Store
from method_loop.durable import canonical


def request(index=0):
    catalog={'source':{'meaning':'Contract metadata only; no biological claim. β',
        'report_schema':{'description':'schema field '*12000}}}
    return {'context':{'available_report_facts':catalog,
        'scope':{'subject_refs':['engineering-target']},'tools':[{'name':'context.fusion'}],
        'last_local_outcome':{'index':index}},'contract_information':{'facts_by_role':catalog},
        'schema':{'type':'object'},'decision_protocol':'engineering-control'}


def test_large_metadata_is_interned_and_all_store_readers_keep_original_json(tmp_path):
    with Store(tmp_path/'state') as store:
        journal=Journal(store,'metadata-control')
        for index in range(20):
            payload=request(index)
            journal.save('runtime_model_calls',{'episode_id':'episode','call_index':index,
                'purpose':'decision','request':canonical(payload)})
            assert json.loads(journal.row('runtime_model_calls','episode',index)['request'])==payload
        row=store.db.execute('SELECT request FROM runtime_model_calls WHERE call_index=3').fetchone()
        assert isinstance(row,sqlite3.Row) and json.loads(row[0])==request(3)
        inline=store.db.execute("SELECT json_extract(request,'$.context.tools[0].name') FROM runtime_model_calls LIMIT 1").fetchone()[0]
        assert inline=='context.fusion'
        assert store.db.execute('SELECT count(*) FROM artifacts WHERE media_type=?',(MEDIA_TYPE,)).fetchone()[0]==2
        with sqlite3.connect(store.path/'state.sqlite3') as raw:
            packed=raw.execute('SELECT request FROM runtime_model_calls LIMIT 1').fetchone()[0]
        assert len(packed)<2000 and json.loads(packed)[ROOT_FLAG] is True


def test_exchange_replay_and_reopened_store_preserve_exact_contract_identity(tmp_path):
    path=tmp_path/'state'
    payload=request()
    exchange={'instructions':'Preserve the supplied contract.','context':payload['context'],
        'output_schema':payload['schema'],'restoration':{'snapshot':payload}}
    with Store(path) as store:
        journal=Journal(store,'metadata-control')
        journal.save('runtime_model_calls',{'episode_id':'episode','call_index':0,
            'purpose':'decision','request':canonical(payload)})
        exchanges=DecisionExchanges(journal)
        first=exchanges.prepare('episode',0,0,exchange)
        assert first['request']==exchange
        assert exchanges.prepare('episode',0,0,exchange)==first
    with Store(path) as store:
        exchanges=DecisionExchanges(Journal(store,'metadata-control'))
        assert exchanges.rows('episode',0)[0]['request']==exchange
        assert exchanges.prepare('episode',0,0,exchange)['request']==exchange
        with pytest.raises(WorkflowError,match='request_identity_conflict'):
            exchanges.prepare('episode',0,0,{**exchange,'instructions':'Different contract'})


def test_literal_metadata_marker_never_reads_an_unrelated_private_artifact(tmp_path):
    with Store(tmp_path/'state') as store:
        secret=store.artifact('Private data is not a contract schema.','text/plain')
        payload={'context':{'available_report_facts':{MARKER:secret}}}
        journal=Journal(store,'metadata-control')
        journal.save('runtime_model_calls',{'episode_id':'episode','call_index':0,
            'purpose':'decision','request':canonical(payload)})
        assert json.loads(journal.row('runtime_model_calls','episode',0)['request'])==payload
        assert store.count('observation')==0


def test_corrupt_metadata_artifact_is_an_error_without_substituting_a_schema(tmp_path):
    with Store(tmp_path/'state') as store:
        journal=Journal(store,'metadata-control')
        journal.save('runtime_model_calls',{'episode_id':'episode','call_index':0,
            'purpose':'decision','request':canonical(request())})
        digest=store.db.execute('SELECT sha256 FROM artifacts WHERE media_type=? LIMIT 1',(MEDIA_TYPE,)).fetchone()[0]
        (store.path/'artifacts'/digest[:2]/digest).write_text('corrupt')
        with pytest.raises(ContractError,match='artifact_digest_mismatch'):
            journal.row('runtime_model_calls','episode',0)
