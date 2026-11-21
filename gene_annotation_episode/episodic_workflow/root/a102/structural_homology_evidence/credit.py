"""Credit: the owner's differential credit over the candidate annotations the head holds structural evidence for (the rule of
2026-11-20, as A101 counts it; A102 has its own library copy of the arithmetic).

``credit(summary, records)`` is ``candidate_table(...)['credit']`` (library: ``grading/structural_homology_evidence/
candidate_measurements.py``, which reads the held graded sources in the order the head obtained them and calls
``differential_credit``): a candidate annotation with positive evidence is admitted and earns its score; applying a test the
candidates already on the list have all undergone earns the sizes of the differences of their moves; a repeat changes
nothing, so it earns nothing. The sum has no fixed maximum; every action the head offers has a ceiling (``ceiling``), so the
credit's controller is the forecast controller (``yield_estimator.py``). ``A102DifferentialCredit`` is its definition record.
A child's credit is information in the summary and is never added."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    candidate_standing, candidate_table, held_sources)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    SHEET_WEIGHT, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ROUTE_KIND)

# THE MOST CANDIDATES ONE SEARCH CAN MEASURE: 1000, one product per hit at most. SOURCE: the Foldseek README (retained copy
# ``runs/a102_measure_check/foldseek_README.md``, line 161) gives the option ``--max-seqs`` ("the amount of prefilter handed to
# alignment ... default: 1000"), the most results one query sequence keeps. The Foldseek server's documentation (retained at
# ``episode_support/forms/application_service_specs/original/StructureSearch_server_api_docs.html``) names no limit on the hits
# of a result, and the per-database search parameters of the server (``params.Search`` of its ``worker.go``) are not published,
# so that the server leaves the default is OBSERVED, not documented: the stored results of the live tickets hold 976 hits
# (tmalign, afdb-swissprot, ``runs/a102_service_probe/foldseek/result_tmalign_afdb_swissprot_cspa.json``), 548 (tmalign,
# pdb100, ``result2_tmalign_0.json``) and 982, 481 and 549 (3diaa, afdb-swissprot, cath50, pdb100, ``result_0.json``): the
# largest is 982, below 1000. A result with more hits than this would earn more than its ceiling and the run would end with
# ``episode_ceiling_exceeded``: the figure is then wrong and is to be changed with its ``CEILING_VERSIONS`` entry.
HIT_BOUND = 1000
SLOT = 'structure_search'
FAMILY = 'structure_search'
OBTAIN = 'obtain_one'


class A102DifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'a102_differential_credit', 'version': 'a102_differential_credit_v1', 'axis': 'A102',
                'measurement': 'index_b_of_each_hit_of_one_structure_search_from_the_aligned_pairs_after_superposition',
                'candidates': 'product_from_the_uniprot_name_of_the_hit',
                'test': 'one_graded_source_structure_search_foldseek_tmalign_database_at_source',
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
    """The differential credit of the held graded sources over the commissioned scope: counted as soon as a graded sheet is
    held. No model step stands between a graded result and its being counted. A child's credit is never added."""
    return held_candidate_table(summary, records)['credit']


def model_sha256(summary, model_ref):
    """The SHA-256 of the held model row ``model_ref`` (``OBTAIN``: none, the child obtains one)."""
    return None if model_ref == OBTAIN else next(row['settings']['sha256'] for row in summary['model_rows']
                                                 if row['id'] == model_ref)


def outstanding(summary, query, database, resource_id=None):
    """The outstanding job (parked: launched, no closure held, not shown failed or lost) of the search of ``query`` in
    ``database`` (on ``resource_id`` when given), or ``None``."""
    return next((job for job in summary['structure_search_jobs']
                 if job['outstanding'] and job['identity']['query_ref'] == query and job['identity']['database'] == database
                 and (resource_id is None or job['resource_id'] == resource_id)), None)


def refused(summary, query, database, model_ref):
    """Whether the head's check refuses this commission as a repeat (``task.check_structure_search``): a search of the same
    query, database and model is graded, or the same commission was made and no outstanding job of it is continued."""
    sha = model_sha256(summary, model_ref)
    if sha is not None and [database, sha] in summary['held_searches'].get(query, []):
        return True
    return (query, database, model_ref) in commissioned(summary) and outstanding(summary, query, database) is None


def commissioned(summary):
    """The ``(query, database, model)`` of the commissions of ``structure_search`` this episode made (the model as a held row
    or ``OBTAIN``)."""
    return [(row['arguments']['query_ref'], row['arguments']['database'], row['arguments']['model_ref'])
            for row in summary['units'] if row['kind'] == 'child' and row['slot'] == SLOT]


def search_value(standing, query):
    """The proved maximum of one search of ``query`` that the head's check accepts (see ``ceiling``)."""
    held = standing.get(query, {})
    products = [candidate for candidate in held if candidate.startswith('product:')]
    return test_ceiling(held, products, FAMILY, unseen=HIT_BOUND, limit=HIT_BOUND)


def queries(summary):
    """The protein sequences of the scope: what a search may be commissioned for."""
    return [ref for ref in summary['scope']['subject_refs'] if summary['held_sequences'].get(ref) == 'protein']


def open_pairs(summary):
    """``(query, database)`` of the searches that can still be commissioned: not graded with any model and not commissioned
    with any model and left (no outstanding job of it)."""
    graded = {(row['query_ref'], row['database']) for row in summary['graded_searches']}
    left = {(query, database) for query, database, _ in commissioned(summary)}
    return [(query, database) for query in queries(summary) for database in DATABASES
            if (query, database) not in graded
            and ((query, database) not in left or outstanding(summary, query, database) is not None)]


def best_arguments(summary, records, action_type, ctx):
    """The commission that reaches the action's ceiling asked with ``arguments`` ``None`` (``ceiling``), as the arguments a
    decision can name, or ``None`` when no choice changes it or none can earn. For ``structure_search``: the continuation
    (``until`` ``extracted``) of the outstanding job when a job is parked (the one commission of that search the head's check
    accepts while it is outstanding: it extracts what the launch started, so its ceiling is the search's); else, with a
    model of a query held, the first database not yet searched with that model; else ``None`` (a search with no model held
    is the model's own commission)."""
    if action_type != SLOT:
        return None
    parked = next((job for job in summary['structure_search_jobs'] if job['outstanding']), None)
    if parked is not None:
        identity = parked['identity']
        return {'query_ref': identity['query_ref'], 'database': identity['database'], 'resource_id': parked['resource_id'],
                'model_ref': next((row['id'] for row in summary['model_rows']
                                   if row['settings']['sha256'] == identity['model_sha256']), OBTAIN),
                'until': 'extracted'}
    resource = next((item['resource_id'] for item in ctx.services['job_access'].read('resources')
                     if item['kind'] == ROUTE_KIND), None)
    for row in summary['model_rows']:
        query = row['query_ref']
        for database in DATABASES:
            if query in queries(summary) and resource is not None and not refused(summary, query, database, row['id']):
                return {'query_ref': query, 'database': database, 'resource_id': resource, 'model_ref': row['id'],
                        'until': 'extracted'}
    return None


def outcome_pending(summary, records, position):
    """Whether the outcome of unit ``position`` is pending (``method_loop.episode_type``; ``summary`` after the unit): a child
    commission whose child returned parked (its job launched and not extracted, by ``until`` ``launched`` or wound down
    before the job ended). Its rise (0: nothing is extracted yet) does not measure its action and its seconds cover only the
    launch, so the forecast controller learns neither from it and its ledger row is resolved ``pending``; the commission that
    continues the job (``until`` ``extracted``) is the observation."""
    row = summary['units'][position]
    return row['kind'] == 'child' and row['parked']


# What ``ceiling`` means for each action type the head offers. The forecast controller learns an action's share of its
# ceiling only from ledger rows recorded under the same credit definition and the same version of that action's ceiling
# (``yield_estimator.py``): change an action's version whenever its ceiling's derivation changes, and only that action's.
CEILING_VERSIONS = {'structure_search': 'a102_ceiling_v1'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (with
    ``arguments`` ``None``: the most over every arguments the action type can take now).

    The credit is, per target, the sum of the entry scores of the candidates and of the differentials
    (``differential_credit``). A unit adds at most one graded source, which is one test appended after the earlier ones. A
    candidate's value in a test is the family's weight times its mean index B of the test, in [0, w] (B lies in [0, 1]), so
    the test moves a score by at most ``w`` and ``differential_credit.test_ceiling`` bounds what the one test can add: a pair of
    candidates on the list that the test measures earns at most ``w``; a candidate it admits earns at most its entry, ``w``; a
    test that measures one listed candidate and admits none earns 0.

    * ``structure_search``: the one test of one search measures the product candidates of its hits: the ones already on the
      list (``product:`` standing) and at most ``HIT_BOUND`` in all (the most hits one search of the server returns; the
      figure and its source are in the comment of ``HIT_BOUND``: the Foldseek default ``--max-seqs`` 1000, observed results
      at most 982; the server's own override is not published), each hit naming at most one product. The ceiling is that
      bound of ``test_ceiling`` with ``unseen`` and ``limit`` ``HIT_BOUND``. A commission the head's check would refuse as a
      repeat earns 0 (``refused``: a search of the same query, database and model graded, or commissioned and not
      continued). The resume of a parked job (the same fields, ``until`` ``extracted``) is not a repeat and has the
      search's ceiling, which is what the launch started. With ``arguments`` ``None``: the largest over the queries with a
      database not yet searched (``open_pairs``), and ``best_arguments`` names that commission when it can be stated."""
    if action_type != SLOT:
        raise ValueError('a102_ceiling_not_derived_for_action_type:' + action_type)
    standing = candidate_standing(records, summary['scope'], held_sources(records))
    if arguments is None:
        return max((search_value(standing, query) for query, _ in open_pairs(summary)), default=0.0)
    if refused(summary, arguments['query_ref'], arguments['database'], arguments['model_ref']):
        return 0.0
    return search_value(standing, arguments['query_ref'])
