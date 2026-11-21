"""Where the assessment stands, as a pure function of the loop's view: the search assignment, custody of the
sources it hands over, the first page of the episode's own acquisition and read outcomes, what each commissioned
examination returned (its credit and controlled finding), the controlled features of the reaction sheets
saved and of the held assessments, the latest image the model looked at, the assessments the
episode holds and what the yield controller forecasts. Carried from the old ``internal_summary.py``
(``LiteratureSummary.decision_context``: ``literature_assignment``, ``literature_source_custody``,
``own_literature_outcomes``, ``literature_history_meaning``, ``literature_experimental_work``) and from the generic
snapshot (``visual_evidence`` of the latest completed ``image.view``, the yield table, the child reports). The old
reads of ``runtime_actions`` and ``runtime_model_calls`` are the unit outcomes of ``view``.

The old ``literature_source_custody`` listed the sources of ``assignment['source_refs']`` (``[page.source_ref]``
for a page), which this assignment does not carry, so it was empty; it lists the sources the assignment hands over
(``search_result_refs``) here. ``held_sources`` (every source the episode holds, with its artifacts and the sources
it derives from) is not shown to the model: ``msg_to_child`` names the records a commission passes from it.

Not carried here: the reaction population contexts of the old file (``literature_owned_population_sources`` and
``literature_selected_population_attempt``, which classified population sheets of the old ``literature_*`` tables
through ``store.db`` and ``runtime_actions``), ``component_axis_source_origin`` and
``component_axis_source_access`` (they read the old workflow's journal and the parent's request), and the
root-only ``reference_evidence_parent`` context. The saved reaction sheets are
the work table of the reaction repository and the sheet features the children return."""
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.investigation_finding_features import (
    investigation_finding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_reaction_cells import (
    current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_reaction_instructions import (
    selected_family)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from .msg_to_child import source_closure

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size default
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_sabiork_search', 'public_sabiork_read', 'public_brenda_search', 'public_brenda_read',
                     'public_bioassay_search', 'public_bioassay_read', 'public_chembl_search',
                     'public_chembl_read', 'public_mavedb_search', 'public_mavedb_read',
                     'public_brenda_graph_search')
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_scan', 'source_sequence_references',
              'source_experimental_records', 'source_xlsx_rows', 'source_pdf_text', 'image_view')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Inspect original source records and exact prior operations before '
                   'interpreting them.')
EXPERIMENTAL_WORK = {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}


def consumed_search_results(children, held_sources, search_result_refs):
    """The handed-over search results the examinations consumed, in the order consumed (nano-graphrag
    ``processed_row_ids`` / ``processed_chunk_ids``): a source handed to an examination child consumes itself and every
    search result it derives from (``parent_source_refs``). A source commissioned is consumed when it is commissioned."""
    consumed = []
    for outcome in children:
        consumed.extend(ref for ref in source_closure(held_sources, outcome['arguments']['source_ref'])
                        if ref in search_result_refs)
    return list(dict.fromkeys(consumed))


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    held_sources = {row['id']: {key: row.get(key) for key in CUSTODY_KEYS} for row in view.records.list('source')}
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The input list (nano-graphrag's input list paradigm): the search results the parent handed over that no
    # examination has consumed yet, in the order handed over. An item handed to an examination is consumed and is no
    # longer offered; the yield estimator (another owner's) stops the episode when the list is empty.
    consumed = consumed_search_results(children, held_sources, set(assignment['search_result_refs']))
    input_list = [ref for ref in assignment['search_result_refs'] if ref not in consumed]
    known = [row['id'] for row in view.records.list('assessment')]
    requested = {'requested_reaction_components'} if parent['requested_reaction_components'] else set()
    last = view.outcomes[-1] if view.outcomes else None
    visual = (last['outcome'].get('visual_inputs', []) if last is not None and last['kind'] == 'tool'
              and last['tool'] == 'image_view' and last['outcome'].get('status') == 'completed' else [])
    if last is None:
        last_local = None
    elif last['kind'] == 'tool':
        last_local = {'tool': last['tool'], 'outcome': last['outcome']}
    else:
        last_local = {'slot': last['slot'], 'report': last['report']}
    return {
        'literature_assignment': assignment, 'assignment': assignment,
        'requested_reaction_components': parent['requested_reaction_components'],
        'family': selected_family(requested, set()),
        'scope': parent['scope'], 'finding_unit': parent['finding_unit'],
        'received_record_refs': parent['received_record_refs'],
        'literature_source_custody': [{'source_ref': reference, **held_sources[reference]}
                                      for reference in assignment['search_result_refs']],
        'held_sources': held_sources,
        'input_list': input_list, 'consumed_input_ids': consumed,
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*ACQUISITION_TOOLS, *READ_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_experimental_work': EXPERIMENTAL_WORK,
        'held_record_refs': sorted(view.records.refs()),
        'known_assessment_refs': known,
        'examinations': [{'source_ref': outcome['arguments']['source_ref'], **outcome['report']}
                         for outcome in children],
        'reaction_sheets': merged_sheet_features(
            current_sheet_features(view.records),
            [features for outcome in children for features in outcome['report']['finding']['reaction_sheets']]),
        'investigation_finding': investigation_finding(view.records, parent['scope'], parent['finding_unit'], known),
        'last_local_outcome': last_local,
        'visual_evidence': visual,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
