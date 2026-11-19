"""Receipt-triggered attribution of each A104 test to its original target part: the per-use attribution sheet.

Restored from ``root/a104/a104_attachments.py`` at ``60889621e`` (``_qualify``, ``refresh``): the owner's text and
logic, with the storage on the scoped store (the ``a104_attachments`` table is the declared work table of
``records/evolutionary_history_evidence/attachments.py``, whose ``received_attachments`` reads it back). The old
``context`` argument fed the characterization from received literature forms; the characterization now reads the
held A105 sheets (``characterization.py``). The ``historical_cause`` sub-sheet takes the held judged grade of
``history_explanation.py`` for the measurement when there is one. ``store`` is ``ctx.store``."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.attachments import (
    ATTACHMENTS, PROVIDER, received_attachments)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import native_body, require
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import VERSION, PROFILE, digest
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.native_publications import received_measurement
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.history_explanation import held_explanations
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.tool_grading_artifacts import retain_tool_grading


def _historical_cause(body, explanation):
    if explanation is not None:
        return {**explanation['cell'], 'explanation_ref': explanation['source_ref']}
    return body['historical_cause'] if body['schema'] == 'a104_history_comparison_v1' else 'unassessed'


def _qualify(store, measured, *, known, explanation=None, captured=()):
    body = measured['body']
    native = native_body(store, body['native_phylogeny_ref'])
    require(native is not None and native['target_ref'] == body['target_ref'], 'a104_native_target_binding_conflict')
    regions = body['target_regions']
    require(regions and all(type(a) is int and type(b) is int and 0 <= a < b <= store.subject_length(body['target_ref'])
                           for a, b in regions), 'a104_original_target_region_required')
    missing = []
    if measured['grade']['raw_value'] is None:
        missing.append('native_evaluable_support_or_relationship')
    value = measured['grade']['raw_value']
    characterization = None
    dependencies = {measured['source_ref']}
    if explanation is not None:
        dependencies.add(explanation['source_ref'])
    if body['schema'] == 'a104_clade_composition_v1':
        from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.characterization import (
            received_links, clade_sheet, exact_reference_correspondence)
        links = received_links(store, known)
        # A returned host grade is itself received evidence. Preserve its
        # qualified facts without reading private upstream worksheet inputs.
        for previous in captured:
            if 'reference_characterization' in previous['sheets']:
                links.extend(previous['sheets']['reference_characterization']['links'])
        # A whole-protein assay cannot identify a selected subregion's activity.
        # A directly assayed feature can qualify its own complete feature span.
        eligible = {subject for subject, part in body['required_reference_parts'].items()
                    if part['regions'] == [[0, part['full_length']]]}
        links = exact_reference_correspondence(store, eligible, links, known)
        links = [row for row in links if row['reference_ref'] in eligible]
        characterization = clade_sheet(set(body['characterization_subject_refs']), links)
        dependencies.update(characterization['evidence_refs'])
        if characterization['unknown_subject_refs']:
            missing.append('A105_reference_activity_and_exact_assayed_subject_links')
        factors = {row['reference_ref']: row['identity_extent_factor'] for row in body['reference_correspondences']}
        # A clade test's score is scaled by the native MSA identity and matched extent of each characterized reference.
        measured_factor = sum(factors[subject] if subject in factors else 0.
                              for subject in characterization['characterized_subject_refs']) / \
            len(body['characterization_subject_refs']) if body['characterization_subject_refs'] else 0.
        characterization['reference_transfer_factor'] = measured_factor
        characterization['transfer_policy'] = 'exact_native_MSA_identity_and_matched_extent_per_characterized_reference_v1'
        characterization['regional_assay_links_required'] = sorted(set(body['characterization_subject_refs'])-eligible)
        value = value*measured_factor if value is not None else None
    result = {'schema': 'a104_per_use_attribution_v1', 'version': VERSION, 'profile': PROFILE,
        'measurement_ref': measured['source_ref'], 'target_ref': body['target_ref'],
        'target_regions': regions, 'policy': body['producer_operation']+'_original_native_operands_v1',
        'score': value, 'raw_value': measured['grade']['raw_value'],
        # Uncharacterized members widen the bounds and are recorded as a missing A105 link.
        'bounds': [value, measured['grade']['raw_value'] if characterization and missing else value]
                  if value is not None else [0., 1.],
        'state': 'attributed_phylogeny_received' if value is not None else 'unresolved_attribution',
        'missing': sorted(set(missing)), 'native_phylogeny_ref': body['native_phylogeny_ref'],
        'hpc_result_ref': body['hpc_result_ref'], 'request_ref': body['native_request_ref'],
        # The same test repeated is one variant group.
        'variant_group': body['variant_group'], 'variant': body['variant'],
        **({'compared_variant_group': body['compared_variant_group'],
             'compared_variants': body['compared_variants']} if 'compared_variant_group' in body else {}),
        'qualification_dependencies': sorted(dependencies),
        # Target identity, execution, native test, functional scope and historical cause stay separate sub-sheets.
        'sheets': {'target_identity': {'original_target': body['target_ref'], 'original_regions': regions,
                                      'native_request_sha256': native['request_sha256']},
            'execution': {'pbs_job_id': body['pbs_job_id'], 'result_sha256': body['result_sha256']},
            'native_test': {'producer': body['producer_operation'], 'native_grade_ref': measured['grading_artifact_ref']},
            'functional_scope': {'status': body['function_status'],
                                 'historical_cause': _historical_cause(body, explanation)}},
        'interpretation': 'this_tool_use_only; no_aggregate_A101_or_A105_multiplier'}
    if characterization is not None:
        result['sheets']['reference_characterization'] = characterization
    return result


def refresh(store, known, scope):
    """Attribute every held native measurement of the scope again from what is held now: a late receipt (an A105
    sheet, a judged historical cause) yields a new immutable attribution sheet."""
    known = set(known)
    generated, needs = [], []
    captured = received_attachments(store, known)
    explanations = held_explanations(store, known)
    for reference in sorted(known):
        measured = received_measurement(store, reference)
        if measured is None or measured['body']['target_ref'] not in scope['subject_refs']:
            continue
        body = _qualify(store, measured, known=known, explanation=explanations.get(reference),
                        captured=[row for row in captured if row['measurement_ref'] == reference])
        with store.transaction():
            artifact = store.artifact(canonical(body), 'application/json')
            grading = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=artifact,
                grading={'grader': VERSION, 'failure': None, 'sheet': body})
            source = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
                'retrieved_at': None, 'operand_refs': [body['target_ref']], 'auxiliary_artifact_refs': [grading]}, origin='tool')['id']
            store.table(ATTACHMENTS).put({'source_ref': source, 'body': body, 'grading_artifact_ref': grading})
        generated.append(source)
        if body['missing']:
            needs.append({'measurement_ref': reference, 'target_ref': body['target_ref'], 'policy': body['policy'],
                'missing': body['missing'], 'required_operands': {'native_phylogeny_ref': body['native_phylogeny_ref'],
                    'measurement_ref': reference, **({'reference_subject_refs':
                        body['sheets']['reference_characterization']['unknown_subject_refs']}
                        if 'reference_characterization' in body['sheets'] else {})}})
    return sorted(set(generated)), needs
