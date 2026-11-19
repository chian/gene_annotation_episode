"""Where the execution stands, as a pure function of the loop's view: the assignment, the saved command receipts
the episode's own units returned, the practical credit view over them and the completion proof.

Carried from the old ``terminal_summary.py`` (``execution_assignment``, ``execution_progress`` = the practical
state's credit view, ``execution_completion`` = its completion proof) and from the practical state
(``PracticalState.credit_view`` / ``_completion``), which kept the same facts in files under the run directory;
here the saved receipts are the unit outcomes of ``view``. The completion proof is the old ``_completion`` over
those receipts (private copy: the library keeps it only inside the file-backed ``PracticalState``).

The resource information and the coordinator workspace the old ``decision_context`` showed come from the
episode's settings and are added in ``decide``. The old ``initial_decision_context`` (the resource capabilities
and the initial inventory) is the same settings content, shown at every decision."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest, terminal_job_matches)

# The initial validations only need what the old call assessed: no outcome facts. The old call stamped the wall
# clock; a summary is a pure function of its view, so the stamp is fixed (credit reads only the satisfaction).
INITIAL_CHECKED_AT = '1970-01-01T00:00:00+00:00'
HANDOFF_STATUSES = ('submitted', 'running', 'completed')


def completion_proof(assignment, satisfied_keys, receipts):
    """The old ``PracticalState._completion``: every completion key is satisfied and the last receipt satisfies the
    endpoint predicate for a completion key. ``None`` when not."""
    if not receipts:
        return None
    keys = set(assignment['completion_keys'])
    if not keys <= set(satisfied_keys):
        return None
    endpoint_kind = ('requested_job_handoff' if assignment['endpoint'] == 'usable_handoff'
                     else 'requested_job_outputs')
    last = receipts[-1]
    if not any(item['key'] in keys and item['satisfied'] and item['predicate']['kind'] == endpoint_kind
               for item in last['validations']):
        return None
    return {'version': COMPLETION_VERSION, 'run_id': last['run_id'], 'episode_id': last['episode_id'],
            'assignment_sha256': last['assignment_sha256'], 'endpoint': assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}


def returnable_handoff(assignment, receipt):
    """An own command receipt that is a returnable handoff for this exact assignment: the scheduler submission the
    receipt records matches the assignment's requested job and its job is submitted, running or completed (the
    old ``execution_handoff_refs`` asked the old handoff reader for the same)."""
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    return (job is not None and terminal_job_matches(assignment, receipt['outcome'])
            and job['status'] in HANDOFF_STATUSES and job['handoff'] is not None)


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    initial = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                 checked_at=INITIAL_CHECKED_AT)
    commands = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    receipts = [command['outcome']['receipt'] for command in commands]
    refs = [command['outcome']['receipt_ref'] for command in commands]
    progress = project_practical_credit(assignment, initial, receipts)
    return {
        'assignment': assignment,
        'message': parent['message'],
        'initial_validations': initial,
        'receipts': receipts,
        'receipt_refs': refs,
        'handoff_refs': [ref for ref, receipt in zip(refs, receipts) if returnable_handoff(assignment, receipt)],
        'context': receipts[-1]['context_after'] if receipts else assignment['initial_context'],
        'progress': progress,
        'completion_proof': completion_proof(assignment, progress['satisfied_keys'], receipts),
        'last_command': (None if not commands else {'tool': commands[-1]['tool'],
                                                     'arguments': commands[-1]['arguments']['command'],
                                                     'outcome': commands[-1]['outcome']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
