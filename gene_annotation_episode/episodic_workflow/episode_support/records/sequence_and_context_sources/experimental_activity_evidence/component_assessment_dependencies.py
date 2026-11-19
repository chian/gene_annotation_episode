"""Private A105 received-assessment identity and revision dependencies."""

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


