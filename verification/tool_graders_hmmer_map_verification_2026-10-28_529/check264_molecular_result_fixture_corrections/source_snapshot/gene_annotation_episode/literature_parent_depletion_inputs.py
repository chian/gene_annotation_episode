"""Read one original XLSX parent-removal row with the ordinary workbook reader.

The source labels identify reported arm estimates; this reader authenticates
their numeric cells, not the biochemical interpretation of disappearance.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import sqlite3

from .domain import ContractError, obj, validate_schema
from .spreadsheet_tools import Workbook

VERSION = 'a105_parent_depletion_xlsx_selection_v1'
HEADERS = {'A':'Time','B':'Bio','C':'Stdev1','D':'Ab','E':'Stdev2',
    'F':'inactive_enzyme','G':'Stdev3','I':'Compound','J':'Submix',
    'K':'Difference_dead_enzyme','L':'Difference_abio'}
VALUES = {'active':'B','active_sd':'C','abiotic':'D','abiotic_sd':'E',
    'inactive':'F','inactive_sd':'G','reported_active_minus_inactive':'K',
    'reported_active_minus_abiotic':'L'}


def parent_depletion_population_schema():
    text={'type':'string','minLength':1}
    return obj({'version':{'const':VERSION},'source_ref':text,
        'expected_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},
        'sheet_name':text,'compound':text,'submix':text,
        'time_hours':{'type':'integer','minimum':0}})


def _number(cell, address, *, allow_formula_cache=False):
    if cell is None or cell['address'] != address or cell['error'] is not None \
            or cell['cell_type'] not in ('n', None) or cell['raw_value'] is None \
            or cell['value_is_formula_cache'] and not allow_formula_cache:
        raise ContractError('parent_depletion_numeric_cell_required')
    try:
        value=Decimal(cell['raw_value'])
    except (InvalidOperation, ValueError) as error:
        raise ContractError('parent_depletion_numeric_cell_required') from error
    if not value.is_finite():
        raise ContractError('parent_depletion_finite_cell_required')
    return {'address':address,'raw_value':cell['raw_value'],'exact_decimal':str(value),
        'value_origin':'formula_cache' if cell['value_is_formula_cache'] else 'literal_numeric_cell',
        'formula':cell['formula']}


def read_parent_depletion_inputs(selection, workbook_bytes):
    validate_schema(selection,parent_depletion_population_schema())
    digest=sha256(workbook_bytes).hexdigest()
    if digest!=selection['expected_sha256']:
        raise ContractError('parent_depletion_workbook_hash_mismatch')
    try:
        workbook=Workbook(BytesIO(workbook_bytes))
        try:
            layout=workbook.layout()
            sheets=[s for s in layout['sheets'] if s['name']==selection['sheet_name'] and s['available']]
            if len(sheets)!=1:
                raise ContractError('parent_depletion_unique_sheet_required')
            with sqlite3.connect(':memory:') as connection:
                result=workbook.rows(layout,connection,sheet_key=sheets[0]['sheet_key'],offset=0,limit=32,
                    header_row=1,where={'column':'I','match':'equals','value':selection['compound'],
                        'case_sensitive':True})
        finally:
            workbook.close()
    except (OSError,ValueError,sqlite3.Error) as error:
        raise ContractError('parent_depletion_xlsx_read_failed') from error
    if not result['complete'] or result['total_matches'] is None or result['total_matches']>32 or result['header'] is None:
        raise ContractError('parent_depletion_complete_xlsx_row_required')
    header={c['address']:c for c in result['header']['cells']}
    for column,label in HEADERS.items():
        cell=header.get(column+'1')
        if cell is None or cell['value']!=label or cell['error'] is not None:
            raise ContractError('parent_depletion_header_mismatch')
    matches=[]
    for row in result['rows']:
        cells={c['address']:c for c in row['cells']}
        index=row['row_number']
        if index is None or cells.get('J'+str(index),{}).get('value')!=selection['submix']:
            continue
        if cells.get('A'+str(index),{}).get('raw_value')!=str(selection['time_hours']):
            continue
        matches.append((row,cells))
    if len(matches)!=1:
        raise ContractError('parent_depletion_unique_matching_row_required')
    row,cells=matches[0];index=row['row_number']
    values={role:_number(cells.get(column+str(index)),column+str(index),
        allow_formula_cache=role.startswith('reported_active_minus_')) for role,column in VALUES.items()}
    return {'version':'a105_parent_depletion_extraction_v1','source_ref':selection['source_ref'],
        'workbook_sha256':digest,'sheet_name':selection['sheet_name'],
        'sheet_key':result['sheet']['sheet_key'],'worksheet_part':result['sheet']['worksheet_part'],
        'row_number':index,'compound':selection['compound'],'submix':selection['submix'],
        'time_hours':selection['time_hours'],'values':values,
        'normalization_status':'source_relative_removal_denominator_raw_values_unavailable',
        'repetition_basis':'unknown','active_control_covariance':'unknown',
        'equal_mutant_protein_amount':'unknown','product_identity_for_studied_enzyme':'unknown'}


__all__=['VERSION','VALUES','parent_depletion_population_schema','read_parent_depletion_inputs']
