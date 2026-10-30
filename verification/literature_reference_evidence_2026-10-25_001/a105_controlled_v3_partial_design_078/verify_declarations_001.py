from pathlib import Path
import json
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
errors=[]
for p in sorted(HERE.glob('*SCHEMA*_001.json')):
 s=json.loads(p.read_text());Draft202012Validator.check_schema(s)
 def walk(x,path='$'):
  if isinstance(x,dict):
   if '$ref' in x and x['$ref'].startswith('#/$defs/') and x['$ref'][8:] not in s.get('$defs',{}):errors.append(dict(file=p.name,path=path,unresolved_ref=x['$ref']))
   for k,v in x.items():walk(v,path+'.'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+f'[{i}]')
 walk(s)
with (HERE/'INITIAL_DECLARATION_CHECK_001.json').open('x') as f:json.dump(dict(errors=errors),f,indent=2);f.write('\n')
print(json.dumps({'unresolved_references':len(errors)}))
