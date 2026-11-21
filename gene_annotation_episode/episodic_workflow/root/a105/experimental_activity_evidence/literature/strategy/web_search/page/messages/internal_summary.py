"""Where the examination stands, as a pure function of the loop's view: the commission (the commissioner's objective, a
value of this episode's fixed vocabulary, with this episode's meaning of it), the claim's sheet class, the page's input
list (nano-graphrag's page, ``literature_page_content``): the candidate input units of the paper (table regions and
prose chunks, byte offsets), the information needs of the claim, Jev's held assessment, which candidates the leaf
children consumed, and the planner context over the unconsumed candidates only; the returns of the leaf children
commissioned (their credit, the counts of their findings, their candidate or windows and the method each leaf record
names), the byte length of the paper and the windows the returned leaf records cover, the leaf records they returned and
the latest update of the subscoring sheet. The page reads no text and holds no reasoning record: the old reads of
tools, the screening, assessment, measurement and assembly tasks are not carried."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_identity_extraction import (
    one_record_per_experiment)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    representation_content)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_claim import (
    PARTNER_VALUE_TYPES, claim_of_hypothesis, record_name)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    class_of_predicate)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    CHUNK_SIZE, PROSE_CHUNK, SOURCE_TABLE, TABLE_PREVIEW_CHARS, candidate_text, information_needs, page_candidates,
    planner_context, report_windows)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    classified_credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import PLANNING_QUESTION
from .read_from_child import LEAF_SLOTS


def text_preview(content, candidate):
    """The exact beginning of a table candidate (nano-graphrag ``exact_table_beginning``)."""
    return candidate_text(content, candidate)[:TABLE_PREVIEW_CHARS]


def commission_claim(records, proposed):
    """The claim (predicate, subject, partner) of the commissioned hypothesis, with the names read from the records it
    points at (``literature_claim.claim_of_hypothesis``; a hypothesis that is no claim raises: the commission is wrong)."""
    hypothesis = records.get(proposed)
    refs = list(hypothesis['subject_refs'])
    if hypothesis['value']['type'] in PARTNER_VALUE_TYPES:
        refs.append(hypothesis['value']['ref'])
    return claim_of_hypothesis(hypothesis, {ref: record_name(records.get(ref)) for ref in refs})


def credit_binding(task_key, task):
    """The credit definition the model is shown: the page's credit is the sheet's (``credit.py``): the resolution its sheet
    update gains for the proposed annotation, and a paper whose sheet row bears on the claim is the lead."""
    binding = classified_credit_binding(task_key, task)
    return {**binding, 'unit': 'sheet_resolution_gain_of_the_proposed_annotation_per_source'}


def bearing_lead_sources(records, source_ref, proposed, base_state_refs, sheet_update):
    """The verified source lead of a page: the page's source when its latest sheet update holds a row of the proposed
    annotation that is measured (``status`` not ``unknown``) and that the page itself wrote or changed (its ``sheet_ref``,
    the content-addressed row reference, is not one of the rows of the states the page was given). No sheet update, or
    only unknown or given rows: no lead."""
    if sheet_update is None:
        return []
    given = {json.loads(records.get_artifact(ref))['row']['row_ref'] for ref in base_state_refs}
    bears = any(features['assertion_ref'] == proposed and features['status'] != 'unknown'
                and features['sheet_ref'] not in given for features in sheet_update['features'])
    return [source_ref] if bears else []


def consumed_candidates(children, candidates, records):
    """The candidate ids a leaf child consumed, in the order consumed (nano-graphrag ``selected_source_table_ids`` and
    ``processed_chunk_ids``): the candidate a ``chunk`` or ``table`` child was handed, when it was commissioned; and every
    prose chunk lying inside a window a ``report`` child returned a leaf record of (the windows it actually read)."""
    consumed = []
    for outcome in children:
        if outcome['slot'] in ('chunk', 'table'):
            consumed.append(outcome['arguments']['candidate_id'])
            continue
        for ref in outcome['report']['record_refs']:
            record = json.loads(records.get_artifact(ref))
            consumed.extend(candidate['candidate_id'] for candidate in candidates
                            if candidate['candidate_type'] == PROSE_CHUNK
                            and record['span_start'] <= candidate['start'] and candidate['end'] <= record['span_end'])
    return list(dict.fromkeys(consumed))


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The page's input list (nano-graphrag's page state): the candidate input units of its paper (table regions and prose
    # chunks), the information needs of the claim, Jev's held assessment of them (the outcome of the page's
    # ``assess_content`` unit) and which candidates the leaf children consumed. Only unconsumed candidates are offered
    # and shown with their probabilities; the list shrinks as each child consumes its candidate.
    content = representation_content(records, page['source_ref'], page['representation'])
    candidates = page_candidates(content)
    consumed = consumed_candidates(children, candidates, records)
    unconsumed = [candidate for candidate in candidates if candidate['candidate_id'] not in consumed]
    claim = commission_claim(records, parent['proposed_annotation_ref'])
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == 'assess_content']
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    text = content.decode('utf-8')
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    # The sheet: the leaf records the leaf children returned (in arrival order, one per experiment ref: two children that
    # extracted the same window of the same kind return the same experiment ref, and the record stating the most fields
    # stands, ties broken by the latest; a re-extraction supersedes, it is not merged), the states the commissioner passed
    # in, and the latest sheet update (each update regroups all the leaf records from those states, so the latest one is the
    # page's whole result).
    leaf_record_refs = one_record_per_experiment([(ref, json.loads(records.get_artifact(ref)))
                                                  for outcome in children if outcome['slot'] in LEAF_SLOTS
                                                  for ref in outcome['report']['record_refs']])
    updates = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == 'update_sheet']
    sheet_update = updates[-1]['outcome']['sheet_update'] if updates else None
    # The leaf records the latest update did not group (all of them before any update): the update runs, automatically,
    # while there is one; an update without one regroups the same records and changes nothing.
    grouped = set(updates[-1]['arguments']['leaf_record_refs']) if updates else set()
    unused_leaf_record_refs = [ref for ref in leaf_record_refs if ref not in grouped]
    # How long the paper is (the bytes of the commissioned representation, read through custody) and which byte ranges the
    # leaf children already read: each returned leaf record's own span with its experiment type and the child's slot.
    source_bytes = len(content)
    covered_windows = []
    for outcome in children:
        for ref in outcome['report']['record_refs']:
            record = json.loads(records.get_artifact(ref))
            covered_windows.append({'offset': record['span_start'], 'end': record['span_end'],
                                    'experiment_type': record['experiment_type'], 'slot': outcome['slot']})
    return {
        'commission': {'objective': parent['objective']['value'], 'objective_meaning': parent['objective']['meaning'],
                       'task': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref']},
        'literature_assignment': assignment, 'page': page,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'],
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'planning_question': PLANNING_QUESTION,
        # A leaf's return also says which candidate (chunk, table) or which windows (report) it was handed and which
        # method it named (the experiment type of each leaf record it returned), so the model sees what each child consumed.
        'child_returns': [{'slot': outcome['slot'], 'credit': outcome['report']['credit'],
                           **outcome['report']['counts'],
                           **({'windows': outcome['message']['assignment']['windows']} if outcome['slot'] == 'report'
                              else {'candidate_id': outcome['arguments']['candidate_id']}),
                           'experiment_types': [json.loads(records.get_artifact(ref))['experiment_type']
                                                for ref in outcome['report']['record_refs']]}
                          for outcome in children],
        # The sheet class of the claim (a fixed vocabulary value): what the page hands each leaf in place of an experiment
        # type; the leaf names the method its passage reports.
        'sheet_class': class_of_predicate(claim['predicate']),
        'source_bytes': source_bytes, 'covered_windows': covered_windows,
        # The candidates, the needs and Jev's assessment (nano-graphrag ``PageChildProposer``): ``jev_goal`` and
        # ``jev_page_context`` are what the ``assess_content`` unit sends Jev with the needs; ``planner_context`` is the
        # assessment over the unconsumed candidates only.
        'content_candidates': candidates,
        'consumed_candidate_ids': consumed,
        'unconsumed_chunk_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == PROSE_CHUNK],
        'unconsumed_table_ids': [item['candidate_id'] for item in unconsumed if item['candidate_type'] == SOURCE_TABLE],
        'report_windows': report_windows(candidates, {item['candidate_id'] for item in unconsumed}),
        'table_previews': {item['candidate_id']: text_preview(content, item) for item in unconsumed
                           if item['candidate_type'] == SOURCE_TABLE},
        'information_needs': information_needs([], claim),
        'jev_goal': {'objective': parent['objective']['value'], 'objective_meaning': parent['objective']['meaning'],
                     'task_kind': task['kind'], 'claim': claim, 'commissioned_experiments': []},
        'jev_page_context': {'source_ref': page['source_ref'], 'representation': page['representation'],
                             'source_bytes': source_bytes,
                             'prose_chunk_count': sum(item['candidate_type'] == PROSE_CHUNK for item in candidates),
                             'source_table_count': sum(item['candidate_type'] == SOURCE_TABLE for item in candidates),
                             'exact_beginning': text[:CHUNK_SIZE]},
        'content_assessment_ref': assessment_ref,
        'planner_context': (None if assessment is None
                            else planner_context(assessment, [item['candidate_id'] for item in unconsumed])),
        # The page's input list: what is still to be consumed, the unconsumed candidates in document order and the leaf
        # records the latest update_sheet did not group.
        'input_list': [item['candidate_id'] for item in unconsumed] + unused_leaf_record_refs,
        'leaf_record_refs': leaf_record_refs, 'unused_leaf_record_refs': unused_leaf_record_refs,
        'base_state_refs': parent['sheet_state_refs'],
        'sheet_update': sheet_update,
        'sheet_state_refs': sheet_update['sheet_state_refs'] if sheet_update is not None else parent['sheet_state_refs'],
        'lead_source_refs': bearing_lead_sources(records, page['source_ref'], parent['proposed_annotation_ref'],
                                                 parent['sheet_state_refs'], sheet_update),
    }
