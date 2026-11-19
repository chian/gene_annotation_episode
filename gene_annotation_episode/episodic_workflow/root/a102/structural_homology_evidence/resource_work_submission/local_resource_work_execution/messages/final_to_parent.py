"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
resource, whether the requested endpoint was verified, which requirements are satisfied, the execution handoffs
found usable, and the commands run). Selectable: ``execution_handoff`` (the one usable handoff when exactly one
physical execution is known, the empty record otherwise), ``execution_handoffs`` and ``execution_handoff_record_refs``
(the proof records the checks of the returned handoffs name)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    digest)

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The selected local resource'),
    'assignment_id': Field('text', 'The identity of the job assignment'),
    'assignment_sha256': Field('text', 'The digest of the original job assignment'),
    'endpoint': Field('text', 'The requested endpoint: usable_handoff or completed_job_outputs'),
    'completion_target': Field('number', 'The total credit of the commissioned requirements'),
    'completed': Field('boolean', 'Whether the original requested endpoint predicates have a verified completion'),
    'completion_proof': Field('record', 'The verified completion, or the empty record when there is none'),
    'satisfied_keys': Field('list', 'The original requirement keys currently satisfied'),
    'requirements': Field('list', 'Each original requirement with its credit and whether it is satisfied'),
    'commands_run': Field('integer', 'The number of commands executed'),
    'failures': Field('list', 'The recorded failures of the commands that failed, in order'),
    'receipt_refs': Field('list', 'The references of the saved command receipts'),
    'handoff_checks': Field('integer', 'The number of receiving checks of an execution handoff that were run'),
    'execution_handoff_identities': Field('list', 'The (capability_binding_ref, execution_handle) of every '
                                                  'usable execution handoff found, in identity order'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'Whether the requested endpoint was verified, which execution handoffs are usable, '
                               'and what the commands did', form=FINDING_FORM),
    'execution_handoff': Field('record', 'The latest original usable received or own selected check when exactly '
                                         'one physical execution is known (empty for zero or several '
                                         'identities). No new receiving check occurs at closure.', required=False),
    'execution_handoffs': Field('list', 'For each distinct registry and execution handle, the available usable '
                                        'check with latest original checked_at, in identity order. This records '
                                        'available facts without selecting a resource or rechecking it.',
                                required=False),
    'execution_handoff_record_refs': Field('record_refs', 'The proof records the checks of the returned execution '
                                                          'handoffs name', required=False),
})


def _facts(summary):
    """The handoff facts over this episode's own recorded checks."""
    handoffs = summary['handoffs']
    return {'execution_handoffs': handoffs, 'execution_handoff': handoffs[0] if len(handoffs) == 1 else {}}


def _references(handoffs):
    """The proof records the checks name."""
    references = set()
    for handoff in handoffs:
        references.update(handoff['check_record_refs'])
    return sorted(references)


def final_to_parent(summary, completion, selection):
    progress = summary['execution_progress']
    facts = _facts(summary)
    failures = [command['failure'] for command in summary['commands'] if command['failure'] is not None]
    result = {'credit': completion['credit'],
              'finding': {'resource_id': summary['launch']['resource_selection']['resource_id'],
                          'assignment_id': summary['assignment']['assignment_id'],
                          'assignment_sha256': digest(summary['assignment']),
                          'endpoint': summary['assignment']['endpoint'],
                          'completion_target': summary['completion_target'],
                          'completed': summary['execution_completion'] is not None,
                          'completion_proof': summary['execution_completion'] or {},
                          'satisfied_keys': list(progress['satisfied_keys']),
                          'requirements': [{name: row[name] for name in ('key', 'credit', 'satisfied')}
                                           for row in progress['requirements']],
                          'commands_run': len(summary['commands']), 'failures': failures,
                          'receipt_refs': list(summary['receipt_refs']),
                          'handoff_checks': len(summary['checks']),
                          'execution_handoff_identities': [
                              [handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle']]
                              for handoff in facts['execution_handoffs']]}}
    for name in selection:
        if name == 'execution_handoff_record_refs':
            result[name] = _references(facts['execution_handoffs'])
        else:
            result[name] = facts[name]
    return result
