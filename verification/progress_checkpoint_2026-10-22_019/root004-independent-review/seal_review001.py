"""Local evidence metadata/sealing only; no SQLite or application imports."""
from pathlib import Path
import ast,datetime,hashlib,json,os,stat
ROOT=Path(__file__).parent
SOURCE=Path('/tmp/gene-annotation-configured-caller-20261022-008')
EVIDENCE=Path('/tmp/direct-hmmer-root008-evidence-20261022-001')
FIXTURE=EVIDENCE/'invocation-004/preserved-fixtures/test_real_detached_direct_sear0'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,v):(ROOT/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def row(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'bytes':len(b),'mode':stat.S_IMODE(s.st_mode)}
def main():
 first=json.loads((ROOT/'invocation-001/RESULTS001.json').read_text());correction=json.loads((ROOT/'metadata-correction-002/RESULTS_METADATA002.json').read_text());readset=json.loads((ROOT/'invocation-001/READSET_FINAL001.json').read_text());readmap={r['path']:r for r in readset['files']}
 assert len(first['checks'])==279 and all(x['passed'] for x in first['checks'])
 assert first['all_opened_inputs_unchanged_after_explicit_close'] is False
 assert correction['corrected_all_opened_inputs_unchanged'] is True and correction['differences']==[] and correction['witness_count']==183
 selections={
 'tests/test_direct_hmmer_timing_reconstruction.py':['test_real_detached_direct_search_restores_caller_map_timing_and_original_forecast'],
 'gene_annotation_episode/direct_hmmer_timing.py':['direct_operation_key','DirectHmmerTiming.acquire','DirectHmmerTiming._timing','DirectHmmerTiming._finish'],
 'gene_annotation_episode/episode_commissions.py':['CommissionCoordinator.select','CommissionCoordinator._validate_assignment','CommissionCoordinator.dispatch'],
 'gene_annotation_episode/episode_admission.py':['_validate_original','_admit_form','_admit_return'],
 'gene_annotation_episode/independent_execution.py':['implementation_sha256','make_runtime_binding','_check_bindings','open_commission'],
 'gene_annotation_episode/case_execution.py':['_load_policy','prepared_case_bindings','run_prepared_case'],
 'gene_annotation_episode/runtime.py':['Workflow.next_return','Workflow.completed_unit','Workflow.receive_api_timing_outcome','Workflow.api_execution_planning_context','Workflow._receive_form','Workflow.source_credit_view'],
 'gene_annotation_episode/tools.py':['ToolRegistry._save','ToolRegistry._acquire_async'],
 'gene_annotation_episode/api_timing_information.py':['ApiReportedTimingFactReader._witness','ApiReportedTimingFactReader.read_source','ApiReportedTimingFactReader.publish','ReceivedExecutionTimingInformation.read_details'],
 'gene_annotation_episode/api_execution_planning.py':['ApiExecutionPlanner.estimate','ApiExecutionPlanner._validate_capture','ApiExecutionPlanner.validate_result'],
 'method_loop/archive.py':['ArchivedRecord.iter_json','ArchivedRecord.load'],
 'method_loop/durable.py':['validate_commission','validate_return','DurableExecutionStore.start','DurableExecutionStore.publish_return','DurableExecutionStore.load_return','DurableExecutionStore.acknowledge'],
 'gene_annotation_episode/assembled_service_setup.py':['bind_assembled_services_with_public_search_timing_planning_direct'],
 'gene_annotation_episode/api_planning_case_policy.py':['create_policy']}
 anchors=[]
 for rel,names in selections.items():
  path=SOURCE/rel;data=path.read_bytes();authority=readmap[str(path)];assert sha(data)==authority['sha256']
  copy=ROOT/'invocation-001/inputs/source'/rel
  if not copy.exists():copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(data)
  tree=ast.parse(data)
  def visit(nodes,prefix=''):
   for n in nodes:
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
     qual=prefix+n.name
     if qual in names:anchors.append({'path':rel,'sha256':authority['sha256'],'qualified_name':qual,'start_line':n.lineno,'end_line':n.end_lineno,'inspection_extent':'complete named function/method; file hash binds current frozen source'})
     if isinstance(n,ast.ClassDef):visit(n.body,qual+'.')
  visit(tree.body)
 save('SOURCE_ANCHORS001.json',{'version':'offline_review_static_source_anchors_v1','anchors':anchors,'whole_file_reads':['tests/test_direct_hmmer_timing_reconstruction.py','gene_annotation_episode/direct_hmmer_timing.py','gene_annotation_episode/episode_commissions.py'],'note':'Source files copied whole for custody. Inspection coverage is complete named affected functions, not a claim every line of every copied file was independently audited. A-owned operation ports had prior complete owned implementation review and are held6093; this review hashes them without new execution.'})
 controls=[]
 for p in sorted((ROOT/'invocation-001/inputs').rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(ROOT/'invocation-001/inputs').as_posix()
  if rel.startswith('source/'):original=SOURCE/rel[len('source/'):]
  elif rel.startswith('fixture/'):original=FIXTURE/rel[len('fixture/'):]
  elif rel.startswith('invocation-004/'):original=EVIDENCE/rel
  else:original=EVIDENCE/rel
  expected=readmap[str(original)];actual=row(p)
  assert actual['sha256']==expected['sha256'] and actual['bytes']==expected['bytes']
  controls.append({'member':actual['path'],'original_witness':expected,'copy_sha256':actual['sha256'],'copy_bytes':actual['bytes'],'byte_copy_equal':True,'original_mode_retained_as_metadata':expected['mode'],'destination_mode_will_be0444':True})
 save('COPY_CONTROLS001.json',{'version':'offline_review_exactcopy_controls_v1','copies':controls,'copy_count':len(controls),'guard_authority':'metadata-correction-002/RESULTS_METADATA002.json','guard_semantics':'All183 exact original file descriptors matched on additive rehash after all SQLite handles closed. Copied bytes equal those retained originals. Sealing changes only this new bundle permissions; no input permissions changed.','sql_limits':'Only selected preserved synthetic state.sqlite3 and executions.sqlite were connected mode=ro/immutable/query_only/BEGIN/finally-close. Later correction/sealing uses no SQLite connections.'})
 final={'version':'direct_hmmer_root004_final_review_v1','status':'verified_closed_scripted_worker_fixture_with_explicit_metadata_correction','required_authorities':[row(ROOT/'invocation-001/RESULTS001.json'),row(ROOT/'metadata-correction-002/RESULTS_METADATA002.json')],'original_check_count':279,'original_guard_false_preserved':True,'corrected_guard_true':True,'corrected_witness_count':183,'corrected_witness_differences':0,'source_pin':first['source_pin'],'pytest':first['pytest'],'identities':first['identities'],'timing_fact':first['timing_fact'],'forecast':first['forecast'],'observation_counts':first['observation_counts'],'verified_claims':['Original C1 scientific child ownership, scope and parent-defined timing/forecast typed form agree across intent, backend, saved child request and archives.','One immutable closed C3 return; one admitted C4 original parent action; backend ACK names that exact admission and return.','Three child own actions and three parent own observations; saved raw scientific scalar stays0, received monitoring contexts rise0→1 and remain1 without duplicate credit.','Actual search returned2.75 reported elapsed seconds, followed by explicitly selected execution.estimate with saved support1; later child and parent contexts reuse its original forecast.','One original outer tool operation and provider job; deterministic submit/status/result receipts; one cached first-page selector; durable worker PID incarnation740525 differs from parent740358.','Closed episode/result/facts archives and immutable artifact hashes agree; original saved caller pins and138runtime source pin agree.'],'correction':'Original verifier incorrectly compared returned bytes with descriptor dict in its final flag and did not gate status on that flag. Root caught the false flag; original files remain unchanged. A separate metadata-only checker compared full descriptors, found0/183 differences, and requires its corrected true flag. Final status requires both authorities, not the original status alone.','limits':first['limits'],'copy_count':len(controls),'sealing':'Local new review bundle only; no production/test/input edits, no replay or scientific execution.'}
 save('RESULTS_FINAL001.json',final)
 (ROOT/'REVIEW_FINAL001.md').write_text('''The closed preserved root004 scripted fixture is verified, with an explicit metadata correction. Invocation004 retained five passing cases at138-file source pin6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30; this independent review concerns only the one detached direct-search fixture.\n\nThe original reviewer passed279 engineering checks but incorrectly reported its final unchanged guard as false: it compared bytes with descriptor dictionaries and failed to gate status on that boolean. Root caught this. Original code/result remain untouched. The separate metadata correction rehashed all183 original descriptors, found zero differences, and reported the corrected guard true. RESULTS_FINAL requires both records.\n\nC1 retains the scientific child’s original request, parent goal, scope and typed timing/forecast form. One C3 closed return was admitted once by the original parent under C4; the backend acknowledgment names the same admission. Raw rows and closed archives retain three child actions and three parent observations. Scientific credit remains zero. Saved monitoring contexts rise from zero to one in the child and remain one after the parent receives the form. No credit or estimate was recomputed.\n\nThe search’s reported elapsed time is2.75 seconds. A later explicit execution.estimate action has one supporting result and that same expected duration. It was selected after the search, so this witness does not prove an informed initial search choice. Original outer-operation, provider-job, deterministic sub-operation, cached-selector, worker-incarnation, caller-pin and archive/artifact identities agree.\n\nThe fixture continuation law, loopback service, scripted decisions, native capability declaration and test deadline are explicit controls. This is engineering evidence, with no configured-model scientific or biological conclusion. The passing test asserts in-memory shared owners, unchanged replay and POST/GET/GET; this reviewer verifies the saved durable evidence and test authority without replay, HTTP, app/projector imports, native execution or score recomputation. Only two selected closed copied fixture databases were connected read-only, with query_only, explicit transactions and finally-close. No original fixture or live scientific database was opened.\n''')
 # All original evidence inputs remain outside this local sealing operation.
 for p in ROOT.rglob('*'):
  assert not p.is_symlink(),'unexpected alias in own review bundle'
  if p.is_file():os.chmod(p,0o444)
 for p in sorted((x for x in ROOT.rglob('*') if x.is_dir()),reverse=True):os.chmod(p,0o500)
 members=[row(p) for p in sorted(ROOT.rglob('*')) if p.is_file()]
 manifest={'version':'direct_hmmer_root004_independent_review_manifest_v1','root':str(ROOT),'regular_members':members,'member_count_excluding_manifest':len(members),'total_bytes_excluding_manifest':sum(x['bytes'] for x in members),'directories':[str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob('*')) if p.is_dir()],'aliases':[],'root_mode':'0500','member_modes':'0444','manifest_excludes_itself':True,'results_final_sha256':sha((ROOT/'RESULTS_FINAL001.json').read_bytes())}
 save('MANIFEST_FINAL001.json',manifest);os.chmod(ROOT/'MANIFEST_FINAL001.json',0o444);os.chmod(ROOT,0o500)
 print(json.dumps({'bundle':str(ROOT),'manifest_sha256':sha((ROOT/'MANIFEST_FINAL001.json').read_bytes()),'results_final_sha256':manifest['results_final_sha256'],'copy_controls_sha256':sha((ROOT/'COPY_CONTROLS001.json').read_bytes()),'members_excluding_manifest':len(members),'total_files_including_manifest':len(members)+1,'bytes_excluding_manifest':manifest['total_bytes_excluding_manifest'],'directories':len(manifest['directories']),'aliases':0},sort_keys=True))
if __name__=='__main__':main()
