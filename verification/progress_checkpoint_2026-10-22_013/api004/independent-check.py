from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime, timezone
import json, stat, xml.etree.ElementTree as ET
R=Path('/home/chia/repos/gene_annotation_episode'); C=R/'verification/hmmer_api_resource_2026-10-22_004'; P=R/'verification/hmmer_api_resource_2026-10-22_003'; W=Path('/tmp/gene-annotation-hmmer-api-20261022-004'); O=Path(__file__).parent
D=R/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md'; E=Path('/tmp/api-planning-publication-preparation-20261022-001')
def h(p): return sha256(p.read_bytes()).hexdigest()
def j(p): return json.loads(p.read_text())
def ck(v,s):
    if not v: raise AssertionError(s)
def walk(root):
    out={}
    for p in root.rglob('*'):
        ck(not p.is_symlink(),'symlink '+str(p))
        if p.is_file(): out[p.relative_to(root).as_posix()]=p
        else: ck(p.is_dir(),'special '+str(p))
    return out
ck(h(E/'ROOT_REVIEWED_PUBLICATION_CONTRACT.json')=='6e53b29ea8d0282b14a93794d2ba2c0b8a6e2a2d82f715a3baaea176c0ca47f4','contract')
ck(h(E/'APPROVED_MEMBER_INVENTORY.json')=='1c121423127df09185139a7875eb1a1c219dfe10ea3b8da1e0ebb7c4124573ca','inventory')
ck(h(D)=='d0d7b07e8db1b8410591b48a497cb99a933ae3e04fdabfc1e8a82a017a5c7b7e','report')
manifest=j(C/'MANIFEST.json'); expected=j(E/'APPROVED_MEMBER_INVENTORY.json')['members']; actual=walk(C)
ck(len(expected)==2356 and set(actual)==set(expected)|{'MANIFEST.json'},'membership')
ck(len(manifest['members'])==2356 and len({r['path'] for r in manifest['members']})==2356,'manifest rows')
mr={r['path']:r for r in manifest['members']}; ck(set(mr)==set(expected),'manifest identity')
size=0; modes=Counter()
for rel,row in expected.items():
    p=actual[rel]; parts=Path(rel); ck(not parts.is_absolute() and '..' not in parts.parts,'unsafe path')
    ck(h(p)==row['sha256']==mr[rel]['sha256'] and p.stat().st_size==row['bytes']==mr[rel]['bytes'],'hash/size '+rel)
    mode=format(stat.S_IMODE(p.stat().st_mode),'04o'); ck(mode==row['publish_mode']==mr[rel]['mode'] and mode in {'0444','0555'},'mode '+rel); size+=p.stat().st_size; modes[mode]+=1
ck(size==59005145,'bytes'); dirs=[C,*[p for p in C.rglob('*') if p.is_dir()]]; ck(all(stat.S_IMODE(p.stat().st_mode)==0o555 for p in dirs),'directory modes')
ck(stat.S_IMODE((C/'MANIFEST.json').stat().st_mode)==0o444 and stat.S_IMODE(D.stat().st_mode)==0o444,'outer/report modes'); ck(D.read_bytes()==(C/'docs'/D.name).read_bytes(),'report copy')
inputs=j(C/'evidence/root-final/INPUTS.json'); ck(h(C/'evidence/root-final/INPUTS.json')=='3ec66f29419f90b09461e5e541b852f9a8e8588101dd42935848b9858883d690','input pin'); files=inputs['files']; src={r:v for r,v in files.items() if not r.startswith('tests/')}; tests={r:v for r,v in files.items() if r.startswith('tests/')}; ck(len(src)==133 and len(tests)==211,'source/test counts')
ck({r for r in actual if r.endswith('.py') and r.split('/')[0] in {'gene_annotation_episode','method_loop','tests'}}==set(files),'source/test membership')
pin=sha256()
for rel in sorted(src): pin.update(rel.encode()+b'\0'+bytes.fromhex(src[rel]['sha256']))
ck(pin.hexdigest()==inputs['runtime_pin']==manifest['implementation_sha256']=='16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d','runtime pin')
for rel,v in files.items(): ck(h(C/rel)==h(W/rel)==v['sha256'] and (C/rel).stat().st_size==(W/rel).stat().st_size==v['bytes'],'source/test bytes '+rel)
parent=walk(P); copied=walk(C/'parent-generation003'); ck(len(parent)==len(copied)==1445 and set(parent)==set(copied),'parent1455 membership')
for rel,p in parent.items(): ck(h(p)==h(copied[rel]),'parent original '+rel)
assets=j(P/'STATIC_INPUTS.json')['files']; ck(len(assets)==319,'assets319')
for rel in assets: ck(h(C/rel)==h(P/rel),'asset original '+rel)
results=j(C/'evidence/root-final/RESULTS.json'); ck(h(C/'evidence/root-final/RESULTS.json')=='dba4b6ea4cc6863564145571b82e6ed60bb2f967424a711207e43cb06344dead','results')
nodes=set(); classes=set()
for g in results['groups']:
    xp=C/'evidence/root-final'/(g['group']+'.xml'); lp=C/'evidence/root-final'/(g['group']+'.log'); ck(h(xp)==g['xml_sha256'] and h(lp)==g['log_sha256'],'evidence '+g['group']); cases=ET.parse(xp).getroot().findall('.//testcase'); ns={c.attrib['classname']+'::'+c.attrib['name'] for c in cases}; cs={c.attrib['classname'] for c in cases}; ck(len(ns)==len(cases)==g['passed'] and all(not list(c) for c in cases),'XML cases'); ck(not nodes.intersection(ns) and not classes.intersection(cs),'XML overlap'); ck(ns==set(g['node_ids']),'node ledger'); nodes.update(ns); classes.update(cs)
ck(len(nodes)==316 and len(classes)==19,'distinct316/19')
base=j(W/'GENERATION_BASELINE_004.json')['files']; changed={r for r in base if r in files and base[r]!=files[r]}; added=set(files)-set(base); ck(len([r for r in changed if not r.startswith('tests/')])==8 and not any(r.startswith('tests/') for r in changed),'changed8 existing runtime/0tests'); ck(len([r for r in added if r.startswith('tests/')])==6 and len([r for r in added if not r.startswith('tests/')])==2 and not set(base)-set(files),'added2runtime6tests/no removed')
out={'version':'api004_independent_root_publication_verification_v1','verified_at':datetime.now(timezone.utc).isoformat(),'manifest_sha256':h(C/'MANIFEST.json'),'report_sha256':h(D),'members':len(expected),'member_bytes':size,'runtime_pin':pin.hexdigest(),'runtime_files':len(src),'test_files':len(tests),'distinct_cases':len(nodes),'disjoint_test_files':len(classes),'parent_exact_files':len(parent),'unchanged_assets':len(assets),'file_modes':dict(modes),'directories':len(dirs),'directory_mode':'0555','source_test_originals_unchanged':True,'application_imports_db_opens_model_http_native_calls':0,'goal_complete':False}
with (O/'RESULTS.json').open('x') as f: f.write(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,sort_keys=True))
