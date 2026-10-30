#!/usr/bin/env python3
"""Owned read-only public snapshot and saved-only native-rate host replay.

Run with repo .venv Python. No live Store, provider history, original paper,
calculator, population, model transport, delivery, or observation is invoked.
"""
import sys
sys.dont_write_bytecode = True
import argparse, hashlib, importlib, inspect, json, math, shutil, sqlite3, subprocess
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

OWN = Path(__file__).resolve().parent
BASE = OWN.parent
PIN = BASE/'literature_model_run_024/pin_001'
LIVE = BASE/'literature_model_run_024/live_001'
PRIVATE = {'runtime_model_calls','runtime_decision_exchanges'}
RUN = 'run_b99702cf8216443c9d0bc0444f3736e8'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def digest(path): return sha(path.read_bytes())
def save(path, obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def require(value, code):
    if not value: raise AssertionError(code)
def ro(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db
def fingerprint():
    manifest=json.loads((PIN/'SOURCE_MANIFEST.json').read_text())
    for row in manifest['files']:
        p=(PIN/row['pin_relative_path']).resolve()
        require(p.is_relative_to(PIN) and p.stat().st_size==row['size'] and digest(p)==row['sha256'],'pin_bytes_changed')
    return {'manifest_sha256':digest(PIN/'SOURCE_MANIFEST.json'),'files':len(manifest['files'])}
def process():
    p=Path('/proc/1614626/stat')
    row={'pid':1614626,'expected_start_ticks':'82830508','present':p.exists()}
    if p.exists():
        parts=p.read_text().rsplit(')',1)[1].split()
        row.update(state=parts[0],start_ticks=parts[19],same_process=parts[19]=='82830508')
    row['terminal_result_file_present']=(LIVE/'RESULT.json').exists()
    row['checked_at']=now()
    return row
def snapshot(out):
    require(out.parent==OWN and not out.exists(),'new_owned_snapshot_required')
    before=fingerprint(); out.mkdir(); state=out/'state'; state.mkdir()
    started=now()
    with closing(ro(LIVE/'state/state.sqlite3')) as src:
        src.execute('BEGIN'); src.execute('SELECT count(*) FROM sqlite_master').fetchone()
        with sqlite3.connect(state/'state.sqlite3') as dst: src.backup(dst)
        src.rollback()
    artifacts=[]
    with closing(ro(state/'state.sqlite3')) as db:
        require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','snapshot_integrity')
        refs=set()
        for r in db.execute('SELECT outcome FROM literature_rate_operations WHERE run_id=?',(RUN,)):
            sheet=json.loads(r[0])['result']['sheet_ref']
            source=json.loads(db.execute('SELECT data FROM records WHERE id=?',(sheet,)).fetchone()[0])
            refs.update((source['request_ref'],source['artifact_ref']))
        for ref in sorted(refs):
            r=dict(db.execute('SELECT * FROM artifacts WHERE id=?',(ref,)).fetchone())
            relative=Path('artifacts')/r['sha256'][:2]/r['sha256']
            target=state/relative; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(LIVE/'state'/relative,target)
            require(digest(target)==r['sha256'] and target.stat().st_size==r['size'],'saved_artifact_integrity')
            artifacts.append(r)
    require(before==fingerprint(),'pin_changed')
    save(out/'snapshot.json',{'started_at':started,'completed_at':now(),'pin':str(PIN),'live':str(LIVE),
        'fingerprint':before,'consistent_backup_sha256':digest(state/'state.sqlite3'),'artifacts':artifacts,
        'read_scope':'One mode=ro/query_only SQLite BEGIN snapshot; SQLite backup API includes committed WAL. Copy only saved sheet/request artifacts; no source paper artifacts copied. Full database opaque backup includes private tables, never queried.'})

def replay(out):
    require(out.parent==OWN,'owned_only')
    manifest=json.loads((out/'snapshot.json').read_text()); require(fingerprint()==manifest['fingerprint'],'pin_changed')
    sys.path.insert(0,str(PIN))
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.domain import canonical, identity, obj, ContractError
    from gene_annotation_episode.communication import validate_form, ReportBoundaryError, plain
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, rate_source_cells_schema
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from method_loop.identities import UnitRef
    storage=importlib.import_module('gene_annotation_episode.literature_rate_storage')
    native=importlib.import_module('gene_annotation_episode.literature_rate_native_inputs')
    calculations=importlib.import_module('gene_annotation_episode.literature_rate_calculations')
    providers=importlib.import_module('gene_annotation_episode.providers')
    blocked=[]; disabled=[]
    def forbidden(label):
        def call(*a,**k): blocked.append(label); raise AssertionError('forbidden:'+label)
        return call
    for module,name in [(storage,'read_rate_table'),(storage,'populate_rate_contrast'),
                        (native,'read_rate_source_inputs'),(calculations,'populate_rate_contrast')]:
        setattr(module,name,forbidden(module.__name__+'.'+name)); disabled.append(module.__name__+'.'+name)
    for cls,names in [(LiteratureRateRepository,('populate','populate_native','receive_cells')),
                      (EpisodeReceipts,('bind','receive')),
                      (providers.ModelConnection,('__init__','__aenter__','complete','catalog')),
                      (providers._SessionConnection,('__init__','__aenter__','complete','catalog'))]:
        for name in names: setattr(cls,name,forbidden(cls.__name__+'.'+name)); disabled.append(cls.__name__+'.'+name)
    allowed={r['id'] for r in manifest['artifacts']}; allowed_paths={out/'state/artifacts'/r['sha256'][:2]/r['sha256'] for r in manifest['artifacts']}
    def host_guard(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(args[0]).resolve()
            require(not p.is_relative_to(LIVE),'live_read_in_replay')
            if p.is_relative_to(out/'state/artifacts'): require(p in allowed_paths,'source_artifact_read')
        if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.system','os.exec'}: raise AssertionError('offline_host_event:'+event)
    sys.addaudithook(host_guard)
    state=out/'state'
    with closing(ro(state/'state.sqlite3')) as db:
        tables=sorted(r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] not in PRIVATE)
        def hashes(db): return {t:sha(canonical([list(r) for r in db.execute('SELECT * FROM "'+t+'" ORDER BY rowid')]).encode()) for t in tables}
        initial=hashes(db)
    with Store(state) as store:
        db=store.db; repo=LiteratureRateRepository(store,RUN).source_projection(); receipts=EpisodeReceipts(store,RUN); returns=EpisodeReturnRecords(store,RUN,failure_prefix='audit_')
        # Constructors may initialize missing tables only in the owned copy.
        additions=sorted(r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] not in tables and r[0] not in PRIVATE)
        require(hashes(db)==initial,'constructor_changed_original_public_rows')
        db.execute('PRAGMA query_only=ON')
        denied=[]
        def guard(action,arg1,arg2,*unused):
            if action==sqlite3.SQLITE_READ and arg1 in PRIVATE or action in {sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE,sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH}:
                denied.append([action,arg1,arg2]); return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(guard)
        reads=Counter(); get_artifact=store.get_artifact
        def saved_only(ref):
            require(ref in allowed,'nonsaved_artifact_read'); reads[ref]+=1; return get_artifact(ref)
        store.get_artifact=saved_only
        episodes={r['episode_id']:dict(r) for r in db.execute('SELECT * FROM runtime_episodes WHERE run_id=?',(RUN,))}
        contexts={eid:returns.context(eid) for eid in episodes}; known={eid:set(receipts.known(eid)) for eid in episodes}
        actions={(r['episode_id'],r['decision_index']):dict(r) for r in db.execute('SELECT * FROM runtime_actions WHERE run_id=?',(RUN,))}
        projections=[]; contract_checks=[]
        for row in db.execute('SELECT * FROM literature_rate_operations WHERE run_id=?',(RUN,)):
            outcome=json.loads(row['outcome']); eid=row['episode_id']; context=contexts[eid]
            prefix=f'{RUN}:{eid}:'; require(row['operation_key'].startswith(prefix),'operation_key')
            index=int(row['operation_key'][len(prefix):]); actionrow=actions[eid,index]; action=json.loads(actionrow['action'])
            require(action['tool']=='literature.rate.source.populate','selected_tool')
            actual=json.loads(actionrow['result']); require(all(canonical(actual[k])==canonical(v) for k,v in outcome.items()),'outcome_changed')
            require(row['signature']==canonical({'input_mode':'native_source_spans','arguments':action['arguments'],'scope':plain(context.scope)}),'signature')
            sheetref=outcome['result']['sheet_ref']; source=store.get(sheetref)
            request=json.loads(saved_only(source['request_ref']))
            require(request=={'run_id':RUN,'episode_id':eid,'operation_key':row['operation_key'],'arguments':action['arguments']},'request_ownership')
            payload=repo.read(sheetref)
            require(payload['native_selection']==action['arguments'],'selection_changed')
            source_value={k:v for k,v in source.items() if k not in {'id','record_type','origin'}}
            require(identity('source',{'origin':source['origin'],'record':source_value})==sheetref,'immutable_sheet_identity')
            require(sheetref in known[eid],'sheet_custody')
            receipt=dict(db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?',(RUN,eid,sheetref)).fetchone())
            require(receipt=={'receipt_kind':'own_action','source_index':index},'own_receipt')
            require(set(payload['direct_input_source_refs']).issubset(known[eid]),'direct_source_custody')
            for ref in payload['input_source_refs']: repo._native_provenance(context.scope,ref)
            requested=list(context.assignment.get('requested_rate_components',repo.components))
            projected=repo.project_cells([sheetref],permitted_record_refs=known[eid],components=requested)
            repo.validate_cells(projected,sheet_refs=[sheetref],permitted_record_refs=known[eid],components=requested)
            repo.validate_returned_values(projected,permitted_record_refs=known[eid])
            resolver=lambda ref,ns: ref in known[eid] and (ns is None or store.get(ref)['record_type']==ns)
            validate_form({'cells':projected},obj({'cells':rate_source_cells_schema()}),resolver)
            original=plain(context.request['report_contract']['measurements']['schema'])
            native_fields={name:node for name,node in original['properties'].items() if node.get('x-source')=='literature_rate_source_cells'}
            consumer=LiteratureEpisodes.__new__(LiteratureEpisodes)
            consumer.rate_population=True
            consumer.services=SimpleNamespace(record_selection=lambda c:{'run_id':RUN,'episode_id':eid,'known_record_refs':list(known[eid])})
            consumer._population_routes=lambda:(('literature_rate_source_cells','requested_rate_components',storage.PROVIDER,repo.components,lambda:repo),)
            received_context=replace(context,received_record_refs=tuple(known[eid]))
            for name,node in native_fields.items():
                validate_form({name:projected},obj({name:node}),resolver)
                consumer.validate_received_report(received_context,{name:projected},obj({name:node}))
                expected=rate_source_cells_schema()['items']['properties']; selected=node['items']['properties']
                omitted=[k for k,v in expected.items() if 'x-reference-namespace' in v and 'x-reference-namespace' not in selected[k]]
                contract_checks.append({'field':name,'required_fields':len(node['items']['required']),'missing_explicit_namespaces':omitted,
                    'schema_exact_copy':canonical(node)==canonical(rate_source_cells_schema()),'requested_schema_sha256':sha(canonical(node).encode()),
                    'descriptor_reference_check':'format=reference verifies actual custody/existence; absent namespace does not by itself enforce record type',
                    'downstream_semantics':'validate_returned_values reprojects saved selected sheet and exact cell/binding equality; read validates native witness/selection associations and generated reference/context/term identities without source reread'})
            cells=[]
            for cell in projected:
                raw=payload['sheet']['cells'][cell['component']]
                for field in ('value','unit','status','origin','unavailable_reason','conditional_on','approximate','threshold','bound'):
                    require(canonical(cell[field])==canonical(raw[field]),'changed_cell:'+field)
                require((cell['status']=='unavailable')==(cell['value'] is None),'null_status')
                require(cell['value'] is None or type(cell['value']) in (int,float) and math.isfinite(cell['value']),'nonnumeric')
                require((cell['unavailable_reason'] is not None)==(cell['status']=='unavailable'),'reason_status')
                cells.append(cell)
            # Rejection probes use detached trees only, never modify facts.
            rejection={}
            try: repo.project_cells([sheetref],permitted_record_refs=[],components=requested)
            except ContractError as exc: rejection['unreceived_sheet']=str(exc)
            mutated=json.loads(canonical(projected)); mutated[0]['reference_subject_ref']=mutated[0]['evidence_source_ref']
            try: repo.validate_returned_values(mutated,permitted_record_refs=known[eid])
            except ContractError as exc: rejection['wrong_native_binding']=str(exc)
            for name,node in native_fields.items():
                try: consumer.validate_received_report(received_context,{name:mutated},obj({name:node}))
                except ReportBoundaryError as exc: rejection['actual_consumer_wrong_native_binding']=exc.diagnostic
            require(rejection.get('unreceived_sheet')=='literature_sheet_not_received' and rejection.get('wrong_native_binding')=='literature_rate_return_differs_from_saved_cells'
                and rejection.get('actual_consumer_wrong_native_binding',{}).get('code')=='literature_rate_return_differs_from_saved_cells','rejection_probe_missing')
            arm_operands=[]
            for arm in payload['sheet']['extraction']['rows']:
                src=arm['source']; number=src['number']; unit=src['unit']
                if unit and unit['raw_unit'].strip()=='U/mg' and unit['source_defined_unit'] is None:
                    require(unit['canonical_unit'] is None and unit['multiplier'] is None and unit['unavailable_reason']=='source_defined_unit_definition_required','unavailable_defined_unit_reason')
                    require(arm['status']=='unavailable' and arm['value'] is None,'missing_definition_fabricated_value')
                arm_operands.append({'arm':arm['arm'],'number':None if number is None else {k:number[k] for k in ('raw_number','value','relation','approximate')},
                    'raw_unit':unit['raw_unit'] if unit else None,'canonical_unit':unit['canonical_unit'] if unit else None,
                    'source_defined_unit_present':bool(unit and unit['source_defined_unit'] is not None),
                    'unit_unavailable_reason':unit['unavailable_reason'] if unit else None,
                    'converted_value':arm['value'],'status':arm['status'],'uncertainty':arm['uncertainty'],
                    'saved_meanings_sha256':sha(canonical(src['meanings']).encode())})
            projections.append({'episode_id':eid,'decision_index':index,'sheet_ref':sheetref,'record_version':payload['version'],
                'payload_sha256':sha(saved_only(source['artifact_ref'])),'request_sha256':sha(saved_only(source['request_ref'])),
                'selected_arguments_sha256':sha(canonical(action['arguments']).encode()),'native_selection_sha256':sha(canonical(payload['native_selection']).encode()),
                'requested_components':requested,'cells':cells,'own_receipt':receipt,'rejection_probes':rejection,'saved_arm_operands':arm_operands,
                'all_saved_component_status_counts':dict(Counter(c['status'] for c in payload['sheet']['cells'].values())),
                'requested_nonnull_numeric_cells':sum(c['value'] is not None for c in cells),
                'units_qualifiers_subjects_constructs_preserved':True,'scientific_truth_of_assignments_assessed':False})
        attempts=[]
        for r in db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=?',(RUN,)):
            row=dict(r); item={k:row[k] for k in ('parent_episode_id','decision_index','child_episode_id','delivery_ref')}
            if row['failure'] is not None: item.update(status='saved_failure_retained',failure=json.loads(row['failure']))
            elif row['form'] is None: item['status']='pending_form'
            elif (row['parent_episode_id'],row['decision_index']) not in actions: item['status']='public_redelivery_authentication_unavailable'
            else:
                child,form,schema=returns._attempt(contexts[row['parent_episode_id']],row['decision_index'])
                validate_form(form,schema,lambda ref,ns:ref in known[child.episode_id] and (ns is None or store.get(ref)['record_type']==ns))
                for name,node in schema['properties'].items():
                    if node.get('x-source')=='literature_rate_source_cells': repo.validate_returned_values(form[name],permitted_record_refs=known[child.episode_id])
                item['status']='actual_frozen_return_validated'
            attempts.append(item)
        received=[]
        for r in db.execute('SELECT * FROM literature_rate_source_received WHERE run_id=?',(RUN,)):
            row=dict(r); cells=json.loads(row['cells']); repo.validate_returned_values(cells,permitted_record_refs=known[row['episode_id']])
            prefix=f"{RUN}:{row['episode_id']}:"; require(row['operation_key'].startswith(prefix) and row['operation_key'].endswith(':typed_form'),'typed_admission_key')
            index=int(row['operation_key'][len(prefix):-len(':typed_form')]); child,form,schema=returns._attempt(contexts[row['episode_id']],index)
            expected=[c for name,node in schema['properties'].items() if node.get('x-source')=='literature_rate_source_cells' for c in form[name]]
            require(canonical(cells)==canonical(expected),'admitted_subset_changed')
            received.append({'episode_id':row['episode_id'],'operation_key':row['operation_key'],'cells':cells,'matches_actual_form':True})
        accounting=[]
        for eid,episode in episodes.items():
            observations=[dict(r) for r in db.execute('SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',(RUN,eid))]
            slots={r['sequence']:json.loads(r['slot']) for r in db.execute('SELECT * FROM runtime_completion_slots WHERE run_id=? AND episode_id=?',(RUN,eid))}
            seen=[]
            for seq,r in enumerate(observations):
                o=json.loads(r['observation']); idx=o['decision_index']; a=actions[eid,idx]; result=json.loads(a['result'])
                require(r['unit_index']==seq and idx not in seen and result['status'] in ('completed','partial'),'one_completed_own_action')
                require(o['unit_ref']==UnitRef(eid,seq).as_record() and o['credit']['credit']==a['credit'],'original_credit_identity')
                if seq in slots:
                    slot=slots[seq]; require(slot['original_decision_index']==idx and canonical(slot['controller_input'])==canonical(o['credit']),'slot_input_changed')
                seen.append(idx)
            classifications=[]
            for (owner,idx),a in actions.items():
                if owner!=eid: continue
                action=json.loads(a['action']); result=json.loads(a['result']) if a['result'] else None; status=result.get('status') if result else None
                label='completed_observed' if idx in seen else 'completed_pending_observation' if status in ('completed','partial') else 'pending_selected_work' if status in (None,'pending') else 'failed_attempt_no_observation'
                if label=='failed_attempt_no_observation': require(a['credit'] is None,'failed_attempt_credit')
                classifications.append({'decision_index':idx,'tool':action.get('tool'),'kind':action['kind'],'status':status,'classification':label,'original_credit':a['credit'],'failure_code':(result.get('feedback') or {}).get('code') if result else None})
            accounting.append({'episode_id':eid,'state':episode['state'],'path':json.loads(episode['path']),'action_rows':len(classifications),'observations':len(observations),'completion_slots':len(slots),'actions':classifications,'last_saved_step':json.loads(observations[-1]['observation'])['step'] if observations else None})
        require(hashes(db)==initial and not blocked and not denied,'read_only_violation')
        imports={name:{'path':str(Path(module.__file__).resolve()),'sha256':digest(Path(module.__file__))} for name,module in sys.modules.items() if name.startswith(('gene_annotation_episode','method_loop')) and getattr(module,'__file__',None)}
        require(all(Path(r['path']).is_relative_to(PIN) for r in imports.values()),'unpinned_import')
        counts={t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}
    # Independent reopen of the backup with real Store, same saved-only reads.
    with Store(state) as reopened:
        reopened.db.execute('PRAGMA query_only=ON'); reopened.db.set_authorizer(guard)
        for row in projections:
            source=reopened.get(row['sheet_ref']); require(source['artifact_ref'] in allowed and sha(reopened.get_artifact(source['artifact_ref']))==row['payload_sha256'],'reopen_payload_changed')
        require(hashes(reopened.db)==initial,'reopen_changed_rows')
    require(fingerprint()==manifest['fingerprint'],'final_pin_changed')
    save(out/'receipt.json',{'completed_at':now(),'run_id':RUN,'status':'passed_saved_only_audit','public_counts':counts,'audit_script_sha256':digest(Path(__file__)),
        'contract_checks':contract_checks,'selected_native_sheets':projections,'actual_report_attempts':attempts,'actual_parent_admitted_subsets':received,'episode_accounting':accounting,
        'replay':{'kind':'fresh host subprocess saved-only repository replay, followed by second Store reopen','detached_or_model_run_reconstruction':False,'original_backup_byte_identical_to_live_DB':False,
            'consistent_backup':True,'original_public_rows_sha256':initial,'constructor_added_empty_tables_in_owned_copy':additions,'artifact_reads':dict(reads),'disabled':disabled,'blocked_calls':blocked,'denied_sql':denied,'actual_pinned_imports':imports},
        'limits':['No original scientific artifact read, native source parser, calculator, transport, numerical fit/repricing, controller observation, live mutation or source reinterpretation.',
            'Saved validators inspect saved units/number/definition relationships, including deterministic validation arithmetic; no numerical sheet repopulation.',
            'Requested saved projection is diagnostic and does not establish actual closure/admission. Absent actual returns are pending, not failure.',
            'No whole A105 sheet/axis, W05 combination, or full-goal completion established.']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',type=Path);args=p.parse_args()
    if args.replay: replay(args.replay.resolve())
    else:
        out=OWN/'snapshot_001';snapshot(out)
        r=subprocess.run([sys.executable,'-B','-P',str(Path(__file__).resolve()),'--replay',str(out)],capture_output=True,text=True)
        (out/'replay_stdout.txt').write_text(r.stdout);(out/'replay_stderr.txt').write_text(r.stderr)
        save(OWN/'final_process_cut.json',process())
        require(r.returncode==0,'replay_failed_see_stderr')
        print(json.dumps({'receipt':str(out/'receipt.json'),'process_cut':str(OWN/'final_process_cut.json')}))
