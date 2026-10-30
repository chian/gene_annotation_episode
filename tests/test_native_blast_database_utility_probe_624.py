"""Specific native follow-ups to original084 failures/undiscriminating strand case."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest


def _pin(path):
    content=path.read_bytes()
    return {'path':str(path),'sha256':hashlib.sha256(content).hexdigest(),'size_bytes':len(content)}


def test_original_database_diagnostic_and_strand():
    location=os.environ.get('HMMER529_ATTEMPT')
    if not location: pytest.skip('requires bounded runner529')
    attempt=Path(location)
    snapshot=Path(__file__).resolve().parents[1]
    original=snapshot/'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check084_database_utility_native/temporary/database_utility_native'
    selected=json.loads((attempt/'selected_native_executables.json').read_text())
    programs={Path(p).name:p for p in selected}
    assert set(programs)=={'blastdbcmd','blastdbcheck'}
    before=[_pin(p) for p in sorted(original.rglob('*')) if p.is_file()]
    dest=attempt/'temporary/database_utility_probe'
    dest.mkdir()
    env=dict(os.environ)
    env.update(BLAST_USAGE_REPORT='false', NCBI_DONT_USE_NCBIRC='1', BLASTDB_LMDB_MAP_SIZE='100000000')
    cases=[]
    for name,program,db,args in (
        ('v5_integrity_diagnostic','blastdbcheck','build_dna_v5',['-full','-verbosity','4']),
        ('v4_integrity_full','blastdbcheck','build_dna_v4',['-full','-verbosity','4']),
        ('strand_plus','blastdbcmd','build_dna_v5',['-entry','seqB','-range','2-7','-strand','plus','-outfmt','%o\t%i\t%a\t%l\t%s']),
        ('strand_minus','blastdbcmd','build_dna_v5',['-entry','seqB','-range','2-7','-strand','minus','-outfmt','%o\t%i\t%a\t%l\t%s']),
    ):
        work=dest/name
        work.mkdir()
        argv=[programs[program],'-db',str(original/db/'database'),'-dbtype','nucl',*args]
        stdout,stderr=work/'stdout.txt',work/'stderr.txt'
        with stdout.open('wb') as out,stderr.open('wb') as err:
            result=subprocess.run(argv,cwd=work,env=env,stdout=out,stderr=err,check=False)
        cases.append({'name':name,'program':program,'argv':argv,'cwd':str(work),
            'returncode':result.returncode,'stdout':_pin(stdout),'stderr':_pin(stderr)})
        (dest/'PROBE_001.json').write_text(json.dumps({'cases':cases,'original_inputs_before':before},indent=2)+'\n')
    after=[_pin(p) for p in sorted(original.rglob('*')) if p.is_file()]
    assert before==after
    assert all(r['returncode']==0 for r in cases if r['name'].startswith('strand_'))
    assert (dest/'strand_plus/stdout.txt').read_text().splitlines()[0].split('\t')[-1]=='TGCAAT'
    assert (dest/'strand_minus/stdout.txt').read_text().splitlines()[0].split('\t')[-1]=='ATTGCA'
    # Diagnostic status is observed, not forced to pass. Unknown exceptions aren't corruption.
