"""Retain one actual scripted C1/worker/C4 proof from the isolated code pin."""
import asyncio
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from method_loop.durable import DurableExecutionStore, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.literature_controlled_response_storage import LiteratureControlledResponseRepository
from gene_annotation_episode.literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_journal import Journal
from literature_controlled_response_worker_fixture_095 import make_case, run_case, module_imports
from test_literature_controlled_response_consumer import READONLY

BASE=Path(__file__).resolve().parent
PIN=BASE/'coherent_code_001'
DIRECTORY=BASE/'retained_worker_001'
assert not DIRECTORY.exists()
DIRECTORY.mkdir()
manifest=json.loads((BASE/'COHERENT_CODE_MANIFEST_001.json').read_text())
assert module_imports()['runtime_implementation_sha256']==manifest['runtime_implementation_sha256']


def alternatives(fixture):
    for state,key in [('unknown','unknown scope / β'),('conflicting','conflicting scope : γ')]:
        companion=deepcopy(fixture.args['companion_readings'][0]);companion['reading_key']=key
        fixture.args['companion_readings'].append(companion)
        nomination=deepcopy(fixture.args['joint_reading_assignments'][0])
        nomination['assignment']['protein_condition1']=key
        nomination['admissibility']={'value':state,'witnesses':[] if state=='unknown' else [
            fixture.witness('nmol/min'),fixture.witness('Construct: protein X.')]}
        fixture.args['joint_reading_assignments'].append(nomination)
        scope=deepcopy(fixture.args['joint_scopes'][0]);scope['assignment_index']=len(fixture.args['joint_scopes'])
        fixture.args['joint_scopes'].append(scope)


store,case=make_case(DIRECTORY/'state',unresolved=True,alter_fixture=alternatives,
    names=['controlled_response_difference','local_difference'],views=['conditional','local_difference'])
try:
    summary,provider,controllers=asyncio.run(run_case(store,case,DIRECTORY/'run',durable=True,child_actions=3))
    assert summary['credit']==0 and summary['pending_handles']==[]
    spec=json.loads(store.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()[0])
    backend=DurableExecutionStore(DIRECTORY/'run/episode-execution')
    returned=backend.load_return(spec['handle'],backend.status(spec['handle'])['return_id'])
    admission=json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
    assert returned['outcome']=='closed' and returned['failure'] is None and returned['completion']['units_consumed']==3
    assert admission['state']=='admitted' and admission['report']==returned['form']
    form=returned['form'];rows=form['requested_response']
    assert [r['component_key'] for r in rows]==['local:condition0-real:difference',*[
        'joint:'+str(i)+':controlled_response_difference' for i in range(4)]]
    joint=[r for r in rows if r['kind']=='conditional']
    assert [r['joint_scope_context']['effective_admissibility'] for r in joint]==['compatible','compatible','unknown','conflicting']
    assert joint[0]['cell']['value']==joint[1]['cell']['value'] and joint[0]['component_key']!=joint[1]['component_key']
    assert all(r['cell']['value'] is None for r in joint[2:])
    assert all(r['native_reading'] is None and r['reported_uncertainty'] is None for r in rows)
    parent_state=next(state for state in provider.contexts if state.get('child_reports'))
    assert parent_state['child_reports']==[form]
    parent_text=provider.presented[-1]
    worker_texts=json.loads((DIRECTORY/'run/worker095-presentation.json').read_text())
    assert len(worker_texts)==4 and all(CONTROLLED_RESPONSE_TASK in text for text in worker_texts)
    assert REFERENCE_PARENT_TASK in parent_text and CONTROLLED_RESPONSE_TASK not in parent_text
    for text in [parent_text,worker_texts[-1]]:
        steering=text.split('\n\nSTEERING\n',1)[1]
        for hidden in ('component_key','sheet_ref','raw:','protein_condition1_response','contrast_variance'):
            assert hidden not in steering
        assert all(r['sheet_ref'] not in steering for r in rows)
    run=spec['run_id'];parent=spec['parent']['episode_id'];child=spec['child']['episode_id']
    observations=[list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    assert len(observations)==6 and all(score==0 for controller in controllers.values for score in controller.scores)
    assert not store.list('observation') and not store.list('assessment')
    repository=LiteratureControlledResponseRepository(store,run,evidence_origin='synthetic_fixture')
    request=json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',(parent,)).fetchone()[0])
    context=BindingContext(run,parent,'annotation',spec['parent']['path'],case['scope'],{},request,
        tuple(EpisodeReceipts(store,run).known(parent)))
    assert repository.received_cells(context)==rows
    action=store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')='literature.controlled_response.source_v3.populate'").fetchone()
    original=json.loads(store.db.execute('SELECT outcome FROM literature_controlled_response_operations').fetchone()[0])
    runtime=json.loads(action['result']);assert 'pending_work_after_action' in runtime
    assert {k:v for k,v in runtime.items() if k!='pending_work_after_action'}==original
    runtime_binding=dict(store.db.execute('SELECT * FROM '+repository.runtime_binding_table).fetchone())
    saved=repository.read(rows[0]['sheet_ref'])
    def forbidden(*a,**kw):raise AssertionError('admission replay callback invoked')
    contract=spec['child']['request']['report_contract']
    receiver=ReceiverBindingV1(store,Journal(store,run),0,
        TypedReportContract(contract['decision'],contract['measurements']['schema'],forbidden),
        forbidden,forbidden,forbidden,forbidden)
    before=store.db.total_changes
    assert admit_return(spec,returned,receiver)==admission and store.db.total_changes==before
    fixture={'run':run,'parent':parent,'path':spec['parent']['path'],'scope':case['scope'],
        'known':list(context.received_record_refs),'sheet':rows[0]['sheet_ref'],
        'keys':[r['component_key'] for r in rows],'admitted':rows,'bindings':repository.semantic_bindings(rows),
        'banned':[store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']], 'observations':observations}
    (DIRECTORY/'READONLY_INPUT.json').write_text(json.dumps(fixture,indent=2)+'\n')
    (DIRECTORY/'C1_C4_EVIDENCE.json').write_text(json.dumps({'spec':spec,'returned':returned,'admission':admission,
        'runtime_binding':runtime_binding,'observations':observations,'summary':summary,
        'interpretation_limit':'The scripted parent commits a fixed source-subject anchor. This proves delivery to a later parent decision, not substantive scientific use of the numerical distinctions.'},indent=2)+'\n')
    (DIRECTORY/'PARENT_PRESENTATION.txt').write_text(parent_text)
    (DIRECTORY/'PARENT_IMPORTS.json').write_text(json.dumps(module_imports(),indent=2)+'\n')
finally:store.close()

environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(PIN/'tests')+os.pathsep+str(PIN)}
readonly=subprocess.run([sys.executable,'-c',READONLY,str(DIRECTORY/'state'),str(DIRECTORY/'READONLY_INPUT.json')],
    cwd=PIN,env=environment,text=True,capture_output=True)
(DIRECTORY/'READONLY_STDOUT.txt').write_text(readonly.stdout)
(DIRECTORY/'READONLY_STDERR.txt').write_text(readonly.stderr)
assert readonly.returncode==0,readonly.stdout+readonly.stderr
proof=json.loads(readonly.stdout);assert proof['total_changes']==0 and proof['first_projection']==rows
worker_imports=json.loads((DIRECTORY/'run/worker095-imports.json').read_text())
assert worker_imports['runtime_implementation_sha256']==manifest['runtime_implementation_sha256']
assert all(Path(row['path']).is_relative_to(PIN) for name,row in worker_imports['modules'].items()
    if name.startswith(('gene_annotation_episode','method_loop')))
assert all(hashlib.sha256((PIN/path).read_bytes()).hexdigest()==sha for path,sha in manifest['files'].items())
(DIRECTORY/'RESULT.json').write_text(json.dumps({'status':'passed','source_scopes':['compatible','compatible','unknown','conflicting'],
    'exact_returned_components':5,'equal_valued_distinct_alternatives_preserved':True,'actual_controller_observations':6,
    'first_fresh_readonly_changes':0,'admission_replay_callbacks_called':False,
    'runtime_implementation_sha256':manifest['runtime_implementation_sha256'],
    'actual_worker_repository_imports':len(worker_imports['modules']),
    'environment':{name:importlib.metadata.version(name) for name in ('Pillow','jsonschema','pytest')},
    'evidence_class':'actual selected scripted engineering C1/worker/C4 and saved-only proof, not model-backed science'},indent=2)+'\n')
print('Retained scripted095 original-worker/typed-scope/read-only proof passed.')
