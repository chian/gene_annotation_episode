"""The three tools of the ``all_vs_all`` child of the A101 head, as plain library functions that the child's actions call.

The commission: the target, a held graded BV-BRC search of it, the product candidates (at least two), ``per_candidate``
(sequences of each) and the inflations the clustering may use. The model fills out one JSON for a tool; ONE deterministic
check (``check_prepare``, ``check_blast``, ``check_cluster``) returns the things to fix, or the unit runs. Every tool runs
in one unit through the existing local inspection point (``execute_on_local_resource``), in a job folder of the run's
local resource, and keeps its product as a labelled data product (``records/data_products.py``). A unit's ``graded_refs`` (what
the child returns) are only its labelled products and, for the committed clustering, the source and its grading: the jobs'
ledger rows, the prepared-data row, the plans, the driver, the staged graph and the files the jobs left (the database's
component files, the raw report, receipts, logs) stay in the child, which is the only one that reads them.

1. ``prepare_database``: the SET is the target and, for each chosen candidate, its hits by the head's own selection rule
   (``bvbrc_msa_alignment.search_rows`` and ``plan_rows``: highest value in the search, one per distinct ``aa_sequence_md5``,
   the first ``per_candidate``). The hit sequences are fetched once, by md5, through ``sequences_by_md5`` (the public BV-BRC
   data service: no login, batches of 100, 10 s apart) and kept with the target as a ``protein_sequences`` product with
   PLAIN ids (``target``, ``r1``, ``r2`` ...: the code-side map ``set_members`` gives each id its candidate and accession).
   ``makeblastdb`` then builds the database through the existing preparation (``blast_preparation_run.prepare_locally``:
   ``compile_preparation``, the job, the receipt read, the prepared-data record) and the files it wrote (everything under
   ``db/``) are packed, in the same unit, into ONE TAR artifact: the ``blast_protein_database`` product.
2. ``all_vs_all_blast``: REQUIRES a held ``blast_protein_database`` product (``require_product``). Its archive and the set are
   staged into a new job folder, the driver (``all_vs_all_driver``) unpacks the archive there and runs ``blastp`` of every
   sequence of the set against the database (E-value 10, BLAST's default, so weak relatives are kept and the matrix is as
   complete as BLAST makes it; ``max_target_seqs`` the size of the set, so no pair is truncated). The report is read by
   the existing ``blast_all_vs_all_graph.parse_report`` and ``build_edges`` (best alignment of each ordered pair) and checked by
   its ``completeness`` (every sequence found itself: otherwise the run is a failure, never "no relatives"). The pairwise
   matrix of BIT SCORES (``cluster_sheet``: why bit scores) is the ``sequence_similarity_matrix`` product.
3. ``cluster`` (a TRY): REQUIRES a held ``sequence_similarity_matrix`` product. Its weights are the score ratio
   (``cluster_sheet.score_ratio_graph``) under the contrast the model chose, clustered by ``mcl`` (``cluster_sheet``: why MCL, and the
   tuning) at the inflation the model chose. A try is a working result: its clusters
   are a ``sequence_clusters`` product (a partition already held is reported as the same clustering, not a second product) and the
   model is shown controlled facts of it (``cluster_sheet.cluster_facts``). Nothing is graded and nothing reaches the head's credit.
   Before the first try the model is shown the facts of the matrix's score ratios (``held_matrix_facts``).
4. ``commit_clustering``: REQUIRES a held ``sequence_clusters`` product (``committable``): the clustering is graded into the cluster sheet
   (``cluster_sheet.grade_clustering``) as a source of provider ``all_vs_all``: the graded test the head reads.

Settings (``ctx.settings``): ``blast_executable_directory`` (``makeblastdb``, ``blastdbcmd``, ``blastp``),
``mcl_executable_directory`` (``mcl``) and ``python_executable``."""
import hashlib
import inspect
import io
import json
import os
import tarfile
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    DATABASE_PREFIX)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_all_vs_all_graph import (
    REPORT_FIELDS, build_edges, completeness, parse_report)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.cluster_sheet import (
    EDGE_WEIGHT, INFLATIONS, METHOD, TARGET_ID, CONTRASTS, abc_text, cluster_facts, contrast_graph, contrast_undefined, grade_clustering,
    matrix_facts, parse_clusters, score_ratio_graph, with_singletons)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence.blast_preparation_run import (
    prepare_locally)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import (
    products, record_product, require_product)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_driver)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_hit_metadata import (
    sequences_by_md5)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    MINIMUM_CANDIDATES, PER_CANDIDATE_RANGE, plan_rows, search_rows)

CHILD = 'all_vs_all'
PROVIDER = 'all_vs_all'
EVALUE = 10
DB_VERSION = 5
SET_FILE, ARCHIVE_FILE, PLAN_FILE, DRIVER_FILE = 'set.fasta', 'database.tar', 'plan.json', 'driver.py'
REPORT_FILE, GRAPH_FILE, CLUSTERS_FILE = 'graph.tsv', 'graph.abc', 'clusters.txt'
DRIVER_SOURCE = Path(inspect.getsourcefile(all_vs_all_driver)).read_bytes()
SET_KIND, DATABASE_KIND, MATRIX_KIND, CLUSTERS_KIND = ('protein_sequences', 'blast_protein_database',
                                                       'sequence_similarity_matrix', 'sequence_clusters')
BLAST_PROGRAMS = ('makeblastdb', 'blastdbcmd')
TOOLS = ('prepare_database', 'all_vs_all_blast', 'cluster', 'commit_clustering')
HOLD_REASONS = ('a_step_failed_and_cannot_be_retried', 'every_step_is_done')
OWN_FAILURE_CODES = ('sequence_not_returned_by_the_service', 'a_sequence_did_not_find_itself', 'blastp_exit_nonzero',
                     'mcl_exit_nonzero', 'job_not_accepted', 'job_not_fetched', 'failed', 'incomplete')


# -- the set ---------------------------------------------------------------------------------------------------------
def set_members(reader, commission, per_candidate):
    """The members of the set in file order: the target (id ``target``) and the plan's hits (ids ``r1``..., in the order of
    the candidates, each candidate's hits by value): ``{'id', 'candidate' (None for the target), 'accession', 'md5',
    'length'}``. Deterministic from the held search, so every record that needs the map recomputes it."""
    rows = search_rows(reader, {'subject_refs': [commission['query_ref']]}, commission['search_ref'])
    plan = plan_rows(rows, commission['candidates'], per_candidate)
    target = reader.get_artifact(reader.get(commission['query_ref'])['sequence_ref']).decode('ascii').strip().upper()
    return [{'id': TARGET_ID, 'candidate': None, 'accession': None, 'md5': hashlib.md5(target.encode('ascii')).hexdigest(),
             'length': len(target)},
            *({'id': 'r' + str(index), 'candidate': row['candidate'], 'accession': row['accession'], 'md5': row['md5'],
               'length': row['aa_length']} for index, row in enumerate(plan, 1))]


def set_settings(commission, per_candidate):
    """The settings of the set's products (closed JSON): the reuse keys."""
    return {'child': CHILD, 'candidates': sorted(commission['candidates']), 'per_candidate': per_candidate}


def _used(reader, commission):
    """What every product of the commission used, known before anything is fetched: the target's sequence artifact and the
    search source."""
    return [reader.get(commission['query_ref'])['sequence_ref'], commission['search_ref']]


# -- the checks (the things to fix; empty means the call can run) ------------------------------------------------------
def _resource_problems(call, resources):
    if call['resource_id'] not in resources:
        return [{'code': 'resource_not_bound', 'field': 'resource_id'}]
    if resources[call['resource_id']] != 'local':
        return [{'code': 'resource_not_local', 'field': 'resource_id'}]
    return []


def _programs(directory, names):
    return [{'code': 'program_missing', 'field': 'settings', 'detail': name} for name in names
            if not os.access(Path(directory) / name, os.X_OK)]


def check_prepare(call, *, commission, per_candidate, reader, resources, blast_directory, python):
    """The things to fix in a ``prepare_database`` call (``resource_id``): the resource is a bound local one; the set the
    commission gives has at least two sequences; the BLAST programs and the interpreter exist."""
    problems = _resource_problems(call, resources)
    if len(set_members(reader, commission, per_candidate)) < 2:
        problems.append({'code': 'set_needs_two_sequences', 'field': 'commission'})
    problems.extend(_programs(blast_directory, BLAST_PROGRAMS))
    if not os.access(python, os.X_OK):
        problems.append({'code': 'python_missing', 'field': 'settings'})
    return problems


def check_blast(call, *, reader, resources, blast_directory, python):
    """The things to fix in an ``all_vs_all_blast`` call (``resource_id``, ``database_ref``): the resource is a bound local
    one; the database is a held ``blast_protein_database`` product (``require_product``); ``blastp`` and the interpreter
    exist."""
    problems = _resource_problems(call, resources)
    row, problem = require_product(reader, call['database_ref'], DATABASE_KIND)
    if problem is not None:
        problems.append({'code': problem, 'field': 'database_ref'})
    problems.extend(_programs(blast_directory, ('blastp',)))
    if not os.access(python, os.X_OK):
        problems.append({'code': 'python_missing', 'field': 'settings'})
    return problems


def check_cluster(call, *, reader, ids, resources, mcl_directory):
    """The things to fix in a ``cluster`` call (``resource_id``, ``matrix_ref``, ``inflation``, ``contrast``): the resource is a bound
    local one; the matrix is a held ``sequence_similarity_matrix`` product (``require_product``); the inflation and the contrast are of
    the fixed sets; the contrast has a meaning on this matrix (``rescale`` needs ratios below 1); ``mcl`` exists. ``ids`` are the
    set's ids in file order."""
    problems = _resource_problems(call, resources)
    row, problem = require_product(reader, call['matrix_ref'], MATRIX_KIND)
    if problem is not None:
        problems.append({'code': problem, 'field': 'matrix_ref'})
    if call['inflation'] not in INFLATIONS:
        problems.append({'code': 'inflation_not_in_the_fixed_set', 'field': 'inflation', 'choose_from': list(INFLATIONS)})
    if call['contrast'] not in CONTRASTS:
        problems.append({'code': 'contrast_not_in_the_fixed_set', 'field': 'contrast', 'choose_from': list(CONTRASTS)})
    if problem is None and call['contrast'] in CONTRASTS:
        if contrast_undefined(score_ratio_graph(matrix_edges(reader.get_artifact(row['artifact_ref']).decode()), ids),
                              call['contrast']):
            problems.append({'code': 'contrast_undefined_on_this_matrix', 'field': 'contrast'})
    problems.extend(_programs(mcl_directory, ('mcl',)))
    return problems


def committable(reader):
    """The held clusterings, any of which may be committed: the ``sequence_clusters`` products."""
    return [row['id'] for row in products(reader, CLUSTERS_KIND)]


def check_commit(call, *, reader):
    """The things to fix in a ``commit_clustering`` call (``clusters_ref``): the clusters are a held ``sequence_clusters`` product
    (``require_product``)."""
    row, problem = require_product(reader, call['clusters_ref'], CLUSTERS_KIND)
    return [] if problem is None else [{'code': problem, 'field': 'clusters_ref'}]


# -- the settings of the products ------------------------------------------------------------------------------------
def database_settings(commission, per_candidate):
    return {**set_settings(commission, per_candidate), 'tool': 'makeblastdb', 'molecule': 'protein', 'parse_seqids': True,
            'db_version': DB_VERSION}


def matrix_settings(commission, per_candidate):
    return {**set_settings(commission, per_candidate), 'tool': 'blastp', 'evalue': EVALUE,
            'score': 'bit_score_of_the_best_alignment_of_the_ordered_pair'}


def clusters_settings(inflation, contrast):
    return {'method': METHOD, 'inflation': inflation, 'contrast': contrast, 'edge_weight': EDGE_WEIGHT}


def _failed(code, record_refs=(), **facts):
    return {'status': 'failed', 'failure_code': code, 'retryable': False, 'record_refs': list(record_refs),
            'graded_refs': [], **facts}


def _job_failure(ran, name):
    """The failure code of a job that was refused (``job_not_accepted``), not fetched (``job_not_fetched``) or ended with a
    nonzero exit code (``<program>_exit_nonzero``); ``None`` for a job that ended well."""
    if ran['status'] != 'completed':
        return 'job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched'
    return name + '_exit_nonzero' if ran['returncode'] != 0 else None


def _staged_plan(store, argv_plan):
    """The plan and the driver as artifacts the Episode holds, and their names for a job's inputs."""
    plan_ref = store.artifact(json.dumps(argv_plan, sort_keys=True, separators=(',', ':')).encode(), 'application/json')
    driver_ref = store.artifact(DRIVER_SOURCE, 'text/x-python')
    return plan_ref, {PLAN_FILE: plan_ref, DRIVER_FILE: driver_ref}


def pack_database(files, store):
    """The files of the database (the result files under ``db/``), packed in name order into one TAR with fixed
    metadata, so the same database is the same bytes: ``(archive bytes, [names])``."""
    chosen = sorted((item for item in files if item['name'].startswith(DATABASE_PREFIX.split('/')[0] + '/')),
                    key=lambda item: item['name'])
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for item in chosen:
            data = store.get_artifact(item['ref'])
            info = tarfile.TarInfo(item['name'])
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue(), [item['name'] for item in chosen]


# -- the head's side: the options, the held clusterings and the commission check -----------------------------------------
def held_clusterings(reader):
    """The committed (graded) clusterings the reader holds, one per source of provider ``all_vs_all``: the commission's identity
    (``search_ref``, sorted ``candidates``, ``per_candidate``) and the tuning and facts of the clustering."""
    found = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(reader, source['id'])
        sheet = entry['grading']['sheet']
        found.append({'source_ref': source['id'], 'query_ref': source['operand_refs'][0], **sheet['commission'],
                      'inflation': sheet['parameters']['inflation'], 'contrast': sheet['parameters']['contrast'],
                      'cluster_count': sheet['set']['cluster_count'], 'target_cluster_size': sheet['target_cluster']['size']})
    return found


def commission_keys(summary):
    """The identities (search, sorted candidates) of the commissions of this child the head holds: those it made (the units that
    were child commissions of the slot) and those whose clustering it holds graded (``held_clusterings``). The sequences per
    candidate are not part of the identity: the same candidates of the same search, with more or fewer sequences each, are the
    same dataset clustered again, a replicate (the owner: "You only can earn one credit for one dataset - you can improve a
    clustering to earn more, but you cannot replicate"); improving a clustering is the child's tuning of its tries."""
    made = [(row['arguments']['search_ref'], sorted(row['arguments']['candidates']))
            for row in summary['units'] if row['kind'] == 'child' and row['slot'] == CHILD]
    return made + [(row['search_ref'], sorted(row['candidates'])) for row in summary['held_clusterings']]


def check_commission(request, *, scope_subjects, sequences, options, commissioned):
    """The things to fix in the head's commission of this child (``request``: ``query_ref``, ``search_ref``, ``candidates``,
    ``per_candidate``). ``options`` is ``msa_options`` (each held graded BV-BRC search with the product candidates the head admitted
    from it). The conditions: the query
    is a protein sequence of the scope; the search is a held graded search of that query; at least two distinct candidates, each
    admitted from that search; ``per_candidate`` in range. ``commissioned`` is not read here: a set commissioned before is not
    refused (the head's ceiling prices a replicate at 0)."""
    problems = []
    query, search = request['query_ref'], request['search_ref']
    if query not in scope_subjects or sequences.get(query) != 'protein':
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_protein_sequence_of_the_scope',
                         'choose_from': [ref for ref in scope_subjects if sequences.get(ref) == 'protein']})
    option = [item for item in options if item['search_ref'] == search and item['query_ref'] == query]
    if not option:
        problems.append({'field': 'search_ref', 'code': 'search_is_not_a_held_graded_search_of_the_query',
                         'choose_from': [item['search_ref'] for item in options if item['query_ref'] == query]})
    else:
        outside = [name for name in request['candidates'] if name not in option[0]['candidates']]
        if outside:
            problems.append({'field': 'candidates', 'code': 'candidate_is_not_admitted_from_the_search',
                             'not_admitted': outside, 'choose_from': option[0]['candidates']})
    if len(set(request['candidates'])) != len(request['candidates']) or len(request['candidates']) < MINIMUM_CANDIDATES:
        problems.append({'field': 'candidates', 'code': 'two_or_more_distinct_candidates_required'})
    if not PER_CANDIDATE_RANGE[0] <= request['per_candidate'] <= PER_CANDIDATE_RANGE[1]:
        problems.append({'field': 'per_candidate', 'code': 'per_candidate_out_of_range', 'minimum': PER_CANDIDATE_RANGE[0],
                         'maximum': PER_CANDIDATE_RANGE[1]})
    return problems


# -- the units -------------------------------------------------------------------------------------------------------
async def prepare_database(ctx, resource_id, commission, per_candidate):
    """Fetch the set's sequences once, keep the set, build the database and pack it, as one unit. Returns the outcome
    (``status`` ``completed`` or ``failed`` with a ``failure_code``; the records, the jobs' handoff and closure rows and
    the product rows it made)."""
    store = ctx.store
    members = set_members(store, commission, per_candidate)
    target = store.get_artifact(store.get(commission['query_ref'])['sequence_ref']).decode('ascii').strip().upper()
    fetched = sequences_by_md5([row['md5'] for row in members if row['id'] != TARGET_ID])
    absent = sorted({row['md5'] for row in members if row['id'] != TARGET_ID} - set(fetched['sequences']))
    if absent:
        return _failed('sequence_not_returned_by_the_service', missing_count=len(absent))
    text = ''.join('>' + row['id'] + '\n' + (target if row['id'] == TARGET_ID else fetched['sequences'][row['md5']]) + '\n'
                   for row in members)
    used = _used(store, commission)
    with store.transaction():
        set_ref = store.artifact(text.encode('ascii'), 'text/x-fasta')
        sequences = record_product(store, artifact_ref=set_ref, kind=SET_KIND, generated_by=commission['search_ref'],
                                   used=used, settings={**set_settings(commission, per_candidate), 'ids': 'plain',
                                                        'fetched_by': 'bvbrc_feature_sequence_md5'})
    fields = {'kind': 'database_build', 'molecule': 'protein', 'input_ref': set_ref, 'parse_seqids': True,
              'hash_index': False, 'db_version': DB_VERSION}
    prepared = await prepare_locally(ctx, resource_id, fields, executable_directory=ctx.settings['blast_executable_directory'],
                                     python=ctx.settings['python_executable'])
    if prepared['status'] != 'usable':
        return _failed(prepared['failure_code'] or prepared['status'], [set_ref, sequences['id'], *prepared['record_refs']],
                       set_product_ref=sequences['id'])
    archive, names = pack_database(prepared['files'], store)
    with store.transaction():
        archive_ref = store.artifact(archive, 'application/x-tar')
        database = record_product(store, artifact_ref=archive_ref, kind=DATABASE_KIND, generated_by=prepared['handoff_ref'],
                                  used=used, derived_from=[sequences['id']],
                                  settings={**database_settings(commission, per_candidate), 'files': names})
    graded = [set_ref, sequences['id'], archive_ref, database['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False,
            'record_refs': [*graded, *prepared['record_refs']], 'graded_refs': graded,
            'sequence_count': len(members), 'letters': sum(row['length'] for row in members),
            'file_count': len(names), 'database_ref': database['id'], 'set_product_ref': sequences['id']}


async def all_vs_all_blast(ctx, resource_id, database_ref, commission, per_candidate):
    """``blastp`` of every sequence of the set against the prepared database, as one unit; the matrix of bit scores
    (the best alignment of each ordered pair) is kept as a product. A report in which some sequence did not find itself is
    a failure and keeps nothing."""
    store = ctx.store
    database = next(row for row in products(store, DATABASE_KIND) if row['id'] == database_ref)
    set_row = next(row for row in products(store, SET_KIND) if row['id'] == database['derived_from'][0])
    members = set_members(store, commission, per_candidate)
    plan = {'archive': ARCHIVE_FILE, 'argv': [str((Path(ctx.settings['blast_executable_directory']) / 'blastp').resolve()),
                                              '-query', SET_FILE, '-db', DATABASE_PREFIX, '-evalue', str(EVALUE),
                                              '-max_target_seqs', str(len(members)), '-outfmt',
                                              '6 ' + ' '.join(REPORT_FIELDS), '-out', REPORT_FILE]}
    plan_ref, inputs = _staged_plan(store, plan)
    ran = await execute_on_local_resource(
        ctx, resource_id, [ctx.settings['python_executable'], DRIVER_FILE, PLAN_FILE], {}, wait=True,
        inputs={**inputs, SET_FILE: set_row['artifact_ref'], ARCHIVE_FILE: database['artifact_ref']}, name='all_vs_all_blast')
    code = _job_failure(ran, 'blastp')
    if code is not None:
        return _failed(code, [plan_ref])
    handoff, closure = ran['launch']['handoff_ref'], ran['fetch']['closure_ref']
    (report_ref,) = [item['ref'] for item in ran['fetch']['results'] if item['name'] == REPORT_FILE]
    edges = build_edges(parse_report(store.get_artifact(report_ref).decode()))
    status = completeness(edges, [row['id'] for row in members])
    if status['status'] != 'complete':
        return _failed('a_sequence_did_not_find_itself', [plan_ref, report_ref], missing_count=len(status['missing_queries']))
    text = 'query\tsubject\tbit_score\n' + ''.join(
        edge['query'] + '\t' + edge['subject'] + '\t' + format(edge['bitscore'], 'g') + '\n' for edge in edges)
    with store.transaction():
        matrix_ref = store.artifact(text.encode('ascii'), 'text/tab-separated-values')
        matrix = record_product(store, artifact_ref=matrix_ref, kind=MATRIX_KIND, generated_by=handoff,
                                used=[database['artifact_ref']], derived_from=[database['id'], set_row['id']],
                                settings=matrix_settings(commission, per_candidate))
    graded = [matrix_ref, matrix['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False,
            'record_refs': [*graded, plan_ref, report_ref, handoff, closure], 'graded_refs': graded, 'sequence_count': len(members),
            'pair_count': sum(1 for edge in edges if not edge['self']), 'matrix_ref': matrix['id']}


def matrix_edges(text):
    """The rows of a matrix product as ``build_edges``-shaped edges (``query``, ``subject``, ``self``, ``bitscore``)."""
    rows = [line.split('\t') for line in text.splitlines()[1:]]
    return [{'query': query, 'subject': subject, 'self': query == subject, 'bitscore': float(bits)}
            for query, subject, bits in rows]


def held_matrix_facts(reader, members):
    """For each held ``sequence_similarity_matrix`` product, ``{'matrix_ref', **cluster_sheet.matrix_facts}``: the facts of its
    score-ratio graph the child's model is shown before it tunes a try. ``members`` are ``set_members`` of the commission."""
    ids = [row['id'] for row in members]
    return [{'matrix_ref': row['id'],
             **matrix_facts(score_ratio_graph(matrix_edges(reader.get_artifact(row['artifact_ref']).decode()), ids), members)}
            for row in products(reader, MATRIX_KIND)]


async def cluster(ctx, resource_id, matrix_ref, inflation, contrast, commission, per_candidate):
    """One TRY: cluster the matrix with ``mcl`` at ``inflation`` on the graph under ``contrast`` as one unit and keep the clusters as a
    working result with the controlled facts the model is shown. Nothing is graded. A sequence with no edge to any other is a cluster of
    its own (``mcl`` reads edges, so an isolated sequence is absent from its output); a partition already held is the same clustering
    (``same_as_held``), not a second product."""
    store = ctx.store
    matrix = next(row for row in products(store, MATRIX_KIND) if row['id'] == matrix_ref)
    members = set_members(store, commission, per_candidate)
    ids = [row['id'] for row in members]
    ratio = score_ratio_graph(matrix_edges(store.get_artifact(matrix['artifact_ref']).decode()), ids)
    graph = contrast_graph(ratio, contrast)
    graph_ref = store.artifact(abc_text(graph).encode('ascii'), 'text/tab-separated-values')
    executable = (Path(ctx.settings['mcl_executable_directory']) / 'mcl').resolve()
    ran = await execute_on_local_resource(
        ctx, resource_id, [str(executable), GRAPH_FILE, '--abc', '-I', str(inflation), '-o', CLUSTERS_FILE], {}, wait=True,
        inputs={GRAPH_FILE: graph_ref}, name='cluster_' + str(inflation) + '_' + contrast)
    code = _job_failure(ran, 'mcl')
    if code is not None:
        return _failed(code, [graph_ref])
    handoff, closure = ran['launch']['handoff_ref'], ran['fetch']['closure_ref']
    (clusters_ref,) = [item['ref'] for item in ran['fetch']['results'] if item['name'] == CLUSTERS_FILE]
    clusters = with_singletons(parse_clusters(store.get_artifact(clusters_ref).decode()), ids)
    facts = {**cluster_facts(clusters, members), 'edges_kept': len(graph), 'edge_count': len(ratio)}
    held = next((row for row in products(store, CLUSTERS_KIND) if row['artifact_ref'] == clusters_ref), None)
    if held is None:
        settings = {**clusters_settings(inflation, contrast), 'software_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}
        with store.transaction():
            held = record_product(store, artifact_ref=clusters_ref, kind=CLUSTERS_KIND, generated_by=handoff,
                                  used=[matrix['artifact_ref']], derived_from=[matrix['id']], settings=settings)
    graded = [clusters_ref, held['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [*graded, graph_ref, handoff, closure],
            'graded_refs': graded, 'clusters_ref': held['id'],
            'same_as_held': held['settings']['inflation'] != inflation or held['settings']['contrast'] != contrast,
            'facts': facts}


def commit_clustering(ctx, clusters_ref, commission, per_candidate):
    """Commit the held clustering: grade it into the cluster sheet and keep, through custody, the grading artifact (labelled as a
    ``tool_grading_sheet`` data product) and a source of provider ``all_vs_all`` over the clusters (the one graded test of the
    commission; what the head's credit reads)."""
    store = ctx.store
    product = next(row for row in products(store, CLUSTERS_KIND) if row['id'] == clusters_ref)
    members = set_members(store, commission, per_candidate)
    clusters = with_singletons(parse_clusters(store.get_artifact(product['artifact_ref']).decode()), [row['id'] for row in members])
    settings = product['settings']
    grading = grade_clustering(clusters, [{key: row[key] for key in ('id', 'candidate', 'accession', 'md5')} for row in members],
                               method=METHOD, parameters={'inflation': settings['inflation'], 'contrast': settings['contrast'],
                                                          'edge_weight': EDGE_WEIGHT,
                                                          'software_sha256': settings['software_sha256']},
                               commission={'search_ref': commission['search_ref'], 'candidates': sorted(commission['candidates']),
                                           'per_candidate': per_candidate})
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=product['artifact_ref'], grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': product['artifact_ref'], 'text_ref': None,
            'request_ref': None, 'version': METHOD + ':' + str(settings['inflation']) + ':' + settings['contrast'],
            'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [commission['query_ref']]},
            origin='tool')
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[product['artifact_ref']],
                                                 derived_from=[product['id']])
    graded = [source['id'], grading_ref, product['id'], grading_product['id']]
    sheet = grading['sheet']
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': graded, 'graded_refs': graded,
            'inflation': settings['inflation'], 'contrast': settings['contrast'],
            'cluster_count': sheet['set']['cluster_count'], 'target_cluster_size': sheet['target_cluster']['size'],
            'source_ref': source['id']}


__all__ = ['BLAST_PROGRAMS', 'CHILD', 'CONTRASTS', 'CLUSTERS_KIND', 'DATABASE_KIND', 'EVALUE', 'HOLD_REASONS', 'INFLATIONS', 'OWN_FAILURE_CODES', 'MATRIX_KIND',
           'MINIMUM_CANDIDATES', 'PER_CANDIDATE_RANGE', 'PROVIDER', 'SET_KIND', 'TOOLS', 'all_vs_all_blast', 'check_blast',
           'check_cluster', 'check_commission', 'commission_keys', 'check_commit', 'check_prepare', 'held_clusterings', 'held_matrix_facts',
           'cluster', 'commit_clustering', 'committable', 'database_settings', 'matrix_settings', 'clusters_settings',
           'pack_database', 'prepare_database', 'set_members', 'set_settings']
