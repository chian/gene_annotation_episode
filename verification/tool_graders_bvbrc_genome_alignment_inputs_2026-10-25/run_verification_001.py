"""Verify closed C records and retain labelled synthetic input examples."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OWNED = ['gene_annotation_episode/bvbrc_genome_alignment_input_contracts.py',
         'tests/test_bvbrc_genome_alignment_input_contracts.py']


def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in OWNED}


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


before = hashes()
command = ['.venv/bin/python', '-m', 'pytest', '-q', '--tb=short', OWNED[1],
           '--junitxml=' + str((HERE / 'tests-001.xml').relative_to(ROOT))]
started = datetime.now(timezone.utc).isoformat()
with (HERE / 'tests-001.log').open('x') as stream:
    result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False)
after = hashes()
suite = ET.parse(HERE / 'tests-001.xml').getroot().find('testsuite')
record = {'command': command, 'started_at': started,
    'ended_at': datetime.now(timezone.utc).isoformat(), 'returncode': result.returncode,
    'source_before': before, 'source_after': after, 'source_unchanged': before == after,
    'counts': {key: int(suite.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')},
    'pytest_seconds': float(suite.attrib['time']),
    'scope': 'Closed input/association values only; synthetic task custody, in-memory FASTA parsing. No metadata extractor, service execution or complete episode path claimed.'}
save('TEST_001.json', record)
assert result.returncode == 0 and before == after

spec = importlib.util.spec_from_file_location('genome_alignment_contract_examples', ROOT / OWNED[1])
examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(examples)
from gene_annotation_episode.bvbrc_genome_alignment_input_contracts import (
    validate_genome_alignment_inputs, validate_genome_alignment_associations)
for mode in ('multiple_files_concatenated', 'single_file_entries'):
    value, raw = examples.input_fixture(mode)
    checked = validate_genome_alignment_inputs(value)
    save(mode + '.json', {'provenance': 'synthetic task/custody; actual supplied FASTA bytes',
        'input_fasta_ascii': {key: data.decode('ascii') for key, data in raw.items()},
        'inputs': checked, 'member_lengths': [m['source_length'] for m in checked['member_bindings']]})
save('explicit_interval_join.json', {'provenance': 'synthetic task/custody/association only',
    'associations': validate_genome_alignment_associations(examples.association_fixture())})
save('SOURCE_HASHES_001.json', {'owned_sources': hashes(),
    'artifacts': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(HERE.iterdir()) if p.is_file()}})
print(json.dumps(record))
