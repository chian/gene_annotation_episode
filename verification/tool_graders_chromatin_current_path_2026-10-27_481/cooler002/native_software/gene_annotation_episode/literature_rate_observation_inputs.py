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
