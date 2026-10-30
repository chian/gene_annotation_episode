"""Root independent regression of241 alpha repair, comparing both frozen pins."""
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
OWN = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241'
PIN = OWN / 'implementation_005'
OLD = OWN / 'implementation_004'

def verify():
    manifest = json.loads((PIN/'MANIFEST_003.json').read_text())
    for f in manifest['files']:
        raw = (PIN/f['path']).read_bytes()
        assert len(raw) == f['bytes'] and hashlib.sha256(raw).hexdigest() == f['sha256'], f['path']
    return len(manifest['files'])

def main():
    before = verify()
    unchanged = ['literature_endpoint_signal_calculations.py', 'literature_endpoint_signal_prompt.py']
    for name in unchanged:
        assert (PIN/'gene_annotation_episode'/name).read_bytes() == (OLD/'gene_annotation_episode'/name).read_bytes()
    for name in ('ACTUAL_SOURCE_EXTRACTION_003.json','ACTUAL_SOURCE_SHEET_003.json'):
        assert (PIN/name).read_bytes() == (OLD/name).read_bytes(), name
    env = dict(os.environ, PYTHONPATH=str(PIN), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        'tests/test_literature_endpoint_signal_components_241.py', '-k', 'rgba or opaque', '--tb=short']
    start = time.monotonic()
    result = subprocess.run(command,cwd=PIN,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (HERE/'ALPHA_PYTEST_002.txt').write_text(result.stdout)
    sys.path.insert(0,str(PIN))
    m = runpy.run_path(str(PIN/'tests/test_literature_endpoint_signal_components_241.py'))
    from PIL import Image
    checks=[]
    # Boundary cases independently expected from white-basis alpha compositing.
    for alpha,threshold,expected in ((0,255,False),(64,180,False),(74,180,False),
            (75,180,True),(128,180,True),(255,180,True)):
        args,blobs = m['_synthetic']()
        with Image.new('RGBA',(512,512),(0,0,0,alpha)) as image:
            output=BytesIO();image.save(output,format='PNG')
        raw=output.getvalue();blobs['synthetic_image','original']=raw
        args['image']['expected_sha256']=hashlib.sha256(raw).hexdigest()
        for p in args['image']['points'].values():p['maximum_rgb']=threshold
        extraction=m['_read'](args,blobs)
        supported=all(p['observation'] is not None for p in extraction['points'].values())
        assert supported is expected
        assert extraction['context']['subject'] is not None
        checks.append({'alpha':alpha,'threshold':threshold,'visible_over_white':255-alpha,'supported':supported})
    imports=[]
    for name,module in sorted(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module,'__file__',None):
            path=Path(module.__file__).resolve();assert path.is_relative_to(PIN)
            imports.append({'module':name,'path':str(path.relative_to(PIN)),
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt={'status':'passed' if result.returncode==0 else 'failed','command':command,
        'exit_code':result.returncode,'test_output':result.stdout,'seconds':time.monotonic()-start,
        'pin_files_before':before,'pin_files_after':verify(),'imports':imports,
        'independent_controlled_checks':checks,'unchanged_calculations_and_task':True,
        'original_source_extraction_and_sheet_byte_identical':True,
        'scope':'Pure reader repair; selected execution, typed returns and full A105 assessment unfinished.'}
    (HERE/'ROOT_ALPHA_REVIEW_002.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','test_output','seconds','pin_files_before')}))
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
