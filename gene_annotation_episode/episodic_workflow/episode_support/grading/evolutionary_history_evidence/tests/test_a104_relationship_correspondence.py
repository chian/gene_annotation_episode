"""Actual PBS branch inventory plus explicit numerical contract controls.

The retained native data came from job 9040517.
"""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import relationship_inventory


NATIVE = json.loads((Path(__file__).parent/'fixtures/a104/real/mj0044/native-pbs-9040517.json').read_text())


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
