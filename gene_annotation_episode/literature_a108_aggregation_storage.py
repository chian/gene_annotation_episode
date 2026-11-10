"""Persist main A108 evidence counts over actually admitted subscoring cells."""
from copy import deepcopy

from .domain import ContractError, canonical, obj, validate_schema
from .literature_a108_aggregation import (
    COMPONENTS, SCOPE, aggregate_a108, aggregation_population_schema,
    aggregation_cell_schema, aggregation_sheet_schema,
)
from .literature_a108_grading_storage import LiteratureA108GradingRepository, grading_cells_schema
from .literature_a108_storage import A108SheetRepository

PROVIDER = 'literature.a108.aggregation'
VERSION = 'literature_a108_context_aggregation_record_v1'
NAMESPACE = 'literature_a108_aggregation_cells'
REQUESTED = 'requested_a108_aggregation_components'
OPERATION_DESCRIPTION = (
    'Populate the main A108 evidence scoring sheet from explicitly selected, possessed '
    'evidence_amount components of contextual subscoring sheets. Union original observation '
    'identities within physiology, environment, availability and localization and across '
    'all four domains. Preserve supporting, conflicting, overlapping and unresolved counts '
    'and their actual organism/condition qualifications. The total counts each assessed '
    'original observation once; it does not sum child totals, citation counts or repeated '
    'representations. Select the intended current assessments; competing revisions of '
    'one observation and contextual claim cannot be pooled. These are evidence counts, '
    'not annotation probabilities or an automatically installed continuation-credit rule.'
)


def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}


def _rows(saved, sheet_ref, components):
    return [dict(sheet_ref=sheet_ref, **deepcopy(saved['sheet']['cells'][name])) for name in components]


class LiteratureA108AggregationRepository(A108SheetRepository):
    def current_annotation_cells(self, context):
        """Resolve this owner's admitted current final cells without granting private inputs."""
        rows = ([row for row in self.received_cells(context) if row['component'] == 'overall']
            if self._installed(self.received_table) else [])
        from .literature_sheet_updates import current_scoring_sheets
        current = [row for row in current_scoring_sheets(self.store, context) if row['axis'] == 'A108']
        return ([cell for row in current if row['status'] == 'current'
            for cell in row['cells'] if cell['component'] == 'overall'] if current else rows)

    def annotation_contribution(self, store, context, *, target, annotation, scope,
                                comparison_ref=None, selection=None, details_limit=0, details_offset=0):
        from .communication import plain
        from .root_axis_scalars import _result, require_attribution, bind_contribution
        from .literature_a108_aggregation import annotation_scalar
        import json
        rows = [row for row in self.current_annotation_cells(context) if row['assertion_ref'] == annotation['id']
            and (comparison_ref is None or row.get('comparison_ref') == comparison_ref)
            and (selection is None or row['sheet_ref'] == selection)]
        refs, details = [], []
        if len(rows) != 1:
            reason = ('no_received_current_final_cell_for_this_question' if not rows else
                'multiple_current_axis_questions_require_explicit_sheet_selection')
            scalar = _result('A108', None, formula='received_current_axis_result_required',
                inputs={'sheet_refs': [row['sheet_ref'] for row in rows]}, reasons=[reason])
            transfer = {'status': 'unresolved', 'missing_inputs': [reason],
                'needed_refs': [], 'link_refs': [row['sheet_ref'] for row in rows]}
        else:
            cell = rows[0]
            refs = [cell['sheet_ref']]
            scalar = annotation_scalar(cell)
            subjects = set(annotation['subject_refs'])
            missing = (['contextual_assertion_not_bound_to_target'] if target not in subjects else
                ['pooled_context_score_has_no_individual_subject_attribution'] if subjects != {target} else [])
            transfer = {'status': 'invalid' if target not in subjects else 'unresolved' if missing else 'established',
                'missing_inputs': missing, 'needed_refs': [], 'link_refs': [cell['sheet_ref']]}
            source = store.get(cell['sheet_ref'])
            request = json.loads(store.get_artifact(source['request_ref']))
            if not store.scope_contains(request['scope'], plain(scope)):
                transfer = {**transfer, 'status': 'unresolved',
                    'missing_inputs': [*transfer['missing_inputs'], 'received_axis_result_does_not_cover_requested_scope']}
            scalar = require_attribution(scalar, missing=transfer['missing_inputs'])
            details = [{'source_ref': cell['sheet_ref'], 'target_ref': target,
                'proposed_annotation_ref': annotation['id'], 'scope': plain(scope), 'transfer': transfer}]
        scalar.update(question={'assertion_ref': annotation['id'], 'comparison_ref': comparison_ref},
            source_contribution_count=len(refs))
        return bind_contribution(scalar, annotation=annotation, subject=target, scope=scope,
            transfer=transfer, source_refs=refs), details[details_offset:details_offset + details_limit]


    provider = PROVIDER
    record_version = VERSION
    components = COMPONENTS
    operations_table = 'literature_a108_aggregation_operations'
    received_table = 'literature_a108_aggregation_received'
    requested = REQUESTED
    population_schema = staticmethod(aggregation_population_schema)
    input_schema = staticmethod(grading_cells_schema)
    sheet_schema = staticmethod(aggregation_sheet_schema)
    cells_schema = staticmethod(aggregation_cells_schema)
    rows = staticmethod(_rows)

    def peer_repository(self):
        return LiteratureA108GradingRepository(self.store, self.run_id)

    def read_inputs(self, context, arguments, *, read_record, read_source, retain_selection):
        read_record(arguments['assertion_ref'])
        if arguments['target_context_ref'] is not None:
            read_record(arguments['target_context_ref'])
        grouped = {}
        for selection in arguments['contributions']:
            grouped.setdefault(selection['sheet_ref'], []).append(selection['component'])
        if grouped and self._read_cells is None:
            raise ContractError('a108_aggregation_component_reader_unbound')
        native = LiteratureA108GradingRepository(self.store, self.run_id)
        rows = []
        for ref, components in grouped.items():
            read_record(ref)
            actual = self._read_cells(context, ref, components)
            validate_schema(actual, grading_cells_schema())
            if [(row['sheet_ref'], row['component']) for row in actual] != [(ref, name) for name in components]:
                raise ContractError('a108_aggregation_component_not_received')
            expected = native.fact_cells(context, [ref], components=components)
            if canonical(actual) != canonical(expected):
                raise ContractError('a108_aggregation_component_not_received')
            rows.extend(deepcopy(actual))
        return rows

    @staticmethod
    def calculate(arguments, extraction):
        return aggregate_a108(arguments, extraction)

    def calculation_context(self, context, arguments, extraction):
        from .literature_sheet_updates import a108_revision_context
        return a108_revision_context(self.store, context, extraction)

    @staticmethod
    def calculate_current(arguments, extraction, calculation_context):
        from .literature_sheet_updates import aggregate_current_a108
        return aggregate_current_a108(arguments, extraction, calculation_context)

    def validate_saved_inputs(self, saved):
        native = LiteratureA108GradingRepository(self.store, self.run_id)
        for row in saved['extraction']:
            actual = native.project_cells([row['sheet_ref']],
                permitted_record_refs=[row['sheet_ref']], components=[row['component']])
            if canonical(actual) != canonical([row]):
                raise ContractError('a108_aggregation_saved_component_mismatch')
        if 'calculation_context' in saved:
            current = self.calculate_current(saved['selection'], saved['extraction'],
                saved['calculation_context'])
            if canonical(current) != canonical(saved['sheet']):
                raise ContractError('a108_aggregation_saved_revision_projection_mismatch')


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS',
    'OPERATION_DESCRIPTION', 'LiteratureA108AggregationRepository', 'aggregation_cells_schema',
    'aggregation_population_schema']
