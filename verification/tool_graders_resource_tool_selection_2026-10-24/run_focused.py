"""Bounded selection verification with an audit of loaded production sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import method_loop
import pytest


ROOT = Path(__file__).resolve().parents[2]
DESTINATION = Path(__file__).resolve().parent
PACKAGES = (ROOT/'gene_annotation_episode', Path(method_loop.__file__).resolve().parent)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


started = datetime.now(timezone.utc).isoformat()
before = {str(path.resolve()): digest(path) for package in PACKAGES
          for path in package.rglob('*.py')}
arguments = ['-q', 'tests/test_resource_tool_selection.py',
    'tests/test_resource_tool_selection_workflow.py', 'tests/test_child_tool_information.py',
    'tests/test_current_process_preparation.py']
exit_code = pytest.main(arguments)
loaded = {}
for name, module in tuple(sys.modules.items()):
    if name.split('.')[0] not in {'gene_annotation_episode', 'method_loop'}:
        continue
    value = getattr(module, '__file__', None)
    if value is None:
        continue
    path = Path(value).resolve()
    if path.suffix == '.py':
        loaded.setdefault(str(path), []).append(name)
rows = [{'path': path, 'modules': sorted(modules), 'before_sha256': before.get(path),
         'after_sha256': digest(Path(path))} for path, modules in sorted(loaded.items())]
changed = [row['path'] for row in rows if row['before_sha256'] != row['after_sha256']]
audit = {'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'pytest_arguments': arguments, 'pytest_exit_code': int(exit_code),
    'loaded_production_source_count': len(rows), 'changed_loaded_production_sources': changed,
    'sources': rows}
(DESTINATION/'production-source-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
print(f'Loaded production source audit: {len(rows)} files; {len(changed)} changed.')
raise SystemExit(int(exit_code) if exit_code else int(bool(changed)))
