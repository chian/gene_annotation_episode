"""Original native subject/footprint mapping private to root aggregation."""

def _merge(segments):
    result = []
    for start, end in sorted(segments):
        if start == end:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def native_regions_for_footprint(store, subject_ref, footprint):
    """Map an original-input footprint back to complete native subject symbols.

    Native amino-acid positions remain distinct from their nucleotide footprint.
    Only exact recorded sequence mappings are used, including reverse strands,
    compound paths and codons split across path segments.
    """
    if not store.has_exact_mapping(subject_ref):
        return []
    mapping = store.sequence_mapping(subject_ref)
    scale, offset, covered = mapping['units_per_symbol'], 0, []
    for part in mapping['path']:
        original = store.get(part['subject_ref'])
        target = original.get('library_ref', part['subject_ref'])
        member = original.get('member_ref')
        for span in footprint:
            if (span['target_ref'] != target or span.get('member_ref') != member
                    or span['unit'] != part['unit']):
                continue
            start, end = max(part['start'], span['start']), min(part['end'], span['end'])
            if start < end:
                left, right = ((start - part['start'], end - part['start']) if part['strand'] == '+'
                    else (part['end'] - end, part['end'] - start))
                covered.append((offset + left, offset + right))
        offset += part['end'] - part['start']
    return [[(start + scale - 1) // scale, end // scale] for start, end in _merge(covered)
        if (start + scale - 1) // scale < end // scale]


def native_subject_regions(store, scope, subjects):
    """Select native subjects inside an unchanged original-input scope."""
    if (isinstance(subjects, (str, bytes, dict)) or not subjects
            or len(set(subjects)) != len(subjects)):
        raise ValueError('explicit_unique_native_subjects_required')
    footprint = store.scope_coverage(scope)
    return {subject: regions for subject in subjects
        if (regions := native_regions_for_footprint(store, subject, footprint))}


