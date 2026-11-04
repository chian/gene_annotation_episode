"""Selected XLSX data access; no biological interpretation or episode decisions.

The worker resolves workbook relationships and shared strings, preserves native
cell identities and formula/cache distinctions, and uses disk for shared strings.
Caller limits are enforced by the existing protected native lifecycle.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import posixpath
import sqlite3
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from .acquisition import AcquisitionError
from .document_tools import DocumentOutput
from .local_jobs import LocalJobPolicy, run_local_job


VERSION = 'xlsx_selected_cells_v1'


def _tag(element):
    return element.tag.rsplit('}', 1)[-1]


def _child(element, name):
    return next((child for child in element if _tag(child) == name), None)


def _text(element):
    # Rich text runs contribute visible text; phonetic annotations do not.
    return ''.join(child.text or '' for part in element
        for child in ([part] if _tag(part) == 't' else list(part) if _tag(part) == 'r' else [])
        if _tag(child) == 't')


def _part(parent, target):
    value = posixpath.normpath(posixpath.join(posixpath.dirname(parent), target)
        if not target.startswith('/') else target.lstrip('/'))
    if value == '..' or value.startswith('../'):
        raise ValueError('xlsx_relationship_outside_package')
    return value


class Workbook:
    def __init__(self, path):
        self.archive = zipfile.ZipFile(path)

    def close(self):
        self.archive.close()

    def open(self, name):
        matches = [entry for entry in self.archive.infolist() if entry.filename == name]
        if len(matches) != 1:
            raise ValueError('xlsx_missing_or_ambiguous_package_part')
        return self.archive.open(matches[0])

    def xml(self, name):
        with self.open(name) as stream:
            return ET.parse(stream).getroot()

    def layout(self):
        roots = [row for row in self.xml('_rels/.rels')
            if row.get('Type', '').endswith('/officeDocument') and row.get('TargetMode') != 'External']
        if len(roots) != 1:
            raise ValueError('xlsx_workbook_relationship_required')
        workbook_part = _part('', roots[0].get('Target', ''))
        directory, filename = posixpath.split(workbook_part)
        relationships = {}
        for row in self.xml(posixpath.join(directory, '_rels', filename+'.rels')):
            relationships.setdefault(row.get('Id'), []).append(row)
        workbook = self.xml(workbook_part)
        sheets, shared_strings, strings_failure = [], None, None
        string_candidates = [relationship for group in relationships.values() for relationship in group
            if relationship.get('Type', '').endswith('/sharedStrings')]
        if len(string_candidates) > 1:
            strings_failure = {'code': 'xlsx_shared_strings_relationship_ambiguous'}
        elif string_candidates:
            relationship = string_candidates[0]
            if (not relationship.get('Id') or len(relationships[relationship.get('Id')]) != 1
                    or relationship.get('TargetMode') == 'External'):
                strings_failure = {'code': 'xlsx_shared_strings_relationship_unavailable'}
            else:
                shared_strings = _part(workbook_part, relationship.get('Target', ''))
        for sheet in workbook.iter():
            if _tag(sheet) != 'sheet':
                continue
            key = next((value for name, value in sheet.attrib.items()
                if name.rsplit('}', 1)[-1] == 'id'), None)
            candidates = relationships.get(key, []) if key else []
            relationship = candidates[0] if len(candidates) == 1 else None
            available = (relationship is not None
                and relationship.get('TargetMode') != 'External'
                and relationship.get('Type', '').endswith('/worksheet'))
            part = _part(workbook_part, relationship.get('Target', '')) if available else None
            sheets.append({'sheet_key': key, 'name': sheet.get('name'),
                'native_sheet_id': sheet.get('sheetId'), 'state': sheet.get('state', 'visible'),
                'worksheet_part': part, 'available': available,
                'failure_code': (None if available else 'xlsx_relationship_id_ambiguous'
                    if len(candidates) > 1 else 'xlsx_worksheet_relationship_unavailable')})
        properties = next((row for row in workbook if _tag(row) == 'workbookPr'), None)
        dates = '1904' if properties is not None and properties.get('date1904') in ('1', 'true') else '1900'
        return {'workbook_part': workbook_part, 'sheets': sheets,
            'shared_strings_part': shared_strings, 'shared_strings_failure': strings_failure,
            'date_system': dates}

    def index_strings(self, connection, part):
        connection.execute('CREATE TABLE strings(ordinal INTEGER PRIMARY KEY,value TEXT NOT NULL)')
        if part is None:
            return None
        failure = None
        try:
            with self.open(part) as stream:
                parser = ET.iterparse(stream, events=('start', 'end'))
                _, root = next(parser)
                ordinal = 0
                for event, element in parser:
                    if event == 'end' and _tag(element) == 'si':
                        connection.execute('INSERT INTO strings VALUES(?,?)', (ordinal, _text(element)))
                        ordinal += 1
                        root.clear()
        except ET.ParseError as error:
            failure = _xml_failure(part, error)
        connection.commit()
        return failure

    @staticmethod
    def cell(cell, connection):
        raw = _child(cell, 'v')
        raw = raw.text if raw is not None else None
        kind = cell.get('t', 'n')
        value, error = raw, None
        if kind == 's' and raw is not None:
            try:
                row = connection.execute('SELECT value FROM strings WHERE ordinal=?', (int(raw),)).fetchone()
                if row is None:
                    raise ValueError()
                value = row[0]
            except ValueError:
                value, error = None, 'xlsx_shared_string_reference_unresolved'
        elif kind == 'inlineStr':
            inline = _child(cell, 'is')
            value = _text(inline) if inline is not None else ''
        formula = _child(cell, 'f')
        return {'address': cell.get('r'), 'cell_type': kind, 'value': value,
            'raw_value': raw, 'style_index': cell.get('s'),
            'formula': None if formula is None else {'text': formula.text, 'attributes': dict(formula.attrib)},
            'value_is_formula_cache': formula is not None, 'error': error}

    def rows(self, layout, connection, *, sheet_key, offset, limit, where=None, header_row=None):
        if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 0:
            raise ValueError('xlsx_nonnegative_page_required')
        if header_row is not None and (type(header_row) is not int or header_row < 1):
            raise ValueError('xlsx_positive_header_row_required')
        if where is not None and (set(where) != {'column', 'match', 'value', 'case_sensitive'}
                or where['match'] not in {'equals', 'contains'} or not isinstance(where['value'], str)
                or type(where['case_sensitive']) is not bool
                or where['column'] is not None and (not isinstance(where['column'], str)
                    or not where['column'] or any(char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for char in where['column']))):
            raise ValueError('xlsx_literal_cell_filter_required')
        selected = [sheet for sheet in layout['sheets'] if sheet['sheet_key'] == sheet_key]
        if len(selected) != 1 or not selected[0]['available']:
            raise ValueError('xlsx_available_sheet_key_required')
        sheet = selected[0]
        strings_failure = self.index_strings(connection, layout['shared_strings_part']) or layout.get('shared_strings_failure')
        rows, matched, header, errors, cell_errors = [], 0, None, [], 0
        row_errors_count, ordinal = 0, 0
        failures = [strings_failure] if strings_failure else []
        data = None
        try:
            with self.open(sheet['worksheet_part']) as stream:
                for event, element in ET.iterparse(stream, events=('start', 'end')):
                    name = _tag(element)
                    if event == 'start' and name == 'sheetData':
                        data = element
                    if event != 'end' or name != 'row':
                        continue
                    ordinal += 1
                    cells = [self.cell(cell, connection) for cell in element if _tag(cell) == 'c']
                    raw_number = element.get('r')
                    number, row_error = None, None
                    if raw_number is not None:
                        try:
                            number = int(raw_number)
                            if number < 1:
                                raise ValueError()
                        except ValueError:
                            number, row_error = None, 'xlsx_row_number_invalid'
                    row = {'row_number': number, 'row_number_raw': raw_number,
                        'row_ordinal': ordinal, 'row_error': row_error, 'cells': cells}
                    row_errors = [{'row_number': row['row_number'], 'address': cell['address'], 'code': cell['error']}
                        for cell in cells if cell['error'] is not None]
                    cell_errors += len(row_errors)
                    if row_error:
                        row_errors_count += 1
                        row_errors.append({'row_ordinal': ordinal, 'row_number_raw': raw_number, 'code': row_error})
                    retained = False
                    if header_row is not None and row['row_number'] == header_row:
                        header, retained = row, True
                    if where is None or any(_matches(cell, where) for cell in cells):
                        if offset <= matched < offset+limit:
                            rows.append(row)
                            retained = True
                        matched += 1
                    # Keep errors for requested rows, plus a full scanned count.
                    # Do not materialize an unrequested archive of failed cells.
                    if retained:
                        errors.extend(row_errors)
                    element.clear()
                    if data is not None:
                        data.clear()
        except ET.ParseError as error:
            failures.append(_xml_failure(sheet['worksheet_part'], error))
        complete = not failures and cell_errors == 0 and row_errors_count == 0
        return {'sheet': sheet, 'date_system': layout['date_system'], 'header': header,
            'rows': rows, 'offset': offset, 'limit': limit, 'total_matches': matched if complete else None,
            'next_offset': offset+len(rows) if complete and offset+len(rows) < matched else None,
            'where': where, 'errors': errors, 'cell_error_count': cell_errors, 'row_error_count': row_errors_count,
            'parse_failures': failures, 'complete': complete,
            'status': 'completed' if complete else 'partial' if rows or header is not None else 'failed',
            'coordinate_system': 'original_xlsx_worksheet_row_and_cell_addresses',
            'numbers_and_dates': 'original_lexical_values_and_styles_not_reformatted',
            'formulas': 'original_formula_and_cached_value_not_recalculated'}


def _xml_failure(part, error):
    return {'code': 'xlsx_xml_parse_failed', 'package_part': part, 'xml_position': list(error.position)}


def _matches(cell, where):
    column = ''.join(letter for letter in (cell['address'] or '') if letter.isalpha())
    if where['column'] is not None and column != where['column']:
        return False
    if cell['value'] is None:
        return False
    actual, expected = cell['value'], where['value']
    if not where['case_sensitive']:
        actual, expected = actual.casefold(), expected.casefold()
    if where['match'] == 'equals':
        return actual == expected
    if where['match'] == 'contains':
        return expected in actual
    raise ValueError('xlsx_literal_match_operator_required')


def read_workbook(path, operation, arguments, scratch):
    workbook = Workbook(path)
    try:
        layout = workbook.layout()
        if operation == 'sheets':
            return layout
        if operation != 'rows':
            raise ValueError('xlsx_operation_unknown')
        with sqlite3.connect(Path(scratch)/'shared-strings.sqlite') as connection:
            return workbook.rows(layout, connection, **arguments)
    finally:
        workbook.close()


def xlsx_native(path, *, operation, arguments, job_limits, cancel_event=None, statistics=None):
    policy = LocalJobPolicy.from_config(job_limits)
    with tempfile.TemporaryDirectory(prefix='annotation-xlsx-') as directory:
        directory = Path(directory)
        request = directory/'request.json'
        output = directory/'output.json'
        request.write_text(json.dumps({'path': str(Path(path).resolve()), 'operation': operation,
            'arguments': arguments}))
        environment = {'PYTHONPATH': str(Path(__file__).resolve().parent.parent)
            +os.pathsep+os.environ.get('PYTHONPATH', '')}
        completed = run_local_job([sys.executable, '-m', 'gene_annotation_episode.spreadsheet_worker',
            str(request), str(output)], cwd=directory, policy=policy, env=environment,
            stdout_path=directory/'native.stdout', stderr_path=directory/'native.stderr', cancel_event=cancel_event,
            statistics=statistics)
        stdout, stderr = completed.stdout_path.read_bytes(), completed.stderr_path.read_bytes()
        if completed.returncode != 0:
            failure = json.loads(output.read_text()) if output.is_file() else {'code': 'xlsx_native_output_unavailable'}
            raise AcquisitionError(failure['code'], phase='native_execution', operational={
                'native': completed.metadata, 'native_returncode': completed.returncode,
                'exception_type': failure.get('exception_type'),
                'selection': arguments, 'operation': operation, 'detail': failure.get('detail')})
        content = output.read_bytes()
    return DocumentOutput({'operation': 'xlsx_'+operation, 'adapter_version': VERSION,
        'selection': arguments, 'job_limits': policy.to_dict(), 'local_jobs': {'work': completed.metadata},
        'returncode': 0, 'biological_interpretation': 'not_performed'}, content,
        'application/json', stdout, stderr)
