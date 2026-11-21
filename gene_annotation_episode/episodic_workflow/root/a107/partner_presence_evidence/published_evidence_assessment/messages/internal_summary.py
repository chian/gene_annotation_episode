"""Where the episode stands, as a pure function of the view: the assignment, the custody of the sources of this episode, the
Episode's own outcomes, the child reports (credit and controlled sheet features), the features of the partner sheets
its own graders saved (read back from their cell rows through the scoped reader) merged with those its child returned,
the agreement counts over them and the yield forecast of its controller (old ``internal_summary.py``:
``LiteratureSummary`` and ``SourceDecisionSummary``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.partner_presence_evidence.literature_partner_findings import (
    agreement, current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8
OWN_TOOLS = ('state_query', 'source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
             'source_experimental_records', 'image_view', 'source_archive_members', 'source_archive_extract',
             'source_xlsx_sheets', 'source_xlsx_rows', 'source_pdf_info', 'source_pdf_text', 'source_pdf_page',
             'public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
             'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset')
POPULATION_TOOLS = ('literature_partner_populate', 'literature_partner_source_populate')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')
SOURCE_FIELDS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')


def named_references(value):
    """Every record a model-written value names: a value under a key ``ref`` or ``..._ref``, or in a list under
    ``..._refs``."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == 'ref' or key.endswith('_ref')) and isinstance(child, str):
                yield child
            elif key.endswith('_refs') and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            else:
                yield from named_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_references(child)


def consumed_sources(outcomes, source_refs):
    """The assigned sources this episode has consumed, in the order consumed (nano-graphrag ``processed_chunk_ids`` /
    ``processed_row_ids``): a source handed to the strategy child as a prior-search source (an input handed out), and
    a source a partner population operation that was not refused named (an input processed)."""
    consumed = []
    for outcome in outcomes:
        if outcome['kind'] == 'child':
            consumed.extend(outcome['arguments']['selection']['prior_search_refs'])
        elif outcome['tool'] in POPULATION_TOOLS and outcome['outcome'].get('status') != 'invalid':
            consumed.extend(reference for reference in named_references(outcome['arguments']['arguments'])
                            if reference in source_refs)
    return [reference for reference in dict.fromkeys(consumed) if reference in source_refs]


def internal_summary(view):
    parent = view.parent_input
    # The input list (nano-graphrag's input-list paradigm): the assigned sources not yet consumed, in assignment order.
    # It shrinks as a source is handed to the child or populated into a partner sheet; the yield estimator stops the
    # episode when it is empty.
    consumed = consumed_sources(view.outcomes, parent['source_refs'])
    custody = []
    for reference in parent['source_refs']:
        source = view.records.get(reference)
        custody.append({'source_ref': reference, **{key: source.get(key) for key in SOURCE_FIELDS}})
    child_reports = [outcome['report'] for outcome in view.outcomes if outcome['kind'] == 'child']
    returned = [features for report in child_reports for features in report['partner_sheets']]
    sheets = merged_sheet_features(current_sheet_features(view.records, view.outcomes), returned)
    summary = {**parent,
               'held_record_refs': sorted(view.records.refs()),
               'consumed_source_refs': consumed,
               'input_list': [reference for reference in parent['source_refs'] if reference not in consumed],
               'source_custody': custody,
               'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                       tools=(*OWN_TOOLS, *POPULATION_TOOLS),
                                                       tool_of=lambda row: row.get('tool')),
               'literature_history_meaning': HISTORY_MEANING,
               'child_reports': child_reports,
               'partner_sheets': sheets,
               'partner_agreement': agreement(sheets),
               'units_consumed': view.units_consumed}
    if view.controller_state is not None:
        summary['yield_table'] = yield_table(view.controller_state, forecast_unit='finding')
    return summary
