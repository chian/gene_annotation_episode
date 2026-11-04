from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.hmmer_native_result_views import (
    NATIVE_HMMER_METRICS, native_hmmer_fact_sources, projected_measurements,
    validate_native_hmmer_result_selector)
from test_native_hmmer_publication import selector


@pytest.mark.parametrize("program", ["hmmscan", "hmmsearch", "jackhmmer", "nhmmer", "nhmmscan", "hmmalign"])
def test_selector_closed_metrics_and_program_family(program):
    wanted = selector(program)
    assert validate_native_hmmer_result_selector(wanted, program=program) == wanted
    bad = deepcopy(wanted)
    bad["projection"]["metrics"].append("generic_confidence")
    with pytest.raises(ContractError):
        validate_native_hmmer_result_selector(bad, program=program)
    bad = deepcopy(wanted)
    bad["projection"]["rows"]["limit"] = 0
    with pytest.raises(ContractError):
        validate_native_hmmer_result_selector(bad, program=program)


@pytest.mark.parametrize("rows", [
    {"record_keys": []}, {"record_keys": ["same", "same"]}, {"offset": True, "limit": 1},
    {"offset": 0.0, "limit": 1}, {"offset": 0, "limit": 1, "threshold": .01}])
def test_invalid_selection_cannot_rank_filter_or_choose_implicit_rows(rows):
    wanted = selector("hmmscan")
    wanted["projection"]["rows"] = rows
    with pytest.raises(ContractError):
        validate_native_hmmer_result_selector(wanted, program="hmmscan")


def test_negative_and_zero_finite_values_differ_from_unavailable():
    values, unavailable = projected_measurements({"native_score_bits": -2.5, "native_evalue": 0,
        "native_bias_bits": None, "availability": {"native_bias_bits": "native_value_unavailable_or_invalid"}},
        ["native_score_bits", "native_evalue", "native_bias_bits"])
    assert values == [{"name": "native_score_bits", "value": -2.5}, {"name": "native_evalue", "value": 0}]
    assert unavailable == [{"name": "native_bias_bits", "reason": "incompatible_input"}]


def test_fact_sources_have_family_specific_enums_and_subject_namespace():
    from gene_annotation_episode.communication import validate_closed_schema
    definitions = native_hmmer_fact_sources()
    assert set(definitions) == {"execution_hmmer_domain_rows", "execution_nhmmer_locus_rows", "execution_hmmalign_sequence_rows"}
    for name, definition in definitions.items():
        schema = definition["report_schema"]
        assert schema["x-source"] == name
        assert schema["items"]["additionalProperties"] is False
        assert schema["items"]["properties"]["subject_ref"]["x-reference-namespace"] == "subject"
        assert schema["items"]["properties"]["record_key"]["x-reference-namespace"] == "native_hmmer_row"
        validate_closed_schema({"type": "object", "properties": {"rows": schema},
            "required": ["rows"], "additionalProperties": False})
    assert definitions["execution_hmmer_domain_rows"]["report_schema"]["items"]["properties"]["measurements"]["items"]["properties"]["name"]["enum"] == list(NATIVE_HMMER_METRICS["protein_domain"])
