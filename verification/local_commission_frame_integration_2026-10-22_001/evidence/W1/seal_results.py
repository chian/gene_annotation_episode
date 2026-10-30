"""Seal W1 component evidence; read/hash only outside this task directory."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-007')
OUT=Path(__file__).parent
REPO=Path('/home/chia/repos/gene_annotation_episode')

def digest(data):return hashlib.sha256(data).hexdigest()
def file(p):
    data=p.read_bytes();return {'bytes':len(data),'sha256':digest(data)}
def pin(records):
    outer=hashlib.sha256()
    rows={name:desc for name,desc in records.items() if name.endswith('.py') and name.split('/')[0] in {'gene_annotation_episode','method_loop'}}
    for name,desc in sorted(rows.items()):outer.update(name.encode()+b'\0'+bytes.fromhex(desc['sha256']))
    return outer.hexdigest(),len(rows)

baseline=json.loads((ROOT/'GENERATION_BASELINE_007.json').read_text())
changed=[];missing=[]
for relative,desc in baseline['files'].items():
    p=ROOT/relative
    if not p.is_file():missing.append(relative)
    elif file(p)!=desc:changed.append(relative)
allowed={'gene_annotation_episode/runtime.py','gene_annotation_episode/waiting.py','gene_annotation_episode/wait_estimation_inputs.py'}
assert not missing and set(changed)==allowed,(missing,changed)
guard={'baseline_sha256':file(ROOT/'GENERATION_BASELINE_007.json')['sha256'],'members':len(baseline['files']),
       'changed_existing_paths':changed,'missing':missing,'unexpected_changes':[],
       'all_original_test_bytes_unchanged':all(not p.startswith('tests/') for p in changed),
       'old_test_files':sum(p.startswith('tests/') and p.endswith('.py') for p in baseline['files'])}
(OUT/'BASELINE_GUARD.json').write_text(json.dumps(guard,indent=2)+'\n')

commands=[]
for name in ['invocation-001','invocation-002','invocation-003']:
    directory=OUT/name
    result=json.loads((directory/'RESULT.json').read_text())
    before=json.loads((directory/'BEFORE.json').read_text());after=json.loads((directory/'AFTER.json').read_text())
    assert before==after
    before_pin,count=pin(before)
    suite=ET.parse(directory/'junit.xml')
    cases=list(suite.iter('testcase'))
    failures=[{'classname':c.attrib['classname'],'name':c.attrib['name'],'message':c.find('failure').get('message')} for c in cases if c.find('failure') is not None]
    errors=[c.attrib for c in cases if c.find('error') is not None]
    skipped=[c.attrib for c in cases if c.find('skipped') is not None]
    by_class={}
    for c in cases:by_class[c.attrib['classname']]=by_class.get(c.attrib['classname'],0)+1
    commands.append({'directory':name,'command':json.loads((directory/'COMMAND.json').read_text()),'process_result':result,
        'implementation_sha256':before_pin,'runtime_files':count,'tests':len(cases),'passed':len(cases)-len(failures)-len(errors)-len(skipped),
        'failures':failures,'errors':errors,'skipped':skipped,'by_class':by_class,
        'artifacts':{p.name:file(p) for p in directory.iterdir() if p.is_file()}})
assert (commands[0]['passed'],commands[1]['passed'],len(commands[1]['failures']),commands[2]['passed'])==(174,1,1,69)
assert commands[2]['implementation_sha256']=='d39a6756507bacd8e9ba90f75912cc01822a316f766cc72764154b7205ba81e3'
source_paths=sorted([*ROOT.glob('gene_annotation_episode/**/*.py'),*ROOT.glob('method_loop/**/*.py')])
current={str(p.relative_to(ROOT)):file(p) for p in source_paths}
assert pin(current)[0]==commands[2]['implementation_sha256']
owned=['gene_annotation_episode/local_commission_frame.py','gene_annotation_episode/wait_estimation_inputs.py',
       'tests/test_local_commission_frame.py','tests/test_local_return_evidence.py']
readset=[ROOT/p for p in ['gene_annotation_episode/local_return_history.py','gene_annotation_episode/episode_commissions.py',
    'gene_annotation_episode/completion_evidence.py','gene_annotation_episode/runtime.py','gene_annotation_episode/waiting.py',
    'method_loop/durable.py','method_loop/durable_worker.py','method_loop/identities.py','method_loop/episode.py',
    'tests/test_local_return_history.py','tests/test_episode_commissions.py']]
readset += [REPO/'docs'/p for p in ['LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md',
    'LOCAL_COMMISSION_FRAME_SCOPE_2026-10-22_001.md','LOCAL_COMMISSION_FRAME_SCOPE_2026-10-22_002.md',
    'LOCAL_COMMISSION_FRAME_SCOPE_2026-10-22_003.md','LOCAL_COMMISSION_FRAME_SCOPE_2026-10-22_004.md',
    'LOCAL_COMMISSION_FRAME_VERIFICATION_2026-10-22_001.md']]
readset += [REPO/'verification/local_commission_frame_2026-10-22_001'/p for p in ['implementation/gene_annotation_episode/local_commission_frame.py','tests/test_local_commission_frame.py']]
(OUT/'READSET.json').write_text(json.dumps({'files':{str(p):file(p) for p in readset},'scope':'complete factual producer/E2 and affected validation/consumer functions; no active workspace or private provider data'},indent=2)+'\n')
result={'status':'W1_source_and_tests_frozen_after_targeted_verification_not_release',
    'implementation_sha256':commands[2]['implementation_sha256'],'runtime_files':len(source_paths),
    'owned_files':{p:file(ROOT/p) for p in owned},'invocations':commands,
    'counting':'174 initial-variant passes and69 final focused passes overlap; do not add them.002 retains one reproduced new-validator rejection, fixed in003. No final whole-suite pass is claimed by W1.',
    'correction':'New E2 validation erroneously required identical int/float JSON for controller input/step credit. Actual standard controller converts input int5 to step float5.0. Only the relationship now matches existing LocalReturnHistory._observe numeric equality; both original saved values/raw deltas are preserved.',
    'inspection_correction':'Root suspected closed+non-null failure invalid. Actual validate_return/durable_worker permit closed+formNone+typed failure. No rejection was added; actual immutable C3 publication/capture/validation roundtrip passed in002 and003.',
    'preservation':'Raw fixtures remain directly under each unique invocation directory, outside rotating pytest parents. Pre/post source guards, exact argv/environment, logs/XML and first failure bytes are retained.',
    'limits':['No main/006/active source or scientific workspace writes.','No actual model/public service/native scientific job/child worker was invoked by W1.','No numerical wait/continuation/scoring policy, unit, estimate or new controller observation is introduced by frame capture/validation.',
        'Selection scope/assignment can precede actual normalization/preparation; pure validation checks only provable unchanged kind/role/goal/purpose and C1/pending/return relationships, without recompiling or guessing omitted original facts.',
        'JSON validation does not authenticate backend reads or re-prove historical population completeness. Store and backend windows are separate; stale pending availability may differ from later observed C3.',
        'Own frozen source is held while R/Q/root verification continues; W1 does not claim integration/release/scientific-goal completion.']}
(OUT/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'FINAL_SOURCE_MANIFEST.json').write_text(json.dumps(current,indent=2)+'\n')
members={str(p.relative_to(OUT)):file(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
(OUT/'MANIFEST.json').write_text(json.dumps({'files':members,'member_count':len(members),'total_bytes':sum(v['bytes'] for v in members.values())},indent=2)+'\n')
print(json.dumps({'implementation_sha256':result['implementation_sha256'],'runtime_files':len(source_paths),'old_test_files':guard['old_test_files'],
    'RESULTS_sha256':file(OUT/'RESULTS.json')['sha256'],'MANIFEST_sha256':file(OUT/'MANIFEST.json')['sha256'],'member_count':len(members),'total_bytes':sum(v['bytes'] for v in members.values())},indent=2))
