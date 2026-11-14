"""Native clade-membership and robustness measurements with bounded meaning."""
from __future__ import annotations

from copy import deepcopy

from .a104_hpc import require
from .a104_publication import received_measurement
from .a104_scoring import digest
from .domain import canonical


def _placement(store, reference, known):
    require(reference in known, 'a104_native_placement_not_received')
    value = received_measurement(store, reference)
    require(value is not None and value['body']['schema'] == 'a104_placement_v1', 'a104_measured_placement_required')
    return value['body']


def clade_composition(store, reference, known):
    placement = _placement(store, reference, known)
    subjects = sorted({part['subject_ref'] for member in placement['clade_members']
                       if member['tip_id'] != placement['target_tip'] for part in member['parts']})
    body = {key: deepcopy(placement[key]) for key in ('version', 'target_ref', 'target_regions',
        'native_phylogeny_ref', 'native_request_ref', 'hpc_result_ref', 'pbs_job_id', 'result_sha256')}
    return {**body, 'schema': 'a104_clade_composition_v1', 'producer_operation': 'phylogeny.clade_functions',
        'native_placement_ref': reference, 'clade_members': deepcopy(placement['clade_members']),
        'reference_correspondences': [row for row in placement['reference_correspondences'] if row['reference_ref'] in subjects],
        'required_reference_parts': {part['subject_ref']: {'regions': part['regions'], 'full_length': part['full_length']}
            for member in placement['clade_members'] if member['tip_id'] != placement['target_tip'] for part in member['parts']},
        'characterization_subject_refs': subjects, 'raw_value': placement['raw_value'],
        'function_status': 'requires_received_reference_characterization',
        'variant_group': digest(['clade_function_use', placement['variant_group'], subjects]),
        'variant': placement['variant'],
        'interpretation': 'actual_native_clade_membership; reference_function_links_qualify_this_use_on_receipt'}


def _member_key(member):
    return canonical([{'subject_ref': part['subject_ref'], 'regions': part['regions']} for part in member['parts']])


def compare_placements(store, references, known):
    require(len(references) == len(set(references)) and len(references) >= 2, 'a104_distinct_analysis_comparison_required')
    references = sorted(references)
    placements = [_placement(store, reference, known) for reference in references]
    first = placements[0]
    require(all(row['target_ref'] == first['target_ref'] and row['target_regions'] == first['target_regions']
                for row in placements), 'a104_robustness_original_region_conflict')
    identities = {row['analysis_configuration_digest'] for row in placements}
    require(len(identities) == len(placements), 'a104_same_native_analysis_is_not_a_robustness_replicate')
    universes = [{_member_key(member) for member in row['reference_panel_members']} for row in placements]
    require(all(universe == universes[0] for universe in universes), 'a104_robustness_requires_same_declared_member_scope')
    groups = [{_member_key(member) for member in row['clade_members'] if member['tip_id'] != row['target_tip']}
              for row in placements]
    from .domain import ContractError
    reference_universe = {_member_key(member) for member in first['reference_panel_members']
                          if member['tip_id'] != first['target_tip']}
    for i, group in enumerate(groups):
        for other in groups[i+1:]:
            # Both chosen sides contain the fixed target. Distinct compatible
            # edges can coexist in the same unrooted tree, so comparing them
            # does not test stability of one relationship. Cross-cutting
            # incompatible splits remain a genuine conflicting comparison.
            if group != other and not all((group-other, other-group, reference_universe-(group | other))):
                raise ContractError('a104_distinct_compatible_branches_are_not_replicate_tests', detail={
                    'recovery': 'Use phylogeny.inspect corresponding_relationships to choose the same '
                        'relationship_id across analyses, then measure those analysis-local split_index values. '
                        'Different split indices can denote the same relationship; equal indices can denote different edges.'})
    common, union = set.intersection(*groups), set.union(*groups)
    stability = len(common)/len(union) if union else None
    value = min(row['raw_value'] for row in placements)*stability if stability is not None else None
    body = {key: deepcopy(first[key]) for key in ('version', 'target_ref', 'target_regions',
        'native_phylogeny_ref', 'native_request_ref', 'hpc_result_ref', 'pbs_job_id', 'result_sha256')}
    return {**body, 'schema': 'a104_robustness_v1', 'producer_operation': 'phylogeny.compare_placements',
        'placement_refs': sorted(references), 'analysis_identities': sorted(identities),
        'common_reference_members': sorted(common), 'union_reference_members': sorted(union),
        'stability_numerator': len(common), 'stability_denominator': len(union), 'stability_fraction': stability,
        'native_support_values': [row['raw_value'] for row in placements], 'raw_value': value,
        'compared_variant_group': first['variant_group'],
        'compared_variants': sorted(identities),
        'variant_group': None, 'variant': None, 'function_status': 'unassessed',
        'interpretation': 'measured_stability_of_declared_native_analyses; conflicting_placements_retained'}


def recompute_measurement(store, body):
    if body['schema'] == 'a104_clade_composition_v1':
        return clade_composition(store, body['native_placement_ref'], {body['native_placement_ref']})
    if body['schema'] == 'a104_robustness_v1':
        return compare_placements(store, body['placement_refs'], set(body['placement_refs']))
    raise ValueError('a104_interpretation_metric_not_bound')
