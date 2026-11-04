"""Actual synthetic custody -> actual caller baseline -> numerical zero-gain reads.

The source helper's only shared outputs are arguments/case_directory/configuration.
No original science, public HTTP, configured model transport or native work runs.
"""
import asyncio
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from jsonschema import Draft202012Validator, FormatChecker

from gene_annotation_episode import api_planning_case_policy as caller_policy
from gene_annotation_episode import independent_execution
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.case_execution import prepare_case_run, run_prepared_case
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.public_search_operations import hmmer_client_binding_sha256
from gene_annotation_episode.scientific_checkpoint_fork import prepare_scientific_checkpoint_fork
from gene_annotation_episode.state import Store
from test_api_planning_case_policy import parameters as caller_parameters
from test_scientific_checkpoint_fork import checkpoint_source_fixture


ROOT = Path(__file__).resolve().parents[1]
_LOCAL_PLAN = ROOT/'verification/scientific_checkpoint_custody_plan_2026-10-22_001'
PLAN = (_LOCAL_PLAN if (_LOCAL_PLAN/'SCHEMAS004.json').is_file() else
    Path('/home/chia/repos/gene_annotation_episode/verification/scientific_checkpoint_custody_plan_2026-10-22_001'))
SCHEMA_SHA = 'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'
CALLER_SHA = '4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f'
TEST_COST = 1000000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def forbidden(*_args, **_kwargs):
    raise AssertionError('Joined fixture cannot start a process, transport or public request')


def files(path):
    """Exact raw regular-file membership/hash/size/mode/mtime witness."""
    result = {}
    for item in sorted(Path(path).rglob('*')):
        assert not item.is_symlink()
        if item.is_file():
            stat = item.stat()
            result[str(item.relative_to(path))] = {'sha256': sha(item), 'bytes': stat.st_size,
                'mode': stat.st_mode & 0o777, 'mtime_ns': stat.st_mtime_ns}
    return result


@contextmanager
def readonly(path):
    db = sqlite3.connect(Path(path).as_uri()+'?mode=ro&immutable=1', uri=True)
    db.execute('PRAGMA query_only=ON')
    try:
        yield db
    finally:
        db.close()


def old_rows(db, run_id):
    return {table: [tuple(row) for row in db.execute(
        'SELECT * FROM '+table+' WHERE run_id=? ORDER BY rowid', (run_id,))]
        for table in ('runtime_runs','runtime_episodes','runtime_actions',
                      'runtime_model_calls','runtime_observations')}


def test_checkpoint_success_prepares_real_caller_without_recrediting_old_work(tmp_path, monkeypatch):
    monkeypatch.setattr('subprocess.run', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('asyncio.create_subprocess_exec', forbidden)
    monkeypatch.setattr('urllib.request.urlopen', forbidden)
    assert sha(PLAN/'SCHEMAS004.json') == SCHEMA_SHA
    schemas = json.loads((PLAN/'SCHEMAS004.json').read_text())
    def validate(kind, value):
        Draft202012Validator({'$ref':'#/$defs/'+kind,'$defs':schemas['$defs']},
            format_checker=FormatChecker()).validate(value)

    source_parent = tmp_path/'synthetic-source'; source_parent.mkdir()
    shared = checkpoint_source_fixture(source_parent)
    # Deliberately discard every private helper output; no private IDs/producers.
    arguments = deepcopy(shared['arguments'])
    case_directory = shared['case_directory']
    configuration = deepcopy(shared['configuration'])
    del shared
    old_run_id = arguments['source_run_id']
    source_root = arguments['source_implementation_root']
    source_before = files(source_root)
    with readonly(arguments['source_workspace']/'state.sqlite3') as db:
        historical = old_rows(db,old_run_id)
    case = json.loads((case_directory/'case.json').read_text())
    old_launch = json.loads((arguments['source_run_directory']/'case-launch.json').read_text())

    directory = tmp_path/'new-caller'; directory.mkdir()
    workspace = directory/'workspace'
    result = prepare_scientific_checkpoint_fork(**arguments,destination_workspace=workspace)
    validate('result',result)
    descriptor = result['receipt']
    receipt_path = Path(descriptor['path'])
    raw_receipt = receipt_path.read_bytes()
    assert sha(receipt_path)==descriptor['sha256'] and len(raw_receipt)==descriptor['bytes']
    receipt = json.loads(raw_receipt); validate('receipt',receipt)
    assert result['destination_workspace']==receipt['destination_workspace']==str(workspace)
    initial = result['initial_known_record_refs']
    assert initial==receipt['initial_known_record_refs']==sorted(set(
        receipt['caller_initial_known_record_refs'])|set(result['lineage_source_refs'].values()))
    assert hashlib.sha256(canonical(initial).encode()).hexdigest()==receipt['initial_known_record_refs_sha256']
    assert result['lineage_source_refs']=={'observations':receipt['lineage']['observation_source_ref'],
        'index':receipt['lineage']['index_source_ref']}
    assert receipt['source']['run_id']==old_run_id
    assert receipt['source']['implementation_sha256']==arguments['expected_source_implementation_sha256']
    assert receipt['source']['pending']['request_raw_utf8_sha256']==arguments['expected_pending_request_sha256']
    assert receipt['fixed_identity']['case_ref']==case['case_ref']
    for key in ('target_ref','problem_ref'):
        assert receipt['fixed_identity'][key]==case[key]==old_launch[key]
    assert receipt['fixed_identity']['target_sequence_sha256']==old_launch['target_sequence_sha256']
    assert receipt['fixed_identity']['target_sequence_artifact_ref']=='artifact_'+old_launch['target_sequence_sha256']
    committed_witness = receipt['checkpoint']['committed_reference_manifest']
    assert committed_witness['path']=='checkpoint/committed-references.json'
    committed_path=workspace/committed_witness['path']
    assert sha(committed_path)==committed_witness['sha256']
    assert committed_path.stat().st_size==committed_witness['bytes']
    committed=json.loads(committed_path.read_text());validate('committed_reference_manifest',committed)
    assert {r['reference'] for r in committed['records']}<=set(initial)
    assert len(committed['records'])==committed['input_count']+committed['record_count']
    checkpoint_path=workspace/receipt['checkpoint']['database']['path']
    assert checkpoint_path.stat().st_ino!=(workspace/'state.sqlite3').stat().st_ino
    assert sha(checkpoint_path)==receipt['checkpoint']['database']['sha256']
    immutable_before=files(workspace/'checkpoint')
    assert files(source_root)==source_before

    # New physical fixture resources cannot probe systemctl or execute /bin/true.
    executable=directory/'native-fixture-never-executed'
    shutil.copyfile(configuration['executable']['path'],executable)
    executable.chmod(0o600)
    configuration.update(workspace=str(workspace),history=str(directory/'statistics.sqlite'),
        local_jobs={'memory_bytes':20*1024**3,'scratch_bytes':4*1024**3},
        restoration={'preview_size':24,'model_presentation':'bounded_wait_history_v1'},
        public={'provider_access_dir':str(directory/'public-access'),'transport_timeout_seconds':90},
        local_tools={'native_receipts_dir':str(directory/'native-receipts'),
            'minimap2_cache_dir':str(directory/'minimap2-cache')},
        executable={'path':str(executable),'sha256':sha(executable)})
    configuration['models']={**load_config(),**configuration['models']}
    configuration['models']['FAST']={'model':'gpt-6-luna','reasoning_effort':'none'}
    configuration['models']['REASONING']={'model':'gpt-6-sol','reasoning_effort':'medium'}
    manifest=prepare_case_run(case_directory,directory,configuration,
        focus='Synthetic inherited-input custody/caller contract fixture; no biological inference.')
    assert manifest['registry_configuration']['registry_ref']!=old_launch['registry_configuration']['registry_ref']
    with readonly(directory/'native-jobs/jobs.sqlite') as db:
        assert db.execute('SELECT count(*) FROM orders').fetchone()[0]==0
    actual_client=PublicClients(timeout=90,access_dir=directory/'public-access')
    parameters=caller_parameters(directory,client=actual_client)
    parameters['services']['api_timing']['history_path']=manifest['configuration']['history']
    assert parameters['services']['public_search_registry']['client_binding_sha256']==hmmer_client_binding_sha256(actual_client)
    parameters['policy']['operational']['registry_ref']=manifest['registry_configuration']['registry_ref']
    parameters['policy']['scientific_progress']['initial_known_record_refs']=list(initial)
    parameters['policy']['controller']['cost']=TEST_COST
    assert parameters['policy']['controller']['window_size']==8
    assert parameters['policy']['controller']['subsample_size']==4
    assert parameters['policy']['controller']['uncertainty_alpha']==.05
    policy=caller_policy.create_policy(parameters)
    scope={'subject_refs':[manifest['target_ref']]}
    with Store(workspace) as store:
        assessments=store.query_records('assessment',scope,current_only=True)['records']
        assert len(assessments)==1
        chosen=assessments[0]['id']
        inherited_assessments=[ref for ref in initial if store.get(ref)['record_type']=='assessment']
        natives=[ref for ref in initial if store.get(ref)['record_type']=='native_execution']
        expected=policy.project_task_credit(store,scope,known_assessment_refs=inherited_assessments)
        assert expected['credit']>0 and chosen in initial and natives
        expected_native=policy.native_timing_information.read_details(store,scope,
            known_execution_refs=natives,initial_execution_refs=natives,details_limit=24,details_offset=0)
        assert expected_native['monitoring_information_credit']==0
        assert expected_native['native_execution_measurements']==[]
        assert old_rows(store.db,old_run_id)==historical
        native_count=store.count('native_execution')

    contexts=[]
    first_receipts=[]
    async def scripted(self,episode_id,role,instructions,context,output_schema):
        assert type(self) is ModelConnection and role=='REASONING'
        assert context['current_credit']==expected['credit']
        assert context['monitoring_information_credit']==0
        if not contexts:
            assert context['waiting_support']['own_completed_action_history']==[]
            with sqlite3.connect((workspace/'state.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
                db.execute('PRAGMA query_only=ON')
                new_run=json.loads((directory/'run.json').read_text())['run_id']
                row=db.execute('SELECT initial_credit FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                    (new_run,episode_id)).fetchone()
                assert row[0]==expected['credit']
                received={r[0] for r in db.execute('SELECT record_ref FROM runtime_record_receipts '
                    "WHERE run_id=? AND episode_id=? AND receipt_kind='initial'",(new_run,episode_id))}
                assert set(initial)<=received
                first_receipts.extend(sorted(received))
                assert db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?',(new_run,)).fetchone()[0]==0
        contexts.append(deepcopy(context))
        # The same inherited record is selected indefinitely; only the actual
        # existing YieldController's numerical rule determines when this ends.
        return {'selection':{'kind':'tool','tool':'state.query','arguments':{'refs':[chosen]}},'report_update':{}}
    monkeypatch.setattr(ModelConnection,'complete',scripted)
    actual_policy=Path(caller_policy.__file__)
    assert sha(actual_policy)==CALLER_SHA
    implementation_before=independent_execution.implementation_sha256()
    provider=ModelConnection(manifest['configuration']['models'],directory/'scripted-provider',directory)
    summary=asyncio.run(run_prepared_case(directory,policy_file=actual_policy,
        parameters=parameters,resume=False,provider=provider))
    assert not provider.workers and provider.session_index==0
    assert sha(actual_policy)==CALLER_SHA
    assert independent_execution.implementation_sha256()==implementation_before
    saved=json.loads((directory/'run.json').read_text())
    new_run_id=saved['run_id'];assert new_run_id!=old_run_id
    assert saved['scientific_knowledge']['initial_known_record_refs']==initial
    recorded=json.loads((directory/'policy-binding.json').read_text())
    assert recorded['parameters']==parameters and recorded['source_sha256']==CALLER_SHA
    assert (directory/recorded['snapshot_file']).read_bytes()==actual_policy.read_bytes()
    assert recorded['episode_application_services']['inputs']=='actual_tool_registry_v1'
    assert recorded['episode_application_services']['definition']==parameters['services']
    assert summary['state']=='yielded' and summary['pending_handles']==[]
    assert summary['credit']==expected['credit'] and summary['monitoring_information_credit']==0
    assert summary['scientific_completion']=='not_established_by_termination'
    with Store(workspace) as store:
        episode,=store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=?',(new_run_id,)).fetchall()
        episode_id=episode['episode_id']
        assert episode_id!=receipt['source']['episode_id'] and episode['initial_credit']==expected['credit']
        receipts=EpisodeReceipts(store,new_run_id)
        assert set(initial)<=set(receipts.known(episode_id,baseline=True))
        assert set(natives)==set(receipts.known(episode_id,record_type='native_execution',baseline=True))
        rows=[json.loads(r[0]) for r in store.db.execute('SELECT observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=? ORDER BY unit_index',(new_run_id,episode_id))]
        assert len(rows)==len(contexts)==summary['completed_actions'] and len(rows)>=8
        assert all(row['step']['marginal_credit']==0 for row in rows)
        assert all(row['step']['stop'] is False for row in rows[:-1])
        assert rows[-1]['step']['stop'] is True
        decision=rows[-1]['step']['decision']
        assert decision['continuation_cost']==TEST_COST and decision['projected_gain']['upper']<=TEST_COST
        assert decision['decision_basis']=='current_estimator_marginal_credit_upper_bound'
        assert [row['unit_ref']['unit_index'] for row in rows]==list(range(len(rows)))
        assert all(row['unit_ref']['episode_id']==episode_id for row in rows)
        assert old_rows(store.db,old_run_id)==historical
        first=store.db.execute('SELECT request FROM runtime_model_calls WHERE run_id=? '
            'AND episode_id=? ORDER BY call_index LIMIT 1',(new_run_id,episode_id)).fetchone()
        envelope=json.loads(first[0])
        assert envelope['version']=='runtime_model_call_request_v2'
        assert envelope['context']['waiting_support']['own_completed_action_history']==[]
        assert envelope['model_presentation']['context']['waiting_support']['own_completed_action_history']==[]
        assert store.count('native_execution')==native_count
        for table in ('provider_jobs','public_search_orders','runtime_commission_intents'):
            assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
        actions=[json.loads(r[0]) for r in store.db.execute('SELECT action FROM runtime_actions '
            'WHERE run_id=? ORDER BY decision_index',(new_run_id,))]
        assert all(a=={'kind':'tool','tool':'state.query','arguments':{'refs':[chosen]}} for a in actions)
    with readonly(directory/'native-jobs/jobs.sqlite') as db:
        assert db.execute('SELECT count(*) FROM orders').fetchone()[0]==0
    with sqlite3.connect(manifest['configuration']['history']) as db:
        assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0]==0
    with sqlite3.connect(parameters['services']['api_timing']['ledger_path']) as db:
        assert db.execute('SELECT count(*) FROM api_timing_measurements').fetchone()[0]==0
    assert sha(receipt_path)==descriptor['sha256'] and files(workspace/'checkpoint')==immutable_before
    assert files(source_root)==source_before
    with readonly(arguments['source_workspace']/'state.sqlite3') as db:
        assert old_rows(db,old_run_id)==historical
    proof={'version':'scientific_checkpoint_api_caller_join_fixture_v1','C_result':result,
        'new_run_id':new_run_id,'old_run_id':old_run_id,'first_initial_receipts':first_receipts,
        'initial_credit':expected['credit'],'initial_native_monitoring_credit':0,
        'summary':summary,'new_observations':rows,'model_visible_contexts':contexts,
        'old_row_counts':{table:len(values) for table,values in historical.items()},
        'immutable_checkpoint_files':immutable_before,'source_files_before':source_before,
        'source_files_before_after_equal':True,
        'actual_policy_sha256':CALLER_SHA,'implementation_sha256':implementation_before,
        'actual_model_public_HTTP_native_calls':0,'scientific_usefulness_demonstrated':False}
    (tmp_path/'joined-proof.json').write_text(canonical(proof)+'\n')
