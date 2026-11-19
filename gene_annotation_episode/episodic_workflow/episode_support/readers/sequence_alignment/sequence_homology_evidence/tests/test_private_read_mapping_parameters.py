"""Exact original native parameter representation cases; no runtime controller."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_alignment.sequence_homology_evidence import read_mapping as mapper
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError

@pytest.mark.parametrize("name,value",[("kmer",1),("kmer",28),("window",1),("window",255),
    ("seed",0),("seed",2147483647),("max_secondary",0),("max_secondary",2147483647)])
def test_native_parameter_boundaries_preserve_original_selected_integer(name,value):
    given={name:value}
    result=mapper.settings("map-ont",given)
    assert result["overrides"] == given and type(result["overrides"][name]) is int
    assert given == {name:value}


@pytest.mark.parametrize("name,value,low,high",[("kmer",0,1,28),("kmer",29,1,28),
    ("window",0,1,255),("window",256,1,255),("window",4294967306,1,255),
    ("seed",-1,0,2147483647),("seed",2147483648,0,2147483647),
    ("max_secondary",-1,0,2147483647),("max_secondary",2147483648,0,2147483647)])
def test_native_unrepresentable_value_reports_exact_field_and_range(name,value,low,high):
    with pytest.raises(ContractError,match="native_mapping_integer_out_of_range") as failure:
        mapper.settings("map-ont",{name:value})
    assert failure.value.detail == {"field_path":["parameters",name],"minimum":low,"maximum":high,
        "value":value,"native_representation":"minimap2_2_31_supported_integer_interface"}


@pytest.mark.parametrize("name",["kmer","window","seed","max_secondary"])
@pytest.mark.parametrize("value",[True,False,1.5,"1"])
def test_native_integer_interface_does_not_coerce_boolean_float_or_string(name,value):
    with pytest.raises(ContractError,match="native_mapping_integer_required") as failure:
        mapper.settings("map-ont",{name:value})
    assert failure.value.detail["field_path"] == ["parameters",name]
    assert failure.value.detail["actual_type"] == type(value).__name__

