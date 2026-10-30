"""Independent metadata-only generation proof, without importing the application."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
NEW = BASE / 'literature_contract_profile_model_run_063'
PIN = NEW / 'pin_001'
UPSTREAM = BASE / 'a105_contract_information_design_059/connected_stage_004/pin_010'
ORIGINAL = BASE / 'literature_model_run_030/pin_001'


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    assert fingerprint(UPSTREAM / 'PIN_MANIFEST.json')['sha256'] == '0a4e66d11cbbf3149bdc0d5f3a9424b4efe20ee2231e0987ed833281cce62a6d'
    assert fingerprint(ORIGINAL / 'SOURCE_MANIFEST.json')['sha256'] == '2616012239523f24d41ce1c9d04d08ab7bd6c75ee7f1e10943172e39b090c2df'
    rows = json.loads((PIN / 'SOURCE_MANIFEST.json').read_bytes())['files']
    names = set()
    for row in rows:
        name = row['pin_relative_path']
        path = PIN / name
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert name not in names and path.resolve().is_relative_to(PIN.resolve())
        names.add(name)
        assert fingerprint(path) == {'bytes': row['size'], 'sha256': row['sha256']}, name
    assert len(names) == 1432
    actual = {str(path.relative_to(PIN)) for path in PIN.rglob('*') if path.is_file()}
    assert actual == names | {'SOURCE_MANIFEST.json'}, sorted(actual ^ names ^ {'SOURCE_MANIFEST.json'})
    upstream = json.loads((UPSTREAM / 'PIN_MANIFEST.json').read_bytes())
    assert len(upstream) == 1425
    for name, expected in upstream.items():
        assert fingerprint(PIN / name) == expected == fingerprint(UPSTREAM / name), name
    assert (PIN / 'PIN_MANIFEST.json').read_bytes() == (UPSTREAM / 'PIN_MANIFEST.json').read_bytes()
    inputs = [row for row in json.loads((ORIGINAL / 'SOURCE_MANIFEST.json').read_bytes())['files']
              if row['pin_relative_path'].startswith('inputs/')]
    assert {row['pin_relative_path'] for row in inputs} == {
        'inputs/JOB.txt', 'inputs/PRIMARY_ARTICLE_TEXT_001.txt', 'inputs/PRIMARY_PMC_001.html',
        'inputs/SOURCE_INPUT_METADATA.json', 'inputs/target.fna'}
    for row in inputs:
        name = row['pin_relative_path']
        expected = {'bytes': row['size'], 'sha256': row['sha256']}
        assert fingerprint(PIN / name) == expected == fingerprint(ORIGINAL / name), name
    before = (ORIGINAL / 'runner/run_literature_source_job_019.py').read_text()
    after = (PIN / 'runner/run_literature_source_job_062.py').read_text()
    assert hashlib.sha256(before.encode()).hexdigest() == '45dd9a8fd93ce1777358cd7a23f3a25ead609aa23a56d0699a65c0c640c02a70'
    reversed_text = after
    substitutions = [
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
         'annotation_child_roles=("literature",), decision_protocol="decision_exchange_v1")\n')]
    for old, new in reversed(substitutions):
        assert reversed_text.count(new) == 1
        reversed_text = reversed_text.replace(new, old)
    assert reversed_text == before
    ast.parse(after)
    expected_diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='original030/runner/run_literature_source_job_019.py',
        tofile='new063/runner/run_literature_source_job_062.py'))
    assert (NEW / 'RUNNER_DIFF_001.patch').read_text() == expected_diff
    added = names - set(upstream) - {'PIN_MANIFEST.json'}
    assert added == {*(row['pin_relative_path'] for row in inputs), 'runner/run_literature_source_job_062.py'}
    result = {'scope': 'Independent root metadata-only proof; no application import, source decoding, model or runtime work',
        'manifest_entries_verified': len(rows), 'unmanifested_pin_files': [], 'exact_upstream_entries_verified': len(upstream),
        'upstream_manifest_byte_identical': True, 'opaque_original_inputs_verified': len(inputs),
        'exact_runner_substitutions_reversed': len(substitutions), 'runner_ast_syntax': 'valid',
        'full_unified_diff_exact': True, 'added_files': sorted(added),
        'new_source_manifest': fingerprint(PIN / 'SOURCE_MANIFEST.json'),
        'new_runner': fingerprint(PIN / 'runner/run_literature_source_job_062.py'),
        'not_proved': ['imports/dependencies/contract preflight', 'source-registering offline preparation',
                       'actual model selection', 'scientific numerical work', 'new typed delivery or reconstruction'],
        'application_imports': 0, 'model_calls': 0, 'runtime_observations': 0}
    with (HERE / 'GENERATION_ROOT_RECEIPT_003.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('manifest_entries_verified', 'exact_upstream_entries_verified',
        'opaque_original_inputs_verified', 'exact_runner_substitutions_reversed', 'application_imports', 'model_calls')}))


if __name__ == '__main__':
    main()
