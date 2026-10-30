"""Verify the applied numerical modules in the production checkout."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'applied_verification_001'
OUT.mkdir(exist_ok=False)
TESTS = ['tests/test_bvbrc_proteome_directional_' + name + '.py'
         for name in ('sheet','numerical_contracts','geometry','calculators')]
TESTS += ['tests/test_bvbrc_proteome_directional.py',
          'tests/test_bvbrc_proteome_directional_contracts.py',
          'tests/test_blast_pairwise_grader.py', 'tests/test_blast_database_grader.py']


def snapshot():
    paths = {ROOT / 'pyproject.toml'}
    for directory in ('gene_annotation_episode', 'method_loop', 'tests'):
        paths.update(p for p in (ROOT / directory).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts
            and (p.suffix in ('.py','.json') or 'fixtures' in p.parts))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


before = snapshot()
save('source_before.json',before)
applied = json.loads((HERE / 'APPLICATION_RECEIPT_001.json').read_text())
assert applied['production_applied']
assert all(before[r['path']] == r['after_sha256'] for r in applied['files'])
command = [sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
           '--junitxml=' + str(OUT / 'pytest.xml'),*TESTS]
save('command.json',command)
start = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
with (OUT / 'pytest.log').open('x') as log:
    process = subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
after = snapshot()
save('source_after.json',after)
changes = [p for p in sorted(set(before)|set(after)) if before.get(p) != after.get(p)]
suite = list(ET.parse(OUT / 'pytest.xml').getroot().iter('testsuite'))
receipt = {'started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),
           'elapsed_seconds':time.monotonic()-clock,'exit_code':process.returncode,
           'cwd':str(ROOT),'testsuites':[s.attrib for s in suite],
           'source_count':len(before),'changed_sources':changes,
           'verification':'applied numerical modules, retained output and synthetic cases; no live service or provider-return integration'}
save('receipt.json',receipt)
print(json.dumps(receipt))
sys.exit(process.returncode or bool(changes))
