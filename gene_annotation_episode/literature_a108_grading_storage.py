"""Persist A108's purpose-specific contextual subscoring sheets and returns."""
from copy import deepcopy

from .domain import identity, obj
from .literature_a108_grading import (
    COMPONENTS, GRADER_TYPES, SCOPE, grade_context_evidence,
    grading_input_schema, grading_cell_schema, grading_sheet_schema,
)
from .literature_a108_grading_inputs import grading_population_schema, read_grading_inputs
from .literature_a108_storage import A108SheetRepository
from .scientific_findings import FindingIdentity

PROVIDER = 'literature.a108.context_grading'
VERSION = 'literature_a108_context_grading_record_v1'
NAMESPACE = 'literature_a108_grading_cells'
REQUESTED = 'requested_a108_grading_components'
OPERATION_DESCRIPTION = (
    'Populate the purpose-specific A108 subscoring sheet for actual organism-context observations. '
    'Select the biological grader and authenticate the target organism/context, original observations '
    'and source statements using literature passages or native context-record fields. Apply that '
    'grader\'s scientific criteria to each supporting, conflicting or unresolved contextual relation. '
    'The host calculates counts of original observations; do not supply scores. Each original '
    'observation has its own source-anchored literature_result reference, distinct from its paper; '
    'reuse that reference for repeated papers/database representations. Physiological literature '
    'statements can be evidence without assay measurements. Taxonomic identity, predicted function '
    'and search hits alone remain leads. Return only requested numerical components and their '
    'actual source/organism/condition qualifications.'
)


def grading_cells_schema():
    fields = deepcopy(grading_cell_schema()['properties'])
    fields.update({
        'sheet_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
        'assertion_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'},
        'target_context_ref': {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': 'context'},
        'grader_type': {'enum': list(GRADER_TYPES)},
    })
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}


def _rows(saved, sheet_ref, components):
    sheet = saved['sheet']
    return [dict(sheet_ref=sheet_ref,
        **{name: deepcopy(sheet[name]) for name in ('assertion_ref', 'target_context_ref', 'grader_type')},
        **deepcopy(sheet['cells'][component])) for component in components]


class LiteratureA108GradingRepository(A108SheetRepository):
    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = 'literature_a108_grading_operations'
    received_table = 'literature_a108_grading_received'
    requested = REQUESTED
    population_schema = staticmethod(grading_population_schema)
    input_schema = staticmethod(grading_input_schema)
    sheet_schema = staticmethod(grading_sheet_schema)
    cells_schema = staticmethod(grading_cells_schema)
    rows = staticmethod(_rows)

    def peer_repository(self):
        from .literature_a108_aggregation_storage import LiteratureA108AggregationRepository
        return LiteratureA108AggregationRepository(self.store, self.run_id)

    def read_inputs(self, context, arguments, *, read_record, read_source, retain_selection):
        normalizer = FindingIdentity(self.store)
        def original_identity(record, selected_sources):
            source_ref = record.get('source_ref')
            meaning = {'source_result': normalizer.entity(record['id'])}
            anchor = record.get('anchor')
            if anchor is not None:
                # These references denote original observations, not merely
                # entities with the same label. Two result statements at
                # different source locations must remain distinct even when
                # their literal labels happen to be identical.
                meaning['original_anchor'] = {
                    'source': normalizer.source(anchor['source_ref']),
                    **{name: deepcopy(anchor[name]) for name in
                        ('artifact_ref', 'start', 'end', 'quote')}}
            if source_ref is not None:
                read_record(source_ref)
            # Same actual publication metadata survives fresh source acquisition
            # IDs. Different anchors are not merged by their label. Other
            # representations reuse the original observation ref explicitly;
            # semantic equivalence is not guessed from prose.
            original_source = normalizer.source(source_ref) if source_ref is not None else None
            return {'key': identity('a108_original_observation', meaning),
                'source_ref': source_ref,
                'source_matches': source_ref is not None and any(
                    normalizer.source(ref) == original_source for ref in selected_sources)}
        return read_grading_inputs(arguments, read_source=read_source,
            read_record=read_record, canonical_observation=original_identity,
            retain_selection=retain_selection)

    @staticmethod
    def calculate(arguments, extraction):
        return grade_context_evidence(extraction)


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS',
    'OPERATION_DESCRIPTION', 'LiteratureA108GradingRepository', 'grading_cells_schema',
    'grading_population_schema']
