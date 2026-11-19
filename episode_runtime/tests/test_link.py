"""Every way a link is refused, and an entry below scoped ancestors (an inner entry)."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, LinkError as LinkErrorType, MissingBinding, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from method_loop import EpisodeGoal, FormError
from .fact_collection.episode import FactCollection
from .fact_collection.fact_extraction.episode import FactExtraction
from .test_system_recording import CHILD, CONTINUATION, PARENT, SETTINGS, child_path, parent_path


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    subject = store.artifact(json.dumps({'name': 'GeneX', 'function': 'kinase'}), 'application/json')
    yield {'store': store, 'subject': subject, 'journal': RunJournal(tmp_path / 'journal.sqlite3'),
           'provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)}
    store.close()


def good(world):
    return {'store': world['store'], 'model_provider': world['provider'], 'continuation': CONTINUATION,
            'services': {}}


def parent_entry(world):
    return {'assignment': {'subject_refs': [world['subject']]}, 'message': {'fields': ['name']}, 'selection': []}


def try_link(world, collaborators, run_id='refused', registry=None, entry=None, **options):
    return link(registry or BindingRegistry([FactCollection(), FactExtraction()]), PARENT,
                entry or parent_entry(world), run_id=run_id, journal=world['journal'],
                collaborators=collaborators, **options)


def test_a_missing_or_nonconforming_collaborator_is_refused_before_the_run_is_recorded(world):
    for name in ('store', 'model_provider', 'continuation', 'services'):
        collaborators = {key: value for key, value in good(world).items() if key != name}
        with pytest.raises(LinkErrorType, match='collaborator_required:' + name):
            try_link(world, collaborators)

    class NoStore:
        pass

    class SyncProvider:
        def complete(self, *args):
            return {}
    with pytest.raises(LinkErrorType, match='collaborator_interface:store:get,get_artifact,put,artifact'):
        try_link(world, {**good(world), 'store': NoStore()})
    with pytest.raises(LinkErrorType, match='collaborator_interface:model_provider:complete:async'):
        try_link(world, {**good(world), 'model_provider': SyncProvider()})
    with pytest.raises(LinkErrorType, match='collaborator_interface:continuation:mapping'):
        try_link(world, {**good(world), 'continuation': []})
    with pytest.raises(LinkErrorType, match='collaborator_interface:services:factory:thing'):
        try_link(world, {**good(world), 'services': {'thing': 3}})
    assert world['journal'].db.execute('SELECT count(*) FROM runs').fetchone()[0] == 0


def test_settings_for_every_binding_and_a_factory_for_every_declared_service_are_required(world, episode_variant):
    with pytest.raises(LinkErrorType, match='continuation_settings_required:fact_collection/fact_extraction'):
        try_link(world, {**good(world), 'continuation': {PARENT: SETTINGS}})

    needing = episode_variant(PARENT, {'task.py': [('SERVICES = ()', "SERVICES = ('needed',)")]}).FactCollection
    registry = BindingRegistry([needing(), FactExtraction()])
    with pytest.raises(LinkErrorType, match='service_required:fact_collection:needed'):
        try_link(world, good(world), registry=registry)
    assert world['journal'].db.execute('SELECT count(*) FROM runs').fetchone()[0] == 0


def test_a_yield_controller_that_is_not_a_yield_control_controller_is_refused(world, episode_variant):
    other = episode_variant(PARENT, {'yield_estimator.py': [(
        "    return CompletionYieldController('fact_collection', initial_credit, settings['cost'], TARGET,\n"
        "                                     settings['parameters'])", '    return object()')]}).FactCollection
    registry = BindingRegistry([other(), FactExtraction()])
    with pytest.raises(LinkErrorType, match='yield_controller_must_be_a_yield_control_controller:fact_collection'):
        asyncio.run(try_link(world, good(world), registry=registry).run())


def test_an_unregistered_entry_and_a_foreign_entry_input_are_refused(world):
    with pytest.raises(MissingBinding, match='binding_not_registered:nowhere'):
        link(BindingRegistry([FactCollection(), FactExtraction()]), 'nowhere', {}, run_id='x',
             journal=world['journal'], collaborators=good(world))
    with pytest.raises(ValueError, match='entry_input_requires_exactly:assignment,message,selection'):
        try_link(world, good(world), entry={'assignment': {'subject_refs': []}, 'message': {}})
    with pytest.raises(FormError, match='entry_assignment:fact_collection_missing_field:subject_refs'):
        try_link(world, good(world), entry={'assignment': {}, 'message': {}, 'selection': []})


def parent_goal_record():
    return EpisodeGoal.root(objective=FactCollection.goal,
                            result_contract={'unit': FactCollection.unit, 'result': FactCollection.result}
                            ).as_record()


def ancestor(key='top', goal=None, path=PARENT):
    return {'binding_path': path, 'key': key, 'goal': parent_goal_record() if goal is None else goal}


def child_entry(world):
    return {'assignment': {'source_refs': [world['subject']], 'field': 'name'}, 'message': {}, 'selection': []}


def test_an_entry_below_scoped_ancestors_runs_as_an_inner_node(world):
    registry = BindingRegistry([FactCollection(), FactExtraction()])
    linked = link(registry, CHILD, child_entry(world), run_id='inner', journal=world['journal'],
                  collaborators=good(world), ancestors=[ancestor()], key='extraction_9')
    result = asyncio.run(linked.run())['result'].as_record()
    assert result['fact'] == 'GeneX'
    path = (*parent_path('top'), ('fact_collection__fact_extraction', 'extraction_9'))
    assert [row['path'] for row in world['journal'].episodes('inner')] == [[list(part) for part in path][0:2]]
    assert [label for label, *_ in world['journal'].units('inner', path)] == ['tool:extract_field:0']
    # The ancestor is never built, run or journaled.
    assert world['journal'].units('inner', parent_path('top')) == []


def test_every_ancestry_refusal(world):
    registry = BindingRegistry([FactCollection(), FactExtraction()])

    def inner(ancestors, entry_path=CHILD, entry=None):
        return link(registry, entry_path, entry or child_entry(world), run_id='bad', journal=world['journal'],
                    collaborators=good(world), ancestors=ancestors)
    with pytest.raises(LinkErrorType, match='ancestor_requires_binding_path_key_goal'):
        inner([{'binding_path': PARENT}])
    with pytest.raises(LinkErrorType, match='ancestor_key_required:fact_collection'):
        inner([ancestor(key='')])
    child_goal = EpisodeGoal.child(EpisodeGoal.from_record(parent_goal_record()), objective='x',
                                   result_contract={'unit': 'u', 'result': 'r'}).as_record()
    with pytest.raises(LinkErrorType, match='top_ancestor_goal_must_be_a_root_goal'):
        inner([ancestor(goal=child_goal)])
    with pytest.raises(LinkErrorType, match='ancestor_goal_does_not_refine_its_parent'):
        inner([ancestor(), ancestor(key='second', goal=parent_goal_record(), path=CHILD)])
    with pytest.raises(LinkErrorType, match='ancestor_is_not_a_declared_child:fact_collection'):
        inner([ancestor(path=CHILD), ancestor(key='second', goal=child_goal)])
    with pytest.raises(LinkErrorType, match='entry_is_not_a_declared_child_of_its_parent:fact_collection'):
        inner([ancestor(path=CHILD)], entry_path=PARENT, entry=parent_entry(world))



