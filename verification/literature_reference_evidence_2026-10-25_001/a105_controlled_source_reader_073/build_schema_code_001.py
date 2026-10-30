from pathlib import Path
import json,pprint
base=Path('verification/literature_reference_evidence_2026-10-25_001')
out=Path('gene_annotation_episode/literature_controlled_response_v2_inputs.py')
head='''"""Full source-bound A105 controlled-response extraction.

Text science is shared with v1. Actual signed graph reading is delegated to063;
owner covariance and actual068 parsed inputs retain source scope. No sheet,
model, acquisition, runtime action or annotation-credit calculation occurs here.
"""
from __future__ import annotations

from copy import deepcopy as cp
from fractions import Fraction
import errno
import hashlib
import json
import math
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from . import literature_controlled_response_inputs as shared
from . import literature_controlled_response_figure_inputs as graph_reader
from .literature_controlled_response_owner_calculations import (
    controlled_response_owner_arguments_schema, validate_controlled_response_owner_inputs,
)
from .literature_experimental_contracts import ExperimentalContractError

obj, ref, null = shared.obj, shared.ref, shared.nullable
T, N, I, B = shared.TEXT, {"type": "number"}, shared.OFFSET, {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}

def arr(value, **kw):
    return {"type": "array", "items": value, **kw}

def enum(*values):
    return {"enum": list(values)}

def embed(schema, prefix, target):
    def rename(value):
        if isinstance(value, dict):
            return {k: ("#/$defs/" + prefix + v[8:] if k == "$ref" and v.startswith("#/$defs/") else rename(v)) for k,v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return value
    for key,val in schema.get("$defs", {}).items():
        target[prefix + key] = rename(val)
    return rename({k:v for k,v in schema.items() if k not in ("$defs", "$schema")})


def controlled_response_v2_arguments_schema():
    schema = shared.controlled_response_arguments_schema()
    schema["properties"]["version"] = {"const": "controlled_response_source_selection_v2"}
    axis_scale = obj({"status": enum("known", "unknown", "conflicting"),
        "kind": null(enum("linear", "logarithmic", "nonlinear")),
        "basis": enum("source_text_literal", "image_episode_interpretation", "unresolved"),
        "witnesses": arr(ref("Witness"))})
    axis_scale["allOf"] = [{"if": {"properties": {"status": {"const": "known"}}},
        "then": {"properties": {"kind": enum("linear", "logarithmic", "nonlinear"),
            "basis": enum("source_text_literal", "image_episode_interpretation"), "witnesses": {"minItems": 1}}},
        "else": {"properties": {"kind": {"type": "null"}, "basis": {"const": "unresolved"}}}}]
    schema["$defs"]["AxisScale"] = axis_scale
    measurement = schema["$defs"]["GraphMeasurement"]
    measurement["properties"]["axis"]["properties"]["scale"] = ref("AxisScale")
    measurement["properties"]["axis"]["required"].append("scale")
    measurement["properties"]["terminal_edge"] = enum("upper", "lower")
    measurement["required"].append("terminal_edge")
    return schema
'''
def expr(v,level=0):
 if v=={'type':'string','minLength':1}:return 'T'
 if v=={'type':'number'}:return 'N'
 if v=={'type':'integer','minimum':0}:return 'I'
 if v=={'type':'boolean'}:return 'B'
 if isinstance(v,dict):
  if set(v)=={'$ref'}:return 'ref('+repr(v['$ref'][8:])+')'
  if set(v)=={'enum'}:return 'enum('+', '.join(repr(x) for x in v['enum'])+')'
  if set(v)=={'anyOf'} and len(v['anyOf'])==2 and v['anyOf'][1]=={'type':'null'}:return 'null('+expr(v['anyOf'][0],level)+')'
  if v.get('type')=='object' and set(v)=={'type','properties','required','additionalProperties'} and list(v['properties'])==v['required'] and v['additionalProperties'] is False:
   return 'obj({\n'+',\n'.join('    '*(level+2)+repr(k)+': '+expr(w,level+1) for k,w in v['properties'].items())+'})'
  if v.get('type')=='array' and 'items'in v and set(v)<={'type','items','minItems','maxItems','uniqueItems'}:
   return 'arr('+expr(v['items'],level)+''.join(', '+k+'='+repr(w)for k,w in v.items()if k not in ('type','items'))+')'
  return '{'+', '.join(repr(k)+': '+expr(w,level) for k,w in v.items())+'}'
 if isinstance(v,list):return '['+', '.join(expr(w,level)for w in v)+']'
 return repr(v)
g=json.loads((base/'a105_controlled_graph_design_061/GRAPH_RESULT_SCHEMA_002.json').read_text())
sel=json.loads((base/'a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json').read_text())
code=head+'\n\ndef _graph_schema():\n    D = cp(controlled_response_v2_arguments_schema()["$defs"])\n'
for k,v in g['$defs'].items():
 if k not in sel['$defs']:code+='    D['+repr(k)+'] = '+expr(v)+'\n'
code+='    schema = '+expr({k:v for k,v in g.items()if k not in ('$defs','$schema')})+'\n    schema.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})\n    return schema\n'
sheet=json.loads((base/'a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json').read_text())
code+='\n\ndef _sheet_schema():\n    D = {}\n    D["OwnerInputs"] = embed(controlled_response_owner_arguments_schema(), "Input_", D)\n'
for k in ('Cell','ContrastDependencies'):code+='    D['+repr(k)+'] = '+expr(sheet['$defs'][k])+'\n'
code+='    schema = '+expr({k:v for k,v in sheet.items()if k not in ('$defs','$schema')})+'\n    schema.update({"$defs": D, "$schema": "https://json-schema.org/draft/2020-12/schema"})\n    return schema\n'
# Production constructors transcribed from the exact closed069 declaration.
original=(base/'a105_controlled_full_source_design_069/build_declarations_001.py').read_text()
portion=original[original.index('D = cp(selection["$defs"])'):original.index('write("EXTRACTION_SCHEMA_V2_001.json", root)')]
portion=portion.replace('old["diagnostic_codes"]',repr(json.loads((base/'a105_controlled_response_design_056/implementation_stage_008/CLOSED_RESULT_INTERFACE_008.json').read_text())['diagnostic_codes']))
portion=portion.replace('[*old["types"]["DependencyRecord"]["expected_module_fingerprints"],','[*shared.DEPENDENCIES,')
code+='\n\ndef _extraction_schema():\n    selection = controlled_response_v2_arguments_schema()\n    graph = _graph_schema()\n    owner = controlled_response_owner_arguments_schema()\n    sheet = _sheet_schema()\n'+''.join('    '+line+'\n'for line in portion.splitlines())+'    return root\n'
out.write_text(code)
