"""Prospective byte authentication and immutable historical receipt contracts."""
from copy import deepcopy
import hashlib
from importlib import import_module

import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
PILOT = AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'


def modules(pilot):
    base = PILOT if pilot else AXIS
    return {
        'optical': import_module(base + ('.scoring.' if pilot else '.library.') + 'literature_optical_storage'),
        'binding_reader': import_module(base + ('.tools.' if pilot else '.library.') + 'literature_binding_interaction_inputs'),
        'binding_storage': import_module(base + ('.scoring.' if pilot else '.library.') + 'literature_binding_interaction_storage'),
        'summary': import_module(base + ('.scoring.' if pilot else '.library.') + 'literature_kinetic_summary_precision_storage'),
    }


@pytest.mark.parametrize('pilot', (False, True))
@pytest.mark.parametrize('kind', ('optical', 'binding_reader', 'binding_storage', 'summary'))
def test_current_scientific_bytes_are_authenticated_and_tampering_rejected(pilot, kind, tmp_path, monkeypatch):
    module = modules(pilot)[kind]
    if kind == 'summary':
        repository = module.LiteratureKineticSummaryPrecisionRepository.__new__(module.LiteratureKineticSummaryPrecisionRepository)
        read = repository._original_implementation
        receipt = read()
        assert receipt['version'] == 'summary_precision_original_implementation_v4'
        hashes = receipt['files']
        chosen = 'literature_kinetic_summary_precision_inputs.py'
        error = module.ContractError
    else:
        read = module._dependencies
        receipt = read()
        hashes = receipt['sha256']
        chosen = 'literature_optical_inputs.py' if kind == 'optical' else 'literature_binding_reader.py'
        error = module.ExperimentalContractError if kind == 'binding_reader' else module.ContractError
    assert hashes
    assert all(value == hashlib.sha256(module.source_file(name).read_bytes()).hexdigest() for name, value in hashes.items())
    actual = module.source_file
    changed = tmp_path / chosen
    changed.write_bytes(actual(chosen).read_bytes() + b'\n# unapproved source change\n')
    monkeypatch.setattr(module, 'source_file', lambda name: changed if name == chosen else actual(name))
    with pytest.raises(error, match='dependency_mismatch'):
        read()


@pytest.mark.parametrize('pilot', (False, True))
def test_known_historical_binding_receipts_remain_exact_and_unknown_hashes_fail(pilot):
    module = modules(pilot)['binding_storage']
    for receipt in (module._ORIGINAL_DEPENDENCIES, module._PREVIOUS_DEPENDENCIES, module._PRE_CONNECTION_DEPENDENCIES):
        retained = deepcopy(receipt)
        module._dependencies(receipt)
        assert receipt == retained
        changed = deepcopy(receipt)
        changed['sha256']['literature_binding_interaction_inputs.py'] = '0' * 64
        with pytest.raises(module.ContractError, match='implementation_dependency_mismatch'):
            module._dependencies(changed)
        assert receipt == retained


@pytest.mark.parametrize('pilot', (False, True))
def test_historical_optical_receipt_is_checked_without_relabelling(pilot):
    module = modules(pilot)['optical']
    current = module._dependencies()
    historical = {'sha256': deepcopy(module._PINNED), 'validation_version': current['validation_version']}
    retained = deepcopy(historical)
    assert module._saved_dependency_receipt(historical)
    assert historical == retained
    changed = deepcopy(historical)
    changed['sha256']['literature_optical_inputs.py'] = '0' * 64
    assert not module._saved_dependency_receipt(changed)
    assert historical == retained
