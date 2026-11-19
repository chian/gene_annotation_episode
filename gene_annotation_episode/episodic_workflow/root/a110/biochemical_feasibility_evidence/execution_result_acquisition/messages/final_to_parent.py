"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what was
acquired through the original handoff, how many windows were received and failed, whether the requested windows are
covered), ``execution_result_refs`` (the original result acquisitions that contain windows: the job identity,
preserved across a return), ``execution_result_artifact_refs`` (the artifacts of the returned result Sources, in
custody, so the parent reads the receipt body through them) and ``execution_completed``. Selectable:
``execution_handoff_refs``, ``execution_file_source_refs``, ``execution_file_capture_outcomes`` and
``execution_result_origin``, the acquisition semantics of the retained results as ``{'value': ...}``, whose value is
the origin when a window was received and null when none was."""
from method_loop import Field, RecordForm

from .internal_summary import facts

FINDING_FORM = RecordForm({
    'handoff_refs': Field('list', 'The original handoff the results are acquired through'),
    'acquisition_count': Field('integer', 'The acquisitions of this episode that completed'),
    'window_count': Field('integer', 'The byte windows actually received'),
    'failure_count': Field('integer', 'The window reads that failed (kept as failures)'),
    'acquired_selector_fraction': Field('number', 'The share of the requested selector byte positions received'),
    'complete': Field('boolean', 'Whether every requested window is covered by a successful attempt observation'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was acquired through the original handoff', form=FINDING_FORM),
    'execution_result_refs': Field('record_refs', 'Qualified actual requested result acquisitions that contain '
                                                  'windows: the job identity, preserved across a return'),
    'execution_result_artifact_refs': Field('record_refs', 'The artifacts of the returned result Sources (new)'),
    'execution_completed': Field('boolean', 'Whether this assignment has actual complete acquisition'),
    'execution_handoff_refs': Field('record_refs', 'Qualified original handoff records', required=False),
    'execution_file_source_refs': Field('record_refs', 'Source references of retained local file streams',
                                        required=False),
    'execution_file_capture_outcomes': Field('list', 'Recorded selected-file availability', required=False),
    'execution_result_origin': Field('record', 'Actual acquisition semantics of retained results as {"value": ...}; '
                                               'the value is null when no window was received', required=False),
})

_QUALIFICATION = ('Native paths expose the current resource filesystem: the attempt observation does not establish '
                  'that current file bytes were produced by that attempt; separate read windows are not an atomic '
                  'file snapshot.')


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    recorded['execution_result_origin'] = {'value': recorded['execution_result_origin']}
    result_refs = [ref for ref, body in zip(summary['result_refs'], summary['results']) if body['windows']]
    result = {'credit': completion['credit'],
              'finding': {'handoff_refs': list(summary['handoff_refs']),
                          'acquisition_count': len(summary['results']),
                          'window_count': sum(len(body['windows']) for body in summary['results']),
                          'failure_count': sum(len(body['failures']) for body in summary['results']),
                          'acquired_selector_fraction': summary['acquired_selector_fraction'],
                          'complete': recorded['execution_completed'], 'qualification': _QUALIFICATION},
              'execution_result_refs': sorted(result_refs),
              'execution_result_artifact_refs': list(summary['result_artifact_refs']),
              'execution_completed': recorded['execution_completed']}
    for name in selection:
        result[name] = recorded[name]
    return result
