"""Build reproducible A104 inputs from original saved public response bytes.

This utility performs metadata selection and exact sequence copying only. It
does not align sequences or infer a phylogeny. Acquisition uses an explicitly
selected external client; this builder records the original files and queries.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget


GROUPS = ('yjeh', 'adic', 'cadb', 'pote')
MARKERS = {'L2': {'rplb', 'rpl2'}, 'L3': {'rplc', 'rpl3'}, 'S3': {'rpsc', 'rps3'}}


def source_descriptor(path):
    raw = path.read_bytes()
    result = {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
    manifest_path = path.parent/'manifest.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        row = manifest['files'][path.name]
        if row['sha256'] != result['sha256']:
            raise ValueError('a104_original_response_manifest_conflict')
        result['request'] = {'base_url': manifest['base_url'], 'path': manifest['path'],
            'params': {'query': row['query'], 'size': row['size'], 'fields': manifest['fields'], 'format': 'json'}}
    return result


def gene_names(row):
    return {entry['value'].lower() for gene in row.get('genes', [])
            for entry in [gene.get('geneName', {}), *gene.get('synonyms', [])] if entry.get('value')}


def proteins(directory):
    rows, sources = {}, {}
    for group in GROUPS:
        path = directory/('family-'+group+'.json')
        source = json.loads(path.read_text())
        selected = []
        for row in source['results']:
            if group not in gene_names(row):
                continue
            accession = row['primaryAccession']
            if not row.get('sequence', {}).get('value'):
                continue
            selected.append(accession)
            rows[accession] = {'record': row, 'source_path': str(path.resolve()), 'sampling_query_group': group}
        sources[group] = selected
    return rows, sources


def marker_request(args):
    directory = args.input_directory.resolve()
    rows, groups = proteins(directory)
    selected = sorted((rows[key]['record'] for key in groups['yjeh']),
                      key=lambda row: (row['primaryAccession'] != 'P39277', row['primaryAccession']))
    taxa = list(dict.fromkeys(row['organism']['taxonId'] for row in selected))[:8]
    query = '('+' OR '.join('organism_id:'+str(taxon) for taxon in taxa)+') AND ('+ \
            ' OR '.join('gene_exact:'+gene for names in MARKERS.values() for gene in sorted(names))+') AND fragment:false'
    request = {'base_url': 'https://rest.uniprot.org', 'path': 'uniprotkb/search',
        'params': {'query': query, 'fields': 'accession,id,protein_name,gene_names,organism_id,organism_name,sequence,length',
                   'size': 500, 'format': 'json'}, 'record_path': 'results', 'max_items': 1, 'max_depth': 2,
        'save_raw': True, 'raw_output_path': str(directory/'yjeh-organismal-markers.json')}
    args.output.write_text(json.dumps(request, indent=2)+'\n')
    print(json.dumps({'event': 'marker_request_prepared', 'actual_taxon_ids': taxa,
                      'family_proteins': len(rows), 'output': str(args.output)}), flush=True)


def build_yjeh(args):
    directory = args.input_directory.resolve()
    rows, groups = proteins(directory)
    path = directory/'yjeh-organismal-markers.json'
    marker_rows = json.loads(path.read_text())['results']
    markers = defaultdict(lambda: defaultdict(list))
    for row in marker_rows:
        if not row.get('sequence', {}).get('value'):
            continue
        for group, genes in MARKERS.items():
            if gene_names(row) & genes:
                markers[row['organism']['taxonId']][group].append(row)
    complete, unknown = [], []
    for taxon, found in sorted(markers.items()):
        chosen = []
        for group in MARKERS:
            copies = found[group]
            peptides = {row['sequence']['value'] for row in copies}
            if len(peptides) != 1:
                unknown.append({'taxon_id': taxon, 'marker': group,
                                'reason': 'missing' if not copies else 'different_candidate_copies'})
                break
            chosen.append(sorted(copies, key=lambda row: (row['entryType'] != 'UniProtKB reviewed (Swiss-Prot)',
                                                        row['primaryAccession']))[0])
        if len(chosen) == len(MARKERS):
            complete.append({'taxon_id': taxon, 'parts': [row['primaryAccession'] for row in chosen]})
            for row in chosen:
                rows[row['primaryAccession']] = {'record': row, 'source_path': str(path), 'sampling_query_group': 'marker'}
    if len(complete) < 4:
        raise ValueError('fewer_than_four_unambiguous_organismal_marker_sets:'+json.dumps(unknown))
    inputs = []
    for name in GROUPS:
        for accession in groups[name]:
            inputs.append({'tip_id': 'p_'+accession, 'parts': [accession],
                           'taxon_id': rows[accession]['record']['organism']['taxonId']})
    output = {'version': 'a104_real_input_bundle_v1', 'case_id': 'yjeh', 'target_accession': 'P39277',
        'records': rows, 'analyses': [{'name': 'family', 'purpose': 'family', 'members': inputs},
            {'name': 'organismal', 'purpose': 'organismal_reference',
             'organismal_basis': {'kind': 'independent_ribosomal_marker_supermatrix', 'markers': list(MARKERS),
                                 'limitations': ['inferred_reference', 'three_marker_sampling', 'unestablished_root'],
                                 'unknown_marker_sets': unknown},
             'members': [{'tip_id': 'tax_'+str(row['taxon_id']), **row} for row in complete]}],
        'source_files': {str(p): source_descriptor(p)
                         for p in sorted({Path(row['source_path']) for row in rows.values()})},
        'interpretation': 'source_annotations_are_leads; no_expected_function_in_native_or_episode_request'}
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({'event': 'real_input_bundle_built', 'case': 'yjeh', 'family_members': len(inputs),
                      'organismal_taxa': len(complete), 'unknown_marker_sets': unknown,
                      'output': str(args.output)}), flush=True)


def main():
    active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('marker-request', 'build-yjeh'))
    parser.add_argument('--input-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    (marker_request if args.operation == 'marker-request' else build_yjeh)(args)


if __name__ == '__main__':
    main()
