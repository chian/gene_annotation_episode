"""The A104 investigation finding: controlled features that code reads from the saved A104 sheets, each with its
validator (``INVESTIGATION_FINDING_FEATURES_a104.md``, sections 1 to 4 and 7).

One entry per held native measurement (its latest per-use attribution sheet, as the credit selects it): the
evidence type of the measurement's kind and the type-specific lines P (placement), H (history comparison), C
(characterized clade), R (placement robustness) and X (the judged historical-cause cell), plus the references of the
sheet's records so that a receiver holds the sheet. Per target: the lines V of the credit view. No model-written
text: numbers, counts, booleans, fixed vocabularies and record references only. A value a sheet leaves unevaluable
(``None``) is absent from the entry, never 0. ``reader`` is ``ctx.store`` or ``records``."""
from __future__ import annotations

import math

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.attachments import (
    ATTACHMENTS, received_attachments)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import native_body
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.native_publications import (
    PUBLICATIONS, received_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import (
    relationship_inventory)
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.history_explanation import (
    EXPLANATIONS, LEVELS)

EVIDENCE_TYPES = {'a104_placement': 'clade_placement', 'a104_history_comparison': 'history_comparison',
                  'a104_clade_composition': 'characterized_clade', 'a104_robustness': 'placement_robustness'}
CLADE_STATUSES = ('function_identity_mapping_unresolved', 'mixed_characterized_functions', 'uncharacterized',
                  'partially_characterized', 'uniform_observed_activity_in_sampled_references')
ATTRIBUTION_STATUSES = ('attributed_phylogeny_received', 'unresolved_attribution',
                        'no_received_native_phylogeny_test')

# name -> (validator, meaning). Validators: ('number', low, high), ('count',), ('choice', options), ('boolean',),
# ('refs',). Every sheet feature but ``evidence_type`` and ``sheet_refs`` is present only for its kind and only
# when the sheet evaluates it.
SHEET_FEATURES = {
    'evidence_type': (('choice', tuple(EVIDENCE_TYPES.values())), 'The A104 evidence type of the measurement'),
    'sheet_refs': (('refs',), 'The records of the saved sheet: the attribution sheet, the native measurement, '
                              'their artifacts, grading artifacts and table rows'),
    'attribution_state': (('choice', ATTRIBUTION_STATUSES[:2]), 'Whether the use is attributed or unresolved'),
    'attributed_score': (('number', 0, 1), 'The per-use attribution score, unit interval'),
    'attributed_lower': (('number', 0, 1), 'Lower bound of the per-use attribution score'),
    'attributed_upper': (('number', 0, 1), 'Upper bound of the per-use attribution score'),
    'missing_input_count': (('count',), 'Inputs the attribution records as missing'),
    'bootstrap_support': (('number', 0, 1), 'P1: fraction of bootstrap replicates supporting the split'),
    'bootstrap_matches': (('count',), 'P2: supporting bootstrap replicates'),
    'bootstrap_replicates': (('count',), 'P3: bootstrap replicates'),
    'support_kind': (('choice', ('bootstrap_fraction', 'clade_posterior_probability')),
                     'P4: the kind of the native support statistic'),
    'analysis_purpose': (('choice', ('family', 'regional', 'sensitivity')), 'P5: purpose of the measured analysis'),
    'clade_size': (('count',), 'P6: tips on the target side of the split, target included'),
    'panel_size': (('count',), 'P7: members of the analysed panel'),
    'target_region_length': (('count',), 'P8: residues of the original target regions'),
    'nearest_clade_patristic_distance': (('number', 0, math.inf),
                                         'P9: smallest patristic distance from the target to a clade member, '
                                         'expected substitutions per site'),
    'nearest_clade_observed_identity': (('number', 0, 1), 'P10: identity of aligned pairs with that member'),
    'nearest_clade_query_coverage': (('number', 0, 1), 'P11: fraction of target residues aligned to that member'),
    'nearest_clade_aligned_pairs': (('count',), 'P12: aligned residue pairs with that member'),
    'analyses_agreeing': (('count',), 'P13: analyses in which the same physical relationship occurs'),
    'competing_configuration': (('boolean',), 'P14: other configurations of the same test disagree'),
    'comparison_reliability': (('number', 0, 1), 'H1: mean bootstrap reliability of the comparison'),
    'gene_tree_reliability': (('number', 0, 1), 'H2: mean bootstrap reliability of the gene tree splits'),
    'organismal_tree_reliability': (('number', 0, 1), 'H3: mean bootstrap reliability of the organismal splits'),
    'shared_taxon_count': (('count',), 'H4: taxa compared'),
    'gene_split_count': (('count',), 'H5: restricted gene-tree splits'),
    'organismal_split_count': (('count',), 'H6: restricted organismal-tree splits'),
    'organismal_marker_count': (('count',), 'H7: organismal markers'),
    'shared_split_count': (('count',), 'H8: splits shared by both trees'),
    'robinson_foulds_distance': (('count',), 'H8: unrooted Robinson-Foulds distance between the trees'),
    'characterized_count': (('count',), 'C: clade members characterized by received A105 sheets'),
    'uncharacterized_count': (('count',), 'C: clade members without a received characterization'),
    'characterized_fraction': (('number', 0, 1), 'C: fraction of clade members characterized'),
    'independent_assay_observation_count': (('count',), 'C: independent assay observations'),
    'clade_characterization_status': (('choice', CLADE_STATUSES), 'C: the characterization status of the clade'),
    'compared_analysis_count': (('count',), 'R: placement analyses compared'),
    'stability_numerator': (('count',), 'R: reference members common to every compared placement'),
    'stability_denominator': (('count',), 'R: reference members in any compared placement'),
    'historical_cause_grade': (('choice', LEVELS), 'X: the judged grade of a horizontal-transfer explanation'),
    'historical_cause_score': (('count',), 'X: its ordinal rubric level (0, 1 or 2), absent when unknown'),
    'historical_cause_lower': (('count',), 'X: lower possible rubric level'),
    'historical_cause_upper': (('count',), 'X: upper possible rubric level'),
}
TARGET_FEATURES = {
    'target_refs': (('refs',), 'The target'),
    'attribution_status': (('choice', ATTRIBUTION_STATUSES), 'F1: attribution status of the target'),
    'placement_max': (('number', 0, 1), 'F2: highest placement value over the target cells'),
    'history_comparison_max': (('number', 0, 1), 'F3: highest history-comparison value over the target cells'),
    'characterized_clade_max': (('number', 0, 1), 'F4: highest characterized-clade value over the target cells'),
    'supported_length': (('count',), 'F5: residues with any native dimension above zero'),
    'assigned_length': (('count',), 'F6: residues assigned'),
    'pending_measurement_count': (('count',), 'F8: measurements whose attribution misses inputs'),
    'competing_configuration_count': (('count',), 'F9: variant groups whose configurations disagree'),
}


def valid(rule, value):
    if rule[0] == 'number':
        return type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
    if rule[0] == 'count':
        return type(value) is int and value >= 0
    if rule[0] == 'choice':
        return value in rule[1]
    if rule[0] == 'boolean':
        return type(value) is bool
    return type(value) is list and all(type(ref) is str and ref for ref in value) and len(set(value)) == len(value)


def validate(features, table, required):
    """Each feature against its validator; an unknown or missing required feature or an invalid value raises."""
    unknown = set(features) - set(table)
    if unknown or not set(required) <= set(features):
        raise ValueError('a104_finding_features_mismatch:' + ','.join(sorted(unknown)))
    for name, value in features.items():
        if not valid(table[name][0], value):
            raise ValueError('a104_finding_feature_invalid:' + name)
    return features


def _present(**values):
    return {name: value for name, value in values.items() if value is not None}


def _current(attachments):
    """The credit's rule: a sheet superseded by one with encompassing qualification inputs is not current."""
    return [row for row in attachments if not any(
        other['measurement_ref'] == row['measurement_ref']
        and set(row['qualification_dependencies']) < set(other['qualification_dependencies'])
        for other in attachments)]


def _row_ref(reader, declaration, source_ref):
    return reader.table(declaration).select({'source_ref': source_ref})[-1]['id']


def sheet_records(reader, attachment):
    """The records a receiver must hold to read the sheet again (the attribution and the measurement with their
    artifacts, grading artifacts and rows; the judged historical cause when there is one)."""
    refs = []
    for source_ref, declaration in ((attachment['source_ref'], ATTACHMENTS),
                                    (attachment['measurement_ref'], PUBLICATIONS)):
        source = reader.get(source_ref)
        refs.extend([source_ref, source['artifact_ref'], *source['auxiliary_artifact_refs'],
                     _row_ref(reader, declaration, source_ref)])
    cause = attachment['sheets']['functional_scope']['historical_cause']
    if isinstance(cause, dict):
        source = reader.get(cause['explanation_ref'])
        refs.extend([cause['explanation_ref'], source['artifact_ref'],
                     _row_ref(reader, EXPLANATIONS, cause['explanation_ref'])])
    return list(dict.fromkeys(refs))


def _placement(reader, body, competing):
    native = native_body(reader, body['native_phylogeny_ref'])
    binding = next(row for row in native['bindings'] if row['name'] == body['analysis'])
    side = set(body['target_side_tip_ids'])
    nearest = min((row for row in body['reference_correspondences'] if row['tip_id'] in side),
                  key=lambda row: row['patristic_distance'])
    agreeing = [len({item['analysis'] for item in row['occurrences']}) for row in relationship_inventory(native)
                if any(item['analysis'] == body['analysis'] and item['split_index'] == body['split_index']
                       for item in row['occurrences'])]
    return _present(
        bootstrap_support=body['raw_value'], bootstrap_matches=body['bootstrap_population']['matches'],
        bootstrap_replicates=body['bootstrap_population']['denominator'], support_kind=body['support_kind'],
        analysis_purpose=binding['purpose'], clade_size=len(body['target_side_tip_ids']),
        panel_size=len(body['reference_panel_members']),
        target_region_length=sum(end - start for start, end in body['target_regions']),
        nearest_clade_patristic_distance=nearest['patristic_distance'],
        nearest_clade_observed_identity=nearest['observed_identity'],
        nearest_clade_query_coverage=nearest['query_coverage'],
        nearest_clade_aligned_pairs=nearest['aligned_residue_pairs'],
        analyses_agreeing=agreeing[0] if agreeing else 1,
        competing_configuration=body['variant_group'] in competing)


def _history(body):
    comparison = body['comparison']
    return _present(
        comparison_reliability=body['raw_value'],
        gene_tree_reliability=body['native_relationship_reliability']['family'],
        organismal_tree_reliability=body['native_relationship_reliability']['organismal_reference'],
        shared_taxon_count=len(body['selected_tip_ids']), gene_split_count=comparison['gene_splits']['value'],
        organismal_split_count=comparison['organismal_splits']['value'],
        organismal_marker_count=len(body['organismal_basis']['markers']),
        shared_split_count=comparison['shared_splits']['value'], robinson_foulds_distance=comparison['rf']['value'])


def _clade(attachment):
    sheet = attachment['sheets']['reference_characterization']
    return {'characterized_count': len(sheet['characterized_subject_refs']),
            'uncharacterized_count': len(sheet['unknown_subject_refs']),
            'characterized_fraction': sheet['characterized_fraction'],
            'independent_assay_observation_count': sheet['independent_assay_observation_count'],
            'clade_characterization_status': sheet['status']}


def _robustness(body):
    return {'compared_analysis_count': len(body['placement_refs']), 'stability_numerator': body['stability_numerator'],
            'stability_denominator': body['stability_denominator']}


def _cause(attachment):
    cause = attachment['sheets']['functional_scope']['historical_cause']
    if not isinstance(cause, dict):
        return {}
    return _present(historical_cause_grade=cause['grade'], historical_cause_score=cause['score'],
                    historical_cause_lower=cause['score_bounds']['lower'],
                    historical_cause_upper=cause['score_bounds']['upper'])


def sheet_features(reader, known):
    """One feature entry per held native measurement, from its current attribution sheet, in reference order."""
    attachments = _current(received_attachments(reader, set(known)))
    variants = {}
    for row in attachments:
        if row['variant_group']:
            variants.setdefault(row['variant_group'], set()).add(row['variant'])
    competing = {key for key, values in variants.items() if len(values) > 1}
    entries = []
    for attachment in attachments:
        body = received_measurement(reader, attachment['measurement_ref'])['body']
        features = {'evidence_type': EVIDENCE_TYPES[body['schema']], 'sheet_refs': sheet_records(reader, attachment),
                    'attribution_state': attachment['state'], 'missing_input_count': len(attachment['missing']),
                    **_present(attributed_score=attachment['score'], attributed_lower=attachment['bounds'][0],
                               attributed_upper=attachment['bounds'][1])}
        if body['schema'] == 'a104_placement':
            features.update(_placement(reader, body, competing))
        elif body['schema'] == 'a104_history_comparison':
            features.update(_history(body))
        elif body['schema'] == 'a104_clade_composition':
            features.update(_clade(attachment))
        else:
            features.update(_robustness(body))
        features.update(_cause(attachment))
        entries.append(validate(features, SHEET_FEATURES, ('evidence_type', 'sheet_refs', 'attribution_state')))
    return entries


def target_features(credit_view):
    """The V lines of the credit view, per target (``A104EvolutionaryCredit``; the other projectors have none)."""
    entries = []
    if 'target_sheets' not in credit_view:
        return entries
    for target, sheet in sorted(credit_view['target_sheets'].items()):
        cells = sheet['cells']
        maxima = {name: max((cell['native_dimensions'][name] for cell in cells), default=0.)
                  for name in ('placement', 'history_comparison', 'characterized_clade')}
        entries.append(validate({
            'target_refs': [target], 'attribution_status': sheet['status'],
            'placement_max': maxima['placement'], 'history_comparison_max': maxima['history_comparison'],
            'characterized_clade_max': maxima['characterized_clade'],
            'supported_length': sum(cell['end'] - cell['start'] for cell in cells
                                    if any(value > 0 for value in cell['native_dimensions'].values())),
            'assigned_length': sheet['assigned_length'],
            'pending_measurement_count': len(sheet['pending_measurement_refs']),
            'competing_configuration_count': len(sheet['unresolved_variant_groups'])}, TARGET_FEATURES, TARGET_FEATURES))
    return entries


