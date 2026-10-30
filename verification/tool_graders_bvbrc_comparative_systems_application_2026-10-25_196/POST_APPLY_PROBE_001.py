#!/usr/bin/env python3
"""Run only after application: installed-equivalent values and strict origins."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMPL = ROOT / 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186'
PIN = '118aae7a8a9470b9a7cb2e0f081853ac6730c98e1710ac9018a312312699b68f'
sys.argv = [str(IMPL / 'PACKAGE_PROBE_002.py'), str(ROOT),
            str(IMPL / 'evidence_p/FILLED_PROVIDER_INPUT_003.json'),
            str(IMPL / 'evidence_p/FILLED_PROVIDER_RESULT_003.json'), PIN]
captured = io.StringIO()
with redirect_stdout(captured):
    runpy.run_path(str(IMPL / 'PACKAGE_PROBE_002.py'), run_name='__main__')
answer = json.loads(captured.getvalue())
from gene_annotation_episode.bvbrc_comparative_systems_bundle_adapter import implementation_sha256 as comparative_pin
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import implementation_sha256 as proteome_v1_pin
from gene_annotation_episode.bvbrc_proteome_bundle_adapter_v2 import implementation_sha256 as proteome_v2_pin

origins = {}
for name, module in sorted(sys.modules.items()):
    top = name.split('.')[0]
    if top not in {'gene_annotation_episode', 'method_loop'}:
        continue
    location = getattr(module, '__file__', None)
    if location is None:
        raise RuntimeError('runtime_module_has_no_origin:' + name)
    path = Path(location).resolve()
    if not path.is_relative_to(ROOT / top):
        raise RuntimeError('runtime_module_outside_production_package:' + name + ':' + str(path))
    origins[name] = str(path)
print(json.dumps({'installed_equivalent': answer,
    'pins': {'comparative': comparative_pin(), 'proteome_v1': proteome_v1_pin(), 'proteome_v2': proteome_v2_pin()},
    'no_candidate_imports': True, 'actual_import_origins': origins,
    'live_service_execution_verified': False, 'authenticated_publication_verified': False}))
