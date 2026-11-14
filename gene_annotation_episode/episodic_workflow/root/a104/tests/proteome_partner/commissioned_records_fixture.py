from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.episode import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a104.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a104.runtime import Record, TypedReportContract

def refs_schema(namespace='source'):
    return {'type': 'object', 'properties': {'refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': 'committed_record_refs'}}, 'required': ['refs'], 'additionalProperties': False}

def request():
    return {'version': 'bvbrc_appservice_request_v1', 'effect_contract': 'selected_api_effects_v1', 'required_application_id': 'Homology', 'parameters': {'output_path': '/synthetic/work/output', 'output_file': 'selected', 'input_type': 'dna', 'input_source': 'fasta_data', 'input_fasta_data': '>q\nACGT\n', 'db_type': 'fna', 'db_source': 'fasta_data', 'db_fasta_data': '>s\nACGA\n', 'blast_program': 'blastn', 'blast_max_hits': 2}, 'start_parameters': {}, 'definition_inputs': [], 'input_bindings': [], 'workspace_targets': []}

def api_assignment(query=None, resource='selected-api'):
    return {'version': 'api_service_assignment_v1', 'service': 'bvbrc_appservice', 'resource_id': resource, 'endpoint': 'usable_handoff', 'request': request() if query is None else deepcopy(query), 'constraints': {}}

def launch_assignment(query=None):
    return {'version': 'execution_launch_assignment_v1', 'requests': {'selected-api': api_assignment(query), 'second-api': api_assignment(query, 'second-api')}, 'immutable_input_versions': [], 'constraints': {'allowed_kinds': ['api']}}

def selector():
    return {'version': 'bvbrc_appservice_result_selector_v1', 'endpoint': 'requested_artifacts', 'requirements': [{'requirement_id': 'native', 'role': 'native_output', 'required': True, 'declared_format': {'format': 'json', 'version': None, 'mode': None, 'producer_source_ref': None, 'transformation_evidence': []}, 'producer_rule_evidence': None, 'exact_object': None}], 'adapter': None, 'requested_schema': refs_schema(), 'supplied_metadata': [], 'supplied_capabilities': []}

def content(binding, *, pointer=''):
    return {'content': deepcopy(binding), 'pointer': pointer}

class SavedRecords:
    """Controlled historical records; no fake transport response is a measurement."""

    def __init__(self, store, *, manifest_path=None):
        self.store, self.run_id = (store, 'appservice-custody-fixture')
        self.journal = Journal(store, self.run_id)
        if manifest_path is None:
            self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        else:
            self.scope = {'subject_refs': store.create_problem(manifest_path=manifest_path)['subject_refs']}
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.custody = AppServiceCustody(store, self.run_id)
        goal = EpisodeGoal.root(objective='Test exact input custody', result_contract={'role': 'annotation'})
        self.root = self.save_context('annotation', (('annotation', 'root'),), {}, goal, None)

    def save_context(self, role, path, assignment, goal, contract, *, parent=None, save=True):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inherited = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        message = {'scope': deepcopy(self.scope), 'initial_report': {}, 'episode_assignment': deepcopy(assignment), 'knowledge_inheritance': inherited}
        req = EpisodeRequest(goal, Record(message), contract).as_record()
        ctx = BindingContext(self.run_id, episode_id, role, path, self.scope, assignment, req)
        if save:
            self.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path), 'request': canonical(req), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        return ctx

    def child(self, parent, role, assignment, index, *, schema=None, save=True, action=True, model=True, encoded=False):
        schema = refs_schema() if schema is None else schema
        contract = TypedReportContract('Return only the requested source references', schema, lambda *_: True)
        goal = EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)['goal']), objective='Perform selected fixture work', result_contract=schema)
        path = (*parent.path, (role, 'child_' + str(index)))
        ctx = self.save_context(role, path, assignment, goal, contract, parent=parent, save=save)
        selection = {'kind': 'episode_child', 'role': role, 'assignment': deepcopy(assignment), 'scope': deepcopy(self.scope), 'goal': 'Perform selected fixture work', 'purpose': contract.decision, 'schema_json': canonical(schema), 'initial_report_json': '{}'}
        if model:
            response = {'selection': deepcopy(selection), 'report_update': {}}
            if encoded:
                response['selection']['assignment'] = canonical(assignment)
            original_schema = {'type': 'object', 'properties': {'selection': {'type': 'object', 'properties': {'kind': {'const': 'episode_child'}, 'assignment': {'type': 'object'}}, 'required': list(selection)}}}
            self.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': index, 'purpose': 'decision', 'request': canonical({'context': {}, 'schema': original_schema}), 'response': canonical(response)})
        if action:
            self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index, 'action': canonical(selection), 'result': None, 'credit': None})
        return ctx

    def source(self, raw=b'{"native": [0, 1.25]}', **fields):
        artifact = self.store.artifact(raw, 'application/json')
        source = self.store.put('source', {'provider': 'custody.fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': '2026-10-24T00:00:00+00:00', **fields}, origin='tool')
        return {'source_ref': source['id'], 'artifact_field': 'artifact_ref', 'artifact_ref': artifact, 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}

    def own(self, context, reference, index=0, *, status='completed', tool='source.inspect'):
        result = {'status': status, 'record_refs': [reference], 'changed_record_refs': [reference], 'result': {}}
        self.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index, 'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': {}}), 'result': canonical(result), 'credit': None})
        if status in {'completed', 'partial'}:
            self.receipts.receive(context.episode_id, [reference], kind='own_action', source_index=index)
        return result

    def admit(self, parent, child, reference):
        index = int(child.path[-1][1][6:])
        contract = plain(child.request)['report_contract']
        form = {'refs': [reference]}
        self.journal.save('runtime_forms', {'episode_id': child.episode_id, 'facts': canonical({'committed_record_refs': [reference]}), 'form': canonical(form)})
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24], 'child_episode_id': child.episode_id, 'contract': canonical(contract), 'form': canonical(form), 'failure': None})
        self.receipts.receive(parent.episode_id, [reference], kind='child_form', source_index=index)
        return form

    def supplied_request(self, binding):
        query = request()
        query['definition_inputs'] = [{'binding_id': 'original-definition', 'evidence': content(binding)}]
        return query

    def tree(self, query=None, *, launch_index=2):
        launch = self.child(self.root, 'launch', launch_assignment(query), launch_index)
        self.receipts.receive(launch.episode_id, self.custody.initial_references(launch), kind='initial')
        api = self.child(launch, 'launch_api', api_assignment(query), 0)
        return (launch, api)
