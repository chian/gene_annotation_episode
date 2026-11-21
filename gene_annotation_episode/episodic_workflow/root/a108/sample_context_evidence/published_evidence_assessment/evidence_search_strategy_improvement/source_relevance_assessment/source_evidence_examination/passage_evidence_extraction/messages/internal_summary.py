"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the interpretation written so far, the latest image the model looked
at, the sheets the episode saved, and the typed answers the commissioned task asks for (carried from the old
``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, ``literature_experimental_work``, ``literature_received_fact_display``,
``literature_selected_population_attempt``, and from ``decision_context.py`` the ``visual_evidence`` of the latest
completed ``image.view``; the old reads of ``runtime_actions`` and of the operation ledgers are the unit outcomes of
``view``). The root-only ``reference_evidence_parent`` context is not this episode's."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    lead_return, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, examined_spans, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_xlsx_rows', 'source_pdf_text',
              'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
POPULATION_TOOLS = ('grading_populate', 'aggregate_populate')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')
FACT_KINDS = ('reference', 'term', 'context', 'observation', 'hypothesis', 'assessment')


def completed(outcome):
    return isinstance(outcome, dict) and outcome.get('status') in ('completed', 'partial')


def sheet_refs(outcomes):
    """The subscoring and main sheets the episode saved, in order: the sheet of each graded ``reason`` and of each
    population tool (the old ``current_sheet_refs`` over the operation ledgers)."""
    found = []
    for outcome in outcomes:
        value = outcome['outcome']
        if not completed(value):
            continue
        if outcome['tool'] == 'reason':
            processing = value.get('evidence_processing') or {}
            if processing.get('kind') == 'graded':
                found.extend(grading['result']['sheet_ref'] for grading in processing['gradings'])
        elif outcome['tool'] in POPULATION_TOOLS:
            found.append(value['result']['sheet_ref'])
    return list(dict.fromkeys(found))


def selected_population_attempt(outcomes):
    """The old ``_population_task_context`` latest selected failed action: only a population tool that did not
    complete."""
    if not outcomes:
        return None
    last = outcomes[-1]
    if last['tool'] in POPULATION_TOOLS and last['outcome'].get('status') in ('invalid', 'failed', 'error'):
        return {'tool': last['tool'], 'status': last['outcome']['status']}
    return None


def received_fact_display(records):
    """The old ``_received_fact_display_context`` over the held records of the display kinds."""
    shown = {}
    for reference in records.refs():
        kind = next((kind for kind in FACT_KINDS if reference.startswith(kind + '_')), None)
        if kind is None:
            continue
        record = records.get(reference)
        if record.get('id') != reference or record.get('record_type') != kind:
            raise ValueError('literature_received_fact_display_record_mismatch')
        shown[reference] = record
    return {'records': shown, 'received_refs': sorted(records.refs())}


def graded_assessments(records, reasons):
    """The current retained assessments this episode committed (each with its grading sheet), by reference; their
    typed ``investigation_finding`` stays in the record."""
    found = []
    for outcome in reasons:
        for ref in outcome['record_refs']:
            record = records.get(ref)
            if (record['record_type'] == 'assessment' and record['investigation_finding']['status'] == 'retained'
                    and records.is_current(ref)):
                found.append(ref)
    return list(dict.fromkeys(found))


def span_processed(span, page, reasons, records):
    """A commissioned window is processed (consumed, nano-graphrag's processed chunk) once a completed reasoning commit
    has dealt with it: the commit declared the window examined without applicable evidence
    (``evidence_processing.examined``, whose witnesses together must cover it), or a record the commit made is anchored
    within the window's bytes of the page's artifact."""
    start, end = span['offset'], span['offset'] + span['limit']
    covered = start
    intervals = []
    for outcome in reasons:
        processing = outcome.get('evidence_processing') or {}
        if processing.get('kind') != 'no_applicable_evidence' or not processing.get('reason'):
            continue
        for witness in processing['examined']:
            source = records.get(witness['source_ref'])
            artifact = source.get('artifact_ref' if witness['representation'] == 'original' else 'text_ref')
            if (witness['source_ref'], artifact) == (page['source_ref'], page['artifact_ref']):
                intervals.append((witness['start'], witness['end']))
    for first, last in sorted(intervals):
        if first <= covered:
            covered = max(covered, last)
    if covered >= end:
        return True
    for outcome in reasons:
        for ref in outcome.get('record_refs', []):
            anchor = records.get(ref).get('anchor')
            if (anchor is not None and anchor['artifact_ref'] == page['artifact_ref']
                    and start <= anchor['start'] and anchor['end'] <= end):
                return True
    return False


def input_list(parent, reasons, records):
    """``(consumed, input_list)``: the commissioned windows as ``[offset, end]`` pairs, in the order assigned, those a
    completed commit has processed and those still to process. A consumed window is no longer offered; the episode's
    yield estimator ends it when the input list is empty."""
    page = parent['page']
    pairs = [(span, [span['offset'], span['offset'] + span['limit']]) for span in parent['spans']]
    done = [pair for span, pair in pairs if span_processed(span, page, reasons, records)]
    return done, [pair for _, pair in pairs if pair not in done]


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason' and completed(outcome['outcome'])]
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['tool'] == 'image_view'
              and last['outcome'].get('status') == 'completed' else [])
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': parent['spans']},
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    consumed, remaining = input_list(parent, reasons, view.records)
    summary = {
        'input_list': remaining, 'consumed_inputs': consumed,
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                                         'aspect': 'source_experimental_evidence', 'evidence_axis': 'A108'},
        'literature_received_fact_display': received_fact_display(view.records),
        'literature_selected_population_attempt': selected_population_attempt(outcomes),
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'held_record_refs': sorted(view.records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'finding': {**own_findings(view.records), 'assessment_refs': graded_assessments(view.records, reasons)},
        'sheet_refs': sheet_refs(outcomes),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [outcome['evidence_processing'] for outcome in reasons
                                   if (outcome.get('evidence_processing') or {}).get('kind') == 'no_applicable_evidence'],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary, view.records)
    summary['lead_return'] = lead_return(summary['source_lead_dispositions'])
    summary['screening_return'] = screening_return(examined_spans(summary, view.records), summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
