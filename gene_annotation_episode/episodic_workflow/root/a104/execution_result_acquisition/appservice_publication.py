from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_publication_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_publication_records import AppServicePublicationRecords

class AppServicePublication(AppServicePublicationRecords):

    def _put_content(self, origin, kind, value, stamp):
        raw = canonical(value).encode('utf-8')
        artifact = self.store.artifact(raw, 'application/json')
        request = self.store.artifact(canonical({'version': DATA_VERSION, 'origin': origin, 'kind': kind, 'content_sha256': digest(value)}), 'application/json')
        source = self.store.put('source', {'provider': DATA_PROVIDER, 'accession': kind + '_' + digest(origin), 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': request, 'version': DATA_VERSION, 'retrieved_at': stamp}, origin='tool')
        return validate_contract('ContentBinding', {'source_ref': source['id'], 'artifact_field': 'artifact_ref', 'artifact_ref': artifact, 'sha256': digest(value), 'byte_count': len(raw)})

    def publication_inputs(self, context, prepared, binding, key):
        path = self._directory(context, key) / 'publication_inputs.json'
        if path.exists():
            return self._validate_inputs(context, prepared, binding, validate_contract('PublicationInputs', _read(path)), key)
        before = int(key.rsplit(':', 1)[1])
        priors = sorted((row for row in self.host._own_receipts(context) if row['contract'] == 'AcquisitionReceipt' and int(_origin(row)['operation_key'].rsplit(':', 1)[1]) < before), key=lambda row: int(_origin(row)['operation_key'].rsplit(':', 1)[1]))
        selector = prepared['native_operands']['selector']
        support, evidence = self._dependency_inputs(context, prepared, priors, before)
        adapter = self._adapter(context, selector['adapter'])
        value = validate_contract('PublicationInputs', {'version': 'bvbrc_appservice_publication_inputs_v1', 'request': prepared['native_operands']['request'], 'selector': selector, 'original_handoff_ref': context.assignment['handoff_ref'], 'current_operation': {'name': prepared['operation'], 'arguments': prepared['native_operands']['arguments']}, 'current_snapshot': binding, 'prior_acquisition_receipt_refs': [row['source_ref'] for row in priors], 'support_receipt_refs': support, 'supplied_evidence': evidence, 'adapter': selector['adapter'], 'adapter_implementation_sha256': None if adapter is None else adapter[1]})
        self._validate_inputs(context, prepared, binding, value, key)
        _immutable(path, value)
        return value

    def _grade(self, context, inputs, bundle, origin, stamp, *, current_acquisition):
        """Publish the selected pure calculation within the download action."""
        if inputs['adapter_implementation_sha256'] is None:
            return None
        binding = self._adapter(context, inputs['adapter'])
        _require(binding is not None and binding[1] == inputs['adapter_implementation_sha256'], 'appservice_adapter_implementation_conflict')
        implementation, _ = binding
        if (inputs['adapter']['adapter_id'], inputs['adapter']['adapter_version']) == ('bvbrc_proteome', '2'):
            implementation.validate_result_selector(inputs['selector'])
        before = int(origin['operation_key'].rsplit(':', 1)[1])
        values = [{'evidence': row, 'value': self.host.custody.evidence(context, row, before=before)} for row in bundle['supplied_scientific_metadata']]
        raw = {row['raw_artifact_ref']: self.store.get_artifact(row['raw_artifact_ref']) for row in bundle['artifacts']}
        for content in bundle.get('supplied_contents', []):
            data = self.host.custody.content(context, content, before=before)
            reference = content['artifact_ref']
            _require(reference not in raw or raw[reference] == data, 'appservice_supplied_content_bytes_conflict')
            raw[reference] = data
        result = implementation.consume_bundle(bundle, artifact_bytes=raw, supplied_values=values, requested_form=inputs['selector']['requested_schema'], parameters=inputs['adapter']['parameters'])
        _require((result['adapter_id'], result['adapter_version']) == (inputs['adapter']['adapter_id'], inputs['adapter']['adapter_version']), 'appservice_adapter_result_identity_conflict')
        value = {key: deepcopy(result[key]) for key in ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
        for name in ('sheet', 'components'):
            value[name + '_content'] = None if result[name] is None else self._put_content(origin, name, result[name], stamp)
        return validate_contract('AdapterResult', value)

    def publish(self, context, prepared, event, snapshot, *, common_receipt, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import _outcome
        directory = self._directory(context, operation_key)
        binding = common_receipt['snapshot']
        inputs = None if binding is None else self.publication_inputs(context, prepared, binding, operation_key)
        constructed = build_acquisition_value(prepared, event, snapshot, common_receipt=common_receipt, publication_inputs=inputs, acquisition_receipt_ref=provisional_receipt_ref(common_receipt['origin']))
        current = self.host.records.publish(context, constructed['contract'], constructed['value'], operation_key=operation_key)
        refs = [current['source_ref'], *self.host._native_refs(directory, binding)]
        result = {'service': 'bvbrc_appservice', 'event': event, 'support_receipt_ref': current['source_ref'], 'receipt_contract': current['contract']}
        if current['contract'] != 'AcquisitionReceipt':
            outcome = _outcome(operation_key, result, refs=refs, status='partial', code=event['failure_code'] or 'appservice_download_mapping_unavailable')
            _immutable(directory / 'outcome.json', outcome)
            return outcome
        bundle = self._bundle(inputs, current)
        origin, stamp = (common_receipt['origin'], binding['retrieved_at'])
        input_content = self._put_content(origin, 'publication_inputs', inputs, stamp)
        bundle_content = self._put_content(origin, self._bundle_content_kind(inputs), bundle, stamp)
        adapter_path = directory / 'scientific_adapter_result.json'
        if adapter_path.exists():
            adapter = _read(adapter_path)['adapter_result']
            if adapter is not None:
                validate_contract('AdapterResult', adapter)
        else:
            adapter = self._grade(context, inputs, bundle, origin, stamp, current_acquisition=current)
            _immutable(adapter_path, {'adapter_result': adapter})
        form_status, missing = self._requested_status(inputs, bundle, bundle_content, adapter)
        derivatives = [] if adapter is None else [adapter[name]['source_ref'] for name in ('sheet_content', 'components_content') if adapter[name] is not None]
        result_refs = self._result_references(inputs, bundle, bundle_content, adapter)
        publication = validate_contract('BundlePublication', {'version': 'bvbrc_appservice_bundle_publication_v1', 'origin': origin, 'publication_inputs_content': input_content, 'bundle_content': bundle_content, 'adapter_result': adapter, 'current_acquisition_receipt_ref': current['source_ref'], 'dependency_receipt_refs': inputs['prior_acquisition_receipt_refs'], 'support_record_refs': _unique([*refs, input_content['source_ref'], *derivatives]), 'result_record_refs': result_refs, 'requested_form_status': form_status, 'missing_requirements': missing, 'completion_proof': None})
        if form_status == 'satisfied':
            publication['completion_proof'] = {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'completed_job_outputs', 'operation_key': operation_key, 'receipt_sha256': digest(publication), 'validation_keys': ['requested_service_result']}
        published = self._put_content(origin, 'bundle_publication', publication, stamp)
        _immutable(directory / 'bundle_publication.json', {'content': published, 'value': publication})
        result.update(publication_ref=published['source_ref'], source_ref=bundle_content['source_ref'], result_record_refs=result_refs, missing_requirements=missing)
        refs = _unique([*refs, input_content['source_ref'], bundle_content['source_ref'], published['source_ref'], *derivatives])
        outcome = _outcome(operation_key, result, refs=refs, status='completed' if form_status == 'satisfied' else 'partial', code=None if form_status == 'satisfied' else missing[0]['reason_code'] if missing else 'appservice_result_partial')
        _immutable(directory / 'outcome.json', outcome)
        self.api._index_result(context, directory, outcome)
        return outcome
