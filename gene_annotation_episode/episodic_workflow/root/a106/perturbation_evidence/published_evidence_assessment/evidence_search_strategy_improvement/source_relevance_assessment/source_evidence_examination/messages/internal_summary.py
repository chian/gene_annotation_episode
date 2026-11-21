"""Where the examination stands, as a pure function of the loop's view (nano-graphrag's page state): the commission, the
page's input list (``literature_page_content``): the candidate input units of the paper (table regions and prose chunks,
UTF-8 byte offsets of the representation the page was assigned), the information needs of the claim, Jev's held
assessment, which candidates the leaves consumed, and the planner context over the unconsumed candidates only; the
returns of the leaves commissioned (their credit, their findings, their windows) and the relevant source leads they
returned. The page reads no text and holds no reasoning record."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_page_content import (
    CHUNK_SIZE, PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, claim_of_hypothesis,
    information_needs, page_candidates, planner_context, report_windows, representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions
from ..goal import PLANNING_QUESTION

NO_FINDING = {'intervention_assessments': [], 'a106_subscores': []}


def handed_windows(children):
    """The byte windows the leaves commissioned so far were handed (the child's assignment selection, which
    ``msg_to_child`` built from the candidate the model named): one window, or the one span of a chunk commission."""
    windows = []
    for outcome in children:
        selection = outcome['message']['assignment']['selection']
        windows.extend(selection['spans'] if 'spans' in selection else [selection])
    return windows


def consumed_candidates(children, candidates):
    """The candidate ids handed out, in document order (nano-graphrag ``selected_source_table_ids`` and
    ``processed_chunk_ids``): a candidate lying inside a window a commissioned leaf was handed is consumed and never
    offered again."""
    windows = handed_windows(children)
    return [candidate['candidate_id'] for candidate in candidates
            if any(window['offset'] <= candidate['start'] and candidate['end'] <= window['offset'] + window['limit']
                   for window in windows)]


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    content = representation_content(records, page['source_ref'], page['representation'])
    candidates = page_candidates(content)
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    consumed = consumed_candidates(children, candidates)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    claim = claim_of_hypothesis(records, parent['proposed_annotation_ref'])
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == 'assess_content']
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    text = content.decode('utf-8')
    last = view.outcomes[-1] if view.outcomes else None
    leads = [{'source_ref': ref, 'disposition': 'relevant', 'proposed_annotation_ref': parent['proposed_annotation_ref']}
             for outcome in children for ref in outcome['report']['lead_source_refs']]
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'commission': {'task': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                       'claim': claim},
        'literature_assignment': assignment, 'page': page,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'child_returns': [{'slot': outcome['slot'], 'credit': outcome['report']['credit'],
                           'candidate_or_windows': outcome['message']['assignment']['selection'],
                           'lead_source_refs': outcome['report']['lead_source_refs']} for outcome in children],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'planning_question': PLANNING_QUESTION,
        'a106_findings': merged_findings(NO_FINDING, [outcome['report']['finding'] for outcome in children]),
        'source_leads': leads,
        'source_bytes': len(content),
        # The candidates, the needs and Jev's assessment (nano-graphrag ``PageChildProposer``): ``jev_goal`` and
        # ``jev_page_context`` are what the ``assess_content`` unit sends Jev with the needs; ``planner_context`` is the
        # assessment over the unconsumed candidates only.
        'content_candidates': candidates,
        'consumed_candidate_ids': consumed,
        'unconsumed_chunk_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == PROSE_CHUNK],
        'unconsumed_table_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == SOURCE_TABLE],
        'report_windows': report_windows(candidates, {item['candidate_id'] for item in unconsumed}),
        'table_previews': {item['candidate_id']: candidate_text(content, item)[:TABLE_PREVIEW_CHARS]
                           for item in unconsumed if item['candidate_type'] == SOURCE_TABLE},
        'information_needs': information_needs(claim),
        'jev_goal': {'task_kind': task['kind'], 'claim': claim},
        'jev_page_context': {'source_ref': page['source_ref'], 'representation': page['representation'],
                             'source_bytes': len(content),
                             'prose_chunk_count': sum(item['candidate_type'] == PROSE_CHUNK for item in candidates),
                             'source_table_count': sum(item['candidate_type'] == SOURCE_TABLE for item in candidates),
                             'exact_beginning': text[:CHUNK_SIZE]},
        'content_assessment_ref': assessment_ref,
        'planner_context': (None if assessment is None
                            else planner_context(assessment, [item['candidate_id'] for item in unconsumed])),
        'input_list': [item['candidate_id'] for item in unconsumed],
    }
    summary['source_lead_dispositions'] = lead_dispositions(summary, records)
    return summary
