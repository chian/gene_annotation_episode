"""Capture only two selected public native outputs and their cited source closure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
RUN = BASE / 'literature_model_run_030/live_001'
EPISODE = 'episode_76758a673dea6a01ef47fb2b7252facac1945c143bf2a10ebea32ab9bc9c4343'


def write(name, data):
    with (HERE / name).open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    utc = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect((RUN / 'state/state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('begin')

        def record(reference):
            row = db.execute('select data from records where id=?', (reference,)).fetchone()
            assert row is not None
            return json.loads(row['data'])

        artifact_receipts = {}

        def artifact(reference):
            row = db.execute('select * from artifacts where id=?', (reference,)).fetchone()
            assert row is not None
            data = (RUN / 'state/artifacts' / row['sha256'][:2] / row['sha256']).read_bytes()
            assert digest(data) == row['sha256'] and len(data) == row['size']
            artifact_receipts[reference] = dict(row)
            return data

        actions, payloads, source_refs = [], {}, set()
        rows = list(db.execute('select run_id,episode_id,decision_index,action,result,credit from runtime_actions '
                              'where episode_id=? and decision_index in(29,31) order by decision_index', (EPISODE,)))
        assert len(rows) == 2
        for row in rows:
            selected = dict(row)
            selected['action_json_sha256'] = digest(selected['action'].encode())
            selected['result_json_sha256'] = digest(selected['result'].encode())
            selected['action'] = json.loads(selected['action'])
            selected['result'] = json.loads(selected['result'])
            assert selected['action']['tool'] == 'literature.rate.source.populate'
            assert selected['result']['status'] == 'completed'
            sheet_ref = selected['result']['result']['sheet_ref']
            source = record(sheet_ref)
            payload = json.loads(artifact(source['artifact_ref']))
            request = json.loads(artifact(source['request_ref']))
            assert request['arguments'] == payload['native_selection'] == selected['action']['arguments']
            assert selected['result']['result']['cells'] == payload['sheet']['cells']
            op = db.execute('select * from literature_rate_operations where run_id=? and episode_id=? and operation_key=?',
                            (row['run_id'], EPISODE, request['operation_key'])).fetchone()
            assert json.loads(op['outcome'])['result'] == selected['result']['result']
            payloads[str(row['decision_index'])] = {'source_record': source, 'original_request': request,
                                                  'saved_payload': payload, 'operation_row': dict(op)}
            source_refs.update(payload['direct_input_source_refs'])
            actions.append(selected)
        sources, pending = {}, sorted(source_refs)
        while pending:
            reference = pending.pop(0)
            if reference in sources:
                continue
            source = record(reference)
            assert source['record_type'] == 'source'
            sources[reference] = source
            pending.extend(source.get('parent_source_refs', []))
        assert len(sources) == 1, 'A new paper closure needs explicit single-paper handling'
        source = next(iter(sources.values()))
        for representation, field in [('original', 'artifact_ref'), ('text', 'text_ref')]:
            data = artifact(source[field])
            with (HERE / ('PRIMARY_' + representation.upper() + '_001' + ('.html' if representation == 'original' else '.txt'))).open('xb') as stream:
                stream.write(data)
        episode = dict(db.execute('select * from runtime_episodes where episode_id=?', (EPISODE,)).fetchone())
        episode['request'] = json.loads(episode['request'])
        # State/completion may change later; this is one original short readonly snapshot.
        for field in ('completion', 'archive'):
            if episode[field] is not None:
                episode[field] = json.loads(episode[field])
        write('PUBLIC_SELECTED_ACTIONS_001.json', actions)
        write('PUBLIC_SAVED_PAYLOADS_001.json', payloads)
        write('PUBLIC_SOURCE_RECORDS_001.json', sources)
        write('ORIGINAL_EPISODE_REQUEST_001.json', episode)
        write('CAPTURE_RECEIPT_001.json', {'utc': utc, 'sqlite_mode': 'ro', 'selected_decisions': [29,31],
              'episode_id': EPISODE, 'selected_outputs': len(payloads), 'cited_primary_sources': len(sources),
              'authenticated_artifacts': artifact_receipts,
              'no_provider_or_model_history_access': True, 'no_store_constructor_or_write': True})
    print(json.dumps({'captured': 2, 'primary_sources': len(sources),
                      'primary_bytes': {p.name: p.stat().st_size for p in HERE.glob('PRIMARY_*')}}))


if __name__ == '__main__':
    main()
