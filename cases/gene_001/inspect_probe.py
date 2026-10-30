"""Read the actual probe artifacts; no score, thresholds or annotation transfer."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from Bio import SearchIO, SeqIO


ROOT = Path(__file__).resolve().parent
JOB = ROOT / 'jobs' / 'homology_001'


def main():
    result = SearchIO.read(JOB / 'homology_search.stdout', 'hmmer3-text')
    assert result.id == 'gene_001' and result.seq_len == 253
    assert result.program == 'phmmer'
    descriptions = {}
    with (JOB / 'hits.tbl').open() as stream:
        for line in stream:
            if not line.startswith('#') and line.strip():
                fields = line.split(maxsplit=18)
                assert len(fields) == 19 and fields[2] == result.id
                descriptions[fields[0]] = fields[18].rstrip()
    assert set(descriptions) == {hit.id for hit in result}
    references = {}
    for record in SeqIO.parse(JOB / 'reviewed.fasta', 'fasta'):
        if record.id in descriptions:
            references[record.id] = str(record.seq)
    assert set(references) == set(descriptions)
    query = str(SeqIO.read(ROOT / 'target.faa', 'fasta').seq)
    rows = []
    for hit in result:
        sequence = references[hit.id]
        rows.append({'reference_id': hit.id, 'source_description': descriptions[hit.id],
            'reference_length_aa': len(sequence),
            'reference_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
            'identical_to_query': sequence == query,
            'sequence_evalue': hit.evalue, 'sequence_bitscore': hit.bitscore,
            'native_inclusion_flag': hit.is_included,
            'alignments': [{'domain_index': hsp.domain_index,
                'query_interval_aa_zero_based_half_open': [hsp.query_start, hsp.query_end],
                'reference_interval_aa_zero_based_half_open': [hsp.hit_start, hsp.hit_end],
                'query_aligned': str(hsp.query.seq), 'reference_aligned': str(hsp.hit.seq),
                'conditional_domain_evalue': hsp.evalue_cond,
                'independent_domain_evalue': hsp.evalue,
                'domain_bitscore': hsp.bitscore, 'native_inclusion_flag': hsp.is_included}
                for hsp in hit]})
    # Only reported reference sequences are copied into this small inspection
    # artifact; the complete unchanged search database remains on disk.
    with (JOB / 'reported-references.faa').open('w') as stream:
        for reference, sequence in references.items():
            stream.write('>' + reference + '\n' + sequence + '\n')
    phases = defaultdict(lambda: {'samples': 0, 'sampled_max_resident_bytes': 0,
        'sampled_max_cgroup_memory_bytes': 0, 'observed_stdout_bytes': [],
        'returned': None})
    with (JOB / 'observations.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            phase = phases[row['phase']]
            if row['event'] == 'sample':
                phase['samples'] += 1
                size = row['files'].get(row['phase'] + '.stdout', 0)
                if size not in phase['observed_stdout_bytes']:
                    phase['observed_stdout_bytes'].append(size)
                for process in row['processes']:
                    for field in ('resident_bytes', 'cgroup_memory_bytes'):
                        name = 'sampled_max_' + field
                        phase[name] = max(phase[name], process.get(field, 0))
            if row['event'] == 'phase_returned':
                phase['returned'] = row
    inspection = {'case_ref': 'gene_001', 'query_count': 1,
        'reported_references': len(rows),
        'reference_sequences_identical_to_query': sum(r['identical_to_query'] for r in rows),
        'reference_sequence_groups': len({r['reference_sequence_sha256'] for r in rows}),
        'measurements': rows, 'execution_phases': dict(phases),
        'native_flags_are_scientific_approval': False,
        'new_reporting_cutoff_applied': False, 'credit_assigned': False,
        'annotation_conclusion': None,
        'timing_meaning': 'Probe phase latency includes sampling; native_metadata.elapsed_seconds measures the protected command service; the native stdout also reports phmmer internal time.',
        'progress_meaning': 'Sampled CPU, memory, I/O and file sizes do not establish percentage searched or scientific insight. Unobserved changes between samples remain unknown.'}
    (JOB / 'inspection.json').write_text(json.dumps(inspection, indent=2) + '\n')
    print(json.dumps({key: inspection[key] for key in ('query_count', 'reported_references',
        'reference_sequences_identical_to_query', 'reference_sequence_groups', 'credit_assigned')}))
    for name, phase in phases.items():
        print(json.dumps({'phase': name, 'samples': phase['samples'],
            'observed_stdout_bytes': phase['observed_stdout_bytes'],
            'native_elapsed_seconds': phase['returned']['native_metadata']['elapsed_seconds'],
            'sampled_max_resident_bytes': phase['sampled_max_resident_bytes']}))


if __name__ == '__main__':
    main()
