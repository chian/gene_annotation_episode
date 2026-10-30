"""Execute one explicitly frozen factual-frame check group and retain evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

CODE = Path('/tmp/gene-annotation-configured-caller-20261022-007')
PARENT = Path('/tmp/gene-annotation-configured-caller-20261022-006')
PYTHON = Path('/home/chia/repos/gene_annotation_episode/.venv/bin/python')
SCOPE = Path('/home/chia/repos/gene_annotation_episode/docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md')
EXPECTED_SCOPE = '639a5bc3833be3a74b457afc92e5214788e0c91a8f6360b05da51fbb9a9cc256'
SCOPE2 = SCOPE.with_name('LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_002.md')
EXPECTED_SCOPE2 = '324aca20c4f8448951ad9b657e045c04f4f2abe4fde88df5e46e22d1f28989df'
AMENDMENT = CODE/'GENERATION_TEST_AMENDMENT_007_001.json'
AMENDED_TESTS = {'tests/test_completion_evidence_runtime.py',
    'tests/test_model_context_reconstruction.py'}
expected_pin = sys.argv[1]
assert len(expected_pin) == 64 and all(c in '0123456789abcdef' for c in expected_pin)
tests = sys.argv[2:]
assert tests and all(t.startswith('tests/') and (CODE/t.split('::')[0]).is_file() for t in tests)
out = Path(tempfile.mkdtemp(prefix='factual-frame007-root-checks-20261022-'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (out/name).open('x') as f:
        f.write(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
        f.flush();os.fsync(f.fileno())


def inventory(root):
    return {p.relative_to(root).as_posix(): {'sha256':sha(p),'bytes':p.stat().st_size}
        for p in root.rglob('*') if p.is_file() and not p.is_symlink()
        and not {'.pytest_cache','__pycache__'}.intersection(p.relative_to(root).parts)}


def pin(rows):
    h=hashlib.sha256()
    for rel in sorted(k for k in rows if k.endswith('.py') and k.startswith(('gene_annotation_episode/','method_loop/'))):
        h.update(rel.encode()+b'\0'+bytes.fromhex(rows[rel]['sha256']))
    return h.hexdigest()


assert sha(SCOPE)==EXPECTED_SCOPE
assert sha(SCOPE2)==EXPECTED_SCOPE2
before=inventory(CODE)
parent_before=inventory(PARENT)
assert pin(before)==expected_pin
assert pin(parent_before)=='209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f'
baseline=json.loads((CODE/'GENERATION_BASELINE_007.json').read_text())
amendment=json.loads(AMENDMENT.read_text())
assert amendment['version']=='factual_frame_test_expectations_amendment007_v1'
assert amendment['scope']=={'path':str(SCOPE2),'sha256':EXPECTED_SCOPE2}
assert set(amendment['allowed_original_test_changes'])==AMENDED_TESTS
assert set(amendment['files'])==AMENDED_TESTS
for rel, row in amendment['files'].items():
    original=row['original']; preserved=Path(original['preserved'])
    assert baseline['files'][rel]=={'sha256':original['sha256'],'bytes':original['bytes']}
    assert not preserved.is_symlink() and preserved.is_file()
    assert sha(preserved)==original['sha256'] and preserved.stat().st_size==original['bytes']
    assert before[rel]==row['amended']
changed={rel for rel,v in baseline['files'].items() if before.get(rel)!=v}
assert changed <= set(baseline['allowed_source_changes'])|AMENDED_TESTS,sorted(changed)
assert all(parent_before[k]==v for k,v in baseline['files'].items())
save('INPUTS_BEFORE.json',{'source':str(CODE),'runtime_pin':pin(before),'files':before,
    'changed_original_files':sorted(changed),'parent':str(PARENT),'parent_files':parent_before,
    'scope_sha256':sha(SCOPE),'scope002_sha256':sha(SCOPE2),
    'test_amendment':amendment,'test_amendment_sha256':sha(AMENDMENT),
    'script_sha256':sha(Path(__file__))})
with (out/'OPERATOR.py').open('xb') as f:
    f.write(Path(__file__).read_bytes());f.flush();os.fsync(f.fileno())
env={**os.environ,'PYTHONPATH':str(CODE),'PYTHONDONTWRITEBYTECODE':'1'}
command=[str(PYTHON),'-m','pytest','-q',*tests,'--basetemp',str(out/'pytest-fixtures'),
    '--junitxml',str(out/'junit.xml'),'-o','cache_dir='+str(out/'pytest-cache')]
save('COMMAND.json',{'argv':command,'cwd':str(CODE),'environment_overrides':
    {'PYTHONPATH':str(CODE),'PYTHONDONTWRITEBYTECODE':'1'},'started_at':datetime.now(timezone.utc).isoformat()})
start=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    process=subprocess.Popen(command,cwd=CODE,env=env,stdout=stdout,stderr=stderr)
    print(json.dumps({'out':str(out),'pid':process.pid,'runtime_pin':expected_pin,'selected_tests':tests}),flush=True)
    status=process.wait()
after=inventory(CODE);parent_after=inventory(PARENT)
save('INPUTS_AFTER.json',{'files':after,'runtime_pin':pin(after),'parent_files':parent_after})
required=set(baseline['files'])|{'GENERATION_BASELINE_007.json',AMENDMENT.name}|{t.split('::')[0] for t in tests}|{
    rel for rel in before if rel.endswith('.py') and rel.startswith(('gene_annotation_episode/','method_loop/'))}
changed_during=sorted(rel for rel in set(before)|set(after) if before.get(rel)!=after.get(rel))
changed_inputs=sorted(set(changed_during)&required)
unchanged=(not changed_inputs and pin(after)==expected_pin and parent_before==parent_after
    and sha(SCOPE)==EXPECTED_SCOPE and sha(SCOPE2)==EXPECTED_SCOPE2)
counts=None
if (out/'junit.xml').exists():
    suites=list(ET.parse(out/'junit.xml').getroot().iter('testsuite'))
    counts={key:sum(int(s.attrib[attr]) for s in suites) for key,attr in
        [('cases','tests'),('failures','failures'),('errors','errors'),('skipped','skipped')]}
save('RESULTS.json',{'status':status,'duration_seconds':time.monotonic()-start,'runtime_pin':expected_pin,
    'source_and_original_inputs_unchanged':unchanged,'xml_counts':counts,
    'changed_required_inputs':changed_inputs,'other_new_workload_files_changed':
        [rel for rel in changed_during if rel not in required],
    'actual_configured_model_science':False,'public_external_service_calls':False,
    'test_control_and_fixture_limits':'See each original test and retained raw fixture; numerical fixtures do not adopt a production model.'})
print(json.dumps({'out':str(out),'status':status,'unchanged':unchanged,'counts':counts}),flush=True)
if not unchanged:raise SystemExit('source inputs changed during check')
raise SystemExit(status)
