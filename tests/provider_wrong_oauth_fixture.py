#!/usr/bin/python3
"""Local protocol fixture with a deliberately different synthetic account."""
import base64
import json
import os
from pathlib import Path
import sys

payload = {'https://api.openai.com/auth': {'chatgpt_account_id': 'other-fixture-account'}}
token = 'header.'+base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')+'.signature'
responses = {
    'initialize': {},
    'config/read': {'config': {'model_provider': 'openai'}},
    'account/read': {'account': {'type': 'chatgpt', 'planType': 'business'}},
    'getAuthStatus': {'authMethod': 'chatgpt', 'authToken': token},
}
for line in sys.stdin:
    request = json.loads(line)
    with Path(os.environ['AUTH_FIXTURE_REQUEST_LOG']).open('a') as output:
        output.write(request['method']+'\n')
    if 'id' in request:
        print(json.dumps({'id': request['id'], 'result': responses.get(request['method'], {})}), flush=True)
