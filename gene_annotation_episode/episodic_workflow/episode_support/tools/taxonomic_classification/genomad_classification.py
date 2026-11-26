"""One geNomad run on one DNA sequence: the check of the request, and the run as one unit.

The episode's model fills out one request: ``query_ref``, ``resource_id``. ``check_genomad_request`` examines it before
anything runs and returns the things to fix; an empty list means it can run. ``genomad_classification`` runs a request that
passed, as one unit: the query's FASTA is staged, ``genomad end-to-end`` runs on the local resource (gene calling, the
search of its marker database, its neural network, the aggregated classification, the summary), the tables the grader
reads are copied to the job's directory and the rest of geNomad's output is removed there, the tables are graded
(``genomad_grader``, with the prepared NCBI taxonomy) and the grading is kept through custody: the grading artifact, a
``native.genomad.end_to_end`` source over the aggregated classification (its operand is the query), one ``taxon`` reference
and one ``taxonomy_assignment`` observation for each taxon the run supports (the deepest taxon of the genes' lineage, and
the two taxa a kind of DNA names), and the tables labelled as data products with the grading derived from them.

geNomad's search builds a table of its whole marker database in memory, whatever the size of the query: ``splits`` (a
setting) cuts the database into that many parts, each searched with its own smaller table. The run takes minutes.

geNomad covers viruses and plasmids of every host and tells them from chromosomes; its taxonomy is of viruses only and never
goes below family. The outcome has the shape of every tool outcome of an episode; what can still go wrong after a passed
check is a fault of the environment: ``failed``, ``retryable`` false, reported once."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.genomad_grader import (
    grade_genomad_classification)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    load_taxonomy)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)

JOB_NAME = 'genomad_classify'
PROGRAM = 'genomad'
PROVIDER = 'native.genomad.end_to_end'
QUERY_NAME, QUERY_FILE = 'query_sequence', 'query_sequence.fasta'
CLASSIFICATION_FILE, TAXONOMY_FILE, SUMMARY_FILE, LOG_FILE = (
    'genomad.aggregated_classification.tsv', 'genomad.taxonomy.tsv', 'genomad.virus_summary.tsv', 'genomad.log')
PRODUCT_KIND = 'sequence_kind_scores'
PRODUCT_KINDS = {CLASSIFICATION_FILE: PRODUCT_KIND, TAXONOMY_FILE: 'virus_taxonomy_assignment'}
QUERY_MOLECULES = ('dna',)
SCRIPT = """set -e
mkdir -p tmp
export TMPDIR="$PWD/tmp"
genomad end-to-end --threads 1 --splits {splits} --cleanup {query} out {database} > {log} 2>&1
cp out/{name}_aggregated_classification/{name}_aggregated_classification.tsv {classification}
if [ -f out/{name}_annotate/{name}_taxonomy.tsv ]; then cp out/{name}_annotate/{name}_taxonomy.tsv {taxonomy}; fi
if [ -f out/{name}_summary/{name}_virus_summary.tsv ]; then cp out/{name}_summary/{name}_virus_summary.tsv {summary}; fi
rm -rf out tmp
"""


def run_settings(manifest, splits):
    """The settings of a run's tables as data products (closed JSON): the program, its database's name and version. The
    number of splits does not change the result."""
    return {'program': PROGRAM, 'database': manifest['name'], 'database_version': manifest['version']}


def check_genomad_request(request, *, sequences, scope_subjects, resources):
    """The things to fix in a geNomad request, before anything runs; an empty list means it can run. ``request`` holds
    ``query_ref`` and ``resource_id``. The conditions: the query is a subject of the scope; it is DNA; the resource is local."""
    query = request['query_ref']
    problems = []
    if query not in scope_subjects:
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_sequence_of_the_scope',
                         'choose_from': [ref_ for ref_ in scope_subjects if ref_ in sequences]})
    if sequences[query] not in QUERY_MOLECULES:
        problems.append({'field': 'query_ref', 'code': 'genomad_takes_a_dna_query', 'query_molecule': sequences[query],
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


def _taxa(store, rows, source, query_ref):
    """One ``taxon`` reference and one ``taxonomy_assignment`` observation for each ``(taxon row, score)``."""
    taxa, refs = [], []
    for row, score in rows:
        reference = store.put('reference', {
            'reference_type': 'taxon', 'source_ref': source['id'], 'accession': str(row['taxon_id']), 'label': row['name'],
            'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='external')
        observation = store.put('observation', {
            'kind': 'taxonomy_assignment', 'subject_refs': [query_ref], 'source_subject_refs': [reference['id']],
            'source_ref': source['id'],
            'measurements': measurements(reference_ref=ref(reference['id']), model_score=number(score)),
            'dependencies': [query_ref, reference['id']], 'anchor': None}, origin='tool')
        taxa.append({'taxon_ref': reference['id'], 'observation_ref': observation['id'], 'taxon_id': row['taxon_id'],
                     'name': row['name'], 'rank_code': row['rank_code'], 'score': score})
        refs.extend([reference['id'], observation['id']])
    return taxa, refs


async def genomad_classification(ctx, *, query_ref, resource_id, environment_directory, database_manifest_path,
                                 taxonomy_manifest_path, splits):
    """Run geNomad on the query on the local resource and keep the graded result. ``ctx`` is the tool's ``UnitContext``
    of an episode that declares the service ``job_access``."""
    store = ctx.store
    manifest = json.loads(Path(database_manifest_path).read_text())
    record = store.get(query_ref)
    letters = store.get_artifact(record['sequence_ref']).decode('ascii').upper()
    manifest_ref = store.artifact(Path(database_manifest_path).read_bytes(), 'application/json')   # the database's identity
    taxonomy_ref = store.artifact(Path(taxonomy_manifest_path).read_bytes(), 'application/json')
    fasta = store.artifact(('>' + QUERY_NAME + '\n' + letters + '\n').encode(), 'text/x-fasta')
    script = SCRIPT.format(splits=int(splits), query=QUERY_FILE, database=manifest['directory'], log=LOG_FILE,
                           name=QUERY_NAME, classification=CLASSIFICATION_FILE, taxonomy=TAXONOMY_FILE,
                           summary=SUMMARY_FILE)
    command = ['/bin/bash', '-c', script]
    environment = {'PATH': str(Path(environment_directory) / 'bin') + ':/usr/bin:/bin'}
    request_ref = store.artifact(canonical({'command': command, 'database': run_settings(manifest, splits)}),
                                 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, command, environment, wait=True, inputs={QUERY_FILE: fasta},
                                          name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'])
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if ran['returncode'] != 0 or CLASSIFICATION_FILE not in fetched:
        log = store.get_artifact(fetched[LOG_FILE]).decode(errors='replace')[-2000:] if LOG_FILE in fetched else ''
        return _outcome('failed', 'genomad_program_exit_nonzero' if ran['returncode'] != 0 else 'genomad_output_missing',
                        category='job', detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-1000:], 'log': log})
    try:
        grading = grade_genomad_classification(
            aggregated_text=store.get_artifact(fetched[CLASSIFICATION_FILE]).decode(),
            taxonomy_text=store.get_artifact(fetched[TAXONOMY_FILE]).decode() if TAXONOMY_FILE in fetched else None,
            sequence_name=QUERY_NAME, taxonomy=load_taxonomy(taxonomy_manifest_path))
    except ValueError as error:
        return _outcome('failed', str(error), category='grading')
    grading['database'] = {'name': manifest['name'], 'version': manifest['version']}
    sheet = grading['sheet']
    supported = [(sheet['kind_taxa']['virus'], sheet['kind']['virus_score']),
                 (sheet['kind_taxa']['cellular'], sheet['kind']['chromosome_score'] + sheet['kind']['plasmid_score'])]
    if sheet['taxa']:
        supported.append((sheet['taxa'][-1], sheet['kind']['virus_score'] * sheet['gene_taxonomy']['agreement']))
    present = [name for name in PRODUCT_KINDS if name in fetched]
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=fetched[CLASSIFICATION_FILE],
                                          grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': fetched[CLASSIFICATION_FILE],
            'text_ref': None, 'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, request_ref, *(fetched[name] for name in (TAXONOMY_FILE, SUMMARY_FILE,
                                                                                              LOG_FILE) if name in fetched)],
            'operand_refs': [query_ref]}, origin='tool')
        taxa, written = _taxa(store, supported, source, query_ref)
        product, *labelled = [record_product(store, artifact_ref=fetched[name], kind=PRODUCT_KINDS[name],
                                             generated_by=source['id'],
                                             used=[record['sequence_ref'], manifest_ref, taxonomy_ref],
                                             settings=run_settings(manifest, splits)) for name in present]
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[fetched[name] for name in present],
                                                 derived_from=[product['id'], *(row['id'] for row in labelled)])
    refs = [source['id'], grading_ref, product['id'], *(row['id'] for row in labelled), grading_product['id'], *written]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'database': manifest['name'], 'database_version': manifest['version'], 'product_ref': product['id'],
                       'grading_ref': grading_ref, 'kind': sheet['kind'], 'gene_taxonomy': sheet['gene_taxonomy'],
                       'deepest_taxon_id': sheet['deepest_taxon_id'], 'unresolved_names': sheet['unresolved_names'],
                       'taxa': taxa}, 'feedback': None}


__all__ = ['PROVIDER', 'QUERY_MOLECULES', 'check_genomad_request', 'genomad_classification', 'run_settings']
