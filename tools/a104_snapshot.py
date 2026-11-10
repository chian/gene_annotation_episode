"""Freeze code and exact prepared inputs before running one real A104 workflow."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.execution_memory import ExecutionMemory


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-case', type=Path, required=True)
    parser.add_argument('--entry', choices=('hpc', 'science'), default='hpc')
    parser.add_argument('--model-config', type=Path)
    parser.add_argument('--integrated', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source, case = run/'source', run/'case'
    source.mkdir()
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(root/package, source/package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    example = 'examples/a104_'+('hpc' if args.entry == 'hpc' else 'evolutionary')+'_investigation.py'
    (source/'examples').mkdir()
    shutil.copy2(root/example, source/example)
    case.mkdir()
    (case/'state').mkdir()
    with closing(sqlite3.connect((args.prepared_case.resolve()/'state/state.sqlite3').as_uri()+'?mode=ro', uri=True)) as reader:
        with closing(sqlite3.connect(case/'state/state.sqlite3')) as writer:
            reader.backup(writer)
            if writer.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('a104_prepared_case_integrity_failure')
    shutil.copytree(args.prepared_case/'state/artifacts', case/'state/artifacts')
    prepared = json.loads((args.prepared_case/'PREPARED.json').read_text())
    prepared.setdefault('shared_execution_memory', ExecutionMemory.configured().as_record())
    prepared['execution_resources']['aurora']['workspace'] = \
        '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/'+run.parent.name+'_'+run.name
    (case/'PREPARED.json').write_text(json.dumps(prepared, indent=2)+'\n')
    # Native model clients may inspect Git even with all model-side tools
    # disabled. Bound that discovery to this disposable workspace rather than
    # letting it traverse the large enclosing research repository.
    (case/'.gitignore').write_text('*\n')
    subprocess.run(['git', 'init', '--quiet', str(case)], check=True, capture_output=True)
    manifest = [{'path': str(path.relative_to(source)), 'bytes': path.stat().st_size,
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in sorted(source.rglob('*')) if path.is_file()]
    (source/'SOURCE_MANIFEST.json').write_text(json.dumps({'files': manifest}, indent=2)+'\n')
    command = [sys.executable, '-B', str(source/example), '--case-directory', str(case), '--repository-root', str(root)]
    if args.model_config:
        command.extend(['--model-config', str(args.model_config.resolve())])
    if args.integrated:
        command.append('--integrated')
    os.execvpe(command[0], command, {**os.environ, 'PYTHONPATH': str(source)})


if __name__ == '__main__':
    main()
