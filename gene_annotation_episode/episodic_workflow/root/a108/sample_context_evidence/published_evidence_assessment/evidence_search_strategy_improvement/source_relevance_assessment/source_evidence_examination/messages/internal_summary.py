"""Where the examination stands, as a pure function of the loop's view: the assignment (the page), custody of the
page's source, the first page of the episode's own read outcomes, what each child returned (its credit and the
controlled features of its sheets), the controlled features of the sheets saved (own and the children's), the
latest image the model looked at, and the answers the commissioned task asks for.

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

A child's return (``read_from_child``) is controlled data only: its credit, the features of its sheets with their
references, its relevant lead count and lead sources, its screening counts and the cell rows asked for. Its sheets'
features join the own ones side by side; its lead sources join the own relevant leads in the lead count. The records a
child returned (its assessments, sheets, cell rows) are held but never shown to this episode's model: the received-fact
display lists only the records this episode was given by its parent or produced itself."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    merged_findings, own_cell_refs, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, page_candidates)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError)

from ..credit import credit_binding, lead_dispositions, lead_return, screening_answers
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
POPULATION_TOOLS = ('literature_a108_grading_populate', 'literature_a108_aggregate')
FAILED = ('invalid', 'failed', 'error')

# The page's input list (nano-graphrag's page: ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``): the
# candidate input units of the commissioned representation (table regions and prose chunks, UTF-8 byte offsets, library
# ``page_candidates``). A candidate lying inside a window a child was commissioned with is consumed and offered no more;
# ``input_list`` is the unconsumed candidate ids in document order and the episode's yield estimator stops when it is
# empty. A representation that is not UTF-8 text (a workbook, a PDF, an image) has no text candidates: its basis is
# ``not_utf8``, its list is empty and its children keep their window / workbook selections (nothing to consume).
TEXT_BASIS, BINARY_BASIS = 'text', 'not_utf8'


def handed_windows(selection, page):
    """The byte windows of the page's own source and representation a child commission handed out: the one window of a
    window selection, every span of a ``spans`` selection; a workbook table selection (``sheet_key``) addresses rows,
    not bytes, and hands out none; a window of another source or representation is not a window of this page."""
    if 'sheet_key' in selection:
        return []
    windows = selection['spans'] if 'spans' in selection else [selection]
    return [(window['offset'], window['offset'] + window['limit']) for window in windows
            if window['source_ref'] == page['source_ref'] and window['representation'] == page['representation']]


def consumed_candidates(children, candidates, page):
    """The candidate ids the commissioned children were handed, in the order handed (nano-graphrag
    ``processed_chunk_ids`` and ``selected_source_table_ids``): every candidate lying inside a handed window."""
    consumed = []
    for outcome in children:
        for start, end in handed_windows(outcome['arguments']['selection'], page):
            consumed.extend(candidate['candidate_id'] for candidate in candidates
                            if start <= candidate['start'] and candidate['end'] <= end)
    return list(dict.fromkeys(consumed))


def completed(outcome):
    return outcome['status'] in ('completed', 'partial')


def received_fact_display(records):
    """The old ``_received_fact_display_context`` over the records this episode was given by its parent or produced
    itself: each such reference, term, context, observation, hypothesis and assessment. What a child returned is not
    shown (controlled messaging: a child's records reach this episode's code, never its model)."""
    shown = {}
    held = [ref for ref in records.refs() if records.receipt(ref)['how'] != 'returned']
    for reference in held:
        kind = next((kind for kind in DISPLAY_KINDS if reference.startswith(kind + '_')), None)
        if kind is None:
            continue
        record = records.get(reference)
        if record.get('id') != reference or record.get('record_type') != kind:
            raise ContractError('literature_received_fact_display_record_mismatch')
        shown[reference] = record
    return {'records': shown, 'received_refs': held}


def representation_artifact(source, representation):
    """The artifact a source holds for one representation (the old ``SourceReferences._artifact``)."""
    if representation == 'original':
        return source['artifact_ref']
    if representation == 'text':
        return source.get('text_ref') or source['artifact_ref']
    return source.get(representation + '_ref')


def graded_assessments(records, reasons):
    """The current retained assessments this episode committed (each with its grading sheet), by reference."""
    found = []
    for outcome in reasons:
        for ref in outcome['record_refs']:
            record = records.get(ref)
            if (record['record_type'] == 'assessment' and record['investigation_finding']['status'] == 'retained'
                    and records.is_current(ref)):
                found.append(ref)
    return found


def declared_spans(records, reasons):
    """The examined spans of the own source-grounded ``no_applicable_evidence`` declarations."""
    spans = []
    for outcome in reasons:
        processing = outcome['evidence_processing']
        if processing is not None and processing['kind'] == 'no_applicable_evidence':
            for witness in processing['examined']:
                held = records.get(witness['source_ref'])
                spans.append({**witness, 'artifact_ref': held['artifact_ref' if witness['representation'] == 'original'
                                                             else 'text_ref']})
    return spans


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    source = records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    child_reports = [{'slot': outcome['slot'], 'selection': outcome['arguments']['selection'], **outcome['report']}
                     for outcome in view.outcomes if outcome['kind'] == 'child']
    reasons = [outcome['outcome'] for outcome in outcomes
               if outcome['tool'] == 'reason' and completed(outcome['outcome'])]
    finding = {**merged_findings(own_findings(records), [child['finding'] for child in child_reports]),
               'assessment_refs': list(dict.fromkeys(
                   graded_assessments(records, reasons)
                   + [ref for child in child_reports for ref in child['finding']['assessment_refs']]))}
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome']['visual_inputs'] if last is not None and last['tool'] == 'image_view'
              and last['outcome']['status'] == 'completed' else [])
    attempt = None
    if last is not None and last['tool'] in POPULATION_TOOLS and last['outcome']['status'] in FAILED:
        attempt = {'tool': last['tool'], 'status': last['outcome']['status']}
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    content = representation_content(records, page['source_ref'], page['representation'])
    try:
        candidates, basis = page_candidates(content), TEXT_BASIS
    except UnicodeDecodeError:
        candidates, basis = [], BINARY_BASIS
    consumed = consumed_candidates([outcome for outcome in view.outcomes if outcome['kind'] == 'child'],
                                   candidates, page)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    summary = {
        'input_list': [candidate['candidate_id'] for candidate in unconsumed],
        'input_list_basis': basis,
        'content_candidates': candidates,
        'consumed_candidate_ids': consumed,
        'unconsumed_candidates': unconsumed,
        'unconsumed_candidate_ids': [candidate['candidate_id'] for candidate in unconsumed],
        'unconsumed_table_ids': [candidate['candidate_id'] for candidate in unconsumed
                                 if candidate['candidate_type'] == SOURCE_TABLE],
        'unconsumed_chunk_ids': [candidate['candidate_id'] for candidate in unconsumed
                                 if candidate['candidate_type'] == PROSE_CHUNK],
        'table_previews': {candidate['candidate_id']: candidate_text(content, candidate)[:TABLE_PREVIEW_CHARS]
                           for candidate in unconsumed if candidate['candidate_type'] == SOURCE_TABLE},
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       'page_artifact_ref': representation_artifact(source, page['representation']),
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome['tool']),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                                         'aspect': 'source_experimental_evidence', 'evidence_axis': 'A108'},
        'literature_received_fact_display': received_fact_display(records),
        'literature_owned_population_sources': [name for name, tool in zip((GRADING_NAMESPACE, AGGREGATION_NAMESPACE),
                                                                           POPULATION_TOOLS)
                                                if any(outcome['tool'] == tool and completed(outcome['outcome'])
                                                       for outcome in outcomes)],
        'literature_selected_population_attempt': attempt,
        'literature_goal_plan': {'objective': view.goal.as_record(), 'commission_message': parent['message'],
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
        'child_reports': child_reports,
        'finding': finding,
        'grading_cell_refs': list(dict.fromkeys(
            own_cell_refs(records, GRADING_NAMESPACE)
            + [ref for child in child_reports for ref in child.get(GRADING_NAMESPACE, ())])),
        'aggregation_cell_refs': list(dict.fromkeys(
            own_cell_refs(records, AGGREGATION_NAMESPACE)
            + [ref for child in child_reports for ref in child.get(AGGREGATION_NAMESPACE, ())])),
        'source_leads': [outcome['literature_source_lead'] for outcome in reasons if 'literature_source_lead' in outcome],
        'returned_lead_source_refs': [ref for child in child_reports if 'leads' in child
                                      for ref in child['leads']['lead_source_refs']],
        'no_applicable_evidence': declared_spans(records, reasons),
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['lead_return'] = lead_return(summary, records)
    summary['screening_answers'] = screening_answers(summary)
    summary['screening_return'] = screening_return(summary['no_applicable_evidence'], summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
