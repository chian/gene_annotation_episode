"""Independent finite, offline checks of the captured literature prefix."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import stat

SOURCE = Path('/tmp/configured-literature-commission-prefix-20261022-001-1HuZX6bk')
OUTPUT = Path(__file__).parent/'RESULT001.json'
MANIFEST_SHA = 'e7dbac56e54de4ad0d1b3ccab6a6684ecb83661420e7bdc11955ebe762622cfc'
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and not path.is_symlink()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        assert (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino)
        raw = stream.read()
    after = path.lstat()
    def witness(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
                stat.S_IMODE(value.st_mode))
    assert witness(before) == witness(after) and len(raw) == after.st_size
    return raw, witness(after)


def main():
    assert not OUTPUT.exists()
    witnesses = {}
    def load(name):
        raw, witness = read(SOURCE/name)
        witnesses[name] = (sha(raw), witness)
        return json.loads(raw)
    manifest = load('MANIFEST_FINAL001.json')
    assert witnesses['MANIFEST_FINAL001.json'][0] == MANIFEST_SHA
    rows = manifest['members']
    names = [row['path'] for row in rows]
    assert len(names) == len(set(names)) == 24
    assert {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*')} == set(names)|{'MANIFEST_FINAL001.json'}
    for row in rows:
        assert Path(row['path']).name == row['path']
        raw, witness = read(SOURCE/row['path'])
        assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
        assert witness[-1] == int(row['mode'], 8) == 0o444
        witnesses[row['path']] = (sha(raw), witness)
    assert manifest['runtime_pin'] == PIN
    assert manifest['capture_invocations'] == 1 and manifest['active_database_recaptures'] == 0
    capture, analysis = load('CAPTURE001.json'), load('ANALYSIS001.json')
    spec, selection = load('C1_ORIGINAL_SPEC001.json'), load('C1_ORIGINAL_SELECTION001.json')
    parent, child, handle = spec['parent']['episode_id'], spec['child']['episode_id'], spec['handle']
    assert capture['root_episode_id'] == parent and spec['run_id'] == capture['run_id']
    assert capture['source_pin_authority'] == analysis['runtime_pin'] == PIN
    assert capture['runtime_file_count'] == 137 and capture['source_members_unchanged']
    assert read(SOURCE/'SOURCE_BEFORE001.json')[0] == read(SOURCE/'SOURCE_AFTER001.json')[0]
    assert spec['child']['role'] == selection['role'] == 'literature'
    assert spec['child']['scope'] == selection['scope'] == {'subject_refs':['input_a5c60b96717424cdf5138420']}
    assert spec['resource_selection'] is None
    intent, durable = capture['commission_intents'][0], capture['durable_commissions'][0]
    assert len(capture['commission_intents']) == len(capture['durable_commissions']) == 1
    assert intent['spec'] == durable['spec'] == spec and intent['selection'] == selection
    assert intent['original_decision_index'] == 0
    assert intent['commission_sha256'] == durable['commission_sha256'] == witnesses['C1_ORIGINAL_SPEC001.json'][0]
    assert intent['selection_text']['sha256'] == witnesses['C1_ORIGINAL_SELECTION001.json'][0]
    episodes = {x['episode_id']:x for x in capture['episodes']}
    assert len(episodes) == 2 and set(episodes) == {parent,child}
    assert episodes[child]['request'] == spec['child']['request']
    assert episodes[child]['path'] == spec['child']['path']
    assert episodes[child]['request']['message']['scope'] == spec['child']['scope']
    assert episodes[child]['request']['goal']['parent_goal_id'] == episodes[parent]['request']['goal']['goal_id']
    assert spec['child']['request']['message']['episode_assignment'] == selection['assignment']
    schema = json.loads(selection['schema_json'])
    assert schema['additionalProperties'] is False and len(schema['properties']) == 7
    assert set(schema['required']) == set(schema['properties'])
    assert all(x['type'] == 'array' and x['items']['type'] == 'string' and x['items']['format'] == 'reference'
               for x in schema['properties'].values())
    actions = {(x['episode_id'],x['decision_index']):x for x in capture['actions']}
    assert len(actions) == 16
    initial = actions[parent,0]
    assert initial['selection_metadata'] == {'kind':'episode_child','role':'literature'}
    assert initial['selection_text']['sha256'] == witnesses['C1_ORIGINAL_SELECTION001.json'][0]
    assert initial['result_metadata']['pending_handle'] == handle and initial['credit'] is None
    assert durable['lifecycle_state'] == 'executing' and durable['return_id'] is None
    assert durable['acknowledgment'] is None and durable['failure'] is None
    assert durable['execution_identity'] == {'pid':724788,'start_ticks':'48276382','boot_id':'d53ef063-e9a7-4ae1-99ad-c64c17bdff26'}

    # Match completed own observations and waits without fitting a yield model.
    observations = [x for x in capture['observations'] if x['episode_id'] == parent]
    assert len(capture['observations']) == 13 and len(observations) == 2
    assert {x['unit_index'] for x in observations} == {0,1}
    events = {x['cursor']:x for x in capture['durable_events']}
    waits = {x['original_decision_index']:x for x in capture['root_waits']}
    wait_result = []
    for row in observations:
        value = row['observation']; index = value['decision_index']
        assert index == row['unit_index']+1 and value['label'] == 'wait:'+str(index)
        assert value['unit_ref']['episode_id'] == parent and value['unit_ref']['unit_index'] == row['unit_index']
        assert value['credit']['credit'] == value['step']['credit'] == actions[parent,index]['credit'] == 12
        assert value['step']['marginal_credit'] == 0 and value['step']['stop'] is False
        assert actions[parent,index]['selection_metadata']['kind'] == 'wait'
        request, outcome, wake = (json.loads(waits[index][k]) for k in ('request','outcome','wake'))
        assert request['parent_episode_id'] == parent and request['original_decision_index'] == index
        assert request['wait_id'] == outcome['wait_id'] == waits[index]['wait_id']
        assert outcome['wake_reason'] == wake['reason'] == 'progress_committed'
        trigger = outcome['trigger']; event = events[trigger['cursor']]
        assert trigger['handle'] == handle == event['handle'] and event['event'] == 'progress_committed'
        assert any(x['handle'] == handle and x['event'] == event['event'] and trigger['cursor'] > x['after_cursor']
                   for x in request['condition']['events'])
        assert request['estimate_snapshot']['scientific_gain'] is None
        assert request['estimate_snapshot']['monitoring_gain'] is None
        assert all(x['probability'] is None for x in request['estimate_snapshot']['event_expectations'])
        assert outcome['measured_duration_seconds'] > 0
        wait_result.append({'decision':index,'unit':row['unit_index'],'raw_delta':0,'cursor':trigger['cursor'],
                            'measured_wait_seconds':outcome['measured_duration_seconds']})
    assert waits[3]['outcome'] is None and waits[3]['wake'] is None
    assert actions[parent,3]['credit'] is None
    assert len([x for x in capture['completion_slots'] if x['episode_id'] == parent]) == 2

    # Compute independent interval intersections from captured timings.
    calls = capture['model_call_metadata']; overlaps = []
    for a in calls:
        if a['episode_id'] != parent or not a['response_present']: continue
        for b in calls:
            if b['episode_id'] != child or not b['response_present']: continue
            for ai in a['timing']['intervals']:
                for bi in b['timing']['intervals']:
                    if not ai['ended_at'] or not bi['ended_at']: continue
                    start = max(datetime.fromisoformat(ai['started_at']),datetime.fromisoformat(bi['started_at']))
                    end = min(datetime.fromisoformat(ai['ended_at']),datetime.fromisoformat(bi['ended_at']))
                    if start < end:
                        assert ai['owner']['pid'] != bi['owner']['pid']
                        overlaps.append({'parent':a['call_index'],'child':b['call_index'],
                                         'start':start.isoformat(),'end':end.isoformat()})
    assert {(x['parent'],x['child']) for x in overlaps} == {(1,0),(2,8),(3,10)}

    # Original saved frames are factual inputs, outside both decision contexts.
    requests = {i:load(f'ROOT_REQUEST_{i:04d}.json') for i in range(4)}
    for i, request in requests.items():
        assert request['version'] == 'runtime_model_call_request_v3'
        for context in (request['context'],request['model_presentation']['context']):
            assert 'local_commission_frame' not in context and context['child_reports'] == []
            assert context['monitoring_information_credit'] == 0
        frame = request['local_commission_frame']
        assert frame['version'] == 'local_commission_frame_v1'
        assert frame['episode_id'] == parent and frame['run_id'] == capture['run_id']
        assert frame['population_count'] == len(frame['commissions']) == (0 if i == 0 else 1)
        if i:
            item = frame['commissions'][0]
            assert item['commission'] == spec and item['selection'] == selection
            assert item['handle'] == handle and item['original_decision_index'] == 0
            assert item['admission_evidence'] is None and item['return_metadata'] is None
            assert item['pending_status_fact']['return_available'] is False
    for row in capture['root_estimation_contexts']:
        data, index = row['data'],row['decision_index']
        assert data['version'] == 'completed_action_estimation_context_v6'
        assert data['local_commission_frame_at_selection'] == requests[index]['local_commission_frame']
        assert data['local_commission_frame_after_action']['commissions'][0]['commission'] == spec
        assert data['pending_work_after_action'] is not None
        assert data['wait_outcome'] == json.loads(waits[index]['outcome'])

    main_names = {x['name'] for x in load('MAIN_SCHEMA001.json')}
    durable_names = {x['name'] for x in load('DURABLE_SCHEMA001.json')}
    assert 'returns' in durable_names and capture['durable_returns'] == []
    assert 'runtime_return_admissions' not in main_names and capture['admissions'] == []
    assert 'runtime_report_attempts' in main_names and capture['report_attempts'] == []
    assert capture['root_forms'] == []
    assert capture['connection_explicitly_closed'] and capture['read_protocol']['query_only']
    assert capture['read_protocol']['mode'] == 'ro' and not capture['read_protocol']['immutable']
    assert not capture['read_protocol']['cross_database_atomicity_claimed']
    for name, (digest,witness) in witnesses.items():
        raw, current = read(SOURCE/name)
        assert sha(raw) == digest and current == witness
    result = {'status':'captured_prefix_independently_verified','input_manifest_sha256':MANIFEST_SHA,
              'runtime_pin':PIN,'files_checked':len(witnesses),'original_literature_C1':True,
              'distinct_persisted_worker':durable['execution_identity'],'actual_call_overlaps':overlaps,
              'completed_parent_waits':wait_result,'pending_original_child_action':0,
              'C3':'present table, zero matching returns','C4':'table absent, no admission evidenced',
              'typed_return_or_later_scientific_influence_proved':False,
              'live_database_or_application_calls':0,'input_witnesses_unchanged':True,
              'limits':['Captured finite-prefix consistency only; no current liveness probe.',
                        'No private child findings exported, scientific validity inferred, or scores recomputed.',
                        'Pending-aware numerical law and scientific/monitoring gain estimates remain unbound.']}
    with OUTPUT.open('x') as stream:
        json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    OUTPUT.chmod(0o444)
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
