"""Where the episode stands, as a pure function of the loop's view: the commission, one row per completed unit
(a selected tool, a reasoning commit, a pairwise comparison or a child commission), what each child reported, the
records this episode committed or graded (its reasoning commits and the graded records of its comparisons: what its
credit reads), the handoff records its children returned, the working state of the scope and the controller's yield
table.

For the commissions (``task.commission_fields``, ``msg_to_child``) the summary also holds what a commission is
chosen from and built with: ``held_record_refs`` (the held records), ``held_sequences`` (the held records
that carry a sequence, each with its molecule: what the two sequences of a comparison are chosen from),
``held_comparisons`` (the pairwise comparisons already held: what the check refuses to run again), ``database_searches`` (the searches of the hosted service this episode holds, with their records: what a commission of ``database_blast`` continues), ``held_source_refs`` (the held sources) and ``named_refs`` (for each held
record, the held records it names: what travels in custody beside it)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    scientific_digest)

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    ALL, axis_features)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.pairwise_blast_comparison import (
    PROVIDER as PAIRWISE_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.hmmer_profile_scan import (
    PROVIDER as PROFILE_PROVIDER)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    held_searches)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)

from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_job_child as job_child, bvbrc_msa_alignment as msa)

from ..credit import A101DifferentialCredit, A101SequenceCredit, held_candidate_table
from ..task import CHILD_SLOTS, PAIRWISE_TOOL, PROFILE_TOOL

EXECUTED = ('completed', 'partial')
# The tools whose records this episode's credit reads and so returns: its reasoning commits and its graded comparisons.
CREDITED_TOOLS = ('reason', PAIRWISE_TOOL, PROFILE_TOOL)
EVIDENCE_RECORD_TYPES = ('observation', 'assessment')
# The record types that carry a sequence: what the two sequences of a comparison are chosen from.
SEQUENCE_RECORD_TYPES = ('input', 'reference', 'product')


def _named(records, reference):
    """The held records the held record ``reference`` names (an artifact names none). A pass carries only the
    records named, so a commission names these beside the record for a child whose code follows them: a source and
    its artifacts, an observation and its source and subjects, a subject and its sequence."""
    if reference.startswith('artifact_'):
        return []
    return [named for named in dict.fromkeys(records.named_references(reference))
            if named != reference and records.holds(named)]


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
            'unlabelled_hit_count': target['unlabelled_hit_count'], 'differentials': target['differentials']}


def _across_targets(table, name):
    """The rows ``name`` of every target of the table, each with its target reference."""
    return [{'target_ref': ref, **row} for ref, target in table['targets'].items() for row in target[name]]


def internal_summary(view):
    records = view.records
    parent = view.parent_input
    units, child_reports, committed, handoff_refs, check_refs, closure_refs, last = [], [], [], [], [], [], None
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
                   'credit': report['credit'], 'record_refs': list(report['record_refs'])}
            committed.extend(ref for ref in report['graded_refs'] if ref not in committed)
            child_reports.append({'slot': outcome['slot'], **report})
            handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
            check_refs.extend(ref for ref in report['check_refs'] if ref not in check_refs)
            closure_refs.extend(ref for ref in report['closure_refs'] if ref not in closure_refs)
        units.append(row)
        last = row
    held = [ref for ref in records.refs() if not ref.startswith('row_')]
    held_sequences = {ref: records.get(ref).get('molecule') for ref in held
                      if ref.split('_')[0] in SEQUENCE_RECORD_TYPES and records.get(ref).get('sequence_ref')}
    details = A101SequenceCredit().read_details(records, parent['scope'], known_record_refs=held,
                                                details_limit=ALL, details_offset=0)
    table = held_candidate_table(parent, records)
    held_products = products(records)
    alignments = [row for row in held_products if row['kind'] == msa.PRODUCT_KIND]
    findings = [{**finding, **_candidate_fields(table['targets'][target])}
                for target, finding in zip(details['a101_sheet']['targets'], axis_features(details), strict=True)]
    return {**parent,
            'path_depth': len(view.path),
            'initial_selection_sha256': scientific_digest(parent['selection']),
            'permitted_children': sorted(CHILD_SLOTS),
            'units': units, 'last_local_outcome': last, 'child_reports': child_reports,
            'committed_record_refs': committed, 'handoff_refs': handoff_refs, 'check_refs': check_refs,
            'closure_refs': closure_refs,
            'held_record_refs': held,
            'held_source_refs': [row['id'] for row in records.list('source')],
            'held_comparisons': _held_comparisons(records),
            'held_profile_scans': _held_profile_scans(records),
            'held_sequences': held_sequences,
            'database_searches': held_searches(records, {ref: records.get(ref)['sequence_ref'] for ref in held_sequences}),
            'bvbrc_searches': bvbrc.held_searches(records, {ref: records.get(ref)['sequence_ref'] for ref in held_sequences}),
            'named_refs': {ref: _named(records, ref) for ref in held},
            'msa_options': msa.msa_options(records, parent['scope'], table),
            'bvbrc_msa_jobs': job_child.held_jobs(records, msa.APPLICATION),
            'held_alignments': msa.graded_rows(records),
            'data_products': [{'row_ref': row['id'], 'kind': row['kind'], 'edam_data': row['edam_data'],
                               'edam_format': row['edam_format'], 'locations': row['locations'],
                               'settings': row['settings']} for row in held_products],
            'data_product_refs': [row['id'] for row in held_products],
            'alignment_product_refs': [row['id'] for row in alignments],
            'reusable_alignments': {(row['used'][1], tuple(row['settings']['candidates']),
                                     row['settings']['per_candidate']): row for row in alignments},
            'evidence_refs': [row['id'] for kind in EVIDENCE_RECORD_TYPES for row in records.list(kind)],
            'working_state': records.reasoning_view(parent['scope']),
            'reasoning_schema': records.reasoning_schema(),
            'credit_binding': A101DifferentialCredit().as_record(), 'axis_findings': findings,
            'candidates': _across_targets(table, 'candidates'), 'tests': _across_targets(table, 'tests'),
            'differentials': _across_targets(table, 'differentials'),
            'unlabelled_hit_count': sum(target['unlabelled_hit_count'] for target in table['targets'].values()),
            'units_consumed': view.units_consumed,
            'action_yields': (None if view.controller_state is None
                              else yield_table(view.controller_state, forecast_unit='differential_credit'))}
