"""Where the examination stands, as a pure function of the loop's view: the assignment, custody of the page's source,
the first page of the episode's own read outcomes, the controlled features of the current A106 sheets it saved and
its investigations returned (``literature_a106_findings``), the reports of the investigations it commissioned, the latest image the model looked at, and the typed answers the commissioned task
asks for (carried from the old ``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``,
``own_literature_outcomes``, ``literature_history_meaning``, ``literature_experimental_work``, and from
``decision_context.py`` the ``visual_evidence`` of the latest completed ``image.view``; the old reads of
``runtime_actions`` are the unit outcomes of ``view``, and the old ``completed_action_reports`` are the child
reports ``read_from_child`` made).

``literature_examined_source_inputs`` and
``received_intervention_analysis_rows`` need the old library readers over ``runtime_*`` tables and the BV-BRC
execution binding (``own_source_inputs``, ``intervention_execution_lookup``) and are not carried. The root-only
``reference_evidence_parent`` context is not this episode's."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, page_candidates, report_windows)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings, own_findings)
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
EXPERIMENTAL_WORK = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence',
                     'evidence_axis': 'A106'}


def handed_windows(children):
    """The byte windows the investigations commissioned so far were handed (the child's assignment selection, which
    ``msg_to_child`` built from the candidates the model named): one window of a table or an ordered-reading commission,
    each span of a targeted-passage commission."""
    windows = []
    for outcome in children:
        selection = outcome['message']['assignment']['selection']
        windows.extend(selection['spans'] if 'spans' in selection else [selection])
    return windows


def consumed_candidates(children, candidates):
    """The candidate ids handed out, in document order (nano-graphrag ``selected_source_table_ids`` and
    ``processed_chunk_ids``): a candidate lying inside a window a commissioned investigation was handed is consumed and
    never offered again."""
    windows = handed_windows(children)
    return [candidate['candidate_id'] for candidate in candidates
            if any(window['offset'] <= candidate['start'] and candidate['end'] <= window['offset'] + window['limit']
                   for window in windows)]


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    source = view.records.get(page['source_ref'])
    # The input list (nano-graphrag's page state): the source's candidate input units (table regions and prose chunks,
    # UTF-8 byte offsets of the representation the page was assigned), the ones handed to an investigation consumed. Only
    # unconsumed candidates are offered; the list shrinks as each investigation is commissioned and is empty when every
    # candidate has been handed out. The yield estimator is not given this list and an empty list ends no episode: a
    # verified_source_leads episode's AccumulationYieldController (ADAPTIVE_CONTROL, items=None, no cost) stops only
    # after 4 flat units in a row, a unit being flat when the upper bound of its expected next marginal (hypervolume)
    # credit is at or below the adaptive gamma (fitted from W = 8 units attempted and m = 4 observed).
    content = view.records.get_artifact(page['artifact_ref'])
    candidates = page_candidates(content)
    children_outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    consumed = consumed_candidates(children_outcomes, candidates)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    last = view.outcomes[-1] if view.outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['kind'] == 'tool'
              and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed' else [])
    # The leads in the order of the units: an own validated lead of a reasoning commit, and each relevant lead source
    # an admitted child return names (the old ``lead_dispositions`` merged them by decision order).
    leads, children = [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            leads.extend({'source_ref': ref, 'disposition': 'relevant',
                          'proposed_annotation_ref': parent['proposed_annotation_ref']}
                         for ref in (outcome['report']['lead_source_refs'] if task['kind'] == 'verified_source_leads' else ()))
            children.append({'slot': outcome['slot'], 'arguments': outcome['arguments'],
                             'report': outcome['report']})
        elif outcome['tool'] == 'reason' and 'literature_source_lead' in outcome['outcome']:
            leads.append(outcome['outcome']['literature_source_lead'])
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment, 'page': page,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': EXPERIMENTAL_WORK,
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'held_record_refs': sorted(view.records.refs()),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'child_reports': children,
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': merged_findings(own_findings(view.records, view.outcomes),
                                         [child['report']['finding'] for child in children]),
        'opened_population': opened_population(view.outcomes),
        'source_leads': leads,
        'content_candidates': candidates,
        'consumed_candidate_ids': consumed,
        'unconsumed_chunk_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == PROSE_CHUNK],
        'unconsumed_table_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == SOURCE_TABLE],
        'report_windows': report_windows(candidates, {item['candidate_id'] for item in unconsumed}),
        'table_previews': {item['candidate_id']: candidate_text(content, item)[:TABLE_PREVIEW_CHARS]
                           for item in unconsumed if item['candidate_type'] == SOURCE_TABLE},
        'input_list': [item['candidate_id'] for item in unconsumed],
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
