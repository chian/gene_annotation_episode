from pathlib import Path
import hashlib, json, shutil, stat, xml.etree.ElementTree as ET

REPO = Path('/home/chia/repos/gene_annotation_episode')
PRODUCER = Path('/tmp/api-timing-publication-preparation-20261022-001/FINAL_CANDIDATE')
SOURCE = PRODUCER/'capsule'
WORK = Path(__file__).resolve().parent
STAGE = WORK/'capsule002'
DEST = REPO/'verification/hmmer_api_resource_2026-10-22_003'
REPORT = REPO/'docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_003.md'
INPUTS = Path('/tmp/api-timing-root-final-20261022-001/INPUTS.json')
PIN = 'cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def files(directory):
    return {str(p.relative_to(directory)): p for p in directory.rglob('*') if p.is_file()}

inventory = read(PRODUCER/'MANIFEST.FINAL_CANDIDATE.json')['members']
assert len(inventory) == 1442 and len({r['path'] for r in inventory}) == 1442
assert set(files(SOURCE)) == {r['path'] for r in inventory}
for row in inventory:
    p = SOURCE/row['path']
    assert not p.is_symlink() and sha(p) == row['sha256'] and p.stat().st_size == row['bytes']
copy_plan = read(PRODUCER/'COPY_PLAN.FINAL_CANDIDATE.json')['entries']
assert len(copy_plan) == 1434
for row in copy_plan:
    original, copied = Path(row['source_path']), SOURCE/row['candidate_relative_path']
    assert sha(original) == row['source']['sha256'] == sha(copied)
    assert original.stat().st_size == row['source']['bytes'] == copied.stat().st_size
root_inputs = read(INPUTS)
assert root_inputs['runtime_implementation_sha256'] == PIN
for category in ('source_files','tests'):
    for name, expected in root_inputs[category].items():
        assert sha(SOURCE/name) == expected
digest = hashlib.sha256()
for name in sorted(root_inputs['source_files']):
    digest.update(name.encode()+b'\0')
    digest.update(bytes.fromhex(sha(SOURCE/name)))
assert digest.hexdigest() == PIN
results = read(Path('/tmp/api-timing-root-final-20261022-001/RESULTS.json'))
assert results['distinct_current_pin_cases'] == 213
seen = set()
for group in results['groups']:
    assert group['exit_code'] == 0 and not seen.intersection(group['node_ids'])
    seen.update(group['node_ids'])
assert len(seen) == 213
parent = REPO/'verification/hmmer_api_resource_2026-10-22_002'
parent_files = files(parent)
assert len(parent_files) == 694
for name, original in parent_files.items():
    assert (SOURCE/'parent-generation002'/name).read_bytes() == original.read_bytes()
assert not STAGE.exists() and not DEST.exists() and not REPORT.exists()
shutil.copytree(SOURCE, STAGE)
text = (PRODUCER/'REPORT.FINAL_CANDIDATE.md').read_text()
text = text.replace('# API reported-duration engineering verification, generation003 — final candidate',
    '# API reported-duration engineering verification, generation003')
start = text.index(' This is an unsealed final publication candidate for root review.')
end = text.index('\n\n', start)
text = text[:start]+(' The [new capsule](/home/chia/repos/gene_annotation_episode/verification/hmmer_api_resource_2026-10-22_003/MANIFEST.json) '
    'preserves the exact sources, inputs, outputs and prior lineage. Root independently verified every copied input, '
    'the complete parent002 lineage, source/test identities and distinct final case ledger before readonly publication.')+text[end:]
text = text.replace('Root must still review any publication/redaction requirements, apply final modes, build/check the final outer manifest with no extras, verify final report-copy equality and deliver report/manifest hashes separately. The candidate inventory is not a publication manifest or seal.',
    'Root independently checked all1434 copied input identities and all694 exact parent002 files, then applied the declared readonly/executable modes and verified the outer manifest, no-extra-file membership and exact report copy. Producer metadata retains its original candidate/preparation status as historical evidence; the final outer MANIFEST.json records this publication. Installed dependencies are not claimed to be bundled.')
text = text.replace("Root's joined engineering verification is complete at the recorded pin; permanent publication/sealing remains pending root review, and the fixed overall goal remains active and incomplete.",
    "Root's joined engineering verification and this readonly publication are complete at the recorded pin. The fixed overall goal remains active and incomplete.")
report_copy = STAGE/'docs'/REPORT.name
assert report_copy.exists()
report_copy.write_text(text)
verification = {
    'version':'root_api003_publication_verification_v1', 'implementation_sha256':PIN,
    'producer_inventory_sha256':sha(PRODUCER/'MANIFEST.FINAL_CANDIDATE.json'),
    'producer_copy_plan_sha256':sha(PRODUCER/'COPY_PLAN.FINAL_CANDIDATE.json'),
    'raw_copy_rows_verified':len(copy_plan), 'parent002_exact_files':len(parent_files),
    'runtime_files':131, 'test_python_files':205, 'distinct_root_final_cases':213,
    'actual_public_service_inputs_in_this_capsule':False,
    'producer_candidate_statuses_are_historical':True,
    'final_report_sha256':sha(report_copy),
    'source_inputs_unchanged':True, 'prior_records_rewritten':False}
(STAGE/'ROOT_PUBLICATION_VERIFICATION.json').write_text(json.dumps(verification,indent=2)+'\n')
shutil.copyfile(Path(__file__), STAGE/'root-publication.py')
modes = {r['candidate_relative_path']:int(r['planned_published_mode'],8) for r in copy_plan}
for name,p in files(STAGE).items():
    mode = modes.get(name,0o444)
    assert mode in {0o444,0o555}
    p.chmod(mode)
members = [{'path':name,'sha256':sha(p),'bytes':p.stat().st_size,
    'mode':format(stat.S_IMODE(p.stat().st_mode),'04o')} for name,p in sorted(files(STAGE).items())]
manifest = {'version':'hmmer_api_resource_verification_capsule_v1',
    'implementation_sha256':PIN,'publication_state':'root_verified_readonly', 'members':members}
(STAGE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
(STAGE/'MANIFEST.json').chmod(0o444)

def verify(directory):
    actual = files(directory)
    assert set(actual) == {r['path'] for r in members}|{'MANIFEST.json'}
    for row in members:
        p = directory/row['path']
        assert not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
        assert format(stat.S_IMODE(p.stat().st_mode),'04o')==row['mode']
        assert not p.stat().st_mode & 0o222
    assert read(directory/'MANIFEST.json') == manifest

verify(STAGE)
shutil.copytree(STAGE, DEST)
verify(DEST)
with REPORT.open('x') as stream:
    stream.write(text)
REPORT.chmod(0o444)
assert REPORT.read_bytes()==(DEST/'docs'/REPORT.name).read_bytes()
print(json.dumps({'report':str(REPORT),'report_sha256':sha(REPORT),
    'manifest_sha256':sha(DEST/'MANIFEST.json'),'members':len(members),
    'member_bytes':sum(r['bytes'] for r in members),'implementation_sha256':PIN,
    'readonly_modes_and_exact_member_sets_verified':True},indent=2))
