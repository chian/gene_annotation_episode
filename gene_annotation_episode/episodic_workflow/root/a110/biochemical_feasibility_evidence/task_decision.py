"""Private scientific task presentation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.scientific_decision_presentation import Mapping, _pick, _record, _registered_return_schema_view, _scalar, _schema, _section, _table, _values, is_published_scientific_context, render_episode_steering, schema_fingerprint, text_instructions

def _task(state, instructions):
    process = state['biochemical_feasibility_evidence']
    assignment = process.get('assignment', {})
    goal = state.get('goal', {})
    parts = ['TASK', '', text_instructions(instructions)]
    assigned_goal = _pick(goal, ('objective', 'task_context')) if isinstance(goal, Mapping) else goal
    _section(parts, 'Assigned work', _values(assigned_goal) if isinstance(goal, Mapping) else _scalar(goal))
    if isinstance(goal, Mapping) and 'result_contract' in goal:
        contract, form = (goal['result_contract'], state.get('requested_form'))
        if form is None or schema_fingerprint(contract) != schema_fingerprint(form):
            _section(parts, 'Assigned result contract', _schema(_registered_return_schema_view(contract, state.get('available_report_facts', {})), 'result_contract', named_definitions=True))
    _section(parts, 'Fixed scope', _values(state.get('scope', {})))
    _section(parts, 'Parent constraints', _values(assignment.get('constraints', {})))
    _section(parts, 'Parent-supplied context', _values(assignment.get('context', {})))
    if assignment.get('evidence_refs'):
        _section(parts, 'Parent-selected evidence operands', _values(assignment['evidence_refs']))
    working = state.get('working_state', {})
    material = {name: [_record(row) for row in working[name]] for name in ('subjects', 'materials', 'collections', 'material_links') if working.get(name)}
    material.update(_pick(working, ('target_binding', 'read_library_access', 'supplied_context_source_refs')))
    if material:
        _section(parts, 'Supplied material and scoped access', _values(material))
    selected_sources = set(assignment.get('evidence_refs', ())) | set(working.get('supplied_context_source_refs', ()))
    source_operands = [{'source_ref': row['id'], **_pick(row, ('origin', 'provider', 'accession', 'version', 'uri'))} for row in working.get('sources', ()) if row.get('id') in selected_sources]
    if source_operands:
        _section(parts, 'Selected source operands (metadata only)', 'These are received source identities and provenance for navigation. Read the actual contents to establish what each source supports.\n\n' + _values(source_operands))
    axis = process['evidence_axis']
    _section(parts, 'Investigate the supplied target: ' + axis.get('name', ''), axis['investigation_instructions'])
    thought = process.get('thought_pattern', {})
    _section(parts, 'Reason about the evidence: ' + thought.get('name', ''), '\n\n'.join((_scalar(thought[name]) for name in ('description', 'use_when') if name in thought)))
    for field, label in (('live_alternatives', 'Alternatives to distinguish'), ('decision_guidance', 'How to choose and revise the investigation')):
        if thought.get(field):
            _section(parts, label, '\n'.join(('- ' + item for item in thought[field])))
    if thought.get('outcome_contingencies'):
        _section(parts, 'How outcomes affect the next choice', _table(('If observed', 'Then consider'), ((row['if_observed'], row['then_consider']) for row in thought['outcome_contingencies'])))
    _section(parts, 'Limits of this reasoning approach', thought.get('boundary'))
    for tool in process.get('child_tool_info', ()):
        _section(parts, 'Selected tool: ' + tool['name'] + ' (' + tool['resources'] + ')', tool['description'] + '\n\n' + tool['instructions'])
    selected_manuals = state.get('selected_launch_instructions') or {}
    for section in selected_manuals.get('sections', ()):
        _section(parts, 'Assigned software or resource instructions: ' + section['entry_id'] + ' / ' + section['section_id'], section['text'])
    tools = state.get('tools', ())
    if tools:
        _section(parts, 'Callable operations', _table(('Operation', 'Meaning'), ((tool['name'], tool.get('description', '')) for tool in tools)))
        for tool in tools:
            if 'input_schema' in tool:
                _section(parts, 'Operands for ' + tool['name'], _schema(tool['input_schema'], 'arguments', named_definitions=True))
    _section(parts, 'Permitted child roles', _values(process.get('permitted_children', [])))
    _section(parts, 'Child construction and requested facts', state.get('child_options'))
    _section(parts, 'Evidence through child returns', "Choose each child's return facts to carry the evidence needed for your question. committed_record_refs carries the acquired scientific record references; select the provider's coverage/completeness facts when interpreting acquired rows or an empty result. A job handle, usable handoff or null failure field alone does not return the search data. Keep a completed empty acquisition distinct from partial or unavailable acquisition, and keep those acquisition facts separate from evidence for a biological function.")
    if state.get('contract_information_profile') == 'operation_contract_information_v1':
        _section(parts, 'Discover and select exact return contracts', "Within this pending decision, request_context with view=composition_information, operation=episode.return_contract and arguments containing the permitted child's role and source returns its exact frozen fact type and meaning. In your chosen closed child form, a top-level field may contain only $ref with value episode-fact:<source>. For example, records can reference episode-fact:committed_record_refs. The host expands your explicit selection to its original type and fills recorded facts; leave those fact fields out of initial_report_json. Choose the relevant sources and return their actual saved grading results, numerical status, qualifications and missing inputs. Reporting does not require another supported/contradicted, function, path or scope verdict: use the grading sheet's existing criteria and status, without inventing a score threshold or asking a child to judge the same result again. Contract lookup creates no evidence, child, completed action or credit.")
    _section(parts, 'Information requested by the parent', state.get('requested_report_purpose'))
    if state.get('requested_form') is not None:
        form = state['requested_form']
        sources = state.get('available_report_facts', {})
        _section(parts, 'Parent return form', _schema(_registered_return_schema_view(form, sources), 'return'))
        used = {row.get('x-source') for row in form.get('properties', {}).values()}
        _section(parts, 'Meaning of requested recorded facts', _table(('Source', 'Meaning'), ((name, sources[name].get('meaning', '')) for name in sources if name in used)))
    _section(parts, 'Return interpretation timing', state.get('report_lifecycle'))
    if process.get('selection'):
        _section(parts, 'Callable selection operands for child assignment (copy exact values)', _values(process['selection']))
    return '\n'.join(parts)

def render_biochemical_feasibility_evidence_prompt(state, instructions, *, lookup_results=()):
    """Complete recurring TASK plus current, mechanically selected STEERING."""
    if not is_published_scientific_context(state):
        raise ValueError('published_scientific_instructions_required')
    return _task(state, instructions) + '\n\n' + render_episode_steering(state, lookup_results=lookup_results)
