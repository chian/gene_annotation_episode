import json, os, sys
from pathlib import Path
log = Path(sys.argv[1])
def emit(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params', {})
    if 'id' not in message:
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/start':
        assert params['model'] == 'gpt-6-sol'
        assert params['config']['model_reasoning_effort'] == 'medium'
        result = {'thread': {'id': 'new-caller-fixture-thread'}, 'model': params['model'],
            'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        context = json.loads(params['input'][0]['text'])
        assert 'scientific_process' in context
        assert context['current_credit'] == 0 and context['annotation_score'] == 0
        previous = context['last_local_outcome']
        if previous is None:
            assert 'api_execution_proposal' not in context
            action = {'kind': 'tool', 'tool': 'execution.estimate',
                'arguments': context['scientific_process']['assignment']['context']['estimate_input']}
        else:
            proposal = context['api_execution_proposal']
            assert proposal['api_reported_execution_forecasts'][0]['expected_total_seconds'] is None
            action = {'kind': 'tool', 'tool': 'episode.history',
                'arguments': {'view': 'records', 'decision_indices': [0]}}
        with log.open('a') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'context': context}) + '\n')
        response = {'selection': action, 'report_update': {}}
        emit({'id': message['id'], 'result': {'turn': {'id': 'new-caller-fixture-turn'}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': 'new-caller-fixture-turn', 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
