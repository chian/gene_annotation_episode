"""Where the reading stands, as a pure function of the loop's view: the assignment and the reaction lead it selects,
custody of the page's source, the first page of the episode's own read outcomes, the controlled features of the
reaction sheets it saved and of the assessments it committed, the latest image the model looked at and what the
yield controller forecasts. Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``:
``literature_assignment``, ``literature_source_custody``, ``own_literature_outcomes``,
``literature_history_meaning``; the population contexts ``literature_experimental_work`` and
``literature_owned_population_sources`` are the saved reaction sheets of the work table) and from the generic
snapshot (``visual_evidence`` of the latest completed ``image.view``, the yield table). The old reads of
``runtime_actions`` and ``runtime_model_calls`` are the unit outcomes of ``view``. ``component_axis_source_origin``
and ``component_axis_source_access`` (they read the old workflow's journal and the parent's request) are not
carried.

The input list (nano-graphrag's processed chunk ids / remaining chunks): ``input_list`` holds the assigned windows
``[offset, end]`` not yet processed, in assignment order. A window is processed when its bytes were all read through a
completed ``source_read`` of the page's source and the episode has since committed (a ``reason`` that recorded records or
a completed reaction population); a processed window leaves the list and the offered ``literature_assignment`` selection.
The episode's yield estimator ends it when the list is empty."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    investigation_finding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reaction_cells import (
    current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_span_input_list import (
    input_list)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    selected_family)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size default
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')


def known_assessments(view, outcomes):
    """The assessments this episode committed: the held records named by its reasoning units' outcomes."""
    refs = []
    for outcome in outcomes:
        if outcome['tool'] == 'reason':
            for ref in (*outcome['outcome'].get('record_refs', ()), *outcome['outcome'].get('changed_record_refs', ())):
                if ref not in refs and view.records.get(ref).get('record_type') == 'assessment':
                    refs.append(ref)
    return refs


def internal_summary(view):
    parent = view.parent_input
    page = parent['page']
    source = view.records.get(page['source_ref'])
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    last = outcomes[-1] if outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['tool'] == 'image_view'
              and last['outcome'].get('status') == 'completed' else [])
    known = known_assessments(view, outcomes)
    requested = {'requested_reaction_components'} if parent['requested_reaction_components'] else set()
    windows = [[span['offset'], span['offset'] + span['limit']] for span in parent['spans']]
    remaining = input_list(windows, page['source_ref'], page['representation'], outcomes)
    spans = [span for span, window in zip(parent['spans'], windows) if window in remaining]
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': spans}}
    if requested:
        assignment['requested_reaction_components'] = parent['requested_reaction_components']
    return {
        'literature_assignment': assignment,
        'input_list': remaining, 'windows_total': len(windows),
        'family': selected_family(requested, set()),
        'scope': parent['scope'], 'finding_unit': parent['finding_unit'],
        'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'reasoning_schema': view.records.reasoning_schema(),
        'held_record_refs': sorted(view.records.refs()),
        'known_assessment_refs': known,
        'reaction_sheets': current_sheet_features(view.records),
        'investigation_finding': investigation_finding(view.records, parent['scope'], parent['finding_unit'], known),
        'last_local_outcome': None if last is None else {'tool': last['tool'], 'outcome': last['outcome']},
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
