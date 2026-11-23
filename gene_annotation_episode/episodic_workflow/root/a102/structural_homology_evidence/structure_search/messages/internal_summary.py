"""Where the search stands, as a pure function of the view: the commission (the parent input); the target read from the held
records (its sequence artifact, molecule and length); one row per completed unit (its action, status, failure code, whether it
can be retried, and what the action added: for ``get_model`` the source and what it answered, the estimate, the request, the
state a status request showed, the fix); the model the episode holds (one it obtained, the one its commission passed, or the one
the resumed job was given: ``foldseek_search.held_model``, ``passed_model``, ``job_model``); the model sources still offered;
the state the units give (``structure_search_child.episode_state``: the held estimate, the request, the failure waiting for its
fix); the latest job held (its handoff and check rows) with its latest check and the estimate recorded with its launch; the
graded searches (``foldseek_search.graded_rows``); and the yield table. The seconds since the launch are not here (the summary
reads no clock): ``decide`` computes them from the recorded decision time and ``final_to_parent`` returns the duration observed
at the latest check.

Every returned record list is closed under naming (``job_records.returned_with_names``): the model's product row, its source and
artifact, the result, the hit metadata and the grading sheet come with everything they name."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import returned_with_names
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    APPLICATION, graded_rows, held_model, job_model, passed_model, target_sequence)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    episode_state, job_notice, job_view, resumed_rows, search_facts, sources_offered, unit_row)

COUNTS = ('hit_count', 'named_count', 'not_asked_count', 'control_count', 'candidate_count', 'metadata_request_count',
          'metadata_failure_count', 'naming_batch_count', 'naming_stopped')


def internal_summary(view):
    parent, records = view.parent_input, view.records
    query_ref = parent['query_ref']
    record = records.get(query_ref)
    sequence = target_sequence(records, query_ref)
    rows = [unit_row(position, unit) for position, unit in enumerate(view.outcomes)]
    job = job_view(records, APPLICATION)
    resumed = resumed_rows(APPLICATION, job) if parent['resumed'] else []
    if parent['resumed']:
        model = job_model(job['handoff'])
    elif parent['model_ref'] is not None:
        model = passed_model(records, parent['model_ref'], record['sequence_ref'])
    else:
        model = held_model(records)
    facts = episode_state([*resumed, *rows], model is not None)
    revised = [row['expected_remaining_seconds'] for unit, row in zip(view.outcomes, rows)
               if unit['tool'] == 'monitor' and row['status'] == 'completed'
               and row['state'] not in ('finished', 'failed', 'unknown')]
    extracted = [unit['outcome'] for unit in view.outcomes if unit['tool'] == 'extract' and unit['outcome']['status'] == 'completed']
    return {'fields': parent['fields'], 'units': parent['units'], 'until': parent['until'], 'prior': parent['prior'],
            'resumed': parent['resumed'], 'known_ended': parent['known_ended'], 'model_passed': parent['model_passed'],
            'target': parent['target'],
            'query': {'subject_ref': query_ref, 'sequence_ref': record['sequence_ref'], 'molecule': record.get('molecule'),
                      'length': len(sequence)},
            'model': model,
            'sources': sources_offered(APPLICATION, rows, model_held=model is not None, sequence=sequence),
            'model_tries': [{name: row[name] for name in ('source', 'model_status', 'residues', 'mean_plddt')}
                            for row in rows if row['action'] == 'get_model' and row['status'] == 'completed'],
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
                *([] if model is None or model['row_ref'] is None else [model['row_ref']]),
                *(ref for unit in view.outcomes if unit['tool'] == 'extract' for ref in unit['outcome'].get('graded_refs', []))]),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='structure_search_credit'))}
