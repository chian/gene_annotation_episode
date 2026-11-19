"""The A103 investigation finding: controlled features that code reads from the A103 attachment sheets
(``a103_tool_attachment_v1``, written by ``records.gene_context_evidence.attachments.refresh``) and from the A103
credit projection (``A103ContextCredit``), with the references of the sheets. Numbers, counts, booleans, values of
fixed vocabularies and record references only; no model text (``INVESTIGATION_FINDING_FEATURES_a103.md``, the common
features and section A9).

The fields and their forms are declared here once (``ATTACHMENT_FORM``, ``FINDING_FORM``); an episode that returns the
finding declares them in its own ``final_to_parent.py`` by these forms. ``sheet_refs`` names every record a receiver's
A103 credit reads to count the graded measurement again under its own scope: the attachment source with its artifact
and grading artifact and its work-table row, the native measurement with the same, and the context observations the
grading published (a pass carries only the records named)."""
from __future__ import annotations

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.attachments import (
    ATTACHMENTS, received_attachments)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.publication import (
    PUBLICATIONS)

# Attachment policy -> evidence type (code maps the sheet's policy; the model never chooses it). The locus binding
# policy is an operand of the others, not an evidence type.
EVIDENCE_TYPES = {
    'recurrence_specific_loci_components_and_sampling_v1': 'conserved_neighborhood',
    'fusion_each_required_region_and_actual_coding_product_v1': 'gene_fusion',
    'enumerated_panel_actual_detections_and_declared_null_v1': 'phylogenetic_cooccurrence',
    'native_channel_exact_endpoints_and_specific_distance_v1': 'context_channel_association',
    'functional_contrast_matched_native_context_and_bounds_v1': 'context_contrast',
    'actual_neighborhood_and_specific_target_locus_v1': 'single_locus_organization',
}
EVIDENCE_TYPE_VALUES = tuple(EVIDENCE_TYPES.values())
ATTACHMENT_STATES = ('evaluated', 'partial', 'unresolved')
LINK_STATES = ('evaluated', 'unresolved', 'not_applicable')
ATTRIBUTION_STATES = ('no_received_context_association', 'unresolved_attribution', 'partial_attribution',
                      'attributed_context_received')

ATTACHMENT_FORM = RecordForm({
    'evidence_type': ChoiceField('text', 'The kind of gene-context evidence the sheet grades', EVIDENCE_TYPE_VALUES),
    'sheet_ref': Field('record_refs', 'The attachment sheet (exactly one reference)'),
    'measurement_ref': Field('record_refs', 'The native measurement the sheet grades (exactly one reference)'),
    'attachment_state': ChoiceField('text', 'Whether the attribution of the measurement to the target is evaluated, '
                                    'partial or unresolved', ATTACHMENT_STATES),
    'scored': Field('boolean', 'Whether the sheet carries a context association index'),
    'score_lower': Field('number', 'Lower bound of the context association index in [0, 1] (0 when not scored)'),
    'score_upper': Field('number', 'Upper bound of the context association index in [0, 1] (0 when not scored)'),
    'missing_count': Field('integer', 'The number of operands the sheet lists as missing'),
    'target_link_state': ChoiceField('text', "The state of the sheet's link of the measured locus to the target",
                                     LINK_STATES),
    'target_link_factor': Field('number', 'Fraction of matched residues weighted by native strength in [0, 1] (0 '
                                'unless the link is evaluated)'),
    'dependency_variant_ambiguous': Field('boolean', 'Whether conflicting variants of the same comparison are held'),
})
FINDING_FEATURES = {
    'attribution_state': ChoiceField('text', 'The least attributed state over the assigned targets',
                                     ATTRIBUTION_STATES),
    'source_contribution_count': Field('integer', 'Attached scored measurements counted by the credit'),
    'pending_measurement_count': Field('integer', 'Measurements whose sheets still list missing operands'),
    'ambiguous_variant_group_count': Field('integer', 'Comparisons held in conflicting variants'),
    'covered_fraction': Field('number', 'Fraction of the assigned length with a context value above 0'),
    **{name + '_count': Field('integer', 'Held graded sheets of evidence type ' + name)
       for name in EVIDENCE_TYPE_VALUES},
    'attachments': Field('list', 'One entry per held graded sheet', items=ATTACHMENT_FORM),
    'sheet_refs': Field('record_refs', 'Every record a receiver reads to count the graded measurements again'),
}
FINDING_FORM = RecordForm(FINDING_FEATURES)


def _source_closure(reader, reference):
    source = reader.get(reference)
    return [reference, source['artifact_ref'], *source.get('auxiliary_artifact_refs', ())]


def _attachment_features(row, ambiguous):
    link = row.get('target_link') or {}
    bounds = row.get('bounds') or ([row['score'], row['score']] if row.get('score') is not None else [0., 0.])
    return {
        'evidence_type': EVIDENCE_TYPES[row['policy']],
        'sheet_ref': [row['source_ref']],
        'measurement_ref': [row['measurement_ref']],
        'attachment_state': row['state'],
        'scored': row.get('score') is not None,
        'score_lower': float(bounds[0]),
        'score_upper': float(bounds[1]),
        'missing_count': len(row['missing']),
        'target_link_state': link.get('state', 'not_applicable'),
        'target_link_factor': float(link['factor']) if link.get('state') == 'evaluated' else 0.,
        'dependency_variant_ambiguous': row.get('dependency_group') in ambiguous,
    }


def context_finding(reader, credit_view, scope):
    """The finding of an Episode over the A103 sheets it holds: the episode-level features of its credit view (the
    target sheets of ``A103ContextCredit``) and one feature record per held attachment sheet of an evidence type,
    for targets of ``scope``; ``sheet_refs`` is what a receiver needs to read them."""
    targets = set(scope['subject_refs'])
    held = [row for row in received_attachments(reader, reader.refs())
            if row['target_ref'] in targets and row['policy'] in EVIDENCE_TYPES]
    variants = {}
    for row in held:
        if row.get('dependency_group') is not None:
            variants.setdefault(row['dependency_group'], set()).add(row['variant'])
    ambiguous = {key for key, values in variants.items() if len(values) > 1}
    attachments = [_attachment_features(row, ambiguous) for row in held]
    sheets = credit_view['target_sheets'].values()
    states = {sheet['status'] for sheet in sheets}
    assigned = sum(sheet['assigned_length'] for sheet in sheets)
    covered = sum(cell['end'] - cell['start'] for sheet in sheets for cell in sheet['cells'] if cell['value'] > 0)
    refs = []
    for row in held:
        refs += _source_closure(reader, row['source_ref'])
        refs += [item['id'] for item in reader.table(ATTACHMENTS).select({'source_ref': row['source_ref']})]
        refs += _source_closure(reader, row['measurement_ref'])
        refs += [item['id'] for item in reader.table(PUBLICATIONS).select({'source_ref': row['measurement_ref']})]
        refs += [item['id'] for item in reader.list('observation') if item['source_ref'] == row['source_ref']]
    return {
        'attribution_state': next(state for state in ATTRIBUTION_STATES if state in states),
        'source_contribution_count': credit_view['source_contribution_count'],
        'pending_measurement_count': len({ref for sheet in sheets for ref in sheet['pending_measurement_refs']}),
        'ambiguous_variant_group_count': len({group for sheet in sheets
                                              for group in sheet['unresolved_variant_groups']}),
        'covered_fraction': covered / assigned,
        **{name + '_count': sum(1 for item in attachments if item['evidence_type'] == name)
           for name in EVIDENCE_TYPE_VALUES},
        'attachments': attachments,
        'sheet_refs': list(dict.fromkeys(refs)),
    }


def ungraded_measurements(reader, scope):
    """The held native A103 measurements of the scope's targets that no held attachment sheet grades yet (the
    measurements a grading unit would attach)."""
    targets = set(scope['subject_refs'])
    graded = {row['measurement_ref'] for row in received_attachments(reader, reader.refs())}
    rows = [row for row in reader.table(PUBLICATIONS).select() if row['target_ref'] in targets]
    return sorted(row['source_ref'] for row in rows
                  if row['source_ref'] not in graded and reader.holds(row['source_ref']))
