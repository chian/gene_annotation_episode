"""Write proposed JSON shapes only, no application imports or execution."""
from pathlib import Path
import json
root=Path('/tmp/scientific-context-proposal002-xmmw8Rca')
uint={'type':'integer','minimum':0}
sha={'type':'string','pattern':'^[0-9a-f]{64}$'}
text={'type':'string','minLength':1}
def closed(properties):
    return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def const(value): return {'const':value}
query=closed({'tool':const('episode.history'),'arguments':closed({'view':const('records'),'decision_indices':{'type':'array','minItems':1,'uniqueItems':True,'items':uint}})})
page=closed({
 'version':const('bounded_wait_history_page_v1'), 'run_id':text,'episode_id':text,'before_decision_index':uint,
 'page_size_source':const('restoration.preview_size'),'preview_size':uint,
 'order':const('original_unit_index_ascending'),'total_rows':uint,'included_rows':uint,'omitted_rows':uint,
 'range':closed({'start':uint,'end_exclusive':uint,'unit':const('completed_own_action_history_position')}),
 'first_unit_index':{'anyOf':[uint,{'type':'null'}]},'last_unit_index':{'anyOf':[uint,{'type':'null'}]},
 'decision_indices':{'type':'array','uniqueItems':True,'items':uint},
 'identity_fields':const(['episode_id','unit_index','unit_ref','decision_index']),
 'included_rows_without_decision_identity':uint,'included_rows_without_unit_ref':uint,
 'raw_history_sha256':sha,'included_history_sha256':sha,'history_is_complete':{'type':'boolean'},
 'history_lookup':closed({'availability':{'enum':['available','unavailable','unknown']},'unavailable_reason':{'enum':[None,'episode_history_not_in_saved_catalog','saved_tool_catalog_unavailable']}}),
 'exact_included_records':{'anyOf':[query,{'type':'null'}]},
 'discover_older_decisions':{'anyOf':[closed({'tool':const('episode.history'),'arguments':closed({'view':const('index'),'offset':const(0),'limit':{'type':'integer','minimum':1}})}),{'type':'null'}]},
 'history_result_row_path':const('result.records[*].controller_observation'),
 'history_result_step_path':const('result.records[*].controller_observation.step'),
 'calculation_context':const('runtime_model_calls.request.context'),
})
definition=closed({'version':const('bounded_wait_history_v1'),'history_path':const('waiting_support.own_completed_action_history'),
 'page_size_source':const('restoration.preview_size'),'preview_size':uint,
 'selection':const('latest_completed_rows_in_original_order'),
 'serialization':const('canonical_key_order_then_python_json_default_ascii_v1'),'lookup_tool':const('episode.history'),'lookup_source':const('original_context.tools')})
presentation=closed({'version':const('episode_model_presentation_v1'),'definition':definition,
 'run_id':text,'episode_id':text,'before_decision_index':uint,'original_context_sha256':sha,
 'presented_context_sha256':sha,'model_input_text_sha256':sha,'model_input_char_count':uint,
 'model_input_utf8_byte_count':uint,'context':{'type':'object'}})
envelope=closed({'version':const('runtime_model_call_request_v2'),'context':{'type':'object'},'schema':{'type':'object'},'model_presentation':presentation})
restoration={'anyOf':[closed({'preview_size':uint}),closed({'preview_size':uint,'model_presentation':const('bounded_wait_history_v1')})]}
(root/'PAGE_CONTRACT.json').write_text(json.dumps(page,indent=2,sort_keys=True)+'\n')
(root/'CONTRACTS002.json').write_text(json.dumps({'status':'proposed_unimplemented','restoration':restoration,'definition':definition,'presentation':presentation,'new_request_envelope':envelope,'semantic_validation':'See PROPOSAL002.md: recompute exact declared raw->latest-N projection; canonical type/sign/identity/count/hash comparisons required in addition to these shapes.'},indent=2,sort_keys=True)+'\n')
