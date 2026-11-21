"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the controlled features of the assay-grading sheets it saved,
far, the latest image the model looked at, and the typed answers the commissioned task asks for (carried from the
old ``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, and from ``decision_context.py`` the ``visual_evidence`` of the latest completed
``image.view``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``).

The rate-population display contexts of the old file (``literature_experimental_work``, owned population sources,
the latest failed population attempt, ``literature_completed_work``) are not carried; the saved assay-grading sheets
are shown as their controlled features. The root-only ``reference_evidence_parent`` context is not this episode's.

The input list (nano-graphrag ``PageRunState.remaining_chunks``): ``input_list`` holds the commissioned spans not yet
processed, in the parent's order; ``processed_spans`` the consumed ones. A span is consumed when the episode's completed
``source_read`` windows and ``no_applicable_evidence`` examined spans cover all its bytes; the list shrinks as spans are read
or examined and the episode's yield estimator ends the episode when it is empty."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assay_grading_features import (
    current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_assessment_features import (
    committed_assessment_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['tool'] == 'image_view'
              and last['outcome'].get('status') == 'completed' else [])
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': parent['spans']},
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'held_record_refs': sorted(view.records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'assay_sheets': current_sheet_features(view.records),
        'sheet_record_refs': sheet_records(view.records, reasons),
        'assessments': committed_assessment_features(view.records, reasons),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [examined_span(view.records, span) for outcome in reasons
                                   if declared_absent(outcome)
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    summary['processed_spans'], summary['input_list'] = input_list(parent['spans'], outcomes,
                                                                   summary['no_applicable_evidence'])
    return summary


def covered_intervals(outcomes, declared):
    """The byte intervals the episode has handed out or processed, per (source, representation): each completed
    ``source_read`` window and each source-grounded ``no_applicable_evidence`` examined span."""
    intervals = {}
    for outcome in outcomes:
        result = outcome['outcome'].get('result') if outcome['tool'] == 'source_read' else None
        if outcome['outcome'].get('status') == 'completed' and isinstance(result, dict):
            intervals.setdefault((result['source_ref'], result['representation']), []).append(
                (result['start'], result['end']))
    for span in declared:
        intervals.setdefault((span['source_ref'], span['representation']), []).append((span['start'], span['end']))
    return intervals


def input_list(spans, outcomes, declared):
    """The input list (nano-graphrag ``processed_chunk_ids`` / ``remaining_chunks``): the commissioned spans, in the
    parent's order, that the episode has not yet processed; a span is consumed once the episode's completed reads
    and examined declarations together cover all of its bytes. Returns (processed spans, remaining spans)."""
    intervals = covered_intervals(outcomes, declared)
    processed, remaining = [], []
    for span in spans:
        start, end = span['offset'], span['offset'] + span['limit']
        covered = start
        for first, last in sorted(intervals.get((span['source_ref'], span['representation']), [])):
            if first <= covered:
                covered = max(covered, last)
        (processed if covered >= end else remaining).append(span)
    return processed, remaining


def examined_span(records, span):
    """A span a ``no_applicable_evidence`` declaration examined, with the artifact of the representation read."""
    source = records.get(span['source_ref'])
    return {**span, 'artifact_ref': source['artifact_ref' if span['representation'] == 'original' else 'text_ref']}


def declared_absent(outcome):
    """Whether a reasoning outcome is a source-grounded ``no_applicable_evidence`` declaration."""
    processing = outcome['evidence_processing'] if 'evidence_processing' in outcome else None
    return processing is not None and processing['kind'] == 'no_applicable_evidence'


def sheet_records(records, reasons):
    """The records a receiver needs to read this Episode's assay-grading sheets again and to follow them to the
    graded interpretation: each sheet with its saved record and request artifacts, the records and sources it was
    graded from, and the records the graded reasoning committed (assay references, observations, hypotheses,
    assessments). References only; nothing of the model's text."""
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
