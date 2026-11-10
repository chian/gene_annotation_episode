"""Received assessment identity, extent and revisions for scientific evidence uses.

An immutable assessment body cannot reveal a later revision by changing its
digest. Retain the original use and identify received corrections separately;
never substitute a newer claim or inspect an unreceived assessment.
"""
from copy import deepcopy


VERSION = 'received_component_assessment_dependencies_v1'


def assessment_dependencies(store, reference, known, *, anchor=None):
    known = set(known)
    if reference in known:
        original = store.get(reference)
        if original['record_type'] != 'assessment':
            raise ValueError('component_source_assessment_required')
        key, revision = store.assessment_key(original), original['revision']
        status = (original.get('investigation_finding') or {}).get('status')
    elif anchor is not None and anchor.get('assessment_ref') == reference:
        # Only callers reading an authenticated saved qualification supply
        # this anchor. Its original identity is already part of that result.
        key, revision = anchor['assessment_key_ref'], anchor['assessment_revision']
        status = anchor['original_finding_status']
    else:
        return None
    latest = {}
    for ref in sorted(known):
        row = store.get(ref)
        if row['record_type'] == 'assessment':
            row_key = store.assessment_key(row)
            if row_key not in latest or row['revision'] > latest[row_key]['revision']:
                latest[row_key] = row
    superseding = ([latest[key]['id']] if key in latest
        and latest[key]['revision'] > revision else [])
    # Current received correction chains may cross assessment keys. Resolve
    # their explicit edges without imposing a chain-length or action limit.
    retired, replacements = {reference}, set()
    while True:
        additions = {row['id'] for row in latest.values()
            if retired.intersection((row.get('investigation_finding') or {}).get('replaces_refs', []))}
        additions.difference_update(retired)
        if not additions:
            break
        replacements.update(additions)
        retired.update(additions)
    return {'version': VERSION, 'assessment_ref': reference,
        'assessment_key_ref': key, 'assessment_revision': revision,
        'original_finding_status': status,
        'superseding_assessment_refs': superseding,
        'replacement_refs': sorted(replacements),
        'retired': status == 'withdrawn' or bool(superseding or replacements),
        'scope': 'received_assessment_revisions_and_explicit_corrections_only'}


def correction_refs(dependency):
    return set(dependency['superseding_assessment_refs']) | set(dependency['replacement_refs'])


def qualification_assessment_changes(store, qualification, known):
    result = qualification['result']
    finding = result.get('source_function_finding')
    if finding is None and qualification.get('operation') == 'partner.requirement_evidence':
        finding = result
    if not finding or finding.get('assessment_ref') is None:
        return []
    dependency = assessment_dependencies(store, finding['assessment_ref'], known,
        anchor=deepcopy(finding.get('assessment_revision_dependency')))
    if dependency is None:
        return []  # Historical result without an admitted original identity.
    return sorted(correction_refs(dependency) - set(qualification['qualification_dependencies']))


def annotation_assessments(store, known_record_refs, annotation, subject, scope):
    """Current received assessment links, including explicit invalidations.

    The scientific owner selects its measurements and decides which directions
    contribute. This lookup supplies identities, dependencies and exact extent.
    """
    from .evidence_geometry import native_regions_for_footprint, native_subject_regions, _intersection
    known = set(known_record_refs)
    available = known | set(store.problem()['subject_refs'])
    rows = []
    for assessment in store.current_assessment_subset(known).values():
        if assessment['hypothesis_ref'] != annotation['id']:
            continue
        observation_ref = assessment['observation_ref']
        if observation_ref not in known:
            continue  # An unreceived observation cannot identify an axis measurement.
        observation = store.get(observation_ref)
        if subject not in observation['subject_refs'] or observation['origin'] not in {'tool', 'extracted'}:
            continue
        finding = assessment.get('investigation_finding')
        qualification = finding['qualification'] if finding else None
        conditions = set(assessment['condition_refs']) | set((qualification or {}).get('context_refs', ()))
        assumptions = set(assessment['assumption_refs']) | set((qualification or {}).get('assumption_refs', ()))
        required = {observation['source_ref'], *observation.get('dependencies', ()),
            *observation.get('source_subject_refs', ()), *annotation['context_refs'], *conditions, *assumptions}
        needed = sorted(required - available)
        dependency = assessment_dependencies(store, assessment['id'], known)
        status, missing = 'established', []
        if finding and finding['status'] == 'withdrawn':
            status, missing = 'withdrawn', ['assessment_withdrawn']
        elif dependency is None or dependency['retired']:
            status, missing = 'unresolved', ['assessment_not_current']
        elif assessment['applicability'] == 'incomparable':
            status, missing = 'invalid', ['assessment_explicitly_incomparable']
        elif needed:
            status, missing = 'unresolved', ['assessment_dependencies_not_received']
        extent = store._assessment_write_extent(assessment)
        regions = (_intersection(native_regions_for_footprint(store, subject, extent),
            native_subject_regions(store, scope, (subject,)).get(subject, [])) if extent else [])
        if status == 'established' and (not regions or assessment['extent_basis'] == 'context_allocation'):
            status, missing = 'unresolved', ['assessment_native_extent_unavailable']
        rows.append({'assessment_ref': assessment['id'], 'observation': observation,
            'relation': assessment['relation'], 'applicability': assessment['applicability'],
            'regions': regions, 'original_extent': extent, 'condition_refs': sorted(conditions),
            'assumption_refs': sorted(assumptions), 'qualification': qualification,
            'transfer_status': status, 'missing_inputs': missing, 'needed_refs': needed})
    return rows


def assigned_annotation(store, known_record_refs, assignment):
    """Resolve the existing original assignment without granting unseen records."""
    reference = (assignment or {}).get('proposed_annotation_ref')
    if reference is None:
        return None
    known = set(known_record_refs)
    if reference not in known:
        raise ValueError('assigned_proposed_annotation_not_received')
    annotation = store.get(reference)
    if annotation['record_type'] != 'hypothesis':
        raise ValueError('assigned_proposed_annotation_required')
    if not set(annotation['subject_refs']) <= known | set(store.problem()['subject_refs']):
        raise ValueError('assigned_annotation_subject_not_received')
    return annotation


def assessment_transfer(rows, *, missing=()):
    """Summarize declared links without turning absence into invalidation."""
    states = {row['transfer_status'] for row in rows}
    status = ('established' if 'established' in states else
        'withdrawn' if states == {'withdrawn'} else 'invalid' if states == {'invalid'} else 'unresolved')
    return {'status': status,
        'missing_inputs': sorted(set(missing) | {reason for row in rows for reason in row['missing_inputs']}),
        'needed_refs': sorted({ref for row in rows for ref in row['needed_refs']}),
        'link_refs': sorted({row['assessment_ref'] for row in rows}),
        'owner_states': sorted(states)}


def assessment_details(rows, references):
    selected = set(references)
    return [{key: row[key] for key in ('assessment_ref', 'condition_refs', 'assumption_refs',
        'qualification', 'applicability', 'relation')} for row in rows if row['assessment_ref'] in selected]


def qualification_annotation(store, context, result):
    """Resolve the question declared by an admitted qualification only."""
    if result.get('assessment_hypothesis_ref') is not None:
        return result['assessment_hypothesis_ref']
    reference = result.get('assessment_ref') or (result.get('source_function_finding') or {}).get('assessment_ref')
    return store.get(reference)['hypothesis_ref'] if reference in context.received_record_refs else None
