"""Where the page stands, as a pure function of the loop's view (nano-graphrag's ``PageRunState``): the paper it was
handed (read through custody), its candidate input units (table regions and prose chunks, UTF-8 byte offsets of the
commissioned representation), the information needs of the claim, Jev's held assessment of the candidates (the outcome of
the page's ``assess_content`` unit), which candidates the leaf children consumed, what each leaf returned (its credit and
the controlled features of the sheets it saved) and the answers the commissioned task asks for.

Consumption (nano-graphrag ``selected_source_table_ids`` and ``processed_chunk_ids``): the candidate a table or passage
leaf was commissioned with, and, for the ordered reading, every prose chunk not yet consumed when it was commissioned.

A leaf's return is controlled data only: its credit, the features of its sheets with their references, its relevant lead
count and lead sources and the cell rows asked for. The records a leaf returned (its assessments, sheets, cell rows) are
held but never shown to this episode's model."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    CHUNK_SIZE, PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, page_candidates, planner_context,
    report_windows)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis, merged_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_page_content import (
    claim_of, information_needs, record_name)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_return
from ..goal import PLANNING_QUESTION
from .msg_to_child import AGGREGATION_CELLS, GRADING_CELLS
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

ASSESS = 'assess_content'
VALUE_TYPES_WITH_NAME = ('term_ref', 'reference')


def consumed_candidates(children, candidates):
    """The candidate ids the commissioned leaves were handed, in the order handed."""
    consumed = []
    for outcome in children:
        if outcome['slot'] == 'source_coverage_improvement':
            consumed.extend(candidate['candidate_id'] for candidate in candidates
                            if candidate['candidate_type'] == PROSE_CHUNK and candidate['candidate_id'] not in consumed)
        else:
            consumed.append(outcome['arguments']['candidate_id'])
    return list(dict.fromkeys(consumed))


def claim_of_commission(records, proposed_ref, question_context_refs):
    """The claim the Jev measurement serves: the proposed annotation's predicate and what its value names, with the names
    of the organism contexts the caller supplied (read through custody)."""
    hypothesis = records.get(proposed_ref)
    value = hypothesis['value']
    value_name = record_name(records.get(value['ref'])) if value['type'] in VALUE_TYPES_WITH_NAME else None
    return claim_of(hypothesis, value_name, [record_name(records.get(ref)) for ref in question_context_refs])


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    content = representation_content(records, page['source_ref'], page['representation'])
    candidates = page_candidates(content)
    consumed = consumed_candidates(children, candidates)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    claim = claim_of_commission(records, parent['proposed_annotation_ref'], page['question_context_refs'])
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    text = content.decode('utf-8')
    last = view.outcomes[-1] if view.outcomes else None
    child_reports = [{**outcome['report'], 'candidate_id': outcome['arguments'].get('candidate_id')}
                     for outcome in children]
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    finding = {**merged_findings({'grading_sheets': [], 'aggregation_cells': []},
                                 [child['finding'] for child in child_reports]),
               'assessment_refs': list(dict.fromkeys(ref for child in child_reports
                                                     for ref in child['finding']['assessment_refs']))}
    finding['observation_refs'] = assessment_basis(records, finding['assessment_refs'])
    summary = {
        'commission': {'task': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                       'claim': claim},
        'literature_assignment': assignment, 'page': page,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'credit_binding': binding,
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'planning_question': PLANNING_QUESTION,
        'content_candidates': candidates,
        'consumed_candidate_ids': consumed,
        'unconsumed_chunk_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == PROSE_CHUNK],
        'unconsumed_table_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == SOURCE_TABLE],
        'report_windows': report_windows(candidates, {item['candidate_id'] for item in unconsumed}),
        'table_previews': {item['candidate_id']: candidate_text(content, item)[:TABLE_PREVIEW_CHARS]
                           for item in unconsumed if item['candidate_type'] == SOURCE_TABLE},
        # What the ``assess_content`` unit sends Jev with the needs, and Jev's held assessment over the unconsumed
        # candidates only.
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
        'child_reports': child_reports,
        'finding': finding,
        'grading_cell_refs': list(dict.fromkeys(ref for child in child_reports
                                                for ref in child.get(GRADING_CELLS, ()))),
        'aggregation_cell_refs': list(dict.fromkeys(ref for child in child_reports
                                                    for ref in child.get(AGGREGATION_CELLS, ()))),
        'returned_lead_source_refs': [ref for child in child_reports if 'leads' in child
                                      for ref in child['leads']['lead_source_refs']],
    }
    summary['lead_return'] = lead_return(summary, records)
    return summary
