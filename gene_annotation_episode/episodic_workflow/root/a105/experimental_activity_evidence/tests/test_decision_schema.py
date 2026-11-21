"""The A105 head's first model request, checked offline against the model endpoint's rules for a strict output
schema (``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model
call. The head is linked in its real world (``grading_world``: the problem, a synthetic source, the assay reference
and the proposed annotation, held in custody; the published process library frozen into the test's directory) with
its whole subtree registered, with the public API, and stepped with ``EpisodeRun.next_decision``: ``decide`` builds
the request the model would be sent; the model is not asked."""
import asyncio
import importlib
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, ModelRequest, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    INPUT_CHARACTERS, admitted_by_provider, measures, violations)

from .. import task
from ..episode import ExperimentalActivityEvidence
from .grading_world import SETTINGS, held_world

LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'


def subtree():
    root = Path(__file__).resolve().parent.parent
    package = ExperimentalActivityEvidence.__module__.rsplit('.', 1)[0]
    bindings = []
    for path in sorted(root.rglob('episode.py')):
        relative = path.relative_to(root).parent.parts
        if 'tests' in relative:
            continue
        module = importlib.import_module('.'.join((package, *relative, 'episode')))
        bindings.extend(value() for value in vars(module).values()
                        if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding)
    return bindings


def unbuilt(name):
    def build():
        raise LookupError('service_not_built_in_this_world:' + name)
    return build


def test_the_decision_schema_is_one_the_model_endpoint_takes(tmp_path):
    held = held_world(tmp_path)
    library = task.ExperimentalActivityEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    selection = {**held['input']['assignment']['selection'], 'evidence_axis': library.reference('A105'),
                 'thought_pattern': thought,
                 'child_tool_info': [{'name': name, 'resources': 'api'} for name in task.REGISTRY_NAMES]}
    entry = {**held['input'], 'assignment': {**held['input']['assignment'], 'selection': selection}}
    bindings = subtree()
    settings = {**SETTINGS, 'library_directory': str(library.directory)}
    collaborators = {'store': held['store'],
                     'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                     'continuation': {binding.binding_path: settings for binding in bindings},
                     'services': {name: unbuilt(name) for binding in bindings for name in binding.services}}
    run = link(BindingRegistry(bindings), ExperimentalActivityEvidence.binding_path, entry,
               run_id='a105-decision-schema', journal=RunJournal(tmp_path / 'journal.sqlite3'),
               collaborators=collaborators)
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    text, schema = admitted_by_provider(request, tmp_path / 'provider')
    print('SCHEMA', measures(schema), 'INPUT', len(text))
    found = violations(schema)
    assert found == [], found
    assert len(text) <= INPUT_CHARACTERS
    options = schema['properties']['selection']['anyOf']
    assert {option['properties']['slot']['enum'][0] for option in options
            if option['properties']['kind']['enum'] == ['child']} == set(task.CHILD_SLOTS)
    held['store'].close()
