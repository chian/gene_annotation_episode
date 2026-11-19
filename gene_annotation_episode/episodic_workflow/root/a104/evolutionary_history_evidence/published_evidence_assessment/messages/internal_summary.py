"""Where the investigation stands, as a pure function of the loop's view: the assignment (the context records, the
sources it starts from and the commissioned task), custody of those sources, the first page of the episode's own
acquisition and read outcomes, the features of the saved sheets and committed assessments so far, the latest image the model looked at, what its
strategy child returned, and the typed answers the commissioned task asks for (carried from the old
``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, and from ``decision_context.py`` the ``visual_evidence`` of the latest completed
``image.view``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``).

The custody listed is that of the assignment's ``source_refs`` (the old ``decision_context`` listed the page source,
or ``source_refs`` when there is no page; this episode has no page). The rate-population display contexts of the old
file (``literature_experimental_work``, owned population sources, the latest failed population attempt,
``literature_completed_work``) are not carried; the saved assay-grading sheets and committed assessments are shown as their
controlled features. The root-only
``reference_evidence_parent`` context is not this episode's."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assay_grading_features import (
    current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assessment_features import (
    committed_assessment_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view',
              'public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
              'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')
LEADS = 'literature_source_lead_dispositions'


def internal_summary(view):
    parent = view.parent_input
    literature, task = parent['literature'], parent['task']
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['tool'] == 'image_view'
              and last['outcome'].get('status') == 'completed' else [])
    child_reports, source_leads, no_applicable, child_sheets, child_sheet_records, child_assessments = [], [], [], [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            child_reports.append({'objective': outcome['message']['objective'],
                                  'prior_search_refs': outcome['arguments']['prior_search_refs'],
                                  **outcome['report']})
            source_leads.extend(returned_leads(outcome['report'], parent['proposed_annotation_ref']))
            child_sheets.extend(outcome['report']['finding']['assay_sheets'])
            child_sheet_records.extend(outcome['report']['finding']['sheet_record_refs'])
            child_assessments.extend(outcome['report']['finding']['assessments'])
        elif outcome['tool'] == 'reason':
            if 'literature_source_lead' in outcome['outcome']:
                source_leads.append(outcome['outcome']['literature_source_lead'])
            if declared_absent(outcome['outcome']):
                no_applicable.extend(examined_span(view.records, span)
                                     for span in outcome['outcome']['evidence_processing']['examined'])
    assignment = {**literature, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    custody = []
    for source_ref in literature['source_refs']:
        source = view.records.get(source_ref)
        custody.append({'source_ref': source_ref, **{key: source.get(key) for key in CUSTODY_KEYS}})
    summary = {
        'assignment': parent,
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'question_context_refs': literature['question_context_refs'],
        'literature_source_custody': custody,
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'held_record_refs': sorted(view.records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'child_reports': child_reports,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'assay_sheets': merged_sheet_features(current_sheet_features(view.records), child_sheets),
        'assessments': [*committed_assessment_features(view.records, [outcome['outcome'] for outcome in outcomes
                                                                      if outcome['tool'] == 'reason']),
                        *child_assessments],
        'sheet_record_refs': list(dict.fromkeys([*sheet_records(view.records, [outcome['outcome'] for outcome in outcomes
                                                                                if outcome['tool'] == 'reason']),
                                                 *child_sheet_records])),
        'source_leads': source_leads,
        'no_applicable_evidence': no_applicable,
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary


def returned_leads(report, proposed):
    """A child's relevant source leads as this episode's lead dispositions: the child returns only how many and their
    sources (controlled), so each returned source is one relevant lead for the commissioned annotation."""
    if LEADS not in report:
        return []
    return [{'source_ref': reference, 'proposed_annotation_ref': proposed, 'disposition': 'relevant'}
            for reference in report[LEADS]['lead_source_refs']]


def declared_absent(outcome):
    """Whether a reasoning outcome is a source-grounded ``no_applicable_evidence`` declaration."""
    processing = outcome['evidence_processing'] if 'evidence_processing' in outcome else None
    return processing is not None and processing['kind'] == 'no_applicable_evidence'


def examined_span(records, span):
    """A span a ``no_applicable_evidence`` declaration examined, with the artifact of the representation read."""
    source = records.get(span['source_ref'])
    return {**span, 'artifact_ref': source['artifact_ref' if span['representation'] == 'original' else 'text_ref']}


def sheet_records(records, reasons):
    """The records a receiver needs to read this Episode's own assay-grading sheets again and to follow them to the
    graded interpretation (references only)."""
    refs = []
    repository = LiteratureAssayGradingRepository(records)
    for sheet_ref in repository.current_sheet_refs():
        source = records.get(sheet_ref)
        saved = repository.read(sheet_ref)
        refs.extend([sheet_ref, source['artifact_ref'], source['request_ref'], *saved['record_bindings'],
                     *saved['input_source_refs'],
                     *(binding['artifact_ref'] for binding in saved['artifact_bindings'])])
    for outcome in reasons:
        if 'evidence_processing' in outcome and outcome['evidence_processing'] is not None \
                and outcome['evidence_processing']['kind'] == 'graded':
            refs.extend(outcome['record_refs'])
    return [ref for ref in dict.fromkeys(refs) if records.holds(ref)]
