"""Frozen scientific test process, executed only by the bounded packet launcher."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(os.environ['HIC_EXTRA_SITE'])

import numpy
import zlib

def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}

Path('DEPENDENCIES.json').write_text(json.dumps({'python': sys.version,
    'numpy': importlib.metadata.version('numpy'), 'numpy_file': pin(numpy.__file__),
    'jsonschema': importlib.metadata.version('jsonschema'),
    'zlib_compile': zlib.ZLIB_VERSION, 'zlib_runtime': zlib.ZLIB_RUNTIME_VERSION}, indent=2) + '\n')

suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or ['tests.test_chromatin_hic_inputs'])
result = unittest.TextTestRunner(verbosity=2).run(suite)
Path('TEST_RESULT.json').write_text(json.dumps({'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
    'skips': len(result.skipped), 'successful': result.wasSuccessful()}, indent=2) + '\n')

checkable = []
summary = {'production_sources': [pin(Path(__file__).parent / 'gene_annotation_episode' / name) for name in (
    'chromatin_hic_inputs.py', 'chromatin_hic_binary.py', 'chromatin_hic_records.py',
    'chromatin_hic_table_validation.py', 'chromatin_interaction_contracts.py',
    'chromatin_interaction_inputs.py', 'chromatin_interaction_tables.py',
    'chromatin_interaction_calculations.py')], 'native_cases': []}
for directory in sorted(Path('hic_cases').iterdir()):
    extraction_path = directory / 'extraction.json'
    if not extraction_path.is_file():
        continue
    request = json.loads((directory / 'request.json').read_text())
    extraction = json.loads(extraction_path.read_text())
    item = {'case_directory': str(directory.resolve()), 'input': request['contact']['file'],
        'origin': (directory / 'origin.txt').read_text().strip(),
        'normalization': request['normalization'],
        'populations': [{'population_key': p['population_key'], 'selected_region': p['selected_region'],
                        'extent': p['extent'], 'counts': p['raw_cell_population'],
                        'read_evidence': p['read_evidence']} for p in extraction['populations']],
        'failure_codes': [f['code'] for f in extraction['failures']], 'components': []}
    component_paths = sorted(directory.glob('components.*.json')) + sorted(directory.glob('saved_raw_components.json'))
    for path in component_paths:
        components = json.loads(path.read_text())
        record = {'file': pin(path), 'parameters': components['parameters']}
        if components['contact'] is not None:
            record['contact'] = [{'population_key': p['population_key'],
                'pairs': p['pairs'], 'distance_expectations': p['distance_expectations']} for p in components['contact']['populations']]
        if components['insulation'] is not None:
            record['insulation'] = [{'population_key': p['population_key'],
                'statistics': p['statistics'], 'domains': p['domains']} for p in components['insulation']['populations']]
        item['components'].append(record)
        compact = {'native_sha256': item['input']['sha256'], 'case_directory': item['case_directory'],
                   'origin': item['origin'], 'component_file': str(path.resolve()),
                   'parameters': components['parameters'], 'selected_regions': request['populations']}
        if components['contact'] is not None:
            contact = components['contact']['populations'][0]
            if contact['pairs']:
                compact['first_pair'] = {name: contact['pairs'][0]['measurements'][name] for name in ('raw_contact', 'fold_enrichment')}
            if len(contact['distance_expectations']) > 1:
                compact['distance_two'] = {name: contact['distance_expectations'][1]['measurements'][name] for name in (
                    'nominal_distance_pair_count', 'expected_contact', 'distance_population_variance')}
        if components['insulation'] is not None:
            insulation = components['insulation']['populations'][0]
            compact['insulation'] = {'statistics': insulation['statistics'], 'domains': insulation['domains']}
        checkable.append(compact)
    summary['native_cases'].append(item)
Path('NUMERICAL_AND_FAILURE_EVIDENCE.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
Path('CHECKABLE_EXAMPLES.json').write_text(json.dumps(checkable, indent=2, allow_nan=False) + '\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
