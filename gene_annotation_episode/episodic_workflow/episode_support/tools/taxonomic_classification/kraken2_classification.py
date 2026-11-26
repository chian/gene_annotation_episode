"""One Kraken 2 classification of one DNA sequence: the check of the request, and the classification as one unit.

The episode's model fills out one request: ``query_ref``, ``index``, ``resource_id``. Two functions of this module do
the rest, deterministically:

``check_kraken2_request`` examines the request against what the episode holds and the bound resources, before anything
runs. It returns the things to fix (one entry per problem: the field, a code and what to choose from); an empty list
means the request can run. The episode's ``action`` rejects a request with problems, so no unit is made.

``kraken2_classification`` runs a request that passed the check, as one unit, in this order:

1. read the query sequence through custody and make its FASTA file as an artifact;
2. build the ``kraken2`` command: the index of the manifest read from disk (``--memory-mapping``: the index is not
   loaded into memory), one thread, the per-sequence output and the report as files of the job's directory;
3. run it on the local resource through the inspection point (``execute_on_local_resource`` with ``wait=True``);
4. grade the per-sequence output with the library's Kraken 2 grader and the index's own taxonomy into the sheet (one
   row per taxon that has a k-mer of its own or below it);
5. keep the grading through custody: the grading artifact, a ``native.kraken2.classify`` source over the output (its
   operand is the query), one ``taxon`` reference for each taxon of the sheet (its accession is the taxon id of the
   index's taxonomy, NCBI's; its label the index's name for it) and one ``taxonomy_assignment`` observation for each
   (the query, the taxon, the k-mers of the query in the taxon's clade); the output and the report labelled as data
   products, and the grading labelled as a ``tool_grading_sheet`` data product derived from them.

Grading is not a choice of anyone: it follows the run in the same unit.

An index is named by a manifest (a JSON file beside the index: ``name``, ``version``, ``directory`` and, for each file
of the index, its path, size and SHA-256): the manifest's bytes are the index's identity in custody. What an index
covers is a fact of the index (the viral index holds viral genomes only; the capped standard index holds archaea,
bacteria, viruses, plasmids and human, with a part of their k-mers): a sequence of an organism the index does not hold
can still share a few k-mers with it, and the sheet reports them as they are.

The outcome has the shape of every tool outcome of an episode. ``completed``: ``record_refs`` are the source, the grading
artifact, the product rows, the references and the observations, and ``result`` holds the k-mer counts and, for each
taxon of the sheet, its reference, id, name, rank code and k-mers. A sequence with no k-mer in the index is completed with
no taxon. What can still go wrong after a passed check is a fault of the environment: a ``failed`` outcome with its code
and ``retryable`` false, reported once."""
import json
from pathlib import Path

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.kraken2_grader import (
    grade_kraken2_classification)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)

JOB_NAME = 'kraken2_classify'
PROGRAM = 'kraken2'
PROVIDER = 'native.kraken2.classify'
QUERY_NAME, QUERY_FILE = 'query_sequence', 'query_sequence.fasta'
OPTIONS = ['--memory-mapping', '--threads', '1']
OUTPUT_FILE, REPORT_FILE = 'kraken2.output.tsv', 'kraken2.report.tsv'
TAXONOMY_ROLE = 'taxonomy'
PRODUCT_KIND = 'taxonomic_classification_results'
PRODUCT_KINDS = {OUTPUT_FILE: PRODUCT_KIND, REPORT_FILE: 'taxonomic_classification_report'}
QUERY_MOLECULES = ('dna',)


def classification_settings(manifest):
    """The settings of a classification's output as a data product (closed JSON): the program, the index's name and
    version (the thread count and the memory mapping do not change the result)."""
    return {'program': PROGRAM, 'index': manifest['name'], 'index_version': manifest['version']}


def check_kraken2_request(request, *, sequences, scope_subjects, resources):
    """The things to fix in a classification request, before anything runs; an empty list means it can run.

    ``request`` holds ``query_ref`` (a key of ``sequences``), ``index`` (a configured index) and ``resource_id`` (a key
    of ``resources``); the caller's schema has already bound each to those sets. ``sequences`` is ``{record: molecule}``
    of the sequence records the episode holds, ``scope_subjects`` the subjects of its scope and ``resources`` ``{resource
    id: kind}``. The conditions:

    1. the query is a subject of the episode's scope;
    2. the query is DNA (the indexes hold nucleotide k-mers);
    3. the resource is a local resource."""
    query = request['query_ref']
    problems = []
    if query not in scope_subjects:
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_sequence_of_the_scope',
                         'choose_from': [ref_ for ref_ in scope_subjects if ref_ in sequences]})
    if sequences[query] not in QUERY_MOLECULES:
        problems.append({'field': 'query_ref', 'code': 'kraken2_takes_a_dna_query', 'query_molecule': sequences[query],
                         'choose_from': [ref_ for ref_ in scope_subjects if sequences.get(ref_) in QUERY_MOLECULES]})
    if resources[request['resource_id']] != 'local':
        problems.append({'field': 'resource_id', 'code': 'resource_is_not_local',
                         'choose_from': [name for name, kind in resources.items() if kind == 'local']})
    return problems


def _outcome(status, code, *, category, detail=None):
    feedback = {'category': category, 'code': code, 'retryable': False}
    if detail is not None:
        feedback['detail'] = detail
    return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': feedback}


def _taxa(store, sheet, source, query_ref):
    """One ``taxon`` reference and one ``taxonomy_assignment`` observation for each taxon of the sheet, projected from
    the already graded rows (nothing is calculated or graded again)."""
    taxa, refs = [], []
    for row in sheet['taxa']:
        reference = store.put('reference', {
            'reference_type': 'taxon', 'source_ref': source['id'], 'accession': str(row['taxon_id']),
            'label': row['name'], 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [],
            'context_refs': []}, origin='external')
        observation = store.put('observation', {
            'kind': 'taxonomy_assignment', 'subject_refs': [query_ref], 'source_subject_refs': [reference['id']],
            'source_ref': source['id'],
            'measurements': measurements(reference_ref=ref(reference['id']), count=number(row['kmers_clade'])),
            'dependencies': [query_ref, reference['id']], 'anchor': None}, origin='tool')
        taxa.append({'taxon_ref': reference['id'], 'observation_ref': observation['id'], 'taxon_id': row['taxon_id'],
                     'name': row['name'], 'rank_code': row['rank_code'], 'kmers_direct': row['kmers_direct'],
                     'kmers_clade': row['kmers_clade']})
        refs.extend([reference['id'], observation['id']])
    return taxa, refs


async def kraken2_classification(ctx, *, query_ref, index, resource_id, executable_directory, manifest_path):
    """Classify the query against the index of ``manifest_path`` on the local resource and keep the graded taxa.
    ``ctx`` is the tool's ``UnitContext`` of an episode that declares the service ``job_access``."""
    store, access = ctx.store, ctx.services['job_access']
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest['name'] != index:
        raise ValueError('kraken2_manifest_is_of_another_index')
    record = store.get(query_ref)
    letters = store.get_artifact(record['sequence_ref']).decode('ascii').upper()
    manifest_ref = store.artifact(Path(manifest_path).read_bytes(), 'application/json')   # the index's identity
    fasta = store.artifact(('>' + QUERY_NAME + '\n' + letters + '\n').encode(), 'text/x-fasta')
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    command = [str((Path(executable_directory) / PROGRAM).resolve()), '--db', manifest['directory'], *OPTIONS,
               '--output', OUTPUT_FILE, '--report', REPORT_FILE, str(directory / QUERY_FILE)]
    request_ref = store.artifact(canonical({'command': command, 'index': classification_settings(manifest)}),
                                 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, command, {}, wait=True, inputs={QUERY_FILE: fasta},
                                          name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'])
    if ran['returncode'] != 0:
        return _outcome('failed', 'kraken2_program_exit_nonzero', category='job',
                        detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-2000:]})
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if OUTPUT_FILE not in fetched or REPORT_FILE not in fetched:
        return _outcome('failed', 'kraken2_output_missing', category='job', detail={'files': sorted(fetched)})
    try:
        grading = grade_kraken2_classification(
            output_text=store.get_artifact(fetched[OUTPUT_FILE]).decode(),
            taxonomy_text=Path(manifest['files'][TAXONOMY_ROLE]['path']).read_text(), sequence_name=QUERY_NAME,
            sequence_length=len(letters))
    except ValueError as error:
        return _outcome('failed', str(error), category='grading')
    grading['index'] = {**classification_settings(manifest), 'covers_taxon_ids': list(manifest['covers_taxon_ids'])}
    sheet = grading['sheet']
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=fetched[OUTPUT_FILE],
                                          grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': fetched[OUTPUT_FILE],
            'text_ref': None, 'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, request_ref, fetched[REPORT_FILE]],
            'operand_refs': [query_ref]}, origin='tool')
        taxa, written = _taxa(store, sheet, source, query_ref)
        product, *labelled = [record_product(store, artifact_ref=fetched[name], kind=kind, generated_by=source['id'],
                                             used=[record['sequence_ref'], manifest_ref],
                                             settings=classification_settings(manifest))
                              for name, kind in PRODUCT_KINDS.items()]
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[fetched[name] for name in PRODUCT_KINDS],
                                                 derived_from=[product['id'], *(row['id'] for row in labelled)])
    refs = [source['id'], grading_ref, product['id'], *(row['id'] for row in labelled), grading_product['id'], *written]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'index': manifest['name'], 'index_version': manifest['version'], 'product_ref': product['id'],
                       'grading_ref': grading_ref, 'classified': sheet['sequence']['classified'],
                       'assigned_taxon_id': sheet['sequence']['assigned_taxon_id'], 'kmers': sheet['kmers'],
                       'taxon_count': len(taxa), 'taxa': taxa}, 'feedback': None}


__all__ = ['PROVIDER', 'check_kraken2_request', 'classification_settings', 'kraken2_classification']
