"""Independent synthetic cross-family checks; no actual model investigation.

Controlled decisions run the real shared method_loop and typed delivery. Neither
these synthetic measurements nor their passing arithmetic establishes A105
adequacy. No retained paper packet is opened by this module.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import partial
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_completion_time_inputs import LITERAL_FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_completion_time_prompt import COMPLETION_TIME_TASK
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_completion_time_storage import LiteratureCompletionTimeRepository, completion_time_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_product_partition_inputs import MEANINGS
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_product_partition_prompt import PRODUCT_PARTITION_TASK
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_product_partition_storage import LiteratureProductPartitionRepository, product_partition_cells_schema
from .unit_world import in_unit
RAW_NUMBERS = ('47.125713', '6.234891', '71.234567', '28.765433')
TEXT = 'Synthetic investigation. Single mixture and baseline mixture contain reference protein. Cleanup took >47.125713 h; baseline took <6.234891 min to equilibrium. Purification changed; heating also changed. Single mixture has component A 71.234567% and component B 28.765433%. NMR amount composition at equilibrium. Common selected denominator. Native construct. Fixed assay condition. Source describes these reports as approximate. One preparation; no independent repeat.'
TIME_REQUEST = ['completion_time_ratio']
PARTITION_REQUEST = ['selected_fraction_sum']
NUMERICAL_ENDPOINT = '71.234567% component A at 31 C'
FORM = obj({'times': completion_time_cells_schema(), 'partition': product_partition_cells_schema(), 'ordinary_credit': {'type': 'number', 'x-source': 'credit'}, 'interpretation': {'type': 'string', 'enum': ['partial']}})

def synthetic_inputs(store, *, numerical_endpoint=False):
    text = TEXT + (' For both duration reports, equilibrium is defined as ' + NUMERICAL_ENDPOINT + '.' if numerical_endpoint else '')
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_joined_audit_149', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']

    def witness(quote, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = text.index(quote, start + 1)
        return {'source_ref': source, 'representation': 'original', 'start': start, 'end': start + len(quote), 'quote': quote}

    def interpreted(value, quote='equilibrium'):
        return {'value': value, 'witnesses': [] if value == 'unknown' else [witness(quote)]}
    broad = 'Cleanup took >47.125713 h; baseline took <6.234891 min to equilibrium.'

    def time(number, unit, preparation):
        unit_start = text.index(number) + len(number) + 1
        return {**dict.fromkeys(LITERAL_FIELDS), 'subject': witness('reference protein'), 'construct': witness('Native construct'), 'preparation': witness(preparation), 'condition': witness('31 C' if numerical_endpoint else 'Fixed assay condition'), 'endpoint': witness(NUMERICAL_ENDPOINT if numerical_endpoint else 'equilibrium'), 'measurement_identity': witness('Single mixture' if preparation == 'Cleanup' else 'baseline mixture'), 'measurement': {'number': {'witness': witness(number), 'number_start': 0, 'number_end': len(number)}, 'unit': {'source_ref': source, 'representation': 'original', 'start': unit_start, 'end': unit_start + len(unit), 'quote': unit}}, 'qualification': interpreted('source_qualified_approximate', 'Source describes these reports as approximate')}
    times = {'source_ref': source, 'source_kind': 'synthetic_fixture', 'experiment': witness(broad), 'intended_change': witness('Purification'), 'other_changes': [witness('heating also changed')], 'comparison': {'endpoint_relation': interpreted('same'), 'preparation_relation': interpreted('different'), 'pair_relationship': interpreted('supported'), 'other_changes_status': interpreted('partial')}, 'quantities': {'numerator': time(RAW_NUMBERS[0], 'h', 'Cleanup'), 'denominator': time(RAW_NUMBERS[1], 'min', 'baseline')}}

    def fraction(number, compound, occurrence):
        meanings = dict.fromkeys(MEANINGS)
        meanings.update(subject=witness('reference protein'), construct=witness('Native construct'), preparation=witness('Single mixture'), compound=witness(compound), endpoint=witness('equilibrium'), condition=witness('Fixed assay condition'), stage=witness('equilibrium'), denominator=witness('Single mixture has component A 71.234567% and component B 28.765433%'), measurement_basis=witness('NMR amount composition'), measurement_identity=witness('Single mixture' if occurrence == 0 else 'component B'))
        return {'meanings': meanings, 'measurement': {'number': {'witness': witness(number), 'number_start': 0, 'number_end': len(number)}, 'unit': witness('%', occurrence)}, 'basis': interpreted('amount_fraction', 'NMR amount composition'), 'stage': interpreted('equilibrium'), 'qualification': interpreted('source_qualified_approximate', 'Source describes these reports as approximate')}
    partition = {'source_ref': source, 'source_kind': 'synthetic_fixture', 'experiment': witness('Synthetic investigation'), 'quantities': {'a': fraction(RAW_NUMBERS[2], 'component A', 0), 'b': fraction(RAW_NUMBERS[3], 'component B', 1)}, 'relationships': {field: interpreted('supported', 'Common selected denominator') for field in ('same_preparation', 'same_endpoint', 'shared_denominator')}, 'evidence': [{'role': 'repetition_basis', 'witness': witness('One preparation; no independent repeat')}, {'role': 'composition', 'witness': witness('component A 71.234567% and component B 28.765433%')}]}
    return (source, artifact, times, partition)

@in_unit
def test_both_optional_cold_repositories_read_nothing_and_write_nothing(store, ctx):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'annotation', (('annotation', 'receiver'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {}, {}, [])
    before = store.refs()
    for cls in (LiteratureCompletionTimeRepository, LiteratureProductPartitionRepository):
        repo = cls(store, context.run_id)
        assert repo.received_cells(context) == []
        assert repo.project_cells([], permitted_record_refs=[], components=[]) == []
    assert store.refs() == before
