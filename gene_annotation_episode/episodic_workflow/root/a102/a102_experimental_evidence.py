"""Receipt-bound A102 view over the existing experimental structure sheets.

No source is fetched, model parsed, job launched or scientific value recalculated
here. Numerical possession is checked by the existing literature repository.
"""
from copy import deepcopy
import json

from .a102_structural_evidence import VERSION
from .communication import plain
from .domain import ContractError
from .literature_structure_storage import LiteratureStructureRepository


def _model_identity(metadata):
    if metadata is None:
        return None
    # Raw validation XML attributes can contain additional measured quantities.
    # Keep identity metadata here; only the delivered cells carry numbers from
    # the scientific sheet. Original sources remain available through their
    # own separately authorized reading operations.
    return {key: deepcopy(metadata[key]) for key in ('entry_id', 'revision_number',
        'revision_date', 'method', 'model_numbers', 'coordinate_unit',
        'creation_date', 'schema_location', 'source_ref', 'artifact_ref') if key in metadata}


def _source_identity(store, reference):
    """Keep acquisition custody without opening the original scientific bytes."""
    source = store.get(reference)
    return {'source_ref': reference, **{key: deepcopy(source.get(key)) for key in (
        'provider', 'accession', 'uri', 'artifact_ref', 'request_ref', 'version',
        'retrieved_at', 'parent_source_refs')}}


def experimental_evidence(repository, context, cells):
    """Expose exactly the receiver's admitted numerical subset and its identity.

    The injected repository is the already configured application service.
    Knowing a sheet reference does not grant its undelivered components.
    """
    if not isinstance(repository, LiteratureStructureRepository):
        raise TypeError('a102_structure_repository_required')
    if repository.run_id != context.run_id:
        raise ContractError('a102_experimental_run_mismatch')
    cells = plain(cells)
    repository.validate_fact_values(context, cells)
    grouped = {}
    for row in cells:
        grouped.setdefault(row['sheet_ref'], []).append(deepcopy(row))
    results = []
    for ref, rows in grouped.items():
        saved = repository.read(ref)
        extraction = saved['extraction']
        coordinate = _model_identity(extraction['coordinate_metadata'])
        validation = _model_identity(extraction['validation_metadata'])
        assessment = deepcopy(saved.get('experiment_assessment'))
        sheet_source = repository.store.get(ref)
        request = json.loads(repository.store.get_artifact(sheet_source['request_ref']))
        results.append({'sheet_ref': ref, 'calculation_version': saved['sheet']['version'],
            'record_version': saved['version'],
            'numerical_identity': 'original_sheet_ref_and_component; no_new_A102_measurement',
            'assessment_scope': deepcopy(request['scope']), 'receiving_scope': plain(context.scope),
            'experimental_bindings': deepcopy(saved['experimental_bindings']),
            'assessment': assessment,
            'assessment_state': 'retained' if assessment else 'legacy_unlinked',
            'coordinate_identity': coordinate, 'validation_identity': validation,
            'source_refs': list(saved['input_source_refs']),
            'direct_source_refs': list(saved['direct_input_source_refs']),
            'acquisition_provenance': [_source_identity(repository.store, source)
                for source in saved['input_source_refs']],
            'source_artifact_ref': saved['input_artifact_ref'],
            'saved_sheet_artifact_ref': sheet_source['artifact_ref'],
            'population_request_ref': sheet_source['request_ref'],
            'selection': {key: deepcopy(rows[0][key]) for key in (
                'model_number', 'geometry_definition', 'local_validation_definition')},
            'local_validation': {'source_ref': saved['validation_source_ref'],
                'granularity': rows[0]['local_validation_granularity'], 'native_metric': 'RSCC',
                'native_unit': 'dimensionless',
                'members': [{'selector': deepcopy(member['selector']),
                    'unavailable_reason': member['unavailable_reason'],
                    'native_value_location': {'artifact_ref': sheet_source['artifact_ref'],
                        'json_pointer': f'/extraction/native_local/{index}/rscc'}}
                    for index, member in enumerate(extraction['native_local'])],
                'native_value_access': 'separately_authorized_source_read; not_additional_delivered_cells'},
            'geometry_missing_reasons': [member['unavailable_reason']
                for member in extraction['calculation_inputs']['geometry_members']],
            'cells': rows,
            'validation_binding': rows[0]['validation_binding'],
            'target_transfer': 'not_established_by_source_geometry',
            'independence': 'not_inferred',
            'revision_scope': 'delivered_assessments_only'})
    by_ref = {row['sheet_ref']: row for row in results}
    for result in results:
        assessment = result['assessment']
        if assessment is None:
            continue
        predecessor = assessment['revises_sheet_ref']
        if predecessor is not None:
            if predecessor in by_ref:
                by_ref[predecessor]['assessment_state'] = 'superseded_in_return'
            else:
                result['revision_scope'] = 'predecessor_not_in_return'
    heads = {}
    for result in results:
        assessment = result['assessment']
        if assessment is not None and result['assessment_state'] != 'superseded_in_return':
            key = (assessment['experiment_ref'], assessment['assessment_key'])
            heads.setdefault(key, []).append(result)
    for alternatives in heads.values():
        if len(alternatives) > 1:
            for result in alternatives:
                result['assessment_state'] = 'unresolved_revision_heads_in_return'
    return {'version': VERSION, 'records': results,
        'combination': 'separate_conditional_components_no_joint_scalar',
        'target_transfer': 'requires_separate_subject_correspondence_and_claim_assessment'}


def dependency_links(experimental, comparisons, attachments=()):
    """Describe shared identities without claiming unlinked uses independent.

    Shared source provenance and shared coordinates are labelled separately
    from experiment identity. A common paper can describe several experiments.
    Distinct questions/results survive; this function performs no aggregation.
    """
    uses, owners = [], {}

    def retain(path, reference, identities):
        use = {'path': path, 'record_ref': reference}
        uses.append(use)
        for kind, identity in set([('measurement_record', reference), *identities]):
            if identity is not None:
                owners.setdefault((kind, identity), []).append(use)

    for result in experimental['records']:
        model = result['coordinate_identity']
        identities = [('source', ref) for ref in result['source_refs']]
        # Only the explicit assessment identity is shared experiment authority.
        # Legacy literal bindings are preserved but may name a representation.
        if result['assessment'] is not None:
            identities.append(('experiment', result['assessment']['experiment_ref']))
        if model:
            artifact = model.get('artifact_ref')
            if isinstance(artifact, str) and artifact.startswith('artifact_'):
                identities.append(('coordinate_file_sha256', artifact[len('artifact_'):]))
            entry = model.get('entry_id')
            if entry is not None:
                identities.append(('deposited_entry', entry))
            if entry is not None and all(model.get(key) is not None
                    for key in ('revision_number', 'revision_date')):
                identities.append(('deposited_revision',
                    json.dumps([entry, model['revision_number'], model['revision_date']])))
        retain('experimental', result['sheet_ref'], identities)
    for comparison in comparisons:
        grade = comparison['grade']
        identities = []
        for side in ('target', 'reference'):
            digest = grade.get(f'{side}_structure_sha256')
            if digest is not None:
                identities.append(('coordinate_file_sha256', digest))
            identities.extend(('source', ref)
                for ref in grade.get(f'{side}_model', {}).get('origin_witness_refs', ()))
        identities.extend(('structural_binding', grade[key])
            for key in ('target_binding_ref', 'reference_ref') if grade.get(key) is not None)
        retain('comparative', comparison['source_ref'], identities)
    for attachment in attachments:
        identities = [('source', ref) for ref in attachment.get('evidence_refs', ())
            if ref.startswith('source_')]
        identities.extend(('structural_binding', ref)
            for ref in attachment.get('actual_subject_refs', ()))
        if attachment.get('measurement_ref') is not None:
            identities.append(('measurement_record', attachment['measurement_ref']))
        retain('comparative_attachment', attachment['source_ref'], identities)
    return {'uses': uses, 'shared_identities': [
        {'kind': kind, 'identity': identity, 'uses': values}
        for (kind, identity), values in sorted(owners.items()) if len(values) > 1],
        'unlinked_uses': 'dependence_unresolved_not_independent',
        'aggregation': 'none; retain component meanings and shared measurement ownership'}
