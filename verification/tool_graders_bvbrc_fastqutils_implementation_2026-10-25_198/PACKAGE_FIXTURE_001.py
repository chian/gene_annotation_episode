"""Export the already-tested synthetic provider fixture from the frozen source."""
from copy import deepcopy
import base64
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
source, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
sys.path.insert(0, str(source))
spec = importlib.util.spec_from_file_location('frozen_fastq_fixture',
    source / 'tests/test_bvbrc_fastqutils_returns.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
data, fields = fixture.f.seven_family_data()
body, sheet, components = fixture.saved_fixture(data, fields)
bundle, native_bytes, supplied, parameters = data
saved = body['publication']['adapter_result']
expected = {key: deepcopy(saved[key]) for key in
    ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
expected.update(sheet=sheet, components=components)
values = {
    'provider_input.json': {'bundle': bundle,
        'artifact_bytes_base64': {key: base64.b64encode(raw).decode('ascii') for key, raw in native_bytes.items()},
        'supplied_values': supplied, 'parameters': parameters,
        'requested_form': body['publication_inputs']['selector']['requested_schema']},
    'provider_result.json': expected,
    'saved_publication.json': body,
    'communication.json': fixture.projected((body, sheet, components)),
}
for name, value in values.items():
    with (output / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(source / name.split('.')[0]), (name, path)
        origins[name] = str(path)
print(json.dumps({'provider_pin': fixture.adapter.implementation_sha256(),
    'source_origins': origins, 'qualification': 'Previously tested synthetic fixture; no host custody or live service.'}))
