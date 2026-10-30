"""Original030 admitted typed return: readonly first projection and public custody.

No provider/model-history table or private archive is read. No original document,
image,native reader,scientific calculator,receive/reprice/controller is invoked.
"""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SOURCE_AUDIT = HERE.parent
BASE = SOURCE_AUDIT.parent
PIN = BASE / 'literature_model_run_030/pin_001'
RUN = BASE / 'literature_model_run_030/live_001'
CHILD = 'episode_76758a673dea6a01ef47fb2b7252facac1945c143bf2a10ebea32ab9bc9c4343'
PARENT = 'episode_0e9aa175e90da812f104b9e0a97c222406e91f755d211ca7ad44583f4a31a631'
RUN_ID = 'run_dc292076ddea4603a04abf5b79c6ad3a'
INDEX = 18
sys.path.insert(0, str(PIN))
from method_loop.durable import canonical, content_digest, validate_commission, validate_return
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_admission import AdmissionError, ReceiverBindingV1, admit_return, _install
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.independent_execution import implementation_sha256
from gene_annotation_episode.investigation_progress import ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.state import Store


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def readonly(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def one(db, sql, parameters=()):
    row = db.execute(sql, parameters).fetchone()
    assert row is not None, sql
    return dict(row)


def public_snapshot(db):
    """Exact public rows only; never scans runtime_model_calls or archives."""
    result = {}
    queries = {
        'commission': ('select * from runtime_commission_intents where run_id=? and parent_episode_id=? and original_decision_index=?', (RUN_ID,PARENT,INDEX)),
        'admission': ('select * from runtime_return_admissions where run_id=? and parent_episode_id=? and original_decision_index=?', (RUN_ID,PARENT,INDEX)),
        'parent_action': ('select * from runtime_actions where run_id=? and episode_id=? and decision_index=?', (RUN_ID,PARENT,INDEX)),
        'report_attempt': ('select * from runtime_report_attempts where run_id=? and parent_episode_id=? and decision_index=?', (RUN_ID,PARENT,INDEX)),
        'parent_episode': ('select * from runtime_episodes where run_id=? and episode_id=?', (RUN_ID,PARENT)),
        'child_episode': ('select * from runtime_episodes where run_id=? and episode_id=?', (RUN_ID,CHILD)),
        'child_form': ('select * from runtime_forms where run_id=? and episode_id=?', (RUN_ID,CHILD)),
        'received': ('select * from literature_rate_source_received where run_id=? and episode_id=? and operation_key=?', (RUN_ID,PARENT,f'{RUN_ID}:{PARENT}:{INDEX}:typed_form')),
        'slot': ('select * from runtime_completion_slots where run_id=? and episode_id=? and original_decision_index=?', (RUN_ID,PARENT,INDEX)),
    }
    for name,(sql,args) in queries.items():
        result[name] = one(db,sql,args)
    result['observations'] = [dict(row) for row in db.execute(
        "select * from runtime_observations where run_id=? and episode_id=? and json_extract(observation,'$.decision_index')=?",
        (RUN_ID,PARENT,INDEX))]
    result['native_actions'] = [dict(row) for row in db.execute(
        'select * from runtime_actions where run_id=? and episode_id=? and decision_index in(29,31) order by decision_index',(RUN_ID,CHILD))]
    result['parent_receipts'] = [dict(row) for row in db.execute(
        'select * from runtime_record_receipts where run_id=? and episode_id=? and source_index=? order by receipt_index',(RUN_ID,PARENT,INDEX))]
    result['child_known_refs'] = [row[0] for row in db.execute(
        'select distinct record_ref from runtime_record_receipts where run_id=? and episode_id=? order by record_ref',(RUN_ID,CHILD))]
    result['parent_known_refs'] = [row[0] for row in db.execute(
        'select distinct record_ref from runtime_record_receipts where run_id=? and episode_id=? order by record_ref',(RUN_ID,PARENT))]
    rows = json.loads(result['received']['cells'])
    references = set()
    for row in rows:
        references.update(value for key,value in row.items() if key.endswith('_ref') and value is not None)
    result['records'] = {ref: one(db,'select * from records where id=?',(ref,)) for ref in sorted(references)}
    artifacts = {value for row in result['records'].values() for key,value in json.loads(row['data']).items()
                 if key in ('artifact_ref','text_ref','request_ref') and value is not None}
    result['artifacts'] = {ref:one(db,'select * from artifacts where id=?',(ref,)) for ref in sorted(artifacts)}
    result['native_operations'] = []
    for row in result['native_actions']:
        result['native_operations'].append(one(db,'select * from literature_rate_operations where run_id=? and episode_id=? and operation_key=?',
                                             (RUN_ID,CHILD,f'{RUN_ID}:{CHILD}:{row["decision_index"]}')))
    return result


class ForbiddenOriginalWork(BaseException):
    """Cannot become an ordinary unavailable scientific result through a catch."""


FORBIDDEN_CALLS = []


def forbidden(*args, **kwargs):
    FORBIDDEN_CALLS.append('forbidden_original_work')
    raise ForbiddenOriginalWork('No original source/image/scientific reading,calculation,receiving,repricing,model or controller during audit projection')


def setup_metadata(settings):
    """Genuine constructors write only a new empty owned metadata fixture."""
    store = Store(HERE / 'metadata_factory_state')
    journal = Journal(store,RUN_ID)
    host = SimpleNamespace(store=store,run_id=RUN_ID,tools=None,progress_provider=None,native_event_information=None)
    services = WorkflowServices(host)
    descriptors = [row for row in settings['episode_bindings'] if row['binding_id']=='literature']
    descriptor, = descriptors
    binding = LiteratureEpisodes(services,**descriptor['configuration'])
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    assert binding.as_record() == descriptor
    # These constructors install empty tables only. No received/projected fact
    # is requested before the fresh original mode=ro connection is installed.
    for _,_,_,_,factory in binding._population_routes():
        factory()
    store.close()
    return store,journal,host,services,binding,descriptor


def context(row, known):
    request = json.loads(row['request'])
    path = tuple(tuple(part) for part in json.loads(row['path']))
    message = request['message']
    return BindingContext(RUN_ID,row['episode_id'],path[-1][0],path,message['scope'],
                          message.get('episode_assignment',{}),request,tuple(known))


def main():
    manifest = load(SOURCE_AUDIT/'MANIFEST_001.json')
    for name,row in manifest['files'].items():
        path = SOURCE_AUDIT/name
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],name
    pin = load(PIN/'SOURCE_MANIFEST.json')
    for row in pin['files']:
        path = PIN/row['pin_relative_path']
        assert path.stat().st_size==row['size'] and sha(path)==row['sha256'],path
    run_manifest = load(RUN/'run/run.json')
    settings = {key:value for key,value in run_manifest.items() if key!='run_id'}
    runtime_binding = load(RUN/'run/episode-execution-binding.json')
    assert runtime_binding['implementation_sha256']==implementation_sha256()
    assert runtime_binding['settings_sha256']==content_digest(settings)
    store,journal,host,services,binding,descriptor = setup_metadata(settings)
    original_directory = store.path
    capture_utc = datetime.now(timezone.utc).isoformat()
    db = readonly(RUN/'state/state.sqlite3')
    store.path,store.db,journal.db = RUN/'state',db,db
    db.create_function('library_scope_record',2,store._scope_filter_record)
    db.execute('begin')
    denied_writes = []
    write_codes = {getattr(sqlite3,name) for name in ('SQLITE_INSERT','SQLITE_UPDATE','SQLITE_DELETE','SQLITE_CREATE_TABLE','SQLITE_DROP_TABLE','SQLITE_ALTER_TABLE','SQLITE_CREATE_INDEX','SQLITE_DROP_INDEX')}
    def authorize(action, first, second, database, trigger):
        if action in write_codes:
            denied_writes.append([action,first,second])
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    db.set_authorizer(authorize)
    try:
        before = public_snapshot(db)
        intent,admission_row = before['commission'],before['admission']
        spec = validate_commission(json.loads(intent['spec']))
        admission = json.loads(admission_row['admission'])
        assert spec['child']['episode_id']==CHILD and spec['parent']['episode_id']==PARENT
        assert spec['runtime_binding']==runtime_binding
        assert content_digest(spec)==intent['commission_sha256']==admission_row['commission_sha256']
        selected = json.loads(intent['selection'])
        assert selected==json.loads(before['parent_action']['action'])
        assert content_digest(selected)==admission_row['selection_sha256']
        child_request=json.loads(before['child_episode']['request'])
        assert child_request==spec['child']['request']==load(SOURCE_AUDIT/'ORIGINAL_EPISODE_REQUEST_001.json')['request']
        original_contract=child_request['report_contract']
        requested=child_request['message']['episode_assignment']['requested_rate_components']
        assert requested==['reference_rate','test_rate','rate_difference','retained_fraction','fractional_decrease']
        assert json.loads(selected['schema_json'])==original_contract['measurements']['schema']
        assert original_contract==json.loads(before['report_attempt']['contract'])
        assert before['report_attempt']['child_episode_id']==CHILD and before['report_attempt']['failure'] is None
        assert admission['state']=='admitted' and admission['delivery_failure'] is None
        expected=json.loads(before['received']['cells'])
        assert len(expected)==10 and {row['component'] for row in expected}==set(requested)
        form={next(iter(original_contract['information'])):expected}
        assert form==admission['report']==json.loads(before['report_attempt']['form'])==json.loads(before['child_form']['form'])
        facts=json.loads(before['child_form']['facts'])
        assert facts['literature_rate_source_cells']==expected
        with readonly(RUN/'run/episode-execution/executions.sqlite') as backend:
            backend.execute('begin')
            # Explicit public columns: execution_token/identity are NOT selected.
            backend_commission=one(backend,'select handle,operation_key,parent_episode_id,commission_sha256,spec,lifecycle_state,return_id,acknowledgment,failure from commissions where handle=?',(spec['handle'],))
            backend_return=one(backend,'select handle,return_id,returned_at,envelope,cursor from returns where handle=? and return_id=?',(spec['handle'],admission['return_id']))
        assert json.loads(backend_commission['spec'])==spec
        assert backend_commission['commission_sha256']==intent['commission_sha256']
        returned=validate_return(json.loads(backend_return['envelope']),spec=spec,commission_sha256=intent['commission_sha256'])
        assert returned['return_id']==admission['return_id']==backend_return['return_id']==backend_commission['return_id']
        assert returned['form']==form
        assert returned['outcome']=='closed'
        assert len(before['observations'])==1
        observation=json.loads(before['observations'][0]['observation'])
        slot=json.loads(before['slot']['slot'])
        assert before['observations'][0]['unit_index']==slot['sequence']==21
        assert slot['original_decision_index']==observation['decision_index']==18
        assert slot['label']==observation['label']=='child_18' and slot['kind']=='child_return'
        assert slot['child_return']=={key:admission[key] for key in ('handle','return_id','admission_id')}
        assert slot['controller_input']==observation['credit']==admission['controller_input']
        assert before['parent_action']['credit']==admission_row['credit_snapshot']==0.0
        assert json.loads(before['parent_action']['result'])['status']=='completed'
        child_context=context(before['child_episode'],before['child_known_refs'])
        parent_context=context(before['parent_episode'],before['parent_known_refs'])
        primary_refs=child_request['message']['episode_assignment']['source_refs']
        primary_artifacts={store.get(ref)[key] for ref in primary_refs for key in ('artifact_ref','text_ref') if store.get(ref).get(key)}
        sheet_refs=list(dict.fromkeys(row['sheet_ref'] for row in expected))
        allowed_artifacts={store.get(ref)[key] for ref in sheet_refs for key in ('artifact_ref','request_ref')}
        denied_paths={(RUN/'state/artifacts'/ref.removeprefix('artifact_')[:2]/ref.removeprefix('artifact_')).resolve() for ref in primary_artifacts}
        denied_paths.update((SOURCE_AUDIT/name).resolve() for name in ('PRIMARY_TEXT_001.txt','PRIMARY_ORIGINAL_001.html'))
        original_open=Path.open
        original_get=store.get_artifact
        saved_reads=[]
        def guarded_open(path,*args,**kwargs):
            target=path.resolve()
            if target in denied_paths or target.is_relative_to((PIN/'inputs').resolve()):
                return forbidden()
            return original_open(path,*args,**kwargs)
        def saved_artifact(reference):
            if reference not in allowed_artifacts:
                return forbidden()
            saved_reads.append(reference)
            return original_get(reference)
        with ExitStack() as guard:
            guard.enter_context(patch.object(Path,'open',guarded_open))
            guard.enter_context(patch.object(store,'get_artifact',saved_artifact))
            for name in ('gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs',
                         'gene_annotation_episode.literature_rate_calculations.populate_rate_contrast',
                         'gene_annotation_episode.literature_rate_storage.populate_rate_contrast',
                         'gene_annotation_episode.literature_rate_storage.read_rate_table',
                         'PIL.Image.open'):
                guard.enter_context(patch(name,forbidden))
            for cls,names in ((LiteratureRateRepository,('populate','populate_native','receive_cells')),
                              (Workflow,('receive_form','_receive_form','source_credit_view','projection_view','controller_value')),
                              (WorkflowServices,('execute_tool','scientific_credit')),
                              (ScientificFindingProgress,('__call__',)),(_SessionConnection,('complete',))):
                for name in names:
                    guard.enter_context(patch.object(cls,name,forbidden))
            # FIRST scientific parent fact projection on this fresh mode=ro
            # connection. No earlier received_report_facts/facts call exists.
            projected=host.episode_bindings.received_report_facts(parent_context)
            actual=projected['literature_rate_source_cells']
            assert actual==expected
            assert saved_reads==[], 'Received-row projection should not even open its saved sheet artifacts'
            # Validate original sourced child form from saved artifacts only,
            # after the first parent projection; neither source IO nor a new
            # scientific calculation is permitted.
            contract=TypedReportContract(original_contract['decision'],original_contract['measurements']['schema'],
                lambda ref,namespace:binding.resolve(child_context,ref,namespace),
                lambda value:binding.validate_report(child_context,value,original_contract['measurements']['schema']))
            assert contract.as_record()==original_contract
            assert plain(contract.admit(form,audit_identifiers=(CHILD,child_request['goal']['goal_id'])).as_record())==form
            child_facts=binding.facts(child_context,{'committed_record_refs':sheet_refs})
            assert child_facts['literature_rate_source_cells']==expected
            repo=services.literature_rate_repository().source_projection()
            extra=repo.project_cells([sheet_refs[0]],permitted_record_refs=child_context.received_record_refs,components=('difference_se',))[0]
            expanded=deepcopy(form)
            expanded[next(iter(original_contract['information']))].append(extra)
            try:
                contract.admit(expanded,audit_identifiers=(CHILD,child_request['goal']['goal_id']))
            except ReportBoundaryError as error:
                assert error.diagnostic['code']=='unrequested_literature_rate_component'
                expanded_rejection=error.diagnostic
            else:
                raise AssertionError('Original requested-component binding must reject an expanded form')
            after=public_snapshot(db)
            assert before==after
        assert not FORBIDDEN_CALLS and not denied_writes
        original_saved=load(SOURCE_AUDIT/'PUBLIC_SAVED_PAYLOADS_001.json')
        # This is saved association inspection,not another scientific source read.
        aliases=[row['saved_payload']['sheet']['extraction']['rows'][0]['source']['location'] for row in original_saved.values()]
        assert aliases[0]==aliases[1]
        assert all(row['reference_construct_ref'] is None and row['test_construct_ref'] is None for row in actual)
        limited=[row for row in actual if row['component']=='test_rate' and row['bound']=='lt']
        assert len(limited)==1 and limited[0]['value'] is None and limited[0]['threshold']==.01
        imports={name:str(Path(module.__file__).resolve().relative_to(PIN.resolve())) for name,module in tuple(sys.modules.items())
                 if name.startswith(('gene_annotation_episode','method_loop')) and getattr(module,'__file__',None)}
        assert imports
        public={'captured_utc':capture_utc,'sqlite_mode':'ro','rows':before,'backend_commission':backend_commission,'backend_return':backend_return}
        write('ORIGINAL_PUBLIC_DELIVERY_002.json',public)
        write('ACTUAL_PARENT_PROJECTION_002.json',projected)
        write('ORIGINAL_CHILD_FORM_002.json',form)
        write('ORIGINAL_BINDING_DESCRIPTOR_002.json',descriptor)
        write('UNREQUESTED_ROW_002.json',extra)
        receipt={'passed':True,'capture_utc':capture_utc,'mode_ro_before_first_parent_projection':True,
            'original_pin_files_verified':len(pin['files']),'original_pin_manifest_sha256':sha(PIN/'SOURCE_MANIFEST.json'),
            'original_runtime_implementation_sha256':runtime_binding['implementation_sha256'],
            'original_settings_sha256':runtime_binding['settings_sha256'],'original_C7_descriptor_exact':True,
            'actual_typed_rows':len(actual),'requested_components':requested,'distinct_saved_sheets':len(sheet_refs),
            'nonnull_point_rows':sum(row['value'] is not None for row in actual),'strict_censoring_preserved':True,
            'source_artifact_reads_during_first_parent_projection':0,'all_later_artifact_reads_are_saved_sheet_or_request':True,
            'saved_artifact_read_refs':sorted(set(saved_reads)),'original_scientific_callbacks_forbidden':True,
            'forbidden_callback_invocations':FORBIDDEN_CALLS,'denied_write_attempts':denied_writes,
            'public_selected_snapshot_sha256_before':content_digest(before),'public_selected_snapshot_sha256_after':content_digest(after),
            'public_selected_snapshot_unchanged':True,'whole_live_database_read_or_stability_claim':False,
            'original_commission_sha256':intent['commission_sha256'],'original_return_id':returned['return_id'],
            'original_admission_id':admission['admission_id'],'original_parent_decision_index':18,
            'original_parent_observation_index':21,'original_parent_observations_for_this_commission':1,
            'original_parent_credit':0.0,'original_source_shared_alias_preserved':True,
            'original_form_full_typed_saved_validation':True,'unrequested_component_rejected':expanded_rejection,
            'no_live_re_admission':True,'application_imports_from_original_pin':imports,
            'new_model_calls':0,'new_actual_runtime_actions':0,'new_actual_runtime_observations':0,
            'root_run_terminal_result_present_at_capture':(RUN/'RESULT.json').exists(),
            'scope':'Actual original configured-model child delivery and first readonly parent received-fact projection; no new scientific reading/inference or full root-run/A105 completion'}
        write('READONLY_DELIVERY_RECEIPT_002.json',receipt)
        print(json.dumps({key:receipt[key] for key in ('passed','capture_utc','actual_typed_rows','nonnull_point_rows',
              'mode_ro_before_first_parent_projection','public_selected_snapshot_unchanged','original_parent_observation_index')}))
    finally:
        db.close()
        store.path=original_directory


if __name__=='__main__':
    main()
