"""Controlled monitor presentation data, not a saved job or scientific result."""
from copy import deepcopy
INSTRUCTION_TEXT = 'Inspect the assigned execution progress and report requested monitoring information.'
OUTPUT_SCHEMA = {'type':'object','properties':{'fixture':{'const':True}},'required':['fixture'],'additionalProperties':False}
LOOKUP_TEXT = 'Controlled monitoring contract explanation; no execution result is asserted.'

def snapshot():
    return {'monitor_assignment':{'version':'monitor_assignment_v1','target_handle':'controlled-target','requested_fields':['status']},
        'requested_form':{'type':'object','properties':{'requested':{'type':'string','x-source':'selected_contract'}}},
        'available_report_facts':{'selected_contract':{'description':'SELECTED_CONTRACT'},
            'monitoring_status':{'description':'MONITOR_CONTRACT'},
            'unrequested_science':{'description':'UNREQUESTED_SCIENTIFIC_CATALOG'}},
        'feedback':None}

def changed_state():
    result=deepcopy(snapshot());result['feedback']={'code':'controlled_monitor_feedback'};return result

def assert_rendered(text, *, changed=False):
    assert text.startswith('TASK\n'+INSTRUCTION_TEXT)
    for value in ('Actual monitor state','controlled-target','SELECTED_CONTRACT','MONITOR_CONTRACT'):
        assert value in text
    assert 'UNREQUESTED_SCIENTIFIC_CATALOG' not in text
    if changed: assert 'controlled_monitor_feedback' in text
