"""Synthetic unit checks; no paper measurements or mass normalization inferred."""
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_rate_reader import read_rate_table
from test_literature_rate_reader import source_table


def test_explicit_specific_activity_units_preserve_mass_denominator():
    source = source_table(changes={"unit": "µmol min−1 mg−1"})
    extracted = read_rate_table(source, expected_subject="ConstructX", expected_experiment="assay-1")
    assert all(row["unit"] == "umol/min/mg" for row in extracted["rows"])
    assert "µmol min−1 mg−1" in extracted["rows"][0]["source"]["raw_row"]


def test_specific_rate_is_not_an_amount_rate_or_a_turnover_number():
    from test_literature_rate_calculations import extraction
    data = extraction()
    data["rows"][0]["unit"] = "umol/min/mg"
    with pytest.raises(ExperimentalContractError, match="incompatible_rate_dimensions"):
        populate_rate_contrast(data, reference_arm="reference", test_arm="test",
            reference_condition="without_inhibitor", test_condition="with_inhibitor")


def test_specific_rate_conversion_does_not_require_invented_protein_amount():
    from test_literature_rate_calculations import extraction
    data = extraction(a=2, b=1000)
    data["rows"][0]["unit"] = "umol/min/mg"
    data["rows"][1]["unit"] = "nmol/min/mg"
    sheet = populate_rate_contrast(data, reference_arm="reference", test_arm="test",
        reference_condition="without_inhibitor", test_condition="with_inhibitor")
    assert sheet["cells"]["rate_difference"]["value"] == 1
    assert sheet["cells"]["rate_difference"]["unit"] == "umol/min/mg"
    assert sheet["cells"]["retained_fraction"]["value"] == .5
    assert sheet["molecule_specific_product_rate"] is None
