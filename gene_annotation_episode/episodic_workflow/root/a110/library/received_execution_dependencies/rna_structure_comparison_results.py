from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_result_publication import authenticate_rna_results_commission
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_contracts import CALCULATOR_VERSION, SELECTOR_VERSION, validate_rna_comparison_issue, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_operands import SAVED_REFERENCE_FIELDS, _require, resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_views import PROJECTION_SOURCE
VERSION = 'rna_structure_comparison_result_receipt_v1'
IDENTIFIER_NAMESPACES = ('rna_comparison_receipt', 'rna_comparison_calculation')
FIELDS = {'version', 'run_id', 'episode_id', 'scope_key', 'assignment_digest', 'operation_key', 'tool_name', 'arguments', 'selected_action_digest', 'anchor_handoff_ref', 'selector', 'original_receipt_keys', 'selected_input_digests', 'comparison_sheet_artifact_ref', 'comparison_sheet_sha256', 'components_artifact_ref', 'components_sha256', 'calculator_version', 'projection_rows', 'issues', 'preparation_failure', 'delivery_complete'}
PREPARED_COPY_FIELDS = ('original_receipt_keys', 'selected_input_digests', 'comparison_sheet_artifact_ref', 'comparison_sheet_sha256', 'components_artifact_ref', 'components_sha256', 'calculator_version', 'projection_rows', 'issues', 'preparation_failure', 'delivery_complete')

def result_receipt_key(body):
    return 'rna_comparison_receipt:' + digest({key: body[key] for key in ('run_id', 'episode_id', 'operation_key')})

def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Check only the explicitly selected retained RNA inputs and recorded comparison receipts.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Calculate the assigned comparison from independently received retained sheets and return exactly its selected projections.', 'input_schema': obj({})}]

def _original_keys(selector):
    return [member['saved_input' if member['kind'] == 'saved_sheet' else 'failure']['result_receipt_key'] for member in selector['question']['membership'] if member['kind'] in {'saved_sheet', 'received_failure'}]

class NativeRNAStructureComparisonResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.directory = owner.directory / 'rna-structure-comparison-result-index'
        self.records = EpisodeReturnRecords(owner.store, owner.run_id, failure_prefix='rna_comparison_')

    @property
    def returns(self):
        return self.owner.native_rna_structure_returns

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == SELECTOR_VERSION

    def _saved_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'rna-structure-comparison-actions' / digest(operation_key)

    def _assignment(self, context, *, allow_unsaved=False):
        authenticate_rna_results_commission(self.store, context, allow_unsaved=allow_unsaved)
        _require(self.applies(context), 'original_results_owner_required')
        assignment = plain(context.assignment)
        _require(set(assignment) == {'version', 'handoff_ref', 'selector'} and assignment['version'] == 'execution_results_assignment_v1', 'selected_assignment_conflict')
        selector = validate_rna_comparison_selector(assignment['selector'])
        validate_rna_comparison_selected_inputs(self.store, context, selector, anchor_handoff_ref=assignment['handoff_ref'], returns=self.returns)
        return assignment

    def _resolve_operands(self, context, assignment):
        return resolve_rna_comparison_operands(self.store, context, assignment['selector'], anchor_handoff_ref=assignment['handoff_ref'], returns=self.returns)

    def _intent(self, context, assignment, target, operation_key, tool_name, arguments, selected):
        return {'run_id': context.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope), 'assignment': assignment, 'anchor_target': target, 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'selected_action_digest': digest(json.loads(selected['action']))}

    @staticmethod
    def _outcome(body):
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': deepcopy(body), 'feedback': None}

    def _validate_body(self, body, scope):
        _require(type(body) is dict and set(body) == FIELDS and (body['version'] == VERSION) and (body['run_id'] == self.owner.run_id), 'receipt_mismatch')
        context = self.records.context(body['episode_id'])
        assignment = self._assignment(context)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        _require(body['scope_key'] == digest(plain(context.scope)) and body['assignment_digest'] == digest(assignment) and (body['anchor_handoff_ref'] == assignment['handoff_ref']) and self.records._equal(body['selector'], assignment['selector']), 'receipt_mismatch')
        _require(body['tool_name'] in {item['name'] for item in operation_catalog()} and type(body['arguments']) is dict and (not body['arguments']), 'selected_action_mismatch')
        selected = self.owner._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        _require(body['selected_action_digest'] == digest(json.loads(selected['action'])), 'selected_action_mismatch')
        directory = self._saved_directory(body['episode_id'], body['operation_key'])
        target = self.owner.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)
        expected_intent = self._intent(context, assignment, target, body['operation_key'], body['tool_name'], body['arguments'], selected)
        _require(self.records._equal(_read(directory / 'intent.json'), expected_intent) and self.records._equal(_read(directory / 'receipt.json'), body), 'immutable_receipt_mismatch')
        if selected['result'] is not None:
            outcome, expected = (json.loads(selected['result']), self._outcome(body))
            _require(set(outcome) in (set(expected), {*expected, 'pending_work_after_action'}) and self.records._equal({key: outcome[key] for key in expected}, expected), 'recorded_outcome_mismatch')
            if 'pending_work_after_action' in outcome:
                from gene_annotation_episode.episodic_workflow.root.a110.waiting import validate_pending
                validate_pending(outcome['pending_work_after_action'])
        _require(body['original_receipt_keys'] == _original_keys(assignment['selector']) and body['calculator_version'] == CALCULATOR_VERSION and (type(body['delivery_complete']) is bool), 'receipt_mismatch')
        for issue in body['issues']:
            validate_rna_comparison_issue(issue)
        if body['tool_name'] == 'execution.results.status' or (directory / 'input-failure.json').exists():
            status = body['tool_name'] == 'execution.results.status'
            failure = _read(directory / ('status.json' if status else 'input-failure.json'))
            _require(type(failure) is dict and set(failure) == {'issues', 'cause'} and self.records._equal(failure['issues'], body['issues']), 'custody_record_mismatch')
            if failure['issues']:
                _require(len(failure['issues']) == 1 and type(failure['cause']) is dict and (set(failure['cause']) == {'exception_type', 'detail'}), 'custody_record_mismatch')
                problem = failure['issues'][0]
                expected = {'stage': 'input', 'code': problem['code'], 'member_id': problem['member_id'], 'comparison_id': None, 'selection_id': None, 'field': None, 'index': None}
                _require(problem == expected and problem['code'] in {'retained_sheet_missing', 'retained_sheet_digest_mismatch'} and any((m['member_id'] == problem['member_id'] and m['kind'] == 'saved_sheet' for m in assignment['selector']['question']['membership'])), 'custody_record_mismatch')
            else:
                _require(status and failure['cause'] is None, 'custody_record_mismatch')
            _require(not body['delivery_complete'] and body['projection_rows'] == [] and (body['selected_input_digests'] == []) and (body['preparation_failure'] is None) and all((body[key] is None for key in ('comparison_sheet_artifact_ref', 'comparison_sheet_sha256', 'components_artifact_ref', 'components_sha256'))), 'receipt_mismatch')
        else:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_publication import validate_prepared_rna_comparison
            operands = self._resolve_operands(context, assignment)
            prepared = _read(directory / 'grading' / 'prepared.json')
            validate_prepared_rna_comparison(self.store, prepared, selector=assignment['selector'], operands=operands, result_receipt_key=result_receipt_key(body))
            _require(all((self.records._equal(body[key], prepared[key]) for key in PREPARED_COPY_FIELDS)), 'prepared_receipt_mismatch')
        return deepcopy(body)

    def _own_bodies(self, context):
        self.records.authenticate(context, allow_unsaved=True)
        _require(self.applies(context), 'original_results_owner_required')
        directory = self._saved_directory(context.episode_id, 'unused').parent
        bodies = [_read(path) for path in directory.glob('*/receipt.json')] if directory.exists() else []
        for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
            _require(body['episode_id'] == context.episode_id and body['assignment_digest'] == digest(plain(context.assignment)), 'receipt_mismatch')
            yield self._validate_body(body, context.scope)

    def facts(self, context, *, verify_artifacts=True):
        requested = {node.get('x-source') for node in (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {}).values()}
        bodies = list(self._own_bodies(context))
        rows, seen, completed = ([], set(), False)
        for body in bodies:
            action = self.owner._selected_result_action(context.episode_id, body['operation_key'], body['tool_name'], body['arguments'])
            if action['result'] is None:
                continue
            completed = completed or body['delivery_complete']
            if PROJECTION_SOURCE in requested:
                for row in body['projection_rows']:
                    identity = canonical({key: value for key, value in row.items() if key != 'result_receipt_key'})
                    if identity not in seen:
                        rows.append(row)
                        seen.add(identity)
        return {PROJECTION_SOURCE: rows, 'execution_handoff_refs': [], 'execution_blast_hsps': [], 'execution_result_refs': [], 'execution_completed': completed, 'execution_result_origin': None}

    def resolve(self, context, reference, namespace):
        if not self.applies(context) or namespace not in IDENTIFIER_NAMESPACES:
            return False
        field = 'result_receipt_key' if namespace == IDENTIFIER_NAMESPACES[0] else 'calculation_key'
        return any((row[field] == reference for row in self.facts(context)[PROJECTION_SOURCE]))

    def retained_reference_access(self, context, reference, namespace):
        if any((reference.startswith(prefix + ':') for prefix in IDENTIFIER_NAMESPACES)):
            return self.resolve(context, reference, namespace)
        if namespace not in {None, 'artifact', 'source', 'execution_result', 'execution_handoff'}:
            return None
        if self.applies(context):
            assignment = plain(context.assignment)
            selected = [assignment['handoff_ref']]
            selected_handoffs = {assignment['handoff_ref']}
            for member in assignment['selector']['question']['membership']:
                if member['kind'] == 'saved_sheet':
                    selected.extend((member['saved_input'][key] for key in SAVED_REFERENCE_FIELDS))
                    selected_handoffs.add(member['saved_input']['handoff_ref'])
                elif member['kind'] == 'received_failure' and member['failure']['source_ref'] is not None:
                    selected.append(member['failure']['source_ref'])
            if namespace == 'execution_handoff' and reference not in selected_handoffs:
                return False
            if reference in selected:
                allowed = validate_rna_comparison_selected_inputs(self.store, context, assignment['selector'], anchor_handoff_ref=assignment['handoff_ref'], returns=self.returns)
                record = self.store.get(reference)
                return reference in allowed and namespace in {None, 'execution_result', record['record_type'], *({'execution_handoff'} if reference in selected_handoffs else set())}
        for action in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION)):
            body = json.loads(action['result'])['result']
            grading = self._saved_directory(body['episode_id'], body['operation_key']) / 'grading'
            prepared_path = grading / 'prepared.json'
            prepared = _read(prepared_path) if prepared_path.exists() else None
            refs = {body[key] for key in ('comparison_sheet_artifact_ref', 'components_artifact_ref')}
            if prepared is not None:
                refs.update((value for key, value in prepared.items() if key.endswith('artifact_ref')))
            worker_path = grading / 'worker-receipt.json'
            if worker_path.exists():
                worker = _read(worker_path)
                refs.update((value for key, value in worker.items() if key.endswith('artifact_ref')))
                refs.update((row['artifact_ref'] for row in worker['output_artifacts']))
                refs.add(worker['input_observation']['artifact_ref'])
            execution_path = grading / 'execution-receipt.json'
            if execution_path.exists():
                execution = _read(execution_path)
                refs.update((execution[key] for key in ('stdout_artifact_ref', 'stderr_artifact_ref')))
            if reference in refs:
                return self._independent_artifact_access(context, reference, namespace)
        return None

    def _independent_artifact_access(self, context, reference, namespace):
        """Preserve actual explicit custody of identical content-addressed bytes."""
        self.records.authenticate(context, allow_unsaved=True)
        if namespace not in {None, 'artifact', 'execution_result'}:
            return False
        old = self.owner.native_rna_structure_results.retained_reference_access(context, reference, namespace)
        if old is not None:
            return old
        assignment = plain(context.assignment)
        explicit = {row.get('artifact_ref') for row in assignment.get('requested_job', {}).get('native_rna_structure', {}).get('operands', [])}
        if reference in explicit:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_result_publication import validate_rna_structure_job_inputs
            return reference in validate_rna_structure_job_inputs(self.store, context, assignment)
        if reference in self.store._refs(assignment) and reference in set(EpisodeReceipts(self.store, context.run_id).known(context.episode_id, baseline=True)):
            return True
        scope = self.store.validate_scope(plain(context.scope))
        if any((self.store.get(subject).get('sequence_ref') == reference for subject in scope.get('subject_refs', []))):
            return namespace in {None, 'artifact'}
        for action in self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL', (context.run_id, context.episode_id)):
            outcome = json.loads(action['result'])
            if outcome.get('status') in {'completed', 'partial'} and reference in outcome.get('record_refs', []):
                body = outcome.get('result')
                if isinstance(body, dict) and body.get('version') == VERSION:
                    self._validate_body(body, context.scope)
                return True
        old = self.returns.resolve_received(context, reference, namespace)
        if old is not None:
            return old
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_returns import requested_sources
        for attempt in self.returns._attempts(context):
            schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
            if requested_sources(schema) or any((node.get('x-source') == PROJECTION_SOURCE for node in schema.get('properties', {}).values())):
                continue
            _, form, schema = self.returns._attempt(context, attempt['decision_index'])
            explicit_refs = []

            def collect(value, declared_namespace):
                if declared_namespace in {None, 'artifact'}:
                    explicit_refs.append(value)
                return True
            validate_form(form, schema, collect)
            if reference in explicit_refs:
                return True
        return False
