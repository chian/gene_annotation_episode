"""Route requests over existing observation kinds; no adopted catalog or target findings."""
import pytest

from gene_annotation_episode.episodic_workflow.root.scientific_support_metadata import annotation_policy_routes


@pytest.mark.parametrize("invalid", [["unknown"], ["alignment", "alignment"], "alignment",
    ("alignment",), [None], {"alignment"}, None, [float("nan")]])
def test_route_requests_reject_undeclared_or_duplicate_kind_values(invalid):
    with pytest.raises(ValueError, match="scientific_support_observation_kinds_invalid"):
        annotation_policy_routes(None, None, observation_kinds=invalid)
