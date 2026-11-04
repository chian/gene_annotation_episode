"""Rescore saved, received native results without executing tools or models.

The original state and recorded scores are never changed. A SQLite backup in
the caller's explicit work directory is opened by the current Store; immutable
artifacts are read from the original run. This is a rescore, not a live rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from .a101_credit import A101SequenceCredit
from .state import Store


def rescore_saved_run(source_run, *, work_directory):
    source = Path(source_run).resolve()
    work = Path(work_directory).resolve()
    state = work/'state'
    if work == source or source in work.parents:
        raise ValueError('a101_rescore_work_directory_must_be_outside_original_run')
    state.mkdir(parents=True, exist_ok=True)
    original = sqlite3.connect(f'file:{source / "state/state.sqlite3"}?mode=ro',uri=True)
    copied = sqlite3.connect(state/'state.sqlite3')
    try:
        original.backup(copied)
    finally:
        copied.close()
        original.close()
    artifacts = state/'artifacts'
    expected = source/'state/artifacts'
    if artifacts.is_symlink():
        if artifacts.resolve() != expected.resolve():
            raise ValueError('a101_rescore_artifact_directory_conflict')
    elif artifacts.exists():
        raise ValueError('a101_rescore_artifact_directory_conflict')
    else:
        artifacts.symlink_to(expected,target_is_directory=True)
    projector = A101SequenceCredit()
    episodes = []
    with Store(state) as store:
        for row in store.db.execute('SELECT episode_id,path,request,archive FROM runtime_episodes'):
            path = json.loads(row['path'])
            if path[-1][0] not in ('annotation','scientific_process'):
                continue
            request = json.loads(row['request'])
            if path[-1][0] == 'scientific_process':
                assignment = request['message'].get('episode_assignment',{})
                selection = assignment.get('selection',{})
                axis = selection.get('evidence_axis',selection.get('annotation_ref',{}))
                if axis.get('option_id') != 'A101':
                    continue
            known = [ref[0] for ref in store.db.execute(
                'SELECT record_ref FROM runtime_record_receipts WHERE episode_id=?',(row['episode_id'],))]
            view = projector.read_details(store,request['message']['scope'],
                known_record_refs=known,details_limit=50,details_offset=0)
            last = store.db.execute('SELECT observation FROM runtime_observations WHERE episode_id=? '
                'ORDER BY unit_index DESC LIMIT 1',(row['episode_id'],)).fetchone()
            episodes.append({'episode_id':row['episode_id'], 'role':path[-1][0],
                'original_recorded_credit':json.loads(last[0])['step']['credit'] if last else None,
                'rescored_native_credit':view['credit'], 'projection':view})
    return {'version':'a101_saved_native_rescore_v1', 'source_run':str(source),
        'meaning':'current_native_sheet_projection_of_original_received_results_not_a_live_rerun',
        'original_scores_rewritten':False, 'native_jobs_submitted':0, 'model_calls':0,
        'scorer':projector.as_record(),
        'implementation_sha256':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('a101_credit.py','a101_scoring.py')},
        'episodes':episodes}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',required=True,type=Path)
    parser.add_argument('--work-directory',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    source=args.source_run.resolve()
    if source == args.output.resolve() or source in args.output.resolve().parents:
        raise ValueError('a101_rescore_output_must_be_outside_original_run')
    report=rescore_saved_run(source,work_directory=args.work_directory)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(args.output), 'episodes':[
        {'role':row['role'],'original_credit':row['original_recorded_credit'],
         'native_credit':row['rescored_native_credit']} for row in report['episodes']]},indent=2))


if __name__ == '__main__':
    main()
