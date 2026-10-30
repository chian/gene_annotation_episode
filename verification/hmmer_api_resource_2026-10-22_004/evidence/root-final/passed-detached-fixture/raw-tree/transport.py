import json,sys
from pathlib import Path
log=Path(sys.argv[1])
def emit(value): print(json.dumps(value),flush=True)
for line in sys.stdin:
    message=json.loads(line)
    method,params=message.get('method'),message.get('params',{})
    if 'id' not in message: continue
    if method=='initialize': result={}
    elif method=='thread/start':
        result={'thread':{'id':'planning-fixture-thread'},'model':params['model'],
                'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method=='turn/start':
        context=json.loads(params['input'][0]['text'])
        assert 'scientific_process' in context
        previous=context['last_local_outcome']
        if previous:
            assert context['api_execution_proposal']==previous['result']
            assert context['api_reported_execution_forecasts'][0]['reported_result_support']=={'reported_result_count':0}
            selected={'kind':'tool','tool':'episode.history','arguments':{'view':'records','decision_indices':[0]}}
        else:
            assert 'api_execution_proposal' not in context
            selected={'kind':'tool','tool':'execution.estimate',
                'arguments':context['scientific_process']['assignment']['context']['estimate_input']}
        with log.open('a') as stream: stream.write(json.dumps(context)+'\n')
        response={'selection':selected,'report_update':{}}
        emit({'id':message['id'],'result':{'turn':{'id':'planning-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'planning-fixture-turn','status':'completed'}}})
        continue
    else: raise AssertionError(method)
    emit({'id':message['id'],'result':result})
