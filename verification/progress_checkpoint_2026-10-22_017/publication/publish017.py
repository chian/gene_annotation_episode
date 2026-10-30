"""Add record017 with a bounded capsule; replace no existing record."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import re
import stat
import tempfile

ROOT=Path('/home/chia/repos/gene_annotation_episode')
OLD=ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_016.md'
DOC=ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_017.md'
OUT=ROOT/'verification/progress_checkpoint_2026-10-22_017'
OLD_SHA='047984dc3712f8ff51e6f83f41323bfa188fcdd4d950bebbe99f6ccd99115500'
BUNDLES=(
 ('science003','/tmp/configured-api-science-proof003-R-20261022-7ttdezk2','MANIFEST003.json','52e9cfe9c24f26578d8b9f80e6aa8c722823589731bda8bf1f1493d89d9e07a4','files'),
 ('science003-independent','/tmp/configured-api-science-proof003-independent-20261022-001-r0RFt20J','MANIFEST001.json','3dfe47059fb332f8d94b0404e367b53b8559ec47cb9cd6a50a02c1a0d5117745','files'),
 ('literature-prefix','/tmp/configured-literature-commission-prefix-20261022-001-1HuZX6bk','MANIFEST_FINAL001.json','e7dbac56e54de4ad0d1b3ccab6a6684ecb83661420e7bdc11955ebe762622cfc','members'),
 ('literature-prefix-root-review','/tmp/configured-literature-prefix-root-review-20261022-001','MANIFEST001.json','671062f63daedaad73fce18835d79bec9f5f6895e81ebc96a282a6e2e1a59e44','members'))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path):
 before=path.lstat();assert stat.S_ISREG(before.st_mode) and not path.is_symlink()
 with path.open('rb') as stream:
  opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino)
  raw=stream.read()
 after=path.lstat()
 def witness(s):return {'bytes':s.st_size,'mode':format(stat.S_IMODE(s.st_mode),'04o'),'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'sha256':sha(raw)}
 assert witness(before)==witness(after) and len(raw)==after.st_size
 return raw,witness(after)


def write(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(raw);stream.flush()
  os.fchmod(fd,0o444);os.fsync(fd)
 finally:os.close(fd)


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def sync(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)


def main():
 assert not os.path.lexists(DOC) and not os.path.lexists(OUT)
 old,_=read(OLD);assert sha(old)==OLD_SHA
 old_text=old.decode();fixed=old_text[old_text.index('## Retained correction checklist'):old_text.index('## Completed factual integration007')]
 assert len(re.findall(r'^- \[[ x]\] \*\*',fixed,re.M))==41
 stage=Path(tempfile.mkdtemp(prefix='.'+OUT.name+'-staging-',dir=OUT.parent));controls={};inventories={}
 def copy(source,member):
  raw,before=read(source);write(stage/member,raw)
  assert read(source)[1]==before
  controls[member]={'source':str(source),'before':before,'after':before,'copy_equals_source':True}
 for prefix,directory,manifest_name,digest,key in BUNDLES:
  directory=Path(directory);raw,_=read(directory/manifest_name);assert sha(raw)==digest
  manifest=json.loads(raw);rows=manifest[key]
  if isinstance(rows,list):rows={x['path']:x for x in rows}
  expected=set(rows)|{manifest_name}
  entries=list(directory.rglob('*'))
  assert all(not p.is_symlink() and (stat.S_ISDIR(p.lstat().st_mode) or stat.S_ISREG(p.lstat().st_mode)) for p in entries)
  actual={p.relative_to(directory).as_posix() for p in entries if p.is_file()}
  assert actual==expected
  inventories[prefix]={'root':str(directory),'manifest':manifest_name,'manifest_sha256':digest,'regular_members':len(expected)}
  for name,row in rows.items():
   assert not Path(name).is_absolute() and '..' not in Path(name).parts
   b,w=read(directory/name);assert sha(b)==row['sha256'] and len(b)==row['bytes']
   assert w['mode']==row['mode']=='0444'
   copy(directory/name,prefix+'/'+name)
  copy(directory/manifest_name,prefix+'/'+manifest_name)
 copy(OLD,'lineage/PROGRESS016.md')
 copy(ROOT/'verification/progress_checkpoint_2026-10-22_016/MANIFEST.json','lineage/MANIFEST016.json')
 copy(Path(__file__),'publication/publish017.py')
 copy(Path(__file__).parent/'SCOPE001.md','publication/SCOPE001.md')
 body=('''# Separate permanent progress record017

This additive record follows unchanged016, SHA256 '''+OLD_SHA+'''. Its same41 IDs, order, checked states and historical descriptions follow verbatim. New finite evidence follows them. No whole-goal item is closed by this record.

'''+fixed+'''## Additional actual scientific qualifications under frozen006

The sealed science003 proof remains separate from factual007. It concerns actual run run_23b029a976e343e2bf3957dcc5d0d2ac under frozen006 source209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f. Its primary snapshot is2026-10-22T11:36:43.814647+00:00; its bounded followup is11:39:36.727303+00:00, ending at decision55 and saved call56. Different database read windows are not claimed simultaneous. The actual operators made readonly/query_only transactions, closed them explicitly and recorded total_changes0; they did not run a projector or rescore history.

Action38 acquired a new public phmmer sequence comparison to a reference labelled Exodeoxyribonuclease III. It is not a structure or activity assay. Action39 retained assessment_40b9f1991d5139c31739e6fd, qualification measurement_does_not_establish_claim and relation does_not_discriminate, for the inherited generic catalytic-activity hypothesis. Own observation unit29 records actual marginal1, scientific progress16→17. Actual annotation action40 references that assessment. Its raw own gain is0.

Action55 retained assessment_850a818195e42ac59fce9d37: different_source_subject, incomparable, does_not_discriminate. The recorded PMC7548837 source assay concerns DrXth from Deinococcus radiodurans, not the fixed E. coli YbhP target. This is a transfer limitation, not a new target assay or a finding that target activity is absent. Own observation unit42 records marginal1, progress17→18. Saved raw and presented call56 receive the new committed assessment and its supporting records; a later completed integration action for55 is not established here. Annotation support stays0.36004572009144015 in the six checked calls. Both contributions are own scientific reasoning, with zero commissions in the captured run and one root episode.

The independently written offline verifier passed with limits, result3cb1176fd8b51e339e0a3d3bafca76717a38ab6e8b0738ced9cba2020bb700e8. It checked the35-file input inventory, exact selected action/assessment/receipt/observation relationships, original saved contexts and five new source anchors against the copied UTF-8 byte range20000:22200. One inherited catalytic-term anchor points to an artifact outside this bounded packet and remains explicitly unverified. The original capture's character-versus-byte offset error and both independent verifier corrections remain preserved. The first verifier wrongly reconstructed an extra context digest; the second exposed its unsupported inherited-anchor coverage assumption. Corrected offline checks changed no input, runtime or science. No current live DB, app, model, service or native work was accessed by independent verification. Copied public bytes and typed relationships do not prove scientific entailment or experimental validity.

## Actual separate literature commission and overlapping iteration under frozen007

The finite prefix concerns configured_literature_localization_001, run_d1f1317290114adb95d8a1d58ad970c1, root episode_dbb4a5b6e50c304d33264cfdbebff3133709af38b63d07e69fc29c193ec9ad2c. It uses frozen137-file implementation3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842, unchanged before/after capture. The main read window is11:47:40.393179–.430035UTC; the durable-ledger window is11:47:40.430044–.430368UTC. These are distinct captured cuts, not an atomic cross-database snapshot.

At original decision0 the configured scientific parent selected the existing literature role. C1 digest7d6594cc9b05f127ee3014bd13bd4206a3b74acfaa76eccd473ab0b7ff804c65 binds handle execution_c748279857cf36bcdcc67d2fc2b1df77dece496fab91d9165c31e204de84aa79 and child episode_267cad05b876f1333f2c094cc23c5ad87fd97243aeb837e8bddff8040d08ca7a. The original contained scope is the one fixed target. The requested iterative question examines original source provenance, actual subjects, methods, conditions and limitations behind Cytoplasm versus IM source assertions; it supplies no localization verdict. The actual requested closed seven-field form uses typed semantic references and recorded-fact relationships. Literature remains separate from the A/P/actual-tool scientific library; no new episode type or slot entry was introduced.

The prefix has two active episodes,16 selected actions,13 own observations and17 model-call rows. It preserves a distinct child worker incarnation, PID724788/start48276382/bootd53ef063-e9a7-4ae1-99ad-c64c17bdff26, separately from parentPID724600/start48273549. Those are durable recorded facts, not a present liveness claim. Three completed parent/child call pairs overlap: parent1/child0, parent2/child8, parent3/child10. The child has iterative selected actions and its own local observations. Its private model payloads and unreturned scientific meanings are not exported or admitted to its parent by this inspection.

Parent waits1 and2 wake on original progress_committed events at cursors3 and4, with actual measured wait durations127.190826365 and97.609253593seconds. Each supplies exactly one parent own observation with cumulative scientific progress12 and raw marginal0. Child turns do not become parent observations. Wait3 is pending at this cut. Original saved requests0–3 are v3 with complete factual commission frames outside raw/model contexts, populations0/1/1/1. Completed waits1/2 preserve original v6 selection/after-action frame pairs. Scientific gain, monitoring gain and event probability in the wait estimate remain unbound; these factual frames do not adopt a numerical pending-aware model.

C3 has a present returns table with zero matching rows. C4 admissions table is absent, which is distinguished from an empty installed table. There are no report attempts or received child forms in this cut. The original commission remains pending and no returned-child scientific influence is claimed. Eight typed record IDs are absent from the checkpoint: two are already prepared lineage sources; the other six have no root receipt. Root's separate stdlib-only offline verifier passed, resultf445696c7d13de2143961d14e9280003a910f267e337d50942a64537d25a7cc9, independently matching original C1/selection/worker ownership, computing call intersections, matching zero-gain waits and original frames, and checking the absent return/admission boundary. It reads only the sealed finite prefix; it makes no runtime, database or scientific call.

## Remaining goal work and decisions

The actual typed child closure, C4 admission, exactly-once projection to the parent, and a later completed parent scientific action using the received form remain to be demonstrated. These prefixes do not close C, I, CREDIT, SCIENCE or VERIFY. Composed scientific children still require the first-slot decision; active content remains A0/P19 with variable retrieval of actual tools. Support/scoring adoption, the complete wait-forecast mathematical contract, and intended real HPC environment remain unanswered. Root resurfaced those specific human questions while independent work continues; silence is not approval. API/resource execution planning remains separate from literature and does not create an equivalent-job resource comparison merely by using different adapters.

Original investigations were not resumed by these evidence checks, and the checks requested no application-state or configuration change. Active WAL reads retain ordinary SQLite sidecar behavior; no unchanged-active-file claim is made. No run was stopped, cancelled, retried or given a controller override. The immutable goal remains active and incomplete. This [bounded capsule](../../verification/progress_checkpoint_2026-10-22_017/MANIFEST.json) preserves each newly selected sealed bundle once and exact earlier016 lineage. It contains no live database or private provider log; earlier records remain unchanged.
''')
 assert body[body.index('## Retained correction checklist'):body.index('## Additional actual scientific qualifications under frozen006')]==fixed
 write(stage/'PROGRESS.md',body.encode())
 write(stage/'EXTERNAL_REFERENCES.json',encoded({'prior_record_sha256':OLD_SHA,'input_bundles':inventories,'goal_status':'active_incomplete','old_records_replaced':0,'live_database_or_provider_logs_copied':0}))
 for row in controls.values():assert read(Path(row['source']))[1]==row['before']
 write(stage/'COPY_CONTROLS.json',encoded(controls))
 members={p.relative_to(stage).as_posix():{'sha256':read(p)[1]['sha256'],'bytes':p.stat().st_size,'mode':'0444'} for p in stage.rglob('*') if p.is_file()}
 manifest={'version':'permanent_progress_checkpoint_v1','members':members,'report_sha256':sha(body.encode()),'report_path':str(DOC),'fixed41_verbatim':True,'goal_status':'active_incomplete','old_records_replaced':0}
 write(stage/'MANIFEST.json',encoded(manifest))
 for p in sorted((p for p in stage.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):p.chmod(0o555);sync(p)
 stage.chmod(0o555);sync(stage)
 libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
 rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
 assert rename(-100,os.fsencode(stage),-100,os.fsencode(OUT),1)==0,ctypes.get_errno()
 sync(OUT.parent);os.link(OUT/'PROGRESS.md',DOC,follow_symlinks=False);sync(DOC.parent)
 assert read(OLD)[0]==old and read(DOC)[0]==read(OUT/'PROGRESS.md')[0]
 for name,row in members.items():
  b,w=read(OUT/name);assert sha(b)==row['sha256'] and len(b)==row['bytes'] and w['mode']=='0444'
 print(json.dumps({'record':str(DOC),'report_sha256':sha(body.encode()),'capsule':str(OUT),'manifest_sha256':read(OUT/'MANIFEST.json')[1]['sha256'],'members':len(members),'fixed41_verbatim':True,'goal_status':'active_incomplete'},sort_keys=True))


if __name__=='__main__':main()
