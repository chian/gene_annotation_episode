"""Build an explicit new source catalog without rewriting historical libraries."""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile

from .a102_structural_evidence import VERSION, merged_entry
from .domain import canonical
from .scientific_process_library import (_load, _within, _validate_entry,
    _validate_rows, _validate_source_index)


def prepare_catalog(source_directory, destination):
    """Materialize a run-owned nine-axis catalog from the selected publication.

    Callers keep destination beneath their run directory. All unaffected entry
    bytes are preserved. Source evidence is instruction provenance, never new
    scientific evidence. A pre-existing, different destination is an error.
    """
    source, destination = Path(source_directory).resolve(), Path(destination).resolve()
    if (destination == source or source.is_relative_to(destination)
            or destination.is_relative_to(source)):
        raise ValueError('a102_catalog_destination_must_not_replace_source')
    index, index_bytes = _load(source / 'index.json', 'a102_catalog_index_invalid')
    _validate_source_index(index)
    table, table_bytes = _load(source / 'option_sources.json', 'a102_catalog_sources_invalid')
    if set(table) != {'meaning', 'rows'} or not isinstance(table['meaning'], str):
        raise ValueError('a102_catalog_sources_invalid')
    entries, files, source_digests = {}, {}, {}
    headers = {row['id']: row for row in index['entries']}
    axes = {row['id'] for row in index['entries'] if row['slot'] == 'evidence_axis'}
    if axes != {'A101', 'A102', 'A103', 'A104', 'A105', 'A106', 'A107', 'A108', 'A110', 'A111'}:
        raise ValueError('a102_catalog_requires_unmerged_axis_publication')
    if not isinstance(table['rows'], list) or any(not isinstance(row, dict)
            or row.get('option_id') not in headers for row in table['rows']):
        raise ValueError('a102_catalog_sources_invalid')
    for key, header in headers.items():
        entry, data = _load(_within(source, header['detail_path'], 'a102_catalog_entry_missing'),
            'a102_catalog_entry_invalid')
        _validate_entry(entry)
        if any(entry[field] != header[field] for field in ('id', 'slot', 'name', 'description')):
            raise ValueError('a102_catalog_header_mismatch')
        rows = [row for row in table['rows'] if row['option_id'] == key]
        _validate_rows(rows, entry, header['source_evidence_ids'])
        entries[key] = entry
        files[header['detail_path']] = data
        source_digests[header['detail_path']] = hashlib.sha256(data).hexdigest()
    updated = merged_entry(entries['A102'], entries['A111'])
    index = deepcopy(index)
    index['entries'] = [row for row in index['entries'] if row['id'] != 'A111']
    index['status'] = 'Nine evidence axes; A102 owns comparative and experimental structural evidence. ' + VERSION
    table = deepcopy(table)
    rows = [row for row in table['rows'] if row['option_id'] != 'A111']
    a102 = next(row for row in index['entries'] if row['id'] == 'A102')
    a102.update(name=updated['name'], description=updated['description'])
    old_ids = list(a102['source_evidence_ids'])
    links = []
    ordinal = max(int(value.rsplit('-', 1)[1]) for value in old_ids) if old_ids else 0
    for row in table['rows']:
        if row['option_id'] != 'A111':
            continue
        ordinal += 1
        new_id = f'E-A102-{ordinal:04d}'
        links.append({'original_evidence_id': row['evidence_id'], 'new_evidence_id': new_id})
        rows.append({**row, 'evidence_id': new_id, 'option_id': 'A102'})
        a102['source_evidence_ids'].append(new_id)
    table['rows'] = rows
    table['meaning'] += ' A111 instruction provenance is retained under A102 with an explicit migration map.'
    del files[headers['A111']['detail_path']]
    files[headers['A102']['detail_path']] = (canonical(updated) + '\n').encode()
    for slot in index['slots']:
        slot['count'] = sum(row['slot'] == slot['slot'] for row in index['entries'])
        files[slot['catalog']] = (canonical({'slot': slot['slot'], 'options': [
            row for row in index['entries'] if row['slot'] == slot['slot']]}) + '\n').encode()
    _validate_source_index(index)
    _validate_rows([row for row in rows if row['option_id'] == 'A102'], updated, a102['source_evidence_ids'])
    files['index.json'] = (canonical(index) + '\n').encode()
    files['option_sources.json'] = (canonical(table) + '\n').encode()
    files['a102_merge_provenance.json'] = (canonical({'version': VERSION,
        'source_index_sha256': hashlib.sha256(index_bytes).hexdigest(),
        'source_table_sha256': hashlib.sha256(table_bytes).hexdigest(),
        'original_entries_sha256': source_digests, 'retired_selection': 'A111',
        'instruction_source_links': links,
        'legacy_records': 'Unchanged; no scientific result or formula migration.'}) + '\n').encode()
    if destination.exists():
        if (not destination.is_dir() or any(not (destination / name).is_file()
                or (destination / name).read_bytes() != data for name, data in files.items())
                or {str(path.relative_to(destination)) for path in destination.rglob('*')
                    if path.is_file()} != set(files)):
            raise ValueError('a102_catalog_existing_publication_differs')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.a102-catalog-', dir=destination.parent) as temporary:
        staged = Path(temporary) / 'catalog'
        staged.mkdir()
        for name, data in files.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        staged.rename(destination)
    return destination
