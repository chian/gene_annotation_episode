"""Original selected API operation recovery, execution and publication bodies.

The real owning host supplies its authenticated context, providers and custody.
This partition does not construct a provider or establish a fresh producer route.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_error_feedback import api_error_feedback, api_error_response
from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.immutable_json_records import _immutable, _read


PROVIDER = 'episode.api_service_handoff'
HANDOFF_VERSION = 'api_service_handoff_v1'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _outcome(key, result=None, *, refs=(), status='completed', code=None, **feedback):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}),
        'record_refs': list(refs), 'changed_record_refs': list(refs), 'result': result,
        'feedback': None if code is None else {'category': 'provider', 'code': code, **feedback}}


class APIServiceOperations:
    async def execute(self, context, name, arguments, operation_key):
        if self._legacy_context(context):
            return await self._legacy_binding().execute(context, name, arguments, operation_key)
        try:
            arguments = plain(arguments)
            self.initialize(context)
            assignment, service, target = self._context(context)
            entry = next((row for row in self.catalog(context) if row['name'] == name), None)
            if entry is None:
                raise ValueError('api_operation_not_available')
            validate_schema(arguments, entry['input_schema'])
            self._selected(context, name, arguments, operation_key)
        except (ValueError, ContractError, KeyError, TypeError) as error:
            return _outcome(operation_key, status='invalid', code=str(error),
                **api_error_feedback(error))
        directory = self._manifest(context)/'actions'/digest(operation_key)
        directory.mkdir(exist_ok=True)
        # Acquire outside the event loop: a concurrent recovery must not block
        # the coroutine that owns the selected request and will release the lock.
        with (directory/'.lock').open('a') as lock:
            await asyncio.to_thread(fcntl.flock, lock, fcntl.LOCK_EX)
            try:
                return await self._execute_locked(context, assignment, service, target,
                    name, arguments, operation_key, directory)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    async def _execute_locked(self, context, assignment, service, target, name, arguments, key, directory):
        if service.service == 'bvbrc_appservice':
            return await self.appservice.execute_locked(context, assignment, service, target,
                name, arguments, key, directory)
        intent_path, snapshot_path = directory/'intent.json', directory/'snapshot.json'
        event_path, outcome_path = directory/'event.json', directory/'outcome.json'
        original = {'run_id': self.run_id, 'episode_id': context.episode_id, 'name': name,
            'arguments': arguments, 'assignment_sha256': digest(context.assignment), 'operation_key': key}
        if intent_path.exists():
            intent = _read(intent_path)
            if any(intent.get(field) != value for field, value in original.items()):
                return _outcome(key, status='invalid', code='api_operation_key_reused_for_different_work')
            if outcome_path.exists():
                outcome = _read(outcome_path)
                if context.role == 'results':
                    self._index_result(context, directory, outcome)
                return outcome
            fresh = False
        else:
            try:
                if self._completion(context) is not None:
                    raise ValueError('api_assignment_already_completed')
                from .bvbrc_data_host import is_bvbrc_request
                if target is not None and service.service == 'bvbrc_data' and is_bvbrc_request(assignment['request']):
                    self.bvbrc_data.validate_inputs(context, plain(context.assignment)['selector'],
                        request=assignment['request'])
                if target is not None and service.service == 'bvbrc_minhash':
                    self.minhash.validate_inputs(context, plain(context.assignment)['selector'],
                        request=assignment['request'], handoff_ref=target['handle'])
                previous = self._events(context.episode_id)
                handle = None if target is None else self._native_handle(target)
                prepared = service.prepare(name, assignment['request'], arguments,
                    scope=plain(context.scope), previous_events=previous, handle=handle,
                    selector=None if target is None else plain(context.assignment)['selector'])
                canonical(prepared)
                if not isinstance(prepared, dict) or prepared.get('operation') != name:
                    raise ValueError('api_service_prepared_operation_conflict')
                if prepared.get('mutates_remote'):
                    for old in self._action_paths(context.episode_id):
                        if _read(old)['prepared'].get('mutates_remote'):
                            prior_path = old.parent/'outcome.json'
                            prior = _read(prior_path) if prior_path.exists() else {}
                            not_sent = ((prior.get('feedback') or {}).get('submission_outcome') == 'not_sent')
                            if not not_sent:
                                raise ValueError('api_original_submission_already_exists')
                intent = {**original, 'prepared': prepared, 'started_at': _now()}
                _immutable(intent_path, intent)
                fresh = True
            except (ValueError, ContractError, AcquisitionError, KeyError, TypeError) as error:
                return _outcome(key, status='invalid', code=getattr(error, 'code', str(error)),
                    retry_after=getattr(error, 'retry_after', None),
                    **api_error_feedback(error))
        prepared = intent['prepared']
        snapshot = None
        try:
            if snapshot_path.exists():
                snapshot = self._load_snapshot(_read(snapshot_path))
            elif prepared.get('cache_original'):
                if target is None:
                    raise ValueError('api_cached_result_requires_original_handoff')
                metadata = self._read_handoff(target['handle'], context.scope)['snapshot']
                snapshot = self._load_snapshot(metadata)
                _immutable(snapshot_path, metadata)
            elif service.service == 'enrichr':
                # Recovery resumes only unissued fixed protocol stages. The
                # host never repeats a stage whose response is uncertain.
                snapshot = await self.enrichr_protocol.acquire(
                    context, service, intent, directory)
                _immutable(snapshot_path, self._snapshot(snapshot))
            elif fresh:
                try:
                    snapshot = await asyncio.to_thread(service.invoke, prepared)
                except BaseException as error:
                    if getattr(error, 'snapshot', None) is not None:
                        _immutable(snapshot_path, self._snapshot(error.snapshot))
                    raise
                if snapshot is not None:
                    _immutable(snapshot_path, self._snapshot(snapshot))
            elif not event_path.exists():
                raise AcquisitionError('api_operation_response_unknown', phase='recovery',
                    submission_outcome='unknown' if prepared.get('mutates_remote') else None)
            if service.service == 'enrichr':
                if target is None:
                    self.enrichr_protocol.validate(context, service, intent, directory, snapshot)
                else:
                    self._validate_enrichr_result_snapshot(target, context.scope, snapshot)
            event = self._event(_read(event_path) if event_path.exists() else service.decode(prepared, snapshot))
            _immutable(event_path, event)
            acquired = context.role == 'results' and event['kind'] == 'response' and event['result_available']
            if acquired:
                if snapshot is None:
                    raise ValueError('api_result_response_required')
                publication = {}
                from .bvbrc_data_host import is_bvbrc_request
                if service.service == 'bvbrc_data' and is_bvbrc_request(assignment['request']):
                    inputs_path = directory/'publication_inputs.json'
                    inputs = self.bvbrc_data.publication_inputs(context, prepared['prepared_query'])
                    _immutable(inputs_path, inputs)
                    publication['publication_inputs'] = _read(inputs_path)
                if service.service == 'bvbrc_minhash' and plain(context.assignment)['selector']:
                    from gene_annotation_episode.episodic_workflow.root.library.bvbrc_minhash_contracts import validate_minhash_publication_inputs
                    inputs_path = directory/'publication_inputs.json'
                    if not inputs_path.exists():
                        if (directory/'publication.json').exists():
                            raise ValueError('minhash_publication_inputs_conflict')
                        inputs = self.minhash.publication_inputs(context,
                            request=assignment['request'], selector=plain(context.assignment)['selector'],
                            handoff_ref=target['handle'])
                        _immutable(inputs_path, inputs)
                    # Recovery uses the original snapshot before any input extraction.
                    publication['publication_inputs'] = validate_minhash_publication_inputs(
                        _read(inputs_path), request=assignment['request'],
                        selector=plain(context.assignment)['selector'])
                published_path = directory/'publication.json'
                if publication and published_path.exists():
                    outcome = _read(published_path)
                else:
                    outcome = service.publish(assignment['request'], plain(context.assignment)['selector'],
                        snapshot, plain(context.scope), key+':publication',
                        submission_snapshot=self._submission_snapshot(target), handle=self._native_handle(target),
                        **publication)
                    if publication:
                        _immutable(published_path, json.loads(canonical(outcome)))
                outcome = json.loads(canonical(outcome))
                outcome['operation_ref'] = identity('api_operation', {'key': key})
                result = outcome.setdefault('result', {})
                if result is None:
                    result = outcome['result'] = {}
                receipt = {**original, 'version': 'api_service_acquisition_v1',
                    'handoff_ref': target['handle'], 'selector': plain(context.assignment)['selector'],
                    'snapshot_sha256': snapshot.sha256, 'record_refs': list(outcome.get('record_refs', [])),
                    'source_ref': result.get('source_ref'), 'finished_at': _now()}
                if publication:
                    if service.service == 'bvbrc_minhash':
                        receipt['publication_inputs_sha256'] = digest(publication['publication_inputs'])
                    else:
                        from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_schema import json_digest
                        receipt['publication_inputs_sha256'] = json_digest(publication['publication_inputs'])
                if (directory/'acquisition.json').exists():
                    saved = _read(directory/'acquisition.json')
                    if any(saved.get(field) != value for field, value in receipt.items() if field != 'finished_at'):
                        raise ValueError('api_acquisition_recovery_conflict')
                    receipt = saved
                result['acquisition_receipt'] = receipt
                result['handoff_ref'] = target['handle']
                _immutable(directory/'acquisition.json', receipt)
            else:
                outcome = _outcome(key, result={'service': service.service, 'event': event})
                if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
                    outcome['result']['error_response'] = api_error_response(snapshot)
                if context.role == 'launch_api' and event['handoff_ready']:
                    if snapshot is None:
                        raise ValueError('api_handoff_requires_actual_response')
                    receipt = {**original, 'version': 'api_service_receipt_v1',
                        'tool_name': name, 'state': event['state'], 'native_kind': event['kind'],
                        'snapshot_sha256': snapshot.sha256, 'finished_at': _now()}
                    if (directory/'handoff_receipt.json').exists():
                        saved = _read(directory/'handoff_receipt.json')
                        if any(saved.get(field) != value for field, value in receipt.items() if field != 'finished_at'):
                            raise ValueError('api_handoff_recovery_conflict')
                        receipt = saved
                    _immutable(directory/'handoff_receipt.json', receipt)
                    reference = self._publish_handoff(context, event, _read(snapshot_path), receipt)
                    outcome['record_refs'] = outcome['changed_record_refs'] = [reference]
                    outcome['result'].update(handoff_ref=reference, receipt=receipt)
            if acquired:
                self._index_result(context, directory, outcome)
            _immutable(outcome_path, outcome)
            return outcome
        except BaseException as error:
            interruption = isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit))
            feedback = {**api_error_feedback(error, snapshot=snapshot),
                'phase': getattr(error, 'phase', None),
                'retry_after': getattr(error, 'retry_after', None),
                'submission_outcome': getattr(error, 'submission_outcome', None)}
            if service.service == 'enrichr':
                diagnostic = getattr(error, 'diagnostic', None)
                if isinstance(diagnostic, dict) and set(diagnostic) == {
                        'stage_ordinal', 'stage_code', 'captured_prefix_count',
                        'http_status', 'response_retained', 'all_stage_responses_captured'}:
                    feedback['protocol'] = deepcopy(diagnostic)
            if service.service == 'rfam_batch':
                diagnostic = getattr(error, 'diagnostic', None)
                if diagnostic is not None:
                    feedback['diagnostic_ref'] = self.store.artifact(canonical({
                        'transport_phase': feedback['phase'], 'diagnostic': diagnostic}), 'application/json')
                feedback['phase'] = {'local_preflight': 'preflight',
                    'connect': 'submission' if prepared.get('mutates_remote') else 'response',
                    'http_request': 'submission' if prepared.get('mutates_remote') else 'response',
                    'http_response_headers': 'response', 'transport': 'response',
                    'recovery': 'recovery'}.get(feedback['phase'], feedback['phase'])
            if snapshot_path.exists():
                feedback['response_retained'] = True
            outcome = _outcome(key, status='failed', code=getattr(error, 'code',
                str(error) if isinstance(error, (ValueError, ContractError)) else 'api_service_operation_failed'),
                **feedback)
            # Interruption retains the intent/response for original-action
            # recovery rather than freezing cancellation as the action outcome.
            if not interruption:
                _immutable(outcome_path, outcome)
            if interruption:
                raise
            return outcome

    def _publish_handoff(self, context, event, snapshot, receipt):
        body = {'version': HANDOFF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'assignment': plain(context.assignment), 'assignment_sha256': digest(context.assignment),
            'scope': plain(context.scope), 'event': event, 'snapshot': snapshot, 'receipt': receipt}
        return self._handoff_source(body)

    def _handoff_source(self, body):
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': PROVIDER, 'accession': 'api_handoff_'+digest([
            self.run_id, body['episode_id'], body['receipt']['operation_key']]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': artifact,
            'version': HANDOFF_VERSION, 'retrieved_at': body['receipt']['finished_at']}
        return self.store.put('source', payload, origin='tool')['id']

