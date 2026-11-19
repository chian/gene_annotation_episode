"""Where the examination stands, as a pure function of the view: the assignment, the custody of the page's source, the
Episode's own outcomes, the child reports (credit and controlled sheet features), the features of the partner sheets
its own graders saved (read back from their cell rows through the scoped reader) merged with those its children
returned, the agreement counts over them and the yield forecast of its controller (old ``internal_summary.py``:
``LiteratureSummary`` and ``SourceDecisionSummary``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement, current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8
OWN_TOOLS = ('source_read', 'source_locate', 'literature_partner_populate', 'literature_partner_source_populate')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')
SOURCE_FIELDS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    child_reports = [outcome['report'] for outcome in view.outcomes if outcome['kind'] == 'child']
    returned = [features for report in child_reports for features in report['partner_sheets']]
    sheets = merged_sheet_features(current_sheet_features(view.records, view.outcomes), returned)
    summary = {**parent,
               'held_record_refs': sorted(view.records.refs()),
               # The page's source and the held sources derived from it (a dataset, a supplement, a literal source).
               'source_custody': [{'source_ref': row['id'], 'provider': row['provider'],
                                   **{key: row.get(key) for key in SOURCE_FIELDS}}
                                  for row in [source, *(row for row in view.records.list('source')
                                                        if page['source_ref'] in row.get('parent_source_refs', ()))]],
               'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                       tools=OWN_TOOLS, tool_of=lambda row: row.get('tool')),
               'literature_history_meaning': HISTORY_MEANING,
               'child_reports': child_reports,
               'partner_sheets': sheets,
               'partner_agreement': agreement(sheets),
               'units_consumed': view.units_consumed}
    if view.controller_state is not None:
        summary['yield_table'] = yield_table(view.controller_state, forecast_unit='finding')
    return summary
