"""Schema permits exact ports while validators own cross-field meanings."""
from copy import deepcopy

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_hmmer_preparation_contracts import requested_job_from_hmmer_preparation
from gene_annotation_episode.native_hmmer_preparation_job_schema import preparation_job_schema, preparation_requested_job_schema
from test_native_hmmer_preparation_contracts import CASES, job


@pytest.mark.parametrize("program,mode", CASES)
def test_all_concrete_job_and_request_schemas(program, mode):
    selected = job(program, mode)
    schema = preparation_job_schema(program, mode)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(selected)
    Draft202012Validator(preparation_requested_job_schema(program, mode)).validate(requested_job_from_hmmer_preparation(selected))
    incomplete = deepcopy(selected)
    incomplete["outputs"] = [r for r in selected["outputs"] if r["role"] != "stderr"]
    assert list(Draft202012Validator(schema).iter_errors(incomplete))


def test_fm_abi_is_supplied_and_other_metadata_is_closed():
    selected = job("hmmerfm-exactmatch", "locations")
    selected["input_metadata"] = {}
    assert list(Draft202012Validator(preparation_job_schema("hmmerfm-exactmatch", "locations")).iter_errors(selected))
    selected = job()
    selected["input_metadata"] = {"producer_contract": {}}
    assert list(Draft202012Validator(preparation_job_schema("hmmconvert", "ascii")).iter_errors(selected))
    with pytest.raises(ValueError):
        preparation_job_schema("not-a-program")
