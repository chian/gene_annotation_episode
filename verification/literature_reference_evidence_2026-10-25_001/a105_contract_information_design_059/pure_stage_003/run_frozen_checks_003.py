"""Execute only the released pure-contract checks in the supplied frozen pin."""
import hashlib
import json
from pathlib import Path
import sys

PIN = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(PIN), str(PIN / 'tests')]


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write('\n')


def main():
    manifest = json.loads((PIN / 'PIN_MANIFEST.json').read_bytes())
    def verify():
        for name, row in manifest.items():
            assert fingerprint(PIN / name) == row, name
    verify()
    import pytest
    code = pytest.main(['-q', str(PIN / 'tests/test_schema_information_text.py'),
        str(PIN / 'tests/test_episode_contract_information.py'), '--tb=short', '-p', 'no:cacheprovider'])
    assert code == 0
    from gene_annotation_episode.episode_contract_information import (
        operation_contract_information, return_contract_information, expand_fact_form, validate_saved_fact_form)
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
    from gene_annotation_episode.schema_information_text import parse_schema_information, schema_fingerprint
    from gene_annotation_episode.domain import obj
    operations = _population_catalog()
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    examples = []
    for row in operations:
        outcome = operation_contract_information(catalog=operations, operation=row['name'])
        result = outcome['result']
        assert schema_fingerprint(parse_schema_information(result['text'])) == schema_fingerprint(row['input_schema'])
        examples.append(outcome)
    for source, row in facts.items():
        outcome = return_contract_information(facts_by_role={'literature': facts}, permitted_child_roles=['literature'],
            role='literature', source=source)
        result = outcome['result']
        assert schema_fingerprint(parse_schema_information(result['text'])) == schema_fingerprint(row['report_schema'])
        examples.append(outcome)
    save('ACTUAL_SCHEMA_EXAMPLES_003.json', examples)
    forms = []
    for source in facts:
        submitted = json.dumps(obj({'chosen_' + source: {'$ref': 'episode-fact:' + source}}), separators=(',', ':'))
        result = expand_fact_form(submitted, child_role='literature', facts_by_role={'literature': facts},
                                  permitted_child_roles=['literature'])
        assert validate_saved_fact_form(child_role='literature', submitted_schema_json=submitted,
            expanded_schema=result['expanded_schema'], declaration=result['declaration']) == result['expanded_schema']
        forms.append({'source': source, **result})
    save('ACTUAL_FACT_FORM_EXAMPLES_003.json', forms)
    imported = {}
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('gene_annotation_episode', 'method_loop', 'test_schema_information_text', 'test_episode_contract_information')) and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN), name
            imported[name] = str(path.relative_to(PIN))
    verify()
    receipt = {'pytest_exit_code': int(code), 'pin_files_verified_before_after': len(manifest),
        'pin_manifest_sha256': fingerprint(PIN / 'PIN_MANIFEST.json')['sha256'],
        'verified_imports': imported, 'actual_operation_examples': len(operations),
        'actual_fact_examples': len(facts), 'actual_form_examples': len(forms),
        'scope': 'Pure contract schemas and synthetic forms only; no Store/provider/runtime/source/scientific operation',
        'model_calls': 0, 'actions': 0, 'observations': 0, 'C1_C4_authentication_claim': False}
    save('WORKER_RECEIPT_003.json', receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'verified_imports'}))


if __name__ == '__main__':
    main()
