"""Small numerical fixtures. Symbolic439 identities are not native receipts."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import MappingProxyType

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / 'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json'


def record(key):
    return next(deepcopy(r['record']) for r in json.loads(ORACLE.read_text())['records'] if r['example_key'] == key)


def readonly(array):
    array.flags.writeable = False
    return array


def case(name='raw'):
    sheet, fixture = record(name + '.sheet'), record(name + '.tables')
    populations = {}
    for rows in fixture['populations']:
        key = rows['population_key']
        descriptors = {d['role']: d for d in sheet['data_tables'] if d['population_key'] == key}
        arrays = {'population_key': key}
        for role in ('bins', 'contacts', 'weights', 'cell_states', 'dense_values'):
            data = rows[role]
            if data is None:
                arrays[role] = None
                continue
            if role == 'bins':
                dtype = [(n, '<i8') for n in ('bin_id', 'chromosome_index', 'start_bp', 'end_bp')]
                values = [tuple(r[n] for n, _ in dtype) for r in data]
            elif role == 'weights':
                dtype = '<f8'
                values = [r['value']['value'] for r in data]
            else:
                spec = descriptors[role]['dtype_descriptor']
                dtype = [(r['name'], r['dtype']) for r in spec['fields']]
                values = [tuple(r[n]['value'] if n == 'value' else r[n] for n, _ in dtype) for r in data]
            arrays[role] = readonly(np.array(values, dtype=dtype))
        populations[key] = arrays
    return sheet, {'version': 'chromatin_contact_arrays_v1', 'populations': MappingProxyType(populations)}, record(name + '.selector')['parameters']


def replace_array(sheet, tables, role, value, key='p0'):
    arrays = tables['populations'][key]
    arrays[role] = readonly(value) if value is not None else None
    descriptor = next(d for d in sheet['data_tables'] if d['population_key'] == key and d['role'] == role)
    if value is not None:
        descriptor['shape'] = [len(value), 4] if role == 'bins' else list(value.shape)
        descriptor['row_count'] = len(value)
        if role != 'bins':
            descriptor['dtype_descriptor'] = ({'kind': 'structured', 'fields':
                [{'name': n, 'dtype': value.dtype[n].str} for n in value.dtype.names]}
                if value.dtype.names else {'kind': 'scalar', 'dtype': value.dtype.str})
    return arrays


def set_contact(sheet, tables, first, second, value):
    array = tables['populations']['p0']['contacts'].copy()
    if not isinstance(value, int):
        dtype = [(n, '<f8' if n == 'value' else array.dtype[n]) for n in array.dtype.names]
        array = array.astype(dtype)
    row = np.flatnonzero((array['bin1_id'] == first) & (array['bin2_id'] == second))[0]
    array[row]['value'] = value
    replace_array(sheet, tables, 'contacts', array)
    for pair in sheet['populations'][0]['pair_rows']:
        if sorted((pair['enhancer_bin_id'], pair['promoter_bin_id'])) == [first, second]:
            measurement = pair['raw_contact']
            if np.isfinite(value):
                measurement.update(value=value, state='observed', reason=None)
            else:
                measurement.update(value=None, state='failed', reason='native_value_nonfinite')


def insulation_case(adjacent):
    sheet, tables, parameters = case('insulation')
    n = len(adjacent) + 1
    p = sheet['populations'][0]
    p['bin_count'] = n
    p['selected_region']['end_bp'] = n * 10
    sheet['request']['populations'][0]['end_bp'] = n * 10
    sheet['native']['chromosomes'][0]['length_bp'] = n * 10
    bins = np.array([(i, 0, i * 10, (i + 1) * 10) for i in range(n)], dtype=tables['populations']['p0']['bins'].dtype)
    contacts = np.array([(i, j, adjacent[i] if j == i + 1 else 0, -1, k)
        for k, (i, j) in enumerate((i, j) for i in range(n) for j in range(i, n))],
        dtype=tables['populations']['p0']['contacts'].dtype)
    replace_array(sheet, tables, 'bins', bins)
    replace_array(sheet, tables, 'contacts', contacts)
    p['raw_cell_population'].update(directed_cells=n*n, unique_unordered_cells=n*(n+1)//2,
        stored_rows=len(contacts), explicit_zero_rows=int(np.count_nonzero(contacts['value'] == 0)),
        validated_observed_row_count=len(contacts))
    p['read_evidence']['required_native_row_ranges'][0]['end_row'] = len(contacts)
    return sheet, tables, parameters


def serialize_tables(sheet, tables):
    """Real retained canonical table encodings for C1's saved-data loader."""
    import hashlib
    streams = {}
    for descriptor in sheet['data_tables']:
        array = tables['populations'][descriptor['population_key']][descriptor['role']]
        if array is None:
            continue
        stream = io.BytesIO()
        if descriptor['role'] == 'bins':
            stream.write(('bin_id\tchromosome_index\tstart_bp\tend_bp\n' +
                ''.join('\t'.join(str(int(row[n])) for n in array.dtype.names) + '\n' for row in array)).encode())
        else:
            np.save(stream, array, allow_pickle=False)
        raw = stream.getvalue()
        digest = hashlib.sha256(raw).hexdigest()
        descriptor['file'] = {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(raw),
                              'format': 'chromatin_contact_tables_v1:' + descriptor['role']}
        stream.seek(0)
        streams[descriptor['table_key']] = stream
    return streams


def native_case(name='weighted', *, bed=None, assignments=None, raw_transform=None):
    """Parse440 actual serialized synthetic Cooler files using C1 production ports."""
    import hashlib
    from gene_annotation_episode.chromatin_cooler_inputs import read_cooler_contacts
    from gene_annotation_episode.chromatin_interaction_inputs import (
        parse_chromatin_elements, extract_chromatin_metadata, build_chromatin_sheet,
    )
    from gene_annotation_episode.chromatin_interaction_tables import open_chromatin_contact_tables
    request = record(name + '.request')
    filename = 'six-bin-all-full-windows.cool' if name == 'insulation' else 'four-bin-raw-weighted.cool'
    path = ROOT / 'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures' / filename
    raw = path.read_bytes()
    if raw_transform is not None:
        raw = raw_transform(raw)
    def identity(data, format):
        digest = hashlib.sha256(data).hexdigest()
        return {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': len(data), 'format': format}
    request['contact']['file'] = identity(raw, 'cooler_hdf5_v3')
    request['supplied_metadata']['reference']['assembly_label'] = None
    if request['elements'] is not None:
        bed = bed if bed is not None else b'chrA\t1\t2\tE\t0\t.\nchrA\t21\t22\tP\t0\t.\nchrA\t31\t32\tQ\t0\t.\n'
        request['elements']['file'] = identity(bed, 'bed_outer_span_v1')
        request['elements']['reference']['assembly_label'] = None
        if assignments is not None:
            request['elements']['assignments'] = assignments
    produced = {(p['population_key'], role): io.BytesIO() for p in request['populations']
                for role in ('bins','contacts','weights','cell_states','dense_values')}
    extraction = read_cooler_contacts(io.BytesIO(raw), spec=request['contact'], normalization=request['normalization'],
                                      populations=request['populations'], table_streams=produced)
    descriptors, streams = [], {}
    for draft in extraction['table_drafts']:
        data = produced[(draft['population_key'],draft['role'])].getvalue()
        descriptors.append(draft | {'file': identity(data, 'chromatin_contact_tables_v1:' + draft['role'])
            if draft['availability'] == 'present' else None})
        if draft['availability'] == 'present':
            streams[draft['table_key']] = io.BytesIO(data)
    elements = parse_chromatin_elements(bed, spec=request['elements']) if request['elements'] is not None else None
    metadata = extract_chromatin_metadata(request=request, native=extraction, supplied=request['supplied_metadata'], elements=elements)
    with open_chromatin_contact_tables(descriptors, streams=streams) as arrays:
        sheet = build_chromatin_sheet(request=request, contacts=extraction, elements=elements, metadata=metadata,
                                     tables=descriptors, table_views=arrays)
    return sheet, streams, record(name + '.selector')['parameters']
