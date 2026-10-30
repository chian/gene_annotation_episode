"""Publish one explicitly handed-off engineering capsule; no application imports."""
from __future__ import annotations
import argparse, ctypes, errno, hashlib, json, os, stat, uuid
from pathlib import Path
import xml.etree.ElementTree as ET

MAIN = Path('/home/chia/repos/gene_annotation_episode')
TARGET = MAIN/'verification/configured_api_caller_2026-10-22_001'
REPORT = MAIN/'docs/CONFIGURED_API_CALLER_VERIFICATION_2026-10-22_001.md'
BASELINE_SHA = '5ba160e1bcbdb14c08b5a929015143b7bd1d316eedc5dd2d239b5f45c6ab644e'
PARENT_SHA = '98e73e6972dfaa087295abc4756d3d30974a7cf14fa3e9cc38461dad519e963a'


def sha(body): return hashlib.sha256(body).hexdigest()
def dumps(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def check(condition, detail):
    if not condition: raise RuntimeError(detail)
def safe(relative):
    p=Path(relative)
    check(not p.is_absolute() and '..' not in p.parts and str(p)==relative and relative not in ('','.'),relative)
    return relative

def witness(path):
    s=path.stat();body=path.read_bytes()
    return {'sha256':sha(body),'bytes':len(body),'mode':f'{stat.S_IMODE(s.st_mode):04o}',
            'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}

def read_ref(ref):
    p=Path(ref['path']);check(p.is_absolute() and p.is_file() and not p.is_symlink(),str(p))
    body=p.read_bytes();check(sha(body)==ref['sha256'],'Reference changed: '+str(p));return body

def tree(root,alias_mappings=None):
    alias_mappings=alias_mappings or {}
    check(root.is_dir() and not root.is_symlink(),str(root));files={};links={};dirs={}
    for parent,subdirs,names in os.walk(root,followlinks=False):
        for name in list(subdirs)+names:
            p=Path(parent)/name;rel=p.relative_to(root).as_posix();s=p.lstat()
            if stat.S_ISLNK(s.st_mode):
                original=os.readlink(p)
                if rel in alias_mappings:
                    mapping=alias_mappings[rel]
                    check(original==mapping['original_target'],'Original alias target changed: '+str(p))
                    resolved=(root/mapping['internal_target']).resolve(strict=True)
                    check(resolved.is_relative_to(root.resolve()),'Mapped alias escapes: '+str(p))
                    authority=json.loads(read_ref(mapping['authority']))
                    records=[r for r in authority['files'] if Path(r['original_path']).is_relative_to(Path(original))]
                    check(records,'Missing preserved alias authority: '+rel)
                    for record in records:
                        suffix=Path(record['original_path']).relative_to(original)
                        backup=Path(record['backup_path'])
                        check(backup==resolved/suffix and backup.is_relative_to(root),'Alias mapping differs: '+rel)
                        actual=witness(backup)
                        check(actual['sha256']==record['sha256'] and actual['bytes']==record['bytes'],'Alias backup differs: '+rel)
                    links[rel]={'target':original,'resolved':resolved.relative_to(root.resolve()).as_posix(),
                        'mapping_authority':mapping['authority'],'original_external_target_not_followed':True}
                else:
                    resolved=p.resolve(strict=True)
                    check(resolved.is_relative_to(root.resolve()),'Escaping alias: '+str(p))
                    links[rel]={'target':original,'resolved':resolved.relative_to(root.resolve()).as_posix()}
            elif stat.S_ISDIR(s.st_mode):dirs[rel]={'mode':f'{stat.S_IMODE(s.st_mode):04o}','mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
            elif stat.S_ISREG(s.st_mode):files[rel]=witness(p)
            else:raise RuntimeError('Unsupported evidence member: '+str(p))
    rs=root.stat()
    return {'files':files,'links':links,'directories':dirs,'root_control':{'mode':f'{stat.S_IMODE(rs.st_mode):04o}','mtime_ns':rs.st_mtime_ns,'inode':rs.st_ino,'device':rs.st_dev}}

def rename_no_replace(source,destination):
    libc=ctypes.CDLL(None,use_errno=True)
    check(hasattr(libc,'renameat2'),'renameat2 unavailable; no replacement fallback')
    fn=libc.renameat2;fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];fn.restype=ctypes.c_int
    if fn(-100,os.fsencode(source),-100,os.fsencode(destination),1):
        err=ctypes.get_errno();raise OSError(err,os.strerror(err),str(destination))

def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('inputs');args=parser.parse_args()
    input_path=Path(args.inputs).resolve();cfg=json.loads(input_path.read_text())
    check(cfg['ready'] is True,'Final owner handoffs are unresolved')
    check(not TARGET.exists() and not REPORT.exists(),'Permanent target already exists')
    checkout=Path(cfg['checkout']);baseline_path=checkout/'GENERATION_BASELINE_006.json'
    check(sha(baseline_path.read_bytes())==BASELINE_SHA,'Baseline changed')
    baseline=json.loads(baseline_path.read_text());inventory=json.loads(Path(cfg['inventory']).read_text())
    check(len(inventory['files'])==689,'Inventory must have689 source inputs')
    expected=dict(inventory['files'])
    for rel,identity in cfg['final_identities'].items():
        check(rel in expected,'Uninventoried final identity: '+rel);expected[rel]['expected_sha256']=identity
    check(all(isinstance(r.get('expected_sha256'),str) and len(r['expected_sha256'])==64 for r in expected.values()),'Unresolved input identity')
    source_controls={}
    for rel,row in sorted(expected.items()):
        safe(rel);safe(row['capsule_member']);p=Path(row['source']);actual=witness(p)
        check(actual['sha256']==row['expected_sha256'],'Source identity changed: '+rel)
        if row.get('expected_bytes') is not None:check(actual['bytes']==row['expected_bytes'],'Source size changed: '+rel)
        source_controls[rel]=actual
    for group in ('files','static_assets','instructions'):
        for rel,row in baseline[group].items():
            check(source_controls[rel]['sha256']==row['sha256'],'Inherited input changed: '+rel)
    runtime=sorted(rel for rel in expected if rel.endswith('.py') and rel.startswith(('gene_annotation_episode/','method_loop/')))
    tests=sorted(rel for rel in expected if rel.startswith('tests/') and rel.endswith('.py'))
    check(len(runtime)==136 and len(tests)==218,'Wrong runtime/test count')
    check(set(runtime)=={p.relative_to(checkout).as_posix() for package in ('gene_annotation_episode','method_loop') for p in(checkout/package).rglob('*.py')},'Runtime membership differs')
    check(set(tests)=={p.relative_to(checkout).as_posix() for p in(checkout/'tests').rglob('*.py')},'Test membership differs')
    digest=hashlib.sha256()
    for rel in runtime:digest.update(rel.encode()+b'\0'+bytes.fromhex(source_controls[rel]['sha256']))
    pin=digest.hexdigest();check(pin==cfg['runtime_pin'],'Combined runtime pin changed')
    roots={name:Path(row['path']).resolve() for name,row in cfg['evidence_roots'].items()}
    check(set(roots)=={'C','C-late-failure-raw','P-component','R-caller-only135','JOIN-full136','root-worker-full136'},'Evidence roots differ')
    alias_mappings=cfg.get('alias_mappings',{})
    snapshots={name:tree(root,alias_mappings.get(name)) for name,root in roots.items()}
    for name,row in cfg['evidence_roots'].items():
        check(row['final'] is True and row['synthetic_engineering_only'] is True,'Unfinished/unqualified evidence root: '+name)
        for ref in row['final_control_references']:read_ref(ref)
    parent=cfg['parent_manifest'];check(parent['sha256']==PARENT_SHA,'Parent manifest identity');read_ref(parent)
    for ref in cfg['external_references']:read_ref(ref)
    invocation_rows=[]
    for chosen in cfg['selected_invocations']:
        xml=read_ref(chosen['xml']);read_ref(chosen['log'])
        suites=list(ET.fromstring(xml).iter('testsuite'));check(len(suites)==1,'Expected one suite: '+chosen['id']);s=suites[0]
        counts={key:int(s.attrib[attr]) for key,attr in [('cases','tests'),('failed','failures'),('errors','errors'),('skipped','skipped')]}
        check(counts==chosen['expected_xml_counts'],'Selected XML differs: '+chosen['id'])
        if chosen['scope']=='final_combined136':check(chosen['runtime_pin']==pin,'Selected final pin differs')
        invocation_rows.append({**chosen,'actual_xml_counts':counts,'actual_suite_seconds':float(s.attrib['time']),
            'nodeids':[c.attrib.get('classname','')+'::'+c.attrib['name'] for c in s.findall('testcase')]})
    stage=TARGET.parent/('.'+TARGET.name+'.candidate-'+uuid.uuid4().hex);stage.mkdir()
    copies={};links={};members={}
    def write(relative,body,classification):
        safe(relative);p=stage/relative;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
        members[relative]={'sha256':sha(body),'bytes':len(body),'mode':'0444','classification':classification}
    def copy(source,relative,classification,known=None):
        source=Path(source);check(source.is_file() and not source.is_symlink(),'Nonregular copy: '+str(source))
        before=witness(source)
        if known is not None:check(before==known,'Input changed before copy: '+str(source))
        write(relative,source.read_bytes(),classification)
        os.utime(stage/relative,ns=(source.stat().st_atime_ns,before['mtime_ns']))
        after=witness(source);check(before==after,'Original changed during copy: '+str(source))
        check(witness(stage/relative)['sha256']==before['sha256'],'Copy differs: '+relative)
        copies[relative]={'source':str(source),'before':before,'after':after,'source_unchanged':True,'copy_equals_source':True}
    for rel,row in sorted(expected.items()):copy(row['source'],row['capsule_member'],row['class'],source_controls[rel])
    for name,root in roots.items():
        snap=snapshots[name];prefix='evidence/'+name
        for relative in snap['directories']:(stage/prefix/relative).mkdir(parents=True,exist_ok=True)
        for relative,known in sorted(snap['files'].items()):copy(root/relative,prefix+'/'+relative,'synthetic_engineering_evidence',known)
        for relative,row in sorted(snap['links'].items()):
            dest=stage/prefix/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            target=stage/prefix/row['resolved'];new_target=os.path.relpath(target,dest.parent)
            check(not os.path.isabs(new_target),'Absolute capsule alias');os.symlink(new_target,dest)
            links[prefix+'/'+relative]={**row,'published_target':new_target,'source':str(root/relative)}
    copy(parent['path'],'parent005-MANIFEST.json','parent_manifest_only')
    copy(input_path,'publication/BUILD_INPUTS_FINAL.json','publication_control')
    copy(Path(__file__).resolve(),'publication/build_capsule.py','publication_control')
    copy(Path(cfg['plan']),'publication/BUILD_PLAN001.md','publication_control')
    copy(Path(cfg['inventory']),'publication/SOURCE_INVENTORY_ORIGINAL.json','publication_control')
    write('FINAL_INPUTS.json',dumps({'version':'configured_api_caller_final_inputs_v1','runtime_pin':pin,'runtime_files':136,'test_files':218,
        'inherited_source_tests':348,'inherited_assets':319,'new_schema_authority':1,'normative_inputs':8,'new_adopted_scopes':6,
        'source_files':source_controls,'evidence_roots':{name:{'path':str(roots[name]),'regular_files':len(snap['files']),'aliases':len(snap['links'])}for name,snap in snapshots.items()},
        'original_scientific_database_opens':0,'applications_or_additional_tests_run_by_builder':0}), 'input_guard')
    external={'version':'configured_api_caller_external_references_v1','parent005_manifest_only':parent,
        'external_only':cfg['external_references'],'parent005_complete_capsule_copied':False,'recursive_earlier_generations_copied':False,
        'fixed41_unchanged':True,'later_status015':'Root authors after publication; excluded to avoid a reference cycle.'}
    write('EXTERNAL_REFERENCES.json',dumps(external),'external_reference_control')
    results={'version':'configured_api_caller_engineering_results_v1','runtime_pin':pin,'runtime_files':136,'test_files':218,
        'selected_invocations':invocation_rows,'counting':'No cross-pin grand total. R1358 and R136repeat1 share a node. Historical C56 is not the full suite at corrected source. P57 has owned historical component scope.',
        'all348_old_source_tests_319_assets_8_normative_inputs_unchanged':True,'new_file_identities':cfg['final_identities'],
        'original_scientific_state_accessed':False,'actual_scientific_run_prepared_or_launched':False,
        'real_model_public_service_native_programs_run':False,'builder_additional_tests':0,'fixed41_unchanged':True,
        'scope':'Synthetic engineering custody/caller/typed return/reconstruction. Actual synthetic C fixture fork occurs only inside its recorded tests. No original scientific checkpoint operation.',
        'limits':['Parent005 manifest only; full parent and older generations remain external.','Fixture source paths and original preservation receipts are provenance, not relocated resumability.','Selected history retains original failures and source identities; it does not become a final-pin pass.']}
    result_body=dumps(results);write('RESULTS_FINAL.json',result_body,'final_results')
    table=['| Invocation | Scope and source identity | XML cases / failures / errors / skipped |','|---|---|---|']
    for row in invocation_rows:
        c=row['actual_xml_counts'];identity=row['runtime_pin'] or 'whole-runtime pin not claimed';table.append('| '+row['id']+' | '+row['scope']+'; '+identity+' | '+str(c['cases'])+' / '+str(c['failed'])+' / '+str(c['errors'])+' / '+str(c['skipped'])+' |')
    report=('''# Configured API caller engineering verification006\n\nThe engineering capsule preserves136 runtime files,218 tests,319 inherited assets, the C schema authority, eight normative inputs, and six adopted engineering scopes. The348 old runtime/tests and319 assets remain byte-identical to generation005. The final runtime pin is `'''+pin+'''`.\n\nThe new configured policy binds the actual timing/planning services and saved reconstruction path. Custody and joined tests use synthetic source fixtures; the detached worker uses scripted transport and the actual numerical controller, typed child return, parent admission, later parent context, exactly-once receipt/redelivery, and archives. No original scientific database, actual scientific checkpoint/prepare/launch, real model, public service, or native program was used by these engineering checks.\n\n'''+ '\n'.join(table)+'''\n\nOriginal logs/XML, recorded commands, available input records, and retained fixtures are preserved in the [capsule](../verification/configured_api_caller_2026-10-22_001/). These counts are separated by source identity and are not a cross-pin grand total. R's eight caller-only cases use the135-file pin and exclude C; the final136 worker repeats one of those nodes. P's57-node component group has its owned historical source scope. C's historical56-case suite is preserved atcce993/d115; the late reproduction failure and corrected affected checks retain separate identities. Earlier failures and fixture corrections are archived without being relabeled successful final checks. Original owner receipts describe their input/raw capture limits; not every earlier failure has a complete raw tree. The two-case late C failure raw tree is additionally copied at publication time with original copy controls, without an immediate-retention claim.\n\nThe exact final result file is [RESULTS_FINAL.json](../verification/configured_api_caller_2026-10-22_001/RESULTS_FINAL.json), SHA256`'''+sha(result_body)+'''`. [MANIFEST.json](../verification/configured_api_caller_2026-10-22_001/MANIFEST.json) enumerates capsule membership and read-only modes; its final digest is recorded in the publication receipt and root's later status record, avoiding a circular report-copy digest.\n\nThe parent005 [manifest](../verification/configured_api_caller_2026-10-22_001/parent005-MANIFEST.json) is copied alone, SHA256`'''+PARENT_SHA+'''`; its full capsule and earlier generations remain external. Adopted plans and historical corrections are pinned in EXTERNAL_REFERENCES.json. Preserved raw fixture paths are original provenance; relocated resumability is not claimed.\n\nThe [prior status014](AMENDMENTS/SLOT_CORRECTION_2026-10-22_014.md), SHA256`e0376b08d6da1e853e1103a301b67e5e4bd3c392a5f83c76fc5de66bb5c90a59`, remains unchanged: fixed41 is not advanced by this engineering publication. Root's later record015 and any actual custody or scientific launch are outside this capsule.\n''').encode()
    write('REPORT.md',report,'report_copy')
    # Every original is checked again before the copy receipt and immutable manifest.
    for relative,row in copies.items():check(witness(Path(row['source']))==row['before'],'Original changed after copy: '+relative)
    for name,root in roots.items():check(tree(root,alias_mappings.get(name))==snapshots[name],'Evidence tree changed: '+name)
    write('COPY_RECEIPT.json',dumps({'version':'configured_api_caller_copy_receipt_v1','regular_files':copies,'aliases':links,
        'original_bytes_sizes_modes_mtimes_and_membership_unchanged':True,'original_directory_controls':{name:{'root':snap['root_control'],'directories':snap['directories']}for name,snap in snapshots.items()},'no_original_chmod':True,
        'alias_rule':'Only verified internal targets, rebased relative to the capsule. Raw-preservation metadata aliases remain metadata.'}), 'copy_receipt')
    for p in stage.rglob('*'):
        if p.is_symlink():continue
        if p.is_file():os.chmod(p,0o444)
    directories=['.']+sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_dir() and not p.is_symlink())
    for relative,row in links.items():
        p=stage/relative;check(os.readlink(p)==row['published_target'] and p.resolve(strict=True).is_relative_to(stage.resolve()),'Published alias escapes: '+relative)
    actual_files={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() and not p.is_symlink()}
    check(actual_files==set(members),'Staged file membership differs')
    for rel,row in members.items():
        actual=witness(stage/rel);check(actual['sha256']==row['sha256'] and actual['bytes']==row['bytes'] and actual['mode']=='0444','Staged copy changed: '+rel)
    manifest={'version':'configured_api_caller_verification_capsule_v1','runtime_pin':pin,'runtime_files':136,'test_files':218,
        'members':members,'file_count_excluding_manifest':len(members),'content_bytes_excluding_manifest':sum(r['bytes']for r in members.values()),
        'aliases':links,'directories_including_root':directories,'regular_file_modes':'0444','directory_modes':'0555',
        'manifest_self_excluded':True,'report_path':str(REPORT),'report_sha256':sha(report),'parent005_extent':'MANIFEST ONLY',
        'source_and_evidence_originals_unchanged':True,'proof_counting':'Per invocation/source scope only; no cross-pin grand total.'}
    manifest_body=dumps(manifest);write('MANIFEST.json',manifest_body,'manifest')
    os.chmod(stage/'MANIFEST.json',0o444)
    for rel in sorted(directories,key=lambda x:len(Path(x).parts),reverse=True):
        p=stage if rel=='.' else stage/rel;os.chmod(p,0o555);fsync_dir(p)
    check(stat.S_IMODE(stage.stat().st_mode)==0o555,'Stage root mode')
    for relative,row in copies.items():check(witness(Path(row['source']))==row['before'],'Original changed before publication: '+relative)
    for name,root in roots.items():check(tree(root,alias_mappings.get(name))==snapshots[name],'Evidence tree changed before publication: '+name)
    check(not TARGET.exists() and not REPORT.exists(),'Publication target appeared')
    rename_no_replace(stage,TARGET);fsync_dir(TARGET.parent)
    receipt={'version':'configured_api_caller_publication_receipt_v1','capsule_published':True,'capsule':str(TARGET),
        'manifest_sha256':sha(manifest_body),'report':str(REPORT),'report_sha256':sha(report),'runtime_pin':pin,
        'member_files_excluding_manifest':len(members)-1,'content_bytes_excluding_manifest':manifest['content_bytes_excluding_manifest'],
        'directories_including_root':len(directories),'aliases':len(links),'originals_unchanged':True}
    try:
        os.link(TARGET/'REPORT.md',REPORT);fsync_dir(REPORT.parent)
        check(REPORT.read_bytes()==report,'Report copy mismatch');receipt['report_published']=True
    finally:
        dest=input_path.parent/'PUBLICATION_RECEIPT_FINAL.json'
        with dest.open('xb') as f:f.write(dumps(receipt));f.flush();os.fsync(f.fileno())
    print(json.dumps(receipt,sort_keys=True),flush=True)

if __name__=='__main__':main()
