from __future__ import annotations
from copy import deepcopy
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_bundle_values import build_artifact_bundle
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
DATA_PROVIDER = 'episode.bvbrc_appservice_bundle_data'
DATA_VERSION = 'bvbrc_appservice_bundle_data_v1'
RESULT_VERSION = 'bvbrc_appservice_acquired_bundle_v1'

def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(deepcopy(value))
    return result

def _require(condition, code):
    if not condition:
        raise ValueError(code)

class AppServicePublications:

    def __init__(self, host):
        self.host, self.api, self.store = (host, host.api, host.store)

    @staticmethod
    def is_provider(provider):
        return provider == DATA_PROVIDER

    def _directory(self, context, key):
        return self.api._manifest(context, create=False) / 'actions' / digest(key)

    @staticmethod
    def _bundle_content_kind(inputs):
        selected = inputs['adapter']
        if selected is not None and ((selected['adapter_id'], selected['adapter_version']) in {('bvbrc_annotation', '1'), ('bvbrc_assembly', '1'), ('bvbrc_variation', '1'), ('bvbrc_influenza_ha', '1'), ('bvbrc_subspecies', '1'), ('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}):
            return 'application_artifact_bundle'
        return 'artifact_bundle'

    def _content(self, binding, origin, kind, stamp):
        binding = validate_contract('ContentBinding', binding)
        source = self.host.records._source(binding['source_ref'], provider=DATA_PROVIDER, origin='tool', version=DATA_VERSION)
        value = self.host.records._artifact_json(binding['artifact_ref'])
        request = self.host.records._artifact_json(source['request_ref'])
        _require(request == {'version': DATA_VERSION, 'origin': origin, 'kind': kind, 'content_sha256': digest(value)}, 'appservice_bundle_content_origin_conflict')
        _require(source['accession'] == kind + '_' + digest(origin) and source['uri'] is None and (source['text_ref'] is None) and (source['retrieved_at'] == stamp) and (source['artifact_ref'] == binding['artifact_ref']) and (binding['artifact_field'] == 'artifact_ref') and (binding['sha256'] == digest(value)) and (binding['byte_count'] == len(canonical(value).encode('utf-8'))), 'appservice_bundle_content_conflict')
        return value

    def _evidence(self, context, prepared, before):
        selector = prepared['native_operands']['selector']
        arguments = prepared['native_operands']['arguments']
        evidence = list(selector['supplied_metadata'])
        evidence.extend((row['producer_rule_evidence'] for row in selector['requirements'] if row['producer_rule_evidence'] is not None))
        evidence.extend(arguments['declared_format']['transformation_evidence'])
        evidence = _unique(evidence)
        for row in evidence:
            self.host.custody.evidence(context, row, before=before)
        return evidence

    def _dependency_inputs(self, context, prepared, priors, before):
        support = list(prepared['bound_inputs']['support_receipt_refs'])
        evidence = self._evidence(context, prepared, before)
        producer = prepared['native_operands']['arguments']['declared_format']['producer_source_ref']
        if producer is not None:
            support.append(producer)
        for row in priors:
            origin = row['value']['origin']
            prior = validate_contract('PublicationInputs', _read(self._directory(context, origin['operation_key']) / 'publication_inputs.json'))
            _require(digest(prior) == row['value']['publication_inputs_sha256'], 'appservice_publication_dependency_conflict')
            support.extend(prior['support_receipt_refs'])
            evidence.extend(prior['supplied_evidence'])
        return (_unique(support), _unique(evidence))

    def _validate_inputs(self, context, prepared, binding, value, key):
        before = int(key.rsplit(':', 1)[1])
        _require(canonical(value['request']) == canonical(prepared['native_operands']['request']) and canonical(value['selector']) == canonical(prepared['native_operands']['selector']) and (value['original_handoff_ref'] == context.assignment['handoff_ref']) and (canonical(value['current_snapshot']) == canonical(binding)) and (canonical(value['current_operation']) == canonical({'name': prepared['operation'], 'arguments': prepared['native_operands']['arguments']})), 'appservice_publication_original_inputs_conflict')
        self.host.custody.possession(context, value['original_handoff_ref'], before=before)
        for ref in value['support_receipt_refs']:
            self.host.custody.possession(context, ref, before=before)
        indices, priors = ([], [])
        for ref in value['prior_acquisition_receipt_refs']:
            receipt = self.host.read_acquisition(ref)
            self.host.custody.possession(context, ref, before=before)
            origin = receipt['origin']
            index = int(origin['operation_key'].rsplit(':', 1)[1])
            _require(origin['run_id'] == context.run_id and origin['episode_id'] == context.episode_id and (index < before) and (receipt['original_handoff_ref'] == value['original_handoff_ref']) and (receipt['selector_sha256'] == digest(value['selector'])), 'appservice_publication_dependency_conflict')
            indices.append(index)
            priors.append({'source_ref': ref, 'contract': 'AcquisitionReceipt', 'value': receipt})
        _require(indices == sorted(set(indices)), 'appservice_publication_dependency_order_conflict')
        support, evidence = self._dependency_inputs(context, prepared, priors, before)
        _require(canonical(value['supplied_evidence']) == canonical(evidence) and value['support_receipt_refs'] == support, 'appservice_publication_original_inputs_conflict')
        for row in evidence:
            self.host.custody.evidence(context, row, before=before)
        for binding in value['selector'].get('supplied_contents', []):
            self.host.custody.content(context, binding, before=before)
        selected = value['adapter']
        _require(canonical(selected) == canonical(value['selector']['adapter']), 'appservice_publication_adapter_conflict')
        return value

    def _bundle(self, inputs, current):
        acquisitions = [{'receipt_ref': ref, 'receipt': self.host.read_acquisition(ref)} for ref in inputs['prior_acquisition_receipt_refs']]
        acquisitions.append({'receipt_ref': current['source_ref'], 'receipt': current['value']})
        task = self.host.read_handoff(inputs['original_handoff_ref'])['task_handoff']['original_task']
        return build_artifact_bundle(inputs, original_task=task, acquisitions=acquisitions, input_bindings=inputs['request']['input_bindings'], query_bindings=[])

    @staticmethod
    def _requested_status(inputs, bundle, bundle_content, adapter):
        missing = deepcopy(bundle['missing_requirements'])
        status = 'satisfied' if bundle['status'] == 'ok' else 'partial'
        if inputs['selector']['endpoint'] != 'requested_projection':
            return (status, missing)
        if adapter is None:
            missing.append({'requirement_id': 'scientific_adapter', 'kind': 'parser_binding', 'role': None, 'source_refs': [bundle_content['source_ref']], 'reason_code': 'scientific_adapter_unbound'})
            return ('unavailable', missing)
        missing = _unique([*missing, *adapter['missing_requirements']])
        if adapter['status'] in {'ok', 'partial'}:
            errors = list(Draft202012Validator(inputs['selector']['requested_schema']).iter_errors(adapter['facts']))
            _require(not errors, 'appservice_adapter_requested_facts_conflict')
        if adapter['status'] == 'invalid':
            status = 'invalid'
        elif adapter['status'] != 'ok' or bundle['status'] != 'ok' or (missing and (adapter['adapter_id'], adapter['adapter_version']) not in {('bvbrc_msa', '1'), ('bvbrc_metacats', '1'), ('bvbrc_genome_alignment', '1'), ('bvbrc_proteome', '1'), ('bvbrc_proteome', '2'), ('bvbrc_comparative_systems', '1'), ('bvbrc_fastqutils', '2')}):
            status = 'partial'
        return (status, missing)

    @staticmethod
    def _result_references(inputs, bundle, bundle_content, adapter):
        """One shared publication/read predicate; partial science is not completion."""
        native_usable = any((row['transfer']['body_complete'] is True and row['transfer']['object_complete'] == 'yes' for row in bundle['artifacts']))
        selected = inputs['adapter']
        partial_sheet_saved = selected is not None and adapter is not None and ((selected['adapter_id'], selected['adapter_version']) in {('bvbrc_proteome', '2'), ('bvbrc_fastqutils', '2'), ('bvbrc_annotation', '1'), ('bvbrc_assembly', '1'), ('bvbrc_variation', '1'), ('bvbrc_influenza_ha', '1'), ('bvbrc_subspecies', '1'), ('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}) and ((adapter['adapter_id'], adapter['adapter_version']) == (selected['adapter_id'], selected['adapter_version'])) and (adapter['status'] in {'ok', 'partial'}) and (adapter['sheet_content'] is not None)
        return [bundle_content['source_ref']] if native_usable or partial_sheet_saved else []

    def read_content_source(self, reference, scope):
        """Authenticate a retained sheet/input/publication without granting custody."""
        source = self.host.records._source(reference, provider=DATA_PROVIDER, origin='tool', version=DATA_VERSION)
        request = self.host.records._artifact_json(source['request_ref'])
        _require(set(request) == {'version', 'origin', 'kind', 'content_sha256'} and request['version'] == DATA_VERSION, 'appservice_bundle_content_origin_conflict')
        origin = validate_contract('ReceiptOrigin', request['origin'])
        context = self.host.custody.context(origin['episode_id'])
        directory = self._directory(context, origin['operation_key'])
        retained = _read(directory / 'bundle_publication.json')
        publication = retained['value']
        body = self.read(publication['bundle_content']['source_ref'], scope, episode_id=context.episode_id)
        bindings = {'bundle_publication': retained['content'], self._bundle_content_kind(body['publication_inputs']): publication['bundle_content'], 'publication_inputs': publication['publication_inputs_content']}
        adapter = publication['adapter_result']
        if adapter is not None:
            bindings.update({name: adapter[name + '_content'] for name in ('sheet', 'components') if adapter[name + '_content'] is not None})
        binding = bindings.get(request['kind'])
        _require(binding is not None and binding['source_ref'] == reference, 'appservice_bundle_content_not_published')
        return self._content(binding, origin, request['kind'], source['retrieved_at'])

    def read(self, reference, scope, *, episode_id=None):
        index = self.api.directory / 'result-index' / digest(reference)
        for path in sorted(index.glob('*.json')):
            pointer = _read(path)
            if episode_id is not None and pointer['episode_id'] != episode_id:
                continue
            context = self.host.custody.context(pointer['episode_id'])
            self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
            _require(context.role == 'results' and self.host.owns_context(context), 'appservice_bundle_original_results_required')
            directory = self._directory(context, pointer['operation_key'])
            retained = _read(directory / 'bundle_publication.json')
            publication = validate_contract('BundlePublication', retained['value'])
            if reference not in publication['result_record_refs']:
                continue
            acquisition = self.host.records.read(publication['current_acquisition_receipt_ref'])
            _require(acquisition['contract'] == 'AcquisitionReceipt', 'appservice_acquisition_receipt_required')
            value, origin = (acquisition['value'], publication['origin'])
            _require(canonical(origin) == canonical(value['origin']), 'appservice_bundle_origin_conflict')
            stamp = value['snapshot']['retrieved_at']
            _require(canonical(self._content(retained['content'], origin, 'bundle_publication', stamp)) == canonical(publication), 'appservice_bundle_publication_conflict')
            inputs = self._content(publication['publication_inputs_content'], origin, 'publication_inputs', stamp)
            _require(canonical(inputs) == canonical(_read(directory / 'publication_inputs.json')) and digest(inputs) == value['publication_inputs_sha256'], 'appservice_publication_original_inputs_conflict')
            intent = _read(directory / 'intent.json')
            self._validate_inputs(context, intent['prepared'], value['snapshot'], inputs, origin['operation_key'])
            bundle = self._content(publication['bundle_content'], origin, self._bundle_content_kind(inputs), stamp)
            _require(canonical(bundle) == canonical(self._bundle(inputs, acquisition)) and publication['dependency_receipt_refs'] == inputs['prior_acquisition_receipt_refs'], 'appservice_bundle_dependency_conflict')
            adapter = publication['adapter_result']
            retained_adapter = directory / 'scientific_adapter_result.json'
            if retained_adapter.exists():
                _require(canonical(_read(retained_adapter)) == canonical({'adapter_result': adapter}), 'appservice_adapter_publication_conflict')
            if adapter is not None:
                _require(inputs['adapter'] is not None and (adapter['adapter_id'], adapter['adapter_version']) == (inputs['adapter']['adapter_id'], inputs['adapter']['adapter_version']), 'appservice_adapter_result_identity_conflict')
                contents = {}
                for name in ('sheet', 'components'):
                    content = adapter[name + '_content']
                    contents[name] = None if content is None else self._content(content, origin, name, stamp)
                if (adapter['adapter_id'], adapter['adapter_version']) == ('bvbrc_comparative_systems', '1'):
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_publication import decode_comparative_publication_result
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
                    native, failure_context = decode_comparative_publication_result(adapter, **contents)
                    validate_saved_comparative_systems_projection(native['sheet'], native['components'], **{key: native[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')}, requested_form=inputs['selector']['requested_schema'], parameters=inputs['adapter']['parameters'], original_task=bundle['original_task'], bundle=bundle, failure_context=failure_context)
                if (adapter['adapter_id'], adapter['adapter_version']) == ('bvbrc_fastqutils', '2'):
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_fastqutils_saved_codec import validate_saved_projection
                    validate_saved_projection(contents['sheet'], contents['components'], **{key: adapter[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')}, requested_form=inputs['selector']['requested_schema'], parameters=inputs['adapter']['parameters'], original_task=bundle['original_task'], bundle=bundle)
                if (adapter['adapter_id'], adapter['adapter_version']) in {('bvbrc_annotation', '1'), ('bvbrc_assembly', '1'), ('bvbrc_variation', '1'), ('bvbrc_influenza_ha', '1'), ('bvbrc_subspecies', '1'), ('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}:
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_bundle_adapter import validate_saved_annotation_facts, annotation_projection_status
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_assembly_bundle_adapter import validate_saved_assembly_facts, assembly_projection_status
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_variation_bundle_adapter import validate_saved_variation_facts, variation_projection_status
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_influenza_ha_bundle_adapter import validate_saved_influenza_ha_facts, influenza_ha_projection_status
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_subspecies_bundle_adapter import validate_saved_subspecies_facts, subspecies_projection_status
                    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_intervention_bundle_adapter import validate_saved_intervention_facts, intervention_projection_status
                    saved_reader, status_reader = {'bvbrc_annotation': (validate_saved_annotation_facts, annotation_projection_status), 'bvbrc_assembly': (validate_saved_assembly_facts, assembly_projection_status), 'bvbrc_variation': (validate_saved_variation_facts, variation_projection_status), 'bvbrc_influenza_ha': (validate_saved_influenza_ha_facts, influenza_ha_projection_status), 'bvbrc_subspecies': (validate_saved_subspecies_facts, subspecies_projection_status), 'bvbrc_tnseq': (validate_saved_intervention_facts, intervention_projection_status), 'bvbrc_rnaseq': (validate_saved_intervention_facts, intervention_projection_status)}[adapter['adapter_id']]
                    empty_invalid = adapter['status'] == 'invalid' and contents['sheet'] is None and (contents['components'] is None) and (adapter['facts'] == {})
                    if not empty_invalid:
                        saved_reader(adapter['facts'], **contents, requested_form=inputs['selector']['requested_schema'], parameters=inputs['adapter']['parameters'])
                        _require(contents['sheet']['original_task'] == bundle['original_task'] and adapter['status'] == status_reader(bundle_status=bundle['status'], missing_requirements=adapter['missing_requirements'], diagnostics=adapter['diagnostics'], facts=adapter['facts']), 'appservice_' + adapter['adapter_id'].removeprefix('bvbrc_') + '_saved_projection_conflict')
            status, missing = self._requested_status(inputs, bundle, publication['bundle_content'], adapter)
            _require(publication['result_record_refs'] == self._result_references(inputs, bundle, publication['bundle_content'], adapter), 'appservice_bundle_result_references_conflict')
            _require(status == publication['requested_form_status'] and canonical(missing) == canonical(publication['missing_requirements']), 'appservice_bundle_requested_form_conflict')
            outcome = _read(directory / 'outcome.json')
            _require(outcome.get('result', {}).get('publication_ref') == retained['content']['source_ref'] and outcome['result'].get('result_record_refs') == publication['result_record_refs'] and (reference in outcome['record_refs']), 'appservice_bundle_outcome_conflict')
            proof = publication['completion_proof']
            selected = inputs['adapter']
            if selected is not None and (selected['adapter_id'], selected['adapter_version']) in {('bvbrc_proteome', '2'), ('bvbrc_comparative_systems', '1'), ('bvbrc_fastqutils', '2'), ('bvbrc_annotation', '1'), ('bvbrc_assembly', '1'), ('bvbrc_variation', '1'), ('bvbrc_influenza_ha', '1'), ('bvbrc_subspecies', '1'), ('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}:
                _require((proof is not None) == (status == 'satisfied') and outcome['status'] == ('completed' if status == 'satisfied' else 'partial'), 'appservice_bundle_completion_conflict')
            if proof is not None:
                _require(publication['requested_form_status'] == 'satisfied' and proof == {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': 'completed_job_outputs', 'operation_key': origin['operation_key'], 'receipt_sha256': digest({**publication, 'completion_proof': None}), 'validation_keys': ['requested_service_result']}, 'appservice_bundle_completion_conflict')
            return {'version': RESULT_VERSION, 'reference': reference, 'run_id': context.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope), 'assignment': plain(context.assignment), 'target': self.host.read_target(inputs['original_handoff_ref'], scope), 'source_ref': publication['bundle_content']['source_ref'], 'record_refs': publication['result_record_refs'], 'status': outcome['status'], 'service_request': inputs['request'], 'publication': publication, 'publication_inputs': inputs, 'bundle': bundle}
        raise ValueError('not_an_appservice_acquired_result')

    def own_results(self, context):
        if context.role != 'results':
            return []
        refs = []
        for _, outcome in self.api._own_outcomes(context):
            for reference in (outcome.get('result') or {}).get('result_record_refs', []):
                self.read(reference, context.scope, episode_id=context.episode_id)
                refs.append(reference)
        return _unique(refs)

    def completion(self, context):
        selected = plain(context.assignment).get('selector', {}).get('adapter')
        if selected is not None and (selected['adapter_id'], selected['adapter_version']) in {('bvbrc_genome_alignment', '1'), ('bvbrc_proteome', '1'), ('bvbrc_proteome', '2'), ('bvbrc_comparative_systems', '1'), ('bvbrc_fastqutils', '2'), ('bvbrc_annotation', '1'), ('bvbrc_assembly', '1'), ('bvbrc_variation', '1'), ('bvbrc_influenza_ha', '1'), ('bvbrc_subspecies', '1'), ('bvbrc_tnseq', '1'), ('bvbrc_rnaseq', '1')}:
            self.host.custody.authenticate(context, allow_unsaved=True)
            for _, outcome in reversed(list(self.api._own_outcomes(context))):
                result = outcome.get('result') or {}
                if result.get('publication_ref') is None:
                    continue
                refs = result.get('result_record_refs', [])
                if not refs:
                    return None
                return self.read(refs[-1], context.scope, episode_id=context.episode_id)['publication']['completion_proof']
            return None
        for reference in reversed(self.own_results(context)):
            proof = self.read(reference, context.scope, episode_id=context.episode_id)['publication']['completion_proof']
            if proof is not None:
                return proof
        return None
