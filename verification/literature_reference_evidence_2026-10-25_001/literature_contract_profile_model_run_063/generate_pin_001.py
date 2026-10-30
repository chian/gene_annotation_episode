from pathlib import Path
import ast
import difflib
import hashlib
import json
import shutil

repo = Path('/home/chia/repos/gene_annotation_episode')
base = repo / 'verification/literature_reference_evidence_2026-10-25_001'
accepted = base / 'a105_contract_information_design_059/connected_stage_004/pin_010'
original = base / 'literature_model_run_030/pin_001'
destination = base / 'literature_contract_profile_model_run_063'
pin = destination / 'pin_001'

def fingerprint(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')

assert fingerprint(accepted / 'PIN_MANIFEST.json')['sha256'] == '0a4e66d11cbbf3149bdc0d5f3a9424b4efe20ee2231e0987ed833281cce62a6d'
upstream = json.loads((accepted / 'PIN_MANIFEST.json').read_bytes())
assert len(upstream) == 1425
for name, row in upstream.items():
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert fingerprint(accepted / name) == row
    assert (accepted / name).resolve().is_relative_to(accepted.resolve())
assert fingerprint(original / 'SOURCE_MANIFEST.json')['sha256'] == '2616012239523f24d41ce1c9d04d08ab7bd6c75ee7f1e10943172e39b090c2df'
old_manifest = json.loads((original / 'SOURCE_MANIFEST.json').read_bytes())
input_rows = [row for row in old_manifest['files'] if row['pin_relative_path'].startswith('inputs/')]
assert len(input_rows) == 5
assert {row['pin_relative_path'] for row in input_rows} == {
    'inputs/JOB.txt', 'inputs/PRIMARY_ARTICLE_TEXT_001.txt', 'inputs/PRIMARY_PMC_001.html',
    'inputs/SOURCE_INPUT_METADATA.json', 'inputs/target.fna'}
for row in input_rows:
    assert fingerprint(original / row['pin_relative_path']) == {
        'bytes': row['size'], 'sha256': row['sha256']}
runner_old = original / 'runner/run_literature_source_job_019.py'
assert fingerprint(runner_old)['sha256'] == '45dd9a8fd93ce1777358cd7a23f3a25ead609aa23a56d0699a65c0c640c02a70'

destination.mkdir(exist_ok=False)
shutil.copytree(accepted, pin)
assert set(str(p.relative_to(pin)) for p in pin.rglob('*') if p.is_file()) == {
    *upstream, 'PIN_MANIFEST.json'}
for name, row in upstream.items():
    assert fingerprint(pin / name) == row
(pin / 'inputs').mkdir()
for row in input_rows:
    relative = row['pin_relative_path']
    shutil.copyfile(original / relative, pin / relative)
    assert fingerprint(pin / relative) == {'bytes': row['size'], 'sha256': row['sha256']}

before = runner_old.read_text(encoding='utf-8')
after = before
changes = [
    ('binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,\n',
     'binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,\n'
     '            contract_information_profile="operation_contract_information_v1",\n'),
    ('episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,\n',
     'episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,\n'
     '                contract_information_profile="operation_contract_information_v1",\n'),
    ('rendered = render_literature_experimental_prompt({\n',
     'rendered = render_literature_experimental_prompt({\n'
     '            "contract_information_profile": "operation_contract_information_v1",\n'),
    ('parent_rendered = render_literature_experimental_prompt({**parent_initial,\n',
     'parent_rendered = render_literature_experimental_prompt({**parent_initial,\n'
     '            "contract_information_profile": "operation_contract_information_v1",\n'),
    ('annotation_child_roles=("literature",))\n',
     'annotation_child_roles=("literature",), decision_protocol="decision_exchange_v1")\n'),
]
for old, new in changes:
    assert after.count(old) == 1, old
    after = after.replace(old, new)
reversed_text = after
for old, new in reversed(changes):
    assert reversed_text.count(new) == 1
    reversed_text = reversed_text.replace(new, old)
assert reversed_text == before
ast.parse(after)  # syntax only; no import/application execution
(pin / 'runner').mkdir()
runner_new = pin / 'runner/run_literature_source_job_062.py'
with runner_new.open('x', encoding='utf-8') as stream:
    stream.write(after)
with (destination / 'RUNNER_DIFF_001.patch').open('x', encoding='utf-8') as stream:
    stream.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='original030/runner/run_literature_source_job_019.py',
        tofile='new063/runner/run_literature_source_job_062.py'))

rows = []
for path in sorted(pin.rglob('*')):
    if not path.is_file():
        continue
    assert path.resolve().is_relative_to(pin.resolve())
    name = str(path.relative_to(pin))
    fp = fingerprint(path)
    origin = ('accepted059_pin010' if name in upstream or name == 'PIN_MANIFEST.json'
              else 'original030_inputs' if name.startswith('inputs/') else 'proposal062_runner_delta')
    rows.append({'pin_relative_path': name, 'size': fp['bytes'], 'sha256': fp['sha256'], 'origin': origin})
assert len(rows) == 1432
save(pin / 'SOURCE_MANIFEST.json', {'version': 'literature_source_pin_v1', 'files': rows})
for name, row in upstream.items():
    assert fingerprint(pin / name) == row and fingerprint(accepted / name) == row
for row in input_rows:
    expected = {'bytes': row['size'], 'sha256': row['sha256']}
    assert fingerprint(pin / row['pin_relative_path']) == expected
    assert fingerprint(original / row['pin_relative_path']) == expected
save(destination / 'GENERATION_RECEIPT_001.json', {
    'status': 'metadata_generation_only', 'new_pin': str(pin), 'files': len(rows),
    'source_manifest': fingerprint(pin / 'SOURCE_MANIFEST.json'),
    'runner': fingerprint(runner_new), 'runner_diff': fingerprint(destination / 'RUNNER_DIFF_001.patch'),
    'upstream_manifest': fingerprint(pin / 'PIN_MANIFEST.json'),
    'original_input_manifest': fingerprint(original / 'SOURCE_MANIFEST.json'),
    'model_launched': False, 'source_interpreted': False, 'application_imported': False,
    'dependency_preflight': 'still required', 'offline_preparation': 'still requires release',
    'configured_model_execution': 'still requires separate root release'})
print(json.dumps({'status': 'metadata_generation_only', 'files': len(rows), 'pin': str(pin)}))
