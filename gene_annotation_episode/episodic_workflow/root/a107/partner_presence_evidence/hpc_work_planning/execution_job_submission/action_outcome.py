"""Private A107 action outcome"""
from __future__ import annotations

def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references), 'changed_record_refs': list(references), 'result': result, 'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}
