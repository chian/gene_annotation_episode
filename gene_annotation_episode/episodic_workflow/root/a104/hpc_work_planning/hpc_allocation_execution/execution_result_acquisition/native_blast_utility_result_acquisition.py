"""Private native result acquisition; original action and returned outcome preserved."""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, obj
from gene_annotation_episode.episodic_workflow.root.a104.form_reference_validation import _binding_key, form_reference_validation, form_validation_value
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_utility_acquisition import capture_local_utility_bundle, is_native_blast_utility_target, _source_payload, _validate_saved
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_utility_contracts import BUNDLE_VERSION, validate_native_blast_utility_requested_job
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_result_publication import prepare_native_blast_utility_result, publish_selected_utility_result, validate_utility_publication, validate_prepared_utility_result
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_capture_failure import FILENAME as CAPTURE_FAILURE_PUBLICATION, QUALIFICATION_FAILURE, publish_capture_failure, validate_capture_failure
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import FACT_SOURCES, IDENTIFIER_NAMESPACES, PROJECTION_FIELDS, PROJECTION_V2_FIELDS, blast_utility_projection_fields, projection_identifiers, validate_blast_utility_result_selector
from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_result_records import NativeBLASTUtilityResultRecords, V2_VERSION, VERSION, _ARRAY_FIELDS, _PROJECTION_FIELDS, _SELECTOR_VERSIONS, _array_fields, _body_projection_fields, _body_version, _complete, _current_bodies, _has_parsed_result, _require, _selector, _virtual_references, operation_catalog

def _failure(stage):
    return {'stage': 'parse' if stage == 'prepare' else 'projection', 'code': 'semantic_validation_unavailable', 'occurrence_id': None, 'record_key': None, 'line_number': None, 'native_returncode': None}

class NativeBLASTUtilityResultAcquisition(NativeBLASTUtilityResultRecords):

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
            if _has_parsed_result(body['prepared']):
                return body
            fallback = body
        return fallback

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner.native_blast_utility_returns.authenticate(context)
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        _require(self.applies(context) and target == self.owner._target(context), 'original_target_conflict')
        _require(tool_name in {row['name'] for row in operation_catalog()} and arguments == {}, 'original_operation_conflict')
        selector = _selector(plain(context.assignment), target)
        projection_fields = blast_utility_projection_fields(selector)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        intent = {'target': target, 'assignment': plain(context.assignment), 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'scope': plain(context.scope)}
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            _require(self.completion(context) is None, 'assignment_already_completed')
            prior = self._prior(target, context.scope) if tool_name == 'execution.results.collect' else None
            if not (directory / 'observation.json').exists():
                observation = prior['observation'] if prior is not None else self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory / 'observation.json', observation)
            body = {'version': _body_version(selector), 'run_id': context.run_id, 'episode_id': context.episode_id, **intent, 'observation': _read(directory / 'observation.json'), 'capture': None, 'prepared': None, 'source_ref': None, 'reused_from': None, 'operational_failures': [], 'complete': False, 'status': None, 'record_refs': [], **{key: [] for key in _array_fields(projection_fields)}}
            diagnostics = []
            if tool_name == 'execution.results.collect':
                if prior is not None:
                    body['reused_from'] = prior['reused_from'] or {key: prior[key] for key in ('run_id', 'episode_id', 'operation_key')}
                    capture, prepared = (prior['capture'], prior['prepared'])
                else:
                    capture = capture_local_utility_bundle(self.store, target=target, directory=directory / 'capture')
                    prepared = None
                body['capture'] = capture
                if capture['bundle_validated']:
                    source = capture['source_ref']
                    body['source_ref'], body['record_refs'] = (source, [source])
                    policy = self._policy(target)
                    stage = 'prepare'
                    try:
                        if not _has_parsed_result(prepared):
                            prepared = prepare_native_blast_utility_result(self.store, capture=capture, directory=directory / 'prepared', policy=policy)
                        body['prepared'] = prepared
                        stage = 'projection'
                        publication = publish_selected_utility_result(self.store, source_ref=source, prepared=prepared, selector=selector, directory=directory / 'projection', policy=policy)
                        _immutable(directory / 'publication.json', publication)
                        body.update({key: publication[key] for key in projection_fields})
                    except (ValueError, OSError) as error:
                        failure = _failure(stage)
                        body['operational_failures'].append(failure)
                        diagnostics.append({'failure': failure, 'exception_type': type(error).__name__, 'detail': str(error)})
                        body['failures'] = [{'source_ref': body['source_ref'], **failure}]
                        if stage == 'prepare' and prepared is None and isinstance(error, ContractError) and (str(error) == QUALIFICATION_FAILURE) and (body['version'] == V2_VERSION):
                            try:
                                failed = publish_capture_failure(self.store, capture=capture, selector=selector, operational_failures=body['operational_failures'], directory=directory)
                                body.update({key: failed['projection'][key] for key in projection_fields})
                            except (ValueError, OSError) as projection_error:
                                extra = _failure('projection')
                                body['operational_failures'].append(extra)
                                diagnostics.append({'failure': extra, 'exception_type': type(projection_error).__name__, 'detail': str(projection_error)})
                                body['failures'].append({'source_ref': body['source_ref'], **extra})
            body['complete'] = _complete(body)
            if diagnostics:
                _immutable(directory / 'operational-diagnostics.json', diagnostics)
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}
