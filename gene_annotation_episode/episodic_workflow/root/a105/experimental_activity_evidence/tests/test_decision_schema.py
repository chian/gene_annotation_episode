"""The A105 head's first model request, checked offline against the model endpoint's rules for a strict output
schema (``provider_schema_rules``): the endpoint refuses a schema that breaks one with HTTP 400 at the first model
call. The head is linked in its real world (``grading_world``: the problem, a synthetic source, the assay reference
and the proposed annotation, held in custody; the published process library frozen into the test's directory) with
its whole subtree registered, with the public API, and stepped with ``EpisodeRun.next_decision``: ``decide`` builds
the request the model would be sent; the model is not asked."""
import asyncio
import importlib
import json
import types
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


# The answer the head's model wrote in the first real run (runs/a105_head_real_20261121_01/workspace_g, journal table
# model_calls, the response of call 1), with the run's records replaced by the ones of this test's world. The scope
# travels as JSON text, as the model endpoint takes no open object.
def real_literature_answer(proposed, scope):
    return {'selection': {
        'arguments': {
            'assignment': {
                'literature_task': {'credit_unit': 1.0, 'evidence_axis': 'A105', 'kind': 'verified_source_leads',
                                    'version': 'literature_local_task_v1', 'yield_settings': None},
                'proposed_annotation_ref': proposed, 'question_context_refs': [proposed],
                'version': 'literature_assignment_v1'},
            'objective': 'Investigate whether experiments directly establish binding between the supplied Caulobacter '
                         'PopZ and ParB proteins. Verify the assayed constructs against the supplied sequences, '
                         'distinguish direct binding from localization or genetic effects, and grade each applicable '
                         'result with its controls, conditions, measurements, and unresolved correspondence.',
            'scope': json.dumps(scope, separators=(',', ':'))},
        'kind': 'child', 'slot': 'literature'}}


def test_the_literature_commission_the_model_writes_is_built_by_the_head_and_admitted_by_the_literature_child(tmp_path):
    """Hand-off head -> literature: the model's own answer goes through the head's ``action`` (the records it names must be
    held), the head's ``msg_to_child`` builds the commission, and the literature child's own forms admit its assignment and
    its selection, its ``read_from_parent`` reads it, and every record it passes is one the head holds."""
    from ..literature.episode import PublishedEvidenceAssessment as Literature
    held = held_world(tmp_path)
    library = task.ExperimentalActivityEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    selection = {**held['input']['assignment']['selection'], 'evidence_axis': library.reference('A105'),
                 'thought_pattern': thought, 'child_tool_info': [{'name': 'state.query', 'resources': 'api'}]}
    entry = {**held['input'], 'assignment': {**held['input']['assignment'], 'selection': selection}}
    bindings = subtree()
    settings = {**SETTINGS, 'library_directory': str(library.directory)}
    collaborators = {'store': held['store'],
                     'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                     'continuation': {binding.binding_path: settings for binding in bindings},
                     'services': {name: unbuilt(name) for binding in bindings for name in binding.services}}
    run = link(BindingRegistry(bindings), ExperimentalActivityEvidence.binding_path, entry,
               run_id='a105-head-literature', journal=RunJournal(tmp_path / 'journal.sqlite3'),
               collaborators=collaborators)
    asyncio.run(run.next_decision())
    summary = ExperimentalActivityEvidence()._summary(run.view)
    answer = real_literature_answer(held['proposed'], held['scope'])
    call = ExperimentalActivityEvidence.action(answer, summary, run.view.records, None)
    message = ExperimentalActivityEvidence.msg_to_child(call.slot, call.arguments, summary)
    form = Literature.return_form.select(message.selection)
    admitted = Literature.assignment_form.admit(message.assignment, 'test')
    parent_input = Literature.read_from_parent(dict(admitted), message.message)
    assert parent_input['proposed_annotation_ref'] == held['proposed'] and parent_input['scope'] == held['scope']
    assert parent_input['task_key'] == 'A105:verified_source_leads'
    assert set(form.fields) >= {'credit', 'finding', 'sheet_state_refs', 'literature_source_lead_dispositions'}
    passed = Literature.assignment_form.record_refs(admitted)
    assert passed and all(run.view.records.holds(ref) for ref in passed)
    # the return: what the literature child builds for the selection asked is what the head reads, sums up and passes up
    records = run.view.records
    returned = Literature.final_to_parent({'scores': [], 'features': [], 'sheet_state_refs': [], 'lead_source_refs': []},
                                          {'credit': 0.0}, message.selection)
    result = form.admit(returned, 'test')
    report = ExperimentalActivityEvidence.read_from_child(call.slot, result, summary, records)
    outcome = {'kind': 'child', 'slot': call.slot, 'arguments': dict(call.arguments),
               'message': {'objective': message.objective, 'message': dict(message.message),
                           'assignment': dict(message.assignment), 'selection': list(message.selection)},
               'completion': {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0},
               'result': result, 'report': report}
    view = types.SimpleNamespace(parent_input=run.view.parent_input, records=records, goal=run.view.goal,
                                 units_consumed=1, controller_state=None, outcomes=[outcome])
    after = ExperimentalActivityEvidence()._summary(view)
    assert after['sheet_state_refs'] == [] and after['child_returns'][0]['slot'] == 'literature'
    assert ExperimentalActivityEvidence.credit(after, records) == 0
    asked = ('sheet_state_refs', 'committed_record_refs')
    sent = ExperimentalActivityEvidence.final_to_parent(after, {'credit': 0.0}, asked)
    assert ExperimentalActivityEvidence.return_form.select(asked).admit(sent, 'test') == sent
    held['store'].close()
