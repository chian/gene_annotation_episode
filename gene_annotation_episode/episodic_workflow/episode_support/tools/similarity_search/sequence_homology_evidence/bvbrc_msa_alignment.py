"""One multiple sequence alignment through the BV-BRC application service (the ``MSA`` application) of the target with
the sequences of the candidates a graded BV-BRC database search found, as plain library functions that the actions of the
``bvbrc_msa`` episode call. The five actions, their checks, the estimate gate, the credit and the ledger are the shared
``bvbrc_job_child``; this module is the binding of the ``MSA`` application to it (``APPLICATION``) and what is specific:

* the plan: code, not the model, chooses the sequences. For each chosen candidate (a ``product`` of the search), its hits
  ordered by their value in the search (the subscore the head's credit reads; highest first, ties by accession), one per
  distinct ``aa_sequence_md5``, the first ``per_candidate``. The target's own sequence is always first, under the fixed
  name ``target``; the references are named ``r1``, ``r2`` ... in that order (``plan_rows``);
* the inputs: the chosen hits go in as a BV-BRC feature group (``group.json``: their ``feature_id``s; the route creates the
  feature group object ``<job folder>/hits`` in the BV-BRC workspace) and the target as pasted FASTA in the same job
  (``sequences.fasta``; the service accepts both together, verified live); BV-BRC reads the hits' sequences itself, so
  they are not fetched (``bvbrc_hit_metadata.sequences_by_md5`` stays in the library; the grading does not need it: each
  aligned row is checked against the hit's ``aa_sequence_md5``);
* the extract: the aligned FASTA ``msa.afa`` is fetched and graded in the same unit (``msa_alignment_sheet.grade_alignment``,
  which reads it with the existing ``parse_aligned_fasta``): the sheet, a source of provider ``bvbrc_msa``, a ``reference``
  record per sequence and one ``alignment`` observation per reference sequence (``compared_symbol_count``: the columns
  where both have a residue; ``matching_symbol_count``: how many are identical; ``query_selected_length``: the target's
  length), and the alignment labelled as a ``multiple_sequence_alignment`` data product (``used``: the target's sequence artifact, the search source and the feature group's artifact) with its place in the BV-BRC
  workspace in ``locations``: THE RECORD a later child (MetaCATS) is passed and requires.

The reuse key of the alignment is computed from what is known before the launch: ``used`` = the target's sequence artifact
and the search source; ``settings`` = the application, aligner, alphabet, the candidates (sorted) and ``per_candidate``."""
import hashlib
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    _regions)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    search_hits)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.msa_alignment_sheet import (
    grade_alignment)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    compile_native_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import (
    find_reusable, record_product)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    PROVIDER as SEARCH_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    JobApplication, _choose, _failed, check_resource_and_continuation)

CHILD = 'bvbrc_msa'
PROVIDER = 'bvbrc_msa'
ALIGNER, ALPHABET = 'Muscle', 'protein'
TARGET_NAME = 'target'
PER_CANDIDATE_RANGE = (2, 20)
MINIMUM_CANDIDATES = 2
SEQUENCES_FILE, GROUP_FILE, ALIGNMENT_FILE = 'sequences.fasta', 'group.json', 'msa.afa'
PRODUCT_KIND = 'multiple_sequence_alignment'
REQUEST_FIELDS = ('per_candidate', 'resource_id')


def settings_of(candidates, per_candidate):
    """The settings of the alignment (closed JSON): the reuse key and the product's settings."""
    return {'application': 'MSA', 'aligner': ALIGNER.lower(), 'alphabet': ALPHABET, 'candidates': sorted(candidates),
            'per_candidate': per_candidate}


# -- the plan --------------------------------------------------------------------------------------------------------
def search_rows(reader, scope, search_ref):
    """The product-named hits of the held graded search ``search_ref`` with their values (the head's credit's own
    subscore): ``search_hits`` over the retained grading of the source."""
    source = reader.get(search_ref)
    (entry,) = source_tool_grading_entries(reader, search_ref)
    target = source['operand_refs'][0]
    length, regions = reader.subject_length(target), _regions(reader, scope, target)
    rows = search_hits(entry['grading'], lambda rows_: compile_native_sheet(
        rows_, supplied_length=length, regions=regions)['value'])
    return [row for row in rows if row['product'] is not None]


def plan_rows(rows, candidates, per_candidate):
    """The references of the alignment: for each of ``candidates`` its hits that carry a sequence and a feature id, by value (highest first, ties by accession),
    one per distinct ``aa_sequence_md5``, the first ``per_candidate``; named ``r1``... in the order of ``candidates``."""
    chosen = []
    for candidate in candidates:
        seen = set()
        for row in sorted((row for row in rows if row['product'] == candidate and row['aa_sequence_md5']
                           and row['feature_id']),
                          key=lambda row: (-row['value'], row['accession'])):
            if row['aa_sequence_md5'] not in seen and len(seen) < per_candidate:
                seen.add(row['aa_sequence_md5'])
                chosen.append({'candidate': candidate, 'accession': row['accession'], 'md5': row['aa_sequence_md5'],
                               'aa_length': row['aa_length'], 'value': row['value'], 'feature_id': row['feature_id']})
    return [{'name': 'fig|' + row['accession'], **row} for row in chosen]


def planned_size(plan, target_length):
    """The size of the job the plan gives, from the hits' recorded lengths: ``sequences``, ``residues``, ``longest``."""
    lengths = [target_length, *(row['aa_length'] for row in plan)]
    return {'sequences': len(lengths), 'residues': sum(lengths), 'longest': max(lengths)}


def msa_options(reader, scope, table):
    """The held graded BV-BRC searches of the head, each with the product candidates the head admitted from it:
    ``[{'search_ref', 'query_ref', 'candidates'}]`` (``table`` is ``candidate_table``'s; a candidate of the search is a
    ``product`` candidate of the target that underwent the search's test)."""
    options = []
    for ref_ in (ref_ for ref_ in reader.list('source') if ref_['provider'] == SEARCH_PROVIDER):
        (entry,) = source_tool_grading_entries(reader, ref_['id'])
        search = entry['grading']['sheet']['normalized_result']['search']
        test = ('database_search:' + SEARCH_PROVIDER + ':' + search['program'] + ':' + search['request']['database']
                + '@' + ref_['id'])   # one test is one graded source (candidate_measurements)
        target = ref_['operand_refs'][0]
        if target not in table['targets']:      # a held search of a sequence that is not a target of the head
            continue
        names = [row['name'] for row in table['targets'][target]['candidates']
                 if row['vocabulary'] == 'product' and test in row['tests']]
        options.append({'search_ref': ref_['id'], 'query_ref': target, 'candidates': names})
    return options


# -- the binding -----------------------------------------------------------------------------------------------------
def field_problems(request, commission):
    problems = []
    if not PER_CANDIDATE_RANGE[0] <= request['per_candidate'] <= PER_CANDIDATE_RANGE[1]:
        problems.append(_choose('per_candidate', 'per_candidate_out_of_range', minimum=PER_CANDIDATE_RANGE[0],
                                maximum=PER_CANDIDATE_RANGE[1]))
    return problems


def _plan(store, request, commission):
    """The plan of the job of ``commission``: a function of the job's identity (the target, the search, the candidates
    SORTED, ``per_candidate``), never of the order a commission names the candidates in. A parked job is resumed by a
    commission built from that identity (the head's ``resume_commission``), so the continuation plans exactly the job
    the launch planned, and the group file it names is the one the launch staged."""
    rows = search_rows(store, {'subject_refs': [commission['query_ref']]}, commission['search_ref'])
    return plan_rows(rows, sorted(commission['candidates']), request['per_candidate'])


def feature_group_bytes(plan):
    """The feature group of the plan's hits (their ``feature_id``s, in plan order) as the closed JSON the job is given
    (``group.json``): the route creates the BV-BRC feature group object from it and BV-BRC reads the sequences itself."""
    return canonical({'feature_ids': [row['feature_id'] for row in plan]}).encode('ascii')


def feature_group_ref(plan):
    """The reference the group's artifact has (content-addressed: ``artifact_`` and the SHA-256 of its bytes), known before
    the launch: it is in ``used`` of the alignment's product and so in its reuse key."""
    return 'artifact_' + hashlib.sha256(feature_group_bytes(plan)).hexdigest()


def prepare(ctx, request, commission):
    """The job of one launch: the plan; the hits go in as a BV-BRC feature group (``group.json``: their feature ids; the
    route creates the group object under the job's folder) and the target as the pasted FASTA, in the same job. The
    sequences of the hits are not fetched: BV-BRC reads them, and the grading checks each aligned row against the hit's
    ``aa_sequence_md5``."""
    store = ctx.store
    plan = _plan(store, request, commission)
    target = store.get_artifact(store.get(commission['query_ref'])['sequence_ref']).decode('ascii').strip().upper()
    fasta_ref = store.artifact(('>' + TARGET_NAME + '\n' + target + '\n').encode('ascii'), 'text/plain')
    group_ref = store.artifact(feature_group_bytes(plan), 'application/json')
    lengths = [len(target), *(row['aa_length'] for row in plan)]
    return {'job': {'application': 'MSA', 'aligner': ALIGNER, 'alphabet': ALPHABET, 'sequences_file': SEQUENCES_FILE,
                    'feature_group_file': GROUP_FILE},
            'inputs': {SEQUENCES_FILE: fasta_ref, GROUP_FILE: group_ref},
            'job_facts': {'sequences': len(lengths), 'residues': sum(lengths), 'longest': max(lengths)},
            'identity': {'query_ref': commission['query_ref'], 'search_ref': commission['search_ref'],
                         'candidates': sorted(commission['candidates']), 'per_candidate': request['per_candidate']}}


def describe_identity(reader, handoff):
    """The controlled identity of a held MSA job (target, search, candidates, sequences per candidate), kept by ``prepare``
    in the handoff row's estimates: the head holds the row, not the plan artifact the job was given."""
    return handoff['detail']['estimates']['identity']


def reusable_alignment(reader, commission, per_candidate):
    """The held alignment product of exactly this target, search and settings, or ``None``."""
    sequence_ref = reader.get(commission['query_ref'])['sequence_ref']
    plan = _plan(reader, {'per_candidate': per_candidate}, commission)
    return find_reusable(reader, PRODUCT_KIND, [sequence_ref, commission['search_ref'], feature_group_ref(plan)],
                         settings_of(commission['candidates'], per_candidate))


def extract(ctx, handoff_ref, request, commission):
    """Fetch the alignment of the finished job and grade it in the same unit; keep, through custody: the grading
    artifact, a source of provider ``bvbrc_msa`` over the alignment, a reference record per sequence, one alignment
    observation per reference sequence, the alignment as a ``multiple_sequence_alignment`` data product (its path in
    the BV-BRC workspace in ``locations``) and the grading as a ``tool_grading_sheet`` data product. A fault of the grading is returned once as ``grading_refused``."""
    store = ctx.store
    fetched = ctx.services['job_access'].fetch(ctx, handoff_ref, names=[ALIGNMENT_FILE])
    if fetched['status'] != 'completed':
        return {**_failed(fetched['failure']['code'], False), 'closure_ref': None}
    (result_ref,) = [item['ref'] for item in fetched['results'] if item['name'] == ALIGNMENT_FILE]
    plan = _plan(store, request, commission)
    target = store.get_artifact(store.get(commission['query_ref'])['sequence_ref']).decode('ascii').strip().upper()
    given = [{'name': TARGET_NAME, 'sequence': target},
             *({'name': row['name'], 'candidate': row['candidate'], 'accession': row['accession'], 'md5': row['md5']}
               for row in plan)]
    try:
        grading = grade_alignment(store.get_artifact(result_ref), given=given, target_name=TARGET_NAME,
                                  aligner=ALIGNER.lower(), alphabet=ALPHABET, source_ref=handoff_ref)
    except ValueError as error:
        return {**_failed('grading_refused', False, reason=str(error)), 'closure_ref': fetched['closure_ref']}
    sheet = grading['sheet']
    (path,) = [item['workspace_path'] for item in json.loads(store.get_artifact(fetched['reply_ref']))['catalog']
               if item['name'] == ALIGNMENT_FILE]
    target_ref = commission['query_ref']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=result_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': result_ref, 'text_ref': None,
            'request_ref': None, 'version': sheet['aligner'] + ':' + sheet['alphabet'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [target_ref]}, origin='tool')
        references, observations = [], []
        for row in sheet['references']:
            reference = store.put('reference', {
                'reference_type': 'protein', 'source_ref': source['id'], 'accession': row['accession'],
                'label': row['candidate'], 'sequence_ref': None, 'molecule': 'protein',
                'length': row['length'], 'term_refs': [], 'context_refs': []}, origin='external')
            references.append(reference['id'])
            observations.append(store.put('observation', {
                'kind': 'alignment', 'subject_refs': [target_ref], 'source_subject_refs': [reference['id']],
                'source_ref': source['id'], 'anchor': None,
                'measurements': measurements(
                    reference_ref=ref(reference['id']), compared_symbol_count=number(row['paired_columns']),
                    matching_symbol_count=number(row['identical_columns']),
                    query_selected_length=number(sheet['alignment']['target_length'])),
                'dependencies': [target_ref, reference['id']]}, origin='tool')['id'])
        sequence_ref = store.get(target_ref)['sequence_ref']
        # the group file the job was given: the one its handoff row staged (held, passed back with the row on a resume)
        product = record_product(
            store, artifact_ref=result_ref, kind=PRODUCT_KIND, generated_by=handoff_ref,
            used=[sequence_ref, commission['search_ref'], store.get(handoff_ref)['detail']['input_refs'][GROUP_FILE]],
            settings=settings_of(commission['candidates'], request['per_candidate']),
            locations=[{'service': 'bvbrc_workspace', 'path': path}])
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[result_ref], derived_from=[product['id']])
    refs = [source['id'], grading_ref, product['id'], grading_product['id'], *references, *observations]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'closure_ref': fetched['closure_ref'],
            'graded_refs': refs, 'record_refs': [*refs, fetched['closure_ref']], 'product_ref': product['id'],
            'sequence_count': sheet['alignment']['sequences'], 'column_count': sheet['alignment']['columns'],
            'candidate_count': len({row['candidate'] for row in sheet['references']})}


def graded_rows(reader):
    """The graded alignments the episode holds: one row per held source of provider ``bvbrc_msa`` with its sheet's
    facts (sequences, columns, references) and its product row."""
    rows = []
    for source in reader.list('source'):
        if source['provider'] != PROVIDER:
            continue
        (entry,) = source_tool_grading_entries(reader, source['id'])
        sheet = entry['grading']['sheet']
        rows.append({'source_ref': source['id'], 'grading_ref': entry['artifact_ref'],
                     'sequence_count': sheet['alignment']['sequences'], 'column_count': sheet['alignment']['columns'],
                     'reference_count': len(sheet['references']),
                     'candidate_count': len({row['candidate'] for row in sheet['references']})})
    return rows


def check_commission(request, *, scope_subjects, sequences, options, resources, jobs):
    """The things to fix in the head's commission of this child (``request``: ``query_ref``, ``search_ref``,
    ``candidates``, ``per_candidate``, ``resource_id``, ``until``). ``options`` is ``msa_options``; ``jobs`` the head's
    held MSA jobs (``bvbrc_job_child.held_jobs``). The conditions:
    the query is a protein sequence of the scope; the search is a held graded BV-BRC search of that query; at least two
    distinct candidates, each admitted from that search; ``per_candidate`` in range; the resource a bound BV-BRC service;
    an outstanding job of this commission is continued (``until`` ``extracted``) and another one blocks it."""
    problems = []
    query, search = request['query_ref'], request['search_ref']
    if query not in scope_subjects or sequences.get(query) != 'protein':
        problems.append(_choose('query_ref', 'query_is_not_a_protein_sequence_of_the_scope',
                                choose_from=[ref_ for ref_ in scope_subjects if sequences.get(ref_) == 'protein']))
    option = [item for item in options if item['search_ref'] == search and item['query_ref'] == query]
    if not option:
        problems.append(_choose('search_ref', 'search_is_not_a_held_graded_search_of_the_query',
                                choose_from=[item['search_ref'] for item in options if item['query_ref'] == query]))
    else:
        outside = [name for name in request['candidates'] if name not in option[0]['candidates']]
        if outside:
            problems.append(_choose('candidates', 'candidate_is_not_admitted_from_the_search', not_admitted=outside,
                                    choose_from=option[0]['candidates']))
    if len(set(request['candidates'])) != len(request['candidates']) or len(request['candidates']) < MINIMUM_CANDIDATES:
        problems.append(_choose('candidates', 'two_or_more_distinct_candidates_required'))
    problems.extend(field_problems(request, None))
    same = lambda job: (job['identity']['search_ref'] == search and job['identity']['candidates'] == sorted(
        request['candidates']) and job['identity']['per_candidate'] == request['per_candidate']
        and job['resource_id'] == request['resource_id'])
    problems.extend(check_resource_and_continuation(request, resources=resources, jobs=jobs, same=same))
    return problems


APPLICATION = JobApplication(
    application='MSA', child=CHILD, service='bvbrc_msa', provider=PROVIDER, product_kind=PRODUCT_KIND,
    request_fields=REQUEST_FIELDS, estimate_fields=('per_candidate',),
    field_schemas={'per_candidate': {'type': 'integer', 'minimum': PER_CANDIDATE_RANGE[0],
                                     'maximum': PER_CANDIDATE_RANGE[1]},
                   'resource_id': {'type': 'string', 'minLength': 1}},
    size_field='residues', kind=lambda fields: 'MSA:' + ALIGNER.lower() + ':' + ALPHABET,
    field_problems=field_problems, prepare=prepare, extract=extract, describe_identity=describe_identity)

__all__ = ['ALIGNER', 'ALPHABET', 'APPLICATION', 'CHILD', 'PER_CANDIDATE_RANGE', 'PROVIDER', 'REQUEST_FIELDS',
           'TARGET_NAME', 'check_commission', 'graded_rows', 'msa_options', 'plan_rows', 'planned_size',
           'reusable_alignment', 'search_rows', 'settings_of']
