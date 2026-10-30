"""Independent engineering review of frozen241; no new paper interpretation."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import os
import runpy
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241/implementation_004'

def check_pin():
    manifest = json.loads((PIN / 'MANIFEST_003.json').read_text())
    for item in manifest['files']:
        raw = (PIN / item['path']).read_bytes()
        assert len(raw) == item['bytes'], item['path']
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    return len(manifest['files'])

def main():
    before = check_pin()
    env = dict(os.environ, PYTHONPATH=str(PIN), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        'tests/test_literature_endpoint_signal_components_241.py', '--tb=short']
    started = time.monotonic()
    result = subprocess.run(command, cwd=PIN, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (HERE / 'FROZEN_PYTEST_001.txt').write_text(result.stdout)
    # Use the same frozen modules and controlled fixture constructors. No actual
    # provider payload or runtime source store is involved.
    sys.path.insert(0, str(PIN))
    helpers = runpy.run_path(str(PIN / command[-2]))
    from PIL import Image
    args, blobs = helpers['_synthetic']()
    with Image.new('RGBA', (512, 512), (0, 0, 0, 0)) as image:
        buffer = BytesIO()
        image.save(buffer, format='PNG')
    raw = buffer.getvalue()
    blobs['synthetic_image', 'original'] = raw
    args['image']['expected_sha256'] = hashlib.sha256(raw).hexdigest()
    extraction = helpers['_read'](args, blobs)
    sheet = helpers['populate_endpoint_signal'](extraction)
    imported = []
    for name, module in sorted(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN), str(path)
            imported.append({'module': name, 'path': str(path.relative_to(PIN)),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt = {'classification': 'progress: independent frozen verification and new reproduced defect',
        'pin_files_checked_before': before, 'pin_files_checked_after': check_pin(),
        'pytest_command': command, 'pytest_exit_code': result.returncode,
        'pytest_output': result.stdout, 'seconds': time.monotonic() - started,
        'actual_local_imports': imported,
        'controlled_fixture': 'Every RGBA pixel is black with alpha zero; no visible trace ink.',
        'rgba_image_sha256': hashlib.sha256(raw).hexdigest(),
        'point_errors': {k: v['error'] for k, v in extraction['points'].items()},
        'qualifying_pixels': {k: v['observation']['support']['qualifying_pixel_count']
            if v['observation'] else None for k, v in extraction['points'].items()},
        'returned_cells': [{k: c[k] for k in ('component', 'value', 'status')}
            for c in sheet['cells'][:5]],
        'finding': 'RGBA conversion drops alpha; invisible black pixels authenticate as dark ink.',
        'scope': 'Pure engineering only; no new source conversion, selected operation, model run or credit.'}
    (HERE / 'ROOT_FROZEN_REVIEW_001.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'pytest_exit_code': result.returncode, 'pin_files': before,
        'imports': len(imported), 'alpha_defect_reproduced': all(v is None for v in receipt['point_errors'].values()),
        'seconds': receipt['seconds']}))
    return result.returncode

if __name__ == '__main__':
    raise SystemExit(main())
