from pathlib import Path
import ast,hashlib,json,sqlite3,sys
import gene_annotation_episode.literature_experimental_prompt as prompt
from gene_annotation_episode.literature_episodes import _population_catalog
p=Path('/tmp/pytest-of-chia/pytest-1813/test_actual_selected_delivery_0/state/state.sqlite3')
db=sqlite3.connect(f'file:{p}?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('pragma query_only=on')
results={}
for r in db.execute('select call_index,request from runtime_model_calls order by rowid'):
 if r['call_index']!=1:continue
 state=json.loads(r['request'])['context'];kind='parent' if state.get('child_reports') else 'own'
 task=prompt._task(state,'Constructed reaction investigation')
 args=[(t['name'],len(prompt._schema(t['input_schema'],'arguments'))) for t in state.get('tools',()) if 'input_schema'in t]
 results[kind]={'contract_information_profile':state.get('contract_information_profile'),
  'task_characters':len(task),'reaction_task_characters':len(prompt.REACTION_TASK),
  'total_operation_schema_characters':sum(n for _,n in args),'largest_operation_schemas':sorted(args,key=lambda r:r[1],reverse=True)[:3],
  'return_schema_characters':len(prompt._schema(state['requested_form'],'return')) if isinstance(state.get('requested_form'),dict) else 0}
source=Path(prompt.__file__).read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_task')
cat=_population_catalog();payload=json.dumps(cat,sort_keys=True,separators=(',',':'),allow_nan=False)
print(json.dumps({'renderer_path':prompt.__file__,'same_actual_saved_125_states':True,'results':results,
 'task_builder_ast_sha256':hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
 'default_population_catalog_sha256':hashlib.sha256(payload.encode()).hexdigest(),'default_population_operations':len(cat)}))
db.close()
