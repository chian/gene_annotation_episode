"""Execute the immutable C1 snapshot under the existing bounded lifecycle."""
from pathlib import Path
import json
import sys
import unittest

attempt = Path.cwd()
repo = Path('/home/chia/repos/gene_annotation_episode')
sys.path.insert(0, str(attempt / 'snapshot'))
sys.path.append(str(repo / '.venv/lib/python3.12/site-packages'))
suite = unittest.TestSuite()
names = sys.argv[1:] or ['tests.' + name for name in
    ('test_chromatin_interaction_contracts', 'test_chromatin_cooler_inputs',
     'test_chromatin_interaction_inputs', 'test_chromatin_interaction_tables')]
for name in names:
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
result = unittest.TextTestRunner(verbosity=2).run(suite)
(attempt / 'TEST_RESULT.json').write_text(json.dumps({'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors), 'successful': result.wasSuccessful()}, indent=2) + '\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
