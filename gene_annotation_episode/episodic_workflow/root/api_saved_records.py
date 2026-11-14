"""Original authenticated saved API handoffs, response captures and acquisitions.

No constructor, provider selection or new publication authority is supplied here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json

from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import validate_target
from .api_hmmer_protocol import PROVIDER as LEGACY_PROVIDER
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.immutable_json_records import _read
from .api_service_operations import PROVIDER, HANDOFF_VERSION


class APISavedRecords:
    def is_handoff_source(self, reference):
        try:
            from .bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
            if self.store.get(reference).get('provider') == APPSERVICE_PROVIDER:
                self.appservice.read_handoff(reference)
                return True
            return self.store.get(reference).get('provider') in {PROVIDER, LEGACY_PROVIDER}
        except (ValueError, KeyError, OSError, TypeError):
            return False

    def _native_handle(self, target):
        return self._read_handoff(target['handle'], target['scope'])['event']['native_handle']

    def _submission_snapshot(self, target):
        if target['assignment'].get('service') == 'bvbrc_appservice':
            body = self.appservice.read_handoff(target['handle'], target['scope'])
            return self._load_snapshot(body['snapshot'])
        for path in self._action_paths(target['origin_episode_id']):
            intent = _read(path)
            snapshot = path.parent/'snapshot.json'
            if intent['prepared'].get('mutates_remote') and snapshot.exists():
                return self._load_snapshot(_read(snapshot))
        return None

    def closed_enrichr_target(self, context):
        """Recover an actual closed Results target from its original proof."""
        if context.role != 'results' or not any(
                service.service == 'enrichr' for service in self.services.values()):
            return None
        from gene_annotation_episode.enrichr_returns import OWN_WITNESSES
        from gene_annotation_episode.episodic_workflow.root.episode_return_records import _same
        owner = self.enrichr_returns
        closed = owner._closed(context)
        if closed is None or OWN_WITNESSES not in closed['facts']:
            return None
        owner.authenticate(context)
        if not _same(owner.context(context.episode_id).as_record(), context.as_record()):
            raise ValueError('enrichr_original_context_conflict')
        if not owner._successful_closed(context):
            return None
        witnesses = owner._own_witnesses(context)
        if not witnesses:
            return None
        # All publications belong to the fixed original Results assignment.
        # An original stored pointer recovers that target; it selects no work.
        original = witnesses[0]
        body = self.read_result(original['source_ref'], context.scope,
            episode_id=context.episode_id, operation_key=original['operation_key'],
            verify_artifacts=False)
        return body['target']

    def _enrichr_history_witness(self, handoff_ref, scope, caller):
        """Recheck saved caller identities; the tuple itself grants nothing."""
        if (type(caller) is not tuple or len(caller) != 3
                or any(type(value) is not str for value in caller)):
            raise ValueError('enrichr_original_context_conflict')
        episode_id, operation_key, source_ref = caller
        context = self.enrichr_returns.context(episode_id)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        if context.role != 'results' or context.assignment.get('handoff_ref') != handoff_ref:
            raise ValueError('enrichr_original_context_conflict')
        return self.enrichr_returns.historical_result_witness(
            source_ref, context=context, operation_key=operation_key)

    def _validate_enrichr_result_snapshot(self, target, scope, snapshot):
        """A local window must use the authenticated original query capture."""
        body = self._read_handoff(target['handle'], scope)
        original = self._load_snapshot(body['snapshot'])
        actual_fields, original_fields = asdict(snapshot), asdict(original)
        actual_content = actual_fields.pop('content')
        original_content = original_fields.pop('content')
        if (type(actual_content) is not bytes or actual_content != original_content
                or canonical(actual_fields) != canonical(original_fields)):
            raise ValueError('enrichr_original_result_snapshot_conflict')

    def _original_context(self, manifest):
        from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
        return BindingContext(self.run_id, manifest['episode_id'], manifest['role'],
            ((manifest['role'], 'original'),), manifest['scope'], manifest['assignment'], {})

    def _read_handoff(self, reference, scope, *, verify_artifacts=True, _enrichr_history=None):
        source = self.store.get(reference)
        if _enrichr_history is not None and source.get('provider') != PROVIDER:
            raise ValueError('enrichr_original_context_conflict')
        from .bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if source.get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_handoff(reference, scope)
        if source.get('provider') != PROVIDER or source.get('record_type') != 'source' or source.get('origin') != 'tool':
            raise ValueError('not_an_api_service_handoff')
        body = self._artifact_json(source['artifact_ref'])
        if (set(body) != {'version', 'run_id', 'episode_id', 'assignment', 'assignment_sha256',
                         'scope', 'event', 'snapshot', 'receipt'}
                or body.get('version') != HANDOFF_VERSION or body.get('run_id') != self.run_id):
            raise ValueError('api_service_handoff_identity_conflict')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        assignment = self.validate_assignment(body['assignment'], scope=body['scope'])
        if body['assignment_sha256'] != digest(assignment):
            raise ValueError('api_service_handoff_assignment_conflict')
        manifest = _read(self._episode_directory(body['episode_id'])/'assignment.json')
        if (manifest['role'] != 'launch_api' or manifest['assignment'] != assignment
                or manifest['scope'] != body['scope']):
            raise ValueError('api_service_original_assignment_conflict')
        receipt = body['receipt']
        context = self._original_context(manifest)
        directory = self._manifest(context, create=False)/'actions'/digest(receipt['operation_key'])
        intent = _read(directory/'intent.json')
        if _read(directory/'handoff_receipt.json') != receipt:
            raise ValueError('api_service_original_handoff_receipt_conflict')
        event = self._event(_read(directory/'event.json'))
        metadata = _read(directory/'snapshot.json')
        historical_uniprot = not verify_artifacts and assignment.get('service') == 'uniprot'
        historical_enrichr = None
        if _enrichr_history is not None:
            if verify_artifacts or assignment.get('service') != 'enrichr':
                raise ValueError('enrichr_original_context_conflict')
            historical_enrichr = self._enrichr_history_witness(reference, scope, _enrichr_history)
            if (digest(metadata) != historical_enrichr['snapshot_metadata_sha256']
                    or metadata.get('content_ref') != historical_enrichr['native_artifact_ref']
                    or historical_enrichr['snapshot_sha256'] != receipt['snapshot_sha256']):
                raise ValueError('enrichr_source_snapshot_conflict')
        if historical_uniprot:
            # Retain the metadata relationship without manufacturing a snapshot
            # containing substitute bytes. Other services keep full verification.
            if metadata.get('content_ref') != 'artifact_' + receipt['snapshot_sha256']:
                raise ValueError('uniprot_source_snapshot_conflict')
            snapshot_sha256 = receipt['snapshot_sha256']
        elif historical_enrichr is not None:
            snapshot_sha256 = historical_enrichr['snapshot_sha256']
        else:
            snapshot_sha256 = self._load_snapshot(metadata).sha256
        if (event != body['event'] or not event['handoff_ready'] or metadata != body['snapshot']
                or receipt['run_id'] != self.run_id or receipt['episode_id'] != body['episode_id']
                or receipt['assignment_sha256'] != digest(assignment)
                or receipt['name'] != intent['name'] or receipt['tool_name'] != intent['name']
                or receipt['arguments'] != intent['arguments'] or receipt['state'] != event['state']
                or receipt['snapshot_sha256'] != snapshot_sha256):
            raise ValueError('api_service_handoff_receipt_conflict')
        selected = self._selected(context, intent['name'], intent['arguments'], receipt['operation_key'])
        if (directory/'outcome.json').exists():
            outcome = _read(directory/'outcome.json')
            if (outcome.get('status') != 'completed' or reference not in outcome.get('record_refs', [])
                    or outcome.get('result', {}).get('receipt') != receipt):
                raise ValueError('api_service_handoff_outcome_conflict')
        if selected['result'] is not None and reference not in json.loads(selected['result']).get('record_refs', []):
            raise ValueError('api_service_handoff_runtime_outcome_conflict')
        expected = {'provider': PROVIDER, 'accession': 'api_handoff_'+digest([
            self.run_id, body['episode_id'], receipt['operation_key']]), 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'],
            'request_ref': source['artifact_ref'], 'version': HANDOFF_VERSION,
            'retrieved_at': receipt['finished_at']}
        if ({key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != expected
                or reference != identity('source', {'origin': 'tool', 'record': expected})):
            raise ValueError('api_service_handoff_source_conflict')
        if assignment.get('service') == 'enrichr':
            if historical_enrichr is None:
                self.enrichr_protocol.validate(context, self.services[assignment['resource_id']],
                    intent, directory, self._load_snapshot(metadata))
            else:
                self.enrichr_protocol.validate_closed_metadata(context,
                    self.services[assignment['resource_id']], intent, directory, metadata,
                    protocol_artifacts=historical_enrichr['protocol_artifacts'])
        return body

    def scope(self, handoff_ref):
        from .bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_handoff(handoff_ref)['scope']
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().scope(handoff_ref)
        body = self._artifact_json(self.store.get(handoff_ref)['artifact_ref'])
        return self._read_handoff(handoff_ref, body['scope'])['scope']

    def read_target(self, handoff_ref, scope, *, verify_artifacts=True, _enrichr_history=None,
                    _completed_appservice_download=False):
        from .bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
        if _enrichr_history is not None and self.store.get(handoff_ref).get('provider') != PROVIDER:
            raise ValueError('enrichr_original_context_conflict')
        if self.store.get(handoff_ref).get('provider') == APPSERVICE_PROVIDER:
            return self.appservice.read_target(handoff_ref, scope,
                **({'_completed_download': True} if _completed_appservice_download else {}))
        if _completed_appservice_download:
            raise ValueError('appservice_cached_download_context_conflict')
        if self.store.get(handoff_ref).get('provider') == LEGACY_PROVIDER:
            return self._legacy_binding().read_target(handoff_ref, scope)
        body = self._read_handoff(handoff_ref, scope,
            verify_artifacts=verify_artifacts, _enrichr_history=_enrichr_history)
        event = body['event']
        handle = event['native_handle'] or {}
        if event['kind'] == 'job':
            execution_id = next((handle[key] for key in ('id', 'rid', 'task_id', 'execution_id', 'job_id')
                if isinstance(handle.get(key), str) and handle[key]), None)
            if execution_id is None:
                raise ValueError('api_actual_native_job_identity_required')
        else:
            execution_id = 'request:'+body['receipt']['operation_key']
        return validate_target({'version': 'execution_target_v1', 'handle': handoff_ref,
            'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api',
            'execution_id': execution_id, 'request_sha256': digest(body['assignment']),
            'origin_episode_id': body['episode_id'], 'assignment': body['assignment'], 'scope': body['scope']})

    def read_result(self, reference, scope, *, episode_id=None, operation_key=None,
                    verify_artifacts=True):
        if self.appservice.publications.is_provider(self.store.get(reference).get('provider')):
            return self.appservice.publications.read(reference, scope, episode_id=episode_id)
        index = self.directory/'result-index'/digest(reference)
        if index.exists():
            for path in sorted(index.glob('*.json')):
                pointer = _read(path)
                if episode_id is not None and pointer['episode_id'] != episode_id:
                    continue
                if operation_key is not None and pointer['operation_key'] != operation_key:
                    continue
                manifest = _read(self._episode_directory(pointer['episode_id'])/'assignment.json')
                self.store.validate_scope(manifest['scope'], parent_scope=plain(scope))
                if manifest['role'] != 'results':
                    raise ValueError('api_result_original_role_conflict')
                context = self._original_context(manifest)
                enrichr_history = None
                if not verify_artifacts and self.store.get(reference).get('provider') == 'enrichr':
                    if type(verify_artifacts) is not bool:
                        raise ValueError('enrichr_original_context_conflict')
                    from gene_annotation_episode.episodic_workflow.root.episode_return_records import _same
                    owner = self.enrichr_returns.context(context.episode_id)
                    if (owner.role != context.role or not _same(owner.scope, context.scope)
                            or not _same(owner.assignment, context.assignment)):
                        raise ValueError('enrichr_original_context_conflict')
                    self.enrichr_returns.historical_result_witness(reference, context=owner,
                        operation_key=pointer['operation_key'])
                    enrichr_history = (context.episode_id, pointer['operation_key'], reference)
                assignment, _, target = self._context(context,
                    verify_artifacts=verify_artifacts, _enrichr_history=enrichr_history)
                directory = self._manifest(context, create=False)/'actions'/digest(pointer['operation_key'])
                intent, outcome = _read(directory/'intent.json'), _read(directory/'outcome.json')
                receipt = _read(directory/'acquisition.json')
                if outcome['status'] not in {'completed', 'partial'} or reference not in outcome['record_refs']:
                    continue
                metadata = _read(directory/'snapshot.json')
                uniprot = assignment.get('service') == 'uniprot'
                enrichr = assignment.get('service') == 'enrichr'
                exact_publication = uniprot or enrichr
                historical_uniprot = uniprot and not verify_artifacts
                historical_enrichr = enrichr and enrichr_history is not None
                if enrichr_history is not None and not enrichr:
                    raise ValueError('enrichr_original_context_conflict')
                if historical_uniprot:
                    from gene_annotation_episode.episodic_workflow.root.episode_return_records import _same
                    owner = self.uniprot_returns.context(context.episode_id)
                    if (owner.role != context.role or not _same(owner.scope, context.scope)
                            or not _same(owner.assignment, context.assignment)):
                        raise ValueError('uniprot_original_context_conflict')
                    if not self.uniprot_returns._successful_closed(owner):
                        raise ValueError('uniprot_frozen_prefix_conflict')
                historical = historical_uniprot or historical_enrichr
                snapshot = None if historical else self._load_snapshot(metadata)
                snapshot_sha256 = receipt['snapshot_sha256'] if historical else snapshot.sha256
                if enrichr and not historical_enrichr:
                    self._validate_enrichr_result_snapshot(target, context.scope, snapshot)
                if (receipt['record_refs'] != outcome['record_refs']
                        or receipt['handoff_ref'] != target['handle'] or receipt['selector'] != plain(context.assignment)['selector']
                        or receipt['assignment_sha256'] != digest(context.assignment)
                        or receipt['snapshot_sha256'] != snapshot_sha256
                        or receipt['source_ref'] != outcome['result'].get('source_ref')
                        or outcome['result'].get('acquisition_receipt') != receipt):
                    raise ValueError('api_result_acquisition_receipt_conflict')
                selected = self._selected(context, intent['name'], intent['arguments'], pointer['operation_key'])
                if exact_publication and (receipt.get('run_id') != self.run_id
                        or receipt.get('episode_id') != context.episode_id
                        or receipt.get('operation_key') != pointer['operation_key']
                        or intent.get('operation_key') != pointer['operation_key']
                        or intent.get('run_id') != self.run_id
                        or intent.get('episode_id') != context.episode_id
                        or intent.get('assignment_sha256') != digest(context.assignment)
                        or receipt.get('name') != intent['name']
                        or receipt.get('arguments') != intent['arguments']):
                    raise ValueError(assignment['service'] + '_original_receipt_conflict')
                if selected['result'] is not None:
                    actual = json.loads(selected['result'])
                    if actual.get('record_refs') != outcome['record_refs'] or actual.get('result') != outcome['result']:
                        raise ValueError('api_result_runtime_outcome_conflict')
                    if exact_publication:
                        from gene_annotation_episode.episodic_workflow.root.episode_return_records import _same
                        if enrichr and 'pending_work_after_action' in actual:
                            from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending
                            validate_pending(actual['pending_work_after_action'])
                        actual.pop('pending_work_after_action', None)
                        if not _same(actual, outcome):
                            raise ValueError(assignment['service'] + '_original_receipt_conflict')
                source = self.store.get(receipt['source_ref'])
                if exact_publication and (metadata.get('content_ref') != source.get('artifact_ref')
                        or source.get('artifact_ref') != 'artifact_' + receipt['snapshot_sha256']):
                    raise ValueError(assignment['service'] + '_source_snapshot_conflict')
                if not historical and self.store.get_artifact(source['artifact_ref']) != snapshot.content:
                    raise ValueError('api_result_original_response_conflict')
                return {'version': 'api_service_acquired_result_v1', 'reference': reference,
                    'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': manifest['scope'],
                    'assignment': plain(context.assignment), 'target': target, 'source_ref': receipt['source_ref'],
                    'record_refs': list(outcome['record_refs']), 'status': outcome['status'],
                    'snapshot_sha256': snapshot_sha256, 'service_request': assignment['request'],
                    **({'publication_result': deepcopy(outcome['result'])}
                       if assignment['service'] in {'rfam_batch', 'uniprot', 'sequence_support', 'enrichr'} else {})}
        if self.legacy is not None and episode_id is None and operation_key is None:
            return self._legacy_binding().read_result(reference, scope)
        raise ValueError('not_an_api_acquired_result')

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        if body['version'] == 'bvbrc_appservice_acquired_bundle_v1':
            return self.appservice.publications.result_identity(body)
        if body['version'] != 'api_service_acquired_result_v1':
            return self._legacy_binding().result_identity(reference, scope)
        if body['target']['assignment']['service'] == 'sequence_support':
            from gene_annotation_episode.episodic_workflow.root.library.sequence_support_publication import read_sequence_support_publication
            publication = read_sequence_support_publication(self.store,
                body['publication_result']['sequence_support_ref'])
            if (publication['native_source_ref'] != body['source_ref']
                    or publication['native_artifact_ref'] != 'artifact_' + body['snapshot_sha256']):
                raise ValueError('sequence_support_original_source_conflict')
            return digest({'service': 'sequence_support', 'request': body['service_request'],
                           'response_sha256': body['snapshot_sha256']})
        if body['target']['assignment']['service'] == 'rfam_batch':
            body = self.rfam_returns.read(reference, scope)
            # Submission, native source and derived grading source describe one
            # acquired result. A different preview of the same retained bytes
            # must not manufacture another acquired-record contribution.
            return digest({'service': 'rfam_batch', 'request': body['service_request'],
                'job_id': body['target']['execution_id'],
                'representation': body['assignment']['selector']['representation'],
                'response_sha256': body['snapshot_sha256']})
        publication = set(body['record_refs'])
        from .bvbrc_data_host import is_bvbrc_request
        if is_bvbrc_request(body['service_request']) and body['target']['assignment']['service'] == 'bvbrc_data':
            _, _, _, grading, _ = self.bvbrc_data._stored(reference, scope)
            page = digest({'service': 'bvbrc_data', 'request': grading['prepared']['effective_request'],
                'population': grading['prepared']['query_population'], 'response_sha256': body['snapshot_sha256']})
        else:
            page = digest({'service': body['target']['assignment']['service'], 'request': body['service_request'],
                'selector': ({} if body['target']['assignment']['service'] in {'bvbrc_minhash', 'enrichr'}
                             else body['assignment']['selector']),
                'response_sha256': body['snapshot_sha256']})
        cache = {body['source_ref']: {'record_type': 'source', 'page': page}}
        visiting = set()
        def record(ref):
            if ref in cache:
                return cache[ref]
            if ref in visiting:
                raise ValueError('cyclic_api_result_identity')
            visiting.add(ref)
            value = {key: normalize(value) for key, value in self.store.get(ref).items()
                if key not in {'id', 'origin', 'retrieved_at'}}
            visiting.remove(ref)
            cache[ref] = value
            return value
        def normalize(value):
            if isinstance(value, str) and value in publication:
                return record(value)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value
        return digest({'page': page, 'record': record(reference)})

