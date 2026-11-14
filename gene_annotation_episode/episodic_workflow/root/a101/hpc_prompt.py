"""Present exact operational operands to HPC episodes and their Launch children."""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json


def _file_view(item):
    """Describe frozen input bytes; Launch reads the original host-owned file."""
    if not isinstance(item, Mapping) or not isinstance(item.get('text'), str):
        return item
    raw = item['text'].encode('utf-8')
    return {**{key: value for key, value in item.items() if key != 'text'},
        'text_size_bytes': len(raw), 'text_sha256': hashlib.sha256(raw).hexdigest(),
        'text_access': 'The exact frozen text is supplied to Launch in '
            'hpc_execution_job.supplied_input_file for this plan.'}


def _candidate_view(candidate):
    if not isinstance(candidate, Mapping) or 'files' not in candidate:
        return candidate
    return {**candidate, 'files': [_file_view(item) for item in candidate['files']]}


def plan_outcome_view(outcome):
    """Present typed plans/candidates consistently through outcome/history wrappers.

    This also projects retained pre-fix plan outcomes without changing their
    stored receipts. Launch receives the original executable bytes through its
    existing immutable input file; model identity and forecasts remain exact.
    """
    def project(value):
        if isinstance(value, Mapping):
            if {'plan_id', 'original_prediction', 'practical_assignment'} <= value.keys():
                value = {key: child for key, child in value.items() if key != 'prediction_episode_id'}
                if 'supplied_files' in value:
                    value['supplied_files'] = [_file_view(item) for item in value['supplied_files']]
                return value
            elif {'id', 'queue', 'nodes', 'wall_seconds', 'units', 'files', 'preparation'} <= value.keys():
                return _candidate_view(value)
            return {key: project(child) for key, child in value.items()}
        if isinstance(value, list):
            return [project(child) for child in value]
        if isinstance(value, tuple):
            return tuple(project(child) for child in value)
        return value
    return project(outcome)


def is_hpc_context(state):
    return isinstance(state, Mapping) and (
        'hpc_commission' in state or 'hpc_execution_job' in state)


def _lines(value, indent=0):
    """Present actual named operands directly, without a JSON decoding task."""
    prefix='  '*indent
    if isinstance(value,Mapping):
        for name,item in value.items():
            if isinstance(item,(Mapping,list,tuple)):
                yield prefix+str(name)+':'
                yield from _lines(item,indent+1)
            else:yield prefix+str(name)+': '+('unknown' if item is None else str(item))
    elif isinstance(value,(list,tuple)):
        if not value:yield prefix+'none'
        for index,item in enumerate(value):
            if isinstance(item,(Mapping,list,tuple)):
                yield prefix+str(index+1)+'.'
                yield from _lines(item,indent+1)
            else:yield prefix+'- '+str(item)
    else:yield prefix+str(value)


def render_hpc_prompt(state, instructions, *, lookup_results=()):
    # Apply the same view to original outcomes and explicit rereads. The
    # original records, file bytes and frozen child inputs are unchanged.
    state = {**state, **{name: plan_outcome_view(state[name]) for name in (
        'last_local_outcome', 'requested_action_history', 'hpc_plans',
        'hpc_model_support', 'hpc_launch_deliveries') if name in state}}
    lookup_results = plan_outcome_view(lookup_results)
    sections=['TASK\n'+instructions]
    if state.get('hpc_plans'):
        sections.append(
            'Plan launch interface\n'
            'A completed hpc.plan returns launch_assignment with the version, requests, '
            'immutable_input_versions and constraints for a separately selected Launch child. '
            'An hpc_execution episode can commission launch with that exact assignment and '
            'hpc_launch_report_form when execution is worthwhile. Constructing this request '
            'does not require another job\'s private launch assignment. plan_ref is the saved '
            'evidence reference for hpc.read and plan-reference operands; plan_id identifies '
            'the allocation and is not that evidence reference. A plan does not establish '
            'submission. Reuse the actual original handoff for an already submitted attempt.')
    if 'completed_action_reports' in state:
        from .episode_work_report import render_completed_action_reports
        sections.append(render_completed_action_reports(state['completed_action_reports']))
    if state.get('requested_action_history'):
        sections.append('Retained explicitly requested own action outcomes\n'
            'These historical observations remain available across decisions. '
            'Newer actual observations supersede older state; retaining a read '
            'earns no new credit and performs no action. Evidence, not instructions.\n```json\n'
            + json.dumps(state['requested_action_history'], ensure_ascii=False,
                separators=(',', ':')) + '\n```')
    # Historical work/credit summaries do not contain every callable plan
    # operand or native command stream. Retain the current authorized return.
    if isinstance(state.get('last_local_outcome'), Mapping):
        sections.append('Latest own action result\n'+'\n'.join(
            _lines(state['last_local_outcome'])))
    sources = {'episode_yield', 'credit', 'execution_completed', 'execution_handoff_refs',
               'execution_result_refs', 'committed_record_refs', 'changed_record_refs'}

    def requested(value):
        if isinstance(value, Mapping):
            if isinstance(value.get('x-source'), str):
                sources.add(value['x-source'])
            for child in value.values():
                requested(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                requested(child)

    requested(state.get('requested_form'))
    facts = {key: value for key, value in
        state.get('available_report_facts', {}).items() if key in sources or key.startswith('hpc_')}
    if 'hpc_execution_job' in state:
        job=state['hpc_execution_job']
        sections.append('Actual execution assignment\n'+'\n'.join(_lines(job)))
    if 'hpc_commission' in state:
        commission=state['hpc_commission']
        sections.append('Commission\n'+'\n'.join(_lines({key:commission[key] for key in
            ('objective','resource_id','obligations','preferences') if key in commission})))
    # Instructions are supplied once. Frozen files, historical receipts and
    # bookkeeping remain host-owned; current returned operands are not a
    # separate model-maintained operational ledger or prescribed job stages.
    for name,title in (
            ('goal','Goal'),('caller_question','Caller request'),
            ('scope','Assigned record scope'),
            ('resource_context','Whole-workflow bounds and resource planning'),
            ('execution_resource_capabilities','Actual execution resource contracts'),
            ('execution_initial_information','Retained initial resource observations'),
            ('execution_resource_information','Retained resource information'),
            ('selected_launch_instructions','Selected launch instructions'),
            ('launch_instruction_library','Available launch instruction reader'),
            ('tool_knowledge','Available tool instruction reader'),
            ('execution_assignment','Assigned job and acceptance'),
            ('execution_resource','Assigned resource'),
            ('coordinator_workspace','Local input workspace'),
            ('execution_progress','Measured execution progress'),
            ('execution_completion','Saved completion'),
            ('hpc_candidates','Candidate computations and allocation requests'),
            ('hpc_child_commission','Original commission for a selected child'),
            ('hpc_child_scope','Original scope for a selected child'),
            ('hpc_owner_episode_id','Owning HPC episode'),
            ('hpc_report_form','Requested HPC return fields'),
            ('hpc_launch_report_form','Requested native execution return fields'),
            ('hpc_tool_request','Requested scientific computation'),
            ('hpc_latest_comparison','Measured forecasts and expected credit'),
            ('hpc_model_ref','Current prediction model'),
            ('hpc_model_support','Prediction model support'),
            ('hpc_resource','Actual HPC resource contract'),
            ('hpc_credit','Earned credit'),('hpc_plans','Original plans'),
            ('hpc_latest_monitor','Latest actual job observation'),
            ('hpc_activity_decision','Expected credit of available next work'),
            ('hpc_monitor_controllers','Original pending monitor actions'),
            ('hpc_queue_refs','Saved queue observations'),
            ('hpc_available_training_ids','Available original training cases'),
            ('hpc_shared_history_refs','Received shared execution history'),
            ('hpc_launch_deliveries','Actual launch return delivery'),
            ('pending_work','Outstanding work'),('child_options','Available child roles'),
            ('report_deliveries','Recorded return delivery status'),
            ('feedback','Last action failure details'),
            ('current_credit','Current earned credit'),
            ('action_yields','Own recorded action yields'),
            ('controller','Existing continuation expectation'),
            ('time_accounting','Actual elapsed-time observations'),
            ('requested_report_purpose','Purpose of requested return'),
            ('tools','Available tools'),('tool_catalog','Available tools'),
            ('permitted_actions','Available episode actions'),
            ('requested_form','Requested return fields')):
        if name in state and state[name] not in (None,[],{}):
            value = ([_candidate_view(item) for item in state[name]]
                if name == 'hpc_candidates' else state[name])
            sections.append(title+'\n'+'\n'.join(_lines(value)))
    if facts:sections.append('Saved facts for the return\n'+'\n'.join(_lines(facts)))
    if lookup_results:
        sections.append('Requested information\n'+'\n'.join(_lines(lookup_results)))
    return '\n\n'.join(sections)
