"""Verify final C1/C2 together, retaining exact command and source identities."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = [ROOT / 'gene_annotation_episode' / (name + '.py') for name in (
    'bvbrc_genome_alignment_inputs', 'bvbrc_genome_alignment_retained_records',
    'bvbrc_genome_alignment_associations', 'bvbrc_genome_alignment_input_contracts')]
TESTS = ['tests/test_bvbrc_genome_alignment_inputs.py',
         'tests/test_bvbrc_genome_alignment_retained_records.py',
         'tests/test_bvbrc_genome_alignment_associations.py',
         'tests/test_bvbrc_genome_alignment_input_contracts.py']
FILES += [ROOT / p for p in TESTS]


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def main():
    target = HERE / 'COMBINED_TEST_002.json'
    assert not target.exists()
    before = hashes()
    assert before['gene_annotation_episode/bvbrc_genome_alignment_inputs.py'] == '06f3e21d52273a286caea31672adcce4352c9fffb6f6afa3f0f7e4cbe77302a1'
    assert before['gene_annotation_episode/bvbrc_genome_alignment_retained_records.py'] == '9605282aeaf35e3efb8906145ec17f6c4c2b59e896c1f1e06ac7107f9f9259b9'
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--tb=short',
               *TESTS, '--junitxml=' + str(HERE / 'combined-002.xml')]
    with (HERE / 'combined-002.log').open('x') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    after = hashes()
    tree = ET.parse(HERE / 'combined-002.xml')
    suites = list(tree.getroot().iter('testsuite'))
    counts = {k: sum(int(s.attrib[k]) for s in suites) for k in ('tests', 'errors', 'failures', 'skipped')}
    record = {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'command': command, 'returncode': result.returncode, 'counts': counts,
        'source_before': before, 'source_after': after, 'source_unchanged': before == after,
        'scope': 'C1/C2 pure extraction/association and existing C value contracts. No live service or Workflow integration.'}
    with target.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: record[k] for k in ('returncode', 'counts', 'source_unchanged')}))
    raise SystemExit(result.returncode or (0 if before == after else 1))


if __name__ == '__main__':
    main()
