"""Original scientific request preparation for experimental_activity_evidence."""
from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError

def prepare_request(workflow, source, selection, index):
    scope = workflow.store.validate_scope(selection['scope'], parent_scope=source.scope)
    role = 'experimental_activity_evidence'
    episode_assignment = None
    experimental_activity_evidence = None
    schema, report_declaration = workflow.expanded_contract_form(source, selection, index, role)
    binding = workflow.episode_bindings.for_child(source.path, role)
    required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(workflow.binding_context(source), role)
    sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
    for fact_source in required:
        if sources.count(fact_source) != 1:
            raise _original_runtime.ContractError('child_return_requires_' + fact_source)
    hpc_launch = False
    initial = _original_runtime.parse_json_object(workflow.child_initial_report_input(source, selection, role))
    _original_runtime.validate_form(initial, _original_runtime.interpretation_schema(schema), lambda *_: True)
    specialist = workflow.specialist(source)
    allowed = workflow.available_child_roles(source) if workflow.annotation_child_roles is not None else specialist.allowed_children(workflow.binding_context(source), workflow.services.capabilities()) if specialist is not None else workflow.episode_bindings.entry_roles
    if role not in allowed:
        raise ValueError('child_role_not_available_to_parent')
    binding = workflow.episode_bindings.for_child(source.path, role)
    workflow.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
    closed = {}
    recorded = workflow.journal.row('runtime_actions', source.episode_id, index)
    if recorded is not None and recorded['result'] is not None and (_original_runtime._json(_original_runtime.json.loads(recorded['action'])) == _original_runtime._json(selection)) and (_original_runtime.json.loads(recorded['result']).get('status') == 'completed'):
        from gene_annotation_episode.episodic_workflow.root.a105.episode_return_records import EpisodeReturnRecords
        child_id = _original_runtime.Episode.identity(workflow.context, workflow.grains[role], f'child_{index}', parent_path=source.path).episode_id
        if workflow.journal.row('runtime_episodes', child_id) is not None:
            records = EpisodeReturnRecords(workflow.store, workflow.run_id, failure_prefix='scientific_closed_')
            candidate = records.context(child_id)
            read_closed = getattr(workflow.services, 'scientific_closed_request', None)
            if callable(read_closed) and read_closed(candidate) is not None:
                closed['closed_context'] = candidate
    prepared = binding.prepare_invocation(workflow.binding_context(source), role, selection['assignment'], scope, f'{workflow.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
    episode_assignment = prepared['assignment']
    experimental_activity_evidence = prepared['experimental_activity_evidence']
    assignment = None
    return {'scope': scope, 'role': role, 'schema': schema, 'report_declaration': report_declaration, 'initial': initial, 'episode_assignment': episode_assignment, 'experimental_activity_evidence': experimental_activity_evidence, 'assignment': assignment}
