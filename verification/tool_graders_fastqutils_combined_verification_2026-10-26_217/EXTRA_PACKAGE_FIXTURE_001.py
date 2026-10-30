"""Export retained SRA/SAMstat cases and immutable historical 208 evidence."""
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

source, out, old_specimen = map(lambda p: Path(p).resolve(), sys.argv[1:])
sys.path.insert(0, str(source))
sys.path.insert(1, str(source / 'tests'))
returns = importlib.import_module('test_bvbrc_fastqutils_returns')
mapping = importlib.import_module('test_bvbrc_fastqutils_samstat_mapping')
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS


def denied(*args, **kwargs):
    raise AssertionError('Fixture export attempted network or native execution')


socket.socket.connect = denied
socket.create_connection = denied
urllib.request.OpenerDirector.open = denied
subprocess.Popen = denied
subprocess.run = denied


def save(name, value):
    with (out / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def pack(data, fields, provenance):
    body, sheet, components = returns.saved_fixture(data, fields)
    saved = body['publication']['adapter_result']
    result = {k: deepcopy(saved[k]) for k in
              ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    result.update(sheet=sheet, components=components)
    return dict(provenance=provenance, inputs=dict(bundle=data[0],
        artifact_bytes_base64={k: base64.b64encode(v).decode() for k, v in data[1].items()},
        supplied_values=data[2], parameters=data[3],
        requested_form=body['publication_inputs']['selector']['requested_schema']),
        expected=result, saved_publication=body,
        communication=returns.projected((body, sheet, components)))


cases = {}
for family, expected in [('legacy', [[10, 11], [5, 11]]), ('current', [[9, 10], [4, 10]])]:
    case = pack(mapping.fixture_data(family), mapping.fields('available_value'),
                'Retained SAMstat producer output on synthetic alignment input; synthetic provider/publication envelope.')
    case['independent_expected_numerator_denominator'] = expected
    cases[family] = case
raw = (source / 'tests/fixtures/bvbrc_fastqutils/sra/native_selected_run.json').read_bytes()
data = returns.f.build({'sra': (raw, 'sra_metadata')})
fields = {name: returns.f.selection('measurement', returns.f.measurement('sra', metric, 'sra_run'),
                                  availability='available_value') for name, (metric, *_) in SRA_FIELDS.items()}
fields['requirements'] = returns.f.selection('requirements')
cases['sra'] = pack(data, fields, 'Retained real p3-sra output from earlier acquired NCBI metadata; no fresh acquisition; synthetic provider/publication envelope.')
save('extra_provider_cases.json', cases)
old_path = old_specimen / 'provider_cases.json'
old = json.loads(old_path.read_text())['native']
save('historical208_native.json', old)
provenance = {
    'samstat': json.loads((source / 'tests/fixtures/bvbrc_fastqutils_samstat_mapping/PROVENANCE.json').read_text()),
    'sra': json.loads((source / 'tests/fixtures/bvbrc_fastqutils/sra/SOURCE_RECEIPT.json').read_text()),
    'historical208_provider_cases': dict(path=str(old_path), sha256=hashlib.sha256(old_path.read_bytes()).hexdigest()),
    'scope': 'No new scientific acquisition or producer execution. Provider envelopes are synthetic; no host/Workflow claim.',
}
save('extra_provenance.json', provenance)
print(json.dumps(dict(cases=list(cases), historical208_source_sha256=provenance['historical208_provider_cases']['sha256'])))
