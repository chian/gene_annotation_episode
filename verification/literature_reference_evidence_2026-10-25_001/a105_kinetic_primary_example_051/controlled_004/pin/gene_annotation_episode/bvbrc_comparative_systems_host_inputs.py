"""Authenticate only explicitly supplied ComparativeSystems inputs.

No acquisition or scientific extraction is performed here. Data qualification
uses the existing host's actual read, receipt, retained-byte and selection checks.
Source examination is distinct from execution and deployment attestation.
"""
from copy import deepcopy
import hashlib

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_comparative_systems_bundle_contracts import validate_parameters
from .bvbrc_comparative_systems_handoff_contracts import validate_shape
from .bvbrc_data_host import BVBRCDataHost
from .communication import plain
from .execution_contracts import canonical, digest


def _require(condition, code):
    if not condition:
        raise ValueError('comparative_systems_host_' + code)


def _selected_bindings(selector):
    return [*selector.get('supplied_contents', []),
            *(row['content'] for row in selector['supplied_metadata'])]


class _SelectedDataHost(BVBRCDataHost):
    """Extend only the existing parent's explicit-input recursion hook."""
    def _selected_input_refs(self, assignment):
        ordinary = super()._selected_input_refs(assignment)
        selector = assignment.get('selector', {})
        selected = selector.get('adapter')
        if (assignment.get('version') != 'execution_results_assignment_v1'
                or selector.get('version') != 'bvbrc_appservice_result_selector_v1'
                or type(selected) is not dict
                or (selected.get('adapter_id'), selected.get('adapter_version')) != ('bvbrc_comparative_systems', '1')):
            return ordinary
        selector = validate_contract('ResultSelector', selector)
        parameters = validate_parameters(selected['parameters'])
        data = parameters['supplied_data_selection']
        if data is None:
            return ordinary
        bound = {binding['source_ref'] for binding in _selected_bindings(selector)}
        references = list(dict.fromkeys(ref for record in data['record_sets'] for ref in record['source_refs']))
        _require(set(references) <= bound, 'data_source_not_explicitly_bound')
        return references


def _materialize_producers(publications, context, parameters, bundle, bindings, raw, before):
    host = publications.host
    result = []
    for selection in parameters['producer_evidence_selections']:
        selected = [row for row in bundle['supplied_scientific_metadata']
                    if row['content']['source_ref'] == selection['source_ref']
                    and row['content']['artifact_ref'] == selection['raw_artifact_ref']
                    and row['pointer'] == selection['record_path']]
        _require(len(selected) == 1, 'producer_source_binding_mismatch')
        value = validate_shape('ProducerEvidenceV1', host.custody.evidence(context, selected[0], before=before))
        _require(value['evidence_id'] == selection['evidence_id'], 'producer_evidence_identity_mismatch')
        # No producing-execution or deployed-task attestation format is bound.
        # Retained metadata claiming either identity cannot grant that meaning.
        _require(value['identity_kind'] in {'unknown', 'source_examined'}, 'producer_execution_attestation_unbound')
        _require(all(value[key] is None for key in ('runtime_version', 'dependency_version', 'reference_release')),
                 'producer_unexecuted_version_claim')
        references = [selection['source_ref']]
        code_sources = []
        for location in value['source_locations']:
            candidates = [binding for binding in bindings if binding['source_ref'] == location['source_ref']
                          and binding['artifact_ref'] == location['raw_artifact_ref']]
            _require(len(candidates) == 1, 'producer_location_unselected')
            binding = candidates[0]
            data = raw[binding['artifact_ref']]
            # Source-only evidence names exact source bytes. It cannot claim a
            # native scientific row or turn JSON metadata about code into code.
            _require(location['document_id'] is None and location['table'] is None
                     and location['row_ordinal'] is None and location['column_ordinal'] is None
                     and location['native_field'] is None, 'producer_location_invalid')
            if location['json_pointer']:
                host.custody.evidence(context, {'content': binding, 'pointer': location['json_pointer']}, before=before)
            if hashlib.sha256(data).hexdigest() == value['source_sha256']:
                _require(location['json_pointer'] == '', 'producer_source_pointer_mismatch')
                code_sources.append(publications.store.get(binding['source_ref']))
            references.append(binding['source_ref'])
        if value['identity_kind'] == 'source_examined':
            _require(value['source_sha256'] is not None and bool(code_sources), 'producer_source_bytes_missing')
            if value['repository_url'] is not None or value['commit'] is not None:
                _require(value['repository_url'] is not None and value['commit'] is not None,
                         'producer_repository_identity_incomplete')
                repository = value['repository_url'].rstrip('/')
                # Exact retained acquisition URLs, not a local checkout label.
                prefixes = [repository + '/blob/' + value['commit'] + '/']
                if repository.startswith('https://github.com/'):
                    prefixes.append('https://raw.githubusercontent.com/' + repository.removeprefix('https://github.com/')
                                    + '/' + value['commit'] + '/')
                _require(any(type(source.get('uri')) is str and any(source['uri'].startswith(prefix)
                    for prefix in prefixes) for source in code_sources), 'producer_repository_source_mismatch')
        else:
            _require(value['repository_url'] is None and value['commit'] is None and value['source_sha256'] is None,
                     'producer_unknown_identity_claim')
        result.append(validate_shape('QualifiedProducerEvidenceV1', {'evidence': value, 'qualification': {
            'original_task_ref': None,
            'basis': 'source_only' if value['identity_kind'] == 'source_examined' else 'unknown',
            'evidence_source_refs': list(dict.fromkeys(references)), 'host_binding_verified': True,
            'evidence_fields_verified': True, 'receiver_possession_verified': True}}))
    return tuple(result)


def collect_comparative_systems_inputs(publications, context, inputs, bundle, *, current_acquisition):
    """Return qualified Data, producer evidence and exact selected retained bytes."""
    host = publications.host
    host.custody.authenticate(context)
    inputs = validate_contract('PublicationInputs', inputs)
    bundle = validate_contract('ArtifactBundle', bundle)
    _require(context.role == 'results' and canonical(plain(context.assignment)['selector']) == canonical(inputs['selector'])
             and canonical(inputs['adapter']) == canonical(inputs['selector']['adapter']), 'original_selector_conflict')
    selected = inputs['adapter']
    _require(selected is not None and (selected['adapter_id'], selected['adapter_version']) ==
             ('bvbrc_comparative_systems', '1'), 'adapter_required')
    parameters = validate_parameters(selected['parameters'])
    binding = publications._adapter(context, selected)
    _require(binding is not None and binding[1] == inputs['adapter_implementation_sha256'], 'adapter_pin_conflict')
    current = host.records.read(current_acquisition['source_ref'], require_completed=False)
    _require(current['contract'] == 'AcquisitionReceipt' and canonical(current) == canonical(current_acquisition),
             'current_acquisition_conflict')
    value = current['value']
    origin = value['origin']
    before = int(origin['operation_key'].rsplit(':', 1)[1])
    _require(origin['run_id'] == context.run_id and origin['episode_id'] == context.episode_id
             and value['original_handoff_ref'] == inputs['original_handoff_ref']
             and canonical(value['snapshot']) == canonical(inputs['current_snapshot'])
             and value['publication_inputs_sha256'] == digest(inputs)
             and bundle['acquisition_receipt_refs'] == [*inputs['prior_acquisition_receipt_refs'], current['source_ref']],
             'current_acquisition_conflict')
    original = host.read_handoff(inputs['original_handoff_ref'], context.scope)
    _require(canonical(original['task_handoff']['original_task']) == canonical(bundle['original_task'])
             and canonical(original['assignment']['request']) == canonical(inputs['request']), 'original_task_conflict')
    _require(bundle['original_task']['required_application_id'] == bundle['original_task']['native_application_id']
             == 'ComparativeSystems', 'original_task_conflict')
    _require(canonical(bundle['supplied_contents']) == canonical(inputs['selector'].get('supplied_contents', []))
             and canonical(bundle['supplied_scientific_metadata']) == canonical(inputs['supplied_evidence']),
             'supplied_binding_conflict')
    raw, bindings = {}, []
    for content in [*bundle.get('supplied_contents', []),
                    *(row['content'] for row in bundle['supplied_scientific_metadata'])]:
        binding = validate_contract('ContentBinding', content)
        data = host.custody.content(context, binding, before=before)
        _require(binding['artifact_ref'] not in raw or raw[binding['artifact_ref']] == data, 'content_bytes_conflict')
        raw[binding['artifact_ref']] = data
        if binding not in bindings:
            bindings.append(binding)
    qualified = []
    selection = parameters['supplied_data_selection']
    reader = _SelectedDataHost(publications.api)
    for reference in dict.fromkeys(ref for record in (selection['record_sets'] if selection else [])
                                   for ref in record['source_refs']):
        # The inherited read authenticates the original publication, native bytes,
        # original selector and receiver's parent/prior-decision possession.
        result = reader.read(reference, context=context)
        saved = result['binding']
        candidates = [item for item in bindings if item['source_ref'] == reference
                      and item['artifact_ref'] == saved['native_artifact_ref']
                      and item['sha256'] == saved['native_sha256'] and item['artifact_field'] == 'artifact_ref']
        _require(len(candidates) == 1, 'data_raw_binding_mismatch')
        content = candidates[0]
        qualified.append(validate_shape('QualifiedDataInputV1', {'qualified_result': result, 'raw_binding': {
            'source_ref': reference, 'raw_artifact_ref': content['artifact_ref'], 'sha256': content['sha256'],
            'byte_count': len(raw[content['artifact_ref']]), 'bytes_key': content['artifact_ref']}}))
    producers = _materialize_producers(publications, context, parameters, bundle, bindings, raw, before)
    return tuple(qualified), producers, raw


__all__ = ['collect_comparative_systems_inputs']
