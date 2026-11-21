"""Where the literature investigation stands, as a pure function of the loop's view: the assignment, custody of the
sources assigned for reading and of every source held (the old ``literature_source_custody`` for the assigned
``source_refs``), the first page of the episode's own read and acquisition outcomes, the controlled features of the current A106 sheets saved here and below
(``literature_a106_findings``), the reports of the children it commissioned, the latest image the model looked at, the handoffs of its launches,
the intervention analysis rows its result acquisitions returned, and the typed answers the commissioned task asks for
(carried from the old ``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``,
``own_literature_outcomes``, ``literature_history_meaning``, ``received_intervention_analysis_rows``,
``literature_experimental_work``, and from ``decision_context.py`` the ``visual_evidence`` of the latest completed
``image.view``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``, and the old
``completed_action_reports`` are the child reports ``read_from_child`` made).

The old display contexts of the population route (owned population sources, the latest failed population
attempt, ``literature_completed_work``, the per-sheet contexts) are replaced by the controlled features of the G1 and
G2 sheets (``a106_findings``). ``literature_examined_source_inputs`` needs the old library reader over ``runtime_*`` tables
(``own_source_inputs``) and is not carried. The root-only ``reference_evidence_parent`` context is not this
episode's.

``source_custody`` maps each held source to the records a commission of the strategy child must name for it: the
source and the artifacts it holds (the old ``prepare_assignment`` read them in scope; the child now reads only what
is passed)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings, own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_population_route import (
    opened_population)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers
from ..task import ACQUISITION_NAMES

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
EXECUTION_SLOTS = ('launch', 'results')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')
EXPERIMENTAL_WORK = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence',
                     'evidence_axis': 'A106'}

# The literature child, whose finding is the A106 finding (its sheets are listed beside this episode's own).
LITERATURE = ('literature_strategy',)


def held_sources(view):
    """The assigned sources and the sources the episode's own tool units produced, in order."""
    references = list(view.parent_input['literature']['source_refs'])
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            references.extend(outcome['produced'])
    return [reference for reference in dict.fromkeys(references)
            if view.records.get(reference).get('record_type') == 'source']


def consumed_sources(view):
    """The sources already handed to the strategy child as its prior search sources, in the order handed out
    (nano-graphrag ``processed_chunk_ids``: an input handed out is consumed)."""
    return list(dict.fromkeys(reference for outcome in view.outcomes
                              if outcome['kind'] == 'child' and outcome['slot'] in LITERATURE
                              for reference in outcome['arguments']['prior_search_refs']))


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    # The input list (nano-graphrag's input-list paradigm): the held sources (assigned and acquired) no strategy child
    # has been handed. Only these are offered to a commission; the list shrinks as a commission consumes its prior
    # search sources and grows when an acquisition produces a new source. The yield estimator stops the episode when
    # it is empty.
    consumed = consumed_sources(view)
    input_list = [reference for reference in held_sources(view) if reference not in consumed]
    sources = view.records.list('source')
    assigned = [view.records.require(reference, {'source'}) for reference in parent['literature']['source_refs']]
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in outcomes if outcome['tool'] == 'reason']
    last = view.outcomes[-1] if view.outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['kind'] == 'tool'
              and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed' else [])
    # The leads in the order of the units: an own validated lead of a reasoning commit, and each relevant lead source
    # an admitted literature child return names (the old ``lead_dispositions`` merged them by decision order).
    leads, children = [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            leads.extend({'source_ref': ref, 'disposition': 'relevant',
                          'proposed_annotation_ref': parent['proposed_annotation_ref']}
                         for ref in (outcome['report']['lead_source_refs']
                                     if outcome['slot'] in LITERATURE and task['kind'] == 'verified_source_leads'
                                     else ()))
            children.append({'slot': outcome['slot'], 'arguments': outcome['arguments'],
                             'report': outcome['report']})
        elif outcome['tool'] == 'reason' and 'literature_source_lead' in outcome['outcome']:
            leads.append(outcome['outcome']['literature_source_lead'])
    assignment = {**parent['literature'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref']}
    reports = {slot: [outcome['report'] for outcome in view.outcomes
                      if outcome['kind'] == 'child' and outcome['slot'] == slot] for slot in EXECUTION_SLOTS}
    summary = {
        'input_list': input_list, 'consumed_source_refs': consumed,
        'literature_assignment': assignment, 'literature': parent['literature'],
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': source['id'], **{key: source.get(key) for key in CUSTODY_KEYS}}
                                      for source in assigned],
        'source_custody': {source['id']: [source['id'], *[source[key] for key in ARTIFACT_KEYS
                                                          if source.get(key) is not None]]
                           for source in sources},
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*ACQUISITION_NAMES, *READ_TOOLS),
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
        'handoff_refs': list(dict.fromkeys(ref for report in reports['launch'] for ref in report['handoff_refs'])),
        'received_intervention_analysis_rows': [row for report in reports['results']
                                                for row in report['application_rows']],
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': merged_findings(own_findings(view.records, view.outcomes),
                                         [child['report']['finding'] for child in children
                                          if child['slot'] in LITERATURE]),
        'opened_population': opened_population(view.outcomes),
        'source_leads': leads,
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
