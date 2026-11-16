"""Real configured descriptors round-trip; changed binding identity or configuration is refused."""
from copy import deepcopy
import json
import pytest
from .receiving_context_controls import own
from .test_actual_private_registry import constructed
from .test_private_descriptor_reopening import compose


def test_real_configured_descriptor_roundtrip(constructed,tmp_path):
    _,_,_,bindings,literature = constructed
    descriptors = [b.as_record() for b in (bindings[0],*literature)]
    (tmp_path/'actual-descriptors.json').write_text(json.dumps(descriptors,sort_keys=True)+'\n')
    rebuilt = compose(constructed,descriptors)
    assert [b.as_record() for b in rebuilt.bindings] == descriptors
    assert [type(b) for b in rebuilt.bindings] == [type(b) for b in (bindings[0],*literature)]


@pytest.mark.parametrize('change', ('binding_id','configuration'))
def test_configured_saved_descriptor_rejects_nonhash_identity_changes(constructed,change):
    *_,literature=constructed
    original=literature[0].as_record(); changed=deepcopy(original)
    if change=='binding_id': changed['binding_id']='foreign/unknown_episode'
    else: changed['configuration']['unrecognized_original_operand']=True
    with pytest.raises(own('method_loop.durable').DurableExecutionError): compose(constructed,[changed])
    assert literature[0].as_record()==original
