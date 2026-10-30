"""Read-only byte, inventory, mode, copy-control and XML checks; no DB opens."""
import hashlib,json,os,stat
from pathlib import Path
import xml.etree.ElementTree as ET

OUT=Path(__file__).parent
ROOT=Path('/home/chia/repos/gene_annotation_episode/verification/configured_api_caller_2026-10-22_001')
DOC=ROOT.parents[1]/'docs/CONFIGURED_API_CALLER_VERIFICATION_2026-10-22_001.md'
PIN='209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'MANIFEST.json').read_text())
files={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')if p.is_file()and not p.is_symlink()}
links={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')if p.is_symlink()}
dirs={'.'}|{p.relative_to(ROOT).as_posix()for p in ROOT.rglob('*')if p.is_dir()and not p.is_symlink()}
assert files==set(m['members'])|{'MANIFEST.json'}
assert links==set(m['aliases'])and dirs==set(m['directories_including_root'])
for rel in files:
 p=ROOT/rel;assert stat.S_IMODE(p.stat().st_mode)==0o444
 if rel!='MANIFEST.json':
  r=m['members'][rel];assert digest(p)==r['sha256']and p.stat().st_size==r['bytes']
for rel in dirs:assert stat.S_IMODE((ROOT/rel).stat().st_mode)==0o555
for rel in links:
 p=ROOT/rel;assert not os.path.isabs(os.readlink(p))and p.resolve(strict=True).is_relative_to(ROOT)
 assert os.readlink(p)==m['aliases'][rel]['published_target']
assert len(m['members'])==m['file_count_excluding_manifest']
assert sum(r['bytes']for r in m['members'].values())==m['content_bytes_excluding_manifest']
runtime=sorted(rel for rel in m['members']if rel.startswith(('source/gene_annotation_episode/','source/method_loop/'))and rel.endswith('.py'))
tests=[rel for rel in m['members']if rel.startswith('source/tests/')and rel.endswith('.py')]
assert len(runtime)==136 and len(tests)==218
pin=hashlib.sha256()
for rel in runtime:pin.update(rel.removeprefix('source/').encode()+b'\0'+bytes.fromhex(digest(ROOT/rel)))
assert pin.hexdigest()==m['runtime_pin']==PIN
b=json.loads((ROOT/'GENERATION_BASELINE_006.json').read_text())
for key in('files','static_assets','instructions'):
 for rel,r in b[key].items():assert digest(ROOT/'source'/rel)==r['sha256']
assert DOC.read_bytes()==(ROOT/'REPORT.md').read_bytes()
assert digest(DOC)==m['report_sha256']and stat.S_IMODE(DOC.stat().st_mode)==0o444
results=json.loads((ROOT/'RESULTS_FINAL.json').read_text())
assert digest(ROOT/'RESULTS_FINAL.json')in DOC.read_text()
assert digest(ROOT/'parent005-MANIFEST.json')=='98e73e6972dfaa087295abc4756d3d30974a7cf14fa3e9cc38461dad519e963a'
copies=json.loads((ROOT/'COPY_RECEIPT.json').read_text())
source_to_member={r['source']:rel for rel,r in copies['regular_files'].items()}
for rel,r in copies['regular_files'].items():
 assert r['before']==r['after']
 p=Path(r['source']);s=p.stat();actual={'sha256':digest(p),'bytes':p.stat().st_size,'mode':f'{stat.S_IMODE(s.st_mode):04o}','mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
 assert actual==r['before'],str(p)
 assert digest(ROOT/rel)==actual['sha256']
selected=[]
for chosen in results['selected_invocations']:
 p=ROOT/source_to_member[chosen['xml']['path']]
 assert digest(p)==chosen['xml']['sha256']
 suites=list(ET.parse(p).getroot().iter('testsuite'));assert len(suites)==1
 counts={key:int(suites[0].attrib[attr])for key,attr in[('cases','tests'),('failed','failures'),('errors','errors'),('skipped','skipped')]}
 assert counts==chosen['actual_xml_counts']==chosen['expected_xml_counts']
 selected.append({'id':chosen['id'],'scope':chosen['scope'],'runtime_pin':chosen['runtime_pin'],'counts':counts})
record={'status':'passed','manifest_sha256':digest(ROOT/'MANIFEST.json'),'report_sha256':digest(DOC),'results_sha256':digest(ROOT/'RESULTS_FINAL.json'),'runtime_pin':PIN,'runtime_files':136,'test_files':218,'regular_files_including_manifest':len(files),'regular_members_excluding_manifest':len(m['members']),'content_bytes_excluding_manifest':m['content_bytes_excluding_manifest'],'directories_including_root':len(dirs),'internal_aliases':len(links),'copied_original_controls_verified':len(copies['regular_files']),'old_baseline_source_tests':len(b['files']),'old_assets':len(b['static_assets']),'normative_inputs':len(b['instructions']),'selected_invocations_by_scope':selected,'grand_total_across_pins':None,'applications_or_databases_or_tests_run_by_checker':0}
with(OUT/'VERIFICATION_FINAL001.json').open('x')as f:f.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
