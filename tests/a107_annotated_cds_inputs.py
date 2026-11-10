"""Copy original GenBank translation annotations into reusable search inputs.

This is fixture preparation, not translation verification or a detection test.
The autonomous workflow must verify the encoded sequences, actual searched
extent and native search custody. No expected matches are emitted here.
Run this helper through tools/one_workflow.sh after any live workflow exits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from Bio import SeqIO


GENOMIC_FILES = ('rcapsulatus-bioy.gb', 'ecoli-window.gb')


def prepare(output: Path) -> dict:
    original = Path(__file__).parent/'fixtures'/'a103'/'real'
    acquisition = json.loads((original/'manifest.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        'version': 'a107_copied_translation_inputs_v1',
        'meaning': 'Original annotated translations copied for native sequence search; '
            'not verified against DNA and not independent evidence.',
        'whole_genome_coverage': False,
        'files': [],
    }
    for name in GENOMIC_FILES:
        source = original/name
        source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_sha != acquisition['genomic_files'][name]['sha256']:
            raise ValueError('original_genbank_acquisition_identity_conflict: '+name)
        rows, missing, text = [], [], []
        for record in SeqIO.parse(source, 'genbank'):
            for index, feature in enumerate(record.features):
                if feature.type != 'CDS':
                    continue
                translations = feature.qualifiers.get('translation', [])
                identity = {'accession': record.id, 'source_feature_index': index}
                if len(translations) != 1 or not translations[0].strip():
                    missing.append({**identity, 'reason':
                        'missing_or_ambiguous_translation_annotation'})
                    continue
                sequence = ''.join(translations[0].split())
                entry_id = record.id+':CDS:'+str(index)
                text.extend(['>'+entry_id, *[sequence[start:start+80]
                    for start in range(0, len(sequence), 80)]])
                rows.append({**identity, 'fasta_id': entry_id,
                    'annotation_sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
                    'verification': 'not_performed'})
        fasta = ('\n'.join(text)+'\n').encode('ascii')
        destination = output/(Path(name).stem+'.annotated.faa')
        destination.write_bytes(fasta)
        manifest['files'].append({
            'original_genbank_name': name, 'original_genbank_sha256': source_sha,
            'original_acquisition': acquisition['genomic_files'][name],
            'fasta_name': destination.name, 'fasta_sha256': hashlib.sha256(fasta).hexdigest(),
            'copied_annotations': rows, 'uncopied_cds': missing,
        })
    (output/'provenance.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    saved = prepare(args.output.resolve())
    print(json.dumps({'event': 'annotated_cds_inputs_copied', 'output': str(args.output),
        'files': [{'name': item['fasta_name'], 'sha256': item['fasta_sha256'],
            'copied_annotations': len(item['copied_annotations']),
            'uncopied_cds': len(item['uncopied_cds'])} for item in saved['files']],
        'dna_verification_performed': False, 'search_performed': False}))
