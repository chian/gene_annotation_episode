"""Where the extraction stands, as a pure function of the view: the assignment (page and spans), the custody row of
the page's source, the first own read outcomes, the tool catalog (once obtained), the latest reported finding, the
controller's yield table and the meaning of the history."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page

OUTCOME_PAGE_SIZE = 8
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
HISTORY_MEANING = 'Read exact prior outcomes from own_outcomes; source discovery alone is not A103 evidence.'
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
SOURCE_KEYS = ('provider', 'accession', 'uri')


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
            report = outcome['outcome']['finding']
    cited = [] if report is None else [passage['source_ref'] for passage in report['passages']]
    controller = view.controller_state
    return {'assignment': parent, 'source_custody': custody, 'catalog': catalog, 'report': report,
            'report_sources_held': {ref: bool(view.records.holds(ref)) for ref in cited},
            'own_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                         tool_of=lambda row: row.get('tool')),
            'history_meaning': HISTORY_MEANING,
            'controller': None if controller is None else controller.as_record(),
            'units_consumed': view.units_consumed}
