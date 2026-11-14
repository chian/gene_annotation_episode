from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
import json
from gene_annotation_episode.episodic_workflow.root.a107.domain import canonical
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import EpisodeBindingRegistry, BindingContext, _plain
from gene_annotation_episode.episodic_workflow.root.a107.state import Store
BASE = Path(__file__).parents[2] / 'tests/fixtures/source_records'
PRIMARY = BASE / 'primary_pdx_partner_015'

class OriginalReceivedEvidence:

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        return self._component_scoring_facts(context)

    def validate_received_report(self, context, form, schema):
        if context.role == 'annotation':
            self._validate_component_axis_report(context, form, schema)

class OriginalRegistry(EpisodeBindingRegistry):

    def _received_report_mapping(self, name, argument, *, context=None):
        supplied = {}
        for binding in self._context_bindings(context if context is not None else argument):
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            value = callback(argument)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('received_report_field_conflict:' + name)
            supplied.update(_plain(value))
        return supplied

    def validate_received_report(self, context, form, schema):
        for binding in self._context_bindings(context):
            callback = getattr(binding, 'validate_received_report', None)
            if callback is not None:
                callback(context, form, schema)
from gene_annotation_episode.episodic_workflow.root.a107.runtime import ContractInformationError, Episode, EpisodeGoal, EpisodeRequest, Record, _plain as _runtime_plain, validate_saved_fact_form

def original_assemble_scientific_process(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise ContractInformationError('report_contract_required_for_declaration')
        validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _runtime_plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _runtime_plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _runtime_plain(scientific_process)
    identity = Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)

def original_assemble_hpc_work_planning(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise ContractInformationError('report_contract_required_for_declaration')
        validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _runtime_plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _runtime_plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _runtime_plain(scientific_process)
    identity = Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)

def original_assemble_published_evidence_assessment(workflow, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None):
    path = (*parent_path, (name, key))
    goal = EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
    message = {'scope': scope, 'initial_report': initial or {}}
    if workflow.inprocess_completion_order is not None:
        message['inprocess_completion_order'] = {'version': workflow.inprocess_completion_order}
    if report_contract_declaration is not None:
        if contract is None:
            raise ContractInformationError('report_contract_required_for_declaration')
        validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
        message['report_contract_declaration'] = _runtime_plain(report_contract_declaration)
    if job_assignment is not None:
        message['job_assignment'] = job_assignment
    if episode_assignment is not None:
        workflow.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
        message['episode_assignment'] = _runtime_plain(episode_assignment)
    if scientific_process is not None:
        message['scientific_process'] = _runtime_plain(scientific_process)
    identity = Episode.identity(workflow.context, workflow.grains[name], key, parent_path=parent_path)
    if workflow.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.scientific_process_records import scientific_invocation_ref
        message['scientific_invocation_ref'] = scientific_invocation_ref(workflow.run_id, path)
    if workflow.receipts is not None:
        parent_id = Episode.identity(workflow.context, workflow.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
        message['knowledge_inheritance'] = workflow.receipts.bind(identity.episode_id, parent_id)
    request = EpisodeRequest(goal, Record(message), contract)
    return (path, goal, message, identity, request)

def source(store, raw, *, parents=(), text=None):
    artifact = store.artifact(raw, 'application/octet-stream')
    text_ref = store.artifact(text, 'text/plain') if text is not None else None
    return store.put('source', {'provider': 'source_reaction_example', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': text_ref, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def witness(ref, raw, quote, representation='original'):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': representation, 'start': start, 'end': start + len(token), 'quote': quote}

def setup_case(path, *, case='primary_crossed', components=None, target_sequence=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT' if target_sequence is None else target_sequence, molecule='dna' if target_sequence is None else 'protein')
    if case == 'primary_crossed':
        manifest = json.loads((PRIMARY / 'PAPER_SOURCE_RECORD_001.json').read_text())
        original_args = json.loads((PRIMARY / 'PAPER_ARGUMENTS_001.json').read_text())
        sources, refs = ({}, [])
        for row in manifest['sources'][:2]:
            raw = (PRIMARY / row['file']).read_bytes()
            saved = source(store, raw, parents=refs[:1])
            sources[row['source_ref']] = saved['id']
            refs.append(saved['id'])
        recipe = json.loads((PRIMARY / 'PAPER_SELECTION_001.json').read_text())
        args = deepcopy(original_args)
        args['source_ref'] = sources[args['source_ref']]
        for selected in (*args['literals'].values(), *args['interpretation_witnesses']):
            if selected:
                selected['source_ref'] = sources[selected['source_ref']]
    else:
        raw = b'Synthetic subject; Synthetic partner; PLP assay; product formation; reference glutamine; omitted glutamine; addback glutamine; per mg subject. All other declared conditions are matched.'
        paper = source(store, raw)
        refs = [paper['id']]
        w = lambda q: witness(paper['id'], raw, q)
        literal_quotes = ('Synthetic subject', 'Synthetic partner', 'PLP assay', 'product formation', 'per mg subject', 'reference glutamine', 'omitted glutamine', 'addback glutamine', 'PLP assay')
        args = {'source_ref': paper['id'], 'source_kind': 'synthetic_fixture', 'literals': {name: w(quote) for name, quote in zip(LITERAL_FIELDS, literal_quotes)}, 'interpretation_witnesses': [w('All other declared conditions are matched.')]}
        arms = {}
        for role, value in (('reference', 100), ('omitted', 20), ('addback', 90)):
            arms[role] = {'subject_ref': 'synthetic_subject', 'partner_ref': 'synthetic_partner', 'partner_state': 'absent' if role == 'omitted' else 'present', 'endpoint_ref': 'synthetic_PLP', 'normalization_ref': 'synthetic_subject_mass', 'unit': 'pmol/min/mg', 'conditions': {'coverage': 'complete', 'factors': [{'factor': 'nitrogen_source', 'level': 'glutamine', 'unit': 'identity'}, {'factor': 'temperature', 'level': 37, 'unit': 'degC'}]}, 'measurement': {'measurement_id': 'synthetic_' + role, 'status': 'observed', 'value': value, 'origin': 'synthetic', 'spread': {'kind': 'unreported', 'magnitude': None}}}
        if case == 'censored':
            arms['omitted']['measurement'].update(status='upper_bound', value=5)
        elif case == 'baseline_reused':
            arms['addback']['measurement'].update(measurement_id='synthetic_reference', value=100)
        recipe = {'version': 'literature_partner_selection_v1', 'inputs': {'version': 'literature_partner_inputs_v1', 'arms': arms}}
    dataset = source(store, json.dumps(recipe), parents=refs)
    refs.append(dataset['id'])
    args['data_source_ref'] = dataset['id']
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': refs, 'requested_partner_components': list(COMPONENTS if components is None else components)}
    context = BindingContext('partner-fixture-run', 'partner-fixture-child', 'literature', (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return (store, context, args)
COMPONENTS = ('reference_rate', 'omitted_rate', 'addback_rate', 'partner_loss', 'partner_loss_fraction', 'addback_gain', 'addback_fraction', 'restored_reference_fraction')
LITERAL_FIELDS = ('subject', 'partner', 'experiment', 'endpoint', 'normalization', 'reference_condition', 'omitted_condition', 'addback_condition', 'function')
