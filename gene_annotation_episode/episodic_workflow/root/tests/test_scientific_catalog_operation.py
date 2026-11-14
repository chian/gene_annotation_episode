"""Root/private catalog boundary using the existing genuine A105 fixture.

These are metadata calls, not executed iterator units or scientific work.
"""
import asyncio

from jsonschema import Draft202012Validator, ValidationError
import pytest

from gene_annotation_episode.episodic_workflow.root.tests.private_setup_support import (
    actual_private_root, actual_rows,
)


@pytest.fixture
def root(tmp_path):
    with actual_private_root(tmp_path) as value:
        before = actual_rows(value)
        yield value
        assert actual_rows(value) == before


def metadata_operation(root, name, arguments):
    return asyncio.run(root.workflow.execute(root.episode.source, name, arguments,
        decision_index=0,
        operation_key=root.workflow.run_id + ':' + root.episode.source.episode_id + ':0',
        _composition_lookup=True))


def test_selected_private_catalog_callback_receives_root_library_executor(root, monkeypatch):
    arguments = {'option_id': 'P01'}
    expected = root.head.library.execute('process.entry', arguments)
    original_callback = root.head.execute_catalog_operation
    original_library = root.head.execute_scientific_library
    callbacks, library_calls = [], []

    async def observe_callback(*args, **kwargs):
        callbacks.append((args, kwargs))
        return await original_callback(*args, **kwargs)

    def observe_library(context, name, supplied):
        library_calls.append((context, name, supplied))
        return original_library(context, name, supplied)

    monkeypatch.setattr(root.head, 'execute_catalog_operation', observe_callback)
    monkeypatch.setattr(root.head, 'execute_scientific_library', observe_library)
    assert metadata_operation(root, 'process.entry', arguments) == expected
    assert len(callbacks) == len(library_calls) == 1
    args, kwargs = callbacks[0]
    assert args[0] is root.workflow and args[1] is root.episode.source
    assert args[2] == 'process.entry' and args[3] is arguments
    assert kwargs['validator_type'] is Draft202012Validator
    assert kwargs['validation_error'] is ValidationError
    assert callable(kwargs['library_executor'])
    context, name, supplied = library_calls[0]
    assert context == root.context and name == 'process.entry' and supplied is arguments


def test_binding_without_catalog_callback_keeps_direct_root_library_execution(root, monkeypatch):
    arguments = {'option_id': 'P01'}
    expected = root.head.library.execute('process.entry', arguments)
    monkeypatch.setattr(root.head, 'execute_catalog_operation', None)
    monkeypatch.setattr(root.head, 'execute_scientific_library', None)
    assert metadata_operation(root, 'process.entry', arguments) == expected
    assert expected['status'] == 'completed'
    assert 'annotation_support_routes' not in expected['result']


@pytest.mark.parametrize('private_callback', [True, False], ids=['private', 'fallback'])
def test_invalid_literal_retrieval_outcome_survives_catalog_boundary(root, monkeypatch, private_callback):
    if not private_callback:
        monkeypatch.setattr(root.head, 'execute_catalog_operation', None)
    # Whitespace satisfies the catalog's string schema but the actual retriever
    # rejects it. This observes its returned invalid outcome after dispatch.
    assert metadata_operation(root, 'process.tools', {'investigation': ' '}) == {
        'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
        'result': None, 'feedback': {'code': 'scientific_tool_investigation_invalid'},
    }
