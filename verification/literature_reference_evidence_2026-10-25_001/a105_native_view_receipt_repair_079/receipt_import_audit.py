"""Pytest provenance only; this plugin changes no workflow behavior."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys


def pytest_sessionfinish(session, exitstatus):
    root = Path(os.environ['RECEIPT_PIN_ROOT']).resolve()
    imports = {}
    for name, module in sorted(sys.modules.items()):
        if not (name.startswith(('gene_annotation_episode', 'method_loop', 'test_literature_ratio_source'))):
            continue
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        assert path.is_relative_to(root), (name, str(path), str(root))
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    output = {'pin_root': str(root), 'exitstatus': int(exitstatus), 'collected_tests': session.testscollected,
        'python_executable': sys.executable, 'python_version': sys.version,
        'imported_sources': imports,
        'installed_distributions': {dist.metadata['Name']: dist.version for dist in metadata.distributions()}}
    Path(os.environ['RECEIPT_IMPORT_AUDIT']).write_text(json.dumps(output, indent=2) + '\n')
