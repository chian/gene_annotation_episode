import json, os, sys, time
from pathlib import Path
log, gate, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
def emit(value):
    print(json.dumps(value), flush=True)
def record(kind, params):
    with log.open('a') as stream:
        stream.write(json.dumps({'kind': kind, 'pid': os.getpid(), 'params': params})+'\n')
for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params', {})
    if 'id' not in message:
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/start':
        record(method, params)
        result = {'thread': {'id': 'scripted-frame-thread'}, 'model': params['model'],
                  'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        record(method, params)
        if mode == 'interrupt':
            sys.exit(5)  # Deliberate transport interruption after original request save.
        context = json.loads(params['input'][0]['text'])
        assert 'local_commission_frame' not in context
        if context['goal']['parent_goal_id']:
            # Test synchronization only: no episode work is selected by this gate.
            deadline = time.monotonic()+45
            while not gate.exists():
                if time.monotonic() >= deadline:
                    raise AssertionError('fixture report gate was not released')
                time.sleep(.01)
            selected = {'kind': 'tool', 'tool': 'state.query',
                        'arguments': {'refs': context['scope']['subject_refs']}}
            update = {'finding': 'qualified' if context['last_local_outcome'] else 'unknown'}
        elif not context['pending_work']['items'] and not context['child_reports']:
            form = {'type': 'object', 'properties': {
                'finding': {'type': 'string', 'enum': ['unknown', 'qualified']},
                'subjects': {'type': 'array', 'items': {'type': 'string',
                    'format': 'reference', 'x-reference-namespace': 'input'},
                    'x-source': 'subject_refs'}},
                'required': ['finding', 'subjects'], 'additionalProperties': False}
            selected = {'kind': 'child',
                'goal': 'Inspect the original bounded synthetic fixture inputs',
                'scope': context['scope'],
                'purpose': 'Return the original constrained fixture interpretation',
                'schema_json': json.dumps(form),
                'initial_report_json': json.dumps({'finding': 'unknown'})}
            update = {}
        elif context['pending_work']['items']:
            item, = context['pending_work']['items']
            assert item['return_available'] is False
            selected = {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
                'events': [{'handle': item['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}}
            update = {}
        else:
            assert context['child_reports'][0]['finding'] == 'qualified'
            selected = {'kind': 'tool', 'tool': 'state.query',
                        'arguments': {'refs': context['scope']['subject_refs']}}
            update = {}
        response = {'selection': selected, 'report_update': update}
        emit({'id': message['id'], 'result': {'turn': {'id': 'scripted-frame-turn'}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': 'scripted-frame-turn', 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
