"""Reproduce057 child interfaces offline in a new root-owned synthetic Store."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'a105_model_execution_design_057'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE / 'DELIVERY_MANIFEST_001.json').read_bytes())
    for name, row in manifest.items():
        path = SOURCE / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    spec = importlib.util.spec_from_file_location('root_measure_057', SOURCE / 'measure_synthetic_001.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    dependencies = ['gene_annotation_episode/' + name for name in (
        'runtime.py', 'providers.py', 'literature_episodes.py', 'literature_experimental_prompt.py',
        'literature_reference_parent_prompt.py', 'composition_information.py', 'scientific_process_prompt.py',
        'literature_binding_interaction_inputs.py', 'literature_binding_interaction_storage.py',
        'literature_kinetic_inputs.py', 'literature_kinetic_storage.py')]
    before = {name: digest(ROOT / name) for name in dependencies}
    with contextlib.redirect_stdout(io.StringIO()):
        module.main()
    result = json.loads((OUT / 'SCHEMA_MEASUREMENTS_001.json').read_bytes())
    expected = json.loads((SOURCE / 'SCHEMA_MEASUREMENTS_001.json').read_bytes())
    assert result == expected
    after = {name: digest(ROOT / name) for name in dependencies}
    assert before == after
    assert all(value == 0 for value in result['runtime_counts'].values())
    child = result['literature_child']
    second = json.loads((SOURCE / 'SCHEMA_MEASUREMENTS_002.json').read_bytes())
    parent_text = SOURCE / 'synthetic_measurement_002/parent_model_text.txt'
    assert parent_text.stat().st_size == second['parent']['recurring_model_text']['utf8_bytes']
    assert digest(parent_text) == second['parent']['recurring_model_text']['sha256']
    assert result['component_selection_leaves_catalog_equal']
    receipt = {'passed': True, 'manifest_entries_verified': len(manifest),
        'complete_child_measurement_exactly_reproduced': True,
        'unchanged_current_dependencies': before,
        'population_operations': result['population_operation_count'],
        'child_recurring_text_bytes': child['recurring_model_text']['utf8_bytes'],
        'child_provider_output_schema_bytes': child['provider_output_schema']['utf8_bytes'],
        'parent_saved_text_bytes_authenticated': parent_text.stat().st_size,
        'runtime_counts': result['runtime_counts'], 'scientific_sources': 0,
        'provider_acceptance_or_model_extraction_claim': False,
        'scope': 'Offline synthetic interface reproduction; full child fields exact, parent saved text authenticated, no model/backend acceptance inference'}
    with (OUT / 'MODEL_INTERFACE_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in receipt.items() if key != 'unchanged_current_dependencies'}))


if __name__ == '__main__':
    main()
