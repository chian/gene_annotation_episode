"""Real configurable bindings with independent original source framing + four operands."""
from copy import deepcopy
import json
import pytest
from .receiving_context_controls import own, AXIS, CASES
from .test_actual_private_registry import constructed
from .test_private_descriptor_reopening import compose


@pytest.fixture(scope='module')
def owners(constructed):
    _,_,_,bindings,_ = constructed
    services = bindings[0].services
    result = {b.binding_path:b for b in bindings}
    for prefix in ('','scientific_process.'):
        for binding in own(prefix+'published_evidence_assessment.episode').create_binding_tree(services):
            result[binding.binding_path] = binding
        monitor = own(prefix+'execution_progress_assessment.episode').MonitorEpisode(services)
        result[monitor.binding_path] = monitor
    for row in CASES['records']:
        if row['family'] == 'a101_resource_raw_home_ordered_sources':
            home = row['home']; binding = own(home.replace('/','.')+'.episode').ResourceEpisode(services)
            assert binding.binding_path == home
            result[home] = binding
    assert set(r['home'] for r in CASES['records']) <= set(result)
    return result


if AXIS == 'a101':
    @pytest.mark.parametrize('row', [r for r in CASES['records'] if r['family']=='a101_resource_raw_home_ordered_sources'],ids=lambda row:row['home'])
    def test_resource_information_profile_keeps_conditional_original_inputs(owners,row):
        profile = own('composition_information').CONTRACT_INFORMATION_PROFILE
        original = owners[row['home']]
        binding = type(original)(original.services,contract_information_profile=profile)
        assert binding.as_record()['configuration']['contract_information_profile'] == profile
        assert binding.as_record()['implementation_sha256'] == framing(row,profile)


def test_real_configured_descriptor_roundtrip_and_strict_hash_conflict(constructed,tmp_path):
    _,_,_,bindings,literature = constructed
    descriptors = [b.as_record() for b in (bindings[0],*literature)]
    (tmp_path/'actual-descriptors.json').write_text(json.dumps(descriptors,sort_keys=True)+'\n')
    rebuilt = compose(constructed,descriptors)
    assert [b.as_record() for b in rebuilt.bindings] == descriptors
    assert [type(b) for b in rebuilt.bindings] == [type(b) for b in (bindings[0],*literature)]
    saved = deepcopy(descriptors)
    for original in descriptors:
        changed=deepcopy(original); changed['implementation_sha256']='0'*64
        with pytest.raises(own('method_loop.durable').DurableExecutionError):
            compose(constructed,[changed])
    assert descriptors == saved


@pytest.mark.parametrize('change', ('binding_id','configuration'))
def test_configured_saved_descriptor_rejects_nonhash_identity_changes(constructed,change):
    *_,literature=constructed
    original=literature[0].as_record(); changed=deepcopy(original)
    if change=='binding_id': changed['binding_id']='foreign/unknown_episode'
    else: changed['configuration']['unrecognized_original_operand']=True
    with pytest.raises(own('method_loop.durable').DurableExecutionError): compose(constructed,[changed])
    assert literature[0].as_record()==original
