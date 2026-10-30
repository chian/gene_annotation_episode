"""Engineering conversion of accepted types; no source/paper reading."""
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.literature_concentration_window_inputs import (
    concentration_window_selection_schema, concentration_window_extraction_schema,
    concentration_window_calculation_inputs_schema, concentration_window_sheet_schema,
    concentration_window_covariance_schema, ROLES, ANALYTES)
from gene_annotation_episode.literature_concentration_window_calculations import _DEFINITIONS

def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

selection=concentration_window_selection_schema()
sheet=concentration_window_sheet_schema()
assay_fields=[k for k in selection['$defs']['assay']['properties'] if k not in ('arrangement','participants')]
paths=['assay.'+k for k in assay_fields]+['assay.participants.identity']
paths += ['quantities.'+r+'.'+k for r in ROLES for k in ('analyte','coordinate','unit','record','measurement_identity')]
paths += ['stoichiometry.'+a+'.'+k for a in ANALYTES for k in ('analyte','reaction','coefficient_token_support')]
window=obj(dict(start=dict(type='integer',minimum=0),end=dict(type='integer',minimum=1)))
context_entry=obj(dict(field=dict(enum=paths),participant_index=dict(type=['integer','null'],minimum=0),
    windows=dict(type='array',items=window,uniqueItems=True)))
request=obj(dict(version=dict(const='literature_concentration_window_population_v1'),
    selection=deepcopy({k:v for k,v in selection.items() if k not in ('$id','$schema','$defs')}),
    return_context=dict(type='array',items=context_entry,uniqueItems=True)))
request['$defs']=deepcopy(selection['$defs'])
definitions=deepcopy(sheet['$defs'])
sf=definitions['scientific_field']
sf['properties'].pop('scientific_text')
sf['properties']['display_status']={'enum':['selected_fragments','support_location_only','not_selected']}
sf['properties']['fragments']={'type':'array','items':obj(dict(text=dict(type='string',minLength=1),
    start=dict(type='integer',minimum=0),end=dict(type='integer',minimum=1)))}
sf['required']=list(sf['properties'])
context=definitions['scientific_context']
context['properties']['usage']={'const':'scoped_parent_scientific_context'}
for name in ('quantities','stoichiometry'):
    context['properties'][name]['required']=[]
for name in ('scientific_pair_relationships','scientific_cross_relationships'):
    definitions[name]['required']=[]
reference=dict(type='string',format='reference',**{'x-reference-namespace':'source'})
row=obj(dict(sheet_ref=reference,evidence_source_ref=deepcopy(reference),
    row_version=dict(const='concentration_window_return_v1'),evaluation_scope=dict(const='source_concentration_window'),
    component=deepcopy(definitions['cell']['properties']['component']),
    cell={'$ref':'#/$defs/cell'},source_kind=deepcopy(selection['properties']['source_kind']),
    assertion_resolution=deepcopy(sheet['properties']['assertion_resolution']),
    scientific_context={'$ref':'#/$defs/scientific_context'},
    covariance_context={'$ref':'#/$defs/covariance_context'},
    estimate_bindings=deepcopy(sheet['properties']['estimate_bindings']),
    source_artifacts=deepcopy(sheet['properties']['source_artifacts']),
    operand_metadata=dict(type='array',items={}),
    withheld_locations=dict(type='array',items=obj(dict(source_ref=deepcopy(reference),
        artifact_ref=dict(type='string',format='reference',**{'x-reference-namespace':'artifact'}),
        representation=dict(enum=['original','text']),start=dict(type='integer',minimum=0),
        end=dict(type='integer',minimum=1))),uniqueItems=True),
    limits=deepcopy(sheet['properties']['limits'])))
rows=dict(type='array',items=row,**{'x-source':'literature_concentration_window_cells','$defs':definitions})
quantity_schema=concentration_window_extraction_schema()['properties']['quantities']['properties']['substrate_start']['anyOf'][0]
# Resolve the pure numerical operand shape without altering its vocabulary.
defs=concentration_window_extraction_schema()['$defs']
quantity_schema=defs[quantity_schema['$ref'].split('/')[-1]] if '$ref' in quantity_schema else quantity_schema
row['properties']['operand_metadata']['items']=obj(dict(role=dict(enum=list(ROLES)),
    **{k:deepcopy(quantity_schema['properties'][k]) for k in ('status','origin','relation','approximate','unit','reasons')}))
resources=dict(request=request,rows=rows,selection=selection,
    extraction=concentration_window_extraction_schema(),inputs=concentration_window_calculation_inputs_schema(),
    sheet=sheet,covariance=concentration_window_covariance_schema())
out=Path(__file__).parent
(out/'PROPOSED_SCHEMAS_002.json').write_text(json.dumps(resources,indent=2,ensure_ascii=False)+'\n')
