"""Private native result acquisition; original action and returned outcome preserved."""
from __future__ import annotations
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a104.form_reference_validation import _binding_key, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_acquisition import capture_standard_blast_database_bundle, is_standard_blast_database_target, _source_payload, _validate_capture
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import prepare_standard_blast_database_grading, publish_selected_standard_blast_database_rows, validate_standard_blast_database_publication, _failure, _json, _json_artifact, _local_job_failure, _exception_diagnostic
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_views import standard_blast_database_fact_sources, validate_standard_blast_database_selector
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_standard_database_result_records import ACQUISITION_SOURCE, FAILURE_SOURCE, IDENTIFIER_NAMESPACES, REFERENCE_SOURCE, StandardBLASTDatabaseResultRecords, VERSION, empty_facts, operation_catalog, schema_references

class StandardBLASTDatabaseResultAcquisition(StandardBLASTDatabaseResultRecords):

    def _index(self, body):
        for ref in body['record_refs']:
            directory = self.directory / digest(ref)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), {key: body[key] for key in ('run_id', 'episode_id', 'operation_key')})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.original_records.authenticate(context)
        if not self.applies(context) or target != self.owner._target(context):
            raise ContractError('native_blast_standard_database_original_results_owner_required')
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        if arguments != {} or tool_name not in {r['name'] for r in operation_catalog()}:
            raise ContractError('native_blast_standard_database_result_operation_invalid')
        selector = self.owner._selector(plain(context.assignment), target)
        directory = self._action_directory(context, operation_key)
        intent = dict(target=target, assignment=plain(context.assignment), scope=plain(context.scope), operation_key=operation_key, tool_name=tool_name, arguments=arguments)
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            if self.completion(context) is not None:
                raise ContractError('execution_results_assignment_already_completed')
            if not (directory / 'observation.json').exists():
                _immutable(directory / 'observation.json', self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key))
            body = dict(version=VERSION, run_id=context.run_id, episode_id=context.episode_id, **intent, observation=_read(directory / 'observation.json'), capture=None, preparation=None, publication=None, record_refs=[], failures=[], diagnostic_artifact_refs=[], complete=False)
            if tool_name == 'execution.results.collect':
                capture = capture_standard_blast_database_bundle(self.store, target=target, reader=self.owner.job_progress_provider.targets, operation_key=operation_key, directory=directory / 'capture')
                body['capture'] = capture
                if capture['status'] in {'complete', 'partial'}:
                    bundle = _json(self.store, capture['bundle_artifact_ref'])
                    source = self.store.put('source', _source_payload(bundle, capture), origin='tool')['id']
                    body['record_refs'] = [source]
                    try:
                        prepared = prepare_standard_blast_database_grading(self.store, context=context, target=target, capture=capture, selector=selector, directory=directory / 'grading', policy=LocalJobPolicy(ENVIRONMENT_BOUNDS['memory_bytes'], 4 * 1024 ** 3))
                        body['preparation'] = prepared
                        publication = publish_selected_standard_blast_database_rows(self.store, context=context, preparation=prepared, selector=selector, directory=directory / 'publication')
                        body.update(publication=publication, record_refs=publication['record_refs'], failures=publication['failures'], complete=publication['complete'])
                    except (AcquisitionError, ValueError, KeyError, TypeError, OSError) as error:
                        invalid_contract = str(error) == 'native_blast_standard_database_calculator_contract_invalid'
                        failure = _local_job_failure(error) if isinstance(error, AcquisitionError) else _failure('calculation' if invalid_contract else 'worker', 'native_blast_standard_database_calculation_failed' if invalid_contract else 'native_blast_standard_database_worker_failed', 'calculator_contract_invalid' if invalid_contract else 'implementation_failure')
                        body['failures'].append(failure)
                        body['diagnostic_artifact_refs'].append(_json_artifact(self.store, {'schema': 'native_blast_standard_database_diagnostics_v1', 'failures': [failure], 'metadata_issues': [], 'errors': [_exception_diagnostic(error)]}))
                        for name in ('invalid-request.json', 'invalid-request-diagnostics.json', 'implementation-receipt.json'):
                            path = directory / 'grading' / name
                            if path.exists():
                                from gene_annotation_episode.episodic_workflow.root.a104.materials import artifact_file
                                body['diagnostic_artifact_refs'].append(artifact_file(self.store, path, 'application/json'))
                else:
                    body['failures'] = [_failure('capture', 'native_blast_standard_database_capture_incomplete', 'attempt_identity_conflict' if row['code'] == 'attempt_mismatch' else 'artifact_bytes_unavailable', artifact_key=row['artifact_key'], pointer='/capture/failures/' + str(i)) for i, row in enumerate(capture['failures'])]
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}
