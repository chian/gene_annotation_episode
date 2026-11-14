"""Private native result acquisition; original action and returned outcome preserved."""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a104.hmmer_native_result_views import FAMILY_SOURCES, family_for_program, validate_native_hmmer_result_selector
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_acquisition import ORIGIN, capture_local_bundle, is_native_hmmer_target, publish_original_source, original_source_payload
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_result_publication import prepare_native_hmmer_grading, publish_selected_native_hmmer_rows
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_result_records import NativeHMMERResultRecords, VERSION, operation_catalog

class NativeHMMERResultAcquisition(NativeHMMERResultRecords):

    def _action_directory(self, context, operation_key):
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _index(self, body):
        for reference in body['record_refs']:
            directory = self.directory / digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), {'run_id': body['run_id'], 'episode_id': body['episode_id'], 'operation_key': body['operation_key']})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        selector = validate_native_hmmer_result_selector(plain(context.assignment)['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
        directory = self._action_directory(context, operation_key)
        intent = {'target': target, 'assignment': plain(context.assignment), 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'scope': plain(context.scope)}
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            if self.completion(context) is not None:
                raise ContractError('execution_results_assignment_already_completed')
            if not (directory / 'observation.json').exists():
                observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory / 'observation.json', observation)
            observation = _read(directory / 'observation.json')
            body = {'version': VERSION, 'run_id': context.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope), 'assignment': plain(context.assignment), 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'target': target, 'observation': observation, 'capture': None, 'prepared': None, 'source_ref': None, 'record_refs': [], 'rows': [], 'failures': [], 'complete': False}
            if tool_name == 'execution.results.collect':
                capture = capture_local_bundle(self.store, target=target, directory=directory / 'capture')
                body['capture'] = capture
                body['failures'].extend(capture['failures'])
                if capture['bundle_validated']:
                    bundle = json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                    configuration = self.owner.resources[target['resource_id']]
                    policy = LocalJobPolicy(**configuration['policy'])
                    try:
                        prepared = prepare_native_hmmer_grading(self.store, bundle=bundle, bundle_artifact_ref=capture['bundle_artifact_ref'], artifacts=capture['artifacts'], directory=directory / 'grading', policy=policy, selector=selector)
                    except (ValueError, OSError) as error:
                        prepared = None
                        body['failures'].append({'stage': 'grading', 'code': str(error) if isinstance(error, ValueError) else 'native_hmmer_grading_unavailable', 'record_key': None})
                    body['prepared'] = prepared
                    source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                    body['source_ref'], body['record_refs'] = (source, [source])
                    if prepared is not None:
                        if (directory / 'publication.json').exists():
                            publication = _read(directory / 'publication.json')
                        else:
                            publication = publish_selected_native_hmmer_rows(self.store, source_ref=source, bundle=bundle, prepared=prepared, scope=plain(context.scope), selector=selector)
                            _immutable(directory / 'publication.json', publication)
                        body.update(record_refs=publication['record_refs'], rows=publication['rows'])
                        body['failures'].extend(publication['failures'])
                        body['complete'] = capture['complete'] and bundle['returncode'] == 0 and (not bundle['failures']) and prepared['numerical_complete'] and (not any((row['status'] == 'invalid' for row in publication['rows']))) and (observation['state'] == 'completed') and (observation['returncode'] == 0)
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}
