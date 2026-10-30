"""Execute unchanged MetaCATS statistical producers in a private local runtime.

This is native-format verification only, not an installed scientific API or
production parser. No service call, sequence alignment or annotation occurs.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys


BASE = Path(__file__).resolve().parent
SOURCE = BASE.parent / 'tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25'
NATIVE = SOURCE / 'retained_sources/bvbrc_metacats'
R_SCRIPT = NATIVE / 'scripts/Meta-CATS.R'
PERL_SCRIPT = NATIVE / 'scripts/metadata_parser.pl'
R_HOME = BASE / 'runtime/usr/lib/R'
R_BIN = R_HOME / 'bin/exec/R'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def memory_limit():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))


def fasta_rows(text):
    rows = []
    for line in text.splitlines():
        if line.startswith('>'):
            rows.append([line[1:], ''])
        else:
            assert rows, 'sequence before header'
            rows[-1][1] += line
    return rows


def synthetic(groups, *, category='comparison', extra_metadata=()):
    rows, metadata = [], ['Seq_ID\t' + category]
    for group, residue, n in groups:
        for j in range(n):
            identity = group + '-' + str(j)
            rows.append((identity, 'A' + residue + 'C-'))
            metadata.append(identity + '\t' + group)
    metadata.extend(identity + '\t' + group for identity, group in extra_metadata)
    return ''.join('>' + name + '\n' + seq + '\n' for name, seq in rows), '\n'.join(metadata) + '\n'


def main():
    assert not (BASE / 'NATIVE_RUNS_001.json').exists()
    binary = BASE / 'bin'
    binary.mkdir(exist_ok=True)
    launcher = binary / 'Meta-CATS'
    # The unchanged Perl caller invokes Meta-CATS on PATH. This launcher runs
    # the unchanged R source and copies its raw files before the Perl program
    # performs its normal significance filtering and deletes those raw files.
    launcher.write_text('#!' + sys.executable + '\n' +
        'import pathlib, subprocess, sys, shutil, json\n' +
        'cmd=' + repr([str(R_BIN), '--vanilla', '--slave', '--file=' + str(R_SCRIPT), '--args']) + ' + sys.argv[1:]\n' +
        'p=subprocess.run(cmd)\n' +
        'out=pathlib.Path(sys.argv[4]); keep=out/"retained_raw"; keep.mkdir(exist_ok=True)\n' +
        'name=sys.argv[5]\n' +
        'for suffix in ("-chisqTable.txt","-mcTable.txt"):\n' +
        ' src=out/(name+suffix)\n' +
        ' if src.exists(): shutil.copyfile(src,keep/src.name)\n' +
        '(keep/(name+".invocation.json")).write_text(json.dumps({"command":cmd,"returncode":p.returncode},indent=2)+"\\n")\n' +
        'sys.exit(p.returncode)\n')
    launcher.chmod(0o755)
    env = os.environ.copy()
    env.update(R_HOME=str(R_HOME), R_SHARE_DIR=str(BASE / 'runtime/usr/share/R/share'),
        R_INCLUDE_DIR=str(BASE / 'runtime/usr/share/R/include'), R_DOC_DIR=str(BASE / 'runtime/usr/share/doc/R'),
        LD_LIBRARY_PATH=str(R_HOME / 'lib'), TMPDIR=str(BASE / 'scratch'),
        R_LIBS_USER=str(BASE / 'runtime/empty-user-library'),
        PERL5LIB=os.pathsep.join(str(BASE / part) for part in (
            'runtime/usr/share/perl5', 'runtime/usr/lib/x86_64-linux-gnu/perl5/5.38')),
        PATH=str(binary) + os.pathsep + env['PATH'])
    official = SOURCE / 'additional_sources/bvbrc_metacats/tests/data'
    cases = [('official_na', 'na', (official / 'na_test.afa').read_text(),
        (official / 'metadata.na.1.tsv').read_text(), .05, 'official retained input')]
    for name, groups, extra in (
        ('aa_two_groups', [('A', 'A', 6), ('B', 'C', 6)], ()),
        ('aa_three_groups', [('A', 'A', 6), ('B', 'C', 6), ('C', 'D', 6)], ()),
        ('metadata_only_first_group', [('B', 'A', 6), ('C', 'C', 6)], [('missing-sequence', 'A')]),
        ('twelve_groups', [('g'+str(i+1).zfill(2), letter, 4)
                           for i, letter in enumerate('ACDEFGHIKLMN')], ()),
        ('native_pair_tail_underflow', [('A', 'A', 2000), ('B', 'C', 2000)], ()),
    ):
        fasta, metadata = synthetic(groups, extra_metadata=extra)
        cases.append((name, 'aa', fasta, metadata, .05, 'explicit synthetic input'))
    cases.append(('all_missing', 'na', '>a\n---\n>b\n---\n',
        'Seq_ID\tcomparison\na\tA\nb\tB\n', .05, 'explicit synthetic input'))
    original_hashes = {str(path): sha(path) for path in (R_SCRIPT, PERL_SCRIPT,
        NATIVE / 'service-scripts/App-MetaCATS.pl')}
    receipts = []
    for name, alphabet, fasta, metadata, cutoff, kind in cases:
        folder = BASE / 'cases' / name
        folder.mkdir(exist_ok=False)
        (folder / 'original.fasta').write_text(fasta)
        (folder / 'metadata.tsv').write_text(metadata)
        # This explicit verification preprocessing matches the inspected
        # App-MetaCATS.pl replace_gaps function. It is not an AppService run.
        rows = fasta_rows(fasta)
        adjusted = ''.join('>' + name + '\n' +
            re.sub(r'-+$', lambda match: '#' * len(match[0]),
                re.sub(r'^-+', lambda match: '#' * len(match[0]), seq)) + '\n'
            for name, seq in rows)
        (folder / 'adjusted.fasta').write_text(adjusted)
        output = folder / 'output'
        output.mkdir()
        cmd = ['perl', str(PERL_SCRIPT), str(folder / 'adjusted.fasta'),
            str(folder / 'metadata.tsv'), alphabet, str(cutoff), '1', str(output) + '/']
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(cmd, env=env, cwd=folder, capture_output=True, text=True,
                                preexec_fn=memory_limit)
        (folder / 'stdout.txt').write_text(result.stdout)
        (folder / 'stderr.txt').write_text(result.stderr)
        record = {'case': name, 'input_kind': kind, 'alphabet': alphabet,
            'command': cmd, 'started_at': started, 'returncode': result.returncode,
            'source_hashes': original_hashes, 'original_rows': len(rows),
            'original_lengths': sorted({len(seq) for _, seq in rows}),
            'explicit_preprocessing': 'terminal dashes to hash; Python verification preprocessing, matching inspected native replace_gaps',
            'local_R_version': '4.3.3-2build2', 'complete_AppService_execution': False,
            'retained_before_native_deletion': True,
            'files': {str(path.relative_to(folder)): {'sha256': sha(path), 'bytes': path.stat().st_size}
                      for path in sorted(folder.rglob('*')) if path.is_file()},
            'exported_table_rows': {path.name: max(0, len(path.read_text().splitlines()) - 1)
                                    for path in output.glob('*Table.tsv')}}
        write(folder / 'RECEIPT.json', record)
        receipts.append(record)
        print(json.dumps({key: record[key] for key in ('case', 'returncode', 'original_rows', 'exported_table_rows')}), flush=True)
    assert original_hashes == {str(path): sha(path) for path in (R_SCRIPT, PERL_SCRIPT,
        NATIVE / 'service-scripts/App-MetaCATS.pl')}
    write(BASE / 'NATIVE_RUNS_001.json', receipts)


if __name__ == '__main__':
    main()
