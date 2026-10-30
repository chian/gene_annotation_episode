"""Finite original-XLSX source-cell reading, with no experimental-unit inference."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import io
import re
import sqlite3
import xml.etree.ElementTree as ET
import zipfile

from .domain import REF, identity, obj, validate_schema
from .literature_experimental_contracts import ExperimentalContractError
from .spreadsheet_tools import Workbook, _tag

VERSION = 'a105_reported_rate_observations_v1'
SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
TEXT = {'type': 'string', 'minLength': 1}
CELL = {'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}
STATUSES = ('observed', 'missing', 'not_detected', 'censored', 'unsupported_cell')
ENTRY_REASONS = ('source_measurement_unavailable', 'nondetection_without_point',
    'censored_measurement', 'formula_measurement_unsupported', 'numeric_cell_type_required',
    'source_cell_error', 'invalid_numeric_lexeme')


def label_schema():
    return obj({'cell': deepcopy(CELL), 'expected_text': deepcopy(TEXT)})


def rate_observation_population_schema():
    observation = obj({'label': label_schema(), 'value_cell': deepcopy(CELL)})
    group = obj({'label': label_schema(), 'observations': {'type': 'array',
        'minItems': 1, 'items': observation}})
    return obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
        'worksheet': deepcopy(TEXT), **{name: label_schema() for name in ('panel','subject','native_unit')},
        'groups': {'type': 'array', 'minItems': 1, 'items': group},
        'reference_group': deepcopy(TEXT), 'test_group': deepcopy(TEXT)})


def _fail(code, field):
    raise ExperimentalContractError(code,field)


def _row_column(address):
    match=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',address)
    return int(match[2]),match[1]


def validate_selected_layout(args):
    """The supported layout is contiguous labelled rows under group headers.

    This validates representation relationships, not experimental independence.
    Different source cells never collapse merely because their text matches.
    """
    subject_row,subject_column=_row_column(args['subject']['cell'])
    headers={}
    for group in args['groups']:
        label=group['label'];address=label['cell']
        previous=headers.setdefault(label['expected_text'],address)
        if previous!=address:_fail('ambiguous_group_label_scope','groups')
        row,column=_row_column(address)
        if row<=subject_row:_fail('group_header_must_follow_subject_header','groups')
        selected_rows=set()
        for observation in group['observations']:
            lr,lc=_row_column(observation['label']['cell']);vr,vc=_row_column(observation['value_cell'])
            if lr!=vr:_fail('observation_label_value_row_mismatch','value_cell')
            if vc!=subject_column:_fail('observation_subject_column_mismatch','value_cell')
            if lc!=column or lr<=row:_fail('observation_group_row_mismatch','groups')
            selected_rows.add(lr)
        if selected_rows!=set(range(row+1,max(selected_rows)+1)):
            _fail('contiguous_group_observation_rows_required','groups')
        next_headers=[_row_column(g['label']['cell'])[0] for g in args['groups']
            if _row_column(g['label']['cell'])[1]==column and _row_column(g['label']['cell'])[0]>row]
        if next_headers and max(selected_rows)>=min(next_headers):
            _fail('observation_crosses_selected_group_header','groups')


def entry_meaning(args, artifact_ref, group, observation):
    """Identity of the witnessed reported representation; no physical unit ID."""
    return {'source_ref':args['source_ref'],'artifact_ref':artifact_ref,'worksheet':args['worksheet'],
        'panel':args['panel']['expected_text'],'subject':args['subject']['expected_text'],
        'native_unit':args['native_unit']['expected_text'],'group':group['label']['expected_text'],
        'observation_label':observation['label']['expected_text'],
        'panel_cell':args['panel']['cell'],'subject_cell':args['subject']['cell'],
        'native_unit_cell':args['native_unit']['cell'],'group_cell':group['label']['cell'],
        'label_cell':observation['label']['cell'],'value_cell':observation['value_cell']}


def read_rate_observations(content, arguments, *, artifact_ref):
    """Read only chosen entries; all measurements originate in workbook bytes.

    Model arguments identify meanings/locations, never measured values. Numeric
    nonformula cells supply points. Blank/ND/limits remain in the source roster;
    cached formula values and text numerals are not accepted numeric points.
    Observation identities identify source-labelled reports, not physical units.
    """
    args=deepcopy(arguments)
    validate_schema(args,rate_observation_population_schema())
    validate_selected_layout(args)
    if args['reference_group']==args['test_group']:
        _fail('distinct_groups_required','test_group')
    digest=hashlib.sha256(content).hexdigest()
    if artifact_ref != 'artifact_'+digest:
        _fail('source_artifact_hash_mismatch','artifact_ref')
    try:
        workbook=Workbook(io.BytesIO(content))
        try:
            layout=workbook.layout()
            selected=[sheet for sheet in layout['sheets'] if sheet['name']==args['worksheet']]
            if len(selected)!=1 or not selected[0]['available']:
                _fail('xlsx_available_unique_worksheet_required','worksheet')
            sheet=selected[0]; member=sheet['worksheet_part']
            with workbook.open(member) as stream: member_bytes=stream.read()
            member_digest=hashlib.sha256(member_bytes).hexdigest()
            wanted={args[name]['cell'] for name in ('panel','subject','native_unit')}
            for group in args['groups']:
                wanted.add(group['label']['cell'])
                for entry in group['observations']:wanted.update((entry['label']['cell'],entry['value_cell']))
            cells={}
            with sqlite3.connect(':memory:') as connection:
                failure=workbook.index_strings(connection,layout['shared_strings_part']) or layout.get('shared_strings_failure')
                if failure:_fail(failure['code'],'shared_strings')
                for element in ET.fromstring(member_bytes).iter():
                    if _tag(element)=='c' and element.get('r') in wanted:
                        address=element.get('r')
                        if address in cells:_fail('xlsx_ambiguous_cell','cell.'+address)
                        cells[address]=workbook.cell(element,connection)
        finally:workbook.close()
    except (zipfile.BadZipFile,ET.ParseError,KeyError,ValueError) as error:
        if isinstance(error,ExperimentalContractError):raise
        raise ExperimentalContractError('xlsx_source_unreadable','source_ref') from error
    custody={'source_ref': args['source_ref'], 'artifact_ref':artifact_ref,
        'workbook_sha256':digest,'worksheet':args['worksheet'],'member':member,'member_sha256':member_digest}
    def witness(address):
        cell=cells.get(address,{'address':address,'cell_type':'absent','value':None,'raw_value':None,
            'style_index':None,'formula':None,'value_is_formula_cache':False,'error':None})
        return {**custody,'cell':address,**{key:deepcopy(cell[key]) for key in
            ('cell_type','value','raw_value','style_index','formula','value_is_formula_cache','error')}}
    def labelled(selector):
        result=witness(selector['cell'])
        if result['formula'] is not None or result['error'] is not None or result['value']!=selector['expected_text']:
            _fail('source_label_witness_mismatch','cell.'+selector['cell'])
        return result
    meanings={name:labelled(args[name]) for name in ('panel','subject','native_unit')}
    origin='synthetic' if args['source_kind']=='synthetic_fixture' else 'reported'
    entries=[]
    for group in args['groups']:
        group_witness=labelled(group['label'])
        for selected in group['observations']:
            label=labelled(selected['label']); value=witness(selected['value_cell'])
            status,reason,exact,bound='unsupported_cell','numeric_cell_type_required',None,'none'
            if value['formula'] is not None:reason='formula_measurement_unsupported'
            elif value['error'] is not None:reason='source_cell_error'
            elif value['value'] is None or value['value'].strip()=='':
                status,reason='missing','source_measurement_unavailable'
            elif value['cell_type']=='n':
                token=value['raw_value']
                if isinstance(token,str) and re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',token):
                    exact=Fraction(token);status,reason='observed',None
                else:reason='invalid_numeric_lexeme'
            elif value['value'].strip().casefold() in ('nd','not detected'):
                status,reason='not_detected','nondetection_without_point'
            else:
                match=re.fullmatch(r'\s*(<=|>=|<|>|≤|≥)\s*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\s*',value['value'])
                if match:
                    status,reason='censored','censored_measurement';bound=match[1]
            meaning=entry_meaning(args,artifact_ref,group,selected)
            entries.append({'record_identity':identity('source_reported_entry',meaning),
                'meaning':meaning,'group':group_witness['value'],'label':label['value'],
                'status':status,'unavailable_reason':reason,'bound':bound,
                'exact_value':None if exact is None else {'numerator':str(exact.numerator),'denominator':str(exact.denominator)},
                'origin':origin,'group_source':group_witness,'label_source':label,'value_source':value})
    return {'version':VERSION,'source_kind':args['source_kind'],'custody':custody,
        'meanings':meanings,'entries':entries,'grouping':'unknown','physical_conversion':'unknown'}


# Explicit grid version; the complete legacy v1 implementation above is retained.
GRID_INPUT_VERSION = 'a105_reported_rate_grid_v1'
GRID_SOURCE_STATUSES = ('observed', 'missing', 'not_detected', 'censored', 'unsupported_cell')
GRID_ENTRY_REASONS = (*ENTRY_REASONS, 'source_error_cell')


def _grid_array(schema, *, minimum=0):
    return {'type': 'array', 'minItems': minimum, 'items': deepcopy(schema)}


def _grid_nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def _grid_exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
                'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})


def _grid_context_selector_schema():
    return obj({'kind': {'const': 'context_span'}, 'source_ref': deepcopy(REF),
        'artifact_ref': deepcopy(REF), 'start': {'type': 'integer', 'minimum': 0},
        'end': {'type': 'integer', 'minimum': 1}, 'quote': deepcopy(TEXT)})


def _grid_witness_selector_schema():
    return {'anyOf': [obj({'kind': {'const': 'xlsx_label'}, **label_schema()['properties']}),
                      _grid_context_selector_schema()]}


def reported_rate_grid_population_schema():
    """Locations/meanings only: measured operands always come from XLSX bytes."""
    witness = _grid_witness_selector_schema()
    interpretation = obj({'status': {'enum': ['reported_convention_only', 'supported', 'unknown', 'conflicting']},
                          'witnesses': _grid_array(witness)})
    sampling = obj({'status': {'enum': ['supported', 'stipulated_sensitivity', 'unknown', 'conflicting']},
        'assumption': {'enum': ['none', 'iid_reported_curve_vectors']},
        'source_claim': {'enum': ['iid_reporting_vectors_supported', 'not_established', 'unknown', 'conflicting']},
        'witnesses': _grid_array(witness)})
    return obj({'version': {'const': GRID_INPUT_VERSION}, 'source_ref': deepcopy(REF),
        'source_kind': {'enum': list(SOURCE_KINDS)}, 'worksheet': deepcopy(TEXT),
        **{name: label_schema() for name in ('panel', 'subject', 'native_rate_label')},
        'curves': _grid_array(obj({'header': label_schema()}), minimum=1),
        'points': _grid_array(obj({'concentration_cell': deepcopy(CELL),
                                  'rate_cells': _grid_array(CELL, minimum=1)}), minimum=1),
        'rate_unit': obj({'code': {'enum': ['umol/min', 'nmol/min', 'mmol/min']}, 'witness': witness}),
        'concentration_unit': obj({'code': {'enum': ['M', 'mM', 'uM', 'nM', 'unknown']},
                                   'witness': _grid_nullable(witness)}),
        'endpoint_relationship': interpretation, 'curve_sampling': sampling})


def _grid_custody_schema():
    return obj({name: deepcopy(TEXT) for name in
        ('source_ref', 'artifact_ref', 'workbook_sha256', 'worksheet', 'member', 'member_sha256')})


def _grid_cell_witness_schema():
    return obj({**_grid_custody_schema()['properties'], 'cell': deepcopy(CELL),
        'cell_type': deepcopy(TEXT), **{name: {'type': ['string', 'null']} for name in
            ('value', 'raw_value', 'style_index', 'error')},
        'formula': _grid_nullable(obj({'text': {'type': ['string', 'null']},
            'attributes': {'type': 'object', 'additionalProperties': {'type': 'string'}}})),
        'value_is_formula_cache': {'type': 'boolean'}})


def _grid_quantity_schema():
    return obj({'measurement_key': deepcopy(TEXT), 'status': {'enum': list(GRID_SOURCE_STATUSES)},
        'unavailable_reason': {'enum': [*GRID_ENTRY_REASONS, None]},
        'bound': {'enum': ['none', '<', '>', '<=', '>=', '≤', '≥']},
        'exact_value': _grid_nullable(_grid_exact_schema()),
        'exact_limit': _grid_nullable(_grid_exact_schema()),
        'origin': {'enum': ['reported', 'synthetic']}, 'witness': _grid_cell_witness_schema()})


def reported_rate_grid_extraction_schema():
    return obj({'version': {'const': GRID_INPUT_VERSION},
        'original_arguments': reported_rate_grid_population_schema(),
        'custody': _grid_custody_schema(),
        'meanings': obj({name: _grid_cell_witness_schema() for name in ('panel', 'subject', 'native_rate_label')}),
        'context_witnesses': _grid_array(_grid_witness_selector_schema()),
        'curves': _grid_array(obj({'curve_key': deepcopy(TEXT), 'header': _grid_cell_witness_schema(),
                                 'selection_indices': _grid_array({'type': 'integer', 'minimum': 0})}), minimum=1),
        'points': _grid_array(obj({'point_key': deepcopy(TEXT), 'concentration': _grid_quantity_schema(),
            'entries': _grid_array(obj({'curve_key': deepcopy(TEXT), 'representation_key': deepcopy(TEXT),
                                      'quantity': _grid_quantity_schema()}), minimum=1),
            'selection_indices': _grid_array({'type': 'integer', 'minimum': 0})}), minimum=1),
        'qualifications': _grid_array({'enum': ['reporting_columns_not_physical_units',
            'physical_preparation_count_unknown', 'published_estimator_identity_unknown',
            'no_product_specific_rate_conversion', 'no_Vmax_to_kcat_conversion']})})


def _grid_exact(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _grid_quantity(witness, origin):
    """Preserve source missingness, limits, formula caches and native errors."""
    token = witness['raw_value']; text = (witness['value'] or '').strip()
    status, reason, exact, limit, bound = 'unsupported_cell', 'numeric_cell_type_required', None, None, 'none'
    grammar = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
    if witness['formula'] is not None: reason = 'formula_measurement_unsupported'
    elif witness['error'] is not None: reason = 'source_cell_error'
    elif witness['cell_type'] == 'e': reason = 'source_error_cell'
    elif not text: status, reason = 'missing', 'source_measurement_unavailable'
    elif witness['cell_type'] == 'n':
        if isinstance(token, str) and re.fullmatch(grammar, token):
            exact = _grid_exact(Fraction(token)); status, reason = 'observed', None
        else: reason = 'invalid_numeric_lexeme'
    elif text.casefold() in ('nd', 'not detected'):
        status, reason = 'not_detected', 'nondetection_without_point'
    else:
        match = re.fullmatch(r'(<=|>=|<|>|≤|≥)\s*(' + grammar + ')', text)
        if match:
            status, reason, bound = 'censored', 'censored_measurement', match[1]
            limit = _grid_exact(Fraction(match[2]))
    return {'measurement_key': identity('reported_grid_measurement', {key: witness[key] for key in
            ('artifact_ref', 'member', 'cell')}),
        'status': status, 'unavailable_reason': reason, 'bound': bound,
        'exact_value': exact, 'exact_limit': limit, 'origin': origin, 'witness': deepcopy(witness)}


def _grid_layout(args):
    """Complete aliases may repeat; incompatible coordinate reuse is rejected."""
    curves, curve_map = [], []
    seen = {}
    for index, selected in enumerate(args['curves']):
        cell = selected['header']['cell']
        if cell in seen:
            ordinal = seen[cell]
            if curves[ordinal]['selection']['header'] != selected['header']:
                _fail('grid_conflicting_curve_alias', 'curves')
            curves[ordinal]['indices'].append(index)
        else:
            ordinal = len(curves); seen[cell] = ordinal
            curves.append({'selection': selected, 'indices': [index]})
        curve_map.append(ordinal)
    columns = [_row_column(c['selection']['header']['cell'])[1] for c in curves]
    if len(set(columns)) != len(columns): _fail('grid_distinct_report_columns_required', 'curves')
    points, locations, owners = [], {}, {}
    concentration_column = None
    for index, selected in enumerate(args['points']):
        if len(selected['rate_cells']) != len(args['curves']): _fail('grid_curve_dimension_mismatch', 'points')
        row, column = _row_column(selected['concentration_cell'])
        concentration_column = concentration_column or column
        if column != concentration_column or column in columns:
            _fail('grid_concentration_column_mismatch', 'points')
        canonical = {}
        for original, address in enumerate(selected['rate_cells']):
            ordinal = curve_map[original]; header_row, header_column = _row_column(curves[ordinal]['selection']['header']['cell'])
            value_row, value_column = _row_column(address)
            if value_row != row or value_column != header_column or row <= header_row:
                _fail('grid_row_column_association_mismatch', 'points')
            if ordinal in canonical and canonical[ordinal] != address:
                _fail('grid_conflicting_curve_alias', 'points')
            canonical[ordinal] = address
            meaning = (selected['concentration_cell'], curves[ordinal]['selection']['header']['cell'])
            if address in owners and owners[address] != meaning:
                _fail('grid_incompatible_value_cell_reuse', 'points')
            owners[address] = meaning
        rates = [canonical[j] for j in range(len(curves))]
        key = selected['concentration_cell']
        if key in locations:
            previous = points[locations[key]]
            if previous['rates'] != rates: _fail('grid_conflicting_point_alias', 'points')
            previous['indices'].append(index)
        else:
            locations[key] = len(points)
            points.append({'cell': key, 'rates': rates, 'indices': [index]})
    return curves, points


def read_reported_rate_grid(content, arguments, *, artifact_ref, context_documents=()):
    """Read explicit original grid cells and authenticate selected context spans.

    Matching custody is not proof of a selected scientific interpretation.
    Host context bytes are never parsed into measured numeric operands.
    """
    args = deepcopy(arguments); validate_schema(args, reported_rate_grid_population_schema())
    curves, points = _grid_layout(args)
    digest = hashlib.sha256(content).hexdigest()
    if artifact_ref != 'artifact_' + digest: _fail('source_artifact_hash_mismatch', 'artifact_ref')
    documents = {}
    for doc in context_documents:
        if not isinstance(doc, dict) or set(doc) != {'source_ref', 'artifact_ref', 'content'} or not isinstance(doc['content'], bytes):
            _fail('grid_closed_context_document_required', 'context_documents')
        if doc['artifact_ref'] != 'artifact_' + hashlib.sha256(doc['content']).hexdigest():
            _fail('grid_context_artifact_hash_mismatch', 'context_documents')
        key = (doc['source_ref'], doc['artifact_ref'])
        if key in documents and documents[key] != doc['content']: _fail('grid_context_identity_conflict', 'context_documents')
        documents[key] = doc['content']
    wanted = {args[name]['cell'] for name in ('panel', 'subject', 'native_rate_label')}
    wanted.update(c['selection']['header']['cell'] for c in curves)
    for point in points: wanted.update([point['cell'], *point['rates']])
    selectors = [args['rate_unit']['witness'], args['concentration_unit']['witness'],
                 *args['endpoint_relationship']['witnesses'], *args['curve_sampling']['witnesses']]
    wanted.update(w['cell'] for w in selectors if w is not None and w['kind'] == 'xlsx_label')
    workbook = None
    try:
        workbook = Workbook(io.BytesIO(content)); layout = workbook.layout()
        selected = [s for s in layout['sheets'] if s['name'] == args['worksheet']]
        if len(selected) != 1 or not selected[0]['available']: _fail('xlsx_available_unique_worksheet_required', 'worksheet')
        member = selected[0]['worksheet_part']
        with workbook.open(member) as stream: raw = stream.read()
        cells = {}
        with sqlite3.connect(':memory:') as connection:
            failure = workbook.index_strings(connection, layout['shared_strings_part']) or layout.get('shared_strings_failure')
            if failure: _fail(failure['code'], 'shared_strings')
            for element in ET.fromstring(raw).iter():
                if _tag(element) == 'c' and element.get('r') in wanted:
                    address = element.get('r')
                    if address in cells: _fail('xlsx_ambiguous_cell', 'cell.' + address)
                    cells[address] = workbook.cell(element, connection)
    except (zipfile.BadZipFile, ET.ParseError, KeyError, ValueError) as error:
        if isinstance(error, ExperimentalContractError): raise
        raise ExperimentalContractError('xlsx_source_unreadable', 'source_ref') from error
    finally:
        if workbook is not None: workbook.close()
    custody = dict(source_ref=args['source_ref'], artifact_ref=artifact_ref, workbook_sha256=digest,
                   worksheet=args['worksheet'], member=member, member_sha256=hashlib.sha256(raw).hexdigest())
    def witness(address):
        value = cells.get(address, dict(cell_type='absent', value=None, raw_value=None, style_index=None,
            formula=None, value_is_formula_cache=False, error=None))
        return {**custody, 'cell': address, **{key: deepcopy(value[key]) for key in
            ('cell_type', 'value', 'raw_value', 'style_index', 'formula', 'value_is_formula_cache', 'error')}}
    def label(selected):
        value = witness(selected['cell'])
        if value['formula'] is not None or value['error'] is not None or value['cell_type']=='e' or value['value'] != selected['expected_text']:
            _fail('source_label_witness_mismatch', 'cell.' + selected['cell'])
        return value
    retained_context = []
    for selected in selectors:
        if selected is None: continue
        if selected['kind'] == 'xlsx_label': label(selected)
        else:
            raw_context = documents.get((selected['source_ref'], selected['artifact_ref']))
            if raw_context is None: _fail('grid_context_document_required', 'context_documents')
            if not 0 <= selected['start'] < selected['end'] <= len(raw_context) or raw_context[selected['start']:selected['end']] != selected['quote'].encode():
                _fail('grid_context_span_mismatch', 'context_documents')
        if selected not in retained_context: retained_context.append(deepcopy(selected))
    concentration = args['concentration_unit']
    if (concentration['code'] == 'unknown') != (concentration['witness'] is None):
        _fail('grid_concentration_unit_witness_required', 'concentration_unit')
    sampling = args['curve_sampling']
    if sampling['status'] in ('supported', 'stipulated_sensitivity'):
        if sampling['assumption'] != 'iid_reported_curve_vectors' or not sampling['witnesses']:
            _fail('grid_explicit_iid_model_provenance_required', 'curve_sampling')
        if sampling['status'] == 'supported' and sampling['source_claim'] != 'iid_reporting_vectors_supported':
            _fail('grid_supported_sampling_claim_required', 'curve_sampling')
        if sampling['status'] == 'stipulated_sensitivity' and sampling['source_claim'] == 'iid_reporting_vectors_supported':
            _fail('grid_stipulated_model_is_not_source_claim', 'curve_sampling')
    origin = 'synthetic' if args['source_kind'] == 'synthetic_fixture' else 'reported'
    result_curves = [{'curve_key': identity('reported_grid_curve', {'artifact_ref': artifact_ref, 'member': member,
        'header_cell': c['selection']['header']['cell']}), 'header': label(c['selection']['header']),
        'selection_indices': c['indices']} for c in curves]
    result_points = []
    for point in points:
        result_points.append({'point_key': identity('reported_grid_point', {'artifact_ref': artifact_ref,
            'member': member, 'concentration_cell': point['cell']}),
            'concentration': _grid_quantity(witness(point['cell']), origin),
            'entries': [{'curve_key': c['curve_key'], 'representation_key': identity('reported_grid_representation',
                {'source_ref': args['source_ref'], 'point': point['cell'], 'header': c['header']['cell']}),
                'quantity': _grid_quantity(witness(address), origin)} for c, address in zip(result_curves, point['rates'])],
            'selection_indices': point['indices']})
    result = dict(version=GRID_INPUT_VERSION, original_arguments=args, custody=custody,
        meanings={name: label(args[name]) for name in ('panel', 'subject', 'native_rate_label')},
        context_witnesses=retained_context, curves=result_curves, points=result_points,
        qualifications=['reporting_columns_not_physical_units', 'physical_preparation_count_unknown',
            'published_estimator_identity_unknown', 'no_product_specific_rate_conversion', 'no_Vmax_to_kcat_conversion'])
    validate_reported_rate_grid_extraction(result)
    return result


def _grid_validate_unit_mapping(selected, family):
    if selected['code']=='unknown':return
    w=selected['witness']
    if w is None:_fail('grid_unit_meaning_witness_required',family)
    text=(w['expected_text'] if w['kind']=='xlsx_label' else w['quote']).replace('μ','u').replace('µ','u').replace('−','-').replace('⁻¹','-1')
    if family=='rate_unit':
        matches=list(re.finditer(r'(?<![A-Za-z])((?:n|m|u)mol)\s*(?:/\s*min|(?:min)\s*(?:\^?\s*-1))(?![A-Za-z0-9])',text))
        for match in matches:
            tail=text[match.end():]
            if re.match(r'\s*(?:/|per\s|(?:mg|g|mL|L|min|s)\s*(?:\^?\s*-1))',tail):
                _fail('grid_unit_spelling_unsupported',family)
        units={match[1]+'/min' for match in matches}
    else:
        matches=list(re.finditer(r'(?<![A-Za-z])(?:M|mM|uM|nM)(?![A-Za-z])',text))
        if any(re.match(r'\s*/',text[m.end():]) for m in matches):_fail('grid_unit_spelling_unsupported',family)
        units={m[0] for m in matches}
    if len(units)>1:_fail('grid_unit_meaning_ambiguous',family)
    if not units:_fail('grid_unit_spelling_unsupported',family)
    if selected['code'] not in units:_fail('grid_unit_code_witness_mismatch',family)


def _grid_validate_meanings(args):
    concentration=args['concentration_unit'];sampling=args['curve_sampling']
    _grid_validate_unit_mapping(args['rate_unit'],'rate_unit')
    _grid_validate_unit_mapping(concentration,'concentration_unit')
    if (concentration['code']=='unknown') != (concentration['witness'] is None):
        _fail('grid_concentration_unit_witness_required','concentration_unit')
    if sampling['status'] in ('supported','stipulated_sensitivity'):
        if sampling['assumption']!='iid_reported_curve_vectors' or not sampling['witnesses']:
            _fail('grid_explicit_iid_model_provenance_required','curve_sampling')
        if sampling['status']=='supported' and sampling['source_claim']!='iid_reporting_vectors_supported':
            _fail('grid_supported_sampling_claim_required','curve_sampling')
        if sampling['status']=='stipulated_sensitivity' and sampling['source_claim']=='iid_reporting_vectors_supported':
            _fail('grid_stipulated_model_is_not_source_claim','curve_sampling')


def validate_reported_rate_grid_extraction(extraction):
    """Validate the retained scalar operands and coordinate/identity relationships.

    Artifact byte authentication is performed by the reader and future storage;
    this pure validation does not reacquire/reinterpret the original source.
    """
    validate_schema(extraction, reported_rate_grid_extraction_schema())
    args = extraction['original_arguments']; _grid_validate_meanings(args); curves, points = _grid_layout(args)
    custody = extraction['custody']; artifact = custody['artifact_ref']; member = custody['member']
    selected_context=[]
    for w in [args['rate_unit']['witness'],args['concentration_unit']['witness'],*args['endpoint_relationship']['witnesses'],*args['curve_sampling']['witnesses']]:
        if w is not None and w not in selected_context:selected_context.append(w)
    if extraction['context_witnesses']!=selected_context:_fail('grid_detached_context_mismatch','context_witnesses')
    if artifact != 'artifact_' + custody['workbook_sha256'] or custody['source_ref'] != args['source_ref'] or custody['worksheet'] != args['worksheet']:
        _fail('grid_detached_custody_mismatch', 'extraction')
    if len(curves) != len(extraction['curves']) or len(points) != len(extraction['points']):
        _fail('grid_detached_roster_mismatch', 'extraction')
    def check(w, cell):
        if w['cell'] != cell or any(w[k] != v for k, v in custody.items()) or w['value_is_formula_cache'] != (w['formula'] is not None): _fail('grid_detached_witness_mismatch', 'extraction')
    for name in ('panel', 'subject', 'native_rate_label'):
        w = extraction['meanings'][name]; check(w, args[name]['cell'])
        if w['cell_type']=='e' or w['value'] != args[name]['expected_text'] or w['formula'] is not None or w['error'] is not None:
            _fail('grid_detached_label_mismatch', name)
    for c, selected in zip(extraction['curves'], curves):
        check(c['header'], selected['selection']['header']['cell'])
        if c['header']['formula'] is not None or c['header']['error'] is not None or c['header']['cell_type']=='e' or c['header']['value'] != selected['selection']['header']['expected_text'] or c['selection_indices'] != selected['indices'] or c['curve_key'] != identity('reported_grid_curve',
                {'artifact_ref': artifact, 'member': member, 'header_cell': c['header']['cell']}):
            _fail('grid_detached_curve_mismatch', 'curves')
    origin = 'synthetic' if args['source_kind'] == 'synthetic_fixture' else 'reported'
    for p, selected in zip(extraction['points'], points):
        if len(p['entries']) != len(curves) or p['selection_indices'] != selected['indices'] or p['point_key'] != identity('reported_grid_point',
                {'artifact_ref': artifact, 'member': member, 'concentration_cell': selected['cell']}):
            _fail('grid_detached_point_mismatch', 'points')
        quantities = [(p['concentration'], selected['cell'])]
        for entry, c, address in zip(p['entries'], extraction['curves'], selected['rates']):
            if entry['curve_key'] != c['curve_key'] or entry['representation_key'] != identity('reported_grid_representation',
                    {'source_ref': args['source_ref'], 'point': selected['cell'], 'header': c['header']['cell']}):
                _fail('grid_detached_entry_mismatch', 'points')
            quantities.append((entry['quantity'], address))
        for q, address in quantities:
            check(q['witness'], address)
            if q != _grid_quantity(q['witness'], origin): _fail('grid_detached_quantity_mismatch', 'points')
    return deepcopy(extraction)
