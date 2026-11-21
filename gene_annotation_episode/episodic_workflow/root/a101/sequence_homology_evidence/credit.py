"""Credit: the owner's differential credit over the candidate annotations the head holds evidence for (2026-11-20).

``credit(summary, records)`` is ``candidate_table(...)['credit']`` (library: ``grading/sequence_homology_evidence/
candidate_measurements.py``, which reads the held graded sources in the order the head obtained them and calls
``differential_credit``): a candidate annotation with positive evidence is admitted and earns its score; applying a
test the candidates already on the list have all undergone earns the sizes of the differences of their moves; a
repeat changes nothing, so it earns nothing. The sum has no fixed maximum, so the credit's controller is the
accumulation controller (``yield_estimator.py``); ``A101DifferentialCredit`` is its definition record.

``A101SequenceCredit`` is no longer the credit. It stays as the reader of the residue-similarity index of the
target (``read_details``: the private copy of the old ``native_correspondence_credit.py`` projector, over the
library's ``NativeCorrespondenceScoring``), which the head still reports as a feature of each target
(``axis_findings`` of ``messages/internal_summary.py``). ``read_details`` scores the native BLAST and HMMER gradings
of the received observations inside the scope's target segments and reads only through the custody reader."""
from dataclasses import dataclass
import json
from pathlib import Path

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    SITE_WEIGHT, alignment_contexts, candidate_standing, candidate_table, held_sources, matched_positions_taken)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    SHEET_WEIGHT, msa_test_ceiling, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.msa_alignment_sheet import (
    MINIMUM_GROUP_SIZE)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    PER_CANDIDATE_RANGE, plan_rows, search_rows)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.all_vs_all_run import (
    MINIMUM_CANDIDATES as ALL_VS_ALL_MINIMUM_CANDIDATES, commission_keys as all_vs_all_commission_keys)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    SCALES, VERSION)


@dataclass(frozen=True)
class A101SequenceCredit(NativeCorrespondenceScoring):
    """One deterministic projection for normal actions, details and parents."""
    requires_episode_receipts = True
    requires_known_record_refs = True
    def as_record(self):
        return {'kind': 'a101_native_sequence_correspondence', 'version': VERSION, 'axis': 'A101',
                'sheet': 'convention_015_native_correspondence',
                'supported_algorithms': ['blastp', 'phmmer', 'hmmsearch', 'hmmscan'],
                'inverse_bit_scales': dict(SCALES), 'receipt': 'explicit_known_record_refs',
                'target_aggregation': 'supplied_scope_length_weighted_mean',
                'function_specific_support': 'separate_unknown_without_grounded_inputs',
                'interpretation': 'dimensionless_native_correspondence_not_function_probability',
                'duplicate_handling': 'per_position_max_not_sum_of_hits_or_assertions'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, episode_id=None, run_id=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs, assignment=assignment,
                                 episode_id=episode_id, run_id=run_id, details_limit=0, details_offset=0)


class A101DifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'a101_differential_credit', 'version': 'a101_differential_credit_v3', 'axis': 'A101',
                'measurement': 'subscore_of_one_references_alignments_over_the_scope_regions',
                'subscore_version': VERSION,
                'candidates': 'product_from_database_search_functions_profile_family_reference_sequence',
                'test': 'one_graded_source_kind_with_its_program_and_database',
                'sheet_weights': dict(SHEET_WEIGHT),
                'score': 'sum_over_subscoring_sheets_of_weight_times_sum_of_mean_value_in_test_of_that_kind',
                'admission': 'first_value_above_zero',
                'entry': 'score_after_the_admitting_test_only',
                'differential': 'abs_difference_of_score_moves_of_two_listed_candidates_in_a_test_both_underwent',
                'credit': 'sum_of_entry_scores_and_differentials', 'maximum': 'none',
                'repeat': 'earns_nothing'}


def held_candidate_table(summary, records):
    """The table of candidates of the records this episode holds over the commissioned scope."""
    return candidate_table(records, summary['scope'], held_sources(records))


def credit(summary, records):
    """The differential credit of the held graded sources over the commissioned scope: counted as soon as a graded
    sheet is held. No assessment or reasoning commit switches it on or off, and no model step stands between a graded
    result and its being counted. A child's credit is information in the summary and is never added."""
    return held_candidate_table(summary, records)['credit']


BVBRC_HOMOLOGY_SPEC = (Path(__file__).parents[3] / 'episode_support' / 'forms' / 'application_service_specs'
                       / 'original' / 'Homology.json')


def bvbrc_hit_bound():
    """The most hits a BV-BRC Homology search returns: the default of the application's parameter ``blast_max_hits`` in
    the retained application definition (the route sets no other value)."""
    (parameter,) = [item for item in json.loads(BVBRC_HOMOLOGY_SPEC.read_text())['parameters']
                    if item['id'] == 'blast_max_hits']
    return parameter['default']


def msa_state(summary, records):
    """What the ceiling of one alignment reads, once per call: where the candidates stand, the matched positions taken, the held
    alignments' inputs, and a cache of the searches' product rows."""
    scope, sources = summary['scope'], held_sources(records)
    return {'standing': candidate_standing(records, scope, sources),
            'taken': matched_positions_taken(records, scope, sources),
            'contexts': alignment_contexts(records, scope, sources), 'rows': {}, 'plans': {}}


def msa_value(state, records, query, search_ref, names, per_candidate):
    """The proved maximum of one commission of ``bvbrc_msa`` (see ``ceiling``): 0 unless two candidates each have at least
    ``MINIMUM_GROUP_SIZE`` sequences in the plan and the plan is not exactly a held alignment's input; else
    ``differential_credit.msa_test_ceiling`` over the eligible candidates."""
    if search_ref not in state['rows']:
        state['rows'][search_ref] = search_rows(records, {'subject_refs': [query]}, search_ref)
    rows = state['rows'][search_ref]
    plan = []
    for name in names:
        plan.extend(state['plans'].setdefault((search_ref, name, per_candidate),
                                              plan_rows(rows, [name], per_candidate)))
    if tuple((row['candidate'], row['md5']) for row in plan) in state['contexts'].get(query, ()):
        return 0.0
    sizes = {name: sum(1 for row in plan if row['candidate'] == name) for name in names}
    eligible = ['product:' + name for name in names if sizes[name] >= MINIMUM_GROUP_SIZE]
    if len(eligible) < 2:
        return 0.0
    length, taken = records.subject_length(query), state['taken'].get(query, {})
    return msa_test_ceiling(state['standing'].get(query, {}),
                            {name: (length - taken.get(name, 0)) * SITE_WEIGHT * SHEET_WEIGHT['msa'] for name in eligible},
                            eligible)


def msa_refused(summary, search_ref, names, per_candidate):
    """Whether the head's check refuses this commission as a repeat (``task.check_bvbrc_msa``): an alignment product of it is
    held, or it was commissioned and no outstanding job of it is continued."""
    ordered = sorted(names)
    if any(search_ref in row['used'] and row['settings']['candidates'] == ordered
           and row['settings']['per_candidate'] == per_candidate for row in summary['reusable_alignments']):
        return True
    commissioned = [(row['arguments']['search_ref'], sorted(row['arguments']['candidates']),
                     row['arguments']['per_candidate']) for row in summary['units']
                    if row['kind'] == 'child' and row['slot'] == 'bvbrc_msa']
    return (search_ref, ordered, per_candidate) in commissioned and not any(
        job['outstanding'] and job['identity']['search_ref'] == search_ref
        and job['identity']['candidates'] == ordered and job['identity']['per_candidate'] == per_candidate
        for job in summary['bvbrc_msa_jobs'])


def msa_best(summary, records):
    """``(ceiling, arguments)`` of the commission of ``bvbrc_msa`` with the largest proved maximum among those the head's checks
    would accept now: every held graded search with at least two admitted candidates (``summary['msa_options']``), every
    subset of at least two of them (in the option's order), every sequence count (largest first); ties go to the
    smaller candidate set (a candidate that adds nothing is not named), then the larger count, then the first found. ``(0.0, None)`` when there is none. More than 12
    admitted candidates: only the full set (the maximum is not lowered by adding a candidate, apart from repeats)."""
    state, best = msa_state(summary, records), (0.0, None)
    low, high = PER_CANDIDATE_RANGE
    for item in summary['msa_options']:
        names = item['candidates']
        if len(names) < 2 or summary['held_sequences'].get(item['query_ref']) != 'protein':
            continue
        subsets = ([names] if len(names) > 12 else [[name for i, name in enumerate(names) if mask >> i & 1]
                                                   for mask in range((1 << len(names)) - 1, 0, -1)])
        for chosen in subsets:
            if len(chosen) < 2:
                continue
            for count in range(high, low - 1, -1):
                if msa_refused(summary, item['search_ref'], chosen, count):
                    continue
                value = msa_value(state, records, item['query_ref'], item['search_ref'], chosen, count)
                if value > best[0] + 1e-12 or (best[1] is not None and abs(value - best[0]) <= 1e-12 and value > 0
                                               and len(chosen) < len(best[1]['candidates'])):
                    best = (value, {'query_ref': item['query_ref'], 'search_ref': item['search_ref'],
                                    'candidates': list(chosen), 'per_candidate': count})
    return best


def best_arguments(summary, records, action_type, ctx):
    """The commission that reaches the action's ceiling asked with ``arguments`` ``None`` (``ceiling``), as the arguments a
    decision can name, or ``None`` when no choice of arguments changes the action's ceiling or none can earn
    (``reason``, ``bvbrc_metacats``, and the actions whose arguments the ceiling does not distinguish here). For ``bvbrc_msa``:
    the query, the search, the candidates (a subset of those admitted) and the sequences per candidate (``msa_best``)."""
    if action_type == 'bvbrc_msa':
        return msa_best(summary, records)[1]
    return None


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (with
    ``arguments`` ``None``: the most over every arguments the action type can take now).

    The credit is, per target, the sum of the entry scores of the candidates and of the differentials
    (``differential_credit``). A unit adds at most one graded source, which is one test appended after the earlier ones.
    A candidate's score is the sum of its weighted values over the tests (``differential_credit.SHEET_WEIGHT``: the value of a test
    of a family is the family's weight times its raw value, which is in [0, 1] except an alignment's, below), so that test moves a
    candidate's score by its weighted value. ``differential_credit.test_ceiling`` (for the alignment, ``msa_test_ceiling``) then bounds what the one test can add to
    the target's credit: a pair of candidates on the list that the test measures earns at most ``w`` (the family's weight: the
    difference of two moves in [0, ``w``]); a candidate the test admits earns its entry, its first score, at most ``w``, and its pairs earn
    nothing in that test; a test that measures one candidate on the list and admits none earns 0. Per action type:

    * ``reason``: 0. A reasoning commit holds interpretations and writes no graded source, and the credit is read from
      graded sources only (``held_sources``).
    * ``pairwise_blast``: the one test measures one candidate, the reference sequence (``reference_sequence:<ref>``)
      of the target ``query_ref``. With no pair, a candidate already on the list earns 0; one not on the list can be
      admitted for at most 1.
    * ``bvbrc_blast``: the same, with the hits bounded by the application's ``blast_max_hits`` default
      (``bvbrc_hit_bound``).
    * ``bvbrc_msa``: derived from the current state, as a proved maximum (the proof is in
      ``differential_credit.msa_test_ceiling``). For one commission (the target, the search, the candidates named, the
      sequences per candidate) the plan is deterministic (``plan_rows``: each candidate's top hits by value, one per distinct
      sequence), so each candidate's group size in the alignment is known: a candidate with fewer than ``MINIMUM_GROUP_SIZE``
      sequences, or fewer than two such candidates, earns 0; an alignment whose input (candidates, sequences and order) is
      exactly a held alignment's earns 0 (a repeat). Otherwise a candidate's value is at most ``SITE_WEIGHT`` x (the target
      positions whose matched site of it no held alignment identified) and the alignment's rise is at most the vertex
      maximum of ``msa_test_ceiling``. With ``arguments`` ``None`` the ceiling is the largest over every commission
      the head's checks would accept now (``msa_best``: every held search, every subset of at least two of its admitted
      candidates, every sequence count; commissions already held or already commissioned are left out), so that the
      ceiling of the row shown to the model is the ceiling of one named commission, ``best_arguments``. A group context
      that differs from every held alignment keeps the open bound: the aligner's columns for a group depend on the other
      groups in the alignment, so nothing about a pair already compared carries over.
    * ``all_vs_all``: the cluster test of the commission's committed clustering: it measures the candidates named once each, a
      value being the share of a candidate's sequences in the target's cluster, raw in [0, 1], so bounded as every such test is
      (``test_ceiling`` of the family ``cluster``): a pair of listed candidates at most ``w``, a candidate it admits at most ``w``,
      a single listed candidate 0. A commission identical to one already commissioned or already graded (the search, the candidates, the
      sequences per candidate) earns 0. With ``arguments`` ``None``: the largest over the held graded searches' admitted
      candidates (the bound only grows with candidates).
    * ``bvbrc_metacats``: 0. A MetaCATS report gives no measurement (``candidate_measurements``).
    * ``hmmer_profile_scan``: the scan of the target ``query_ref`` against the profile database ``database`` reports
      each family at most once, so it measures at most as many families as the database holds profiles (``model_count``
      of the manifest the setting ``profile_databases`` names; the family's own reporting threshold only lowers the
      number): at most that many candidates (``profile_family:<accession>``), any on the list or new.
    * ``execute_selected_tool``: ``UNBOUNDED``: a selected registry tool can import a search report of any size and its
      arguments fix no bound on the candidates it measures.

    An action the head's request checks would refuse as a repeat earns nothing, so its ceiling is 0: a pairwise
    comparison already held (``held_comparisons``), a profile scan of the same query and database already held
    (``held_profile_scans``), a search of the same query, program and database already graded (a closed search of
    ``bvbrc_searches``; an outstanding one can still be continued and keeps its ceiling)."""
    if action_type == 'reason' or action_type == 'bvbrc_metacats':
        return 0.0
    scope = summary['scope']
    standing = candidate_standing(records, scope, held_sources(records))
    sequences = [ref for ref in scope['subject_refs'] if ref in summary['held_sequences']]
    queries = sequences if arguments is None else [arguments['query_ref']]
    scanned = {(row['query_ref'], row['database']) for row in summary['held_profile_scans']}
    compared = {(row['query_ref'], row['reference_ref']) for row in summary['held_comparisons']
                if arguments is None or row['program'] == arguments['program']}

    def searched(view, query):
        """Whether a search of ``query`` with the arguments' program and database (any, with no arguments) is graded."""
        return any(row['query_ref'] == query and row['closed']
                   and (arguments is None or (row.get('program'), row.get('database'))
                        == (arguments.get('program'), arguments.get('database')))
                   for row in summary[view])

    def products(target):
        return [candidate for candidate in standing.get(target, {}) if candidate.startswith('product:')]
    if action_type == 'pairwise_blast':
        references = list(summary['held_sequences']) if arguments is None else [arguments['reference_ref']]
        return max((test_ceiling(standing.get(query, {}), ['reference_sequence:' + reference], 'pairwise')
                    for query in queries for reference in references if (query, reference) not in compared),
                   default=0.0)
    if action_type == 'bvbrc_blast':
        limit = bvbrc_hit_bound()
        return max((test_ceiling(standing.get(query, {}), products(query), 'database_search', unseen=limit, limit=limit)
                    for query in queries if not searched('bvbrc_searches', query)), default=0.0)
    if action_type == 'all_vs_all':
        if arguments is None:
            options = [(item['query_ref'], item['candidates']) for item in summary['msa_options']
                       if len(item['candidates']) >= ALL_VS_ALL_MINIMUM_CANDIDATES]
        elif (arguments['search_ref'], sorted(arguments['candidates']), arguments['per_candidate']) in all_vs_all_commission_keys(summary):
            options = []
        else:
            options = [(arguments['query_ref'], arguments['candidates'])]
        return max((test_ceiling(standing.get(query, {}), ['product:' + name for name in names], 'cluster')
                    for query, names in options), default=0.0)
    if action_type == 'bvbrc_msa':
        if arguments is None:
            return msa_best(summary, records)[0]
        return msa_value(msa_state(summary, records), records, arguments['query_ref'], arguments['search_ref'],
                         arguments['candidates'], arguments['per_candidate'])
    if action_type == 'hmmer_profile_scan':
        databases = (ctx.settings['profile_databases'] if arguments is None
                     else {arguments['database']: ctx.settings['profile_databases'][arguments['database']]})
        sizes = [json.loads(Path(path).read_text())['model_count'] for path in databases.values()]
        families = lambda target: [candidate for candidate in standing.get(target, {})
                                   if candidate.startswith('profile_family:')]
        return max((test_ceiling(standing.get(query, {}), families(query), 'profile_scan', unseen=size, limit=size)
                    for query in queries for name, size in zip(databases, sizes) if (query, name) not in scanned),
                   default=0.0)
    if action_type == 'execute_selected_tool':
        return UNBOUNDED
    raise ValueError('a101_ceiling_not_derived_for_action_type:' + action_type)
