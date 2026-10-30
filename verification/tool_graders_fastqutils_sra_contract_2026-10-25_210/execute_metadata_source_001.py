"""Execute the retained metadata producer on exact supplied XML, without I/O acquisition."""
from copy import deepcopy
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
NATIVE = HERE / 'native_metadata_001'
OUT = HERE / 'source_executed_examples_001'
OUT.mkdir()
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024 ** 3, 20 * 1024 ** 3))
sys.path.insert(0, str(NATIVE / 'lxml_target'))
from lxml import etree

source = HERE / 'sources/sra_import/lib/sra_tools.py'
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'd07b913099d6c6081949353eb41ee006fe7c2d797c770dbb89b9e6894e9c08e3'
spec = importlib.util.spec_from_file_location('retained_sra_tools', source)
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
attempts = []


def forbidden(*args, **kwargs):
    attempts.append(True)
    raise AssertionError('source-only metadata example attempted acquisition or subprocess')


producer.requests.get = forbidden
producer.urlopen = forbidden
producer.subprocess.call = forbidden
producer.subprocess.check_output = forbidden
raw = (NATIVE / 'response.bin').read_bytes()
receipt = json.loads((NATIVE / 'receipt.json').read_text())
assert receipt['http_status'] == 200
assert hashlib.sha256(raw).hexdigest() == receipt['sha256']


def load():
    return etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))


cases = [('native_selected_run', 'SRR6263255', load(), 'unaltered_live_NCBI_XML'),
         ('native_all_returned_runs', None, load(), 'unaltered_live_NCBI_XML')]
tree = load()
for node in tree.xpath('//RUN/Statistics'):
    node.getparent().remove(node)
for node in tree.xpath('//LIBRARY_LAYOUT/*'):
    node.getparent().remove(node)
cases.append(('missing_statistics_and_layout', 'SRR6263255', tree, 'handcrafted_native_XML_mutation'))
tree = load()
for run in tree.xpath('//RUN'):
    run.attrib.pop('total_bases', None)
cases.append(('missing_first_size_attribute', 'SRR6263255', tree, 'handcrafted_native_XML_mutation'))
tree = load()
for run in tree.xpath('//RUN'):
    for key in ('total_bases', 'total_spots', 'size'):
        run.set(key, '0')
cases.append(('reported_zeros', 'SRR6263255', tree, 'handcrafted_native_XML_mutation'))
tree = load()
runs = tree.xpath('//RUN_SET')
extra = deepcopy(runs[0][0])
extra.set('accession', 'SRR_SYNTHETIC_2')
runs[0].append(extra)
cases.append(('two_rows_same_experiment', None, tree, 'handcrafted_native_XML_mutation'))

records = []
for name, accession, tree, provenance in cases:
    directory = OUT / name
    directory.mkdir()
    input_bytes = etree.tostring(tree, pretty_print=True)
    (directory / 'input.xml').write_bytes(input_bytes)
    stdout, stderr = io.StringIO(), io.StringIO()
    started = time.monotonic()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = producer.parse_accession_metadata(accession, tree)
    value = json.dumps(result, indent=2).encode()
    (directory / 'metadata.json').write_bytes(value)
    (directory / 'stdout.log').write_text(stdout.getvalue())
    (directory / 'stderr.log').write_text(stderr.getvalue())
    record = {'case': name, 'accession_filter': accession, 'provenance': provenance,
        'original_live_XML_sha256': receipt['sha256'], 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'selected_function': 'parse_accession_metadata', 'row_count': len(result),
        'elapsed_seconds': time.monotonic() - started, 'input_reformatted_without_semantic_change': provenance == 'unaltered_live_NCBI_XML',
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}}
    (directory / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    records.append(record)
    print(json.dumps({'case': name, 'rows': [{k: row.get(k) for k in
        ('run_id', 'exp_id', 'study_id', 'sample_id', 'total_bases', 'total_spots', 'size',
         'read_length', 'n_reads', 'library_layout', 'estimated_size')} for row in result]}))

assert not attempts
output = {'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
    'python': sys.version, 'lxml_version': etree.LXML_VERSION, 'source': str(source),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'cases': records,
    'exit_code': 0, 'acquisition_attempts': len(attempts), 'read_download': False,
    'live_BV_BRC_job': False, 'metadata_acquisition_receipt': str(NATIVE / 'receipt.json'),
    'memory_limit_bytes': 20 * 1024 ** 3, 'scratch_limit_bytes': 4 * 1024 ** 3,
    'wall_time_limit': None}
(OUT / 'receipt.json').write_text(json.dumps(output, indent=2) + '\n')
