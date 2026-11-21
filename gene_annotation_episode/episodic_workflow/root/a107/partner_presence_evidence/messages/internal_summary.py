"""Where the episode stands, as a pure function of the view: the assignment, the Episode's own outcomes, the
child reports, the literature partner sheets its children returned, the A107 scoring sheet, the records it committed, the preparations of alternative processes it
made, the A107 evidence it holds and the yield forecast of its controller.

Carried from the old ``internal_summary.py`` (``ScientificInternalSummary.decision_context`` and
``initial_decision_context``, ``ScientificDecisionSummary._decision_snapshot``) and ``received_evidence.py``
(``_component_scoring_facts``):

* ``decision_context``: the selected evidence axis, thought pattern and tools are resolved from the commission's
  selection by ``decide`` through the run's library services; this summary holds the assignment and the permitted
  children (the slots of ``task.py``).
* ``initial_decision_context``: the A107 received qualifications, the genomic execution findings and the native
  component and execution findings, read from the records the Episode holds through ``view.records``
  (``received_evidence`` below). Those library readers are still written against the raw Store.
* Not carried: the journal reads of ``_decision_snapshot`` (the last image view, ``elapsed_view``,
  ``pending_work``, delivery status), the controller binding and credit binding records, ``working_state``, the
  report-form machinery (``report_values``, ``report_basis``, ``requested_form``), ``component_axis_source_access``
  and the received component reports and scoring sheets of ``component_axis_reports`` and
  ``component_axis_execution_context`` (no placement)."""
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.episode_support.grading.qualification import (
    execution_findings as genomic_execution_findings, received_qualifications)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_and_context_sources.component_axis_native_hpc import (
    execution_findings as native_execution_findings, received_components)
from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.scoring_sheet import (
    scoring_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import outstanding_jobs
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8
HISTORY_MEANING = ('Own outcome metadata only. Inspect original records and exact prior operations before '
                   'interpreting them.')


def received_evidence(records, scope):
    """The A107 evidence this Episode holds: qualifications, genomic execution findings, native component records
    and native execution findings (old ``initial_decision_context``). Each reader takes the held sources."""
    sources = sorted(ref for ref in records.refs() if ref.startswith('source_'))
    return {'qualifications': received_qualifications(records, sources, scope),
            'genomic_execution': genomic_execution_findings(records, SimpleNamespace(scope=scope), set(sources)),
            'native_components': received_components(records, sources, scope),
            'native_execution': native_execution_findings(records, sources, scope)}


def internal_summary(view):
    parent = view.parent_input
    committed, revisions, child_reports, returned = [], [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            report = outcome['report']
            child_reports.append(report)
            if 'committed_record_refs' in report:
                committed.extend(report['committed_record_refs'])
            if outcome['slot'] in ('literature', 'partner_presence_evidence'):
                returned.extend(report['finding']['partner_sheets'])
        elif outcome['tool'] == 'reason':
            committed.extend(outcome['outcome'].get('record_refs', ()))
        elif outcome['tool'] == 'process_revise' and outcome['outcome']['status'] == 'completed':
            revisions.append({'result': outcome['outcome']['result'],
                              'revision_origin': outcome['outcome']['revision_origin']})
    summary = {**parent,
               'objective': view.goal.objective,
               'held_record_refs': sorted(view.records.refs()),
               'own_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                            tools=None, tool_of=None),
               'history_meaning': HISTORY_MEANING,
               'child_reports': child_reports,
               # the jobs whose handoff row of the job ledger this Episode holds and whose closure row it does not
               # hold, with the check rows it holds of each: what a monitor commission passes in custody
               'outstanding_jobs': outstanding_jobs(view.records),
               'committed_record_refs': list(dict.fromkeys(committed)),
               'revisions': revisions,
               'received': received_evidence(view.records, parent['scope']),
               'literature_sheets': merged_sheet_features((), returned),
               'reasoning_schema': view.records.reasoning_schema(),
               'units_consumed': view.units_consumed}
    summary['scoring_sheet'] = scoring_sheet(view.records, summary['literature_sheets'],
                                             summary['received']['native_components'],
                                             summary['received']['qualifications'])
    if view.controller_state is not None:
        summary['yield_table'] = yield_table(view.controller_state, forecast_unit='finding')
    return summary
