"""Run original frozen-native dependency checks without mutating shared source."""
from pathlib import Path
import hashlib
import json
import sys
import time
OUT=Path(__file__).resolve().parent
PIN=OUT/'pin_001'
sys.path.insert(0,str(PIN));sys.path.insert(0,str(PIN/'tests'))
import pytest
selected=['tests/test_literature_binding_interaction_model_inputs.py','tests/test_literature_binding_interaction_model_storage.py','tests/test_literature_binding_interaction_model_integration.py']
start=time.monotonic()
code=pytest.main(['-q','--tb=short','-p','no:cacheprovider','--junitxml='+str(OUT/'PIN_FOCUSED_001.xml'),*[str(PIN/p) for p in selected]])
files=json.loads((OUT/'PIN_001.json').read_text())['files']
changed=[p for p,d in files.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=d]
imports={name:str(Path(m.__file__).resolve()) for name,m in list(sys.modules.items()) if getattr(m,'__file__',None) and (name.startswith(('gene_annotation_episode','method_loop','test_literature')))}
outside={k:p for k,p in imports.items() if not Path(p).is_relative_to(PIN)}
(OUT/'PIN_FOCUSED_RESULT_001.json').write_text(json.dumps({'pytest_exit_code':int(code),'elapsed_seconds':time.monotonic()-start,'changed_snapshot_files':changed,'imports_outside_snapshot':outside,'selected':selected},indent=2)+'\n')
(OUT/'PIN_FOCUSED_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
raise SystemExit(int(code) or bool(changed) or bool(outside))
