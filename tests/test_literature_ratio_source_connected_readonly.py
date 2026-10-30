"""True durable C1/worker/C4 and first fresh mode=ro subset projection.

All inputs, choices and finite controller seams are constructed engineering
fixtures. No inserted runtime form/receipt or scientific model is used.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode.runtime import TypedReportContract
from method_loop.durable import DurableExecutionStore
from literature_ratio_source_worker_fixture_077 import make_case, run_case

READONLY = r'''
import json,sqlite3,sys
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode import literature_ratio_source_inputs as inputs
from gene_annotation_episode import literature_ratio_source_calculations as calculations
from gene_annotation_episode import providers
fixture=json.loads(Path(sys.argv[2]).read_text())
def forbidden(*a,**kw):raise AssertionError('forbidden source/image/model/population/receive/mutation/credit/observation')
store=Store.__new__(Store);store.path=Path(sys.argv[1]);store._savepoint=0
store.db=sqlite3.connect(store.path.joinpath('state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)
store.db.row_factory=sqlite3.Row
store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record',2,store._scope_filter_record)
get=store.get_artifact;reads=[]
def saved_only(ref):
 if ref in fixture['banned']:raise AssertionError('original source/image bytes accessed')
 reads.append(ref);return get(ref)
store.get_artifact=saved_only
for name in ('artifact','put','transaction','register_material','parse_material'):setattr(store,name,forbidden)
inputs.read_relative_signal_source_inputs=forbidden
calculations.populate_relative_signal_v2=forbidden
Image.open=forbidden;providers.ModelConnection=forbidden
repo=LiteratureRatioSourceRepository(store,fixture['run'],evidence_origin='synthetic_fixture')
repo.receive_cells=forbidden
context=SimpleNamespace(run_id=fixture['run'],episode_id=fixture['parent'],role='annotation',assignment={},
 scope=fixture['scope'],received_record_refs=fixture['known'])
assert store.db.total_changes==0
# FIRST projection in this process; no previous read or repair/cache warmup.
actual=repo.fact_cells(context,[fixture['sheet']],components=['reported_ratio'])
assert actual==fixture['admitted']
assert repo.fact_cells(context,[fixture['sheet']],components=['difference_from_reference'])==[]
assert repo.received_cells(context)==actual
repo.validate_fact_values(context,actual)
observations=[list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
assert observations==fixture['observations']
assert store.db.total_changes==0
print(json.dumps({'evidence_class':'actual connected scripted077 C1/worker/C4; no scientific model',
 'mode':'ro','query_only':store.db.execute('PRAGMA query_only').fetchone()[0],'total_changes':store.db.total_changes,
 'first_projection':actual,'observation_identities_unchanged':True,'observation_count':len(observations),
 'source_image_decoder_model_population_receive_mutation_called':False,'saved_artifact_read_count':len(reads),
 'storage_import':__import__('gene_annotation_episode.literature_ratio_source_storage',fromlist=['']).__file__}))
store.close()
'''


@pytest.mark.parametrize('interrupt_receive',[False,True])
def test_actual_durable_commission_c4_recovery_replay_parent_and_first_readonly(tmp_path,monkeypatch,interrupt_receive):
    store,case=make_case(tmp_path/'state');directory=tmp_path/'run'
    original_service=WorkflowServices.literature_ratio_source_repository
    injected=[]
    if interrupt_receive:
        def service(self,**kw):
            repo=original_service(self,**kw)
            if not hasattr(repo,'_fixture_interrupt_installed'):
                repo._fixture_interrupt_installed=True
                original=repo.receive_cells
                def receive(context,rows,key):
                    original(context,rows,key)
                    if context.role=='annotation' and not injected:
                        injected.append(key)
                        raise OSError('constructed interruption after actual native receive')
                repo.receive_cells=receive
            return repo
        monkeypatch.setattr(WorkflowServices,'literature_ratio_source_repository',service)
    try:
        if interrupt_receive:
            with pytest.raises(OSError,match='after actual native receive'):
                asyncio.run(run_case(store,case,directory,durable=True))
            assert injected
            assert store.db.execute('SELECT count(*) FROM literature_ratio_source_received').fetchone()[0]==0
            installed=store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_return_admissions'").fetchone()
            assert not installed or store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0]==0
            assert store.db.execute('SELECT count(*) FROM literature_ratio_source_operations').fetchone()[0]==1
        result,provider,_=asyncio.run(run_case(store,case,directory,durable=True,resume=interrupt_receive))
        assert result['credit']==0 and result['pending_handles']==[]
        spec=json.loads(store.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()[0])
        backend=DurableExecutionStore(directory/'episode-execution')
        returned=backend.load_return(spec['handle'],backend.status(spec['handle'])['return_id'])
        assert returned['outcome']=='closed' and returned['failure'] is None
        assert returned['completion']['units_consumed']==2
        assert spec['child']['request']['message']['episode_assignment']['requested_ratio_source_components']==['reported_ratio']
        assert '$ref' in spec['child']['request']['message']['report_contract_declaration']['submitted_schema_json']
        parent=spec['parent']['episode_id'];child=spec['child']['episode_id'];run=spec['run_id']
        form,=provider.contexts[-1]['child_reports'];rows=form['requested_signal'];row,=rows
        assert row['component']=='reported_ratio' and row['value']==.64
        assert provider.contexts[-1]['visual_evidence']==[]
        steering=provider.presented[-1].split('\n\nSTEERING\n',1)[1]
        assert 'K426A' in steering and '128.000' not in steering and '200.000' not in steering
        attempt,=store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['parent_episode_id']==parent and attempt['child_episode_id']==child and attempt['failure'] is None
        assert json.loads(attempt['form'])==returned['form']==form
        receipt,=store.db.execute('SELECT * FROM literature_ratio_source_received')
        assert receipt['operation_key']==run+':'+parent+':0:typed_form' and json.loads(receipt['cells'])==rows
        bound,=store.db.execute('SELECT * FROM literature_ratio_source_delivery_bindings')
        repo=LiteratureRatioSourceRepository(store,run,evidence_origin='synthetic_fixture')
        assert bound['cells_digest']==repo._delivery_digest(rows)
        identities=[]
        for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index'):
            value=json.loads(r['observation']);identities.append((r['episode_id'],r['unit_index'],value['decision_index'],value['label']))
        assert sorted(identities)==sorted([(parent,0,1,'wait:1'),(parent,1,0,'child_0'),(parent,2,2,'reason:2'),
            (child,0,0,'tool:0'),(child,1,1,'tool:1')])
        assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0]==1
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0]==1
        assert not store.list('observation') and not store.list('assessment')
        def forbidden(*a,**kw):raise AssertionError('admission replay invoked callback')
        contract=spec['child']['request']['report_contract']
        typed=TypedReportContract(contract['decision'],contract['measurements']['schema'],forbidden)
        from gene_annotation_episode.episode_journal import Journal
        receiver=ReceiverBindingV1(store,Journal(store,run),0,typed,forbidden,forbidden,forbidden,forbidden)
        admission=json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        before=store.db.total_changes
        assert admit_return(spec,returned,receiver)==admission
        assert store.db.total_changes==before
        saved=repo.read(row['sheet_ref'])
        banned={store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']}
        banned.update(value for view in saved['extraction']['views'] for key,value in view['metadata'].items()
            if key in ('original_artifact_ref','image_artifact_ref'))
        fixture={'run':run,'parent':parent,'scope':plain_scope(case['scope']),
            'known':list(EpisodeReceipts(store,run).known(parent)),'sheet':row['sheet_ref'],'admitted':rows,
            'banned':list(banned),'observations':[list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]}
        manifest=tmp_path/'actual-connected077.json';manifest.write_text(json.dumps(fixture))
        (tmp_path/'CONNECTED_PROOF.json').write_text(json.dumps({'spec':spec,'returned':returned,'admission':admission,
            'observation_identities':identities,'parent_steering':steering,'evidence_class':'constructed engineering fixture'},indent=2))
        store.close()
        process=subprocess.run([sys.executable,'-c',READONLY,str(tmp_path/'state'),str(manifest)],
            text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',
                'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
        (tmp_path/'READONLY_STDOUT.txt').write_text(process.stdout)
        (tmp_path/'READONLY_STDERR.txt').write_text(process.stderr)
        assert process.returncode==0,process.stdout+process.stderr
        proof=json.loads(process.stdout)
        assert proof['total_changes']==0 and proof['first_projection']==rows
        assert proof['observation_count']==5
    finally:store.close()


def plain_scope(scope):return json.loads(json.dumps(scope))
