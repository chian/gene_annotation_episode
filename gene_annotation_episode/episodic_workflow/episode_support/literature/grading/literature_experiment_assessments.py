"""Experiment identity and immutable revision custody for this episode.

Numerical readers and graders remain axis-specific. This module keeps their
assessments and revisions associated with actual experiments without creating
new scores, scientific observations, or cross-experiment weighting rules.
"""
from copy import deepcopy
import hashlib
from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, REF, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain

ASSESSMENTS = TableDeclaration(name='literature_experiment_assessments',
                               columns=('sheet_ref', 'experiment_ref', 'assessment_key', 'assessment'),
                               key=('sheet_ref',), record_refs=('sheet_ref', 'experiment_ref'))

def record_assessment(store, sheet_ref, assessment):
    """Keep the assessment saved with a sheet as the Episode's row, keyed by the sheet."""
    return store.table(ASSESSMENTS).put({'sheet_ref': sheet_ref, 'experiment_ref': assessment['experiment_ref'], 'assessment_key': assessment['assessment_key'], 'assessment': deepcopy(assessment)})

def assessment_schema(experiment_types):
    reference = {**REF, 'x-reference-namespace': 'reference'}
    source = {**REF, 'x-reference-namespace': 'source'}
    text = {'type': 'string', 'minLength': 1}
    return obj({'experiment_ref': reference, 'experiment_type': {'enum': list(experiment_types)}, 'assessment_key': text, 'scientific_question': text, 'conclusion': text, 'limitations': {'type': 'array', 'items': text}, 'revision_reason': {'type': ['string', 'null'], 'minLength': 1}, 'revises_sheet_ref': {**source, 'type': ['string', 'null']}})

def validate_assessment(value, experiment_types):
    validate_schema(value, assessment_schema(experiment_types))
    for key in ('assessment_key', 'scientific_question', 'conclusion'):
        if not value[key].strip():
            raise ContractError('experimental_assessment_text_required')
    if any((not item.strip() for item in value['limitations'])):
        raise ContractError('experimental_assessment_text_required')
    if (value['revises_sheet_ref'] is None) != (value['revision_reason'] is None):
        raise ContractError('experimental_revision_reason_required')
    if value['revision_reason'] is not None and (not value['revision_reason'].strip()):
        raise ContractError('experimental_revision_reason_required')

def authorize_assessment(repository, context, value):
    """Use an explicitly received, sourced assay identity; never infer identity."""
    validate_assessment(value, repository.experiment_types)
    ref = value['experiment_ref']
    if ref not in context.received_record_refs:
        raise ContractError('experimental_experiment_not_received')
    record = repository.store.get(ref)
    if record['record_type'] != 'reference' or record.get('reference_type') != 'assay':
        raise ContractError('experimental_experiment_reference_required')
    if not repository.store.reference_subset([ref], plain(context.scope)):
        raise ContractError('experimental_experiment_outside_scope')
    repository._source(context, record['source_ref'])
    if value['revises_sheet_ref'] is not None:
        repository._source(context, value['revises_sheet_ref'])

def current_assessments(repository):
    """Read current assessments, retaining one head per experiment/question key.

    This is an inventory, not a numerical aggregate or an independence count.
    Historical unlinked sheets remain available through their original APIs.
    """
    histories, superseded = ({}, set())
    for row in repository.store.table(ASSESSMENTS).select():
        assessment = row['assessment']
        saved = repository.read(row['sheet_ref'])
        if saved.get('experiment_assessment') != assessment:
            raise ContractError('experimental_assessment_saved_mismatch')
        histories[row['sheet_ref']] = deepcopy(assessment)
        if assessment['revises_sheet_ref'] is not None:
            superseded.add(assessment['revises_sheet_ref'])
    heads = [{'sheet_ref': ref, **value} for ref, value in histories.items() if ref not in superseded]
    keys = [(v['experiment_ref'], v['assessment_key']) for v in heads]
    if len(keys) != len(set(keys)):
        raise ContractError('experimental_assessment_conflicting_heads')
    return sorted(heads, key=lambda v: (v['experiment_ref'], v['assessment_key']))

def check_revision(repository, value):
    """Call inside the publication transaction so stale writers cannot branch."""
    heads = current_assessments(repository)
    head = next((v for v in heads if (v['experiment_ref'], v['assessment_key']) == (value['experiment_ref'], value['assessment_key'])), None)
    expected = head['sheet_ref'] if head else None
    if expected != value['revises_sheet_ref']:
        raise ContractError('experimental_assessment_revision_required' if expected else 'experimental_assessment_predecessor_mismatch')

def validate_saved_assessment(repository, saved, request, sheet_ref):
    expected = request['arguments'].get('experiment_assessment')
    if saved.get('experiment_assessment') != expected:
        raise ContractError('experimental_assessment_saved_mismatch')
    if expected is not None:
        validate_assessment(expected, repository.experiment_types)
        row = repository.store.table(ASSESSMENTS).select({"sheet_ref": sheet_ref})[0]
        source = repository.store.get(row['sheet_ref'])
        for field in ('artifact_ref', 'request_ref'):
            raw = repository.store.get_artifact(source[field])
            if 'artifact_' + hashlib.sha256(raw).hexdigest() != source[field]:
                raise ContractError('experimental_assessment_artifact_mismatch')
        if row['assessment'] != expected:
            raise ContractError('experimental_assessment_saved_mismatch')
        if saved['experimental_bindings']['experiment_ref'] != expected['experiment_ref']:
            raise ContractError('experimental_assessment_experiment_mismatch')

def assessment_history(repository, sheet_ref):
    """Reconstruct revisions from saved results, without reading original data."""
    rows, seen, key = ([], set(), None)
    while sheet_ref is not None:
        if sheet_ref in seen:
            raise ContractError('experimental_assessment_revision_cycle')
        seen.add(sheet_ref)
        saved = repository.read(sheet_ref)
        value = saved.get('experiment_assessment')
        if value is None:
            raise ContractError('experimental_assessment_required')
        actual = (value['experiment_ref'], value['assessment_key'])
        if key is not None and actual != key:
            raise ContractError('experimental_assessment_predecessor_mismatch')
        key = actual
        rows.append({'sheet_ref': sheet_ref, **deepcopy(value)})
        sheet_ref = value['revises_sheet_ref']
    return list(reversed(rows))
