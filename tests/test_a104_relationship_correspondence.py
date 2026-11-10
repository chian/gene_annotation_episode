"""Actual PBS branch inventory plus explicit numerical contract controls.

The retained native data came from job 9040517. Numerical controls below mock
the measurement reader and create no producer grant, worksheet or credit.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.a104_scoring import relationship_inventory, target_member, target_regions, VERSION
from gene_annotation_episode import a104_interpretation as interpretation


NATIVE = json.loads((Path(__file__).parent/'fixtures/a104/real/mj0044/native-pbs-9040517.json').read_text())


def controlled_placement(analysis, index):
    binding = next(row for row in NATIVE['bindings'] if row['name'] == analysis)
    result = next(row for row in NATIVE['result']['analyses'] if row['name'] == analysis)
    target = target_member(binding, NATIVE['target_ref'])
    split = result['tree_summary']['splits'][index]
    side = split['side'] if target['tip_id'] in split['side'] else split['complement']
    population = result['bootstrap_population']['splits'][index]
    return {'schema': 'a104_placement_v1', 'version': VERSION, 'target_ref': NATIVE['target_ref'],
        'target_regions': target_regions(target, NATIVE['target_ref']),
        'native_phylogeny_ref': 'engineering_native_handle', 'native_request_ref': NATIVE['request_ref'],
        'hpc_result_ref': NATIVE['hpc_result_ref'], 'pbs_job_id': NATIVE['pbs_job_id'],
        'result_sha256': NATIVE['result_sha256'], 'target_tip': target['tip_id'],
        'analysis_configuration_digest': analysis, 'reference_panel_members': deepcopy(binding['members']),
        'clade_members': deepcopy([row for row in binding['members'] if row['tip_id'] in side]),
        'raw_value': population['matches']/population['denominator'], 'variant_group': 'engineering_panel',
        'variant': analysis}


def compare(first, second, monkeypatch):
    values = {'engineering_first': first, 'engineering_second': second}
    monkeypatch.setattr(interpretation, 'received_measurement',
                        lambda store, reference: {'body': values[reference]})
    return interpretation.compare_placements(object(), list(values), set(values))


def test_real_native_same_relationship_has_different_analysis_local_indices():
    inventory = relationship_inventory(NATIVE)
    matching = [row for row in inventory if any(item['analysis'] == 'family' and item['split_index'] == 9
                                              for item in row['occurrences'])]
    assert len(matching) == 1
    assert len(matching[0]['reference_members']) == 5
    assert {(item['analysis'], item['split_index']) for item in matching[0]['occurrences']} == {
        ('family', 9), ('family_mfp', 8)}
    assert all(item['bootstrap_denominator'] == 1000 for item in matching[0]['occurrences'])
    assert not any(item['analysis'] == 'target_region' for row in inventory for item in row['occurrences'])


def test_reused_split_ordinal_cannot_be_interpreted_as_model_instability(monkeypatch):
    with pytest.raises(ValueError, match='distinct_compatible_branches_are_not_replicate_tests'):
        compare(controlled_placement('family', 9), controlled_placement('family_mfp', 9), monkeypatch)


def test_actual_corresponding_relationship_preserves_native_support(monkeypatch):
    result = compare(controlled_placement('family', 9), controlled_placement('family_mfp', 8), monkeypatch)
    assert result['stability_fraction'] == 1
    assert result['stability_numerator'] == result['stability_denominator'] == 5
    assert result['raw_value'] == pytest.approx(.381)


def test_genuinely_incompatible_relationships_remain_a_comparison(monkeypatch):
    first, second = controlled_placement('family', 9), controlled_placement('family_mfp', 8)
    target = next(row for row in first['reference_panel_members'] if row['tip_id'] == first['target_tip'])
    refs = [row for row in first['reference_panel_members'] if row['tip_id'] != first['target_tip']]
    first.update(clade_members=[target, refs[0], refs[1]], raw_value=.9)
    second.update(clade_members=[target, refs[1], refs[2]], raw_value=.6)
    result = compare(first, second, monkeypatch)
    assert result['stability_fraction'] == pytest.approx(1/3)
    assert result['raw_value'] == pytest.approx(.2)
