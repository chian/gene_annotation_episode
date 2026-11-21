"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the controlled features of the current A106 sheets it saved (G1
and G2, ``literature_a106_findings.own_findings``), the latest image the model looked at, and the typed answers the commissioned task asks for (carried from the
old ``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, and from ``decision_context.py`` the ``visual_evidence`` of the latest completed
``image.view``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``).

The root-only ``reference_evidence_parent`` context is not
this episode's."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_population_route import (
    opened_population)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')


def span_processed(span, page, reasons, records):
    """A commissioned window is processed (consumed, nano-graphrag's processed chunk) once a reasoning commit has
    dealt with it: the commit declared the window examined without applicable evidence
    (``evidence_processing.examined``, which must cover it), or a record the commit made is anchored in the window's
    bytes of the page's artifact."""
    start, end = span['offset'], span['offset'] + span['limit']
    covered = start
    for outcome in reasons:
        for examined in outcome.get('evidence_processing', {}).get('examined', []):
            if ((examined['source_ref'], examined['artifact_ref']) == (page['source_ref'], page['artifact_ref'])
                    and examined['start'] <= covered):
                covered = max(covered, examined['end'])
    if covered >= end:
        return True
    for outcome in reasons:
        for ref in outcome.get('record_refs', []):
            anchor = records.get(ref).get('anchor')
            if (anchor is not None and anchor['artifact_ref'] == page['artifact_ref']
                    and start <= anchor['start'] and anchor['end'] <= end):
                return True
    return False


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    # The input list (nano-graphrag's remaining chunks): the commissioned windows still unprocessed, in the order
    # assigned, as [offset, end] pairs; a processed window is consumed and no longer offered, and the yield
    # estimator ends the episode when the list is empty.
    committed = [outcome for outcome in reasons if outcome.get('status') in ('completed', 'partial')]
    consumed = [[span['offset'], span['offset'] + span['limit']] for span in parent['spans']
                if span_processed(span, page, committed, view.records)]
    input_list = [[span['offset'], span['offset'] + span['limit']] for span in parent['spans']
                  if [span['offset'], span['offset'] + span['limit']] not in consumed]
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
        'input_list': input_list, 'consumed_inputs': consumed,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': own_findings(view.records, view.outcomes),
        'opened_population': opened_population(view.outcomes),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
