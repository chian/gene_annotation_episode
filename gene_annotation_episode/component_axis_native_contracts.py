"""Declared source-table formats for A107/A110 native component calculations.

These schemas describe supplied records, not experimental truth or target
attribution. Only the shared HPC adapter authenticates their input/output bytes.
"""
from copy import deepcopy
from collections.abc import Mapping
import importlib


VERSION = 'component_axis_native_v1'
OPERATIONS = {'A107': 'partner.request_expression_hpc',
    'A110': 'chemistry.request_accounting_hpc'}
MODULES = {'A107': 'a107_expression_contracts', 'A110': 'a110_chemical_contracts'}


def _contract(axis):
    if axis not in MODULES:
        raise ValueError('component_axis_native_unknown_axis')
    return importlib.import_module('.'+MODULES[axis], __package__)


class _Profiles(Mapping):
    def __getitem__(self, axis):
        if axis not in MODULES:
            raise KeyError(axis)
        return _contract(axis).VERSION

    def __iter__(self):
        return iter(MODULES)

    def __len__(self):
        return len(MODULES)


PROFILES = _Profiles()


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


def expression_schema(version=None):
    return _contract('A107').source_schema(version)


def chemistry_schema():
    return _contract('A110').source_schema()


def source_schema(axis):
    return _contract(axis).source_schema()


def selection_schema(axis):
    return _contract(axis).selection_schema()


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


def tool_catalog(axis):
    import json
    ref = {'type': 'string', 'format': 'reference'}
    description = ('Prepare an A107 shared-HPC request to calculate selected matched-condition expression measurements, declared assay-threshold '
        'comparisons and optional descriptive Pearson correlation from an admitted declared table. '
        'Select right_feature_id=null for one measured component. Retain censor bounds without '
        'imputation, missing pairs, repeated biological units and actual feature identity. Source '
        'calibration/condition assertions require scientific review. This is not protein activity, a significance test or '
        'automatic target correspondence.' if axis == 'A107' else
        'Prepare an A110 shared-HPC request to calculate exact signed stoichiometric atom/charge residuals, explicit electron terms, '
        'declared pathway/carrier accounting and supported chemical Gibbs components from an '
        'admitted declared panel. Optionally reuse the original reported reaction/resource '
        'calculator. Missing identities and prerequisites remain unknown. This is not activity '
        'or an annotation probability.')
    description += (' Source-content inspection is the separate source.read/source.locate '
        'capability. When preparing a fixed child toolset, retrieve and include the actual '
        'readers it needs to inspect supplied table IDs, conditions and operands; selecting '
        'this request operation alone does not grant those readers.')
    return {OPERATIONS[axis]: {'description': description, 'resources': 'local',
        'instructions': description+' Freeze this exact source and selection, then commission the '
            'returned shared HPC assignment. This operation does no native calculation or job launch. '
            'Source tables are supplied observations or explicit sourced extractions; preparation '
            'does not turn a model-authored number into an experimental measurement. Native '
            'publication and grading occur automatically when its authenticated result arrives. '
            'The supported input JSON contract is:\n'+json.dumps(source_schema(axis), sort_keys=True),
        'input_schema': obj({'target_ref': ref, 'source_ref': ref,
            'resource_id': text(), 'selection': selection_schema(axis)})}}
