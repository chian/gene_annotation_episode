"""Root arithmetic and common-target boundaries, without invented native facts."""
import pytest

from gene_annotation_episode.evidence_root import NativeEvidenceRootCredit, offset_volume
from gene_annotation_episode.state import Store


def test_zero_dimension_preserves_earned_credit_and_future_empty_axes_are_neutral():
    assert offset_volume({'A101': .8, 'A102': 0})['credit'] == pytest.approx(.8)
    assert offset_volume({'A101': 0, 'A102': .6})['credit'] == pytest.approx(.6)
    both = offset_volume({'A101': .8, 'A102': .6})
    assert both['additive'] == pytest.approx(1.4)
    assert both['interaction'] == pytest.approx(.48)
    assert both['credit'] == pytest.approx(1.88)
    assert sum(both['attribution'].values()) == pytest.approx(both['credit'])
    assert offset_volume({'A101': .8, 'A102': .6, 'future': 0})['credit'] == both['credit']
    assert offset_volume({'A101': 0, 'A102': 0})['credit'] == 0


def test_different_targets_do_not_manufacture_cross_axis_interaction(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        inputs = tmp_path/'two-targets.faa'
        inputs.write_text('>first\nAGST\n>second\nQWERTYIP\n')
        first, second = store.create_problem(inputs, molecule='protein')['subject_refs']
        class Projector:
            def __init__(self, axis): self.axis = axis
            def read_details(self, store, scope, **kwargs):
                target = scope['subject_refs'][0]
                value = int((self.axis == 'A101' and target == first) or (self.axis == 'A102' and target == second))
                return {'credit': value, 'source_contributions': [], 'source_contribution_count': 0,
                    'detail_pages': {'source_contributions_total': 0},
                    'a101_sheet': {'targets': {target: {'profile': []}}}}
        monkeypatch.setattr('gene_annotation_episode.evidence_root._projector', Projector)
        view = NativeEvidenceRootCredit()(store, {'subject_refs': [first, second]}, known_record_refs=[])
        assert view['axis_components'] == pytest.approx({'A101': 1/3, 'A102': 2/3, 'A103': 0, 'A104': 0})
        assert view['credit'] == 1
        assert view['volume_components']['interaction'] == 0


def test_unbound_axes_are_explicit_and_cannot_masquerade_as_zero_measurements():
    with pytest.raises(ValueError, match='axis_scorer_not_bound'):
        NativeEvidenceRootCredit(('A101', 'A105'))
