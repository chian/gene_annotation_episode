"""Where the investigation stands, as a pure function of the loop's view: the assignment, custody of the sources
this episode holds (the prior search results and the sources its own acquisitions produced), the first page of
the episode's own acquisition and read outcomes, the reports of the search children it commissioned, the
structure sheets it saved and its children returned (each its own entry), and the typed answers the commissioned task asks for (carried from the old
``internal_summary.py``: ``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; the old reads of ``runtime_actions`` are the unit outcomes of ``view``, the old
reads of ``runtime_report_attempts`` the child reports of ``view``).

Custody: the old code read ``assignment.get('page')`` and then ``assignment.get('source_refs')``; this
assignment's field is ``prior_search_refs``, so the old custody was always empty here. It now lists the prior
search results and the sources the episode's own acquisition tools produced, so that a search child can be
commissioned for any of them (each entry also names the records the child must be passed: the source, its
artifacts and the sources it derives from that this episode holds)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions, screening_answers

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_sabiork_search', 'public_sabiork_read', 'public_brenda_search', 'public_brenda_read',
                     'public_brenda_graph_search', 'public_bioassay_search', 'public_bioassay_read',
                     'public_chembl_search', 'public_chembl_read', 'public_mavedb_search', 'public_mavedb_read')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding.')


def source_custody(records, reference):
    """The old custody entry of one source, and the records a commission of it passes (the source, its
    artifacts and the sources it derives from, transitively, that this episode holds)."""
    source = records.get(reference)
    entry = {'source_ref': reference, **{key: source.get(key) for key in CUSTODY_KEYS}}
    passed, pending = [reference], list(source.get('parent_source_refs', ()))
    passed.extend(entry[key] for key in ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')
                  if entry[key] is not None)
    while pending:
        parent = pending.pop()
        if parent in passed or not records.holds(parent):
            continue
        passed.append(parent)
        pending.extend(records.get(parent).get('parent_source_refs', ()))
    entry['passed_record_refs'] = passed
    return entry


def held_sources(view):
    """The prior search results and the sources the episode's own tool units produced, in order."""
    references = list(view.parent_input['prior_search_refs'])
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            references.extend(outcome['produced'])
    return [reference for reference in dict.fromkeys(references)
            if view.records.get(reference).get('record_type') == 'source']


def consumed_sources(view):
    """The search results a search child was handed, in the order handed (nano-graphrag ``processed_chunk_ids``:
    an input handed out is consumed and no longer offered)."""
    handed = []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            handed.extend(outcome['arguments']['search']['search_result_refs'])
    return list(dict.fromkeys(handed))


def internal_summary(view):
    parent = view.parent_input
    consumed = consumed_sources(view)
    custody = [source_custody(view.records, reference) for reference in held_sources(view)]
    task = parent['task']
    tool_outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    reasons = [outcome['outcome'] for outcome in tool_outcomes if outcome['tool'] == 'reason']
    assignment = {'version': parent['version'], 'question_context_refs': parent['question_context_refs'],
                  'prior_search_refs': parent['prior_search_refs'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref']}
    leads = []
    # Own validated leads and each relevant lead source an admitted child return names, in unit order (the old
    # ``lead_dispositions`` merged them by decision order); a child names lead sources only on a leads commission.
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            leads.extend({'source_ref': reference, 'disposition': 'relevant',
                          'proposed_annotation_ref': parent['proposed_annotation_ref']}
                         for reference in (outcome['report']['lead_source_refs']
                                           if task['kind'] == 'verified_source_leads' else ()))
        elif outcome['tool'] == 'reason' and 'literature_source_lead' in outcome['outcome']:
            leads.append(outcome['outcome']['literature_source_lead'])
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': custody,
        # The input list: the held search results not yet handed to a search child, in custody order. A result
        # handed to a child is consumed and offered no more; the yield estimator stops on an empty list.
        'input_list': [entry for entry in custody if entry['source_ref'] not in consumed],
        'consumed_source_refs': consumed,
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*ACQUISITION_TOOLS, *READ_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'child_reports': [{'slot': outcome['slot'], 'search': outcome['arguments']['search'],
                           'report': outcome['report']} for outcome in view.outcomes if outcome['kind'] == 'child'],
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'structure_sheets': merged_sheet_features(
            current_sheet_features(view.records),
            [features for outcome in view.outcomes if outcome['kind'] == 'child'
             for features in outcome['report']['structure_sheets']]),
        'source_leads': leads,
        'no_applicable_evidence': [span for outcome in reasons if 'evidence_processing' in outcome
                                   for span in outcome['evidence_processing']['examined']],
    }
    summary['source_lead_dispositions'] = (lead_dispositions(summary, view.records)
                                           if task['kind'] == 'verified_source_leads' else [])
    summary['screening_answers'] = screening_answers(summary)
    return summary
