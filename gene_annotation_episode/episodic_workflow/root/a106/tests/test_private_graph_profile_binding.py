"""Saved graph source identity is correlated with the admitted full profile."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from .test_private_controlled_retained_profiles import captured
from ..literature_contract_error import ExperimentalContractError
from ..library.controlled_response_retained_profiles import PROFILES_BY_SOURCE_STAGE, RETAINED_PRIVATE_DEPENDENCIES
from .scientific_source_custody import science

def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from _walk(child)
    elif isinstance(value,list):
        for child in value:yield from _walk(child)

@pytest.mark.parametrize('index',range(6))
@pytest.mark.parametrize('mutation',('unknown_counter','counter_of_prospective_other_source'))
def test_accepted_full_profile_rejects_a_different_counter(index,mutation):
    arguments,result,_,validate,_=captured(index);value=deepcopy(result)
    directory=Path(__file__).parent/'fixtures/controlled_response_private_profiles_20261112'
    other=(directory/'prospective_counter.py.txt').read_bytes()
    assert hashlib.sha256(other).hexdigest()==json.loads((directory/'manifest.json').read_bytes())['prospective_counter_sha256']
    wrong='0'*64 if mutation=='unknown_counter' else hashlib.sha256(other).hexdigest()
    pixels=[x for x in _walk(value) if 'counter_module_sha256' in x];assert pixels
    assert all(x['counter_module_sha256']!=wrong for x in pixels)
    for x in pixels:x['counter_module_sha256']=wrong
    with pytest.raises(ExperimentalContractError) as error:validate(arguments,value)
    assert error.value.code=='saved_graph_image_identity_mismatch' and error.value.field=='pixels'


def test_current_repository_descriptor_includes_the_passive_profile_dependency():
    from ..library import controlled_response_retained_profiles
    expected=hashlib.sha256(Path(controlled_response_retained_profiles.__file__).read_bytes()).hexdigest()
    descriptor=science('literature_controlled_response_storage').implementation_descriptor(evidence_origin='synthetic_fixture')
    assert descriptor['modules']['library/controlled_response_retained_profiles.py']==expected
