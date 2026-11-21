"""Where the investigation stands, as a pure function of the loop's view: the assignment, custody of the assigned
sources, the first page of the episode's own read and acquisition outcomes, the goal plan, the controlled features of
the current grading and aggregation sheets it saved and its child returned (each sheet its own entry), the returns
of the children commissioned (their credit and the counts of their findings), and what the units answer for the
commissioned task.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``, ``literature_goal_plan``
from ``goal.planning_context``). The old reads of ``runtime_actions`` and ``runtime_report_attempts`` are the unit
outcomes of ``view``: a tool unit's outcome, and a child unit's ``report`` (what ``read_from_child`` made of the
admitted result)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    no_applicable_spans, relevant_lead_sources, screening_covered, spans_cover)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    current_aggregation_features, current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import GOAL as PLANNING_QUESTION

CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_experimental_records',
              'source_pdf_text')
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_sabiork_search', 'public_sabiork_read', 'public_brenda_search', 'public_brenda_read',
                     'public_bioassay_search', 'public_bioassay_read', 'public_chembl_search', 'public_chembl_read',
                     'public_mavedb_search', 'public_mavedb_read', 'public_brenda_graph_search')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')


def named_sources(value):
    """Every ``source_ref`` an executed unit's arguments name (a read, a population operation, a reasoning commit's
    witnesses and the JSON arguments of its gradings)."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'source_ref' and isinstance(item, str):
                found.append(item)
            elif key == 'arguments' and isinstance(item, str):
                found.extend(named_sources(json.loads(item)))
            else:
                found.extend(named_sources(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(named_sources(item))
    return found


def work_sources(literature, task, outcomes, records):
    """The sources this episode works through, in the order they came: the sources the commission gave and the
    sources its task names, then the sources its own acquisitions produced (nano-graphrag ``remaining_chunks``: the
    items of the work before any is consumed)."""
    sources = [*literature['source_refs'], *task.get('source_refs', ())]
    if task.get('answer_kind') == 'measurement':
        sources.append(task['selection']['source_ref'])
    for outcome in outcomes:
        if outcome['kind'] == 'tool':
            sources.extend(ref for ref in outcome['produced'] if records.get(ref)['record_type'] == 'source')
    return list(dict.fromkeys(sources))


def consumed_inputs(task, outcomes, spans, covered):
    """The sources consumed, in the order consumed (nano-graphrag ``processed_chunk_ids`` / ``processed_row_ids``): a
    source handed to the strategy child as a prior-search source, and a source a completed or partial unit WORKED on
    (a population operation, a reasoning commit naming it). Looking at a source is not the work on it: a read or a
    locate (``READ_TOOLS``) consumes nothing, so a source this episode has only read can still be handed to the
    strategy child (the real head run of 2026-11-21 lost the child after one read of its only source). For a screening
    answer a source is consumed only when its commissioned spans are covered (declared to hold no applicable evidence,
    or returned covered by the child), or when it was handed to the child."""
    screening = task.get('answer_kind') == 'screening'
    consumed = []
    for outcome in outcomes:
        if outcome['kind'] == 'child':
            consumed.extend(outcome['arguments']['strategy']['prior_search_refs'])
        elif (not screening and outcome['tool'] not in READ_TOOLS
              and outcome['outcome']['status'] in ('completed', 'partial')):
            consumed.extend(named_sources(outcome['arguments']['arguments']))
    if screening:
        consumed.extend(span['source_ref'] for span in task['examined']
                        if covered or spans_cover({'examined': [span]}, spans))
    return list(dict.fromkeys(consumed))


def internal_summary(view):
    parent = view.parent_input
    literature, task = parent['literature'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    spans = no_applicable_spans(view.outcomes, records)
    covered = screening_covered(task, view.outcomes, spans)
    # The input list (nano-graphrag's input-list paradigm): the sources of the work not yet consumed, in the order they
    # came (for a screening answer, the sources of the commissioned spans). A consumed source is not offered to the
    # child again. The yield estimator passes no item list (``items=None``), so an empty list does not end the episode:
    # a ``verified_source_leads`` task's accumulation controller (``ADAPTIVE_CONTROL``, no cost) stops after 4 flat
    # units in a row (expected next marginal credit's upper bound at or below the adaptive gamma, once W = 8 units
    # are attempted and m = 4 observed).
    consumed = consumed_inputs(task, view.outcomes, spans, covered)
    items = ([span['source_ref'] for span in task['examined']] if task.get('answer_kind') == 'screening'
             else work_sources(literature, task, view.outcomes, records))
    input_list = [ref for ref in dict.fromkeys(items) if ref not in consumed]
    assignment = {**literature, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **parent['requested']}
    return {
        'literature_assignment': assignment, 'literature': literature,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'requested': parent['requested'],
        'literature_source_custody': [{'source_ref': reference, **{key: records.require(reference, {'source'}).get(key) for key in CUSTODY_KEYS}}
                                      for reference in literature['source_refs']],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*ACQUISITION_TOOLS, *READ_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_goal_plan': {'objective': view.goal.as_record()['objective'],
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task,
                                 'progress_definition': credit_binding(parent['task_key'], task),
                                 'planning_question': PLANNING_QUESTION},
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], 'scores': outcome['report']['scores'],
                           'features': outcome['report']['features']}
                          for outcome in children],
        # The strategy child returns the whole subscoring sheet as it stands after it, starting from the states this
        # episode passed to it: the latest return is the current sheet. Before any child returned, the sheet is the one
        # this episode was given (the states its commissioner passed, no scores, no features).
        'sheet_state_refs': children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs'],
        'scores': children[-1]['report']['scores'] if children else [],
        'features': children[-1]['report']['features'] if children else [],
        'assay_sheets': current_sheet_features(records),
        'aggregation_sheets': current_aggregation_features(records),
        'no_applicable_spans': spans,
        'screening_covered': covered,
        'input_list': input_list, 'consumed_inputs': consumed,
        'lead_source_refs': (relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records)
                             if task['kind'] == 'verified_source_leads' else []),
        # The lead sources this episode's own reason units validated (the child's leads are credited through the credit
        # the child returned, which ``credit.py`` adds).
        'own_lead_source_refs': (relevant_lead_sources([outcome for outcome in view.outcomes
                                                        if outcome['kind'] == 'tool'],
                                                       parent['proposed_annotation_ref'], records)
                                 if task['kind'] == 'verified_source_leads' else []),
    }
