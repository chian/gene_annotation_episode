"""Build a resource launch packet from exact templates and metadata copies only."""
from pathlib import Path
import difflib
import hashlib
import json

P = Path(__file__).resolve().parent
TEMPLATE = Path('/tmp/configured-literature-launch-plan-20261022-001-li2s253s')
COPY = Path('/tmp/configured-resource-preparation-output-handoff-20261022-001-0c8q1ose')
VERIFY = Path('/tmp/configured-resource-actual-verifier-20261022-001-BAWpJPut/VERIFICATION_ACTUAL001.json')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
ROOT_INVOCATION = Path('/tmp/configured-resource-investigation-root-preparation-20261022-001/INVOCATION001.json')
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'

def d(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def save(name, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with (P / name).open('xb') as stream:
        stream.write(raw)

def load(path):
    return json.loads(path.read_bytes())

assert d(COPY / 'MANIFEST_FINAL001.json')['sha256'] == '38729c8fe75993301ba1bc5c2a22b037d0508840caf5485b4ee28860b80568f5'
for name, expected in load(COPY / 'MANIFEST_FINAL001.json')['members'].items():
    actual = d(COPY / name)
    assert all(actual[key] == expected[key] for key in ('sha256', 'bytes'))
assert d(VERIFY)['sha256'] == '764be765e71d3354ca64aa8372f71b7592629b2c9512b5257a38378c765d7964'
verification = load(VERIFY)
assert verification['status'] == 'verified_prepared_not_started'
assert verification['external_preparation_exit_code'] == 0
assert verification['source_pin'] == {'file_count': 137, 'sha256': PIN}
assert verification['external_preparation_process_receipt']['sha256'] == 'c837af2fc9bd11851598d65ce064c4c1c33f53f87b3f120cd60824a027c7612d'

replacements = [
    ('configured_literature_localization_001', 'configured_resource_investigation_001'),
    ('configured-literature-localization-launch-20261022-001', 'configured-resource-investigation-launch-20261022-001'),
    ('configured_literature_launch_driver_', 'configured_resource_launch_driver_'),
    ('configured_literature_first_request_proof_', 'configured_resource_first_request_proof_'),
]
diffs = {}
for name, expected in [('launch_driver001.py', '98bdba2f453eb5326b5c57f8e0d93809cc47fffc1469e586cf791f3c8f06792e'),
                       ('inspect_first_request001.py', 'd7add9b635dce741a3722dc4169c82ec55925c510e4b57d430ca53feab2daea2')]:
    original = (TEMPLATE / name).read_bytes()
    assert hashlib.sha256(original).hexdigest() == expected
    modified = original.decode()
    for before, after in replacements:
        modified = modified.replace(before, after)
    save(name, modified.encode())
    diffname = name.removesuffix('.py') + '-vs-template001.patch'
    diff = ''.join(difflib.unified_diff(original.decode().splitlines(keepends=True), modified.splitlines(keepends=True),
        fromfile=str(TEMPLATE / name), tofile=str(P / name)))
    save(diffname, diff.encode())
    diffs[name] = {'original': d(TEMPLATE / name), 'modified': d(P / name), 'full_diff': d(P / diffname)}

sources = {
    'PREPARATION_RESULT001.json': COPY / 'run/caller-inputs/PREPARATION_RESULT001.json',
    'C_RESULT001.json': COPY / 'run/caller-inputs/C_RESULT001.json',
    'parameters.json': COPY / 'run/caller-inputs/parameters.json',
    'config.toml': COPY / 'run/caller-inputs/config.toml',
    'focus.txt': COPY / 'run/caller-inputs/focus.txt',
    'case-launch.json': COPY / 'run/case-launch.json',
    'scientific-checkpoint-fork.json': COPY / 'run/workspace/scientific-checkpoint-fork.json',
    'PREPARATION_INVOCATION001.json': COPY / 'root-invocation/INVOCATION001.json',
}
members = {}
for name, source in sources.items():
    save('prepared-' + name, source.read_bytes())
    if name == 'case-launch.json':
        target = RUN / name
    elif name == 'scientific-checkpoint-fork.json':
        target = RUN / 'workspace' / name
    elif name == 'PREPARATION_INVOCATION001.json':
        target = ROOT_INVOCATION
    else:
        target = RUN / 'caller-inputs' / name
    members[name] = {**d(source), 'path': str(target)}

prepared = load(P / 'prepared-PREPARATION_RESULT001.json')
assert d(P / 'prepared-PREPARATION_RESULT001.json')['sha256'] == 'adc2d3ff19ad2c97c4b162d5a59a7ab597a78d8ca972b873d75f9434fb2d9671'
assert prepared['parameters']['sha256'] == '651d132265e6c7b974dd06c152ed6498b2c5b4ed5bae0130836278743695b6cb'
assert prepared['working_database_after_prepare']['sha256'] == 'c8b8529c643f7bf2a3eaab690cae04510856b3290698143c92d28487ba70d68a'
assert d(P / 'prepared-scientific-checkpoint-fork.json')['sha256'] == '91ff42c4aff373a041dfb25e9940d095f32ae4ff0a8145e854e242931440e0fd'
save('INDEPENDENT_PREPARATION_VERIFICATION001.json', VERIFY.read_bytes())
save('CHECKPOINT_TABLE_METADATA001.json', (COPY / 'run/workspace/checkpoint/tables.json').read_bytes())

argv = ['/home/chia/repos/gene_annotation_episode/.venv/bin/python', '-m', 'gene_annotation_episode.case_execution', 'run',
    '--run-dir', str(RUN), '--policy', str(CODE / 'gene_annotation_episode/api_planning_case_policy.py'),
    '--parameters', str(RUN / 'caller-inputs/parameters.json')]
command = {'version': 'configured_resource_investigation_launch_command_v1', 'status': 'unadopted_not_executed',
    'argv': argv, 'cwd': str(CODE),
    'environment_overrides': {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(CODE)},
    'runtime_pin': PIN, 'runtime_files': 137,
    'policy_source_sha256': '4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f',
    'inputs': members, 'working_database_before_launch': prepared['working_database_after_prepare'],
    'native_registry_ref': prepared['native_registry_ref'],
    'public_search_registry_ref': prepared['public_search_registry_ref'],
    'launch_evidence_directory': '/tmp/configured-resource-investigation-launch-20261022-001',
    'resume': False, 'timeout': None, 'retry': False, 'cancellation': False,
    'preparation_manifest': d(COPY / 'MANIFEST_FINAL001.json'),
    'prepared_result_descriptor': d(sources['PREPARATION_RESULT001.json']),
    'external_preparation_invocation': {**d(sources['PREPARATION_INVOCATION001.json']), 'path': str(ROOT_INVOCATION)},
    'independent_preparation_verification': d(VERIFY), 'historical_working_hashes_equal_observed': True}
save('LAUNCH_COMMAND_DRAFT001.json', command)
save('ADAPTATION001.json', {'version': 'resource_launch_template_adaptation_v1',
    'template_manifest': d(TEMPLATE / 'MANIFEST_FINAL001.json'), 'exact_text_replacements': replacements,
    'code_diffs': diffs, 'copied_preparation_metadata_manifest': d(COPY / 'MANIFEST_FINAL001.json'),
    'copied_prepared_sources': {name: d(source) for name, source in sources.items()},
    'additional_pinned_input': 'Actual root preparation invocation is an eighth prepared operand; driver/helper already validate every declared input.',
    'independent_verification': d(VERIFY), 'static_authoring_only': True,
    'application_imports': 0, 'database_opens': 0, 'launches': 0, 'helper_invocations': 0})
print(json.dumps({'status': 'static_inputs_built_not_launched_or_inspected', 'root': str(P),
    'launch_command': d(P / 'LAUNCH_COMMAND_DRAFT001.json'), 'driver': d(P / 'launch_driver001.py'),
    'helper': d(P / 'inspect_first_request001.py')}, sort_keys=True))
