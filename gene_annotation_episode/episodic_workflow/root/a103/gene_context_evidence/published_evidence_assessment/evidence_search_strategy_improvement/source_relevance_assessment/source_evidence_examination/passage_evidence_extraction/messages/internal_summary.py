"""Where the extraction stands, as a pure function of the view: the assignment (page and spans), the custody row of
the page's source, the first own read outcomes, the tool catalog (once obtained), the latest controlled report and
the finding code reads from it, the current A103 sheets of the credit view, the controller's yield table and the
meaning of the history.

The A103 sheets (row 9 of ``LOST_CONTENT_a103.md``): the old ``decision_state.py`` of this episode (line 43 at
97308b94c) put ``a103_sheet``, ``target_sheets``, ``tool_attachments`` and ``source_contributions`` of the credit view
in the decision context as ``_completed_work_axis_results`` ("Current gene-context scoring sheet", "Saved
measurement-specific context attribution"): the literature reading decides while seeing them."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)
from .final_to_parent import finding_of

OUTCOME_PAGE_SIZE = 8
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
HISTORY_MEANING = 'Read exact prior outcomes from own_outcomes; source discovery alone is not A103 evidence.'
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
SOURCE_KEYS = ('provider', 'accession', 'uri')
SHEET_KEYS = ('a103_sheet', 'target_sheets', 'tool_attachments', 'source_contributions')


def internal_summary(view):
    parent = view.parent_input
    source = view.records.get(parent['page']['source_ref'])
    custody = [{'source_ref': parent['page']['source_ref'], **{key: source.get(key) for key in CUSTODY_KEYS},
                **{key: source.get(key) for key in SOURCE_KEYS}}]
    catalog, report = None, None
    for outcome in view.outcomes:
        if outcome['kind'] != 'tool':
            continue
        if outcome['tool'] == 'tool_catalog':
            catalog = outcome['outcome']['catalog']
        elif outcome['tool'] == 'report' and outcome['outcome']['status'] == 'reported':
            report = outcome['outcome']['report']
    credit_view = A103ContextCredit()(view.records, parent['scope'], known_record_refs=view.records.refs())
    controller = view.controller_state
    return {'assignment': parent, 'source_custody': custody, 'catalog': catalog, 'report': report,
            'finding': finding_of(report),
            'completed_work_axis_results': {key: credit_view[key] for key in SHEET_KEYS},
            'own_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                         tool_of=lambda row: row.get('tool')),
            'history_meaning': HISTORY_MEANING,
            'controller': None if controller is None else controller.as_record(),
            'units_consumed': view.units_consumed}
