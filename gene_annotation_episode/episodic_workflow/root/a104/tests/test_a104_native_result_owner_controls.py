"""Scoped original/current native Results ownership and refusal controls."""
import importlib
import os
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.tests.native_result_owner_controls import FAMILIES, HOMES, PREFIX, observe, original, selected
from gene_annotation_episode.episodic_workflow.root.a104.state import Store

PHASE = os.environ['A104_NATIVE_RESULT_OWNER_PHASE']
assert PHASE in {'baseline', 'connected'}
FLAGS = ('native_blast_standard_database', 'native_blast_database', 'native_blast', 'native_hmmer_preparation')

@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('native Results boundary control attempted external execution')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)

@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', FAMILIES, ids=lambda family: family[0])
def test_original_constructor_receipt_and_admission(home, family, tmp_path):
    reconstructed_module, reconstructed = original(family)
    actual_module, actual = selected(home, family, PHASE)
    from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
    assert reconstructed_module.ContractError is actual_module.ContractError is ContractError
    if PHASE == 'connected':
        shared = importlib.import_module(PREFIX + '.library.' + family[0].removesuffix('_results') + '_result_records')
        reader = getattr(shared, family[2])
        assert actual.__bases__ == (reader,)
        assert 'execute' in actual.__dict__ and not hasattr(reader, 'execute')
        assert actual.__module__ == actual_module.__name__
    with Store(tmp_path / 'store') as store:
        old = observe(reconstructed, store, tmp_path / 'old-actions', family)
        current = observe(actual, store, tmp_path / 'current-actions', family)
        assert old == current

@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('flags', [(), *(tuple([name]) for name in FLAGS), FLAGS])
def test_actual_selected_installer_conditions_and_return_identity(home, flags, tmp_path):
    module = importlib.import_module(PREFIX + ('.a104_execution_bindings' if PHASE == 'baseline'
        else '.' + home.replace('/', '.') + '.native_result_bindings'))
    with Store(tmp_path / 'store') as store:
        owner = SimpleNamespace(store=store, run_id='native-reader-installer-control', directory=tmp_path / 'actions',
            resources={'selected': {name: {'selected': True} for name in flags}})
        module.install_primary_result_readers(owner)
        module.install_preparation_result_readers(owner)
        for family in FAMILIES:
            instance = getattr(owner, family[0])
            flag = family[0].removesuffix('_results')
            assert (instance is not None) == (flag not in FLAGS or flag in flags)
            if instance is None:
                continue
            _, expected = selected(home, family, PHASE)
            assert type(instance) is expected and instance.owner is owner and instance.store is store
            returns = getattr(owner, flag + '_returns', None)
            if returns is not None:
                assert returns.owner is owner and returns.store is store
                if hasattr(returns, 'results'):
                    assert returns.results is instance
