from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_record_access import AppServiceRecordAccess

class AppServiceSubmission(AppServiceRecordAccess):

    def __init__(self, execution):
        self.api, self.store, self.run_id = (execution, execution.store, execution.run_id)
        self.records = AppServiceRecords(execution)
        self.custody = AppServiceCustody(self.store, self.run_id, read_original_handoff=self.original_handoff)
        self.inputs = AppServiceInputs(execution, records=self.records, custody=self.custody, read_acquisition=self.read_acquisition)
        from gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_job_submission.api_job_execution.appservice_publication import AppServicePublication as AppServicePublications
        self.publications = AppServicePublications(self)

    def legacy_cached_download(self, context, name, arguments, key):
        """Admit only an authenticated, already-published uncapped old action.

        This read permits no invocation and inserts no operand/default. Fresh
        downloads, including a new action repeating old arguments, need a cap.
        """
        if name != 'api.bvbrc_appservice.download' or type(arguments) is not dict or 'max_bytes' in arguments:
            return None
        validate_contract('Arguments_download', arguments)
        self.custody.authenticate(context)
        self.custody._require(context.role == 'results' and self.owns_context(context), 'appservice_cached_download_context_conflict')
        selected = self.api._selected(context, name, arguments, key)
        self.custody.possession(context, plain(context.assignment)['handoff_ref'])
        directory = self.api._episode_directory(context.episode_id) / 'actions' / digest(key)
        if not (directory / 'intent.json').exists() or not (directory / 'outcome.json').exists():
            return None
        _, service, _ = self.api._context(context, _completed_appservice_download=True)
        self.custody._require(service.service == SERVICE, 'appservice_cached_download_context_conflict')
        self.api._manifest(context, create=False)
        try:
            intent, outcome = (_read(directory / 'intent.json'), _read(directory / 'outcome.json'))
        except FileNotFoundError:
            return None
        except OSError as error:
            raise ValueError('appservice_cached_download_unavailable') from error
        original = dict(run_id=self.run_id, episode_id=context.episode_id, name=name, arguments=arguments, assignment_sha256=digest(context.assignment), operation_key=key)
        self.custody._require(all((canonical(intent.get(field)) == canonical(value) for field, value in original.items())), 'appservice_cached_download_intent_conflict')
        prepared = validate_contract('PreparedOperation', intent['prepared'])
        call = prepared['native_operands']['call']
        self.custody._require(prepared['operation'] == name and prepared['native_kind'] == 'download' and (prepared['purpose'] == 'acquisition') and (not prepared['effects']) and (not prepared['mutates_remote']) and (set(call) == {'url', 'byte_range'}) and ('max_bytes' not in download_request(call, arguments=arguments)), 'appservice_cached_download_intent_conflict')
        origin = self.records._origin(context, prepared, key, _completed_download=True)
        result = outcome.get('result') or {}
        reference = result.get('support_receipt_ref')
        self.custody._require(outcome.get('status') in {'completed', 'partial'} and outcome.get('operation_ref') == identity('api_operation', {'key': key}) and (reference in outcome.get('record_refs', [])), 'appservice_cached_download_outcome_conflict')
        receipt = self.records.read(reference, _completed_download=True)
        common = receipt['value'] if receipt['contract'] == 'AcquisitionReceipt' else _common(receipt)
        self.custody._require(result.get('service') == SERVICE and result.get('receipt_contract') == receipt['contract'] and (canonical(common['origin']) == canonical(origin)), 'appservice_cached_download_outcome_conflict')
        self.custody._require(selected['result'] is not None, 'appservice_cached_download_outcome_conflict')
        actual = json.loads(selected['result'])
        self.custody._require(all((field in actual and canonical(actual[field]) == canonical(value) for field, value in outcome.items())), 'appservice_cached_download_outcome_conflict')
        return deepcopy(outcome)

    async def execute_locked(self, context, assignment, service, target, name, arguments, key, directory):
        from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import _now, _outcome
        intent_path, outcome_path = (directory / 'intent.json', directory / 'outcome.json')
        original = {'run_id': self.run_id, 'episode_id': context.episode_id, 'name': name, 'arguments': arguments, 'assignment_sha256': digest(context.assignment), 'operation_key': key}
        if intent_path.exists():
            intent = _read(intent_path)
            if any((canonical(intent.get(field)) != canonical(value) for field, value in original.items())):
                return _outcome(key, status='invalid', code='api_operation_key_reused_for_different_work')
            if outcome_path.exists():
                outcome = _read(outcome_path)
                if (outcome.get('result') or {}).get('publication_ref') is not None:
                    self.api._index_result(context, directory, outcome)
                return outcome
            fresh = False
        else:
            try:
                if name == 'api.bvbrc_appservice.download':
                    if type(arguments.get('max_bytes')) is not int or arguments['max_bytes'] <= 0:
                        raise ValueError('bvbrc_download_byte_limit_required')
                if self.completion(context) is not None:
                    raise ValueError('api_assignment_already_completed')
                bound = self.bind_inputs(context, name, arguments, operation_key=key)
                prepared = service.prepare(name, assignment['request'], arguments, scope=plain(context.scope), previous_events=self.api._events(context.episode_id), handle=None if target is None else {'task_id': target['execution_id']}, selector=None if target is None else plain(context.assignment)['selector'], bound_inputs=bound)
                if prepared['purpose'] == 'acquisition' and prepared['native_kind'] == 'download':
                    self.publications.validate_selected_inputs(context, prepared, key)
                intent = {**original, 'prepared': prepared, 'started_at': _now()}
                _immutable(intent_path, intent)
                fresh = True
            except (ValueError, ContractError, KeyError, TypeError) as error:
                return _outcome(key, status='invalid', code=getattr(error, 'code', str(error)))
        prepared = validate_contract('PreparedOperation', intent['prepared'])
        try:
            call = await perform_selected_call(self.api, context, service, prepared, operation_key=key, directory=directory, fresh=fresh)
        except EffectConflict as error:
            return _outcome(key, status='invalid', code=error.code, affected_effect_refs=list(error.effect_refs))
        snapshot, failure = (call['snapshot'], call['failure'])
        binding = None if snapshot is None else self.records.retain_snapshot(context, prepared, snapshot, operation_key=key)
        if snapshot is None and failure is not None:
            event = native_event('metadata', 'unknown', failure_code=failure['code'], facts={'operation': name, 'failure': failure, 'diagnostics': []})
        else:
            event = service.decode(prepared, snapshot)
        event = self.api._event(event)
        _immutable(directory / 'event.json', event)
        effects = call['effect_receipts']
        if effects:
            effects = self.api.selected_effects.record_outcome(_read(directory / 'effect_reservation.json'), confirm_appservice_effects(prepared, event, snapshot, snapshot_binding=binding, effect_receipts=effects))
        origin = self.records._origin(context, prepared, key)
        diagnostics = [] if failure is None else [_diagnostic(failure['code'], phase=failure['phase'], refs=failure['valid_record_refs'])]
        common = validate_contract('CommonReceipt', {'version': 'bvbrc_appservice_support_receipt_v1', 'receipt_ref': provisional_receipt_ref(origin), 'purpose': prepared['purpose'], 'origin': origin, 'snapshot': binding, 'effect_receipt_refs': [row['effect_ref'] for row in effects], 'status': 'ok' if failure is None else 'partial', 'diagnostics': diagnostics})
        if prepared['purpose'] == 'acquisition':
            return self.publish_acquisition(context, prepared, event, snapshot, common_receipt=common, operation_key=key)
        value = build_appservice_receipt(prepared, event, snapshot, common_receipt=common, effect_receipts=effects)
        published = self.records.publish(context, value['contract'], value['value'], operation_key=key)
        refs = [published['source_ref'], *self._native_refs(directory, binding)]
        receipt = _common(published)
        result = {'service': SERVICE, 'event': event, 'support_receipt_ref': published['source_ref'], 'receipt_contract': published['contract']}
        if published['contract'] == 'TaskHandoff':
            result.pop('support_receipt_ref')
            result.update(handoff_ref=published['source_ref'], receipt=receipt)
        outcome = _outcome(key, result, refs=refs, status='completed' if receipt['status'] == 'ok' else 'partial', code=None if receipt['status'] == 'ok' else event['failure_code'] or 'appservice_operation_qualified')
        _immutable(outcome_path, outcome)
        return outcome

    def _own_receipts(self, context):
        if not self.owns_context(context):
            return []
        self.custody.authenticate(context, allow_unsaved=True)
        rows = []
        for _, outcome in self.api._own_outcomes(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            result = outcome.get('result') or {}
            reference = result.get('handoff_ref') or result.get('support_receipt_ref')
            if reference is not None:
                rows.append(self.records.read(reference))
        return rows

    def facts(self, context):
        rows = self._own_receipts(context)
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        facts = {'execution_handoff_refs': [r['source_ref'] for r in rows if r['contract'] == 'TaskHandoff'], SUPPORT_SOURCE: [r['source_ref'] for r in rows if r['contract'] != 'TaskHandoff'], 'execution_result_refs': self.publications.own_results(context), 'execution_blast_hsps': [], 'execution_completed': self.completion(context) is not None}
        for returns in (self.api.homology_returns, self.api.phylogeny_returns, self.api.proteome_returns):
            supplied = returns.facts(context, schema)
            if set(facts).intersection(supplied):
                raise ValueError('appservice_own_fact_source_conflict')
            facts.update(supplied)
        return facts

    def completion(self, context):
        for record in reversed(self._own_receipts(context)):
            if record['contract'] != 'TaskHandoff':
                continue
            common = record['value']['receipt']
            self.read_handoff(record['source_ref'], context.scope)
            return {'version': 'practical_completion_v1', 'run_id': self.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'usable_handoff', 'operation_key': common['origin']['operation_key'], 'receipt_sha256': digest(common), 'validation_keys': ['usable_handoff']}
        return None

    def publish_acquisition(self, context, prepared, event, snapshot, *, common_receipt, operation_key):
        return self.publications.publish(context, prepared, event, snapshot, common_receipt=common_receipt, operation_key=operation_key)
