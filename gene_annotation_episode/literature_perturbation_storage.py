"""Selected reference perturbation components; no target transfer or credit."""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_perturbation_inputs import perturbation_population_schema, read_perturbation_inputs
from .literature_perturbation_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, populate_source_restoration, populate_source_summary_restoration,
)

PROVIDER = 'literature.experimental.perturbation'
FORMULA_CODES = {name: 'perturbation_' + name + '_v1' for name in COMPONENTS}
BINDINGS = {'assayed_subject_ref': ('molecule', 'reference'),
    'recipient_ref': ('recipient', 'reference'), 'donor_ref': ('donor', 'reference'),
    'experiment_ref': ('experiment', 'reference'), 'reference_arm_ref': ('reference_arm', 'reference'),
    'perturbed_arm_ref': ('perturbed_arm', 'reference'), 'restored_arm_ref': ('restored_arm', 'reference'),
    'partner_ref': ('partner', 'reference'), 'endpoint_ref': ('endpoint', 'term'),
    'normalization_ref': ('normalization', 'term'), 'condition_ref': ('condition', 'context'),
    'intended_change_ref': ('intended_change', 'term')}


def _metadata(extraction):
    return {**{name: extraction[name] for name in ('design', 'measurement_status',
        'same_endpoint_scope', 'amount_role', 'orientation', 'data_origin', 'endpoint_unit', 'exposure_unit')},
        'operand_source_kind': extraction['source_kind'],
        'uncertainty_basis': extraction['uncertainty_basis'],
        'index_kind': 'proposed_source_restoration_index',
        'evaluated_scope': 'interpreted_reference_perturbation'}


class LiteraturePerturbationRepository(LiteratureRateRepository):
    provider = PROVIDER
    components = COMPONENTS
    record_version = 'literature_perturbation_record_v1'
    operations_table = 'literature_perturbation_operations'
    received_table = 'literature_perturbation_received'
    binding_fields = tuple(BINDINGS)

    def _provenance(self, context, reference):
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('literature_source_outside_scope')
        source = self.store.get(reference)
        if source['record_type'] != 'source':
            raise ContractError('literature_source_required')
        return source

    def _source(self, context, reference):
        if reference not in context.received_record_refs:
            raise ContractError('literature_source_not_received')
        source = self._provenance(context, reference)
        page = context.assignment if context.role == 'literature_page' else context.assignment.get('page')
        if page:
            pending, seen = [reference], set()
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                ancestor = self._provenance(context, current)
                if current == page['source_ref']:
                    break
                pending.extend(ancestor.get('parent_source_refs', ()))
            else:
                raise ContractError('literature_reading_outside_assigned_source')
        return source

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, perturbation_population_schema())
        signature = canonical({'arguments': args, 'scope': plain(context.scope)})
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} '
            'WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone()
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            saved = self.read(outcome['result']['sheet_ref'])
            for ref in saved['direct_input_source_refs']:
                self._source(context, ref)
            for ref in saved['input_source_refs']:
                self._provenance(context, ref)
            if 'experiment_assessment' in args:
                from .literature_perturbation_assessments import authorize_assessment
                authorize_assessment(self, context, args['experiment_assessment'])
            return outcome
        assessment = args.get('experiment_assessment')
        if assessment is not None:
            from .literature_perturbation_assessments import authorize_assessment
            authorize_assessment(self, context, assessment)
        source = self._source(context, args['source_ref'])
        def read_source(reference, representation):
            row = self._source(context, reference)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        extraction = read_perturbation_inputs(args, read_source=read_source)
        origin = extraction['data_origin'] or {'primary_source': 'reported',
            'retained_extraction': 'derived', 'graph_extraction': 'graph_derived',
            'synthetic_fixture': 'synthetic'}[args['source_kind']]
        summary = extraction['version'] == 'a106_perturbation_inputs_v2'
        if summary:
            sheet = populate_source_summary_restoration(extraction, origin=origin)
        else:
            sheet = populate_source_restoration({**{name: extraction[name] for name in (
                'values', 'measurement_keys', 'endpoint_unit', 'exposure_unit', 'design',
                'measurement_status', 'same_endpoint_scope', 'amount_role', 'orientation')}, 'origin': origin})
        direct = extraction['source_refs']
        parents = list(direct)
        for ref in direct:
            for parent in self.store.get(ref).get('parent_source_refs', ()):
                self._provenance(context, parent)
                parents.append(parent)
        if assessment is not None:
            parents.append(self.store.get(assessment['experiment_ref'])['source_ref'])
            if assessment['revises_sheet_ref'] is not None:
                parents.append(assessment['revises_sheet_ref'])
        parents = list(dict.fromkeys(parents))
        record_version = 'literature_perturbation_record_v2' if summary else self.record_version
        payload = {'version': record_version, 'input_source_ref': source['id'],
            'input_artifact_ref': source['artifact_ref'], 'input_source_refs': parents,
            'direct_input_source_refs': direct, 'extraction': extraction, 'sheet': sheet,
            'data_source_ref': args['data_source_ref']}
        with self.store.transaction():
            if assessment is not None:
                from .literature_perturbation_assessments import check_revision
                check_revision(self, assessment)
            created = []
            def publish(kind, record):
                candidate = identity(kind, {'origin': 'tool', 'record': record})
                existed = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (candidate,)).fetchone()
                row = self.store.put(kind, record, origin='tool', scope=plain(context.scope))
                if existed is None:
                    created.append(row['id'])
                return row['id']
            bindings = {}
            for field, (literal, kind) in BINDINGS.items():
                if field == 'experiment_ref' and assessment is not None:
                    bindings[field] = assessment['experiment_ref']
                    continue
                item = extraction['literals'][literal]
                if item is None:
                    bindings[field] = None
                    continue
                witness = item['witness']
                common = {'source_ref': witness['source_ref']}
                accession = identity('perturbation_literal', {'field': literal,
                    'source_ref': witness['source_ref'], 'artifact_ref': witness['artifact_ref'],
                    'start': witness['start'], 'end': witness['end']})
                if kind == 'reference':
                    record = {**common, 'reference_type': 'assay', 'accession': accession,
                        'label': item['value'], 'sequence_ref': None, 'molecule': None,
                        'length': None, 'term_refs': [], 'context_refs': []}
                elif kind == 'term':
                    record = {**common, 'namespace': 'literature_perturbation_' + literal,
                        'accession': accession, 'label': item['value'], 'term_type': 'other', 'anchor': None}
                else:
                    record = {**common, 'context_type': 'assay_condition', 'name': item['value'],
                        'attributes': [], 'related_refs': []}
                bindings[field] = publish(kind, record)
            if assessment is not None:
                # The source's literal label is still retained in extraction;
                # the stable assay identity spans alternate representations.
                bindings['experiment_ref'] = assessment['experiment_ref']
                payload['experiment_assessment'] = deepcopy(assessment)
            payload['experimental_bindings'] = bindings
            covariance_refs = []
            if summary:
                from .literature_perturbation_summary_storage import publish_covariance_meanings
                covariance_bindings, covariance_refs = publish_covariance_meanings(extraction, sheet, publish)
                if covariance_bindings is not None:
                    payload['covariance_support_bindings'] = covariance_bindings
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request = self.store.artifact(canonical({'run_id': self.run_id, 'episode_id': context.episode_id,
                'operation_key': operation_key, 'arguments': args}), 'application/json')
            sheet_ref = publish('source', {'provider': PROVIDER, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                'version': record_version, 'retrieved_at': None, 'parent_source_refs': parents})
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {
                'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}),
                'record_refs': list(dict.fromkeys([sheet_ref, *parents, *(ref for ref in bindings.values() if ref), *covariance_refs])),
                'changed_record_refs': created, 'result': {'sheet_ref': sheet_ref,
                    'cells': sheet['cells'], 'assay_interpretation': extraction['literals'],
                    **_metadata(extraction)}, 'feedback': None}
            if assessment is not None:
                outcome['result']['experiment_assessment'] = deepcopy(assessment)
                previous = assessment['revises_sheet_ref']
                if previous is not None:
                    outcome['record_refs'].append(previous)
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def read(self, sheet_ref):
        if self.store.get(sheet_ref).get('version') == 'literature_perturbation_record_v2':
            return self.summary_projection().read(sheet_ref)
        saved = super().read(sheet_ref)
        source = self.store.get(sheet_ref)
        request = json.loads(self.store.get_artifact(source['request_ref']))
        if (source['version'] != self.record_version
                or saved['data_source_ref'] != request['arguments']['data_source_ref']
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']):
            raise ContractError('literature_perturbation_sheet_source_mismatch')
        from .literature_perturbation_assessments import validate_saved_assessment
        validate_saved_assessment(self, saved, request)
        return saved

    def current_assessments(self):
        from .literature_perturbation_assessments import current_assessments
        return current_assessments(self)

    def assessment_history(self, sheet_ref):
        from .literature_perturbation_assessments import assessment_history
        return assessment_history(self, sheet_ref)

    def summary_projection(self):
        if not hasattr(self, '_summary_projection'):
            from .literature_perturbation_summary_storage import LiteraturePerturbationSummaryProjection
            self._summary_projection = LiteraturePerturbationSummaryProjection(self.store, self.run_id)
        return self._summary_projection

    def validate_empty_return_family(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        versions = set()
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)):
            outcome = json.loads(row['outcome'])
            if outcome.get('status') == 'completed':
                source = self.store.get(outcome['result']['sheet_ref'])
                if source.get('provider') == PROVIDER:
                    versions.add(source.get('version'))
        if self.record_version not in versions and versions & {'literature_perturbation_record_v1', 'literature_perturbation_record_v2'}:
            raise ContractError('literature_perturbation_projection_version_mismatch')

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        components = self.components if components is None else components
        if (not isinstance(components, (list, tuple))
                or any(not isinstance(name, str) or name not in self.components for name in components)
                or len(set(components)) != len(components)):
            raise ContractError('literature_perturbation_component_selection_invalid')
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref)
            if saved['version'] != self.record_version:
                raise ContractError('literature_perturbation_projection_version_mismatch')
            for name in components:
                cell = {key: deepcopy(value) for key, value in saved['sheet']['cells'][name].items() if key != 'formula'}
                rows.append({'sheet_ref': ref, 'evidence_source_ref': saved['input_source_ref'],
                    'data_source_ref': saved['data_source_ref'], **saved['experimental_bindings'],
                    'component': name, **cell, 'formula_code': FORMULA_CODES[name], **_metadata(saved['extraction'])})
        validate_schema(rows, perturbation_cells_schema())
        return rows


def perturbation_cells_schema():
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    properties = {'sheet_ref': dict(source), 'evidence_source_ref': dict(source),
        'data_source_ref': {**source, 'type': ['string', 'null']},
        **{field: {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': kind}
           for field, (_, kind) in BINDINGS.items()},
        'component': {'type': 'string', 'enum': list(COMPONENTS), 'description':
            'Native reference/perturbed/restored outcomes and separate effect, restoration, nuisance amount and isolation components. The reference index combines their declared orientation and proposed conventions; it is not target correspondence or probability. Joint uncertainty remains unreported.'},
        'value': {'type': ['number', 'null']},
        'unit': {'type': 'string', 'enum': ['unreported', 'events_per_100000_cells', 'fraction',
            'CFU_per_mL', 'minutes', 'per_min', 'dimensionless']},
        'status': {'type': 'string', 'enum': ['populated', 'unavailable']},
        'formula_code': {'type': 'string', 'enum': list(FORMULA_CODES.values())},
        'origin': {'type': 'string', 'enum': ['reported', 'derived', 'graph_derived', 'synthetic', 'proposed']},
        'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]},
        'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': list(CONDITIONAL_CODES)}},
        'design': {'type': 'string', 'enum': ['native_deletion_restoration', 'selective_perturbation_restoration',
            'cas_free_reconstitution', 'variant_replacement', 'other_explicit', 'unknown', 'conflicting']},
        'measurement_status': {'type': 'string', 'enum': ['validated_ratio_scale', 'qualitative_only', 'unknown', 'conflicting']},
        'same_endpoint_scope': {'type': 'string', 'enum': ['yes', 'no', 'unknown', 'conflicting']},
        'amount_role': {'type': 'string', 'enum': ['nuisance', 'intended_change', 'unknown']},
        'orientation': {'type': ['integer', 'null'], 'enum': [None, -1, 1]},
        'data_origin': {'type': ['string', 'null'], 'enum': [None, 'reported', 'graph_derived', 'synthetic']},
        'operand_source_kind': {'type': 'string', 'enum': ['primary_source', 'retained_extraction', 'graph_extraction', 'synthetic_fixture']},
        'uncertainty_basis': {'type': 'string', 'enum': ['unreported']},
        'endpoint_unit': {'type': 'string', 'enum': ['unreported', 'events_per_100000_cells',
            'fraction', 'CFU_per_mL', 'minutes', 'per_min']},
        'exposure_unit': {'type': 'string', 'enum': ['unreported', 'molecules_per_cell',
            'normalized_signal', 'fraction', 'mg_per_mL']},
        'index_kind': {'type': 'string', 'enum': ['proposed_source_restoration_index']},
        'evaluated_scope': {'type': 'string', 'enum': ['interpreted_reference_perturbation']}}
    return {'type': 'array', 'items': obj(properties), 'x-source': 'literature_perturbation_cells'}


__all__ = ['LiteraturePerturbationRepository', 'COMPONENTS', 'PROVIDER',
    'perturbation_population_schema', 'perturbation_cells_schema']
