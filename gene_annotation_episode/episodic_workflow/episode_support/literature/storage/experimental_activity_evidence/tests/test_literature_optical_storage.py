"""Synthetic selected optical persistence, saved integrity and exact typed subsets."""
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_optical_inputs import read_optical_rate_operands
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_optical_storage import LiteratureOpticalRepository, optical_cells_schema
from .unit_world import in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_optical_storage import OPERATIONS
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_optical_inputs import fixture, witness, SOURCE, TEXT, PRIMITIVE_ORDER
SUFFIX = ' Molecule reference-R; construct reference-RC; preparation reference-RP; condition buffer-B; measured NADH.'

def setup(store, ctx, *, covariance=True, status='known', text=TEXT + SUFFIX, change=None, operands=None):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_optical_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    args = fixture(text, **operands or {})[0]
    for field, quote in (('molecule', 'reference-R'), ('construct', 'reference-RC'), ('preparation', 'reference-RP'), ('condition', 'buffer-B'), ('measured_entity', 'NADH')):
        args[field] = witness(text, quote)
    if change:
        change(args)

    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    refs = [source]

    def read(ref, representation):
        row = store.get(ref)
        key = row['artifact_ref'] if representation == 'original' else row['text_ref']
        return {'artifact_ref': key, 'content': store.get_artifact(key)}
    if covariance:
        ex = read_optical_rate_operands(args, read_source=read)
        rows = [ex['signals']['sample'], ex['signals']['blank'], ex['calibration']['epsilon'], ex['calibration']['path_length']]
        data = {'version': 'a105_optical_covariance', 'primitive_order': list(PRIMITIVE_ORDER), 'primitive_measurement_keys': [r['measurement_key'] for r in rows], 'primitive_physical_observation_keys': [r['physical_observation_key'] for r in rows], 'primitive_owner_keys': [r['owner_key'] for r in rows], 'primitive_units': [r['unit']['raw_unit'] for r in rows], 'covariance': [[1e-08, 5e-09, 0, 0], [5e-09, 1e-08, 0, 0], [0, 0, 10000, 0], [0, 0, 0, 0.01]], 'origin': 'synthetic', 'covariance_status': status}
        cov_artifact = store.artifact(canonical(data), 'application/json')
        cov_source = store.put('source', {'provider': 'synthetic_optical_covariance', 'accession': None, 'uri': None, 'artifact_ref': cov_artifact, 'text_ref': cov_artifact, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': [source]}, origin='caller')['id']
        refs.append(cov_source)
        args['covariance_source_ref'] = cov_source
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment', 'question_context_refs': [], 'source_refs': [source]}, {}, refs)
    return (store, context, args)

















