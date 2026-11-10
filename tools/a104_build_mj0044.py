"""Build an IPK/FomA comparison request from original acquired responses only."""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from tools.a104_inputs import MARKERS, gene_names


def build(directory, refined, output):
    records, paths = {}, []
    files = [directory/name for name in ('target-mj0044.json', 'family-ipk-specific.json', 'family-foma.json')]
    files.append(refined/'family-ipk-refined.json')
    for path in files:
        paths.append(path)
        for row in json.loads(path.read_text())['results']:
            if row.get('sequence', {}).get('value'):
                records.setdefault(row['primaryAccession'], {'record': row, 'source_path': str(path.resolve()),
                    'sampling_query_group': path.stem})
    if 'Q60352' not in records:
        raise ValueError('mj0044_original_target_missing')
    family = [{'tip_id': 'p_'+accession, 'parts': [accession], 'taxon_id': value['record']['organism']['taxonId']}
              for accession, value in sorted(records.items())]
    analyses = [{'name': 'family', 'purpose': 'family', 'members': family}]
    markers_path = refined/'mj0044-organismal-markers-refined.json'
    paths.append(markers_path)
    markers = defaultdict(lambda: defaultdict(list))
    for row in json.loads(markers_path.read_text())['results']:
        for group, genes in MARKERS.items():
            if gene_names(row) & genes and row.get('sequence', {}).get('value'):
                markers[row['organism']['taxonId']][group].append(row)
    complete, unknown = [], []
    for taxon, found in sorted(markers.items()):
        chosen = []
        for group in MARKERS:
            peptides = {row['sequence']['value'] for row in found[group]}
            if len(peptides) != 1:
                unknown.append({'taxon_id': taxon, 'marker': group, 'reason': 'missing_or_ambiguous_copy'})
                break
            chosen.append(sorted(found[group], key=lambda row: row['primaryAccession'])[0])
        if len(chosen) == len(MARKERS):
            complete.append({'tip_id': 'tax_'+str(taxon), 'taxon_id': taxon,
                             'parts': [row['primaryAccession'] for row in chosen]})
            for row in chosen:
                records.setdefault(row['primaryAccession'], {'record': row, 'source_path': str(markers_path.resolve()),
                    'sampling_query_group': 'independent_ribosomal_marker'})
    if len(complete) >= 4:
        analyses.append({'name': 'organismal', 'purpose': 'organismal_reference', 'members': complete,
            'organismal_basis': {'kind': 'independent_ribosomal_marker_supermatrix', 'markers': list(MARKERS),
                'limitations': ['inferred_reference', 'three_marker_sampling', 'unestablished_root'],
                'unknown_marker_sets': unknown}})
    sensitivity = deepcopy(analyses[0])
    sensitivity.update(name='family_mfp', purpose='sensitivity', model='MFP', seed=105)
    analyses.append(sensitivity)
    fragment = deepcopy(analyses[0])
    fragment.update(name='target_region', purpose='regional')
    for member in fragment['members']:
        if member['parts'] == ['Q60352']:
            length = len(records['Q60352']['record']['sequence']['value'])
            member['parts'] = [{'accession': 'Q60352', 'regions': [[0, min(120, length)]]}]
    analyses.append(fragment)
    source_files = {}
    for path in paths:
        request_path = path.with_name(path.stem+'-request.json')
        source_files[str(path.resolve())] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'size_bytes': path.stat().st_size,
            'request': json.loads(request_path.read_text()) if request_path.is_file() else None}
    exclusions = []
    for name in ('ipk', 'mvk', 'thrb', 'galk'):
        path = directory/('family-'+name+'.json')
        if path.is_file():
            exclusions.extend(row['primaryAccession'] for row in json.loads(path.read_text())['results']
                              if row['primaryAccession'] not in records)
    value = {'version': 'a104_real_input_bundle_v1', 'case_id': 'mj0044', 'target_accession': 'Q60352',
        'records': records, 'analyses': analyses, 'source_files': source_files,
        'excluded_initial_query_leads': sorted(set(exclusions)),
        'panel_curation': {'basis': 'amino_acid_kinase_IPK_and_FomA_comparison_leads',
            'primary_sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC1447442/',
                                'https://pubmed.ncbi.nlm.nih.gov/19928876/'],
            'limitation': 'Broad_GHMP_queries_not_admitted_as_homologous_tree_inputs; no_activity_assertion_supplied_to_episode'},
        'interpretation': 'source_names_are_comparison_leads; target_region_and_model_sensitivity_are_explicit_native_tests'}
    output.write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps({'case': 'mj0044', 'family_members': len(family), 'organismal_taxa': len(complete),
        'analyses': [row['name'] for row in analyses], 'unknown_marker_sets': unknown}), flush=True)


if __name__ == '__main__':
    active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-directory', type=Path, required=True)
    parser.add_argument('--refined-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.input_directory.resolve(), args.refined_directory.resolve(), args.output)
