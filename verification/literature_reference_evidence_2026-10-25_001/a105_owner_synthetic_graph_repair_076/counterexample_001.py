"""Constructed input; no source reader, graph count, model or episode work."""
from pathlib import Path
import json
import runpy
import sys
import traceback

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
fixture = runpy.run_path(str(root / 'tests/test_literature_controlled_response_owner_calculations.py'))
output = Path(sys.argv[2])
inputs = fixture['shared']()
row = inputs['arms'][fixture['ROLES'][3]]
fixture['graph'](row)
row['origin'] = 'synthetic'
inputs['model_kind'] = 'known_joint_normal_source_means'
fixture['Draft202012Validator'](fixture['INPUT_SCHEMA']).validate(inputs)
record = {'constructed_only': True, 'schema_validation': 'passed', 'inputs': inputs}
try:
    result = fixture['calculate'](inputs)
except Exception as error:
    record.update(outcome='failed', error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
else:
    record.update(outcome='passed', result=result)
output.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('inputs','result','traceback')}))
if record['outcome'] != 'passed':
    print(record['traceback'])
    raise SystemExit(1)
