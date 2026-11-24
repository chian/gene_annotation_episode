"""The A107 scoring sheet (``component_axis_scoring_sheet``), restored from ``component_axis_reports.py`` at
``60889621e`` (``current_scoring_sheets``, ``dependence``, ``native_dependence``, ``cross_dependence``, ``PATHS``) onto
what an Episode now holds: the controlled features of the literature partner sheets its children returned (with the
sheets' references), the native component records and the per-use tool qualification records it holds.

The sheet keeps three named component groups side by side and never reduces them to one axis number. Shared origins
across sheets, native components and the two together are recorded; a shared or unknown origin is never counted as
independent confirmation. Nothing here writes: it is read through the reader of the Episode that calls it.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement)

SCORING_SHEET_VERSION = 'component_axis_scoring_sheet'
# Owner's grading decision (row 11): the A107 sheet keeps five evidence paths apart.
PATHS = {'A107': ('requirement', 'presence', 'expression', 'coexpression', 'interaction')}


def dependence(reader, sheets):
    """Common origins of the literature sheets without summing or asserting independence (old ``dependence``): each
    sheet's own record, its saved artifact, the sources it was read from and the experiment it binds."""
    owners = {}
    for features in sheets:
        sheet_ref = features['sheet_refs'][0]
        source = reader.get(sheet_ref)
        origins = [('saved_sheet', sheet_ref), ('saved_artifact', source['artifact_ref'])]
        origins.extend(('source', reference) for reference in source['parent_source_refs'])
        origins.extend(('experiment', reference) for reference in features['experiment_refs'])
        for kind, identity in set(origins):
            owners.setdefault((kind, identity), set()).add(sheet_ref)
    # Owner's grading decision (row 10): a missing identity is unknown dependence, not independence, and a repeated
    # view of a sheet is not a new measurement.
    return {'shared_origins': [{'kind': kind, 'identity': identity, 'sheet_refs': sorted(references)}
                               for (kind, identity), references in sorted(owners.items()) if len(references) > 1],
            'missing_identity': 'unknown_dependence_not_independence',
            'numerical_ownership': 'original_sheet_ref_and_component; repeated_views_are_not_new_measurements'}


def native_dependence(rows):
    """Common origins of the native component records (old ``native_dependence``)."""
    origins = {}
    for row in rows:
        for kind, identity in (('input_bytes', row['input_file']['sha256']),
                               ('dataset', row['dependencies']['dataset_id']),
                               ('logical_native_measurement', row['logical_work_sha256']),
                               *[('source', reference) for reference in row['dependencies']['origin_source_refs']]):
            if identity is not None:
                origins.setdefault((kind, identity), set()).add(row['source_ref'])
    # Owner's grading decision (row 10): shared native and literature origins need scientific review; no automatic
    # independence.
    return {'shared_origins': [{'kind': kind, 'identity': identity, 'source_refs': sorted(refs)}
                               for (kind, identity), refs in sorted(origins.items()) if len(refs) > 1],
            'missing_dataset_identity': 'unknown_dependence_not_independence',
            'native_and_literature_views': 'shared_origins_require_scientific_review; no_automatic_independence'}


def cross_dependence(reader, sheets, native):
    """Sources shared by a literature sheet and a native component (old ``cross_dependence``)."""
    origins = {}
    for features in sheets:
        sheet_ref = features['sheet_refs'][0]
        for reference in reader.get(sheet_ref)['parent_source_refs']:
            origins.setdefault(reference, {'experimental_sheet_refs': set(), 'native_source_refs': set()})[
                'experimental_sheet_refs'].add(sheet_ref)
    for row in native:
        for reference in row['dependencies']['origin_source_refs']:
            origins.setdefault(reference, {'experimental_sheet_refs': set(), 'native_source_refs': set()})[
                'native_source_refs'].add(row['source_ref'])
    return {'shared_source_uses': [{'source_ref': reference,
                                    'experimental_sheet_refs': sorted(uses['experimental_sheet_refs']),
                                    'native_source_refs': sorted(uses['native_source_refs'])}
                                   for reference, uses in sorted(origins.items())
                                   if uses['experimental_sheet_refs'] and uses['native_source_refs']],
            'unmatched_or_missing_origins': 'unknown_dependence; not_independent_confirmation'}


def scoring_sheet(reader, sheets, native_components, qualifications):
    """The A107 scoring sheet of the Episode that holds these components (old ``current_scoring_sheets``): the
    literature partner sheets' features, the native components and the per-use qualifications as three separate
    named groups, their dependence, and no combined score. ``None`` when the Episode holds none of them."""
    if not sheets and not native_components and not qualifications:
        return None
    # Owner's grading decision (row 9): three separate named component groups; no axis reducer; unqualified uses stay
    # unknown and do not suppress the original scientific components.
    return {'version': SCORING_SHEET_VERSION, 'axis': 'A107', 'paths': list(PATHS['A107']),
            'numerical_results': list(sheets), 'numerical_agreement': agreement(sheets),
            'native_component_results': list(native_components),
            'tool_qualifications': list(qualifications),
            'dependencies': {**dependence(reader, sheets), 'native': native_dependence(native_components),
                             'cross_path': cross_dependence(reader, sheets, native_components)},
            'combined_scientific_score': None,
            'combination_status': 'separate_named_components; no_new_axis_reducer',
            'unqualified_uses': 'remain_unknown; do_not_suppress_the_original_scientific_components',
            'controller_progress': 'separate_from_this_scientific_scoring_sheet'}


def strongest_sheet(sheets):
    """The literature sheet the head returns as its finding (E1): among the sheets whose reference/omitted comparison
    is matched, the one with the largest partner loss fraction; else the first sheet; ``None`` without sheets. A
    choice made by code from the features, never a combination of them."""
    matched = [features for features in sheets if features['reference_omitted_check'] == 'matched'
               and 'partner_loss_fraction' in features]
    if matched:
        return max(matched, key=lambda features: features['partner_loss_fraction'])
    return sheets[0] if sheets else None
