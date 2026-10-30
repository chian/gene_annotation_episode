"""Actual scientific-tool consumers with controlled utility source bytes.

No native executable, acquisition or scientific measurement is fabricated.
The scientific binding, selected tools, Store and utility grant resolver are real.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_records import SELECTION_VERSION, scientific_invocation_ref
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary

from test_blast_utility_episode_wiring_632 import host, context, source
from test_scientific_process_episodes import ContractLibrary


NAMES = ('material.from_source', 'material.parse', 'material.read', 'source.read', 'source.locate')


@pytest.fixture
def consumer(host):
    h = host
    workflow = SimpleNamespace(store=h.store, run_id=h.journal.run_id,
        tools=h.family.tool_registry, episode_bindings=EpisodeBindingRegistry([h.family]),
        scientific_process_binding=None)
    services = WorkflowServices(workflow)
    library = ContractLibrary()
    tool_library = ScientificToolLibrary.freeze(h.tmp_path / 'selected-material-tools',
        catalog=[row for row in services.tool_information_catalog(h.scope) if row['name'] in NAMES],
        tool_info=True)
    scientific = ScientificProcessEpisodes(services, library=library,
        tool_library=tool_library, child_roles=('scientific_process',))
    workflow.scientific_process_binding = scientific
    workflow.episode_bindings = EpisodeBindingRegistry([h.family, scientific])
    parent = context(h, 'annotation', {})
    selected = {'selection': {'version': SELECTION_VERSION,
        'evidence_axis': library.reference('A01'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': name, 'resources': 'local'} for name in NAMES]},
        'evidence_refs': [], 'constraints': {}, 'context': {}}
    invocation = {'objective': 'Inspect explicitly supplied evidence bytes',
        'purpose': 'Return only the requested material measurements',
        'report_schema': obj({}), 'initial_report': {}}
    filled = scientific.prepare_invocation(parent, 'scientific_process', selected,
        h.scope, 'controlled-commission', invocation=invocation)

    def child(index=0):
        path = (*parent.path, ('scientific_process', 'child_' + str(index)))
        request = {'goal': {'objective': invocation['objective']},
            'report_contract': {'decision': invocation['purpose'],
                'measurements': {'schema': invocation['report_schema']}},
            'message': {'scope': deepcopy(h.scope), 'episode_assignment': filled['assignment'],
                'scientific_invocation_ref': scientific_invocation_ref(h.journal.run_id, path),
                'initial_report': {}, 'scientific_process': filled['scientific_process']}}
        ctx = BindingContext(h.journal.run_id, EpisodeRef(h.journal.run_id, path).episode_id,
            'scientific_process', path, h.scope, filled['assignment'], request)
        h.journal.save('runtime_episodes', {'episode_id': ctx.episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
        h.receipts.bind(ctx.episode_id, parent.episode_id)
        return ctx

    return SimpleNamespace(h=h, workflow=workflow, services=services,
        scientific=scientific, context=child(), child=child)


def execute(c, name, args, *, key=None, ctx=None):
    ctx = ctx or c.context
    ctx = replace(ctx, received_record_refs=tuple(c.h.receipts.known(ctx.episode_id)))
    return asyncio.run(c.scientific.execute(ctx, name, args, key or 'selected-' + name))


def arguments(c, name, reference):
    if name == 'material.from_source':
        return {'source_ref': reference, 'format': 'text'}
    if name == 'source.read':
        return {'source_ref': reference, 'representation': 'original', 'limit': 8}
    if name == 'source.locate':
        return {'source_ref': reference, 'representation': 'original', 'needle': 'fixture'}
    # A preexisting wrapper is deliberately supplied to expose the separate
    # parse/read consumer boundary; it is not a new grant of its original bytes.
    material = c.h.store.register_material(source_ref=reference, format='text')
    return {'material_ref': material['id'], **({'format': 'text'} if name == 'material.parse' else {'limit': 8})}


@pytest.mark.parametrize('name', NAMES)
def test_source_only_utility_return_cannot_open_or_wrap_unselected_bytes(consumer, monkeypatch, name):
    c = consumer
    reference, bundle, auxiliary = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference], kind='initial')
    args = arguments(c, name, reference)
    count = c.h.store.db.execute('SELECT count(*) FROM records').fetchone()[0]
    import gene_annotation_episode.materials as materials
    monkeypatch.setattr(materials, 'artifact_path', lambda *_: pytest.fail('unselected bytes opened'))
    result = execute(c, name, args)
    assert result['status'] == 'invalid', result
    assert result['feedback']['code'] == 'native_blast_utility_source_artifact_not_granted'
    assert result['record_refs'] == []
    assert c.h.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == count
    assert c.h.store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
    assert bundle not in c.h.receipts.known(c.context.episode_id)
    assert auxiliary not in c.h.receipts.known(c.context.episode_id)


@pytest.mark.parametrize('name', NAMES)
def test_explicit_selected_bundle_bytes_reach_the_same_consumers(consumer, name):
    c = consumer
    reference, bundle, _ = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference, bundle], kind='initial')
    args = arguments(c, name, reference)
    result = execute(c, name, args)
    assert result['status'] == 'completed', result
    assert execute(c, name, args) == result


def test_unrelated_auxiliary_grant_does_not_grant_bundle_or_replay(consumer):
    c = consumer
    reference, bundle, auxiliary = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference, bundle], kind='initial')
    args = arguments(c, 'material.from_source', reference)
    original = execute(c, 'material.from_source', args, key='original-wrapper')
    assert original['status'] == 'completed'
    sibling = c.child(1)
    c.h.receipts.receive(sibling.episode_id, [reference, auxiliary], kind='initial')
    rejected = execute(c, 'material.from_source', args, key='original-wrapper', ctx=sibling)
    assert rejected['status'] == 'invalid'
    assert rejected['feedback']['code'] == 'native_blast_utility_source_artifact_not_granted'
    assert execute(c, 'material.from_source', args, key='original-wrapper') == original


def test_source_read_text_fallback_checks_the_actual_bundle(consumer):
    c = consumer
    reference, bundle, _ = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference], kind='initial')
    args = {'source_ref': reference, 'limit': 7}
    assert execute(c, 'source.read', args, key='no-bundle')['status'] == 'invalid'
    c.h.receipts.receive(c.context.episode_id, [bundle], kind='initial')
    result = execute(c, 'source.read', args, key='selected-bundle')
    assert result['status'] == 'completed'
    assert result['result']['representation'] == 'original'
    assert result['result']['artifact_ref'] == bundle


def test_ordinary_caller_material_and_source_locate_preserve_behavior(consumer):
    c = consumer
    material = c.h.store.register_material(data=b'ordinary literal fixture', format='text')
    reference = material['source_ref']
    c.h.receipts.receive(c.context.episode_id, [reference], kind='initial')
    for name in NAMES:
        result = execute(c, name, arguments(c, name, reference))
        assert result['status'] == 'completed', (name, result)


@pytest.mark.parametrize('representation', ['text', 'stdout', 'stderr'])
def test_each_selected_representation_requires_its_own_artifact_grant(consumer, representation):
    c = consumer
    reference, bundle, auxiliary = source(c.h)
    body = {key: value for key, value in c.h.store.get(reference).items()
        if key not in {'id', 'record_type', 'origin'}}
    selected = c.h.store.artifact((representation + ' controlled fixture').encode())
    body[representation + '_ref'] = selected
    body['auxiliary_artifact_refs'] = [auxiliary, selected]
    reference = c.h.store.put('source', body, origin='tool')['id']
    c.h.receipts.receive(c.context.episode_id, [reference, bundle], kind='initial')
    args = {'source_ref': reference, 'representation': representation, 'limit': 100}
    denied = execute(c, 'source.read', args, key='without-selected-stream')
    assert denied['status'] == 'invalid'
    assert denied['feedback']['code'] == 'native_blast_utility_source_artifact_not_granted'
    c.h.receipts.receive(c.context.episode_id, [selected], kind='initial')
    allowed = execute(c, 'source.read', args, key='with-selected-stream')
    assert allowed['status'] == 'completed', allowed
    assert allowed['result']['artifact_ref'] == selected
    assert allowed['result']['representation'] == representation
    assert allowed['result']['text'] == representation + ' controlled fixture'


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('receipt_kind,expected_code', [
    ('decision_input', 'native_blast_utility_source_artifact_not_granted'),
    ('child_form', 'native_blast_utility_return_successful_return_required'),
])
def test_different_source_wrapper_does_not_erase_utility_artifact_ownership(
        consumer, name, receipt_kind, expected_code):
    c = consumer
    _, bundle, _ = source(c.h)
    wrapper = c.h.store.put('source', {'provider': 'controlled-wrapper', 'artifact_ref': bundle,
        'accession': None, 'uri': None, 'retrieved_at': None,
        'text_ref': None, 'request_ref': None, 'version': 'fixture_v1'}, origin='tool')['id']
    # Metadata lookup does not grant bytes; a claimed child-form receipt with
    # no successful original form must also fail the existing return check.
    c.h.receipts.receive(c.context.episode_id, [wrapper], kind=receipt_kind)
    result = execute(c, name, arguments(c, name, wrapper))
    assert result['status'] == 'invalid', result
    assert result['feedback']['code'] == expected_code


def test_missing_utility_owner_does_not_make_known_utility_bytes_ordinary(consumer):
    c = consumer
    reference, bundle, _ = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference, bundle], kind='initial')
    c.workflow.episode_bindings = EpisodeBindingRegistry([c.scientific])
    result = execute(c, 'source.read', arguments(c, 'source.read', reference))
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'native_blast_utility_source_artifact_not_granted'
    ordinary = c.h.store.register_material(data=b'ordinary fixture', format='text')
    assert execute(c, 'source.read', arguments(c, 'source.read', ordinary['source_ref']),
        key='ordinary-without-utility-owner')['status'] == 'completed'


def test_unavailable_stream_retains_existing_structured_feedback(consumer):
    c = consumer
    reference, bundle, _ = source(c.h)
    c.h.receipts.receive(c.context.episode_id, [reference, bundle], kind='initial')
    result = execute(c, 'source.read', {'source_ref': reference, 'representation': 'stderr'})
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'source_representation_unavailable'
    assert result['feedback']['detail'] == {'representation': 'stderr',
        'available_representations': ['original']}


def test_artifact_grants_cannot_be_checked_under_another_run(consumer):
    c = consumer
    reference, _, _ = source(c.h)
    with pytest.raises(ValueError, match='source_byte_context_run_mismatch'):
        c.services.authenticate_source_byte_operands(replace(c.context, run_id='other-run'),
            'source.read', {'source_ref': reference})

