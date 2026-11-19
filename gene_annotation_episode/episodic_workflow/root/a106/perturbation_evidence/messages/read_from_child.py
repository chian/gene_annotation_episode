"""What this parent takes from a child's admitted return (carried from the old ``from_child_published_evidence_
assessment.receive_report``, ``from_child_execution_job_submission.receive_report``, ``from_child_execution_
progress_assessment.receive_report`` and ``receive_progress``, ``from_child_execution_result_acquisition.
receive_report`` and ``from_child_perturbation_evidence.receive_report`` at 97308b94c). The old receivers admitted the
child's typed form through the saved attempts and the receipts ledger (``EpisodeReturnRecords``, ``workflow.receipts``,
``runtime_report_attempts``), checked the delivered role and binding path, and admitted the monitor's progress
references into the progress provider (``receive_progress``); that bookkeeping is the system's custody and is not
carried. The report keeps what the summary and the model are shown: the child's credit and finding and the fact
sources this parent selected. A monitor's delivered progress observations are returned with their snapshots (the
snapshots replace the provider read of a reference), so the report carries them for this parent's later monitor
commissions."""

LITERATURE = ('literature_screening_answers', 'literature_source_lead_dispositions')
LAUNCH = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
          'bvbrc_application_outcomes')
MONITOR = ('monitoring_progress_refs', 'monitoring_target_handle', 'monitoring_execution_state',
           'monitoring_result_available', 'monitoring_observed_at_unix_seconds', 'monitoring_committed_record_refs',
           'monitoring_dependency_handles', 'monitoring_progress_snapshots')
RESULTS = ('execution_result_refs', 'execution_handoff_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
           'bvbrc_application_outcomes')
OWN = ('perturbation_evidence_results', 'committed_record_refs')
FACTS = {'literature': LITERATURE, 'launch': LAUNCH, 'monitor': MONITOR, 'results': RESULTS,
         'perturbation_evidence': OWN}


def read_from_child(slot, result, summary, records):
    """The child's credit and finding with every fact source the child returned, in the form of the slot."""
    report = {'slot': slot, 'credit': result['credit'], 'finding': result['finding'],
              'facts': {name: result[name] for name in FACTS[slot] if name in result}}
    if slot == 'monitor':
        report['progress_snapshots'] = result['monitoring_progress_snapshots']
    if slot == 'perturbation_evidence':
        report['committed_record_refs'] = result['committed_record_refs']
    return report
