from pathlib import Path
import hashlib, json, shutil

OLD = Path('/tmp/scientific-support-slot-draft-20261022-001')
REVIEW = Path('/tmp/scientific-support-independent-review-20261022-v5GiMt')
NEW = Path('/tmp/scientific-support-slot-draft-20261022-002')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)

old_manifest = json.loads((OLD/'output_manifest.json').read_text())
expected = {r['path'] for r in old_manifest['files']} | {'output_manifest.json'}
assert {str(p.relative_to(OLD)) for p in OLD.rglob('*') if p.is_file()} == expected
for row in old_manifest['files']:
    p = OLD/row['path']
    assert sha(p) == row['sha256'] and p.stat().st_size == row['bytes']
assert not NEW.exists()
NEW.mkdir()
for p in OLD.rglob('*.json'):
    if p.name in {'output_manifest.json', 'validation.json'}:
        continue
    target = NEW/p.relative_to(OLD)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, target)
shutil.copyfile(OLD/'source_mapping.tsv', NEW/'source_mapping.tsv')
deltas = json.loads((REVIEW/'scientific_boundary_review.json').read_text())['proposed_new_draft_deltas']
changes = []
for delta in deltas:
    p = NEW/delta['path']
    entry = json.loads(p.read_text())
    parts = delta['json_pointer'].split('/')[1:]
    node = entry
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    field = parts[-1]
    previous = node[field]
    node[field] += delta['text']
    p.write_text(json.dumps(entry, ensure_ascii=False, indent=2)+'\n')
    changes.append({**delta, 'previous_value_sha256': hashlib.sha256(previous.encode()).hexdigest(),
        'new_value_sha256': hashlib.sha256(node[field].encode()).hexdigest()})
p = NEW/'entries/A102.json'
entry = json.loads(p.read_text())
old = entry['support']['operands'][0]['instruction']
needle = 'deposited versus predicted origin'
assert old.count(needle) == 1
entry['support']['operands'][0]['instruction'] = old.replace(needle,
    'experimentally constrained/refined versus purely predicted origin (deposition is a separate provenance fact)')
p.write_text(json.dumps(entry, ensure_ascii=False, indent=2)+'\n')
changes.append({'id': 'D4', 'path': 'entries/A102.json',
    'json_pointer': '/support/operands/0/instruction', 'operation': 'replace_exact_text',
    'old_text': needle, 'new_text': 'experimentally constrained/refined versus purely predicted origin (deposition is a separate provenance fact)',
    'basis': 'Independent scientific_boundary_review.json other_concrete_boundaries_reviewed A102/A108; deposited and predicted are not exclusive.'})
catalog = json.loads((NEW/'candidate_catalog.json').read_text())
for row in catalog['entries']:
    path = NEW/row['path']
    body = json.loads(path.read_text())
    row['file_sha256'] = sha(path)
    row['canonical_sha256'] = hashlib.sha256(canonical(body).encode()).hexdigest()
(NEW/'candidate_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
revision = {'status': 'review_draft_only_not_adopted', 'previous_draft': str(OLD),
    'previous_manifest_sha256': sha(OLD/'output_manifest.json'),
    'independent_review_manifest_sha256': sha(REVIEW/'independent_manifest.json'),
    'changes': changes,
    'unchanged': ['All entry evidence rows and source mappings', 'All149 original record identities',
        '142group review coverage and163 contrasts', 'Existing numerical policy',
        'Active A0/P19/library/tool retriever and all application/scientific state'],
    'source_relation_limit': {'exact_source_id_url_rows': 22, 'case_or_trace_url_membership_rows': 284,
        'all_retained_pointer_clause_rows': 306,
        'independent_primary_source_entailment_for_every_mapping': False}}
(NEW/'REVISION.json').write_text(json.dumps(revision, ensure_ascii=False, indent=2)+'\n')
prefix = '''# Review candidate002: explicit structural origin and functional limits

This is a NEW, unadopted review candidate. Candidate001 is unchanged. Exact
changes D1–D4 are in REVISION.json: A111's measured and derived structural
operands now explicitly distinguish experimental constraints from wholly
predicted coordinates and separate a structural fact from a functional claim;
A102 no longer treats deposition and prediction as exclusive origins. All
eleven evidence tables and306 source relationships are unchanged.

The independent review verified22 exact source_id-to-URL resolutions and284
declared case/trace URL memberships. All306 retained pointers/clauses match;
this is not proof of306 independently entailed primary-source relationships.
No new literature retrieval, experiment or target finding occurred.

The original draft report is copied below as historical context. Its mechanical
validation was repeated for these revised bodies with a separately derived
validator directed at this NEW temporary directory. Validation writes only its
own validation.json; it is not an active library installation.

---

'''
(NEW/'REVIEW.md').write_text(prefix+(OLD/'REVIEW.md').read_text())
(NEW/'REPRODUCE.md').write_text('''# Review-only reproduction

The builder and original validation script are historical evidence. Do not run
them against sealed directories. Copy the candidate to a NEW writable temporary
directory and redirect the explicit OUT value in a separately hashed derived
validator before rerunning. validate_candidate.py is the exact original
validate_draft.py with only OUT changed to the new candidate002 temporary path.
It writes validation.json and creates/removes an ephemeral metadata-loader
fixture; it never opens a scientific Store/Workflow or adopts library content.

Source/URL membership is narrower than scientific entailment. Existing numeric
policy arithmetic is retained only as a review reference. Content adoption and
numerical changes remain unresolved human choices.
''')
validator = (OLD/'validate_draft.py').read_text()
assert validator.count(str(OLD)) == 1
(NEW/'validate_candidate.py').write_text(validator.replace(str(OLD), str(NEW)))
revision['validator_derivation'] = {'original_script_sha256': sha(OLD/'validate_draft.py'),
    'derived_script_sha256': sha(NEW/'validate_candidate.py'),
    'only_script_delta': {'old_OUT': str(OLD), 'new_OUT': str(NEW)}}
(NEW/'REVISION.json').write_text(json.dumps(revision, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'new_candidate': str(NEW), 'entry_changes': ['A102', 'A111'],
    'amendments': [x['id'] for x in changes], 'original_manifest_unchanged': sha(OLD/'output_manifest.json')}, indent=2))
