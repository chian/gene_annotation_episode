"""Where the co-folding stands, as a pure function of the view: the commission (the parent input); the target read from the held records
(its sequence artifact, molecule and length); one row per completed unit (its action, status, failure code, whether it can be retried,
and what the action added: the estimate, the request, the state a status request showed, the fix); the state the units give
(``structure_search_child.episode_state`` with no model: the state before an estimate is ``ready``; the held estimate, the request,
the failure waiting for its fix); the latest job held (its handoff and check rows) with its latest check and the estimate recorded with
its launch; the graded co-foldings (``partner_cofolding.graded_rows``); and the yield table. The seconds since the launch are not here
(the summary reads no clock): ``decide`` computes them from the recorded decision time and ``final_to_parent`` returns the duration
observed at the latest check.

Every returned record list is closed under naming (``job_records.returned_with_names``): the scores, their source and the grading sheet
come with everything they name."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    APPLICATION, graded_rows, target_sequence)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    episode_state, job_notice, job_view, resumed_rows, search_facts, unit_row)

COUNTS = ('ligand_count', 'candidate_count', 'sample_count', 'clashing_sample_count', 'highest_value', 'lowest_value')


def internal_summary(view):
    parent, records = view.parent_input, view.records
    query_ref = parent['query_ref']
    record = records.get(query_ref)
    sequence = target_sequence(records, query_ref)
    rows = [unit_row(position, unit) for position, unit in enumerate(view.outcomes)]
    job = job_view(records, APPLICATION)
    resumed = resumed_rows(APPLICATION, job) if parent['resumed'] else []
    facts = episode_state([*resumed, *rows], True, ready_state='ready')
    revised = [row['expected_remaining_seconds'] for unit, row in zip(view.outcomes, rows)
               if unit['tool'] == 'monitor' and row['status'] == 'completed'
               and row['state'] not in ('finished', 'failed', 'unknown')]
    extracted = [unit['outcome'] for unit in view.outcomes if unit['tool'] == 'extract' and unit['outcome']['status'] == 'completed']
    return {'fields': parent['fields'], 'units': parent['units'], 'until': parent['until'], 'prior': parent['prior'],
            'resumed': parent['resumed'], 'known_ended': parent['known_ended'], 'model_passed': parent['model_passed'],
            'target': parent['target'],
            'query': {'subject_ref': query_ref, 'sequence_ref': record['sequence_ref'], 'molecule': record.get('molecule'),
                      'length': len(sequence)},
            'notice': (job_notice(search_facts(job), revised[-1] if revised else None)
                       if job is not None and facts['state'] in ('launched', 'finished') else None),
            'unit_rows': rows, 'state_facts': facts, 'state': facts['state'],
            'last_failure_code': facts['last_failure_code'], 'job': search_facts(job), 'graded': graded_rows(records),
            'counts': [{name: outcome[name] for name in COUNTS} for outcome in extracted],
            'handoff_refs': returned_with_names(records, [ref for unit in view.outcomes if unit['tool'] == 'launch'
                                                          for ref in unit['outcome']['handoff_refs']]),
            'check_refs': returned_with_names(records, [unit['outcome']['check_ref'] for unit in view.outcomes
                                                        if unit['tool'] == 'monitor' and unit['outcome']['status'] == 'completed']),
            'closure_refs': returned_with_names(records, [unit['outcome']['closure_ref'] for unit in view.outcomes
                                                          if unit['tool'] == 'extract' and unit['outcome']['closure_ref'] is not None]),
            'graded_refs': returned_with_names(records, [
                ref for unit in view.outcomes if unit['tool'] == 'extract' for ref in unit['outcome'].get('graded_refs', [])]),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='partner_cofolding_credit'))}
