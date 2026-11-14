"""Read one Figure 2D CcCdP time point from the authors' original XLSX."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import re
import sqlite3

from .domain import ContractError, obj, validate_schema
from .spreadsheet_tools import Workbook

VERSION = 'a105_stoichiometric_balance_xlsx_selection_v1'
MEANS = {'g2_initial': 'B52', 'g2': 'B', 'g3': 'D', 'g4': 'F',
         'g5': 'H', 'g6': 'J', 'pi': 'N'}
SDS = {'g2_sd': 'C', 'g3_sd': 'E', 'g4_sd': 'G', 'g5_sd': 'I',
       'g6_sd': 'K', 'pi_sd': 'O'}
HEADERS = {'A': 'Time', 'B': 'G2', 'C': 'G2_Stdev', 'D': 'G3',
           'E': 'G3_Stdev', 'F': 'G4', 'G': 'G4_Stdev', 'H': 'G5',
           'I': 'G5_Stdev', 'J': 'G6', 'K': 'G6_Stdev', 'M': 'Time',
           'N': 'Pi', 'O': 'Pi_Stdev'}
CALIBRATION_MM = {'g2': ('2.5', '50'), 'g3': ('2.5', '15'),
                  'g4': ('2.5', '15'), 'g5': ('1', '7.5'), 'g6': ('1', '2.5')}
CALIBRATION_PATTERNS = (r'G2\s*\(2\.5\s*[–-]\s*50\s*mM\)',
    r'G3/G4\s*\(2\.5\s*[–-]\s*15\s*mM\)',
    r'G5\s*\(1\.0\s*[–-]\s*7\.5\s*mM\)',
    r'G6\s*\(1\.0\s*[–-]\s*2\.5\s*mM\)')
MODEL_PREMISE = 'The released phosphate equals the αGlc1-P converted and the glucosyl residues not accounted for in the soluble products are considered to be present as insoluble products.'


def stoichiometric_balance_population_schema():
    return obj({'version': {'const': VERSION}, 'source_ref': {'type': 'string', 'minLength': 1},
        'expected_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'sheet_name': {'const': 'Data'}, 'panel': {'const': 'D'},
        'row_number': {'type': 'integer', 'minimum': 53},
        'time_minutes': {'type': 'number', 'minimum': 0}})


def _cell(cells, address, *, numeric=True):
    cell = cells.get(address)
    if cell is None or cell.get('address') != address or cell.get('error') is not None:
        raise ContractError('stoichiometric_balance_required_cell_missing')
    if not numeric:
        return cell['value']
    if cell['cell_type'] not in ('n', None) or cell['raw_value'] is None or cell['value_is_formula_cache']:
        raise ContractError('stoichiometric_balance_literal_numeric_cell_required')
    try:
        value = Decimal(cell['raw_value'])
    except (InvalidOperation, ValueError) as error:
        raise ContractError('stoichiometric_balance_literal_numeric_cell_required') from error
    if not value.is_finite():
        raise ContractError('stoichiometric_balance_finite_cell_required')
    return {'address': address, 'raw_value': cell['raw_value'],
            'exact_decimal': str(value), 'value_origin': 'literal_numeric_cell'}


def _row_map(result):
    if not result['complete'] or result['total_matches'] is None or result['total_matches'] > 100:
        raise ContractError('stoichiometric_balance_complete_xlsx_rows_required')
    rows = {}
    for row in result['rows']:
        number = row['row_number']
        if number is None or number in rows:
            raise ContractError('stoichiometric_balance_unique_rows_required')
        rows[number] = {cell['address']: cell for cell in row['cells']}
    return rows


def read_stoichiometric_balance_inputs(selection, workbook_bytes):
    validate_schema(selection, stoichiometric_balance_population_schema())
    digest = sha256(workbook_bytes).hexdigest()
    if digest != selection['expected_sha256']:
        raise ContractError('stoichiometric_balance_workbook_hash_mismatch')
    try:
        book = Workbook(BytesIO(workbook_bytes))
        try:
            layout = book.layout()
            sheets = {s['name']: s for s in layout['sheets'] if s['available']}
            if set(('Data', 'Metadata')) - set(sheets):
                raise ContractError('stoichiometric_balance_source_sheets_required')
            with sqlite3.connect(':memory:') as data_connection:
                data = book.rows(layout, data_connection, sheet_key=sheets['Data']['sheet_key'],
                                 offset=0, limit=100)
            with sqlite3.connect(':memory:') as metadata_connection:
                metadata = book.rows(layout, metadata_connection, sheet_key=sheets['Metadata']['sheet_key'],
                                     offset=0, limit=40)
        finally:
            book.close()
    except (OSError, ValueError, sqlite3.Error) as error:
        raise ContractError('stoichiometric_balance_xlsx_read_failed') from error
    data_rows, meta_rows = _row_map(data), _row_map(metadata)
    row_number = selection['row_number']
    if row_number not in data_rows or not 53 <= row_number or row_number <= 52:
        raise ContractError('stoichiometric_balance_selected_row_missing')
    if (_cell(data_rows[50], 'A50', numeric=False) != 'Experiment D'
            or _cell(meta_rows[3], 'F3', numeric=False) != 'Experiment D'):
        raise ContractError('stoichiometric_balance_panel_mismatch')
    for column, label in HEADERS.items():
        if _cell(data_rows[51], column + '51', numeric=False) != label:
            raise ContractError('stoichiometric_balance_header_mismatch')
    zero = {column: _cell(data_rows[52], column + '52') for column in ('A', 'M')}
    if any(Decimal(cell['exact_decimal']) != 0 for cell in zero.values()):
        raise ContractError('stoichiometric_balance_zero_time_mismatch')
    baseline = {role: _cell(data_rows[52], column + '52')
        for role, column in (('g3', 'D'), ('g4', 'F'), ('g5', 'H'), ('g6', 'J'), ('pi', 'N'))}
    if any(Decimal(cell['exact_decimal']) != 0 for cell in baseline.values()):
        raise ContractError('stoichiometric_balance_nonzero_initial_product_or_pi')
    times = {column: _cell(data_rows[row_number], column + str(row_number)) for column in ('A', 'M')}
    if any(Decimal(cell['exact_decimal']) != Decimal(str(selection['time_minutes'])) for cell in times.values()):
        raise ContractError('stoichiometric_balance_selected_time_mismatch')
    values = {'g2_initial': _cell(data_rows[52], 'B52')}
    for role, column in MEANS.items():
        if role != 'g2_initial':
            values[role] = _cell(data_rows[row_number], column + str(row_number))
    for role, column in SDS.items():
        values[role] = _cell(data_rows[row_number], column + str(row_number))
        if Decimal(values[role]['exact_decimal']) < 0:
            raise ContractError('stoichiometric_balance_negative_reported_sd')
    conditions = {}
    expected = {'F4': ('aGlc1-P', 'mM'), 'F5': ('Cellobiose (G2)', 'mM'),
        'F6': ('Cellodextrin phosphorylase from Clostridium cellulosi', 'U/mL'),
        'F7': ('MES buffer', 'mM'), 'F8': ('pH', None), 'F9': ('Temperature', '°C')}
    for address, (label, unit) in expected.items():
        number = int(address[1:])
        if (_cell(meta_rows[number], 'A' + str(number), numeric=False) != label
                or _cell(meta_rows[number], 'B' + str(number), numeric=False) != unit):
            raise ContractError('stoichiometric_balance_metadata_label_mismatch')
        if label == 'pH':
            # The authors stored this metadata value as a shared-string token.
            token = _cell(meta_rows[number], address, numeric=False)
            try:
                value = Decimal(token)
            except (TypeError, InvalidOperation) as error:
                raise ContractError('stoichiometric_balance_metadata_numeric_required') from error
            conditions[label] = {'value': {'address': address, 'raw_value': token,
                'exact_decimal': str(value), 'value_origin': 'source_text_numeric'}, 'unit': unit}
        else:
            conditions[label] = {'value': _cell(meta_rows[number], address), 'unit': unit}
    if Decimal(conditions['Cellobiose (G2)']['value']['exact_decimal']) != Decimal(values['g2_initial']['exact_decimal']):
        raise ContractError('stoichiometric_balance_initial_g2_mismatch')
    calibration_text = _cell(meta_rows[22], 'A22', numeric=False)
    if not isinstance(calibration_text, str) or not all(re.search(pattern, calibration_text) for pattern in CALIBRATION_PATTERNS):
        raise ContractError('stoichiometric_balance_calibration_source_missing')
    for analyte, bounds in CALIBRATION_MM.items():
        value = Decimal(values[analyte]['exact_decimal'])
        if not Decimal(bounds[0]) <= value <= Decimal(bounds[1]):
            raise ContractError('stoichiometric_balance_outside_calibration_range')
    premise = _cell(meta_rows[29], 'A29', numeric=False)
    if premise != MODEL_PREMISE:
        raise ContractError('stoichiometric_balance_model_premise_missing')
    method = _cell(meta_rows[23], 'A23', numeric=False)
    duplicates = _cell(meta_rows[16], 'A16', numeric=False)
    if not isinstance(method, str) or 'colorimetric assay' not in method or duplicates != 'Each reaction was carried out in duplicates.':
        raise ContractError('stoichiometric_balance_method_context_missing')
    return {'version': 'a105_stoichiometric_balance_extraction_v1',
        'source_ref': selection['source_ref'], 'workbook_sha256': digest,
        'sheet_name': 'Data', 'sheet_key': sheets['Data']['sheet_key'],
        'metadata_sheet_key': sheets['Metadata']['sheet_key'], 'panel': 'D',
        'row_number': row_number, 'time_minutes': selection['time_minutes'],
        'values': values, 'initial_product_and_pi_entries': baseline,
        'initial_baseline_status': 'source_printed_zero_measurement_and_detection_limit_unestablished',
        'conditions': conditions,
        'assayed_molecule': 'Cellodextrin phosphorylase from Clostridium cellulosi',
        'construct_status': 'not_reported_in_workbook',
        'expression_host': None,
        'calibration_ranges_mM': {k: list(v) for k, v in CALIBRATION_MM.items()},
        'calibration_source_cell': 'Metadata!A22',
        'model_premise': {'text': premise, 'source_cell': 'Metadata!A29',
                          'meaning': 'source Pi-equals-converted-donor premise, interpreted conditionally as one Pi per donor glucosyl transfer'},
        'pi_method': {'text': method, 'source_cell': 'Metadata!A23'},
        'replication': {'text': duplicates, 'source_cell': 'Metadata!A16',
                        'independent_preparation_count': None},
        'matched_no_enzyme_arm': None, 'joint_covariance': None,
        'molecule_specific_attribution': None}


__all__ = ['VERSION', 'MEANS', 'SDS', 'CALIBRATION_MM',
           'stoichiometric_balance_population_schema', 'read_stoichiometric_balance_inputs']
