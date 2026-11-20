"""The head's commissions on a real stepped run (no model): after a real ``sequence.align`` unit and a real
``process_revise`` unit, the commission of each child the head can state is controlled fields only, and the
assignment ``msg_to_child`` builds from them and the summary is one the child's own form admits and its own
``read_from_parent`` reads, naming only records this episode holds. The run is linked and stepped through the
public API (``link``, ``EpisodeRun.run_unit``, ``EpisodeRun.next_decision``); the Store, journal, tool registry and
job services are the real ones."""
import asyncio

from episode_runtime import ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary)

from .. import task
from ..episode import SequenceHomologyEvidence
from ..execution_job_submission.episode import ExecutionJobSubmission
from ..messages.msg_to_child import msg_to_child
from ..literature.episode import Literature
from ..literature.messages import read_from_parent as literature_objectives
from .a101_world import linked, world

ALIGN = 'sequence.align'


def stepped(tmp_path):
    """The head after one completed alignment (a source and an observation) and one completed revision."""
    held = world(tmp_path, [ALIGN])
    run = linked(held, 'a101-commissions')
    aligned = asyncio.run(run.run_unit(ToolCall('execute_selected_tool', {
        'tool': ALIGN, 'arguments': {'query_ref': held['target'], 'reference_ref': held['reference'],
                                     'molecule': 'protein', 'mode': 'global'},
        'scope': held['assignment']['scope'], 'permitted_record_refs': None})))
    assert aligned['outcome']['status'] == 'completed', aligned['outcome']
    library = SequenceHomologyEvidenceLibrary(held['settings']['process_library_directory'])
    thoughts = [header['option_ref'] for header in library.headers()
                if header['option_ref']['slot'] == 'thought_pattern']
    revised = asyncio.run(run.run_unit(ToolCall('process_revise', {
        'arguments': {'thought_pattern': thoughts[-1], 'child_tool_info': [{'name': ALIGN, 'resources': 'local'}]},
        'selection': held['assignment']['selection']})))
    assert revised['outcome']['status'] == 'completed', revised['outcome']
    return held, run, aligned['outcome'], thoughts[-1]


def test_the_offered_commissions_are_controlled_fields_built_from_what_the_episode_holds(tmp_path):
    held, run, aligned, _ = stepped(tmp_path)
    summary = SequenceHomologyEvidence.internal_summary(run.view)
    source, = summary['held_source_refs']
    assert source in aligned['record_refs']
    # no bound API resource, no outstanding job: the launch, the monitor and the results acquisition are not
    # offered; the resource children have no controlled commission
    assert task.offered_children(summary, []) == [task.LITERATURE, task.HEAD]
    literature, required = task.commission_fields(task.LITERATURE, summary, [])
    assert set(literature) == {'objective', 'question_context_refs', 'source_refs', 'scope'}
    assert literature['objective']['enum'] == list(literature_objectives.OBJECTIVES)
    assert required == ['objective', 'question_context_refs']
    recursive, required = task.commission_fields(task.HEAD, summary, [])
    assert set(recursive) == {'evidence_refs', 'scope', 'revision_position'} and required == ['evidence_refs']
    assert recursive['revision_position'] == {'enum': [1]}
    # with a bound API resource of the BLAST service the launch is offered: the resource, the query and a database
    launch, required = task.commission_fields(task.LAUNCH, summary, ['ncbi_blast'])
    assert launch['resource_id'] == {'enum': ['ncbi_blast']}
    assert launch['query_subject_ref'] == {'enum': [held['target']]} and set(launch) == {
        'resource_id', 'query_subject_ref', 'database'}
    assert task.commission_fields(task.RESULTS, summary, ['ncbi_blast']) is None
    assert all(task.commission_fields(slot, summary, ['ncbi_blast']) is None for slot in task.WITHOUT_COMMISSION)
    # the request the model would be sent offers the two children with those fields and nothing the model writes
    request = asyncio.run(run.next_decision())
    options = {option['properties']['slot']['enum'][0]: option['properties']
               for option in request.output_schema['properties']['selection']['anyOf']
               if option['properties']['kind']['enum'] == ['episode_child']}
    assert set(options) == {task.LITERATURE, task.HEAD}
    assert set(options[task.LITERATURE]) == {'kind', 'slot', 'objective', 'question_context_refs', 'source_refs',
                                             'scope'}
    assert set(options[task.HEAD]) == {'kind', 'slot', 'evidence_refs', 'scope', 'revision_position', 'selection'}
    assert [row['slot'] for row in request.context['child_options']] == [task.LITERATURE, task.HEAD]
    assert request.context['held_source_refs'] == [source] and request.context['launch_resources'] == []
    held['store'].close()


def test_a_literature_commission_is_admitted_by_the_child_and_names_held_records(tmp_path):
    held, run, aligned, _ = stepped(tmp_path)
    summary = SequenceHomologyEvidence.internal_summary(run.view)
    source, = summary['held_source_refs']
    message = msg_to_child(task.LITERATURE, {'objective': 'evidence_in_supplied_sources',
                                             'question_context_refs': [held['hypothesis'], held['target']],
                                             'source_refs': [source]}, summary)
    assert message.message == {'objective': 'evidence_in_supplied_sources'} and message.selection == ()
    assignment = Literature.assignment_form.admit(message.assignment, 'assignment')
    assert assignment['question_context_refs'] == [held['hypothesis'], held['target']]
    assert assignment['source_refs'] == [source] and assignment['scope'] == held['assignment']['scope']
    # the source and the held records it names (its artifact) travel in custody with the question context
    assert {source, *summary['named_refs'][source]} <= set(assignment['received_record_refs'])
    assert summary['named_refs'][source]
    assert all(run.view.records.holds(ref) for ref in assignment['received_record_refs'])
    parent_input = Literature.read_from_parent(assignment, message.message)
    assert parent_input['assignment']['source_refs'] == [source]
    # the proposed annotation this episode evaluates is carried by code, in custody: the child's credit is read for it
    assert assignment['proposed_annotation_refs'] == [held['hypothesis']]
    assert parent_input['proposed_annotation_ref'] == held['hypothesis']
    # an answer that names a record this episode does not hold is an invalid answer of the model
    assert task.unheld_references({'question_context_refs': [held['hypothesis'], 'input_' + 'a' * 24],
                                   'source_refs': [held['target']]}, summary) == ['input_' + 'a' * 24, held['target']]
    assert task.unheld_references({'question_context_refs': [held['hypothesis']], 'source_refs': [source]},
                                  summary) == []
    held['store'].close()


def test_a_recursive_commission_takes_the_named_revision_and_inherits_the_task(tmp_path):
    held, run, aligned, thought = stepped(tmp_path)
    summary = SequenceHomologyEvidence.internal_summary(run.view)
    observation, = (ref for ref in aligned['record_refs'] if ref.startswith('observation_'))
    alternative = msg_to_child(task.HEAD, {'evidence_refs': [observation], 'revision_position': 1,
                                           'selection': ['execution_handoff_refs']}, summary)
    assert alternative.selection == ('committed_record_refs', 'execution_handoff_refs')
    assignment = SequenceHomologyEvidence.assignment_form.admit(alternative.assignment, 'assignment')
    parent_input = SequenceHomologyEvidence.read_from_parent(assignment, alternative.message)
    assert parent_input['selection']['thought_pattern'] == thought
    assert parent_input['revision_origin'] == summary['revisions'][0]['revision_origin']
    assert parent_input['proposed_annotation_ref'] == held['hypothesis']
    assert parent_input['constraints'] == held['assignment']['constraints']
    assert parent_input['scope_refs'] == held['assignment']['scope_refs']
    assert all(run.view.records.holds(ref) for ref in (*assignment['scope_refs'], *assignment['evidence_refs'],
                                                       *assignment['proposed_annotation_refs']))
    same = msg_to_child(task.HEAD, {'evidence_refs': []}, summary)
    assignment = SequenceHomologyEvidence.assignment_form.admit(same.assignment, 'assignment')
    assert assignment['selection'] == summary['selection'] and 'revision_origin' not in assignment
    held['store'].close()


def test_a_launch_commission_is_the_blast_request_of_a_bound_resource(tmp_path):
    held, run, _, _ = stepped(tmp_path)
    summary = SequenceHomologyEvidence.internal_summary(run.view)
    message = msg_to_child(task.LAUNCH, {'resource_id': 'ncbi_blast', 'query_subject_ref': held['target'],
                                         'database': 'swissprot'}, summary)
    assert message.selection == ('execution_handoff_refs',) and message.message == {}
    assignment = ExecutionJobSubmission.assignment_form.admit(message.assignment, 'assignment')
    parent_input = ExecutionJobSubmission.read_from_parent(assignment, message.message)
    assert parent_input['permitted'] == {'ncbi_blast': {
        'slot': 'launch_api', 'kind': 'api', 'yield_class': 'compact_blast_database_grader_return_request_v1'}}
    assert parent_input['assignment']['requests']['ncbi_blast'] == {
        'version': 'blast_database_grader_return_request_v1', 'resource_id': 'ncbi_blast',
        'return_type': 'blast_database_sheet_v1', 'query_subject_ref': held['target'], 'database': 'swissprot'}
    # the query and its sequence travel in custody
    sequence = held['store'].get(held['target'])['sequence_ref']
    assert assignment['record_refs'][0] == held['target'] and sequence in assignment['record_refs']
    assert assignment['scope'] == {'subject_refs': [held['target']]}
    assert all(run.view.records.holds(ref) for ref in assignment['record_refs'])
    held['store'].close()


def test_a_literature_commission_passes_the_records_of_the_childs_scope(tmp_path):
    """The commission the real model made (run ``a101head_7``): an observation as the question's context, no
    source, the scope of this episode. The child reads the subjects of its scope, so they travel in custody."""
    held, run, aligned, _ = stepped(tmp_path)
    summary = SequenceHomologyEvidence.internal_summary(run.view)
    observation, = (ref for ref in aligned['record_refs'] if ref.startswith('observation_'))
    message = msg_to_child(task.LITERATURE, {'objective': 'evidence_about_aligned_homolog',
                                             'question_context_refs': [observation], 'source_refs': [],
                                             'scope': {'subject_refs': [held['target']]}}, summary)
    assignment = Literature.assignment_form.admit(message.assignment, 'assignment')
    sequence = held['store'].get(held['target'])['sequence_ref']
    source, = summary['held_source_refs']
    received = assignment['received_record_refs']
    assert received[0] == observation and {source, *summary['named_refs'][source], held['target'], sequence} <= set(
        received)
    assert all(run.view.records.holds(ref) for ref in received)
    assert assignment['source_refs'] == []
    # the objective asks about the aligned homolog: the reference the observation names (a held problem subject
    # outside this episode's own scope) is a subject of the child's scope, with its sequence in custody, and the
    # Store admits that scope from what the head holds
    reference_sequence = held['store'].get(held['reference'])['sequence_ref']
    assert summary['scope'] == {'subject_refs': [held['target']]}
    assert assignment['scope'] == {'subject_refs': [held['target'], held['reference']]}
    assert {held['reference'], reference_sequence} <= set(received)
    assert run.view.records.validate_scope(assignment['scope']) == {
        'subject_refs': sorted([held['target'], held['reference']])}
    # the model did not name the proposed annotation: code carries it and passes it in custody all the same
    assert assignment['proposed_annotation_refs'] == [held['hypothesis']] and held['hypothesis'] in received
    # the homolog's subject named itself is the same commission; a scope that carries segments takes the homolog whole
    length = held['store'].get(held['target'])['length']
    segment = {'target_ref': held['target'], 'start': 0, 'end': 10, 'unit': held['store'].get(held['target'])['unit']}
    named = msg_to_child(task.LITERATURE, {
        'objective': 'evidence_about_aligned_homolog', 'question_context_refs': [held['reference']],
        'scope': {'subject_refs': [held['target']], 'segments': [segment]}}, summary).assignment['scope']
    assert named['subject_refs'] == [held['target'], held['reference']]
    assert named['segments'] == [segment, {'target_ref': held['reference'], 'start': 0, 'end': length,
                                           'unit': segment['unit']}]
    assert run.view.records.validate_scope(named)['subject_refs'] == sorted([held['target'], held['reference']])
    # any other objective leaves the scope as the model chose it, whatever the context names
    for objective in ('evidence_in_supplied_sources', 'evidence_about_target_sequence'):
        other = msg_to_child(task.LITERATURE, {'objective': objective, 'question_context_refs': [observation],
                                               'source_refs': []}, summary).assignment
        assert other['scope'] == {'subject_refs': [held['target']]}
    held['store'].close()
