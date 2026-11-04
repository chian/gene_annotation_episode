"""Freeze the code and required inputs, then exec one bounded real A103 case."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from contextlib import closing

from gene_annotation_episode.workflow_budget import active_budget


def main():
    budget = active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=['poxa','bioy','yjef','mj0044'],required=True)
    parser.add_argument('--retained-case',type=Path)
    parser.add_argument('--recover-completed-native',action='store_true')
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--wiring-smoke',action='store_true')
    args = parser.parse_args()
    directory = Path(budget['run_directory'])
    retained=None
    if args.retained_case is not None:
        original=args.retained_case.resolve()/'state'
        previous=original/'RETAINED_INPUTS.json'
        prior=json.loads(previous.read_text()) if previous.exists() else None
        retained=directory/'case'/'state';retained.mkdir(parents=True)
        with closing(sqlite3.connect((original/'state.sqlite3').as_uri()+'?mode=ro',uri=True)) as reader:
            with closing(sqlite3.connect(retained/'state.sqlite3')) as writer:
                reader.backup(writer)
                if writer.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                    raise ValueError('retained_state_integrity_failure')
                records=[row[0] for row in writer.execute('SELECT DISTINCT record_ref FROM runtime_record_receipts')]
        if prior is not None and prior.get('mode')=='explicit_retained_record_handover':
            records=list(dict.fromkeys([*records,*prior['record_refs']]))
        shutil.copytree(original/'artifacts',retained/'artifacts')
        recoveries=[]
        if args.recover_completed_native:
            from gene_annotation_episode.state import Store
            from gene_annotation_episode.homology_recovery import recover_unparsed_searches
            with Store(retained) as recovered_store:
                records,recoveries=asyncio.run(recover_unparsed_searches(recovered_store,args.retained_case.resolve(),records,
                    directory=directory/'case'/'recovered-native'))
        (retained/'RETAINED_INPUTS.json').write_text(json.dumps({
            'mode':'explicit_retained_record_handover','source_case':str(args.retained_case.resolve()),
            'record_refs':sorted(records),'scientific_status':'retained_observations_and_interpretations; not_expected_answers',
            'prior_handover':prior,
            'recovered_native_outputs':recoveries,
        },indent=2)+'\n')
    snapshot = directory/'source'
    snapshot.mkdir()
    root = Path(__file__).resolve().parents[1]
    for package in ('gene_annotation_episode','method_loop'):
        shutil.copytree(root/package,snapshot/package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for relative in (
        'tests/fixtures/a103/real',
        'research/slotted_process_library/publications/2026-10-24-001',
    ):
        shutil.copytree(root/relative,snapshot/relative)
    for relative in (
        'tests/a103_native_fixture.py','tests/a103_parent_dispatch.py','tests/a103_run_audit.py',
        'examples/a103_gene_context_investigation.py',
        'tools/a103_case_snapshot.py',
        'resources/software/infernal-1.1.5/hmmer/src/phmmer',
    ):
        destination = snapshot/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/relative,destination)
    manifest = [{'path':str(path.relative_to(snapshot)),'bytes':path.stat().st_size,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(snapshot.rglob('*')) if path.is_file()]
    (snapshot/'SOURCE_MANIFEST.json').write_text(json.dumps({'files':manifest},indent=2)+'\n')
    environment = {**os.environ,'PYTHONPATH':str(snapshot)}
    command = [sys.executable,str(snapshot/'examples/a103_gene_context_investigation.py'),
        '--case',args.case,'--run-directory',str(directory/'case'),'--timeout','540']
    if args.smoke:command.append('--smoke')
    if args.wiring_smoke:command.append('--wiring-smoke')
    if retained is not None:command.extend(['--retained-state',str(retained)])
    os.execvpe(command[0],command,environment)


if __name__=='__main__':main()
