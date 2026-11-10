"""Copy exact published OarX peptides into a comparative native-test request.

The source annotations select comparison leads only. This metadata builder
performs no alignment, phylogeny or experimental activity inference.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from tools.a104_acquire_cases import table_preview


def build(original, fabg, output):
    workbook = original/'oarx-supplement.xlsx'
    table = table_preview(workbook.read_bytes())['xl/worksheets/sheet2.xml']
    entries, current = [], None
    for row in table:
        for cell, text in row.items():
            text = text.strip()
            if text.startswith('>'):
                current = {'accession': text[1:].split()[0].replace('|', ':'), 'header': text,
                           'header_cell': cell, 'sequence_cells': [], 'peptide_parts': []}
                entries.append(current)
            elif current is not None and text:
                if set(text)-set('ACDEFGHIKLMNPQRSTVWYBXZJUO*'):
                    raise ValueError('oarx_original_sequence_cell_not_peptide:'+cell)
                current['sequence_cells'].append(cell)
                current['peptide_parts'].append(text)
    targets = [row for row in entries if '[Corynebacterium glutamicum ATCC 13032]' in row['header']]
    if len(targets) != 1:
        raise ValueError('oarx_target_sequence_not_unique')
    target = targets[0]
    sampled = [entries[i*(len(entries)-1)//31] for i in range(min(32, len(entries)))]
    if target not in sampled:
        sampled[-1] = target
    records, members = {}, []
    for i, row in enumerate(sampled):
        original_peptide = ''.join(row['peptide_parts'])
        peptide = original_peptide.removesuffix('*')
        if not peptide or '*' in peptide:
            raise ValueError('oarx_original_peptide_empty')
        accession = row['accession']
        records[accession] = {'record': {'primaryAccession': accession,
            'sequence': {'value': peptide, 'length': len(peptide)},
            'original_workbook': {'sheet': 'sheet2', **{key: row[key] for key in
                ('header', 'header_cell', 'sequence_cells')},
                'terminal_stop_symbol_omitted': original_peptide.endswith('*')}},
            'source_path': str(workbook.resolve()), 'sampling_query_group': 'published_OarX_sequence_panel'}
        members.append({'tip_id': 'oarx_'+str(i), 'parts': [accession]})
    reference = fabg/'family-fabg.json'
    for row in json.loads(reference.read_text())['results']:
        accession = row['primaryAccession']
        records[accession] = {'record': row, 'source_path': str(reference.resolve()),
                              'sampling_query_group': 'reviewed_FabG_comparison_lead'}
        members.append({'tip_id': 'p_'+accession, 'parts': [accession], 'taxon_id': row['organism']['taxonId']})
    family = {'name': 'family', 'purpose': 'family', 'members': members}
    sensitivity = deepcopy(family)
    sensitivity.update(name='family_mfp', purpose='sensitivity', model='MFP', seed=105)
    regional = deepcopy(family)
    regional.update(name='target_region', purpose='regional')
    next(row for row in regional['members'] if row['parts'] == [target['accession']])['parts'] = [
        {'accession': target['accession'], 'regions': [[0, 120]]}]
    acquisition = json.loads((original/'oarx-supplement-acquisition.json').read_text())
    sources = {str(workbook.resolve()): {'sha256': hashlib.sha256(workbook.read_bytes()).hexdigest(),
        'size_bytes': workbook.stat().st_size, 'provider': 'retained.publication.sequence_table',
        'media_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'uri': acquisition['requested_url'], 'request': {**acquisition,
            'archive_member': 'ao4c03514_si_002.xlsx',
            'extracted_workbook_sha256': hashlib.sha256(workbook.read_bytes()).hexdigest()}},
        str(reference.resolve()): {'sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
            'size_bytes': reference.stat().st_size,
            'request': json.loads(reference.with_name('family-fabg-request.json').read_text())}}
    output.write_text(json.dumps({'version': 'a104_real_input_bundle_v1', 'case_id': 'oarx',
        'target_accession': target['accession'], 'records': records,
        'analyses': [family, sensitivity, regional], 'source_files': sources,
        'interpretation': 'original_publication_peptides_and_comparison_leads; no_assayed_function_or_independent_organismal_tree_supplied'}, indent=2)+'\n')
    print(json.dumps({'case': 'oarx', 'original_published_sequences': len(entries),
        'sampled_published_sequences': len(sampled), 'comparison_proteins': len(members),
        'target_accession': target['accession'], 'target_length': len(''.join(target['peptide_parts']))}), flush=True)


if __name__ == '__main__':
    active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-directory', type=Path, required=True)
    parser.add_argument('--fabg-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.original_directory.resolve(), args.fabg_directory.resolve(), args.output)
