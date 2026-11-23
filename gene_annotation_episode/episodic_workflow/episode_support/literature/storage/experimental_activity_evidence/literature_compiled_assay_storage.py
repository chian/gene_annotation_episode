"""Selected saved-component compilation and exact scoped numerical returns.

Population alone reads source context and computes. Saved projection authenticates
original receipts and content-addressed snapshots without upstream acquisition,
unit conversion, scientific arithmetic or additional controller observations.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import operations_ledger, received_ledger
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import canonical, identity, obj, validate_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import ROLES, ALLOWLIST, ASSAY_LITERAL_FIELDS, ENDPOINTS, ARRANGEMENTS, STAGES, STAGE_VALUES, LINKS, LINK_LIMITS, compiled_assay_population_schema, read_compiled_assay_inputs, source_schema, NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE, POPULATION
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_compiled_assay_calculations import VERSION as SHEET_VERSION, PRIMITIVES, COMPONENTS, SECTIONS, MEANINGS, REASONS, FORMULAS, FORMULA_VARIANTS, QUALIFICATIONS, populate_compiled_assay
PROVIDER = 'literature.a105.compiled_assay'
VERSION = 'literature_compiled_assay_record'
NAMESPACE = 'literature_compiled_assay_cells'
REQUESTED = 'requested_compiled_assay_components'
VIEW = 'compiled_assay_components'
COMMON_VERSION = 'literature_common_assessment_record'
COMMON_NAMESPACE = 'literature_common_assessment_cells'
COMMON_REQUESTED = 'requested_common_assessment_components'
COMMON_SCOPE = 'common_assertion_contrast'

def compiled_assay_operation_schema():
    """Expose the common binding alongside the compiled-assay request."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import compiled_assay_operation_schema as compiled_operation_schema, common_assessment_population_schema
    return {'type': 'object', 'anyOf': [*compiled_operation_schema()['anyOf'], common_assessment_population_schema()]}

def common_assessment_cells_schema():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import common_assessment_inputs_schema
    from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_compiled_assay_calculations import common_assessment_sheet_schema, COMMON_COMPONENTS
    sheet = common_assessment_sheet_schema()['properties']
    metadata = {name: deepcopy(schema) for name, schema in sheet.items() if name not in ('version', 'cells', 'evaluation_scope')}
    covariance = deepcopy(common_assessment_inputs_schema()['properties']['covariance_blocks']['items']['properties'])
    del covariance['matrix_exact']
    return {**_array(obj({**deepcopy(sheet['cells']['items']['properties']), **metadata, 'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': COMMON_SCOPE}, 'scientific_sheet_version': deepcopy(sheet['version']), 'formula_code': {'enum': [name + '_common_assessment' for name in COMMON_COMPONENTS]}, 'covariance_provenance': {'anyOf': [obj(covariance), {'type': 'null'}]}})), 'x-source': COMMON_NAMESPACE}

def _project_common_saved(saved, reference, components):
    """Copy saved scientific output; never recalculate or parse input values."""
    sheet = saved['sheet']
    by_name = {row['component']: row for row in sheet['cells']}
    metadata = {name: deepcopy(value) for name, value in sheet.items() if name not in ('version', 'cells', 'evaluation_scope')}
    rows = []
    for name in components:
        if name not in by_name:
            raise ContractError('common_assessment_component_not_selected')
        cell = by_name[name]
        cov_ref = cell['uncertainty']['covariance_source_ref']
        covariance = None
        if cov_ref is not None:
            blocks = [block for block in saved['extraction']['covariance_blocks'] if block['source_ref'] == cov_ref]
            if len(blocks) != 1:
                raise ContractError('common_assessment_saved_covariance_binding_mismatch')
            covariance = {k: deepcopy(v) for k, v in blocks[0].items() if k != 'matrix_exact'}
        rows.append({**deepcopy(cell), **deepcopy(metadata), 'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'evaluation_scope': COMMON_SCOPE, 'scientific_sheet_version': sheet['version'], 'formula_code': name + '_common_assessment', 'covariance_provenance': covariance})
    return rows

def _array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _ref(namespace='source', nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _text(nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'minLength': 1}

def _selector():
    return obj({'namespace': {'type': 'string', 'enum': list(dict.fromkeys((ns for choices in ALLOWLIST.values() for ns in choices)))}, 'sheet_ref': _ref(), 'component': {'type': 'string', 'enum': list(dict.fromkeys((name for choices in ALLOWLIST.values() for names in choices.values() for name in names)))}})

def _dependency():
    return obj({'role': {'type': 'string', 'enum': list(ROLES)}, 'selection': {'anyOf': [_selector(), {'type': 'null'}]}, 'component_key': _text(True), 'quantity_key': _text(True), 'canonical_physical_keys': _array(_text(), True), 'recorded_dependency_keys': _array(_text(), True), 'physical_identity_status': {'type': 'string', 'enum': ['partly_canonical', 'cross_component_identity_unknown', 'definition_identity']}, 'identity_stage': {'type': ['string', 'null'], 'enum': [*STAGES, None]}})

def _numerical_cell():
    return obj({'value': {'type': ['number', 'null']}, 'unit': {'type': ['string', 'null'], 'enum': ['uM/min', 'uM', 'dimensionless', 'per_min', 'per_min_squared', 'min_squared', 'nM', 'fraction', 'umol/min', 'nmol/min', 'mmol/min', 'nM/min', 'per_s', 'umol/min/mg', 'nmol/min/mg', 'mg/ml', None]}, 'status': {'type': 'string', 'enum': ['populated', 'unavailable']}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]}, 'formula': {'type': 'string', 'enum': list(dict.fromkeys((*FORMULA_VARIANTS, *FORMULAS.values())))}, 'origin': {'type': 'string', 'enum': ['reported', 'derived', 'graph_derived', 'synthetic', 'proposed', 'definition_identity']}, 'section': {'type': 'string', 'enum': list(dict.fromkeys(SECTIONS.values()))}, 'meaning': {'type': 'string', 'enum': list(dict.fromkeys(MEANINGS.values()))}, 'conditional_on': _array({'type': 'string', 'enum': ['first_order_covariance_propagation', 'known_variance', 'known_normal_nonnegative_presence']}), 'qualifications': _array({'type': 'string', 'enum': list(QUALIFICATIONS)})})

def _native_quantity_schema():
    properties = [source_schema(ns)['items']['properties'] for ns in (NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, NS_AMOUNT, NS_NATIVE, NS_REPLICATE)]

    def union(field, fallback):
        choices = [deepcopy(p[field]) for p in properties if field in p]
        return {'anyOf': [*choices, fallback]}
    return {'anyOf': [obj({'value': {'type': ['number', 'null']}, 'source_unit': union('unit', {'type': 'null'}), 'threshold': {'type': ['number', 'null']}, 'bound': {'type': 'string', 'enum': ['none', 'point', 'lt', 'le', 'gt', 'ge']}, 'approximate': {'type': ['boolean', 'null']}, 'reported_domain': union('reported_domain', {'type': 'null'}), 'exact_domain': union('exact_domain', {'type': 'null'}), 'meaning': {'type': 'string', 'const': 'unchanged_selected_native_component_domain'}, 'domain_conversion': {'type': 'string', 'const': 'not_converted'}}), {'type': 'null'}]}

def _native_quantity(extraction, component):
    role = next((r for r, name in PRIMITIVES.items() if name == component), None)
    operand = extraction['operands'][role] if role is not None else None
    if operand is None:
        return None
    row = operand['row']
    return {'value': row.get('value'), 'source_unit': row.get('unit'), 'threshold': row.get('threshold'), 'bound': row.get('bound', 'none'), 'approximate': row.get('approximate'), 'reported_domain': deepcopy(row.get('reported_domain')), 'exact_domain': deepcopy(row.get('exact_domain')), 'meaning': 'unchanged_selected_native_component_domain', 'domain_conversion': 'not_converted'}

def compiled_assay_cells_schema():
    components = COMPONENTS
    schema = {**_array(obj({'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'type': 'string', 'const': 'compiled_source_endpoint'}, 'component': {'type': 'string', 'enum': list(components)}, **_numerical_cell()['properties'], 'formula_code': {'type': 'string', 'enum': [name + '_compiled' for name in components]}, 'dependencies': _array(_dependency()), 'native_quantity': _native_quantity_schema(), 'operand_meanings': obj({role: {'type': 'string', 'enum': [*LINKS[role], *LINK_LIMITS]} for role in ROLES}), 'assay_meanings': obj({name: _text(True) for name in ASSAY_LITERAL_FIELDS}), 'endpoint_kind': {'type': 'string', 'enum': list(ENDPOINTS)}, 'arrangement_kind': {'type': 'string', 'enum': list(ARRANGEMENTS)}, 'correction_stages': obj({name: {'type': 'string', 'enum': list(STAGE_VALUES)} for name in STAGES}), 'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']}, 'observation_model': {'type': 'string', 'enum': ['none', 'known_normal_nonnegative_presence']}, 'covariance_source_ref': _ref(nullable=True), 'residual_variance_source_ref': _ref(nullable=True), 'operand_eligibility': obj({role: {'type': ['string', 'null'], 'enum': [None, *REASONS]} for role in ROLES}), 'partial_uncertainty_status': {'type': 'string', 'const': 'unimplemented'}, 'covariance_input_status': {'type': 'string', 'enum': ['not_selected', 'selected_known', 'selected_estimated', 'selected_unknown']}, 'annotation_credit': {'type': 'null'}})), 'x-source': NAMESPACE}
    properties = schema['items']['properties']
    properties['partial_uncertainty_status'] = {'type': 'string', 'const': 'component_scoped'}
    properties['uncertainty'] = obj({'estimand_component': {'type': ['string', 'null'], 'enum': [None, 'measured_endpoint_per_selected_amount', 'calibrated_measured_endpoint_per_selected_amount', 'corrected_activity']}, 'scope': {'type': 'string', 'enum': ['not_applicable', 'operand_propagated', 'total_with_distinct_residual']}, 'covariance_source_ref': _ref(nullable=True), 'source_primitive_order': _array({'type': 'string', 'enum': list(ROLES)}, True), 'operand_order': _array({'type': 'string', 'enum': list(ROLES)}, True), 'operand_keys': _array(_text()), 'variance_status': {'type': 'string', 'enum': ['known', 'estimated', 'unknown']}, 'covariance_origin': {'type': ['string', 'null'], 'enum': [None, 'reported', 'derived', 'synthetic']}, 'propagation_model': {'type': 'string', 'enum': ['none', 'first_order_covariance_propagation']}})
    schema['items']['required'] = list(properties)
    return schema

def _project_saved(saved, reference, components):
    if saved['version'] == COMMON_VERSION:
        return _project_common_saved(saved, reference, components)
    sheet, extraction = (saved['sheet'], saved['extraction'])
    meanings = {name: None if extraction['assay'][name] is None else extraction['assay'][name]['value'] for name in ASSAY_LITERAL_FIELDS}
    return [{'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'evaluation_scope': 'compiled_source_endpoint', 'component': name, **deepcopy(sheet['cells'][name]), 'formula_code': name + '_compiled', 'dependencies': deepcopy(sheet['dependencies'][name]), 'assay_meanings': deepcopy(meanings), 'native_quantity': _native_quantity(extraction, name), 'operand_meanings': {role: extraction['relationships'][role]['value'] for role in ROLES}, 'endpoint_kind': extraction['assay']['endpoint']['value'], 'arrangement_kind': extraction['assay']['arrangement']['value'], 'correction_stages': {stage: extraction['correction_stages'][stage]['value'] for stage in STAGES}, 'variance_status': extraction['variance_status'], 'observation_model': extraction['observation_model'], 'covariance_source_ref': sheet['uncertainty'][name]['covariance_source_ref'], 'residual_variance_source_ref': extraction['distinct_residual_observation']['witness']['source_ref'] if extraction['distinct_residual_observation'] else None, 'operand_eligibility': deepcopy(sheet['operand_eligibility_reasons']), 'partial_uncertainty_status': 'component_scoped', 'covariance_input_status': ('not_selected' if sheet['uncertainty'][name]['covariance_source_ref'] is None else 'selected_' + sheet['uncertainty'][name]['variance_status']), 'annotation_credit': None, 'uncertainty': deepcopy(sheet['uncertainty'][name])} for name in components]

OPERATIONS = operations_ledger('literature_compiled_assay_operations')
RECEIVED = received_ledger('literature_compiled_assay_received')
COMMON_RECEIVED = received_ledger('literature_common_assessment_received')

class LiteratureCompiledAssayRepository(LiteratureRateRepository):
    provider, components, record_version = (PROVIDER, COMPONENTS, VERSION)
    operations = OPERATIONS
    received = RECEIVED
    binding_fields = ()

    def __init__(self, store, run_id, common=False):
        super().__init__(store, run_id)
        self.common = common
        if common:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_compiled_assay_calculations import COMMON_COMPONENTS
            self.components, self.record_version = (COMMON_COMPONENTS, COMMON_VERSION)
            self.received = COMMON_RECEIVED

    def common_projection(self):
        return type(self)(self.store, self.run_id, True)

    def _components(self, components):
        if not isinstance(components, (list, tuple)) or any((type(name) is not str or name not in self.components for name in components)) or len(set(components)) != len(components):
            raise ContractError('compiled_assay_component_selection_invalid')
        return list(components)

    def _input_repository(self, namespace):
        if namespace == 'literature_product_coupling_cells':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_product_coupling_storage import LiteratureProductCouplingRepository
            cls = LiteratureProductCouplingRepository
        elif namespace == 'literature_kinetic_cells':
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_kinetic_storage import LiteratureKineticRepository
            cls = LiteratureKineticRepository
        elif namespace == NS_ASSAY:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_storage import LiteratureAssayRepository
            cls = LiteratureAssayRepository
        elif namespace == NS_OPTICAL:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_optical_storage import LiteratureOpticalRepository
            cls = LiteratureOpticalRepository
        elif namespace == NS_RECOVERY:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
            cls = LiteratureCalibrationRecoveryRepository
        elif namespace == NS_ACTIVE:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_active_site_storage import LiteratureActiveSiteRepository
            cls = LiteratureActiveSiteRepository
        elif namespace == NS_AMOUNT:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_amount_storage import LiteratureAmountRepository
            cls = LiteratureAmountRepository
        elif namespace == NS_REPLICATE:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_replicate_storage import LiteratureRateReplicateRepository
            cls = LiteratureRateReplicateRepository
        elif namespace == NS_NATIVE:
            from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_rate_meaning_delivery import LiteratureRateSourceMeaningProjection
            cls = LiteratureRateSourceMeaningProjection
        else:
            raise ContractError('unsupported_compilation_namespace')
        return cls(self.store, self.run_id)

    def _ancestors(self, scope, references):
        refs = list(dict.fromkeys(references))
        for ref in refs:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in refs:
                    refs.append(parent)
        return refs

    def populate(self, context, arguments, operation_key):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import COMMON_POPULATION
        if arguments.get('population_version') == COMMON_POPULATION and not self.common:
            return self.common_projection().populate(context, arguments, operation_key)
        if self.common:
            return self._populate_common(context, arguments, operation_key)
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, compiled_assay_population_schema())
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope), 'components': requested}
        signature = canonical(request)
        old = self._operation(context.episode_id, operation_key)
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            saved = self.read(outcome['result']['sheet_ref'])
            for ref in saved['direct_input_source_refs']:
                self._native_source(context, ref)
            for selected in saved['component_selections']:
                if selected['sheet_ref'] not in context.received_record_refs:
                    raise ContractError('literature_sheet_not_received')
            return outcome
        source = self._native_source(context, args['source_ref'])
        snapshots = []
        selected_refs = []

        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}

        def component(selection):
            repo = self._input_repository(selection['namespace'])
            refs = [selection['sheet_ref']]
            if self.store.reference_subset(refs, plain(context.scope)) != refs:
                raise ContractError('literature_source_outside_scope')
            rows = repo.fact_cells(context, refs, components=[selection['component']])
            if len(rows) != 1:
                raise ContractError('selected_component_not_received')
            snapshots.append({'selection': deepcopy(selection), 'row': deepcopy(rows[0])})
            selected_refs.extend(refs)
            return rows

        def record(ref):
            if self.store.reference_subset([ref], plain(context.scope)) != [ref]:
                raise ContractError('literature_source_outside_scope')
            return self.store.get(ref)
        extraction = read_compiled_assay_inputs(args, read_source=read_source, read_component=component, read_record=record)
        sheet = populate_compiled_assay(extraction)
        direct = extraction['source_refs']
        parents = self._ancestors(context.scope, [*direct, *selected_refs])
        metadata = {ref: self.store.get(ref) for ref in parents}
        payload = {'version': self.record_version, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'], 'direct_input_source_refs': direct, 'input_source_refs': parents, 'selection': args, 'component_selections': [item['selection'] for item in snapshots], 'input_snapshots': snapshots, 'source_metadata': metadata, 'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': req_ref, 'version': self.record_version, 'retrieved_at': None, 'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.holds(reference)
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested)
            validate_schema(rows, compiled_assay_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference], 'changed_record_refs': [] if exists else [reference], 'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows}, 'feedback': None}
            self._save_operation(operation_key, signature, outcome)
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(raw).hexdigest() != reference:
            raise ContractError('compiled_assay_saved_artifact_hash_mismatch')
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as error:
            raise ContractError('compiled_assay_saved_json_invalid') from error

    def _populate_common(self, context, arguments, operation_key):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import common_assessment_population_schema, read_common_assessment_inputs
        from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_compiled_assay_calculations import populate_common_assessment
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, common_assessment_population_schema())
        requested = self._components(plain(context.assignment.get(COMMON_REQUESTED, [])))
        if args['requested_cells'] != requested:
            raise ContractError('common_assessment_requested_subset_mismatch')
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'scope': plain(context.scope), 'arguments': args, 'components': requested, 'role': context.role, 'assignment': plain(context.assignment), 'received_record_refs': list(context.received_record_refs)}
        signature = canonical(request)
        old = self._operation(context.episode_id, operation_key)
        if old is not None:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            self.read(outcome['result']['sheet_ref'])
            return outcome
        source = self._native_source(context, args['source_ref'])
        public_records = {}
        authorized = set(context.received_record_refs)

        def references(value):
            if isinstance(value, dict):
                for child in value.values():
                    yield from references(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    yield from references(child)
            elif isinstance(value, str) and value.startswith(('reference_', 'source_', 'artifact_')):
                yield value

        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            raw = self.store.get_artifact(artifact)
            if artifact != 'artifact_' + hashlib.sha256(raw).hexdigest():
                raise ContractError('common_assessment_source_artifact_hash_mismatch')
            return {'artifact_ref': artifact, 'content': raw}

        def component(selection):
            ref = selection['sheet_ref']
            if self.store.reference_subset([ref], plain(context.scope)) != [ref]:
                raise ContractError('literature_source_outside_scope')
            rows = self._input_repository(selection['namespace']).fact_cells(context, [ref], components=[selection['component']])
            if len(rows) != 1:
                raise ContractError('selected_component_not_received')
            row = rows[0]
            visible = row[selection['component'].removesuffix('_parameter')] if selection['namespace'] == 'literature_kinetic_cells' else row
            authorized.update(references(visible))
            authorized.add(row['evidence_source_ref'])
            return rows

        def record(ref):
            if ref not in authorized:
                raise ContractError('common_assessment_public_binding_not_received')
            if self.store.reference_subset([ref], plain(context.scope)) != [ref]:
                raise ContractError('literature_source_outside_scope')
            row = self.store.get(ref)
            public_records[ref] = deepcopy(row)
            return row
        extraction = read_common_assessment_inputs(args, read_source=read_source, read_component=component, read_record=record)
        sheet = populate_common_assessment(extraction)
        snapshots = extraction['component_snapshots']
        selected = [item['selection'] for item in snapshots]
        direct = extraction['source_refs']
        parents = self._ancestors(context.scope, [*direct, *(s['sheet_ref'] for s in selected)])
        payload = {'version': COMMON_VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'], 'direct_input_source_refs': direct, 'input_source_refs': parents, 'selection': args, 'component_selections': selected, 'input_snapshots': snapshots, 'public_input_records': public_records, 'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref, 'version': COMMON_VERSION, 'retrieved_at': None, 'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.holds(reference)
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_common_saved(payload, reference, requested)
            validate_schema(rows, common_assessment_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id, 'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference], 'changed_record_refs': [] if exists else [reference], 'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows, 'record_version': COMMON_VERSION, 'scientific_sheet_version': sheet['version']}, 'feedback': None}
            self._save_operation(operation_key, signature, outcome)
        return outcome

    def _read_common(self, reference):
        try:
            return self._read_common_bound(reference)
        except (KeyError, TypeError, ValueError, UnicodeError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError('common_assessment_saved_binding_mismatch') from error

    def _read_common_bound(self, reference):
        """Authenticate closed records without scientific source IO/arithmetic."""
        from collections import Counter
        from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_compiled_assay_inputs import common_assessment_population_schema, common_assessment_inputs_schema, COMMON_ROLES
        from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.literature_compiled_assay_calculations import common_assessment_sheet_schema, _COMMON_FORMULAS, _COMMON_MEANINGS
        source = self.store.get(reference)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER or (source.get('version') != COMMON_VERSION) or (source['text_ref'] != source['artifact_ref']) or (identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_compiled_assay_sheet_required')
        request = self._json(source['request_ref'])
        if set(request) != {'run_id', 'episode_id', 'operation_key', 'scope', 'arguments', 'components', 'role', 'assignment', 'received_record_refs'} or request['run_id'] != self.run_id or (not all((isinstance(request[k], str) and request[k] for k in ('episode_id', 'operation_key', 'role')))) or (request['components'] != request['assignment'].get(COMMON_REQUESTED, [])) or (request['components'] != request['arguments']['requested_cells']):
            raise ContractError('common_assessment_saved_request_mismatch')
        validate_schema(request['arguments'], common_assessment_population_schema())
        self._components(request['components'])
        self._native_provenance(request['scope'], reference)
        operation = self._operation(request['episode_id'], request['operation_key'])
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        keys = {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs', 'input_source_refs', 'selection', 'component_selections', 'input_snapshots', 'public_input_records', 'source_metadata', 'extraction', 'sheet'}
        if set(saved) != keys or saved['version'] != COMMON_VERSION or saved['selection'] != request['arguments'] or (saved['input_source_ref'] != request['arguments']['source_ref']) or (saved['input_source_refs'] != source['parent_source_refs']) or (saved['input_artifact_ref'] != self.store.get(saved['input_source_ref'])['artifact_ref']):
            raise ContractError('common_assessment_saved_selection_mismatch')
        selected = saved['component_selections']
        e, sheet = (saved['extraction'], saved['sheet'])
        validate_schema(e, common_assessment_inputs_schema())
        validate_schema(sheet, common_assessment_sheet_schema())
        if e['request'] != request['arguments'] or e['source_refs'] != saved['direct_input_source_refs'] or saved['input_source_ref'] not in e['source_refs'] or (len(set(e['source_refs'])) != len(e['source_refs'])) or any((ref not in request['received_record_refs'] for ref in e['source_refs'])) or (self._ancestors(request['scope'], [*e['source_refs'], *(s['sheet_ref'] for s in selected)]) != saved['input_source_refs']) or (set(saved['source_metadata']) != set(saved['input_source_refs'])) or any((canonical(self._native_provenance(request['scope'], ref)) != canonical(row) for ref, row in saved['source_metadata'].items())) or any((self.store.reference_subset([ref], request['scope']) != [ref] or canonical(self.store.get(ref)) != canonical(row) for ref, row in saved['public_input_records'].items())):
            raise ContractError('common_assessment_saved_source_mismatch')
        if e['component_snapshots'] != saved['input_snapshots'] or selected != [s['selection'] for s in saved['input_snapshots']] or Counter(map(canonical, selected)) != Counter((canonical(s) for s in request['arguments']['estimates'].values() if s is not None and s['kind'] == 'received_component')):
            raise ContractError('common_assessment_saved_operand_mismatch')
        for role in COMMON_ROLES:
            estimate, choice = (e['estimates'][role], request['arguments']['estimates'][role])
            if (estimate is None) != (choice is None) or (estimate is not None and (estimate['role'] != role or estimate['selection'] != choice)):
                raise ContractError('common_assessment_saved_operand_mismatch')
            if choice is not None and choice['kind'] == 'received_component' and (choice['sheet_ref'] not in request['received_record_refs']):
                raise ContractError('common_assessment_saved_custody_mismatch')
        for snapshot in saved['input_snapshots']:
            row, choice = (snapshot['row'], snapshot['selection'])
            if row['sheet_ref'] != choice['sheet_ref'] or row['component'] != choice['component']:
                raise ContractError('common_assessment_saved_operand_mismatch')
        artifacts = {(a['source_ref'], a['representation']): a['artifact_ref'] for a in e['source_artifacts']}
        for (ref, representation), artifact in artifacts.items():
            meta = saved['source_metadata'][ref]
            if meta['artifact_ref' if representation == 'original' else 'text_ref'] != artifact:
                raise ContractError('common_assessment_saved_artifact_binding_mismatch')

        def witnesses(value):
            if isinstance(value, dict):
                if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote'}:
                    yield value
                else:
                    for child in value.values():
                        yield from witnesses(child)
            elif isinstance(value, list):
                for child in value:
                    yield from witnesses(child)
        for w in witnesses(request['arguments']):
            artifact = artifacts.get((w['source_ref'], w['representation']))
            if artifact is None or w['end'] - w['start'] != len(w['quote'].encode()) or w['end'] > self.store.get(artifact)['size']:
                raise ContractError('common_assessment_saved_witness_binding_mismatch')
        for block in e['covariance_blocks']:
            roles = block['roles']
            if block['source_ref'] not in request['arguments']['covariance_source_refs'] or block['artifact_ref'] != artifacts.get((block['source_ref'], 'original')) or block['owner_keys'] != [e['estimates'][r]['owner_key'] for r in roles] or (block['units'] != [e['estimates'][r]['unit'] for r in roles]) or (block['dependency_keys'] != [e['estimates'][r]['dependency_keys'] for r in roles]):
                raise ContractError('common_assessment_saved_covariance_binding_mismatch')
        if [b['source_ref'] for b in e['covariance_blocks']] != request['arguments']['covariance_source_refs']:
            raise ContractError('common_assessment_saved_covariance_binding_mismatch')
        if sheet['host_custody'] != {'source_refs': e['source_refs'], 'source_artifacts': e['source_artifacts'], 'withheld_locations': e['numerical_scope_locations']} or [c['component'] for c in sheet['cells']] != request['components'] or sheet['assertion_resolution'] != request['arguments']['assertion']['resolution'] or (sheet['question'] != request['arguments']['assertion']['question']):
            raise ContractError('common_assessment_saved_sheet_binding_mismatch')
        for cell in sheet['cells']:
            name = cell['component']
            native = name.startswith('estimate_')
            expected_formula = 'selected_native_estimate' if native else _COMMON_FORMULAS[name]
            expected_meaning = 'Native selected source report; qualified nondetection is not exact physical absence.' if native else _COMMON_MEANINGS[name]
            owners = list(dict.fromkeys((e['estimates'][r]['owner_key'] for r in cell['operand_roles'] if e['estimates'][r] is not None)))
            if cell['formula'] != expected_formula or cell['meaning'] != expected_meaning or cell['operand_keys'] != owners or (cell['status'] == 'populated' and (cell['value'] is None or cell['conditional_value'] is not None)) or (cell['status'] == 'conditional_scenario' and (cell['conditional_value'] is None or cell['value'] is not None)) or (cell['status'] == 'unavailable' and (cell['value'] is not None or cell['conditional_value'] is not None)):
                raise ContractError('common_assessment_saved_cell_binding_mismatch')
            cov_ref = cell['uncertainty']['covariance_source_ref']
            if cov_ref is not None and (not any((cov_ref == b['source_ref'] and cell['uncertainty']['variance_status'] == b['variance_status'] and (cell['uncertainty']['basis'] == b['basis']) for b in e['covariance_blocks']))):
                raise ContractError('common_assessment_saved_covariance_binding_mismatch')
        rows = _project_common_saved(saved, reference, request['components'])
        validate_schema(rows, common_assessment_cells_schema())
        outcome = json.loads(operation['outcome'])
        if outcome.get('status') != 'completed' or outcome.get('record_refs') != [reference] or outcome.get('feedback') is not None or (canonical(outcome.get('result')) != canonical({'sheet_ref': reference, 'view': VIEW, 'cells': rows, 'record_version': COMMON_VERSION, 'scientific_sheet_version': sheet['version']})) or (outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('common_assessment_saved_outcome_mismatch')
        return saved

    def read(self, reference):
        if self.common:
            return self._read_common(reference)
        source = self.store.get(reference)
        value = {k: v for k, v in source.items() if k not in ('id', 'record_type', 'origin')}
        if source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER or (source.get('version') != self.record_version) or (identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_compiled_assay_sheet_required')
        request = self._json(source['request_ref'])
        if set(request) != {'run_id', 'episode_id', 'operation_key', 'arguments', 'scope', 'components'} or request['run_id'] != self.run_id:
            raise ContractError('compiled_assay_saved_request_mismatch')
        validate_schema(request['arguments'], compiled_assay_population_schema())
        self._components(request['components'])
        operation = self._operation(request['episode_id'], request['operation_key'])
        if operation is None or operation['signature'] != canonical(request):
            raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        expected_fields = {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs', 'input_source_refs', 'selection', 'component_selections', 'input_snapshots', 'source_metadata', 'extraction', 'sheet'}
        if set(saved) != expected_fields or saved['version'] != self.record_version or saved['selection'] != request['arguments'] or (saved['input_source_ref'] != request['arguments']['source_ref']) or (saved['input_source_refs'] != source['parent_source_refs']):
            raise ContractError('compiled_assay_saved_selection_mismatch')
        if self._ancestors(request['scope'], [*saved['direct_input_source_refs'], *(s['sheet_ref'] for s in saved['component_selections'])]) != saved['input_source_refs']:
            raise ContractError('compiled_assay_saved_source_mismatch')
        if any((canonical(self.store.get(ref)) != canonical(metadata) for ref, metadata in saved['source_metadata'].items())):
            raise ContractError('compiled_assay_saved_source_mismatch')
        if self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']:
            raise ContractError('compiled_assay_saved_source_mismatch')
        extraction = saved['extraction']
        if extraction['source_ref'] != saved['input_source_ref'] or extraction['artifact_ref'] != saved['input_artifact_ref'] or extraction['source_refs'] != saved['direct_input_source_refs'] or (saved['sheet']['version'] != SHEET_VERSION) or (saved['sheet']['original_extraction'] != extraction):
            raise ContractError('compiled_assay_saved_extraction_mismatch')
        selected = [request['arguments']['operands'][role] for role in ROLES if request['arguments']['operands'][role] is not None]
        if selected != saved['component_selections'] or selected != [row['selection'] for row in saved['input_snapshots']]:
            raise ContractError('compiled_assay_saved_operand_mismatch')
        for snapshot in saved['input_snapshots']:
            validate_schema([snapshot['row']], source_schema(snapshot['selection']['namespace']))
            if snapshot['row']['sheet_ref'] != snapshot['selection']['sheet_ref'] or snapshot['row']['component'] != snapshot['selection']['component']:
                raise ContractError('compiled_assay_saved_operand_mismatch')
        for role in ROLES:
            operand = extraction['operands'][role]
            selection = request['arguments']['operands'][role]
            if (operand is None) != (selection is None) or (operand is not None and (operand['selection'] != selection or operand['row'] != next((s['row'] for s in saved['input_snapshots'] if s['selection'] == selection)))):
                raise ContractError('compiled_assay_saved_operand_mismatch')
        if set(saved['sheet']['cells']) != set(self.components) or set(saved['sheet']['dependencies']) != set(self.components):
            raise ContractError('compiled_assay_saved_component_mismatch')
        for name, cell in saved['sheet']['cells'].items():
            validate_schema(cell, _numerical_cell())
            if cell['section'] != SECTIONS[name] or cell['meaning'] != MEANINGS[name] or (cell['value'] is None) != (cell['status'] == 'unavailable') or ((cell['unavailable_reason'] is None) != (cell['status'] == 'populated')):
                raise ContractError('compiled_assay_saved_cell_mismatch')
        rows = _project_saved(saved, reference, request['components'])
        validate_schema(rows, compiled_assay_cells_schema())
        outcome = json.loads(operation['outcome'])
        expected = {'sheet_ref': reference, 'view': VIEW, 'cells': rows}
        if outcome.get('status') != 'completed' or canonical(outcome.get('result')) != canonical(expected) or outcome.get('record_refs') != [reference] or (outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('compiled_assay_saved_outcome_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = self._components(self.components if components is None else components)
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            rows.extend(_project_saved(self.read(ref), ref, selected))
        return rows

    def fact_cells(self, context, sheet_refs, *, components):
        refs = list(dict.fromkeys(sheet_refs))
        if self.store.reference_subset(refs, plain(context.scope)) != refs:
            raise ContractError('literature_source_outside_scope')
        if self.common:
            selected = self._components(components)
            received = None
            result = []
            for ref in refs:
                if ref not in context.received_record_refs:
                    raise ContractError('literature_sheet_not_received')
                if self._sheet_owner(ref) == context.episode_id:
                    requested = self._json(self.store.get(ref)['request_ref'])['components']
                    result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs, components=[name for name in requested if name in selected]))
                else:
                    if received is None:
                        received = self.received_cells(context)
                    result.extend((deepcopy(row) for row in received if row['sheet_ref'] == ref and row['component'] in selected))
            return result
        return super().fact_cells(context, refs, components=components)

    def has_work(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if self.common:
            return bool(self.available_sheet_refs(context))
        own = any((self.store.get(json.loads(row['outcome'])['result']['sheet_ref']).get('version') == VERSION for row in self._operations(context.episode_id)))
        received = self.store.table(self.received).select({'run_id': self.run_id, 'episode_id': context.episode_id}, limit=1)
        return bool(own or received)

    def owned_sheet_refs(self, context):
        return [json.loads(row['outcome'])['result']['sheet_ref'] for row in self._operations(context.episode_id) if json.loads(row['outcome'])['result']['sheet_ref'] in context.received_record_refs and self.store.get(json.loads(row['outcome'])['result']['sheet_ref']).get('version') == self.record_version]

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        refs = list(dict.fromkeys((json.loads(row['outcome'])['result']['sheet_ref'] for row in self._operations(context.episode_id))))
        refs = [ref for ref in refs if self.store.get(ref).get('version') == self.record_version]
        for ref in refs:
            self.read(ref)
        return refs

    def validate_empty_return_family(self, context):
        versions = {self.store.get(json.loads(row['outcome'])['result']['sheet_ref']).get('version') for row in self._operations(context.episode_id)}
        if not self.common and COMMON_VERSION not in versions:
            return
        if versions and self.record_version not in versions:
            raise ContractError('literature_compiled_assay_projection_version_mismatch')

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*self.owned_sheet_refs(context), *(r['sheet_ref'] for r in self.received_cells(context) if r['sheet_ref'] in context.received_record_refs)]))

    @staticmethod
    def cell_record_refs(cells):
        if any((row.get('evaluation_scope') == COMMON_SCOPE for row in cells)):
            result = []

            def visit(value):
                if isinstance(value, dict):
                    for name, child in value.items():
                        if name.endswith('_ref') and isinstance(child, str) and child.startswith(('source_', 'artifact_')):
                            result.append(child)
                        elif name == 'source_refs':
                            result.extend(child)
                        else:
                            visit(child)
                elif isinstance(value, (list, tuple)):
                    for child in value:
                        visit(child)
            visit(cells)
            return list(dict.fromkeys(result))
        return list(dict.fromkeys((ref for row in cells for ref in [row['sheet_ref'], row['evidence_source_ref'], *(d['selection']['sheet_ref'] for d in row['dependencies'] if d['selection'] is not None), *[row[name] for name in ('covariance_source_ref', 'residual_variance_source_ref') if row[name] is not None]])))
__all__ = ['LiteratureCompiledAssayRepository', 'compiled_assay_cells_schema', 'common_assessment_cells_schema', 'compiled_assay_operation_schema', 'PROVIDER', 'VERSION', 'COMMON_VERSION', 'NAMESPACE', 'COMMON_NAMESPACE', 'REQUESTED', 'COMMON_REQUESTED', 'VIEW', 'COMPONENTS']
