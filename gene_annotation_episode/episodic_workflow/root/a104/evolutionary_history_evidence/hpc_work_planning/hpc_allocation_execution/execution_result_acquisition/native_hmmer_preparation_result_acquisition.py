"""Private native result acquisition; original action and returned outcome preserved."""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a104.form_reference_validation import _binding_key, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES, preparation_fact_sources, validate_preparation_result_selector
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_acquisition import ORIGIN
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_preparation_acquisition import capture_local_bundle, is_native_hmmer_preparation_target, original_source_payload, publish_original_source
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_preparation_result_publication import prepare_native_hmmer_preparation_grading, publish_selected_preparation_result, validate_prepared_grading, validate_publication
from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_preparation_failure_views import preparation_failure_facts
from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_preparation_result_worker import exception_code, exception_diagnostic, unique_failures, validate_failures
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_preparation_result_records import NativeHmmerPreparationResultRecords, PREFIX, VERSION, _complete, _require, _selector, _ungraded_native_failures, operation_catalog

class NativeHmmerPreparationResultAcquisition(NativeHmmerPreparationResultRecords):

    def _index(self, body):
        for reference in body['record_refs']:
            directory = self.directory / digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), {'run_id': body['run_id'], 'episode_id': body['episode_id'], 'operation_key': body['operation_key']})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner.native_hmmer_preparation_returns.authenticate(context)
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        _require(self.applies(context) and target == self.owner._target(context), 'original_target_conflict')
        _require(tool_name in {row['name'] for row in operation_catalog()} and arguments == {}, 'original_operation_conflict')
        selector = _selector(plain(context.assignment), target)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        intent = {'target': target, 'assignment': plain(context.assignment), 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'scope': plain(context.scope)}
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            _require(self.completion(context) is None, 'assignment_already_completed')
            if not (directory / 'observation.json').exists():
                observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory / 'observation.json', observation)
            observation = _read(directory / 'observation.json')
            body = {'version': VERSION, 'run_id': context.run_id, 'episode_id': context.episode_id, **intent, 'observation': observation, 'capture': None, 'prepared': None, 'source_ref': None, 'record_refs': [], 'rows': [], 'artifacts': [], 'population': None, 'failures': [], 'complete': False}
            diagnostics = []
            if tool_name == 'execution.results.collect':
                capture = capture_local_bundle(self.store, target=target, directory=directory / 'capture')
                body['capture'] = capture
                body['failures'].extend(capture['failures'])
                if capture['bundle_validated']:
                    bundle = json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                    policy = self._policy(target)
                    try:
                        prepared = prepare_native_hmmer_preparation_grading(self.store, target=target, capture=capture, capture_directory=directory / 'capture', directory=directory / 'grading', policy=policy)
                    except (ValueError, OSError) as error:
                        prepared = None
                        problem = {'stage': 'grading', 'code': exception_code(error, 'native_hmmer_preparation_retained_grading_unavailable'), 'record_key': None}
                        body['failures'].append(problem)
                        diagnostics.append({'failure': problem, **exception_diagnostic(error)})
                    body['prepared'] = prepared
                    if prepared is None:
                        body['failures'] = [*capture['failures'], *_ungraded_native_failures(body, bundle), *body['failures']]
                    source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                    body['source_ref'], body['record_refs'] = (source, [source])
                    if prepared is not None:
                        body['failures'].extend(prepared['failures'])
                    if prepared is not None:
                        try:
                            publication = publish_selected_preparation_result(self.store, source_ref=source, prepared=prepared, selector=selector, directory=directory / 'projection', policy=policy)
                        except (ValueError, OSError) as error:
                            problem = {'stage': 'projection', 'code': exception_code(error, 'native_hmmer_preparation_retained_projection_unavailable'), 'record_key': None}
                            body['failures'].append(problem)
                            diagnostics.append({'failure': problem, **exception_diagnostic(error)})
                        else:
                            _immutable(directory / 'publication.json', publication)
                            body.update({key: publication[key] for key in ('record_refs', 'rows', 'artifacts', 'population')})
                            body['failures'].extend(publication['failures'])
                    body['complete'] = _complete(body, bundle)
            body['failures'] = unique_failures(body['failures'])
            if diagnostics:
                _immutable(directory / 'operational-diagnostics.json', diagnostics)
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}
