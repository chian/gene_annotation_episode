"""Read-only provenance and existing-validator checks; ephemeral loader fixture.

No Store, Workflow, model, scientific execution, network or active-library access.
"""
from pathlib import Path
import hashlib,json,tempfile
from gene_annotation_episode.scientific_support_metadata import validate_support_entry
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
ROOT=Path('/home/chia/repos/gene_annotation_episode');OUT=Path('/tmp/scientific-support-slot-draft-20261022-002')
def can(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def dig(v):return hashlib.sha256(can(v).encode()).hexdigest()
def fd(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ptr(v,p):
 for k in p.split('/')[1:]:
  k=k.replace('~1','/').replace('~0','~');v=v[int(k)] if isinstance(v,list) else v[k]
 return v

def strings(v):
 if isinstance(v,str):yield v
 elif isinstance(v,list):
  for a in v:yield from strings(a)
 elif isinstance(v,dict):
  for a in v.values():yield from strings(a)

def original(s):
 p=ROOT/s['corpus_path'];sel=s['line_or_selector']
 document=json.loads(p.read_text().splitlines()[sel-1]) if type(sel)is int else json.loads(p.read_text())
 record=document if type(sel)is int or not sel else ptr(document,sel)
 return document,record
cross_path='docs/SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json'
x=json.loads((ROOT/cross_path).read_text())
entries={}
for p in sorted((OUT/'entries').glob('*.json')):
 e=json.loads(p.read_text());assert e['id']==p.stem
 assert validate_support_entry(e)==e
 for o in e['support']['operands']:
  assert not ('direct' in o['applicabilities'] and 'inferred_extent' in o['extent_bases'])
 entries[e['id']]=e
assert set(entries)=={f'A{i}' for i in range(101,112)}
# All retained original records, including unused abstract-only groups, match
# their existing crosswalk identities. This is not a source-inspection upgrade.
record_count=0
for cr in x['case_rows']:
 for s in cr['record_sources']:
  document,record=original(s);assert dig(record)==s['original_record_sha256'],s['case_id'];record_count+=1
assert record_count==149
mapping=json.loads((OUT/'source_mapping.json').read_text())
assert mapping['crosswalk_file_sha256']==fd(ROOT/cross_path)
source_table=json.loads((OUT/'instruction_sources.json').read_text())['rows']
assert len(source_table)==len(mapping['rows'])
seen=set()
for m,table_row in zip(mapping['rows'],source_table):
 cr=ptr(x,m['crosswalk_case_pointer']);s=ptr(x,m['crosswalk_record_pointer']);document,record=original(s)
 assert m['original_record_sha256']==s['original_record_sha256']==dig(record)
 assert m['original_path']==s['corpus_path'] and m['original_record_selector']==s['line_or_selector']
 assert m['original_file_sha256']==fd(ROOT/m['original_path'])
 evidence=entries[m['entry_id']]['evidence'][m['evidence_index']]
 assert evidence['case_id']==s['case_id'] and evidence['case_group']==cr['case_group']
 assert dig(evidence)==m['evidence_sha256']
 scope=m['observation_pointer_scope']
 trace_path=m.get('observation_document_path')
 if trace_path:
  assert trace_path in cr['trace_extensions']
  assert fd(ROOT/trace_path)==m['observation_document_file_sha256']
  document=json.loads((ROOT/trace_path).read_text())
  assert document['case_group']==cr['case_group']
  assert evidence['source_url'] in set(strings(document['sources']))
 else:assert evidence['source_url'] in set(strings(s['primary_urls']))
 raw=ptr(document if scope=='document' else record,m['original_observation_pointer'])
 if m.get('excerpt_character_span'):
  a,b=m['excerpt_character_span'];raw=raw[a:b]
 assert evidence['observation']==raw
 assert evidence['limit'].strip() and m['original_inspection_scope']==s['inspected_scope']
 assert table_row==dict(evidence_id=m['evidence_id'],option_id=m['entry_id'],**evidence)
 assert m['evidence_id'] not in seen;seen.add(m['evidence_id'])
 assert m['curation_uses'] and all(z['rationale'].strip() for z in m['curation_uses'])
coverage=json.loads((OUT/'review_coverage.json').read_text())
assert len(coverage['groups'])==142
assert {r['case_group'] for r in coverage['groups']}=={r['case_group'] for r in x['case_rows']}
assert sum(bool(r['selected_draft_entries']) for r in coverage['groups'])==134
assert len(coverage['unused_group_ids'])==8
for r in coverage['groups']:
 assert r['selected_draft_entries'] or r['unassigned_reason']
 for i in r['selected_draft_entries']:assert r['case_group'] in {s['case_group'] for s in entries[i]['evidence']}
assert len(set().union(*(set(p['case_groups']) for p in x['partitions'].values())))==142
for item in json.loads((OUT/'input_manifest.json').read_text())['files']:
 p=Path(item['path']);p=p if p.is_absolute() else ROOT/p
 assert fd(p)==item['file_sha256'],('input changed since read',item['path'])
# This uses the complete existing public source->freeze->reload->resolve->sources
# path in a disposable /tmp-only fixture. It is not an installed/active library.
with tempfile.TemporaryDirectory(prefix='.loader-compatibility-',dir=OUT) as tmp:
 tmp=Path(tmp);source=tmp/'source';source.mkdir();(source/'entries').mkdir()
 headers=[]
 for i,e in entries.items():
  relative=f'entries/{i}.json';(source/relative).write_bytes((OUT/relative).read_bytes())
  ids=[m['evidence_id'] for m in mapping['rows'] if m['entry_id']==i]
  headers.append(dict(id=i,slot=e['slot'],name=e['name'],description=e['description'],detail_path=relative,source_evidence_ids=ids))
 index=dict(format='research_three_slot_options_v1',status='ephemeral review-only compatibility fixture',
  slots=[dict(slot='annotation_distinction',catalog='annotation_options.json',count=11),dict(slot='thought_pattern',catalog='thought_patterns.json',count=0)],entries=headers)
 (source/'index.json').write_text(json.dumps(index)+'\n')
 (source/'option_sources.json').write_text(json.dumps(dict(meaning='Disposable instruction provenance fixture; no active source adoption.',rows=source_table))+'\n')
 frozen=ScientificProcessLibrary.freeze(tmp/'frozen',source=source)
 descriptor=frozen.as_record();assert len(frozen.headers())==11
 reopened=ScientificProcessLibrary(tmp/'frozen')
 for i,e in entries.items():
  ref=reopened.reference(i);assert ref['option_id']==i
  assert reopened.resolve(ref)==e
  actual=reopened.sources(option_ref=ref,offset=0,limit=10000)['rows']
  assert actual==[r for r in source_table if r['option_id']==i]
 loader=dict(existing_public_loader_round_trip='passed',source_entries=11,thought_entries=0,source_rows=len(source_table),
  ephemeral_snapshot_library_id=descriptor['library_id'],fixture_removed_on_exit=True,
  active_library_changed=False,runtime_objects='No Store, Workflow, model or scientific database object created.')
# The draft did not adopt a runtime route binding. The reference policy remains
# exactly the arithmetic_review value preserved in the existing crosswalk.
policy=json.loads((OUT/'review_policy_reference.json').read_text())
assert policy['policy']==x['arithmetic_review']['policy']
report=dict(status='passed',schema_validator='gene_annotation_episode.scientific_support_metadata.validate_support_entry',
 original_ten_entries=10,new_case_driven_entries=1,validated_entries=len(entries),validated_original_record_hashes=record_count,
 validated_source_rows=len(mapping['rows']),validated_review_groups=142,unassigned_abstract_or_summary_groups=8,
 direct_inferred_extent_cross_products=0,loader=loader,
 scientific_validation='Structure/provenance and loader compatibility only; not scientific entailment, calibrated thresholds, independence, target findings, adoption or configured-model behavior.',
 numerical_policy='Unchanged existing policy is only the draft reference; no score calculated and no caller route binding created.',
 current_numeric_bound=dict(path='gene_annotation_episode/domain.py',file_sha256=fd(ROOT/'gene_annotation_episode/domain.py'),
  existing_values=['less_than','less_or_equal','greater_than','greater_or_equal'],note='Current numeric ATOM already has these bounds; the older review002 missing-bound discussion is historical and was not edited.'))
(OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,indent=2))
