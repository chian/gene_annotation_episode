"""Persist selected A105 aggregation over the parent's possessed grade rows."""
from copy import deepcopy
from episode_runtime import TableDeclaration
from hashlib import sha256
import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_aggregation import COMPONENTS, SCOPE, aggregate_a105, aggregation_population_schema, aggregation_cell_schema, aggregation_sheet_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_assay_grading_storage import LiteratureAssayGradingRepository, assay_grading_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.a105.aggregation'
VERSION = 'literature_a105_aggregation_record'
OPERATIONS = TableDeclaration(name='literature_a105_aggregation_operations', columns=('sheet_ref',), key=('sheet_ref',), record_refs=('sheet_ref',))
CELLS = TableDeclaration(name='literature_a105_aggregation_cells', columns=('sheet_ref', 'component', 'cell'), key=('sheet_ref', 'component'), record_refs=('sheet_ref',))
NAMESPACE = 'literature_a105_aggregation_cells'
REQUESTED = 'requested_a105_aggregation_components'
OPERATION_DESCRIPTION = (
    'Combine the retained experimental A105 components selected by the parent. '
    'Use one actual possessed numerical component per experiment and metric: '
    'reliability SUM, validity SUM, relevance MAX, attribution MAX, overall SUM. '
    'Preserve the selected native values, units and meanings, with no weighting, '
    'rescaling or orthogonality correction. Select one assessment of each experiment '
    'so duplicate reports or revisions do not become additional experiments. '
    'Keep missing values explicit and report available partial totals separately. '
    'The comparison reference is a parent declaration; no alternative hypothesis '
    'identity is inferred from the native prediction numbers. Return exactly the '
    'requested saved metrics. This is A105 evidence aggregation, not W05 annotation credit.'
)


def aggregation_cells_schema():
    fields = deepcopy(aggregation_cell_schema()['properties'])
    fields['sheet_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields)}


def _rows(saved, sheet_ref, components):
    return [dict(sheet_ref=sheet_ref, **deepcopy(saved['sheet']['cells'][name])) for name in components]


class LiteratureA105AggregationRepository(LiteratureRateRepository):
    def current_annotation_cells(self, context):
        """Resolve this owner's admitted current final cells without granting private inputs."""
        rows = [row for row in self.received_cells(context) if row['component'] == 'overall']
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_sheet_updates import current_scoring_sheets
        current = [row for row in current_scoring_sheets(self.store, context) if row['axis'] == 'A105']
        return ([cell for row in current if row['status'] == 'current'
            for cell in row['cells'] if cell['component'] == 'overall'] if current else rows)

    def annotation_contribution(self, store, context, *, target, annotation, scope,
                                comparison_ref=None, selection=None, details_limit=0, details_offset=0):
        from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_assay_contribution import _result, require_attribution, bind_contribution
        from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_aggregation import annotation_scalar
        import json
        rows = [row for row in self.current_annotation_cells(context) if row['assertion_ref'] == annotation['id']
            and (comparison_ref is None or row.get('comparison_ref') == comparison_ref)
            and (selection is None or row['sheet_ref'] == selection)]
        refs, details = [], []
        if len(rows) != 1:
            reason = ('no_received_current_final_cell_for_this_question' if not rows else
                'multiple_current_axis_questions_require_explicit_sheet_selection')
            scalar = _result(None, formula='received_current_axis_result_required',
                inputs={'sheet_refs': [row['sheet_ref'] for row in rows]}, reasons=[reason])
            transfer = {'status': 'unresolved', 'missing_inputs': [reason],
                'needed_refs': [], 'link_refs': [row['sheet_ref'] for row in rows]}
        else:
            cell = rows[0]
            refs = [cell['sheet_ref']]
            scalar = annotation_scalar(cell)
            transfer = direct_target_application(store, context, cell, target, scope)
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
    components = COMPONENTS
    record_version = VERSION
    operations = OPERATIONS
    cells_table = CELLS
    binding_fields = ()

    def __init__(self, store, *, read_cells=None):
        self.store = store
        self._read_cells = read_cells

    def _record(self, context, reference, kind=None):
        if reference not in context.received_record_refs:
            raise ContractError('a105_aggregation_record_not_received')
        if not self.store.reference_subset([reference], plain(context.scope)):
            raise ContractError('a105_aggregation_record_outside_scope')
        record = self.store.get(reference)
        if kind is not None and record['record_type'] != kind:
            raise ContractError('a105_aggregation_record_type_mismatch')
        return record

    def populate(self, context, arguments, operation_key):
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, aggregation_population_schema())
        requested = list(context.assignment.get(REQUESTED, ()))
        if len(set(requested)) != len(requested) or any(name not in COMPONENTS for name in requested):
            raise ContractError('a105_aggregation_component_selection_invalid')
        request = {
            'operation_key': operation_key, 'arguments': args, 'scope': plain(context.scope),
            'requested_components': requested}

        direct, bindings = [], {}
        def retain(reference, kind=None, possessed=True):
            record = self._record(context, reference, kind) if possessed else self._native_provenance(context.scope, reference)
            bindings[reference] = identity('a105_aggregation_input_record', record)
            if possessed and reference not in direct:
                direct.append(reference)
            return record
        retain(args['assertion_ref'], 'hypothesis')
        if args['comparison_ref'] is not None:
            retain(args['comparison_ref'], 'hypothesis')
        selections = {}
        for experiment in args['experiments']:
            retain(experiment['experiment_ref'], 'reference')
            for selected in experiment['metrics'].values():
                if selected is not None:
                    key = selected['sheet_ref'], selected['component']
                    selections[key] = selected
        if selections and self._read_cells is None:
            raise ContractError('a105_aggregation_grade_reader_unbound')
        input_rows, sources, grouped = [], [], {}
        for sheet_ref, component in selections:
            grouped.setdefault(sheet_ref, []).append(component)
        native = LiteratureAssayGradingRepository(self.store)
        for sheet_ref, components in grouped.items():
            retain(sheet_ref, 'source')
            rows = self._read_cells(context, sheet_ref, components)
            validate_schema(rows, assay_grading_cells_schema())
            if [(row['sheet_ref'], row['component']) for row in rows] != [(sheet_ref, component) for component in components]:
                raise ContractError('a105_aggregation_component_not_received')
            # The callback supplies exact possessed rows. Revalidate numerical
            # identity against the saved native row without widening custody.
            expected_rows = native.fact_cells(context, [sheet_ref], components=components)
            if canonical(rows) != canonical(expected_rows):
                raise ContractError('a105_aggregation_component_not_received')
            input_rows.extend(deepcopy(rows))
            sources.append(sheet_ref)
        sheet = aggregate_a105(args, input_rows)
        for reference in list(dict.fromkeys(sources)):
            source = retain(reference, 'source')
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        # Retain closure facts, not source bytes or private numerical operands.
        for reference in sources:
            source = retain(reference, possessed=False)
            for ancestor in source.get('parent_source_refs', ()):
                if ancestor not in sources:
                    sources.append(ancestor)
        payload = {'version': VERSION, 'selection': args, 'source_cells': input_rows,
            'sheet': sheet, 'direct_record_refs': direct, 'input_source_refs': sources,
            'record_bindings': bindings}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
                'version': VERSION, 'retrieved_at': None, 'parent_source_refs': sources}
            sheet_ref = identity('source', {'origin': 'tool', 'record': record})
            new = not self.store.holds(sheet_ref)
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = _rows(payload, sheet_ref, requested)
            validate_schema(rows, aggregation_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key}),
                'record_refs': [sheet_ref], 'changed_record_refs': [sheet_ref] if new else [],
                'result': {'sheet_ref': sheet_ref, 'cells': rows}, 'feedback': None}
            self.store.table(self.operations).put({'sheet_ref': sheet_ref})
            self.publish_cells(sheet_ref, requested)
        return outcome

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        if reference != 'artifact_' + sha256(raw).hexdigest():
            raise ContractError('a105_aggregation_saved_hash_mismatch')
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as cause:
            raise ContractError('a105_aggregation_saved_json_required') from cause
        if not isinstance(result, dict):
            raise ContractError('a105_aggregation_saved_object_required')
        return result

    def read(self, sheet_ref):
        source = self.store.get(sheet_ref)
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool'
                or source.get('provider') != PROVIDER or source.get('version') != VERSION):
            raise ContractError('a105_aggregation_sheet_required')
        record = {key: value for key, value in source.items() if key not in ('id', 'record_type', 'origin')}
        if identity('source', {'origin': 'tool', 'record': record}) != sheet_ref:
            raise ContractError('a105_aggregation_saved_identity_mismatch')
        request = self._artifact_json(source['request_ref'])
        if set(request) != {'operation_key', 'arguments', 'scope', 'requested_components'}:
            raise ContractError('a105_aggregation_saved_selection_mismatch')
        scope = self.store.validate_scope(request['scope'])
        self._native_provenance(scope, sheet_ref)
        saved = self._artifact_json(source['artifact_ref'])
        if (set(saved) != {'version', 'selection', 'source_cells', 'sheet', 'direct_record_refs',
                'input_source_refs', 'record_bindings'} or saved['version'] != VERSION
                or saved['selection'] != request['arguments']
                or saved['input_source_refs'] != source['parent_source_refs']):
            raise ContractError('a105_aggregation_saved_selection_mismatch')
        validate_schema(saved['selection'], aggregation_population_schema())
        validate_schema(saved['source_cells'], assay_grading_cells_schema())
        validate_schema(saved['sheet'], aggregation_sheet_schema())
        for reference, digest in saved['record_bindings'].items():
            if (not self.store.reference_subset([reference], plain(scope))
                    or identity('a105_aggregation_input_record', self.store.get(reference)) != digest):
                raise ContractError('a105_aggregation_saved_input_mismatch')
        if not set(saved['direct_record_refs']) <= set(saved['record_bindings']):
            raise ContractError('a105_aggregation_saved_input_mismatch')
        native = LiteratureAssayGradingRepository(self.store)
        grouped = {}
        for row in saved['source_cells']:
            grouped.setdefault(row['sheet_ref'], []).append(row)
        for reference, originals in grouped.items():
            expected_rows = native.project_cells([reference],
                components=[row['component'] for row in originals])
            if canonical(originals) != canonical(expected_rows):
                raise ContractError('a105_aggregation_saved_input_mismatch')
        rows = _rows(saved, sheet_ref, request['requested_components'])
        validate_schema(rows, aggregation_cells_schema())
        return saved

    def project_cells(self, sheet_refs, *, components=None):
        selected = COMPONENTS if components is None else components
        if (not isinstance(selected, (list, tuple)) or len(set(selected)) != len(selected)
                or any(component not in COMPONENTS for component in selected)):
            raise ContractError('a105_aggregation_component_selection_invalid')
        rows = []
        for reference in dict.fromkeys(sheet_refs):
            rows.extend(_rows(self.read(reference), reference, selected))
        return rows

    def selected_sheet_refs(self, context):
        return self.owned_sheet_refs()

    def available_sheet_refs(self, context):
        refs = []
        for reference in context.received_record_refs:
            try:
                row = self.store.get(reference)
            except (LookupError, ContractError):
                continue
            if row.get('record_type') == 'source' and row.get('provider') == PROVIDER and row.get('version') == VERSION:
                self.read(reference)
                refs.append(reference)
        return list(dict.fromkeys(refs))

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        for row in cells:
            refs.extend((row['sheet_ref'], row['assertion_ref'], row['comparison_ref']))
            refs.extend(row['selected_experiment_refs'])
            refs.extend(row['source_refs'])
            refs.extend(LiteratureAssayGradingRepository.cell_record_refs(row['selected_components']))
        return list(dict.fromkeys(ref for ref in refs if ref is not None))


__all__ = ['PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'SCOPE', 'COMPONENTS',
    'OPERATION_DESCRIPTION', 'aggregation_cells_schema', 'LiteratureA105AggregationRepository']


def direct_target_application(store, context, cell, target, scope=None):
    """A105's current direct experiment-to-target links; no invented transfer kernel."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_and_context_sources.perturbation_evidence.component_assessment_dependencies import assessment_dependencies
    scope = plain(scope) if scope is not None else None
    experiments, linked, links, needed, states = set(cell['selected_experiment_refs']), set(), set(), set(), set()
    known = set(context.received_record_refs)
    for reference in known:
        row = store.get(reference)
        if row['record_type'] != 'assessment' or row['hypothesis_ref'] != cell['assertion_ref']:
            continue
        finding = row.get('investigation_finding')
        if finding is None or target not in finding['source_claim']['subject_refs'] or row['observation_ref'] not in known:
            continue
        observation = store.get(row['observation_ref'])
        references = {*observation.get('subject_refs', ()), *observation.get('source_subject_refs', ()),
            *observation.get('dependencies', ())}
        matching = experiments.intersection(references)
        if not matching:
            continue
        links.add(reference)
        dependency = assessment_dependencies(store, reference, known)
        if finding['status'] == 'withdrawn':
            states.add('withdrawn')
            continue
        if row['applicability'] == 'incomparable':
            states.add('invalid')
            continue
        if dependency is not None and dependency['retired']:
            continue
        if dependency is None or row['extent_basis'] == 'context_allocation':
            states.add('unresolved')
            continue
        required = {observation['source_ref'], *observation.get('dependencies', ()),
            *row['condition_refs'], *row['assumption_refs'],
            *finding['qualification']['context_refs'], *finding['qualification']['assumption_refs']}
        missing = required - (known | set(store.problem()['subject_refs']))
        needed.update(missing)
        extent = store.assessment_write_extent(row['id'])
        if missing or scope is not None and (not extent or not store.scope_contains(
                {'subject_refs': sorted({span['target_ref'] for span in extent}), 'segments': extent}, scope)):
            states.add('unresolved')
            continue
        states.add('established')
        linked.update(matching)
    established = bool(experiments) and linked == experiments
    return {'status': 'established' if established else 'withdrawn' if states == {'withdrawn'}
        else 'invalid' if states == {'invalid'} else 'unresolved',
        'missing_inputs': [] if established else ['a105_direct_target_experiment_application_unresolved'],
        'needed_refs': sorted(needed), 'link_refs': sorted(links), 'owner_states': sorted(states)}
