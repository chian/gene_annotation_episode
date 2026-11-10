"""Freeze a real A104 molecular panel and its exact shared-HPC commission."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.state import Store
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.a104_hpc import prepare_request, commission
from gene_annotation_episode.hpc_campaign import validate_commission
from gene_annotation_episode.execution_memory import ExecutionMemory


def prepare(bundle_path, directory, *, threads=4, model='LG'):
    root = Path(__file__).resolve().parents[1]
    bundle = json.loads(Path(bundle_path).read_text())
    directory.mkdir(parents=True, exist_ok=False)
    sources, proteins, known = {}, {}, []
    with Store(directory/'state') as store:
        for path, descriptor in bundle['source_files'].items():
            raw = Path(path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
                raise ValueError('a104_original_input_file_changed')
            artifact = store.artifact(raw, descriptor.get('media_type', 'application/json'))
            text = artifact
            if descriptor.get('media_type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                from tools.a104_acquire_cases import table_preview
                text = store.artifact(canonical({'format': 'source_preserving_workbook_cells_v1',
                    'source_workbook_sha256': descriptor['sha256'], 'worksheets': table_preview(raw)}), 'application/json')
            source = store.put('source', {'provider': descriptor.get('provider', 'retained.uniprot'), 'accession': Path(path).name,
                'uri': descriptor.get('uri', 'https://rest.uniprot.org/uniprotkb/search'), 'artifact_ref': artifact,
                'text_ref': text, 'request_ref': store.artifact(canonical(descriptor['request']), 'application/json')
                    if descriptor.get('request') else None, 'version': 'original_a104_sequence_acquisition_20261104',
                'retrieved_at': None}, origin='external')['id']
            sources[str(Path(path).resolve())] = source
            known.append(source)
        for accession, metadata in bundle['records'].items():
            row = metadata['record']
            symbols = row['sequence']['value']
            source = sources[str(Path(metadata['source_path']).resolve())]
            reference = store.put('reference', {'reference_type': 'protein', 'source_ref': source,
                'accession': accession, 'label': 'Acquired protein '+accession,
                'sequence_ref': store.artifact(symbols, 'text/plain'), 'molecule': 'protein',
                'length': len(symbols), 'term_refs': [], 'context_refs': []}, origin='external')['id']
            proteins[accession] = reference
            known.append(reference)
        origin = proteins[bundle['target_accession']]
        original = bundle['records'][bundle['target_accession']]['record']
        target, = store.create_problem(raw_sequence=original['sequence']['value'], molecule='protein',
            caller_context='Actual input from the preserved original public source, accession '+bundle['target_accession']+
                '; exact original response and peptide bytes are preserved. No proposed function is supplied.')['subject_refs']
        scope = {'subject_refs': [target]}
        known.append(target)
        analyses = deepcopy(bundle['analyses'])
        for analysis in analyses:
            for row in analysis['members']:
                parts = []
                for part in row['parts']:
                    selected = {'accession': part} if isinstance(part, str) else part
                    accession = selected['accession']
                    parts.append({'subject_ref': target if accession == bundle['target_accession']
                        and analysis['purpose'] in {'family', 'regional', 'sensitivity'} else proteins[accession],
                        **({'regions': selected['regions']} if 'regions' in selected else {})})
                row['parts'] = parts
        request = prepare_request(store, target_ref=target, analyses=analyses, scope=scope,
            known_record_refs=known, case_id=bundle['case_id'], threads=threads, model=model,
            target_origin_reference_ref=origin)
        known.append(request)
        resources = json.loads((root/'examples/aurora_execution_resources.json').read_text())
        resources['aurora']['workspace'] = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/'+directory.parent.name
        work = commission(store, request, resources['aurora'])
        validate_commission(work, resources)
        prepared = {'version': 'a104_prepared_case_v1', 'case_id': bundle['case_id'], 'scope': scope,
            'target_ref': target, 'target_origin_reference_ref': origin, 'native_request_ref': request,
            'known_record_refs': known, 'execution_resources': resources,
            'hpc_commissions': {'a104-native': work},
            'shared_execution_memory': ExecutionMemory.configured().as_record(),
            'source_directory': str(root/'research/slotted_process_library/publications/2026-10-24-001'),
            'scientific_status': 'actual_source_inputs_and_native_job_request; no_alignment_tree_or_credit_yet'}
        (directory/'PREPARED.json').write_text(json.dumps(prepared, indent=2)+'\n')
    return prepared


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--model', choices=('LG', 'MFP'), default='LG')
    args = parser.parse_args()
    value = prepare(args.bundle, run/'case', threads=args.threads, model=args.model)
    print(canonical({'event': 'a104_exact_hpc_case_prepared', 'case': value['case_id'],
        'case_directory': str(run/'case'), 'native_request_ref': value['native_request_ref'],
        'target_ref': value['target_ref'], 'commission_count': len(value['hpc_commissions'])}), flush=True)


if __name__ == '__main__':
    main()
