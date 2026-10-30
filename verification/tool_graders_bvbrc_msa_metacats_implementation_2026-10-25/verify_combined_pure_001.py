"""Verify new pure modules together with exact source snapshots; no live job."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
modules = ['bvbrc_alignment_values', 'bvbrc_msa_formats', 'bvbrc_msa_format_contracts',
    'bvbrc_msa_calculators', 'bvbrc_msa_calculation_contracts', 'bvbrc_metacats_formats',
    'bvbrc_metacats_format_contracts', 'bvbrc_metacats_calculators',
    'bvbrc_metacats_calculation_contracts', 'phylogeny_formats', 'phylogeny_format_contracts',
    'phylogeny_calculators', 'phylogeny_calculation_contracts']
tests = ['test_bvbrc_alignment_values', 'test_bvbrc_msa_formats', 'test_bvbrc_msa_calculators',
    'test_bvbrc_metacats_formats', 'test_bvbrc_metacats_format_contracts', 'test_bvbrc_metacats_calculators']
paths = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in modules]
paths += [ROOT / 'tests' / (name + '.py') for name in tests]


def hashes():
    return [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in paths]


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


before = hashes()
save('COMBINED_SOURCE_BEFORE_001.json', before)
command = [sys.executable, '-m', 'pytest', '-q', *['tests/' + name + '.py' for name in tests],
    '--junitxml=' + str((HERE / 'combined-pure-001.xml').relative_to(ROOT))]
with (HERE / 'combined-pure-001.log').open('x') as log:
    process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = hashes()
save('COMBINED_SOURCE_AFTER_001.json', after)
suite = ET.parse(HERE / 'combined-pure-001.xml').getroot().find('testsuite')
counts = {key: int(suite.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
receipt = {'argv': command, 'returncode': process.returncode, 'source_unchanged': before == after,
    'counts': counts, 'seconds': float(suite.attrib['time']),
    'scope': 'Nine new pure MSA/MetaCATS modules and their actual shared operand dependencies. No provider, service, configured model, HPC or episode path is executed.'}
save('COMBINED_VERIFICATION_001.json', receipt)
print(json.dumps(receipt))
assert process.returncode == 0 and before == after and not any(counts[k] for k in ('errors', 'failures', 'skipped'))
