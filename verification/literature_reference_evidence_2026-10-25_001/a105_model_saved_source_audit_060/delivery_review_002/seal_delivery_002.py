"""Seal bounded002 proof and independently check original public relationships."""
import hashlib
import json
from pathlib import Path
import sqlite3

HERE=Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,value):
    with (HERE/name).open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def main():
    original=load(HERE.parent/'MANIFEST_001.json')
    for name,row in original['files'].items():
        path=HERE.parent/name
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],name
    proof=load(HERE/'READONLY_DELIVERY_RECEIPT_002.json')
    assert proof['passed'] and proof['actual_typed_rows']==10 and proof['nonnull_point_rows']==6
    assert proof['public_selected_snapshot_unchanged'] and proof['no_live_re_admission']
    assert load(HERE/'EXIT_002.json')['exit_code']==1
    assert load(HERE/'EXIT_003.json')['exit_code']==0
    assert '"passed": true' in (HERE/'TERMINAL_003.log').read_text()
    captured=load(HERE/'ORIGINAL_PUBLIC_DELIVERY_002.json')
    rows=captured['rows']
    spec=json.loads(rows['commission']['spec'])
    parent=json.loads(rows['parent_episode']['request'])
    child=json.loads(rows['child_episode']['request'])
    assert parent['goal']['goal_id']==spec['parent']['goal_id']
    assert json.loads(rows['parent_episode']['path'])==spec['parent']['path']
    assert json.loads(rows['child_episode']['path'])==spec['child']['path']
    assert spec['child']['scope']==child['message']['scope']==parent['message']['scope']
    admission=json.loads(rows['admission']['admission'])
    ack=json.loads(captured['backend_commission']['acknowledgment'])
    assert all(ack[key]==admission[key] for key in ('admission_id','handle','return_id'))
    received=json.loads(rows['received']['cells'])
    assert len({(row['sheet_ref'],row['component']) for row in received})==10
    prior={row['decision_index']:row for row in load(HERE.parent/'PUBLIC_SELECTED_ACTIONS_001.json')}
    for row in rows['native_actions']:
        first=prior[row['decision_index']]
        assert json.loads(row['action'])==first['action']
        assert json.loads(row['result'])['result']==first['result']['result']
    # This owned database has only empty constructor tables. It contains no
    # live/private-history copy; inspect its row counts to prove that boundary.
    with sqlite3.connect((HERE/'metadata_factory_state/state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:
        names=[row[0] for row in db.execute("select name from sqlite_master where type='table'")]
        counts={name:db.execute('select count(*) from "'+name+'"').fetchone()[0] for name in names}
        assert all(count==0 for count in counts.values())
    write('PACKAGING_CHECKS_002.json',{'passed':True,'original001_files_unchanged':len(original['files']),
        'original_parent_goal_path_scope_and_child_request_consistent':True,
        'backend_acknowledgment_matches_original_admission':True,
        'native_selected_actions_numerical_results_equal_scientific001_capture':True,
        'no_duplicate_sheet_component_rows':True,'metadata_fixture_table_counts':counts,
        'optional_C4_replay_fixture_run':False})
    excluded={'MANIFEST_002.json','FINAL_VERIFY_002.json'}
    files={str(path.relative_to(HERE)):{'bytes':path.stat().st_size,'sha256':sha(path)}
           for path in sorted(HERE.rglob('*')) if path.is_file() and path.name not in excluded}
    write('MANIFEST_002.json',{'scope':'Mechanical actual030 typed delivery and readonly reconstruction; original001 roster remains frozen; no new science or whole-goal completion',
                             'excluded':sorted(excluded),'files':files})
    for name,row in files.items():
        path=HERE/name
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],name
    receipt={'passed':True,'files_verified':len(files),'manifest_sha256':sha(HERE/'MANIFEST_002.json'),
        'original001_files_unchanged':len(original['files']),'actual_typed_rows':10,'nonnull_point_rows':6,
        'original_parent_observation_index':21,'first_projection_original_scientific_source_reads':0,
        'actual_model_child_delivery':True,'new_model_or_episode_work':False,
        'whole_live_database_read_or_stability_claim':False,'full_root_run_A105_goal_complete_claim':False}
    write('FINAL_VERIFY_002.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
