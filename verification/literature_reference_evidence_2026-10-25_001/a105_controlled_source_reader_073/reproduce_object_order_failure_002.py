from pathlib import Path
import importlib.util
import json
import traceback
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('fixtures',ROOT/'tests/test_literature_controlled_response_v2_inputs.py');fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
f=fixtures.Fixture();x=f.read()
try:fixtures.reader.validate_controlled_response_v2_extraction(json.loads(json.dumps(f.args,sort_keys=True)),json.loads(json.dumps(x,sort_keys=True)))
except Exception:print(traceback.format_exc())
else:raise AssertionError('Expected the preserved pre-correction failure')
