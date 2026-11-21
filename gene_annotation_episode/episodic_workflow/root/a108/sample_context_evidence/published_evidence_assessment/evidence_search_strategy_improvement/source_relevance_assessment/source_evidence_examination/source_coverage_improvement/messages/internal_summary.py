"""Where the reading stands, as a pure function of the loop's view: the assignment, custody of the page's source, the
first page of the episode's own read outcomes, the saved A108 sheets and their controlled features so far, the
latest image the model looked at, and the answers the commissioned task asks for.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``,
``literature_experimental_work``, ``literature_received_fact_display``, ``literature_owned_population_sources``,
``literature_selected_population_attempt``, ``literature_goal_plan``), from ``decision_context.py`` (the
``visual_evidence`` of the latest completed ``image.view``), from ``to_parent.py`` (``_a108_facts``: the requested
cells) and from ``credit.py`` (the answers). The old reads of ``runtime_actions`` and of the population operation
tables are the unit outcomes of ``view``: a grading or aggregation outcome carries the requested cells of the sheet.
The own cells are shown to this episode's model only; the finding returned to the parent is the controlled features
code reads from the saved sheets (``literature_context_findings``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    lead_return, own_cell_refs, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_reading_input_list import (
    input_list, read_ranges)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers
from ..goal import GOAL

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_xlsx_rows', 'source_pdf_text',
              'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')
# The old ``_population_routes``: (namespace, requested field, provider, populate tool).
POPULATION_ROUTES = (
    ('literature_a108_grading_cells', 'requested_a108_grading_components', 'literature.a108.context_grading',
     'literature_a108_grading_populate'),
    ('literature_a108_aggregation_cells', 'requested_a108_aggregation_components', 'literature.a108.aggregation',
     'literature_a108_aggregate'))
DISPLAY_KINDS = ('reference', 'term', 'context', 'observation', 'hypothesis', 'assessment')
FAILED = ('invalid', 'failed', 'error')



def completed(outcome):
    return outcome['status'] in ('completed', 'partial')


def latest_cells(cells):
    """One cell per sheet and component, the latest saved (a repeated population of a sheet rewrites its cells)."""
    kept = {}
    for cell in cells:
        kept[(cell['sheet_ref'], cell['component'])] = cell
    return list(kept.values())


def graded_cells(outcomes):
    """The grading cells: those of the gradings coupled to a reason action and of the grading population tool."""
    cells = []
    for outcome in outcomes:
        value = outcome['outcome']
        if outcome['tool'] == 'reason' and completed(value):
            processing = value['evidence_processing']
            if processing is not None and processing['kind'] == 'graded':
                for grading in processing['gradings']:
                    cells.extend(grading['result']['cells'])
        elif outcome['tool'] == POPULATION_ROUTES[0][3] and completed(value):
            cells.extend(value['result']['cells'])
    return latest_cells(cells)


def aggregated_cells(outcomes):
    cells = []
    for outcome in outcomes:
        if outcome['tool'] == POPULATION_ROUTES[1][3] and completed(outcome['outcome']):
            cells.extend(outcome['outcome']['result']['cells'])
    return latest_cells(cells)


def graded_assessments(records, reasons):
    """The current retained assessments this episode committed (each together with its grading sheet: the
    ``reason`` tool admits no interpretation without it), by reference. Their typed ``investigation_finding``
    stays in the record."""
    found = []
    for outcome in reasons:
        for ref in outcome['record_refs']:
            record = records.get(ref)
            if (record['record_type'] == 'assessment' and record['investigation_finding']['status'] == 'retained'
                    and records.is_current(ref)):
                found.append(ref)
    return list(dict.fromkeys(found))


def declared_spans(records, reasons):
    """The examined spans of the own source-grounded ``no_applicable_evidence`` declarations, with the artifact of
    the representation read."""
    spans = []
    for outcome in reasons:
        processing = outcome['evidence_processing']
        if processing is not None and processing['kind'] == 'no_applicable_evidence':
            for witness in processing['examined']:
                holder = records.get(witness['source_ref'])
                spans.append({**witness, 'artifact_ref': holder['artifact_ref' if witness['representation'] == 'original'
                                                               else 'text_ref']})
    return spans


def internal_summary(view):
    parent = view.parent_input
    page, task, records = parent['page'], parent['task'], view.records
    source = records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason' and completed(outcome['outcome'])]
    requested = {name: parent[name] for _, name, _, _ in POPULATION_ROUTES}
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome']['visual_inputs'] if last is not None and last['tool'] == 'image_view'
              and last['outcome']['status'] == 'completed' else [])
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['window'],
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'], **requested}
    credit = credit_binding(parent['task_key'], task)
    grading, aggregation = graded_cells(outcomes), aggregated_cells(outcomes)
    attempt = None
    if (last is not None and last['tool'] in [route[3] for route in POPULATION_ROUTES]
            and last['outcome']['status'] in FAILED):
        attempt = {'tool': last['tool'], 'status': last['outcome']['status']}
    # The input list (nano-graphrag remaining_chunks): the page source's unread content candidates from the commissioned
    # window on, in document order; a candidate covered by this episode's own source.read windows is consumed.
    reading = input_list(representation_content(records, page['source_ref'], page['representation']),
                         parent['window']['offset'], read_ranges(outcomes, page['source_ref'], page['representation']))
    finding = {**own_findings(records), 'assessment_refs': graded_assessments(records, reasons)}
    summary = {
        'literature_assignment': assignment, 'requested': requested,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome['tool']),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                                         'aspect': 'source_experimental_evidence', 'evidence_axis': 'A108'},
        'literature_owned_population_sources': [namespace for namespace, _, _, tool in POPULATION_ROUTES
                                                if any(outcome['tool'] == tool and completed(outcome['outcome'])
                                                       for outcome in outcomes)],
        'literature_selected_population_attempt': attempt,
        'literature_received_fact_display': {
            'records': {ref: records.get(ref) for ref in sorted(records.refs())
                        if ref.split('_', 1)[0] in DISPLAY_KINDS},
            'received_refs': list(parent['received_record_refs'])},
        'credit_binding': credit,
        'literature_goal_plan': {'objective': parent['message'], 'proposed_annotation_ref':
                                 parent['proposed_annotation_ref'], 'commissioned_result': task,
                                 'progress_definition': credit, 'planning_question': GOAL},
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'input_list': reading['input_list'], 'consumed_input_ids': reading['consumed_ids'],
        'remaining_windows': reading['windows'],
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'finding': finding,
        'grading_cells': grading, 'aggregation_cells': aggregation,
        'grading_cell_refs': own_cell_refs(records, POPULATION_ROUTES[0][0]),
        'aggregation_cell_refs': own_cell_refs(records, POPULATION_ROUTES[1][0]),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons if 'literature_source_lead' in outcome],
        'no_applicable_evidence': declared_spans(records, reasons),
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    summary['lead_return'] = lead_return(summary['source_lead_dispositions'])
    summary['screening_return'] = screening_return(summary['no_applicable_evidence'], summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
