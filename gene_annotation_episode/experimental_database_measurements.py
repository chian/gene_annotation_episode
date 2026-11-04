"""Authenticate native database cells for the existing A105 assay grader.

The selector contains locations, never a model-authored measurement. Native
units, censoring, missingness and score definitions remain explicit. This is a
source reader; it supplies no assay validity, variance or prediction defaults.
"""
import json
import math
import re

from .domain import ContractError, REF, identity, obj
from .experimental_database_records import native_rows


def measurement_schema():
    return obj({'kind': {'const': 'database_measurement'}, 'source_ref': REF,
        'record_index': {'type': 'integer', 'minimum': 0},
        'field': {'type': 'string', 'minLength': 1, 'maxLength': 200},
        'metadata_source_ref': {'anyOf': [REF, {'type': 'null'}]}})


def _record(reference, read_record, sources, read_database_request):
    source = read_record(reference)
    if source.get('record_type') != 'source' or source.get('id') != reference:
        raise ContractError('database_measurement_source_required')
    provider = source.get('provider', '').removeprefix('experimental.')
    if provider not in ('sabiork', 'chembl', 'mavedb', 'bioassay'):
        raise ContractError('database_measurement_provider_unsupported')
    if read_database_request is None:
        raise ContractError('database_measurement_request_reader_required')
    receipt = read_database_request(reference)
    selected = receipt.get('request', {})
    transport = receipt.get('transport', {})
    response = transport.get('response', transport)
    if (selected.get('operation') not in ('public.' + provider + '.search', 'public.' + provider + '.read')
            or response.get('status') != 200 or response.get('body_complete') is not True):
        raise ContractError('database_measurement_complete_successful_source_required')
    body = sources.source(reference, 'original')
    return source, provider, body, selected


def _json(body):
    try:
        return json.loads(body['content'])
    except (ValueError, UnicodeDecodeError) as error:
        raise ContractError('database_measurement_native_json_required') from error


def _row(rows, index):
    if not 0 <= index < len(rows):
        raise ContractError('database_measurement_record_index_out_of_bounds')
    return rows[index]


def _number(value):
    if value is None or str(value).strip() in ('', 'NA', 'NaN', 'nan', 'null'):
        return None
    if type(value) is bool or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', str(value).strip()):
        raise ContractError('database_measurement_literal_number_required')
    result = float(value)
    if not math.isfinite(result):
        raise ContractError('database_measurement_finite_number_required')
    return result


def read_measurement(selection, *, sources, read_record, read_database_request, role):
    source, provider, body, request = _record(selection['source_ref'], read_record, sources, read_database_request)
    index, field = selection['record_index'], selection['field']
    unit, relation, value, native_type = None, None, None, None
    qualifiers, source_refs = [], [source['id']]
    metadata = selection['metadata_source_ref']
    native_owner = None
    if provider == 'sabiork':
        row = _row(_json(body)['data'], index)
        match = re.fullmatch(r'parameter:([0-9]+)', field)
        if match is None:
            raise ContractError('sabiork_parameter_selector_required')
        parameter = _row(row.get('kineticlaw', {}).get('parameter', []), int(match[1]))
        value, end = parameter.get('start_value'), parameter.get('end_value')
        unit = parameter.get('unit', {}).get('name')
        native_type = parameter.get('parameter_type', {}).get('name')
        relation = '=' if end is None or end == value else 'range'
        if relation == 'range':
            qualifiers.append('reported_parameter_range_is_not_point_or_censoring')
        qualifiers.append('native_parameter:' + str(native_type))
        native_owner = {'provider': provider, 'entry_id': row['id'], 'parameter_index': int(match[1])}
    elif provider == 'chembl':
        data = _json(body)
        row = _row(data['activities'], index)
        if field not in ('standard_value', 'value'):
            raise ContractError('chembl_activity_value_selector_required')
        prefix = 'standard_' if field == 'standard_value' else ''
        value, unit, relation = row.get(field), row.get(prefix + 'units'), row.get(prefix + 'relation')
        native_type = row.get(prefix + 'type')
        qualifiers.append('native_parameter:' + str(native_type))
        for key in ('data_validity_comment', 'activity_comment', 'potential_duplicate'):
            if row.get(key) not in (None, '', False, 0):
                qualifiers.append(key + ':' + str(row[key]))
        native_owner = {'provider': provider, 'activity_id': row['activity_id']}
    else:
        if metadata is None:
            raise ContractError('database_measurement_matching_assay_metadata_required')
        meta_source, meta_provider, meta_body, meta_request = _record(metadata, read_record, sources, read_database_request)
        if meta_provider != provider:
            raise ContractError('database_measurement_metadata_provider_mismatch')
        source_refs.append(metadata)
        data = _json(meta_body)
        if provider == 'mavedb':
            if (request['arguments'].get('section') != 'scores'
                    or meta_request['arguments'].get('section') != 'metadata'):
                raise ContractError('mavedb_scores_and_metadata_sources_required')
            urn = data['urn']
            rows = native_rows(body['content'], 'public.mavedb.read', {'section': 'scores'})
            row = _row(rows, index)
            if not str(row.get('accession', '')).startswith(urn + '#'):
                raise ContractError('mavedb_score_metadata_identity_mismatch')
            if field not in data.get('datasetColumns', {}).get('scoreColumns', []):
                raise ContractError('mavedb_declared_score_column_required')
            value, unit, relation = row.get(field), 'native_score', '='
            native_type = 'deposited_assay_score'
            qualifiers.extend(('native_score_definition_requires_assay_interpretation',
                'variant:' + str(row.get('hgvs_pro') or row.get('hgvs_nt')),
                'target_construct_and_variant_background_retained'))
            native_owner = {'provider': provider, 'variant_accession': row['accession'], 'field': field}
        else:
            if (request['arguments'].get('section') != 'results'
                    or meta_request['arguments'].get('section') != 'description'):
                raise ContractError('bioassay_results_and_description_sources_required')
            descr = data['PC_AssayContainer'][0]['assay']['descr']
            if str(descr['aid']['id']) != source.get('accession'):
                raise ContractError('bioassay_result_metadata_identity_mismatch')
            row = _row(native_rows(body['content'], 'public.bioassay.read', {'section': 'results'}), index)
            definition = next((item for item in descr.get('results', []) if item.get('name') == field), None)
            if definition is None:
                raise ContractError('bioassay_defined_result_column_required')
            # PubChem ASN.1 PC-AssayDescription result-unit codes. Unknown/custom
            # units stay unresolved; prose definitions remain readable separately.
            unit = {1: 'ppt', 2: 'ppm', 3: 'ppb', 4: 'mM', 5: 'uM', 6: 'nM',
                    7: 'pM', 8: 'fM', 9: 'mg/mL', 10: 'ug/mL', 11: 'ng/mL',
                    12: 'pg/mL', 13: 'fg/mL', 14: 'M', 15: 'percent',
                    16: 'ratio', 17: 's', 18: 's^-1', 19: 'min', 20: 'min^-1',
                    21: 'day', 22: 'day^-1', 23: 'mL/min/kg', 24: 'L/kg',
                    25: 'h*ng/mL', 26: 'cm/s', 27: 'mg/kg',
                    254: 'dimensionless'}.get(definition.get('unit'))
            value, relation, native_type = row.get(field), None, field
            qualifiers.extend(('result_definition:' + json.dumps(definition, ensure_ascii=False),
                'activity_outcome:' + str(row.get('PUBCHEM_ACTIVITY_OUTCOME'))))
            # Numeric CSV cells can carry explicit comparators. A plain number
            # remains a reported point, with the protocol's qualifications intact.
            if value is not None:
                match = re.fullmatch(r'\s*(<=|>=|<|>|=)?\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*', str(value))
                if match:
                    relation, value = match[1] or '=', match[2]
            native_owner = {'provider': provider, 'aid': descr['aid']['id'],
                'result_tag': row.get('PUBCHEM_RESULT_TAG'), 'sid': row.get('PUBCHEM_SID'),
                'field': field}
    if role != 'effect':
        # These finite readers expose measured parameters/scores, not inferred
        # variances, attribution fractions, recoveries or independent predictions.
        raise ContractError('database_measurement_requires_effect_role')
    value = _number(value)
    status, reason = 'point', None
    if value is None:
        status, reason = 'unavailable', 'native_measurement_missing'
    elif unit is None:
        status, reason = 'unavailable', 'native_measurement_unit_unresolved'
    elif relation not in ('=', '<', '<=', '>', '>='):
        status, reason = 'unavailable', 'native_measurement_relation_unresolved'
    factor = 1.
    if unit is not None and unit != 'native_score':
        from .literature_assay_grading_inputs import _unit
        aliases = {'s^(-1)': 's^-1', 'min^(-1)': 'min^-1', 'M': 'M',
                   'percent': '%', 'ratio': 'dimensionless'}
        try:
            unit, factor = _unit(aliases.get(unit, unit))
        except ContractError:
            status, reason = 'unavailable', 'native_measurement_unit_unsupported:' + str(unit)
    if status == 'point' and relation != '=':
        status, reason = 'bounded', 'reported_censoring_event'
    key = identity('database_physical_measurement', native_owner)
    result = {'value': value * factor if status == 'point' else None, 'unit': unit or 'unknown',
              'status': status, 'reason': reason, 'measurement_keys': [key],
              'source_refs': list(dict.fromkeys(source_refs)), 'origin': 'reported',
              'native_component': provider + ':' + field,
              'qualifications': qualifiers + ['source_cell:' + body['artifact_ref']]}
    if result['value'] is not None and not math.isfinite(result['value']):
        raise ContractError('database_measurement_numerical_range')
    if status == 'bounded':
        result['bound'] = {'relation': {'<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge'}[relation],
                          'lower': value * factor if relation.startswith('>') else None,
                          'upper': value * factor if relation.startswith('<') else None}
    return result
