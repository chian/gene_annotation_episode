"""Retain the terminal root integration checks and the exact sources tested."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
tests = [
    'tests/test_bvbrc_alignment_returns.py',
    'tests/test_bvbrc_alignment_tool_info.py',
    'tests/test_communication.py',
    'tests/test_bvbrc_appservice_publication.py',
    'tests/test_api_service_result_ordering.py',
    'tests/test_bvbrc_phylogeny_returns.py',
    'tests/test_bvbrc_homology_returns.py',
    'tests/test_bvbrc_alignment_bundle_resolution.py',
    'tests/test_bvbrc_alignment_bundle_projection.py',
]
source_names = [
    'bvbrc_alignment_returns.py', 'bvbrc_alignment_tool_info.py',
    'communication.py', 'bvbrc_appservice_adapters.py',
    'api_service_execution.py', 'bvbrc_appservice_host.py',
    'execution_episodes.py', 'bvbrc_appservice_publication.py',
    'bvbrc_alignment_bundle_contracts.py',
    'bvbrc_alignment_bundle_projection.py',
    'bvbrc_alignment_bundle_resolution.py',
    'bvbrc_msa_bundle_adapter.py', 'bvbrc_metacats_bundle_adapter.py',
    'scientific_tool_library.py', 'resource_tool_information.py',
    'scientific_process_episodes.py', 'tool_schema_validation.py',
    'bvbrc_appservice_contracts.py',
]
paths = [*(ROOT/'gene_annotation_episode'/name for name in source_names),
         *(ROOT/name for name in tests)]


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


receipt_path = HERE/'TEST_004.json'
assert not receipt_path.exists()
log_path, xml_path = HERE/'returns-004.log', HERE/'returns-004.xml'
command = ['.venv/bin/python', '-m', 'pytest', '-q', '--tb=short', *tests,
           '--junitxml='+str(xml_path.relative_to(ROOT))]
before = hashes()
started = datetime.now(timezone.utc).isoformat()
with log_path.open('x') as log:
    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = hashes()
receipt = {'command': command, 'started_at': started,
           'ended_at': datetime.now(timezone.utc).isoformat(),
           'returncode': result.returncode, 'source_before': before,
           'source_after': after, 'source_unchanged': before == after,
           'log': str(log_path.relative_to(ROOT)),
           'junit': str(xml_path.relative_to(ROOT))}
if xml_path.exists():
    suite = ET.parse(xml_path).getroot().find('testsuite')
    receipt['counts'] = {key: int(suite.attrib[key])
                         for key in ('tests', 'errors', 'failures', 'skipped')}
with receipt_path.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: receipt[key] for key in
      ('returncode', 'source_unchanged', 'counts', 'log', 'junit') if key in receipt}))
print('\n'.join(log_path.read_text().splitlines()[-12:]))
raise SystemExit(result.returncode)
