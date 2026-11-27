"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit
(a selected tool, a pairwise comparison, a profile scan or a child commission), what each child reported, the
records this episode graded (the graded records of its comparisons: what its
credit reads), the handoff records its children returned and the controller's yield
table.

For the commissions (``task.commission_fields``, ``msg_to_child``) the summary also holds what a commission is
chosen from and built with: ``held_record_refs`` (the held records), ``held_sequences`` (the held records
that carry a sequence, each with its molecule: what the two sequences of a comparison are chosen from),
``held_comparisons`` (the pairwise comparisons already held: what the check refuses to run again), ``bvbrc_searches`` (the BV-BRC searches this episode holds, with their records: what a commission of ``bvbrc_blast`` continues), ``held_clusterings`` (the committed clusterings of the ``all_vs_all`` child) and ``named_refs`` (for each held
record, job ledger rows included, the held records it names: what travels in custody beside it).

``returned_refs`` are the record lists ``final_to_parent`` returns (``committed_record_refs``, ``execution_handoff_refs``,
``execution_check_refs``, ``execution_closure_refs``, ``data_product_refs``), each CLOSED UNDER NAMING by
``job_records.returned_with_names`` (the records chosen with everything they name, recursively, among the held records), as every
child's returned lists are: the parent holds what a returned record names.

``candidate_hit_organisms`` is the selectable field of that name ``final_to_parent`` returns: for each target, in the
order of ``axis_findings``, the organisms of the database hits behind each candidate a database search named (taxon
ids and hit counts: the table's ``hit_organisms``). ``candidate_hit_feature_kinds`` is the selectable field of that
name, in the same arrangement: the feature types of those hits (types of ``feature_types.KINDS`` and hit counts: the
table's ``hit_feature_kinds``)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    named_records, outstanding_jobs, returned_with_names)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.pairwise_blast_comparison import (
    PROVIDER as PAIRWISE_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.hmmer_profile_scan import (
    PROVIDER as PROFILE_PROVIDER)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)

from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as all_vs_all, bvbrc_job_child as job_child, bvbrc_metacats_search as metacats, bvbrc_msa_alignment as msa)

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    targets)
from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    TRACE_PROVIDER)

from ..credit import A101SequenceCredit, held_candidate_table
from ..task import PAIRWISE_TOOL, PROFILE_TOOL

EXECUTED = ('completed', 'partial')
# The tools whose records this episode returns: its graded comparisons, its joinings of its
# candidates (all read by its credit) and the claims it made.
CREDITED_TOOLS = (PAIRWISE_TOOL, PROFILE_TOOL)
# The record types that carry a sequence: what the two sequences of a comparison are chosen from.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')


def _held_comparisons(records):
    """The pairwise comparisons this episode holds, read from their sources: the query, the reference and the
    program of the retained sheet."""
    rows = []
    for source in records.list('source'):
        if source['provider'] == PAIRWISE_PROVIDER:
            sheet = json.loads(records.get_artifact(source['auxiliary_artifact_refs'][0]))['grading']['sheet']
            query, reference = source['operand_refs']
            rows.append({'query_ref': query, 'reference_ref': reference, 'program': sheet['input']['search']['program'],
                         'source_ref': source['id']})
    return rows


def _held_profile_scans(records):
    """The profile scans this episode holds, read from their sources: the query, the profile database and the number
    of families that matched."""
    return [{'query_ref': source['operand_refs'][0], 'database': source['accession'], 'source_ref': source['id'],
             'family_count': sum(1 for row in records.list('reference') if row['source_ref'] == source['id'])}
            for source in records.list('source') if source['provider'] == PROFILE_PROVIDER]


def _candidate_fields(target):
    """The candidate fields of the finding of one target (``final_to_parent``)."""
    return {'candidates': target['candidates'], 'candidate_count': len(target['candidates']),
            'not_asked_hit_count': target['not_asked_hit_count'], 'no_product_hit_count': target['no_product_hit_count'],
            'uncharacterized_hit_count': target['uncharacterized_hit_count'],
            **({'uncharacterized_best_value': target['uncharacterized_best_value']}
               if 'uncharacterized_best_value' in target else {}),
            'uncharacterized_families': target['uncharacterized_families'],
            **{name: target[name] for name in ('grouped_candidates', 'grouping_in_force') if name in target},
            'differentials': target['differentials']}


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, child_reports, committed, handoff_refs, check_refs, closure_refs = [], [], [], [], [], []
    for position, outcome in enumerate(view.outcomes):
        if outcome['kind'] == 'tool':
            result = outcome['outcome']
            row = {'position': position, 'kind': 'tool', 'tool': outcome['tool'],
                   'selected': outcome['arguments'].get('tool'), 'status': result['status'],
                   'record_refs': list(result['record_refs']), 'feedback': result.get('feedback')}
            if outcome['tool'] == PAIRWISE_TOOL:
                row['comparison'] = dict(outcome['arguments'])
                row['features'] = result['result']
            if outcome['tool'] == PROFILE_TOOL:
                row['scan'] = dict(outcome['arguments'])
                row['features'] = result['result']
            if outcome['tool'] in CREDITED_TOOLS and result['status'] in EXECUTED:
                committed.extend(ref for ref in result['record_refs'] if ref not in committed)
        else:
            report = outcome['report']
            row = {'position': position, 'kind': 'child', 'slot': outcome['slot'], 'status': 'completed',
                   'arguments': outcome['arguments'], 'child_state': report['finding'].get('state'),
                   'credit': report['credit'], 'record_refs': list(report['record_refs']),
                   # the child returned parked (its job launched, not extracted: the job children set ``parked`` true then
                   # and only then): the unit's outcome is pending (``credit.outcome_pending``)
                   'parked': report['finding'].get('parked') is True}
            committed.extend(ref for ref in report['graded_refs'] if ref not in committed)
            child_reports.append({'slot': outcome['slot'], **report})
            handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
            check_refs.extend(ref for ref in report['check_refs'] if ref not in check_refs)
            closure_refs.extend(ref for ref in report['closure_refs'] if ref not in closure_refs)
        units.append(row)
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    held_sequences = {ref: records.get(ref).get('molecule') for ref in held
                      if ref.split('_')[0] in SEQUENCE_RECORD_TYPES and records.get(ref).get('sequence_ref')
                      # a reference whose accession is a record held is that record's own sequence under another name
                      and records.get(ref).get('accession') not in held}
    # the sequences the head finds annotations for: the scope's subjects, or the proteins of the feature calls held
    wanted = targets(records, parent['scope'])
    details = A101SequenceCredit().read_details(
        records, parent['scope'], known_record_refs=held, details_limit=ALL, details_offset=0,
        subjects=None if wanted == records.validate_scope(parent['scope'])['subject_refs'] else wanted)
    table = held_candidate_table(parent, records)
    held_products = products(records)
    alignments = [row for row in held_products if row['kind'] == msa.PRODUCT_KIND]
    findings = [{'target_ref': [target], **finding, **_candidate_fields(table['targets'][target])}
                for target, finding in zip(details['a101_sheet']['targets'], axis_features(details), strict=True)]
    return {**parent,
            'path_depth': len(view.path),
            'units': units, 'child_reports': child_reports,
            'returned_refs': {name: returned_with_names(records, refs) for name, refs in (
                ('committed_record_refs', committed), ('execution_handoff_refs', handoff_refs),
                ('execution_check_refs', check_refs), ('execution_closure_refs', closure_refs),
                ('data_product_refs', [row['id'] for row in held_products]))},
            'held_record_refs': held,
            'held_comparisons': _held_comparisons(records),
            'held_profile_scans': _held_profile_scans(records),
            'held_sequences': held_sequences, 'targets': wanted,
            'bvbrc_searches': bvbrc.held_searches(records, {ref: records.get(ref)['sequence_ref'] for ref in held_sequences},
                                                  searched_types=('input', 'product')),
            'named_refs': {ref: named_records(records, ref) for ref in records.refs()},
            # the held handoffs whose closure is not held (``job_records.outstanding_jobs``): this episode's own local jobs
            # (the profile scan) are closed in their unit; a child's job counts until the closure it returns is held
            'outstanding_handoff_count': len(outstanding_jobs(records)),
            'msa_options': msa.msa_options(records, parent['scope'], table),
            'bvbrc_msa_jobs': job_child.held_jobs(records, msa.APPLICATION),
            'held_alignments': msa.graded_rows(records),
            'metacats_options': metacats.held_alignments(records),
            'bvbrc_metacats_jobs': job_child.held_jobs(records, metacats.APPLICATION),
            'held_clusterings': all_vs_all.held_clusterings(records),
            'held_metacats': metacats.graded_rows(records),
            'data_products': [{'row_ref': row['id'], 'kind': row['kind'], 'edam_data': row['edam_data'],
                               'edam_format': row['edam_format'], 'locations': row['locations'],
                               'settings': row['settings']} for row in held_products],
            'alignment_product_refs': [row['id'] for row in alignments],
            'reusable_alignments': alignments,
            'axis_findings': findings,
            'candidate_hit_organisms': [{'candidates': table['targets'][target]['hit_organisms']}
                                        for target in details['a101_sheet']['targets']],
            'candidate_hit_feature_kinds': [{'candidates': table['targets'][target]['hit_feature_kinds']}
                                            for target in details['a101_sheet']['targets']],
            # the claims this episode holds, each with the annotation it was made from, read from the claim tool's traces
            'claims': [{**claim, 'annotation': trace['annotation'], 'target_ref': [trace['subject_ref']]}
                       for trace in (json.loads(records.get_artifact(source['artifact_ref']))
                                     for source in records.list('source') if source['provider'] == TRACE_PROVIDER)
                       for claim in trace['claims']],
            'candidates': [{'target_ref': ref, **row} for ref, target in table['targets'].items()
                           for row in target['candidates']],
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='differential_credit'))}
