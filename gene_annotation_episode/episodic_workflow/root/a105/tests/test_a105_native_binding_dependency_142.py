"""Bounded dependency compatibility; all scientific inputs here are synthetic.

Historical records are written by the untouched original runtime in a subprocess,
not by relabeling current records or replacing dependency-check functions.
"""
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_storage import COMPONENTS, LiteratureBindingInteractionRepository, _dependencies, _ORIGINAL_DEPENDENCIES, _PREVIOUS_DEPENDENCIES, _PRE_CONNECTION_DEPENDENCIES
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_binding_interaction_storage import setup, project
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_rate_episode_integration import service_binding
from gene_annotation_episode.episodic_workflow.root.a105.literature_implementation_sources import source_file
from gene_annotation_episode.episodic_workflow.root.a105 import literature_implementation_sources as source_owner
HISTORICAL_HARNESS = Path(__file__).parent / 'fixtures/retained_reference/a105_native_binding_dependency_142/historical_harness/tests'
PIN = Path(__file__).parent / 'fixtures/retained_reference/a105_native_binding_dependency_142/original_pin'
PREVIOUS_PIN = Path(__file__).parent / 'fixtures/retained_reference/a105_native_binding_dependency_142/previous_pin'



def test_whole_supported_maps_do_not_authorize_mixed_snapshots():
    snapshots = [_ORIGINAL_DEPENDENCIES, _PREVIOUS_DEPENDENCIES, _PRE_CONNECTION_DEPENDENCIES, _dependencies()]
    for left in snapshots:
        for right in snapshots:
            if left == right:
                continue
            for field in ('literature_rate_storage.py', 'literature_binding_interaction_storage.py'):
                mixed = deepcopy(left)
                mixed['sha256'][field] = right['sha256'][field]
                with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
                    _dependencies(mixed)


def test_preconnection_writer_is_retained_as_one_exact_historical_map():
    assert _dependencies(_PRE_CONNECTION_DEPENDENCIES) == _dependencies()
    altered = deepcopy(_PRE_CONNECTION_DEPENDENCIES)
    altered['sha256']['literature_rate_storage.py'] = _dependencies()['sha256']['literature_rate_storage.py']
    with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
        _dependencies(altered)

@pytest.mark.parametrize('change', ['null', 'empty', 'unknown_rate', 'old_writer_current_rate', 'unknown_writer', 'unknown_validator', 'missing_hash', 'extra_hash', 'changed_calculator'])
def test_unknown_or_mixed_saved_versions_are_rejected(change):
    saved = deepcopy(_ORIGINAL_DEPENDENCIES)
    if change == 'null':
        saved = None
    elif change == 'empty':
        saved = {}
    elif change == 'unknown_rate':
        saved['sha256']['literature_rate_storage.py'] = '0' * 64
    elif change == 'old_writer_current_rate':
        saved['sha256']['literature_rate_storage.py'] = _dependencies()['sha256']['literature_rate_storage.py']
    elif change == 'unknown_writer':
        saved['sha256']['literature_binding_interaction_storage.py'] = '0' * 64
    elif change == 'unknown_validator':
        saved['validation_version'] = 'unknown'
    elif change == 'missing_hash':
        del saved['sha256']['literature_binding_reader.py']
    elif change == 'extra_hash':
        saved['sha256']['unreviewed.py'] = '0' * 64
    else:
        saved['sha256']['literature_binding_interaction_calculations.py'] = '0' * 64
    with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
        _dependencies(saved)

@pytest.mark.parametrize('changed_file', ['literature_rate_storage.py', 'literature_binding_interaction_calculations.py'])
def test_unknown_actual_dependency_bytes_reject_before_publication(tmp_path, changed_file):
    package = tmp_path / 'dependency_copy'
    package.mkdir()
    for name in _dependencies()['sha256']:
        (package / name).write_bytes(source_file(name).read_bytes())
    with (package / changed_file).open('ab') as stream:
        stream.write(b'\n# Deliberately unknown dependency version for rejection test.\n')
    (package / 'literature_implementation_sources.py').write_bytes(Path(source_owner.__file__).read_bytes())
    source_spec = importlib.util.spec_from_file_location('gene_annotation_episode.episodic_workflow.root.a105._dependency_sources_142', package / 'literature_implementation_sources.py')
    copied_source_owner = importlib.util.module_from_spec(source_spec)
    source_spec.loader.exec_module(copied_source_owner)
    module_path = package / 'literature_binding_interaction_storage.py'
    spec = importlib.util.spec_from_file_location('gene_annotation_episode.episodic_workflow.root.a105.library._dependency_rejection_142', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.source_file = copied_source_owner.source_file
    store, context, args = setup(tmp_path / 'state')
    with store:
        repo = module.LiteratureBindingInteractionRepository(store, context.run_id)
        with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
            repo.populate(context, args, 'unknown-implementation')
        assert store.db.execute('SELECT count(*) FROM literature_binding_interaction_operations').fetchone()[0] == 0
        assert not [row for row in store.list('source') if row.get('provider') == module.PROVIDER]

def test_current_native_cells_record_actual_dependency_and_keep_subset_custody(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureBindingInteractionRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'current')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['implementation_dependencies'] == _dependencies()
        rows = project(repo, outcome)
        assert [row['component'] for row in rows] == list(COMPONENTS)
        assert [row['value'] for row in rows[:7]] == [5, 40, 2, 4, 8, 2, 4]
        owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        parent = replace(owner, episode_id='parent')
        repo.receive_cells(parent, [rows[6]], 'manual-admission')
        assert repo.fact_cells(parent, [outcome['result']['sheet_ref']], components=COMPONENTS) == [rows[6]]
        assert repo.populate(context, args, 'current') == outcome
        assert not store.list('observation') and (not store.list('assessment'))

