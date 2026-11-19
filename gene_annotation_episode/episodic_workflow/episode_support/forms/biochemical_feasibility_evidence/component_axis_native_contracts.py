"""Declared source-table formats for A110 native component calculations.

These schemas describe supplied records, not experimental truth or target
attribution. Only the shared HPC adapter authenticates their input/output bytes.
"""
from copy import deepcopy


VERSION = 'component_axis_native_v1'
OPERATIONS = {'A110': 'chemistry.request_accounting_hpc'}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def text():
    return {'type': 'string', 'minLength': 1}


def array(schema, *, minimum=0):
    return {'type': 'array', 'items': schema, 'minItems': minimum}


def identities():
    return {**array(text()), 'uniqueItems': True}


from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence import a110_chemical_contracts as contracts
PROFILES = {'A110': contracts.VERSION}


def chemistry_schema():
    return contracts.source_schema()


def source_schema(axis):
    return contracts.source_schema()


def selection_schema(axis):
    return contracts.selection_schema()


def validate_source(axis, document):
    import json
    import jsonschema
    json.dumps(document, allow_nan=False)
    jsonschema.Draft202012Validator(source_schema(axis)).validate(document)
    return document


def load_json(raw):
    import json
    import math
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('component_axis_native_duplicate_json_key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('component_axis_native_nonfinite_json')
    def floating(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('component_axis_native_nonfinite_json')
        return number
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)


def tool_catalog():
    import json
    ref = {'type': 'string', 'format': 'reference'}
    description = ('Prepare an A110 shared-HPC request to calculate exact signed stoichiometric atom/charge residuals, explicit electron terms, '
        'declared pathway/carrier accounting and supported chemical Gibbs components from an '
        'admitted declared panel. Optionally reuse the original reported reaction/resource '
        'calculator. Missing identities and prerequisites remain unknown. This is not activity '
        'or an annotation probability.')
    description += (' Source-content inspection is the separate source.read/source.locate '
        'capability. When preparing a fixed child toolset, retrieve and include the actual '
        'readers it needs to inspect supplied table IDs, conditions and operands; selecting '
        'this request operation alone does not grant those readers.')
    return {OPERATIONS['A110']: {'description': description, 'resources': 'local',
        'instructions': description+' Freeze this exact source and selection, then commission the '
            'returned shared HPC assignment. This operation does no native calculation or job launch. '
            'Source tables are supplied observations or explicit sourced extractions; preparation '
            'does not turn a model-authored number into an experimental measurement. Native '
            'publication and grading occur automatically when its authenticated result arrives. '
            'The supported input JSON contract is:\n'+json.dumps(contracts.source_schema(), sort_keys=True),
        'input_schema': obj({'target_ref': ref, 'source_ref': ref,
            'resource_id': text(), 'selection': contracts.selection_schema()})}}
