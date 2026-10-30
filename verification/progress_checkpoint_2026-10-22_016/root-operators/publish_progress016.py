"""Add permanent record016 and a bounded evidence capsule, preserving record015."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import tempfile

ROOT = Path('/home/chia/repos/gene_annotation_episode')
PREVIOUS = ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_015.md'
PREVIOUS_SHA = '29276414b63013921834f0589ae052137434c0dd85273f5405a12821a8a03d8d'
OUT = ROOT/'verification/progress_checkpoint_2026-10-22_016'
DOC = ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_016.md'
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def read(path):
    path = Path(path)
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode)
    with path.open('rb') as stream:
        assert stream.fileno() >= 0
        opened=os.fstat(stream.fileno())
        assert (opened.st_ino,opened.st_dev)==(before.st_ino,before.st_dev)
        raw=stream.read()
    after=path.lstat()
    def witness(info):
        return {'sha256':digest(raw),'bytes':info.st_size,
            'mode':format(stat.S_IMODE(info.st_mode),'04o'),'mtime_ns':info.st_mtime_ns,
            'inode':info.st_ino,'device':info.st_dev}
    assert witness(before)==witness(after) and len(raw)==after.st_size
    return raw,witness(before)


def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb',closefd=False) as stream:
            stream.write(raw);stream.flush()
        os.fchmod(fd,0o444);os.fsync(fd)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publication-check',type=Path,required=True)
    parser.add_argument('--caller-verification',type=Path)
    parser.add_argument('--first-request-proof',type=Path)
    args=parser.parse_args()
    assert not os.path.lexists(OUT) and not os.path.lexists(DOC)
    previous,_=read(PREVIOUS);assert digest(previous)==PREVIOUS_SHA
    old=previous.decode()
    checklist=old[old.index('## Retained correction checklist'):old.index('## Completed006 engineering and publication')]
    assert len(re.findall(r'^- \[[ x]\] \*\*',checklist,re.M))==41
    check_raw,_=read(args.publication_check);check=json.loads(check_raw)
    assert check['status']=='passed' and check['runtime_pin']==PIN
    assert check['original_files_checked']>0 and check['original_trees_checked']==6
    capsule=ROOT/'verification/local_commission_frame_integration_2026-10-22_001'
    report=ROOT/'docs/LOCAL_COMMISSION_FRAME_INTEGRATION_VERIFICATION_2026-10-22_001.md'
    manifest_raw,_=read(capsule/'MANIFEST.json')
    report_raw,_=read(report)
    assert digest(manifest_raw)==check['manifest_sha256']
    assert digest(report_raw)==check['report_sha256']
    stage=Path(tempfile.mkdtemp(prefix='.'+OUT.name+'-staging-',dir=OUT.parent))
    controls={}
    def copy(source,member):
        raw,before=read(source);write(stage/member,raw)
        assert read(source)[1]==before
        controls[member]={'source':str(source),'before':before,'after':before,
            'copy_equals_source':True}
    copy(args.publication_check,'engineering/PUBLICATION_CHECK.json')
    copy(capsule/'MANIFEST.json','engineering/MANIFEST007.json')
    copy(report,'engineering/REPORT007.md')
    copy(PREVIOUS,'lineage/PROGRESS015.md')
    publication_logs=Path('/tmp/factual-frame007-root-publication-20261022-001')
    for path in sorted(publication_logs.iterdir()):
        if path.is_file() and not path.is_symlink():copy(path,'root-publication/'+path.name)
    caller_plan=Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
    caller_handoff=Path('/tmp/configured-literature-localization-invocation-20261022-001-nuzn9c6c')
    for directory,prefix,manifest_name,manifest_sha in (
            (caller_plan,'literature-caller-plan','MANIFEST_FINAL001.json','d1a696d49123fbf6363f8cb9bb46a7dc2fc413ba06b1f9f9f9e81947a51f06ad'),
            (caller_handoff,'literature-caller-preparation','MANIFEST_FINAL002.json','1f4644c5512295d0ca37181e68b84e98f4e07be65987eecaafb799cb9a912a0f')):
        raw,_=read(directory/manifest_name);assert digest(raw)==manifest_sha
        for name,row in json.loads(raw)['members'].items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            b,_=read(directory/name);assert digest(b)==row['sha256'] and len(b)==row['bytes']
            copy(directory/name,prefix+'/'+name)
        copy(directory/manifest_name,prefix+'/'+manifest_name)
    copy(ROOT/'docs/CONFIGURED_LITERATURE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md','LITERATURE_PREPARATION_SCOPE001.md')
    caller_review_clause='Independent output verification is being prepared; no independent SQL review is claimed here.'
    if args.caller_verification is not None:
        review_raw,_=read(args.caller_verification);review=json.loads(review_raw)
        assert review['status']=='verified_prepared_not_started'
        copy(args.caller_verification,'literature-caller-independent/VERIFICATION001.json')
        for name in ('verify_actual_preparation001.py','SCOPE001.md'):
            copy(args.caller_verification.parent/name,'literature-caller-independent/'+name)
        caller_review_clause='The separate independent output verifier passed; its exact result and SQL limits are retained in this capsule.'
    launch_clause='No configured launch or first-request evidence is included in this record.'
    if args.first_request_proof is not None:
        first_raw,_=read(args.first_request_proof);first=json.loads(first_raw)
        assert first['status']=='first_request_verified'
        assert digest(first_raw)=='c052692a7e1d072e0a9c94e1234c71a4ac49b6abbf3a5a8f6634c0b925d92895'
        for path in sorted(args.first_request_proof.parent.iterdir()):
            if path.is_file() and not path.is_symlink():copy(path,'literature-first-request/'+path.name)
        launch_plan=Path('/tmp/configured-literature-launch-plan-20261022-001-li2s253s')
        launch_manifest=read(launch_plan/'MANIFEST_FINAL001.json')[0]
        assert digest(launch_manifest)=='4b78ee733c57623ee484e6101e8408161e9d990020b385a54eb840d1c0e895f7'
        for name,row in json.loads(launch_manifest)['members'].items():
            b,_=read(launch_plan/name);assert digest(b)==row['sha256'] and len(b)==row['bytes']
            copy(launch_plan/name,'literature-launch-plan/'+name)
        copy(launch_plan/'MANIFEST_FINAL001.json','literature-launch-plan/MANIFEST_FINAL001.json')
        copy(ROOT/'docs/CONFIGURED_LITERATURE_CALLER_LAUNCH_SCOPE_2026-10-22_001.md','LITERATURE_LAUNCH_SCOPE001.md')
        launch_evidence=Path('/tmp/configured-literature-localization-launch-20261022-001')
        for name in ('LAUNCH_COMMAND001.json','SOURCE_BEFORE001.json','PROCESS_STARTED001.json'):
            copy(launch_evidence/name,'literature-actual-launch/'+name)
        launch_clause='Root then launched the ordinary configured-model CLI once under permanent scope42923d99c03a842525b5535c39eccd6b1f86be19d436259d5e0402cd70d13baa, without resume or a transport shim. Actual run '+first['run_id']+', root '+first['episode_id']+', uses the same frozen137-file source. The separate one-shot readonly first-request proof passed: resultc052692a7e1d072e0a9c94e1234c71a4ac49b6abbf3a5a8f6634c0b925d92895. Saved call0 is v3, raw request681735bytes/SHA0a5bd2e27b57f1e07fe5a50ecbe91ace99f5306e35cc2bf28df7757fe95b0c31, with its original complete-empty commission frame outside raw/model contexts. Observed initial scientific progress12, monitoring0, annotation score0 and empty own histories are not imported old175 observations. The initial receipt index has339 rows and199/200 selected refs; the remaining actual collection_member is paged. Current counts at that later capture were2episodes,5actions,2observations,6calls, separate from the saved initial inputs. That count alone establishes no child role, typed return or later parent scientific use. Old006 remains separate. Live scientific/provider logs are excluded; no scientific completion is inferred from launch or call0.'
    for number in ('001','002'):
        directory=Path('/tmp/configured-caller-actual-science-20261022-'+number)
        members=json.loads(read(directory/('MANIFEST'+number+'.json'))[0])['members']
        for name,row in members.items():
            assert '/' not in name and name not in {'.','..'}
            raw,_=read(directory/name)
            assert digest(raw)==row['sha256'] and len(raw)==row['bytes']
            copy(directory/name,'actual-science'+number+'/'+name)
        copy(directory/('MANIFEST'+number+'.json'),'actual-science'+number+'/MANIFEST'+number+'.json')
    operator_root=Path('/tmp/configured-api-caller-root-preparation-20261022-001')
    for name in ('capture_science_gain001.py','capture_science_gain002.py',
            'capture_science_gain002.attempt001.py','capture_science_gain002.attempt002.py',
            'science_gain001.stdout.log','science_gain001.stderr.log',
            'science_gain002.stdout.log','science_gain002.stderr.log',
            'science_gain002.attempt002.stdout.log','science_gain002.attempt002.stderr.log',
            'science_gain002.attempt003.stdout.log','science_gain002.attempt003.stderr.log'):
        copy(operator_root/name,'root-operators/'+name)
    copy(Path(__file__),'root-operators/'+Path(__file__).name)
    body=('''# Separate permanent progress record016

This additive record follows unchanged015, SHA256 '''+PREVIOUS_SHA+'''. The same41 IDs, order, checked states and historical descriptions follow verbatim. Later evidence is appended after them. No whole-goal item is closed by this increment.

'''+checklist+'''## Completed factual integration007

The isolated frozen007 implementation has137 runtime files and222 test files, source pin '''+PIN+'''. It saves factual local commission frames with fresh durable v3 requests and forwards the original selection/after-action pair into factual completed-context v6. Saved contexts replay without new capture. Legacy saved formats remain unchanged. These are factual inputs; no pending-aware numerical law, forecast horizon, prior, smoothing or changed continuation rule is adopted.

The original215-case compatibility invocation passed209 and failed six at its historical d39 source pin. Five failures asserted old fresh-request formats. One exposed a real defect: saved-v6 replay wrongly required a capture callback. Scope002 removes that condition only on saved replay, and adds callback-absent regressions for both observe paths with capture/provider/backend/write work forbidden. The exact two original test files and their assertion patches are preserved under scope002; the original690-file baseline is unchanged. All other original inputs retain their bytes.

At the repaired pin, the full affected invocation passed61/61 with unchanged source and required inputs. The unchanged four actual detached-worker/interrupted-request cases passed4/4 in52.018s at that same pin. Earlier component/runtime/reconstruction results retain their original source versions and are not summed into a coverage total. All engineering invocations use scripted fixtures, not configured-model scientific reasoning.

The permanent [integration report](../LOCAL_COMMISSION_FRAME_INTEGRATION_VERIFICATION_2026-10-22_001.md) has SHA256 '''+check['report_sha256']+'''. Its capsule manifest is '''+check['manifest_sha256']+'''. Root ran the independently written, fully read checker, verifying exact member hashes, sizes, modes, source pin, baseline/amendments, XML results, aliases and original copy controls. It checked '''+str(check['original_files_checked'])+''' original files and six evidence trees. It invoked no application, database, model, service or test. The capsule contains engineering fixtures only; original006 and actual scientific workspaces were not swept into it.

Publication preparation failures are retained separately from test results. Root first assumed the wrong final inventory key, then attempted a dependent wrapper without its log directory; neither command ran the application or assembly. The first actual assembly rejected the named FIFO left by the existing reconstruction fixture. The corrected source-only sealer preserves the original FIFO and its before/after type/mode/time/inode/device/size through a clearly named metadata-only JSON record, without opening or copying its stream. General publication/checker special-node rejection remains unchanged. Original partial outputs and exact failed commands remain preserved.

## Actual scientific evidence under unchanged006

The separate configured_api_prechoice_001 investigation continues under frozen006 and its own configured controller. Proof001 preserves actual parent action13: a qualified Cytoplasm source assertion weakens an existing IM hypothesis, while the original workbook also contains an IM sucrose-gradient classification. The two assertions do not resolve localization. Its new assessment appears in the later parent decision context; scientific progress12→13 and annotation support0 remain separate.

Proof002 preserves actual actions29/30/32/33/34. A new public hmmscan/Pfam result supports broad PF03372/Exo_endo_phos correspondence. The same profile does not establish catalytic activity or substrate; the activity qualification explicitly reuses that source claim. An inherited partial P25618/CWH43 alignment does not discriminate the proposed lyso-GPI-related role. Actual raw own-action gains are0,+1,+1,0,+1, cumulative13→16; the annotation remains unresolved. Later call35 receives scientific progress16 and a separate annotation vector. The saved public source artifact and exact253-aa target sequence are included. These proofs establish qualified own scientific findings, not experimental validation or returned-child influence.

Proof002's fixed snapshot has one episode,35 action rows,27 observations and zero commissions. Later readonly status at11:08UTC has42 action rows,32 observations,scientific credit17 and zero commissions; the later17th unit's meaning is not claimed by these earlier proofs. Two further selected XLSX operations failed; they are not observations or invented progress. Active-table absence is unknown, not zero. No active or original database is copied into this record. The actual operators' initial proof failures are retained: wrong product length field, then existing empty destination; corrected capture uses the actual sequence artifact. Neither correction changed scientific state or runtime code.

## Remaining implementation and human decisions

Separate literature already has an existing commissioning/form/receipt route independent of the empty selectable support population A0. The isolated caller described below targets a configured-model literature investigation of the localization discrepancy. No new episode type, library population, numerical policy, forced action order or controller override is needed or adopted. A prepared plan or available route does not demonstrate a scientific child or its later use.

Actual caller preparation for configured_literature_localization_001 then succeeded once in15.2941s at11:22UTC under the new permanent scope81543967a4f5e85490c8f3fb92ee36e7491f46a4206c928ae01f79b86af7ab38. Its fresh custody receipt b7b59190ba1f5e28b3c688a2ff0189efba735862b14826cca0ee1377c80ac9f6 binds198 original selected refs plus two fresh lineage refs to200 inherited refs. Parameters5ab22e01f87cec425adaa7dcde1ffbaa5df776a8a0070a77e6c746870af74d73 preserve the reviewed numerical operands. Native registry execution_registry_d0dbd700ba854b2d83c0c5c57ca7c598 and public registry execution_registry_9d451c293fb649cea87d48ab2f5ea4d2 are fresh. All three original source-guard JSON files are byte-identical0dd69bebd9c2cf42dcef6f0408f38c9392ceb6030e94a748f11ce7e5801dc15b. Preparation made zero new scientific runs, model calls, service calls or native jobs; the old179actions/175observations/180calls are inherited lineage. Its post-prepare working hash1285aebde40f17b731b3f3e8ce878fcd905f093c21fbebb66a992d57a28d9fb3 equals the receipt's historical publication hash in this run. They are measurements at separate instants; neither is a claim about future active bytes. '''+caller_review_clause+'''

The first outer preparation handoff manifest omitted one nested copied plan manifest by basename; original001 and its additive complete002 correction remain preserved. This was a metadata-inventory error, not a caller/application defect or second preparation attempt. The complete002 manifest1f4644c5512295d0ca37181e68b84e98f4e07be65987eecaafb799cb9a912a0f is authoritative for its32 members. This prelaunch result does not establish child decisions, a typed scientific return or later parent integration. Subsequent scientific execution, if started, requires its own actual evidence.

'''+launch_clause+'''

Actual useful child receipt and later parent decisions, composed scientific children, configured recursive monitoring and prospective timing-informed choices, pending-aware numerical continuation, intended HPC execution, and complete connected lifecycle/scientific evidence remain open. The same three human inputs remain unresolved: support/scoring adoption based on the existing concrete route/arithmetic review; wait-forecast horizon and compatible numerical-model contract; and the intended actual HPC host/service/scheduler/access instructions. No unanswered question is treated as approval.

The immutable goal remains active and incomplete. Earlier records are unchanged. The permanent [progress capsule](../../verification/progress_checkpoint_2026-10-22_016/MANIFEST.json) preserves this record, bounded engineering references and the two exact public scientific proofs. It contains no live database, private provider events or rewritten history.
''')
    assert body[body.index('## Retained correction checklist'):body.index('## Completed factual integration007')]==checklist
    write(stage/'PROGRESS.md',body.encode())
    references={'immutable_goal':{'path':'/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt','sha256':'3a5d965c4dc76f6be6bf6c509d019eeabfff854b009f31c40e98de4ff73f096f'},
        'engineering_extent':'Manifest/report/independent checker result only; no recursive prior engineering capsule copy.',
        'scientific_extent':'Two fixed public proof snapshots/artifacts only. No live DB or private provider events.'}
    write(stage/'EXTERNAL_REFERENCES.json',encoded(references))
    for row in controls.values():assert read(row['source'])[1]==row['before']
    write(stage/'COPY_CONTROLS.json',encoded(controls))
    members={p.relative_to(stage).as_posix():{'sha256':read(p)[1]['sha256'],'bytes':p.stat().st_size,'mode':'0444'} for p in stage.rglob('*') if p.is_file()}
    manifest={'version':'permanent_progress_checkpoint_v1','members':members,
        'report_path':str(DOC),'report_sha256':digest(body.encode()),
        'fixed41_same_ids_order_states_descriptions_verbatim':True,'goal_status':'active_incomplete',
        'old_records_replaced':0,'live_databases_or_private_provider_events_copied':0}
    write(stage/'MANIFEST.json',encoded(manifest))
    for p in sorted((p for p in stage.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        p.chmod(0o555);fsync_dir(p)
    stage.chmod(0o555);fsync_dir(stage)
    libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    assert rename(-100,os.fsencode(stage),-100,os.fsencode(OUT),1)==0,ctypes.get_errno()
    fsync_dir(OUT.parent)
    os.link(OUT/'PROGRESS.md',DOC,follow_symlinks=False);fsync_dir(DOC.parent)
    assert read(PREVIOUS)[0]==previous
    assert read(DOC)[0]==read(OUT/'PROGRESS.md')[0]
    for name,row in members.items():
        actual=read(OUT/name)[1]
        assert all(actual[k]==row[k] for k in ('sha256','bytes','mode'))
    print(json.dumps({'record':str(DOC),'sha256':digest(body.encode()),'capsule':str(OUT),
        'manifest_sha256':read(OUT/'MANIFEST.json')[1]['sha256'],'members':len(members),
        'fixed41_verbatim':True,'goal_status':'active_incomplete'},sort_keys=True))


if __name__=='__main__':main()
