"""Seal only060's own completed audit, preserving original pins/live work."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[2]
PIN = BASE / 'literature_model_run_030/pin_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def main():
    proof = json.loads((HERE / 'SOURCE_AND_ARITHMETIC_RECEIPT_001.json').read_bytes())
    reset = json.loads((HERE / 'RESET_READ_RECEIPT_001.json').read_bytes())
    assert proof['passed'] and reset['complete']
    assert len(reset['acknowledged_chunks']) == 49 and len(reset['documents']) == 25
    modules = ['literature_rate_reader.py','literature_rate_native_inputs.py','literature_rate_calculations.py',
               'literature_rate_storage.py','literature_partner_defined_units.py','literature_experimental_contracts.py',
               'literature_assay_inputs.py','literature_episodes.py','state.py']
    write(HERE / 'IMPLEMENTATION_IDENTITIES_001.json', {
        'scope': 'Original030 modules inspected; partial methods versus complete modules are distinguished in READ_PROVENANCE_001.md',
        'original_pin_source_manifest_sha256': sha(PIN / 'SOURCE_MANIFEST.json'),
        'modules': {name: {'path': str((PIN / 'gene_annotation_episode' / name).relative_to(ROOT)),
                            'sha256': sha(PIN / 'gene_annotation_episode' / name)} for name in modules}})
    excluded = ['MANIFEST_001.json', 'FINAL_VERIFY_001.json']
    files = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.name not in excluded:
            files[str(path.relative_to(HERE))] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    manifest = {'scope': 'Own060 read-only source audit; no scientific implementation/model/runtime completion claim',
                'excluded': excluded, 'files': files}
    write(HERE / 'MANIFEST_001.json', manifest)
    for name, row in files.items():
        path = HERE / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    extras = [str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()
              and str(p.relative_to(HERE)) not in files and p.name not in excluded]
    assert not extras
    receipt = {'passed': True, 'files_verified': len(files), 'manifest_sha256': sha(HERE / 'MANIFEST_001.json'),
               'original_pin_files_verified_by_source_proof': proof['original_pin_files_verified'],
               'reset_chunks_verified': 49, 'reset_document_entries': 25,
               'scientific_text_paths': ['SCIENTIFIC_AUDIT_001.md','HANDOFF_001.md','READ_PROVENANCE_001.md'],
               'oldrun_pin_shared_production_files_modified': False}
    write(HERE / 'FINAL_VERIFY_001.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
