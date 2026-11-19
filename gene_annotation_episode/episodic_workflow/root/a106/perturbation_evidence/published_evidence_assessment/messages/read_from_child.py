"""What this parent takes from a child's admitted return (carried from the old ``from_child_evidence_search_
strategy_improvement.receive_report``, ``from_child_execution_job_submission.receive_report`` and
``from_child_execution_result_acquisition.receive_report``: the child's typed form, the references in it, the
source-lead dispositions of a strategy child (which count toward this episode's leads credit through
``credit.lead_dispositions``), and the received application rows of the results child
(``received_evidence.received_application_rows``)). The old receipt bookkeeping (``EpisodeReturnRecords``,
``workflow.receipts``, population-cell receipts, native timing receipts, the progress receiver, the checks of the
delivered role and binding path) is the system's custody and is not carried. The report keeps what the summary and
the model are shown: the child's credit and finding and the fact sources this parent selected."""

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
HANDOFF = 'execution_handoff_refs'
COMPLETED = 'execution_completed'
RESULTS = 'execution_result_refs'
APPLICATION_OUTCOMES = 'bvbrc_application_outcomes'


def read_from_child(slot, result, summary, records):
    report = {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
    if slot == 'literature_strategy':
        if LEADS in result:
            report['lead_source_refs'] = result[LEADS]['lead_source_refs']
        if SCREENING in result:
            report['screening'] = result[SCREENING]
        return report
    if slot == 'launch':
        return {**report, 'handoff_refs': result[HANDOFF], 'completed': result[COMPLETED]}
    if slot == 'results':
        return {**report, 'result_refs': result[RESULTS], 'completed': result[COMPLETED],
                'application_rows': result[APPLICATION_OUTCOMES]}
    raise KeyError(slot)
