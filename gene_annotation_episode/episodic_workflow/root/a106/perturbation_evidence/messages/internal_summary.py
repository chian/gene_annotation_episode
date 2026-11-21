"""Where the A106 investigation stands, as a pure function of the loop's view: the commission (the parent input under
its old names), the investigation progress of the retained findings held (the old credit-view fields
``retained_finding_count``, ``inactive_dependencies`` and ``detail_pages``, which ``project_finding_progress`` gives and
which the old ``commissioned_credit_presentation`` and ``standalone_credit_presentation`` showed), the credit
binding (the projector's ``as_record()``), the latest page of the own outcomes (old ``episode.history``: the old reads
of ``runtime_actions`` are the unit outcomes of ``view``), the last local outcome, the reports of the children, the
handoffs the children returned, the outstanding jobs (the jobs whose handoff row of the job ledger this Episode
holds and whose closure row it does not hold, with the check rows it holds of each: what a monitor commission
passes in custody), the interpretation written, the records committed, the controller's
yield table and the reasoning schema.

Carried from the old ``internal_summary.py``, ``decision_state.py``, ``commissioned_credit_presentation.py``,
``standalone_credit_presentation.py`` and ``decision_inputs.py``. What those showed that came from outside the Store
(``resource_context``, ``shared_information_context``, the execution expectations, the resource tool estimates,
``waiting_support``, ``pending_work``) belongs to the job services that are not built and to the actions that no
longer exist (``wait``, ``redeliver_report``); it is not shown. The old ``annotation_axis_credit`` mode of the root
presentation (the root's arms, annotation credits, comparisons and the A101 to A104 sheets) is the root's own and is
not this episode's. What the old binding's ``decision_context`` showed from the process library (the selected
entries, the thought pattern, the resolved tools, ``annotation_support_routes``) is read from the frozen libraries,
which are files outside the Store: ``task.decide`` shows it."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import outstanding_jobs
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import finding_progress

OUTCOME_PAGE_SIZE = 8            # the old configuration outcome_page_size
PREVIEW_SIZE = 24                # the old ``loss_preview_size`` of ``ScientificFindingProgress``


def children(view, slot):
    return [outcome['report'] for outcome in view.outcomes if outcome['kind'] == 'child' and outcome['slot'] == slot]


def internal_summary(view):
    parent = view.parent_input
    records = view.records
    progress = finding_progress(records, parent, details_limit=PREVIEW_SIZE)
    tool_outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    written = [outcome['outcome']['report'] for outcome in tool_outcomes if outcome['tool'] == 'report']
    report = written[-1] if written else None
    last = view.outcomes[-1] if view.outcomes else None
    launches, own = children(view, 'launch'), children(view, 'perturbation_evidence')
    committed = []
    for outcome in tool_outcomes:
        if outcome['tool'] == 'reason':
            committed.extend([*outcome['outcome'].get('record_refs', []),
                              *outcome['outcome'].get('changed_record_refs', [])])
    for child in own:
        committed.extend(child['committed_record_refs'])
    committed = list(dict.fromkeys(committed))
    page_offset = max(0, len(view.outcomes) - OUTCOME_PAGE_SIZE)
    return {
        **parent,
        'credit_binding': ScientificFindingProgress(FindingProgressPolicy(parent['task']['credit_unit']),
                                                    PREVIEW_SIZE).as_record(),
        'investigation_progress': {key: progress[key] for key in ('credit', 'retained_finding_count',
                                                                  'inactive_dependencies', 'detail_pages')},
        'own_outcomes': outcome_page(view.outcomes, offset=page_offset, limit=OUTCOME_PAGE_SIZE),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'held_record_refs': sorted(records.refs()),
        'reasoning_schema': records.reasoning_schema(),
        'child_reports': [{'slot': outcome['slot'], 'arguments': outcome['arguments'], 'report': outcome['report']}
                          for outcome in view.outcomes if outcome['kind'] == 'child'],
        'handoff_refs': list(dict.fromkeys(ref for report_ in launches
                                           for ref in report_['facts'].get('execution_handoff_refs', []))),
        'handoff_resources': list(dict.fromkeys(resource for report_ in launches
                                                for resource in report_['finding']['handoff_resources'])),
        'outstanding_jobs': outstanding_jobs(records),
        'report': report,
        'report_source_held': ({} if report is None else
                               {item['source_ref']: records.holds(item['source_ref']) for item in report['sources']}),
        'committed_record_refs': committed,
        'committed_record_held': {reference: records.holds(reference) for reference in committed},
        'received_process_results': [row for child in own
                                     for row in child['facts'].get('perturbation_evidence_results', [])],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
