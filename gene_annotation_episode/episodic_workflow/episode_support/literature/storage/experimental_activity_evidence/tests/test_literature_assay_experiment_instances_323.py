"""Multiple experiments share a template without overwriting parent evidence."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_worksheet import VERSION, a105_worksheet_template
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository, REQUESTED, NAMESPACE, PROVIDER
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_a105_assay_type_binding_322 import grading_fixture

def two_experiments(store):
    context, first, artifact = grading_fixture(store)
    text = store.get_artifact(artifact).decode()
    quote = 'Experiment B'
    start = text.index(quote)
    original = store.get(first['experiment_ref'])
    record = {k: deepcopy(v) for k, v in original.items() if k not in ('id', 'record_type', 'origin')}
    record.update(accession='synthetic_assay_B', label=quote, anchor={'source_ref': first['source_ref'], 'artifact_ref': artifact, 'start': start, 'end': start + len(quote), 'quote': quote})
    experiment = store.put('reference', record, origin='caller')['id']
    second = deepcopy(first)
    second['experiment_ref'] = experiment
    for role, label, token, unit in (('effect', 'effect', '0.2', 'fraction'), ('effect_variance', 'variance', '0.09', 'fraction_squared')):
        fragment = f'{label} {token} {unit}'
        offset = text.index(fragment, start)
        witness = {'source_ref': first['source_ref'], 'representation': 'original', 'start': offset, 'end': offset + len(fragment), 'quote': fragment}
        unit_start = offset + len(label) + len(token) + 2
        second['quantities'][role] = {'kind': 'source_number', 'number': {'witness': witness, 'number_start': len(label) + 1, 'number_end': len(label) + 1 + len(token)}, 'unit': {**witness, 'start': unit_start, 'end': unit_start + len(unit), 'quote': unit}, 'origin': 'synthetic'}
    return (replace(context, received_record_refs=[*context.received_record_refs, experiment]), first, second)


def test_new_assessments_require_possessed_source_anchored_experiment_identity(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        missing = deepcopy(args)
        del missing['experiment_ref']
        with pytest.raises(ContractError, match='experiment_reference_required'):
            repo.populate(context, missing, 'missing')
        wrong = deepcopy(args)
        wrong['experiment_ref'] = args['assertion_ref']
        with pytest.raises(ContractError, match='anchored_support_required'):
            repo.populate(context, wrong, 'wrong')
        refs = [ref for ref in context.received_record_refs if ref != args['experiment_ref']]
        with pytest.raises(ContractError, match='record_not_received'):
            repo.populate(replace(context, received_record_refs=refs), args, 'unreceived')


