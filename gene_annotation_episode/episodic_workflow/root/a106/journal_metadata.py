"""Intern repeated contract metadata without changing logical journal requests.

Only bulky contract dictionaries move to digest-verified Store artifacts.
Scientific observations, tool arguments, outcomes and receipts stay in place.
"""
from __future__ import annotations

import json


MARKER='__journal_metadata_artifact_v1__'
ROOT_FLAG='__journal_metadata_interned_v1__'
MEDIA_TYPE='application/vnd.gene-annotation.journal-metadata+json'
FIELDS={'available_report_facts','contract_information'}
THRESHOLD=32*1024


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def pack_request(store,text):
    value=json.loads(text)
    if not isinstance(value,dict):return text
    if ROOT_FLAG in value:raise ValueError('reserved_journal_metadata_key')
    changed=False
    def pack(item):
        nonlocal changed
        if isinstance(item,dict):
            result={}
            for key,child in item.items():
                if key in FIELDS and isinstance(child,(dict,list)):
                    encoded=_json(child)
                    # Escape even a small literal marker supplied as data.
                    if len(encoded)>THRESHOLD or isinstance(child,dict) and MARKER in child:
                        result[key]={MARKER:store.artifact(encoded,MEDIA_TYPE)}
                        changed=True
                        continue
                result[key]=pack(child)
            return result
        if isinstance(item,list):return [pack(child) for child in item]
        return item
    packed=pack(value)
    if changed:packed[ROOT_FLAG]=True
    return _json(packed) if changed else text


def restore_request(store,text):
    if ROOT_FLAG not in text:return text
    value=json.loads(text)
    if not isinstance(value,dict) or value.get(ROOT_FLAG) is not True:return text
    value.pop(ROOT_FLAG)
    def restore(item):
        if isinstance(item,dict):
            result={}
            for key,child in item.items():
                if key in FIELDS and isinstance(child,dict) and set(child)=={MARKER}:
                    artifact=store.db.execute('SELECT media_type FROM artifacts WHERE id=?',(child[MARKER],)).fetchone()
                    if artifact is None or artifact['media_type']!=MEDIA_TYPE:
                        raise ValueError('journal_metadata_artifact_type_conflict')
                    # Restore one layer only: a literal marker is opaque data.
                    result[key]=json.loads(store.get_artifact(child[MARKER]))
                else:result[key]=restore(child)
            return result
        if isinstance(item,list):return [restore(child) for child in item]
        return item
    return _json(restore(value))
