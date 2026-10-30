from pathlib import Path
import hashlib, json, shutil

REPO = Path('/home/chia/repos/gene_annotation_episode')
OLD = Path('/tmp/scientific-support-slot-draft-20261022-001')
NEW = Path('/tmp/scientific-support-slot-draft-20261022-002')
REVIEW = Path('/tmp/scientific-support-independent-review-20261022-v5GiMt')
WORK = Path(__file__).resolve().parent
DEST = REPO/'verification/scientific_support_slot_candidates_2026-10-22_002'
REPORT = REPO/'docs/SCIENTIFIC_SUPPORT_SLOT_CANDIDATES_2026-10-22_002.md'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def seal(directory, name, status):
    target = directory/name
    rows = [{'path': str(p.relative_to(directory)), 'sha256': sha(p), 'bytes': p.stat().st_size}
        for p in sorted(directory.rglob('*')) if p.is_file()]
    rows = [r for r in rows if r['path'] != name]
    value = {'status': status, 'files': rows}
    if target.exists():
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2)+'\n')
    return rows

assert json.loads((NEW/'validation.json').read_text())['status'] == 'passed'
revision = json.loads((NEW/'REVISION.json').read_text())
for name in ('A101','A103','A104','A105','A106','A107','A108','A109','A110'):
    assert (OLD/'entries'/f'{name}.json').read_bytes() == (NEW/'entries'/f'{name}.json').read_bytes()
for name in ('A102','A111'):
    old = json.loads((OLD/'entries'/f'{name}.json').read_text())
    new = json.loads((NEW/'entries'/f'{name}.json').read_text())
    assert old['evidence'] == new['evidence']
for name in ('source_mapping.json','source_mapping.tsv','instruction_sources.json','review_coverage.json','review_policy_reference.json'):
    assert (OLD/name).read_bytes() == (NEW/name).read_bytes()
seal(NEW, 'output_manifest.json', 'review_candidate002_only_not_adopted')
assert not DEST.exists() and not REPORT.exists()
DEST.mkdir(parents=True)
shutil.copytree(OLD, DEST/'original_draft001')
shutil.copytree(NEW, DEST/'candidate002')
shutil.copytree(REVIEW, DEST/'independent_review001')
shutil.copytree(WORK, DEST/'root_publication')
inputs = json.loads((OLD/'input_manifest.json').read_text())['files']
input_map = []
for row in inputs:
    path = Path(row['path'])
    actual = path if path.is_absolute() else REPO/path
    assert sha(actual) == row['file_sha256']
    relative = Path('inputs/immutable_goal.txt') if path.is_absolute() else Path('inputs')/path
    target = DEST/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(actual, target)
    input_map.append({'original_path': row['path'], 'published_path': str(relative), 'sha256': sha(target)})
(DEST/'INPUT_COPY_MAP.json').write_text(json.dumps(input_map, indent=2)+'\n')
catalog = json.loads((NEW/'candidate_catalog.json').read_text())['entries']
mapping = json.loads((NEW/'source_mapping.json').read_text())['rows']
rows = []
for item in catalog:
    group_count = len({r['case_group'] for r in json.loads((NEW/item['path']).read_text())['evidence']})
    rows.append(f"| [{item['id']}](../verification/scientific_support_slot_candidates_2026-10-22_002/candidate002/{item['path']}) | {item['name']} | {group_count} | {item['evidence_rows']} |")
text = '''# Scientific-support slot candidates002: concrete unadopted bodies

The initial unsealed packaging attempt001 failed on a source-table field lookup
before creating a report or capsule manifest; its partial bytes remain unchanged.
This NEW permanent publication preserves the complete original candidate001,
its independent review, and separately revised candidate002. It replaces no
implementation/research note and adopts no active library content or scoring.
The existing first-slot placeholder A0,19 thought patterns and variable actual
tool retriever remain unchanged. These are first-slot scientific-support
definitions; they are not complete episodes, biological claim headings or
fixed tool bundles. Literature episodes retain their separate hierarchy.

The complete prior review covers142 case groups,149 original records and163
support contrasts. Candidate002 contains11 existing-schema SupportEntryV1
bodies,134 assigned groups,306 retained source rows and eight explicitly
unassigned abstract/summary groups. Reusing a group in several entries does not
establish independent corroboration. Each body declares actual observation
kinds, assessed predicates/relations, applicability and extent constraints.
Construction resolves kinds through the actual caller's existing policy routes;
selecting an entry creates no evidence or credit.

| Entry | Scientific support approached | Groups | Source rows |
| --- | --- | ---: | ---: |
'''+ '\n'.join(rows)+'''

[source_mapping.tsv](../verification/scientific_support_slot_candidates_2026-10-22_002/candidate002/source_mapping.tsv)
is the inspectable option-to-source table. Its JSON equivalent preserves exact
original file/hash, case/record selector, observation/clause pointer, retained
text, inspection limits, URL relation and curation rationale. All142 groups,
including unassigned cases and residual questions, remain in review_coverage.json.
These published cases are instruction provenance about their named subjects,
not findings about the fixed ybhP target or experiments performed by this work.

## Exact revision and provenance limits

Root read all eleven definition bodies. The independent reviewer exhaustively
checked recorded provenance and examined selected complete scientific records,
including all eight A111 source groups. No retained example demonstrated a
wholly predicted structure incorrectly admitted as measured. Nevertheless the
original measured-versus-modeled wording was insufficiently precise.

Candidate002 applies exact D1–D3 append-text revisions to A111: experimental
constraints remain distinct from purely predicted coordinates; coordinate-derived
comparisons retain their dependent origin; and structural compatibility does
not establish measured transport, catalysis or necessity. Experimentally refined
crystallographic/cryo-EM models remain usable with their actual uncertainty.
Unknown FrsA ligand identity remains unknown. D4 clarifies A102 that deposition
and prediction are not exclusive origins. The exact before/after hashes and
texts are in candidate002/REVISION.json. Other nine bodies and all source rows,
mapping/coverage/policy files are byte-identical to candidate001.

All306 retained observation/selected-clause pointers match the original records.
**22 rows resolve an exact single source_id to the selected URL;284 establish
declared case/trace URL membership.** These checks do not prove306 independent
primary-source entailments. No new primary source was retrieved during this
curation/verification. Original inspection limits stay attached.

## What was verified and what remains

Independent candidate001 verification checked all32 manifested files plus its
manifest,36 exact input hashes,149 original record hashes,306 provenance rows,
142-group membership/partition coverage and163 contrasts. It found no changed
original draft bytes. Root verified the exact candidate002 revision boundaries,
reran the existing closed-schema validator for11 entries and the complete
original-record/pointer checks, and exercised the existing public library
freeze/reopen/resolve/sources interfaces in a new ephemeral temporary fixture.
The fixture was removed; no active library was installed. Candidate002's loader
fixture ID is569cf3b2f40166279c03b9132d51f3dc4ca6f9f89ace1eb474766a13a84ae537.

The validator is a separately hashed derivative of the original script with
only its output-directory literal changed. It wrote candidate002 validation
only. Original validators/builders in the historical copy retain their original
absolute paths: do not execute them against sealed artifacts. For reproduction,
use a new writable copy and explicitly redirect a separately hashed checker.

This verifies structure, retained provenance and loader compatibility. It does
not establish calibrated scientific thresholds, source independence, complete
primary-source entailment, target annotation behavior or numerical suitability.
The reference policy still merges observation kinds into its existing components,
uses the existing same-component maximum/applicability/relation/extent arithmetic
and derived discrimination. No weight, axis, hypervolume formula or controller
changed. Component splitting, dependent comparison credit, provenance-aware
accumulation and the treatment of derived discrimination remain unresolved.

The pending human choice remains whether to adopt these concrete entries with
existing numeric combinations or decide the scoring changes first. A107's
deployment criteria, A104's detection/distribution criteria and A101/A102's
transfer adequacy remain scientific review questions; this publication does not
invent acceptance thresholds or infer an answer. No Store, Workflow, scientific
database, model, scientific episode, native operation or network was used by
this slot curation/publication. The overall goal remains incomplete.

The capsule contains exact original/revised drafts, independent checks, root
derivation/validation evidence and36 exact input copies. MANIFEST.json binds
all member paths/bytes/hashes and the exact report copy. Earlier permanent notes
and scientific state remain unchanged.
'''
REPORT.write_text(text)
shutil.copyfile(REPORT, DEST/REPORT.name)
members = seal(DEST, 'MANIFEST.json', 'review_only_not_adopted_no_scoring_or_active_library_change')
for p in DEST.rglob('*'):
    if p.is_file():
        p.chmod(0o444)
for p in NEW.rglob('*'):
    if p.is_file():
        p.chmod(0o444)
REPORT.chmod(0o444)
for row in members:
    p = DEST/row['path']
    assert sha(p) == row['sha256'] and p.stat().st_size == row['bytes']
assert {str(p.relative_to(DEST)) for p in DEST.rglob('*') if p.is_file()} == {r['path'] for r in members}|{'MANIFEST.json'}
assert (DEST/REPORT.name).read_bytes() == REPORT.read_bytes()
print(json.dumps({'report': str(REPORT), 'report_sha256': sha(REPORT),
    'manifest_sha256': sha(DEST/'MANIFEST.json'), 'members': len(members),
    'member_bytes': sum(r['bytes'] for r in members),
    'candidate002_manifest_sha256': sha(NEW/'output_manifest.json')}, indent=2))
