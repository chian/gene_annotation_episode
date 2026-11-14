"""The pre-relocation optical release remains an exact immutable declaration."""
from copy import deepcopy
from importlib import import_module
import pytest
from .test_private_scientific_attestations import AXIS, PILOT

# Literal released metadata from original HEAD literature_optical_storage._PINNED.
ORIGINAL = {
    'literature_optical_inputs.py': '6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474',
    'literature_optical_calculations.py': '1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e',
    'literature_optical_validation.py': '4340cce4a7a659d167b15fcb707b646bd13f8d213e36e0957a454cc02eb54425',
}

@pytest.mark.parametrize('pilot', (False, True))
def test_original_optical_receipt_retains_exact_hashes(pilot):
    module = import_module((PILOT + '.scoring.' if pilot else AXIS + '.library.') + 'literature_optical_storage')
    validation = import_module((PILOT + '.tools.' if pilot else AXIS + '.library.') + 'literature_optical_validation')
    receipt = {'sha256': deepcopy(ORIGINAL), 'validation_version': validation.VERSION}
    before = deepcopy(receipt)
    assert module._saved_dependency_receipt(receipt)
    assert receipt == before
    receipt['sha256']['literature_optical_inputs.py'] = '0' * 64
    assert not module._saved_dependency_receipt(receipt)
    assert before['sha256'] == ORIGINAL
