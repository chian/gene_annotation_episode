"""Read-only diagnosis using the original failed binding, under native_lifecycle."""
import importlib
import json
from pathlib import Path
import sys
import traceback

from gene_annotation_episode.native_chromatin_interaction_driver import verify_software
from gene_annotation_episode.native_chromatin_hic_runtime import _runtime_files

software = json.loads(Path(sys.argv[1]).read_text())
result = {'before_import': None, 'after_import': None}
before = set(_runtime_files())
try:
    verify_software(software)
    result['before_import'] = 'verified'
except Exception:
    result['before_import'] = traceback.format_exc()
importlib.import_module('gene_annotation_episode.chromatin_hic_inputs')
result['added_native_paths'] = sorted(set(_runtime_files()) - before)
try:
    verify_software(software)
    result['after_import'] = 'verified'
except Exception:
    result['after_import'] = traceback.format_exc()
print(json.dumps(result, indent=2))
