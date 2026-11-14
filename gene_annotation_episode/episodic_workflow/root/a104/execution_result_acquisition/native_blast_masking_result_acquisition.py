"""Private native result acquisition; original action and returned outcome preserved."""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a104.form_reference_validation import _binding_key, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_masking_acquisition import capture_local_bundle, is_native_blast_masking_target, original_source_payload, publish_original_source
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_masking_contracts import BUNDLE_VERSION, generated_statistics_binding, validate_native_blast_masking_job, validate_native_blast_masking_requested_job
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_masking_result_publication import prepare_native_blast_masking_result, publish_selected_masking_result, validate_masking_publication, validate_prepared_masking_result
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_contracts import validate_sequence_masking_record
from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import FACT_SOURCES, IDENTIFIER_NAMESPACES, validate_masking_result_selector
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_masking_result_records import NativeBLASTMaskingResultRecords, VERSION, _ARRAY_FIELDS, _PROJECTION_FIELDS, _complete, _require, _selector, _virtual_references, operation_catalog

def _failure(code):
    return {'stage': 'calculation', 'code': code, 'occurrence_id': None, 'record_key': None, 'line_number': None}

class NativeBLASTMaskingResultAcquisition(NativeBLASTMaskingResultRecords):

    def _index(self, body):
        row = {key: body[key] for key in ('run_id', 'episode_id', 'operation_key')}
        for reference in dict.fromkeys([*body['record_refs'], *_virtual_references(body)]):
            directory = self.directory / digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), row)
        if body['source_ref'] is not None:
            directory = self.target_directory / digest(body['target'])
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), row)

    def _prior(self, target, scope):
        directory = self.target_directory / digest(target)
        fallback = None
        for path in sorted(directory.glob('*.json')) if directory.exists() else ():
            body = self._receipt(_read(path), scope)
            _require(body['target'] == target, 'target_index_conflict')
            if body['prepared'] is not None:
                return body
            fallback = body
        return fallback

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner.native_blast_masking_returns.authenticate(context)
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
            prior = self._prior(target, context.scope) if tool_name == 'execution.results.collect' or selector['mode'] == 'saved_recalculation' else None
            if selector['mode'] == 'saved_recalculation':
                _require(prior is not None and selector['saved_sheet_ref'] == prior['prepared']['sheet_artifact_ref'], 'received_original_sheet_required')
                _require(selector['saved_sheet_ref'] in self._known(context) and self._explicit_grant(context, selector['saved_sheet_ref']), 'saved_sheet_not_received')
            if not (directory / 'observation.json').exists():
                observation = prior['observation'] if prior is not None else self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory / 'observation.json', observation)
            body = {'version': VERSION, 'run_id': context.run_id, 'episode_id': context.episode_id, **intent, 'observation': _read(directory / 'observation.json'), 'capture': None, 'prepared': None, 'source_ref': None, 'reused_from': None, 'operational_failures': [], 'complete': False, 'status': None, 'record_refs': [], **{key: [] for key in _ARRAY_FIELDS}}
            diagnostics = []
            if tool_name == 'execution.results.collect':
                if prior is not None:
                    body['reused_from'] = prior['reused_from'] or {key: prior[key] for key in ('run_id', 'episode_id', 'operation_key')}
                    capture, prepared = (prior['capture'], prior['prepared'])
                else:
                    capture = capture_local_bundle(self.store, target=target, directory=directory / 'capture')
                    prepared = None
                body['capture'] = capture
                if capture['bundle_validated']:
                    bundle = json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                    policy = self._policy(target)
                    stage = 'prepare'
                    try:
                        if prepared is None:
                            prepared = prepare_native_blast_masking_result(self.store, bundle=bundle, bundle_artifact_ref=capture['bundle_artifact_ref'], artifacts=capture['artifacts'], capture=capture, directory=directory / 'prepared', policy=policy)
                        body['prepared'] = prepared
                        source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                        body['source_ref'], body['record_refs'] = (source, [source])
                        stage = 'projection'
                        publication = publish_selected_masking_result(self.store, source_ref=source, prepared=prepared, selector=selector, directory=directory / 'projection', policy=policy)
                        _immutable(directory / 'publication.json', publication)
                        body.update({key: publication[key] for key in _PROJECTION_FIELDS})
                    except (ValueError, OSError) as error:
                        failure = _failure('retained_' + stage + '_unavailable')
                        body['operational_failures'].append(failure)
                        diagnostics.append({'failure': failure, 'exception_type': type(error).__name__, 'detail': str(error)})
                        if body['source_ref'] is None:
                            source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=body['prepared'])
                            body['source_ref'], body['record_refs'] = (source, [source])
                        body['failures'] = [{'source_ref': body['source_ref'], **failure}]
            body['complete'] = _complete(body)
            if diagnostics:
                _immutable(directory / 'operational-diagnostics.json', diagnostics)
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}
