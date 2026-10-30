from pathlib import Path
import json
H=Path(__file__).resolve().parent
P=H.parents[2]/'gene_annotation_episode/literature_kinetic_summary_precision_inputs.py'
text=P.read_text();marker="\nVERSION = 'a105_kinetic_summary_precision_extraction_v1'"
header=text[:text.index('# Generated, readable and losslessly shared schema declarations.')]
header=header.replace('(002 input/extraction;003 sheet)','(002 selection;004 input/extraction/sheet)')
body=marker+text.split(marker,1)[1]
roots={k:json.loads((H/f).read_text()) for k,f in [('selection','SELECTION_SCHEMA_002.json'),('extraction','EXTRACTION_SCHEMA_004.json'),('inputs','CALCULATION_INPUTS_SCHEMA_004.json'),('sheet','SHEET_SCHEMA_004.json')]}
seen={};lines=[]
def emit(value):
 key=json.dumps(value,sort_keys=True,separators=(',',':'))
 if key in seen:return seen[key]
 if isinstance(value,dict):expr='{'+', '.join(repr(k)+': '+emit(v) for k,v in value.items())+'}'
 elif isinstance(value,list):expr='['+', '.join(emit(v) for v in value)+']'
 else:return repr(value)
 name='_S'+str(len(lines));lines.append(name+' = '+expr);seen[key]=name;return name
rootnames={k:emit(v) for k,v in roots.items()}
P.write_text(header+'# Generated, readable and losslessly shared schema declarations. Do not mutate.\n'+'\n'.join(lines)+'\n\n_SCHEMAS = {'+', '.join(repr(k)+': '+v for k,v in rootnames.items())+'}\n'+body)
print('Adopted root-approved exact unresolved-kind schema delta004.')
