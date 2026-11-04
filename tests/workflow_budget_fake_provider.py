"""Tiny RPC fixture for process lifecycle checks; makes no model calls."""
import json
import sys

for line in sys.stdin:
    request=json.loads(line)
    if 'id' in request:
        print(json.dumps({'id':request['id'],'result':{}}),flush=True)
