"""Register already acquired case evidence; no search, score or interpretation.

This is reproducible case preparation, not an episodic run. The single original
gene stays the sole target. Native HSP measurements and source assertions remain
distinct from assessments and annotations, which this script never creates.
"""
import hashlib
import json
from pathlib import Path

from Bio import SeqIO

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.phmmer_format import paired_segments
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parent
JOB = ROOT / 'jobs' / 'homology_001'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def source(store, path, *, provider, accession=None, uri=None, origin='external',
           request=None, parents=(), operands=(), version=None, retrieved_at=None,
           stdout=None, stderr=None):
    content = path.read_bytes()
    artifact = store.artifact(content)
    row = {'provider': provider, 'accession': accession, 'uri': uri,
        'artifact_ref': artifact, 'text_ref': artifact,
        'request_ref': store.artifact(canonical(request)) if request is not None else None,
        'version': version, 'retrieved_at': retrieved_at,
        'parent_source_refs': list(parents), 'operand_refs': list(operands)}
    if stdout is not None:
        row['stdout_ref'] = store.artifact(stdout.read_bytes())
    if stderr is not None:
        row['stderr_ref'] = store.artifact(stderr.read_bytes())
    return store.put('source', row, origin=origin)


def background_sources(store, case, result):
    """Retain original assertions/literature, without extracting conclusions."""
    root = ROOT/'acquisition'
    declarations = [
        ('UniProt.P0AAW1', 'uniprot-P0AAW1.json', 'uniprot', 'P0AAW1', None, 'external'),
        ('NCBI.Gene.945408', 'ncbi-gene-945408.json', 'ncbi.gene.summary', '945408', None, 'external'),
        ('NCBI.target_genbank', 'ybhP-NC_000913.3.gb', 'ncbi.genbank', 'NC_000913.3', None, 'external'),
        ('NCBI.neighborhood', 'ybhP-source-neighborhood.gb', 'ncbi.genbank', 'NC_000913.3.neighborhood', None, 'external'),
        ('NCBI.neighborhood_features', 'neighborhood-features.json', 'case.genbank.feature_projection', None, 'NCBI.neighborhood', 'tool'),
        ('NCBI.gene_pubmed_links', 'gene-945408-pubmed-links.json', 'ncbi.gene.pubmed.links', '945408', None, 'external'),
        ('PubMed.gene_linked_abstracts', 'gene-linked-articles.xml', 'ncbi.pubmed', None, 'NCBI.gene_pubmed_links', 'external'),
        ('PubMed.32127419', 'pubmed-32127419.xml', 'ncbi.pubmed', '32127419', 'NCBI.gene_pubmed_links', 'external'),
        ('PubMed.name_search', 'pubmed-ybhP-search.json', 'ncbi.pubmed.search', None, None, 'external'),
        ('PubMed.name_search_abstracts', 'pubmed-ybhP-articles.xml', 'ncbi.pubmed', None, 'PubMed.name_search', 'external'),
        ('PubMed.context_search', 'pubmed-ybhP-context-search.json', 'ncbi.pubmed.search', None, None, 'external'),
        ('PMC7055658.full_text', 'europepmc-7055658-response.body', 'europepmc.full_text', 'PMC7055658', 'PubMed.32127419', 'external'),
        ('PMC7055658.supplement_response', 'pmc-7055658-table-S3-response.body', 'transport.http_response', None, 'PMC7055658.full_text', 'external'),
        ('PMC7055658.supplement_failure', 'supplement-transfer-failure.json', 'transport.failure', None, 'PMC7055658.full_text', 'tool')]
    response_metadata = {'PMC7055658.full_text': 'europepmc-7055658-response.json',
                         'PMC7055658.supplement_response': 'pmc-7055658-table-S3-response.json'}
    result['background_unavailable'] = []
    for alias, filename, provider, accession, parent, origin in declarations:
        path = root/filename
        if not path.is_file() or digest(path) != case['acquisition_files'].get(filename):
            result['background_unavailable'].append({'input_key': alias, 'code': 'retained_source_unavailable_or_changed'})
            continue
        parents = [result['source_refs'][parent]] if parent in result['source_refs'] else []
        request = {'retained_filename': filename, 'retained_sha256': case['acquisition_files'][filename],
                   'retrieval_details_unavailable': True}
        metadata = {}
        if alias in response_metadata:
            name = response_metadata[alias]
            if not (root/name).is_file() or digest(root/name) != case['acquisition_files'][name]:
                result['background_unavailable'].append({'input_key': alias+'.transport_metadata',
                                                        'code': 'retained_response_metadata_unavailable_or_changed'})
            else:
                metadata = json.loads((root/name).read_text())
                request = {'url': metadata['url'], 'http_status': metadata['status'],
                           'retained_metadata_sha256': case['acquisition_files'][name]}
        row = source(store, path, provider=provider, accession=accession, origin=origin,
            parents=parents, uri=metadata.get('resolved_url', metadata.get('url')),
            retrieved_at=metadata.get('retrieved_at'), request=request)
        result['source_refs'][alias] = row['id']


def main():
    case = json.loads((ROOT / 'case.json').read_text())
    job = json.loads((JOB / 'job.json').read_text())
    inspection = json.loads((JOB / 'inspection.json').read_text())
    for name, value in case['target_files'].items():
        if digest(ROOT / name) != value:
            raise ValueError('fixed_case_input_changed')
    for name, item in job['outputs'].items():
        if digest(JOB / name) != item['sha256']:
            raise ValueError('retained_native_output_changed')
    if job['query_count'] != 1 or job['query_sha256'] != digest(ROOT / 'target.faa'):
        raise ValueError('native_job_does_not_bind_this_one_query')
    query = str(SeqIO.read(ROOT / 'target.faa', 'fasta').seq)
    references = {row.id: str(row.seq) for row in SeqIO.parse(JOB / 'reported-references.faa', 'fasta')}
    # Re-read the native output normalization before trusting a previously
    # written inspection artifact. This is parsing, not another native search.
    from inspect_probe import main as inspect_probe
    inspect_probe()
    inspection = json.loads((JOB / 'inspection.json').read_text())
    prepared = []
    for hit in inspection['measurements']:
        for alignment in hit['alignments']:
            intervals, paired, identical = paired_segments(alignment, query, references[hit['reference_id']])
            prepared.append((hit, alignment, intervals, paired, identical))
    result = {'case_ref': 'gene_001', 'source_refs': {}, 'comparison_refs': [],
        'reference_refs': {}, 'annotation_created': False, 'credit_assigned': False,
        'preparation_is_model_driven_episodic_execution': False}
    with Store(ROOT / 'workspace') as store:
        targets = store.targets()
        if len(targets) != 1 or targets[0]['id'] != case['target_ref']:
            raise ValueError('case_target_binding_changed')
        target_ref = targets[0]['id']
        scope = {'subject_refs': [target_ref]}
        translated = ToolRegistry(store).execute('sequence.translate', {'subject_ref': target_ref,
            'code': 11, 'strand': '+', 'frame': 0, 'start': 0, 'end': 762, 'cds': True},
            scope=scope, operation_key='gene_001_prepare_actual_probe_translation_v1')
        if translated['status'] != 'completed':
            raise ValueError('fixed_gene_translation_unavailable')
        product_ref = translated['result']['records'][0]['product_ref']
        if store.get_artifact(store.get(product_ref)['sequence_ref']).decode('ascii') != query:
            raise ValueError('registered_product_differs_from_native_query')
        result.update(target_ref=target_ref, product_ref=product_ref)
        with store.transaction():
            background_sources(store, case, result)
            for accession in ('IPR051916', 'IPR005135'):
                metadata = json.loads((ROOT / 'acquisition' / f'interpro-{accession}-request.json').read_text())
                path = ROOT / 'acquisition' / metadata['body']
                if metadata['status'] != 200 or digest(path) != metadata['sha256']:
                    raise ValueError('acquired_family_record_identity_changed')
                row = source(store, path, provider='interpro', accession=accession,
                    uri=metadata['url'], request=metadata,
                    retrieved_at=metadata['retrieved_at'])
                result['source_refs'][accession] = row['id']
            structure = source(store, ROOT / 'acquisition/rcsb-4RUW-entry.json',
                provider='rcsb', accession='4RUW', uri='https://data.rcsb.org/rest/v1/core/entry/4RUW',
                request={'serialization': 'installed_RCSB_skill_reserialized_JSON',
                    'actual_retrieval_timestamp_unavailable': True})
            result['source_refs']['4RUW'] = structure['id']
            polymer = source(store, ROOT / 'acquisition/rcsb-4RUW-polymer1.json',
                provider='rcsb', accession='4RUW/polymer_entity/1',
                uri='https://data.rcsb.org/rest/v1/core/polymer_entity/4RUW/1',
                parents=[structure['id']],
                request={'serialization': 'installed_RCSB_skill_reserialized_JSON',
                    'actual_retrieval_timestamp_unavailable': True})
            result['source_refs']['4RUW.polymer_entity.1'] = polymer['id']
            manifest = source(store, JOB / 'job.json', provider='native.phmmer.provenance',
                origin='tool', accession='gene_001.homology_001', operands=[product_ref],
                request={'mode': job['mode'], 'database_body_retained_on_disk': 'reviewed.fasta',
                    'database_sha256': job['database_sha256'],
                    'database_release_unavailable': True})
            result['source_refs']['job_manifest'] = manifest['id']
            native = source(store, JOB / 'homology_search.stdout', provider='native.phmmer',
                origin='tool', accession='gene_001.homology_001.output', version='3.4',
                parents=[manifest['id']], operands=[product_ref],
                stdout=JOB / 'homology_search.stdout', stderr=JOB / 'homology_search.stderr')
            result['source_refs']['native_output'] = native['id']
            normalized = source(store, JOB / 'inspection.json', provider='native.phmmer.normalized',
                origin='tool', version='case_phmmer_inspection_v1',
                parents=[native['id']], operands=[product_ref])
            result['source_refs']['normalized_output'] = normalized['id']
            subset = source(store, JOB / 'reported-references.faa', provider='native.phmmer.database_subset',
                origin='tool', parents=[manifest['id']],
                request={'transformation': 'complete_native_reported_reference_sequences_selected_from_fixed_database',
                    'database_sha256': job['database_sha256'], 'selection': 'all_reported_references'})
            for hit in inspection['measurements']:
                native_id = hit['reference_id']
                sequence = references[native_id]
                row = store.put('reference', {'reference_type': 'protein', 'source_ref': subset['id'],
                    'accession': native_id.split('|')[1], 'label': native_id,
                    'sequence_ref': store.artifact(sequence), 'molecule': 'protein',
                    'length': len(sequence), 'term_refs': [], 'context_refs': []}, origin='tool')
                result['reference_refs'][native_id] = row['id']
            for hit, alignment, intervals, paired, identical in prepared:
                reference_ref = result['reference_refs'][hit['reference_id']]
                values = [('evalue', alignment['independent_domain_evalue']),
                    ('bitscore', alignment['domain_bitscore']),
                    ('query_coverage', paired / len(query)),
                    ('target_coverage', paired / hit['reference_length_aa'])]
                if paired:
                    values.append(('identity_fraction', identical / paired))
                metrics = [{'name': key, 'value': {'type': 'number', 'value': value, 'unit_ref': None}}
                    for key, value in values]
                metrics.append({'name': 'reference_ref', 'value': {'type': 'reference', 'ref': reference_ref}})
                # One exact structured row supplies both native statistics and
                # their source context. It confers no function/acceptance verdict.
                body = {**alignment, 'query_ref': product_ref, 'reference_ref': reference_ref,
                    'native_reference_id': hit['reference_id'], 'query_length_aa': len(query),
                    'sequence_evalue': hit['sequence_evalue'], 'sequence_bitscore': hit['sequence_bitscore'],
                    'paired_residues': paired, 'identical_paired_residues': identical,
                    'coordinate_system': 'zero_based_half_open',
                    'gap_semantics': 'operand_intervals_include_only_residues_paired_in_native_alignment',
                    'native_flags_have_control_effect': False}
                artifact = store.artifact(canonical(body))
                row_source = store.put('source', {'provider': 'native.phmmer.alignment',
                    'accession': f"{hit['reference_id'].split('|')[1]}.domain{alignment['domain_index']}",
                    'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
                    'request_ref': None, 'version': 'case_phmmer_alignment_v1', 'retrieved_at': None,
                    'parent_source_refs': [normalized['id'], subset['id']],
                    'operand_refs': [product_ref, reference_ref]}, origin='tool')
                operands = [{'role': role, 'subject_ref': ref, 'start': start, 'end': end,
                    'unit': 'aa', 'model_unit': 'aa'}
                    for role, ref in (('query', product_ref), ('reference', reference_ref))
                    for start, end in intervals[role]]
                observation = store.put('observation', {'subject_refs': [product_ref],
                    'source_subject_refs': [reference_ref], 'kind': 'alignment',
                    'source_ref': row_source['id'], 'measurements': metrics,
                    'dependencies': [product_ref, reference_ref], 'anchor': None,
                    'operand_intervals': operands}, origin='tool', scope=scope)
                result['comparison_refs'].append(observation['id'])
        result['native_alignment_rows'] = len(prepared)
    (ROOT / 'evidence-refs.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'targets': 1, 'reference_records': len(result['reference_refs']),
        'native_alignment_rows': result['native_alignment_rows'], 'annotation_created': False,
        'model_calls': 0, 'new_native_searches': 0}))


if __name__ == '__main__':
    main()
