from pathlib import Path
import json,csv,hashlib
ROOT=Path('/home/chia/repos/gene_annotation_episode');OUT=Path('/tmp/scientific-support-slot-draft-20261022-001')
CP='docs/SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json'
x=json.loads((ROOT/CP).read_text());SF='case_group case_id source_url source_locator observation limit'.split()
def can(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def dig(v):return hashlib.sha256(can(v).encode()).hexdigest()
def fd(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ptr(v,p):
 for k in p.split('/')[1:]:
  k=k.replace('~1','/').replace('~0','~');v=v[int(k)] if isinstance(v,list) else v[k]
 return v

def write(p,v):(OUT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def strings(v):
 if isinstance(v,str):yield v
 elif isinstance(v,list):
  for a in v:yield from strings(a)
 elif isinstance(v,dict):
  for a in v.values():yield from strings(a)
entries={f'A{i}':json.loads((OUT/f'entries/A{i}.json').read_text()) for i in range(101,112)}
for e in entries.values():e['evidence']=[]
curated=[]
for name in ['curation_transfer_followups.json','curation_system.json']:
 doc=json.loads((OUT/name).read_text()); gs=doc['groups']
 if isinstance(gs,dict):gs=list(gs.values())
 curated.extend(gs)
bygroup={g['case_group']:g for g in curated}; assert len(curated)==len(bygroup)==142
for extra in json.loads((OUT/'curation_additional_candidate.json').read_text())['groups']:
 bygroup[extra['case_group']]['mappings'].extend(extra['mappings'])
# Auditor correction: OarX retained conditional negatives lack explicit allele-linked native restoration.
bygroup['context_oarx_thiamin_2024']['mappings']=[m for m in bygroup['context_oarx_thiamin_2024']['mappings'] if m['entry_id']!='A109']
bygroup['context_oarx_thiamin_2024'].setdefault('gaps',[]).append('Conditional whole-cell rescue-capacity negatives lack the explicit allele-linked perturbation/restoration required by A109 and cannot be treated as intrinsic catalysis. This residual support relation is left unassigned rather than forced.')
huc_excerpts={'A105':'Purified Huc oxidized very low hydrogen concentrations and reduced quinone analogues despite oxygen.','A106':'Hydrogen addition stimulated oxygen consumption; respiratory inhibitors and oxidase mutants constrained coupling.','A107':'Growth-phase expression/activity separated Huc from sustained-persistence Hhy.'}
for m in bygroup['organism_09_huc']['mappings']:
 if m['entry_id'] in huc_excerpts:
  for ev in m['evidence']:ev['observation_excerpt']=huc_excerpts[m['entry_id']]
for m in bygroup['organism_02_xoxf']['mappings']:
 for ev in m['evidence']:
  if 'PMC5075040' in ev['source_url']:
   ev['observation_excerpt']='triple-mutant residual growth led to ExaF, rather than XoxF exclusivity.'
  else:
   ev['observation_excerpt']='Metal-conditioned growth, purified protein identity/metal content and knockout combinations support lanthanide-dependent oxidation'
   if m['entry_id']=='A105':
    ev['source_url']='https://pmc.ncbi.nlm.nih.gov/articles/PMC4859578/'
crindex={r['case_group']:(i,r) for i,r in enumerate(x['case_rows'])}
maprows=[]; entry_seen={i:{} for i in entries}
for group in sorted(bygroup):
 c=bygroup[group];ci,cr=crindex[group]
 assert c.get('mappings') or c.get('unassigned_reason'),group
 for m in c.get('mappings',[]):
  entry_id=m['entry_id'];assert entry_id in entries
  for ev in m['evidence']:
   si,s=next((i,s) for i,s in enumerate(cr['record_sources']) if s['case_id']==ev['case_id'])
   p=ROOT/s['corpus_path'];sel=s['line_or_selector'];raw=p.read_text()
   document=json.loads(raw.splitlines()[sel-1]) if type(sel)is int else json.loads(raw)
   record=document if type(sel)is int or not sel else ptr(document,sel)
   assert dig(record)==s['original_record_sha256'],(group,'original digest')
   is_doc='document_observation_pointer' in ev
   op=ev['document_observation_pointer'] if is_doc else ev['observation_pointer']
   observation_document=document
   trace_path=ev.get('document_path')
   if trace_path:
    assert trace_path in cr['trace_extensions'],(group,'unlinked trace')
    observation_document=json.loads((ROOT/trace_path).read_text())
    assert observation_document['case_group']==group and ev['case_id'] in observation_document['existing_case_ids']
   observation=ptr(observation_document if is_doc else record,op)
   assert isinstance(observation,str) and observation.strip(),(group,op)
   excerpt=ev.get('observation_excerpt')
   if excerpt:
    assert excerpt in observation,(group,'excerpt');excerpt_span=[observation.index(excerpt),observation.index(excerpt)+len(excerpt)]
    observation=excerpt
   else:excerpt_span=None
   url=ev['source_url']
   if trace_path: assert url in set(strings(observation_document['sources'])),(group,'trace URL')
   else: assert url in set(strings(s['primary_urls'])),(group,'url not source',url)
   # If an original observation supplies source_id, resolve it when possible;
   # otherwise retain the explicit declared case-record URL membership boundary.
   selected_object=None
   try:selected_object=ptr(observation_document if is_doc else record,op.rsplit('/',1)[0])
   except (KeyError,TypeError,ValueError,IndexError):pass
   source_id=selected_object.get('source_id') if isinstance(selected_object,dict) else None
   source_ids=selected_object.get('source_ids') if isinstance(selected_object,dict) else None
   precise_source=None
   if source_id:
    pools=[]
    for d in [record,document]:
     for k in ['sources','primary_sources','primary_source_urls+DOIs']:
      if k in d:
       z=d[k]
       if isinstance(z,dict):pools.extend(dict(source_id=key,**val) for key,val in z.items())
       elif isinstance(z,list):pools.extend(z)
    precise_source=next((z for z in pools if isinstance(z,dict) and z.get('source_id')==source_id and z.get('url')==url),None)
    if pools:assert precise_source is not None,(group,source_id,url)
   # An observation outside a selected group record must be one of that group's
   # explicitly retained observation IDs, not another group's source result.
   if is_doc and not trace_path:
    assert isinstance(selected_object,dict)
    oid=selected_object.get('observation_id')
    assert oid in s['preserved_observations'],(group,'unlinked document observation',oid)
   limit=s['inspected_scope']
   if trace_path:limit=next(z['scope_read'] for z in observation_document['sources'] if z['url']==url)
   if isinstance(selected_object,dict):
    for k in ['limit','limits','assay_bounds']:
     if isinstance(selected_object.get(k),str):limit+=' | Source observation limit: '+selected_object[k]
   extra=ev.get('limit') or ev.get('additional_limit') or m.get('limit')
   if extra:limit+=' | Draft source-use limitation: '+extra
   if c.get('limits'):limit+=' | Group source-use limits: '+' '.join(c['limits'])
   if excerpt_span:limit+=' | This row selects an exact clause from the aggregate retained observation; other source clauses are not attributed to this URL.'
   base=trace_path if trace_path else s['corpus_path']+(':'+str(sel) if type(sel)is int else '')
   fullop=op if is_doc or type(sel)is int or not sel else sel+op
   locator=base+'#'+fullop
   if excerpt_span:locator+=f"[characters {excerpt_span[0]}:{excerpt_span[1]}]"
   evidence=dict(case_group=group,case_id=s['case_id'],source_url=url,source_locator=locator,observation=observation,limit=limit)
   key=can(evidence)
   if key in entry_seen[entry_id]:
    old=maprows[entry_seen[entry_id][key]]
    old['curation_uses'].append(dict(rationale=m['rationale'],role=m.get('role','support_and_boundary')))
    continue
   ei=len(entries[entry_id]['evidence']);entries[entry_id]['evidence'].append(evidence)
   entry_seen[entry_id][key]=len(maprows)
   maprows.append(dict(entry_id=entry_id,evidence_index=ei,evidence_id=f'E-{entry_id}-{ei+1:03d}',evidence_sha256=dig(evidence),
    crosswalk_case_pointer=f'/case_rows/{ci}',crosswalk_record_pointer=f'/case_rows/{ci}/record_sources/{si}',
    original_path=s['corpus_path'],original_file_sha256=fd(p),original_record_selector=sel,original_record_sha256=dig(record),
    observation_document_path=trace_path,observation_document_file_sha256=fd(ROOT/trace_path) if trace_path else None,original_observation_pointer=op,observation_pointer_scope='document' if is_doc else 'record',excerpt_character_span=excerpt_span,
    original_inspection_scope=s['inspected_scope'],original_source_id=source_id,original_source_ids=source_ids,
    precise_original_source_id_url_resolved=bool(precise_source),
    source_relation='exact retained original observation (or explicit exact clause) and case-source URL membership; source_id URL checked when original supplies resolvable source IDs; no new primary-source passage verification',
    curation_uses=[dict(rationale=m['rationale'],role=m.get('role','support_and_boundary'))]))
for i,e in entries.items():write(f'entries/{i}.json',e)
write('source_mapping.json',dict(status='review_draft_only_not_adopted',meaning='Curated exact source relationships across all142 individually reviewed groups. Assignments are new draft library-source judgements, not target findings, independent corroboration counts or historical tag reinterpretation.',crosswalk_path=CP,crosswalk_file_sha256=fd(ROOT/CP),rows=maprows))
write('instruction_sources.json',dict(meaning='Instruction provenance only; source experiments are published work, not newly executed target findings.',rows=[dict(evidence_id=m['evidence_id'],option_id=m['entry_id'],**entries[m['entry_id']]['evidence'][m['evidence_index']]) for m in maprows]))
coverage=[]
for ci,r in enumerate(x['case_rows']):
 c=bygroup[r['case_group']]
 coverage.append(dict(case_group=r['case_group'],crosswalk_case_pointer=f'/case_rows/{ci}',best_coverage=r['best_coverage'],
  retained_candidate_mentions=sorted({t for z in r['support_contrasts'] for t in z['candidate_support_entries']}),
  records=[{k:s[k] for k in ['case_id','corpus_path','line_or_selector','original_record_sha256']} for s in r['record_sources']],
  selected_draft_entries=sorted({m['entry_id'] for m in c.get('mappings',[])}),
  mapping_judgments=[dict(entry_id=m['entry_id'],rationale=m['rationale'],role=m.get('role','support_and_boundary')) for m in c.get('mappings',[])],
  unassigned_reason=c.get('unassigned_reason'),gaps=c.get('gaps',[]),limits=c.get('limits',[]),dependence_notes=c.get('dependence_notes',[]),retained_unresolved=c.get('retained_unresolved')))
summary=dict(original_candidate_entries=10,additional_case_driven_candidate_entries=1,groups=142,records=sum(len(r['records']) for r in coverage),support_contrasts=sum(len(r['support_contrasts']) for r in x['case_rows']),
 selected_groups=sum(bool(r['selected_draft_entries']) for r in coverage),unused_groups=sum(not r['selected_draft_entries'] for r in coverage),
 relevant_primary_section_groups=sum(r['best_coverage']=='relevant_primary_sections' for r in coverage),
 abstract_or_summary_groups=sum(r['best_coverage']=='abstract_or_summary' for r in coverage),
 instruction_source_rows=len(maprows),route_links=sum(len(r['mapping_judgments']) for r in coverage))
write('review_coverage.json',dict(status='draft_curation_not_adopted',meaning='Complete retained review inventory plus explicitly new, individually reasoned draft source assignments. Repeated use of one case across entries is not independence. A route link can be a negative, qualification or boundary example.',source_path=CP,partitions=x['partitions'],counts=summary,
 abstract_or_summary_group_ids=[r['case_group'] for r in coverage if r['best_coverage']=='abstract_or_summary'],
 unused_group_ids=[r['case_group'] for r in coverage if not r['selected_draft_entries']],
 entry_case_index={i:sorted({s['case_group'] for s in e['evidence']}) for i,e in entries.items()},
 retained_exact_tag_index={f'A{101+i}':sorted(r['case_group'] for r in coverage if c['id'] in r['retained_candidate_mentions']) for i,c in enumerate(x['candidate_support_entries'])},groups=coverage))
with (OUT/'source_mapping.tsv').open('w',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['entry_id','evidence_id',*SF,'original_record_sha256'])
 for m in maprows:
  e=entries[m['entry_id']]['evidence'][m['evidence_index']];w.writerow([m['entry_id'],m['evidence_id'],*(e[k] for k in SF),m['original_record_sha256']])
write('candidate_catalog.json',dict(status='review_draft_only_not_a_loadable_source_index',entries=[dict(id=i,name=e['name'],path=f'entries/{i}.json',candidate_source_pointer=f'/candidate_support_entries/{int(i[1:])-101}' if i!='A111' else None,canonical_sha256=dig(e),file_sha256=fd(OUT/f'entries/{i}.json'),evidence_rows=len(e['evidence'])) for i,e in entries.items()]))
manifest=json.loads((OUT/'input_manifest.json').read_text());paths={z['path'] for z in manifest['files']}
for m in maprows:
 if m['original_path'] not in paths:manifest['files'].append(dict(path=m['original_path'],file_sha256=m['original_file_sha256']));paths.add(m['original_path'])
for m in maprows:
 if m.get('observation_document_path') and m['observation_document_path'] not in paths:
  manifest['files'].append(dict(path=m['observation_document_path'],file_sha256=m['observation_document_file_sha256']));paths.add(m['observation_document_path'])
write('input_manifest.json',manifest)
print(json.dumps(summary));print(json.dumps({i:dict(groups=len({s['case_group'] for s in e['evidence']}),source_rows=len(e['evidence'])) for i,e in entries.items()}))
