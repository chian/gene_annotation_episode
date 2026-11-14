"""Original pure target validation, without producer or launch capability."""
from copy import deepcopy

import pytest

from .. import execution_contracts as contracts


def original_target():
    return {'version': 'execution_target_v1', 'handle': 'saved-source', 'run_id': 'original-run',
        'resource_id': 'original-resource', 'resource_kind': 'local', 'execution_id': '/saved/native.json',
        'request_sha256': 'a' * 64, 'origin_episode_id': 'original-episode',
        'assignment': {'source_subject': 'β original molecule'}, 'scope': {'subject_refs': ['input']}}


def test_pure_original_target_preserves_unicode_and_returns_detached_record():
    target = original_target()
    returned = contracts.validate_target(target)
    assert returned == target and returned is not target
    returned['assignment']['source_subject'] = 'changed detached copy'
    assert target['assignment']['source_subject'] == 'β original molecule'


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'bad_kind', 'bad_digest', 'nonfinite'])
def test_pure_original_target_rejects_invalid_shape_with_original_error(mutation):
    target = deepcopy(original_target())
    if mutation == 'missing':
        del target['origin_episode_id']
    elif mutation == 'extra':
        target['invented'] = True
    elif mutation == 'bad_kind':
        target['resource_kind'] = 'invented'
    elif mutation == 'bad_digest':
        target['request_sha256'] = 'invalid'
    else:
        target['assignment']['value'] = float('nan')
    with pytest.raises(ValueError, match='^invalid_execution_target$'):
        contracts.validate_target(target)
