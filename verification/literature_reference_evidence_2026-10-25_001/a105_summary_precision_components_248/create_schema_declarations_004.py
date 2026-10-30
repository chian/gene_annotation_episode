from pathlib import Path
import json
H=Path(__file__).resolve().parent
R=H.parents[2]
P=R/'gene_annotation_episode/literature_kinetic_summary_precision_inputs.py'
assert not P.exists()
roots={k:json.loads((H/f).read_text()) for k,f in [('selection','SELECTION_SCHEMA_002.json'),('extraction','EXTRACTION_SCHEMA_002.json'),('inputs','CALCULATION_INPUTS_SCHEMA_002.json'),('sheet','SHEET_SCHEMA_003.json')]}
seen={};lines=[]
def emit(value):
 key=json.dumps(value,sort_keys=True,separators=(',',':'))
 if key in seen:return seen[key]
 if isinstance(value,dict):expr='{'+', '.join(repr(k)+': '+emit(v) for k,v in value.items())+'}'
 elif isinstance(value,list):expr='['+', '.join(emit(v) for v in value)+']'
 else:return repr(value)
 name='_S'+str(len(lines));lines.append(name+' = '+expr);seen[key]=name
 return name
rootnames={k:emit(v) for k,v in roots.items()}
header='''"""Source-bound summary precision inputs, separate from numerical calculation.

Schemas are exact reviewed declarations (002 input/extraction;003 sheet).
Repeated declarations below share Python values only; accessors detach them.
The sheet's local $defs remain scoped to that standalone sheet schema.
No acquisition, model call, Store or episode behavior belongs here.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import re

from .domain import ContractError, canonical, validate_schema
from .literature_assay_inputs import _Sources
from .literature_experimental_contracts import ExperimentalContractError
from .literature_kinetic_inputs import (
    read_kinetic_inputs, _count_reading, _cardinal_count, _literal_fraction,
    _UNIT_TABLES, _normalize,
)

# Generated, readable and losslessly shared schema declarations. Do not mutate.
'''
P.write_text(header+'\n'.join(lines)+'\n\n_SCHEMAS = {'+', '.join(repr(k)+': '+n for k,n in rootnames.items())+'}\n')
print('Created new inputs module declarations:',len(lines),'shared nodes; no verification dependency at runtime.')
