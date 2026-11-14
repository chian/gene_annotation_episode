"""Actual retained pre-repair extraction; metadata and science remain distinct."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.library import literature_amount_inputs as inputs
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_contracts import ExperimentalContractError
from .amount_source_fixtures import fixture

CAPTURE_SHA256='016ef33436e0e9a03eec6c3a3c21abaafa2a533330564bb2205a2e12d43bde47'


def captured():
    data=(Path(__file__).parent/'fixtures/retained_scientific_sources/amount/initial_private_result.json').read_bytes()
    assert hashlib.sha256(data).hexdigest()==CAPTURE_SHA256
    return json.loads(data)


def test_actual_emitted_extraction_keeps_its_original_labels_and_scientific_values():
    result=captured()
    original=deepcopy(result['saved']['extraction'])
    assert inputs.validate_amount_extraction(original)==result['saved']['extraction']
    assert original['lexical_dependency']==result['observed_lexical_dependency']
    assert original==result['saved']['extraction']
    assert [row['value'] for row in result['projected']]==[5/7,1.4]
    assert all(row['mass_factor_applied_to_rate'] is False for row in result['projected'])


@pytest.mark.parametrize('field',['module','scope_module','sha256_at_release','scope_sha256_at_release',
                                  'interface','scope_generation','unrecognized_extra'])
def test_unknown_lexical_map_cannot_use_the_retained_generation(field):
    extraction=deepcopy(captured()['saved']['extraction'])
    extraction['lexical_dependency'][field]='not-an-evidenced-generation'
    with pytest.raises(ExperimentalContractError,match='amount_lexical_dependency_mismatch'):
        inputs.validate_amount_extraction(extraction)


def test_retained_identity_does_not_relax_scientific_quantity_validation():
    extraction=deepcopy(captured()['saved']['extraction'])
    extraction['quantities']['numerator']['value']+=1
    with pytest.raises(ExperimentalContractError,match='amount_saved_quantity_mismatch'):
        inputs.validate_amount_extraction(extraction)


def test_new_production_uses_the_original_release_labels():
    arguments,_,reader=fixture()
    extracted=inputs.read_amount_inputs(arguments,read_source=reader)
    assert extracted['lexical_dependency']==inputs.LEXICAL_DEPENDENCY
    assert extracted['lexical_dependency']['module']=='gene_annotation_episode.literature_rate_native_inputs'
    assert extracted['lexical_dependency']['scope_module']=='gene_annotation_episode.literature_partner_source_fields'
    assert extracted['lexical_dependency']!=captured()['observed_lexical_dependency']
