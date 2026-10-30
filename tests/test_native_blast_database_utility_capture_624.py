"""Original tiny database utility observations; never runs a database search."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest


def _pin(path):
    content = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest(),
            'size_bytes': len(content)}


def test_capture_selected_tiny_database_utilities():
    attempt_name = os.environ.get('HMMER529_ATTEMPT')
    if not attempt_name:
        pytest.skip('requires bounded runner529')
    attempt = Path(attempt_name)
    snapshot = Path(__file__).resolve().parents[1]
    selected = json.loads((attempt / 'selected_native_executables.json').read_text())
    binaries = {Path(p).name: Path(p) for p in selected}
    assert set(binaries) == {'makeblastdb', 'blastdbcmd', 'blastdbcheck'}
    assert all(p.is_relative_to(snapshot) for p in binaries.values())
    dest = attempt / 'temporary/database_utility_native'
    dest.mkdir(exist_ok=False)
    inputs = dest / 'inputs'
    inputs.mkdir()
    (inputs / 'dna.fa').write_text('>seqA\nACGTACGTACGT\n>seqB\nTTGCAATTGCAA\n>ambiguous\nACGTRYN\n')
    (inputs / 'protein.fa').write_text('>seqP\nACDEFGHIKLMNPQRSTVWY\n>seqQ\nMKTLLILAVAFAVAA\n')
    (inputs / 'duplicate.fa').write_text('>same\nACGTACGTACGT\n>same\nTTGCAATTGCAA\n')
    env = dict(os.environ)
    env.update(BLAST_USAGE_REPORT='false', NCBI_DONT_USE_NCBIRC='1',
               BLASTDB_LMDB_MAP_SIZE='100000000')
    cases = []
    manifest = dest / 'CAPTURE_001.json'

    def record():
        manifest.write_text(json.dumps({
            'record_type': 'blast_database_utility_native_capture_v1',
            'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296,
                       'swap_bytes': 0, 'wall_seconds': None},
            'environment_overrides': {k:env[k] for k in
                ('BLAST_USAGE_REPORT','NCBI_DONT_USE_NCBIRC','BLASTDB_LMDB_MAP_SIZE')},
            'inputs': [_pin(p) for p in sorted(inputs.iterdir())],
            'cases': cases,
            'qualification': 'Explicit tiny native utility observations only; no search or episode binding claim.'
        }, indent=2)+'\n')

    def run(name, program, arguments, expected_returncode=None):
        work = dest / name
        work.mkdir()
        argv = [str(binaries[program]), *arguments]
        stdout, stderr = work / 'stdout.txt', work / 'stderr.txt'
        case = {'name':name,'program':program,'argv':argv,'cwd':str(work),
                'executable':_pin(binaries[program]),'started':False,
                'returncode':None,'launch_error':None,
                'expected_returncode':expected_returncode}
        with stdout.open('wb') as output, stderr.open('wb') as errors:
            try:
                completed = subprocess.run(argv,cwd=work,env=env,
                    stdout=output,stderr=errors,check=False)
            except OSError as error:
                case['launch_error']={'type':type(error).__name__,'errno':error.errno}
            else:
                case.update(started=True,returncode=completed.returncode)
        case.update(stdout=_pin(stdout),stderr=_pin(stderr))
        case['files']=[_pin(p) for p in sorted(work.rglob('*')) if p.is_file()]
        cases.append(case)
        record()
        return case

    databases = []
    for name, molecule, version, fasta in (
            ('dna_v4','nucl',4,'dna.fa'),('dna_v5','nucl',5,'dna.fa'),
            ('protein_v5','prot',5,'protein.fa')):
        prefix = dest / ('build_'+name) / 'database'
        result = run('build_'+name,'makeblastdb',[
            '-in',str(inputs/fasta),'-input_type','fasta','-dbtype',molecule,
            '-out',str(prefix),'-blastdb_version',str(version),
            '-title','explicit tiny '+name,'-parse_seqids'],0)
        if result['returncode'] == 0:
            databases.append((name,molecule,prefix))
    fmt = '%o\t%i\t%a\t%l\t%s'
    for name,molecule,prefix in databases:
        common=['-db',str(prefix),'-dbtype',molecule]
        run('info_'+name,'blastdbcmd',common+['-info','-exact_length'],0)
        run('metadata_'+name,'blastdbcmd',common+['-metadata'],0)
        selector='seqP,seqQ' if molecule=='prot' else 'seqA,seqB,ambiguous'
        run('extract_'+name,'blastdbcmd',common+['-entry',selector,'-outfmt',fmt],0)
    dna = next((r for r in databases if r[0]=='dna_v5'),None)
    if dna:
        common=['-db',str(dna[2]),'-dbtype','nucl']
        for name,range_value,strand in (
                ('range_plus','2-7','plus'),('range_minus','2-7','minus'),
                ('range_past_end','8-99','plus')):
            run(name,'blastdbcmd',common+['-entry','seqA','-outfmt',fmt,
                '-range',range_value,'-strand',strand],0)
        run('duplicate_selectors','blastdbcmd',common+[
            '-entry','seqA,seqA','-outfmt',fmt],0)
        run('missing_selector','blastdbcmd',common+[
            '-entry','seqA,missing_record','-outfmt',fmt])
        run('integrity_full','blastdbcheck',common+['-full'],0)
        run('integrity_stride','blastdbcheck',common+['-stride','2'],0)
    run('build_duplicate_ids','makeblastdb',[
        '-in',str(inputs/'duplicate.fa'),'-input_type','fasta','-dbtype','nucl',
        '-out',str(dest/'build_duplicate_ids'/'database'),'-blastdb_version','5',
        '-title','explicit duplicate-ID failure case','-parse_seqids'])
    assert len(databases)==3, cases
    assert all(r['started'] for r in cases), cases
    assert all(r['returncode']==r['expected_returncode'] for r in cases
               if r['expected_returncode'] is not None), cases
    assert next(r for r in cases if r['name']=='missing_selector')['returncode'] != 0
    assert next(r for r in cases if r['name']=='build_duplicate_ids')['returncode'] != 0
