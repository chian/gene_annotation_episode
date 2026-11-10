"""A107 metadata/qualification operations; heavy native science stays external."""
from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, obj, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .a103_tools import A103ToolRegistry
from .a103_native_requests import OPERATIONS as GENOMIC_OPERATIONS
from .tools import ToolRegistry
from .component_axis_native_tools import ComponentNativeHPCMixin
from .a107_qualification import VERSION, PROVIDER as QUALIFICATION_PROVIDER, MAX_MAP_POSITIONS, request, refresh, require


def catalog():
    ref = {'type': 'string', 'format': 'reference'}
    nullable = {'anyOf': [ref, {'type': 'null'}]}
    from .literature_partner_calculations import COMPONENTS
    definitions = {
        'partner.component_correspondence': ('Measure this particular actual/reference protein or region correspondence from received native alignments or exact peptide identity. For a protein feature, positions use its local protein coordinates; native reuse requires its actually received parent sequence frame. Return native maps, coordinate paths, distance, extent, unresolved competing maps and their sources. This runs no search and establishes no functional requirement or new scalar score.',
            obj({'target_ref': ref, 'actual_ref': ref, 'component_ref': ref,
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable})),
        'partner.requirement_evidence': ('Retain a received source-backed requires/partner_dependence finding and its exact partner, direction, actual subject and conditions. Optionally attach actually delivered native omission/addback components from that same experiment. The finding observation must explicitly link the sheet experiment_ref in its subject_refs, source_subject_refs or dependencies. A shared paper alone does not establish that experiment link; missing linkage retains the numerical components with unresolved application. A source interpretation does not create target transfer or prove necessity. No model-authored numerical values are accepted.',
            obj({'target_ref': ref, 'assessment_ref': ref, 'component_ref': ref,
                'sheet_ref': nullable, 'components': {'type': 'array', 'items': {'enum': list(COMPONENTS)},
                    'uniqueItems': True}})),
        'partner.detection_evidence': ('Read an actual received native A103 detector inventory or authenticated A107 HPC search/detector publication using the exact required-component query sequence. Distinguish exact peptide detection, a homologous match, scoped no included hit and incomplete detection. New detector results retain the original computed reference-CDS translations, nucleotide sequences, record-local coordinates and all sequence-matched locus candidates; reuse those saved witnesses before seeking a new translation or placement calculation. A verified reference correspondence does not establish submitted target/sample genomic origin. Historical results without these witnesses retain their original meanings. Preserve original records, examined CDS, native statistics and unknown identity. This runs no detector/search and makes no whole-genome or functional-partner absence claim.',
            obj({'target_ref': ref, 'detection_ref': ref, 'component_ref': ref})),
        'partner.expression_evidence': ('Attach one actually received expression-table feature to a particular supplied target or required component using its declared measured-molecule sequence identity and received native correspondence. For measured RNA to a protein, supply the actual received native translation product and its original mapping witnesses. Positions then refer to that encoded product. Keep measured transcript, protein or reporter, whole-feature quantity, selected condition and local correspondence distinct. Missing measured-feature identity does not become target coexpression.',
            obj({'target_ref': ref, 'expression_ref': ref, 'feature_side': {'enum': ['left', 'right']},
                'actual_ref': ref, 'component_ref': ref,
                'encoded_product_ref': nullable,
                'require_detection_criterion': {'type': 'boolean', 'description':
                    'Request qualified source-criterion information for this measured feature. '
                    'Omit or use false for correspondence/coexpression alone.'},
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable},
                required=['target_ref', 'expression_ref', 'feature_side', 'actual_ref', 'component_ref',
                    'encoded_product_ref', 'positions', 'alignment_ref'])),
        'partner.expression_locus_evidence': ('Attach a gene-ID-level RNA measurement to an actually received native genomic locus. Require the measured feature entity_id to match its exact locus tag and retain each selected sample\'s declared reference-genome accession. Reuse the original verified CDS translation and received protein/region correspondence when available. A reference-locus assignment is not verification of the assay sample genotype, transcript isoform or protein abundance.',
            obj({'target_ref': ref, 'expression_ref': ref, 'feature_side': {'enum': ['left', 'right']},
                'locus_binding_ref': ref, 'component_ref': ref,
                'require_detection_criterion': {'type': 'boolean'},
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable},
                required=['target_ref', 'expression_ref', 'feature_side', 'locus_binding_ref',
                    'component_ref', 'positions', 'alignment_ref'])),
    }
    entries = {name: {'description': text, 'resources': 'local', 'input_schema': schema}
        for name, (text, schema) in definitions.items()}
    from .component_source_identity import catalog as identity_catalog
    entries.update(identity_catalog('A107'))
    # Optional associations extend the existing tools without changing the
    # required arguments or meaning of historical requests.
    entries['partner.requirement_evidence']['input_schema']['properties'].update(
        component_identity_ref=nullable, subject_identity_ref=nullable,
        subject_alignment_ref=nullable)
    entries['partner.requirement_evidence']['description'] += (
        ' Optional component_identity_ref and subject_identity_ref select actual '
        'source_identity_evidence results for the original partner/subject roles. '
        'Their protein references remain separate from the immutable assay roles; '
        'subject correspondence does not create a new regional measurement.')
    for name in ('partner.detection_evidence', 'partner.expression_evidence',
                 'partner.expression_locus_evidence'):
        entries[name]['input_schema']['properties']['requirement_ref'] = nullable
        entries[name]['description'] += (
            ' Optional requirement_ref selects the actual qualified source '
            'requirement whose identified component is being examined. The '
            'original component query/measurement must match that particular '
            'declared sequence; homologs do not automatically acquire its role.')
    return entries


class A107ToolRegistry(ComponentNativeHPCMixin, A103ToolRegistry):
    COMPONENT_NATIVE_AXES = ('A107',)
    def __init__(self, *args, a107_work_directory, a107_detection_bindings=(), **kwargs):
        # Reuse genomic tools and the original detector/HPC adapter. This is
        # tool composition, not an A103 scientific subtree under A107.
        from .a107_genomic_detection_hpc import normalize
        self.a107_detection_bindings = normalize(a107_detection_bindings)
        super().__init__(*args, a103_work_directory=a107_work_directory, **kwargs)
        self.store.db.execute('CREATE TABLE IF NOT EXISTS a107_operations '
            '(operation_key TEXT PRIMARY KEY,request TEXT NOT NULL,result TEXT NOT NULL)')

    def as_record(self):
        return {**super().as_record(), 'a107_tools': {'version': VERSION,
            'detector_bindings': deepcopy(self.a107_detection_bindings),
            'execution': 'qualification_reads_received_evidence; native_genomic_work_uses_shared_HPC'}}

    def catalog(self, scope=None):
        entries = super().catalog(scope=scope)
        for name in GENOMIC_OPERATIONS:
            entries.pop(name, None)
        # Keep the ordinary acquired-source lookup, without advertising the
        # disabled local native-bound-neighborhood branch.
        entries['reference.neighborhood'] = ToolRegistry.catalog(self, scope=scope)['reference.neighborhood']
        if 'context.request_hpc' in entries:
            resource_ids = sorted(name for name, resource in self.a103_execution_resources.items()
                if resource.get('kind') == 'pbs_ssh')
            for branch in entries['context.request_hpc']['input_schema']['oneOf']:
                branch['properties']['resource_id'].update(enum=resource_ids, description=
                    'Configured remote PBS resource ID. Local host observation IDs and '
                    'the local request-preparation tool label are different identifiers.')
        extra = catalog()
        require(not set(entries).intersection(extra), 'a107_operation_owner_conflict')
        return {**entries, **extra}

    def operation_resource_limits(self):
        parent = super().operation_resource_limits()
        if 'a103_native' in parent:
            parent['a103_native'] = {**parent['a103_native'], 'tool_names': [name for name in
                parent['a103_native']['tool_names'] if name not in GENOMIC_OPERATIONS]}
        return {**parent, 'a107_received_qualification': {
            'tool_names': list(catalog()), 'cpu_threads': 1, 'native_jobs': 0,
            'max_map_positions': MAX_MAP_POSITIONS,
            'oversize_behavior': 'explicit_shared_HPC_need; no_truncation_or_local_heavy_fallback'}}

    def received_hpc_attributions(self, context, known, *, hpc_result_reader):
        generated, needs = super().received_hpc_attributions(
            context, known, hpc_result_reader=hpc_result_reader)
        if context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == 'A107':
            from .a103_hpc import receive
            more, pending = receive(self, context, set(known) | set(generated), reader=hpc_result_reader)
            return [*generated, *more], [*needs, *pending]
        return generated, needs

    def received_attributions(self, context, known):
        parent = getattr(super(), 'received_attributions', None)
        generated, needs = parent(context, known) if callable(parent) else ([], [])
        if context.role not in {'annotation', 'scientific_process', 'improvement'} or (
                context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                    'evidence_axis', {}).get('option_id') != 'A107'):
            return generated, needs
        more, pending = refresh(self.store, context, set(known) | set(generated))
        return [*generated, *more], [*needs, *pending]

    async def execute_async(self, name, args, *, scope=None, operation_key=None, permitted_record_refs=None):
        from .component_axis_source_access import source_received_inputs
        permitted_record_refs = source_received_inputs(self, name, args, scope,
            operation_key, permitted_record_refs)
        invocation = self._current_invocation.get()
        if name in GENOMIC_OPERATIONS and invocation is not None and not (
                name == 'reference.neighborhood' and 'binding_ref' not in args):
            return {'status': 'unavailable', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': 'a107_native_genomic_work_requires_shared_hpc',
                    'operation': name, 'request_tool': 'context.request_hpc',
                    'configured': self.a103_execution_resources is not None}}
        if name not in catalog():
            return await super().execute_async(name, args, scope=scope, operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            validate_schema(args, catalog()[name]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (name, args, operation_key),
                'a107_current_action_binding_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='a107_').authenticate(context)
            require(self.store.validate_scope(scope) == plain(context.scope), 'a107_original_action_scope_required')
            require(context.role != 'scientific_process' or context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == 'A107', 'a107_original_scientific_axis_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'a107_explicit_received_inputs_required')
            signature = canonical({'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation': name, 'arguments': args, 'scope': plain(context.scope), 'version': VERSION})
            saved = self.store.db.execute('SELECT * FROM a107_operations WHERE operation_key=?', (operation_key,)).fetchone()
            if saved is not None:
                require(saved['request'] == signature, 'a107_operation_identity_conflict')
                return json.loads(saved['result'])
            with self.store.transaction():
                reference = request(self.store, name, deepcopy(args), context=context, known=known)
                generated, _ = refresh(self.store, context, known | {reference})
                result = {'status': 'completed', 'record_refs': list(dict.fromkeys([reference, *generated])),
                    'changed_record_refs': [], 'feedback': None,
                    'result': {'request_ref': reference, 'qualification_refs': [ref for ref in generated
                            if self.store.get(ref).get('provider') == QUALIFICATION_PROVIDER],
                        'derived_record_refs': [ref for ref in generated
                            if self.store.get(ref).get('provider') != QUALIFICATION_PROVIDER],
                        'native_execution_requested': False, 'scientific_credit': None}}
                self.store.db.execute('INSERT INTO a107_operations VALUES(?,?,?)',
                    (operation_key, signature, canonical(result)))
            return result
        except (ValueError, KeyError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': str(error)}}
