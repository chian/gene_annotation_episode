"""Where the job stands, as a pure function of the view: the commission (the parent input); one row per completed unit; the
state the units give (``bvbrc_job_child.episode_state``); the latest job held (its handoff and check rows) with its latest
check and the estimate recorded with its launch; the planned size of the job (the groups code builds from the held
alignment); the graded analyses (``bvbrc_metacats_search.graded_rows``); and the yield table."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    episode_state, job_notice, job_view, resumed_rows, search_facts, unit_row)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_metacats_search import (
    APPLICATION, graded_rows, plan, planned_size)


def internal_summary(view):
    parent, records = view.parent_input, view.records
    rows = [unit_row(position, unit) for position, unit in enumerate(view.outcomes)]
    extracted = [ref for unit in view.outcomes if unit['tool'] == 'extract' for ref in unit['outcome'].get('graded_refs', [])]
    job = job_view(records, APPLICATION)
    resumed = resumed_rows(APPLICATION, job) if parent['resumed'] else []
    facts = episode_state([*resumed, *rows])
    revised = [row['expected_remaining_seconds'] for unit, row in zip(view.outcomes, rows)
               if unit['tool'] == 'monitor' and row['status'] == 'completed'
               and row['state'] not in ('finished', 'failed', 'unknown')]
    planned = plan(records, parent['alignment_ref'])
    return {'fields': parent['fields'], 'units': parent['units'], 'until': parent['until'], 'prior': parent['prior'],
            'resumed': parent['resumed'], 'known_ended': parent['known_ended'], 'target': parent['target'],
            'scope': parent['scope'], 'organism': parent['organism'],
            'commission': {'query_ref': parent['query_ref'], 'alignment_ref': parent['alignment_ref']},
            'planned': {**planned_size(planned), 'candidates': [{'name': group['product'], 'size': len(group['ids'])}
                                                                for group in planned['groups']]},
            'notice': (job_notice(search_facts(job), revised[-1] if revised else None)
                       if job is not None and facts['state'] in ('launched', 'finished') else None),
            'unit_rows': rows, 'state_facts': facts, 'state': facts['state'],
            'last_failure_code': facts['last_failure_code'], 'job': search_facts(job),
            'graded': [row for row in graded_rows(records) if row['source_ref'] in extracted],
            'handoff_refs': returned_with_names(records, [ref for unit in view.outcomes if unit['tool'] == 'launch'
                                                          for ref in unit['outcome']['handoff_refs']]),
            'check_refs': returned_with_names(records, [unit['outcome']['check_ref'] for unit in view.outcomes
                                                        if unit['tool'] == 'monitor' and unit['outcome']['status'] == 'completed']),
            'closure_refs': returned_with_names(records, [unit['outcome']['closure_ref'] for unit in view.outcomes
                                                          if unit['tool'] == 'extract' and unit['outcome']['closure_ref'] is not None]),
            'graded_refs': returned_with_names(records, extracted),
            'counts': [{name: unit['outcome'][name] for name in ('group_count', 'sequence_count', 'column_count',
                                                                 'significant_count')}
                       for unit in view.outcomes if unit['tool'] == 'extract' and unit['outcome']['status'] == 'completed'],
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='bvbrc_metacats_credit'))}
