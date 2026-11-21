"""Where the assessment stands, as a pure function of the loop's view: the search assignment, custody of the sources
it holds, the first page of the episode's own acquisition and read outcomes, the interpretation written so far, what
the child returned, the investigation findings of the assessments committed (own and the child's), the contextual
sheets saved, the latest image the model looked at, and the typed answers the commissioned task asks for.

Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``, ``_owned_population_task_sources``,
``_population_task_context``, ``_received_fact_display_context``), ``decision_inputs.py`` and ``decision_presentation.py``
of ``literature_search``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``, ``literature_experimental_work``, ``literature_received_fact_display``,
``literature_owned_population_sources``, ``literature_selected_population_attempt``, ``literature_goal_plan`` (the old
``planning_context``), ``visual_evidence`` and the yield table. The old reads of ``runtime_actions`` and of the
operations tables are the unit outcomes of ``view``.

Differences from the old context, both needed by the new custody rule: the source custody lists the sources of
``search_result_refs`` (the old listed ``assignment['source_refs']``, which a search assignment does not have, so it was
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
episode's code, never its model: the received-fact display leaves them out.

The search step's Jev measurement (nano-graphrag ``web_search_binding``: ``assess_page_candidate`` and
``SearchPageProposer``): every search result of the assignment is a possible source examination child with its provider
rank (its position in ``search_result_refs``, the order the search returned it), a title and a description read from its
source record. ``jev_search_goal`` is the immutable Search Goal Jev measures them against (the runner's goal record of
this episode, as nano-graphrag's ``goal.as_record()``, with this episode's grain, what the commission requests and the
subject of the proposed annotation); ``search_assessment_ref`` is the assessment the code-decided
``assess_search_results`` unit holds, and ``search_planner_context`` is that assessment over the unconsumed search
results only with the measured outcomes of the prior source examination children (``prior_page_outcomes``)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    search_planner_context)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    merged_findings, own_cell_refs, own_findings, screening_return)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError)

from ..credit import credit_binding, lead_dispositions, lead_return, screening_answers
from ..goal import BINDING_PATH, GOAL, RESULT, UNIT
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_taxonomy', 'public_ncbi_sequence')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_xlsx_rows', 'source_pdf_text',
              'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
SEARCH_ASSIGNMENT = 'search_assignment_v1'
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


def source_inputs(parent, custody, children):
    """The input list (nano-graphrag ``PageRunState.processed_chunk_ids`` / ``remaining_chunks`` over this episode's
    sources): the sources this episode works through, in the order they were handed to it (the search results, the
    task's sources and screening spans, then any other source it holds), less the sources a source examination child
    was commissioned on. A source handed to a child is consumed and is never offered again.
    Returns ``(consumed_source_refs, input_list)``."""
    task = parent['task']
    listed = list(dict.fromkeys([*parent['search_result_refs'], *task.get('source_refs', ()),
                                 *(span['source_ref'] for span in task.get('examined', ())), *custody]))
    consumed = list(dict.fromkeys(outcome['arguments']['page']['source_ref'] for outcome in children))
    return consumed, [ref for ref in listed if ref not in consumed]


ASSESS = 'assess_search_results'
DESCRIPTION_KEYS = ('provider', 'accession', 'uri', 'version', 'retrieved_at')


def search_result_candidates(search_result_refs, records):
    """Each search result as a possible source examination child (nano-graphrag's provider result): its id (the source
    ref the planner selects), its provider rank (1-based position in the order the search returned it), a title (the
    source's accession, else its uri, else its provider) and a description (the source record's provider metadata, as
    ``key=value``)."""
    candidates = []
    for rank, ref in enumerate(search_result_refs, start=1):
        source = records.get(ref)
        title = source.get('accession') or source.get('uri') or source.get('provider') or ''
        description = '; '.join(f'{key}={source[key]}' for key in DESCRIPTION_KEYS if source.get(key))
        candidates.append({'result_id': ref, 'provider_rank': rank, 'title': str(title), 'description': description})
    return candidates


def label_of(records, ref):
    record = records.get(ref)
    return record.get('label') or record.get('name') or ref


def question_context(records, ref):
    """One record giving the assigned question its context, as the Search Goal names it: its record type, its context
    type and its name or label, where it has them."""
    record = records.get(ref)
    entry = {'record_type': record.get('record_type'), 'context_type': record.get('context_type'),
             'name': record.get('name') or record.get('label')}
    return {key: value for key, value in entry.items() if value is not None}


def search_goal(view, parent, records):
    """The immutable Search Goal Jev measures every result against (nano-graphrag: ``EpisodeGoal.for_grain(search_grain,
    parent=strategy goal, objective=...)`` and ``goal.as_record()``), derived from the commission. The runner already
    built this episode's goal as the child of its commissioner's goal with the commission's objective (``view.goal``);
    its record is carried as it is, with this episode's grain (binding path, unit, result) and what the commission
    requests: the commissioned A108 task (its key, kind and answer kind), the A108 grading and aggregation components the
    parent wants returned, the records giving the question its context, and the subject of the proposed annotation (its
    predicate, the labels of its subjects and its value)."""
    task = parent['task']
    hypothesis = records.get(parent['proposed_annotation_ref'])
    value = hypothesis['value']
    requested = {'task_key': parent['task_key'], 'task_kind': task['kind'], 'answer_kind': task.get('answer_kind'),
                 REQUESTED_GRADING: parent[REQUESTED_GRADING], REQUESTED_AGGREGATION: parent[REQUESTED_AGGREGATION],
                 'question_context': [question_context(records, ref) for ref in parent['question_context_refs']]}
    return {**view.goal.as_record(), 'grain': {'binding_path': BINDING_PATH, 'unit': UNIT, 'result': RESULT},
            'requested_results': {key: item for key, item in requested.items() if item not in (None, [])},
            'subject': {'predicate': hypothesis['predicate'],
                        'subjects': [label_of(records, ref) for ref in hypothesis['subject_refs']],
                        'partner': (label_of(records, value['ref']) if value.get('type') in ('term_ref', 'reference')
                                    else value)}}


def prior_page_outcomes(children, ranks):
    """The compact measured outcome of each source examination child, in the order commissioned (nano-graphrag
    ``record_page_outcome``): the source it was handed and its provider rank (null for a source that is not a search
    result), how it ended, its units, its credit and the counts of its finding."""
    return [{'result_id': outcome['arguments']['page']['source_ref'],
             'provider_rank': ranks.get(outcome['arguments']['page']['source_ref']),
             'ended_by': outcome['completion']['ended_by'],
             'units_consumed': outcome['completion']['units_consumed'], 'credit': outcome['report']['credit'],
             'grading_sheets': len(outcome['report']['finding']['grading_sheets']),
             'aggregation_cells': len(outcome['report']['finding']['aggregation_cells']),
             'assessments': len(outcome['report']['finding']['assessment_refs']),
             'lead_sources': (len(outcome['report']['leads']['lead_source_refs']) if 'leads' in outcome['report']
                              else 0)}
            for outcome in children]


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    records = view.records
    held = sorted(records.refs())
    custody = source_custody(records, held)
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    consumed_sources, input_list = source_inputs(parent, custody, children)
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    # Jev's measurement of the search results (nano-graphrag ``SearchPageProposer``): held once by the code-decided
    # ``assess_search_results`` unit; the planner sees it for the unconsumed search results only.
    candidates = search_result_candidates(parent['search_result_refs'], records)
    assessed = [outcome for outcome in outcomes if outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    page_outcomes = prior_page_outcomes(children, {item['result_id']: item['provider_rank'] for item in candidates})
    unconsumed_results = [ref for ref in input_list if ref in parent['search_result_refs']]
    child_reports = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                      'page': outcome['arguments']['page'], **outcome['report']}
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
    assignment = {'version': SEARCH_ASSIGNMENT, 'question_context_refs': parent['question_context_refs'],
                  'search_result_refs': parent['search_result_refs'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': reference, **custody[reference]} for reference in
                                      dict.fromkeys([*parent['search_result_refs'], *task.get('source_refs', [])])],
        'held_source_custody': custody,
        'input_list': input_list, 'consumed_source_refs': consumed_sources,
        'search_result_candidates': candidates,
        'jev_search_goal': search_goal(view, parent, records),
        'search_assessment_ref': assessment_ref,
        'prior_page_outcomes': page_outcomes,
        'search_planner_context': (None if assessment is None
                                   else search_planner_context(assessment, unconsumed_results, page_outcomes)),
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
    summary['screening_answers'] = screening_answers(summary)
    summary['lead_return'] = lead_return(summary, records)
    summary['screening_return'] = screening_return(spans, summary['screening_answers'])
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
