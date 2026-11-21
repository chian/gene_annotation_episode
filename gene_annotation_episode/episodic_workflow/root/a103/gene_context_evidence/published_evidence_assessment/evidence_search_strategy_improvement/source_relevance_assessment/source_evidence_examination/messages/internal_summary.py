"""Where the source examination stands, as a pure function of the loop's view: the assignment, custody of the page's
source, the first page of the episode's own read outcomes, the tool catalog (once obtained), the latest completed
image view, what each child returned and the finding written so far (carried from the old ``internal_summary.py``:
``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; and from the old ``decision_state.py``: the visual evidence rule, the controller
state and the report-lifecycle sentence)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.gene_context_evidence.literature_input_list import (
    input_list_state)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)
from .final_to_parent import finding_of

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
SOURCE_KEYS = ('provider', 'accession', 'uri')
HISTORY_MEANING = 'Read exact prior outcomes from own_literature_outcomes; source discovery alone is not A103 evidence.'
REPORT_LIFECYCLE = 'The report is the last actual reading basis; later tool outcomes are facts, not a new judgment.'
# The A103 sheets of the credit view (row 9 of LOST_CONTENT_a103.md: the old decision_state.py line 43 put them in
# the decision context as _completed_work_axis_results, "Current gene-context scoring sheet").
SHEET_KEYS = ('a103_sheet', 'target_sheets', 'tool_attachments', 'source_contributions')


def representation_artifact(source, representation):
    """The artifact a source holds for one representation (the old ``SourceReferences._artifact``)."""
    if representation == 'original':
        return source['artifact_ref']
    if representation == 'text':
        return source.get('text_ref') or source['artifact_ref']
    return source.get(representation + '_ref')


def visual_evidence(outcomes):
    """The pixels of the most recent unit when it was a completed ``image_view`` (the old rule read the last
    completed action's ``visual_inputs``); nothing otherwise."""
    if not outcomes:
        return []
    last = outcomes[-1]
    if last['kind'] == 'tool' and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed':
        return last['outcome'].get('visual_inputs') or []
    return []


def internal_summary(view):
    parent = view.parent_input
    source = view.records.get(parent['source_ref'])
    catalog, report, child_reports = None, None, []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            child_reports.append({'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                                  'selection': outcome['arguments']['selection'], **outcome['report']})
        elif outcome['tool'] == 'tool_catalog':
            catalog = outcome['outcome']['catalog']
        elif outcome['tool'] == 'report' and outcome['outcome']['status'] == 'reported':
            report = outcome['outcome']['report']
    credit_view = A103ContextCredit()(view.records, parent['scope'], known_record_refs=view.records.refs())
    controller = view.controller_state
    # The page's input list (nano-graphrag's page state, ``literature_input_list``): the candidate input units of the
    # source (table regions and prose chunks, byte intervals of the assigned representation); a candidate handed to a
    # child is consumed and offered no more. The list shrinks as children are commissioned.
    content = view.records.get_artifact(representation_artifact(source, parent['representation']))
    inputs = input_list_state(content, [
        {'slot': outcome['slot'], 'selection': outcome['arguments']['selection'],
         'finding': outcome['report']['finding']} for outcome in view.outcomes if outcome['kind'] == 'child'])
    return {
        'assignment': parent,
        'source_custody': [{'source_ref': parent['source_ref'],
                            'page_artifact_ref': representation_artifact(source, parent['representation']),
                            **{key: source.get(key) for key in CUSTODY_KEYS + SOURCE_KEYS}}],
        'catalog': catalog,
        'own_literature_outcomes': outcome_page(
            [outcome for outcome in view.outcomes if outcome['kind'] == 'tool'], offset=0, limit=OUTCOME_PAGE_SIZE,
            tools=READ_TOOLS, tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'visual_evidence': visual_evidence(view.outcomes),
        'child_reports': child_reports,
        'source_bytes': len(content),
        'content_candidates': inputs['candidates'],
        'consumed_candidate_ids': inputs['consumed'],
        'unconsumed_candidates': inputs['unconsumed'],
        'remaining_windows': inputs['remaining_windows'],
        # The page's input list: the unconsumed candidates in document order. The yield estimator stops the episode
        # when it is empty.
        'input_list': inputs['input_list'],
        'units_consumed': view.units_consumed,
        'action_yields': None if controller is None else yield_table(controller, forecast_unit='credit'),
        'report': report,
        'report_lifecycle': REPORT_LIFECYCLE,
        'finding': finding_of(report),
        'completed_work_axis_results': {key: credit_view[key] for key in SHEET_KEYS},
    }
