"""One HMMER profile scan: the check of the request, and the scan as one unit.

The episode's model fills out one request: ``query_ref``, ``database``, ``resource_id``. Two functions of this
module do the rest, deterministically:

``check_profile_scan_request`` examines the request against what the episode holds and the bound resources, before
anything runs. It returns the things to fix (one entry per problem: the field, a code and what to choose from); an
empty list means the request can run. The episode's ``action`` rejects a request with problems, so no unit is made.

``hmmer_profile_scan`` runs a request that passed the check, as one unit, in this order:

1. read the query sequence through custody and make its FASTA file as an artifact;
2. build the ``hmmscan`` job with the library's native HMMER job contract (``native_hmmer_contracts``): the pressed
   profile database of the manifest, the query, the family gathering cutoffs (``--cut_ga``: each profile's own
   trained threshold decides what is reported) and one CPU;
3. run it on the local resource through the inspection point (``execute_on_local_resource`` with ``wait=True``);
4. grade the three native texts (the report and the two tables) with the library's HMMER grader into the search
   sheet and its scores;
5. keep the grading through custody: the grading artifact, a ``native.hmmer.hmmscan`` source over the domain table
   (its operand is the query), one ``family`` reference for each profile that matched (its accession and name are
   the profile database's own) and one ``profile_match`` observation for each matched domain (the query's interval
   and the measurements of the already graded domain row), in the shape the registry gives a profile match.

Grading is not a choice of anyone: it follows the fetch in the same unit.

The outcome has the shape of every tool outcome of an episode. ``completed``: ``record_refs`` are the source, the
grading artifact, the references and the observations, and ``result`` holds, for each matched family, its reference,
its accession and name, its observations and the numbers of its graded domains. A scan that matched no family is
completed with no family. What can still go wrong after a passed check is a fault of the environment: a ``failed``
outcome with its code and ``retryable`` false, reported once."""
import hashlib
import json
from pathlib import Path

from episode_runtime.job_access import job_handle

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_hmmer_contracts import (
    requested_job_from_native)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    comparison_weight, hmmer_comparisons)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_graders import (
    HMMER_DOMAIN_METRICS, grade_hmmer_native_artifacts)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import (
    find_reusable, record_product)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    enum, measurements, number, ref)

JOB_NAME = 'hmmer_profile_scan'
PROGRAM = 'hmmscan'
PROVIDER = 'native.hmmer.hmmscan'
QUERY_ROLE, QUERY_FILE = 'query_sequence', 'query_sequence.fasta'
OPTIONS = ['--cut_ga', '--cpu', '1']
# role -> (format, file in the job's directory); the route writes the two logs under these names
OUTPUTS = {'stdout': ('hmmer_stdout', 'stdout.log'), 'stderr': ('text', 'stderr.log'),
           'tblout': ('protein_tblout', 'hmmscan.tblout'), 'domtblout': ('protein_domtblout', 'hmmscan.domtblout')}
GRADED_ROLES = ('stdout', 'tblout', 'domtblout')
PRODUCT_KIND = 'profile_scan_results'


def scan_settings(manifest):
    """The settings of a scan's domain table as a data product (closed JSON): the program, the profile database's name
    and version and the cut-off option (``OPTIONS`` without the CPU count, which does not change the result)."""
    return {'program': PROGRAM, 'database': manifest['name'], 'database_version': manifest['version'],
            'cutoff': OPTIONS[0]}


def check_profile_scan_request(request, *, sequences, scope_subjects, resources, made):
    """The things to fix in a profile scan request, before anything runs; an empty list means it can run.

    ``request`` holds ``query_ref`` (a key of ``sequences``), ``database`` (a configured profile database) and
    ``resource_id`` (a key of ``resources``); the caller's schema has already bound each to those sets.
    ``sequences`` is ``{record: molecule}`` of the sequence records the episode holds, ``scope_subjects`` the
    subjects of its scope, ``resources`` ``{resource id: kind}`` and ``made`` ``{(query, database): 'completed' |
    'failed'}`` of the scans the episode already holds or already saw fail. The conditions:

    1. the query is a subject of the episode's scope;
    2. the query is a protein (the profiles are protein families);
    3. the resource is a local resource;
    4. the same scan (query, database) is not already held;
    5. the same scan has not already failed."""
    query = request['query_ref']
    problems = []
    if query not in scope_subjects:
        problems.append({'field': 'query_ref', 'code': 'query_is_not_a_sequence_of_the_scope',
                         'choose_from': [ref for ref in scope_subjects if ref in sequences]})
    if sequences[query] != 'protein':
        problems.append({'field': 'query_ref', 'code': 'profile_scan_takes_a_protein_query',
                         'query_molecule': sequences[query],
                         'choose_from': [ref for ref in scope_subjects if sequences.get(ref) == 'protein']})
    if resources[request['resource_id']] != 'local':
        problems.append({'field': 'resource_id', 'code': 'resource_is_not_local',
                         'choose_from': [name for name, kind in resources.items() if kind == 'local']})
    if (query, request['database']) in made:
        problems.append({'field': 'database', 'code': {
            'completed': 'scan_already_held', 'failed': 'scan_already_failed_and_cannot_be_retried'}[
                made[query, request['database']]]})
    return problems


def record_scan_product(store, *, source_ref, domtblout_ref, sequence_ref, manifest_ref, manifest):
    """Label the scan's domain table ``domtblout_ref`` as a ``profile_scan_results`` data product and return its row:
    generated by the scan's source record, made from the query's sequence artifact and the profile database's manifest
    (its artifact is the database's identity), with the scan's settings."""
    return record_product(store, artifact_ref=domtblout_ref, kind=PRODUCT_KIND, generated_by=source_ref,
                          used=[sequence_ref, manifest_ref], settings=scan_settings(manifest))


def _outcome(status, code, *, category, detail=None):
    feedback = {'category': category, 'code': code, 'retryable': False}
    if detail is not None:
        feedback['detail'] = detail
    return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': feedback}


def _job(store, directory, query_ref, residues, manifest, executable_directory):
    """The requested ``hmmscan`` job of the query against the manifest's pressed database, with the file it stages."""
    data = ('>' + QUERY_ROLE + '\n' + residues + '\n').encode()
    artifact = store.artifact(data, 'text/x-fasta')
    executable = (Path(executable_directory) / PROGRAM).resolve()
    operands = [{'role': role, 'path': row['path'], 'format': row['format'], 'sha256': row['sha256'],
                 'size_bytes': row['size_bytes'], 'artifact_ref': None} for role, row in manifest['files'].items()]
    operands.append({'role': QUERY_ROLE, 'path': str(directory / QUERY_FILE), 'format': 'fasta',
                     'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data), 'artifact_ref': artifact})
    requested = requested_job_from_native({
        'version': 'native_hmmer_job_v1', 'program': PROGRAM, 'mode': 'search',
        'software': {'executable': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                     'engine_version': None},
        'environment': {}, 'operands': operands,
        'operand_bindings': [{'operand_role': QUERY_ROLE, 'record_ordinal': 0, 'native_name': QUERY_ROLE,
                              'native_accession': None, 'subject_ref': query_ref, 'reference_ref': None}],
        'options': list(OPTIONS),
        'outputs': [{'role': role, 'format': kind, 'relative_path': name} for role, (kind, name) in OUTPUTS.items()],
        'metadata': {'database': manifest['name'], 'database_version': manifest['version'],
                     'model_count': manifest['model_count']},
        'grading_parameters': {}})
    return requested, {QUERY_FILE: artifact}


def _blocks(positions):
    """The contiguous blocks ``[start, end)`` of the paired query positions."""
    blocks = []
    for start, end in positions:
        if blocks and blocks[-1][1] == start:
            blocks[-1][1] = end
        else:
            blocks.append([start, end])
    return blocks


def _families(store, grading, source, query_ref):
    """One ``family`` reference for each matched profile and one ``profile_match`` observation for each of its
    domains, projected from the already graded rows (nothing is calculated or graded again)."""
    hits = {row['target_name']: row for row in grading['sheet']['hits']}
    scores = {row['record_key']: row for row in grading['scores']['domains']}
    model = store.put('context', {'context_type': 'processing', 'name': 'protein_search_model',
                                  'source_ref': source['id'], 'attributes': measurements(molecule_model=enum('protein')),
                                  'related_refs': [query_ref]}, origin='tool')
    families, refs = {}, [model['id']]
    for row in hmmer_comparisons(grading):
        hit, score = hits[row['target_name']], scores[row['native_record_key']]
        if row['target_name'] not in families:
            reference = store.put('reference', {
                'reference_type': 'family', 'source_ref': source['id'], 'accession': hit['target_accession'],
                'label': hit['target_name'], 'sequence_ref': None, 'molecule': None, 'length': None,
                'term_refs': [], 'context_refs': []}, origin='external')
            families[row['target_name']] = {'profile_ref': reference['id'], 'accession': hit['target_accession'],
                                            'name': hit['target_name'], 'observation_refs': [], 'domains': []}
            refs.append(reference['id'])
        family = families[row['target_name']]
        values = measurements(reference_ref=ref(family['profile_ref']), profile_ref=ref(family['profile_ref']),
                              bitscore=number(row['bits']), evalue=number(row['native_evalue']))
        values += [{'name': name, 'value': number(score[name])} for name in HMMER_DOMAIN_METRICS
                   if type(score.get(name)) in (int, float)]
        observation = store.put('observation', {
            'kind': 'profile_match', 'subject_refs': [query_ref], 'source_subject_refs': [family['profile_ref']],
            'source_ref': source['id'], 'measurements': values,
            'dependencies': [query_ref, family['profile_ref'], model['id']], 'anchor': None,
            'operand_intervals': [{'role': 'query', 'subject_ref': query_ref, 'start': start, 'end': end,
                                   'unit': 'aa', 'model_unit': 'aa'}
                                  for start, end in _blocks(row['target_intervals'])]}, origin='tool')
        family['observation_refs'].append(observation['id'])
        family['domains'].append({'query_start': row['target_intervals'][0][0],
                                  'query_end': row['target_intervals'][-1][1], 'domain_score_bits': row['bits'],
                                  'independent_evalue': row['native_evalue'],
                                  'model_paired_fraction': row['reference_paired_count'] / row['reference_length'],
                                  'match_strength': comparison_weight(row)['weight']})
        refs.append(observation['id'])
    return list(families.values()), refs


async def hmmer_profile_scan(ctx, *, query_ref, database, resource_id, executable_directory, manifest_path):
    """Scan the query against the profile database of ``manifest_path`` on the local resource and keep the graded
    family matches. ``ctx`` is the tool's ``UnitContext`` of an episode that declares the service ``job_access``."""
    store, access = ctx.store, ctx.services['job_access']
    manifest = json.loads(Path(manifest_path).read_text())
    record = store.get(query_ref)
    residues = store.get_artifact(record['sequence_ref']).decode('ascii').upper()
    manifest_ref = store.artifact(Path(manifest_path).read_bytes(), 'application/json')   # the database's identity
    directory = Path(access.describe(resource_id)['workspace']) / job_handle(ctx.operation_key, resource_id, JOB_NAME)
    requested, inputs = _job(store, directory, query_ref, residues, manifest, executable_directory)
    request_ref = store.artifact(canonical(requested), 'application/json')
    ran = await execute_on_local_resource(ctx, resource_id, requested['argv'], requested['environment'], wait=True,
                                          inputs=inputs, name=JOB_NAME)
    if ran['status'] != 'completed':
        refused = (ran['launch'] if ran['launch']['status'] != 'completed' else ran['fetch'])['failure']
        return _outcome('failed', refused['code'], category='job', detail=refused['detail'])
    if ran['returncode'] != 0:
        return _outcome('failed', 'hmmer_profile_scan_program_exit_nonzero', category='job',
                        detail={'returncode': ran['returncode'], 'stderr': ran['stderr'][-2000:]})
    fetched = {item['name']: item['ref'] for item in ran['fetch']['results']}
    artifact_refs = {role: fetched[OUTPUTS[role][1]] for role in GRADED_ROLES}
    try:
        grading = grade_hmmer_native_artifacts(
            program=PROGRAM, artifacts={role: store.get_artifact(artifact_refs[role]).decode() for role in GRADED_ROLES},
            artifact_refs=artifact_refs, engine_version=None,
            inputs={'query': {'name': QUERY_ROLE, 'kind': 'protein_sequence', 'alphabet': 'amino',
                              'length': len(residues), 'sequence': residues},
                    'database': {'name': manifest['name'], 'version': manifest['version'],
                                 'population': manifest['model_count']},
                    'native_parameters': {'options': list(OPTIONS)}})
    except (ValueError, ContractError) as error:
        return _outcome('failed', str(error), category='grading')
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=artifact_refs['domtblout'],
                                          grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': manifest['name'], 'uri': None, 'artifact_ref': artifact_refs['domtblout'],
            'text_ref': None, 'request_ref': None, 'version': manifest['version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, request_ref, artifact_refs['tblout'], artifact_refs['stdout']],
            'operand_refs': [query_ref]}, origin='tool')
        families, written = _families(store, grading, source, query_ref)
        product = record_scan_product(store, source_ref=source['id'], domtblout_ref=artifact_refs['domtblout'],
                                       sequence_ref=record['sequence_ref'], manifest_ref=manifest_ref,
                                       manifest=manifest)
    refs = [source['id'], grading_ref, product['id'], *written]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'database': manifest['name'], 'database_version': manifest['version'],
                       'profiles_searched': manifest['model_count'], 'product_ref': product['id'], 'family_count': len(families),
                       'grading_ref': grading_ref, 'families': families}, 'feedback': None}


__all__ = ['PROVIDER', 'check_profile_scan_request', 'hmmer_profile_scan', 'record_scan_product', 'scan_settings']
