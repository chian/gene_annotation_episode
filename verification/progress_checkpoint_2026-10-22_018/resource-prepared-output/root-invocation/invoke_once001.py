"""Record one explicit preparation subprocess, without importing application code."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).parent
CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
PLAN=Path('/tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE')
PYTHON='/home/chia/repos/gene_annotation_episode/.venv/bin/python'
PIN='3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'


def now():return datetime.now(timezone.utc).isoformat()


def descriptor(path):
    assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes()
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def source_pin():
    paths=sorted(p for package in ('gene_annotation_episode','method_loop') for p in (CODE/package).rglob('*.py'))
    digest=hashlib.sha256()
    for path in paths:
        row=descriptor(path)
        digest.update(path.relative_to(CODE).as_posix().encode()+b'\0')
        digest.update(bytes.fromhex(row['sha256']))
    value={'sha256':digest.hexdigest(),'file_count':len(paths)}
    return value


def write(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    with os.fdopen(fd,'wb') as stream:
        stream.write((json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
        stream.flush();os.fsync(stream.fileno())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-sha256',required=True)
    parser.add_argument('--inputs-sha256',required=True)
    args=parser.parse_args()
    for name in ('STARTED001.json','INVOCATION001.json','STDOUT001.log','STDERR001.log'):
        assert not os.path.lexists(ROOT/name)
    operator=descriptor(PLAN/'prepare_caller001.py');inputs=descriptor(PLAN/'INPUTS001.json')
    assert operator['sha256']==args.operator_sha256 and inputs['sha256']==args.inputs_sha256
    before=source_pin()
    assert before=={'sha256':PIN,'file_count':137}
    argv=[PYTHON,operator['path'],'--prepare','--input-manifest-sha256',inputs['sha256']]
    explicit={'PYTHONPATH':str(CODE),'PYTHONDONTWRITEBYTECODE':'1'}
    env=dict(os.environ);env.update(explicit)
    stdout_path,stderr_path=ROOT/'STDOUT001.log',ROOT/'STDERR001.log'
    with stdout_path.open('xb') as stdout,stderr_path.open('xb') as stderr:
        started=now()
        write(ROOT/'STARTED001.json',{'version':'root_resource_preparation_start_v1','argv':argv,
            'cwd':str(CODE),'explicit_environment':explicit,'started_at_utc':started,
            'operator':operator,'input_manifest':inputs,'source_pin_before':before})
        process=subprocess.Popen(argv,cwd=CODE,env=env,stdout=stdout,stderr=stderr)
        code=process.wait()
        finished=now()
        stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
    stdout_path.chmod(0o400);stderr_path.chmod(0o400)
    after=source_pin()
    guards_equal=(after==before and descriptor(PLAN/'prepare_caller001.py')==operator
                  and descriptor(PLAN/'INPUTS001.json')==inputs)
    value={'version':'root_configured_resource_preparation_invocation_v1','status':'exited',
        'argv':argv,'cwd':str(CODE),'explicit_environment':explicit,
        'started_at_utc':started,'finished_at_utc':finished,'exit_code':code,
        'stdout':descriptor(stdout_path),'stderr':descriptor(stderr_path),
        'operator':operator,'input_manifest':inputs,'source_pin_before':before,'source_pin_after':after}
    write(ROOT/'INVOCATION001.json',value)
    print(json.dumps({'exit_code':code,'receipt':str(ROOT/'INVOCATION001.json'),
        'receipt_sha256':descriptor(ROOT/'INVOCATION001.json')['sha256'],
        'source_and_input_guards_unchanged':guards_equal},sort_keys=True))
    raise SystemExit(code if guards_equal else 1)


if __name__=='__main__':main()
