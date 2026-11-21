"""Where the search strategy improvement stands, as a pure function of the loop's view: the strategy assignment,
custody of the sources it holds, the first page of the episode's own acquisition and read outcomes, the interpretation
written so far, what the child returned, the investigation findings of the assessments committed (own and the child's), the contextual
sheets saved, the latest image the model looked at, and the typed answers the commissioned task asks for.

Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``, ``_owned_population_task_sources``,
``_population_task_context``, ``_received_fact_display_context``), ``decision_inputs.py`` and ``decision_presentation.py``
of ``literature_strategy``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, ``literature_experimental_work``, ``literature_received_fact_display``,
``literature_owned_population_sources``, ``literature_selected_population_attempt``, ``literature_goal_plan`` (the old
``planning_context``), ``visual_evidence`` and the yield table. The old reads of ``runtime_actions`` and of the
operations tables are the unit outcomes of ``view``.

Differences from the old context, both needed by the new custody rule: the source custody lists the sources of
``prior_search_refs`` (the old listed ``assignment['source_refs']``, which a strategy assignment does not have, so it was
empty) and the task's ``source_refs``; ``held_source_custody`` lists the artifacts and parent sources of every held
source and ``proposed_annotation_subject_refs`` the subjects of the proposed annotation, which ``msg_to_child`` names
when it commissions the child (decision T5).

Not carried: ``initial_decision_context`` (the root-only ``reference_evidence_parent`` context is not this episode's);
``literature_examined_source_inputs`` (old ``literature_source_inputs.own_source_inputs``) and the source metadata of
the received-fact display (old ``literature_work_report.source_metadata``): those two old shared-library modules are not
in ``episode_support/`` and are not rebuilt here.

The child's return (``read_from_child``) joins the own work in decision order: its source leads join the own leads, and
its committed records, findings, sheets and cells join the own ones. Child logs are never read.

A child's return is controlled data only (credit, the features of its sheets with their references, the lead count
and lead sources, the screening counts, the requested cell rows by reference); the records it returned reach this
episode's code, never its model: the received-fact display leaves them out."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    merged_findings, own_cell_refs, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError)

from ..credit import credit_binding, lead_dispositions, lead_return, screening_answers
from ..goal import GOAL
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_taxonomy', 'public_ncbi_sequence')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_xlsx_rows', 'source_pdf_text',
              'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
STRATEGY_ASSIGNMENT = 'strategy_assignment_v1'
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


def source_custody(records, held):
    """The custody of each held source: its version, artifacts and the sources it derives from."""
    return {reference: {key: records.get(reference).get(key) for key in CUSTODY_KEYS}
            for reference in held if reference.startswith('source_')}


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


SEARCH_TOOLS = ('public_literature_search', 'public_ncbi_search')


def candidate_sources(parent, outcomes, records):
    """The candidate sources of the episode's input list (nano-graphrag web search state: search results and
    candidate sources), in arrival order: the prior search results the assignment names, the task's own sources, then
    the source records this episode's own searches returned and it holds."""
    found = [*parent['prior_search_refs'], *parent['task'].get('source_refs', [])]
    for outcome in outcomes:
        if outcome['kind'] == 'tool' and outcome['tool'] in SEARCH_TOOLS:
            found.extend(ref for ref in outcome['outcome'].get('record_refs', ())
                         if ref.startswith('source_') and records.holds(ref))
    return list(dict.fromkeys(found))


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    records = view.records
    # The input list: candidate sources not yet handed to the assessment child; a source handed out is consumed and
    # no longer offered (nano-graphrag ``PageRunState.processed_chunk_ids`` / ``remaining_chunks``). The yield
    # estimator (another agent's) stops when it is empty.
    consumed = list(dict.fromkeys(ref for outcome in view.outcomes if outcome['kind'] == 'child'
                                  for ref in outcome['arguments']['search_result_refs']))
    input_list = [ref for ref in candidate_sources(parent, view.outcomes, records) if ref not in consumed]
    held = sorted(records.refs())
    custody = source_custody(records, held)
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    child_reports = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                      'search_result_refs': outcome['arguments']['search_result_refs'],
                      **outcome['report']}
                     for outcome in view.outcomes if outcome['kind'] == 'child']
    reasons = [outcome['outcome'] for outcome in outcomes
               if outcome['tool'] == 'reason' and outcome['outcome']['status'] in ('completed', 'partial')]
    graded = [grading['result']['sheet_ref'] for outcome in reasons
              if outcome['evidence_processing'] is not None and outcome['evidence_processing']['kind'] == 'graded'
              for grading in outcome['evidence_processing']['gradings']]
    grading_sheets = list(dict.fromkeys(graded + population_sheets(outcomes, 'literature_a108_grading_populate')))
    aggregation_sheets = population_sheets(outcomes, 'literature_a108_aggregate')
    leads = [outcome['literature_source_lead'] for outcome in reasons if 'literature_source_lead' in outcome]
    spans = []
    for outcome in reasons:
        processing = outcome['evidence_processing']
        if processing is not None and processing['kind'] == 'no_applicable_evidence':
            for witness in processing['examined']:
                examined = records.get(witness['source_ref'])
                spans.append({**witness, 'artifact_ref': examined.get('artifact_ref' if witness['representation'] == 'original'
                                                                      else 'text_ref')})
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome']['visual_inputs'] if last is not None and last['tool'] == 'image_view'
              and last['outcome']['status'] == 'completed' else [])
    attempt = None
    if (last is not None and last['tool'] in ('literature_a108_grading_populate', 'literature_a108_aggregate')
            and last['outcome']['status'] in FAILED):
        attempt = {'tool': last['tool'], 'status': last['outcome']['status']}
    assignment = {'version': STRATEGY_ASSIGNMENT, 'question_context_refs': parent['question_context_refs'],
                  'prior_search_refs': parent['prior_search_refs'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': reference, **custody[reference]} for reference in
                                      dict.fromkeys([*parent['prior_search_refs'], *task.get('source_refs', [])])],
        'held_source_custody': custody,
        'proposed_annotation_subject_refs': records.get(parent['proposed_annotation_ref'])['subject_refs'],
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=(*ACQUISITION_TOOLS, *READ_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
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
        'held_record_refs': held,
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'input_list': input_list,
        'consumed_search_result_refs': consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_reports': child_reports,
        'finding': {**merged_findings(own_findings(records), [child['finding'] for child in child_reports]),
                    'assessment_refs': list(dict.fromkeys(
                        graded_assessments(records, reasons)
                        + [ref for child in child_reports for ref in child['finding']['assessment_refs']]))},
        'grading_cell_refs': list(dict.fromkeys(
            own_cell_refs(records, GRADING_NAMESPACE)
            + [ref for child in child_reports for ref in child.get(GRADING_NAMESPACE, ())])),
        'aggregation_cell_refs': list(dict.fromkeys(
            own_cell_refs(records, AGGREGATION_NAMESPACE)
            + [ref for child in child_reports for ref in child.get(AGGREGATION_NAMESPACE, ())])),
        'returned_lead_source_refs': [ref for child in child_reports if 'leads' in child
                                      for ref in child['leads']['lead_source_refs']],
        'source_leads': leads,
        'no_applicable_evidence': spans,
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = (screening_answers(summary)
                                    + [{'disposition': 'no_applicable_evidence'} for child in child_reports
                                       if 'screening' in child and child['screening']['commissioned_spans_covered']])
    summary['lead_return'] = lead_return(summary, records)
    summary['screening_return'] = screening_return(spans, summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
