"""Qualify selected atac inputs from original received metadata only.

This boundary neither reads scientific bytes nor establishes native usability.
The selected driver owns staging, digest verification and parsing. Receipt
access and scope access do not assert a biological relationship to the target.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_atac_differential_contracts import validate_atac_requested_job

def _require(condition, code):
    if not condition:
        raise ValueError('atac_input_' + code)

def _context_inputs(store, context):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.received_native_file_inputs import received_file_context
    return received_file_context(store, context, failure_prefix='atac_input_')

def _source(store, reference, *, metadata=False):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.received_native_file_inputs import received_file_source
    return received_file_source(store, reference, metadata=metadata, failure_prefix='atac_input_')

def _file(store, identity):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.received_native_file_inputs import received_file_path
    return received_file_path(store, identity, failure_prefix='atac_input_')

def validate_atac_job_inputs(store, context: BindingContext, assignment: dict, *, reference_access) -> list[str]:
    """Return exact selected received handles once, in the agreed field order.

    Callback True is only a provider decision. Actual original receipts, Store
    scope, source/file relationships and metadata identity remain necessary.
    """
    if not (type(assignment) is dict and type(assignment.get('requested_job')) is dict and ('native_atac_differential' in assignment['requested_job'])):
        return []
    try:
        requested = validate_atac_requested_job(assignment['requested_job'])
    except ValueError as error:
        raise ValueError('atac_input_invalid_requested_job') from error
    known, scope = _context_inputs(store, context)
    job = requested['native_atac_differential']
    request = job['request']
    references, seen = ([], set())

    def received(reference, *, artifact=False):
        decision = reference_access(context, reference, None)
        _require(decision is None or type(decision) is bool, 'invalid_reference_access')
        _require(decision is not False, 'protected_reference_denied')
        _require(reference in known, 'input_not_received')
        if not artifact:
            _require(reference in store.reference_subset([reference], scope), 'input_outside_scope')
        if reference not in seen:
            seen.add(reference)
            references.append(reference)

    def metadata_source(reference):
        if reference is not None:
            received(reference)
            _source(store, reference, metadata=True)
    for occurrence, binding in zip(request['inputs'], job['input_bindings']):
        identity = occurrence['file']
        received(identity['artifact_ref'], artifact=True)
        _require(binding['input_key'] == occurrence['input_key'] and binding['file'] == identity, 'input_binding_mismatch')
        _require(binding['path'] == str(_file(store, identity)), 'selected_path_mismatch')
    reference = request['reference']
    for value in [reference, *reference['contigs'], *reference['aliases']]:
        for source_ref in value['source_refs']:
            metadata_source(source_ref)
    return references
