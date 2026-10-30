#!/usr/bin/env python3
"""Sealed evidence checker; stdlib reads only, writes new /tmp output only."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime,timezone
import json, stat, re, tempfile, xml.etree.ElementTree as ET
R=Path('/home/chia/repos/gene_annotation_episode')
C=R/'verification/hmmer_api_resource_2026-10-22_003'
P=R/'verification/hmmer_api_resource_2026-10-22_002'
D=R/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_003.md'
PIN='cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623'
REPORT_HASH='d24dcb76e39571e8f265501c404b9f1d42672bc814466351cb4d19522b781bae'
MANIFEST_HASH='32dc15a3533d99d36cae42125549b17da6832066c0ec11af51a3afbeadaf59f1'
O=Path(tempfile.mkdtemp(prefix='api003-independent-seal-'))
F={}
def h(p):return sha256(p.read_bytes()).hexdigest()
def j(p):return json.loads(p.read_text())
def check(ok,msg):
 if not ok:raise AssertionError('MISMATCH: '+msg)
def walk(p):
 out={}
 for f in p.rglob('*'):
  check(not f.is_symlink(),'symlink '+str(f))
  if f.is_file():out[f.relative_to(p).as_posix()]=f
  else:check(f.is_dir(),'special member '+str(f))
 return out

def main():
 check(h(D)==REPORT_HASH,'report digest');check(h(C/'MANIFEST.json')==MANIFEST_HASH,'manifest digest')
 m=j(C/'MANIFEST.json');check(set(m)=={'version','implementation_sha256','publication_state','members'},'outer schema')
 check(m['implementation_sha256']==PIN and m['publication_state']=='root_verified_readonly','outer pin/state')
 rows=m['members'];check(len(rows)==1444,'member1444 count')
 check(all(set(r)=={'path','sha256','bytes','mode'} for r in rows),'member schema')
 names=[r['path'] for r in rows];check(len(set(names))==len(names),'duplicate member')
 a=walk(C);check(set(a)==set(names)|{'MANIFEST.json'},'extra/missing file membership')
 modes=Counter();size=0
 for r in rows:
  rel=r['path'];p=Path(rel);check(not p.is_absolute() and '..' not in p.parts and p.as_posix()==rel,'unsafe/noncanonical path '+rel)
  f=a[rel];s=f.stat();mode=format(stat.S_IMODE(s.st_mode),'04o')
  check(s.st_size==r['bytes'],'member size '+rel);check(h(f)==r['sha256'],'member hash '+rel)
  check(mode==r['mode'] and not s.st_mode&0o222,'member mode '+rel);modes[mode]+=1;size+=s.st_size
 check(size==32121307,'member byte32121307 total');check(format(stat.S_IMODE((C/'MANIFEST.json').stat().st_mode),'04o')=='0444','outer mode')
 dirs=[C]+[p for p in C.rglob('*') if p.is_dir()];directory_modes=Counter(format(stat.S_IMODE(p.stat().st_mode),'04o') for p in dirs);writable_directories=sum(bool(p.stat().st_mode&0o222) for p in dirs)
 parent_dirs={q.as_posix() for rel in a for q in Path(rel).parents if q.as_posix()!='.'}
 check({p.relative_to(C).as_posix() for p in dirs[1:]}==parent_dirs,'extra empty directories')
 check(D.read_bytes()==(C/'docs'/D.name).read_bytes(),'exact report copy')
 F['seal']={'report_sha256':h(D),'manifest_sha256':h(C/'MANIFEST.json'),'members':len(rows),'member_bytes':size,'total_files_with_outer_manifest':len(a),'outer_manifest_bytes':(C/'MANIFEST.json').stat().st_size,'file_modes':dict(modes),'outer_manifest_mode':'0444','directory_count':len(dirs),'directory_modes':dict(directory_modes),'writable_directories':writable_directories,'directory_modes_declared_by_manifest':False,'extra_missing_files':0,'symlinks_special_members':0,'extra_empty_directories':0,'exact_report_copy':True}
 inp=j(C/'evidence/root-final/INPUTS.json');ids=j(C/'SOURCE_IDENTITIES.json');src=inp['source_files'];tests=inp['tests']
 check(h(C/'evidence/root-final/INPUTS.json')=='b0e07e293e22a18e52a6a7c695a3ea7c6ed3a4a48a17e7a931085e0b8009aa6e','INPUTS hash')
 check(len(src)==131 and len(tests)==205,'runtime/test counts');check(ids['files']==src and ids['tests']==tests,'INPUTS/SOURCE_IDENTITIES equality')
 check({str(p.relative_to(C)) for pkg in ['gene_annotation_episode','method_loop'] for p in (C/pkg).rglob('*.py')}==set(src),'runtime source membership')
 check({str(p.relative_to(C)) for p in (C/'tests').rglob('*.py')}==set(tests),'test membership')
 for rel,d in list(src.items())+list(tests.items()):check(h(C/rel)==d,'runtime/test bytes '+rel)
 pin=sha256()
 for rel in sorted(src):pin.update(rel.encode('utf8')+b'\0'+bytes.fromhex(h(C/rel)))
 check(pin.hexdigest()==inp['runtime_implementation_sha256']==ids['implementation_sha256']==PIN,'recomputed runtime pin')
 base=j(C/'lineage/GENERATION_BASELINE_001.json');check(h(C/'lineage/GENERATION_BASELINE_001.json')==inp['baseline_sha256']=='c0b61a45ef0cfbe6b0ab9b76a984e280ea2aad5f1ea4719e7e18f7522b3db554','baseline hash')
 old=base['source_files'];ot=base['test_files'];added=set(src)-set(old);changed={r for r in old if r in src and old[r]!=src[r]};same={r for r in old if old[r]==src.get(r)}
 ta=set(tests)-set(ot);tc={r for r in ot if r in tests and ot[r]!=tests[r]};ts={r for r in ot if ot[r]==tests.get(r)}
 check(len(added)==3 and len(changed)==12 and len(same)==116 and not set(old)-set(src),'runtime lineage')
 check(len(ta)==6 and tc=={'tests/test_run_statistics.py'} and len(ts)==198 and not set(ot)-set(tests),'test lineage')
 check(set(inp['changed_or_new_sources'])==set(ids['changed_or_new_runtime_sources_from_generation002'])==added|changed,'runtime delta records')
 check(set(inp['added_tests'])==set(ids['new_tests'])==ta,'added test records')
 for rel,d in list(old.items())+list(ot.items()):check(h(C/'parent-generation002'/rel)==d,'baseline original source/test '+rel)
 F['source_identity']={'runtime_pin':pin.hexdigest(),'pin_algorithm':'sha256(concat(sorted relative UTF8 path,NUL,raw SHA256(file)))','runtime_files':131,'test_python_files':205,'all_membership_bytes_match':True,'runtime_added':sorted(added),'runtime_changed':sorted(changed),'runtime_unchanged':len(same),'runtime_removed':0,'tests_added':sorted(ta),'tests_changed':sorted(tc),'tests_unchanged':len(ts),'tests_removed':0}
 pfiles=walk(P);copies=walk(C/'parent-generation002');check(len(pfiles)==len(copies)==694 and set(pfiles)==set(copies),'parent694 membership')
 for rel,p in pfiles.items():check(p.read_bytes()==copies[rel].read_bytes(),'parent byte equality '+rel)
 check(h(P/'MANIFEST.json')==ids['parent_manifest_sha256']=='fa15fca23194b03b0fb2cef06c8082dda05226213339caa8fba7510892dd71ea','parent manifest hash')
 F['parent002']={'exact_files_including_manifest':694,'all_byte_identical_to_original':True,'manifest_sha256':h(P/'MANIFEST.json')}
 res=j(C/'evidence/root-final/RESULTS.json');check(h(C/'evidence/root-final/RESULTS.json')=='827cd5eff370f76a333520bc2943fb70da0218befd4f9de52f0b7d3090f14fce','root RESULTS hash')
 check(res['runtime_implementation_sha256']==PIN and res['all_source_and_test_bytes_and_membership_unchanged'] and res['source_file_count']==131 and res['test_file_count']==205,'root pin/identity declarations')
 nodes=set();classes=set();groups=[]
 for g in res['groups']:
  name=g['group'];xp=C/'evidence/root-final'/(name+'.xml');lp=C/'evidence/root-final'/(name+'.log');xml=ET.parse(xp).getroot();cases=xml.findall('.//testcase')
  ns=[q.attrib['classname']+'::'+q.attrib['name'] for q in cases];cs={q.attrib['classname'] for q in cases}
  check(h(xp)==g['xml_sha256'] and h(lp)==g['log_sha256'],'root group evidence hashes '+name)
  check(len(ns)==len(set(ns))==g['passed'] and set(ns)==set(g['node_ids']),'XML node ledger '+name)
  check(all(not list(q) for q in cases),'XML nonpassing testcase '+name)
  check(all(int(q.attrib.get(k,0))==0 for q in xml.findall('.//testsuite') for k in ['failures','errors','skipped']),'XML suite nonpass counters '+name)
  check(not nodes.intersection(ns) and not classes.intersection(cs),'root group overlap '+name)
  check(g['exit_code']==0,'recorded group exit '+name)
  check(re.search(r'\b'+str(g['passed'])+r' passed in '+re.escape(format(g['duration_seconds'],'.2f'))+r's\b',lp.read_text()) is not None,'log count/time '+name)
  check(all(c.replace('.','/')+'.py' in tests for c in cs),'XML files in frozen tests '+name)
  nodes.update(ns);classes.update(cs);groups.append({'group':name,'cases':len(ns),'files':sorted(c.replace('.','/')+'.py' for c in cs),'duration_seconds':g['duration_seconds'],'recorded_exit_code':0,'log_sha256':h(lp),'xml_sha256':h(xp)})
 check(len(nodes)==res['distinct_current_pin_cases']==213 and len(classes)==11,'final213 across11')
 counts=j(C/'VERIFICATION_COUNTS.json');check(counts['distinct_current_pin_cases']==213 and counts['disjoint_current_pin_test_files']==11 and not counts['producer_invocations_counted_in213'],'counting boundary')
 F['root_final_regression']={'distinct_xml_nodes':len(nodes),'disjoint_test_files':len(classes),'node_overlap':0,'file_overlap':0,'failures':0,'errors':0,'skips':0,'groups':groups,'runtime_pin':res['runtime_implementation_sha256'],'reexecuted_by_verifier':False,'producer_invocations_counted_in213':False}
 (O/'final-node-ledger.json').write_text(json.dumps({'runtime_pin':PIN,'node_ids':sorted(nodes)},indent=2)+'\n')
 ci=j(C/'COPIED_INPUT_IDENTITIES.json');check(ci['copied_file_count']==len(ci['files'])==1434,'1434 copied input records')
 for rel,row in ci['files'].items():
  check(h(C/rel)==row['candidate']['sha256']==row['source']['sha256'],'copied input recorded hash '+rel)
  check((C/rel).stat().st_size==row['candidate']['bytes']==row['source']['bytes'],'copied input recorded size '+rel)
  check(format(stat.S_IMODE((C/rel).stat().st_mode),'04o')==row['planned_published_mode'],'copied input planned mode '+rel)
  check(row['redaction_count']==0,'copied input redaction '+rel)
 assets=j(C/'STATIC_INPUTS.json');check(assets['asset_count']==len(assets['files'])==319 and assets['non_python_count']==317,'static319/317 counts')
 check(sum(Path(r).suffix=='.py' for r in assets['files'])==2,'static archival2 scripts')
 for rel in assets['files']:check((C/rel).read_bytes()==(P/rel).read_bytes(),'static parent bytes '+rel)
 refs=j(C/'CHECKLIST_REFERENCES.json');cp=Path(refs['source']);lines=cp.read_text().splitlines();check(h(cp)==refs['source_sha256']=='76eb448324a797c01174b28b13b7c7becfaac07fd1c7ee1c5586c3e573d82d86','checklist pin')
 check(len(refs['entries'])==len({e['label'] for e in refs['entries']})==41,'41 checklist labels');nos=[]
 for e in refs['entries']:
  rp,no=e['reference'].rsplit(':',1);no=int(no);check(Path(rp)==cp and e['label'] in lines[no-1],'checklist source line '+e['label']);nos.append(no)
 check(nos==sorted(nos),'checklist reference order')
 F['retained_inputs']={'copied_input_record_hashes_bytes_modes_verified':1434,'unchanged_parent_static_assets':319,'non_python_static':317,'archival_python_scripts':2,'ordered_checklist_references':41,'checklist_sha256':h(cp)}
 producer=[('A custody','evidence/a-custody/custody_final_003.log',28,144.16),('A identity','evidence/a-custody/custody_identity_channels.log',2,15.91),('A operations','evidence/a-custody/baseline_operations.log',36,64.78),('B statistics','evidence/b-statistics/pytest-final.stdout.log',77,49.46),('B caller','evidence/b-case-estimator/pytest-001.log',14,135.88),('C final','evidence/c-integration/final-owned-after-scope025.log',7,74.30),('root earlier joined','evidence/root-connected/after-source-version-correction.log',1,13.26),('C native overrun','evidence/c-integration/first-regression.log',56,259.63)]
 for label,rel,n,sec in producer:check(re.search(r'\b'+str(n)+r' passed in '+re.escape(format(sec,'.2f'))+r's\b',(C/rel).read_text()) is not None,'producer log '+label)
 over=(C/'evidence/c-integration/SCOPE_OVERRUN.md').read_text();check(len(re.findall(r'^- `tests/test_native_timing_information_runtime.py::',over,re.M))==7,'recorded7 native node IDs')
 check('eight selected real alignments' in over and '20 GiB memory, 4 GiB scratch, no wall-time' in over,'recorded native count/limits')
 c=j(C/'evidence/c-integration/RESULTS.json');check(c['implementation_source_sha256']==PIN and c['counts_are_per_invocation_and_overlap'],'C final pin/counting')
 check(c['earlier_native_containing_regression']['passed']==56 and not c['earlier_native_containing_regression']['rerun'],'C earlier native-containing record')
 check(c['final_check']['passed']==7 and 'no native process' in c['final_check']['actual_work'],'C distinct final7 record')
 b=j(C/'evidence/b-statistics/evidence.json');check('reconstructed' in b['stdout_provenance'] and 'not rerun' in b['stdout_provenance'],'B stdout provenance')
 F['report_boundaries']={'retained_invocations':[{'label':label,'log':rel,'passed':n,'seconds':sec,'counted_in213':False} for label,rel,n,sec in producer],'only_root135_plus78_counted_in213':True,'no341_at_one_pin_result_inferred':True,'C_overrun':{'earlier_checks':56,'seconds':259.63,'recorded_native_nodes':7,'recorded_tiny_local_alignments':8,'recorded_path':'sequence_worker through protected systemd native lifecycle','recorded_limits':'20GiB RAM/4GiB scratch/no wall-time limit','separate_from_C_final7_and_root_final213':True},'B_reconstructed_stdout_disclosed':True,'historical_candidate_unsealed_statuses_preserved':True,'source_semantics_and_historical_execution_not_reproven_by_file_checker':True}
 check(h(D)==REPORT_HASH and h(C/'MANIFEST.json')==MANIFEST_HASH,'seal unchanged at end')
 F['limits']=['The original checker added an undeclared stronger directory-readonly assertion and stopped at writable directory mode0775; original checker and /tmp/api003-independent-seal-q9sab8_r/FAILURE.json are preserved. Root clarified declared readonly means member file modes. All122 directory modes remain unchanged and are a custody limitation, not a declared-mode mismatch.','Read-only Python stdlib filesystem/hash/JSON/XML/regular-expression inspection; no application imports, Store/Workflow/history/ledger construction, tests, services, native execution, network/model calls, scientific database access, active-process inspection or production/scientific/sealed-artifact mutation.','This verifies present sealed evidence integrity, source identities, recorded regression nodes/counts and reported boundaries. It does not reproduce execution or establish new implementation/scientific behavior.','Historical native execution count/path/limits and absence of external/model/live-workspace activity are retained producer provenance, not independently re-executed observations.','All1434 copied records match their saved source/candidate identities; current original mutable /tmp input sources are not newly consulted. All694 original immutable API002 files and319 static assets are directly byte-compared.','Separate API003 scope026 actual-service work, live scientific state and whole fixed-goal completion are outside this check.','One initial administrative Python writer text failed with IndentationError before execution/file creation; the corrected checker is new and writes only this /tmp output.']
 F['status']='PASS';F['checked_at_utc']=datetime.now(timezone.utc).isoformat()
 (O/'findings.json').write_text(json.dumps(F,indent=2)+'\n')
 note=['# Independent sealed API003 verification','','PASS. Both requested report/manifest hashes match. All1,444 members match hash, size and read-only modes, totaling32,121,307 bytes; no extras/missing files, symlinks/special members or empty extra directories. The report copy is exact.','', 'Directory custody limitation: all122 directories have mode0775. Directory modes are absent from the manifest and are not a promised replacement-resistant seal. The initial stronger directory-readonly assertion failed and is preserved separately; this corrected checker verifies declared member file modes without inventing a directory requirement.','', 'The runtime pin independently recomputes across131 sources to '+PIN+'. Exactly205 frozen test/helper files match recorded memberships/bytes. All694 parent API002 files, including its outer manifest, are byte-identical to the original.','', 'Root final XML gives135+78=213 distinct passing cases across11 disjoint files, with no overlap/failures/errors/skips. Logs, exact node ledgers, recorded exit0, time summaries and hashes agree. This verification did not rerun pytest. Producer/earlier groups remain separate overlapping evidence; no341-at-one-pin inference is made.','', 'The report explicitly preserves C earlier56-check no-native-assignment overrun: seven recorded native nodes/eight tiny local alignments via the protected native lifecycle at20GiB RAM/4GiB scratch/no wall-time limit. Those historical records remain distinct from C final7 synthetic-native invocation and root final213, whose selected files exclude the native-runtime group. No native work was executed by this verifier.','', 'All1434 copied-input records match saved source/candidate hashes/bytes and final modes; all319 static assets match original API002 bytes. All41 checklist IDs point to their exact pinned source lines in original order. Historical candidate/preparation status and reconstructed B stdout remain explicitly disclosed lineage.','', 'This is evidence integrity/boundary verification using only stdlib file reads/hashes/JSON/XML, not a new source-behavior audit. Historical execution and no-external-activity claims remain recorded producer provenance. No application import, test/service/native/model/network call or scientific state access occurred. Only new /tmp verification files were written. The fixed goal remains active and incomplete.','', 'Exact findings, group file sets, all213 nodes, provenance distinctions and limits are in findings.json and final-node-ledger.json. An initial administrative writer string failed before execution/file creation; no sealed/source/state artifact was affected.','']
 (O/'NOTE.md').write_text('\n'.join(note));(O/'check.py').write_bytes(Path(__file__).read_bytes())
 entries=[{'path':p.name,'bytes':p.stat().st_size,'sha256':h(p)} for p in sorted(O.iterdir()) if p.is_file() and p.name!='MANIFEST.json']
 (O/'MANIFEST.json').write_text(json.dumps({'version':'independent_api003_sealed_evidence_verification_v1','status':'PASS','members':entries},indent=2)+'\n')
 print(json.dumps({'status':'PASS','directory':str(O),'note_sha256':h(O/'NOTE.md'),'checkscript_sha256':h(O/'check.py'),'findings_sha256':h(O/'findings.json'),'manifest_sha256':h(O/'MANIFEST.json'),'report_sha256':h(D),'sealed_manifest_sha256':h(C/'MANIFEST.json'),'members':1444,'bytes':size,'runtime_files':131,'runtime_pin':pin.hexdigest(),'test_python_files':205,'distinct_final_cases':213,'disjoint_files':11,'exact_parent_files':694},indent=2))
try:main()
except Exception as e:
 (O/'FAILURE.json').write_text(json.dumps({'status':'FAIL','error':str(e),'partial_findings':F},indent=2)+'\n')
 print('FAILED',str(O),str(e),flush=True)
 raise
