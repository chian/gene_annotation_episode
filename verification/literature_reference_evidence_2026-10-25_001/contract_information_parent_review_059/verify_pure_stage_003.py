"""Authenticate059 pure helpers and their executed pin; no runtime/source work."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
STAGE = BASE / 'a105_contract_information_design_059/pure_stage_003'
RUN = STAGE / 'frozen_checks_003'
PIN = RUN / 'pin'
sys.path.insert(0, str(PIN))
from gene_annotation_episode import episode_contract_information as api
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.schema_information_text import parse_schema_information, schema_fingerprint


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden(*args, **kwargs):
    raise AssertionError('Saved-form validation cannot call current fact factories')


def main():
    manifest = load(STAGE / 'MANIFEST_003.json')['entries']
    for name, row in manifest.items():
        path = ROOT / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    pin = load(PIN / 'PIN_MANIFEST.json')
    for name, row in pin.items():
        path = PIN / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    delivery = load(STAGE / 'DELIVERY_RECEIPT_003.json')
    for name, row in delivery['owned_files'].items():
        assert digest(ROOT / name) == row['sha256'] == digest(PIN / name)
    before = load(STAGE / 'BEFORE_003.json')
    for name, row in before['read_only_dependencies'].items():
        assert digest(ROOT / name) == row['sha256'] == digest(PIN / name)
    terminal = load(RUN / 'TERMINAL_RECEIPT_003.json')
    worker = load(RUN / 'WORKER_RECEIPT_003.json')
    assert terminal['exit_code'] == worker['pytest_exit_code'] == 0
    assert digest(PIN / 'PIN_MANIFEST.json') == terminal['pin_manifest_sha256'] == worker['pin_manifest_sha256']
    assert '167 passed in 3.00s' in (RUN / 'TERMINAL_003.log').read_text()
    rebuilt = OUT / 'reconstructed_pure_stage_003'
    rebuilt.mkdir()
    result = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(STAGE / 'IMPLEMENTATION_003.patch')],
                            cwd=rebuilt, capture_output=True, text=True)
    assert result.returncode == 0 and 'offset' not in result.stdout and 'fuzz' not in result.stdout, result.stdout + result.stderr
    for name, row in delivery['owned_files'].items():
        assert digest(rebuilt / name) == row['sha256'], name
    catalog = _population_catalog()
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    examples = load(RUN / 'ACTUAL_SCHEMA_EXAMPLES_003.json')
    fresh = [api.operation_contract_information(catalog=catalog, operation=row['name']) for row in catalog]
    fresh += [api.return_contract_information(facts_by_role={'literature': facts}, permitted_child_roles=['literature'],
                                            role='literature', source=name) for name in facts]
    assert fresh == examples and len(fresh) == 37
    for outcome in fresh:
        record = outcome['result']
        schema = record.get('input_schema', record.get('report_schema'))
        assert schema_fingerprint(parse_schema_information(record['text'])) == schema_fingerprint(schema)
    forms = load(RUN / 'ACTUAL_FACT_FORM_EXAMPLES_003.json')
    assert len(forms) == 18
    with patch.object(api, '_fact', forbidden), patch.object(LiteratureEpisodes, '_rate_fact_sources', forbidden):
        for example in forms:
            declaration = example['declaration']
            actual = api.validate_saved_fact_form(child_role=declaration['child_role'],
                submitted_schema_json=declaration['submitted_schema_json'],
                expanded_schema=example['expanded_schema'], declaration=declaration)
            assert actual == example['expanded_schema']
    imports = 0
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('gene_annotation_episode', 'method_loop')) and getattr(module, '__file__', None):
            assert Path(module.__file__).resolve().is_relative_to(PIN), name
            imports += 1
    receipt = {'passed': True, 'delivery_entries_verified': len(manifest),
        'executed_python_pin_entries_verified': len(pin), 'new_files_reconstructed': len(delivery['owned_files']),
        'actual_full_information_outcomes_reproduced': len(fresh), 'saved_forms_revalidated_with_fact_factories_forbidden': len(forms),
        'root_imports_from_executed_pin': imports,
        'owner_final_targeted_terminal': '167 passed in3.00s', 'root_test_suite_rerun': False,
        'scope': 'Pure information/typed-form consistency; no registered profile/lookup/decoder/commission/C1/C4/model/scientific integration claim'}
    with (OUT / 'PURE_STAGE_RECEIPT_003.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
