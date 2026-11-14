"""Authenticate actual A106 scientific source bytes and retained binding receipts."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.library import literature_optical_storage as optical
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_binding_interaction_inputs as binding_reader
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_binding_interaction_storage as binding_storage
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_kinetic_summary_precision_storage as summary


@pytest.mark.parametrize('module,kind', [(optical, 'optical'), (binding_reader, 'binding_reader'),
                                       (binding_storage, 'binding_storage'), (summary, 'summary')])
def test_actual_scientific_bytes_are_authenticated_and_changed_bytes_rejected(module, kind, tmp_path, monkeypatch):
    if kind == 'summary':
        repository = object.__new__(module.LiteratureKineticSummaryPrecisionRepository)
        read = repository._original_implementation
        hashes = read()['files']
        chosen = 'literature_kinetic_summary_precision_inputs.py'
        error = module.ContractError
    else:
        read = module._dependencies
        hashes = read()['sha256']
        chosen = 'literature_optical_inputs.py' if kind == 'optical' else 'literature_binding_reader.py'
        error = module.ExperimentalContractError if kind == 'binding_reader' else module.ContractError
    assert hashes
    assert all(digest == hashlib.sha256(module.source_file(name).read_bytes()).hexdigest()
               for name, digest in hashes.items())
    original = module.source_file
    changed = tmp_path / chosen
    changed.write_bytes(original(chosen).read_bytes() + b'\n# unapproved source mutation\n')
    monkeypatch.setattr(module, 'source_file', lambda name: changed if name == chosen else original(name))
    with pytest.raises(error, match='dependency_mismatch'):
        read()


def test_exact_known_historical_binding_receipts_survive_and_unknown_hashes_fail():
    for receipt in (binding_storage._ORIGINAL_DEPENDENCIES, binding_storage._PREVIOUS_DEPENDENCIES,
                    binding_storage._PRE_CONNECTION_DEPENDENCIES):
        original = deepcopy(receipt)
        binding_storage._dependencies(receipt)
        assert receipt == original
        changed = deepcopy(receipt)
        changed['sha256']['literature_binding_interaction_inputs.py'] = '0' * 64
        with pytest.raises(binding_storage.ContractError, match='implementation_dependency_mismatch'):
            binding_storage._dependencies(changed)
        assert receipt == original
