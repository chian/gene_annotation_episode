"""Typed Source groups for the unchanged shared TF public projection.

Shape and semantic-reference annotations belong here. The measurement owner
validates numerical identities and cross-field relationships without rescoring.
Neither validator establishes publication custody or grants input File access.
"""
from copy import deepcopy
import hashlib
import json
import math

from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import ValidationError

from . import tf_binding_measurements as core


TOOL = core.OPERATION
FACT_SOURCE = 'tf_binding_outcomes'
SOURCE_VERSION = 'ordinary_tf_binding_result_v1'
CAPTURE_VERSION = 'ordinary_tf_binding_native_capture_v1'
PACKET_VERSION = 'ordinary_tf_binding_public_packet_v1'
_TEXT = {'type': 'string', 'minLength': 1}
_INT = {'type': 'integer', 'minimum': 0}
_DIGEST = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
_SOURCE = {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$',
    'format': 'reference', 'x-reference-namespace': 'source'}
_STRICT = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine_many({
        'integer': lambda _, value: type(value) is int,
        'number': lambda _, value: type(value) is int or type(value) is float and math.isfinite(value),
    }))


def _object(properties):
    return {'type': 'object', 'properties': deepcopy(properties),
        'required': list(properties), 'additionalProperties': False}


def _array(items):
    return {'type': 'array', 'items': deepcopy(items)}


def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def _ref(name):
    return {'$ref': '#/$defs/' + name}


def _definitions():
    definitions = {}
    definitions['BaseParameterMap'] = _object({base: {'type': 'number', 'minimum': 0}
        for base in 'ACGT'})
    definitions['Parameters'] = _object(dict(background=_ref('BaseParameterMap'),
        pseudocounts=_ref('BaseParameterMap')))
    definitions['Selection'] = _object(dict(version={'const': 'tf_binding_selection_v1'},
        scan_ids={**_array(_TEXT), 'uniqueItems': True}, raw_threshold={'type': 'number'},
        offset=_INT, limit=_INT))
    definitions['Execution'] = _object(dict(native_outcome={'enum': ['succeeded', 'failed', 'not_run', 'unknown']},
        returncode={'type': 'null'}))
    definitions['Authority'] = _object(dict(convention={'const': core.NUMERIC_CONVENTION},
        numpy_version=_TEXT, biopython_version=_TEXT, threshold_operand={'const': 'python_float'},
        threshold_binary64_hex={'type': 'string', 'pattern': '^[0-9a-f]{16}$'},
        comparison={'const': 'float32_ndarray_ge_python_float'},
        relative={'const': 'numpy_float32_scalar_minus_python_float_div_python_float'},
        relative_bounds={'const': 'forward_pssm_bounds_for_both_strands'}))
    definitions['Capture'] = _object(dict(state={'enum': ['complete', 'truncated', 'missing']},
        byte_start_0based={'const': 0}, byte_end_0based_exclusive=_INT,
        original_size_bytes=_nullable(_INT)))
    # These IDs retain input associations. They are not semantic references.
    definitions['Input'] = _object(dict(input_id=_TEXT, role={'enum': ['dna', 'matrix']},
        format={'enum': ['fasta', 'raw_dna', 'jaspar_json', 'jaspar_pfm', 'acgt_count_json']},
        artifact_id={'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}, sha256=_DIGEST,
        size_bytes=_INT, upstream_source_id=_nullable(_TEXT), capture=_ref('Capture')))
    definitions['Sequence'] = _object(dict(sequence_id=_TEXT, input_id=_TEXT,
        record_ordinal_0based=_INT, identifier=_nullable({'type': 'string'}),
        length=_nullable(_INT), state={'enum': ['available', 'unavailable']}))
    definitions['Matrix'] = _object(dict(matrix_occurrence_id=_TEXT, model_id=_TEXT, input_id=_TEXT,
        record_ordinal_0based=_INT, native_matrix_id=_nullable({'type': 'string'}),
        name=_nullable({'type': 'string'}), length=_nullable(_INT), state={'enum': ['available', 'unavailable']}))
    definitions['Coverage'] = _object(dict(state={'enum': ['complete', 'partial', 'zero_possible', 'unavailable']},
        expected_positions=_nullable(_INT), declared_count=_nullable(_INT), captured_complete_elements=_INT,
        usable_elements=_INT, trailing_bytes={**_INT, 'maximum': 3}, excess_elements=_INT))
    definitions['Scan'] = _object(dict(scan_id=_TEXT, sequence_id=_TEXT, matrix_occurrence_id=_TEXT,
        model_id=_TEXT, strand={'enum': ['+', '-']}, possible_positions=_nullable(_INT), coverage=_ref('Coverage')))
    definitions['SelectedScan'] = _object(dict(scan_id=_TEXT, coverage=_ref('Coverage')))
    extended = dict(classification={'enum': ['finite', 'nan', 'positive_infinity', 'negative_infinity']},
        value=_nullable({'type': 'number'}), dtype={'enum': ['float32', 'float64']},
        byte_order={'enum': ['little', 'big']}, bits_hex={'type': 'string', 'pattern': '^(?:[0-9a-f]{8}|[0-9a-f]{16})$'},
        unit={'enum': ['bits', 'dimensionless']}, origin={'enum': ['native_observation', 'calculated']},
        state={'enum': ['available', 'undefined']}, reason_code=_nullable(_TEXT))
    definitions['Extended'] = _object(extended)
    definitions['Relative'] = _object(dict(extended, relative_normalization_id=_TEXT))
    definitions['Normalization'] = _object(dict(normalization_id=_TEXT, model_id=_TEXT,
        bounds_strand={'const': '+'}, operand_dtype={'const': 'python_float_binary64'},
        scientific_state={'enum': ['defined', 'undefined']}, reason_code=_nullable(_TEXT),
        minimum=_ref('Extended'), maximum=_ref('Extended'), span=_ref('Extended')))
    uncertainty = _nullable(_object(dict(kind={'enum': ['confidence_interval', 'standard_error',
        'standard_deviation', 'native_unknown']}, lower=_nullable({'type': 'number'}),
        upper=_nullable({'type': 'number'}), value=_nullable({'type': 'number'}), method_id=_TEXT)))
    definitions['NumericCell'] = _object(dict(value=_nullable(_INT),
        state={'enum': ['available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible']},
        unit={'const': 'count'}, origin={'const': 'calculated'}, numerator=_nullable({'type': 'number'}),
        denominator=_nullable({'type': 'number'}), population_id=_TEXT, method_id=_TEXT, uncertainty=uncertainty))
    fields = ('raw_complete_elements', 'observed_window_scores', 'finite_scores', 'nan_scores',
        'positive_infinity_scores', 'negative_infinity_scores', 'extended_scorable_scores',
        'possible_strand_windows', 'possible_unique_windows', 'matched_observed_scores',
        'raw_full_threshold_matches', 'full_matched_scores', 'model_eligible_candidate_sites',
        'returned_raw_threshold_rows', 'returned_candidate_rows')
    definitions['Totals'] = _object({name: _ref('NumericCell') for name in fields})
    definitions['Hit'] = _object(dict(hit_id=_TEXT, scan_id=_TEXT, sequence_id=_TEXT,
        matrix_occurrence_id=_TEXT, sequence_record_ordinal_0based=_INT, matrix_record_ordinal_0based=_INT,
        start_0based=_INT, end_0based_exclusive=_INT, strand={'enum': ['+', '-']},
        forward_sequence={'type': 'string'}, model_normalization_eligible={'type': 'boolean'},
        motif_oriented_sequence={'type': 'string'}, score=_ref('Extended'), relative_score=_ref('Relative')))
    definitions['Issue'] = _object(dict(code=_TEXT,
        phase={'enum': ['custody', 'prepare', 'transport', 'native_decode', 'association', 'publication', 'recovery', 'return']},
        path={'type': 'string', 'pattern': '^(?:/.*)?$'}, severity={'enum': ['error', 'qualification']}))
    properties = dict(status={'enum': ['complete', 'partial', 'unavailable']},
        parameters=_ref('Parameters'), selection=_ref('Selection'),
        execution=_ref('Execution'), numeric_authority=_ref('Authority'), available_scans=_array(_ref('Scan')),
        relative_normalizations=_array(_ref('Normalization')), inputs=_array(_ref('Input')),
        sequences=_array(_ref('Sequence')), matrices=_array(_ref('Matrix')),
        selected_scans=_array(_ref('SelectedScan')), totals=_ref('Totals'),
        raw_threshold_matches=_array(_ref('Hit')), hits=_array(_ref('Hit')), issues=_array(_ref('Issue')))
    definitions['Value'] = _object(properties)
    definitions['Return'] = _object(dict(version={'const': core.RETURN_VERSION}, source_ref=_SOURCE, **properties))
    return definitions


def tf_binding_result_schema(kind='Return'):
    """Return detached exact public schemas, including only reachable records."""
    if kind not in ('Value', 'Return'): raise ValueError('tf_binding_result_schema_kind_invalid')
    definitions = _definitions(); pending, reachable = [kind], {}
    def refs(node):
        if type(node) is dict:
            if '$ref' in node: yield node['$ref'].removeprefix('#/$defs/')
            for child in node.values(): yield from refs(child)
        elif type(node) is list:
            for child in node: yield from refs(child)
    while pending:
        name = pending.pop()
        if name in reachable: continue
        reachable[name] = deepcopy(definitions[name]); pending.extend(refs(reachable[name]))
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$ref': '#/$defs/' + kind, '$defs': reachable}


def _validated(kind, value):
    try:
        json.dumps(value, allow_nan=False)
        _STRICT(tf_binding_result_schema(kind)).validate(value)
        public = value if kind == 'Value' else {key: item for key, item in value.items() if key not in ('version', 'source_ref')}
        core.validate_tf_binding_public_value(public)
    except (ValidationError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        raise ValueError('tf_binding_' + kind.lower() + '_invalid') from error
    return deepcopy(value)


def validate_tf_binding_return(value):
    """Check literal public facts; Source custody remains the reader's task."""
    return _validated('Return', value)


def validate_tf_binding_value(value):
    """Validate a source-free packet without constructing any SourceRef."""
    return _validated('Value', value)


def tf_binding_return(value, *, source_ref):
    return validate_tf_binding_return(dict(version=core.RETURN_VERSION, source_ref=source_ref,
        **validate_tf_binding_value(value)))


def tf_binding_fact_sources():
    schema = tf_binding_result_schema()
    report = {'$schema': schema['$schema'], '$defs': schema['$defs'], 'type': 'array',
        'items': {'$ref': schema['$ref']}, 'x-source': FACT_SOURCE}
    encoded = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    report['$id'] = 'urn:gene-annotation:tf-binding-return:' + hashlib.sha256(encoded).hexdigest()
    return {FACT_SOURCE: {'type': 'array', 'meaning': (
        'Retained supplied-sequence/count-matrix TF score measurements, raw log2 threshold selection, '
        'ordered occurrence/strand populations, normalization eligibility and qualifications. '
        'Candidate sites do not establish measured binding or regulation.'), 'report_schema': report}}


__all__ = ['TOOL', 'FACT_SOURCE', 'SOURCE_VERSION', 'CAPTURE_VERSION', 'PACKET_VERSION',
    'tf_binding_result_schema', 'validate_tf_binding_return', 'validate_tf_binding_value',
    'tf_binding_return', 'tf_binding_fact_sources']
