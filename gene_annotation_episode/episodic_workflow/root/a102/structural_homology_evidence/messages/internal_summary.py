"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit (a child
commission), what the child reported, the graded searches and the models the episode holds, the job rows of the child's jobs, the
candidates with their scores and the controller's yield table.

For the commission (``task.commission_fields``, ``msg_to_child``) the summary also holds what a commission is chosen from and
built with: ``held_sequences`` (the held records that carry a sequence, each with its molecule), ``model_rows`` (the held data-product
rows of kind ``protein_structure_model``, each with the target it was made from), ``graded_searches`` (the searches graded: what the
decision shows), ``held_searches`` (per target the ``[database, model SHA-256]`` of each graded search, read by the credit's own reader:
what the commission's check refuses to run again), ``structure_search_jobs`` (the child's jobs, read ONLY from the job ledger rows
the head holds: their request, identity, state and rows) and ``named_refs`` (for each held record, job ledger rows included, the held
records it names: what travels in custody beside it).

``returned_refs`` are the record lists ``final_to_parent`` returns (``committed_record_refs``, ``execution_handoff_refs``,
``execution_check_refs``, ``execution_closure_refs``, ``data_product_refs``), each CLOSED UNDER NAMING by
``job_records.returned_with_names`` (the records chosen with everything they name, recursively, among the held records), as every
child's returned lists are: the parent holds what a returned record names."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    held_searches, held_sources)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    named_records, outstanding_jobs, returned_with_names)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    APPLICATION, MODEL_KIND, graded_rows, target_sequence)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    held_jobs)

from ..credit import held_candidate_table

LEADING = 10
# The record types that carry a sequence: what the target of a search is chosen from.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')


def _leading(target):
    """The leading candidates of one target of the candidate table: name, score and sheets, the leading one first."""
    return [{'vocabulary': row['vocabulary'], 'name': row['name'], 'score': row['score'], 'sheets': row['sheets']}
            for row in target['candidates'][:LEADING]]


def internal_summary(view):
    records, parent = view.records, view.parent_input
    units, child_reports, handoff_refs, check_refs, closure_refs, graded = [], [], [], [], [], []
    for position, outcome in enumerate(view.outcomes):
        report = outcome['report']
        units.append({'position': position, 'kind': 'child', 'slot': outcome['slot'], 'status': 'completed',
                      'arguments': outcome['arguments'], 'child_state': report['finding'].get('state'),
                      'credit': report['credit'], 'record_refs': list(report['record_refs']),
                      # the child returned parked (its job launched, not extracted: the job children set ``parked`` true
                      # then and only then): the unit's outcome is pending (``credit.outcome_pending``)
                      'parked': report['finding'].get('parked') is True})
        child_reports.append({'slot': outcome['slot'], **report})
        for found, name in ((handoff_refs, 'handoff_refs'), (check_refs, 'check_refs'), (closure_refs, 'closure_refs'),
                            (graded, 'graded_refs')):
            found.extend(ref for ref in report[name] if ref not in found)
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    held_sequences = {ref: records.get(ref).get('molecule') for ref in held
                      if ref.split('_')[0] in SEQUENCE_RECORD_TYPES and records.get(ref).get('sequence_ref')}
    scope = parent['scope']
    targets = [{'target_ref': ref, 'molecule': held_sequences.get(ref), 'length': len(target_sequence(records, ref))}
               for ref in scope['subject_refs'] if ref in held_sequences]
    sequence_of = {records.get(ref)['sequence_ref']: ref for ref in held_sequences}
    model_rows = [{**row, 'query_ref': next(sequence_of[ref] for ref in row['used'] if ref in sequence_of)}
                  for row in products(records, MODEL_KIND)]
    table = held_candidate_table(parent, records)
    searches = graded_rows(records)
    held_products = products(records)
    findings = []
    for target in targets:
        ref = target['target_ref']
        row, mine = table['targets'][ref], [item for item in searches if item['query_ref'] == ref]
        model = next((item for item in model_rows if item['query_ref'] == ref), None)
        findings.append({
            'target_ref': ref, 'molecule': target['molecule'], 'search_count': len(mine),
            'hit_count': sum(item['hit_count'] for item in mine), 'named_count': sum(item['named_count'] for item in mine),
            'not_asked_count': sum(item['not_asked_count'] for item in mine),
            'candidate_count': len(row['candidates']), 'candidates': _leading(row),
            **({} if model is None else {'model_origin': model['settings']['origin'],
                                         'model_residues': model['settings']['residues_covered'],
                                         'model_mean_plddt': model['settings']['mean_plddt']})})
    return {**parent,
            'path_depth': len(view.path),
            'units': units, 'child_reports': child_reports,
            'returned_refs': {name: returned_with_names(records, refs) for name, refs in (
                ('committed_record_refs', graded), ('execution_handoff_refs', handoff_refs),
                ('execution_check_refs', check_refs), ('execution_closure_refs', closure_refs),
                ('data_product_refs', [row['id'] for row in held_products]))},
            'held_record_refs': held, 'held_sequences': held_sequences, 'targets': targets,
            'model_rows': model_rows, 'graded_searches': searches,
            'held_searches': {target: [list(pair) for pair in pairs] for target, pairs in held_searches(
                records, scope, held_sources(records)).items()},
            'structure_search_jobs': held_jobs(records, APPLICATION),
            'named_refs': {ref: named_records(records, ref) for ref in records.refs()},
            # the held handoffs whose closure is not held (``job_records.outstanding_jobs``): a child's job counts until the
            # closure it returns is held
            'outstanding_handoff_count': len(outstanding_jobs(records)),
            'data_products': [{'row_ref': row['id'], 'kind': row['kind'], 'edam_data': row['edam_data'],
                               'edam_format': row['edam_format'], 'locations': row['locations'],
                               'settings': row['settings']} for row in held_products],
            'credit_table': {ref: {'candidate_count': len(row['candidates']), 'candidates': _leading(row),
                                   'tests': row['tests']} for ref, row in table['targets'].items()},
            'findings': findings,
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='differential_credit'))}
