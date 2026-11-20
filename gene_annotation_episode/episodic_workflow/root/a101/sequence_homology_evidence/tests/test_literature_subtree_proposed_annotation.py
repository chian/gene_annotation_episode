"""The proposed annotation travels down the published-evidence subtree, and each of its seven episodes reads its
credit for that annotation (no model; real runner, journal, Store, tool registry and job services).

The case is the commission the real model made in run ``a101head_14`` (branch 2): after a real ``sequence.align``
the head commissions the published evidence assessment with the pairwise alignment observation as the question's
context and no source. That observation's grading sheet is neither a BLAST nor an HMMER sheet, so a credit read
without the proposed annotation raised ``a101_unsupported_score_profile`` when the child's controller was built.

Each episode of the subtree is linked as the entry of a run of its own, in the same Store and journal, with exactly
the assignment its parent's ``msg_to_child`` builds from the parent's real summary (the head's for the first), and
stepped through the public API: ``next_decision`` (the yield controller is built from the credit of the initial
summary: the step that failed) and ``run_unit`` (one real ``state_query`` unit, whose credit goes to the
controller). The real-model test (selected only with ``-m model_run``) makes the same commission on a head run and
lets child and head run by their own decisions to their controllers' stops."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, ChildCall, ModelRequest, RunJournal, ToolCall, link, resume
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    A101ScoringUnavailable)

from ..episode import SequenceHomologyEvidence
from ..messages.final_to_parent import RETURN_FORM
from ..literature import credit as literature_credit
from ..literature.episode import Literature
from ..literature.strategy.episode import (
    Strategy)
from ..literature.strategy.search.episode import (
    Search)
from ..literature.strategy.search.page.episode import (
    Page)
from ..literature.strategy.search.page.lexical_probe.episode import (
    LexicalProbe)
from ..literature.strategy.search.page.report.episode import (
    Report)
from ..literature.strategy.search.page.source_table.episode import (
    SourceTable)
from .a101_world import collaborators, linked, report_children, subtree, world

ALIGN = 'sequence.align'
LEAVES = {'lexical_probe': LexicalProbe,
          'report': Report,
          'source_table': SourceTable}


def commissioned(held, journal, parent_run, episode, message, run_id):
    """``episode`` linked as the entry of a run of its own with the commission ``message`` its parent built. Every
    record the commission names is one the parent holds (what custody requires of a commission)."""
    assignment = episode.assignment_form.admit(message.assignment, 'assignment')
    named = episode.assignment_form.record_refs(assignment)
    assert held['hypothesis'] in named
    assert all(parent_run.view.records.holds(ref) for ref in named)
    bindings = subtree()
    entry = {'assignment': message.assignment, 'message': message.message, 'selection': list(message.selection)}
    return link(BindingRegistry(bindings), episode.binding_path, entry, run_id=run_id, journal=journal,
                collaborators=collaborators(held, bindings, 'model_calls_' + run_id))


CONTROLLER_INTERNALS = {'action_yields', 'time_accounting', 'current_report_update', 'goal'}
OLD_RUNNER_TEXT = ('tool itinerary', 'report_update', 'redeliver_report', 'controller.arms', 'annotation_score')


def stepped(run, episode, held, observation, objective, **envelope):
    """The episode's first decision and one real unit; the summary after the unit and the first request. The
    request is the episode's own brief with the commissioner's objective (a value of the episode's vocabulary, with
    the episode's meaning of it), and the decision after the unit shows what the unit returned."""
    name = episode.binding_path.rsplit('/', 1)[-1]
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    print('REQUEST', name, 'instructions', len(request.instructions),
          'context', len(json.dumps(request.context)), 'context_without_tools',
          len(json.dumps({name: value for name, value in request.context.items() if name != 'tools'})),
          'schema', len(json.dumps(request.output_schema)), 'keys', sorted(request.context))
    print('REQUEST_FIRST_LINES', json.dumps(request.instructions[:400]))
    assert request.instructions.startswith('THIS EPISODE: ' + name + ' (A101')
    own = 'YOUR OWN TOOL' if name == 'literature' else 'YOUR OWN TOOLS'     # run has the one lookup and proposes strategies
    goal = "THE OWNER'S GOAL:" if name == 'literature' else "THE OWNER'S GOAL AND RULES OF EVIDENCE:"
    for heading in ('WHAT THE COMMISSIONER ASKED:', own, 'WHAT RETURNS:', 'CREDIT', goal):
        assert heading in request.instructions, (name, heading)
    assert ('THE CHILD' in request.instructions) == bool(episode.child_slots)
    assert not [text for text in OLD_RUNNER_TEXT if text in request.instructions]
    assert not CONTROLLER_INTERNALS & set(request.context), sorted(request.context)
    commission = request.context['commission']
    assert commission['objective'] == objective and commission['proposed_annotation_ref'] == held['hypothesis']
    assert commission['objective'] in request.instructions and commission['objective_meaning']
    assert request.context['own_literature_outcomes']['records'] == [] and request.context.get('report') is None
    # the controller was built from the credit of the initial summary, read for the proposed annotation
    assert request.context['current_credit'] == 0.0
    records = run.view.records
    summary = episode.internal_summary(run.view)
    assert summary['proposed_annotation_ref'] == held['hypothesis']
    assert records.get(held['hypothesis'])['record_type'] == 'hypothesis'
    assert records.holds(observation), 'the pairwise alignment observation is held by ' + episode.binding_path
    assert episode.credit(summary, records) == 0.0
    # the commission asked about the aligned homolog, so the homolog's subject is a subject of the scope the head
    # built and every episode below carries on, and the record lookup answers for it (run a101prompt_6: the scope
    # was the target alone and 2 of the child's 4 lookups were refused with subject_outside_assigned_scope)
    assert request.context['scope'] == summary['scope'] == {'subject_refs': [held['target'], held['reference']]}
    lookup = [held['hypothesis'], held['reference']]
    unit = asyncio.run(run.run_unit(ToolCall('state_query', {
        'arguments': {'refs': lookup}, 'scope': summary['scope'], **envelope})))
    assert unit['outcome']['status'] == 'completed', unit['outcome']
    assert [row['id'] for row in unit['outcome']['result']['records']] == lookup
    assert run.view.units_consumed == 1 and run.view.controller_state.current_credit == 0.0
    # the lookup's outcome is in the next request and stays there (run a101lit_5: the model was never shown it and
    # asked four times; run a101prompt_6: shown for one decision only, it asked again after the next unit)
    after = asyncio.run(run.next_decision())
    shown, = after.context['own_literature_outcomes']['records']
    assert shown['tool'] == 'state_query' and shown['outcome'] == unit['outcome']
    assert shown['arguments']['arguments'] == {'refs': lookup}
    assert after.context['commission'] == commission
    return episode.internal_summary(run.view), request


def test_each_episode_of_the_literature_subtree_reads_its_credit_for_the_carried_proposed_annotation(tmp_path):
    held = world(tmp_path, [ALIGN])
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    head = linked(held, 'a101-annotation-head', journal=journal)
    aligned = asyncio.run(head.run_unit(ToolCall('execute_selected_tool', {
        'tool': ALIGN, 'arguments': {'query_ref': held['target'], 'reference_ref': held['reference'],
                                     'molecule': 'protein', 'mode': 'global'},
        'scope': held['assignment']['scope'], 'permitted_record_refs': None})))
    assert aligned['outcome']['status'] == 'completed', aligned['outcome']
    observation, = (ref for ref in aligned['outcome']['record_refs'] if ref.startswith('observation_'))
    summary = SequenceHomologyEvidence.internal_summary(head.view)
    source, = summary['held_source_refs']
    artifact = held['store'].get(source)['artifact_ref']

    # the head: the model names the objective (a value of the child's vocabulary) and the observation; code carries
    # the proposed annotation
    message = SequenceHomologyEvidence.msg_to_child('literature', {
        'objective': 'evidence_about_aligned_homolog', 'question_context_refs': [observation]}, summary)
    assert message.assignment['proposed_annotation_refs'] == [held['hypothesis']]
    assert message.message == {'objective': 'evidence_about_aligned_homolog'}
    literature = commissioned(held, journal, head, Literature, message, 'a101-annotation-1')
    summary, request = stepped(literature, Literature, held, observation,
                               'evidence_about_aligned_homolog')
    print('LITERATURE_REQUEST_CONTEXT', json.dumps({name: value for name, value in request.context.items()
                                                    if name != 'tools'}, sort_keys=True))
    # the model is shown the assignment it was shown before: the carried annotation is not a field of it
    assert request.context['literature_assignment'] == {
        'version': 'literature_assignment_v1', 'question_context_refs': [observation], 'source_refs': []}
    # without the proposed annotation every held tool alignment is scored, and this one has no supported profile
    with pytest.raises(A101ScoringUnavailable, match='a101_unsupported_score_profile'):
        literature_credit.A101SequenceCredit().read_details(
            literature.view.records, summary['scope'], known_record_refs=literature.view.records.refs(),
            details_limit=0, details_offset=0)

    message = Literature.msg_to_child('strategy', {
        'strategy_family': 'target_exact_anchor', 'seed_queries': ['glutathione transferase']}, summary)
    strategy = commissioned(held, journal, literature, Strategy, message,
                            'a101-annotation-2')
    summary, _ = stepped(strategy, Strategy, held, observation, 'no_search_made')

    message = Strategy.msg_to_child('search', {
        'objective': 'acquired_sources_unassessed', 'search': {
            'version': 'search_assignment_v1', 'question_context_refs': [observation],
            'search_result_refs': [source]}}, summary)
    relevance = commissioned(held, journal, strategy, Search, message, 'a101-annotation-3')
    summary, _ = stepped(relevance, Search, held, observation, 'acquired_sources_unassessed')

    message = Search.msg_to_child('page', {
        'objective': 'evidence_location_unknown', 'page': {
            'version': 'page_assignment_v1', 'source_ref': source, 'representation': 'original',
            'artifact_ref': artifact, 'question_context_refs': [observation], 'prior_delivery_refs': []}}, summary)
    examination = commissioned(held, journal, relevance, Page, message, 'a101-annotation-4')
    summary, _ = stepped(examination, Page, held, observation, 'evidence_location_unknown',
                         page_source_ref=source)

    window = {'source_ref': source, 'representation': 'original', 'offset': 0, 'limit': 64}
    selections = {'lexical_probe': {'spans': [window]}, 'report': window,
                  'source_table': window}
    # what each leaf's own ``action`` adds to a tool call (the table examination: the sheet of a table selection)
    envelopes = {'lexical_probe': {}, 'report': {},
                 'source_table': {'sheet_key': None}}
    objectives = {'lexical_probe': 'extract_reported_finding',
                  'report': 'find_applicable_evidence',
                  'source_table': 'find_applicable_evidence'}
    for number, (slot, episode) in enumerate(LEAVES.items(), start=5):
        message = Page.msg_to_child(slot, {'objective': objectives[slot],
                                                                'selection': selections[slot]}, summary)
        leaf = commissioned(held, journal, examination, episode, message, 'a101-annotation-' + str(number))
        stepped(leaf, episode, held, observation, objectives[slot], page_source_ref=source, **envelopes[slot])
    # a commission whose objective is no value of the child's vocabulary fails where the child reads it
    message = SequenceHomologyEvidence.msg_to_child('literature', {
        'objective': 'Assess the published evidence', 'question_context_refs': [observation]},
        SequenceHomologyEvidence.internal_summary(head.view))
    with pytest.raises(KeyError, match='Assess the published evidence'):
        commissioned(held, journal, head, Literature, message, 'a101-annotation-wrong')
    # the lookup's scope rule is unchanged: a commission that does not ask about the homolog keeps the head's scope
    # (the target alone); the child holds the homolog's subject (the observation names it) and a lookup of it is
    # refused
    message = SequenceHomologyEvidence.msg_to_child('literature', {
        'objective': 'evidence_about_target_sequence', 'question_context_refs': [observation]},
        SequenceHomologyEvidence.internal_summary(head.view))
    assert message.assignment['scope'] == {'subject_refs': [held['target']]}
    outside = commissioned(held, journal, head, Literature, message, 'a101-annotation-target')
    refused = asyncio.run(outside.run_unit(ToolCall('state_query', {
        'arguments': {'refs': [held['reference']]}, 'scope': message.assignment['scope']})))
    assert outside.view.records.holds(held['reference'])
    assert refused['outcome']['status'] == 'invalid'
    assert refused['outcome']['feedback']['code'] == 'subject_outside_assigned_scope'
    held['store'].close()


@pytest.mark.model_run
def test_the_commission_that_failed_runs_with_the_real_model_to_the_stop_of_child_and_head(tmp_path):
    """The commission the head's real model made in run ``a101head_14`` (branches 1 and 2), made here as a stepped
    unit so that it is always exercised: the pairwise alignment observation as the question's context, no source.
    The child holds that observation, is built (its controller from its initial credit, read for the carried
    proposed annotation), runs by its own real-model decisions to its controller's stop, and its return is admitted
    and reported; the head runs on by its own decisions to its own stop; a resume asks the model nothing."""
    held = world(tmp_path, [ALIGN])
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = linked(held, 'a101-annotation-model', journal=journal)
    aligned = asyncio.run(run.run_unit(ToolCall('execute_selected_tool', {
        'tool': ALIGN, 'arguments': {'query_ref': held['target'], 'reference_ref': held['reference'],
                                     'molecule': 'protein', 'mode': 'global'},
        'scope': held['assignment']['scope'], 'permitted_record_refs': None})))
    observation, = (ref for ref in aligned['outcome']['record_refs'] if ref.startswith('observation_'))
    child = asyncio.run(run.run_unit(ChildCall('literature', {
        'objective': 'evidence_about_aligned_homolog', 'question_context_refs': [observation]})))
    print('CHILD', child['completion'], child['report'])
    # what the literature child (and any episode it commissioned) did with the commission, from the journal
    report_children(journal, 'a101-annotation-model')
    literature_path = next(tuple(tuple(step) for step in episode['path'])
                           for episode in journal.episodes('a101-annotation-model') if len(episode['path']) == 2)
    for index, call in enumerate(journal.model_calls('a101-annotation-model', literature_path)):
        request = call['request']
        if index == 0:
            print('LITERATURE_REQUEST_INSTRUCTIONS', json.dumps(request['instructions']))
            print('LITERATURE_REQUEST_CONTEXT', json.dumps({name: value for name, value in request['context'].items()
                                                            if name != 'tools'}, sort_keys=True))
        print('LITERATURE_DECISION', index, json.dumps(call['response'], sort_keys=True))
        # the homolog the commission asks about is a subject of the scope the child's model is shown
        assert request['context']['scope'] == {'subject_refs': [held['target'], held['reference']]}
        assert request['instructions'].startswith('THIS EPISODE: run')
        assert request['context']['commission']['objective'] == 'evidence_about_aligned_homolog'
        assert not CONTROLLER_INTERNALS & set(request['context'])
    assert child['message']['message'] == {'objective': 'evidence_about_aligned_homolog'}
    assert child['message']['assignment']['proposed_annotation_refs'] == [held['hypothesis']]
    assert observation in child['message']['assignment']['received_record_refs']
    assert child['message']['assignment']['scope'] == {'subject_refs': [held['target'], held['reference']]}
    assert child['completion']['ended_by'] == 'yield_stop'
    assert set(child['report']) == {'credit', 'finding', 'record_refs', 'handoff_refs'}
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    print('RESULT', result)
    print('ENDED', journal.run_state('a101-annotation-model')[1])
    assert journal.run_state('a101-annotation-model')[1]['ended_by'] == 'yield_stop'
    assert RETURN_FORM.select(('committed_record_refs',)).admit(result, 'return') == result
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    bindings = subtree()
    again = asyncio.run(resume(BindingRegistry(bindings), run_id='a101-annotation-model', journal=journal,
                               collaborators=collaborators(held, bindings, 'model_calls_resumed')).run())
    assert again['result'].as_record() == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    held['store'].close()
