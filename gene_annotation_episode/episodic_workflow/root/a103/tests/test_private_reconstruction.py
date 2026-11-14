"""Literal saved binding recreation only; no receiving-owner or science claim."""
from copy import deepcopy
from contextlib import ExitStack
from unittest.mock import patch
import pytest
from .reconstruction_checks import (AXIS, HOMES, EXECUTION_HOMES, MONITOR_HOMES,
    HPC_HOMES, construction_case, forbidden, own)


@pytest.fixture(scope='module')
def case(tmp_path_factory):
    with construction_case(tmp_path_factory.mktemp('private-reconstruction')) as value:
        yield value


@pytest.mark.parametrize('home', HOMES)
def test_exact_private_binding_recreated(home, case):
    assert case.report['constructors'][home]['status'] == 'returned'
    assert case.report['composition']['status'] == 'returned', case.report['composition']
    assert len(case.rebuilt.bindings) == len(HOMES) == 43
    recreated = {binding.binding_path: binding for binding in case.rebuilt.bindings}
    original, actual = case.direct[home], recreated[home]
    assert actual is not original and type(actual) is type(original)
    assert actual.as_record() == original.as_record()
    assert actual.services is case.services
    if home in EXECUTION_HOMES or home in HPC_HOMES:
        assert actual.store is case.store and actual.run_id == case.journal.run_id
        assert actual.directory == original.directory
    if home in EXECUTION_HOMES:
        assert actual.tool_registry is case.tools
    registry = own('episode_bindings').EpisodeBindingRegistry(case.rebuilt.bindings)
    assert registry.for_binding_path(home) is actual
    for role in actual.roles:
        if actual.credit_kind(role) != 'scientific':
            assert case.rebuilt.role_credit_projectors[role] is forbidden
            assert dict(case.rebuilt.role_credit_definitions[role]) == {'fixture': 'caller_owned', 'role': role}


def test_current_scientific_descriptor_is_exact(case):
    assert case.report['current_scientific_compatibility'] is True
    descriptor = case.direct['scientific_process'].as_record()
    tampered = deepcopy(descriptor)
    tampered['implementation_sha256'] = '0' * 64
    assert not case.composition.scientific_binding_compatible(tampered, descriptor)
    assert not case.composition.scientific_binding_compatible(descriptor, tampered)


@pytest.mark.parametrize('change', ['unknown', 'foreign', 'duplicate', 'version', 'extra_descriptor',
    'missing_configuration', 'extra_configuration', 'missing_required', 'fingerprint_type', 'fingerprint_invalid'])
def test_rejected_descriptor_does_not_enter_any_constructor(change, case):
    assert len(case.direct) == 43
    rows = deepcopy(case.descriptors)
    row = rows[-1]
    if change == 'unknown':
        row['binding_id'] = 'unknown_private_episode'
    elif change == 'foreign':
        row['binding_id'] = 'gene_annotation_episode.episodic_workflow.root.a110.hpc_work_planning'
    elif change == 'duplicate':
        rows.append(deepcopy(rows[0]))
    elif change == 'version':
        row['version'] = 'future_unknown_version'
    elif change == 'extra_descriptor':
        row['implementation_module'] = 'untrusted.module'
    elif change == 'missing_configuration':
        del row['configuration']
    elif change == 'extra_configuration':
        row['configuration']['unrelated_role_switch'] = True
    elif change == 'missing_required':
        del row['configuration']['resources']
    elif change == 'fingerprint_type':
        row['implementation_sha256'] = 5
    else:
        row['implementation_sha256'] = 'not-a-source-hash'
    arguments = dict(case.arguments, descriptors=rows)
    error_type = own('method_loop.durable').DurableExecutionError
    with ExitStack() as stack:
        for cls in {type(binding) for binding in case.direct.values()}:
            stack.enter_context(patch.object(cls, '__init__', forbidden))
        with pytest.raises(error_type) as caught:
            case.composition.compose_episode_bindings(case.services, **arguments)
    assert caught.value.failure['code'] == ('identity_conflict' if change == 'duplicate' else 'unavailable_binding')


@pytest.mark.parametrize('change', ['source_hash', 'library_record', 'missing_directory', 'unknown_version'])
def test_direct_scientific_reopen_keeps_saved_identity(change, case):
    descriptor = deepcopy(case.direct['scientific_process'].as_record())
    directory = case.arguments['directory']
    if change == 'source_hash':
        descriptor['implementation_sha256'] = '0' * 64
    elif change == 'library_record':
        descriptor['configuration']['library']['library_id'] = 'changed'
    elif change == 'missing_directory':
        directory = case.output / 'absent-workflow'
    else:
        descriptor['version'] = 'scientific_process_episodes_v10'
    with pytest.raises(own('method_loop.durable').DurableExecutionError):
        case.composition.reopen_scientific_binding(case.services, descriptor=descriptor, directory=directory)


def test_required_projector_is_not_inferred(case):
    descriptor = case.direct[EXECUTION_HOMES[0]].as_record()
    with pytest.raises(own('method_loop.durable').DurableExecutionError) as caught:
        case.composition.compose_episode_bindings(case.services,
            **dict(case.arguments, descriptors=[descriptor], role_credit_bindings={}))
    assert caught.value.failure['code'] == 'unavailable_binding'
    assert caught.value.failure['affected_refs'] == ['launch']


def test_monitor_requires_actual_execution_backend(case):
    descriptor = case.direct[MONITOR_HOMES[0]].as_record()
    with pytest.raises(own('method_loop.durable').DurableExecutionError) as caught:
        case.composition.compose_episode_bindings(case.services,
            **dict(case.arguments, descriptors=[descriptor], execution_backend=None))
    assert caught.value.failure['affected_refs'] == ['execution_backend']


def test_wrong_journal_store_rejected(case):
    from types import SimpleNamespace
    with pytest.raises(own('method_loop.durable').DurableExecutionError) as caught:
        case.composition.compose_episode_bindings(case.services,
            **dict(case.arguments, journal=SimpleNamespace(store=object(), run_id=case.journal.run_id)))
    assert caught.value.failure['code'] == 'identity_conflict'
    assert caught.value.failure['affected_refs'] == ['journal.store']


def test_no_implicit_provider_from_reconstruction(case):
    assert case.report['composition']['status'] == 'returned'
    assert case.rebuilt.progress_provider is not None
    assert case.rebuilt.resource_capabilities == ()
    # The unchanged original capability tail recognizes only its legacy name.
    # Explicit private capability aggregation remains a separate ownership stage.


def test_a103_existing_directed_scientific_compatibility_is_preserved(case):
    if AXIS != 'a103':
        pytest.skip('A102 has no historical directed compatibility table')
    for old, new in case.composition._SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY:
        original = {'version': 'scientific_process_episodes_v8', 'binding_id': 'scientific_process',
            'implementation_sha256': old, 'configuration': {'fixture': 'preserved'}}
        current = dict(original, implementation_sha256=new)
        assert case.composition.scientific_binding_compatible(current, original)
