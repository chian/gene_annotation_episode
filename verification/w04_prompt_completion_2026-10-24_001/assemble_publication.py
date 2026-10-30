"""Assemble the new instruction publication without changing its historical inputs.

This is a development publication utility, not an episode operation or scorer.
The content worker owns the ten new A entry files. Existing P bytes and source
rows are copied exactly; instruction provenance is never target evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'research/slotted_process_library'
PUBLICATION = SOURCE / 'publications/2026-10-24-001'
AXES = tuple(f'A{number}' for number in (*range(101, 109), 110, 111))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    from gene_annotation_episode.evidence_axis_instructions import validate_instruction_entry

    source_index = json.loads((SOURCE / 'index.json').read_text())
    source_table = json.loads((SOURCE / 'option_sources.json').read_text())
    thought_headers = [item for item in source_index['entries'] if item['slot'] == 'thought_pattern']
    if [row['id'] for row in thought_headers] != [f'P{number:02}' for number in range(1, 20)]:
        raise ValueError('expected_the_retained_nineteen_thought_patterns')
    axes = [validate_instruction_entry(json.loads(
        (PUBLICATION / 'entries' / f'{axis}.json').read_text())) for axis in AXES]
    if [entry['id'] for entry in axes] != list(AXES):
        raise ValueError('publication_axis_identity_mismatch')

    headers, rows, provenance = [], [], []
    for entry in axes:
        source_ids = [f'E-{entry["id"]}-{number:04}' for number in range(1, len(entry['evidence']) + 1)]
        headers.append({key: entry[key] for key in ('id', 'slot', 'name', 'description')} | {
            'detail_path': f'entries/{entry["id"]}.json', 'source_evidence_ids': source_ids})
        rows.extend({'evidence_id': reference, 'option_id': entry['id'], **row}
                    for reference, row in zip(source_ids, entry['evidence'], strict=True))
        original = SOURCE / 'publications/2026-10-23-002/entries' / f'{entry["id"]}.json'
        original_body = json.loads(original.read_text())
        if entry['evidence'] != original_body['evidence']:
            raise ValueError('instruction_source_rows_changed')
        provenance.append({'option': entry['id'], 'retained_source': str(original.relative_to(REPO)),
                           'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest()})

    for header in thought_headers:
        original = SOURCE / header['detail_path']
        target = PUBLICATION / header['detail_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original.read_bytes())
        headers.append(header)
        rows.extend(row for row in source_table['rows'] if row['option_id'] == header['id'])
        provenance.append({'option': header['id'], 'retained_source': str(original.relative_to(REPO)),
                           'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest()})

    write_json(PUBLICATION / 'index.json', {
        'format': 'research_three_slot_options_v1',
        'status': ('Ten evidence-axis investigation instructions and nineteen retained thought patterns. '
                   'Actual tool information is retrieved separately. This publication installs no '
                   'scoring sheet, score formula, reader or target evidence.'),
        'slots': [
            {'slot': 'evidence_axis', 'catalog': 'evidence_axis_options.json', 'count': len(axes)},
            {'slot': 'thought_pattern', 'catalog': 'thought_options.json', 'count': len(thought_headers)}],
        'entries': headers})
    write_json(PUBLICATION / 'option_sources.json', {
        'meaning': ('Retained source links explain reusable investigation instructions. They are not '
                    'findings about the current target, independent experiment counts or credit receipts.'),
        'rows': rows})
    write_json(PUBLICATION / 'evidence_axis_options.json', {
        'slot': 'evidence_axis', 'options': [entry for entry in headers if entry['slot'] == 'evidence_axis']})
    (PUBLICATION / 'thought_options.json').write_bytes((SOURCE / 'thought_options.json').read_bytes())
    write_json(PUBLICATION / 'SOURCE_PROVENANCE.json', {
        'purpose': 'Instruction provenance; source observations were retained, not newly researched.',
        'entries': provenance})
    print(json.dumps({'publication': str(PUBLICATION), 'evidence_axes': len(axes),
                      'thought_patterns': len(thought_headers), 'source_rows': len(rows)}))


if __name__ == '__main__':
    main()
