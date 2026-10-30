"""Controlled pure projection/render probes; no selected episode or paper read."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKET=HERE.parent/'a105_summary_precision_components_248'
PIN=PACKET/'pin_006'
sys.path[:0]=[str(PIN),str(PIN/'tests')]
from test_literature_kinetic_summary_precision_components_248 import synthetic
from gene_annotation_episode.literature_kinetic_summary_precision_inputs import read_kinetic_summary_precision_inputs
from gene_annotation_episode.literature_kinetic_summary_precision_calculations import populate_kinetic_summary_precision

snapshot=HERE/'preliminary_source_002'
storage=ast.parse((snapshot/'literature_kinetic_summary_precision_storage.py').read_text())
renderer=ast.parse((snapshot/'literature_kinetic_summary_precision_render.py').read_text())
dependency_map=json.loads((HERE.parent/'a105_summary_precision_binding_251/COMPONENT_DEPENDENCY_MAP_001.json').read_text())
def exact_function(tree,name,namespace):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(snapshot/name),'exec'),namespace)
    return namespace[name]
namespace={'COMPONENT_DEPENDENCIES':dependency_map}
exact_function(storage,'_count_route_dependencies',namespace)
dependencies=exact_function(storage,'_row_dependencies',namespace)
render=exact_function(renderer,'render_received',{})
selection,original_read=synthetic()
extra=b'Explicit controlled extra count: four technical observations. SD relationship unknown.'
a=extra.index(b'four')
selection['interpretation']['statistical_count']={'witness':{'source_ref':'@unused_extra256','representation':'text',
    'start':0,'end':len(extra),'quote':extra.decode()},'number_start':a,'number_end':a+4}
def read(ref,representation):
    if ref=='@unused_extra256':return {'artifact_ref':'sha256_'+sha256(extra).hexdigest(),'content':extra}
    return original_read(ref,representation)
extraction=read_kinetic_summary_precision_inputs(selection,read_source=read)
data=extraction['calculation_inputs'];sheet=populate_kinetic_summary_precision(data)
assert sheet['source_cells']['statistical_estimator_count']['value']==4
assert sheet['source_cells']['mean_standard_error']['value']==6
conditions,locations=dependencies('mean_standard_error',sheet['source_cells']['mean_standard_error'],data,'source_cells')
unused_location=data['dependencies']['statistical_count_source']
assert data['assessments']['statistical_count_matches_sd']=='unknown'
assert {'condition':'statistical_count_matches_sd','state':'unknown'} not in conditions
assert unused_location not in locations

plan=HERE.parent/'a105_summary_precision_binding_251'
examples=json.loads((plan/'PROPOSED_SCHEMA_EXAMPLES_001.json').read_text())['proposed_output_rows']
rows=[deepcopy(next(r for r in examples if r['component']=='source_mean_standard_error')),
      deepcopy(next(r for r in examples if r['component']=='source_reported_parameter'))]
for row in rows:
    row['source_kind']='synthetic_fixture'
    row['sampling_basis'].update(source_count_meaning='technical_measurement_count',repetition_basis='technical_measurements')
row=rows[1]
row['cell'].update(value=600,status='populated',qualification='source_reported',origin='synthetic',approximate=True,
                   unavailable_reason=None,source_exact_value={'numerator':'600','denominator':'1'})
parts=[]
def section(parts,title,body):parts.append(title+'\n'+body)
def table(headers,values):return '\n'.join([' | '.join(headers),*[' | '.join(map(str,row)) for row in values]])
render(parts,rows,section=section,table=table)
text='\n\n'.join(parts)
assert 'technical_measurements' in text and 'technical_measurement_count' in text
assert 'synthetic_fixture' in text and 'synthetic' in text
assert 'approximate' in text.lower() and 'True' in text
with (HERE/'CONTROLLED_RENDER_OUTPUT_002.txt').open('x') as output:output.write(text+'\n')
report={'classification':'passed_preliminary_projection_and_render_repairs',
    'code_snapshot':{name:sha256((snapshot/name).read_bytes()).hexdigest() for name in (
        'literature_kinetic_summary_precision_storage.py','literature_kinetic_summary_precision_render.py')},
    'fixture':'explicit synthetic original count plus unrelated separately selected extra count; schema-illustration render rows',
    'supported_statistical_n':4,'valid_mean_SE_per_min':6,
    'unused_unknown_count_relationship_returned':False,'unused_extra_count_location_returned':False,
    'sampling_basis_missing_from_render':False,'synthetic_source_and_origin_missing_from_render':False,
    'approximation_missing_from_render':False,
    'selected_episode_execution':False,'actual_model_execution':False,'private_provider_data_read':False,
    'goal_changed':False,'A105_complete':False}
with (HERE/'PRELIMINARY_REPAIR_CHECK_002.json').open('x') as output:json.dump(report,output,indent=2);output.write('\n')
print(json.dumps(report,indent=2))
