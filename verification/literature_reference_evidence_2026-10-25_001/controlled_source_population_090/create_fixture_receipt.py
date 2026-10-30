"""Create immutable synthetic-byte examples and actual imported source snapshot."""
from pathlib import Path
import base64
from copy import deepcopy as cp
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))
from test_literature_controlled_response_v3_inputs import Fixture
from gene_annotation_episode import literature_controlled_response_v3_inputs as source
from gene_annotation_episode import literature_controlled_response_v3_population as population
from gene_annotation_episode import literature_controlled_response_inputs as shared


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


cases = []
for name, fixture in [
    ('ready', Fixture()),
    ('unresolved_explicit_two_joint_assignments', Fixture(companion=True, joints=True)),
    ('source_explicit_mean_display', Fixture(companion=True, authority=True, joints=True)),
    ('unknown_owner', Fixture(4)),
    ('invalid_unused_full_covariance_row', Fixture(9)),
    ('mixed_original_origins', Fixture(companion=True)),
    ('zero_local_variance', Fixture()),
    ('underflow_variance_representable_standard_uncertainty', Fixture()),
]:
    if name == 'mixed_original_origins':
        fixture.args['companion_readings'][0]['reading']['source_kind'] = 'primary_source'
    if name in ('zero_local_variance','underflow_variance_representable_standard_uncertainty'):
        factor = 0 if name == 'zero_local_variance' else 1e-320
        fixture.doc['covariance'] = [[v*factor for v in row] for row in fixture.doc['covariance']]
        fixture.covariance()
        fixture.args['local_pair_assignments'][0]['covariance_selection'] = cp(fixture.args['covariance'])
        fixture.args['local_pair_assignments'][0]['variance_status'] = cp(fixture.args['variance_status'])
    closure = shared._reference_closure(fixture.args)
    extraction = fixture.read()
    assert fixture.calls == closure
    result = population.populate_controlled_response_v3(extraction)
    assert source.validate_controlled_response_v3_extraction(fixture.args, extraction) == extraction
    cases.append({'name': name, 'source_status': 'constructed_engineering_fixture_not_primary_science',
        'selection': cp(fixture.args), 'sources': [dict(source_ref=r, representation=p,
            artifact_ref='artifact_'+hashlib.sha256(fixture.data[r]).hexdigest(),
            content_base64=base64.b64encode(fixture.data[r]).decode()) for r,p in closure],
        'extraction': extraction, 'population': result})
dump(OUT/'CONSTRUCTED_CASES.json', cases)
pin = OUT/'pin'
imports = {}
for name, module in sorted(sys.modules.copy().items()):
    if not name.startswith('gene_annotation_episode') or not getattr(module, '__file__', None): continue
    path = Path(module.__file__).resolve()
    if path.suffix != '.py' or not path.is_relative_to(ROOT): continue
    relative = path.relative_to(ROOT)
    target = pin/relative; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    imports[name] = {'relative_path': str(relative), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
# Include all tests in this coherent release; the executable proof below uses
# retained constructed bytes directly and does not import test fixtures.
for filename in ['test_literature_controlled_response_v3_inputs.py',
    'test_literature_controlled_response_local_calculations.py',
    'test_literature_controlled_response_v3_population.py', 'test_literature_controlled_response_v3_stages.py']:
    target = pin/'tests'/filename; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/'tests'/filename, target)
dump(OUT/'PINNED_IMPORTS.json', imports)
dump(OUT/'LIVE_SCHEMA_DIGESTS.json', {key: hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(',',':')).encode()).hexdigest()
    for key, schema in source._schemas().items()})
print(json.dumps({'cases': len(cases), 'actual_imported_project_modules': len(imports), 'fixture_bytes_only': True}))
