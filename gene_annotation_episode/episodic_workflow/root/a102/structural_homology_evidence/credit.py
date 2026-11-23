"""Credit: the owner's differential credit over the candidate annotations the head holds structural evidence for (the rule of
2026-11-20, as A101 counts it; A102 has its own library copy of the arithmetic).

``credit(summary, records)`` is ``candidate_table(...)['credit']`` (library: ``grading/structural_homology_evidence/
candidate_measurements.py``, which reads the held graded sources in the order the head obtained them and calls
``differential_credit``): a candidate annotation with positive evidence is admitted and earns its score; a test earns the size of the difference of the
moves of the TWO highest-scored candidates already on the list that it measures (the top two, whatever their kind), and
nothing for any other pair; a repeat changes nothing, so it earns nothing. The sum has no fixed maximum; every action the head offers has a ceiling (``ceiling``), so the
credit's controller is the forecast controller (``yield_estimator.py``). ``A102DifferentialCredit`` is its definition record.
A child's credit is information in the summary and is never added."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    candidate_standing, candidate_table, held_sources)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    SHEET_WEIGHT, bound_partner_test_ceiling, ligand_transplant_test_ceiling, rna_family_scan_test_ceiling,
    partner_cofolding_test_ceiling, rna_structure_agreement_test_ceiling, site_test_ceiling, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    SITE_SOURCES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.ligand_transplants import (
    ORIGIN as TRANSPLANT_ORIGIN)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    LIGAND_COUNT, ROUTE_KIND as COFOLDING_ROUTE_KIND)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_contacts import (
    DATABASE as PARTNER_DATABASE)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.rna_structure_agreement import (
    MINIMUM_FAMILIES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.site_correspondence import (
    UNIPROT_NUMBERED)
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
# ``episode_ceiling_exceeded``: the figure is then wrong and is to be changed with its ``CEILINGS`` entry.
HIT_BOUND = 1000
SLOT = 'structure_search'
COFOLDING_SLOT = 'partner_cofolding'
SITE_TOOL = 'site_correspondence'
PARTNER_TOOL = 'partner_contacts'
TRANSPLANT_TOOL = 'ligand_transplants'
RNA_SCAN_TOOL = 'rna_family_scan'
RNA_AGREEMENT_TOOL = 'rna_structure_agreement'
FAMILY = 'structure_search'
OBTAIN = 'obtain_one'


class A102DifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'a102_differential_credit', 'version': 'a102_differential_credit', 'axis': 'A102',
                'measurement': 'index_b_of_each_hit_of_one_structure_search_from_the_aligned_pairs_after_superposition',
                'site_measurement': 'mean_e_of_the_hits_with_sites_e_is_b_times_the_mean_residue_score_of_class_match_times_kernel',
                'candidates': 'product_from_the_uniprot_name_of_the_hit',
                'partner_measurement': ('mean_e_of_the_hits_with_a_functional_partner_per_product_and_mean_e_of_the_hits_bound_to_'
                                        'each_partner_e_is_b_times_the_mean_residue_score_of_the_partners_contact_residues'),
                'partner_candidates': 'ligand_chemical_component_id_and_nucleic_acid_dna_or_rna_of_the_solved_hit_chains',
                'transplant_measurement': 'value_of_the_best_alphafill_transplant_of_each_ligand_fit_times_no_clash',
                'transplant_candidates': 'ligand_chemical_component_id_of_the_solved_donor_of_each_non_additive_transplant',
                'rna_scan_measurement': 'value_of_the_best_hit_of_each_rfam_family_x_squared_over_one_plus_x_squared_x_is_bits_over_ga',
                'rna_scan_candidates': 'rfam_family_accession_of_each_hit_of_the_cmscan_over_the_covariance_database',
                'rna_agreement_measurement': 'canonical_pairs_over_consensus_pairs_of_the_cmalign_span_of_each_scan_family',
                'cofolding_measurement': 'mean_over_five_samples_of_iptm_of_the_target_with_each_ligand_zero_for_a_clashing_sample',
                'cofolding_candidates': 'the_ligand_candidates_the_head_already_holds_none_is_admitted_by_the_test',
                'test': ('one_graded_source_structure_search_foldseek_tmalign_database_at_source_or_site_correspondence_'
                         'site_source_at_source_or_site_correspondence_partner_contacts_at_source_or_bound_partner_pdb100_at_source_or_ligand_transplant_alphafill_at_source'
                         '_or_rna_family_scan_database_at_source_or_rna_structure_agreement_rfam_at_source'
                         '_or_partner_cofolding_chai1_at_source'),
                'sheet_weights': dict(SHEET_WEIGHT),
                'score': 'sum_over_subscoring_sheets_of_weight_times_sum_of_mean_value_in_test_of_that_kind',
                'admission': 'first_value_above_zero',
                'entry': 'score_after_the_admitting_test_only',
                'differential': ('abs_difference_of_the_score_moves_in_a_test_of_the_top_two_candidates_listed_before_the_test_that_the_test_measures_'
                                 'ties_by_candidate_key_nothing_for_any_other_pair_none_with_fewer_than_two'),
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


def held_ligands(summary):
    """Per protein sequence of the scope, the ligand candidates the head holds (``ligand:<id>``, the leading one first): the
    candidates a ``partner_cofolding`` commission may name (``internal_summary`` reads them from the candidate table)."""
    return {query: summary['held_ligands'].get(query, []) for query in queries(summary)}


def cofolded_ligands(summary):
    """Per target, the ligand names (``ligand:<id>``) already co-folded for it: the graded ``partner_cofolding`` sheets the head
    holds (``partner_cofolding.graded_rows``, read in ``internal_summary``)."""
    found = {}
    for row in summary['cofolding_test_rows']:
        found.setdefault(row['query_ref'], set()).update(row['ligands'])
    return found


def available_ligands(summary, query):
    """The ligand candidates of ``query`` a ``partner_cofolding`` commission may name now: held and not co-folded for it before."""
    done = cofolded_ligands(summary).get(query, set())
    return [ligand for ligand in held_ligands(summary).get(query, []) if ligand not in done]


def offered_cofolding_queries(summary):
    """The protein sequences of the scope that hold at least ``LIGAND_COUNT[0]`` ligand candidates not yet co-folded for them."""
    return [query for query in queries(summary) if len(available_ligands(summary, query)) >= LIGAND_COUNT[0]]


def commissioned_cofoldings(summary):
    """The ``(query, frozenset of ligands)`` of the commissions of ``partner_cofolding`` this episode made."""
    return [(row['arguments']['query_ref'], frozenset(row['arguments']['ligands']))
            for row in summary['units'] if row['kind'] == 'child' and row['slot'] == COFOLDING_SLOT]


def outstanding_cofolding(summary, query, ligands, resource_id=None):
    """The outstanding job of the co-folding of ``query`` with exactly ``ligands`` (on ``resource_id`` when given), or ``None``."""
    return next((job for job in summary['partner_cofolding_jobs']
                 if job['outstanding'] and job['identity']['query_ref'] == query
                 and set(job['identity']['ligands']) == set(ligands)
                 and (resource_id is None or job['resource_id'] == resource_id)), None)


def cofolding_refused(summary, query, ligands):
    """Whether the head's check refuses this commission as a repeat (``task.check_partner_cofolding``): a ligand of it co-folded
    for the query before, or the same set commissioned and no outstanding job of it continued."""
    if set(ligands) & cofolded_ligands(summary).get(query, set()):
        return True
    return (query, frozenset(ligands)) in commissioned_cofoldings(summary) and outstanding_cofolding(summary, query, ligands) is None


def cofolding_value(summary, standing, query, ligands):
    """The proved maximum of one ``partner_cofolding`` unit of ``query`` with ``ligands`` (see ``ceiling``)."""
    return partner_cofolding_test_ceiling(standing.get(query, {}), ligands)


def search_value(standing, query):
    """The proved maximum of one search of ``query`` that the head's check accepts (see ``ceiling``)."""
    held = standing.get(query, {})
    products = [candidate for candidate in held if candidate.startswith('product:')]
    return test_ceiling(held, products, FAMILY, unseen=HIT_BOUND, limit=HIT_BOUND)


def queries(summary):
    """The protein sequences of the scope: what a search may be commissioned for."""
    return [ref for ref in summary['scope']['subject_refs'] if summary['held_sequences'].get(ref) == 'protein']


def rna_queries(summary):
    """The RNA sequences of the scope: what an RNA family scan may be requested for (a protein target is offered neither RNA tool,
    an RNA target none of the protein tools)."""
    return [ref for ref in summary['scope']['subject_refs'] if summary['held_sequences'].get(ref) == 'rna']


def scanned_targets(summary):
    """The targets that hold an RNA family scan (``candidate_measurements.held_rna_scans``, read in ``internal_summary``)."""
    return {target for target, refs in summary['held_rna_scans'].items() if refs}


def unscanned_queries(summary):
    """The RNA sequences of the scope not yet scanned: what an ``rna_family_scan`` request may name."""
    scanned = scanned_targets(summary)
    return [ref for ref in rna_queries(summary) if ref not in scanned]


def agreed_scans(summary):
    """The scan source references whose ``rna_structure_agreement`` this episode holds (``candidate_measurements.
    held_rna_agreements``, read in ``internal_summary``)."""
    return {ref for refs in summary['held_rna_agreements'].values() for ref in refs}


def offered_agreement_scans(summary):
    """The scan source references an ``rna_structure_agreement`` request may name now, in the order of the held scans: a scan of an
    RNA sequence of the scope that lists at least two families and is not yet tested."""
    targets, agreed = rna_queries(summary), agreed_scans(summary)
    return [scan for scan, held in summary['rna_scan_inputs'].items()
            if held['query_ref'] in targets and len(held['families']) >= MINIMUM_FAMILIES and scan not in agreed]


def database_families(settings, database):
    """The number of families of the covariance database ``database`` of the settings (its manifest's ``model_count``)."""
    return json.loads(Path(settings['covariance_databases'][database]).read_text())['model_count']


def open_pairs(summary):
    """``(query, database)`` of the searches that can still be commissioned: not graded with any model and not commissioned
    with any model and left (no outstanding job of it)."""
    graded = {(row['query_ref'], row['database']) for row in summary['graded_searches']}
    left = {(query, database) for query, database, _ in commissioned(summary)}
    return [(query, database) for query in queries(summary) for database in DATABASES
            if (query, database) not in graded
            and ((query, database) not in left or outstanding(summary, query, database) is not None)]


def graded_site_pairs(summary):
    """The ``(search source reference, site source)`` pairs of the site tests this episode holds
    (``candidate_measurements.held_site_tests``, read in ``internal_summary``)."""
    return {tuple(pair) for pairs in summary['held_site_tests'].values() for pair in pairs}


def offered_site_pairs(summary):
    """The ``(search source reference, site source)`` pairs a ``site_correspondence`` request may name now, in the order of the
    graded searches and of ``SITE_SOURCES``: a graded search of a protein sequence of the scope, of a database numbered along the UniProt
    sequence (``site_correspondence.UNIPROT_NUMBERED``: not ``pdb100``, whose hits are numbered along the solved chain), whose raw result and model this
    episode holds (``site_correspondence.search_inputs``), with a site source not yet graded for it. A request of one of these
    passes ``check_site_correspondence_request``."""
    graded, targets = graded_site_pairs(summary), queries(summary)
    return [(search, source) for search, held in summary['search_inputs'].items()
            if held['row']['query_ref'] in targets and held['row']['database'] in UNIPROT_NUMBERED
            and held['result_held'] and held['model_held']
            for source in SITE_SOURCES if (search, source) not in graded]


def analysed_searches(summary):
    """The search source references whose ``partner_contacts`` this episode holds
    (``candidate_measurements.held_partner_analyses``, read in ``internal_summary``)."""
    return {ref for refs in summary['held_partner_analyses'].values() for ref in refs}


def offered_partner_searches(summary):
    """The graded searches a ``partner_contacts`` request may name now, in the order of the graded searches: a ``pdb100`` search of
    a protein sequence of the scope whose raw result, model, hit-metadata product and partner metadata this episode holds
    (``partner_contacts.partner_search_inputs``) and that is not yet analysed."""
    targets, analysed = queries(summary), analysed_searches(summary)
    return [search for search, held in summary['search_inputs'].items()
            if held['row']['query_ref'] in targets and held['row']['database'] == PARTNER_DATABASE
            and held['result_held'] and held['model_held'] and held['metadata_held'] and held['partner_metadata']
            and search not in analysed]


def tested_models(summary):
    """The model references whose ``ligand_transplants`` this episode holds (``candidate_measurements.held_transplant_models``,
    read in ``internal_summary``)."""
    return {ref for refs in summary['held_transplant_models'].values() for ref in refs}


def transplant_models(summary):
    """The held models as the library's check reads them: ``{model row reference: {'origin', 'accession', 'query_ref'}}``."""
    return {row['id']: {'origin': row['settings']['origin'], 'accession': row['settings']['accession'],
                        'query_ref': row['query_ref']} for row in summary['model_rows']}


def offered_transplant_models(summary):
    """The model references a ``ligand_transplants`` request may name now, in the order of the held models: a held model of a
    protein sequence of the scope whose origin is ``alphafold_db`` (it has an accession) and that is not yet tested."""
    targets, tested = queries(summary), tested_models(summary)
    return [row['id'] for row in summary['model_rows']
            if row['query_ref'] in targets and row['settings']['origin'] == TRANSPLANT_ORIGIN and row['id'] not in tested]


def transplant_value(summary, standing, model):
    """The proved maximum of one ``ligand_transplants`` unit of the held model ``model`` (see ``ceiling``)."""
    query = next(row['query_ref'] for row in summary['model_rows'] if row['id'] == model)
    return ligand_transplant_test_ceiling(standing.get(query, {}))


def partner_value(summary, records, standing, search):
    """The proved maximum of one ``partner_contacts`` unit of the held search ``search`` (see ``ceiling``): the first test's
    ``site_test_ceiling`` over the product candidates of the search's own test plus the second test's
    ``bound_partner_test_ceiling`` over the partner candidates the search's entries make possible."""
    (entry,) = source_tool_grading_entries(records, search)
    held = summary['search_inputs'][search]
    candidates = ['product:' + row['product'] for row in entry['grading']['sheet']['candidates'] if row['mean_B'] is not None]
    target = standing.get(held['row']['query_ref'], {})
    return site_test_ceiling(target, candidates) + bound_partner_test_ceiling(target, held['possible_partners'])


def site_value(summary, records, standing, search):
    """The proved maximum of one site test of the held search ``search`` (see ``ceiling``): ``site_test_ceiling`` over the
    product candidates of the search's own test."""
    (entry,) = source_tool_grading_entries(records, search)
    candidates = ['product:' + row['product'] for row in entry['grading']['sheet']['candidates'] if row['mean_B'] is not None]
    return site_test_ceiling(standing.get(summary['search_inputs'][search]['row']['query_ref'], {}), candidates)


def best_arguments(summary, records, action_type, ctx):
    """The commission that reaches the action's ceiling asked with ``arguments`` ``None`` (``ceiling``), as the arguments a
    decision can name, or ``None`` when no choice changes it or none can earn. For ``site_correspondence``: the first offered
    pair (``offered_site_pairs``) of the search whose site test has the largest ceiling (the ceiling does not depend on the site
    source; the first in the fixed order on a tie). For ``structure_search``: the continuation
    (``until`` ``extracted``) of the outstanding job when a job is parked (the one commission of that search the head's check
    accepts while it is outstanding: it extracts what the launch started, so its ceiling is the search's); else, with a
    model of a query held, the first database not yet searched with that model; else ``None`` (a search with no model held
    is the model's own commission)."""
    if action_type in (RNA_SCAN_TOOL, RNA_AGREEMENT_TOOL):
        resource = next((item['resource_id'] for item in ctx.services['job_access'].read('resources') if item['kind'] == 'local'), None)
        if resource is None:
            return None
        if action_type == RNA_AGREEMENT_TOOL:
            scans = offered_agreement_scans(summary)
            return {'scan_ref': scans[0], 'resource_id': resource} if scans else None
        queries_left, databases = unscanned_queries(summary), sorted(ctx.settings['covariance_databases'])
        return {'query_ref': queries_left[0], 'database': databases[0], 'resource_id': resource} if queries_left else None
    if action_type == TRANSPLANT_TOOL:
        models = offered_transplant_models(summary)
        if not models:
            return None
        standing = candidate_standing(records, summary['scope'], held_sources(records))
        return {'model_ref': max(models, key=lambda found: transplant_value(summary, standing, found))}
    if action_type == PARTNER_TOOL:
        standing = candidate_standing(records, summary['scope'], held_sources(records))
        searches = offered_partner_searches(summary)
        if not searches:
            return None
        search = max(searches, key=lambda found: partner_value(summary, records, standing, found))
        resource = next((item['resource_id'] for item in ctx.services['job_access'].read('resources') if item['kind'] == 'local'), None)
        return None if resource is None else {'search_ref': search, 'resource_id': resource}
    if action_type == SITE_TOOL:
        pairs = offered_site_pairs(summary)
        if not pairs:
            return None
        standing = candidate_standing(records, summary['scope'], held_sources(records))
        search, source = max(pairs, key=lambda pair: site_value(summary, records, standing, pair[0]))
        return {'search_ref': search, 'site_source': source}
    if action_type == COFOLDING_SLOT:
        parked = next((job for job in summary['partner_cofolding_jobs'] if job['outstanding']), None)
        if parked is not None:
            return {'query_ref': parked['identity']['query_ref'], 'ligands': list(parked['identity']['ligands']),
                    'resource_id': parked['resource_id'], 'until': 'extracted'}
        resource = next((item['resource_id'] for item in ctx.services['job_access'].read('resources')
                         if item['kind'] == COFOLDING_ROUTE_KIND), None)
        queries_left = offered_cofolding_queries(summary)
        if resource is None or not queries_left:
            return None
        standing = candidate_standing(records, summary['scope'], held_sources(records))
        query = max(queries_left, key=lambda found: cofolding_value(summary, standing, found,
                                                                    available_ligands(summary, found)[:LIGAND_COUNT[1]]))
        return {'query_ref': query, 'ligands': available_ligands(summary, query)[:LIGAND_COUNT[1]], 'resource_id': resource,
                'until': 'extracted'}
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
# ceiling only from ledger rows recorded under the same credit definition and the same name of that action's ceiling
# (``yield_estimator.py``).
CEILINGS = {'structure_search': 'a102_ceiling', 'site_correspondence': 'a102_ceiling',
            'partner_contacts': 'a102_ceiling', 'ligand_transplants': 'a102_ceiling',
            'rna_family_scan': 'a102_ceiling', 'rna_structure_agreement': 'a102_ceiling',
            'partner_cofolding': 'a102_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (with
    ``arguments`` ``None``: the most over every arguments the action type can take now).

    The credit is, per target, the sum of the entry scores of the candidates and of the differentials
    (``differential_credit``). A unit adds at most one graded source, which is one test appended after the earlier ones. A
    candidate's value in a test is the family's weight times its mean index B of the test, in [0, w] (B lies in [0, 1]), so
    the test moves a score by at most ``w`` and the one test earns the entries of the candidates it admits (each at most ``w``)
    plus ONE differential, the difference of the moves of the top two listed candidates it measures (at most ``w``, and only with
    two such candidates); nothing else.

    * ``site_correspondence``: the one site test of a held graded search measures at most the product candidates of that
      search's own test (``mean_B`` not null on its sheet), each with a value in [0, w] (its mean E = B F, E in [0, 1]), and
      the candidates are all listed or unlisted by the search's own test; ``differential_credit.site_test_ceiling`` is the proved
      maximum (``w`` when at least two of the candidates are listed, else 0: the family weight once; the proof is in its
      docstring). A pair already
      graded (``graded_site_pairs``) earns 0: the request check refuses it. With ``arguments`` ``None``: the largest over the
      pairs still offered (``offered_site_pairs``), 0 when none is offered, and ``best_arguments`` names the pair.
    * ``partner_contacts``: one unit appends two tests, in this order. TEST 1 (``site_correspondence:partner_contacts``) measures
      at most the product candidates of the named search's own test, each with a value in [0, w] (its mean E): the bound is
      ``differential_credit.site_test_ceiling`` over them. TEST 2 (``bound_partner:pdb100``) measures partner candidates, which
      are all in the set the search's entries make possible (``partner_contacts.possible_partners``, read from the held hit
      metadata; the unit fails if a file shows another): ``differential_credit.bound_partner_test_ceiling`` (``w (u + 1)`` over that
      set with ``u`` of them unlisted and at least two listed, ``w u`` otherwise; proof in its docstring). Test 1 adds only product candidates, so it changes no partner
      candidate's standing and the two bounds add. A search already analysed earns 0 (the request check refuses it). With
      ``arguments`` ``None``: the largest over the searches still offered (``offered_partner_searches``), 0 when none is offered.
    * ``ligand_transplants``: the one test of one held AlphaFold DB model (``ligand_transplant:alphafill``) measures ligand candidates
      (``ligand:<compound id>``, the non-additive compounds AlphaFill transplants, at most ``ELIGIBLE_COMPOUNDS`` distinct),
      each with a value in (0, w] (the value of its best transplant, fit x no_clash);
      ``differential_credit.ligand_transplant_test_ceiling`` is the proved maximum (``w (2694 + 1)`` with two or more listed ligand
      candidates, else ``w 2694``; proof in its docstring; constant and loose). A model already tested earns 0 (the request check
      refuses it). With ``arguments`` ``None``: the largest over the models still offered (``offered_transplant_models``), 0 when
      none is offered.
    * ``rna_family_scan``: the one test of one scan of an RNA target measures the families of the covariance database
      (``rna_family:<accession>``, each at most once, each with a value below 1 and at least one half), all admitted by this test (no
      other test lists an RNA family before a scan), so no differential:
      ``differential_credit.rna_family_scan_test_ceiling`` is ``w`` times the families of the database (``database_families``:
      the manifest's ``model_count``), and 0 for a target already scanned (the request check refuses it); constant and loose. With
      ``arguments`` ``None``: the largest over the databases of the settings when an RNA target of the scope is not yet scanned,
      else 0. An action that is offered with the ceiling 0 is how an RNA target with nothing left to do ends the episode, as
      ``structure_search`` does for a protein: the controller finds no offered action worth its cost.
    * ``rna_structure_agreement``: the one test of a held scan measures the families that scan lists, all listed already, so it
      admits none and earns one differential at most: ``differential_credit.rna_structure_agreement_test_ceiling``, ``w`` when the
      scan lists at least two families (a scan with fewer is refused by the request check and earns 0), else 0; a scan already tested
      earns 0. With ``arguments`` ``None``: ``w`` when a scan is offered (``offered_agreement_scans``), else 0.
    * ``partner_cofolding``: the one test of one co-folding of a target with two to four of its held ligand candidates measures
      those ligands, all listed already, so it admits none and earns one differential at most:
      ``differential_credit.partner_cofolding_test_ceiling``, ``w`` when at least two of the commissioned ligands are listed, else
      0. A commission the head's check would refuse as a repeat earns 0 (``cofolding_refused``: a ligand of it co-folded for the
      query before, or the same set commissioned and not continued). The resume of a parked job (the same fields, ``until``
      ``extracted``) is not a repeat and has the ceiling of what the launch started. With ``arguments`` ``None``: the largest
      over the queries that hold at least two ligand candidates not yet co-folded (``offered_cofolding_queries``), 0 when none.
    * ``structure_search``: the one test of one search measures the product candidates of its hits: the ones already on the
      list (``product:`` standing) and at most ``HIT_BOUND`` in all (the most hits one search of the server returns; the
      figure and its source are in the comment of ``HIT_BOUND``: the Foldseek default ``--max-seqs`` 1000, observed results
      at most 982; the server's own override is not published), each hit naming at most one product. The ceiling is that
      bound of ``test_ceiling`` with ``unseen`` and ``limit`` ``HIT_BOUND``. A commission the head's check would refuse as a
      repeat earns 0 (``refused``: a search of the same query, database and model graded, or commissioned and not
      continued). The resume of a parked job (the same fields, ``until`` ``extracted``) is not a repeat and has the
      search's ceiling, which is what the launch started. With ``arguments`` ``None``: the largest over the queries with a
      database not yet searched (``open_pairs``), and ``best_arguments`` names that commission when it can be stated."""
    if action_type not in (SLOT, COFOLDING_SLOT, SITE_TOOL, PARTNER_TOOL, TRANSPLANT_TOOL, RNA_SCAN_TOOL, RNA_AGREEMENT_TOOL):
        raise ValueError('a102_ceiling_not_derived_for_action_type:' + action_type)
    if action_type == RNA_SCAN_TOOL:
        if arguments is None:
            return max((rna_family_scan_test_ceiling(database_families(ctx.settings, database), not unscanned_queries(summary))
                        for database in ctx.settings['covariance_databases']), default=0.0)
        return rna_family_scan_test_ceiling(database_families(ctx.settings, arguments['database']),
                                            arguments['query_ref'] in scanned_targets(summary))
    if action_type == RNA_AGREEMENT_TOOL:
        scans = summary['rna_scan_inputs']
        if arguments is None:
            return max((rna_structure_agreement_test_ceiling(len(scans[scan]['families'])) for scan in offered_agreement_scans(summary)),
                       default=0.0)
        if arguments['scan_ref'] in agreed_scans(summary):
            return 0.0
        return rna_structure_agreement_test_ceiling(len(scans[arguments['scan_ref']]['families']))
    standing = candidate_standing(records, summary['scope'], held_sources(records))
    if action_type == COFOLDING_SLOT:
        if arguments is None:
            return max((cofolding_value(summary, standing, query, available_ligands(summary, query)[:LIGAND_COUNT[1]])
                        for query in offered_cofolding_queries(summary)), default=0.0)
        if cofolding_refused(summary, arguments['query_ref'], arguments['ligands']):
            return 0.0
        return cofolding_value(summary, standing, arguments['query_ref'], arguments['ligands'])
    if action_type == TRANSPLANT_TOOL:
        if arguments is None:
            return max((transplant_value(summary, standing, model) for model in offered_transplant_models(summary)), default=0.0)
        if arguments['model_ref'] in tested_models(summary):
            return 0.0
        return transplant_value(summary, standing, arguments['model_ref'])
    if action_type == PARTNER_TOOL:
        if arguments is None:
            return max((partner_value(summary, records, standing, search) for search in offered_partner_searches(summary)),
                       default=0.0)
        if arguments['search_ref'] in analysed_searches(summary):
            return 0.0
        return partner_value(summary, records, standing, arguments['search_ref'])
    if action_type == SITE_TOOL:
        if arguments is None:
            return max((site_value(summary, records, standing, search) for search, _ in offered_site_pairs(summary)), default=0.0)
        if (arguments['search_ref'], arguments['site_source']) in graded_site_pairs(summary):
            return 0.0
        return site_value(summary, records, standing, arguments['search_ref'])
    if arguments is None:
        return max((search_value(standing, query) for query, _ in open_pairs(summary)), default=0.0)
    if refused(summary, arguments['query_ref'], arguments['database'], arguments['model_ref']):
        return 0.0
    return search_value(standing, arguments['query_ref'])
