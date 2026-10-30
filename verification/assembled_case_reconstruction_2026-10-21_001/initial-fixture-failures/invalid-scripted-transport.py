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
        result = {'thread': {'id':'assembled-fixture-thread'}, 'model':params['model'],
            'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        context = json.loads(params['input'][0]['text'])
        selected = context['scientific_process']['selection']['tools']
        assert selected == ['sequence.inspect','translation.codes']
        names = {entry['name'] for entry in context['tools']}
        assert set(selected) <= names and 'source.archive.extract' not in names
        assert context['scientific_process']['permitted_children'] == [
            'scientific_process','literature','launch','monitor','results']
        assert context['current_credit'] == 0 and context['annotation_score'] == 0
        previous = context['last_local_outcome']
        if previous is None:
            action = {'kind':'tool','tool':'sequence.inspect',
                'arguments':{'subject_ref':context['scope']['subject_refs'][0]}}
            state = 'unknown'
        else:
            assert previous['status'] == 'completed'
            assert previous['result']['length'] == 762
            action = {'kind':'tool','tool':'translation.codes','arguments':{}}
            state = 'measured'
        with log.open('a') as stream:
            stream.write(json.dumps({'pid':os.getpid(),'context':context})+'
')
        response = {'selection':action, 'report_update':{'finding_state':state}}
        emit({'id':message['id'],'result':{'turn':{'id':'assembled-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'assembled-fixture-turn','status':'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id':message['id'],'result':result})
