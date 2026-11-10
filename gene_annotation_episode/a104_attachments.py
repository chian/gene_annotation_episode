"""Receipt-triggered attribution of each A104 test to its original target part."""
from __future__ import annotations

import json

from .a104_hpc import native_body, require
from .a104_publication import received_measurement
from .a104_scoring import VERSION, PROFILE, digest
from .domain import canonical
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER = 'native.a104.tool_attachment'


def install(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS a104_attachments (
        source_ref TEXT PRIMARY KEY, measurement_ref TEXT NOT NULL, target_ref TEXT NOT NULL,
        body TEXT NOT NULL, grading_artifact_ref TEXT NOT NULL)''')


def _qualify(store, measured, *, known, context, captured=()):
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
    if body['schema'] == 'a104_clade_composition_v1':
        from .a104_characterization import received_links, clade_sheet, exact_reference_correspondence
        links = received_links(store, context, known)
        # A returned host grade is itself received evidence. Preserve its
        # qualified facts without reading private upstream worksheet inputs.
        for previous in captured:
            sheet = previous.get('sheets', {}).get('reference_characterization')
            if sheet:
                links.extend(sheet['links'])
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
        measured_factor = sum(factors.get(subject, 0.) for subject in characterization['characterized_subject_refs']) / \
            len(body['characterization_subject_refs']) if body['characterization_subject_refs'] else 0.
        characterization['reference_transfer_factor'] = measured_factor
        characterization['transfer_policy'] = 'exact_native_MSA_identity_and_matched_extent_per_characterized_reference_v1'
        characterization['regional_assay_links_required'] = sorted(set(body['characterization_subject_refs'])-eligible)
        value = value*measured_factor if value is not None else None
    result = {'schema': 'a104_per_use_attribution_v1', 'version': VERSION, 'profile': PROFILE,
        'measurement_ref': measured['source_ref'], 'target_ref': body['target_ref'],
        'target_regions': regions, 'policy': body['producer_operation']+'_original_native_operands_v1',
        'score': value, 'raw_value': measured['grade']['raw_value'],
        'bounds': [value, measured['grade']['raw_value'] if characterization and missing else value]
                  if value is not None else [0., 1.],
        'state': 'attributed_phylogeny_received' if value is not None else 'unresolved_attribution',
        'missing': sorted(set(missing)), 'native_phylogeny_ref': body['native_phylogeny_ref'],
        'hpc_result_ref': body['hpc_result_ref'], 'request_ref': body['native_request_ref'],
        'variant_group': body.get('variant_group'), 'variant': body.get('variant'),
        **({'compared_variant_group': body['compared_variant_group'],
             'compared_variants': body['compared_variants']} if 'compared_variant_group' in body else {}),
        'qualification_dependencies': sorted(dependencies),
        'sheets': {'target_identity': {'original_target': body['target_ref'], 'original_regions': regions,
                                      'native_request_sha256': native['request_sha256']},
            'execution': {'pbs_job_id': body['pbs_job_id'], 'result_sha256': body['result_sha256']},
            'native_test': {'producer': body['producer_operation'], 'native_grade_ref': measured['grading_artifact_ref']},
            'functional_scope': {'status': body.get('function_status', 'unassessed'),
                                 'historical_cause': body.get('historical_cause', 'unassessed')}},
        'interpretation': 'this_tool_use_only; no_aggregate_A101_or_A105_multiplier'}
    if characterization is not None:
        result['sheets']['reference_characterization'] = characterization
    return result


def refresh(store, known, scope, *, context=None):
    install(store)
    generated, needs = [], []
    captured = received_attachments(store, known)
    for reference in sorted(known):
        measured = received_measurement(store, reference)
        if measured is None or measured['body']['target_ref'] not in scope['subject_refs']:
            continue
        body = _qualify(store, measured, known=known, context=context,
                        captured=[row for row in captured if row['measurement_ref'] == reference])
        with store.transaction():
            artifact = store.artifact(canonical(body), 'application/json')
            grading = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=artifact,
                grading={'grader': VERSION, 'failure': None, 'sheet': body})
            source = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
                'retrieved_at': None, 'operand_refs': [body['target_ref']], 'auxiliary_artifact_refs': [grading]}, origin='tool')['id']
            store.db.execute('INSERT OR IGNORE INTO a104_attachments VALUES(?,?,?,?,?)',
                (source, reference, body['target_ref'], canonical(body), grading))
        generated.append(source)
        if body['missing']:
            needs.append((reference, {'target_ref': body['target_ref'], 'policy': body['policy'],
                'missing': body['missing'], 'required_operands': {'native_phylogeny_ref': body['native_phylogeny_ref'],
                    'measurement_ref': reference, **({'reference_subject_refs':
                        body['sheets']['reference_characterization']['unknown_subject_refs']}
                        if 'reference_characterization' in body['sheets'] else {})}}))
    return sorted(set(generated)), needs


def received_attachments(store, known):
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a104_attachments'").fetchone()
    if not exists:
        return []
    result = []
    for reference in sorted(known):
        source = store.get(reference)
        if source['record_type'] != 'source' or source.get('provider') != PROVIDER:
            continue
        row = store.db.execute('SELECT * FROM a104_attachments WHERE source_ref=?', (reference,)).fetchone()
        require(row is not None and source['origin'] == 'tool', 'a104_attachment_host_grant_required')
        body = json.loads(row['body'])
        entries = source_tool_grading_entries(store, reference)
        require(json.loads(store.get_artifact(source['artifact_ref'])) == body and len(entries) == 1
                and entries[0]['artifact_ref'] == row['grading_artifact_ref']
                and entries[0]['grading'] == {'grader': VERSION, 'failure': None, 'sheet': body},
                'a104_attachment_custody_conflict')
        result.append({**body, 'source_ref': reference, 'grading_artifact_ref': row['grading_artifact_ref']})
    return result
