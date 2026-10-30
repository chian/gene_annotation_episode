"""Engineering proposal only; copies reviewed schemas, invokes no reader/calculator."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
from gene_annotation_episode.literature_kinetic_inputs import kinetic_arguments_schema

HERE = Path(__file__).parent
BASE = HERE.parent / 'a105_summary_precision_components_248'

def load(name):
    return json.loads((BASE / name).read_text())

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

selection = load('SELECTION_SCHEMA_002.json')
sheet = load('SHEET_SCHEMA_004.json')
names = list(sheet['properties']['source_cells']['properties'])
components = [prefix + '_' + name for prefix in ('source', 'scenario') for name in names]
roster = {'type': 'array', 'uniqueItems': True, 'items': {'enum': components}}
save('REQUEST_ROSTER_SCHEMA_001.json', roster)
ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
locator = deepcopy(sheet['properties']['contribution']['properties']['dependency_sources']['items'])
locator['properties']['source_ref'] = deepcopy(ref)
locator['properties']['artifact_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'artifact'}
context_names = ['organism', 'genotype', 'molecule', 'construct', 'substrate', 'preparation', 'experiment', 'experimental_system', 'conditions', 'endpoint', 'normalization']
window = obj({'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
return_context = obj({name: {'type': 'array', 'items': deepcopy(window), 'uniqueItems': True} for name in context_names})
args = obj({'version': {'const': 'literature_kinetic_summary_precision_population_v1'},
    'selection': selection, 'requested_cells': deepcopy(roster), 'return_context': return_context})
save('SELECTED_ARGUMENTS_SCHEMA_001.json', args)
save('ORIGINAL_SELECTION_SCHEMA_001.json', selection)
save('ORIGINAL_EXTRACTION_SCHEMA_001.json', load('EXTRACTION_SCHEMA_004.json'))
save('ORIGINAL_CALCULATION_INPUTS_SCHEMA_001.json', load('CALCULATION_INPUTS_SCHEMA_004.json'))
save('ORIGINAL_SHEET_SCHEMA_001.json', sheet)
fragment = obj({'text': {'type': 'string', 'minLength': 1}, 'location': locator})
context = obj({name: obj({'status': {'enum': ['selected', 'not_selected', 'source_unavailable']},
    'fragments': {'type': 'array', 'items': deepcopy(fragment)}}) for name in context_names})
input_props = sheet['properties']['inputs']['properties']
assessment_names = list(input_props['assessments']['properties'])
assessment = obj({'condition': {'enum': assessment_names}, 'state': {'enum': ['source_supported', 'source_contradicted', 'unknown', 'conflicting']}})
row = obj({'row_version': {'const': 'kinetic_summary_precision_return_v1'}, 'sheet_ref': ref,
    'evidence_source_ref': deepcopy(ref), 'evaluation_scope': {'const': 'source_kinetic_summary_precision'},
    'component': {'enum': components}, 'population': {'enum': ['source_cells', 'scenario_cells']},
    'cell_name': {'enum': names}, 'cell': {}, 'source_kind': deepcopy(input_props['source_kind']),
    'parameter_kind': deepcopy(input_props['parameter_kind']), 'source_context': context,
    'sampling_basis': obj({key: deepcopy(input_props[key]) for key in ('source_count_meaning', 'repetition_basis', 'estimate_basis')}),
    'model_conditions': {'type': 'array', 'items': assessment, 'uniqueItems': True},
    'contribution': obj({'kind': {'const': 'one_summary_precision_contribution'},
        'physical_measurement_id': deepcopy(sheet['properties']['contribution']['properties']['physical_measurement_id']),
        'independence_inferred': {'const': False},
        'variance_meaning': {'const': 'estimated_random_mean_precision_not_known_population_variance'},
        'shared_systematic_uncertainty': {'const': 'not_established_by_summary_precision'}}),
    'dependency_locations': {'type': 'array', 'items': deepcopy(locator), 'uniqueItems': True},
    'withheld_locations': {'type': 'array', 'items': deepcopy(locator), 'uniqueItems': True},
    'bounds_kind': {'const': 'no_additional_bounds_in_this_return'},
    'limits': deepcopy(sheet['properties']['limits'])})
branches = []
for prefix, population in [('source', 'source_cells'), ('scenario', 'scenario_cells')]:
    group = sheet['properties'][population]
    if population == 'scenario_cells':
        group = group['anyOf'][0]
    for name in names:
        branches.append({'properties': {'component': {'const': prefix + '_' + name},
            'population': {'const': population}, 'cell_name': {'const': name},
            'cell': deepcopy(group['properties'][name])}})
row['oneOf'] = branches
rows = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'array',
    'x-source': 'literature_kinetic_summary_precision_cells', 'x-unique-by': ['sheet_ref', 'component'],
    'items': row, '$defs': deepcopy(sheet['$defs'])}
save('RETURN_ROWS_SCHEMA_001.json', rows)
save('OPERATION_UNION_SCHEMA_001.json', {'anyOf': [kinetic_arguments_schema(), args]})
save('PROPOSAL_MANIFEST_001.json', {'status': 'plan_only_awaiting_root_review', 'goal_changed': False,
    'schema_sources': {name: hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in (
        'SELECTION_SCHEMA_002.json', 'EXTRACTION_SCHEMA_004.json', 'CALCULATION_INPUTS_SCHEMA_004.json', 'SHEET_SCHEMA_004.json')},
    'task_sha256': hashlib.sha256((BASE/'TASK_PROPOSAL_001.txt').read_bytes()).hexdigest(),
    'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'PROPOSAL_MANIFEST_001.json'}})
