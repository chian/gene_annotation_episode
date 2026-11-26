"""One VITAP assignment of one DNA sequence: the check of the request, and the assignment as one unit.

The episode's model fills out one request: ``query_ref``, ``resource_id``. ``check_vitap_request`` examines it before
anything runs and returns the things to fix; an empty list means it can run. ``vitap_assignment`` runs a request that
passed, as one unit: the query's FASTA is staged, ``VITAP assignment`` runs on the local resource against the database of
the manifest (gene calling, a DIAMOND search of the proteins against the proteins of the database's viruses, the scoring of
the lineages; ``--low_conf`` so that a weak assignment is reported with its score and not dropped), its two tables are
copied to the job's directory and the rest of its output is removed there, the tables are graded (``vitap_grader``, with
the prepared NCBI taxonomy) and the grading is kept through custody: the grading artifact, a ``native.vitap.assignment``
source over VITAP's log (its operand is the query), one ``taxon`` reference and one ``taxonomy_assignment`` observation for
each lineage whose finest name resolves, and the tables labelled as data products with the grading derived from them.

VITAP is a classifier of viruses: it scores virus lineages for whatever it is given, and a piece of a cell that holds a few
genes like a virus's gets a virus lineage with a low score. What the answer means is for the scoring sheet, with the other
signals. A sequence VITAP assigns nothing is a completed unit with no lineage. VITAP adds ten reference genomes of its own
choice to every run for its internal calibration, so two runs of one sequence can differ slightly in their scores.

The outcome has the shape of every tool outcome of an episode; what can still go wrong after a passed check is a fault of
the environment: ``failed``, ``retryable`` false, reported once."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    load_taxonomy)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.vitap_grader import (
    grade_vitap_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    measurements, number, ref)

JOB_NAME = 'vitap_assign'
PROGRAM = 'VITAP'
PROVIDER = 'native.vitap.assignment'
QUERY_NAME, QUERY_FILE = 'query_sequence', 'query_sequence.fasta'
BEST_FILE, ALL_FILE, LOG_FILE = 'vitap.best_determined_lineages.tsv', 'vitap.all_lineages.tsv', 'vitap.log'
PRODUCT_KIND = 'virus_taxonomy_assignment'
PRODUCT_KINDS = {BEST_FILE: PRODUCT_KIND, ALL_FILE: 'virus_taxonomy_lineages'}
QUERY_MOLECULES = ('dna',)
SCRIPT = """set -e
mkdir -p tmp
export TMPDIR="$PWD/tmp"
VITAP assignment -i {query} -d {database} -p 1 -o out --low_conf > {log} 2>&1
if [ -f out/best_determined_lineages.tsv ]; then cp out/best_determined_lineages.tsv {best}; fi
if [ -f out/all_lineages.tsv ]; then cp out/all_lineages.tsv {all}; fi
rm -rf out tmp
"""


def run_settings(manifest):
    """The settings of a run's tables as data products (closed JSON): the program, its database's name and version."""
    return {'program': PROGRAM, 'database': manifest['name'], 'database_version': manifest['version']}


def check_vitap_request(request, *, sequences, scope_subjects, resources):
    """The things to fix in a VITAP request, before anything runs; an empty list means it can run. ``request`` holds
    ``query_ref`` and ``resource_id``. The conditions: the query is a subject of the scope; it is DNA; the resource is
    local."""
    query = request['query_ref']
    problems = []
    if query not in scope_subjects:
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_sequence_of_the_scope',
                         'choose_from': [ref_ for ref_ in scope_subjects if ref_ in sequences]})
    if sequences[query] not in QUERY_MOLECULES:
        problems.append({'field': 'query_ref', 'code': 'vitap_takes_a_dna_query', 'query_molecule': sequences[query],
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


def _taxa(store, lineages, source, query_ref):
    """One ``taxon`` reference and one ``taxonomy_assignment`` observation for each lineage whose finest name resolved
    (one per taxon: the lineage with the highest score)."""
    best = {}
    for lineage in lineages:
        taxon = lineage['taxon']
        if taxon is not None and (taxon['taxon_id'] not in best or lineage['lineage_score'] > best[taxon['taxon_id']][1]):
            best[taxon['taxon_id']] = (taxon, lineage['lineage_score'])
    taxa, refs = [], []
    for row, score in best.values():
        reference = store.put('reference', {
            'reference_type': 'taxon', 'source_ref': source['id'], 'accession': str(row['taxon_id']), 'label': row['name'],
            'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='external')
        observation = store.put('observation', {
            'kind': 'taxonomy_assignment', 'subject_refs': [query_ref], 'source_subject_refs': [reference['id']],
            'source_ref': source['id'],
            'measurements': measurements(reference_ref=ref(reference['id']), model_score=number(score)),
            'dependencies': [query_ref, reference['id']], 'anchor': None}, origin='tool')
        taxa.append({'taxon_ref': reference['id'], 'observation_ref': observation['id'], 'taxon_id': row['taxon_id'],
                     'name': row['name'], 'rank_code': row['rank_code'], 'lineage_score': score})
        refs.extend([reference['id'], observation['id']])
    return taxa, refs


async def vitap_assignment(ctx, *, query_ref, resource_id, environment_directory, database_manifest_path,
                           taxonomy_manifest_path):
    """Run VITAP on the query on the local resource and keep the graded result. ``ctx`` is the tool's ``UnitContext`` of
    an episode that declares the service ``job_access``."""
    store = ctx.store
    manifest = json.loads(Path(database_manifest_path).read_text())
    record = store.get(query_ref)
    letters = store.get_artifact(record['sequence_ref']).decode('ascii').upper()
    manifest_ref = store.artifact(Path(database_manifest_path).read_bytes(), 'application/json')   # the database's identity
    taxonomy_ref = store.artifact(Path(taxonomy_manifest_path).read_bytes(), 'application/json')
    fasta = store.artifact(('>' + QUERY_NAME + '\n' + letters + '\n').encode(), 'text/x-fasta')
    script = SCRIPT.format(query=QUERY_FILE, database=manifest['directory'], log=LOG_FILE, best=BEST_FILE, all=ALL_FILE)
    command = ['/bin/bash', '-c', script]
    environment = {'PATH': str(Path(environment_directory) / 'bin') + ':/usr/bin:/bin'}
    request_ref = store.artifact(canonical({'command': command, 'database': run_settings(manifest)}), 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, command, environment, wait=True, inputs={QUERY_FILE: fasta},
                                          name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'])
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    if ran['returncode'] != 0 or LOG_FILE not in fetched:
        log = store.get_artifact(fetched[LOG_FILE]).decode(errors='replace')[-2000:] if LOG_FILE in fetched else ''
        return _outcome('failed', 'vitap_program_exit_nonzero' if ran['returncode'] != 0 else 'vitap_output_missing',
                        category='job', detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-1000:], 'log': log})
    try:
        grading = grade_vitap_assignment(
            best_text=store.get_artifact(fetched[BEST_FILE]).decode() if BEST_FILE in fetched else None,
            all_text=store.get_artifact(fetched[ALL_FILE]).decode() if ALL_FILE in fetched else None,
            sequence_name=QUERY_NAME, taxonomy=load_taxonomy(taxonomy_manifest_path))
    except ValueError as error:
        return _outcome('failed', str(error), category='grading')
    grading['database'] = {'name': manifest['name'], 'version': manifest['version']}
    sheet = grading['sheet']
    present = [name for name in PRODUCT_KINDS if name in fetched]
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=fetched[LOG_FILE], grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': fetched[LOG_FILE],
            'text_ref': None, 'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, request_ref, *(fetched[name] for name in present)],
            'operand_refs': [query_ref]}, origin='tool')
        taxa, written = _taxa(store, ([] if sheet['best'] is None else [sheet['best']]) + sheet['lineages'], source,
                              query_ref)
        labelled = [record_product(store, artifact_ref=fetched[name], kind=PRODUCT_KINDS[name], generated_by=source['id'],
                                   used=[record['sequence_ref'], manifest_ref, taxonomy_ref], settings=run_settings(manifest))
                    for name in present]
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[fetched[LOG_FILE], *(fetched[name] for name in present)],
                                                 derived_from=[row['id'] for row in labelled])
    refs = [source['id'], grading_ref, *(row['id'] for row in labelled), grading_product['id'], *written]
    best = sheet['best']
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'database': manifest['name'], 'database_version': manifest['version'], 'grading_ref': grading_ref,
                       'best': None if best is None else {
                           'taxon_id': None if best['taxon'] is None else best['taxon']['taxon_id'],
                           'lineage_score': best['lineage_score'], 'confidence_level': best['confidence_level'],
                           'unresolved_names': best['unresolved_names']},
                       'lineage_count': len(sheet['lineages']), 'taxa': taxa}, 'feedback': None}


__all__ = ['PROVIDER', 'QUERY_MOLECULES', 'check_vitap_request', 'run_settings', 'vitap_assignment']
