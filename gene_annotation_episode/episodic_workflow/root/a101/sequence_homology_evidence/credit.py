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
from itertools import combinations
import json
from pathlib import Path

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    SITE_WEIGHT, alignment_contexts, candidate_standing, candidate_table, dataset_bests, held_sources, matched_positions_taken,
    unconfirmed_matched_sites)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    SHEET_WEIGHT, cluster_test_ceiling, metacats_test_ceiling, msa_test_ceiling, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_metacats_search as metacats)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.msa_alignment_sheet import (
    MINIMUM_GROUP_SIZE)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    PER_CANDIDATE_RANGE, plan_rows, search_rows)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.all_vs_all_run import (
    MINIMUM_CANDIDATES as ALL_VS_ALL_MINIMUM_CANDIDATES, PER_CANDIDATE_RANGE as ALL_VS_ALL_PER_CANDIDATE_RANGE,
    commission_keys as all_vs_all_commission_keys)
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
        return {'kind': 'a101_differential_credit', 'version': 'a101_differential_credit_v5', 'axis': 'A101',
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
                'dataset': 'tests_of_one_dataset_earn_their_largest_test_credit_once_and_sheet_reads_largest_value',
                'metacats': 'matched_conserved_sites_confirmed_significant_not_confirmed_before_times_site_weight_msa_family',
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


def metacats_refused(summary, records, alignment_ref):
    """Whether the head's check refuses a MetaCATS commission of this alignment as a repeat (``task.check_bvbrc_metacats``,
    ``bvbrc_metacats_search.check_commission``): a report of its groups is held (the reuse check), or it was commissioned and
    no outstanding job of it is continued."""
    if metacats.reusable_report(records, alignment_ref) is not None:
        return True
    commissioned = [row['arguments']['alignment_ref'] for row in summary['units']
                    if row['kind'] == 'child' and row['slot'] == 'bvbrc_metacats']
    groups = metacats.group_artifact_ref(metacats.plan(records, alignment_ref))
    return alignment_ref in commissioned and not any(
        job['outstanding'] and job['identity']['groups_ref'] == groups for job in summary['bvbrc_metacats_jobs'])


def metacats_value(summary, records, alignment_ref, standing=None):
    """The proved maximum of one commission of ``bvbrc_metacats`` of the held alignment ``alignment_ref`` (see ``ceiling``): 0 when
    the check refuses it as a repeat; else ``differential_credit.metacats_test_ceiling`` over the alignment's group candidates,
    each at most (its matched sites in the alignment not yet confirmed) x ``SITE_WEIGHT`` x the msa sheet's weight."""
    if metacats_refused(summary, records, alignment_ref):
        return 0.0
    scope, sources = summary['scope'], held_sources(records)
    target, open_sites = unconfirmed_matched_sites(records, scope, sources, alignment_ref)
    names = [group['product'] for group in metacats.plan(records, alignment_ref)['groups']]
    if standing is None:
        standing = candidate_standing(records, scope, sources)
    return metacats_test_ceiling(standing.get(target, {}),
                                 {'product:' + name: open_sites.get(name, 0) * SITE_WEIGHT * SHEET_WEIGHT['msa'] for name in names},
                                 ['product:' + name for name in names])


def metacats_best(summary, records):
    """``(ceiling, arguments)`` of the commission of ``bvbrc_metacats`` with the largest proved maximum among the alignments a
    commission may name now (``summary['metacats_options']``; the first found on a tie), as ``{'query_ref', 'alignment_ref'}``
    (the resource and ``until`` do not change the ceiling). ``(0.0, None)`` when none can earn."""
    best, standing = (0.0, None), candidate_standing(records, summary['scope'], held_sources(records))
    for item in summary['metacats_options']:
        value = metacats_value(summary, records, item['alignment_ref'], standing)
        if value > best[0] + 1e-12:
            best = (value, {'query_ref': item['query_ref'], 'alignment_ref': item['alignment_ref']})
    return best


def all_vs_all_value(standing, bests, query, search_ref, names):
    """The proved maximum of one commission of ``all_vs_all`` that the head's check accepts (see ``ceiling``):
    ``differential_credit.cluster_test_ceiling`` over the named product candidates, less the dataset's (the search's) best test
    credit so far (``dataset_bests``). ``standing`` and ``bests`` are ``candidate_standing`` and ``dataset_bests`` of the head."""
    return cluster_test_ceiling(standing.get(query, {}), ['product:' + name for name in names],
                                bests.get(query, {}).get(search_ref, 0.0))


def all_vs_all_best(summary, records):
    """``(ceiling, arguments)`` of the commission of ``all_vs_all`` with the largest proved maximum among those the head's check
    (``all_vs_all_run.check_commission``) would accept now: the query a protein sequence of the scope, a held graded search of it
    (``summary['msa_options']``), two or more of the candidates admitted from it, the candidate set of that search not
    commissioned or graded before at any ``per_candidate`` (``commission_keys``: the same candidates again are a replicate). The arguments are ``{'query_ref', 'search_ref', 'candidates',
    'per_candidate'}``; ``(0.0, None)`` when none can earn.

    Order (the first found wins a tie): the options in their order, larger candidate sets first, the sets of one size in the
    option's order (``itertools.combinations``), at the largest ``per_candidate`` (the count does not
    change the maximum: every named candidate has at least one sequence in the set). A size is skipped, and the search ends, when
    no set of that size can beat the best found: the maximum of a set of ``k`` candidates is largest for the set with the most
    unlisted candidates or the one with the most listed ones (``u + floor(l^2 / 4)`` is convex in ``u`` with ``u + l = k``), and
    it does not grow as ``k`` falls."""
    scope, low, high = summary['scope'], *ALL_VS_ALL_PER_CANDIDATE_RANGE
    options = [item for item in summary['msa_options'] if item['query_ref'] in scope['subject_refs']
               and summary['held_sequences'].get(item['query_ref']) == 'protein'
               and len(set(item['candidates'])) >= ALL_VS_ALL_MINIMUM_CANDIDATES]
    if not options:
        return (0.0, None)
    sources = held_sources(records)
    standing, bests = candidate_standing(records, scope, sources), dataset_bests(records, scope, sources)
    commissioned, best = all_vs_all_commission_keys(summary), (0.0, None)
    for item in options:
        query, search, names = item['query_ref'], item['search_ref'], list(dict.fromkeys(item['candidates']))
        listed = lambda name: bool(standing.get(query, {}).get('product:' + name, {}).get('listed'))
        unlisted_first, listed_first = sorted(names, key=listed), sorted(names, key=lambda name: not listed(name))
        for size in range(len(names), ALL_VS_ALL_MINIMUM_CANDIDATES - 1, -1):
            top = max(all_vs_all_value(standing, bests, query, search, unlisted_first[:size]),
                      all_vs_all_value(standing, bests, query, search, listed_first[:size]))
            if top <= best[0] + 1e-12:
                break
            for chosen in combinations(names, size):
                value = all_vs_all_value(standing, bests, query, search, chosen)
                if value <= best[0] + 1e-12:
                    continue
                if (search, sorted(chosen)) in commissioned:
                    continue
                count = high
                best = (value, {'query_ref': query, 'search_ref': search, 'candidates': list(chosen), 'per_candidate': count})
                if value >= top - 1e-12:
                    break
    return best


def bvbrc_blast_best(summary, records):
    """``(ceiling, arguments)`` of ``bvbrc_blast`` over the scope's held sequences with no graded search (the ceiling
    ``ceiling`` gives with ``arguments`` ``None``; the first query on a tie). The arguments are the continuation of the
    query's outstanding search (its query, program, database and resource, and ``until`` ``extracted``: the one commission
    of that query the head's check accepts while it is outstanding; it extracts what the launch started, so its ceiling is
    the search's), or ``None`` when the query has no outstanding search (a new search: its fields are the model's)."""
    standing, limit, best = candidate_standing(records, summary['scope'], held_sources(records)), bvbrc_hit_bound(), None
    for query in (ref for ref in summary['scope']['subject_refs'] if ref in summary['held_sequences']):
        searches = [row for row in summary['bvbrc_searches'] if row['query_ref'] == query]
        if any(row['closed'] for row in searches):
            continue
        products = [candidate for candidate in standing.get(query, {}) if candidate.startswith('product:')]
        value = test_ceiling(standing.get(query, {}), products, 'database_search', unseen=limit, limit=limit)
        if best is None or value > best[0] + 1e-12:
            best = (value, [row for row in searches if row['outstanding']])
    if best is None:
        return (0.0, None)
    value, outstanding = best
    return (value, None if not outstanding else {
        'query_ref': outstanding[0]['query_ref'], 'program': outstanding[0]['program'],
        'database': outstanding[0]['database'], 'resource_id': outstanding[0]['resource_id'], 'until': 'extracted'})


def best_arguments(summary, records, action_type, ctx):
    """The commission that reaches the action's ceiling asked with ``arguments`` ``None`` (``ceiling``), as the arguments a
    decision can name, or ``None`` when no choice of arguments changes the action's ceiling or none can earn
    (``reason``, and the actions whose arguments the ceiling does not distinguish here). For ``bvbrc_blast``: the
    continuation (``until`` ``extracted``) of the outstanding search of the query that reaches the ceiling, when it has one
    (``bvbrc_blast_best``; a new search: ``None``). For ``bvbrc_msa``:
    the query, the search, the candidates (a subset of those admitted) and the sequences per candidate (``msa_best``). For
    ``bvbrc_metacats``: the query and the alignment (``metacats_best``). For ``all_vs_all``: the query, the search, the
    candidates and the sequences per candidate (``all_vs_all_best``)."""
    if action_type == 'bvbrc_blast':
        return bvbrc_blast_best(summary, records)[1]
    if action_type == 'bvbrc_msa':
        return msa_best(summary, records)[1]
    if action_type == 'bvbrc_metacats':
        return metacats_best(summary, records)[1]
    if action_type == 'all_vs_all':
        return all_vs_all_best(summary, records)[1]
    return None


def outcome_pending(summary, records, position):
    """Whether the outcome of unit ``position`` is pending (``method_loop.episode_type``; ``summary`` after the unit): a
    child commission whose child returned parked (``bvbrc_blast``, ``bvbrc_msa`` or ``bvbrc_metacats``: its job launched and
    not extracted, by ``until`` ``launched`` or wound down before the job ended). Its rise (0: nothing is extracted yet) does
    not measure its action and its seconds cover only the launch, so the forecast controller learns neither from it and
    its ledger row is resolved ``pending``; the commission that continues the job (``until`` ``extracted``) is the
    observation. A tool unit ends its work in the unit and is never pending."""
    row = summary['units'][position]
    return row['kind'] == 'child' and row['parked']


# What ``ceiling`` (and the library's ``test_ceiling``, ``msa_test_ceiling``, ``metacats_test_ceiling`` and
# ``cluster_test_ceiling`` it calls) means for each action type the head offers. The forecast controller learns each
# action's share of its ceiling only from ledger rows recorded under the same credit definition and the same version of
# that action's ceiling (``yield_estimator.py``), so change an action's version whenever its ceiling's derivation changes,
# and only that action's. Every offered action has one; an action without one raises
# (``forecast_definition_missing_for_action``). ``all_vs_all`` v2: the cluster test's vertex bound minus the dataset best
# (``cluster_test_ceiling``, commit b95a11691); every other action keeps the derivation it had under v1.
CEILING_VERSIONS = {'reason': 'a101_ceiling_v1', 'execute_selected_tool': 'a101_ceiling_v1',
                    'pairwise_blast': 'a101_ceiling_v1', 'hmmer_profile_scan': 'a101_ceiling_v1',
                    'bvbrc_blast': 'a101_ceiling_v1', 'bvbrc_msa': 'a101_ceiling_v1',
                    'bvbrc_metacats': 'a101_ceiling_v1', 'all_vs_all': 'a101_ceiling_v3'}


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
    * ``all_vs_all``: derived from the current state, as a proved and tight maximum (the proof is in
      ``differential_credit.cluster_test_ceiling``). The cluster test of the commission's committed clustering measures each named
      candidate once, its value ``w`` x the share of its sequences in the target's cluster, in [0, ``w``]; appended last, its own
      test credit (the entries it admits plus ``|v_a - v_b|`` over the listed pairs) is convex on that box and largest at a vertex:
      with ``l`` listed and ``u`` unlisted candidates named, ``w (u + floor(l^2 / 4))`` (half the listed at ``w``, half at 0). Its
      dataset is the commission's search: all the clusterings of one dataset earn one test's credit together, the largest (the
      owner: "You only can earn one credit for one dataset - you can improve a clustering to earn more, but you cannot
      replicate"), so the ceiling is that vertex bound minus the dataset's best test credit so far, floored at 0
      (``dataset_test_ceiling``; ``dataset_bests``). A commission identical to one already commissioned or already graded (the
      search, the candidates, the sequences per candidate) earns 0. With ``arguments`` ``None``: the largest over every
      commission the head's check would accept now (``all_vs_all_best``), and ``best_arguments`` names that commission.
    * ``bvbrc_metacats``: derived from the current state, as a proved maximum (proof in
      ``differential_credit.metacats_test_ceiling``). The owner: "It's wrong that it has no credit. i told you it gains credit by
      confirming conserved sites in comparison to a gene family." A report of the named alignment measures the alignment's group
      candidates; a candidate's value is ``SITE_WEIGHT`` x (its matched conserved sites of that alignment confirmed by the report
      and by no earlier held report), so at most ``SITE_WEIGHT`` x (its matched sites there not yet confirmed:
      ``candidate_measurements.unconfirmed_matched_sites``) x the msa sheet's weight, and the rise is at most the vertex maximum
      over those bounds. An alignment the head's check refuses (a report of it held: the reuse check; or commissioned and not
      continued) earns 0. With ``arguments`` ``None``: the largest over the alignments a commission may name now
      (``metacats_best``), and ``best_arguments`` names that commission.
    * ``hmmer_profile_scan``: the scan of the target ``query_ref`` against the profile database ``database`` reports
      each family at most once, so it measures at most as many families as the database holds profiles (``model_count``
      of the manifest the setting ``profile_databases`` names; the family's own reporting threshold only lowers the
      number): at most that many candidates (``profile_family:<accession>``), any on the list or new.
    * ``execute_selected_tool``: ``UNBOUNDED``: a selected registry tool can import a search report of any size and its
      arguments fix no bound on the candidates it measures.

    An action the head's request checks would refuse as a repeat earns nothing, so its ceiling is 0: a pairwise
    comparison already held (``held_comparisons``), a profile scan of the same query and database already held
    (``held_profile_scans``), a search of the same query, program and database already graded (a closed search of
    ``bvbrc_searches``; an outstanding one can still be continued and keeps its ceiling: the continuation, ``until``
    ``extracted``, extracts what the launch started, so its ceiling is the search's, and ``best_arguments`` names it)."""
    if action_type == 'reason':
        return 0.0
    if action_type == 'bvbrc_metacats':
        if arguments is None:
            return metacats_best(summary, records)[0]
        return metacats_value(summary, records, arguments['alignment_ref'])
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
            return all_vs_all_best(summary, records)[0]
        if (arguments['search_ref'], sorted(arguments['candidates'])) in all_vs_all_commission_keys(summary):
            return 0.0
        return all_vs_all_value(standing, dataset_bests(records, scope, held_sources(records)), arguments['query_ref'],
                                arguments['search_ref'], arguments['candidates'])
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
