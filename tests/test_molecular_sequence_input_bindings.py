"""Actual Store/EPR receipt controls, with explicitly engineered commissions.

No native service, scientific launch, historical source-version authority or
new receipt/grant is claimed by these read-only input tests.
"""
import pytest

from gene_annotation_episode import molecular_sequence_input_contracts as contracts


@pytest.mark.parametrize("kind", ["string", "key", "cycle"])
def test_pure_validation_normalizes_malformed_unicode_and_recursive_data_to_value_error(kind):
    value = {"bad": "\ud800"} if kind == "string" else {"\udfff": 1} if kind == "key" else []
    if kind == "cycle": value.append(value)
    with pytest.raises(ValueError, match="molecular_sequence_received_input_invalid"):
        contracts.validate_molecular_sequence_received_input(value)
