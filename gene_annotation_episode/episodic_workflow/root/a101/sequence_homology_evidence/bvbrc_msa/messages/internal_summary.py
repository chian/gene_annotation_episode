"""Where the job stands, as a pure function of the view: the commission (the parent input); the target read from the held
records (its sequence artifact and length); one row per completed unit; the state the units give
(``bvbrc_job_child.episode_state``); the latest job held (its handoff and check rows) with its latest check and the
estimate recorded with its launch; the planned size of the job under the commission's ``per_candidate``; the graded
alignments (``bvbrc_msa_alignment.graded_rows``); and the yield table."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    episode_state, job_notice, job_view, resumed_rows, search_facts, unit_row)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    APPLICATION, graded_rows, plan_rows, planned_size, search_rows)


def internal_summary(view):
    parent, records = view.parent_input, view.records
    record = records.get(parent['query_ref'])
    sequence = records.get_artifact(record['sequence_ref'])
    rows = [unit_row(position, unit) for position, unit in enumerate(view.outcomes)]
    job = job_view(records, APPLICATION)
    resumed = resumed_rows(APPLICATION, job) if parent['resumed'] else []
    facts = episode_state([*resumed, *rows])
    revised = [row['expected_remaining_seconds'] for unit, row in zip(view.outcomes, rows)
               if unit['tool'] == 'monitor' and row['status'] == 'completed'
               and row['state'] not in ('finished', 'failed', 'unknown')]
    length = len(sequence.strip())
    plan = plan_rows(search_rows(records, {'subject_refs': [parent['query_ref']]}, parent['search_ref']),
                     parent['candidates'], parent['fields']['per_candidate'])
    return {'fields': parent['fields'], 'units': parent['units'], 'until': parent['until'], 'prior': parent['prior'],
            'resumed': parent['resumed'], 'known_ended': parent['known_ended'], 'target': parent['target'],
            'commission': {'query_ref': parent['query_ref'], 'search_ref': parent['search_ref'],
                           'candidates': parent['candidates'], 'sequence_ref': record['sequence_ref'],
                           'target_length': length},
            'planned': planned_size(plan, length),
            'notice': (job_notice(search_facts(job), revised[-1] if revised else None)
                       if job is not None and facts['state'] in ('launched', 'finished') else None),
            'unit_rows': rows, 'state_facts': facts, 'state': facts['state'],
            'last_failure_code': facts['last_failure_code'], 'job': search_facts(job), 'graded': graded_rows(records),
            'handoff_refs': [ref for unit in view.outcomes if unit['tool'] == 'launch'
                             for ref in unit['outcome']['handoff_refs']],
            'check_refs': [unit['outcome']['check_ref'] for unit in view.outcomes
                           if unit['tool'] == 'monitor' and unit['outcome']['status'] == 'completed'],
            'closure_refs': [unit['outcome']['closure_ref'] for unit in view.outcomes
                             if unit['tool'] == 'extract' and unit['outcome']['closure_ref'] is not None],
            'graded_refs': [ref for unit in view.outcomes if unit['tool'] == 'extract'
                            for ref in unit['outcome'].get('graded_refs', [])],
            'counts': [{name: unit['outcome'][name] for name in ('sequence_count', 'column_count', 'candidate_count')}
                       for unit in view.outcomes if unit['tool'] == 'extract' and unit['outcome']['status'] == 'completed'],
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='bvbrc_msa_credit'))}
