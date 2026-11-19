"""Where the ordered reading stands, as a pure function of the loop's view: the assignment, custody of the page's
source, the first page of the episode's own acquisition and read outcomes, the latest completed image view, and the
interpretation written so far (carried from the old ``internal_summary.py``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``; and from the old
``decision_state.py``: the visual evidence rule, the controller state and the report-lifecycle sentence)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8        # the old configuration.outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = 'Read exact prior outcomes through own_literature_outcomes; source discovery alone is not A101 evidence.'
REPORT_LIFECYCLE = 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'


def representation_artifact(source, representation):
    """The artifact a source holds for one representation (the old ``LiteratureReferences._artifact``)."""
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
    page = parent['page']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    written = [outcome['outcome']['report'] for outcome in outcomes if outcome['tool'] == 'report']
    report = written[-1] if written else None
    sources = [] if report is None else sorted({item['source_ref'] for item in report['windows']})
    return {
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page, 'selection': parent['window']},
        'scope': parent['scope'],
        'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       'page_artifact_ref': representation_artifact(source, page['representation']),
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'visual_evidence': visual_evidence(view.outcomes),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'report': report,
        'report_lifecycle': REPORT_LIFECYCLE,
        'report_source_held': {reference: view.records.holds(reference) for reference in sources},
    }
