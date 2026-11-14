"""Deterministic acquisition/publication inside the existing results episode.

This is an operation binding, not an episode or a private investigation loop.
The original selected action and its immutable receipt qualify every return.
"""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest, obj
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_hmmer_native_result_views import FAMILY_SOURCES, family_for_program, validate_native_hmmer_result_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_hmmer_acquisition import ORIGIN, is_native_hmmer_target, original_source_payload
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
VERSION = 'native_hmmer_acquired_result_v1'

def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Observe the original native attempt once; this does not acquire numerical results.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Capture the original sealed HMMER bundle and complete files, populate deterministic numerical sheets, and return exactly the assigned native rows and metrics. No new search or retry.', 'input_schema': obj({})}]

class NativeHMMERResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.directory = owner.directory / 'native-hmmer-result-index'

    def applies(self, context):
        return context.role == 'results' and is_native_hmmer_target(self.owner._target(context))

    def _directory(self, context):
        return self.owner._result_directory(context) / 'native-hmmer-actions'

    def _validate_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared', 'source_ref', 'record_refs', 'rows', 'failures', 'complete'}
        if not isinstance(body, dict) or set(body) != fields or body['version'] != VERSION or (body['run_id'] != self.owner.run_id):
            raise ContractError('native_hmmer_result_receipt_invalid')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], body['scope'])
        if target != body['target'] or not is_native_hmmer_target(target):
            raise ContractError('native_hmmer_result_original_target_conflict')
        validate_native_hmmer_result_selector(body['assignment']['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        row = self.owner._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        if body['tool_name'] not in {entry['name'] for entry in operation_catalog()} or body['arguments'] != {}:
            raise ContractError('native_hmmer_result_original_operation_conflict')
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.owner.run_id, body['episode_id'])).fetchone()
        if episode is None:
            raise ContractError('native_hmmer_result_original_episode_missing')
        message = json.loads(episode['request'])['message']
        if message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope'] or json.loads(episode['path'])[-1][0] != 'results':
            raise ContractError('native_hmmer_result_original_assignment_conflict')
        directory = self.owner.directory / 'execution-results' / digest([self.owner.run_id, body['episode_id']]) / 'native-hmmer-actions' / digest(body['operation_key'])
        if not (directory / 'receipt.json').exists() or _read(directory / 'receipt.json') != body:
            raise ContractError('native_hmmer_result_original_receipt_conflict')
        if body['capture'] is not None and _read(directory / 'capture' / 'capture.json') != body['capture']:
            raise ContractError('native_hmmer_result_capture_receipt_conflict')
        if body['prepared'] is not None and json.loads((directory / 'grading' / 'native-hmmer-grading' / 'prepared.json').read_bytes()) != body['prepared']:
            raise ContractError('native_hmmer_result_prepared_receipt_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if outcome.get('status') != 'completed' or outcome.get('result') != body or outcome.get('record_refs') != body['record_refs']:
                raise ContractError('native_hmmer_result_saved_outcome_conflict')
        if body['source_ref'] is not None:
            source = self.store.get(body['source_ref'])
            if source.get('provider') != 'episode.execution_result' or source.get('origin') != 'tool' or source.get('version') != 'native_hmmer_bundle_v1' or (source['artifact_ref'] != body['capture']['bundle_artifact_ref']) or (body['source_ref'] not in body['record_refs']):
                raise ContractError('native_hmmer_result_original_source_conflict')
            bundle = json.loads(self.store.get_artifact(source['artifact_ref']))
            if bundle['requested_job'] != target['assignment']['requested_job'] or bundle['identity']['run_id'] != self.owner.run_id or bundle['identity']['execution_id'] != target['execution_id'] or (bundle['identity']['resource_id'] != target['resource_id']):
                raise ContractError('native_hmmer_result_original_bundle_conflict')
            expected_source = original_source_payload(bundle=bundle, capture=body['capture'], prepared=body['prepared'])
            if {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != expected_source:
                raise ContractError('native_hmmer_result_source_content_conflict')
            prepared = body['prepared']
            if prepared is not None and prepared['source_grading_artifact_ref'] not in source['auxiliary_artifact_refs']:
                raise ContractError('native_hmmer_result_grading_custody_conflict')
            if prepared is not None:
                publication = _read(directory / 'publication.json')
                if publication['record_refs'] != body['record_refs'] or publication['rows'] != body['rows']:
                    raise ContractError('native_hmmer_result_publication_receipt_conflict')
            for projected in body['rows']:
                if projected['source_ref'] != source['id']:
                    raise ContractError('native_hmmer_result_row_source_conflict')
                reference = projected['observation_ref']
                if reference is None:
                    continue
                observation = self.store.get(reference)
                if reference not in body['record_refs'] or observation.get('origin') != 'tool' or observation.get('source_ref') != source['id'] or (observation.get('subject_refs') != [projected['subject_ref']]) or (observation.get('source_subject_refs') != projected['reference_refs']) or (observation.get('native_hmmer', {}).get('record_key') != projected['record_key']) or (observation['native_hmmer'].get('bundle_artifact_ref') != source['artifact_ref']):
                    raise ContractError('native_hmmer_result_row_observation_conflict')
                values = {value['name']: value['value']['value'] for value in observation['measurements']}
                if any((values.get(value['name']) != value['value'] for value in projected['measurements'])):
                    raise ContractError('native_hmmer_result_row_measurement_conflict')
        elif body['record_refs'] or body['rows']:
            raise ContractError('native_hmmer_result_source_required')
        complete = False
        if body['source_ref'] is not None and body['prepared'] is not None:
            complete = body['capture']['complete'] and bundle['returncode'] == 0 and (not bundle['failures']) and body['prepared']['numerical_complete'] and (not any((row['status'] == 'invalid' for row in body['rows']))) and (body['observation']['state'] == 'completed') and (body['observation']['returncode'] == 0)
        if type(body['complete']) is not bool or body['complete'] != complete:
            raise ContractError('native_hmmer_result_completion_conflict')
        return body

    def read_result(self, reference, scope, *, assignment=None):
        self.store.get(reference)
        directory = self.directory / digest(reference)
        if directory.exists():
            for path in sorted(directory.glob('*.json')):
                pointer = _read(path)
                if pointer.get('run_id') != self.owner.run_id:
                    raise ContractError('native_hmmer_result_index_run_conflict')
                receipt = self.owner.directory / 'execution-results' / digest([self.owner.run_id, pointer['episode_id']]) / 'native-hmmer-actions' / digest(pointer['operation_key']) / 'receipt.json'
                body = self._validate_body(_read(receipt), scope)
                if assignment is not None and body['assignment'] != plain(assignment):
                    continue
                if reference not in body['record_refs']:
                    raise ContractError('native_hmmer_result_index_reference_conflict')
                return body
        raise ContractError('not_a_native_hmmer_acquired_result')

    def _own_bodies(self, context):
        directory = self._directory(context)
        if directory.exists():
            bodies = [_read(path) for path in directory.glob('*/receipt.json')]
            for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
                yield self._validate_body(body, context.scope)

    def facts(self, context):
        bodies = list(self._own_bodies(context))
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [], 'execution_result_refs': sorted({ref for body in bodies for ref in body['record_refs']}), 'execution_result_origin': deepcopy(ORIGIN) if any((body['capture'] is not None and body['capture']['complete'] for body in bodies)) else None, 'execution_completed': any((body['complete'] for body in bodies)), **{source: [] for source in FAMILY_SOURCES.values()}}
        fields = context.request.get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested = {field.get('x-source') for field in fields.values()}
        seen = set()
        for body in bodies:
            family = family_for_program(body['target']['assignment']['requested_job']['native_hmmer']['program'])
            source = FAMILY_SOURCES[family]
            if source not in requested:
                continue
            for row in body['rows']:
                key = (row['source_ref'], row['record_key'])
                if key not in seen:
                    result[source].append(row)
                    seen.add(key)
        return result

    def resolve(self, context, reference, namespace):
        if namespace == 'native_hmmer_row':
            try:
                if self.applies(context):
                    bodies = self._own_bodies(context)
                else:
                    selected = self.owner._selection(context)
                    bodies = [self.read_result(ref, context.scope) for ref in selected['known_record_refs'] if (self.directory / digest(ref)).is_dir()]
                return any((row['record_key'] == reference for body in bodies for row in body['rows']))
            except (ValueError, KeyError, OSError, TypeError):
                return False
        if namespace not in {None, 'source', 'execution_result'}:
            return False
        try:
            self.read_result(reference, context.scope, assignment=context.assignment if self.applies(context) else None)
            return namespace != 'source' or self.store.get(reference)['record_type'] == 'source'
        except (ValueError, KeyError, OSError, TypeError):
            return False
