"""Exact XML unit witnesses remain readable without discarding their markup.

The superscript syntax mirrors retained publication headers. The numerical
values and fixed predictions are constructed software-test inputs.
"""
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from test_literature_perturbation_source import covariance_arguments, extract, summary_grading_parent_return


@pytest.mark.parametrize("endpoint,covariance,canonical", [
    ("h<sup>−1</sup>", "h<sup>−2</sup>", "per_h"),
    ("h<sup>&#x2212;1</sup>", "(h<sup>&#x2212;1</sup>)<sup>2</sup>", "per_h"),
    ("CFU ml<sup>−1</sup>", "(CFU ml<sup>−1</sup>)<sup>2</sup>", "CFU_per_mL"),
])
def test_xml_unit_witnesses_survive_summary_grading_and_parent_receipt(
        tmp_path, endpoint, covariance, canonical):
    summary_grading_parent_return(tmp_path, endpoint, covariance, endpoint,
        canonical_unit=canonical, expected=40)
    args, raw = covariance_arguments(endpoint_unit=endpoint, unit=covariance)
    extraction = extract(args, raw)
    assert extraction["endpoint_unit"] == canonical
    # Reading the unit must leave the exact retained witness intact.
    assert extraction["summary_data"]["measurements"]["W"]["meaning_witnesses"][-1]["quote"] == endpoint
    assert any(w["quote"] == covariance for w in extraction["summary_data"]["covariances"][0]["witnesses"])


@pytest.mark.parametrize("endpoint", ["h</th><th>−1", "h<sup>x</sup>",
    "h&lt;sup&gt;−1&lt;/sup&gt;"])
def test_xml_fragments_are_not_concatenated_into_a_supported_unit(endpoint):
    args, raw = covariance_arguments(endpoint_unit=endpoint, unit="h<sup>−2</sup>")
    with pytest.raises(ExperimentalContractError, match="unsupported_perturbation_source_unit"):
        extract(args, raw)
