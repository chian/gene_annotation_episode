"""Pure service/mother checks with explicit engineering instruction bodies."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_records import scientific_digest
from gene_annotation_episode.scientific_support_metadata import (
    annotation_policy_routes, support_observation_kinds)
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_scientific_process_episodes import ContractLibrary, ContractServices, make_context


def annotation_binding(projector, *, fixed_case=False):
    definition = projector.as_record()
    if fixed_case:
        definition = {'policy_source_sha256': 'a' * 64,
            'policy_parameters_sha256': 'b' * 64, 'definition': definition}
    return {'projector': 'gene_annotation_episode.scientific_credit.AnnotationSupportScore',
        'versions': {'requirement': 'same_caller_injected_executable'},
        'definition': definition, 'scope_source': 'context.scope',
        'meaning': 'The caller\'s separate annotation support.'}


@pytest.mark.parametrize('fixed_case', [False, True])
def test_service_exposes_actual_policy_without_projection_or_state_access(fixed_case):
    policy = replace(CreditPolicy(), observation_axes=(('alignment', 'mechanistic'),))
    projector = AnnotationSupportScore(policy)
    binding = annotation_binding(projector, fixed_case=fixed_case)
    workflow = SimpleNamespace(run_id='fixture-run', project_annotation_score=projector,
        annotation_score_binding=binding)
    original = deepcopy(binding)
    routes = WorkflowServices(workflow).scientific_support_routes(
        SimpleNamespace(run_id='fixture-run'),
        observation_kinds=['alignment', 'profile_match'])
    assert routes == annotation_policy_routes(projector, binding,
        observation_kinds=['alignment', 'profile_match'])
    assert routes['status'] == 'available'
    assert routes['annotation_binding_sha256'] == scientific_digest(original)
    assert routes['routes'] == [
        {'observation_kind': 'alignment', 'status': 'mapped', 'axis': 'mechanistic'},
        {'observation_kind': 'profile_match', 'status': 'unmapped', 'axis': None}]
    routes['policy']['observation_axes'].append(['profile_match', 'empirical'])
    assert workflow.annotation_score_binding == original
    assert projector.policy is policy
    # The host double deliberately has no store, projection or controller.


def test_service_authenticates_run_before_reading_any_caller_binding():
    services = WorkflowServices(SimpleNamespace(run_id='fixture-run'))
    with pytest.raises(ValueError, match='scientific_support_routes_receiver_identity_mismatch'):
        services.scientific_support_routes(SimpleNamespace(run_id='foreign-run'),
            observation_kinds=['alignment'])


@pytest.mark.parametrize('availability', ['available', 'unbound', 'missing', 'mismatched', 'custom'])
def test_mother_preserves_complete_support_and_original_form_when_routes_unavailable(
        tmp_path, availability):
    library, services = ContractLibrary(), ContractServices()
    projector = AnnotationSupportScore(CreditPolicy())
    binding = annotation_binding(projector)
    if availability == 'unbound':
        projector, binding = None, None
    elif availability == 'missing':
        binding['definition'] = None
    elif availability == 'mismatched':
        binding['definition']['policy']['scale'] += 1
    elif availability == 'custom':
        projector = lambda *_args, **_kwargs: 0
    host = SimpleNamespace(run_id='fixture-run', project_annotation_score=projector,
        annotation_score_binding=binding)
    services.scientific_support_routes = WorkflowServices(host).scientific_support_routes
    tools = ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=services.available)
    mother = ScientificProcessEpisodes(services, library=library, tool_library=tools,
        child_roles=('scientific_process', 'literature'))
    context = make_context(mother)
    original_request = plain(context.request)
    original_assignment = plain(context.assignment)
    body = library.resolve(context.assignment['selection']['annotation_ref'])
    frame = mother.decision_context(context, {})['scientific_process']
    assert frame['annotation'] == {key: body[key] for key in ('id', 'name', 'description', 'support')}
    assert frame['annotation_support_routes'] == annotation_policy_routes(projector, binding,
        observation_kinds=support_observation_kinds(body))
    assert frame['annotation_support_routes']['status'] == (
        'available' if availability == 'available' else 'unavailable')
    assert frame['selection'] == original_assignment['selection']
    assert frame['assignment'] == original_assignment
    assert plain(context.request) == original_request
    assert mother.credit_view(context, {}) == {'credit': 7, 'binding': 'unchanged_fixture_projection'}
    frame['annotation']['support']['qualifications'].append('Detached fixture mutation.')
    assert library.resolve(context.assignment['selection']['annotation_ref']) == body
    assert not services.calls and not services.preparation_reads
    outcome = asyncio.run(mother.execute(context, 'fixture.inspect', {'value': 1},
        'available-scientific-operation'))
    assert outcome['status'] == 'completed'
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert len(services.calls) == 1


def test_new_mother_rejects_legacy_heading_without_upgrading_library_body(tmp_path):
    library, services = ContractLibrary(), ContractServices()
    legacy = {'id': 'A01', 'slot': 'annotation_distinction',
        'name': 'Historical claim heading', 'description': 'Historical fixture only.',
        'evidence': [], 'claim_scope': 'A claimed property.',
        'distinctions': ['One claim versus another.'],
        'not_established': ['No scientific support body.'], 'boundary': 'Historical provenance.'}
    library.entries['A01'] = legacy
    library.library_id = scientific_digest(library.entries)
    original = deepcopy(library.entries)
    tools = ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=services.available)
    mother = ScientificProcessEpisodes(services, library=library, tool_library=tools,
        child_roles=('scientific_process',))
    with pytest.raises(ValueError, match='scientific_support_metadata_required'):
        make_context(mother)
    assert library.entries == original
    assert library.resolve(library.reference('A01')) == legacy
