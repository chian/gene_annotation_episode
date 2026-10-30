"""Code/type preservation audit only; no scientific packets or providers."""
from pathlib import Path
import ast,difflib,hashlib,json,sys
base=Path(__file__).resolve().parent;root=base.parents[2];pin=base/'pin_001';before=base.parent/'a105_ion_binding_review_206/pin_001'
sys.dont_write_bytecode=True;sys.path[:0]=[str(pin),str(pin/'tests')]
from gene_annotation_episode import literature_numerical_contracts as contracts
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.schema_information_text import schema_fingerprint
b=LiteratureEpisodes(None,rate_population=True,channel_population=True,compiled_assay_population=True,ion_discrimination_population=True,completion_time_population=True,product_partition_population=True,active_site_population=True,ratio_source_population=True,controlled_response_population=True,gel_population=True)
facts=b.fact_sources('literature');census=[]
for source in contracts.registered_sources():
 schema=contracts.registered_schema(source);module,factory=contracts._SCHEMAS[source]
 path=Path('gene_annotation_episode')/(module+'.py')
 census.append({'source':source,'factory':[module,factory],'original_complete_schema_sha256':schema_fingerprint(schema),'exact_actual_bound_type':schema_fingerprint(schema)==schema_fingerprint(facts[source]['report_schema']),'factory_code_unchanged_from206':(pin/path).read_bytes()==(before/path).read_bytes(),'top_level_schema_fields':list(schema),'item_fields':list(schema.get('items',{}).get('properties',{})),'original_bound_meaning':facts[source]['meaning']})

def functions(path):
 out={}
 def walk(body,prefix=''):
  for n in body:
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):out[prefix+n.name]=ast.dump(n,include_attributes=False)
   elif isinstance(n,ast.ClassDef):walk(n.body,prefix+n.name+'.')
 walk(ast.parse(path.read_text()).body);return out
paths=['gene_annotation_episode/runtime.py','gene_annotation_episode/episode_contract_information.py','gene_annotation_episode/literature_episodes.py','gene_annotation_episode/literature_experimental_prompt.py','gene_annotation_episode/literature_reference_parent_prompt.py','gene_annotation_episode/literature_numerical_return_presentation.py']
audit={}
for name in paths:
 old=functions(before/name);new=functions(pin/name)
 audit[name]={'changed_functions':[n for n in old if n in new and old[n]!=new[n]],'removed_functions':[n for n in old if n not in new],'added_functions':[n for n in new if n not in old]}
 (base/(Path(name).name+'.final.diff')).write_text(''.join(difflib.unified_diff((before/name).read_text().splitlines(True),(pin/name).read_text().splitlines(True),fromfile='frozen206/'+name,tofile='frozen203/'+name)))
for name in ('test_literature_prompt_surface_144.py','test_literature_channel_binding_188.py','test_contract_information_runtime_059.py','test_contract_information_worker_059.py'):
 old=(base/'preparation_001'/(name+'.baseline')).read_text();new=(pin/'tests'/name).read_text()
 (base/(name+'.final.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before203/tests/'+name,tofile='after203/tests/'+name)))
unchanged={name:(pin/name).read_bytes()==(before/name).read_bytes() for name in ['gene_annotation_episode/communication.py','gene_annotation_episode/numerical.py',*('method_loop/'+p.name for p in (pin/'method_loop').glob('*.py'))]}
goal=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
record={'scope':'Exact declarations and code preservation, not scientific scoring adequacy or reader/assay counts.','registered_return_types':census,'changed_code_functions':audit,'protected_code_unchanged':unchanged,'original_supplied_goal_sha256':hashlib.sha256(goal.read_bytes()).hexdigest(),'root206_display_render_sha256':hashlib.sha256((pin/'gene_annotation_episode/literature_ion_discrimination_render.py').read_bytes()).hexdigest(),'unbound205_registered':any('measurement_validation' in s for s in contracts.registered_sources()),'goal_complete':False,'A105_complete':False}
(base/'FINAL_CODE_TYPE_AUDIT_001.json').write_text(json.dumps(record,indent=2)+'\n')
assert all(row['exact_actual_bound_type'] and row['factory_code_unchanged_from206'] for row in census)
assert all(unchanged.values())
print(json.dumps({'exact_existing_types':len(census),'all_factory_code_preserved':True,'protected_code_preserved':True,'unbound205_registered':False}))
