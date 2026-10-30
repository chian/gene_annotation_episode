"""Export frozen provider and retained native fixtures, with explicit provenance."""
from copy import deepcopy
import base64
import hashlib
import importlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

source, output, original_legacy = [Path(v).resolve() for v in sys.argv[1:]]
sys.dont_write_bytecode = True
sys.path.insert(0, str(source))
sys.path.insert(1, str(source / 'tests'))
provider_fixture = importlib.import_module('test_bvbrc_fastqutils_cutadapt_provider')
return_fixture = importlib.import_module('test_bvbrc_fastqutils_returns')
reader_fixture = importlib.import_module('test_bvbrc_fastqutils_cutadapt_reader')
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils
from gene_annotation_episode.bvbrc_fastqutils_tool_info import fastqutils_tool_contracts


def forbidden(*args, **kwargs):
    raise AssertionError('Fixture export attempted network or native execution')


socket.socket.connect = forbidden
socket.create_connection = forbidden
urllib.request.OpenerDirector.open = forbidden
subprocess.Popen = forbidden
subprocess.run = forbidden


def save(name, value):
    with (output / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def packed_case(data, fields, provenance):
    body, sheet, components = return_fixture.saved_fixture(data, fields)
    saved = body['publication']['adapter_result']
    expected = {k: deepcopy(saved[k]) for k in
        ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    expected.update(sheet=sheet, components=components)
    return dict(provenance=provenance,
        inputs=dict(bundle=data[0], artifact_bytes_base64={k: base64.b64encode(v).decode('ascii') for k, v in data[1].items()},
            supplied_values=data[2], parameters=data[3], requested_form=body['publication_inputs']['selector']['requested_schema']),
        expected=expected, saved_publication=body, communication=return_fixture.projected((body, sheet, components)))


data, fields = provider_fixture.fixture()
cases = {'native': packed_case(data, fields, 'Genuine retained Trim Galore 0.6.10/Cutadapt 4.9 output on synthetic reads; synthetic provider/return envelopes.')}
raw = (provider_fixture.NATIVE / 'synthetic.fastq_trimming_report.txt').read_bytes()
data, fields = provider_fixture.fixture(raw.replace(b'This is cutadapt 4.9', b'This is cutadapt 4.8'))
cases['wrong_version'] = packed_case(data, fields, 'Deliberately mutated version in retained native report; synthetic provider envelope.')
data, fields = provider_fixture.fixture()
data[0]['artifacts'][0]['transfer']['object_complete'] = 'no'
cases['partial'] = packed_case(data, fields, 'Retained native bytes with deliberately partial transfer declaration; synthetic provider envelope.')
data, fields = return_fixture.f.seven_family_data()
cases['seven_family_synthetic'] = packed_case(data, fields, 'Existing handcrafted numerical provider/return fixture; no live service or host custody.')
save('provider_cases.json', cases)

template = json.loads((source / 'tests/fixtures/bvbrc_fastqutils/reports/saved_native_sheet.json').read_text())
direct = []
for name, base in [('cutadapt_single', reader_fixture.INITIAL), ('cutadapt_filtered', reader_fixture.INITIAL),
                   ('cutadapt_empty', reader_fixture.INITIAL), ('zero_bases', reader_fixture.WARNINGS)]:
    raw = reader_fixture.native(name, base)
    doc = reader_fixture.parse(raw)
    row = dict(case=name, provenance='Actual retained Cutadapt 4.9 execution on synthetic inputs; direct helper only, not Trim Galore or standalone dispatch.',
        raw_base64=base64.b64encode(raw).decode('ascii'), context=reader_fixture.context(raw), expected_document=doc,
        native_oracle=json.loads((base / name / 'native.json').read_text()),
        original_receipt=json.loads((base / name / 'receipt.json').read_text()))
    if name != 'cutadapt_empty':
        original = deepcopy(template['original_task'])
        original['submission_receipt_ref'] = doc['artifact']['task_ref']
        metadata = extract_fastqutils_metadata(original, analysis_id=doc['analysis_id'],
            metadata_bindings=[], supplied_values=[], documents=[doc])
        resolution = dict(document_id=doc['document_id'], selection=dict(kind='possessed_content', content=doc['artifact']['content_binding']),
            state='available', matched_contents=[doc['artifact']['content_binding']], artifact_ref=doc['artifact']['id'],
            requirement_refs=[], diagnostic_codes=[])
        sheet = populate_fastqutils_sheet([doc], metadata=metadata, document_resolutions=[resolution])
        before, after = [reader_fixture.total(doc, metric) for metric in ('cutadapt_processed_bases', 'cutadapt_written_bases')]
        edge = next(e for e in doc['native_lineage'] if e['before_population_ref'] == before['population_ref'])
        job = dict(calculation_id='base_retention', method='retention_v1', state='ready',
            population_refs=[before['population_ref'], after['population_ref']],
            operand_measurement_refs=[before['id'], after['id']], comparison_kind='base_retention',
            quality_thresholds=[], read_key_rule=None, lineage_ref=edge['id'],
            lineage_basis=dict(basis='native_report', metadata_id=None, evidence=None, declaration=None, native_lineage_ref=edge['id']),
            requirement_refs=[], diagnostic_codes=[])
        parameters = dict(version='fastqutils_calculators_v2', analysis_id=sheet['analysis_id'], calculations=[job])
        row.update(sheet=sheet, parameters=parameters, components=calculate_fastqutils(sheet, parameters=parameters))
    direct.append(row)
save('direct_native_cases.json', direct)

# Preserve original legacy bytes rather than regenerating or normalizing them.
legacy_files = ['requested_schema.json', 'provider_result.json', 'bundle.json', 'parameters.json']
(output / 'legacy').mkdir()
for name in legacy_files:
    (output / 'legacy' / name).write_bytes((original_legacy / name).read_bytes())
deps = {name: hashlib.sha256((source / 'gene_annotation_episode' / name).read_bytes()).hexdigest()
        for name in adapter._DEPENDENCIES}
tool = fastqutils_tool_contracts(resource_id='selected-api', assignment_schema={'type': 'object'})[0]
save('meta.json', dict(provider_pin=adapter.implementation_sha256(), dependency_order=list(adapter._DEPENDENCIES), dependency_hashes=deps,
    tool_info=tool, qualification='Source baseline for an isolated extracted-wheel verification. No host execution or live BV-BRC.'))
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(source / name.split('.')[0]), (name, path)
        origins[name] = str(path)
print(json.dumps(dict(provider_case_count=len(cases), direct_native_case_count=len(direct), provider_pin=adapter.implementation_sha256(),
    source_origins=origins, dependency_count=len(deps))))
