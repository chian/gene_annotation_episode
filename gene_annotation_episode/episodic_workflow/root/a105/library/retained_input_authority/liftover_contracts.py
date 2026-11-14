"""Pure point-liftover records; shape and consistency confer no custody.

PyLiftover performs the conversion. This module retains its complete supplied
observation, interprets native tuples once, and calculates only explicitly
defined population/selection components. It neither opens a chain nor imports
PyLiftover, acquires data, chooses a mapping, or authenticates a producer.
"""
from copy import deepcopy
RETURN_VERSION = 'liftover_point_return_v1'
FACT_SOURCE = 'liftover_point_mappings'
CALL_SCOPE = 'retained_convert_coordinate_call'
CHAIN_FORMATS = ('ucsc_chain', 'ucsc_chain_gzip')
CALL_STATES = ('not_started', 'returned', 'raised', 'uncertain')
POINT_STATES = ('not_started', 'conversion_failed', 'execution_unconfirmed', 'result_unavailable', 'chromosome_not_in_chain', 'unmapped_under_selected_chain', 'unique', 'multiple', 'native_result_invalid', 'native_rows_invalid')
ISSUES = ('native_result_type_invalid', 'native_tuple_type_invalid', 'native_tuple_width_invalid', 'native_target_chromosome_invalid', 'native_target_position_invalid', 'native_target_strand_invalid', 'native_chain_score_invalid')
FAILURES = {'input_unavailable': 'input', 'input_identity_conflict': 'input', 'chain_read_failed': 'chain_read', 'chain_parse_failed': 'chain_parse', 'coordinate_conversion_failed': 'convert_coordinate', 'native_result_capture_failed': 'capture', 'native_result_unavailable': 'capture', 'execution_unconfirmed': 'execution'}

def _obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _enum(values):
    return {'enum': list(values)}

def _nullable(node):
    return {'anyOf': [node, {'type': 'null'}]}

def _file_schema():
    return _obj(dict(artifact_ref={'type': 'string', 'pattern': '^artifact_[a-f0-9]{64}$'}, sha256={'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, size_bytes={'type': 'integer', 'minimum': 0}, format=_enum(CHAIN_FORMATS)))

def _point_schema():
    return _obj(dict(chromosome={'type': 'string', 'minLength': 1, 'description': 'Exact supplied contig token; no prefix, alias, case or species normalization.'}, position_0based={'type': 'integer', 'minimum': 0, 'description': 'Zero-based nucleotide position relative to the forward source contig, on either strand.'}, strand=_enum(('+', '-'))))

def liftover_fact_sources():
    """Closed Source-owned facts; schema registration alone proves no execution."""
    text = {'type': 'string'}
    integer = {'type': 'integer'}
    count = {'type': 'integer', 'minimum': 0}
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    issue = _obj(dict(code=_enum(ISSUES), row_ordinal=_nullable(count)))
    unknown = _obj(dict(state={'const': 'unavailable'}, label={'type': 'null'}, reason={'const': 'not_provided'}))
    row = _obj(dict(ordinal={**count, 'description': 'Original zero-based row index in the full native returned list.'}, state=_enum(('valid', 'invalid')), target_chromosome=_nullable(text), target_position_0based={**_nullable(count), 'description': 'Literal zero-based nucleotide position relative to the forward target contig on either strand.'}, target_strand=_enum(('+', '-', None)), native_chain_score={**_nullable(integer), 'description': 'Literal native chain alignment score; no probability or uncertainty claim.'}, qualification_codes={'type': 'array', 'items': _enum(ISSUES)}))
    population = _obj(dict(requested_point_count={'type': 'integer', 'const': 1}, point_state=_enum(POINT_STATES), native_row_count=_nullable(count), valid_mapping_count=_nullable(count), mapping_count=_nullable(count), mapping_count_scope={'const': 'full_native_return'}, conversion_call_scope={'const': CALL_SCOPE}, conversion_call_state=_enum(CALL_STATES), conversion_call_count=_nullable({'type': 'integer', 'minimum': 0, 'maximum': 1})))
    returned = _obj(dict(version={'const': RETURN_VERSION}, source_ref=source, chain=_obj(dict(file=_file_schema(), source_ref=_nullable(source))), point=_point_schema(), assembly_context=_obj(dict(source=unknown, target=deepcopy(unknown))), population=population, parsing_state=_enum(('not_applicable', 'complete', 'partial', 'invalid')), selected_mapping_ordinals={'type': 'array', 'items': count, 'uniqueItems': True}, rows={'type': 'array', 'items': row}, issues={'type': 'array', 'items': issue}, failure=_nullable(_obj(dict(stage=_enum(tuple(dict.fromkeys(FAILURES.values()))), code=_enum(FAILURES), location_code={'const': 'native_failure'}, occurrence={'type': 'integer', 'const': 0})))))
    return {FACT_SOURCE: dict(type='array', meaning='Exact retained point-liftover mappings and full-native-population qualifications. Native tuple order, literal contigs, zero-based positions, strands and alignment scores are preserved. Unknown assembly labels and unknown/empty/failed results remain distinct; row selection is not a unique-mapping claim.', report_schema={'type': 'array', 'items': returned, 'x-source': FACT_SOURCE})}
