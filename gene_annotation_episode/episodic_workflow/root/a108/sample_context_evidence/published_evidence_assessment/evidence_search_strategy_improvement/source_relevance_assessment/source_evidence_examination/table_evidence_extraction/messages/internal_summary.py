"""Where the reading stands, as a pure function of the loop's view: the assignment (the page and its table/sheet or
window selection), custody of the page's source, the first page of the episode's own read outcomes, the controlled
features of the contextual sheets saved, the latest image
the model looked at, and the answers the commissioned task asks for.

Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``, ``_owned_population_task_sources``,
``_population_task_context``, ``_received_fact_display_context``), ``decision_inputs.py`` and ``decision_presentation.py``:
``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``,
``literature_experimental_work``, ``literature_received_fact_display``, ``literature_owned_population_sources``,
``literature_selected_population_attempt``, ``literature_goal_plan`` (the old ``planning_context``), ``visual_evidence``
and the yield table. The old reads of ``runtime_actions`` and of the operations tables are the unit outcomes of
``view``.

Not carried: ``initial_decision_context`` (the root-only ``reference_evidence_parent`` context is not this episode's);
``literature_examined_source_inputs`` (old ``literature_source_inputs.own_source_inputs``) and the source metadata of
the received-fact display (old ``literature_work_report.source_metadata``): those two old shared-library modules are not
in ``episode_support/`` and are not rebuilt here.

The finding returned to the parent is the controlled features code reads from the saved sheets
(``literature_context_findings``); the assessments' typed ``investigation_finding`` stays in the records."""

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    lead_return, own_cell_refs, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError)

from ..credit import credit_binding, lead_dispositions, screening_answers
from ..goal import GOAL
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_xlsx_rows', 'source_pdf_text',
              'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')
DISPLAY_KINDS = ('reference', 'term', 'context', 'observation', 'hypothesis', 'assessment')
GRADING_NAMESPACE = 'literature_a108_grading_cells'
AGGREGATION_NAMESPACE = 'literature_a108_aggregation_cells'
FAILED = ('invalid', 'failed', 'error')


def population_sheets(outcomes, tool):
    """The sheets the population tool ``tool`` saved: the ``sheet_ref`` of each of its completed or partial outcomes."""
    return list(dict.fromkeys(
        outcome['outcome']['result']['sheet_ref'] for outcome in outcomes
        if outcome['tool'] == tool and outcome['outcome'].get('status') in ('completed', 'partial')
        and (outcome['outcome'].get('result') or {}).get('sheet_ref')))


def received_fact_display(records):
    """The old ``_received_fact_display_context`` over the records this episode holds: each held reference, term,
    context, observation, hypothesis and assessment (the source metadata of the old display is unplaced)."""
    shown = {}
    held = list(records.refs())
    for reference in held:
        kind = next((kind for kind in DISPLAY_KINDS if reference.startswith(kind + '_')), None)
        if kind is None:
            continue
        record = records.get(reference)
        if record.get('id') != reference or record.get('record_type') != kind:
            raise ContractError('literature_received_fact_display_record_mismatch')
        shown[reference] = record
    return {'records': shown, 'received_refs': held}


def completed(outcome):
    return outcome['status'] in ('completed', 'partial')


def graded_assessments(records, reasons):
    """The current retained assessments this episode committed (each with its grading sheet), by reference."""
    found = []
    for outcome in reasons:
        for ref in outcome['record_refs']:
            record = records.get(ref)
            if (record['record_type'] == 'assessment' and record['investigation_finding']['status'] == 'retained'
                    and records.is_current(ref)):
                found.append(ref)
    return list(dict.fromkeys(found))


def selected_region(selection):
    """The one region the commission selects, as ``[start, end]``: the rows ``[offset, offset + limit]`` of a table
    selection, the bytes ``[offset, offset + limit]`` of a window selection."""
    return [selection['offset'], selection['offset'] + selection['limit']]


def table_inputs(selection, reasons):
    """The input list (nano-graphrag ``SourceTableRun.processed_row_ids``: a selected table region is consumed once it
    has been processed): the selected region of the commission, unconsumed until a reasoning over it has been committed
    (a completed or partial ``reason`` outcome), and empty after that. Returns ``(consumed, input_list)``."""
    region = selected_region(selection)
    return ([region], []) if reasons else ([], [region])


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    source = records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes
               if outcome['tool'] == 'reason' and completed(outcome['outcome'])]
    graded = [grading['result']['sheet_ref'] for outcome in reasons
              if outcome['evidence_processing'] is not None and outcome['evidence_processing']['kind'] == 'graded'
              for grading in outcome['evidence_processing']['gradings']]
    grading_sheets = list(dict.fromkeys(graded + population_sheets(outcomes, 'literature_a108_grading_populate')))
    aggregation_sheets = population_sheets(outcomes, 'literature_a108_aggregate')
    spans = []
    for outcome in reasons:
        processing = outcome['evidence_processing']
        if processing is not None and processing['kind'] == 'no_applicable_evidence':
            for witness in processing['examined']:
                held = records.get(witness['source_ref'])
                spans.append({**witness, 'artifact_ref': held['artifact_ref' if witness['representation'] == 'original'
                                                             else 'text_ref']})
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome']['visual_inputs'] if last is not None and last['tool'] == 'image_view'
              and last['outcome']['status'] == 'completed' else [])
    attempt = None
    if (last is not None and last['tool'] in ('literature_a108_grading_populate', 'literature_a108_aggregate')
            and last['outcome']['status'] in FAILED):
        attempt = {'tool': last['tool'], 'status': last['outcome']['status']}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['selection'],
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    consumed_inputs, input_list = table_inputs(parent['selection'], reasons)
    summary = {
        'input_list': input_list, 'consumed_inputs': consumed_inputs,
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome['tool']),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                                         'aspect': 'source_experimental_evidence', 'evidence_axis': 'A108'},
        'literature_received_fact_display': received_fact_display(records),
        'literature_owned_population_sources': [name for name, refs in ((GRADING_NAMESPACE, grading_sheets),
                                                                        (AGGREGATION_NAMESPACE, aggregation_sheets))
                                                if refs],
        'literature_selected_population_attempt': attempt,
        'literature_goal_plan': {'objective': view.goal.as_record(),
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task, 'progress_definition': binding,
                                 'planning_question': GOAL},
        'credit_binding': binding,
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'finding': {**own_findings(records), 'assessment_refs': graded_assessments(records, reasons)},
        'grading_cell_refs': own_cell_refs(records, GRADING_NAMESPACE),
        'aggregation_cell_refs': own_cell_refs(records, AGGREGATION_NAMESPACE),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons
                         if 'literature_source_lead' in outcome],
        'no_applicable_evidence': spans,
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    summary['lead_return'] = lead_return(summary['source_lead_dispositions'])
    summary['screening_return'] = screening_return(spans, summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
